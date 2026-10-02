# SPDX-License-Identifier: CC-BY-NC-4.0
"""Bundle original CAD surface meshes and existing MIT three.js into offline viewer."""
from pathlib import Path
import json,hashlib
import trimesh
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'docs/viewers/arm-body-a09';OUT.mkdir(parents=True,exist_ok=True)
def meshes(p):return dict(id=p['id'],frame=p['frame'],role=p['role'],vertices=[[round(x,3) for x in v] for v in p['vertices_mm']],faces=p['triangles'])
data={}
for variant in ['slim','long']:
 path=ROOT/'engineering/arm_a09/build'/variant/'manifest.json';d=json.loads(path.read_text());review=json.loads(path.with_name('screening.json').read_text());sha=hashlib.sha256(path.read_bytes()).hexdigest();assert review['source_sha256']==sha
 sweep=json.loads(path.with_name('local-wrist-sweep.json').read_text());assert sweep['manifest_sha256']==sha
 known=[]
 for check in sweep['checks']:
  if check['overlaps']:
   q=d['layout']['poses']['reference'].copy();q[int(check['joint'][1])-1]=check['angle_deg'];known.append(dict(q=q,joint=check['joint'],angle=check['angle_deg']))
 data[variant]=dict(known_conflicts=known,layout=d['layout'],parts=[meshes(p) for p in d['parts']],flange_from_J7_mm=d['flange_from_J7_mm'],shoulder_torque=review['presets']['reference']['axes'][1]['abs_holding_Nm'],sha256=sha)
base=ROOT.parent/'odradek/engineering/base_b04/build';bd=json.loads((base/'manifest.json').read_text());bm=json.loads((base/'cad-surface-meshes.json').read_text());data['base']=[]
for p in bd['parts']:
 if p['category'] in ['guide','routing','environment'] or p['id'].startswith('ENV-'):continue
 if p['id'] in bm:m=bm[p['id']]
 elif p.get('stl') and (base/p['stl']).exists():
  mesh=trimesh.load(base/p['stl'],force='mesh');m=dict(vertices=mesh.vertices.tolist(),faces=mesh.faces.tolist())
 else:continue
 data['base'].append(dict(id=p['id'],color=p.get('color',[.3,.35,.4,1]),vertices=[[round(x,3) for x in v] for v in m['vertices']],faces=m['faces']))
template=(ROOT/'engineering/arm_a09/viewer.template.html').read_text();js=(ROOT/'docs/viewers/arm-body/vendor/three-r160.min.js').read_text();html=template.replace('__THREE__',js).replace('__MODEL_DATA__',json.dumps(data,ensure_ascii=False,separators=(',',':')))
(OUT/'index.html').write_text(html);(OUT/'THREE-LICENSE.txt').write_text((ROOT/'docs/viewers/arm-body/THREE-LICENSE.txt').read_text());print('VIEWER',len(html.encode()))
