# SPDX-License-Identifier: CC-BY-NC-4.0
"""Reconstruct offline script chunks and compare all meshes to audited input."""
from pathlib import Path
import sys,os,json,re,subprocess,hashlib,shutil
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;ACTUAL='--actual' in sys.argv
OUT=ROOT/'work/arm-a14/wrist-tail01/viewer-actual' if ACTUAL else ROOT/'docs/viewers/arm-body-a14-wrist-tail01'
cache=ROOT/('work/arm-a14/wrist-tail01/viewer-data-actual.json' if ACTUAL else 'work/arm-a14/wrist-tail01/viewer-data-public.json')
html=(OUT/'index.html').read_text();refs=re.findall(r'<script src="([^"]+)"',html)
assert refs and all('://' not in x and (OUT/x).is_file() for x in refs)
js='''const fs=require('fs'),vm=require('vm'),assert=require('assert');
const args=JSON.parse(fs.readFileSync(0,'utf8')),ctx={window:{}};vm.createContext(ctx);
for(const p of args.chunks) vm.runInContext(fs.readFileSync(p,'utf8'),ctx);
for(const code of args.inline) new vm.Script(code);
const expected=JSON.parse(fs.readFileSync(args.cache,'utf8')),actual=ctx.window.A14_MODEL;
assert.equal(JSON.stringify(actual),JSON.stringify(expected));
assert(actual.long.parts.every(p=>p.vertices.length&&p.faces.length));
assert(actual.base.every(p=>p.vertices.length&&p.faces.length));
console.log(JSON.stringify({chunks:args.chunks.length,part_count:actual.long.parts.length,base_count:actual.base.length,all_packaged_data_match:true,inline_syntax_valid:true}));'''
args=dict(chunks=[str(OUT/x) for x in refs],cache=str(cache),inline=[x for x in re.findall(r'<script(?: [^>]*)?>(.*?)</script>',html,re.S) if x.strip()])
node=os.environ.get('A14_NODE_RUNTIME') or shutil.which('node');assert node
p=subprocess.run([node,'--max-old-space-size=4096','-e',js],input=json.dumps(args),text=True,capture_output=True)
assert p.returncode==0,p.stderr
report=json.loads(p.stdout);report['index_sha256']=hashlib.sha256((OUT/'index.html').read_bytes()).hexdigest();report['production_release']=False
(HERE/'build'/('viewer-package-actual-audit.json' if ACTUAL else 'viewer-package-public-audit.json')).write_text(json.dumps(report,indent=2)+'\n')
print('OFFLINE_DATA_PASS',ACTUAL,report,flush=True)
