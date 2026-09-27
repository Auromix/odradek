# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Independent 24mm head extension: original CAD, mass and wrist collision probes."""
from pathlib import Path
import argparse,json,hashlib,itertools,math
import cadquery as cq
import numpy as np
from build_layout import frame,moved
from mount_interface_study import load_vendor
from studies.link_interface_tools import check,cache
from build_link56_study import face_contact
from build_link67_study import load_prior,make_parts,make_hardware
import p16_carrier_study as cs
import p16_packaging_study as p16
import gripper_root_support_study as st
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'engineering/generated/wrist-extension-01'
DELTA=24.;FACE=np.array([0,55,780.]);J6=np.array([0,0,605.]);J7=np.array([0,55,640.])
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def wrist_certificate(f,roots,fixed,new,j6,j7,prior,link67):
    """Continuous head-to-wrist proof using exact containment and support planes.

    It does not certify LINK67/J7 self-motion, upstream links or actual wiring.
    """
    root_rows=[];actuator_rows=[]
    beta=26*(123+26)/p16.kin(0)[2]**2;velocity=26+160*beta
    for i,ff in enumerate(f):
        hi=math.radians(ff['closure_study_deg']);zs=[]
        for n,s in roots[i][0].items():
            vals=[]
            for x,u,z in p16.pts(s):
                angles=[0.,hi]
                a=math.atan2(x,z)
                angles.extend(a+k*math.pi for k in range(-2,3) if 0<a+k*math.pi<hi)
                vals.append(min(x*math.sin(q)+z*math.cos(q) for q in angles))
            zs.append(min(vals))
        root_rows.append({'finger':ff['id'],'zmin_from_head_mm':min(zs)+ff['root_z_mm'],
          'method':'All AABB corners, analytic sinusoidal extrema including endpoints; independent finger interval.'})
        points=np.arange(0,ff['closure_study_deg']+1,1.)
        mins=[min(s.BoundingBox().zmin for s in p16.envelopes(float(q)).values()) for q in points]
        margin=velocity*math.radians(1)/2
        actuator_rows.append({'finger':ff['id'],'sample_count':len(points),'maximum_interval_deg':1,
          'minimum_sample_local_z_mm':min(mins),'hausdorff_margin_mm':margin,
          'zmin_from_head_mm':min(mins)-margin+ff['root_z_mm']})
    # Static parts include the extension; lower adapter and long bolts are
    # proved separately because their seated tips cross the separating plane.
    zstatic=min(s.BoundingBox().zmin for n,s in new.items()
      if n!='J7_existing_adapter' and not n.startswith('J7_to_carrier_')
      and not any(n.startswith(ff['id']+'_P16_envelope_') or n.startswith(ff['id']+'_'+k)
        for ff,rr in zip(f,roots) for k in rr[0]))
    zhead=min(zstatic,*[804+r['zmin_from_head_mm'] for r in root_rows+actuator_rows])
    # Every stationary wrist/forearm object fits a lower half-strip plus an
    # upper semicircle of R42.1 around J6 in XZ. For |q6|<=90°, its support
    # x*sin(q6)+(z-605)*cos(q6) is <=42.1 at every point, irrespective of Y.
    R=42.1
    bound=cs.C(R,300,(0,-200,605),(0,1,0)).fuse(cs.B(-R,R,-200,100,300,605))
    containment={}
    for n,s in {**prior,'J6_native':j6}.items():
        outside=sum(sum(x.Volume() for x in so.cut(bound).Solids()) for so in s.Solids())
        containment[n]={'solid_count':len(s.Solids()),'outside_support_bound_mm3':outside}
    assert all(v['outside_support_bound_mm3']<1e-4 for v in containment.values())
    clearance=zhead-605-R;assert clearance>0
    zother=max(s.BoundingBox().zmax for s in {**link67,'J7_native':j7}.values())
    # Adapter circle / long bolts stay at positive Y for all q7. Rotation about
    # J6(+Y) preserves Y; this avoids the stationary arm for any q6.
    low={n:s for n,s in new.items() if n=='J7_existing_adapter' or n.startswith('J7_to_carrier_')}
    ymax=max(s.BoundingBox().ymax for s in {**prior,'J6_native':j6}.values())
    lowrows={}
    for n,s in low.items():
        b=s.BoundingBox()
        r=35 if n=='J7_existing_adapter' else max(np.hypot(x,y-55) for x,y in itertools.product([b.xmin,b.xmax],[b.ymin,b.ymax]))
        lowrows[n]={'full_q7_sweep_Ymin_mm':55-r,'stationary_Ymax_mm':ymax,'Y_gap_mm':55-r-ymax,
          'Zmin_mm':b.zmin,'L67_Zmax_mm':max(t.BoundingBox().zmax for t in link67.values()),
          'L67_Z_gap_mm':b.zmin-max(t.BoundingBox().zmax for t in link67.values())}
        sweep=cs.C(r,b.zmax-b.zmin,(0,55,b.zmin),(0,0,1))
        outside=sum(x.Volume() for x in s.cut(sweep).Solids())
        lowrows[n]['sweep_containment_outside_mm3']=outside
        lowrows[n]['L67_full_cylindrical_sweep_checks']={k:check(sweep,t) for k,t in link67.items()}
        assert outside<1e-4
    assert all(r['Y_gap_mm']>0 and not any(x['events'] for x in r['L67_full_cylindrical_sweep_checks'].values()) for r in lowrows.values())
    return {'head_to_wrist_certified':True,'q6_interval_deg':[-90,90],'q7_interval_deg':[-90,90],
      'finger_intervals_deg':{ff['id']:[0,ff['closure_study_deg']] for ff in f},
      'root_analytic_z_bounds':root_rows,'actuator_continuous_z_bounds':actuator_rows,
      'actuator_point_speed_mm_per_rad':velocity,'minimum_static_head_Z_mm':zstatic,
      'minimum_head_Z_in_q6_zero_frame_mm':zhead,'stationary_support_radius_mm':R,
      'stationary_containment':containment,'head_to_stationary_arm_lower_bound_mm':clearance,
      'L67_J7_max_Z_mm':zother,'head_to_L67_J7_axial_lower_bound_mm':zhead-zother,
      'low_adapter_and_bolts':lowrows,
      'proof':'Z of the head is unchanged by q7. All independent finger states have Z>=zhead. In the inverse q6 frame, every stationary object has Z<=605+42.1 for |q6|<=90 by the contained half-strip/semicircle support function. The separating-plane distance therefore bounds Euclidean clearance. L67/J7 rotate with q6, leaving their Z separation unchanged. Adapter and bolt exceptions have invariant positive-Y separation from stationary objects; their full circular q7 sweep supersets are contained and checked against every L67 solid. Negative AABB Z gap for the adapter is not treated as a collision or a separation proof.',
      'scope':'Nominal P16-CARRIER01 head parts and original actuator/optical envelopes versus J5/J6/L56 and L67/J7 only; original adapter-to-J7 intended rotor interface retained. Does not certify moving L67/J7 against preceding links, the full arm, tolerances, deformation, actual PCBA, optical retention, harness, armor or object. q6 study baseline is +/-100: outer 10-degree bands remain unqualified, and the baseline file is not changed.'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--rh17-step',required=True,type=Path);ap.add_argument('--rh14-step',required=True,type=Path);args=ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    models={m['id']:m for m in json.loads((ROOT/'docs/engineering/sources/rh-interface-extraction.json').read_text())['models']}
    a,op,fp,T6,T7=make_parts(models['RH17-B']['unified_joint_interface'],models['RH14-N']['unified_joint_interface']);hw,*_=make_hardware(op,fp,T6,T7)
    v17=load_vendor(args.rh17_step,models['RH17-B']);v14=load_vendor(args.rh14_step,models['RH14-N'])
    j6=moved(v17,T6);j7=moved(v14,T7);prior=load_prior(models)
    prior['J5_native']=moved(v17,frame([0,-55,450],[0,0,1]))
    f,roots,base,fixed,mods,om=cs.nominal()
    spacer=cs.C(35,DELTA,(0,0,0),(0,0,1),52)
    for x,y in [(30,0),(0,30),(-30,0),(0,-30)]:spacer=spacer.cut(cs.C(2.25,DELTA+.2,(x,y,-.1),(0,0,1)))
    spacer=spacer.clean();assert spacer.isValid() and len(spacer.Solids())==1
    cq.exporters.export(spacer,str(OUT/'ODR-J7-EXT24.step'));cq.exporters.export(spacer,str(OUT/'ODR-J7-EXT24.stl'),tolerance=.025,angularTolerance=.07)
    oldrows=list(fixed.items())
    for i,ff in enumerate(f):
        oldrows.extend((ff['id']+'_'+k,st.place(s,ff,st.SIGNS[i])) for k,s in roots[i][0].items())
        oldrows.extend((ff['id']+'_P16_envelope_'+k,st.place(s,ff,st.SIGNS[i])) for k,s in p16.envelopes(0).items())
    old=dict(oldrows);new={}
    for n,s in old.items():
        if n=='J7_existing_adapter':new[n]=s.translate(tuple(FACE));continue
        if n.startswith('J7_to_carrier_M4x16_'):
            i=int(n.rsplit('_',1)[1]);x,y=[(30,0),(0,30),(-30,0),(0,-30)][i]
            # Keep the original shank tip; longer shank, catalog max cap and shifted seat.
            new[n.replace('M4x16','M4x40')]=cs.C(2,40,(x,y,-137.2),(0,0,1)).fuse(cs.C(3.61,4,(x,y,-97.2),(0,0,1))).translate(tuple(FACE));continue
        new[n]=s.translate(tuple(FACE+[0,0,DELTA]))
    new['extension24']=spacer.translate((0,55,650))
    checks={};special={n:s for n,s in new.items() if n=='extension24' or 'J7_to_carrier_M4x40_' in n}
    # Full bolts against everyone except their intentional adapter-thread overlap.
    for n,s in special.items():
        for other,t in {**new,'J7_native':j7,'J6_native':j6,**a,**hw,**prior}.items():
            if n==other:continue
            c=check(s,t)
            if n.startswith('J7_to_carrier_') and other=='J7_existing_adapter':
                c['intentional_thread_owner_overlap']=True
            checks[n+'__'+other]=c
    errors={n:r for n,r in checks.items() if r['events'] and not r.get('intentional_thread_owner_overlap')}
    # Axial separation is invariant for any q7; evaluate all original static head
    # parts in the open finger state (not the independently moving finger interval).
    upper={**prior,'J6':j6,'J7':j7,**a,**hw};fixed_max=max(s.BoundingBox().zmax for s in upper.values())
    zmins={n:s.BoundingBox().zmin for n,s in new.items() if n!='J7_existing_adapter' and not n.startswith('J7_to_carrier_')}
    gap=min(zmins.values())-fixed_max
    # Adapter/long-bolt thread tips lie below the separation plane. Their own
    # rotational invariance / swept cylindrical bolt envelope is checked separately.
    rotating_low={n:s for n,s in new.items() if n=='J7_existing_adapter' or n.startswith('J7_to_carrier_')}
    low_sweeps={}
    for n,s in rotating_low.items():
        b=s.BoundingBox();R=max(np.hypot(x,y-55) for x,y in itertools.product([b.xmin,b.xmax],[b.ymin,b.ymax]))
        # Adapter corner-box radius is deliberately conservative; ignore nativeJ7
        # here since MOUNT-01 already distinguishes fixed housing from rotor fit.
        if n=='J7_existing_adapter':continue
        swept=cs.C(R,b.zmax-b.zmin,(0,55,b.zmin),(0,0,1))
        # Do not fill centre and report intended contact as a collision: use an annulus.
        rlo=30-2.01
        swept=swept.cut(cs.C(rlo,b.zmax-b.zmin+.2,(0,55,b.zmin-.1),(0,0,1)))
        low_sweeps[n]={k:check(swept,t) for k,t in upper.items() if k!='J7'}
    # Independent source collision witness retained; full q6 poses are sampled
    # next to reveal whether a q7-only correction is sufficient.
    maincarrier=new['main_carrier'];coarse=[]
    for q6,q7 in itertools.product([-100,-90,-60,-30,0,30,60,90,100],[-90,-45,0,45,90]):
        s=maincarrier.rotate(tuple(J7),tuple(J7+[0,0,1]),q7).rotate(tuple(J6),tuple(J6+[0,1,0]),q6)
        r=check(s,j6);coarse.append({'q6_deg':q6,'q7_deg':q7,**r})
        if r['events']:print('Coarse carrier collision',q6,q7,r['solid_pair_intersection_sum_mm3'],flush=True)
    ledger=json.loads((ROOT/'engineering/generated/p16-carrier-01/review.json').read_text())['mass'];massrows=[]
    for r in ledger['rows']:
        n=r['part'];m=r['mass_g'];c=np.array(r['head_center_mm'])+FACE;method=r['method']
        if n=='J7_existing_adapter':pass
        elif n.startswith('J7_to_carrier_M4x16_'):
            s=new[n.replace('M4x16','M4x40')];m=4.7;c=np.array(s.Center().toTuple());method='Accu SSC-M4-40-12.9 catalog4.7g; COM proxy from maximum primitive envelope';n=n.replace('M4x16','M4x40')
        else:c=c+[0,0,DELTA]
        massrows.append({'part':n,'mass_g':m,'COM_world_mm':c.tolist(),'method':method})
    massrows.append({'part':'extension24','mass_g':spacer.Volume()*.0027,'COM_world_mm':[0,55,662],'method':'original6061volume'})
    total=sum(r['mass_g'] for r in massrows);com=sum(r['mass_g']*np.array(r['COM_world_mm']) for r in massrows)/total
    data={'revision':'WRIST-EXTENSION-01','manufacturing_release':False,'generator_sha256':sha(Path(__file__)),
      'source_hashes':{str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'engineering/p16_carrier_study.py',ROOT/'engineering/generated/p16-carrier-01/review.json',ROOT/'engineering/generated/p16-carrier-01/main-carrier.step',ROOT/'engineering/generated/link67-study/evidence.json']},
      'extension_mm':DELTA,'face_world_mm':(FACE+[0,0,DELTA]).tolist(),'old_example_TCP_world_mm':[0,55,890],'shifted_example_TCP_world_mm':[0,55,914],
      'TCP_note':'A task-dependent contact TCP must be defined separately; this moves the historical example by the same extension, not a universal grasp point.',
      'spacer':{'OD_ID_length_mm':[70,52,24],'clearance_4hole_PCD_mm':[4.5,60],'material_candidate':'6061-T6','mass_g':spacer.Volume()*.0027},
      'mounting_screw_stack':{'size':'M4x40','quantity':4,'part':'Accu SSC-M4-40-12.9','source_url':'https://www.accu.co.uk/metric-cap-head-screws/16030-SSC-M4-40-12-9','accessed':'2026-09-27','free_grip_mm':32.8,'nominal_engagement_mm':7.2,'minimum_thread_length_mm':20,'catalog_mass_g':4.7,'head_max_D_H_mm':[7.22,4],'preload_selected':False},
      'checks':checks,'errors':errors,'q7_axial_separation_open_fingers':{'maximum_upper_fixed_Z_mm':fixed_max,'minimum_extended_head_Z_mm':min(zmins.values()),'minimum_gap_mm':gap,'part_Zmin_mm':zmins,'scope':'q6=0; all q7 by unchanged Z. Finger open pose only; complete independent-finger swept minimum must be added.'},
      'long_bolt_q7_sweeps_to_upper_arm':low_sweeps,'carrier_q6_q7_coarse_samples':coarse,
      'mass':{'modeled_g':total,'increase_vs_carrier01_g':total-ledger['modeled_mass_g'],'COM_proxy_world_mm':com.tolist(),'COM_relative_new_face_mm':(com-FACE-[0,0,DELTA]).tolist(),'rows':massrows,
      'planning_head_mass_range_g':[total+sum(x['mass_g'][i] for x in ledger['unmodeled_budget_items']) for i in [0,1]],'scope':'Adapter is NOT moved; four bolts are replaced and extension added. All other modeled COM proxies translate24mm. Remaining component budgets are unchanged allocations.'}}
    data['contact_areas_mm2']={'adapter_spacer':face_contact(new['J7_existing_adapter'],new['extension24'],[0,55,650],[0,0,1])['shared_planar_face_area_mm2'],
       'spacer_carrier':face_contact(new['extension24'],new['main_carrier'],[0,55,674],[0,0,1])['shared_planar_face_area_mm2']}
    data['continuous_head_to_wrist']=wrist_certificate(f,roots,fixed,new,j6,j7,prior,{**a,**hw})
    for source in ['engineering/generated/p16-carrier-01/study.json','engineering/generated/link56-study/part-placements.json','engineering/p16_packaging_study.py','engineering/gripper_root_support_study.py','engineering/build_link56_study.py','engineering/build_link67_study.py','engineering/studies/link_interface_tools.py']:
        data['source_hashes'][source]=sha(ROOT/source)
    data['private_vendor_hashes']={'RH17':sha(args.rh17_step),'RH14':sha(args.rh14_step)}
    assert not errors and all(not v['events'] for r in low_sweeps.values() for v in r.values())
    (OUT/'study.json').write_text(json.dumps(data,indent=2)+'\n');print('mass',total,'COM',com,'axialgap',gap,'staticerrors',len(errors),flush=True)

if __name__=='__main__':main()
