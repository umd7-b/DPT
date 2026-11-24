"""Standalone C2 Euclidean324 gallery retrieval; no fusion or inferred alignment."""
from pathlib import Path
import argparse
import sys

import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from features.C2_hog.src import root_hog as hog
from features.C2_hog.src.common import BASE,read_json,read_csv,write_json,save_csv


def rank_vectors(matrix,ids,query,query_id=None,top_k=5):
    if type(top_k)is not int or top_k<=0:raise ValueError('top_k must be positive')
    if matrix.shape!=(len(ids),324) or matrix.dtype!=np.float64 or len(set(ids))!=len(ids):raise ValueError('Invalid matrix/IDs')
    if not np.isfinite(matrix).all() or np.any(matrix<0) or not np.allclose(np.linalg.norm(matrix,axis=1),1.,rtol=0,atol=1e-12):
        raise ValueError('Gallery must be finite globally L2-normalized C2')
    hog.validate_vector(query)
    distances=np.sqrt(np.sum((matrix-query[None,:])**2,axis=1))
    order=sorted((i for i,key in enumerate(ids) if key!=query_id),key=lambda i:(float(distances[i]),ids[i]))[:top_k]
    return [(ids[i],float(distances[i])) for i in order]


class C2Gallery:
    def __init__(self,directory=BASE/'full_v1'):
        self.directory=Path(directory);self.lock=hog.lock();self.manifest=read_json(self.directory/'manifest.json')
        if any(self.manifest.get(k)!=v for k,v in self.lock.items()):raise ValueError('Query/gallery C2 lock mismatch')
        for name,record in self.manifest['artifacts'].items():
            if Path(name).name!=name or hog.sha256(self.directory/name)!=record['sha256']:raise ValueError('C2 artifact hash mismatch: '+name)
        self.schema=read_json(self.directory/'feature_schema.json')
        if hog.content_hash(self.schema)!=self.schema['content_sha256'] or self.schema['content_sha256']!=self.manifest['schema_content_sha256']:
            raise ValueError('Schema content mismatch')
        self.matrix=np.load(self.directory/'features_C2.npy',allow_pickle=False)
        self.rows=sorted(read_csv(self.directory/'feature_rows.csv'),key=lambda r:int(r['feature_row_index']))
        if self.matrix.shape!=(len(self.rows),324) or self.matrix.dtype!=np.float64:raise ValueError('C2 shape/dtype mismatch')
        self.by_id={}
        for i,row in enumerate(self.rows):
            if int(row['feature_row_index'])!=i or row['image_id'] in self.by_id or any(row[k]!=v for k,v in self.lock.items()):
                raise ValueError('C2 identity/index/version mismatch')
            hog.validate_vector(self.matrix[i]);self.by_id[row['image_id']]=row
        status=read_csv(self.directory/'extraction_status.csv');self.status={r['image_id']:r for r in status}
        if len(self.status)!=len(status) or len(status)!=self.manifest['processed'] or {r['image_id'] for r in status if r['status']=='valid_C2'}!=set(self.by_id):
            raise ValueError('C2 status/gallery identities differ')
        self.matrix.flags.writeable=False

    def vector(self,identity):return self.matrix[int(self.by_id[identity]['feature_row_index'])].copy()

    def search(self,image,top_k=5):
        path=Path(image);identity=path.stem
        if identity not in self.by_id:
            if identity in self.status:raise ValueError('missing_C2: '+self.status[identity]['missing_reason'])
            raise ValueError('Gallery query only; no assumed new-image alignment')
        if path.is_file() and hog.sha256(path)!=self.by_id[identity]['image_sha256']:raise ValueError('Query file differs from gallery source')
        ranking=rank_vectors(self.matrix,[r['image_id'] for r in self.rows],self.vector(identity),identity,top_k)
        return identity,[dict(rank=i,**self.by_id[key],distance=distance) for i,(key,distance) in enumerate(ranking,1)]


def comparison(gallery,identity,results,path):
    entries=[gallery.by_id[identity]]+results;columns=3;rows=(len(entries)+2)//3
    canvas=np.full((40+rows*316,768,3),250,np.uint8)
    cv2.putText(canvas,'C2 ONLY / Euclid324 / center-crop prototype',(8,25),0,.52,(20,20,20),1,cv2.LINE_AA)
    for i,row in enumerate(entries):
        if hog.sha256(row['image_path'])!=row['image_sha256']:raise ValueError('Source image hash changed')
        image=cv2.imread(row['image_path'],cv2.IMREAD_UNCHANGED)
        if image.shape!=(256,256,3):raise ValueError('Unexpected image')
        x,y=(i%columns)*256,40+(i//columns)*316;canvas[y:y+256,x:x+256]=image
        cv2.putText(canvas,'QUERY (excluded)' if i==0 else '#'+str(row['rank'])+' Euclid',(x+7,y+274),0,.45,(20,20,20),1,cv2.LINE_AA)
        cv2.putText(canvas,row['filename'],(x+7,y+291),0,.4,(20,20,20),1,cv2.LINE_AA)
        if i:cv2.putText(canvas,f"d={row['distance']:.10f}",(x+7,y+309),0,.4,(20,20,20),1,cv2.LINE_AA)
    if not cv2.imwrite(str(path),canvas):raise OSError('Could not write comparison')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--image',required=True)
    parser.add_argument('--top-k',type=int,default=5);parser.add_argument('--gallery',type=Path,default=BASE/'full_v1');parser.add_argument('--output',type=Path)
    args=parser.parse_args();gallery=C2Gallery(args.gallery);identity,results=gallery.search(args.image,args.top_k)
    out=args.output or args.gallery/'queries'/identity
    if out.exists():raise FileExistsError('Run output exists; choose a fresh --output')
    out.mkdir(parents=True)
    fields=['rank','image_id','filename','source','distance','feature_row_index','spec_hash','implementation_sha256','preprocessing_id']
    save_csv(out/'results.csv',[{k:r[k] for k in fields} for r in results])
    write_json(out/'results.json',dict(schema_id='C2_ONLY_QUERY_v1',**gallery.lock,query=gallery.by_id[identity],
        metric='Euclid324 = sqrt(sum((a-b)^2))',self_excluded=True,tie_break='distance then image_id',new_image_support=False,results=results))
    comparison(gallery,identity,results,out/'comparison.png')
    for r in results:print(r['rank'],r['filename'],f"Euclid={r['distance']:.12f}")
    print('Saved C2 CSV/JSON/PNG:',out)


if __name__=='__main__':main()
