#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""P16-CARRIER-01 independent carrier and J7 study; shared baselines read-only.
Original geometry only is exported. Vendor inputs remain outside the repository.
"""
from pathlib import Path
import argparse,hashlib,itertools,json,math
import numpy as np
import cadquery as cq
import p16_packaging_study as p16
import gripper_root_support_study as st
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/p16-carrier-01'
B,C,union=st.B,st.C,p16.union
P=dict(revision='P16-CARRIER-01',J7_output_plane_head_z_mm=-140.,adapter_front_head_z_mm=-130.,
       central_ring_OD_mm=84.,central_ring_ID_mm=52.,central_ring_thickness_mm=8.,
       housing_OD_mm=48.,bearing_d_D_B_mm=[12.,32.,10.],bearing_centers_u_mm=[19.,29.],
       stem_r_u_mm=[20.,20.],stem_blind_bore_D_mm=14.,base_bracket_extra_thickness_mm=2.,
       base_arm_thickness_mm=8.,steel_root_integral=True,display_keepout_D_mm=64.,display_keepout_depth_mm=12.)


def root_parts(f):
    p,m,crank=p16.root_parts(f)
    for k in ['output_tenon_D10','shoulder_spacer','parallel_key_3x3x8','end_washer_D18','M4x10_end_screw_envelope']:
        del p[k];del m[k]
    # Integral hub/shaft: remove internal M4/key cuts, retain contact/actuation paths in the same steel body.
    hub=union([p.pop('keyed_hub_lower_fork'),C(12,10,(0,-5,0),(0,1,0)),C(6,37,(0,5,0),(0,1,0)),C(8.65,2,(0,12,0),(0,1,0))])
    del m['keyed_hub_lower_fork']
    hub=hub.cut(B(-1.6,1.6,35.8,42.1,-6.1,-4.4)) # nominal MB1 key slot only at unloaded outer thread end
    p['integral_steel_crank_spindle']=hub;m['integral_steel_crank_spindle']='steel'
    for k,u0,u1,r,bore in [('inner_front_spacer',34,36,8.65,12),('MB1',36,37,12.5,12),('KM1',37,41,11,12)]:
        p[k]=C(r,u1-u0,(0,u0,0),(0,1,0),bore);m[k]='steel'
    assert all(s.isValid() and len(s.Solids())==1 for s in p.values())
    return p,m


def base_parts():
    p=p16.base_parts();base=p['base_bracket'].fuse(B(-15,15,-33,-3,-146,-144))
    for x in [-10,10]:
        base=base.cut(C(2.2,8,(x,-18,-146.5),(0,0,1)))
        base=base.cut(C(3.75,4.3,(x,-18,-143.2),(0,0,1)))
        # M4x10, head recessed .2 below top; 7.2mm candidate engagement in carrier.
        p[f'M4_base_bolt_{x}']=C(2,10,(x,-18,-153.2),(0,0,1)).fuse(C(3.5,4,(x,-18,-143.2),(0,0,1)))
    p['base_bracket']=base
    return p


def local_cartridge(f):
    # Body belongs to main carrier; cap is removable from +u. All four bolt heads stay outside sweep.
    body=C(24,22,(0,12,0),(0,1,0));body=body.cut(C(14,2.1,(0,11.95,0),(0,1,0))).cut(C(16,20.1,(0,14,0),(0,1,0)))
    cap=C(24,4,(0,34,0),(0,1,0),27.5).cut(C(15,2.05,(0,36,0),(0,1,0)))
    fast={}
    for j,a in enumerate([45,135,225,315]):
        x,z=20*math.cos(math.radians(a)),20*math.sin(math.radians(a))
        body=body.cut(C(1.5,7.6,(x,26.5,z),(0,1,0)))
        cap=cap.cut(C(1.7,4.2,(x,33.9,z),(0,1,0)))
        fast[f'M3_cap_bolt_{j}']=C(1.5,10,(x,28.5,z),(0,1,0)).fuse(C(2.75,3,(x,38.5,z),(0,1,0)))
        fast[f'M3_cap_washer_{j}']=C(3.5,.5,(x,38,z),(0,1,0),3.4)
    return body,{'bearing_A':C(16,10,(0,24,0),(0,1,0),12),'bearing_B':C(16,10,(0,14,0),(0,1,0),12),'bearing_outer_cap':cap,**fast}


def beam_xy(a,b,width,z,t):
    a,b=np.array(a),np.array(b);d=b-a;L=np.linalg.norm(d);v=d/L;w=np.array([-v[1],v[0]])*width/2
    return cq.Workplane('XY').workplane(offset=z).polyline([tuple(a-w),tuple(b-w),tuple(b+w),tuple(a+w)]).close().extrude(t).val()


def carrier(fingers):
    central=C(42,8,(0,0,-130),(0,0,1),52);parts=[central]+[C(6,8,(x,y,-130),(0,0,1)) for x,y in itertools.product([-35.,35.],[-22.,22.])];holes=[];separate={};module_bodies=[]
    for i,f in enumerate(fingers):
        body,sep=local_cartridge(f);rz=f['root_z_mm'];bottom=min(-154+rz,-130)-rz
        stem=B(-10,10,14,34,bottom,-18)
        # Axially accessible deep blind circular bore; retain 4mm below housing exterior.
        stem=stem.cut(C(7,-28-bottom,(0,24,bottom),(0,0,1)))
        arm=B(-15,15,-33,34,-154,-146)
        for x in [-10,10]:arm=arm.cut(C(2,8.1,(x,-18,-154.05),(0,0,1)))
        module=union([body,stem,arm]);assert len(module.Solids())==1
        world=st.place(module,f,st.SIGNS[i]);parts.append(world);module_bodies.append(world)
        for k,s in sep.items():separate[f['id']+'_'+k]=st.place(s,f,st.SIGNS[i])
        a=math.radians(f['phi_deg']);er=np.array([math.cos(a),math.sin(a)]);u=st.SIGNS[i]*np.array([-math.sin(a),math.cos(a)])
        end=70*er+24*u;start=end/np.linalg.norm(end)*35
        parts.append(beam_xy(start,end,16,-130,8))
    sh=union(parts)
    for x,y in [(30,0),(0,30),(-30,0),(0,-30)]:sh=sh.cut(C(2.25,8.2,(x,y,-130.1),(0,0,1)))
    for x,y in itertools.product([-35.,35.],[-22.,22.]):sh=sh.cut(C(1.7,8.2,(x,y,-130.1),(0,0,1)))
    # Drill AFTER all arm/web unions: otherwise union can seal these nominally accessible blind bores.
    for i,f in enumerate(fingers):
        bottom=min(-154+f['root_z_mm'],-130)-f['root_z_mm']
        sh=sh.cut(st.place(C(7,-28-bottom,(0,24,bottom),(0,0,1)),f,st.SIGNS[i]))
    assert sh.isValid() and len(sh.Solids())==1
    return sh,separate,module_bodies


def J7_adapter():
    # Original MOUNT-01 adapter, in measured output coordinates; no vendor BREP export.
    path=ROOT/'engineering/generated/mount-study/ODR-J7-TOOL-R4.step'
    sh=cq.importers.importStep(str(path)).val().translate((0,0,P['J7_output_plane_head_z_mm']))
    bolts={}
    for i,(x,y) in enumerate([(30,0),(0,30),(-30,0),(0,-30)]):
        bolts[f'J7_to_carrier_M4x16_{i}']=C(2,16,(x,y,-137.2),(0,0,1)).fuse(C(3.5,4,(x,y,-121.2),(0,0,1)))
        bolts[f'J7_M4_washer_{i}']=C(4.5,.8,(x,y,-122),(0,0,1),4.3)
    return sh,bolts


def camera_place(s,sign):
    return s.rotate((0,0,0),(1,0,0),-sign*8).translate((0,sign*50,-14))


def optical_parts():
    # Physical solids stay private; these are original conservative primitive keepouts.
    out={'display_including_candidate_GH_keepout':C(32,12,(0,0,-11),(0,0,1))};m={}
    for sign in [-1,1]:
        # Box covers rear body/fasteners/FAKRA plug, cylindrical front includes actual lens.
        env=union([B(-12.6,12.6,-12.6,12.6,-33.65,0),C(10.1,4.825,(0,0,0),(0,0,1)),C(8.6,9.2,(0,0,4.8),(0,0,1))])
        out[f'camera_{sign}_physical_keepout']=camera_place(env,sign)
        # Entire original female-connector bounding box placed behind male without overlap.
        # Deliberately NOT an asserted mating registration; full rear length conservative.
        out[f'camera_{sign}_FAKRA_unmated_reservation']=camera_place(B(-4.22,9.79,-11.16,3.05,-59.85,-33.65),sign)
        plate=B(-16,16,-15,15,0,4).cut(C(10.25,4.2,(0,0,-.1),(0,0,1)))
        for x,y in itertools.product([-10.5,10.5],repeat=2):
            plate=plate.cut(C(1.2,4.2,(x,y,-.1),(0,0,1))).cut(C(2.2,2.1,(x,y,2),(0,0,1)))
            key=f'camera_{sign}_M2x6_{x}_{y}'
            out[key]=camera_place(C(1,6,(x,y,-4),(0,0,1)).fuse(C(1.9,2,(x,y,2),(0,0,1))),sign);m[key]='steel'
        out[f'camera_{sign}_front_plate']=camera_place(plate,sign);m[f'camera_{sign}_front_plate']='aluminum'
    # Removable optical front spider; four separate columns. Display itself is only a reservation.
    frame=C(38,4,(0,0,-15),(0,0,1),65)
    for x,y in itertools.product([-35.,35.],[-22.,22.]):
        frame=frame.fuse(beam_xy(np.array([x,y])*.70,[x,y],10,-15,4))
        frame=frame.fuse(C(5,4,(x,y,-15),(0,0,1)))
        frame=frame.cut(C(1.7,4.2,(x,y,-15.1),(0,0,1)))
        # R5 standoff with independent through hole, clamp by M3 tie rod. No invented blind thread.
        k=f'optic_column_{x}_{y}';out[k]=C(5,107,(x,y,-122),(0,0,1),3.4);m[k]='aluminum'
        k=f'optic_M3_tierod_{x}_{y}';out[k]=C(1.5,128,(x,y,-135),(0,0,1));m[k]='steel'
        for end,z in [('rear',-130.5),('front',-11.)]:
            k=f'optic_M3_washer_{end}_{x}_{y}';out[k]=C(3.5,.5,(x,y,z),(0,0,1),3.2);m[k]='steel'
            zz=z-2.4 if end=='rear' else z+.5
            k=f'optic_M3_nut_{end}_{x}_{y}';out[k]=cq.Workplane('XY').workplane(offset=zz).center(x,y).polygon(6,5.5/math.cos(math.pi/6)).extrude(2.4).val().cut(C(1.5,2.6,(x,y,zz-.1),(0,0,1)));m[k]='steel'
    # Camera plate tabs attached by original side brackets to two optical columns per camera.
    # Each side bracket remains behind camera front plane and meets its native plate side at x=+-19.
    for sign in [-1,1]:
        for sx in [-1,1]:
            # Beam at -15..-11 reaches a lug on front plate; small local overlap is metal union.
            a=[sx*35.,sign*22.];b=[sx*15.,sign*50.]
            frame=frame.fuse(beam_xy(a,b,6,-15,4))
        # Integrate the front plates into this single removable optical frame; four M2 holes remain.
        frame=frame.fuse(out.pop(f'camera_{sign}_front_plate'));del m[f'camera_{sign}_front_plate']
    for sign in [-1,1]:frame=frame.cut(out[f'camera_{sign}_physical_keepout'])
    for x,y in itertools.product([-35.,35.],[-22.,22.]):frame=frame.cut(C(1.7,4.2,(x,y,-15.1),(0,0,1)))
    assert frame.isValid() and len(frame.Solids())==1
    out['removable_optical_frame']=frame;m['removable_optical_frame']='aluminum'
    return out,m


def optical_keepouts():return optical_parts()[0]

def nominal():
    f=json.loads((ROOT/'engineering/generated/contact02-study/study.json').read_text())['fingers']
    roots=[root_parts(x) for x in f];base=base_parts();car,sep,mods=carrier(f);ad,bolts=J7_adapter();opt,om=optical_parts()
    fixed={'main_carrier':car,'J7_existing_adapter':ad,**sep,**bolts,**opt}
    for i,ff in enumerate(f):
        for k,s in base.items():fixed[ff['id']+'_'+k]=st.place(s,ff,st.SIGNS[i])
    return f,roots,base,fixed,mods,om


def collisions(rows):
    hits=[];n=0
    for (a,sa),(b,sb) in itertools.combinations(rows,2):
        if st.gap_bounds(st.bb(sa),st.bb(sb))>1e-5:continue
        n+=1;v=sa.intersect(sb).Volume()
        if v>1e-4:
            intended=((a=='J7_existing_adapter' and b.startswith('J7_to_carrier_')) or ('physical_keepout' in a and b.startswith(a.split('_physical')[0]+'_M2x6')))
            hits.append(dict(a=a,b=b,volume_mm3=v,intended_nominal_thread_or_envelope_interface=intended))
    return dict(boolean_count=n,positive_intersections=hits,passes=all(x['intended_nominal_thread_or_envelope_interface'] for x in hits))


class FastSet:
    """Exact distance with AABB lower-bound pruning, never sampled mesh distance."""
    def __init__(self,shapes):
        self.shapes=list(shapes);self.boxes=np.array([st.bb(s) for s in self.shapes])
    def distance(self,other):
        lo=np.maximum(self.boxes[:,None,0,:]-other.boxes[None,:,1,:],other.boxes[None,:,0,:]-self.boxes[:,None,1,:])
        bounds=np.linalg.norm(np.maximum(lo,0),axis=2);best=float('inf')
        for index in np.argsort(bounds,axis=None):
            i,j=np.unravel_index(index,bounds.shape)
            if bounds[i,j]>=best-1e-10:break
            best=min(best,self.shapes[i].distance(other.shapes[j]))
        return best


def run_motion(f,roots,base,fixed):
    # Read prior proofs only for unchanged actuator interfaces; recompute ALL global fixed obstacles.
    prior=json.loads((ROOT/'engineering/generated/p16-packaging-study/study.json').read_text())
    result={};beta=26*(123+26)/p16.kin(0)[2]**2;Vact=26+160*beta
    car,sep,modules=carrier(f)
    # Smooth coaxial superset contains own housing, cap and cap screws. Exact rotational invariance.
    shell=union([C(24,2,(0,12,0),(0,1,0),28),C(24,20,(0,14,0),(0,1,0),32),C(24,2,(0,34,0),(0,1,0),27.5),C(24,5.5,(0,36,0),(0,1,0),30)])
    for i in [0,2]:
        ff=f[i];rr=st.comp(roots[i][0].values());hi=ff['closure_study_deg']
        localgap=rr.distance(shell);assert localgap>1e-5
        # Wide blade positive-r edge exceeds housingR24,z0..6; q in0..122 => z>=0. Other roots u<=12 except circular spindle hardware.
        blade=roots[i][0]['metal_blade_with_narrow_tongue'];blade_wide=blade.intersect(B(-200,200,14,100,-20,20))
        bb=st.bb(blade_wide);assert bb[0][0]>24 and bb[0][2]>=-1e-7
        moving_other=[s for k,s in roots[i][0].items() if k!='metal_blade_with_narrow_tongue']
        # Component-wise continuous z minima (sin/cos extrema plus endpoints) prove rear-stem separation.
        positive_u=[s.intersect(B(-1000,1000,14,1000,-1000,1000)) for s in moving_other if st.bb(s)[1][1]>=14]
        points=np.concatenate([p16.pts(s) for s in positive_u if s.Volume()>1e-6]);zmins=[]
        for x,u,z in points:
            qs=[0,math.radians(hi)]+[v for v in [math.atan2(x,z)+math.pi,math.atan2(x,z)-math.pi] if 0<v<math.radians(hi)]
            if u>=14-1e-8:zmins.append(min(x*math.sin(v)+z*math.cos(v) for v in qs))
        zm=min(zmins) if zmins else float('inf');assert zm>-18
        result[ff['id']+'_own_carrier_analytic']=dict(certified=True,coaxial_shell_minimum_gap_mm=localgap,method='Own support shell is a rotationally invariant conservative superset, including cap and cap screw envelopes; exact distance at q0 is valid throughout range.',stem_proof=dict(wide_blade_xmin_mm=float(bb[0][0]),wide_blade_zmin_through_motion_mm=0,other_positive_u_rotor_zmin_mm=zm,stem_zmax_mm=-18,actuator_u_max_mm=-7.9,stem_u_min_mm=14),base_arm_z_range_mm=[-154,-146],base_arm_proof='Existing continuous base-bridge proof has its obstacle top at -139, and new arm is farther rearward. Pins and rolling contact are separate intended interfaces.')
        othercar=car.cut(modules[i]);fixed_without_own={k:s for k,s in fixed.items() if k!='main_carrier' and not (k.startswith(ff['id']+'_bearing_') or k.startswith(ff['id']+'_M3_cap_'))}
        allfixed=FastSet([othercar,*fixed_without_own.values()])
        result[ff['id']+'_moving_vs_other_fixed']=p16.certificate(lambda q:FastSet([st.place(s,ff,st.SIGNS[i],q) for s in roots[i][0].values()]),lambda q:allfixed,p16.radius(rr),hi,step=2)
        print('motion root',ff['id'],result[ff['id']+'_moving_vs_other_fixed']['certified'],flush=True)
        obstacles=FastSet([othercar,*[s for k,s in fixed_without_own.items() if not k.startswith(ff['id']+'_base_')]])
        result[ff['id']+'_actuator_vs_other_fixed']=p16.certificate(lambda q:FastSet([st.place(s,ff,st.SIGNS[i]) for s in p16.envelopes(q).values()]),lambda q:obstacles,Vact,hi,step=2)
        print('motion actuator',ff['id'],result[ff['id']+'_actuator_vs_other_fixed']['certified'],flush=True)
    asymmetric=FastSet([s for k,s in fixed.items() if k=='J7_existing_adapter' or 'FAKRA_unmated' in k])
    for i in [1,3]:
        ff=f[i];hi=ff['closure_study_deg'];rr=st.comp(roots[i][0].values())
        result[ff['id']+'_asymmetric_fixed_root']=p16.certificate(lambda q:FastSet([st.place(s,ff,st.SIGNS[i],q) for s in roots[i][0].values()]),lambda q:asymmetric,p16.radius(rr),hi,step=2)
        result[ff['id']+'_asymmetric_fixed_actuator']=p16.certificate(lambda q:FastSet([st.place(s,ff,st.SIGNS[i]) for s in p16.envelopes(q).values()]),lambda q:asymmetric,Vact,hi,step=2)
    result['mirror_scope']='UR maps to UL and LL to LR under x reflection for all new fixed original carrier/optic/fastener geometry. J7 adapter asymmetric hole pattern and offset FAKRA reservations checked separately for UL/LR.'
    # Full shaft housing is fixed/common; independent roots and actuators use coordinate separated ranges.
    cart=local_cartridge(f[0])[1]
    result['four_independent_modules']=p16.four_way(f,[x[0] for x in roots],base,cart)
    result['unchanged_interfaces']=dict(source='engineering/generated/p16-packaging-study/study.json',source_sha256=hashlib.sha256((ROOT/'engineering/generated/p16-packaging-study/study.json').read_bytes()).hexdigest(),retained='P16 case vs crank, guide/slider vs cheeks/bridge, pin native fits; root integral changes are u>=-5 and do not enter negative-u actuator halfspace; base added material is z<=-144. Full new root vs actuator native samples below.',limitations='CONTACT02 distal light surface remains placeholder; parent real LED/GH and soft-pad retention not merged.')
    return result


def native_checks(f,roots,base,fixed):
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    vdir=ROOT.parents[1]/'work/p16-reference';fix,mov,ins,outs=p16.vendor(vdir)
    rows=[]
    for i in [0,2]:
        ff=f[i]
        for q in [0,30,60,90,ff['closure_study_deg']]:
            act=p16.vendor_at(fix,mov,q);rot=st.comp([s for k,s in roots[i][0].items() if not k.startswith('tip_')]).rotate((0,0,0),(0,1,0),-q)
            v=sum(a.intersect(b).Volume() for a in act.Solids() for b in rot.Solids() if st.gap_bounds(st.bb(a),st.bb(b))<1e-6)
            rows.append(dict(finger=ff['id'],q=q,native_P16_vs_new_root_mm3=v,passes=v<1e-4))
    camera_dir=ROOT.parents[1]/'work/p16-carrier-reference';cam=cq.importers.importStep(str(camera_dir/'ZED-X-ONE-S-Fisheye.step')).val();physical=st.comp([s for i,s in enumerate(cam.Solids()) if i not in [7,8]])
    assert len(cam.Solids())==14 and len(physical.Solids())==12
    body=cam.Solids()[11];holes=[]
    for face in body.Faces():
        if face.geomType()!='CYLINDER':continue
        c=BRepAdaptor_Surface(face.wrapped).Cylinder();a=c.Axis();l=a.Location()
        if abs(c.Radius()-.8115)<1e-6 and abs(abs(a.Direction().Z())-1)<1e-7 and abs(abs(l.X())-10.5)<1e-6 and abs(abs(l.Y())-10.5)<1e-6:
            h=[round(l.X(),5),round(l.Y(),5)];
            if h not in holes:holes.append(h)
    assert len(holes)==4
    cams=[]
    for sign in [-1,1]:
        s=camera_place(physical,sign);env=fixed[f'camera_{sign}_physical_keepout'];outside=sum(a.cut(env).Volume() for a in s.Solids());v=sum(a.intersect(fixed['removable_optical_frame']).Volume() for a in s.Solids())
        cams.append(dict(sign=sign,physical_outside_original_envelope_mm3=outside,physical_vs_front_frame_mm3=v,passes=outside<1e-4 and v<1e-4))
    # Native J7 check, excluding intentionally engaged adapter/pilot contacts and M4 adapter threads.
    import mount_interface_study as mi
    models=json.loads((ROOT/'docs/engineering/sources/rh-interface-extraction.json').read_text())['models'];m=next(x for x in models if x['id']=='RH14-N')
    path=ROOT.parents[1]/'work/r4-joints/cad14/RH-14-100-E-N-D/RH-14-100-E-N-D 3D-A0.STEP';j7=mi.load_vendor(path,m).translate((0,0,-140))
    own=st.comp([s for k,s in fixed.items() if k=='main_carrier' or k.startswith('optic_')]);jcheck=mi.collision(own,j7)
    return dict(P16_new_root_samples=rows,camera=dict(physical_solids=12,reference_solids_excluded=[dict(index=7,product='Image plane'),dict(index=8,product='Simple FOV')],physical_bbox_native_mm=[x.tolist() for x in st.bb(physical)],front_hole_minor_axes_xy_mm=holes,front_mount_plane_native_z_mm=0,checks=cams),J7_new_carrier_vs_native=jcheck)


def export(f,roots,fixed,closed):
    name='P16-CARRIER-01-'+('closed' if closed else 'open')+'.step';ass=cq.Assembly(name=name[:-5]);rows=[]
    for k,s in fixed.items():
        ass.add(s,name=k,color=cq.Color(*((.12,.15,.18) if 'camera' in k else (.28,.33,.38) if k=='main_carrier' else (.58,.67,.69))));rows.append((k,s))
    for i,ff in enumerate(f):
        q=ff['closure_study_deg'] if closed else 0.
        for k,s in roots[i][0].items():
            ss=st.place(s,ff,st.SIGNS[i],q);name2=ff['id']+'_'+k;ass.add(ss,name=name2,color=cq.Color(*((1,.65,.12) if 'LED' in k else (.25,.65,.50) if 'pad' in k else (.4,.48,.53))));rows.append((name2,ss))
        for k,s in p16.envelopes(q).items():
            ss=st.place(s,ff,st.SIGNS[i]);name2=ff['id']+'_P16_envelope_'+k;ass.add(ss,name=name2,color=cq.Color(.12,.16,.18));rows.append((name2,ss))
    ass.save(str(OUT/name));rt=cq.importers.importStep(str(OUT/name)).val();assert rt.isValid() and len(rt.Solids())==len(rows)
    return dict(filename=name,valid=True,solid_count=len(rows),roundtrip_volume_delta_mm3=rt.Volume()-sum(s.Volume() for k,s in rows)),rows


def finalize_report(result):
    result['contact02_sha256']=hashlib.sha256((ROOT/'engineering/generated/contact02-study/study.json').read_bytes()).hexdigest()
    prior=json.loads((ROOT/'engineering/generated/p16-packaging-study/study.json').read_text())
    assert result['contact02_sha256']==prior['contact02_sha256'],'Inherited actuator proof needs unchanged CONTACT02 geometry.'
    result['generator_sha256']={name:hashlib.sha256((ROOT/'engineering'/name).read_bytes()).hexdigest() for name in ['p16_carrier_study.py','p16_carrier_review.py','p16_carrier_qa.py','draw_p16_carrier.py']}
    result['whole_wrist_available']=False
    result['warnings']=['Own coaxial nominal clearances0.226345 upper/0.379896 lower do not cover tolerance or elastic displacement; enlarge near-root clearance before manufacturing.','J7 +/-90deg collides with J6; see wrist-cross-check.json.','Real distal lamp stack and paired connector not integrated.']
    if 'motion' in result:
        m=result['motion'];result['local_nominal_finger_motion_passed']=all(v['certified'] for v in m.values() if isinstance(v,dict) and 'certified' in v) and m['four_independent_modules']['all_independent_pairs_certified']
        result['minimum_carrier_clearance_is_nominal_only_mm']=min(m[k]['coaxial_shell_minimum_gap_mm'] for k in ['UR_own_carrier_analytic','LL_own_carrier_analytic'])
    return result


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--skip-motion',action='store_true');ap.add_argument('--skip-vendor',action='store_true');a=ap.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    f,roots,base,fixed,mods,om=nominal();result=dict(revision=P['revision'],parameters=P,baseline_sha256=st.EXPECTED,manufacturing_release=False)
    assert hashlib.sha256((ROOT/'engineering/parameters/r4-layout.json').read_bytes()).hexdigest()==st.EXPECTED
    for closed in [False,True]:
        qa,rows=export(f,roots,fixed,closed);result.setdefault('export_QA',[]).append(qa)
        result.setdefault('rigid_state_checks',[]).append(collisions([(k,s) for k,s in rows if 'P16_envelope' not in k]))
    for n,s in [('main-carrier',fixed['main_carrier']),('removable-optical-frame',fixed['removable_optical_frame']),('integral-steel-root-spindle',roots[0][0]['integral_steel_crank_spindle']),('bearing-outer-cap',local_cartridge(f[0])[1]['bearing_outer_cap']),('base-bracket',base['base_bracket'])]:cq.exporters.export(s,str(OUT/(n+'.step')))
    if not a.skip_vendor:
        result['native_checks']=native_checks(f,roots,base,fixed)
        (OUT/'native-checks.json').write_text(json.dumps(result['native_checks'],indent=2)+'\n');print('native done',flush=True)
    elif (OUT/'native-checks.json').exists():result['native_checks_cached_file']='native-checks.json; final carrier removes internal material only, subset proof in qa.json'
    (OUT/'study-partial.json').write_text(json.dumps(result,indent=2)+'\n')
    if not a.skip_motion:result['motion']=run_motion(f,roots,base,fixed)
    result=finalize_report(result)
    (OUT/'study.json').write_text(json.dumps(result,indent=2)+'\n')
    if 'motion' in result:assert result['local_nominal_finger_motion_passed']
    assert all(x['passes'] for x in result['rigid_state_checks'])
    print('done',flush=True)
if __name__=='__main__':main()
