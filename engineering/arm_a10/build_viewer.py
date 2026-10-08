# SPDX-License-Identifier: CC-BY-NC-4.0
"""Self-contained long-arm viewer; exact supplier option stays local."""
from pathlib import Path
import json,hashlib,sys,trimesh
ROOT=Path(__file__).resolve().parents[2];SRC=ROOT/'engineering/arm_a10/build';ACTUAL='--actual' in sys.argv
OUT=ROOT/'work/arm-a10/viewer-actual' if ACTUAL else ROOT/'docs/viewers/arm-body-a10';OUT.mkdir(parents=True,exist_ok=True)
def meshes(p):return dict(id=p['id'],frame=p['frame'],role=p['role'],vertices=[[round(x,3) for x in v] for v in p['vertices_mm']],faces=p['triangles'])
p=SRC/'manifest.json';d=json.loads(p.read_text());sha=hashlib.sha256(p.read_bytes()).hexdigest();review=json.loads((SRC/'feasibility.json').read_text());assert review['manifest_sha256']==sha
parts=[meshes(p) for p in d['parts'] if p['role']!='fit_coupon' and (not ACTUAL or p['role']!='motor_envelope')]
if ACTUAL:parts.extend(meshes(p) for p in json.loads((ROOT/'work/arm-a10/vendor/meshes.json').read_text()))
known=[];passed=[]
for filename in ['collision-full.json','collision-supplier.json']:
 r=json.loads((SRC/filename).read_text());assert r['manifest_sha256']==sha
 for name,check in r['checks'].items():
  if check['overlaps']:known.append(dict(q=check['q_deg'],joint='assembly',angle=name))
passed=[name for name in d['layout']['poses'] if not any(q['q']==d['layout']['poses'][name] for q in known)]
data=dict(long=dict(known_conflicts=known,passed_poses=passed,layout=d['layout'],parts=parts,flange_from_J7_mm=d['flange_from_J7_mm'],shoulder_torque=review['cases']['3']['reference']['axes'][1]['abs_holding_Nm'],sha256=sha),base=[])
base=ROOT/'engineering/arm_a10/context/base_b04';bd=json.loads((base/'manifest.json').read_text());bm=json.loads((base/'cad-surface-meshes.json').read_text())
for p in bd['parts']:
 if p['category'] in ['guide','routing','environment'] or p['id'].startswith('ENV-'):continue
 if p['id'] in bm:m=bm[p['id']]
 elif p.get('stl') and (base/p['stl']).exists():
  mm=trimesh.load(base/p['stl'],force='mesh');m=dict(vertices=mm.vertices.tolist(),faces=mm.faces.tolist())
 else:continue
 data['base'].append(dict(id=p['id'],color=p.get('color',[.3,.35,.4,1]),vertices=[[round(x,3) for x in v] for v in m['vertices']],faces=m['faces']))
t=(ROOT/'engineering/arm_a09/viewer.template.html').read_text().replace('A09','A10').replace('armA09','armA10')
t=t.replace('本体结构讨论','长版打印装配验证').replace('直管骨架 · 交叉肩部 · 收腰底座','金属直管 · 一体打印端座 · 可拆分体护罩').replace('结构与外观提案','机械试装 / 非额定承载')
t=t.replace('<button data-variant="slim" aria-pressed="true">短版 · 611 mm</button>','').replace('data-variant="long" aria-pressed="false"','data-variant="long" aria-pressed="true"').replace("current='slim'","current='long'").replace("build('slim')","build('long')").replace("sourceHashes:{slim:D.slim.sha256,long:D.long.sha256}","sourceHashes:{long:D.long.sha256}")
t=t.replace('此代表姿态：CAD实体未检出相交 · 紧固件/线束尚未完整','此代表姿态：实体与名义紧固件检查通过 · 插头/柔性线束待测')
a=t.index('<p class="note">');b=t.index('</p>',a)
t=t[:a]+'<p class="note">长版690.7 mm轴向参考距离；法兰总外负载目标3 kg。J2散热与打印结构强度未验证，先做受支撑的无动力试装。三个命名姿态经过名义硬件及原厂电机CAD检查；滑条任意组合没有工作空间保证。'+('当前为本机原厂电机CAD版，供应商资产按原权利保留。' if ACTUAL else '公开模型使用自主绘制电机包络；本机另有原厂CAD模型。')+'</p>'+t[b+4:]
t=t.replace("['motor_envelope','hardware'].includes(p.role)","['motor_envelope','hardware','supplier_visual_reference'].includes(p.role)")
t=t.replace("p.id.includes('dark-cuff')?mats.core","(p.role==='printed_cover'&&(p.id.startsWith('J')||p.id.startsWith('S00')))?mats.core")
t=t.replace('Vector3(0,.35,.2)','Vector3(0,.35,.27)').replace('distance:1.35','distance:1.55')
t=t.replace('.stamp{font-size:12px','.stamp{white-space:nowrap;flex-shrink:0;font-size:12px').replace('.layout{display:grid','header>div{min-width:0}.layout{display:grid')
# Preserve angular exterior ridges: split sharp feature edges remain in CAD tessellation.
t=t.replace('__THREE__',(ROOT/'docs/viewers/arm-body/vendor/three-r160.min.js').read_text()).replace('__MODEL_DATA__',json.dumps(data,ensure_ascii=False,separators=(',',':')))
(OUT/'index.html').write_text(t);(OUT/'THREE-LICENSE.txt').write_text((ROOT/'docs/viewers/arm-body/THREE-LICENSE.txt').read_text());print('VIEWER',ACTUAL,len(t.encode()))
