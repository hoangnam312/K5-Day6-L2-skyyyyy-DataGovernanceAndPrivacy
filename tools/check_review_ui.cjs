// Execute the generated review/export JavaScript with a minimal DOM test double.
// TEST_ONLY_UI is a test identity, not evidence of real human review.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const file = process.argv[2] || 'out/poc/review.html';
const html = fs.readFileSync(file, 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const nodes = new Map();
const element = () => ({children: [], value: '', textContent: '', dataset:{}, listeners:{}, hidden:false,
 append(x){this.children.push(x)},replaceChildren(...x){this.children=[...x]},
 addEventListener(type,fn){this.listeners[type]=fn},click(){}});
let exported;
const context = vm.createContext({
  document: {createElement: element, getElementById(id){if(!nodes.has(id)) nodes.set(id, element()); return nodes.get(id)}},
  Blob, URL: {createObjectURL(blob){exported=blob;return 'blob:test'}, revokeObjectURL(){}},
  setTimeout(fn){fn()}, alert(message){throw new Error(message)}, Date
});
vm.runInContext(script, context);
context.document.getElementById('who').value = 'TEST_ONLY_UI';
const target=vm.runInContext('data.find(r=>r.suggested_action===\'delete\').item_id.split(\'::\')[0]', context);
const expected=vm.runInContext('data.filter(r=>r.item_id.split(\'::\')[0]==='+JSON.stringify(target)+'&&r.suggested_action===\'delete\').length', context);
nodes.get('requestFilter').value=target;nodes.get('requestFilter').listeners.change();
nodes.get('actionFilter').value='delete';nodes.get('actionFilter').listeners.change();
assert.equal(vm.runInContext('data.filter(r=>!r.view.hidden).length',context),expected);
nodes.get('approve').onclick();
const approved = vm.runInContext('data.filter(r=>r.reviewer_decision===\'approve\').length', context);
assert.equal(approved,expected);
assert.equal(vm.runInContext('data.some(r=>r.item_id.split(\'::\')[0]!=='+JSON.stringify(target)+'&&r.reviewer_decision)',context),false);
nodes.get('resetFilters').onclick();
assert.equal(vm.runInContext('data.filter(r=>r.reviewer_decision===\'approve\').length',context),expected);
nodes.get('reviewSearch').value='NO_SUCH_ROW';nodes.get('reviewSearch').listeners.input();
assert.equal(vm.runInContext('data.filter(r=>!r.view.hidden).length',context),0);
assert.equal(nodes.get('approve').disabled,true);
vm.runInContext('data.find(r=>r.reviewer_decision).review_note=\'test,"quoted"\\nline\'', context);
nodes.get('export').onclick();
(async()=>{
 const bytes = Buffer.from(await exported.arrayBuffer());
 assert.deepEqual([...bytes.subarray(0,3)], [239,187,191]);
 const csv = bytes.toString('utf8');
 assert.ok(csv.includes('TEST_ONLY_UI'));
 assert.ok(csv.includes('plan_hash'));
 assert.ok(csv.includes('test,""quoted""\nline'));
 assert.ok(csv.includes('\r\n'));
 const ids=vm.runInContext('data.map(r=>r.item_id)',context);
 assert.ok(ids.every(id=>csv.includes('"'+id+'"')),'Filtering must not drop hidden rows from export');
 const result={passed:true, method:'JavaScript execution with DOM test double; not visual browser QA', approved_test_rows:approved, filtered_bulk_scope:true, reset_preserves_decisions:true, export_includes_hidden_rows:true, exported_bytes:bytes.length, real_human_review:false};
 fs.writeFileSync('reports/ui_check.json', JSON.stringify(result,null,2));
 console.log(JSON.stringify(result));
})().catch(e=>{console.error(e);process.exitCode=1});
