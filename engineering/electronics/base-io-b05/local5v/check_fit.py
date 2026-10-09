# SPDX-License-Identifier: CC-BY-NC-4.0
"""Check local supply bodies against the complete BASE-only assembly.

Conservative maximum package envelopes. Does not qualify wiring, connector
latches, printed tolerances, thermal performance or solder process.
"""
import json,hashlib,itertools,argparse
from pathlib import Path
import numpy as np,trimesh,manifold3d as md
HERE=Path(__file__).resolve().parent;R=HERE.parent
BASE=R.parents[1]/'base_b06';E=BASE/'build/exterior'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
spec=json.loads((HERE/'package-envelopes.json').read_text())
parser=argparse.ArgumentParser()
parser.add_argument('--geometry-only',action='store_true',help='Candidate package fit only; never PCB/manufacturing qualification')
args=parser.parse_args()
native_path=R/'controller/native-readback.json'
native=json.loads(native_path.read_text())
assert native['ok'] and native['verification']['native_reopened']
if not args.geometry_only:assert not native['value']['drc'], 'Current controller PCB DRC unresolved; manufacturing audit blocked'
for name,expected in native['source_sha256'].items():assert sha(R/name)==expected
component_by_ref={c['designator']:c for c in native['value']['components']}
for p in spec['parts']:
    c=component_by_ref[p['designator']]
    offset={'U1':2.25,'J7':.3}.get(p['designator'],0)
    assert np.allclose(p['center_uv'],[c['x']*.0254,-c['y']*.0254+offset],atol=.002), 'Stale MCAD placement '+p['designator']
manifest=json.loads((E/'manifest.json').read_text())
assert not manifest['arm_reference_included']
def solid(m):
    s=md.Manifold(md.Mesh(vert_properties=np.asarray(m.vertices,dtype=np.float32),tri_verts=np.asarray(m.faces,dtype=np.uint32)))
    assert s.status()==md.Error.NoError
    return s
packages={};meshes={}
for p in spec['parts']:
    u,v=p['center_uv'];size=p['size_mm'];m=trimesh.creation.box(size)
    m.apply_translation((58-u,30-v,p['body_z0']+size[2]/2))
    packages[p['designator']]=solid(m);meshes[p['designator']]=m
for p in spec.get('mate_reservations',[]):
    lo,hi=np.array(p['bounds_xyz_mm']);m=trimesh.creation.box(hi-lo)
    m.apply_translation((lo+hi)/2);packages[p['id']]=solid(m);meshes[p['id']]=m
checks=[]
for a,b in itertools.combinations(packages,2):
    checks.append({'a':a,'b':b,'intersection_mm3':(packages[a]^packages[b]).volume()})
for p in manifest['parts']:
    if p.get('assembly_role') not in ('structure','electronics','fasteners','cover','light') and not p.get('print_stl'):continue
    if p['id']=='IO-BRI01_PCB' or p['id'].startswith('IO-LOCAL5V-'):continue
    m=trimesh.load_mesh(E/p['stl'],process=True);s=None
    for d,mesh in meshes.items():
        if np.any(mesh.bounds[1]<m.bounds[0]-.001) or np.any(m.bounds[1]<mesh.bounds[0]-.001):continue
        if s is None:s=solid(m)
        checks.append({'a':d,'b':p['id'],'intersection_mm3':(packages[d]^s).volume()})
fail=[c for c in checks if c['intersection_mm3']>.01]
# Include all six PCB screws: Ø7 straight body, accessible before mating plugs.
tools=[]
for u,v in [(6,6),(110,6),(110,50),(6,50),(48,38),(68,38)]:
    m=trimesh.creation.cylinder(radius=3.5,height=35,sections=48)
    m.apply_translation((58-u,30-v,43.1));s=solid(m)
    hits=[d for d in packages if d not in {p['id'] for p in spec.get('mate_reservations',[])} and (s^packages[d]).volume()>.01]
    tools.append({'center_uv':[u,v],'diameter_mm':7,'range_z_mm':[25.6,60.6],'package_collisions':hits})
report={'pass':not fail and all(not t['package_collisions'] for t in tools),'arm_required':False,
    'scope':'Package body and screwdriver geometry only',
    'pcb_drc_pass':not native['value']['drc'],'manufacturing_released':False,
    'checks':checks,'interferences':fail,'driver_paths':tools,
    'hashes':{str(p.relative_to(R.parents[2])):sha(p) for p in [HERE/'package-envelopes.json',E/'manifest.json',native_path]},
    'limits':['Body envelopes only; full mating plug, wire bend, thermal and manufacturing tolerances unqualified','Standalone branch not energized; physical production release false']}
(R/'reports/b06-controller-fit.json').write_text(json.dumps(report,indent=2)+'\n')
print('LOCAL5V_BASE_FIT',report['pass'],'pairs',len(checks));print('INTERFERENCES',fail)
if not report['pass']:raise SystemExit(1)
