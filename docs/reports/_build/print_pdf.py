from pathlib import Path
import html,json,re,subprocess
OUT=Path(__file__).resolve().parents[1];BUILD=OUT/'_build'
chrome=Path('C:/Program Files/Google/Chrome/Application/chrome.exe')
args=[str(chrome),'--headless','--disable-gpu','--in-process-gpu','--no-sandbox','--disable-background-networking',
      '--disable-component-update','--disable-default-apps','--no-first-run','--no-default-browser-check',
      '--disable-sync','--allow-file-access-from-files','--no-pdf-header-footer',
      '--user-data-dir='+str(BUILD/'chrome_profile_local'),'--virtual-time-budget=3000',
      '--print-to-pdf='+str(OUT/'A_B_Feature_Analysis.pdf'),'--dump-dom',
      (OUT/'A_B_Feature_Analysis.html').as_uri()]
with (BUILD/'printed_dom.html').open('wb') as stdout, (BUILD/'chrome_print.log').open('wb') as stderr:
    process=subprocess.Popen(args,stdout=stdout,stderr=stderr)
    print('Local HTML renderer PID:',process.pid,flush=True)
    try:process.wait(timeout=40)
    except subprocess.TimeoutExpired:
        process.kill()
        raise
if process.returncode:raise RuntimeError('Chrome print failed: '+str(process.returncode))
dom=(BUILD/'printed_dom.html').read_text(encoding='utf-8')
match=re.search(r'<pre id="layout-validation"[^>]*>(.*?)</pre>',dom,re.S)
if not match:raise RuntimeError('Layout validation script did not finish')
checks=json.loads(html.unescape(match[1]))
(BUILD/'layout_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
bad=[r for r in checks if r['overflow']>1 or r['bad_elements'] or not r['images_ok'] or not r['footer_clear']]
print(json.dumps({'sections':len(checks),'pdf_bytes':(OUT/'A_B_Feature_Analysis.pdf').stat().st_size,'layout_issues':bad},ensure_ascii=False,indent=2))
