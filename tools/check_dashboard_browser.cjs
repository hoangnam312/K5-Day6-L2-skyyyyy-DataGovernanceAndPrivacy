// Real-browser smoke test against local HTML; launches only an isolated headless Chrome.
const fs=require('node:fs'),path=require('node:path'),{spawn}=require('node:child_process');
const {pathToFileURL}=require('node:url'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),out=path.join(root,'out','poc');
const exe=process.env.T08_CHROME||'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
let browser,ws;
const pause=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
 const profile=path.join(root,'out','browser-cdp-'+Date.now());
 browser=spawn(exe,['--headless','--disable-gpu','--no-first-run','--no-default-browser-check','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{stdio:['ignore','pipe','pipe'],windowsHide:true});
 let stderr='';
 const endpoint=await new Promise((resolve,reject)=>{
  const timer=setTimeout(()=>reject(new Error('DevTools startup timed out: '+stderr.slice(-500))),15000);
  browser.on('error',e=>{clearTimeout(timer);reject(e)});
  browser.stderr.on('data',d=>{stderr+=d;const m=stderr.match(/DevTools listening on (ws:\/\/\S+)/);if(m){clearTimeout(timer);resolve(m[1])}});
 });
 ws=new WebSocket(endpoint);await new Promise((res,rej)=>{ws.onopen=res;ws.onerror=rej});
 let seq=0;const pending=new Map(),errors=[];
 ws.onmessage=event=>{const m=JSON.parse(event.data);if(m.id){const p=pending.get(m.id);if(p){pending.delete(m.id);m.error?p.reject(new Error(JSON.stringify(m.error))):p.resolve(m.result)}}
  if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.text)};
 function send(method,params={},sessionId){return new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params,...(sessionId?{sessionId}:{})}))})}
 const {targetId}=await send('Target.createTarget',{url:'about:blank'});
 const {sessionId}=await send('Target.attachToTarget',{targetId,flatten:true});
 const call=(method,params={})=>send(method,params,sessionId);
 await call('Page.enable');await call('Runtime.enable');
 async function evaluate(expression){const r=await call('Runtime.evaluate',{expression,returnByValue:true});if(r.exceptionDetails)throw new Error(r.exceptionDetails.text);return r.result.value}
 async function viewport(width,height){await call('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:false});await pause(100)}
 async function navigate(name,selector){
  await call('Page.navigate',{url:pathToFileURL(path.join(out,name)).href});
  for(let n=0;n<50;n++){if(await evaluate('document.readyState==="complete" && Boolean(document.querySelector('+JSON.stringify(selector)+'))'))return;await pause(100)}
  throw new Error('Page did not render '+selector);
 }
 async function screenshot(name){const r=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});fs.writeFileSync(path.join(out,name),Buffer.from(r.data,'base64'))}
 await viewport(1440,1100);await navigate('dashboard.html','#requestRows tr');
 assert.equal(await evaluate('document.querySelectorAll("#requestRows tr").length'),10);
 await screenshot('dashboard-preview.png');
 const desktop=await evaluate('({viewport:innerWidth,content:document.documentElement.scrollWidth})');
 await evaluate('document.getElementById("search").value="DR-002";document.getElementById("search").dispatchEvent(new Event("input"))');
 assert.equal(await evaluate('document.querySelectorAll("#requestRows tr").length'),1);
 await evaluate('document.querySelector(".request-button").click()');
 assert.equal(await evaluate('document.getElementById("detailDialog").open'),true);
 assert.equal(await evaluate('document.querySelectorAll("#detailRows tr").length'),15);
 await screenshot('dashboard-detail.png');
 await evaluate('document.getElementById("closeDetail").click();document.getElementById("search").value="";document.getElementById("search").dispatchEvent(new Event("input"))');
 await viewport(430,1100);
 const mobile=await evaluate('({viewport:innerWidth,content:document.documentElement.scrollWidth})');
 assert.ok(mobile.content<=mobile.viewport,'Mobile page overflow: '+JSON.stringify(mobile));
 await screenshot('dashboard-mobile.png');
 await viewport(1440,1000);await navigate('review.html','#rows tr');
 assert.equal(await evaluate('document.querySelectorAll("#rows tr").length'),158);
 await screenshot('review-preview.png');
 assert.deepEqual(errors,[]);
 const result={passed:true,method:'Isolated headless Chrome with CDP',desktop,mobile,requests:10,review_rows:158,search_and_detail:true,console_exceptions:errors};
 fs.writeFileSync(path.join(root,'reports','dashboard_browser_check.json'),JSON.stringify(result,null,2));
 console.log(JSON.stringify(result));
 await send('Browser.close');ws.close();
})().catch(e=>{console.error(e);process.exitCode=1;if(ws)ws.close();if(browser)browser.kill()});
