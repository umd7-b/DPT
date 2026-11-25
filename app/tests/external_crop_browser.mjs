// Chromium CDP QA using Node 24 built-ins only. No package install or mocked results.
import assert from 'node:assert/strict';
import {mkdir,readFile,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
const base=process.env.PORTRAIT_BASE||'http://127.0.0.1:8766';
const debug=process.env.PORTRAIT_DEBUG||'http://127.0.0.1:9225';
const evidence=resolve(process.env.PORTRAIT_EVIDENCE||'app/evidence/external_v1');
await mkdir(resolve(evidence,'screenshots'),{recursive:true});
const target=await (await fetch(debug+'/json/new?'+encodeURIComponent(base),{method:'PUT'})).json();
const socket=new WebSocket(target.webSocketDebuggerUrl);
await new Promise((ok,fail)=>{socket.addEventListener('open',ok,{once:true});socket.addEventListener('error',fail,{once:true});});
let sequence=0;const pending=new Map();const errors=[];const requests=[];
socket.addEventListener('message',event=>{
  const message=JSON.parse(event.data);
  if(message.id){const waiter=pending.get(message.id);if(waiter){pending.delete(message.id);clearTimeout(waiter.timeout);message.error?waiter.fail(new Error(JSON.stringify(message.error))):waiter.ok(message.result);}}
  if(message.method==='Runtime.exceptionThrown')errors.push(message.params.exceptionDetails);
  if(message.method==='Network.requestWillBeSent' && message.params.request.url===base+'/api/search')requests.push(message.params.request.postData);
});
function send(method,params={}){return new Promise((ok,fail)=>{const id=++sequence;const timeout=setTimeout(()=>{pending.delete(id);fail(new Error('CDP timeout '+method));},20000);pending.set(id,{ok,fail,timeout});socket.send(JSON.stringify({id,method,params}));});}
async function evaluate(expression){const result=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(result.exceptionDetails)throw new Error(JSON.stringify(result.exceptionDetails));return result.result.value;}
async function wait(expression){for(let i=0;i<600;i++){if(await evaluate(expression))return;await new Promise(r=>setTimeout(r,100));}throw new Error('DOM condition timed out: '+expression);}
async function click(selector){await evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);}
async function input(selector,value){await evaluate(`(()=>{const x=document.querySelector(${JSON.stringify(selector)});x.value=${JSON.stringify(value)};x.dispatchEvent(new Event('input',{bubbles:true}));})()`);}
async function imagesReady(){await wait(`Array.from(document.querySelectorAll('#query-image,#results img')).every(i=>i.complete&&i.naturalWidth===256)`);}
async function screenshot(name,full=false){await evaluate('window.scrollTo(0,0)');const options={format:'png',captureBeyondViewport:full};if(full){const {cssContentSize}=await send('Page.getLayoutMetrics');options.clip={x:0,y:0,width:Math.ceil(cssContentSize.width),height:Math.ceil(cssContentSize.height),scale:1};}const data=await send('Page.captureScreenshot',options);await writeFile(resolve(evidence,'screenshots',name),Buffer.from(data.data,'base64'));}
function withoutUrl(row){const {image_url,...rest}=row;return rest;}
const checks=[];
async function ready(){await wait(`!state.busy&&$('crop-dialog').open&&externalUI.readyRevision===externalUI.revision&&!$('crop-confirm').disabled`);}
try{
  await send('Page.enable');await send('Runtime.enable');await send('Emulation.setDeviceMetricsOverride',{width:1600,height:1100,deviceScaleFactor:1,mobile:false});
  await send('Page.navigate',{url:base});await wait(`typeof state!=='undefined'&&state.result?.status==='ok'&&!state.busy`);await click('#source-import');
  for(const [name,width,height]of [['landscape.png',900,500],['portrait.png',400,700],['square.png',256,256],['large.png',1200,900],['small.png',48,32],['exif6.jpg',70,120],['decoder.webp',150,90]]){
    const doc=await send('DOM.getDocument'),node=await send('DOM.querySelector',{nodeId:doc.root.nodeId,selector:'#upload-input'});
    await send('DOM.setFileInputFiles',{nodeId:node.nodeId,files:[resolve(evidence,'fixtures',name)]});await ready();
    assert.deepEqual(await evaluate('[externalUI.job.width,externalUI.job.height]'),[width,height]);
    const size=Math.floor(Math.min(width,height)/2);
    for(const [x,y]of [[0,0],[width-size,0],[0,height-size],[width-size,height-size]]){
      await evaluate(`(()=>{$('crop-x').value=${x};$('crop-y').value=${y};$('crop-size').value=${size};$('crop-size').dispatchEvent(new Event('change',{bubbles:true}));})()`);await ready();
      assert.deepEqual(await evaluate('externalUI.crop'),{x,y,size});assert.equal(await evaluate(`$('crop-preview').naturalWidth===256&&$('crop-preview').naturalHeight===256`),true);
      const hash=await evaluate(`(async()=>{const b=await(await fetch(externalUI.preview.preview_url)).arrayBuffer();return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',b))).map(v=>v.toString(16).padStart(2,'0')).join('')})()`);
      assert.equal(hash,await evaluate('externalUI.preview.sha256'));
    }
    await click('#crop-reset');await ready();assert.equal(await evaluate('externalUI.crop.size'),Math.min(width,height));
    await click('#crop-dialog .close-dialog');checks.push({file:name,oriented:[width,height],four_edges:true,output256:true,preview_bytes_exact:true,reset:true});
  }
  await evaluate(`(async()=>{const b=await(await fetch('/media/cfd_final_00001')).blob(),d=new DataTransfer();d.items.add(new File([b],'dragged-new-name.png',{type:'image/png'}));$('upload-zone').dispatchEvent(new DragEvent('drop',{bubbles:true,cancelable:true,dataTransfer:d}));})()`);await ready();
  assert.equal(await evaluate('externalUI.job.filename'),'dragged-new-name.png');
  await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  await screenshot('external_mobile_crop.png',true);assert.equal(await evaluate('document.documentElement.scrollWidth<=window.innerWidth'),true);
  await click('#crop-dialog .close-dialog');checks.push({drag_and_drop:true,mobile_no_horizontal_overflow:true});
  const id=await evaluate('externalUI.job.job_id');await evaluate(`externalRequest('discard',{job_id:'${id}'})`);
  assert.equal(errors.length,0);await writeFile(resolve(evidence,'crop_browser_verification.json'),JSON.stringify({status:'PASS',checks,console_exceptions:errors},null,2));console.log(JSON.stringify({status:'PASS',cases:checks.length,edges:28}));
}finally{socket.close();await fetch(debug+'/json/close/'+target.id);}
