"""Read-only A/B source and artifact audit; reporting assets only."""
from pathlib import Path
import ast, csv, hashlib, json, math, sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

OUT=ROOT/'docs/reports'; BUILD=OUT/'_build'; FIG=OUT/'figures'
FIG.mkdir(parents=True,exist_ok=True)
DATA=Path('D:/TuNam4/dataset_HF_CFD_final')
B=ROOT/'outputs/B_color/color_features_full_v1'
A=ROOT/'outputs/A_geometry/features'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def dump(name,obj): (BUILD/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=lambda v:v.item() if isinstance(v,np.generic) else str(v)),encoding='utf-8')
def protected():
    result={}
    for folder in ('features','shared','retrieval','src','tests','docs','outputs','annotations','models','scripts'):
        for p in (ROOT/folder).rglob('*'):
            if p.is_file() and OUT not in p.parents and '__pycache__' not in p.parts:
                result[str(p.resolve())]=sha(p)
    for p in DATA.rglob('*'):
        if p.is_file():result[str(p.resolve())]=sha(p)
    p=Path('C:/Users/USER/Downloads/csdldpt.pdf');result[str(p)]=sha(p)
    return result
if (BUILD/'protected_before.json').exists():
    assert json.loads((BUILD/'protected_before.json').read_text(encoding='utf-8'))==protected()
else:dump('protected_before.json',protected())
assert sha('C:/Users/USER/Downloads/csdldpt.pdf')=='8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80'
inventory=[]; listing=[]
for folder in ('features/A_geometry','features/B_color','shared','retrieval','tests'):
    for p in sorted((ROOT/folder).rglob('*.py')):
        text=p.read_text(encoding='utf-8-sig'); tree=ast.parse(text)
        funcs=[{'name':n.name,'line':n.lineno} for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
        inventory.append({'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'lines':len(text.splitlines()),'functions':funcs})
        listing.append('\n\n### '+str(p.relative_to(ROOT))+'\n'+'\n'.join(f'{i:04}: {line}' for i,line in enumerate(text.splitlines(),1)))
dump('source_inventory.json',inventory)
(BUILD/'source_review.txt').write_text(''.join(listing),encoding='utf-8')
ar=np.load(A/'features_A_raw.npy',allow_pickle=False); az=np.load(A/'features_A_normalized.npy',allow_pickle=False)
br=np.load(B/'features_B_raw.npy',allow_pickle=False); bz=np.load(B/'features_B_normalized.npy',allow_pickle=False)
am=read(A/'metadata.csv'); bm=read(B/'feature_rows.csv')
def audit_matrix(x,z,stats_path):
    with np.load(stats_path,allow_pickle=False) as f: mu=f['mean'].copy();std=f['std'].copy()
    means=x.astype(np.float64).mean(axis=0); rawstd=x.astype(np.float64).std(axis=0)
    safe=np.where(rawstd<1e-8,1,rawstd); expected=(x.astype(np.float64)-mu)/std
    np.testing.assert_allclose(mu,means,atol=1e-12);np.testing.assert_allclose(std,safe,atol=1e-12)
    if z.dtype==np.float32:np.testing.assert_array_equal(z,expected.astype(np.float32))
    else:np.testing.assert_array_equal(z,expected)
    return dict(shape=list(x.shape),raw_dtype=str(x.dtype),normalized_dtype=str(z.dtype),finite=bool(np.isfinite(x).all() and np.isfinite(z).all()),
        zero_or_near_zero_dimensions=np.flatnonzero(rawstd<1e-8).tolist(),raw_std_min=float(rawstd.min()),raw_std_max=float(rawstd.max()),
        max_saved_mean_error=float(np.max(np.abs(mu-means))),max_saved_divisor_error=float(np.max(np.abs(std-safe))),
        max_z_float64_reconstruction_error=float(np.max(np.abs(z-expected))),
        max_abs_z_mean=float(np.max(np.abs(z.astype(np.float64).mean(axis=0)))),
        max_z_std_error=float(np.max(np.abs(z.astype(np.float64).std(axis=0)-1))),
        raw_min=float(x.min()),raw_max=float(x.max()),z_min=float(z.min()),z_max=float(z.max()))
facts={'A':audit_matrix(ar,az,A/'geometry_stats.npz'),'B':audit_matrix(br,bz,B/'normalization_stats.npz')}
assert len(am)==len(ar)==1438 and len(bm)==len(br)==1437
facts['A']['failed_rows']=len(read(A/'failed_images.csv'))
facts['A']['eye_distance_min']=min(float(r['eye_distance']) for r in am)
facts['A']['eye_distance_max']=max(float(r['eye_distance']) for r in am)
facts['A']['eye_distance_median']=float(np.median([float(r['eye_distance']) for r in am]))
facts['B_summary']=json.loads((B/'summary.json').read_text())
facts['missing_B']=read(B/'missing_features.csv')
shapes={}; pixel_index={}
for path in sorted((DATA/'images').glob('*.png')):
    im=cv2.imread(str(path),cv2.IMREAD_UNCHANGED)
    shapes[str(im.shape)]=shapes.get(str(im.shape),0)+1
    pixel_index.setdefault(hashlib.sha256(im.tobytes()).hexdigest(),[]).append(path.name)
facts['image_shapes']=shapes
from features.A_geometry.src import geometry_features as geom
sample=DATA/'images/cfd_final_00001.png'
p=geom.detect_landmarks(sample)
norm,d=geom.normalize_landmarks(p); a2=geom.calculate_ratios(p)
raw=np.r_[norm.flatten().astype(np.float32),a2]
sample_i=[r['image_name'] for r in am].index(sample.name)
facts['sample_geometry']={'image':sample.name,'points':p.tolist(),'normalized_points':norm.tolist(),'eye_distance':d,
    'eye_left':p[36:42].mean(axis=0).tolist(),'eye_right':p[42:48].mean(axis=0).tolist(),
    'center':((p[36:42].mean(axis=0)+p[42:48].mean(axis=0))/2).tolist(),
    'ratios':a2.tolist(),'max_saved_row_error':float(np.max(np.abs(raw-ar[sample_i]))),'mapping':geom.INDICES}
np.testing.assert_array_equal(raw,ar[sample_i])
# Independent scalar formulas for every A2 on real coordinates.
pf=p.astype(float); dist=lambda i,j:math.dist(pf[i],pf[j]); eL=pf[36:42].mean(0);eR=pf[42:48].mean(0);c=(eL+eR)/2
q={'d':math.dist(eL,eR),'h':math.dist((pf[21]+pf[22])/2,pf[8]),'wf':dist(2,14),'wj':dist(4,12),
   'wl':dist(36,39),'wr':dist(42,45),'vl1':dist(37,41),'vl2':dist(38,40),'vr1':dist(43,47),'vr2':dist(44,46),
   'wn':dist(31,35),'wm':dist(48,54),'om':dist(62,66),'en':math.dist(c,pf[30]),
   'em':math.dist(c,(pf[48]+pf[54])/2),'nc':dist(30,8)}
ep=1e-8; u=pf[4]-pf[8];v=pf[12]-pf[8]
ind=[q['wf']/(q['h']+ep),q['d']/(q['h']+ep),q['wl']/(q['d']+ep),q['wr']/(q['d']+ep),
 (q['vl1']+q['vl2'])/(2*q['wl']+ep),(q['vr1']+q['vr2'])/(2*q['wr']+ep),q['wn']/(q['d']+ep),q['wm']/(q['d']+ep),
 q['om']/(q['d']+ep),q['en']/(q['d']+ep),q['em']/(q['d']+ep),q['nc']/(q['h']+ep),q['wj']/(q['h']+ep),
 math.degrees(math.acos(np.clip(np.dot(u,v)/(math.sqrt(np.dot(u,u))*math.sqrt(np.dot(v,v))),-1,1)))]
facts['sample_geometry']['quantities']=q
facts['sample_geometry']['independent_A2']=ind
facts['sample_geometry']['independent_A2_max_error']=float(np.max(np.abs(np.array(ind)-a2)))
np.testing.assert_allclose(a2,ind,atol=3e-5,rtol=2e-6)
# Recover identities of original saved A panels by exact decoded-pixel equality.
facts['saved_A_top5']={}
mu=np.load(A/'geometry_stats.npz')['mean'];std=np.load(A/'geometry_stats.npz')['std']
for name in ('cfd_final_00001.png','cfd_final_00088.png','cfd_final_00144.png'):
    saved=ROOT/'outputs/retrieval/search_results'/f'{Path(name).stem}_top5.png';canvas=cv2.imread(str(saved))
    recovered=[]
    for i in range(6):
        key=hashlib.sha256(canvas[:256,256*i:256*(i+1)].tobytes()).hexdigest()
        candidates=pixel_index.get(key,[])
        if len(candidates)!=1:raise ValueError(('Ambiguous saved panel',name,i,candidates))
        recovered.append(candidates[0])
    qi=[r['image_name'] for r in am].index(name);query=(ar[qi].astype(float)-mu)/std
    distances=np.linalg.norm(az.astype(float)-query,axis=1);distances[qi]=np.inf
    chosen=np.argsort(distances)[:5]
    ranked=[am[int(j)]['image_name'] for j in chosen]
    assert recovered[0]==name and recovered[1:]==ranked,(name,recovered,ranked)
    facts['saved_A_top5'][name]={'image_path':str(saved),'recovered_panel_names':recovered,
         'results':[{'rank':k,'image_name':am[int(j)]['image_name'],'distance':float(distances[j])} for k,j in enumerate(chosen,1)]}
# Plot style and real data figures.
font=font_manager.FontProperties(fname='C:/Windows/Fonts/arial.ttf').get_name()
plt.rcParams.update({'font.family':font,'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':180})
def save(name):plt.savefig(FIG/name,bbox_inches='tight',facecolor='white');plt.close()
image=cv2.cvtColor(cv2.imread(str(sample)),cv2.COLOR_BGR2RGB)
fig,ax=plt.subplots(figsize=(7,6.5));ax.imshow(image);groups=[(0,17,'Hàm'),(17,22,'Mày trái'),(22,27,'Mày phải'),(27,36,'Mũi'),(36,42,'Mắt trái'),(42,48,'Mắt phải'),(48,68,'Miệng')]
for start,stop,label in groups:
    line=ax.plot(p[start:stop,0],p[start:stop,1],'.-',ms=4,lw=.7,label=label)[0]
    for i in range(start,stop):ax.annotate(str(i),p[i],xytext=(2,2),textcoords='offset points',fontsize=7,color=line.get_color(),fontweight='bold')
ax.axis('off');ax.legend(loc='upper left',bbox_to_anchor=(1,1),fontsize=8);save('landmarks_68.png')
fig,axs=plt.subplots(1,2,figsize=(10,3.2))
axs[0].barh(['A1: tọa độ','A2: tỉ lệ/góc'],[136,14],color=['#235d78','#be8951']);axs[0].set_xlim(0,150);axs[0].set_xlabel('Số chiều');axs[0].set_title('A150 = A1 + A2')
axs[1].barh(['Skin72','Hair72'],[72,72],color=['#be8951','#235d78']);axs[1].set_xlabel('Mỗi vùng: 48 HS + 12 Lab + 12 Hue');axs[1].set_title('B144 = Skin72 + Hair72');save('vector_structure.png')
for kind,x,z,indices,names in [('A',ar,az,[0,136,149],['A1: x của p0','A2: rộng/cao mặt','A2: góc cằm (độ)']),('B',br,bz,[3,48,143],['Skin HS bin h00/s3','Skin Lab L mean','Hair circular std'])]:
    fig,axs=plt.subplots(3,2,figsize=(9,6.4))
    for i,(j,label) in enumerate(zip(indices,names)):
        axs[i,0].hist(x[:,j],bins=35,color='#235d78',alpha=.85);axs[i,1].hist(z[:,j],bins=35,color='#be8951',alpha=.9)
        axs[i,0].set_ylabel('Số ảnh');axs[i,0].set_title(label+' — raw',fontsize=10);axs[i,1].set_title('Z-score theo kho',fontsize=10)
    fig.tight_layout();save(f'{kind}_distributions.png')
# Five-tile mask example composed only from real stored predictions.
fig,axs=plt.subplots(2,5,figsize=(12,5.2))
for y,name in enumerate(('cfd_final_00001.png','hf_merged_00209.png')):
    im=cv2.imread(str(DATA/'images'/name));stem=Path(name).stem
    skin=cv2.imread(str(ROOT/'outputs/B_color/uniface_full/masks/skin'/f'{stem}_skin_mask.png'),0)
    hair=cv2.imread(str(ROOT/'outputs/B_color/uniface_full/masks/hair'/f'{stem}_hair_mask.png'),0)
    tiles=[cv2.cvtColor(im,cv2.COLOR_BGR2RGB),skin,hair,cv2.cvtColor(cv2.bitwise_and(im,im,mask=skin),cv2.COLOR_BGR2RGB),cv2.cvtColor(cv2.bitwise_and(im,im,mask=hair),cv2.COLOR_BGR2RGB)]
    for i,(tile,title) in enumerate(zip(tiles,['Ảnh gốc','Skin mask=1','Hair mask=17','Pixel da','Pixel tóc'])):
        axs[y,i].imshow(tile,cmap='gray',vmin=0,vmax=255);axs[y,i].set_title(title,fontsize=9);axs[y,i].axis('off')
    axs[y,0].set_ylabel(name,fontsize=8)
fig.tight_layout();save('raw_masks.png')
bi=[r['image_name'] for r in bm].index(sample.name); regionfacts={}
fig,axs=plt.subplots(1,2,figsize=(9,3))
for k,(region,offset) in enumerate((('skin',0),('hair',72))):
    heat=br[bi,offset:offset+48].reshape(12,4)
    artist=axs[k].imshow(heat.T,origin='lower',aspect='auto',cmap='YlGnBu');axs[k].set_xlabel('Hue bin 0–11');axs[k].set_ylabel('Saturation bin 0–3');axs[k].set_title(region+' — L1 H–S')
    fig.colorbar(artist,ax=axs[k]);regionfacts[region]={'hs_peak_h_s':list(np.unravel_index(np.argmax(heat),heat.shape)),'hs_peak':float(heat.max()),'hist_sum':float(heat.sum()),'Lab12':br[bi,offset+48:offset+60].tolist(),'hue10':br[bi,offset+60:offset+70].tolist(),'circular_mean':float(br[bi,offset+70]),'circular_std':float(br[bi,offset+71])}
fig.tight_layout();save('HS_histograms.png')
facts['B_sample']=regionfacts
fig,ax=plt.subplots(figsize=(6.5,3.2),subplot_kw={'projection':'polar'})
ax.scatter(np.array([179,1])*2*np.pi/180,[1,1],s=70,color='#235d78');ax.annotate('H=179',(179*2*np.pi/180,1.0),xytext=(-70,12),textcoords='offset points');ax.annotate('H=1',(2*np.pi/180,1.0),xytext=(10,10),textcoords='offset points')
ax.set_ylim(0,1.2);ax.set_yticklabels([]);ax.set_title('Hue gần mép vòng: hai hướng gần nhau',pad=16);save('hue_circle.png')
dump('facts.json',facts)
print(json.dumps({'A':facts['A'],'B':facts['B'],'sample':facts['sample_geometry']['max_saved_row_error'],'A2_oracle_error':facts['sample_geometry']['independent_A2_max_error'],'source_modules':len(inventory),'source_lines':sum(r['lines'] for r in inventory),'figures':len(list(FIG.glob('*.png')))},indent=2))
