"""Report-defined C2 Root-HOG324 with fixed, explicitly versioned conventions."""
from pathlib import Path
import hashlib
import json

import numpy as np

SPEC_PATH = Path(__file__).resolve().parents[1] / 'spec_v1.json'
EPSILON = 1e-8
PREPROCESSING = 'BGR_GRAY_INT16384_CENTER160x192_BORDER_SKIP_v1'
SPEC_PIN = 'a568f2eaec4d54cbc72c2a80d49c371362248367ff88224c158f8c5aaa10f169'


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''): h.update(block)
    return h.hexdigest()


def content_hash(value):
    return hashlib.sha256(json.dumps({k:v for k,v in value.items() if k!='content_sha256'},
        sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')).hexdigest()


def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8'))
    if spec['schema_id'] != 'C2_ROOT_HOG_324_SPEC_v1' or spec.get('content_sha256') != SPEC_PIN or spec.get('content_sha256') != content_hash(spec):
        raise ValueError('C2 spec schema/content hash mismatch')
    if spec['implementation_details']['block_epsilon'] != EPSILON:
        raise ValueError('C2 epsilon mismatch')
    return spec


def lock():
    spec = load_spec()
    return dict(feature_version='C2_ROOT_HOG324_FULL_v1',spec_hash=spec['content_sha256'],
        spec_file_sha256=sha256(SPEC_PATH),implementation_sha256=sha256(__file__),preprocessing_id=PREPROCESSING)


def finite(array, shape):
    if not isinstance(array,np.ndarray) or array.shape != shape or array.dtype != np.float64 or not np.isfinite(array).all():
        raise ValueError('Expected finite float64 array shape'+str(shape))


def extract_face_roi(bgr):
    if not isinstance(bgr,np.ndarray) or bgr.shape!=(256,256,3) or bgr.dtype!=np.uint8:
        raise ValueError('Expected existing aligned256x256 uint8 BGR image')
    return bgr[32:224,48:208].copy()


def convert_to_gray(roi):
    if not isinstance(roi,np.ndarray) or roi.shape!=(192,160,3) or roi.dtype!=np.uint8:
        raise ValueError('Expected192x160 uint8 BGR ROI')
    x = roi.astype(np.uint32)
    gray = (1868*x[...,0]+9617*x[...,1]+4899*x[...,2]+8192)//16384
    return gray.astype(np.uint8).astype(np.float64)


def compute_gradients(gray):
    finite(gray,(192,160))
    gx,gy = np.zeros_like(gray),np.zeros_like(gray)
    gx[1:-1,1:-1] = gray[1:-1,2:]-gray[1:-1,:-2]
    gy[1:-1,1:-1] = gray[2:,1:-1]-gray[:-2,1:-1]
    return gx,gy


def compute_magnitude_orientation(gx,gy):
    finite(gx,(192,160)); finite(gy,(192,160))
    magnitude = np.sqrt(gx*gx+gy*gy)
    orientation = np.mod(np.degrees(np.arctan2(gy,gx)),180.)
    if not np.isfinite(magnitude).all() or not np.isfinite(orientation).all():
        raise ValueError('Nonfinite gradient magnitude/orientation')
    return magnitude,orientation


def compute_cell_histograms(magnitude,orientation):
    finite(magnitude,(192,160)); finite(orientation,(192,160))
    if np.any(magnitude<0) or np.any(orientation<0) or np.any(orientation>=180):
        raise ValueError('Magnitude/orientation outside domain')
    bins = np.floor(orientation/20.).astype(np.int64)
    yy,xx = np.indices((192,160))
    hist = np.zeros((4,4,9),np.float64)
    np.add.at(hist,(yy.ravel()//48,xx.ravel()//40,bins.ravel()),magnitude.ravel())
    return hist


def build_blocks(cells):
    finite(cells,(4,4,9))
    if np.any(cells<0): raise ValueError('Negative histogram')
    return np.stack([cells[y:y+2,x:x+2].reshape(36) for y in range(3) for x in range(3)])


def root_normalize_blocks(blocks):
    finite(blocks,(9,36))
    if np.any(blocks<0): raise ValueError('Negative block histogram')
    return np.sqrt(blocks/(blocks.sum(axis=1,keepdims=True)+EPSILON))


def normalize_final_vector(root_blocks):
    finite(root_blocks,(9,36))
    if np.any(root_blocks<0): raise ValueError('Negative Root-HOG block')
    vector = root_blocks.reshape(324).copy()
    norm = float(np.sqrt(np.sum(vector*vector)))
    if not np.isfinite(norm) or norm<=0: raise ValueError('zero_or_nonfinite_final_L2_norm')
    return vector/norm


def validate_vector(vector):
    finite(vector,(324,))
    if np.any(vector<0) or abs(float(np.sqrt(np.sum(vector*vector)))-1.)>1e-12:
        raise ValueError('C2 vector must be nonnegative and globally L2 normalized')


def extract_c2(bgr):
    result = dict(status='missing_C2',missing_reason=None,vector=None,crop_xyxy_exclusive=[48,32,208,224],
                  gray=None,gx=None,gy=None,magnitude=None,orientation=None,cells=None,blocks=None,root_blocks=None)
    try:
        roi = extract_face_roi(bgr); gray = convert_to_gray(roi)
        gx,gy = compute_gradients(gray); magnitude,orientation = compute_magnitude_orientation(gx,gy)
        cells = compute_cell_histograms(magnitude,orientation); blocks = build_blocks(cells)
        roots = root_normalize_blocks(blocks)
        result.update(gray=gray,gx=gx,gy=gy,magnitude=magnitude,orientation=orientation,cells=cells,blocks=blocks,root_blocks=roots)
        vector = normalize_final_vector(roots); validate_vector(vector)
        result.update(status='valid_C2',vector=vector)
    except ValueError as error:
        result['missing_reason'] = str(error)
    return result


def euclidean(a,b):
    validate_vector(a);validate_vector(b)
    return float(np.sqrt(np.sum((a-b)**2)))
