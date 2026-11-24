"""Render editable Markdown, including math SVGs, to self-contained local HTML."""
from pathlib import Path
import hashlib, html, json, re
import matplotlib
matplotlib.use('Agg')
from matplotlib.mathtext import math_to_image
from matplotlib.font_manager import FontProperties

OUT=Path(__file__).resolve().parents[1];BUILD=OUT/'_build';FIG=OUT/'figures'
text=(OUT/'A_B_Feature_Analysis.md').read_text(encoding='utf-8')
chunks=re.split(r'<!-- PAGE \d+: (.*?) -->',text)[1:]
assert len(chunks)==56
def inline(s):
    s=html.escape(s)
    s=re.sub(r'`([^`]+)`',r'<code>\1</code>',s)
    s=re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',s)
    s=re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)',r'<em>\1</em>',s)
    s=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',r'<a href="\2">\1</a>',s)
    return s
def markdown(s):
    lines=s.strip().splitlines();out=[];i=0
    while i<len(lines):
        line=lines[i].strip()
        if not line:i+=1;continue
        if line=='$$':
            i+=1;math=[]
            while lines[i].strip()!='$$':math.append(lines[i].strip());i+=1
            latex=' '.join(math)
            latex=latex.replace(r'\bmod',r'\operatorname{mod}')
            key=hashlib.sha256(latex.encode()).hexdigest()[:12]
            path=FIG/f'equation_{key}.svg'
            math_to_image('$'+latex+'$',path,prop=FontProperties(size=15),format='svg',color='#102d3c')
            out.append(f'<div class="equation"><img src="{path.relative_to(OUT).as_posix()}" alt="{html.escape(latex,quote=True)}"></div>')
            i+=1;continue
        if line.startswith('#'):
            n=len(line)-len(line.lstrip('#'));out.append(f'<h{n}>{inline(line[n:].strip())}</h{n}>');i+=1;continue
        if line.startswith('!['):
            m=re.fullmatch(r'!\[(.*?)\]\((.*?)\)',line)
            if not m:raise ValueError(line)
            if not (OUT/m[2]).is_file():raise FileNotFoundError(m[2])
            out.append(f'<figure><img src="{html.escape(m[2],quote=True)}" alt="{html.escape(m[1],quote=True)}"></figure>');i+=1;continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                vals=[v.strip() for v in lines[i].strip().split('|')[1:-1]]
                if not all(re.fullmatch(r':?-+:?',v) for v in vals):rows.append(vals)
                i+=1
            count=len(rows[0]);assert all(len(r)==count for r in rows)
            out.append('<table><thead><tr>'+''.join('<th>'+inline(c)+'</th>' for c in rows[0])+'</tr></thead><tbody>')
            for row in rows[1:]:out.append('<tr>'+''.join('<td>'+inline(c)+'</td>' for c in row)+'</tr>')
            out.append('</tbody></table>');continue
        if line.startswith('- '):
            out.append('<ul>')
            while i<len(lines) and lines[i].strip().startswith('- '):out.append('<li>'+inline(lines[i].strip()[2:])+'</li>');i+=1
            out.append('</ul>');continue
        paragraph=[line];i+=1
        while i<len(lines) and lines[i].strip() and not lines[i].strip().startswith(('#','|','![','$$','- ')):
            paragraph.append(lines[i].strip());i+=1
        out.append('<p>'+inline(' '.join(paragraph))+'</p>')
    return '\n'.join(out)

css='''
@page{size:A4;margin:0}*{box-sizing:border-box}html,body{margin:0;padding:0;background:#e7ecef;color:#172b36}
body{font-family:"Times New Roman",serif;font-size:10.5pt;line-height:1.35}
.sheet{position:relative;width:210mm;height:297mm;padding:18mm 17mm 18mm;background:white;break-after:page;break-inside:avoid;overflow:visible}
.sheet:last-of-type{break-after:auto}.content{height:256mm;overflow:visible}
.running{position:absolute;top:7.5mm;left:17mm;right:17mm;border-bottom:.25mm solid #becbd2;padding-bottom:1.5mm;font:8pt Arial,sans-serif;color:#527083;letter-spacing:.6pt}
.footer{position:absolute;left:17mm;right:17mm;bottom:9mm;display:flex;justify-content:space-between;font:8pt Arial,sans-serif;color:#527083;border-top:.25mm solid #ccd7de;padding-top:2mm}
h1,h2,h3{font-family:Arial,sans-serif;color:#153c52;break-after:avoid}h1{font-size:18.5pt;line-height:1.18;margin:0 0 4mm}h2{font-size:12pt;margin:3mm 0 2mm}h3{font-size:11pt;margin:2mm 0}
p{margin:0 0 2.3mm;text-align:justify}strong{font-weight:bold}code{font-family:Consolas,monospace;font-size:.83em;overflow-wrap:anywhere;color:#244d64}
table{width:100%;border-collapse:collapse;margin:2mm 0 3mm;table-layout:auto;font-size:9pt;line-height:1.23;break-inside:avoid}
th{background:#e9f0f4;color:#173b50;font-family:Arial,sans-serif;text-align:left;font-weight:bold}th,td{border:.2mm solid #bdcbd3;padding:1.5mm 1.8mm;vertical-align:top;overflow-wrap:anywhere}tr{break-inside:avoid}
figure{margin:2mm 0 1mm;text-align:center;break-inside:avoid}figure img{max-width:100%;height:auto;max-height:130mm;object-fit:contain}
p:has(em){font-size:9pt;color:#526774;text-align:center;line-height:1.25}.equation{margin:2.5mm 0;padding:1.5mm 2mm;background:#f4f7f9;text-align:center;break-inside:avoid}
.equation img{max-width:100%;height:auto;max-height:15mm;object-fit:contain}a{color:#235d78;text-decoration:none}ul{margin:1mm 0 3mm;padding-left:5mm}li{margin-bottom:1mm}
.sheet[data-n="1"] .running{display:none}.sheet[data-n="1"] .content{border-top:2mm solid #235d78;padding-top:18mm}
.sheet[data-n="1"] h1{font-size:30pt;letter-spacing:.5pt;margin:0 0 7mm}.sheet[data-n="1"] h2{font-size:26pt;margin:0 0 12mm}.sheet[data-n="1"] p{margin-bottom:6mm;font-size:12pt;text-align:left}
.sheet[data-n="5"] figure img{max-height:125mm}.sheet[data-n="19"] figure img{max-height:60mm}
.sheet[data-n="20"] table,.sheet[data-n="21"] table{font:8.5pt Consolas,monospace;line-height:1.2}.sheet[data-n="20"] td,.sheet[data-n="21"] td{padding:.7mm 1.3mm}
.sheet[data-n="22"] figure img{max-height:101mm}.sheet[data-n="23"] figure img{max-height:100mm}.sheet[data-n="24"] figure img{max-height:120mm}.sheet[data-n="25"] figure img{max-height:105mm}.sheet[data-n="27"] figure img{max-height:105mm}
@media print{html,body{background:white}.sheet{margin:0;box-shadow:none}*{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
'''
sections=[];titles=[]
for n in range(0,len(chunks),2):
    title=chunks[n];body=chunks[n+1];i=n//2+1;titles.append(title)
    sections.append(f'<section class="sheet" data-n="{i}" data-title="{html.escape(title,quote=True)}"><div class="running">PORTRAIT RETRIEVAL · PHÂN TÍCH A150 &amp; B144</div><main class="content">{markdown(body)}</main><footer class="footer"><span>Báo cáo kỹ thuật · 22/11/2026</span><span>{i:02d} / 28</span></footer></section>')
script='''
window.addEventListener('load',async()=>{await document.fonts.ready;
 const checks=[...document.querySelectorAll('.sheet')].map(s=>{const c=s.querySelector('.content');const cr=c.getBoundingClientRect();const foot=s.querySelector('.footer').getBoundingClientRect();
 const bad=[...c.querySelectorAll('p,table,h1,h2,figure,.equation')].filter(e=>e.getBoundingClientRect().bottom>cr.bottom+1||e.getBoundingClientRect().right>cr.right+1);
 return {page:Number(s.dataset.n),title:s.dataset.title,overflow:Math.max(0,c.scrollHeight-c.clientHeight),bad_elements:bad.map(e=>e.tagName+':'+e.textContent.slice(0,65)),footer_clear:cr.bottom<foot.top,images_ok:[...s.querySelectorAll('img')].every(x=>x.complete&&x.naturalWidth>0)};});
 const p=document.createElement('pre');p.id='layout-validation';p.style.display='none';p.textContent=JSON.stringify(checks);document.body.appendChild(p);
});
'''
htmltext='<!doctype html><html lang="vi"><head><meta charset="utf-8"><title>Phân tích kỹ thuật A & B — Portrait Retrieval</title><style>'+css+'</style></head><body>'+''.join(sections)+'<script>'+script+'</script></body></html>'
(OUT/'A_B_Feature_Analysis.html').write_text(htmltext,encoding='utf-8')
print('Rendered HTML sections:',len(sections),'math SVGs:',len(list(FIG.glob('equation_*.svg'))))
