# SPDX-License-Identifier: CC-BY-NC-4.0
"""Independent R5-ROUTE01 centerline and ideal-mechanics audit."""
from pathlib import Path
import hashlib, importlib.util, json, math
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'engineering/generated/r5-route01'
SRC=ROOT/'engineering/r5_route01.py'
STUDY=ROOT/'engineering/generated/r5-route01/study.json'
DOC=ROOT/'docs/engineering/r5-route01.md'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
hashes={str(p.relative_to(ROOT)):sha(p) for p in [SRC,STUDY,DOC]}
spec=importlib.util.spec_from_file_location('route_under_review',SRC)
route=importlib.util.module_from_spec(spec);spec.loader.exec_module(route)
j=json.loads(STUDY.read_text()); p=j['parameters']
r=p['leaf_pitch_radius_mm']; b=p['secondary_pitch_radius_mm']
a=p['fixed_center_radius_mm']; zf=p['fixed_center_Z_mm']
assert j['sources']['engineering/r5_route01.py']==sha(SRC)

def arclen(points,center,radius):
    unit=(points-np.asarray(center))/radius
    assert np.max(abs(np.linalg.norm(unit,axis=1)-1))<1e-12
    angles=np.arctan2(np.linalg.norm(np.cross(unit[:-1],unit[1:]),axis=1),np.einsum('ij,ij->i',unit[:-1],unit[1:]))
    return radius*np.sum(angles)

rng=np.random.default_rng(105)
states=[np.array(v['R_mm']) for v in j['poses']]+[rng.uniform(31,91,4) for _ in range(32)]
exact_errors=[];join_errors=[];chord_deficits=[];calculated_lengths=[]
for R in states:
    c=route.configuration(R)
    out=[]
    for k,idxs in enumerate([(0,1),(3,2)]):
        points=c['routes'][k]['points']; assert points.shape==(197,3)
        i,l=idxs; y=r if k==0 else -r
        centers=[a*route.E[i]+[0,0,zf],[0,y,c['Z'][k]],a*route.E[l]+[0,0,zf]]
        # Reconstruct metric from exported path vertices, not its stored length expression.
        straight=sum(np.linalg.norm(points[v]-points[u]) for u,v in [(0,1),(49,50),(146,147),(195,196)])
        length=straight+arclen(points[1:50],centers[0],r)+arclen(points[50:147],centers[1],r)+arclen(points[147:196],centers[2],r)
        out.append(length)
        exact_errors.append(abs(length-c['routes'][k]['exact_length_mm']))
        chord_deficits.append(length-np.linalg.norm(np.diff(points,axis=0),axis=1).sum())
        # Vertical joins and common tangent endpoints are exactly aligned in XY.
        join_errors.extend([np.linalg.norm((points[49]-points[50])[:2]),np.linalg.norm((points[146]-points[147])[:2])])
        for fixed_idx,point_idx in [(i,49),(l,147)]:
            xy=(a-r)*route.E[fixed_idx][:2]
            join_errors.append(np.linalg.norm(points[point_idx,:2]-xy))
    points=c['routes'][2]['points'];assert points.shape==(99,3)
    length=np.linalg.norm(points[1]-points[0])+arclen(points[1:98],[27,0,c['zmean']],b)+np.linalg.norm(points[98]-points[97])
    exact_errors.append(abs(length-c['routes'][2]['exact_length_mm']));out.append(length)
    chord_deficits.append(length-np.linalg.norm(np.diff(points,axis=0),axis=1).sum())
    calculated_lengths.append(out)
assert max(exact_errors)<1e-9 and max(join_errors)<1e-9
assert np.max(np.ptp(calculated_lengths,axis=0))<1e-9

# Differentiate seven-coordinate length constraints independently.
J=np.array([[1,1,0,0,-2,0,0],[0,0,1,1,0,-2,0],[0,0,0,0,1,1,-2]],float)
assert np.linalg.matrix_rank(J)==3
noslip=[];constraint=[];power=[];speed_examples=[]
for vR in rng.uniform(-300,300,(1000,4)):
    vA=(vR[0]+vR[1])/2;vB=(vR[2]+vR[3])/2;vC=np.mean(vR)
    v=np.r_[vR,vA,vB,vC]
    constraint.append(np.max(abs(J@v)))
    # Solve contact velocities = Vcenter + omega cross radius (wheel axes +Y/+X).
    VwA=np.linalg.solve([[1,-r],[1,r]],vR[[0,1]])
    VwB=np.linalg.solve([[1,-r],[1,r]],vR[[3,2]])
    VwC=np.linalg.solve([[1,b],[1,-b]],[vA,vB])
    expected=np.array([[vA,(vR[1]-vR[0])/(2*r)],[vB,(vR[2]-vR[3])/(2*r)],[vC,(vA-vB)/(2*b)]])
    noslip.append(np.max(abs(np.array([VwA,VwB,VwC])-expected)))
    # -J^T tension multipliers are cable generalized forces on all moving endpoints.
    # With leaf T=50, secondary=100, this gives 4 leaves=-50 and mean=+200 N.
    Q=-J.T@np.array([50,50,100])
    power.append(abs(Q@(v/1000)))
assert max(noslip)<1e-10 and max(constraint)<1e-10 and max(power)<1e-10
for name,v in [('equal_150',[150]*4),('one_leaf_150',[150,0,0,0]),('opposed_groups_150',[150,150,-150,-150])]:
    v=np.array(v);va=(v[0]+v[1])/2;vb=(v[2]+v[3])/2
    signed=[*(v/r), (v[1]-v[0])/(2*r),(v[2]-v[3])/(2*r),(va-vb)/(2*b)]
    speed_examples.append(dict(name=name,Rdot_mm_s=v.tolist(),signed_rpm=(np.array(signed)*60/(2*math.pi)).tolist(),order=['F_UR','F_UL','F_LL','F_LR','M_top_Y','M_bottom_Y','M_mean_X']))

# Force/moment from vector cross products, independently of scalar hypot expression.
T=50.; moments=[]
for sign in [1,-1]:
    attachment=np.array([27,sign*b,0])/1000
    wheelcenter=np.array([0,sign*r,0])/1000
    moment=np.cross(attachment-wheelcenter,[0,0,-2*T])
    assert abs(np.linalg.norm(moment)-j['load_path_requirements']['leaf_carriage_offset_moment_Nm'])<1e-12
    moments.append(moment.tolist())
radial_lug_r=np.array([30,0,-25-20])/1000
radial_lug_M=np.cross(radial_lug_r,[-T,0,0])
assert abs(radial_lug_M[1]-2.25)<1e-12
assert abs(math.sqrt(2)*T-j['load_path_requirements']['each_fixed_90deg_wheel_resultant_N'])<1e-12

# Re-derive the plane-separation bounds and rear endpoint from catalogue envelopes.
planes=[zf-15.875-(-75+15.875),2*r-6.35,27-7.1374/2-15.875,zf-15.875-(-140+19.05)]
assert min(planes)>0
assert abs(20-(-140+31-91-19.05)-j['existing_root_to_farthest_pulley_mm'])<1e-12

result=dict(revision='R5-ROUTE01-independent-review',verdict='PASS for nominal centerline/ideal velocity and stated scalar load formulas; support load addition documented',
 inputs=hashes,
 metrics=dict(configurations_reconstructed=len(states),max_path_metric_vs_report_error_mm=max(exact_errors),
 max_tangent_join_XY_error_mm=max(join_errors),length_span_mm=np.ptp(calculated_lengths,axis=0).tolist(),
 leaf_and_secondary_centerline_lengths_mm=calculated_lengths[0],max_polyline_chord_shortfall_mm=max(chord_deficits),
 independent_velocity_cases=1000,max_contact_velocity_solution_error=max(noslip),max_length_velocity_residual_mm_s=max(constraint),
 max_virtual_power_residual_W=max(power),constraint_rank=3,coordinate_count=7,free_coordinates_before_mean_input=4,
 wheel_plane_separation_bounds_mm=planes),
 moment_vectors_Nm=dict(leaf_top= moments[0],leaf_bottom=moments[1],radial_lug_about_root_hinge_local=radial_lug_M.tolist()),
 speed_examples=speed_examples,
 findings=[dict(severity='engineering-load-check',text='At T=50 N, each proposed carrier lug is 45 mm behind root hinge plane (Z -25 vs +20), so its inward force contributes +2.25 N m about local +Y, in addition to the documented 2.71145 N m moving-wheel-yoke moment. This is a carrier/guide support moment, not automatically a petal hinge/cam reaction. Actual support reactions require guide/support locations.'),
 dict(severity='scope',text='Arc path metrics and instantaneous no-slip equations checked independently. Original 21-pose collision results not rerun; wheel-only plane bounds rederived. No continuous rope clearance, groove fit, axial retainers, yokes or actual load reachability proved.')])
assert hashes=={str(p.relative_to(ROOT)):sha(p) for p in [SRC,STUDY,DOC]}, 'inputs changed during review'
(WORK/'independent-review.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
