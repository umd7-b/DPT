"""Report B descriptor: 2 regions x (48 HS + 12 Lab + 12 circular hue).

Unspecified numerical conventions are versioned explicitly in SCHEMA. No inferred
mask or missing-region zero vector is produced by this module.
"""
from dataclasses import dataclass

import cv2
import numpy as np

SCHEMA = {
    'id':'B144_report_v1_explicit_conventions', 'dimension':144,
    'report_sha256':'8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80',
    'regions':['skin','hair'],'region_order':['HS48','Lab12','Hue10','circular_mean','circular_std'],
    'hs_bins':[12,4],'hs_ranges':[[0,180],[0,256]],'histogram_order':'C: hue outer, saturation inner',
    'hue_bins':10,'hue_range':[0,180],'histogram_normalization':'L1 per histogram',
    'lab':'OpenCV float32 BGR/255 to CIE Lab; L* approximately [0,100], signed a*,b*',
    'lab_channel_order':['L','a','b'],'lab_stat_order':['mean','population_std','population_skewness','Pearson_kurtosis'],
    'zero_variance':'std/skew/kurt=0; explicit diagnostic; skew/kurt mathematically undefined for constants',
    'circular_mean':'(atan2(mean(sin(phi)),mean(cos(phi))) mod 2pi)/(2pi)',
    'circular_std':'min(sqrt(-2*log(max(R,1e-12)))/(2pi),1)',
    'undefined_circular_mean':'0 with warning if R<1e-8',
    'conventions_status':'Numerical details omitted by report; experimental conventions, pending group confirmation',
    'missing_policy':'vector=None if either region empty or below minimum pixels; never zero-fill missing data',
}


def feature_names():
    names=[]
    for region in SCHEMA['regions']:
        names += [f'{region}_HS_h{h:02d}_s{s}' for h in range(12) for s in range(4)]
        names += [f'{region}_Lab_{c}_{stat}' for c in ('L','a','b') for stat in ('mean','std','skew','kurtosis')]
        names += [f'{region}_Hue_bin{i:02d}' for i in range(10)]
        names += [f'{region}_circular_mean',f'{region}_circular_std']
    return names


def validate_image(image):
    if not isinstance(image,np.ndarray) or image.dtype!=np.uint8 or image.ndim!=3 or image.shape[2]!=3:
        raise ValueError('Expected original uint8 BGR image')


def validate_mask(mask,shape):
    if not isinstance(mask,np.ndarray) or mask.dtype!=np.uint8 or mask.shape!=shape or not set(np.unique(mask)).issubset({0,255}):
        raise ValueError('Expected matching binary uint8 mask with values 0/255')


def hue_statistics(hue):
    angles=np.asarray(hue,dtype=np.float64)*(2*np.pi/180)
    if angles.size==0:raise ValueError('Hue samples required')
    c,s=np.mean(np.cos(angles)),np.mean(np.sin(angles))
    r=float(np.clip(np.hypot(c,s),0,1))
    warnings=[]
    if r<1e-8:
        mean=0.;warnings.append('circular_mean_undefined_low_resultant')
    else:
        angle=float(np.arctan2(s,c)%(2*np.pi))
        if np.isclose(angle,2*np.pi,atol=1e-12,rtol=0):angle=0.
        mean=angle/(2*np.pi)
    std=float(min(np.sqrt(-2*np.log(max(r,1e-12)))/(2*np.pi),1))
    return mean,std,r,warnings


def region_descriptor(image,mask,min_pixels=100):
    validate_image(image);validate_mask(mask,image.shape[:2])
    if min_pixels<1:raise ValueError('min_pixels must be positive')
    pixels=image[mask>0]
    info={'pixels':len(pixels),'status':'available','warnings':[]}
    if len(pixels)<min_pixels:
        info['status']='missing_empty' if len(pixels)==0 else 'insufficient_pixels'
        return None,info
    # Transform only selected original pixels. Excluded black background never
    # enters a histogram; real black hair pixels selected by the mask still do.
    strip=np.ascontiguousarray(pixels.reshape(-1,1,3))
    hsv=cv2.cvtColor(strip,cv2.COLOR_BGR2HSV).reshape(-1,3)
    lab=cv2.cvtColor(strip.astype(np.float32)/255.,cv2.COLOR_BGR2LAB).reshape(-1,3).astype(np.float64)
    hs=np.histogram2d(hsv[:,0],hsv[:,1],bins=(12,4),range=((0,180),(0,256)))[0].ravel()
    hs=hs/hs.sum()
    moments=[]
    for index,channel in enumerate(lab.T):
        mu=float(np.mean(channel));centered=channel-mu
        std=float(np.sqrt(np.mean(centered**2)))
        if std<1e-12:
            std,skew,kurt=0.,0.,0.
            info['warnings'].append(f'Lab_{index}_zero_variance_moments_convention')
        else:
            scaled=centered/std
            skew=float(np.mean(scaled**3));kurt=float(np.mean(scaled**4))
        moments.extend([mu,std,skew,kurt])
    h=np.histogram(hsv[:,0],bins=10,range=(0,180))[0].astype(np.float64)
    h/=h.sum()
    mean,std,r,warnings=hue_statistics(hsv[:,0])
    info['warnings']+=warnings
    info['hue_resultant']=r
    info['low_saturation_fraction']=float(np.mean(hsv[:,1]<10))
    if info['low_saturation_fraction']>.5:info['warnings'].append('low_saturation_hue_unreliable')
    vector=np.r_[hs,moments,h,mean,std]
    if vector.shape!=(72,) or not np.isfinite(vector).all():raise ValueError('Invalid 72D region descriptor')
    if not np.isclose(vector[:48].sum(),1) or not np.isclose(vector[60:70].sum(),1):raise ValueError('Histogram normalization failed')
    if np.any(vector[:48]<0) or np.any(vector[60:72]<0) or np.any(vector[60:72]>1+1e-12):raise ValueError('Out-of-range histogram/circular values')
    return vector,info


@dataclass
class ColorResult:
    vector: object
    skin: dict
    hair: dict


def extract_color(image,skin_mask,hair_mask,min_pixels=100):
    validate_image(image)
    validate_mask(skin_mask,image.shape[:2]);validate_mask(hair_mask,image.shape[:2])
    if np.any((skin_mask>0)&(hair_mask>0)):raise ValueError('Skin/hair masks overlap')
    skin,sinfo=region_descriptor(image,skin_mask,min_pixels)
    hair,hinfo=region_descriptor(image,hair_mask,min_pixels)
    if skin is None or hair is None:return ColorResult(None,sinfo,hinfo)
    vector=np.r_[skin,hair].astype(np.float64)
    if vector.shape!=(144,) or not np.isfinite(vector).all():raise ValueError('Invalid B144 vector')
    return ColorResult(vector,sinfo,hinfo)


def fit_standardizer(matrix,profile='all144'):
    x=np.asarray(matrix,dtype=np.float64)
    if x.ndim!=2 or x.shape[1]!=144 or len(x)<2 or not np.isfinite(x).all():raise ValueError('At least two finite B144 vectors required')
    if profile not in ('all144','moments_only'):raise ValueError('Unknown normalization profile')
    indices=np.arange(144) if profile=='all144' else np.r_[np.arange(48,60),np.arange(120,132)]
    mean=np.zeros(144);std=np.ones(144)
    mean[indices]=x[:,indices].mean(axis=0)
    raw_std=x[:,indices].std(axis=0,ddof=0)
    std[indices]=np.where(raw_std<1e-8,1.,raw_std)
    return {'mean':mean,'std':std,'profile':profile,'constant_dimensions':indices[raw_std<1e-8]}


def transform(matrix,stats):
    x=np.asarray(matrix,dtype=np.float64)
    if x.ndim not in (1,2) or x.shape[-1]!=144 or not np.isfinite(x).all():raise ValueError('Expected finite B144 input')
    if np.any(stats['std']<=0):raise ValueError('Standard deviations must be positive')
    result=(x-stats['mean'])/stats['std']
    if not np.isfinite(result).all():raise ValueError('Non-finite standardized values')
    return result
