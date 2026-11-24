"""Independent scalar Root-HOG oracle; no production imports/helpers."""
import math
import numpy as np


def extract(bgr):
    gray = np.zeros((192,160),np.float64)
    for y in range(192):
        for x in range(160):
            b,g,r = map(int,bgr[y+32,x+48])
            gray[y,x] = (1868*b+9617*g+4899*r+8192)//16384
    gx=np.zeros((192,160),np.float64);gy=gx.copy();mag=gx.copy();angle=gx.copy()
    cells = [[[0. for b in range(9)] for x in range(4)] for y in range(4)]
    for y in range(1,191):
        for x in range(1,159):
            dx = float(gray[y,x+1])-float(gray[y,x-1])
            dy = float(gray[y+1,x])-float(gray[y-1,x])
            magnitude = math.sqrt(dx*dx+dy*dy)
            theta = math.degrees(math.atan2(dy,dx)) % 180.
            gx[y,x]=dx;gy[y,x]=dy;mag[y,x]=magnitude;angle[y,x]=theta
            cells[y//48][x//40][int(theta//20)] += magnitude
    blocks,roots = [],[]
    for block_y in range(3):
        for block_x in range(3):
            block = [cells[block_y+dy][block_x+dx][b] for dy in range(2) for dx in range(2) for b in range(9)]
            total = math.fsum(block)
            blocks.append(block)
            roots.append([math.sqrt(h/(total+1e-8)) for h in block])
    flat = [v for block in roots for v in block]
    norm = math.sqrt(math.fsum(v*v for v in flat))
    vector = None if norm==0 else np.array([v/norm for v in flat],np.float64)
    return dict(gray=gray,gx=gx,gy=gy,magnitude=mag,orientation=angle,
                cells=np.array(cells,np.float64),blocks=np.array(blocks,np.float64),
                root_blocks=np.array(roots,np.float64),vector=vector)


def euclid(a,b):
    return math.sqrt(math.fsum((float(x)-float(y))**2 for x,y in zip(a,b)))
