# SPDX-License-Identifier: CC-BY-NC-4.0
"""Independent closed-solid interference checks; no mesh repairs.

Requires numpy, trimesh, manifold3d, rtree. Excludes intended bolt/nut pairs.
Volume threshold is numerical, not a manufacturing tolerance.
"""
import json,hashlib,itertools
from pathlib import Path
import numpy as np,trimesh,manifold3d
HERE=Path(__file__).resolve().parent;OUT=HERE/'build/exterior'
MF=OUT/'manifest.json';D=json.loads(MF.read_text())
data={p['id']:p for p in D['parts']}
meshes={k:trimesh.load_mesh(OUT/p['stl'],process=True) for k,p in data.items()}
solids={};invalid=[]
def solid(k):
    if k in solids:return solids[k]
    m=meshes[k]
    # Processing welds coincident vertices only; never fill/repair a failed solid.
    s=manifold3d.Manifold(manifold3d.Mesh(vert_properties=np.asarray(m.vertices,dtype=np.float32),tri_verts=np.asarray(m.faces,dtype=np.uint32)))
    if s.status()!=manifold3d.Error.NoError:invalid.append(dict(id=k,error=str(s.status())))
    solids[k]=s;return s
printed=[k for k,p in data.items() if p.get('print_stl')]
refs=[k for k,p in data.items() if p['assembly_role'] in ('structure','electronics','fasteners') or k=='LIGHT-MATED-GH-RESERVE']
pairs=[]
for a,b in [*itertools.combinations(printed,2),*itertools.product(printed,refs)]:
    aa,bb=meshes[a].bounds,meshes[b].bounds
    if np.any(aa[1]<bb[0]-.001) or np.any(bb[1]<aa[0]-.001):continue
    sa,sb=solid(a),solid(b)
    if sa.status()!=manifold3d.Error.NoError or sb.status()!=manifold3d.Error.NoError:continue
    result=sa^sb;volume=result.volume()
    pairs.append(dict(a=a,b=b,volume_mm3=volume,intersection_status=str(result.status()),penetration_over_0_01mm3=volume>.01))
    if volume>.01:print('INTERFERENCE',a,b,round(volume,5),flush=True)
report=dict(revision=D['revision'],manifest_sha256=hashlib.sha256(MF.read_bytes()).hexdigest(),
            scope='Static closed STL solid intersections; current base cosmetic/structural/electronic parts; arm reference optional',
            engine='manifold3d',numerical_volume_threshold_mm3=.01,
            pairs=pairs,invalid_solids=invalid,
            interferences=[p for p in pairs if p['penetration_over_0_01mm3']],
            static_solid_interference_pass=not invalid and not any(p['penetration_over_0_01mm3'] for p in pairs),
            limits=['Float32 mesh Boolean; no exact BREP or real fit certification.',
                    'PCB/post face contact is intentional; any positive volume is reported.',
                    'No motion, deflection, thermal, cables or clamp/load-path validation.'])
(OUT/'solid-fit-checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('SOLID_CHECK',report['static_solid_interference_pass'],'pairs',len(pairs),'invalid',len(invalid),flush=True)

if not report['static_solid_interference_pass']:raise SystemExit(1)
