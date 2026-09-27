# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""J5-to-J6 metal load-path candidate, not a manufacturing release.

No third-party geometry is published. Source vendor STEP is provided by CLI and
hash-checked. Original threaded holes are shown as pilot drills, no helix.
"""
import argparse
import csv
import hashlib
import itertools
import json
from pathlib import Path
import cadquery as cq
import ezdxf
import trimesh
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Plane
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
from arm_screening import arm_parameters
from review_arm_screening import triangle_bounds
import numpy as np
from build_layout import frame,moved
from mount_interface_study import load_vendor,circular_features,bores,ring
from studies.link_interface_tools import check,cache,contact
ROOT=Path(__file__).resolve().parents[1]
PARAM_SHA='4349d1797b906b67a7bc396fcb84bc439c2d70dd0b337659e552cee293d2dd81'
REV='R4-LINK56-01'
DENSITY=2.7e-6
CORNER=np.array([[35,25],[-35,25],[-35,-25],[35,-25]],dtype=float)


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def rounded(w,d,r,z,h):
    return cq.Workplane('XY').workplane(offset=z).rect(w,d).extrude(h).edges('|Z').fillet(r)

def rect(w,d,z,h):return cq.Workplane('XY').workplane(offset=z).rect(w,d).extrude(h)

def cylinder(origin,axis,r,length):
    return moved(cq.Workplane('XY').circle(r).extrude(length).val(),frame(origin,axis))

def cut_side_pilots(shape,z):
    # Ends are blind flat-bottom Ø3.3 to depth14.9 from spigot side.
    # M4 effective tap-depth10 is a drawing process requirement.
    for sx in [-1,1]:
        for y in [-10,10]:
            shape=shape.cut(cylinder([sx*26.9,y,z],[-sx,0,0],1.65,14.9))
    return shape

def make_parts(iface):
    op=np.array([p['xy_mm'] for p in iface['output_holes']['points']])
    fp=np.array([p['xy_mm'] for p in iface['fixed_through_holes']['points']])
    # Coordinates of first four parts are relative to J5 output, +Z upward.
    adapter=rounded(84,64,3,0,6).cut(bores([[0,0]],23.8,-1,8)).cut(bores(op.tolist(),1.75,-1,8)).cut(bores(CORNER.tolist(),1.65,-1,8)).val()
    lower=rounded(84,64,3,6,10).union(rounded(53.8,33.8,3.2,16,16))
    lower=lower.cut(bores([[0,0]],10,5,28)).cut(bores(CORNER.tolist(),2.25,5,12))
    lower=lower.cut(bores(op.tolist(),3.2,5.9,3.6)).val()
    lower=cut_side_pilots(lower,24)
    beam=rounded(60,40,3,16,75).cut(rounded(54,34,3,15,77)).val()
    for z in [24,83]:
        for y in [-10,10]:beam=beam.cut(cylinder([-31,y,z],[1,0,0],2.25,62))
    upper=rounded(84,64,3,91,10).union(rounded(53.8,33.8,3.2,75,16))
    upper=upper.cut(bores([[0,-5]],8,74,28)).cut(bores(CORNER.tolist(),1.65,90,12)).val()
    upper=cut_side_pilots(upper,83)
    # Carrier in J6 local frame: +Z output; local Y=-world Z.
    # Foot and ring are one milled part, no unsupported floating tube ends.
    rear=ring(42,33.8,-49.7,14).union(cq.Workplane('XY').workplane(offset=-49.7).center(0,27).rect(60,54).extrude(14))
    rear=rear.cut(bores([[0,0]],33.8,-50,15)).cut(bores(fp.tolist(),1.25,-50,15)).val()
    T5=frame([0,-55,450],[0,0,1]);T6=frame([0,0,605],[0,1,0])
    rear_world=moved(rear,T6)
    foot=rounded(84,64,3,551,10).translate((0,-55,0)).cut(bores([[0,-60]],8,550,12)).cut(bores((CORNER+np.array([0,-55])).tolist(),2.25,550,12)).val()
    rear_world=rear_world.fuse(foot).clean()
    roots=[e for e in rear_world.Edges() if e.geomType()=='LINE' and e.BoundingBox().xlen>30 and abs(e.Center().z-561)<1e-6 and min(abs(e.Center().y+49.7),abs(e.Center().y+35.7))<1e-6]
    assert len(roots)==2
    rear_world=rear_world.fillet(2,roots).clean()
    front=ring(42,30.2,-10.5,3).cut(bores(fp.tolist(),1.75,-11,5)).cut(bores([[37,0],[-37,0],[0,37],[0,-37]],3.1,-11,5)).val()
    parts={'ODR-L56-OUT-R4':adapter,'ODR-L56-LOW-R4':lower.translate((0,0,-6)),
           'ODR-L56-TUBE-R4':beam.translate((0,0,-16)),'ODR-L56-UP-R4':upper.translate((0,0,-75)),
           'ODR-L56-CARRIER-R4':rear_world.translate((0,55,-551)),'ODR-L56-FRONT-R4':front.translate((0,0,10.5))}
    assembled={'output_adapter':moved(adapter,T5),'lower_block':moved(lower,T5),'closed_beam':moved(beam,T5),
               'upper_block':moved(upper,T5),'rear_carrier':rear_world,'front_ring':moved(front,T6)}
    for name,s in parts.items():assert s.isValid() and len(s.Solids())==1,(name,s.isValid(),len(s.Solids()))
    return parts,assembled,op,fp,T5,T6



def selected_faces(shape,origin,axis):
    origin=np.array(origin);axis=np.array(axis,dtype=float)
    result=[]
    for face in shape.Faces():
        surf=BRepAdaptor_Surface(face.wrapped)
        if surf.GetType()!=GeomAbs_Plane:continue
        plane=surf.Plane();normal=np.array(plane.Axis().Direction().Coord())
        if abs(abs(normal@axis)-1)>1e-7:continue
        if abs((np.array(face.Center().toTuple())-origin)@axis)<1e-5:result.append(face)
    return result


def face_contact(a,b,origin,axis):
    faces_a,faces_b=selected_faces(a,origin,axis),selected_faces(b,origin,axis)
    areas=[x.intersect(y).Area() for x in faces_a for y in faces_b]
    return {'origin_world_mm':origin,'normal_world':axis,'shared_planar_face_area_mm2':sum(areas),
            'method':'Boolean common of coplanar BREP faces; nominal undeformed contact footprint only'}


def make_hardware(op,fp,T5,T6):
    full={};free={};tools={};table=[]
    def bolt(name,seat,axis,d,L,H,D,freeL,owner,stage,engagement,selected=True):
        seat=np.array(seat);axis=np.array(axis,dtype=float)
        head=cylinder(seat,axis,D/2,H)
        shank=cylinder(seat,-axis,d/2,L)
        full[name]=head.fuse(shank)
        free[name]=head.fuse(cylinder(seat,-axis,d/2,freeL))
        tools[name]=cylinder(seat+axis*H,axis,2 if d==3 else 2.5,60)
        table.append({'id':name,'thread':'M%d'%d,'length_mm':L if selected else None,'seat_world_mm':seat.tolist(),
                      'head_outward_axis':axis.tolist(),'head_D_H_mm':[D,H],'nominal_engagement_mm':engagement,
                      'thread_owner':owner,'stage':stage,'length_selected':selected})
    for i,(x,y) in enumerate(op):
        seat=(T5@np.array([x,y,6,1]))[:3]
        bolt(f'OUT_M3_unknown_{i+1}',seat,[0,0,1],3,9,3,5.68,9,'J5',1,None,False)
    for i,(x,y) in enumerate(CORNER):
        bolt(f'LOW_M4x16_{i+1}',[x,y-55,466],[0,0,1],4,16,4,7.22,10,'output_adapter',2,6)
        bolt(f'FOOT_M4x20_{i+1}',[x,y-55,561],[0,0,1],4,20,4,7.22,10,'upper_block',5,10)
    for end,z,owner,stage in [('LOW',474,'lower_block',3),('UP',533,'upper_block',4)]:
        for sx,y in itertools.product([-1,1],[-10,10]):
            bolt(f'{end}_SIDE_M4x12_{sx}_{y}',[sx*30,y-55,z],[sx,0,0],4,12,4,7.22,3.1,owner,stage,8.9)
    for i,(x,y) in enumerate(fp):
        seat=(T6@np.array([x,y,-7.5,1]))[:3]
        bolt(f'FIX_M3x40_{i+1}',seat,[0,1,0],3,40,3,5.68,28.2,'rear_carrier',7,11.8)
    return full,free,tools,table


def check_assembly(assembled,vendors,hardware,free,tools,table):
    shapes={**assembled,**vendors};cached={n:cache(s) for n,s in shapes.items()}
    result={'static':{},'hardware':{},'tools':{},'motion_samples':[],'contacts':{}}
    for a,b in itertools.combinations(cached,2):
        if a.startswith('J') and b.startswith('J'):continue
        result['static'][a+'__'+b]=check(cached[a],cached[b])
    print('Checking40 screw free portions and staged tools',flush=True)
    for row in table:
        name=row['id'];hfull,hfree=cache(hardware[name]),cache(free[name])
        for other,target in cached.items():
            # Pilot holes do not remove modeled helix; only known thread-owner
            # engagement is excluded. Full bolt checked against every other part.
            probe=hfree if other==row['thread_owner'] else hfull
            result['hardware'][name+'__'+other]=check(probe,target)
        # Tool checks follow the specified partial assembly, not a claim of
        # future service access after installation of J7/head/adjacent links.
        present={1:['output_adapter','J5'],2:['output_adapter','lower_block','J5'],
                 3:['output_adapter','lower_block','closed_beam','J5'],
                 4:['output_adapter','lower_block','closed_beam','upper_block','J5'],
                 5:['output_adapter','lower_block','closed_beam','upper_block','rear_carrier','J5'],
                 7:list(assembled)+['J5','J6']}[row['stage']]
        for other in present:result['tools'][name+'__'+other]=check(tools[name],cached[other])
    # Check free hardware against one another, rather than fusing away contacts.
    for a,b in itertools.combinations(hardware,2):result['hardware'][a+'__'+b]=check(hardware[a],hardware[b])
    pairs=[('J5','output_adapter',[0,-55,450],[0,0,1]),
           ('output_adapter','lower_block',[0,-55,456],[0,0,1]),
           ('lower_block','closed_beam',[0,-55,466],[0,0,1]),
           ('closed_beam','upper_block',[0,-55,541],[0,0,1]),
           ('upper_block','rear_carrier',[0,-55,551],[0,0,1]),
           ('rear_carrier','J6',[0,-35.7,605],[0,1,0]),
           ('front_ring','J6',[0,-10.5,605],[0,1,0])]
    for a,b,o,z in pairs:
        result['contacts'][a+'__'+b]=face_contact(shapes[a],shapes[b],o,z)
        assert result['contacts'][a+'__'+b]['shared_planar_face_area_mm2']>10
    stages=[('lower_block',[0,0,1],30,['output_adapter','J5']),
            ('closed_beam',[0,0,1],100,['lower_block','output_adapter','J5']),
            ('upper_block',[0,0,1],30,['closed_beam','lower_block','output_adapter','J5']),
            ('rear_carrier',[0,0,1],100,['upper_block','closed_beam','lower_block','output_adapter','J5']),
            ('J6',[0,1,0],160,['rear_carrier','upper_block','closed_beam','lower_block','output_adapter','J5']),
            ('front_ring',[0,1,0],120,['J6','rear_carrier','upper_block','closed_beam','lower_block','output_adapter','J5'])]
    for stage_index,(moving,direction,start,stationary) in enumerate(stages,2):
        print('Insertion',moving,flush=True)
        samples=[]
        targetmap={other:cached[other] for other in stationary}
        for row in table:
            if row['stage']<stage_index:targetmap[row['id']]=cache(hardware[row['id']])
        for dist in sorted(set([0,.1,.5,1,2,*range(5,start+1,5)])):
            probe=shapes[moving].translate(tuple(np.array(direction)*dist))
            for other,target in targetmap.items():
                outcome=check(probe,target)
                if outcome['events']:samples.append({'translation_mm':dist,'other':other,**outcome})
        result['motion_samples'].append({'moving':moving,'direction_from_final':direction,'start_distance_mm':start,
              'steps_mm':'0, 0.1, 0.5, 1, 2 then every 5 mm','stationary':stationary,'collisions':samples,
              'scope':'discrete straight insertion samples; not continuous swept-volume or cable/hand clearance proof'})
    return result


def section_properties(beam,z):
    t=.001
    slab=rect(100,100,z-t/2,t).val();section=beam.intersect(slab)
    props=GProp_GProps();BRepGProp.VolumeProperties_s(section.wrapped,props)
    area=props.Mass()/t;mat=props.MatrixOfInertia()
    return {'z_mm':z,'area_mm2':area,'Ix_mm4':mat.Value(1,1)/t-area*t*t/12,
            'Iy_mm4':mat.Value(2,2)/t-area*t*t/12,'sampling_thickness_mm':t}


def load_screen(p,parts,assembled,op,fp):
    section=[section_properties(parts['ODR-L56-TUBE-R4'],z) for z in [8,37.5,67]]
    Imin=min(min(s['Ix_mm4'],s['Iy_mm4']) for s in section);Amin=min(s['area_mm2'] for s in section)
    assert 30/Imin>=np.hypot(20/min(s['Ix_mm4'] for s in section),30/min(s['Iy_mm4'] for s in section))
    median_area=57*37;Jmid=4*median_area**2/(2*(57+37)/3);shear_modulus=70000/(2*(1+.33))
    original_mass=sum(s.Volume()*DENSITY for s in parts.values());hardware_reserve=.1
    rows=[];G=9.80665;E=70000;L=75
    group_error=0
    for points in [CORNER,op,fp]:
        assert np.linalg.norm(points.mean(axis=0))<1e-6
        for angle in np.linspace(0,2*np.pi,361):
            Mtest=np.array([np.cos(angle),np.sin(angle)])*1000
            reaction=points@np.linalg.solve(points.T@points,[-Mtest[1],Mtest[0]])
            recovered=np.array([reaction@points[:,1],-reaction@points[:,0]])
            group_error=max(group_error,float(np.max(np.abs(recovered-Mtest))))
    assert group_error<1e-8
    for head_mass in [2,3.5,4,4.5]:
        model=arm_parameters(p,head_mass)
        nominal=triangle_bounds(model)[0]
        model['bodies']=[b for b in model['bodies'] if b['id']!='L5_budget']
        for name,s in assembled.items():
            model['bodies'].append({'id':'link56_'+name,'mass_kg':s.Volume()*DENSITY,'preceding_joints':5,'com_home_m':(np.array(s.Center().toTuple())*.001).tolist()})
        model['bodies'].append({'id':'L56_hardware_reserve','mass_kg':hardware_reserve,'preceding_joints':5,'com_home_m':[0,-.055,.55]})
        revised=triangle_bounds(model)[0];mass=sum(b['mass_kg'] for b in model['bodies'] if b['preceding_joints']>4)
        # Head COM uncertainty50mm, object COM offset100mm, study multiplier1.5.
        # Bound on full 3D gravity moment magnitude, not solely motor-axis torque.
        cut_bounds={}
        for name,point in {'output':[0,-55,450],'lower':[0,-55,466],'upper':[0,-55,541],
                           'foot':[0,-55,551],'rear':[0,-35.7,605],'front':[0,-10.5,605]}.items():
            P=np.array(point)*.001;bound=0
            for b in model['bodies']:
                n=b['preceding_joints']
                if n<5:continue
                com=np.array(b['com_home_m'])
                if n==5:distance=np.linalg.norm(com-P)
                else:
                    nodes=[P]+[np.array(model['joints'][k]['origin_m']) for k in range(5,n)]+[com]
                    distance=sum(np.linalg.norm(b-a) for a,b in zip(nodes,nodes[1:]))
                bound+=b['mass_kg']*G*distance
            cut_bounds[name]=float(bound)
        expanded=max(cut_bounds.values())+head_mass*G*.05+2*G*.1;M=1.5*expanded*1000;F=1.5*mass*G
        max_m4=F/4+M*max(np.hypot(y/np.sum(CORNER[:,1]**2),x/np.sum(CORNER[:,0]**2)) for x,y in CORNER)
        S=fp.T@fp;inv=np.linalg.inv(S)
        m3max=F/len(fp)+M*max(np.linalg.norm(inv@r) for r in fp)
        outputmax=F/len(op)+M*max(np.linalg.norm(np.linalg.inv(op.T@op)@r) for r in op)
        sigma_beam=M*30/Imin+F/Amin
        delta=M*L*L/(2*E*Imin)+F*L**3/(3*E*Imin)
        theta=M*L/(E*Imin)+F*L*L/(2*E*Imin)
        # Local plate and fork models are sensitivity estimates, not bounds on
        # contact/prying or curved-ring stresses. No preload is inferred.
        overhang=float(np.linalg.norm(CORNER[0])-29.5)
        strip_sigma=6*max_m4*overhang/(12*6**2)
        forkI=2*8.2*14**3/12;forkA=2*8.2*14
        fork_sigma=M*7/forkI+F/forkA
        rows.append({'head_mass_kg':head_mass,'net_object_kg':2,'head_COM_home_mm':[0,55,760],
                     'old_budget_triangle_J5_J6_Nm':nominal[4:6].tolist(),'updated_triangle_J5_J6_Nm':revised[4:6].tolist(),'updated_triangle_all_joints_Nm':revised.tolist(),
                     'cut_moment_triangle_bounds_Nm':cut_bounds,'updated_downstream_mass_J5_kg':mass,'COM_uncertainty_moment_Nm':head_mass*G*.05+2*G*.1,
                     'design_screening_moment_Nm':M/1000,'design_screening_force_N':F,'study_multiplier':1.5,
                     'side_M4_max_shear_demand_N':F/4+M*np.hypot(1/(4*10),1/(4*28.5)),
                     'side_M4_tube_nominal_bearing_stress_MPa':(F/4+M*np.hypot(1/(4*10),1/(4*28.5)))/(4*3),
                     'side_M4_end_tearout_average_shear_MPa':(F/4+M*np.hypot(1/(4*10),1/(4*28.5)))/(2*(8-4.5/2)*3),
                     'beam_axial_plus_bending_stress_MPa':sigma_beam,'beam_deflection_mm':delta,'beam_rotation_deg':float(np.rad2deg(theta)),
                     'unperforated_midspan_torsion_sensitivity_MPa':M/(2*median_area*3),
                     'unperforated_midspan_twist_sensitivity_deg':float(np.rad2deg(M*75/(shear_modulus*Jmid))),
                     'combined_bending_torsion_full_each_sensitivity_MPa':float(np.hypot(sigma_beam,np.sqrt(3)*M/(2*median_area*3))),
                     'M4_corner_max_axial_demand_N':max_m4,'M3_fixed_max_axial_demand_N':m3max,'M3_output_max_axial_demand_N':outputmax,
                     'M4_corner_shear_demand_N':F/4+M/(4*np.linalg.norm(CORNER[0])),
                     'M3_fixed_shear_demand_N':F/8+M/(8*37), 'M3_output_shear_demand_N':F/16+M/(16*27),
                     'output_plate_12mm_strip_bending_sensitivity_MPa':strip_sigma,
                     'rear_ring_two_8_2x14_legs_bending_sensitivity_MPa':fork_sigma,
                     'required_total_output_preload_for_mu_sensitivity_N':{str(mu):M/(mu*27) for mu in [.08,.15,.2]}})
    return {'original_mass_kg':original_mass,'hardware_mass_budget_kg':hardware_reserve,'link56_mass_budget_kg':original_mass+hardware_reserve,
            'bolt_group_moment_recovery_max_error_Nmm':group_error,'replaces_L5_budget_kg':p['link_budgets_kg'][4],'section_properties':section,'E_N_mm2':E,
            'torsion_model':'thin closed rectangle midline57x37,t3; G=E/(2*(1+nu)),nu=.33 assumed; unperforated midspan only; drilled end-section warping and stress concentration NOT bounded',
            'beam_model':'75mm cantilever, minimal sampled net inertia used along full span; M*c/I + F/A with c=30, delta=ML²/(2EI)+FL³/(3EI); excludes joint compliance',
            'loadcases':rows,'status':'strength/stiffness screening only; contact, preload, thread-strip, fatigue and FEA not qualified',
            'side_screw_model':'four equal-stiffness bearing points at x=±28.5,y=±10; force/4+M*hypot(1/40,1/114); bearing uses d*t=4*3, end tear-out uses2*(8-2.25)*3; no clearance/slip/fatigue/contact concentration resolution',
            'ring_model':'sensitivity only: two straight8.2x14mm legs, not a solution of the curved/slotted collar; distributed bolt loads not resolved',
            'plate_model':'sensitivity only:12mm radial strip from r29.5 to corner bolt radius; not a proven conservative plate/contact bound',
            'material_source':'thyssenkrupp EN AW-6061 sheet p2-3; density2.70g/cm3,E70000N/mm2,T6minimumRp0.2=240MPa in listed size ranges; no batch certificate'}


def feature_rows(op,fp):
    rows=[]
    def add(part,feature,points,axis,diameter,zref,depth,thread=''):
        for i,p in enumerate(points):rows.append({'part':part,'feature':feature,'number':i+1,'x_mm':float(p[0]),'y_mm':float(p[1]),'z_mm':zref,'axis':axis,'diameter_mm':diameter,'depth_mm':depth,'thread':thread})
    add('OUT','J5 output clearance',op,'+Z',3.5,0,6)
    add('OUT','corner tap',CORNER,'+Z',3.3,0,6,'M4x0.7 THRU; candidate6H')
    add('LOW','corner clearance',CORNER,'+Z',4.5,0,10)
    add('LOW','J5 cap-head recess',op,'+Z',6.4,0,3.5)
    add('LOW','cable',[[0,0]],'+Z',20,0,26)
    add('UP','corner tap',CORNER,'+Z',3.3,16,10,'M4x0.7 THRU; candidate6H')
    add('UP','cable',[[0,-5]],'+Z',16,0,26)
    add('CARRIER','foot clearance',CORNER,'+Z',4.5,0,10)
    add('CARRIER','cable exit',[[0,-5]],'+Z',16,0,10)
    # Carrier coordinate system is world translation only; holes point along+Y.
    for i,(x,y) in enumerate(fp):rows.append({'part':'CARRIER','feature':'J6 fixed through tap','number':i+1,'x_mm':float(x),'y_mm':5.3,'z_mm':54-float(y),'axis':'+Y','diameter_mm':2.5,'depth_mm':14,'thread':'M3x0.5 THRU; candidate6H'})
    add('FRONT','J6 fixed clearance',fp,'+Z',3.5,0,3)
    add('FRONT','OEM cap-head relief',[[37,0],[-37,0],[0,37],[0,-37]],'+Z',6.2,0,3)
    for part,zlist in [('LOW',[18]),('UP',[8]),('TUBE',[8,67])]:
        for z in zlist:
            for sx,y in itertools.product([-1,1],[-10,10]):
                rows.append({'part':part,'feature':'side pin/tap' if part!='TUBE' else 'side clearance','number':len(rows)+1,
                   'x_mm':sx*(30 if part=='TUBE' else 26.9),'y_mm':y,'z_mm':z,'axis':'-X' if sx>0 else '+X',
                   'diameter_mm':4.5 if part=='TUBE' else 3.3,'depth_mm':3 if part=='TUBE' else 14.9,
                   'thread':'' if part=='TUBE' else 'M4x0.7 effective depth10; flat-bottom pilot14.9'})
    return rows



def projected_edges(mesh,basis):
    """Orthographic contour, retaining edges where one face is exactly edge-on."""
    normal=np.cross(basis[0],basis[1]);adj=mesh.face_adjacency;n=mesh.face_normals
    pair_dot=np.einsum('ij,ij->i',n[adj[:,0]],n[adj[:,1]])
    vd=n@normal;a,b=vd[adj[:,0]],vd[adj[:,1]];eps=1e-10
    tangent=((abs(a)<eps)&(abs(b)>=eps))|((abs(b)<eps)&(abs(a)>=eps))
    silhouette=(a*b<-eps)|tangent
    edges=mesh.face_adjacency_edges[silhouette|(pair_dot<np.cos(np.deg2rad(25)))]
    counts=np.bincount(mesh.edges_unique_inverse,minlength=len(mesh.edges_unique))
    edges=np.vstack([edges,mesh.edges_unique[counts==1]])
    points=mesh.vertices[edges]@basis.T
    seen=set();result=[]
    for line in points:
        if np.linalg.norm(line[1]-line[0])<1e-6:continue
        ends=sorted(tuple(v) for v in np.round(line,6));key=tuple(ends[0]+ends[1])
        if key not in seen:seen.add(key);result.append(line)
    return np.asarray(result)

def export_original(out,parts,assembled,op,fp):
    from build_base_study import export_parts
    info=export_parts(out,parts);meshes={}
    for name in parts:
        meshes[name]=trimesh.load_mesh(out/(name+'.stl'),process=True)
        d=ezdxf.new('R2010');d.units=ezdxf.units.MM;ms=d.modelspace()
        bases=[np.array([[1,0,0],[0,1,0]]),np.array([[1,0,0],[0,0,1]]),np.array([[0,1,0],[0,0,1]])]
        for label,basis,offset in zip(['TOP_XY','FRONT_XZ','SIDE_YZ'],bases,[[0,0],[0,-160],[160,-160]]):
            d.layers.new(label)
            for line in projected_edges(meshes[name],basis):ms.add_line(tuple(line[0]+offset),tuple(line[1]+offset),dxfattribs={'layer':label})
        # Exact circular features complement discretized orthographic mesh edges.
        short=name.split('-')[2]
        for row in feature_rows(op,fp):
            if row['part']==short and row['axis']=='+Z':ms.add_circle((row['x_mm'],row['y_mm']),row['diameter_mm']/2)
        ms.add_text(name+' / mm / 1:1 MODEL SPACE / CANDIDATE NOT RELEASED',dxfattribs={'height':3}).set_placement((-50,-190))
        ms.add_text('Thread pilots, depth and datums per PDF + hole-features.csv; projected edges are not cutter paths.',dxfattribs={'height':2.3}).set_placement((-50,-196))
        dp=out/(name+'.dxf');d.saveas(dp);r=ezdxf.readfile(dp);assert not r.audit().errors
        info[name]['dxf_audit_passed']=True;info[name]['sha256'][dp.name]=sha(dp)
    assembly=cq.Assembly(name='ODR_LINK56_ORIGINAL_CANDIDATE')
    for n,s in assembled.items():assembly.add(s,name=n)
    ap=out/'ODR-LINK56-original-assembly.step';cq.exporters.export(assembly.toCompound(),str(ap))
    read=cq.importers.importStep(str(ap)).val();assert read.isValid() and len(read.Solids())==6
    placements={}
    identifiers={'output_adapter':'OUT','lower_block':'LOW','closed_beam':'TUBE','upper_block':'UP','rear_carrier':'CARRIER','front_ring':'FRONT'}
    heights={'OUT':450,'LOW':456,'TUBE':466,'UP':525,'CARRIER':551}
    for instance,short in identifiers.items():
        name='ODR-L56-'+short+'-R4'
        T=frame([0,-10.5,605],[0,1,0]) if short=='FRONT' else frame([0,-55,heights[short]],[0,0,1])
        transformed=moved(parts[name],T)
        assert np.linalg.norm(np.array(transformed.Center().toTuple())-assembled[instance].Center().toTuple())<1e-6
        placements[instance]={'part_id':name,'T_world_from_part_mm':T.tolist(),'preceding_joints':5,
                              'estimated_COM_world_mm':list(assembled[instance].Center().toTuple()),'mass_kg_6061':assembled[instance].Volume()*DENSITY}
    (out/'part-placements.json').write_text(json.dumps({'revision':REV,'parameters_sha256':PARAM_SHA,'status':'independent candidate; no shared layout modified','instances':placements},indent=2)+'\n')
    rows=feature_rows(op,fp)
    with (out/'hole-features.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    return info,meshes


def make_pdf(path,font,parts,assembled,meshes,evidence,op,fp):
    from reportlab.lib.pagesizes import A3,landscape
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas
    from draw_layout import Sheet,TEAL,GRAY,LIGHT,AMBER
    from pypdf import PdfReader
    pdfmetrics.registerFont(TTFont('Link56CN',str(font)));pdf=canvas.Canvas(str(path),pagesize=landscape(A3),pageCompression=1)
    pdf.setTitle('Odradek J5-J6 candidate dimensions - NOT RELEASED');pdf.setAuthor('Auromix contributors');s=Sheet(pdf,'Link56CN')
    XY=np.array([[1,0,0],[0,1,0]]);XZ=np.array([[1,0,0],[0,0,1]]);YZ=np.array([[0,1,0],[0,0,1]])
    def notes(x,y,lines,size=8.5,step=7):
        for k,line in enumerate(lines):s.text(x,y-k*step,line,size)
    def view(name,basis,origin,scale=1,color=TEAL):
        for edge in projected_edges(meshes[name],basis):s.line(np.array(origin)+edge[0]*scale,np.array(origin)+edge[1]*scale,color,.35)
    def dim(a,b,label,offset=(0,0)):
        a=np.array(a,dtype=float);b=np.array(b,dtype=float);off=np.array(offset,dtype=float);s.line(a,a+off,GRAY,.3);s.line(b,b+off,GRAY,.3)
        s.arrow(a+off,b+off,GRAY,.4);s.arrow(b+off,a+off,GRAY,.4)
        s.text(*((a+b)/2+off+np.array([0,2])),label,8,GRAY,'center')
    def footer(page):
        s.line((15,16),(405,16),GRAY,.4)
        s.text(15,10,'单位 mm | 6061-T6 金属候选 / 打印仅无载试装 | 螺纹以底孔表示 | 禁止制造放行和负载验收',8)
        s.text(405,10,f'{page}/6 | A3 横向 | {REV}',8,align='right');pdf.showPage()
    s.header('J5 → J6 完整连接候选','R4-layout-03 原点保持；真实接触面 → 输出板 → 端块 → 闭口梁 → 带脚后环 → J6 固定法兰',REV)
    # World orthographic projections of our original assembly, shifted to J5.
    for index,(basis,origin) in enumerate([(XZ,[85,62]),(YZ,[240,62])]):
        for name,shape in assembled.items():
            vertices,faces=shape.tessellate(.1,.1)
            mesh=trimesh.Trimesh(vertices=[v.toTuple() for v in vertices],faces=faces,process=True)
            for edge in projected_edges(mesh,basis):
                q=(edge-np.array([0,450]) if index==0 else edge-np.array([-55,450]))*.9+origin
                s.line(q[0],q[1],TEAL,.35)
        s.text(origin[0]-48,251,'正视 XZ / 0.9:1' if index==0 else '侧视 YZ / 0.9:1',10,TEAL)
    # Dimension-derived flange envelope clarifies the load path between our
    # separated retaining faces without publishing any third-party BREP edges.
    x0,x1=240+.9*(-35.7+55),240+.9*(-10.5+55)
    y0,y1=62+.9*(605-39.7-450),62+.9*(605+39.7-450)
    for a0,b0 in [([x0,y0],[x1,y0]),([x1,y0],[x1,y1]),([x1,y1],[x0,y1]),([x0,y1],[x0,y0])]:s.line(a0,b0,GRAY,.4,dash=[2,2])
    for y in np.arange(y0+1,y1-5,5):s.line([x0+1,y],[x1-1,min(y+8,y1-1)],LIGHT,.35)
    notes(309,229,['虚线/浅斜线：原厂固定法兰','尺寸包络示意，非原厂CAD。','夹持间隔25.2，实体并不悬空。'],7.5,6)
    for z,label in [(450,'J5输出 450'),(456,'输出板/端块456'),(466,'梁下端466'),(541,'梁上端541'),(551,'后环脚底551'),(605,'J6轴心605'),(647,'后环顶647')]:
        y=62+(z-450)*.9;s.line((285,y),(309,y),GRAY,.3);s.text(311,y-1,label,8)
    notes(15,48,[f'原创零件质量 {evidence["load_screening"]["original_mass_kg"]:.3f} kg；紧固件预算0.10 kg。旧 L5=0.50 kg 被本研究独立替换，主参数未改。',
                 'J5=[0,-55,450], +Z；J6=[0,0,605], +Y。后接触Y=-35.7，前接触Y=-10.5。',
                 '视图不含第三方实体；完整原厂 STEP 只在本地做逐 solid 碰撞。原厂两套 RH17 并非圆柱近似。'],8.5)
    footer(1)

    s.header('输出安装板 / ODR-L56-OUT-R4','基准 A：底面 z=0；零件 XY 与 J5 unified frame 同向。此页孔位为真实非均布阵列。',REV)
    name='ODR-L56-OUT-R4';view(name,XY,[93,178],1.6);view(name,XZ,[93,83],1.6)
    dim([93-42*1.6,178+32*1.6],[93+42*1.6,178+32*1.6],'84',offset=[0,10]);dim([93-42*1.6,83],[93-42*1.6,83+6*1.6],'6',offset=[-8,0])
    s.text(20,250,'顶视1.6:1；下为侧视',10,TEAL)
    notes(20, 65,['84×64×6；外角R3；中央Ø47.6贯通（避让Ø47凸台，不作定位）。',
                       '16×Ø3.5贯通 / PCD54；4×M4×0.7贯通，坐标X=±35/Y=±25。',
                       '接触原厂输出 annulus r23.8～29.5；输出内孔余边小，不能凭材料屈服值放行。',
                       '输出M3长度未选：图示退距9.6、深6；STEP退距9.5，完整有效螺纹需厂家确认。'],8)
    s.text(206,251,'16 个输出孔中心（mm）',10,TEAL)
    for i,(x,y) in enumerate(op):
        col=i//8;row=i%8;s.text(205+col*100,239-row*9,f'{i+1:02d}  X{x:+8.4f}  Y{y:+8.4f}',8)
    notes(205,155,['候选加工要求，尚未审核：','• 孔中心相对XY基准±0.05；一般线性±0.10。',
                   '• 接触面平面度0.05；通孔Ø3.5(+0.10/0)。','• 自制M4建议6H，去毛刺；入口倒角消耗有效啮合。',
                   '• 所有公差须在原厂实物/CMM及加工评审后冻结。','• 不拆用或覆盖原厂自己的装配螺钉。'],8.5)
    footer(2)

    s.header('实体端块 / LOW 与 UP','两件有不同贯孔、螺纹和插接方向；不得互换。全部为原创建议尺寸。',REV)
    for name,ox,label in [('ODR-L56-LOW-R4',105,'LOW：底面z=0，安装世界Z=456'),('ODR-L56-UP-R4',306,'UP：插头底z=0，安装世界Z=525')]:
        view(name,XY,[ox,197],1.5);view(name,XZ,[ox,100],1.5);s.text(ox-84,253,label,10,TEAL)
        dim([ox-42*1.5,197+32*1.5],[ox+42*1.5,197+32*1.5],'84',offset=[0,6])
    notes(20,96,['LOW 外板84×64×10，z0～10；插头53.8×33.8，R3.2，z10～26。',
                 '中央Ø20贯通；4×Ø4.5，X±35/Y±25。',
                 '底面16×Ø6.4平底让位深3.5，使用第2页输出孔坐标。',
                 '四侧M4：X=±26.9，Y=±10，Z=18；沿±X向内。',
                 'Ø3.3平底孔深14.9；有效螺纹深度要求10；M4×12啮合8.9。',
                 '4×M4×16从上方装入，跨10mm板进入OUT约6mm。'],8)
    notes(219,96,['UP 插头53.8×33.8，R3.2，z0～16；板84×64×10，z16～26。',
                  'Ø16贯通中心[0,-5]；4×M4贯通板，X±35/Y±25。',
                  '四侧M4：X=±26.9，Y=±10，Z=8；沿±X向内。',
                  'Ø3.3平底孔深14.9；有效螺纹深度要求10；M4×12啮合8.9。',
                  '与后环脚用4×M4×20，跨10mm脚进入UP板约10mm。',
                  '插头尺寸建议0/-0.05；梁内腔+0.10/0。每侧名义间隙0.10。'],8)
    footer(3)

    s.header('闭口梁 / ODR-L56-TUBE-R4','本件从实体铣出通腔；不用未经尺寸验证的市场矩形管替代。基准A：下端z=0。',REV)
    name='ODR-L56-TUBE-R4';view(name,XY,[87,202],1.8);view(name,XZ,[225,90],1.8);view(name,YZ,[346,90],1.8)
    s.text(35,253,'顶视1.8:1',10,TEAL);s.text(180,253,'正视 XZ / 1.8:1',10,TEAL);s.text(306,253,'侧视 YZ / 1.8:1',10,TEAL)
    dim([33,238],[141,238],'60',offset=[0,5]);dim([279,90],[279,225],'75',offset=[8,0])
    notes(20,136,['外60×40，外角R3；内54×34，内角R3。','总长75；名义壁厚3；两端面与端块平贴。',
                  '下/上插头各进入16；无填充胶或焊接。','8×Ø4.5侧通孔：X=±30，Y=±10；','Z=8与67；孔轴沿X，穿单壁约3。'],9)
    notes(20, 76,['世界梁底Z=466、梁顶Z=541；中心Y=-55。',
                         '先插入下端块并装下部4螺钉，再装上端块与上部4螺钉。',
                         '侧M4×12名义自由穿过3.1（壁3+装配间隙0.1），进入端块8.9。',
                         '全长试算取最弱带孔截面；不包含端部滑移、疲劳和局部孔口应力集中。'],8.5)
    footer(4)

    s.header('J6 带脚后环与前压环','后环为整体铣削件；不得把独立圆环悬空接在梁旁边。环抱后壳，保留前后原厂接触面。',REV)
    name='ODR-L56-CARRIER-R4';view(name,XZ,[85,104],1.45);view(name,YZ,[248,104],1.45)
    s.text(22,254,'后环正视XZ / 1.45:1',10,TEAL);s.text(202,254,'后环侧视YZ / 1.45:1',10,TEAL)
    dim([85-42*1.45,104+96*1.45],[85+42*1.45,104+96*1.45],'84',offset=[0,6])
    notes(20, 91,['CARRIER局部坐标：世界坐标减[0,-55,551]。脚84×64×10，角R3。',
                         '环心[0,19.3,54]，轴+Y；OD84/ID67.6；后Y=5.3、前Y=19.3，厚14。',
                         '下舌宽60，X±30，Z0～54；与脚前/后内根R2。环顶Z96。',
                         '8×M3×0.5贯通，孔轴Y，X及Z=54−v见右侧坐标表。',
                         '脚4×Ø4.5，X±35/Y±25；Ø16出口[0,-5]。后壳有0.3径向名义避让。',
                         '前压环：OD84/ID60.4/厚3；8×Ø3.5与后环同阵列，另4×Ø6.2让原装头。'],8)
    view('ODR-L56-FRONT-R4',XY,[355,211],.75)
    s.text(317,251,'FRONT / 0.75:1',9,TEAL)
    s.text(305,171,'固定孔：X / v（J6局部平面）',8,TEAL)
    for i,(x,y) in enumerate(fp):s.text(305,162-i*8,f'{i+1}  {x:+8.4f} / {y:+8.4f}',8)
    notes(305, 80,['FRONT基准A底面z=0；安装local z=-10.5。','原装头让位：PCD74，0/90/180/270°。',
                         'M3×40：3+25.2自由跨距，进入后环11.8；','后环贯通厚14，螺钉尖距后面名义2.2。'],8)
    footer(5)

    s.header('装配与载荷筛查','整条金属接触路径已量化；预紧、原厂螺纹、疲劳与实物承载仍未放行。',REV)
    checks=evidence['checks'];loads=evidence['load_screening'];maxrow=loads['loadcases'][-1]
    notes(20,251,['顺序（装配时 J7、头部及其连架尚未安装）：',
                  '1. 先单独固定OUT到J5；16个M3头均可从+Z接近，长度待厂家证实。',
                  '2. LOW从+Z套住输出螺钉头，用4×M4×16固定。',
                  '3. 直梁从+Z套LOW，四侧M4×12固定；再从+Z装UP及四侧M4×12。',
                  '4. 带脚后环从+Z落在UP，用4×M4×20固定；此时还未装J6。',
                  '5. J6从+Y穿过后环至后接触面；再从+Y装前环，用8×M3×40夹持。',
                  '6. 随后另做J6→J7连接。J7装上后不能沿用本页扳手可达结论。'],8.5)
    s.text(20,195,'名义平面接触面积 / mm²',10,TEAL)
    for i,(key,c) in enumerate(checks['contacts'].items()):s.text(20,184-i*8,f'{key}: {c["shared_planar_face_area_mm2"]:.2f}',8)
    notes(20,116,['工具探针：M3直杆Ø4×60；M4直杆Ø5×60，只证实直杆路径。',
                  '插入检查：0/0.1/0.5/1/2mm，随后每5mm；不构成连续扫掠证明。',
                  '紧固件穿入底孔的预期啮合不记为干涉；自由杆段及其他实体逐对检查。',
                  '所有连接依靠已设计接触面与螺钉；无已确定预紧值，不宣称抗滑已达标。'],8)
    s.text(225,251,'静力情景：头重 / J5更新bound / 设计筛查Nm',9,TEAL)
    for i,r in enumerate(loads['loadcases']):s.text(225,238-i*9,f'{r["head_mass_kg"]:.1f} kg  /  {r["updated_triangle_J5_J6_Nm"][0]:.3f} Nm  /  {r["design_screening_moment_Nm"]:.3f} Nm',9)
    notes(225,196,[f'4.5kg头+2kg工件；临时头COM仍[0,55,760]。',
                   '追加工件COM±100mm、头COM±50mm，并乘研究系数1.5。',
                   f'力筛查 {maxrow["design_screening_force_N"]:.1f} N；梁应力 {maxrow["beam_axial_plus_bending_stress_MPa"]:.2f} MPa。',
                   f'梁挠度 {maxrow["beam_deflection_mm"]:.4f} mm；转角 {maxrow["beam_rotation_deg"]:.4f}°。',
                   f'四角M4最大拉力需求 {maxrow["M4_corner_max_axial_demand_N"]:.1f} N/颗。',
                   f'固定侧M3最大拉力需求 {maxrow["M3_fixed_max_axial_demand_N"]:.1f} N/颗。',
                   f'输出板条带敏感性 {maxrow["output_plate_12mm_strip_bending_sensitivity_MPa"]:.1f} MPa。',
                   f'后环双腿敏感性 {maxrow["rear_ring_two_8_2x14_legs_bending_sensitivity_MPa"]:.1f} MPa。',
                   f'侧M4剪力需求 {maxrow["side_M4_max_shear_demand_N"]:.0f} N；孔壁承压 {maxrow["side_M4_tube_nominal_bearing_stress_MPa"]:.1f} MPa。',
                   f'梁端剪出平均 {maxrow["side_M4_end_tearout_average_shear_MPa"]:.1f} MPa，孔口疲劳未验证。',
                   '条带/双腿模型不是已证明保守的局部应力解；需接触FEA与实测。'],8.5)
    notes(20, 68,['主要阻断项：输出有效螺纹起止/允许拧紧值、夹持面摩擦/预紧、1.7mm薄边M3螺纹拉脱、关节轴承载荷与零速保持。',
                         '材料候选6061-T6，E=70GPa、密度2700kg/m³；材料批证、真实COM、加工公差与表面处理仍待确认。',
                         'STL打印只做手动无载试装；禁用本研究中的静力数字证明塑料件、整机、动态或疲劳性能。',
                         '内走线只预留通孔，原厂接插件与最小弯曲半径仍需验证；驱动额定运行扭矩不能当持续静止扭矩。'],8)
    footer(6);pdf.save();assert len(PdfReader(path).pages)==6


def write_bom(out,parts,table):
    sources={
      'M3x40':{'part':'Accu SSC-M3-40-12.9','url':'https://www.accu.co.uk/metric-cap-head-screws/16011-SSC-M3-40-12-9','dimensions':'headD5.68/H3, key2.5, minthread18; length40'},
      'M4x12':{'part':'TR00005918-000 / W/M4/12/SO12CS','url':'https://www.trfastenings.com/products/catalogue/screws-and-bolts/hexagon-socket-screws/cap-head/tr00006369/tr00005063/tr00005810/tr00006352/TR00005918-000','availability':'cataloguePreferred; stock/order not confirmed'},
      'M4x16':{'part':'TR00005927-000 / W/M4/16/SO12CS','url':'https://www.trfastenings.com/Products/Catalogue/Screws-and-Bolts/Hexagon-Socket-Screws/Cap-Head/TR00005927-000','availability':'cataloguePreferred; stock/order not confirmed'},
      'M4x20':{'part':'TR00005935-000 / W/M4/20/SO12CS','url':'https://www.trfastenings.com/products/catalogue/screws-and-bolts/hexagon-socket-screws/cap-head/tr00006369/tr00005063/tr00005810/tr00006352/TR00005935-000','availability':'cataloguePreferred; stock/order not confirmed'},
      'M4dimension_crosscheck':{'part':'Accu SSCF-M4-12-12.9 / SSCF-M4-16-12.9 / SSCF-M4-20-HK-12.9','urls':['https://www.accu.co.uk/metric-cap-head-screws/16020-SSCF-M4-12-12-9','https://www.accu.co.uk/metric-cap-head-screws/16023-SSCF-M4-16-12-9','https://www.accu.co.uk/metric-cap-head-screws/642457-SSCF-M4-20-HK-12-9'],'dimensions':'fullthread; headmaxD7.22/H4,key3; do not assume this catalog proves TR batch max dimensions; confirm purchase drawing','availability':'Accu page contains discontinued/unavailable text; not nominated as current-stock sources'},
      'material':{'url':'https://ucpcdn.thyssenkrupp.com/_legacy/UCPthyssenkruppBAMXUK/assets.files/material-data-sheets/aluminium/aluminium-6061.pdf','pages':[2,3]},
      'vendor':{'url':'https://www.myactuator.com/downloads-rhseries','part':'RH-17-100-E-B-D 3D-A.STEP / 2D-A.pdf'}}
    bom={'original_parts':[{'id':n,'quantity':1,'candidate_material':'6061-T6','mass_kg':s.Volume()*DENSITY} for n,s in parts.items()],
         'fasteners':[{'size':'M3x40','quantity':8},{'size':'M4x12','quantity':8},{'size':'M4x16','quantity':4},{'size':'M4x20','quantity':4},{'size':'M3 length TBD','quantity':16,'reason':'J5 effective output thread limits unconfirmed'}],
         'sources':sources,'no_purchase_made':True,'fastener_12_9_preload_not_selected':True}
    (out/'bom.json').write_text(json.dumps(bom,indent=2,ensure_ascii=False)+'\n')
    with (out/'screw-stacks.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(table[0]));writer.writeheader();writer.writerows(table)
    return bom


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--rh17-step',type=Path,required=True)
    ap.add_argument('--out',type=Path,default=ROOT/'engineering/generated/link56-study')
    ap.add_argument('--neighbor',action='append',default=[],metavar='MODEL=STEP')
    ap.add_argument('--private-assembly',type=Path);ap.add_argument('--font',type=Path)
    ap.add_argument('--probe-only',action='store_true');args=ap.parse_args()
    params=ROOT/'engineering/parameters/r4-layout.json';assert sha(params)==PARAM_SHA
    source=ROOT/'docs/engineering/sources/rh-interface-extraction.json'
    measured=next(m for m in json.loads(source.read_text())['models'] if m['id']=='RH17-B')
    vendor=load_vendor(args.rh17_step,measured);iface=measured['unified_joint_interface']
    parts,assembled,op,fp,T5,T6=make_parts(iface)
    vendor_world={'J5':moved(vendor,T5),'J6':moved(vendor,T6)}
    p=json.loads(params.read_text())
    all_models={m['id']:m for m in json.loads(source.read_text())['models']}
    for item in args.neighbor:
        key,path=item.split('=',1);shape=load_vendor(Path(path),all_models[key])
        for joint in p['joints']:
            if joint['model']==key and joint['id'] not in vendor_world:vendor_world[joint['id']]=moved(shape,frame(joint['origin_mm'],joint['axis']))
    cached={name:cache(s) for name,s in {**assembled,**vendor_world}.items()}
    tests={}
    for a,b in itertools.combinations(cached,2):
        tests[a+'__'+b]=check(cached[a],cached[b])
    errors={k:v for k,v in tests.items() if v['events']}
    evidence={'revision':REV,'parameters_sha256':PARAM_SHA,'source_vendor_sha256':sha(args.rh17_step),
              'original_part_masses_kg':{n:s.Volume()*DENSITY for n,s in parts.items()},'tests':tests,'errors':errors,
              'geometric_contact_path_closed':True,'hardware_definition_complete':False,'manufacturing_release':False,
              'scope':'nominal home phase; original bodies plus vendors listed; no full joint travel or cable validation',
              'vendors_checked':list(vendor_world),'output_M3_thread_length_frozen':False,
              'study_parameters':{'plate_width_depth_mm':[84,64],'output_plate_t_mm':6,'endblock_plate_t_mm':10,
                  'spigot_width_depth_length_mm':[53.8,33.8,16],'spigot_radius_mm':3.2,
                  'tube_outer_mm':[60,40],'tube_inner_mm':[54,34],'tube_length_mm':75,'tube_corner_radius_mm':3,
                  'side_hole_end_distance_mm':8,'side_hole_y_mm':[-10,10],'side_clearance_diameter_mm':4.5,
                  'rear_collar_OD_ID_t_mm':[84,67.6,14],'carrier_root_fillet_mm':2,
                  'front_collar_OD_ID_t_mm':[84,60.4,3],'upper_cable_diameter_mm':16,'upper_cable_y_offset_mm':-5}}
    if not args.probe_only:
        hardware,free,tools,table=make_hardware(op,fp,T5,T6)
        evidence['checks']=check_assembly(assembled,vendor_world,hardware,free,tools,table)
        evidence['hardware']=table
        evidence['load_screening']=load_screen(p,parts,assembled,op,fp)
        for category in ['static','hardware','tools']:
            for key,result in evidence['checks'][category].items():
                if result['events']:errors[category+'__'+key]=result
        for row in evidence['checks']['motion_samples']:
            if row['collisions']:errors['motion__'+row['moving']]=row
        print('Detailed errors',json.dumps(errors,indent=2),flush=True)
        print('Load cases',json.dumps(evidence['load_screening']['loadcases'],indent=2),flush=True)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/'geometry-probe.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps({'mass_kg':sum(evidence['original_part_masses_kg'].values()),'errors':errors},indent=2),flush=True)
    if args.private_assembly:
        private=args.private_assembly.resolve();assert ROOT not in private.parents,'Vendor geometry must remain outside repo'
        private.parent.mkdir(parents=True,exist_ok=True)
        assembly=cq.Assembly(name='J5_J6_PRIVATE_STUDY')
        for name,s in {**assembled,**vendor_world,**({} if args.probe_only else hardware)}.items():assembly.add(s,name=name)
        cq.exporters.export(assembly.toCompound(),str(private))
    if args.probe_only:return
    assert not errors,'Nominal geometry errors must be resolved before exporting candidate drawings'
    info,meshes=export_original(args.out,parts,assembled,op,fp)
    evidence['export_checks']=info;evidence['generator_sha256']=sha(Path(__file__))
    evidence['interface_tools_sha256']=sha(ROOT/'engineering/studies/link_interface_tools.py')
    evidence['interface_extraction_sha256']=sha(source)
    evidence['bom']=write_bom(args.out,parts,table)
    if args.font:
        make_pdf(args.out/'ODR-LINK56-candidate-dimensions.pdf',args.font,parts,assembled,meshes,evidence,op,fp)
        evidence['pdf_sha256']=sha(args.out/'ODR-LINK56-candidate-dimensions.pdf')
    (args.out/'evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
