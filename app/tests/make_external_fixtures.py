"""Deterministic private QA inputs, generated without changing source images."""
import io
from pathlib import Path
import numpy as np
from PIL import Image,PngImagePlugin
from app.server import PortraitService
from app.external_config import QA_EVIDENCE

def main():
    folder=QA_EVIDENCE/'fixtures';folder.mkdir(parents=True,exist_ok=True)
    service=PortraitService()
    try:
        for name,size in dict(landscape=(900,500),portrait=(400,700),square=(256,256),large=(1200,900),small=(48,32)).items():
            w,h=size;a=np.arange(w*h*3,dtype=np.uint32).reshape(h,w,3).astype(np.uint8)
            Image.fromarray(a).save(folder/(name+'.png'))
        exif=Image.Exif();exif[274]=6
        Image.new('RGB',(120,70),(80,120,160)).save(folder/'exif6.jpg',exif=exif)
        Image.new('RGB',(150,90),(80,120,160)).save(folder/'decoder.webp')
        Image.new('RGB',(256,256),(128,128,128)).save(folder/'no_face.png')
        with Image.open(service.catalog['cfd_final_00001']['image_path']) as face:
            info=PngImagePlugin.PngInfo();info.add_text('external_test','different bytes, real extraction')
            face.save(folder/'reencoded.png',pnginfo=info)
    finally:service.external.close()

if __name__=='__main__':main()
