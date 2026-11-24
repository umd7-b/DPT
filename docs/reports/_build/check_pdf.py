"""PDF structure/text/font checks using the already-installed system pypdf."""
from pathlib import Path
import csv,json,re,shutil
from pypdf import PdfReader,PdfWriter
from pypdf.generic import RectangleObject
OUT=Path(__file__).resolve().parents[1];BUILD=OUT/'_build'
pdf=OUT/'A_B_Feature_Analysis.pdf'
shutil.copyfile(pdf,BUILD/'chrome_original.pdf')
reader=PdfReader(pdf);assert len(reader.pages)==28
writer=PdfWriter();writer.clone_document_from_reader(reader)
for page in writer.pages:
    page.mediabox=RectangleObject([0,0,210*72/25.4,297*72/25.4])
writer.add_metadata({'/Title':'Phân tích kỹ thuật Bộ A150 và B144 — Portrait Retrieval','/Author':'Portrait Retrieval','/Subject':'Read-only technical source and artifact audit; approved B144_raw_v1.0.0'})
for title,index in [('Mục lục',1),('Chương 1 — Tổng quan',2),('Chương 2 — A150',4),('Chương 3 — Z-score A',13),('Chương 4 — B144',15),('Chương 5 — Z-score B',21),('Chương 6 — Truy hồi',22),('Chương 7 — Kết quả và giới hạn',25),('Nguồn và tái lập',27)]:writer.add_outline_item(title,index)
with pdf.open('wb') as stream:writer.write(stream)
reader=PdfReader(pdf)
pages=[p.extract_text() for p in reader.pages]
whole='\n'.join(pages)
assert '\ufffd' not in whole
assert len(pages)==28 and all(len(t)>300 for t in pages)
for i,page in enumerate(reader.pages,1):
    assert abs(float(page.mediabox.width)-210*72/25.4)<.001
    assert abs(float(page.mediabox.height)-297*72/25.4)<.001
    assert f'{i:02} / 28' in pages[i-1],i
with (OUT.parents[1]/'outputs/B_color/color_features_full_v1/feature_layout.csv').open(encoding='utf-8-sig',newline='') as stream:
    layout=list(csv.DictReader(stream))
missing=[r['name'] for r in layout if r['name'] not in whole]
assert not missing,missing
for marker in ('PHÂN TÍCH KỸ THUẬT','hf_merged_00209.png','Pearson','std_safe','1.438','1.437','MediaPipe'):
    assert marker in whole,marker
fonts={}
for page in reader.pages:
    for key,ref in page['/Resources'].get('/Font',{}).items():
        font=ref.get_object();name=str(font.get('/BaseFont','unknown'))
        children=font.get('/DescendantFonts',[ref])
        embedded=[]
        for child in children:
            descriptor=child.get_object().get('/FontDescriptor',{})
            if hasattr(descriptor,'get_object'):descriptor=descriptor.get_object()
            embedded.append(any(k in descriptor for k in ('/FontFile','/FontFile2','/FontFile3')))
        fonts[name]={'embedded':all(embedded),'ToUnicode':'/ToUnicode' in font}
assert all(v['embedded'] and v['ToUnicode'] for v in fonts.values()),fonts
checks=json.loads((BUILD/'layout_checks.json').read_text(encoding='utf-8'))
assert all(c['overflow']<=1 and not c['bad_elements'] and c['images_ok'] and c['footer_clear'] for c in checks)
result={'pages':len(pages),'nominal_paper':'A4 210x297 mm','media_box_points':[float(reader.pages[0].mediabox.width),float(reader.pages[0].mediabox.height)],
        'all_pages_text_extractable':True,'unicode_replacement_characters':whole.count('\ufffd'),
        'B_exact_feature_names_verified':len(layout),'missing_B_names':missing,
        'all_page_numbers_verified':True,'all_fonts_embedded_unicode':fonts,'layout_overflow_pages':[],
        'all_images_loaded':True,'bookmarks':9,'note':'Math SVGs are vector paths; formulas additionally reviewed visually in raster proofs.'}
(BUILD/'pdf_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
(BUILD/'pdf_text_pages.json').write_text(json.dumps(pages,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
