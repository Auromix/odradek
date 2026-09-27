# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""J3-to-J4 RH20 closed-beam connection study; no manufacturing release."""
import argparse
import csv
import hashlib
import itertools
import json
from pathlib import Path
import cadquery as cq
import ezdxf
import numpy as np
import trimesh
from build_layout import frame,moved
from mount_interface_study import ring,bores,load_vendor
from build_link56_study import rounded,cylinder,cut_side_pilots,face_contact,projected_edges
from build_link12_study import shape_box
from build_link23_study import inertia_props
from studies.link_interface_tools import cache,check
ROOT=Path(__file__).resolve().parents[1]
REV='R4-LINK34-01'
PARAM_SHA='4349d1797b906b67a7bc396fcb84bc439c2d70dd0b337659e552cee293d2dd81'
DENSITY=2.7e-6
CORNER=np.array([[35,25],[-35,25],[-35,-25],[35,-25]],float)


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def make_parts(iface):
    op=np.array([q['xy_mm'] for q in iface['output_holes']['points']]);fp=np.array([q['xy_mm'] for q in iface['fixed_through_holes']['points']])
    T3=frame([0,55,220],[0,0,1]);T4=frame([0,0,400],[0,-1,0])
    output=ring(48,27.8,0,8).cut(bores(op.tolist(),1.75,-1,10)).cut(bores(CORNER.tolist(),1.65,-1,10)).val()
    lower=rounded(90,76,3,8,10).union(rounded(53.8,33.8,3.2,18,16))
    lower=lower.cut(bores([[0,0]],10,7,28)).cut(bores(CORNER.tolist(),2.25,7,12)).cut(bores(op.tolist(),3.2,7.9,3.6)).val()
    lower=cut_side_pilots(lower,26)
    tube=rounded(60,40,3,18,92).cut(rounded(54,34,3,17,94)).val()
    for z in [26,102]:
        for y in [-10,10]:tube=tube.cut(cylinder([-31,y,z],[1,0,0],2.25,62))
    upper=rounded(90,76,3,110,10).union(rounded(53.8,33.8,3.2,94,16))
    upper=upper.cut(bores([[0,5]],8,93,28)).cut(bores(CORNER.tolist(),1.65,109,12)).val();upper=cut_side_pilots(upper,102)
    rear=ring(50,39.3,-51.5,14).union(cq.Workplane('XY').workplane(offset=-51.5).center(0,-30).rect(60,60).extrude(14))
    rear=rear.cut(bores([[0,0]],39.3,-52,15)).cut(bores(fp.tolist(),1.25,-52,15)).val();rear=moved(rear,T4)
    foot=rounded(90,76,3,340,10).translate((0,55,0)).cut(bores([[0,60]],8,339,12)).cut(bores((CORNER+[0,55]).tolist(),2.25,339,12)).val()
    rear=rear.fuse(foot).clean()
    roots=[e for e in rear.Edges() if e.geomType()=='LINE' and e.BoundingBox().xlen>30 and abs(e.Center().z-350)<1e-6 and min(abs(e.Center().y-37.5),abs(e.Center().y-51.5))<1e-6]
    assert len(roots)==2;rear=rear.fillet(2,roots).clean()
    front=ring(50,35.3,-11.5,4).cut(bores(fp.tolist(),1.75,-12,6)).cut(bores([[42,0],[-42,0],[0,42],[0,-42]],3.1,-12,6)).val()
    a={'output_adapter':moved(output,T3),'lower_block':moved(lower,T3),'closed_beam':moved(tube,T3),'upper_block':moved(upper,T3),'rear_carrier':rear,'front_ring':moved(front,T4)}
    transforms={'output_adapter':T3,'lower_block':frame([0,55,228],[0,0,1]),'closed_beam':frame([0,55,238],[0,0,1]),'upper_block':frame([0,55,314],[0,0,1]),'rear_carrier':frame([0,55,340],[0,0,1]),'front_ring':frame([0,11.5,400],[0,-1,0])}
    names={n:'ODR-L34-'+code+'-R4' for n,code in zip(a,['OUT','LOW','TUBE','UP','CARRIER','FRONT'])}
    parts={names[n]:moved(s,np.linalg.inv(transforms[n])) for n,s in a.items()}
    for n,s in a.items():assert s.isValid() and len(s.Solids())==1,(n,s.isValid(),len(s.Solids()))
    return parts,a,op,fp,T3,T4,transforms,names


def hardware(op,fp,T3,T4):
    full={};free={};tools={};table=[]
    def bolt(name,seat,axis,d,L,grip,engage,owner,stage,selected=True):
        seat=np.asarray(seat,float);axis=np.asarray(axis,float);D,H=(5.68,3) if d==3 else (7.22,4)
        head=cylinder(seat,axis,D/2,H);full[name]=head.fuse(cylinder(seat,-axis,d/2,L));free[name]=head.fuse(cylinder(seat,-axis,d/2,grip))
        tools[name]=cylinder(seat+axis*H,axis,2 if d==3 else 2.5,60)
        table.append({'id':name,'thread':f'M{d}','selected_length_mm':L if selected else None,'modeled_length_mm':L,'free_grip_mm':grip,'nominal_geometric_engagement_mm':engage,'seat_world_mm':seat.tolist(),'head_outward_axis':axis.tolist(),'head_D_H_mm':[D,H],'thread_owner':owner,'stage':stage,'length_selected':selected})
    for i,(x,y) in enumerate(op):bolt(f'OUT_M3_unknown_{i+1}',[x,y+55,228],[0,0,1],3,11,11,None,'J3',1,False)
    for i,(x,y) in enumerate(CORNER):
        bolt(f'LOW_M4x16_{i+1}',[x,y+55,238],[0,0,1],4,16,10,6,'output_adapter',2)
        bolt(f'FOOT_M4x20_{i+1}',[x,y+55,350],[0,0,1],4,20,10,10,'upper_block',5)
    for label,z,owner,stage in [('LOW',246,'lower_block',3),('UP',322,'upper_block',4)]:
        for sx,y in itertools.product([-1,1],[-10,10]):bolt(f'{label}_SIDE_M4x12_{sx}_{y}',[sx*30,y+55,z],[sx,0,0],4,12,3.1,8.9,owner,stage)
    for i,(x,y) in enumerate(fp):bolt(f'FIX_M3x40_{i+1}',(T4@np.array([x,y,-7.5,1]))[:3],[0,-1,0],3,40,30,10,'rear_carrier',7)
    return full,free,tools,table


def prior_L23(models):
    import build_link23_study as l23
    p=ROOT/'engineering/generated/link23-study/part-placements.json';r=json.loads(p.read_text());s={}
    for n,x in r['instances'].items():s['L23_'+n]=moved(cq.importers.importStep(str(p.parent/(x['part_id']+'.step'))).val(),np.array(x['T_world_from_part_mm']))
    i25=models['RH25-B']['unified_joint_interface'];i20=models['RH20-B']['unified_joint_interface'];op=np.array([x['xy_mm'] for x in i25['output_holes']['points']]);fp=np.array([x['xy_mm'] for x in i20['fixed_through_holes']['points']])
    hw=l23.make_hardware(op,fp,frame([0,0,170],[0,1,0]),frame([0,55,220],[0,0,1]))[0]
    s.update({'L23_HW_'+n:q for n,q in hw.items()});return s


def continuous_vendor_insertion(v,targets,T4):
    rear=cylinder([0,0,-95],[0,0,1],39.05,57.5);front=cylinder([0,0,-37.5],[0,0,1],45.05,40.1)
    home=moved(rear.fuse(front),T4);swept=moved(rear.fuse(cylinder([0,0,-37.5],[0,0,1],45.05,200.1)),T4)
    assert home.isValid() and swept.isValid();outside=[]
    for i,s in enumerate(v.Solids()):
        q=s.cut(home);vol=abs(q.Volume()) if q.Solids() else 0.;outside.append({'solid_index':i,'outside_mm3':vol})
    assert sum(x['outside_mm3'] for x in outside)<1e-4
    return {'per_solid_containment':outside,'continuous_world_axis':[0,-1,0],'travel_mm':160,'home_local_envelope_mm':{'rear_R':39.05,'rear_z':[-95,-37.5],'front_R':45.05,'front_z':[-37.5,2.6]},'swept_front_z_mm':[-37.5,162.6],'checks':{n:check(swept,s) for n,s in targets.items()},'method':'Boolean-contained actualvendor solids; two-cylinder enclosing continuoussweep; nominal geometryonly'}


def continuous_original(a,op,stage_targets):
    T3=frame([0,55,220],[0,0,1]);T4=frame([0,0,400],[0,-1,0])
    output=lambda t:ring(48,27.8,0,8+t).val()
    def lower(t):
        s=rounded(90,76,3,8,10+t).union(rounded(53.8,33.8,3.2,18,16+t)).cut(bores([[0,0]],10,7,28+t)).cut(bores(op.tolist(),3.2,7.9,3.6))
        return s.val()
    tube=lambda t:rounded(60,40,3,18,92+t).cut(rounded(54,34,3,17,94+t)).val()
    upper=lambda t:rounded(53.8,33.8,3.2,94,16).union(rounded(90,76,3,110,10+t)).cut(bores([[0,5]],8,93,28+t)).val()
    def carrier(t):
        # Expanded18mm slab contains14mmcollar plusR2concavefoot fillets.
        s=cylinder([0,35.5,400],[0,1,0],50,18).fuse(cylinder([0,35.5,400+t],[0,1,0],50,18))
        if t:s=s.fuse(shape_box(100,18,t,[0,44.5,400+t/2]))
        s=s.fuse(shape_box(60,18,60+t,[0,44.5,370+t/2]))
        return s.fuse(rounded(90,76,3,340,10+t).translate((0,55,0)).val()).clean()
    front=lambda t:ring(50,35.3,-11.5,4+t).cut(bores([[42,0],[-42,0],[0,42],[0,-42]],3.1,-12,6+t)).val()
    rows=[('output_adapter',moved(output(0),T3),moved(output(100),T3),100,[0,0,1]),
      ('lower_block',moved(lower(0),T3),moved(lower(40),T3),40,[0,0,1]),
      ('closed_beam',moved(tube(0),T3),moved(tube(110),T3),110,[0,0,1]),
      ('upper_block',moved(upper(0),T3),moved(upper(40),T3),40,[0,0,1]),
      ('rear_carrier',carrier(0),carrier(100),100,[0,0,1]),
      ('front_ring',moved(front(0),T4),moved(front(120),T4),120,[0,-1,0])]
    descriptions={'output_adapter':'AnnulusR48/R27.8; globalZ220..328',
      'lower_block':'Largebase90x76R3 globalZ228..278; smallspigot53.8x33.8R3.2 Z238..294; centreR10; outputcap reliefsR3.2 retainedonlyZ228..231.5',
      'closed_beam':'Constant60x40R3 minus54x34R3 section, worldZ238..440; sideholes omitted',
      'upper_block':'Smallspigot53.8x33.8R3.2 Z314..330; largebase90x76R3 Z330..380; constantcableR8 centredY60; overlapcontains shiftedspigot',
      'rear_carrier':'worldY35.5..53.5 expandedslab; outerfilledR50 capsule alongZ400..500; width60 lowerwebZ340..500;90x76R3 footZ340..450',
      'front_ring':'J4local annulusR50/R35.3,z-11.5..112.5; retains4axialR3.1 OEMcap reliefsPCD84'}
    result={}
    for n,home,swept,t,axis in rows:
        assert home.isValid() and swept.isValid() and len(home.Solids())==len(swept.Solids())==1
        q=a[n].cut(home);volume=abs(q.Volume()) if q.Solids() else 0;assert volume<1e-4,(n,volume)
        result[n]={'home_outside_mm3':volume,'travel_mm':t,'axis_world':axis,'enclosure':descriptions[n],
          'checks':{k:check(swept,s) for k,s in stage_targets[n].items()},
          'method':'Actualpart Booleancontained in home enclosure; unionof enlargedprisms/capsule covers everytranslation in bounded interval. NominalCADonly.'}
    return result


def continuous_q3_upstream(a,hw,v,prior,op):
    """Full-turn relative clearance for this link vs J2 and L23 only.

    OEMJ3 rotating output is not a stationary obstacle. This does not qualify
    upstream links below J2, cable motion, J4/J5 rotation, or all-arm motion.
    """
    targets={'J2':v['J2'],**prior};near={'output_adapter':a['output_adapter']}
    near.update({n:s for n,s in hw.items() if n.startswith(('OUT_','LOW_M4x16_'))})
    enclosure=cylinder([0,55,217],[0,0,1],48,25)
    containment=[]
    for n,s in near.items():
        q=s.cut(enclosure);vol=abs(q.Volume()) if q.Solids() else 0.;assert vol<1e-4,(n,vol)
        containment.append({'id':n,'outside_mm3':vol})
    far={**{n:s for n,s in a.items() if n not in near},**{n:s for n,s in hw.items() if n not in near}}
    upper=max(s.BoundingBox().zmax for s in targets.values())
    lower=min(s.BoundingBox().zmin for s in far.values());assert lower-upper>1.9
    checks={n:check(enclosure,s) for n,s in targets.items()}
    oldcorner=[[38,30],[-38,30],[-38,-30],[38,-30]]
    rejected=rounded(90,76,3,0,8).cut(bores([[0,0]],27.8,-1,10)).cut(bores(op.tolist(),1.75,-1,10)).cut(bores(oldcorner,1.65,-1,10)).val()
    rejected=moved(rejected,frame([0,55,220],[0,0,1]))
    rejected_checks={str(angle):check(rejected.rotate((0,55,220),(0,55,221),angle),prior['L23_output_adapter']) for angle in [30,45,60,90]}
    assert all(rejected_checks[str(q)]['events'] for q in [30,45,60])
    return {'q3_deg':[-180,180],'home_containment':containment,'sweep_enclosure_world_mm':{'axis_origin':[0,55,217],'axis':[0,0,1],'radius':48,'z':[217,242]},
      'checks':checks,'remaining_moving_parts':list(far),'stationary_maxZ_mm':upper,'remaining_moving_minZ_mm':lower,'remaining_Z_gap_mm':lower-upper,
      'rejected_rectangle':{'outline_mm':[90,76,8],'corner_radius_mm':3,'corner_taps_mm':oldcorner,'angle_deg_to_L23_output_intersection':rejected_checks,'note':'Historical rejected candidate retained for reproducible design rationale; not exported as candidate CAD.'},
      'nominal_radial_sweep_to_L23_upper_output_plate_Y_gap_mm':1.,
      'proof':'Near-interface actualparts/bolts contained in rotation-invariant cylinder, checked against every stationarysolid. Allother linkparts/bolts haveZmin above every stationarysolidZmax; rotationaboutZ preservesZ.',
      'scope':'L34 six originals and40 known screwshapes vs J2 housing andL23 three originals/28 known screwshapes. NoOEMJ3 internal rotor, upstreamwholearm, cable, q4/q5 orwholearm trajectory claim.'}


def validate(a,v,prior,hw,free,tools,table,T4,op):
    allshapes={**a,**v,**prior};cached={n:cache(s) for n,s in allshapes.items()};result={'static':{},'hardware':{},'tools':{},'screw_insertion':{},'contacts':{},'motion_samples':[]}
    for x,y in itertools.combinations(cached,2):
        if x not in a and y not in a:continue
        result['static'][x+'__'+y]=check(cached[x],cached[y])
    print('Static complete',flush=True)
    stagesparts={1:['output_adapter'],2:['output_adapter','lower_block'],3:['output_adapter','lower_block','closed_beam'],4:['output_adapter','lower_block','closed_beam','upper_block'],5:['output_adapter','lower_block','closed_beam','upper_block','rear_carrier'],7:list(a)}
    for row in table:
        n=row['id'];axis=np.array(row['head_outward_axis']);seat=np.array(row['seat_world_mm']);d=int(row['thread'][1:]);D,H=row['head_D_H_mm']
        for target,s in cached.items():result['hardware'][n+'__'+target]=check(free[n] if target==row['thread_owner'] else hw[n],s)
        present=stagesparts[row['stage']]+['J2','J3',*prior]+(['J4'] if row['stage']==7 else [])
        targets={t:allshapes[t] for t in present};targets.update({x:hw[x] for x in hw if x!=n and next(q['stage'] for q in table if q['id']==x)<=row['stage']})
        for target,s in targets.items():
            result['tools'][n+'__'+target]=check(tools[n],s)
            length=row['free_grip_mm'] if target==row['thread_owner'] else row['modeled_length_mm']
            swept=cylinder(seat,axis,D/2,H+60).fuse(cylinder(seat-axis*length,axis,d/2,length+60))
            result['screw_insertion'][n+'__'+target]=check(swept,s)
    for x,y in itertools.combinations(hw,2):result['hardware'][x+'__'+y]=check(hw[x],hw[y])
    for x,y,o,z in [('J3','output_adapter',[0,55,220],[0,0,1]),('output_adapter','lower_block',[0,55,228],[0,0,1]),('lower_block','closed_beam',[0,55,238],[0,0,1]),('closed_beam','upper_block',[0,55,330],[0,0,1]),('upper_block','rear_carrier',[0,55,340],[0,0,1]),('rear_carrier','J4',[0,37.5,400],[0,-1,0]),('front_ring','J4',[0,11.5,400],[0,-1,0])]:
        c=face_contact(allshapes[x],allshapes[y],o,z);assert c['shared_planar_face_area_mm2']>10;result['contacts'][x+'__'+y]=c
    early={c+'__'+n:r for c in ['static','hardware','tools','screw_insertion'] for n,r in result[c].items() if r['events']}
    if early:print('Earlygeometryerrors',json.dumps(early,indent=2),flush=True);return result
    print('Hardware and tools complete',flush=True)
    base={'J2':v['J2'],'J3':v['J3'],**prior}
    stages=[('output_adapter',[0,0,1],100,0,[]),('lower_block',[0,0,1],40,1,['output_adapter']),('closed_beam',[0,0,1],110,2,['output_adapter','lower_block']),('upper_block',[0,0,1],40,3,['output_adapter','lower_block','closed_beam']),('rear_carrier',[0,0,1],100,4,['output_adapter','lower_block','closed_beam','upper_block']),('front_ring',[0,-1,0],120,6,['output_adapter','lower_block','closed_beam','upper_block','rear_carrier','J4'])]
    stage_targets={}
    for name,axis,travel,after,present in stages:
        print('Insertion',name,flush=True);targets={**base,**{n:allshapes[n] for n in present},**{x:hw[x] for x in hw if next(q['stage'] for q in table if q['id']==x)<=after}}
        stage_targets[name]=targets
        target={n:cache(s) for n,s in targets.items()};coll=[];distances=sorted(set([0,.1,.5,1,2,*range(5,travel+1,5)]))
        for dist in distances:
            probe=a[name].translate(tuple(np.array(axis)*dist))
            for n,s in target.items():
                r=check(probe,s)
                if r['events']:coll.append({'distance_mm':dist,'other':n,**r})
        result['motion_samples'].append({'part':name,'axis_world':axis,'distances_mm':distances,'stationary':list(targets),'collisions':coll,'scope':'boundeddiscrete axialpositions; not proofbetween stations'})
    targets={**base,**{n:s for n,s in a.items() if n!='front_ring'},**{x:hw[x] for x in hw if next(q['stage'] for q in table if q['id']==x)<=5}}
    result['continuous_J4_insertion']=continuous_vendor_insertion(v['J4'],targets,T4)
    result['continuous_original_insertions']=continuous_original(a,op,stage_targets)
    result['continuous_q3_upstream_clearance']=continuous_q3_upstream(a,hw,v,prior,op)
    return result


def section_props(shape,axis,coordinate,boxcentre,size):
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
    dim=[1000.,1000.,1000.];dim[axis]=.001;origin=np.array(boxcentre,float);origin[axis]=coordinate
    section=shape.intersect(shape_box(*dim,origin));p=GProp_GProps();BRepGProp.VolumeProperties_s(section.wrapped,p)
    A=p.Mass()/.001;mat=p.MatrixOfInertia();I=np.array([[mat.Value(i+1,j+1) for j in range(3)] for i in range(3)])/.001
    c=np.array(section.Center().toTuple());bb=section.BoundingBox();ext=[max(getattr(bb,k+'max')-c[i],c[i]-getattr(bb,k+'min')) for i,k in enumerate('xyz')]
    for i in range(3):
        if i!=axis:I[i,i]-=A*.001**2/12
    assert A>0
    return {'coordinate_mm':coordinate,'area_mm2':A,'inertia_matrix_mm4':I.tolist(),'centroid_world_mm':c.tolist(),'extremes_mm':ext,'slice_thickness_mm':.001}


def load_screen(p,parts,a,op,fp):
    from arm_screening import arm_parameters
    from review_arm_screening import triangle_bounds,reference_states
    from build_link23_study import strip_screen
    from build_link56_study import section_properties
    G=9.80665;E=70000.;reserve=.15;mass=sum(s.Volume()*DENSITY for s in a.values());com=sum(s.Volume()*DENSITY*np.array(s.Center().toTuple()) for s in a.values())*.001/mass
    other=[];deps={}
    for folder,prefix,pre,res in [('link12-study','L12',1,.20),('link23-study','L23',2,.15),('link56-study','L56',5,.10),('link67-study','L67',6,.10)]:
        path=ROOT/'engineering/generated'/folder/'part-placements.json';data=json.loads(path.read_text())['instances'];deps[str(path.relative_to(ROOT))]=sha(path)
        m=sum(x['mass_kg_6061'] for x in data.values());c=sum(x['mass_kg_6061']*np.array(x['estimated_COM_world_mm']) for x in data.values())*.001/m
        for n,x in data.items():other.append({'id':prefix+'_'+n,'mass_kg':x['mass_kg_6061'],'preceding_joints':pre,'com_home_m':(np.array(x['estimated_COM_world_mm'])*.001).tolist()})
        other.append({'id':prefix+'_hardware_reserve','mass_kg':res,'preceding_joints':pre,'com_home_m':c.tolist()})
    groups={'corner_M4':CORNER,'output_M3':op,'fixed_M3':fp};coeff={};error=0.
    for name,xy in groups.items():
        xy=xy-xy.mean(axis=0);coeff[name]=max(np.linalg.norm(np.linalg.solve(xy.T@xy,r)) for r in xy)
        for angle in np.linspace(0,2*np.pi,721):
            M=np.array([np.cos(angle),np.sin(angle)])*1000;forces=xy@np.linalg.solve(xy.T@xy,[-M[1],M[0]])
            error=max(error,float(np.max(abs(np.array([forces@xy[:,1],-forces@xy[:,0]])-M))))
    assert error<1e-8
    tube_sections=[section_properties(parts['ODR-L34-TUBE-R4'],z) for z in [8,46,84]]
    Imin=min(min(x['Ix_mm4'],x['Iy_mm4']) for x in tube_sections);Amin=min(x['area_mm2'] for x in tube_sections)
    Am=57*37-(4-np.pi)*3**2;Pm=2*(57+37)-8*3+2*np.pi*3;Jthin=4*Am**2*3/Pm;Gshear=E/(2*(1+.33))
    # Unit moment magnitude bound forany bendingdirection, not max(c)/Imin.
    bending_coefficient=max(np.hypot(20/x['Ix_mm4'],30/x['Iy_mm4']) for x in tube_sections)
    plate=[]
    for x,y in CORNER:
        radius=np.hypot(x,y);s=moved(parts['ODR-L34-OUT-R4'],np.linalg.inv(frame([0,0,0],[0,0,1],[x/radius,y/radius,0])))
        plate.append(strip_screen(s,'X',np.linspace(34.7,radius-.1,31),16,2))
    collar=[section_props(a['rear_carrier'],2,z,[0,55,z],None) for z in [350.1,355,360,363.626933,365,370,375,379,380,385,390,395,400]]
    collar_coef=max(np.hypot(x['extremes_mm'][1]/x['inertia_matrix_mm4'][0][0],x['extremes_mm'][0]/x['inertia_matrix_mm4'][1][1]) for x in collar)
    assert max(abs(x['inertia_matrix_mm4'][0][1]) for x in collar)<.1
    Ic=min(min(x['inertia_matrix_mm4'][0][0],x['inertia_matrix_mm4'][1][1]) for x in collar)
    cuts={'J3_output':[0,55,220],'tube_lower':[0,55,238],'tube_upper':[0,55,330],'carrier_foot':[0,55,340],'J4_rear':[0,37.5,400]}
    rows=[];rng=np.random.default_rng(3401)
    for head in [2,3.5,4,4.5]:
        model=arm_parameters(p,head);old=triangle_bounds(model)[0];model['bodies']=[b for b in model['bodies'] if b['id'] not in ['L1_budget','L2_budget','L3_budget','L5_budget','L6_budget']]+other
        for n,s in a.items():model['bodies'].append({'id':'L34_'+n,'mass_kg':s.Volume()*DENSITY,'preceding_joints':3,'com_home_m':(np.array(s.Center().toTuple())*.001).tolist()})
        model['bodies'].append({'id':'L34_hardware_reserve','mass_kg':reserve,'preceding_joints':3,'com_home_m':com.tolist()});bounds=triangle_bounds(model)[0]
        moving=[b for b in model['bodies'] if b['preceding_joints']>=3];W=sum(b['mass_kg'] for b in moving)*G;cutbounds={}
        for cut,origin in cuts.items():
            val=0
            for b in moving:
                n=b['preceding_joints'];points=[np.array(origin)*.001]+[np.array(j['origin_m']) for j in model['joints'][3:n]]+[np.array(b['com_home_m'])]
                val+=b['mass_kg']*G*np.linalg.norm(np.diff(points,axis=0),axis=1).sum()
            cutbounds[cut]=float(val)
        poses=rng.uniform(-np.pi,np.pi,(200,7));Ts,_,_=reference_states(model,poses);ratio=0.
        for cut,origin in cuts.items():
            P=np.einsum('nij,j->ni',Ts[:,3,:3,:3],np.array(origin)*.001)+Ts[:,3,:3,3];M=np.zeros((len(poses),3))
            for b in moving:
                n=b['preceding_joints'];C=np.einsum('nij,j->ni',Ts[:,n,:3,:3],b['com_home_m'])+Ts[:,n,:3,3];M+=np.cross(C-P,[0,0,-G*b['mass_kg']])
            ratio=max(ratio,float(np.linalg.norm(M,axis=1).max()/cutbounds[cut]))
        assert ratio<=1+1e-12
        uncertainty=G*(head*.05+2*.1);scenarios=[]
        for label,moment in [('gravity_COM_uncertainty_times1p5',1.5*(max(cutbounds.values())+uncertainty)),('RH20_peak_single_interface_action_only',80.)]:
            M=moment*1000;F=W*1.5 if label.startswith('gravity') else W;reactions={n:F/len(groups[n])+M*c for n,c in coeff.items()}
            scenarios.append({'id':label,'moment_Nm':moment,'force_N':F,'group_max_external_axial_N':reactions,
              'closed_beam_bending_plus_axial_MPa':M*bending_coefficient+F/Amin,
              'closed_beam_cantilever_tip_deflection_mm':M*92**2/(2*E*Imin)+F*92**3/(3*E*Imin),
              'closed_beam_cantilever_rotation_rad':M*92/(E*Imin)+F*92**2/(2*E*Imin),
              'unperforated_tube_torsion_sensitivity_MPa':M/(2*Am*3),'uniform92mm_tube_twist_sensitivity_rad':M*92/(Gshear*Jthin),
              'unperforated_tube_combined_VM_sensitivity_MPa':float(np.hypot(M*bending_coefficient+F/Amin,np.sqrt(3)*M/(2*Am*3))),
              'output_actual_plate_strip_MPa':reactions['corner_M4']*max(x['stress_per_N_MPa'] for x in plate),
              'output_actual_plate_strip_deflection_mm':reactions['corner_M4']*max(x['deflection_per_N_mm'] for x in plate),
              'collar_straight_cantilever_sensitivity_MPa':M*collar_coef+F/min(x['area_mm2'] for x in collar),
              'collar_straight_cantilever_sensitivity_deflection_mm':M*50**2/(2*E*Ic)+F*50**3/(3*E*Ic)})
        rows.append({'head_mass_kg':head,'head_COM_home_mm':[0,55,760],'net_object_kg':2,'TCP_mm':[0,55,890],'old_triangle_all_Nm':old.tolist(),'revised_triangle_all_Nm':bounds.tolist(),'downstream_mass_kg':W/G,'cut_gravity_moment_bounds_Nm':cutbounds,'COM_uncertainty_Nm':uncertainty,'independent_200pose_max_moment_over_triangle_ratio':ratio,'scenarios':scenarios})
    return {'original_mass_kg':mass,'hardware_mass_budget_kg':reserve,'total_link34_mass_budget_kg':mass+reserve,'old_L3_budget_kg':p['link_budgets_kg'][2],'preceding_joints':3,'hardware_COM_proxy_m':com.tolist(),'hardware_COM_note':'proxyat actual metal weightedCOM; not measured hardwareCOM',
      'integrated_prior_masses':other,'dependencies_sha256':deps,'tube_sections':tube_sections,'tube_length_mm':92,'unperforated_torsion_reference':{'median_enclosed_area_mm2':Am,'median_perimeter_mm':Pm,'assumed_minwall_mm':3,'J_thinwall_mm4':Jthin,'poisson_assumption':.33,'G_N_mm2':Gshear,'scope':'Uniformclosedcentralspan Bredt reference; holes,endblocks,sidebolt/contact transfer and warping requireseparateanalysis'},'tube_bending_coefficient_per_mm3':bending_coefficient,'output_plate_actual_strips':plate,'rear_carrier_actual_slices':collar,
      'group_reconstruction_error_Nmm':error,'material_E_N_mm2':E,'material_yield_reference_MPa':240,'study_multiplier':1.5,'loadcases':rows,
      'unmodeled_head_extension_mm':24,'extension_status':'independentrootstudy not adopted; currentface780/TCP890/COM760; mustrecompute ifextended',
      'limits':['Pointmass triangleboundapplies statedmass/COM assumptionsonly; OEMmodule COM remains midpointproxy, rotorinertia splitunknown',
        'Plate16mm strip clampedatr34.7; collar straightbeam sensitivityclampedfoot; neither iscompletecontactFEA norconservativewholepart strengthbound',
        'Tube92mm perfectlyclamped atlowerend; lateral pointforce plusbending endmoment; coupler compliance/bolt slip/torsion/warping notqualified',
        '80Nm separatepureinterface sensitivity, not concurrentall-axispeak or zero-speedholding guarantee',
        'No fatigue, preload/threadstrip, impact/trajectory/estop, full-motion or cable qualification']}


def feature_rows(op,fp):
    rows=[]
    def add(part,label,points,z,axis,d,depth,thread=''):
        for i,(x,y) in enumerate(points):rows.append({'part':part,'feature':label,'number':i+1,'x_mm':float(x),'y_mm':float(y),'z_mm':z,'axis':axis,'diameter_mm':d,'depth_mm':depth,'thread':thread})
    add('OUT','J3 output clearance',op,0,'+Z',3.5,8);add('OUT','lower block tap',CORNER,0,'+Z',3.3,8,'M4x0.7 THROUGH');add('OUT','boss clearance',[[0,0]],0,'+Z',55.6,8)
    add('LOW','corner clearance',CORNER,0,'+Z',4.5,10);add('LOW','output cap relief',op,0,'+Z',6.4,3.5);add('LOW','cable bore',[[0,0]],0,'+Z',20,26)
    add('UP','foot tap',CORNER,16,'+Z',3.3,10,'M4x0.7 THROUGH');add('UP','cable bore',[[0,5]],0,'+Z',16,26)
    add('CARRIER','foot clearance',CORNER,0,'+Z',4.5,10);add('CARRIER','cable bore',[[0,5]],0,'+Z',16,10)
    for i,(x,y) in enumerate(fp):rows.append({'part':'CARRIER','feature':'J4 fixed tap','number':i+1,'x_mm':float(x),'y_mm':-3.5,'z_mm':60+float(y),'axis':'-Y','diameter_mm':2.5,'depth_mm':14,'thread':'M3x0.5 THROUGH'})
    add('FRONT','fixed clearance',fp,0,'+Z',3.5,4);add('FRONT','OEM cap relief',[[42,0],[-42,0],[0,42],[0,-42]],0,'+Z',6.2,4)
    for part,heights in [('LOW',[18]),('UP',[8]),('TUBE',[8,84])]:
        for z in heights:
            for sx,y in itertools.product([-1,1],[-10,10]):rows.append({'part':part,'feature':'side fastener','number':len(rows)+1,'x_mm':sx*(30 if part=='TUBE' else 26.9),'y_mm':y,'z_mm':z,'axis':'-X' if sx>0 else '+X','diameter_mm':4.5 if part=='TUBE' else 3.3,'depth_mm':3 if part=='TUBE' else 14.9,'thread':'' if part=='TUBE' else 'M4x0.7 effective depth10; flatbottom pilot14.9'})
    return rows


def export_original(out,parts,a,transforms,names,op,fp):
    info={};meshes={};placements={}
    for n,s in parts.items():
        paths=[out/(n+'.'+ext) for ext in ['step','stl']];cq.exporters.export(s,str(paths[0]));cq.exporters.export(s,str(paths[1]),tolerance=.025,angularTolerance=.08)
        reread=cq.importers.importStep(str(paths[0])).val();mesh=trimesh.load_mesh(paths[1],process=True);err=abs(reread.Volume()-s.Volume())
        assert reread.isValid() and len(reread.Solids())==1 and err<1e-3 and err/s.Volume()<1e-8;assert mesh.is_watertight and mesh.body_count==1
        info[n]={'valid_single_solid':True,'volume_mm3':s.Volume(),'STEP_roundtrip_error_mm3':err,'STL_watertight':True,'STL_body_count':1,'sha256':{x.name:sha(x) for x in paths}};meshes[n]=mesh
        d=ezdxf.new('R2010');d.units=ezdxf.units.MM;ms=d.modelspace()
        for label,basis,off in zip(['TOP_XY','FRONT_XZ','SIDE_YZ'],[np.array([[1,0,0],[0,1,0]]),np.array([[1,0,0],[0,0,1]]),np.array([[0,1,0],[0,0,1]])],[[0,0],[0,-170],[150,-170]]):
            d.layers.new(label)
            for edge in projected_edges(mesh,basis):ms.add_line(tuple(edge[0]+off),tuple(edge[1]+off),dxfattribs={'layer':label})
        for row in feature_rows(op,fp):
            if row['part']!=n.split('-')[2]:continue
            if row['axis']=='+Z':ms.add_circle((row['x_mm'],row['y_mm']),row['diameter_mm']/2)
            if row['axis']=='-Y':ms.add_circle((row['x_mm'],row['z_mm']-170),row['diameter_mm']/2)
            if row['axis'] in ['+X','-X']:ms.add_circle((row['y_mm']+150,row['z_mm']-170),row['diameter_mm']/2)
        ms.add_text(n+' / mm / MODEL SPACE1:1 / CANDIDATE; NO RELEASE',dxfattribs={'height':3}).set_placement((-65,-216))
        ms.add_text('Use STEP, PDF and featureCSV; projections not machining cutter paths.',dxfattribs={'height':2.5}).set_placement((-65,-224));path=out/(n+'.dxf');d.saveas(path);assert not ezdxf.readfile(path).audit().errors;info[n]['sha256'][path.name]=sha(path)
    for n,s in a.items():
        I=np.array(inertia_props(s));R=transforms[n][:3,:3];assert np.allclose(I,inertia_props(s.translate((77,-44,123))),rtol=1e-7,atol=1e-12)
        placements[n]={'part_id':names[n],'T_world_from_part_mm':transforms[n].tolist(),'preceding_joints':3,'mass_kg_6061':s.Volume()*DENSITY,'estimated_COM_world_mm':list(s.Center().toTuple()),'estimated_COM_part_mm':list(parts[names[n]].Center().toTuple()),'orientation_home':np.eye(3).tolist(),'inertia_com_kg_m2':I.tolist(),'inertia_axes':'world axes at home; about ownCOM','inertia_com_part_kg_m2':(R.T@I@R).tolist()}
    path=out/'ODR-LINK34-original-assembly.step';cq.exporters.export(cq.Compound.makeCompound(list(a.values())),str(path));r=cq.importers.importStep(str(path)).val();assert r.isValid() and len(r.Solids())==6
    (out/'part-placements.json').write_text(json.dumps({'revision':REV,'parameters_sha256':PARAM_SHA,'density_kg_mm3':DENSITY,'CAD_integral_not_measurement':True,'instances':placements},indent=2)+'\n')
    rows=feature_rows(op,fp)
    with (out/'hole-features.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    return meshes,info


def write_bom(out,parts,table):
    previous=json.loads((ROOT/'engineering/generated/link56-study/bom.json').read_text());sources=previous['sources']
    sources['vendor']={'url':'https://www.myactuator.com/downloads-rhseries','part':'RH-20-100-E-B-D 3D A.STEP / 2D A.pdf; RH25/RH17 neighbors only'}
    data={'revision':REV,'original_parts':[{'id':n,'quantity':1,'material_candidate':'6061-T6','mass_kg':s.Volume()*DENSITY} for n,s in parts.items()],
      'fasteners':[{'source_id':'M4x12','quantity':8,'grip_mm':3.1,'geometric_engagement_mm':8.9},{'source_id':'M4x16','quantity':4,'grip_mm':10,'geometric_engagement_mm':6,'bottom_remaining_output_mm':2},{'source_id':'M4x20','quantity':4,'grip_mm':10,'geometric_engagement_mm':10,'tip_nominally_flush':True},{'source_id':'M3x40','quantity':8,'grip_mm':30,'geometric_engagement_mm':10,'rear_remaining_mm':4},{'size':'M3 lengthTBD','quantity':16,'modeled_known_free_mm':11,'reason':'8mmplate + proven3mmchannel; OEMeffective threadlimitsunknown'}],
      'sources':sources,'hardware_mass_budget_kg':.15,'source_recheck_date':'2026-09-27','M4_sources_rechecked':'TR threeactual grade12.9 catalogentries and Accudimensionalcrosschecks; availabilitynot confirmed; criticalDIN/ISOvariant andmaximumhead requirespurchase drawing',
      'no_purchase_made':True,'thread_helix_modeled':False,'preload_selected':False,'printed_parts':'PLA/PETG unloaded manuallyfitted withseparate jointsupport',
      'stock_profile_selected':False,'closed_beam_note':'Original60x40/54x34 profile, bothcornerradii3.0; arbitrarycommercial60x40x3tube isnot equivalent untilmeasured.'}
    (out/'bom.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    with (out/'screw-stacks.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
    return data


def complete(out,font,parts,a,op,fp,transforms,names,result):
    assert not result['errors'],'Do notexportcandidate drawingsbeforegeometryfailuresresolved'
    meshes,info=export_original(out,parts,a,transforms,names,op,fp)
    result['load_screening']=load_screen(json.loads((ROOT/'engineering/parameters/r4-layout.json').read_text()),parts,a,op,fp)
    result['export_checks']=info;result['bom']=write_bom(out,parts,result['hardware']);result['generator_sha256']=sha(Path(__file__))
    deps=['engineering/build_layout.py','engineering/mount_interface_study.py','engineering/build_link12_study.py','engineering/build_link23_study.py','engineering/build_link56_study.py','engineering/studies/link_interface_tools.py','engineering/arm_screening.py','engineering/review_arm_screening.py','docs/engineering/sources/rh-interface-extraction.json','engineering/generated/link56-study/bom.json']
    result['dependency_sha256']={x:sha(ROOT/x) for x in deps};result['dependency_sha256'].update(result['load_screening']['dependencies_sha256'])
    interface_data=json.loads((ROOT/'docs/engineering/sources/rh-interface-extraction.json').read_text())['models']
    result['vendor_sources_from_hash_checked_interfaces']={m['id']:{'filename':m['input_filename'],'sha256':m['input_sha256']} for m in interface_data if m['id'] in ['RH20-B','RH25-B'] or (m['id']=='RH17-B' and any(k.endswith('__J5') for k in result['checks']['static']))}
    import inspect
    result['geometry_function_sha256']=hashlib.sha256(inspect.getsource(make_parts).encode()).hexdigest()
    result.update(status='candidate geometry and screening; not manufacturingrelease',manufacturing_release=False,strength_qualified=False,OEM_output_screw_length_frozen=False)
    if font:
        path=out/'ODR-LINK34-candidate-dimensions.pdf';make_pdf(path,font,a,parts,meshes,result,op,fp);result['pdf_sha256']=sha(path)
    (out/'evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print('Complete originalCAD/math/PDF',flush=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--rh20-step',required=True,type=Path);ap.add_argument('--rh25-step',required=True,type=Path);ap.add_argument('--rh17-step',type=Path);ap.add_argument('--out',type=Path,default=ROOT/'engineering/generated/link34-study');ap.add_argument('--private-assembly',type=Path);ap.add_argument('--font',type=Path);ap.add_argument('--geometry-only',action='store_true');args=ap.parse_args()
    assert sha(ROOT/'engineering/parameters/r4-layout.json')==PARAM_SHA
    models={q['id']:q for q in json.loads((ROOT/'docs/engineering/sources/rh-interface-extraction.json').read_text())['models']}
    parts,a,op,fp,T3,T4,transforms,names=make_parts(models['RH20-B']['unified_joint_interface']);v20=load_vendor(args.rh20_step,models['RH20-B']);v25=load_vendor(args.rh25_step,models['RH25-B'])
    v={'J2':moved(v25,frame([0,0,170],[0,1,0])),'J3':moved(v20,T3),'J4':moved(v20,T4)}
    if args.rh17_step:v['J5']=moved(load_vendor(args.rh17_step,models['RH17-B']),frame([0,-55,450],[0,0,1]))
    prior=prior_L23(models);hw,free,tools,table=hardware(op,fp,T3,T4);checks=validate(a,v,prior,hw,free,tools,table,T4,op)
    errors={c+'__'+n:r for c in ['static','hardware','tools','screw_insertion'] for n,r in checks[c].items() if r['events']}
    errors.update({'motion__'+r['part']:r for r in checks['motion_samples'] if r['collisions']})
    errors.update({'continuous_J4__'+n:r for n,r in checks.get('continuous_J4_insertion',{}).get('checks',{}).items() if r['events']})
    errors.update({'continuous_original__'+n+'__'+k:x for n,q in checks.get('continuous_original_insertions',{}).items() for k,x in q['checks'].items() if x['events']})
    errors.update({'continuous_q3_upstream__'+n:r for n,r in checks.get('continuous_q3_upstream_clearance',{}).get('checks',{}).items() if r['events']})
    result={'revision':REV,'parameters_sha256':PARAM_SHA,'mass_kg_6061':{n:s.Volume()*DENSITY for n,s in a.items()},'checks':checks,'errors':errors,'hardware':table,'status':'preliminary geometry study'}
    args.out.mkdir(parents=True,exist_ok=True);(args.out/'geometry-probe.json').write_text(json.dumps(result,indent=2)+'\n')
    if args.private_assembly:
        dest=args.private_assembly.resolve();assert ROOT not in dest.parents;dest.parent.mkdir(parents=True,exist_ok=True)
        cq.exporters.export(cq.Compound.makeCompound(list({**a,**v,**prior,**hw}.values())),str(dest))
    print(json.dumps({'mass':result['mass_kg_6061'],'errors':errors},indent=2),flush=True)
    if not args.geometry_only:complete(args.out,args.font,parts,a,op,fp,transforms,names,result)


def make_pdf(path,font,a,parts,meshes,evidence,op,fp):
    from reportlab.lib.pagesizes import A3,landscape
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas
    from draw_layout import Sheet,TEAL,GRAY
    from pypdf import PdfReader
    pdfmetrics.registerFont(TTFont('L34CN',str(font)));pdf=canvas.Canvas(str(path),pagesize=landscape(A3),pageCompression=1);pdf.setTitle('Odradek J3-J4 connection candidate - NO RELEASE');pdf.setAuthor('Auromix contributors');s=Sheet(pdf,'L34CN')
    XY=np.array([[1,0,0],[0,1,0]]);XZ=np.array([[1,0,0],[0,0,1]]);YZ=np.array([[0,1,0],[0,0,1]])
    def notes(x,y,lines,size=8.3,step=7):
        for i,t in enumerate(lines):s.text(x,y-i*step,t,size)
    def view(n,basis,origin,scale=1):
        for edge in projected_edges(meshes[n],basis):q=edge*scale+origin;s.line(q[0],q[1],TEAL,.35)
    def dim(a,b,label,off=(0,0)):
        a,b,off=[np.array(x,dtype=float) for x in [a,b,off]];s.line(a,a+off,GRAY,.3);s.line(b,b+off,GRAY,.3);s.arrow(a+off,b+off,GRAY,.4);s.arrow(b+off,a+off,GRAY,.4)
        vertical=abs(b[1]-a[1])>abs(b[0]-a[0]);shift=np.array([2,0] if vertical else [0,2])
        s.text(*((a+b)/2+off+shift),label,8,GRAY,'left' if vertical else 'center')
    def footer(n):
        s.line((15,16),(405,16),GRAY,.4);s.text(15,10,'单位 mm | 6061-T6候选 | 无载试装 / 结构评审 | 未制造放行，非2kg承载证明',8);s.text(405,10,f'{n}/6 | A3横向 | {REV}',8,align='right');pdf.showPage()
    s.header('J3 → J4 闭口梁连接候选','J3=[0,55,220], +Z；J4=[0,0,400], -Y；所有主轴原点保持R4-layout-03。',REV)
    for basis,origin,shift,label in [(XZ,[82,70],[0,220],'正视XZ / 0.72:1'),(YZ,[214,70],[55,220],'侧视YZ / 0.72:1')]:
        for shape in a.values():
            vs,fs=shape.tessellate(.1,.1);mesh=trimesh.Trimesh(vertices=[v.toTuple() for v in vs],faces=fs,process=True)
            for edge in projected_edges(mesh,basis):q=(edge-shift)*.72+origin;s.line(q[0],q[1],TEAL,.35)
        s.text(origin[0]-40,252,label,9,TEAL)
    notes(280,249,['六件原创：','OUT 输出板 Ø96×8','LOW 下端块 90×76×10+16插头','TUBE 闭口梁 60×40，长92','UP 上端块 16插头+10板','CARRIER 后环、下舌、底脚整体','FRONT 前环 OD100/ID70.6×4','',
       '世界Z安装链：220 / 228 / 238 / 330 / 340。','脚面Z340～350；后环轴向Y37.5～51.5。','J4前接触Y11.5，前环外面Y7.5。','',
       f'金属CAD估重 {evidence["load_screening"]["original_mass_kg"]:.6f} kg。','紧固件预算0.15kg；全部preceding_joints=3。','原厂CAD不公开，仅本地参与逐实体检查。','含L67实际质量；未采用24mm头部延伸。'],8.1,8)
    notes(20,53,['结构路径：J3真实输出面→输出板→实心下插头→闭口梁→实心上插头→后环底脚→J4固定法兰。',
      'J4前法兰下缘约Z355.3。候选脚顶Z350，R2根角最高352；不是把RH17结构直接放大后沿用原高度。',
      '中心孔和上部Ø16孔仅为布线空间候选；连接器、弯曲半径及贯通路线尚未验证。'],8.3,8)
    footer(1)
    s.header('输出板与下端块','OUT局部原点世界[0,55,220]；LOW局部原点世界[0,55,228]；两者XYZ与世界同向。',REV)
    s.text(20,252,'OUT / LOW视图均1.1:1',8,TEAL);view('ODR-L34-OUT-R4',XY,[76,194],1.1);view('ODR-L34-OUT-R4',XZ,[76,127],1.1)
    view('ODR-L34-LOW-R4',XZ,[76,72],1.1)
    dim([76+48*1.1,194-48*1.1],[76+48*1.1,194+48*1.1],'Ø96',(8,0))
    notes(18,61,['OUT：Ø96圆板，厚8；中心Ø55.6贯穿。','16×Ø3.5 PCD62；4×M4贯通，X±35/Y±25。',
      'LOW：90×76×10板，外角R3；插头53.8×33.8，R3.2。','插头由LOW局部Z10延到26；中心Ø20贯穿。','LOW底面16×Ø6.4深3.5避让输出螺钉头。'],7.8,6.5)
    s.text(184,252,'RH20 输出真实孔阵：PCD62，16孔，0°起每22.5°',9,TEAL)
    for i,(x,y) in enumerate(op):s.text(184+(i//8)*108,239-(i%8)*8.5,f'{i+1:02d}: X{x:+8.4f} Y{y:+8.4f}',8)
    notes(184,159,['OUT四角M4底孔Ø3.3，厚8贯通；LOW四角Ø4.5贯穿10。','4×M4×16：穿LOW10，进入OUT6，距OUT底仍余2。',
      '4×M4×12侧螺钉：LOW局部Z18，Y±10，左右各2。','侧孔从X±26.9朝内；Ø3.3平底深14.9，完整牙深拟10。',
      '插头侧面到管外壁3.1；M4×12几何啮合8.9。','原厂输出M3全长TBD：只表示8板厚+3已证实通道。',
      'Ø55.6中央孔相对Ø55凸台，径向名义间隙0.30。','输出孔靠中央孔最小余肉31-27.8-1.75=1.45。','圆法兰覆盖q3全周：对L23上部Y名义间隙1。',
      '穿线孔和安装孔已体现在实体，尚无预紧或螺纹拔牙许可。'],8.3,8)
    footer(2)
    s.header('闭口梁与上端块','TUBE局部原点世界[0,55,238]；UP局部原点世界[0,55,314]；XYZ与世界同向。',REV)
    s.text(20,252,'TUBE / 1.05:1',8,TEAL);s.text(190,252,'UP / 1.15:1',8,TEAL);view('ODR-L34-TUBE-R4',XZ,[76,137],1.05);view('ODR-L34-TUBE-R4',XY,[76,97],1.05)
    dim([76+30*1.05,137],[76+30*1.05,137+92*1.05],'92',(10,0))
    notes(20,68,['原创截面：外60×40/内54×34，内外角均R3。','侧壁3；端面平整，长度92；不可直接替换任意市售管。',
      '8×Ø4.5侧孔：左右壁各4；局部Y±10、Z8和84。','每壁穿3；距两端均8；不把孔穿透误作同侧深孔。','两端插头各伸入16；侧面名义单边间隙0.10。'],8,6.5)
    view('ODR-L34-UP-R4',XY,[288,192],1.15);view('ODR-L34-UP-R4',XZ,[288,111],1.15)
    notes(190,99,['UP插头53.8×33.8/R3.2，从局部Z0到16；板90×76×10。','板从Z16到26；4×M4贯通接受后环底脚，X±35/Y±25。',
      '侧孔局部Z8、Y±10；从X±26.9向内钻Ø3.3平底深14.9。','完整牙深拟10；侧M4×12自由3.1/进入8.9。',
      '中心布线孔Ø16，中心[X0,Y5]，贯穿26。','UP上面贴后环底脚世界Z340；8侧螺钉合计用于上下两端。',
      '建议匹配尺寸（需加工评审）：插头宽/深 -0.05/+0；','内腔宽/深 +0.05/-0，以保持至少0.10单边名义间隙。',
      '端块接触、侧螺钉、间隙和管端局部变形仍需接触FEA。'],8.1,8)
    footer(3)
    s.header('整体后环、下舌与底脚 / ODR-L34-CARRIER-R4','局部原点世界[0,55,340]，XYZ与世界同向；J4固定后接触面世界Y37.5。',REV)
    view('ODR-L34-CARRIER-R4',XZ,[80,133],1.05);view('ODR-L34-CARRIER-R4',YZ,[222,133],1.05)
    s.text(22,252,'正视XZ / 1.05:1',9,TEAL);s.text(180,252,'侧视YZ / 1.05:1',9,TEAL)
    notes(20,112,['后环OD100/ID78.6，轴-Y，厚14；局部Y=-3.5至-17.5。','环心局部[X0,Z60]；下舌宽60，延到局部Z0。',
      '底脚90×76×10，外角R3，局部Z0～10；两处根圆角R2。','脚四角Ø4.5通孔X±35/Y±25；布线孔Ø16中心[X0,Y5]。',
      '固定螺纹8×M3×0.5，Ø2.5底孔贯通14；实际孔u/v见右侧。','在本零件坐标：X=u，Z=60+v；从Y=-3.5朝-Y钻。',
      'J4后壳Ø78与内孔Ø78.6仅0.30mm径向名义间隙。','固定M3大径至内孔边最小1.20mm，需防开裂/拔牙验证。',
      '原形尖角、其他工艺根角、刀具和表面方案仍需制造评审。'],8.1,8)
    s.text(291,252,'PCD84真实孔u/v（mm）',9,TEAL)
    for i,(x,y) in enumerate(fp):s.text(291,239-i*9,f'{i+1}: {x:+8.4f} / {y:+8.4f}',8)
    notes(291,158,['8×M3×40从J4前侧-Y装入。','自由跨30，进入本环10。','原厂接触跨度26，前环厚4。','尖端未穿出后环，距后面4。','4×M4×20从底脚上面+Z装。','自由跨10，进入UP10，名义齐平。','此组螺钉必须先于J4安装。'],8.2,8)
    footer(4)
    s.header('前压环与螺钉堆叠 / ODR-L34-FRONT-R4','局部原点世界[0,11.5,400]；局部X=世界X、Y=世界Z、Z=世界-Y。',REV)
    view('ODR-L34-FRONT-R4',XY,[83,181],1.25);view('ODR-L34-FRONT-R4',XZ,[83,99],1.25)
    dim([83-50*1.25,181+50*1.25],[83+50*1.25,181+50*1.25],'100',(0,6))
    notes(20,79,['视图1.25:1；OD100 / ID70.6，厚4；8×Ø3.5孔PCD84。','4×Ø6.2原装帽头避让孔：PCD84，0/90/180/270°。',
      '可沿输出方向-Y越过Ø70止口；名义径向间隙0.30。','原厂前面世界Y11.5；环外面Y7.5；M3头从7.5到4.5。','4个帽头避让孔外侧余肉4.90，非用于定位的过盈环。'],8,7.5)
    notes(201,251,['本研究合计40个螺钉：24个选长，16个原厂输出长TBD。','8×M4×12 / TR00005918-000 / Grade12.9 / self-colour','自由跨3.1，几何啮合8.9；侧孔完整牙拟10。',
      '4×M4×16 / TR00005927-000 / Grade12.9 / self-colour','自由跨10，进入OUT6；距OUT底2。',
      '4×M4×20 / TR00005935-000 / Grade12.9 / self-colour','自由跨10，进入UP10；尖端名义齐平，完整牙须扣倒角。',
      '8×M3×40 / Accu SSC-M3-40-12.9 / DIN912','最短螺纹18；头下22起有牙，覆盖30～40的啮合段。','M3头最大Ø5.68×3，2.5mm内六角。',
      'M4头研究包络Ø7.22×4 / 3mm内六角，来自Accu同规格。','TR提示DIN/ISO版本变更：下单前必须确认该批最大头径。','目录存在不等于实际库存；没有下单或选择预紧扭矩。',
      '16×J3输出M3：只表示已知11mm自由段，不能当完整螺钉。'],8.3,8)
    footer(5)
    s.header('装配证据与静力筛查','4.5kg完整头 + 2kg净物体；头COM760 / TCP890仍是旧几何；24mm延伸不在本轮模型。',REV)
    r=evidence['load_screening']['loadcases'][-1];c=r['scenarios'][0]
    notes(20,251,['装配：','1. J2/L23/J3已装，J4/J5尚未装。OUT从+Z落到J3。','2. 装16×输出M3（全长TBD）；LOW从+Z套住螺钉头。',
      '3. 4×M4×16锁LOW；梁从+Z套入下插头，再装下部侧M4。','4. UP从+Z进入梁，装上部侧M4；CARRIER从+Z贴UP。','5. 4×M4×20锁脚；J4从-Y方向插入后环。',
      '6. FRONT从-Y方向越过止口；8×M3×40沿+Y拧入。','装配有连续包络；q3全周相对J2/L23也已证实。','40个螺钉已知形状另做60mm连续插入检查。',
      '工具Ø4/M3、Ø5/M4×长60；不是完整手柄/手部模型。','静态含真实J2/J3/J4/J5，既有L23三件和28个螺钉。','实际孔位、接触面积、COM及惯量详见JSON/CSV。'],8.1,8)
    notes(225,251,[f'金属估重 {evidence["load_screening"]["original_mass_kg"]:.6f} kg + 紧固件预算0.15。','归属pre=3；关节模块COM仍为外形中点代理。',
      f'更新J2 / J3三角界：{r["revised_triangle_all_Nm"][1]:.2f} / {r["revised_triangle_all_Nm"][2]:.2f} Nm。',
      f'本连接最大截面静力界：{max(r["cut_gravity_moment_bounds_Nm"].values()):.2f} Nm。',
      f'COM不确定性后×1.5研究倍率：{c["moment_Nm"]:.2f} Nm。',
      f'闭口梁弯曲+轴向：{c["closed_beam_bending_plus_axial_MPa"]:.1f} MPa。',
      f'梁理想固支挠度：{c["closed_beam_cantilever_tip_deflection_mm"]:.3f} mm。',
      f'无孔均匀段扭转参考：{c["unperforated_tube_torsion_sensitivity_MPa"]:.1f} MPa。',
      f'输出板真实条带：{c["output_actual_plate_strip_MPa"]:.1f} MPa。',
      f'后环直梁敏感性：{c["collar_straight_cantilever_sensitivity_MPa"]:.1f} MPa。',
      '板/环条带不是整体结构的保守强度界。','80Nm另列纯接口作用，不是所有轴同时峰值。','动态rated不能当连续零速持载能力。'],8.2,8)
    notes(20,118,['尚未完成：原厂输出有效牙起止/全长、夹持许可、螺纹剥离与预紧、防松、接触FEA、疲劳、急停/碰撞载荷。','梁扭转参考不适用于有孔端部；插头、侧螺钉与间隙的载荷分配需要接触模型，不能只看梁低应力。'],8.3,8)
    notes(20,82,['候选公差：一般±0.10、孔中心±0.05、接触平面度0.05、螺纹6H；匹配插头/内腔尺寸另见第3页。','打印：板和环平放，插头沿Z；闭口梁竖直；后环脚朝床加支撑。关节必须外部承托，仅手动无载试装。',
      '尺寸、公差、表面与工艺需专业制造复核；公开文件不含原厂CAD，不代表关节全行程或内部线束已验证。'],8.2,8)
    footer(6);pdf.save();r=PdfReader(path);assert len(r.pages)==6 and all(len(p.extract_text())>150 for p in r.pages)


if __name__=='__main__':main()
