# SPDX-License-Identifier: CC-BY-NC-4.0
"""Fixture vs current base solids and straight M6/M8 driver-body volumes."""
import json,hashlib,math,itertools
from pathlib import Path
import numpy as np,trimesh,manifold3d as md
HERE=Path(__file__).resolve().parent;F=HERE/'build/standalone-test';E=HERE/'build/exterior'
fixture=json.loads((F/'fixture-manifest.json').read_text());base=json.loads((E/'manifest.json').read_text())
def solid(path):
    m=trimesh.load_mesh(path,process=True)
    s=md.Manifold(md.Mesh(vert_properties=np.asarray(m.vertices,dtype=np.float32),tri_verts=np.asarray(m.faces,dtype=np.uint32)))
    assert s.status()==md.Error.NoError,path
    return s,m.bounds
fs={p['id']:solid(F/p['stl']) for p in fixture['parts']}
bs={p['id']:solid(E/p['stl']) for p in base['parts'] if p.get('print_stl') or p['assembly_role']=='electronics'}
pairs=[]
for a,b in itertools.product(fs,bs):
    sa,aa=fs[a];sb,bb=bs[b]
    if np.any(aa[1]<bb[0]-.001) or np.any(bb[1]<aa[0]-.001):continue
    v=(sa^sb).volume();pairs.append({'fixture':a,'base':b,'intersection_mm3':v})
tools=[]
for label,n,r,phase,z0,z1,d,obstacles in [('M6',8,60,22.5,73.6,200,13,[*bs,'B06-T01-TEST-ADAPTER']),('M8',4,30,45,117.6,300,14,[*bs,'B06-T01-TEST-ADAPTER','B06-T02-TEST-POST'])]:
    for i in range(n):
        a=math.radians(phase+i*360/n);m=trimesh.creation.cylinder(radius=d/2,height=z1-z0,sections=64)
        m.apply_translation((r*math.cos(a),75+r*math.sin(a),(z0+z1)/2))
        t=md.Manifold(md.Mesh(vert_properties=np.asarray(m.vertices,dtype=np.float32),tri_verts=np.asarray(m.faces,dtype=np.uint32)))
        hits=[]
        for k in obstacles:
            v=(t^(bs[k][0] if k in bs else fs[k][0])).volume()
            if v>.01:hits.append({'part':k,'volume_mm3':v})
        tools.append({'fastener':label+'-'+str(i+1),'body_diameter_mm':d,'z_mm':[z0,z1],'collisions':hits})
result={'pass':all(p['intersection_mm3']<=.01 for p in pairs) and all(not t['collisions'] for t in tools),
 'manifest_sha256':hashlib.sha256((E/'manifest.json').read_bytes()).hexdigest(),
 'fixture_manifest_sha256':hashlib.sha256((F/'fixture-manifest.json').read_bytes()).hexdigest(),
 'pairs':pairs,'driver_paths':tools,'limits':['Static nominal closed solids and straight tool bodies only; no hands, turning sweep or actual hardware fit','Apparatus load rating not qualified']}
(F/'fixture-fit-checks.json').write_text(json.dumps(result,indent=2)+'\n')
print('FIXTURE_FIT',result['pass'],'pairs',len(pairs),'driver paths',len(tools))
assert result['pass'],result
# Standalone-test viewer includes the same base product, not a second design.
parts=[]
for p in base['parts']:
    p=dict(p);p['stl']='../exterior/'+p['stl'];p['print_stl']=None;parts.append(p)
data={**base,'revision':base['revision']+'-TEST-RIG','module':'standalone_test_fixture',
      'parts':parts+fixture['parts'],'review_status':'独立底座验证工装 · 非产品件／未经加载验证'}
(F/'manifest.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
