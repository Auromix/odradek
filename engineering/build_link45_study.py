# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""J4 RH20 to J5 RH17 offset bridge candidate; no manufacturing release."""
import argparse
import csv
import hashlib
import itertools
import json
from pathlib import Path
import cadquery as cq
import numpy as np
import ezdxf
import trimesh
from build_layout import frame,moved
from mount_interface_study import load_vendor,ring,bores
from studies.link_interface_tools import check,cache
from build_link56_study import cylinder,face_contact,projected_edges
from build_link12_study import shape_box
from build_link23_study import inertia_props,strip_screen
ROOT=Path(__file__).resolve().parents[1]
PARAM_SHA='4349d1797b906b67a7bc396fcb84bc439c2d70dd0b337659e552cee293d2dd81'
REV='R4-LINK45-01'
DENSITY=2.7e-6
POST_XV=np.array([[49,21],[-49,21],[-49,-21],[49,-21]],float)


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def make_parts(i20,i17):
    op=np.array([q['xy_mm'] for q in i20['output_holes']['points']]);fp=np.array([q['xy_mm'] for q in i17['fixed_through_holes']['points']])
    T4=frame([0,0,400],[0,-1,0]);T5=frame([0,-55,450],[0,0,1])
    output=ring(46,26,0,6).union(cq.Workplane('XY').rect(116,62).extrude(6))
    output=output.cut(bores([[0,0]],26,-1,8)).cut(bores([[0,0]],27.8,-1,4))
    output=output.union(bores(POST_XV.tolist(),8,6,16))
    for x,v in POST_XV:
        radius=np.hypot(x,v);direction=np.array([x/radius,v/radius,0.])
        rib=cq.Workplane('XZ').polyline([(34.7,6),(radius,6),(radius,22),(34.7,14)]).close().extrude(8,both=True).val()
        output=output.union(moved(rib,frame([0,0,0],[0,0,1],direction)))
    raw=output.val();roots=[e for e in raw.Edges() if e.geomType()=='LINE' and abs(e.Center().z-6)<1e-5 and e.BoundingBox().zlen<1e-5 and e.Length()>5 and abs(e.Center().x)<57.5 and abs(e.Center().y)<30.8]
    assert len(roots)>=4
    output=cq.Workplane(obj=raw.fillet(.8,roots).clean())
    output=output.cut(bores(op.tolist(),1.75,-1,25)).cut(bores(op.tolist(),3.2,4,22)).cut(bores(POST_XV.tolist(),2.5,3,20)).val()
    rear=ring(44,33.8,400.3,14).translate((0,-55,0)).val()
    for x in [-49,49]:
        rear=rear.fuse(shape_box(16,14,58,[x,-29,400]))
        rear=rear.fuse(shape_box(28,18,14,[np.sign(x)*42,-31,407.3]))
    rear=rear.cut(cylinder([0,-55,345],[0,0,1],33.8,100)).clean()
    rear=rear.cut(moved(bores(fp.tolist(),1.25,-50.7,16).val(),T5)).clean()
    for x,v in POST_XV:rear=rear.cut(cylinder([x,-21,400+v],[0,-1,0],3.3,16))
    front=ring(44,30.3,-10.5,4).cut(bores(fp.tolist(),1.75,-11,6)).cut(bores([[37,0],[-37,0],[0,37],[0,-37]],3.1,-11,6)).val()
    assembled={'output_adapter':moved(output,T4),'rear_carrier':rear,'front_ring':moved(front,T5)}
    for n,s in assembled.items():assert s.isValid() and len(s.Solids())==1,(n,s.isValid(),len(s.Solids()))
    return assembled,op,fp,T4,T5


def make_hardware(op,fp,T4,T5):
    full={};free={};tools={};table=[]
    def bolt(name,seat,axis,d,L,H,D,grip,engage,owner,stage,selected=True):
        seat=np.asarray(seat,float);axis=np.asarray(axis,float);head=cylinder(seat,axis,D/2,H)
        full[name]=head.fuse(cylinder(seat,-axis,d/2,L));free[name]=head.fuse(cylinder(seat,-axis,d/2,grip));tools[name]=cylinder(seat+axis*H,axis,3 if d==6 else 2,60)
        table.append({'id':name,'thread':f'M{d}','selected_length_mm':L if selected else None,'modeled_length_mm':L,'seat_world_mm':seat.tolist(),'head_outward_axis':axis.tolist(),'head_D_H_mm':[D,H],'free_grip_mm':grip,'nominal_geometric_engagement_mm':engage,'thread_owner':owner,'stage':stage,'length_selected':selected})
    for i,(x,v) in enumerate(op):bolt(f'OUT_M3_unknown_{i+1}',(T4@np.array([x,v,4,1]))[:3],[0,-1,0],3,7,3,5.68,7,None,'J4',1,False)
    for i,(x,v) in enumerate(POST_XV):bolt(f'POST_M6x30_{i+1}',[x,-36,400+v],[0,-1,0],6,30,6,10.22,14,16,'output_adapter',2)
    for i,(x,y) in enumerate(fp):bolt(f'FIX_M3x40_{i+1}',(T5@np.array([x,y,-6.5,1]))[:3],[0,0,1],3,40,3,5.68,29.2,10.8,'rear_carrier',4)
    return full,free,tools,table


def load_neighbors(models):
    import build_link34_study as l34
    import build_link56_study as l56
    before={};after={}
    for folder,label,target in [('link34-study','L34',before),('link56-study','L56',after)]:
        path=ROOT/'engineering/generated'/folder/'part-placements.json'
        for n,r in json.loads(path.read_text())['instances'].items():target[label+'_'+n]=moved(cq.importers.importStep(str(path.parent/(r['part_id']+'.step'))).val(),np.array(r['T_world_from_part_mm']))
    i20=models['RH20-B']['unified_joint_interface'];i17=models['RH17-B']['unified_joint_interface']
    op20=np.array([q['xy_mm'] for q in i20['output_holes']['points']]);fp20=np.array([q['xy_mm'] for q in i20['fixed_through_holes']['points']]);op17=np.array([q['xy_mm'] for q in i17['output_holes']['points']]);fp17=np.array([q['xy_mm'] for q in i17['fixed_through_holes']['points']])
    before.update({'L34_HW_'+n:s for n,s in l34.hardware(op20,fp20,frame([0,55,220],[0,0,1]),frame([0,0,400],[0,-1,0]))[0].items()})
    after.update({'L56_HW_'+n:s for n,s in l56.make_hardware(op17,fp17,frame([0,-55,450],[0,0,1]),frame([0,0,605],[0,1,0]))[0].items()})
    return before,after


def continuous_originals(a,targets):
    T4=frame([0,0,400],[0,-1,0])
    def out(t):return cq.Workplane('XY').circle(46).extrude(22+t).union(cq.Workplane('XY').rect(116,62).extrude(22+t)).cut(bores([[0,0]],26,-1,24+t)).cut(bores([[0,0]],27.8,-1,4)).val()
    def carrier(t):
        s=cylinder([0,-55,400.3],[0,0,1],44,14).fuse(cylinder([0,-55-t,400.3],[0,0,1],44,14))
        if t:s=s.fuse(shape_box(88,t,14,[0,-55-t/2,407.3]))
        for x in [-49,49]:
            s=s.fuse(shape_box(16,14+t,58,[x,-29-t/2,400]));s=s.fuse(shape_box(28,18+t,14,[np.sign(x)*42,-31-t/2,407.3]))
        return s.clean()
    def front(t):return ring(44,30.3,439.5,4+t).cut(bores([[37,0],[-37,0],[0,37],[0,-37]],3.1,439.4,4.2+t)).translate((0,-55,0)).val()
    result={}
    for name,home,swept,axis,travel in [('output_adapter',moved(out(0),T4),moved(out(120),T4),[0,-1,0],120),('rear_carrier',carrier(0),carrier(120),[0,-1,0],120),('front_ring',front(0),front(140),[0,0,1],140)]:
        assert home.isValid() and swept.isValid();q=a[name].cut(home);volume=abs(q.Volume()) if q.Solids() else 0;assert volume<1e-4,(name,volume)
        result[name]={'home_enclosure_outside_mm3':volume,'axis_world':axis,'travel_mm':travel,'checks':{n:check(swept,s) for n,s in targets[name].items()},'method':'Actual solid Boolean-contained in enlarged profile; prism/capsule covers every bounded translation; nominal only.'}
    return result


def continuous_J5(vendor,targets):
    T5=frame([0,-55,450],[0,0,1]);rear=cylinder([0,0,-102.1],[0,0,1],33.55,66.4);front=cylinder([0,0,-35.7],[0,0,1],42.1,37.8)
    home=moved(rear.fuse(front),T5);swept=moved(rear.fuse(cylinder([0,0,-35.7],[0,0,1],42.1,217.8)),T5);contain=[]
    for i,s in enumerate(vendor.Solids()):
        q=s.cut(home);volume=abs(q.Volume()) if q.Solids() else 0;contain.append({'solid':i,'outside_mm3':volume})
    assert sum(x['outside_mm3'] for x in contain)<1e-4,contain
    return {'containment_per_solid':contain,'travel_world_mm':[0,0,180],'home_local_envelope_mm':{'rear_R':33.55,'rear_z':[-102.1,-35.7],'front_R':42.1,'front_z':[-35.7,2.1]},'swept_front_z_mm':[-35.7,182.1],'checks':{n:check(swept,s) for n,s in targets.items()},'method':'Contained OEM solids plus enlarged coaxial cylinders cover continuous0..180mm insertion.'}


def rotation_proofs(a,v,before,after,hw,table,T4):
    # External candidate is bounded by an axisymmetric stepped volume aroundJ4.
    external={**a,**hw,'J5':v['J5']};internal={};positive=moved(shape_box(300,300,160,[0,0,80]),T4)
    for row in table:
        n=row['id']
        if n.startswith('OUT_'):
            external[n]=hw[n].intersect(positive);internal[n]=hw[n].cut(positive)
    envelope=moved(ring(70,27.8,0,3).val().fuse(cylinder([0,0,3],[0,0,1],70,102)),T4)
    contained=[]
    for n,s in external.items():
        for i,solid in enumerate(s.Solids()):
            q=solid.cut(envelope);vol=abs(q.Volume()) if q.Solids() else 0;contained.append({'id':n,'solid':i,'outside_mm3':vol})
    assert sum(x['outside_mm3'] for x in contained)<1e-4,contained
    internal_env=moved(cylinder([0,0,-3],[0,0,1],32.5,3),T4);internal_containment=[]
    for n,s in internal.items():
        q=s.cut(internal_env);vol=abs(q.Volume()) if q.Solids() else 0;assert vol<1e-4;internal_containment.append({'id':n,'outside_mm3':vol})
    checks={n:check(envelope,s) for n,s in {'J3':v['J3'],'J4':v['J4'],**before}.items()}
    stubchecks={n:check(internal_env,s) for n,s in {'J3':v['J3'],**before}.items()}
    # A generous lowZ central shaft column avoids the entire L45 bridge.
    # It also bounds a possible longer M3 shaft without choosing its length.
    shaft_env=cylinder([0,-55,300],[0,0,1],28.5,150);lowbox=shape_box(400,400,150,[0,-55,375]);q5contain=[]
    moving={**after,'J6':v['J6']}
    for n,s in moving.items():
        low=s.intersect(lowbox)
        if low.Solids():
            q=low.cut(shaft_env);vol=abs(q.Volume()) if q.Solids() else 0;assert vol<1e-4,(n,vol)
            q5contain.append({'id':n,'belowZ450_outside_shaft_column_mm3':vol})
        assert s.BoundingBox().zmin>=300
    fixed={**a,**hw};top=max(s.BoundingBox().zmax for s in fixed.values());assert 450-top>3.4
    q5checks={n:check(shaft_env,s) for n,s in fixed.items()}
    return {'q4':{'angle_deg':[-180,180],'envelope_local_mm':{'outerR':70,'bottom_z':[0,3],'bottom_innerR':27.8,'filled_z':[3,105]},'containment':contained,'checks':checks,'known_internal_M3_stub_containment':internal_containment,'known_internal_M3_stub_external_checks':stubchecks,'scope':'L45 originals/known hardware + J5 OEM housing versus J3/J4/L34. Rotating OEMJ4 internal output threads intentionally excluded; all other axes held in stated common-parent frame. No whole downstream arm claim.'},
      'q5':{'angle_deg':[-180,180],'stationary_L45_maxZ_mm':top,'noncentral_moving_minZ_mm':450,'Z_gap_mm':450-top,'central_shaft_column_world_mm':{'xy':[0,-55],'R':28.5,'z':[300,450]},'belowZ450_containment':q5contain,'column_checks':q5checks,'scope':'L56 originals/known hardware + J6 housing versus L45 originals/hardware. AboveZ450 remains separated at allq5; low shafts stay in rotation-invariant clear column. Commonq4 transform cancels. Does not qualify L56/J6 versus L34 or full-arm simultaneous motion.'}}


def wire_quarter_arc(radius,diameter,azimuth_deg):
    A=np.array([0.,0.,400.]);phi=np.deg2rad(azimuth_deg);direction=np.array([np.cos(phi),0,np.sin(phi)])
    def point(theta):return A+radius*((1-np.cos(theta))*direction-np.sin(theta)*np.array([0.,1.,0.]))
    edge=cq.Edge.makeThreePointArc(cq.Vector(*A),cq.Vector(*point(np.pi/4)),cq.Vector(*point(np.pi/2)));wire=cq.Wire.assembleEdges([edge])
    body=cq.Workplane('XZ',origin=tuple(A)).circle(diameter/2).sweep(cq.Workplane().newObject([wire])).val();assert body.isValid()
    return body,[point(x).tolist() for x in np.linspace(0,np.pi/2,31)]


def wiring_probe(a,v):
    cases=[('single_bend_only_reference',15.,3.1),('Basler_conflicted_dynamic_claim_conditional',34.5,3.45),('Rosenberger_dynamic_radius_reference',75.,3.1)];rows=[]
    for label,R,D in cases:
        for angle in range(0,360,45):
            s,points=wire_quarter_arc(R,D,angle);checks={n:check(s,x) for n,x in {'J4':v['J4'],'J5':v['J5'],**a}.items()}
            rows.append({'case':label,'bend_radius_mm':R,'diameter_mm':D,'bend_plane_azimuth_deg':angle,'centreline_world_mm':points,'checks':checks})
    return {'trial_paths':rows,'status':'Specific initial90degree turns only; not global path search or complete dynamic harness validation','scope':'Exact swept round-wire quarterarcs start on J4 output centre, tangent world-Y; plane azimuth measured from+X toward+Z. Singlecable, connectors and pairedcable/bundle not represented.',
      'sources':{'Rosenberger':'https://www.rosenberger.com/fileadmin/content/headquarter/Downloads/_Other/HySpeedVision_Flyer.pdf','Basler_doc':'https://docs.baslerweb.com/basler-cable-gmsl-fakra-z-1x-f-f','Basler_shop_conflict':'https://www.baslerweb.com/en/shop/cable-gmsl-fakra-z-1x-f-f-3m/'},
      'source_notes':['CurrentRosenberger April2026 booklet describes CG03,3.1mm,R75,3M bends,5M torsion at180deg/m; priorCG02 snapshot isnot silentlyreplaced.','Basler2200002798 documentation movingR34.5 conflicts withofficialshop static; geometrycomparisonconditional only.','R15 is singlebend only and isnot permitted as dynamicradius.','Ø12 OEMholes cannot contain existing113.44mm2 completebundle before margin; centralØ52 candidateplate isnot the system bottleneck.']}


def validate(a,v,before,after,hw,free,tools,table):
    all_shapes={**a,**v,**before,**after};cached={n:cache(s) for n,s in all_shapes.items()};r={'static':{},'hardware':{},'tools':{},'screw_insertion':{},'contacts':{},'motion_samples':[]}
    for x,y in itertools.combinations(cached,2):
        if x not in a and y not in a:continue
        r['static'][x+'__'+y]=check(cached[x],cached[y])
    print('Static complete',flush=True)
    for row in table:
        n=row['id']
        for target,s in cached.items():r['hardware'][n+'__'+target]=check(free[n] if target==row['thread_owner'] else hw[n],s)
        present={1:['output_adapter','J3','J4',*before],2:['output_adapter','rear_carrier','J3','J4',*before],4:[*a,'J3','J4','J5',*before]}[row['stage']]
        targets={x:all_shapes[x] for x in present};targets.update({k:s for k,s in hw.items() if k!=n and next(x['stage'] for x in table if x['id']==k)<=row['stage']})
        seat=np.array(row['seat_world_mm']);axis=np.array(row['head_outward_axis']);d=int(row['thread'][1:]);D,H=row['head_D_H_mm']
        for target,s in targets.items():
            r['tools'][n+'__'+target]=check(tools[n],s);L=row['free_grip_mm'] if target==row['thread_owner'] else row['modeled_length_mm']
            swept=cylinder(seat,axis,D/2,H+60).fuse(cylinder(seat-axis*L,axis,d/2,L+60));r['screw_insertion'][n+'__'+target]=check(swept,s)
    for x,y in itertools.combinations(hw,2):r['hardware'][x+'__'+y]=check(hw[x],hw[y])
    for x,y,o,z in [('J4','output_adapter',[0,0,400],[0,-1,0]),('output_adapter','rear_carrier',[0,-22,400],[0,-1,0]),('rear_carrier','J5',[0,-55,414.3],[0,0,1]),('front_ring','J5',[0,-55,439.5],[0,0,1])]:
        r['contacts'][x+'__'+y]=face_contact(all_shapes[x],all_shapes[y],o,z);assert r['contacts'][x+'__'+y]['shared_planar_face_area_mm2']>10
    early={c+'__'+n:x for c in ['static','hardware','tools','screw_insertion'] for n,x in r[c].items() if x['events']}
    if early:return r
    print('Hardware/tools complete; continuous insertions',flush=True)
    prior={'J3':v['J3'],'J4':v['J4'],**before};outbolts={n:s for n,s in hw.items() if n.startswith('OUT_')};postbolts={n:s for n,s in hw.items() if n.startswith('POST_')}
    stages=[('output_adapter',[0,-1,0],120,prior),('rear_carrier',[0,-1,0],120,{**prior,'output_adapter':a['output_adapter'],**outbolts}),('front_ring',[0,0,1],140,{**prior,'output_adapter':a['output_adapter'],'rear_carrier':a['rear_carrier'],'J5':v['J5'],**outbolts,**postbolts})]
    for name,axis,travel,targets in stages:
        print('Insertion',name,flush=True);distances=sorted(set([0,.1,.5,1,2,*range(5,travel+1,5)]));target={n:cache(s) for n,s in targets.items()};coll=[]
        for distance in distances:
            shape=a[name].translate(tuple(np.array(axis)*distance))
            for n,s in target.items():
                q=check(shape,s)
                if q['events']:coll.append({'distance_mm':distance,'other':n,**q})
        r['motion_samples'].append({'part':name,'axis_world':axis,'distances_mm':distances,'stationary':list(targets),'collisions':coll,'scope':'Boundeddiscrete axialstations, supplemental tocontinuous enclosureproof.'})
    r['continuous_original_insertions']=continuous_originals(a,{n:t for n,axis,travel,t in stages})
    r['continuous_J5_insertion']=continuous_J5(v['J5'],{**prior,'output_adapter':a['output_adapter'],'rear_carrier':a['rear_carrier'],**outbolts,**postbolts})
    r['rotations']=rotation_proofs(a,v,before,after,hw,table,frame([0,0,400],[0,-1,0]))
    print('Wiring path comparisons; expected conflicts are recorded separately',flush=True)
    r['wiring']=wiring_probe(a,v)
    return r


def local_parts(a):
    frames={'output_adapter':frame([0,0,400],[0,-1,0]),'rear_carrier':frame([0,-55,400.3],[0,0,1]),'front_ring':frame([0,-55,439.5],[0,0,1])}
    names={'output_adapter':'ODR-L45-OUT-R4','rear_carrier':'ODR-L45-CARRIER-R4','front_ring':'ODR-L45-FRONT-R4'}
    return {names[n]:moved(s,np.linalg.inv(frames[n])) for n,s in a.items()},frames,names


def load_screen(p,a,op,fp):
    from arm_screening import arm_parameters
    from review_arm_screening import triangle_bounds,reference_states
    G=9.80665;reserve=.15;mass=sum(s.Volume()*DENSITY for s in a.values());com=sum(s.Volume()*DENSITY*np.array(s.Center().toTuple()) for s in a.values())*.001/mass
    other=[];deps={}
    for folder,label,pre,res in [('link12-study','L12',1,.20),('link23-study','L23',2,.15),('link34-study','L34',3,.15),('link56-study','L56',5,.10),('link67-study','L67',6,.10)]:
        path=ROOT/'engineering/generated'/folder/'part-placements.json';deps[str(path.relative_to(ROOT))]=sha(path);data=json.loads(path.read_text())['instances'];m=sum(x['mass_kg_6061'] for x in data.values());c=sum(x['mass_kg_6061']*np.array(x['estimated_COM_world_mm']) for x in data.values())*.001/m
        other.extend({'id':label+'_'+n,'mass_kg':x['mass_kg_6061'],'preceding_joints':pre,'com_home_m':(np.array(x['estimated_COM_world_mm'])*.001).tolist()} for n,x in data.items())
        other.append({'id':label+'_hardware_reserve','mass_kg':res,'preceding_joints':pre,'com_home_m':c.tolist()})
    groups={'post_M6':POST_XV,'output_M3':op,'fixed_M3':fp};coeff={};recovery=0.
    for n,points in groups.items():
        xy=points-points.mean(axis=0);coeff[n]=max(np.linalg.norm(np.linalg.solve(xy.T@xy,r)) for r in xy)
        for angle in np.linspace(0,2*np.pi,721):
            M=np.array([np.cos(angle),np.sin(angle)])*1000;f=xy@np.linalg.solve(xy.T@xy,[-M[1],M[0]]);recovery=max(recovery,float(np.max(abs(np.array([f@xy[:,1],-f@xy[:,0]])-M))))
    assert recovery<1e-8
    local=moved(a['output_adapter'],np.linalg.inv(frame([0,0,400],[0,-1,0])));ribs=[]
    for x,v in POST_XV:
        R=np.hypot(x,v);radial=moved(local,np.linalg.inv(frame([0,0,0],[0,0,1],[x/R,v/R,0])));ribs.append(strip_screen(radial,'X',np.linspace(34.7,R-.1,31),16,2))
    bridge=moved(a['rear_carrier'],np.linalg.inv(frame([0,-31,400.3],[0,0,1])));bstrip=strip_screen(bridge,'X',np.linspace(34,48.9,31),18,2)
    cuts={'J4_output':[0,0,400],'post_group':[0,-22,400],'J5_rear':[0,-55,414.3]};rows=[];rng=np.random.default_rng(4501)
    for label,head,extension in [('HISTORICAL',2.,0),('HISTORICAL',3.5,0),('HISTORICAL',4.,0),('HISTORICAL',4.5,0),('EXT24',4.5,24.)]:
        model=arm_parameters(p,head);old=triangle_bounds(model)[0]
        for b in model['bodies']:
            if b['id'] in ['head_budget','net_object']:b['com_home_m'][2]+=extension*.001
        model['tool_home_transform'][2][3]+=extension*.001
        model['bodies']=[b for b in model['bodies'] if b['id'] not in [f'L{i}_budget' for i in range(1,7)]]+other
        model['bodies'].extend({'id':'L45_'+n,'mass_kg':s.Volume()*DENSITY,'preceding_joints':4,'com_home_m':(np.array(s.Center().toTuple())*.001).tolist()} for n,s in a.items());model['bodies'].append({'id':'L45_hardware_reserve','mass_kg':reserve,'preceding_joints':4,'com_home_m':com.tolist()})
        bounds=triangle_bounds(model)[0];moving=[b for b in model['bodies'] if b['preceding_joints']>=4];W=sum(b['mass_kg'] for b in moving)*G;cutbounds={}
        for cut,origin in cuts.items():
            total=0
            for b in moving:
                n=b['preceding_joints'];points=[np.array(origin)*.001]+[np.array(j['origin_m']) for j in model['joints'][4:n]]+[np.array(b['com_home_m'])];total+=b['mass_kg']*G*np.linalg.norm(np.diff(points,axis=0),axis=1).sum()
            cutbounds[cut]=float(total)
        q=rng.uniform(-np.pi,np.pi,(200,7));Ts,_,_=reference_states(model,q);ratio=0.
        for cut,origin in cuts.items():
            P=np.einsum('nij,j->ni',Ts[:,4,:3,:3],np.array(origin)*.001)+Ts[:,4,:3,3];M=np.zeros((len(q),3))
            for b in moving:
                n=b['preceding_joints'];C=np.einsum('nij,j->ni',Ts[:,n,:3,:3],b['com_home_m'])+Ts[:,n,:3,3];M+=np.cross(C-P,[0,0,-G*b['mass_kg']])
            ratio=max(ratio,float(np.linalg.norm(M,axis=1).max()/cutbounds[cut]))
        assert ratio<=1+1e-12
        uncertainty=G*(head*.05+p['payload_net_kg']*.10);scenarios=[]
        for case,MNm in [('gravity_COM_uncertainty_times1p5',1.5*(max(cutbounds.values())+uncertainty)),('RH20_peak_single_interface_action_only',80.)]:
            F=W*1.5 if case.startswith('gravity') else W;M=MNm*1000;reaction={n:F/len(groups[n])+M*c for n,c in coeff.items()};bridgeforce=F/2+M/(2*49)
            scenarios.append({'id':case,'moment_Nm':MNm,'force_N':F,'equal_stiffness_group_max_external_axial_N':reaction,'rib_actual_strip_MPa':reaction['post_M6']*max(x['stress_per_N_MPa'] for x in ribs),'rib_actual_strip_deflection_mm':reaction['post_M6']*max(x['deflection_per_N_mm'] for x in ribs),'bridge_assumed_side_reaction_N':bridgeforce,'bridge_actual_strip_MPa':bridgeforce*bstrip['stress_per_N_MPa'],'bridge_actual_strip_deflection_mm':bridgeforce*bstrip['deflection_per_N_mm'],'output_friction_total_preload_sensitivity_N':{str(mu):M/(mu*31) for mu in [.08,.15,.2]}})
        rows.append({'branch':label,'head_mass_kg':head,'head_face_home_mm':780+extension,'head_COM_home_mm':[0,55,760+extension],'TCP_home_mm':[0,55,890+extension],'net_object_kg':p['payload_net_kg'],'old_baseline_triangle_all_Nm':old.tolist(),'revised_triangle_all_Nm':bounds.tolist(),'downstream_mass_after_J4_kg':W/G,'cut_gravity_moment_bounds_Nm':cutbounds,'COM_uncertainty_Nm':uncertainty,'independent_200pose_max_moment_over_triangle_ratio':ratio,'scenarios':scenarios})
    return {'original_mass_kg':mass,'hardware_mass_budget_kg':reserve,'total_link45_mass_budget_kg':mass+reserve,'old_L4_budget_kg':p['link_budgets_kg'][3],'preceding_joints':4,'hardware_COM_proxy_m':com.tolist(),'hardware_COM_note':'Reserve at actualmetal weightedCOM, not measuredhardwareCOM','integrated_prior_masses':other,'dependencies_sha256':deps,'material_E_N_mm2':70000,'material_yield_reference_MPa':240,'study_multiplier':1.5,'group_moment_reconstruction_error_Nmm':recovery,'post_group_Sxx_Svv_mm2':np.diag(POST_XV.T@POST_XV).tolist(),'rib_actual_strips':ribs,'bridge_actual_strip':bstrip,'loadcases':rows,
      'L7_budget_semantics':'Retain original0.15kg shortJ7-to-head interface reserve in bothbudgetbranches. Actualhead integration containing adapter+EXT24 mustremove oldL7budget toavoid doublecounting.',
      'EXT24_semantics':'Conditional4.5kg head budget movedtoCOM784 and2kg objectTCP914; face804. Actualadapter exceptions are NOT uniformlytranslated here and requireseparate actualpart mass integration byroot. This isnot that actualheadmass model.',
      'limits':['Allpre>=4 masses included at eachcut, including near-side portions ofownbridge; envelope loading, not exactcut freebody.','Triangle bounds applypointmass/COM assumptions only; OEMrotor split/COM remains proxy.','Actual16mm radialrib strips perfectlyclampedatR34.7; bridge18mm strip clampedatX34. Neither iscompletecontactFEA or conservativewholepart strengthbound.','Bridge F/2+M/(2*49) is equalreaction sensitivity, not complete six-component ring solution.','Outputfriction sensitivity uses assumedmu andmeanR31; no preloadapproval/threadstrip/boltproof or fatigue qualification.','80Nm is separatepureinterface sensitivity, not simultaneousallaxispeak or zero-speedholding.']}


def feature_rows(op,fp):
    rows=[]
    def add(part,label,pts,z,axis,D,depth,thread=''):
        for i,(x,y) in enumerate(pts):rows.append({'part':part,'feature':label,'number':i+1,'x_mm':float(x),'y_mm':float(y),'z_mm':float(z),'axis':axis,'diameter_mm':D,'depth_mm':depth,'thread':thread})
    add('OUT','output clearance',op,0,'+Z',3.5,'through all');add('OUT','cap cavity',op,4,'+Z',6.4,'through all material above4');add('OUT','post flat-bottom pilot',POST_XV,22,'-Z',5,19,'M6x1 effective complete thread17 proposed');add('OUT','centre through',[[0,0]],0,'+Z',52,6);add('OUT','boss recess',[[0,0]],0,'+Z',55.6,3)
    add('CARRIER','fixed M3 tap',fp,0,'+Z',2.5,14,'M3x0.5 through; effectiveengagement requiresqualification')
    for i,(x,v) in enumerate(POST_XV):rows.append({'part':'CARRIER','feature':'M6 clearance','number':i+1,'x_mm':float(x),'y_mm':33.,'z_mm':float(v-.3),'axis':'-Y','diameter_mm':6.6,'depth_mm':14,'thread':''})
    add('FRONT','fixed clearance',fp,0,'+Z',3.5,4);add('FRONT','OEM cap relief',[[37,0],[-37,0],[0,37],[0,-37]],0,'+Z',6.2,4);return rows


def export_original(out,a,op,fp):
    from build_link56_study import projected_edges
    parts,frames,names=local_parts(a);info={};meshes={}
    for name,shape in parts.items():
        assert shape.isValid() and len(shape.Solids())==1
        step=out/(name+'.step');stl=out/(name+'.stl')
        cq.exporters.export(shape,str(step));cq.exporters.export(shape,str(stl),tolerance=.025,angularTolerance=.08)
        reread=cq.importers.importStep(str(step)).val();mesh=trimesh.load_mesh(stl,process=True)
        error=abs(reread.Volume()-shape.Volume());relative=error/shape.Volume()
        assert reread.isValid() and len(reread.Solids())==1 and error<1e-3 and relative<1e-8
        assert mesh.is_watertight and mesh.body_count==1
        info[name]={'valid_single_solid':True,'volume_mm3':shape.Volume(),'step_roundtrip_volume_error_mm3':error,'step_roundtrip_relative_volume_error':relative,'roundtrip_acceptance':'absolute<0.001mm3 AND relative<1e-8; curvedface integral numerical tolerance, not dimensional tolerance','stl_watertight':True,'stl_body_count':1,'sha256':{x.name:sha(x) for x in [step,stl]}}
    # Check inertia units against an analytic rectangularbox, thentranslation invariance.
    box=shape_box(20,30,40,[0,0,0]);known=DENSITY*20*30*40/12*np.diag([30**2+40**2,20**2+40**2,20**2+30**2])*1e-6
    assert np.allclose(inertia_props(box),known,rtol=1e-10,atol=1e-12)
    placements={}
    for n,s in a.items():
        I=np.array(inertia_props(s));assert np.allclose(I,inertia_props(s.translate((123,-56,89))),rtol=1e-7,atol=1e-12)
        R=frames[n][:3,:3]
        placements[n]={'part_id':names[n],'T_world_from_part_mm':frames[n].tolist(),'preceding_joints':4,'estimated_COM_world_mm':list(s.Center().toTuple()),
          'estimated_COM_part_mm':list(parts[names[n]].Center().toTuple()),'mass_kg_6061':s.Volume()*DENSITY,
          'orientation_home':np.eye(3).tolist(),'inertia_com_kg_m2':I.tolist(),'inertia_axes':'world-aligned at home; COM origin','inertia_com_part_kg_m2':(R.T@I@R).tolist()}
    (out/'part-placements.json').write_text(json.dumps({'revision':REV,'parameters_sha256':PARAM_SHA,'density_kg_mm3':DENSITY,'CAD_integral_not_measurement':True,'instances':placements},indent=2)+'\n')
    bases=[np.array([[1,0,0],[0,1,0]]),np.array([[1,0,0],[0,0,1]]),np.array([[0,1,0],[0,0,1]])]
    for name in parts:
        mesh=trimesh.load_mesh(out/(name+'.stl'),process=True);meshes[name]=mesh
        d=ezdxf.new('R2010');d.units=ezdxf.units.MM;ms=d.modelspace()
        for label,basis,offset in zip(['TOP_XY','FRONT_XZ','SIDE_YZ'],bases,[[0,0],[0,-150],[160,-150]]):
            d.layers.new(label)
            for line in projected_edges(mesh,basis):ms.add_line(tuple(line[0]+offset),tuple(line[1]+offset),dxfattribs={'layer':label})
        for row in feature_rows(op,fp):
            if row['part']==name.split('-')[2]:
                if row['axis'] in ['+Z','-Z']:ms.add_circle((row['x_mm'],row['y_mm']),row['diameter_mm']/2)
                if row['axis'] in ['+Y','-Y']:ms.add_circle((row['x_mm'],row['z_mm']-150),row['diameter_mm']/2)
        ms.add_text(name+' / mm / 1:1 MODEL SPACE / CANDIDATE NOT RELEASED',dxfattribs={'height':3}).set_placement((-65,-195))
        ms.add_text('Contour mesh projections are not machining toolpaths. Use PDF, STEP and feature CSV.',dxfattribs={'height':2.5}).set_placement((-65,-203))
        path=out/(name+'.dxf');d.saveas(path);assert not ezdxf.readfile(path).audit().errors;info[name]['sha256'][path.name]=sha(path)
    path=out/'ODR-LINK45-original-assembly.step';cq.exporters.export(cq.Compound.makeCompound(list(a.values())),str(path))
    reread=cq.importers.importStep(str(path)).val();assert reread.isValid() and len(reread.Solids())==3
    rows=feature_rows(op,fp)
    with (out/'hole-features.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    return parts,meshes,info


def bom(out,parts,table):
    base=json.loads((ROOT/'engineering/generated/link23-study/bom.json').read_text());bolts=base['fasteners'][:2]
    bolts[1].update(nominal_grip_mm=29.2,nominal_geometric_engagement_mm=10.8,rear_face_remaining_mm=3.2)
    bolts.append({'part':'OEM outputM3 lengthTBD','quantity':16,'only_known_free_length_modeled_mm':7,'reason':'4mm seat +3mm proven OEMchannel; effective threadstart/end unknown'})
    result={'revision':REV,'original_parts':[{'id':n,'quantity':1,'candidate_material':'6061-T6','mass_kg':s.Volume()*DENSITY} for n,s in parts.items()],'fasteners':bolts,'known_selected_fasteners_catalog_mass_kg':.058,'all_fasteners_mass_budget_kg':.15,'catalog_listing_not_stock_confirmation':True,'preload_selected':False,'no_purchase_made':True,
      'sources':[{'url':'https://www.myactuator.com/downloads-rhseries','documents':['RH20 3D A /2D A p1','RH17 3D-A /2D-A p1'],'vendor_STEP_private':True},base['sources'][1]],'printed_parts':'PLA/PETG unloaded fitonly; separately support actualjoints; no poweredloadtest'}
    (out/'bom.json').write_text(json.dumps(result,indent=2)+'\n')
    with (out/'screw-stacks.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
    return result


def complete(out,font,a,op,fp,result):
    assert not result['errors'],'Resolve mechanical geometry failures before drawingexport'
    parts,meshes,info=export_original(out,a,op,fp);result['load_screening']=load_screen(json.loads((ROOT/'engineering/parameters/r4-layout.json').read_text()),a,op,fp);result['export_checks']=info;result['bom']=bom(out,parts,result['hardware'])
    deps=['engineering/build_layout.py','engineering/build_link12_study.py','engineering/build_link23_study.py','engineering/build_link34_study.py','engineering/build_link56_study.py','engineering/mount_interface_study.py','engineering/studies/link_interface_tools.py','engineering/arm_screening.py','engineering/review_arm_screening.py','engineering/generated/link23-study/bom.json','docs/engineering/sources/rh-interface-extraction.json']
    result['dependency_sha256']={x:sha(ROOT/x) for x in deps};result['dependency_sha256'].update(result['load_screening']['dependencies_sha256']);result['generator_sha256']=sha(Path(__file__))
    import inspect
    result['geometry_function_sha256']=hashlib.sha256(inspect.getsource(make_parts).encode()).hexdigest();result.update(status='Candidate mechanical study; dynamiccable routes unresolved; no manufacturingrelease',manufacturing_release=False,strength_qualified=False,OEM_output_screw_length_frozen=False,internal_wiring_qualified=False)
    result['proposed_tolerances']={'linear_mm':.10,'hole_centres_mm':.05,'contact_flatness_mm':.05,'threads':'6H proposed; notapproved'}
    if font:
        pdf=out/'ODR-LINK45-candidate-dimensions.pdf';make_pdf(pdf,font,a,parts,meshes,result,op,fp);result['pdf_sha256']=sha(pdf)
    (out/'evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print('CandidateoriginalCAD math andPDF complete',flush=True)


def make_pdf(path,font,a,parts,meshes,evidence,op,fp):
    from reportlab.lib.pagesizes import A3,landscape
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor
    from draw_layout import Sheet,TEAL,GRAY
    from pypdf import PdfReader
    pdfmetrics.registerFont(TTFont('L45CN',str(font)));pdf=canvas.Canvas(str(path),pagesize=landscape(A3),pageCompression=1);pdf.setTitle('Odradek J4-J5 bridge candidate - NO RELEASE');pdf.setAuthor('Auromix contributors');s=Sheet(pdf,'L45CN')
    XY=np.array([[1,0,0],[0,1,0]]);XZ=np.array([[1,0,0],[0,0,1]]);YZ=np.array([[0,1,0],[0,0,1]])
    def notes(x,y,lines,size=8.2,step=7):
        for i,t in enumerate(lines):s.text(x,y-i*step,t,size)
    def view(n,basis,origin,scale=1):
        for edge in projected_edges(meshes[n],basis):q=edge*scale+origin;s.line(q[0],q[1],TEAL,.35)
    def dim(a,b,label,off=(0,0)):
        a,b,off=[np.array(x,float) for x in [a,b,off]];s.line(a,a+off,GRAY,.3);s.line(b,b+off,GRAY,.3);s.arrow(a+off,b+off,GRAY,.4);s.arrow(b+off,a+off,GRAY,.4)
        vertical=abs(b[1]-a[1])>abs(b[0]-a[0]);s.text(*((a+b)/2+off+np.array([2,0] if vertical else [0,2])),label,8,GRAY,'left' if vertical else 'center')
    def footer(n):
        s.line((15,16),(405,16),GRAY,.4);s.text(15,10,'mm | 6061-T6候选 | 无载装配 / 结构评审 | 动态内走线未通过 | 未制造放行',8);s.text(405,10,f'{n}/6 | A3横向 | {REV}',8,align='right');pdf.showPage()
    s.header('J4 → J5 偏置承力桥候选','J4=[0,0,400] / -Y；J5=[0,-55,450] / +Z；主轴位置不变。',REV)
    for basis,origin,label in [(XZ,[102,164],'正视XZ / 1.35:1'),(YZ,[353,164],'侧视YZ / 1.35:1')]:
        for shape in a.values():
            vs,fs=shape.tessellate(.1,.1);mesh=trimesh.Trimesh(vertices=[v.toTuple() for v in vs],faces=fs,process=True)
            for edge in projected_edges(mesh,basis):q=(edge-[0,400])*1.35+origin;s.line(q[0],q[1],TEAL,.35)
        s.text(25 if basis is XZ else 223,252,label,9,TEAL)
    notes(20,92,['三件原创：带筋输出板 / 四短柱、整体后环与左右支腿、前压环。','J4输出面Y0；柱端Y-22；腿后面Y-36；后环Z400.3～414.3；固定后接触Z414.3。',
      'J5固定前接触Z439.5，前环厚4到443.5；原厂夹持跨度25.2。','中央Ø52贯通，底面Ø55.6×深3避让Ø55×高2.5凸台；不把大板孔当全线束通道。',
      f'原创金属CAD估重{evidence["load_screening"]["original_mass_kg"]:.6f}kg；紧固件预算0.15kg；全部preceding_joints=4。','主承力零件有实际接触、螺钉和连续装配检查；线缆首弯的明确冲突单列第6页。','原厂CAD仅本地核对，公开STEP/STL只包含原创几何。'],8.3,8)
    footer(1)
    s.header('带筋输出板 / ODR-L45-OUT-R4','局部原点J4输出面；X=世界X，Y=世界Z，Z=世界-Y；孔坐标均为该局部坐标。',REV)
    view('ODR-L45-OUT-R4',XY,[94,184],1.05);view('ODR-L45-OUT-R4',XZ,[94,91],1.05)
    dim([94-58*1.05,184+46*1.05],[94+58*1.05,184+46*1.05],'116',(0,8))
    notes(20,77,['底板：Ø92圆盘并116×62居中矩形，厚6；Ø52通孔。','底面Ø55.6×深3；凸台径向/轴向名义间隙0.30/0.50。','四柱Ø16，X±49/Y±21，局部Z6～22；柱高16。','筋宽16，r34.7/Z14到柱心/Z22，底Z6，根圆角R0.8。','从柱顶向-Z：M6×1，Ø5平底孔深19，拟完整牙17。','上帽头底世界Z415.89，避开侧桥顶414.3，余1.59。'],7.7,7)
    s.text(198,252,'RH20真实PCD62 / 16孔：0°起，每22.5°',9,TEAL)
    for i,(x,y) in enumerate(op):s.text(198+(i//8)*101,238-(i%8)*8.5,f'{i+1:02d} X{x:+8.4f} Y{y:+8.4f}',8)
    notes(198,158,['16×Ø3.5贯通；Ø6.4帽头腔自Z4向上清至全部材料外。','M3头最大Ø5.68×高3，底座Z4；顶部Z7，高出6mm底板。','阶梯孔保留帽头腔到中央Ø52孔最小余肉1.80mm。','底部通孔边到Ø55.6避让孔最小余肉1.45mm。','原厂M3：只建模4mm座厚+3mm已知通道，自由段7。','全长与有效牙起止仍TBD，不能按标称牙深选最终长度。',
      '4×M6×30穿腿14，进入柱16，距离底孔终点还余3。','M6头Ø10.22×高6，5mm内六角；无预紧许可。'],8.1,8)
    footer(2)
    s.header('整体后环与支腿 / ODR-L45-CARRIER-R4','局部原点世界[0,-55,400.3]；XYZ与世界同向；固定后接触面局部Z14。',REV)
    s.text(20,252,'XY / XZ / YZ视图均1:1',8,TEAL);view('ODR-L45-CARRIER-R4',XY,[90,194],1);view('ODR-L45-CARRIER-R4',XZ,[90,111],1);view('ODR-L45-CARRIER-R4',YZ,[229,185],1)
    notes(20,68,['后环OD88 / ID67.6，厚14；环心[X0,Y0]，局部Z0～14。','左右腿16×14×58：中心[±49,26,-0.3]。','左右侧桥28×18×14：中心[±42,24,7]；中央Ø67.6贯穿避让。','4×Ø6.6：X±49，Z=±21-0.3；从Y33沿-Y穿14。','侧桥顶Z414.3；脚/筋工艺根角与刀具方案需制造复核。'],7.8,7)
    s.text(298,252,'固定PCD74 / 8×M3',9,TEAL)
    for i,(x,y) in enumerate(fp):s.text(298,239-i*9,f'{i+1}: X{x:+8.4f} Y{y:+8.4f}',8)
    notes(286,151,['Ø2.5底孔贯通14，M3×0.5。','8×M3×40由前环穿入。','自由29.2，进入后环10.8。','尖端距离环背面3.2。','后壳Ø67对孔Ø67.6：径向0.30。','M3大径到内孔边1.70。','两侧桥的完整刚度不能由条带代替。'],8,8)
    footer(3)
    s.header('前压环与装配 / ODR-L45-FRONT-R4','局部原点世界[0,-55,439.5]；XYZ与世界同向；环顶世界Z443.5。',REV)
    view('ODR-L45-FRONT-R4',XY,[90,185],1.3);view('ODR-L45-FRONT-R4',XZ,[90,102],1.3)
    dim([90-44*1.3,185+44*1.3],[90+44*1.3,185+44*1.3],'88',(0,7))
    notes(20,78,['OD88 / ID60.6，厚4；8×Ø3.5孔PCD74，孔坐标见第3页。','四个原厂帽头避让孔Ø6.2：PCD74，0/90/180/270°。','可从+Z越过Ø60输出止口；径向名义间隙0.30。','帽头避让孔外缘余肉3.90；非用于精密定位的过盈环。'],8,8)
    notes(193,249,['28个螺钉：12个选长，16个原厂输出长度TBD。','4×Accu SSC-M6-30-12.9，DIN912，12.9 natural。','8×Accu SSC-M3-40-12.9，DIN912，12.9 natural。','M3最短牙18：头下22开始，覆盖拟啮合29.2～40。','目录存在不代表库存；已知12颗目录质量0.058kg。','',
      '装配顺序（J5/J6/L56尚未安装）：','1. OUT从-Y就位，装16×J4输出M3。','2. CARRIER从-Y就位，4×M6×30由-Y拧入柱。','3. J5从+Z插入后环，贴后接触面Z414.3。','4. FRONT从+Z越过输出止口，8×M3×40朝-Z装入。','5. 随后才能安装L56；不能把最后状态当拧紧顺序。','每一零件有连续平移包络和最大5mm离散复核。','已知螺钉另作60mm插入；工具Ø6/M6、Ø4/M3×60。'],8.2,8)
    footer(4)
    s.header('连续运动范围与载荷筛查','本页机械证明范围受限定；不代表整机所有关节组合、内走线和动态保持已验证。',REV)
    case=evidence['load_screening']['loadcases'][-1];c=case['scenarios'][0]
    notes(20,250,['q4：L45外部几何、螺钉和实际J5全部被旋转不变体包含。','局部外R70；Z0～3挖空R27.8，Z3～105为实心保守包络。','对J3/J4及L34逐实体无碰；完整q4一周均由同一体覆盖。','输出M3内部段分列，只检外部支架，不假装验证原厂转子内部。','',
      'q5：L56+J6在Z450以上，与L45最高Z446.5分离3.5。','Z450以下杆段在J5轴R28.5柱内；该柱对L45全部避让。','绕q5保持Z和柱包络；共同q4变换可取消。','不据此证明L56/J6对L34在q4、q5同时转动时无碰。','',
      'J5的34个原厂solid由双圆柱包含，检查+Z连续180mm插入。','后段R33.55，局部Z-102.1～-35.7；前段R42.1到2.1。','三个原创件分别检查-Y120、-Y120、+Z140连续装入。'],8.1,8)
    notes(222,250,['EXT24条件分支：4.5kg头 + 2kg净工件。','face804 / 预算COM784 / TCP914；轴原点不动。','实际adapter例外需用逐件质量重算，未在本预算中冒充实装。','L7原0.15kg接口余量保留；真实整头含adapter时须移除。',
      f'J2 / J4三角界 {case["revised_triangle_all_Nm"][1]:.3f} / {case["revised_triangle_all_Nm"][3]:.3f} Nm。',f'本连接cut最大 {max(case["cut_gravity_moment_bounds_Nm"].values()):.3f} Nm。',f'含COM变化后×1.5研究倍率 {c["moment_Nm"]:.3f} Nm。',f'输出筋实际条带 {c["rib_actual_strip_MPa"]:.2f} MPa。',f'侧桥实际条带 {c["bridge_actual_strip_MPa"]:.2f} MPa。','条带假定完美固支，非整体接触FEA或保守强度界。','80Nm另列单一接口作用，不是零速保持额定。','所有加速度、冲击、疲劳、螺纹剥离与预紧仍需验证。'],8.1,8)
    notes(20,92,['统一候选：6061-T6，E70GPa/目录屈服参考240MPa；批次与厚度需证书。一般±0.10、孔心±0.05、接触平面度0.05、螺纹6H均待评审。','打印：输出板接触面朝床，后环平放加支腿支撑，前环平放。实际关节由外部夹具承托，只做手动无载装入。',
      '未放行项目：原厂有效牙和夹持许可、预紧/防松、材料/公差/工艺、接触与疲劳、线缆完整路径/寿命、轨迹及急停工况。'],8,9)
    footer(5)
    s.header('内走线首弯几何试探：已有明确冲突','仅单根圆线的第一个90°弯；不是完整布线方案。R15只用于静态对照，不能作为动态许可。',REV)
    origin=np.array([165,83]);scale=.9
    def pos(y,z):return origin+np.array([y,z-300])*scale
    def rectangle(y0,y1,z0,z1):
        q=[pos(y0,z0),pos(y1,z0),pos(y1,z1),pos(y0,z1),pos(y0,z0)]
        for u,v in zip(q,q[1:]):s.line(u,v,GRAY,.55)
    rectangle(-88.55,-21.45,347.9,414.3);rectangle(-97.1,-12.9,414.3,452.1)
    colors={15.:TEAL,34.5:'#c57d16',75.:'#c64538'}
    for row in evidence['checks']['wiring']['trial_paths']:
        if row['bend_plane_azimuth_deg']!=270:continue
        pts=np.array([pos(p[1],p[2]) for p in row['centreline_world_mm']]);color=colors[row['bend_radius_mm']]
        for u,v in zip(pts,pts[1:]):s.line(u,v,color,row['diameter_mm']*scale*.65)
        s.text(pts[-1,0]-5,pts[-1,1]-8,f'R{row["bend_radius_mm"]:g}',9,color)
    s.text(26,248,'YZ正交示意 / 0.9:1；灰线是J5保守包络',9,TEAL);s.text(169,176,'J4出线点',8);s.text(63,223,'J5',9,GRAY)
    notes(210,248,['实际CAD检查：8个转弯平面，每45°一个。','R34.5 / Ø3.45：8/8首弯都撞真实J5。','R75 / Ø3.1：8/8首弯都撞真实J5。','R15 / Ø3.1：仅225/270/315°三条首弯无碰。','这些结果只否定指定弯路，不是全空间不可达证明。','',
      'Basler2200002798文档声称动态R34.5/5M。','同料号商店写static，资料冲突；本页仅条件几何对照。','Rosenberger现行April2026文件CG03列R75。','旧CG02记录保留，不能混合不同版本的寿命条件。','',
      '关节原厂通孔Ø12才是系统瓶颈，不是板上的Ø52。','既有整束毛面积113.44mm² > Ø12孔113.10mm²。','需要独立、可拆侧腔/转接路线和端接顺序。','FAKRA外壳、线束固定点、复合弯扭和全行程仍未建模。'],8.1,8)
    notes(20,68,['图中向下270°首弯用于对比：橙/红首弯进入J5后壳；真实交集体积和24条中心线存于evidence.json。','完整线束尚未合格；不将支架存在中央孔或单条静态弯曲成功写成“内走线完成”。','来源：Basler产品文档与同料号商店；Rosenberger HySpeedVision官方2026资料。完整URL与版本说明见配套Markdown/JSON。'],8.2,8)
    footer(6);pdf.save();r=PdfReader(path);assert len(r.pages)==6 and all(len(p.extract_text())>150 for p in r.pages)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--rh20-step',required=True,type=Path);ap.add_argument('--rh17-step',required=True,type=Path);ap.add_argument('--out',type=Path,default=ROOT/'engineering/generated/link45-study');ap.add_argument('--private-assembly',type=Path);ap.add_argument('--font',type=Path);ap.add_argument('--geometry-only',action='store_true');args=ap.parse_args()
    assert sha(ROOT/'engineering/parameters/r4-layout.json')==PARAM_SHA
    models={q['id']:q for q in json.loads((ROOT/'docs/engineering/sources/rh-interface-extraction.json').read_text())['models']}
    a,op,fp,T4,T5=make_parts(models['RH20-B']['unified_joint_interface'],models['RH17-B']['unified_joint_interface']);v20=load_vendor(args.rh20_step,models['RH20-B']);v17=load_vendor(args.rh17_step,models['RH17-B'])
    v={'J3':moved(v20,frame([0,55,220],[0,0,1])),'J4':moved(v20,T4),'J5':moved(v17,T5),'J6':moved(v17,frame([0,0,605],[0,1,0]))}
    before,after=load_neighbors(models);hw,free,tools,table=make_hardware(op,fp,T4,T5);checks=validate(a,v,before,after,hw,free,tools,table)
    errors={c+'__'+k:x for c in ['static','hardware','tools','screw_insertion'] for k,x in checks[c].items() if x['events']}
    errors.update({'motion__'+x['part']:x for x in checks['motion_samples'] if x['collisions']})
    errors.update({'continuous_J5__'+n:x for n,x in checks.get('continuous_J5_insertion',{}).get('checks',{}).items() if x['events']})
    errors.update({'continuous_original__'+n+'__'+k:x for n,q in checks.get('continuous_original_insertions',{}).items() for k,x in q['checks'].items() if x['events']})
    for branch,key in [('q4','checks'),('q4','known_internal_M3_stub_external_checks'),('q5','column_checks')]:
        errors.update({'rotation__'+branch+'__'+key+'__'+n:x for n,x in checks.get('rotations',{}).get(branch,{}).get(key,{}).items() if x['events']})
    result={'revision':REV,'status':'geometry probe only','parameters_sha256':PARAM_SHA,'mass_kg_6061':{n:s.Volume()*DENSITY for n,s in a.items()},'checks':checks,'errors':errors,'hardware':table,'source_vendor_sha256':{'RH20-B':sha(args.rh20_step),'RH17-B':sha(args.rh17_step)}}
    args.out.mkdir(exist_ok=True,parents=True);(args.out/'geometry-probe.json').write_text(json.dumps(result,indent=2)+'\n')
    if args.private_assembly:
        path=args.private_assembly.resolve();assert ROOT not in path.parents;path.parent.mkdir(exist_ok=True,parents=True);cq.exporters.export(cq.Compound.makeCompound(list({**a,**v,**before,**after,**hw}.values())),str(path))
    print(json.dumps({'mass':result['mass_kg_6061'],'errors':errors},indent=2),flush=True)
    if not args.geometry_only:complete(args.out,args.font,a,op,fp,result)


if __name__=='__main__':main()
