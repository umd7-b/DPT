"""Validated uploads, server-authoritative crops and real external query extraction."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import hashlib
import io
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import threading
import time
import uuid

import numpy as np
from PIL import Image,ImageOps,UnidentifiedImageError

from app import external_config as config
from database import four_feature as four
from database import store
from retrieval import fusion_four as fusion


class ExternalError(ValueError):pass


def decode(payload,claimed_mime):
    if not 0<len(payload)<=config.MAX_UPLOAD_BYTES:raise ExternalError('Ảnh vượt giới hạn 10 MiB hoặc rỗng.')
    try:
        with Image.open(io.BytesIO(payload)) as source:
            fmt=source.format
            if fmt not in config.FORMATS or getattr(source,'n_frames',1)!=1:raise ExternalError('Chỉ nhận PNG, JPEG hoặc WebP tĩnh.')
            if claimed_mime not in (config.FORMATS[fmt],'application/octet-stream'):raise ExternalError('MIME không khớp định dạng thực của ảnh.')
            w,h=source.size
            if w*h>config.MAX_PIXELS or max(w,h)>config.MAX_SIDE:raise ExternalError('Ảnh vượt 16 triệu pixel hoặc cạnh 8192 pixel.')
            orientation=int(source.getexif().get(274,1));source.load()
            oriented=ImageOps.exif_transpose(source)
            if 'A' in oriented.getbands() or 'transparency' in source.info:
                rgba=oriented.convert('RGBA');image=Image.new('RGB',rgba.size,'white');image.paste(rgba,mask=rgba.getchannel('A'))
            else:image=oriented.convert('RGB')
            # Render the same decoded RGB numbers in browser PNG and OpenCV.
            # Do not carry ICC/gamma metadata that browsers interpret differently.
            image.info.clear()
            return image,dict(format=fmt,encoded_width=w,encoded_height=h,orientation=orientation,width=image.width,height=image.height)
    except (UnidentifiedImageError,OSError,Image.DecompressionBombError,ValueError) as error:
        if isinstance(error,ExternalError):raise
        raise ExternalError('Không giải mã được ảnh hoặc định dạng bị hỏng.') from error


def crop_image(image,x,y,size):
    if any(type(v)is not int for v in (x,y,size)) or size<1 or x<0 or y<0 or x+size>image.width or y+size>image.height:
        raise ExternalError('Vùng cắt phải là hình vuông theo pixel gốc và nằm hoàn toàn trong ảnh.')
    return image.crop((x,y,x+size,y+size)).resize((256,256),Image.Resampling.BICUBIC)


def rank_external(gallery,vectors,query_hash,weights,top_k=5):
    fusion.validate_weights(weights)
    if set(vectors)!=set(fusion.KINDS):raise ExternalError('Full Fusion cần đủ bốn vector thật.')
    for k,n in fusion.DIMENSIONS.items():
        if vectors[k].shape!=(n,) or vectors[k].dtype!=np.float64 or not np.isfinite(vectors[k]).all():raise ExternalError('Sai shape/dtype/query vector: '+k)
    from features.C1_lbp.src.lbp236 import validate_vector as validate_c1
    from features.C2_hog.src.root_hog import validate_vector as validate_c2
    validate_c1(vectors['c1']);validate_c2(vectors['c2'])
    raw=fusion.component_distances(vectors,gallery.vectors);normalized,total=fusion.combine(raw,gallery.params,weights)
    excluded={key for key,row in gallery.by_id.items() if row['image_sha256']==query_hash}
    modes={k:[] for k in (*fusion.KINDS,'fusion')}
    for mode in modes:
        scores=total if mode=='fusion' else raw[mode]
        ids=[i for i,key in enumerate(gallery.ids) if key not in excluded]
        ordered=sorted(ids,key=lambda i:(float(scores[i]),gallery.ids[i]))[:top_k]
        for rank,i in enumerate(ordered,1):
            row=gallery.by_id[gallery.ids[i]]
            modes[mode].append(dict(mode=mode,rank=rank,image_id=row['image_id'],filename=row['filename'],source=row['source'],
                image_url='/media/'+row['image_id'],score=float(scores[i]),D=float(total[i]),
                **{'distance_'+k:float(raw[k][i]) for k in fusion.KINDS},
                **{'normalized_'+k:float(normalized[k][i]) for k in fusion.KINDS}))
    return dict(status='ok',modes=modes,excluded_self_ids=sorted(excluded),self_exclusion_count=len(set(gallery.ids)&excluded),
        candidate_count=len(gallery.ids)-len(set(gallery.ids)&excluded),gallery_intersection_count=len(gallery.ids),
        medians=gallery.params['medians'],weights=dict(zip(fusion.KINDS,map(float,weights))),epsilon=fusion.EPSILON,epsilon_c1=fusion.EPSILON_C1)


class ExternalStore:
    def __init__(self,service):
        self.service=service;self.jobs={};self.lock=threading.RLock();self.executor=ThreadPoolExecutor(max_workers=1)
        config.RUNTIME.mkdir(parents=True,exist_ok=True)
        self.stop_event=threading.Event()
        self.janitor=threading.Thread(target=self._janitor,daemon=True);self.janitor.start()

    def _janitor(self):
        while not self.stop_event.wait(30):
            try:self.cleanup()
            except OSError:pass  # Retry next interval if a query file is still held by Windows.

    def close(self):
        self.stop_event.set();self.executor.shutdown(wait=True)
        for key in list(self.jobs):self.discard(key)

    def get(self,identity):
        if not isinstance(identity,str) or not re.fullmatch('[a-f0-9]{32}',identity):raise ExternalError('Query ID không hợp lệ.')
        with self.lock:
            if identity not in self.jobs:raise ExternalError('Phiên ảnh không tồn tại hoặc đã hết hạn.')
            job=self.jobs[identity]
            if time.time()-job['created']>config.TTL_SECONDS and not job['busy']:
                job['created']=time.time();self.discard(identity);raise ExternalError('Phiên ảnh đã hết hạn sau 30 phút.')
            return job

    def upload(self,payload,mime,filename):
        self.cleanup()
        if len(self.jobs)>=config.MAX_SESSIONS:raise ExternalError('Đã có 8 phiên ảnh. Xóa phiên không dùng trước khi upload.')
        if not filename or len(filename)>160 or any(c in filename for c in ('/','\\')) or any(ord(c)<32 for c in filename):raise ExternalError('Tên file không hợp lệ.')
        image,meta=decode(payload,mime);key=uuid.uuid4().hex;folder=config.RUNTIME/key;folder.mkdir()
        (folder/'input.bin').write_bytes(payload);image.save(folder/'source.png')
        job=dict(id=key,folder=folder,image=image,metadata=meta,filename=filename,created=time.time(),input_sha256=hashlib.sha256(payload).hexdigest(),
            revision=0,confirmed=False,busy=False,status='cropping',features={},result=None,events=['uploading','cropping'],lock=threading.RLock())
        (folder/'session.json').write_text(json.dumps(dict(owner='PORTRAIT_EXTERNAL_v1',id=key,created=job['created'],busy=False)),encoding='utf8')
        with self.lock:self.jobs[key]=job
        return dict(job_id=key,filename=filename,**meta,preprocessing=config.PREPROCESSING,source_url='/api/external/media/'+key+'/source')

    def crop(self,key,x,y,size,revision):
        job=self.get(key)
        with job['lock']:
            if job['busy']:raise ExternalError('Đang trích xuất, chưa thể thay crop.')
            if type(revision)is not int or revision<=job['revision']:raise ExternalError('Crop revision cũ; hãy thử lại.')
            image=crop_image(job['image'],x,y,size);path=job['folder']/('crop_'+str(revision)+'.png')
            payload=(job['folder']/'input.bin').read_bytes()
            with Image.open(io.BytesIO(payload)) as original:
                preserve=(job['metadata']['format']=='PNG' and job['metadata']['orientation']==1 and job['image'].size==(256,256)
                          and (x,y,size)==(0,0,256) and original.mode=='RGB'
                          and not {'icc_profile','gamma','srgb','chromaticity'}.intersection(original.info))
            if preserve:path.write_bytes(payload)
            else:image.save(path)
            job.update(revision=revision,confirmed=False,crop=dict(x=x,y=y,size=size),final_path=path,
                final_sha256=store.digest(path),vectors=None,result=None,status='cropping',features={})
            return dict(job_id=key,revision=revision,crop=job['crop'],width=256,height=256,sha256=job['final_sha256'],
                        preview_url='/api/external/media/'+key+'/crop?revision='+str(revision),preprocessing=config.PREPROCESSING)

    def confirm(self,key,revision):
        job=self.get(key)
        with job['lock']:
            if type(revision)is not int or job['busy'] or revision!=job['revision'] or not job.get('final_path'):raise ExternalError('Hãy chờ preview crop mới nhất rồi xác nhận.')
            job['confirmed']=True;return dict(job_id=key,revision=revision,sha256=job['final_sha256'],status='confirmed')

    def media(self,key,kind,revision=None):
        job=self.get(key)
        if kind=='source':return (job['folder']/'source.png').read_bytes()
        if kind=='crop' and revision==job['revision'] and job.get('final_path'):return job['final_path'].read_bytes()
        raise ExternalError('Không tìm thấy preview crop hiện tại.')

    def start(self,key,weights,mode,top_k):
        try:fusion.validate_weights(weights)
        except (ValueError,OverflowError,TypeError):raise ExternalError('Trọng số phải hữu hạn, không âm và tổng bằng 1 (atol 1e-12).') from None
        if mode not in (*fusion.KINDS,'fusion','compare') or type(top_k)is not int or not 1<=top_k<=20:raise ExternalError('Mode hoặc Top-K không hợp lệ.')
        job=self.get(key)
        with job['lock']:
            if not job['confirmed'] or job['busy']:raise ExternalError('Cần xác nhận crop trước khi tìm kiếm; mỗi phiên chỉ chạy một request.')
            job.update(busy=True,status='extracting',result=None,error=None)
            (job['folder']/'session.json').write_text(json.dumps(dict(owner='PORTRAIT_EXTERNAL_v1',id=key,created=job['created'],busy=True)),encoding='utf8')
            job['events'].append('extracting');self.executor.submit(self._run,job,list(weights),mode,top_k)
        return self.status(key)

    def worker(self,module,python,args,log):
        process=subprocess.run([str(python),'-X','utf8','-B','-m',module,*map(str,args)],cwd=config.ROOT,
            capture_output=True,text=True,encoding='utf8',timeout=config.WORKER_TIMEOUT)
        log.write_text(process.stdout+'\n'+process.stderr,encoding='utf8')
        if process.returncode:raise ExternalError('Worker '+module+' thất bại; xem log phiên để kiểm tra model/schema.')

    def _run(self,job,weights,mode,top_k):
        try:
            path=job['final_path'];checksum=job['final_sha256'];dest=job['folder']/('features_'+str(job['revision']))
            if not job.get('vectors'):
                self.worker('app.external_worker',config.ROOT/'.venv311/Scripts/python.exe',
                    ['--image',path,'--output',dest],job['folder']/'ac_worker.log')
                ac=json.loads((dest/'ac_status.json').read_text('utf8'));job['features']=ac['features'];job['extraction_provenance']=ac
                if ac['status']=='failed':
                    job['features']['b']=dict(status='not_extracted',missing_reason='face_count_gate_failed')
                    raise ExternalError('Không có khuôn mặt.' if ac['face_count']==0 else 'Có nhiều khuôn mặt. Chọn vùng chỉ chứa một khuôn mặt.')
                self.worker('retrieval.ab_query_worker_v2',config.ROOT/'.venv-uniface/Scripts/python.exe',
                    ['--kind','b','--image',path,'--output',dest,'--gallery',four.db.b_v2.DEFAULT_OUTPUT],job['folder']/'b_worker.log')
                b=json.loads((dest/'b_status.json').read_text('utf8'));job['features']['b']=b
                versions=self.service.gallery.params['feature_versions']
                observed=dict(a=ac['features']['a']['schema_id'],b=b['schema_id'],c1=ac['features']['c1']['feature_version'],c2=ac['features']['c2']['feature_version'])
                if observed!=versions or b.get('mask_lineage',{}).get('model_sha256')!='0d9bd318e46987c3bdbfacae9e2c0f461cae1c6ac6ea6d43bbe541a91727e33f':
                    raise ExternalError('Query feature/schema/model version mismatch.')
                with closing(self.service.connect()) as c:
                    hashes={r['stage_name']:r['stats_sha256'] for r in c.execute('SELECT * FROM NormalizationStages')}
                if (ac['features']['a']['stats_sha256']!=hashes['zscore150'] or b['moment_stats_sha256']!=hashes['Lab24']
                        or b['final_stats_sha256']!=hashes['final144'] or ac['image_sha256']!=checksum or store.digest(path)!=checksum):
                    raise ExternalError('Query image/normalization hash mismatch.')
                files=dict(a='query_A_normalized.npy',b='query_B_normalized.npy',c1='query_C1.npy',c2='query_C2.npy')
                vectors={k:np.load(dest/name,allow_pickle=False) for k,name in files.items() if (dest/name).is_file()}
                job['vectors']=vectors
            self.service.check_snapshot();job['status']='searching';job['events'].append('searching')
            vectors=job['vectors']
            if set(vectors)==set(fusion.KINDS):result=rank_external(self.service.gallery,vectors,checksum,weights,top_k)
            else:result=dict(status='fusion_unavailable',missing_reason='; '.join(k+':'+str(v.get('missing_reason',v.get('hair',v.get('status')))) for k,v in job['features'].items() if k not in vectors),
                    modes={k:[] for k in (*fusion.KINDS,'fusion')},weights=dict(zip(fusion.KINDS,weights)),medians=self.service.gallery.params['medians'],
                    candidate_count=1437,self_exclusion_count=0,gallery_intersection_count=1437)
            result.update(query=dict(image_id=None,filename=job['filename'],source='external',image_url='/api/external/media/'+job['id']+'/crop?revision='+str(job['revision'])),
                selected_mode=mode,extraction_status=job['features'],preprocessing=config.PREPROCESSING,crop=job['crop'],source_dimensions=job['metadata'],
                query_sha256=checksum,pixel_sha256=job['extraction_provenance']['pixel_sha256'],alignment_applied=False,
                original_url='/api/external/media/'+job['id']+'/source',readonly=True,history_saved=False)
            job.update(result=result,status='completed' if result['status']=='ok' else 'missing_feature')
            job['events'].append(job['status'])
        except Exception as error:
            job.update(status='failed',error=str(error));job['events'].append('failed')
        finally:
            (job['folder']/'session.json').write_text(json.dumps(dict(owner='PORTRAIT_EXTERNAL_v1',id=job['id'],created=job['created'],busy=False)),encoding='utf8')
            job['busy']=False

    def status(self,key):
        job=self.get(key)
        return dict(job_id=key,status=job['status'],busy=job['busy'],features=dict(job['features']),result=job['result'],error=job.get('error'),events=list(job['events']))

    def discard(self,key):
        job=self.get(key)
        if job['busy']:raise ExternalError('Đang xử lý, chưa thể xóa phiên.')
        path=job['folder'].resolve();base=config.RUNTIME.resolve()
        if path.parent!=base or path.name!=key or not re.fullmatch('[a-f0-9]{32}',key):raise ExternalError('Unsafe cleanup target')
        shutil.rmtree(path)
        with self.lock:self.jobs.pop(key,None)

    def cleanup(self):
        for key,job in list(self.jobs.items()):
            if not job['busy'] and time.time()-job['created']>config.TTL_SECONDS:
                # Avoid recursive expired get() while deleting a verified owned directory.
                job['created']=time.time();self.discard(key)
        # Only folders with our UUID name and ownership marker can be removed.
        for path in config.RUNTIME.iterdir():
            if not path.is_dir() or not re.fullmatch('[a-f0-9]{32}',path.name) or path.name in self.jobs:continue
            marker=path/'session.json'
            try:record=json.loads(marker.read_text('utf8'))
            except (OSError,ValueError):continue
            if (record.get('owner')=='PORTRAIT_EXTERNAL_v1' and record.get('id')==path.name
                    and time.time()-record.get('created',time.time())>config.TTL_SECONDS
                    and (not record.get('busy') or time.time()-record['created']>config.TTL_SECONDS+2*config.WORKER_TIMEOUT*config.MAX_SESSIONS+120)
                    and path.resolve().parent==config.RUNTIME.resolve()):shutil.rmtree(path.resolve())
