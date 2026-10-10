# SPDX-License-Identifier: CC-BY-NC-4.0
"""Machinable R6 shoulder-foot candidate and source-bound gravity wrenches."""
from pathlib import Path
import json,sys,math
import numpy as np
import cadquery as cq
import trimesh
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=HERE/'build/root17'
sys.path.insert(0,str(ROOT/'engineering/arm_a18'));import feasibility01 as f
sys.path.insert(0,str(ROOT/'engineering/arm_a16'));import skeleton_review as r
c=f.c
GUSSET='--gusset' in sys.argv
if GUSSET:OUT=HERE/'build/root17-gusset'
THICK='--thick' in sys.argv
if THICK:OUT=HERE/'build/root22'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    path=ROOT/'engineering/arm_a18/build/assembly12.json';d=json.loads(path.read_text())
    row=next(p for p in d['parts'] if p['id']=='A16-C04-J2-mount-plate');src=ROOT/row['step_path'];s=cq.importers.importStep(str(src)).val()
    front=60.5
    if THICK:
        extra=s.translate((0,-4,0)).intersect(cq.Solid.makeBox(160,4,200,c.cad.V([-80,56.5,38])))
        s=s.fuse(extra).fix();front=56.5
        # Preserve old 8mm cover seats as real counterbores in added layer.
        for angle in [45,135,225,315]:
            a=math.radians(angle)
            slot=cq.Workplane(cq.Plane(origin=(0,60.5,114),normal=(0,-1,0),xDir=(1,0,0))).center(70*math.cos(a),70*math.sin(a)).slot2D(32,12,angle).extrude(4.1).val()
            s=s.cut(slot).fix()
        from vendor import interfaces
        from hardware01 import points
        inf=interfaces()[1]
        for delta in points(inf,'fixed_front_fasteners'):
            s=c.cad.drill(s,np.array(inf['fixed_mm'])+delta+[0,0,114]+np.array(inf['n'])*8,inf['n'],9.8,4.1)
    edges=[e for e in s.Edges() if abs(e.BoundingBox().ymin-front)<1e-5 and abs(e.BoundingBox().ymax-front)<1e-5 and abs(e.BoundingBox().zmin-38)<1e-5 and abs(e.BoundingBox().zmax-38)<1e-5]
    assert len(edges)==1 and abs(edges[0].Length()-110)<1e-5
    new=s.fillet(6,edges);assert new.isValid() and len(new.Solids())==1
    if GUSSET:
        # Two ordinary triangular webs, within the shoulder-foot envelope.
        # No closed cavities or unusual linkage; continuous CNC side access.
        for x in [-53,45]:
            web=cq.Workplane(cq.Plane(origin=(x,0,0),normal=(1,0,0),xDir=(0,1,0))).polyline([(28,37.5),(60.5,37.5),(60.5,68)]).close().extrude(8).val()
            new=new.fuse(web).fix()
        assert new.isValid() and len(new.Solids())==1
        for angle in [225,315]:
            a=math.radians(angle);q=np.array([64*math.cos(a),60.49,114+64*math.sin(a)])
            new=c.cad.drill(new,q,[0,-1,0],9.5,25)
        # Side-root cutter corners of the simple webs, where OCC permits
        # the requestedR3; failure is explicit, never a render-only radius.
        bottom_edges=[e for e in new.Edges() if e.geomType()=='LINE' and abs(e.BoundingBox().zmin-38)<1e-5 and abs(e.BoundingBox().zmax-38)<1e-5 and e.BoundingBox().xlen<1e-5 and any(abs(e.Center().x-x)<1e-5 for x in [-53,-45,45,53]) and e.Length()>10]
        assert len(bottom_edges)==4,len(bottom_edges)
        web_radius=None
        for radius in [3,2.5,2,1.5]:
            try:
                candidate=new.fillet(radius,bottom_edges).fix()
                if candidate.isValid() and len(candidate.Solids())==1:
                    new=candidate;web_radius=radius;break
            except Exception:pass
        assert web_radius is not None,'No valid machinable web root blend; do not issue sharp candidate as CNC-ready'
    id=('A19-S22-shoulder-foot-12mm-R6' if THICK else 'A19-S17-shoulder-foot-R6'+('-webs' if GUSSET else ''));step=OUT/(id+'.step');cq.exporters.export(new,str(step))
    vs,ts=new.tessellate(.05,.12);m=trimesh.Trimesh([v.toTuple() for v in vs],ts,process=True)
    assert m.is_watertight and m.is_winding_consistent and m.volume>0
    bed=m.copy();shift=-bed.bounds[0];bed.apply_translation(shift);bed.export(OUT/(id+'-fit.stl'))
    # A metal CAD candidate includes the cutter-root relief. The plastic file
    # is for supported unpowered fit, not an equivalent rated metal bracket.
    budget=[dict(id=p['id'],owner=p['owner'],frame=p['frame'],mass_kg=p['mass_kg'],com_mm=p['com_mm']) for p in d['parts']]
    for owner,mass,com in [(3,.1,[170,0,11]),(4,.08,[92.5,62,11]),(7,.06,[65,0,0]),(2,.25,[45,-80,0])]:budget.append(dict(id=f'allowance-{owner}',owner=owner,frame=f'J{owner}.rotor',mass_kg=mass,com_mm=com))
    bodies=[p for p in budget if p['frame'].startswith('J') and int(p['frame'][1])>=2]+[dict(id=j['id'],frame=j['id']+'.fixed',mass_kg=j['mass_kg'],com_mm=j['motor_center']) for j in c.L['joints'][1:]]
    q=np.array(list(c.L['poses'].values())+[[j['limits_deg'][0]+f.rs.halton(k,b)*(j['limits_deg'][1]-j['limits_deg'][0]) for j,b in zip(c.L['joints'],[2,3,5,7,11,13,17])] for k in range(1,4097)],float)
    origin=np.array([0,68.5,114.]);loads=[]
    for index,v in enumerate(q):
        frames=f.frames(c.L,v);T=np.linalg.inv(frames['J1.rotor']);force=np.zeros(3);moment=np.zeros(3)
        for p in bodies+[dict(id='flange-payload',frame='flange',mass_kg=3,com_mm=[0,0,0])]:
            xyz=(T@frames[p['frame']]@np.r_[p['com_mm'],1])[:3];G=T[:3,:3]@np.array([0,0,-p['mass_kg']*9.81])
            force+=G;moment+=np.cross(xyz-origin,G)
        loads.append(np.r_[force,moment])
    loads=np.array(loads);indices=set([int(np.argmax(np.linalg.norm(loads[:,3:],axis=1)))])
    indices.update(int(np.argmax(abs(loads[:,i]))) for i in [3,4,5])
    cases=[dict(id=f'gravity-pose-{i}',q_deg=q[i].tolist(),force_N=loads[i,:3].tolist(),moment_Nmm=loads[i,3:].tolist()) for i in sorted(indices)]
    # Independent virtual-work J2 moment audit at a governing case, including
    # fixed J2's eccentric mass: distinguish wrench about mount from J2 torque.
    for case in cases:
        T=f.frames(c.L,case['q_deg']);local_axis=(np.linalg.inv(T['J1.rotor'])@T['J2.fixed'])[:3,:3]@np.array([0,1,0])
        expected=f.torque(c.L,np.array([case['q_deg']]),3,budget)[0,1]
        correction=0.
        J=np.linalg.inv(T['J1.rotor'])
        fixed_bodies=[p for p in bodies if p['frame']=='J2.fixed']
        for p in fixed_bodies:
            xyz=(J@T[p['frame']]@np.r_[p['com_mm'],1])[:3]
            G=J[:3,:3]@np.array([0,0,-p['mass_kg']*9.81])
            correction+=np.dot(np.cross(xyz-origin,G),local_axis)/1000
        error=abs(np.dot(np.array(case['moment_Nmm']),local_axis)/1000-correction+expected)
        case['fixed_J2_weight_axis_moment_Nm']=float(correction);case['J2_gravity_torque_audit_error_Nm']=float(error)
        assert error<1e-8
    b=new.BoundingBox()
    report=dict(revision='A19-ROOT17-CNC-CANDIDATE',layout=c.L,base_context=c.base_context(),part_id=id,source_assembly_sha256=c.sha(path),source_step_sha256=c.sha(src),step_sha256=c.sha(step),step_path=str(step.relative_to(ROOT)),fit_stl_sha256=c.sha(OUT/(id+'-fit.stl')),volume_mm3=new.Volume(),nominal_6061_mass_kg=new.Volume()*2.7e-6,plastic_nominal_mass_kg=new.Volume()*1.27e-6,com_mm=list(new.Center().toTuple()),bbox_mm=[b.xmin,b.ymin,b.zmin,b.xmax,b.ymax,b.zmax],print_translation_mm=shift.tolist(),print_rotation=np.eye(3).tolist(),print_size_mm=bed.extents.tolist(),internal_root_radius_mm=6,remaining_native_and_cover_holes_unchanged=True,mount_origin_J1_rotor_mm=origin.tolist(),sample_count=len(q),gravity_load_cases=cases,material=dict(candidate='6061-T651 certified plate; no weld',E_MPa=68300,poisson_assumption=.33,density_kg_mm3=2.7e-6,typical_E_source='https://online.kaiseraluminum.com/depot/PublicProductInformation/Document/1015/Kaiser_Aluminum_6061_Sheet_Coil_and_Plate.pdf',minimum_strength_certificate_required=True),machining='Single piece with ordinary D12 inside-root cutter fillet; billet and setups are proposed, not vendor DFM approved. Native blind motor threads remain in motor. Preserve all mounting centres.',production_release=False,limits=['Gravity loads only; no motor peak/stops, spring support loads, contact/slip/preload or fatigue.','These are A18 masses. New J5 variant requires fresh loads before integration.','R6 adds material; collision review required before manufacturing pack integration.'])
    report['ordinary_triangular_webs']=dict(count=2,thickness_mm=8,local_x_starts_mm=[-53,45],yz_profile_mm=[[28,37.5],[60.5,37.5],[60.5,68]]) if GUSSET else None
    if GUSSET or THICK:
        oldid='A17-C04-J2-cowl-b';pold=next(p for p in d['parts'] if p['id']==oldid)
        cover=cq.importers.importStep(str(ROOT/pold['step_path'])).val();obstacle=new.translate((0,0,-114))
        for delta in [(0,0,0),(.5,0,0),(-.5,0,0),(0,.5,0),(0,-.5,0),(0,0,.5),(0,0,-.5)]:cover=cover.cut(obstacle.translate(delta)).fix()
        assert cover.isValid() and len(cover.Solids())==1
        cid='A19-C22-J2-cowl-b' if THICK else 'A19-C17-J2-cowl-b';cp=OUT/(cid+'.step');cq.exporters.export(cover,str(cp))
        vs,ts=cover.tessellate(.05,.12);cm=trimesh.Trimesh([v.toTuple() for v in vs],ts,process=True);assert cm.is_watertight and cm.is_winding_consistent and cm.volume>0
        from scipy.spatial.transform import Rotation
        R=Rotation.align_vectors([[0,0,1]],[[0,0,-1]])[0].as_matrix();bed=cm.copy();bed.vertices=bed.vertices@R.T;cs=-bed.bounds[0];bed.apply_translation(cs);bed.export(OUT/(cid+'-fit.stl'))
        report['parts']=[dict(id=id,frame='J1.rotor',owner=1,role='printed_structure',step_path=str(step.relative_to(ROOT)),mass_kg=new.Volume()*1.27e-6,com_mm=list(new.Center().toTuple())),dict(id=cid,frame='J2.fixed',owner=1,role='printed_cover',step_path=str(cp.relative_to(ROOT)),step_sha256=c.sha(cp),mass_kg=cover.Volume()*1.27e-6,com_mm=list(cover.Center().toTuple()),print_rotation=R.tolist(),print_translation_mm=cs.tolist(),print_stl_sha256=c.sha(OUT/(cid+'-fit.stl')))]
        report['replaces_only']=['A16-C04-J2-mount-plate',oldid]
        if GUSSET:report['web_bottom_machined_fillet_mm']=web_radius
        if THICK:
            report['fixed_plate_thickness_mm']=12;report['native_fixed_bolt_stack']='Original M4x12,8mm grip underD9.8 depth4 counterbore,.8mm washer,3.2mm insertion,5mm minimum drawing depth; heads stay at original axial station.'
            report['native_head_counterbores_mm']=dict(diameter=9.8,depth=4,count=10)
    (OUT/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');print('ROOT17',report['nominal_6061_mass_kg'],cases,flush=True)
if __name__=='__main__':main()
