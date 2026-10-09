# SPDX-License-Identifier: CC-BY-NC-4.0
"""Sample rear lid extraction and compare actual EDA mounting datums.

No repair, no claim of continuous collision certification or physical fit.
Run after print_checks and check_solids have passed.
"""
import json, hashlib
from pathlib import Path
import numpy as np, trimesh, manifold3d
HERE=Path(__file__).resolve().parent; OUT=HERE/'build/exterior'
D=json.loads((OUT/'manifest.json').read_text())
def solid(part):
    mesh=trimesh.load_mesh(OUT/part['stl'],process=True)
    result=manifold3d.Manifold(manifold3d.Mesh(vert_properties=np.asarray(mesh.vertices,dtype=np.float32),tri_verts=np.asarray(mesh.faces,dtype=np.uint32)))
    if result.status()!=manifold3d.Error.NoError:raise ValueError(part['id'])
    return result
lidpart=next(p for p in D['parts'] if p['id']=='B06-304-REAR-LID')
lid=solid(lidpart)
obstacles=[p for p in D['parts'] if p['id']!=lidpart['id'] and (p.get('print_stl') or p['assembly_role'] in ('structure','electronics'))]
obstacles=[(p['id'],solid(p)) for p in obstacles]
samples=[]
for shift in [[0,-y,0] for y in (0,1,2,4,8,12,20,30,40)]+[[0,-40,z] for z in (5,15,30,60)]:
    moving=lid.translate(shift)
    collisions=[]
    for name,s in obstacles:
        v=(moving^s).volume()
        if v>.01:collisions.append({'part':name,'intersection_mm3':v})
    samples.append({'translation_mm':shift,'collisions':collisions})
eda_path=HERE.parent/'electronics/base-io-b05/reports/b06-native-fit-readback.json'
eda=json.loads(eda_path.read_text())['value']
targets={'H1':[52,24,24],'H2':[-52,24,24],'H3':[-52,-20,24],'H4':[52,-20,24]}
mounts=[]
for c in eda['components']:
    if c['ref'] not in targets:continue
    position=[58-c['u_mm'],30-c['v_mm'],24]
    delta=float(np.linalg.norm(np.array(position)-targets[c['ref']]))
    mounts.append({'ref':c['ref'],'eda_mm':[c['u_mm'],c['v_mm']],'assembly_mm':position,'target_mm':targets[c['ref']],'error_mm':delta})
result={'revision':D['revision'],'manifest_sha256':hashlib.sha256((OUT/'manifest.json').read_bytes()).hexdigest(),
        'eda_readback_sha256':hashlib.sha256(eda_path.read_bytes()).hexdigest(),
        'lid_extraction_samples':samples,'pcb_mounts':mounts,
        'sampled_extraction_pass':all(not s['collisions'] for s in samples),
        'pcb_datum_pass':len(mounts)==4 and all(m['error_mm']<.01 for m in mounts),
        'limits':['Discrete samples; no continuous sweep, tolerance or deflection proof.',
                  'Rear screws and all external plugs must first be removed.',
                  'No desk/wall/clamp, cables or hand/tool envelope included.',
                  'Mount datums from native EDA; component MCAD remains a frozen owned abstraction.']}
(OUT/'service-checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('SERVICE_CHECK',result['sampled_extraction_pass'],'PCB_DATUM',result['pcb_datum_pass'])
for s in samples:
    if s['collisions']:print(s)
if not result['sampled_extraction_pass'] or not result['pcb_datum_pass']:raise SystemExit(1)
