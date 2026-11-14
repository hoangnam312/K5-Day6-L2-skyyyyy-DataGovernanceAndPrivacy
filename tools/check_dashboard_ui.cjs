// Behavioral checks for the generated dashboard with a DOM test double.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(process.argv[2]||'out/poc/dashboard.html','utf8');
const payload=html.match(/<script id="run-data" type="application\/json">([\s\S]*?)<\/script>/)[1];
const scripts=[...html.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)].filter(x=>!x[1].includes('application/json'));
const nodes=new Map();
function make(tag='div'){
 const n={tag,children:[],value:'',textContent:'',className:'',style:{},listeners:{},open:false,
 append(...x){this.children.push(...x)},replaceChildren(...x){this.children=[...x]},
 addEventListener(type,fn){this.listeners[type]=fn},showModal(){this.open=true},close(){this.open=false},
 getBoundingClientRect(){return {left:0,right:100,top:0,bottom:100}}};
 n.classList={add(){},remove(){}};return n;
}
function get(id){if(!nodes.has(id))nodes.set(id,make());return nodes.get(id)}
get('run-data').textContent=payload;get('filter').value='all';
const context=vm.createContext({document:{getElementById:get,createElement:make},console});
for(const script of scripts)vm.runInContext(script[2],context);
const data=JSON.parse(payload);
assert.equal(get('requestRows').children.length,data.summary.requests.length);
const target=data.summary.requests[0];
get('search').value=target.request_id;get('search').listeners.input();
assert.equal(get('requestRows').children.length,1);
get('requestRows').children[0].children[0].children[0].onclick();
assert.equal(get('detailDialog').open,true);
assert.equal(get('detailRows').children.length,target.n_artefacts);
get('closeDetail').onclick();assert.equal(get('detailDialog').open,false);
get('search').value='NO_SUCH_REQUEST';get('search').listeners.input();
assert.ok(get('resultCount').textContent.startsWith('Hiển thị 0'));
get('search').value='';get('filter').value='pending';get('filter').listeners.change();
const pending=data.summary.requests.filter(r=>(r.execution_counts.pending_approval||0)>0).length;
assert.equal(get('resultCount').textContent,'Hiển thị '+pending+' / '+data.summary.requests.length+' yêu cầu');
console.log(JSON.stringify({passed:true,checks:['initial rows','search','detail dialog','close dialog','empty search','pending filter'],method:'DOM test double'}));
