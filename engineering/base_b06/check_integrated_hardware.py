# SPDX-License-Identifier: CC-BY-NC-4.0
"""Check actual CAD hardware/metal vs frozen root/IO and routing reservations.
Threads already audited with exact BREP in check_load_frame.py. No all-motion,
contact tolerance, wire simulation, wrench sweep or supplier fit guarantee.
"""
import json,hashlib,itertools,math
from pathlib import Path
import numpy as np,trimesh,manifold3d as md
HERE=Path(__file__).resolve().parent;OUT=HERE/'build/exterior';mf=OUT/'manifest.json';D=json.loads(mf.read_text())
parts={p['id']:p for p in D['parts']};cache={};bounds={}
def solid(k):
 if k not in cache:
  t=trimesh.load_mesh(OUT/parts[k]['stl'],process=True);bounds[k]=t.bounds
  s=md.Manifold(md.Mesh(vert_properties=np.asarray(t.vertices,dtype=np.float32),tri_verts=np.asarray(t.faces,dtype=np.uint32)))
  if s.status()!=md.Error.NoError:raise ValueError(k)
  cache[k]=s
 return cache[k]
actual=[k for k,p in parts.items() if p['category'] in ('metal','hardware','weld') or p['assembly_role']=='fasteners']
refs=[k for k,p in parts.items() if p['assembly_role'] in ('electronics','routing') or k.startswith('REF-P00') or k.startswith('REF-S00')]
checked=[]
for a,b in itertools.product(actual,refs):
 sa,sb=solid(a),solid(b);aa,bb=bounds[a],bounds[b]
 if np.any(aa[1]<bb[0]-.001) or np.any(bb[1]<aa[0]-.001):continue
 v=(sa^sb).volume();checked.append({'a':a,'b':b,'intersection_mm3':v})
 failures=[r for r in checked if r['intersection_mm3']>.01]
tools=[]
for i in range(8):
 angle=math.radians(22.5+45*i)
 t=trimesh.creation.cylinder(radius=6.5,height=126.4,sections=64)
 t.apply_translation((60*math.cos(angle),75+60*math.sin(angle),136.8))
 tool=md.Manifold(md.Mesh(vert_properties=np.asarray(t.vertices,dtype=np.float32),tri_verts=np.asarray(t.faces,dtype=np.uint32)))
 hits=[]
 for k in ['B06-301-MAIN-SHIELD']+(['REF-P00-root-open'] if 'REF-P00-root-open' in parts else []):
  v=(tool^solid(k)).volume()
  if v>.01:hits.append({'part':k,'intersection_mm3':v})
 tools.append({'root_bolt':i+1,'tool_diameter_mm':13,'z_mm':[73.6,200],'stage':'Base flange access; arm reference checked only if present','arm_reference_present':'REF-P00-root-open' in parts,'collisions':hits})
# Straight driver-body checks at documented assembly stages. The circular
# bodies do not certify handles, turning sweep, fingers or actual bought tools.
parts={p['id']:p for p in D['parts']}
allids=[p['id'] for p in D['parts'] if p.get('print_stl') or p['assembly_role'] in ('structure','electronics')]
assembly_tools=[]
def path(name,x,y,z0,z1,d,stage,obstacles,axis='Z'):
 t=trimesh.creation.cylinder(radius=d/2,height=z1-z0,sections=48)
 if axis=='Y':
  t.apply_transform(trimesh.transformations.rotation_matrix(-math.pi/2,[1,0,0]));t.apply_translation((x,(z0+z1)/2,y))
 else:t.apply_translation((x,y,(z0+z1)/2))
 tool=md.Manifold(md.Mesh(vert_properties=np.asarray(t.vertices,dtype=np.float32),tri_verts=np.asarray(t.faces,dtype=np.uint32)))
 hits=[]
 for k in obstacles:
  v=(tool^solid(k)).volume()
  if v>.01:hits.append({'part':k,'intersection_mm3':v})
 assembly_tools.append({'id':name,'diameter_mm':d,'axis':axis,'range_mm':[z0,z1],'stage':stage,'collisions':hits})
posts=[(-60,75),(60,75),(-38,120),(38,120)]
for i,(x,y) in enumerate(posts,1):
 path('M8-TOP-'+str(i),x,y,57.5,100,10,'Before root/cover fitting',['B06-104-LOAD-FLANGE']+[k for k in allids if k.startswith('B06-105-')])
 path('M8-BOTTOM-'+str(i),x,y,-70,2.5,10,'Before desk pad/table/box fitting',[k for k in allids if not k.startswith(('B06-106','B06-107','B06-108','HW-DIN6311','HW-DIN6332'))])
for x in (-10,10):
 path('COAX-BRACKET-'+str(x),x,-8,29.75,60,4,'PCB off base, RF connectors absent',['IO-BRI01_PCB','B06-309-COAX-BRACKET'])
for i,(x,y) in enumerate([(x,y) for x in (-52,52) for y in (-20,24)],1):
 path('PCB-M3-'+str(i),x,y,27.25,45.5,3.2,'Rear cover absent; short AF2 driver body only',[k for k in allids if k!='B06-304-REAR-LID'])
for i,(x,y) in enumerate([(-87,36),(87,36),(-72,125),(72,125)],1):
 path('COVER-M3-'+str(i),x,y,-30,3.85,4,'Before tabletop fitting',allids)
for x in (-60,60):
 path('REAR-M3-'+str(x),x,32,-80,-36.15,4,'External plugs absent',allids,axis='Y')
for x in (-23,23):
 path('LIGHT-M2-'+str(x),x,163.5,5,40.073,3,'Cover upside down before load frame/desk assembly',
      [k for k in allids if k.startswith(('B06-301','B06-306','B06-308','LIGHT-NATIVE'))])
result={'revision':D['revision'],'manifest_sha256':hashlib.sha256(mf.read_bytes()).hexdigest(),'pairs':checked,
 'interferences':failures,'bare_root_driver_paths':tools,'assembly_driver_paths':assembly_tools,'pass':not failures and all(not p['collisions'] for p in tools+assembly_tools),
 'limits':['Original owned supplier-size abstractions, not complete vendor MCAD.',
 'Thread envelopes are classified separately by exact BREP audit, not included here.',
 'Cables/latches/tools/full trajectories, tolerances and loads are NOT qualified.']}
(OUT/'hardware-integration-checks.json').write_text(json.dumps(result,indent=2)+'\n')
print('HARDWARE_INTEGRATION',result['pass'],'PAIRS',len(checked))
for r in failures:print(r)
if not result['pass']:raise SystemExit(1)
