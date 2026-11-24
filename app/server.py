"""127.0.0.1 web adapter for the accepted SQLite four-feature Python API."""
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import argparse
import hashlib
import json
from pathlib import Path
import secrets
import sqlite3
from urllib.parse import parse_qs, unquote, urlsplit

from database import four_feature as four
from database import store
from retrieval.fusion_four import validate_weights

ROOT=Path(__file__).resolve().parent
DATABASE_SHA256='4d9b5436ac40209fe24b23c46657d00b3befafdbf2e40e37e4ce4f755ce9e2c7'
IMAGE_ROOT=Path('D:/TuNam4/dataset_HF_CFD_final/images').resolve()
STATIC={'/':('index.html','text/html; charset=utf-8'),
        '/styles.css':('styles.css','text/css; charset=utf-8'),
        '/app.js':('app.js','text/javascript; charset=utf-8'),
        '/favicon.svg':('favicon.svg','image/svg+xml')}


class ApiError(Exception):
    def __init__(self,status,code,message):
        self.status,self.code,self.message=status,code,message
        super().__init__(message)


class PortraitService:
    def __init__(self,database=four.DEFAULT_DB):
        self.database=Path(database).resolve()
        if store.digest(self.database)!=DATABASE_SHA256:
            raise ValueError('SQLite snapshot differs from the accepted database; refusing startup')
        self.signature=self._signature()
        self.token=secrets.token_urlsafe(32)
        with closing(self.connect()) as c:
            self.gallery=four.SqlFourGallery(c)
            self.counts=four.summary(c)
            self.catalog={r['image_id']:dict(r) for r in c.execute('SELECT * FROM Images')}
            self.statuses={key:[] for key in self.catalog}
            for r in c.execute('''SELECT v.image_id,f.feature_name,v.feature_version,v.dimension,v.dtype,v.status,v.missing_reason
                FROM FeatureVectors v JOIN FeatureVersions f USING(feature_version) ORDER BY f.feature_name'''):
                value=dict(r);key=value.pop('image_id');self.statuses[key].append(value)
        self.names={r['filename']:key for key,r in self.catalog.items()}
        if (len(self.catalog)!=1438 or sum(r['status']=='valid' for rows in self.statuses.values() for r in rows)!=5751
                or sum(r['status']=='missing' for rows in self.statuses.values() for r in rows)!=1):
            raise ValueError('Unexpected gallery feature coverage')
        for r in self.catalog.values():
            if IMAGE_ROOT not in Path(r['image_path']).resolve().parents:
                raise ValueError('Catalog image is outside the verified image root')

    def _signature(self):
        stat=self.database.stat()
        return stat.st_size,stat.st_mtime_ns

    def connect(self):
        c=store.connect(self.database,readonly=True)
        c.execute('PRAGMA query_only=ON')
        return c

    def check_snapshot(self):
        if self._signature()!=self.signature:
            raise ApiError(409,'snapshot_changed','Snapshot SQLite đã thay đổi. Hãy khởi động lại sau khi xác minh baseline.')

    def identity(self,value):
        if not isinstance(value,str) or len(value)>128 or any(x in value for x in ('/','\\',':','%','\x00')):
            raise ApiError(422,'invalid_image','Chỉ nhập image_id hoặc tên file trong gallery; không nhận đường dẫn.')
        key=value if value in self.catalog else self.names.get(value)
        if key is None:raise ApiError(404,'unknown_image','Không tìm thấy ảnh trong gallery. Kiểm tra ID hoặc tên file.')
        return key

    def item(self,key):
        r=self.catalog[key]
        return dict(image_id=key,filename=r['filename'],source=r['source'],
                    image_url='/media/'+key,features=self.statuses[key])

    def overview(self):
        self.check_snapshot()
        return dict(image_count=len(self.catalog),valid_vectors=5751,missing_vectors=1,comparison_pool=1437,
            counts=self.counts,medians=self.gallery.params['medians'],epsilon=self.gallery.params['epsilon'],
            epsilon_c1=self.gallery.params['epsilon_c1'],feature_versions=self.gallery.params['feature_versions'],
            default_weights=dict.fromkeys(four.fusion.KINDS,.25),weight_configuration='EXPERIMENTAL_EQUAL_WEIGHTS',
            readonly=True,history_enabled=False,new_image_support=False,database_sha256=DATABASE_SHA256,
            calibration_id=four.CALIBRATION_ID,csrf_token=self.token)

    def list_images(self,query='',source='',offset=0,limit=24):
        self.check_snapshot()
        if not isinstance(query,str) or len(query)>128 or source not in ('','CFD','HF') or not 0<=offset<=1438 or not 1<=limit<=100:
            raise ApiError(422,'invalid_filter','Bộ lọc gallery không hợp lệ.')
        keys=[key for key,r in sorted(self.catalog.items()) if query.casefold() in (key+' '+r['filename']).casefold()
              and (not source or r['source'].upper()==source)]
        return dict(total=len(keys),offset=offset,limit=limit,items=[self.item(k) for k in keys[offset:offset+limit]])

    def detail(self,value):
        self.check_snapshot();key=self.identity(value)
        with closing(self.connect()) as c:
            row=dict(c.execute('SELECT * FROM Images WHERE image_id=?',(key,)).fetchone())
            row['source_metadata']=json.loads(row.pop('metadata_json'))
            person=c.execute('SELECT * FROM Persons WHERE person_id=?',(row['person_id'],)).fetchone()
            eyes=[dict(r) for r in c.execute('''SELECT method,model_version,coordinate_role,left_x,left_y,right_x,right_y,
                coordinate_frame FROM EyeCoordinates WHERE image_id=? ORDER BY method''',(key,))]
        return dict(**self.item(key),metadata=row,person=dict(person) if person else None,eye_measurements=eyes)

    def media(self,value):
        key=self.identity(value)
        if value!=key:raise ApiError(404,'unknown_image','Media endpoint chỉ nhận image_id.')
        row=self.catalog[key];path=Path(row['image_path']).resolve()
        if IMAGE_ROOT not in path.parents:raise ApiError(403,'invalid_catalog_path','Đường dẫn ảnh không thuộc catalog đã xác minh.')
        try:payload=path.read_bytes()
        except OSError:raise ApiError(404,'image_missing','Không đọc được ảnh nguồn trong gallery.') from None
        if hashlib.sha256(payload).hexdigest()!=row['image_hash']:
            raise ApiError(409,'image_changed','Ảnh nguồn không còn khớp hash catalog.')
        return payload

    def search(self,payload):
        self.check_snapshot()
        if not isinstance(payload,dict) or set(payload)-{'image','weights','mode','top_k'}:
            raise ApiError(422,'invalid_request','Request tìm kiếm không hợp lệ.')
        key=self.identity(payload.get('image'))
        mode=payload.get('mode','fusion');top_k=payload.get('top_k',5)
        if mode not in (*four.MODES,'compare') or type(top_k)is not int or not 1<=top_k<=20:
            raise ApiError(422,'invalid_mode','Chọn A, B, C1, C2, Fusion hoặc so sánh; top_k từ 1 đến 20.')
        weights=payload.get('weights',dict.fromkeys(four.fusion.KINDS,.25))
        if (not isinstance(weights,dict) or set(weights)!=set(four.fusion.KINDS)
                or any(type(x) not in (float,int) for x in weights.values())):
            raise ApiError(422,'invalid_weights','Cần đủ bốn trọng số số học A, B, C1, C2.')
        try:validate_weights([weights[k] for k in four.fusion.KINDS])
        except (ValueError,OverflowError,TypeError):
            raise ApiError(422,'invalid_weights','Trọng số phải hữu hạn, không âm và tổng bằng 1 (sai số tuyệt đối 1e-12).') from None
        with closing(self.connect()) as c:
            result=four.query(c,key,weights=[weights[k] for k in four.fusion.KINDS],top_k=top_k,persist=False,gallery=self.gallery)
        # Presentation URLs only: rankings, weights and distances are unchanged API values.
        result['query']=dict(result['query'],image_url='/media/'+key)
        for rows in result['modes'].values():
            for row in rows:row['image_url']='/media/'+row['image_id']
        result.update(selected_mode=mode,readonly=True,history_saved=False)
        return result


class AppServer(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,address,service):
        if address[0]!='127.0.0.1':raise ValueError('This demo binds only to 127.0.0.1')
        self.service=service
        super().__init__(address,Handler)


class Handler(BaseHTTPRequestHandler):
    server_version='PortraitLocal/1'
    def send(self,status,payload,content_type):
        self.send_response(status)
        for k,v in [('Content-Type',content_type),('Content-Length',str(len(payload))),('Cache-Control','no-store'),
                    ('X-Content-Type-Options','nosniff'),('Referrer-Policy','same-origin'),
                    ('Cross-Origin-Resource-Policy','same-origin'),
                    ('Content-Security-Policy',"default-src 'self'; img-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")]:
            self.send_header(k,v)
        self.end_headers()
        if self.command!='HEAD':self.wfile.write(payload)

    def json(self,status,value):
        self.send(status,json.dumps(value,ensure_ascii=False,allow_nan=False).encode('utf8'),'application/json; charset=utf-8')

    def guard(self):
        host='127.0.0.1:'+str(self.server.server_port)
        if self.headers.get('Host')!=host:raise ApiError(403,'invalid_host','Chỉ truy cập qua địa chỉ loopback của ứng dụng.')
        origin=self.headers.get('Origin')
        if origin and origin!='http://'+host:raise ApiError(403,'invalid_origin','Request khác origin bị từ chối.')
        path=urlsplit(self.path).path
        decoded=unquote(path)
        if any(x in decoded for x in ('..','\\','\x00','%')):raise ApiError(404,'invalid_path','Đường dẫn không hợp lệ.')
        return decoded

    def dispatch(self):
        try:
            path=self.guard();service=self.server.service
            if self.command=='POST':
                if path!='/api/search':raise ApiError(405,'read_only','Không có endpoint sửa dữ liệu nguồn.')
                if self.headers.get('X-Application-Token')!=service.token:raise ApiError(403,'invalid_token','Phiên ứng dụng không hợp lệ. Tải lại trang.')
                if self.headers.get_content_type()!='application/json':raise ApiError(415,'invalid_content_type','Request phải là JSON.')
                try:length=int(self.headers.get('Content-Length','0'))
                except ValueError:raise ApiError(400,'invalid_json','Độ dài request không hợp lệ.') from None
                if not 0<length<=8192:raise ApiError(413,'body_size','Request rỗng hoặc quá lớn.')
                def constant(value):raise ValueError('Nonfinite JSON value')
                try:data=json.loads(self.rfile.read(length),parse_constant=constant)
                except (ValueError,UnicodeError):raise ApiError(400,'invalid_json','JSON không hợp lệ hoặc chứa NaN/Infinity.') from None
                return self.json(200,service.search(data))
            if self.command not in ('GET','HEAD'):raise ApiError(405,'read_only','Chỉ hỗ trợ đọc và tìm kiếm.')
            if path in STATIC:
                name,kind=STATIC[path];return self.send(200,(ROOT/'static'/name).read_bytes(),kind)
            if path=='/api/overview':return self.json(200,service.overview())
            if path=='/api/gallery':
                args=parse_qs(urlsplit(self.path).query,keep_blank_values=True)
                if set(args)-{'q','source','offset','limit'} or any(len(v)!=1 for v in args.values()):raise ApiError(422,'invalid_filter','Bộ lọc gallery không hợp lệ.')
                try:offset=int(args.get('offset',['0'])[0]);limit=int(args.get('limit',['24'])[0])
                except ValueError:raise ApiError(422,'invalid_filter','Phân trang không hợp lệ.') from None
                return self.json(200,service.list_images(args.get('q',[''])[0],args.get('source',[''])[0],offset,limit))
            if path.startswith('/api/images/'):return self.json(200,service.detail(path[len('/api/images/'):]))
            if path.startswith('/media/'):return self.send(200,service.media(path[len('/media/'):]),'image/png')
            raise ApiError(404,'not_found','Không tìm thấy endpoint hoặc tài nguyên.')
        except ApiError as error:self.json(error.status,dict(error=dict(code=error.code,message=error.message)))
        except (ValueError,OSError,sqlite3.Error):self.json(503,dict(error=dict(code='backend_unavailable',message='Không đọc được dữ liệu đã xác minh. Kiểm tra snapshot và khởi động lại ứng dụng.')))

    do_GET=dispatch
    do_HEAD=dispatch
    do_POST=dispatch
    do_PUT=dispatch
    do_DELETE=dispatch
    do_PATCH=dispatch


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args()
    service=PortraitService()
    with AppServer(('127.0.0.1',args.port),service) as server:
        print(f'Portrait Atlas: http://127.0.0.1:{server.server_port} / SQLite READ ONLY',flush=True)
        try:server.serve_forever()
        except KeyboardInterrupt:pass


if __name__=='__main__':main()
