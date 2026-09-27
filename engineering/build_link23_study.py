# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""J2-to-J3 metal link candidate, no manufacturing or load qualification."""
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
from build_link56_study import cylinder,face_contact
from build_link12_study import shape_box
ROOT=Path(__file__).resolve().parents[1]
PARAM_SHA='4349d1797b906b67a7bc396fcb84bc439c2d70dd0b337659e552cee293d2dd81'
REV='R4-LINK23-01'
DENSITY=2.7e-6
POST_XV=np.array([[57,20],[-57,20],[-57,-20],[57,-20]],dtype=float)


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def make_parts(i25,i20):
    op=np.array([q['xy_mm'] for q in i25['output_holes']['points']]);fp=np.array([q['xy_mm'] for q in i20['fixed_through_holes']['points']])
    T2=frame([0,0,170],[0,1,0]);T3=frame([0,55,220],[0,0,1])
    output=ring(56,33,0,6).union(cq.Workplane('XY').rect(132,64).extrude(6))
    output=output.cut(bores([[0,0]],33,-1,8)).cut(bores([[0,0]],34.8,-1,3.5))
    output=output.union(bores(POST_XV.tolist(),8,6,16))
    for x,v in POST_XV:
        radius=np.hypot(x,v);direction=np.array([x/radius,v/radius,0.])
        rib=cq.Workplane('XZ').polyline([(35,6),(radius,6),(radius,22),(35,14)]).close().extrude(8,both=True).val()
        output=output.union(moved(rib,frame([0,0,0],[0,0,1],direction)))
    raw=output.val();roots=[e for e in raw.Edges() if e.geomType()=='LINE' and abs(e.Center().z-6)<1e-5 and e.BoundingBox().zlen<1e-5 and e.Length()>5 and abs(e.Center().x)<65 and abs(e.Center().y)<31.8]
    output=cq.Workplane(obj=raw.fillet(.8,roots).clean())
    output=output.cut(bores(op.tolist(),2.25,-1,25)).cut(bores(op.tolist(),3.9,4,22))
    # Flat-bottom pilot19mm from column end22; leaves3mm base below blind hole.
    output=output.cut(bores(POST_XV.tolist(),2.5,3,20)).val()
    rear=ring(50,39.3,168.5,14).translate((0,55,0)).val()
    for x in [-57,57]:
        rear=rear.fuse(shape_box(16,14,56,[x,29,170]))
        rear=rear.fuse(shape_box(30,18,14,[np.sign(x)*50,31,175.5]))
    rear=rear.cut(cylinder([0,55,125],[0,0,1],39.3,100)).clean()
    rear=rear.cut(moved(bores(fp.tolist(),1.25,-52.5,16).val(),T3)).clean()
    for x,v in POST_XV:rear=rear.cut(cylinder([x,21,170-v],[0,1,0],3.3,16))
    front=ring(46,35.3,-11.5,4).cut(bores(fp.tolist(),1.75,-12,6))
    front=front.cut(bores([[42,0],[-42,0],[0,42],[0,-42]],3.1,-12,6)).val()
    assembled={'output_adapter':moved(output,T2),'rear_carrier':rear,'front_ring':moved(front,T3)}
    for n,s in assembled.items():assert s.isValid() and len(s.Solids())==1,(n,s.isValid(),len(s.Solids()))
    return assembled,op,fp,T2,T3


def make_hardware(op,fp,T2,T3):
    full={};free={};tools={};table=[]
    def bolt(name,seat,axis,d,L,H,D,grip,engage,owner,stage,selected=True):
        seat=np.asarray(seat,float);axis=np.asarray(axis,float)
        head=cylinder(seat,axis,D/2,H)
        full[name]=head.fuse(cylinder(seat,-axis,d/2,L))
        free[name]=head.fuse(cylinder(seat,-axis,d/2,grip))
        tools[name]=cylinder(seat+axis*H,axis,3 if d==6 else (2.5 if d==4 else 2),60)
        table.append({'id':name,'thread':f'M{d}','selected_length_mm':L if selected else None,
          'modeled_length_mm':L,'seat_world_mm':seat.tolist(),'head_outward_axis':axis.tolist(),
          'head_D_H_mm':[D,H],'free_grip_mm':grip,'nominal_geometric_engagement_mm':engage,
          'thread_owner':owner,'stage':stage,'length_selected':selected})
    for i,(x,v) in enumerate(op):
        bolt(f'OUT_M4_unknown_{i+1}',(T2@np.array([x,v,4,1]))[:3],[0,1,0],4,7.5,4,7.22,7.5,None,'J2',1,False)
    for i,(x,v) in enumerate(POST_XV):
        bolt(f'POST_M6x30_{i+1}',[x,36,170-v],[0,1,0],6,30,6,10.22,14,16,'output_adapter',2)
    for i,(x,y) in enumerate(fp):
        bolt(f'FIX_M3x40_{i+1}',(T3@np.array([x,y,-7.5,1]))[:3],[0,0,1],3,40,3,5.68,30,10,'rear_carrier',4)
    return full,free,tools,table


def continuous_J3_insertion(vendor,stationary):
    T=frame([0,55,220],[0,0,1])
    rear=cylinder([0,0,-95],[0,0,1],39.05,57.5)
    front=cylinder([0,0,-37.5],[0,0,1],45.05,40.1)
    envelope=moved(rear.fuse(front),T)
    containment=[]
    for i,s in enumerate(vendor.Solids()):
        d=s.cut(envelope);v=abs(d.Volume()) if d.Solids() else 0
        containment.append({'vendor_solid_index':i,'outside_envelope_mm3':v})
    total=sum(r['outside_envelope_mm3'] for r in containment)
    assert total<1e-4,('J3 conservative envelope must contain actual solids',total)
    sweep=moved(rear.fuse(cylinder([0,0,-37.5],[0,0,1],45.05,220.1)),T)
    return {'containment_per_solid':containment,'total_outside_envelope_mm3':total,
      'home_joint_frame_envelope_mm':{'rear_R':39.05,'rear_z':[-95,-37.5],'front_R':45.05,'front_z':[-37.5,2.6]},
      'continuous_travel_world_mm':[0,0,180],
      'swept_joint_frame_envelope_mm':{'rear_R':39.05,'rear_z':[-95,-37.5],'front_R':45.05,'front_z':[-37.5,182.6]},
      'checks':{n:check(sweep,s) for n,s in stationary.items()},
      'method':'Each source solid is contained by Boolean difference; larger front cylinder covers the translated rear interval. Swept enclosing volume covers every translation0..180mm. Nominal CAD only.'}


def continuous_original_insertions(a,stationary_by_part):
    # Enclosures deliberately omit holes exceptwhere the outputboss requires
    # itslower pocket. Each entire originalsolid must be contained in its
    # home enclosure before using the continuous swept enclosure.
    T=frame([0,0,170],[0,1,0]);result={}
    def out_profile(height):return cq.Workplane('XY').circle(56).extrude(height).union(cq.Workplane('XY').rect(132,64).extrude(height)).cut(bores([[0,0]],33,-1,height+2)).cut(bores([[0,0]],34.8,-1,3.5)).val()
    home_out=moved(out_profile(22),T);swept_out=moved(out_profile(142),T)
    def carrier_enclosure(travel):
        # Outer annulus swept along+Y is contained in thefilled outer capsule.
        s=cylinder([0,55,168.5],[0,0,1],50,14).fuse(cylinder([0,55+travel,168.5],[0,0,1],50,14))
        if travel:s=s.fuse(shape_box(100,travel,14,[0,55+travel/2,175.5]))
        for x in [-57,57]:
            s=s.fuse(shape_box(16,14+travel,56,[x,29+travel/2,170]))
            s=s.fuse(shape_box(30,18+travel,14,[np.sign(x)*50,31+travel/2,175.5]))
        return s.clean()
    home_car=carrier_enclosure(0);swept_car=carrier_enclosure(120)
    home_front=ring(46,35.3,208.5,4).cut(bores([[42,0],[-42,0],[0,42],[0,-42]],3.1,208.4,4.2)).translate((0,55,0)).val()
    swept_front=ring(46,35.3,208.5,144).cut(bores([[42,0],[-42,0],[0,42],[0,-42]],3.1,208.4,144.2)).translate((0,55,0)).val()
    for n,home,swept,axis,travel in [('output_adapter',home_out,swept_out,[0,1,0],120),('rear_carrier',home_car,swept_car,[0,1,0],120),('front_ring',home_front,swept_front,[0,0,1],140)]:
        assert home.isValid() and swept.isValid() and len(home.Solids())==len(swept.Solids())==1
        outside=a[n].cut(home);v=abs(outside.Volume()) if outside.Solids() else 0.
        assert v<1e-4,(n,'not enclosed',v)
        result[n]={'home_enclosure_outside_mm3':v,'continuous_travel_mm':travel,'axis_world':axis,
          'checks':{k:check(swept,s) for k,s in stationary_by_part[n].items()},
          'method':'Boolean-containment of originalsolid plus enclosingprismatic/capsule sweep for every axialtranslation in interval; nominal only',
          'enclosure_definition':{'output_adapter':'J2local extrusion(circleR56 UNION rectangle132x64 MINUS centreR33), height142; bottomz0..2.5 centreR34.8. Baseprojectioncontainscolumnsandribs.',
          'rear_carrier':'worldZ168.5..182.5 filledoutercapsuleR50 centredXY(0,55)to(0,175), plus legs16x134x56 centre(+/-57,89,170), arms30x138x14 centre(+/-50,91,175.5). Removingtheinnerhole only enlarges thebound.',
          'front_ring':'worldXYcentre(0,55), ringR46/R35.3, worldZ208.5..352.5; retain4invariant axialR3.1 OEMcapreliefsonPCD84at0/90/180/270deg' }[n]}
    return result


def load_prior(models):
    import build_link12_study as l12
    path=ROOT/'engineering/generated/link12-study/part-placements.json';data=json.loads(path.read_text());prior={}
    for n,r in data['instances'].items():
        s=cq.importers.importStep(str(path.parent/(r['part_id']+'.step'))).val()
        prior['L12_'+n]=moved(s,np.array(r['T_world_from_part_mm']))
    iface=models['RH25-B']['unified_joint_interface']
    op=np.array([q['xy_mm'] for q in iface['output_holes']['points']]);fp=np.array([q['xy_mm'] for q in iface['fixed_through_holes']['points']])
    hardware=l12.make_hardware(op,fp,frame([0,0,105.2],[0,0,1]),frame([0,0,170],[0,1,0]))[0]
    prior.update({'L12_HW_'+n:s for n,s in hardware.items()})
    return prior


def validate(a,v,prior,hw,free,tools,table):
    all_shapes={**a,**v,**prior};cached={n:cache(s) for n,s in all_shapes.items()}
    r={'static':{},'hardware':{},'tools':{},'screw_insertion':{},'contacts':{},'motion_samples':[]}
    for x,y in itertools.combinations(cached,2):
        if x not in a and y not in a:continue
        r['static'][x+'__'+y]=check(cached[x],cached[y])
    print('Static complete',flush=True)
    for row in table:
        n=row['id']
        for target,s in cached.items():r['hardware'][n+'__'+target]=check(free[n] if target==row['thread_owner'] else hw[n],s)
        present={1:['output_adapter','J1','J2',*prior],2:['output_adapter','rear_carrier','J1','J2',*prior],4:list(cached)}[row['stage']]
        for target in present:
            r['tools'][n+'__'+target]=check(tools[n],cached[target])
            seat=np.array(row['seat_world_mm']);axis=np.array(row['head_outward_axis']);d=int(row['thread'][1:])
            L=row['free_grip_mm'] if target==row['thread_owner'] else row['modeled_length_mm']
            sweep=cylinder(seat,axis,row['head_D_H_mm'][0]/2,row['head_D_H_mm'][1]+60).fuse(cylinder(seat-axis*L,axis,d/2,L+60))
            r['screw_insertion'][n+'__'+target]=check(sweep,cached[target])
        installed={k:s for k,s in hw.items() if next(x['stage'] for x in table if x['id']==k)<=row['stage'] and k!=n}
        for target,s in installed.items():
            r['tools'][n+'__'+target]=check(tools[n],s)
            L=row['modeled_length_mm'];seat=np.array(row['seat_world_mm']);axis=np.array(row['head_outward_axis']);d=int(row['thread'][1:])
            sweep=cylinder(seat,axis,row['head_D_H_mm'][0]/2,row['head_D_H_mm'][1]+60).fuse(cylinder(seat-axis*L,axis,d/2,L+60))
            r['screw_insertion'][n+'__'+target]=check(sweep,s)
    for x,y in itertools.combinations(hw,2):r['hardware'][x+'__'+y]=check(hw[x],hw[y])
    for x,y,o,z in [('J2','output_adapter',[0,0,170],[0,1,0]),('output_adapter','rear_carrier',[0,22,170],[0,1,0]),('rear_carrier','J3',[0,55,182.5],[0,0,1]),('front_ring','J3',[0,55,208.5],[0,0,1])]:
        r['contacts'][x+'__'+y]=face_contact(all_shapes[x],all_shapes[y],o,z)
        assert r['contacts'][x+'__'+y]['shared_planar_face_area_mm2']>10
    early={c+'__'+k:x for c in ['static','hardware','tools','screw_insertion'] for k,x in r[c].items() if x['events']}
    if early:print('Early failures',json.dumps(early,indent=2),flush=True);return r
    print('Hardware/tools complete; insertions',flush=True)
    preceding={'J1':v['J1'],'J2':v['J2'],**prior}
    outbolts={n:s for n,s in hw.items() if n.startswith('OUT_')}
    postbolts={n:s for n,s in hw.items() if n.startswith('POST_')}
    stages=[('output_adapter',a['output_adapter'],[0,1,0],120,preceding),
      ('rear_carrier',a['rear_carrier'],[0,1,0],120,{**preceding,'output_adapter':a['output_adapter'],**outbolts}),
      ('front_ring',a['front_ring'],[0,0,1],140,{**preceding,'output_adapter':a['output_adapter'],'rear_carrier':a['rear_carrier'],'J3':v['J3'],**outbolts,**postbolts})]
    for name,moving,axis,length,targets in stages:
        print('Insertion',name,flush=True);target={k:cache(s) for k,s in targets.items()};collisions=[]
        distances=sorted(set([0,.1,.5,1,2,*range(5,length+1,5)]))
        for d in distances:
            probe=moving.translate(tuple(np.asarray(axis)*d))
            for n,s in target.items():
                c=check(probe,s)
                if c['events']:collisions.append({'distance_mm':d,'other':n,**c})
        r['motion_samples'].append({'part':name,'world_axis':axis,'distances_mm':distances,'collisions':collisions,'stationary':list(targets),
          'scope':'Bounded axial insertion interval checked at stated discrete stations; does not certify between-sample sweep or clearance under tolerance.'})
    r['continuous_original_insertions']=continuous_original_insertions(a,{n:targets for n,mov,axis,travel,targets in stages})
    print('Continuous J3 envelope',flush=True)
    r['continuous_J3_insertion']=continuous_J3_insertion(v['J3'],{**preceding,'output_adapter':a['output_adapter'],'rear_carrier':a['rear_carrier'],**outbolts,**postbolts})
    return r


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--rh25-step',required=True,type=Path);ap.add_argument('--rh20-step',required=True,type=Path)
    ap.add_argument('--out',type=Path,default=ROOT/'engineering/generated/link23-study');ap.add_argument('--private-assembly',type=Path);ap.add_argument('--font',type=Path);ap.add_argument('--geometry-only',action='store_true');args=ap.parse_args()
    assert sha(ROOT/'engineering/parameters/r4-layout.json')==PARAM_SHA
    models={q['id']:q for q in json.loads((ROOT/'docs/engineering/sources/rh-interface-extraction.json').read_text())['models']}
    a,op,fp,T2,T3=make_parts(models['RH25-B']['unified_joint_interface'],models['RH20-B']['unified_joint_interface'])
    v25=load_vendor(args.rh25_step,models['RH25-B']);v20=load_vendor(args.rh20_step,models['RH20-B'])
    v={'J1':moved(v25,frame([0,0,105.2],[0,0,1])),'J2':moved(v25,T2),'J3':moved(v20,T3),'J4':moved(v20,frame([0,0,400],[0,-1,0]))}
    prior=load_prior(models);hw,free,tools,table=make_hardware(op,fp,T2,T3)
    checks=validate(a,v,prior,hw,free,tools,table)
    errors={c+'__'+k:x for c in ['static','hardware','tools','screw_insertion'] for k,x in checks[c].items() if x['events']}
    errors.update({'insertion__'+x['part']:x for x in checks['motion_samples'] if x['collisions']})
    errors.update({'continuous_J3__'+k:x for k,x in checks.get('continuous_J3_insertion',{}).get('checks',{}).items() if x['events']})
    errors.update({'continuous_original__'+part+'__'+k:x for part,proof in checks.get('continuous_original_insertions',{}).items() for k,x in proof['checks'].items() if x['events']})
    result={'revision':REV,'status':'candidate; not manufacturing release','parameters_sha256':PARAM_SHA,'mass_kg_6061':{n:s.Volume()*DENSITY for n,s in a.items()},
      'checks':checks,'errors':errors,'hardware':table,'source_vendor_sha256':{'RH25-B':sha(args.rh25_step),'RH20-B':sha(args.rh20_step)},'vendors_checked':list(v),'existing_L12_geometry_checked':list(prior)}
    args.out.mkdir(exist_ok=True,parents=True);(args.out/'geometry-probe.json').write_text(json.dumps(result,indent=2)+'\n')
    if args.private_assembly:
        path=args.private_assembly.resolve();assert ROOT not in path.parents;path.parent.mkdir(exist_ok=True,parents=True)
        cq.exporters.export(cq.Compound.makeCompound(list({**a,**v,**prior,**hw}.values())),str(path))
    print(json.dumps({'mass':result['mass_kg_6061'],'errors':errors},indent=2),flush=True)
    if not args.geometry_only:complete(args.out,args.font,a,op,fp,result)


def inertia_props(shape):
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
    prop=GProp_GProps();BRepGProp.VolumeProperties_s(shape.wrapped,prop)
    matrix=prop.MatrixOfInertia();I=np.array([[matrix.Value(i+1,j+1) for j in range(3)] for i in range(3)])*DENSITY*1e-6
    assert np.min(np.linalg.eigvalsh(I))>0 and np.allclose(I,I.T)
    return I.tolist()


def local_parts(assembled):
    frames={'output_adapter':frame([0,0,170],[0,1,0]),'rear_carrier':frame([0,55,168.5],[0,0,1]),'front_ring':frame([0,55,208.5],[0,0,1])}
    names={'output_adapter':'ODR-L23-OUT-R4','rear_carrier':'ODR-L23-CARRIER-R4','front_ring':'ODR-L23-FRONT-R4'}
    return {names[n]:moved(s,np.linalg.inv(frames[n])) for n,s in assembled.items()},frames,names


def strip_screen(shape,axis,centres,width,axis_I):
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
    rows=[]
    for x in centres:
        # Strip local beam axisX, breadthY, bending depthZ. Integrate actual BREP.
        sec=shape.intersect(shape_box(.001,width,100,[x,0,15]))
        prop=GProp_GProps();BRepGProp.VolumeProperties_s(sec.wrapped,prop)
        area=prop.Mass()/.001;I=prop.MatrixOfInertia().Value(axis_I,axis_I)/.001-area*.001**2/12
        c=np.array(sec.Center().toTuple());bb=sec.BoundingBox();extent=max(bb.zmax-c[2],c[2]-bb.zmin)
        assert area>0 and I>0
        rows.append({'x_mm':float(x),'area_mm2':area,'Iy_mm4':I,'extreme_z_mm':extent,'slice_solids':len(sec.Solids()),'slice_thickness_mm':.001})
    end=centres[-1]+.1
    return {'samples':rows,'root_mm':float(centres[0]),'load_point_mm':float(end),
      'stress_per_N_MPa':max((end-r['x_mm'])*r['extreme_z_mm']/r['Iy_mm4'] for r in rows),
      'deflection_per_N_mm':float(np.trapezoid([(end-r['x_mm'])**2/(70000*r['Iy_mm4']) for r in rows],[r['x_mm'] for r in rows]))}


def load_screen(p,assembled,op,fp):
    from arm_screening import arm_parameters
    from review_arm_screening import triangle_bounds,reference_states
    G=9.80665;reserve=.15
    mass=sum(s.Volume()*DENSITY for s in assembled.values())
    com=sum(s.Volume()*DENSITY*np.array(s.Center().toTuple()) for s in assembled.values())*.001/mass
    other=[];dependency={}
    for folder,prefix,pre,res in [('link12-study','L12',1,.20),('link56-study','L56',5,.10)]:
        path=ROOT/'engineering/generated'/folder/'part-placements.json';data=json.loads(path.read_text())['instances'];dependency[folder]=sha(path)
        m=sum(r['mass_kg_6061'] for r in data.values());c=sum(r['mass_kg_6061']*np.array(r['estimated_COM_world_mm']) for r in data.values())*.001/m
        for n,r in data.items():other.append({'id':prefix+'_'+n,'mass_kg':r['mass_kg_6061'],'preceding_joints':pre,'com_home_m':(np.array(r['estimated_COM_world_mm'])*.001).tolist()})
        other.append({'id':prefix+'_hardware_reserve','mass_kg':res,'preceding_joints':pre,'com_home_m':c.tolist()})
    groups={'post_M6':POST_XV,'output_M4':op,'fixed_M3':fp}
    coeff={};recovery=0.
    for n,points in groups.items():
        q=points-points.mean(axis=0);coeff[n]=max(np.linalg.norm(np.linalg.solve(q.T@q,r)) for r in q)
        for a in np.linspace(0,2*np.pi,721):
            M=np.array([np.cos(a),np.sin(a)])*1000;force=q@np.linalg.solve(q.T@q,[-M[1],M[0]])
            recovered=np.array([force@q[:,1],-force@q[:,0]])
            recovery=max(recovery,float(np.max(abs(recovered-M))))
    assert recovery<1e-8
    ribs=[]
    T2=frame([0,0,170],[0,1,0]);outlocal=moved(assembled['output_adapter'],np.linalg.inv(T2))
    for x,v in POST_XV:
        R=np.hypot(x,v);local=moved(outlocal,np.linalg.inv(frame([0,0,0],[0,0,1],[x/R,v/R,0])))
        ribs.append(strip_screen(local,'X',np.linspace(42.5,R-.1,31),16,2))
    # Cut an18mm-wide actual bridge strip atworldY22..40, zeroZworld168.5.
    bridge=moved(assembled['rear_carrier'],np.linalg.inv(frame([0,31,168.5],[0,0,1])))
    bridge_sections=strip_screen(bridge,'X',np.linspace(40,56.9,31),18,2)
    cuts={'J2_output':[0,0,170],'post_group':[0,22,170],'J3_rear':[0,55,182.5]}
    def triangle_at_cut(model,origin):
        P=np.array(origin)*.001;total=0.
        for b in model['bodies']:
            n=b['preceding_joints']
            if n<2:continue
            points=[P]+[np.array(j['origin_m']) for j in model['joints'][2:n]]+[np.array(b['com_home_m'])]
            total+=b['mass_kg']*G*np.linalg.norm(np.diff(points,axis=0),axis=1).sum()
        return total
    rows=[];rng=np.random.default_rng(2301)
    for head in [2,3.5,4,4.5]:
        model=arm_parameters(p,head);oldbounds=triangle_bounds(model)[0]
        model['bodies']=[b for b in model['bodies'] if b['id'] not in ['L1_budget','L2_budget','L5_budget']]+other
        for n,s in assembled.items():model['bodies'].append({'id':'L23_'+n,'mass_kg':s.Volume()*DENSITY,'preceding_joints':2,'com_home_m':(np.array(s.Center().toTuple())*.001).tolist()})
        model['bodies'].append({'id':'L23_hardware_reserve','mass_kg':reserve,'preceding_joints':2,'com_home_m':com.tolist()})
        bounds=triangle_bounds(model)[0];moving=[b for b in model['bodies'] if b['preceding_joints']>=2];weight=sum(b['mass_kg'] for b in moving)*G
        cutbounds={n:float(triangle_at_cut(model,o)) for n,o in cuts.items()}
        # Independent finite-pose direct 3D moment check at cuts attachedtoJ2.
        q=rng.uniform(-np.pi,np.pi,(200,7));Ts,origins,axes=reference_states(model,q);maxratio=0.
        for cut,origin in cuts.items():
            P=np.einsum('nij,j->ni',Ts[:,2,:3,:3],np.array(origin)*.001)+Ts[:,2,:3,3];moment=np.zeros((len(q),3))
            for b in moving:
                n=b['preceding_joints'];C=np.einsum('nij,j->ni',Ts[:,n,:3,:3],b['com_home_m'])+Ts[:,n,:3,3]
                moment+=np.cross(C-P,np.array([0,0,-G*b['mass_kg']]))
            ratio=float(np.linalg.norm(moment,axis=1).max()/cutbounds[cut]);assert ratio<=1+1e-12;maxratio=max(maxratio,ratio)
        uncertainty=G*(head*.05+p['payload_net_kg']*.10);scenarios=[]
        for label,MNm in [('gravity_COM_uncertainty_times1p5',(max(cutbounds.values())+uncertainty)*1.5),('RH25_peak_single_interface_action_only',157.)]:
            F=weight*1.5 if label.startswith('gravity') else weight;M=MNm*1000
            reaction={n:F/len(points)+M*coeff[n] for n,points in groups.items()}
            bridgeforce=F/2+M/(2*57)
            scenarios.append({'id':label,'moment_Nm':MNm,'force_N':F,'equal_stiffness_group_max_external_axial_N':reaction,
              'rib_strip_MPa':reaction['post_M6']*max(x['stress_per_N_MPa'] for x in ribs),
              'rib_strip_deflection_mm':reaction['post_M6']*max(x['deflection_per_N_mm'] for x in ribs),
              'bridge_assumed_side_reaction_N':bridgeforce,'bridge_strip_MPa':bridgeforce*bridge_sections['stress_per_N_MPa'],
              'bridge_strip_deflection_mm':bridgeforce*bridge_sections['deflection_per_N_mm'],
              'preload_total_output_friction_sensitivity_N':{str(mu):M/(mu*38.5) for mu in [.08,.15,.2]}})
        rows.append({'head_mass_kg':head,'head_COM_home_mm':[0,55,760],'net_object_kg':p['payload_net_kg'],'moving_mass_after_J2_kg':weight/G,
          'old_triangle_all_Nm':oldbounds.tolist(),'revised_triangle_all_Nm':bounds.tolist(),'cut_gravity_moment_bounds_Nm':cutbounds,
          'independent_200pose_max_moment_over_triangle_ratio':maxratio,'COM_uncertainty_Nm':uncertainty,'scenarios':scenarios})
    return {'original_mass_kg':mass,'hardware_mass_budget_kg':reserve,'total_link23_mass_budget_kg':mass+reserve,'old_L2_budget_kg':p['link_budgets_kg'][1],
      'hardware_COM_proxy_m':com.tolist(),'hardware_COM_note':'Budget at actual metal weighted COM, not measured fastener COM','preceding_joints':2,
      'integrated_prior_parts_and_reserves':other,'dependencies_sha256':dependency,'group_moment_reconstruction_error_Nmm':recovery,
      'post_group_Sxx_Svv_mm2':np.diag(POST_XV.T@POST_XV).tolist(),'rib_strip_actual_sections':ribs,'bridge_strip_actual_sections':bridge_sections,
      'material_E_N_mm2':70000,'material_yield_reference_MPa':240,'study_multiplier':1.5,'loadcases':rows,
      'cut_bound_formula':'For eachbody withn>=2, mg*(|cut-J3|+...+|Jn-COM|); n2 uses |cut-COM|. AllpointsareattachedtoJ2before downstream rotations. Full3Dmomentnorm boundedbytriangle inequality; gravityprojectionneverneeded.',
      'structural_model_limits':['Isolated actual rib strips assume perfect clamp at vendor output supportouterR42.5; bridge strip assumes clampworldX40 and18mm breadthY22..40. Neither is a conservativeboundonfullsupport/contact structure.',
        'Bridge side force F/2+M/(2*57) is an equalreaction sensitivity, not a full six-component rear-ring solution.',
        'Actual selectedscrewgrade is12.9 but no preload/proof/threadstrip or aluminumthread fatigue qualification.',
        '157Nm separate pureinterface-action sensitivity; not simultaneous allaxispeak bound, zero-speedholding or combinedtrajectory case.',
        'No acceleration, emergency-stop, impact, fullrange cable or collision qualification.']}


def feature_rows(op,fp):
    rows=[]
    def add(part,label,pts,z,axis,D,depth,thread=''):
        for i,(x,y) in enumerate(pts):rows.append({'part':part,'feature':label,'number':i+1,'x_mm':float(x),'y_mm':float(y),'z_mm':float(z),'axis':axis,'diameter_mm':D,'depth_mm':depth,'thread':thread})
    add('OUT','output clearance',op,0,'+Z',4.5,'through all')
    add('OUT','cap counterbore',op,4,'+Z',7.8,'through all material above z4')
    add('OUT','M6 flat-bottom pilot',POST_XV,22,'-Z',5,19,'M6x1 effective full thread17 proposed; blind')
    add('OUT','centre through',[[0,0]],0,'+Z',66,6)
    add('OUT','boss clearance',[[0,0]],0,'+Z',69.6,2.5)
    add('CARRIER','fixed M3 tap',fp,0,'+Z',2.5,14,'M3x0.5 THROUGH; effective engagement to be qualified')
    for i,(x,v) in enumerate(POST_XV):rows.append({'part':'CARRIER','feature':'M6 clearance','number':i+1,'x_mm':float(x),'y_mm':-33.,'z_mm':1.5-float(v),'axis':'+Y','diameter_mm':6.6,'depth_mm':14,'thread':''})
    add('FRONT','fixed M3 clearance',fp,0,'+Z',3.5,4)
    add('FRONT','OEM cap relief',[[42,0],[-42,0],[0,42],[0,-42]],0,'+Z',6.2,4)
    return rows


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
        placements[n]={'part_id':names[n],'T_world_from_part_mm':frames[n].tolist(),'preceding_joints':2,'estimated_COM_world_mm':list(s.Center().toTuple()),
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
                if row['axis']=='+Y':ms.add_circle((row['x_mm'],row['z_mm']-150),row['diameter_mm']/2)
        ms.add_text(name+' / mm / 1:1 MODEL SPACE / CANDIDATE NOT RELEASED',dxfattribs={'height':3}).set_placement((-65,-195))
        ms.add_text('Contour mesh projections are not machining toolpaths. Use PDF, STEP and feature CSV.',dxfattribs={'height':2.5}).set_placement((-65,-203))
        path=out/(name+'.dxf');d.saveas(path);assert not ezdxf.readfile(path).audit().errors;info[name]['sha256'][path.name]=sha(path)
    path=out/'ODR-LINK23-original-assembly.step';cq.exporters.export(cq.Compound.makeCompound(list(a.values())),str(path))
    reread=cq.importers.importStep(str(path)).val();assert reread.isValid() and len(reread.Solids())==3
    rows=feature_rows(op,fp)
    with (out/'hole-features.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    return parts,meshes,info


def bom(out,parts,table):
    result={'revision':REV,'original_parts':[{'id':n,'quantity':1,'candidate_material':'6061-T6','mass_kg':s.Volume()*DENSITY} for n,s in parts.items()],
      'fasteners':[{'part':'Accu SSC-M6-30-12.9','quantity':4,'DIN912':True,'grade':'12.9 natural finish','L_mm':30,'max_D_mm':10.22,'H_mm':6,'key_AF_mm':5,'fully_threaded':True,'nominal_grip_mm':14,'nominal_geometric_engagement_mm':16,'pilot_bottom_remaining_mm':3,'mass_each_kg':.0083,'url':'https://www.accu.co.uk/metric-cap-head-screws/16078-SSC-M6-30-12-9'},
        {'part':'Accu SSC-M3-40-12.9','quantity':8,'DIN912':True,'grade':'12.9 natural finish','L_mm':40,'max_D_mm':5.68,'H_mm':3,'key_AF_mm':2.5,'minimum_thread_mm':18,'nominal_grip_mm':30,'nominal_geometric_engagement_mm':10,'rear_face_remaining_mm':4,'mass_each_kg':.0031,'url':'https://www.accu.co.uk/metric-cap-head-screws/16011-SSC-M3-40-12-9'},
        {'part':'OEM output M4 length TBD','quantity':16,'only_known_free_length_modeled_mm':7.5,'reason':'No verified effective OEM outputthread start/end;13mm drawing recess not assumed completeemptychannel.'}],
      'known_selected_fasteners_catalog_mass_kg':.058,'all_fasteners_mass_budget_kg':.15,'catalog_listing_not_stock_confirmation':True,'preload_selected':False,
      'sources':[{'url':'https://www.myactuator.com/downloads-rhseries','documents':['RH25 3D-A0 /2D-A0 p1','RH20 3D A /2D A p1'],'vendor_STEP_private':True},
        {'url':'https://ucpcdn.thyssenkrupp.com/_legacy/UCPthyssenkruppBAMXUK/assets.files/material-data-sheets/aluminium/aluminium-6061.pdf','pages':[2,3],'values':'E70000N/mm2;rho2.7g/cm3;T6 minimumRp0.2 240MPa in statedproductranges;requiresbatchcert'}],
      'no_purchase_made':True,'printed_parts':'PLA/PETG; external supports carry joints; unloaded manualfitonly'}
    (out/'bom.json').write_text(json.dumps(result,indent=2)+'\n')
    with (out/'screw-stacks.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
    return result


def complete(out,font,a,op,fp,result):
    assert not result['errors'],'Solve geometry failures before producing candidate drawings'
    parts,meshes,info=export_original(out,a,op,fp)
    result['load_screening']=load_screen(json.loads((ROOT/'engineering/parameters/r4-layout.json').read_text()),a,op,fp)
    result['export_checks']=info;result['bom']=bom(out,parts,result['hardware']);result['generator_sha256']=sha(Path(__file__))
    deps=['engineering/generated/link12-study/part-placements.json','engineering/generated/link56-study/part-placements.json','docs/engineering/sources/rh-interface-extraction.json','engineering/build_link12_study.py','engineering/build_link56_study.py','engineering/build_base_study.py','engineering/build_layout.py','engineering/mount_interface_study.py','engineering/studies/link_interface_tools.py','engineering/arm_screening.py','engineering/review_arm_screening.py']
    result['dependency_sha256']={x:sha(ROOT/x) for x in deps}
    result['manufacturing_release']=False;result['strength_qualified']=False;result['contact_path_closed']=True;result['OEM_output_screw_length_frozen']=False
    result['proposed_tolerances']={'general_linear_mm':.10,'hole_centres_mm':.05,'contact_flatness_mm':.05,'threads':'6H proposal','status':'Requiresmachining/tolerance-review;notreleased'}
    result['inertia_checks']=['Analytic20x30x40mm uniformbox agrees','All3COMtensors symmetricpositive definite and translationinvariant','Unitsmm5*rho_kg/mm3*1e-6 =>kgm2']
    if font:
        path=out/'ODR-LINK23-candidate-dimensions.pdf';make_pdf(path,font,a,parts,meshes,result,op,fp);result['pdf_sha256']=sha(path)
    (out/'evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('Originalexports and mass/structural screening complete',flush=True)


def make_pdf(path,font,a,parts,meshes,evidence,op,fp):
    from reportlab.lib.pagesizes import A3,landscape
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas
    from draw_layout import Sheet,TEAL,GRAY
    from build_link56_study import projected_edges
    from pypdf import PdfReader
    pdfmetrics.registerFont(TTFont('Link23CN',str(font)));pdf=canvas.Canvas(str(path),pagesize=landscape(A3),pageCompression=1)
    pdf.setTitle('Odradek J2-J3 connection candidate — NOT RELEASED');pdf.setAuthor('Auromix contributors');s=Sheet(pdf,'Link23CN')
    XY=np.array([[1,0,0],[0,1,0]]);XZ=np.array([[1,0,0],[0,0,1]]);YZ=np.array([[0,1,0],[0,0,1]])
    def notes(x,y,lines,size=8.3,step=7):
        for i,t in enumerate(lines):s.text(x,y-i*step,t,size)
    def view(name,basis,origin,scale=1):
        for edge in projected_edges(meshes[name],basis):
            q=edge*scale+origin;s.line(q[0],q[1],TEAL,.35)
    def dim(a,b,label,off=(0,0)):
        a,b,off=[np.array(x,dtype=float) for x in [a,b,off]];s.line(a,a+off,GRAY,.3);s.line(b,b+off,GRAY,.3)
        s.arrow(a+off,b+off,GRAY,.4);s.arrow(b+off,a+off,GRAY,.4);s.text(*((a+b)/2+off+np.array([0,2])),label,8,GRAY,'center')
    def footer(n):
        s.line((15,16),(405,16),GRAY,.4);s.text(15,10,'单位 mm | 候选结构评审 / 无载试装 | 6061-T6暂定 | 非制造放行；不代表2kg承载通过',8)
        s.text(405,10,f'{n}/5 | A3 横向 | {REV}',8,align='right');pdf.showPage()
    s.header('J2 → J3 实体转接候选','J2=[0,0,170], 轴+Y；J3=[0,55,220], 轴+Z。主轴位置不变；原创三件闭合承力路径。',REV)
    for basis,origin,shift,label in [(XZ,[98,165],[0,170],'正视XZ'),(YZ,[267,165],[0,170],'侧视YZ')]:
        for shape in a.values():
            vs,fs=shape.tessellate(.1,.1);mesh=trimesh.Trimesh(vertices=[v.toTuple() for v in vs],faces=fs,process=True)
            for edge in projected_edges(mesh,basis):q=(edge-shift)*1.3+origin;s.line(q[0],q[1],TEAL,.35)
        s.text(origin[0]-65,252,label+' / 1.3:1',10,TEAL)
    notes(20,88,['实体路径：J2输出接触面 → 带筋输出板 / 四支柱 → 两侧脚与横向后环 → J3固定后法兰。',
       'J2输出面Y0；柱顶Y22；侧脚厚14至Y36；后环Z168.5～182.5；J3后接触Z182.5。',
       'J3前接触Z208.5；前环厚4到Z212.5。前后法兰夹持跨度26，后壳穿过Ø78.6避让孔。',
       f'原创金属估重{evidence["load_screening"]["original_mass_kg"]:.6f} kg；紧固件预算0.15kg；全部 preceding_joints=2。',
       '全长候选：4×M6×30、8×M3×40；16×原厂输出M4长度仍TBD，不能据此采购整套紧固件。',
       '原厂CAD仅用于本地逐实体干涉检查；本公开STEP只包含原创零件，不重新分发原厂几何。'],8.5,8)
    footer(1)
    s.header('输出适配板 / ODR-L23-OUT-R4','局部原点=J2输出接触面；X=世界X，Y=-世界Z方向，Z=世界Y方向。图中孔坐标均为局部坐标。',REV)
    view('ODR-L23-OUT-R4',XY,[95,179],1.05);view('ODR-L23-OUT-R4',XZ,[95,80],1.05)
    dim([95-66*1.05,179+56*1.05],[95+66*1.05,179+56*1.05],'132',(0,7))
    notes(20,64,['底板为Ø112圆盘并132×64居中矩形，厚6；中心Ø66贯通。',
      '底面另Ø69.6×深2.5避让原厂Ø69×高2凸台；间隙0.3/0.5。',
      '4×Ø16支柱：中心X=±57、Y=±20，从Z6到Z22。',
      '径向筋宽16，r35/Z14至柱心/Z22，底Z6；12条筋根R0.8。',
      '4×M6×1：从柱顶向-Z，Ø5平底孔深19，拟完整牙深17。'],7.6,6.5)
    s.text(198,252,'16×Ø4.5 / PCD77；帽头腔Ø7.8铣至Z4',9,TEAL)
    for i,(x,y) in enumerate(op):s.text(198+(i//8)*103,238-(i%8)*9,f'{i+1:02d} X{x:+8.4f} Y{y:+8.4f}',8)
    notes(198,155,['实际孔相位11.34873°+i×22.5°；不得改成0°。',
      '沉孔从Z4向上贯穿所有筋材，头部位于Z4～8。',
      '下部凸台腔与Ø4.5孔最小径向余肉1.45；上部余肉3.25。',
      'Ø7.8沉孔与中心Ø66孔余肉1.60；真实头部间隙1.89。',
      '4×M6×30从侧脚外侧穿14mm后进入柱16mm。',
      '螺钉尖端到平底孔底名义3mm；完整牙深17仍须工艺审核。',
      '输出M4只建立已核实7.5mm自由段，未虚构全长。',
      '其余倒角、边角、深孔刀具与夹持方案仍需加工方确认。'],8,8)
    footer(2)
    s.header('后环与侧脚 / ODR-L23-CARRIER-R4','局部原点世界[0,55,168.5]，XYZ与世界同向；后环接触面局部Z14。整个零件为一个实体。',REV)
    view('ODR-L23-CARRIER-R4',XY,[92,181],1.08);view('ODR-L23-CARRIER-R4',XZ,[92,92],.8);s.text(20,121,'正视XZ 0.8:1；顶视XY 1.08:1',7,TEAL)
    dim([92-65*1.08,181+50*1.08],[92+65*1.08,181+50*1.08],'130',(0,7))
    notes(20,59,['后环OD100/ID78.6，厚14，Z0～14；8×M3×0.5贯通。',
      '侧脚各16×14×56，中心[X±57,Y-26,Z1.5]。',
      '连接臂各30×18×14，中心[X±50,Y-24,Z7]。',
      '合并后统一用Ø78.6竖直圆柱切掉穿入后壳通道的材料。',
      '工艺内角尚待圆角/刀具审核；不得将尖角模型直接当加工放行。'],7.7,6.5)
    s.text(205,252,'J3固定孔：8×M3 / PCD84 / 真实非均布角',9,TEAL)
    for i,(x,y) in enumerate(fp):s.text(205,239-i*8.5,f'{i+1}: X{x:+8.4f} Y{y:+8.4f}',8)
    notes(205,157,['孔角30/60/120/150/210/240/300/330°。',
       '底孔Ø2.5贯穿14mm；输出不是利用原厂内部螺纹。',
       '4×Ø6.6横孔，轴+Y：X=±57，Z=-18.5或21.5。',
       '横孔从局部Y=-33穿至-19；孔深14mm。',
       '原厂后壳Ø78与后环Ø78.6仅0.30mm径向名义间隙。',
       'M3大径至内孔边仅42-39.3-1.5=1.20mm。',
       '必须评审拔牙、孔边开裂、夹持载荷与后环弯曲。',
       '侧脚和环的宽度由碰撞/工具/装配约束共同决定。'],8.3,8)
    footer(3)
    s.header('前环与螺钉 / ODR-L23-FRONT-R4','前环局部原点=世界[0,55,208.5]；+Z沿J3输出方向。非定位套，不封堵中心。',REV)
    view('ODR-L23-FRONT-R4',XY,[93,179],1.4);view('ODR-L23-FRONT-R4',XZ,[93,90],1.4)
    dim([93-46*1.4,179+46*1.4],[93+46*1.4,179+46*1.4],'92',(0,6))
    notes(20,74,['OD92 / ID70.6，厚4；8×Ø3.5孔PCD84，坐标同后环。',
       '4×Ø6.2原装帽头避让孔PCD84，0/90/180/270°。',
       'ID70.6可从+Z越过原厂Ø70输出止口；名义径向余0.30。',
       'OD92让前环最小Y9，与J2输出M4头最高Y8名义余1。',
       '原装头避让孔外侧仅0.90mm；需工艺与刚度审核。'],7.8,7)
    notes(204,250,['4×M6×30 / SSC-M6-30-12.9 / DIN912',
       '目录全牙；头最大Ø10.22×高6；5mm内六角。',
       '头座世界Y36，自由段14，柱内几何啮合16。',
       '原创建议平底孔深19 / 完整牙深17；有效牙和扭矩待核实。','',
       '8×M3×40 / SSC-M3-40-12.9 / DIN912',
       '头最大Ø5.68×高3；2.5mm内六角；最短螺纹18。',
       '自由段=前环4+原厂跨距26=30；后环几何啮合10。',
       '最短螺纹从头下22开始，覆盖30～40拟啮合段。',
       '尖端世界Z172.5，距后环底168.5余4。','',
       '16×原厂输出M4：尚未选全长。',
       '原厂有效牙起止、允许螺钉伸入、预紧与防松均未确认。',
       '供应商页面有目录规格，但不等于本次库存或交期确认。'],8.5,8)
    footer(4)
    s.header('装配证据、质量与载荷筛查','静力按4.5kg完整头+2kg净工件覆盖；头重心仍用暂定[0,55,760]mm。',REV)
    r=evidence['load_screening']['loadcases'][-1];c=r['scenarios'][0]
    notes(20,251,['装配顺序：',
      '1. J1/L12/J2已装妥，J3及以后尚未装；输出板从+Y贴J2。',
      '2. 输出16×M4从+Y锁紧（全长待原厂确认，当前不允许带载）。',
      '3. 后环/侧脚从+Y贴四柱，用4×M6×30由+Y锁紧。',
      '4. J3从+Z穿入后环，后固定面落在Z182.5。',
      '5. 前环从+Z越过输出止口；8×M3×40由+Z穿原厂孔并锁入后环。',
      '6. 后续J3输出连杆另装；结论不包括整机满装维护路径。'],8.2,7.5)
    notes(20,187,['真实OEM J1/J2/J3/J4与既有L12金属及28螺钉参与名义检查。',
      '逐实体Boolean；28个螺钉的已知形状另检查60mm连续轴向装入。',
      '工具轴杆Ø5/M4、Ø6/M6、Ø4/M3，长度60；不代表扳手手柄。',
      'J3：逐原厂实体证明被包络包含后，检查0～180mm连续插入扫掠。',
      '其余三步：实件包含证明 + 连续保守扫掠，另留最大5mm离散记录。'],8,7.5)
    for i,(key,x) in enumerate(evidence['checks']['contacts'].items()):s.text(20,136-i*8,f'{key} 接触面积: {x["shared_planar_face_area_mm2"]:.2f} mm²',8)
    notes(225,251,[f'实重积分仅为6061均质CAD计算，不是称重。',
      f'三件{evidence["load_screening"]["original_mass_kg"]:.6f}kg + 紧固件预算0.15kg。',
      'COM和对质心惯量详见part-placements.json，归属pre=2。',
      f'更新J2/J3三角界 {r["revised_triangle_all_Nm"][1]:.2f}/{r["revised_triangle_all_Nm"][2]:.2f} Nm。',
      f'本连接最大截面三角界 {max(r["cut_gravity_moment_bounds_Nm"].values()):.2f} Nm。',
      f'头COM±50、工件COM100mm不确定性再×1.5：{c["moment_Nm"]:.2f} Nm。',
      f'M6最大外载敏感性 {c["equal_stiffness_group_max_external_axial_N"]["post_M6"]:.0f} N。',
      f'真实筋条: {c["rib_strip_MPa"]:.1f}MPa / {c["rib_strip_deflection_mm"]:.3f}mm。',
      f'真实桥条: {c["bridge_strip_MPa"]:.1f}MPa / {c["bridge_strip_deflection_mm"]:.3f}mm。',
      '条带根固定、等刚度螺栓组都是简化假设。',
      '不覆盖整环弯曲、预紧接触、螺纹拔牙、疲劳与冲击。',
      '目录rated动态额定不能当零速持续保持能力。'],8.3,8)
    notes(20,63,['候选公差：一般线性±0.10、孔中心±0.05、接触平面度0.05、螺纹6H；需加工方和公差链复核。',
      '打印：OUT底面朝床；CARRIER后环底面朝床且侧脚加支撑；FRONT平放。外部支架承托关节，仅手动无载试装。',
      '未放行：原厂输出螺钉全长 / 完整有效牙 / 夹持许可 / 预紧防松 / 接触FEA / 疲劳 / 全行程碰撞与线缆。'],8.2,8)
    footer(5);pdf.save();pdfread=PdfReader(path);assert len(pdfread.pages)==5 and all(len(p.extract_text())>150 for p in pdfread.pages)


if __name__=='__main__':main()
