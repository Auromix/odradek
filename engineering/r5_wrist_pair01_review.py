# SPDX-License-Identifier: CC-BY-NC-4.0
# Independent geometry-integral and load audit, not a manufacturing qualification.
from pathlib import Path
import hashlib, json
import numpy as np
import trimesh

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'engineering/generated/r5-wrist-pair01'
s=json.loads((P/'study.json').read_text())
m=json.loads((P/'manifest.json').read_text())
for row in s['source_hashes']:
    assert hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['sha256']
for row in m['outputs']:
    assert hashlib.sha256((P/row['path']).read_bytes()).hexdigest()==row['sha256']
checks=[]
for name,part in s['parts'].items():
    mesh=trimesh.load(P/'STL'/f'{name}.stl',force='mesh')
    assert mesh.is_watertight and mesh.is_winding_consistent
    mass=mesh.volume*2.7e-6
    I=mesh.moment_inertia*2.7e-12
    com=mesh.center_mass
    dm=abs(mass/part['mass_6061_candidate_kg']-1)
    di=np.linalg.norm(I-np.array(part['inertia_at_com_kg_m2']))/np.linalg.norm(I)
    dc=max(abs(com-np.array(part['com_mm'])))
    assert dm<.0002 and di<.0003 and dc<.003
    checks.append(dict(part=name,mass_relative_error=dm,inertia_relative_error=di,COM_error_mm=dc))
# Independent sum of mass-position vectors; all bodies see one uniform g.
bodies=[(r['mass_kg'],np.array(r['com_pair_mm'])/1000) for r in s['mechanics']['body_rows']]
bodies += [(2.,np.array([0.,.055,.235])),(1.5,np.array([0.,.055,.135])),(.88,np.array([0.,.055,.035-.03215]))]
h=sum((mass*com for mass,com in bodies),start=np.zeros(3))
g=9.80665
bound=g*np.linalg.norm(h)
axisbound=g*np.linalg.norm(np.cross(np.array([0,1.,0]),h))
assert abs(bound-s['mechanics']['J6_zero_geometry_arbitrary_gravity_moment_Nm'])<1e-10
assert abs(axisbound-s['mechanics']['J6_axis_gravity_torque_abs_bound_Nm'])<1e-10
r=dict(result='PASS independent mesh mass/inertia and J6 gravity reconstruction',mesh_checks=checks,J6_moment_Nm=bound,J6_axis_moment_Nm=axisbound,source_hashes_checked=len(s['source_hashes']),artifact_hashes_checked=len(m['outputs']),scope='No vendor geometry, thread qualification, stress or hardware test rerun')
(P/'independent-review.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r,indent=2))
