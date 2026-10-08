# SPDX-License-Identifier: CC-BY-NC-4.0
"""Self-contained long-arm viewer; exact supplier option stays local."""
from pathlib import Path
import json,hashlib,sys,trimesh
sys.path.insert(0,str(Path(__file__).resolve().parent))
from context_source import canonical_repo
CANONICAL=canonical_repo()
ROOT=Path(__file__).resolve().parents[2];SRC=ROOT/'engineering/arm_a11/build';ACTUAL='--actual' in sys.argv
OUT=ROOT/'work/arm-a11/viewer-actual' if ACTUAL else ROOT/'docs/viewers/arm-body-a11';OUT.mkdir(parents=True,exist_ok=True)
def meshes(p):return dict(id=p['id'],frame=p['frame'],role=p['role'],vertices=[[round(x,3) for x in v] for v in p['vertices_mm']],faces=p['triangles'])
p=SRC/'manifest.json';d=json.loads(p.read_text());sha=hashlib.sha256(p.read_bytes()).hexdigest();review=json.loads((SRC/'feasibility.json').read_text());assert review['manifest_sha256']==sha
parts=[meshes(p) for p in d['parts'] if p['role']!='fit_coupon' and (not ACTUAL or p['role']!='motor_envelope')]
if ACTUAL:parts.extend(meshes(p) for p in json.loads((ROOT/'work/arm-a10/vendor/meshes.json').read_text()))
known=[];passed=[]
for filename in ['collision-supplier.json']:
 r=json.loads((SRC/filename).read_text());assert r['manifest_sha256']==sha
 for name,check in r['checks'].items():
  if check['overlaps']:known.append(dict(q=check['q_deg'],joint='assembly',angle=name))
passed=[name for name in d['layout']['poses'] if not any(q['q']==d['layout']['poses'][name] for q in known)]
data=dict(long=dict(known_conflicts=known,passed_poses=passed,layout=d['layout'],parts=parts,flange_from_J7_mm=d['flange_from_J7_mm'],shoulder_torque=review['cases']['3']['reference']['axes'][1]['abs_holding_Nm'],sha256=sha),base=[])
base=CANONICAL/'engineering/base_b05/build/exterior';bd=json.loads((base/'exterior-manifest.json').read_text());bm=json.loads((base/'render-meshes.json').read_text())
for p in bd['parts']:
 m=bm[p['id']]
 data['base'].append(dict(id=p['id'],color=p.get('color',[.18,.22,.26,1]),vertices=[[round(x,3) for x in v] for v in m['vertices']],faces=m['faces']))
t=(ROOT/'engineering/arm_a09/viewer.template.html').read_text().replace('A09','A11').replace('armA09','armA11')
t=t.replace('本体结构讨论','长版打印装配验证').replace('直管骨架 · 交叉肩部 · 收腰底座','收腰长脊 · 可拆折面护罩 · 同源魔鬼鱼底座').replace('结构与外观提案','机械试装 / 非额定承载')
t=t.replace('<button data-variant="slim" aria-pressed="true">短版 · 611 mm</button>','').replace('data-variant="long" aria-pressed="false"','data-variant="long" aria-pressed="true"').replace("current='slim'","current='long'").replace("build('slim')","build('long')").replace("sourceHashes:{slim:D.slim.sha256,long:D.long.sha256}","sourceHashes:{long:D.long.sha256}")
t=t.replace('此代表姿态：CAD实体未检出相交 · 紧固件/线束尚未完整','此代表姿态：实体与名义紧固件检查通过 · 插头/柔性线束待测')
a=t.index('<p class="note">');b=t.index('</p>',a)
t=t[:a]+'<p class="note">长版690.7 mm轴向参考距离；法兰总外负载目标3 kg。J2散热与打印结构强度未验证，先做受支撑的无动力试装。命名姿态检查状态见左上；原厂电机CAD与新护罩重新核对；滑条任意组合没有工作空间保证。'+('当前为本机原厂电机CAD版，供应商资产按原权利保留。' if ACTUAL else '公开模型使用自主绘制电机包络；本机另有原厂CAD模型。')+'</p>'+t[b+4:]
t=t.replace("['motor_envelope','hardware'].includes(p.role)","['motor_envelope','hardware','supplier_visual_reference'].includes(p.role)")
t=t.replace("p.id.includes('dark-cuff')?mats.core","(p.role==='printed_cover'&&(p.id.startsWith('J')||p.id.startsWith('S00')))?mats.core")
t=t.replace('Vector3(0,.35,.2)','Vector3(0,.35,.27)').replace('distance:1.35','distance:1.55')
t=t.replace('.stamp{font-size:12px','.stamp{white-space:nowrap;flex-shrink:0;font-size:12px').replace('.layout{display:grid','header>div{min-width:0}.layout{display:grid')
# Fit the three known poses without changing zoom during free slider edits.
t=t.replace('distance:1.55','distance:1.18')
t=t.replace("q=[...D[current].layout.poses[b.dataset.pose]];setAngles()", "q=[...D[current].layout.poses[b.dataset.pose]];const fit={idle:[.85,.23,.20],attention:[1.18,.29,.28],reference:[1.48,.38,.24]}[b.dataset.pose];orbit.distance=fit[0];target.set(0,fit[1],fit[2]);setAngles()")
# Preserve angular exterior ridges: split sharp feature edges remain in CAD tessellation.
t=t.replace('root.position.set(0,.135,.0346)','root.position.set(0,.075,.0346)').replace('底座与桌夹背景','同源底座外壳').replace('0xb4c2c9','0x53626b').replace('0x293842','0x29333a')
# Keep exact geometry. The private supplier viewer uses small local classic
# scripts so the desktop browser bridge never receives a75MB HTML response.
# All scripts remain offline local assets; no network dependency is added.
if ACTUAL:
 chunks=OUT/'model';chunks.mkdir(exist_ok=True)
 for old in chunks.glob('*.js'):old.unlink()
 setup=json.loads(json.dumps(data));lines=[]
 for group in ['long','base']:
  meshes=data['long']['parts'] if group=='long' else data['base']
  dest=setup['long']['parts'] if group=='long' else setup['base']
  for idx,m in enumerate(meshes):
   target=f"window.A11_MODEL.long.parts[{idx}]" if group=='long' else f"window.A11_MODEL.base[{idx}]"
   for field in ['vertices','faces']:
    dest[idx][field]=[]
    for start in range(0,len(m[field]),5000):lines.append(target+'.'+field+'.push(...'+json.dumps(m[field][start:start+5000],separators=(',',':'))+');\n')
 lines.insert(0,'window.A11_MODEL='+json.dumps(setup,ensure_ascii=False,separators=(',',':'))+';\n')
 scripts=[];buf=''
 def flush():
  global buf
  if not buf:return
  name=f'model/{len(scripts):03d}.js';(OUT/name).write_text(buf);scripts.append(name);buf=''
 for line in lines:
  if len(buf.encode())+len(line.encode())>900000:flush()
  buf+=line
 flush()
 t=t.replace('<script>__THREE__', ''.join(f'<script src="{file}"></script>' for file in scripts)+'<script>__THREE__')
 t=t.replace('__MODEL_DATA__','{}').replace("JSON.parse(document.getElementById('model-data').textContent)",'window.A11_MODEL')
else:t=t.replace('__MODEL_DATA__',json.dumps(data,ensure_ascii=False,separators=(',',':')))
t=t.replace('__THREE__',(ROOT/'docs/viewers/arm-body/vendor/three-r160.min.js').read_text())
(OUT/'index.html').write_text(t);(OUT/'THREE-LICENSE.txt').write_text((ROOT/'docs/viewers/arm-body/THREE-LICENSE.txt').read_text());print('VIEWER',ACTUAL,len(t.encode()))
