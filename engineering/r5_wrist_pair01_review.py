# SPDX-License-Identifier: CC-BY-NC-4.0
# Independent geometry-integral and load audit, not a manufacturing qualification.
from pathlib import Path
import hashlib, json, math
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
# Drawing-only regression for shared polyline endpoints. Geometry/load checks
# above remain independent of the generator; here we exercise its projection.
import cadquery as cq
import r5_wrist_pair01 as drawing
def path_length(cs):
    total=0.
    for c in cs:
        if c['kind']=='LINE':total+=np.linalg.norm(np.array(c['p'])-c['q'])
        elif c['kind']=='CIRCLE':total+=2*math.pi*c['r']
        elif c['kind']=='ARC':total+=((c['end']-c['start'])%360)/180*math.pi*c['r']
    return total
projections=[]
for n in ['W01','A01-P','H01-reuse','A01-P-translated-regression']:
    file_name='A01-P' if n=='A01-P-translated-regression' else n
    shape=cq.importers.importStep(str(P/'STEP'/f'{file_name}.step')).val()
    if n!='W01':shape=drawing.moved(shape,drawing.T7)
    if n=='A01-P-translated-regression':shape=shape.translate((0,55,0))
    for cut_x in ([0.,10.5] if n=='W01' else [0.]):
        raw=drawing.curves(drawing.section(shape.rotate((0,0,0),(0,0,1),90),'XZ',cut_x),'XZ')
        cs=drawing.yzcs(shape,cut_x);bbox=np.array(drawing.bb(shape));outside=[]
        for c in cs:
            for key in ['p','q']:
                if key in c:
                    pt=np.array(c[key]);lo=bbox[0,[1,2]];hi=bbox[1,[1,2]]
                    if np.any(pt<lo-.003) or np.any(pt>hi+.003):outside.append(pt.tolist())
        length_error=abs(path_length(raw)-path_length(cs))
        assert not outside,(n,cut_x,outside)
        assert length_error<1e-8,(n,cut_x,length_error)
        projections.append(dict(part=n,section_X_mm=cut_x,curve_count=len(cs),out_of_shape_bounds=outside,reflection_path_length_error_mm=float(length_error)))
r=dict(result='PASS independent mesh mass/inertia and J6 gravity reconstruction; drawing projection regression PASS',mesh_checks=checks,J6_moment_Nm=bound,J6_axis_moment_Nm=axisbound,source_hashes_checked=len(s['source_hashes']),artifact_hashes_checked=len(m['outputs']),projection_regression=projections,scope='No vendor geometry, thread qualification, stress or hardware test rerun')
(P/'independent-review.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r,indent=2))
