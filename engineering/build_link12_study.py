# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Original J1-to-J2 shoulder candidate; early geometry study, no release."""
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
from arm_screening import arm_parameters
from review_arm_screening import triangle_bounds
from build_link56_study import cylinder,face_contact,projected_edges
from build_layout import frame,moved
from mount_interface_study import load_vendor,ring,bores
from studies.link_interface_tools import check,cache
ROOT=Path(__file__).resolve().parents[1]
PARAM_SHA='4349d1797b906b67a7bc396fcb84bc439c2d70dd0b337659e552cee293d2dd81'
REV='R4-LINK12-01'
DENSITY=2.7e-6
G=9.80665
POST_XY=np.array([[57,-52],[-57,-52],[-57,-26],[57,-26]],dtype=float)


def shape_box(x,y,z,origin):
    return cq.Workplane('XY').box(x,y,z).translate(tuple(origin)).val()


def make_parts(iface):
    op=np.array([p['xy_mm'] for p in iface['output_holes']['points']]);fp=np.array([p['xy_mm'] for p in iface['fixed_through_holes']['points']])
    output=ring(66,33,0,6).union(cq.Workplane('XY').center(0,-33).rect(132,66).extrude(6))
    # Preserve central boss clearance through the rectangular union as well.
    output=output.cut(bores([[0,0]],33,-1,8)).cut(bores([[0,0]],34.8,-1,3.5))
    output=output.union(bores(POST_XY.tolist(),8,6,16))
    for x,y in POST_XY:
        radius=np.hypot(x,y);d=np.array([x/radius,y/radius,0.])
        rib=cq.Workplane('XZ').polyline([(35,6),(radius,6),(radius,22),(35,14)]).close().extrude(8,both=True).val()
        output=output.union(moved(rib,frame([0,0,0],[0,0,1],d)))
    output=output.cut(bores(op.tolist(),2.25,-1,8)).cut(bores(op.tolist(),3.9,4,22))
    output=output.cut(bores(POST_XY.tolist(),3.3,-1,24)).val()
    T1=frame([0,0,105.2],[0,0,1]);T2=frame([0,0,170],[0,1,0])
    rear=moved(ring(64,47.7,-59.7,14).val(),T2)
    # Radial ribs need a defined clearance notch around the rear collar; this
    # cutter only removes material ABOVE the6mm output plate.
    cutter=moved(cq.Workplane('XY').workplane(offset=-60.2).circle(64.5).extrude(15).val(),T2)
    cutter=cutter.intersect(shape_box(250,250,200,[0,0,211.2]))
    safety=moved(cq.Workplane('XY').workplane(offset=-106).circle(55.5).extrude(110).val(),T2)
    ow=moved(output,T1).cut(cutter).cut(safety)
    roots=[e for e in ow.Edges() if e.geomType()=='LINE' and abs(e.Center().z-111.2)<1e-5 and e.BoundingBox().zlen<1e-5 and e.Length()>5 and abs(e.Center().x)<65 and abs(e.Center().y)<65]
    assert len(roots)==16
    ow=ow.fillet(.8,roots).cut(cutter).cut(safety).clean()
    output=moved(ow,np.linalg.inv(T1))
    rear=rear.intersect(shape_box(200,200,200,[0,-45,213.2])) # lower boundaryworldZ113.2
    for x in [-57,57]:rear=rear.fuse(shape_box(16,42,14,[x,-39,134.2]))
    rear=rear.clean()
    rear=rear.cut(moved(bores(fp.tolist(),1.65,-60,15).val(),T2))
    rear=rear.cut(bores(POST_XY.tolist(),2.5,126.2,16).val()).clean()
    front=ring(56,45,-15.5,4).cut(bores(fp.tolist(),2.25,-16,6)).cut(bores([[51,0],[-51,0],[0,51],[0,-51]],3.8,-16,6)).val()
    assembled={'output_adapter':moved(output,T1),'rear_fork':rear,'front_ring':moved(front,T2)}
    for n,s in assembled.items():assert s.isValid() and len(s.Solids())==1,(n,len(s.Solids()))
    return assembled,op,fp,T1,T2



def make_hardware(op,fp,T1,T2):
    full={};free={};tools={};table=[]
    def bolt(name,seat,outward,d,L,H,D,grip,engagement,owner,stage,selected=True):
        seat=np.asarray(seat,dtype=float);axis=np.asarray(outward,dtype=float)
        head=cylinder(seat,axis,D/2,H)
        full[name]=head.fuse(cylinder(seat,-axis,d/2,L))
        free[name]=head.fuse(cylinder(seat,-axis,d/2,grip))
        if engagement is not None and L>grip+engagement:
            free[name]=free[name].fuse(cylinder(seat-axis*(grip+engagement),-axis,d/2,L-grip-engagement))
        tools[name]=cylinder(seat+axis*H,axis,3 if d==6 else 2.5,60)
        table.append({'id':name,'thread':f'M{d}','selected_length_mm':L if selected else None,
                      'modeled_length_mm':L,'seat_world_mm':seat.tolist(),'head_outward_axis':axis.tolist(),
                      'head_D_H_mm':[D,H],'free_grip_mm':grip,'nominal_geometric_engagement_mm':engagement,
                      'tip_protrusion_mm':max(0,L-grip-(engagement or 0)) if selected else None,
                      'thread_owner':owner,'stage':stage,'length_selected':selected})
    for i,(x,y) in enumerate(POST_XY):
        bolt(f'FOOT_M6x35_{i+1}',[x,y,105.2],[0,0,-1],6,35,6,10.22,22,13,'rear_fork',1)
    for i,(x,y) in enumerate(op):
        seat=(T1@np.array([x,y,4,1]))[:3]
        # Only the proven first3.5mm of vendor channel is represented, not an
        # invented complete screw across the13mm drawing recess.
        bolt(f'OUT_M4_unknown_{i+1}',seat,[0,0,1],4,7.5,4,7.22,7.5,None,'J1',3,False)
    for i,(x,y) in enumerate(fp):
        seat=(T2@np.array([x,y,-11.5,1]))[:3]
        bolt(f'FIX_M4x50_{i+1}',seat,[0,1,0],4,50,4,7.22,34.2,14,'rear_fork',5)
    return full,free,tools,table


def continuous_J2_insertion(vendor,stationary):
    """Prove real solids lie inside a conservative envelope, then check its sweep.

    For t in[0,180], rear-cylinder sweep[-104,134.3] lies inside the union
    of stationary rear[-104,-45.7] and larger front[-45.7,182.1]. Thus the
    returned simple two-cylinder union encloses every translation, not samples.
    """
    T=frame([0,0,170],[0,1,0])
    rear=cylinder([0,0,-104],[0,0,1],47.45,58.3)
    front=cylinder([0,0,-45.7],[0,0,1],55.05,47.8)
    envelope=moved(rear.fuse(front),T)
    assert envelope.isValid() and len(envelope.Solids())==1
    containment=[]
    for i,solid in enumerate(vendor.Solids()):
        outside=solid.cut(envelope)
        volume=abs(outside.Volume()) if outside.Solids() else 0.
        containment.append({'vendor_solid_index':i,'outside_envelope_mm3':volume})
    assert sum(x['outside_envelope_mm3'] for x in containment)<1e-4,'Envelope must contain every actual OEM solid'
    sweep=moved(rear.fuse(cylinder([0,0,-45.7],[0,0,1],55.05,227.8)),T)
    assert sweep.isValid() and len(sweep.Solids())==1
    checks={n:check(sweep,s) for n,s in stationary.items()}
    return {'vendor_solid_count':len(containment),'containment_per_solid':containment,
            'total_outside_envelope_mm3':sum(x['outside_envelope_mm3'] for x in containment),
            'home_envelope_joint_frame_mm':{'rear_radius':47.45,'rear_z':[-104,-45.7],'front_radius':55.05,'front_z':[-45.7,2.1]},
            'sweep_direction_world':[0,1,0],'sweep_travel_mm':[0,180],
            'swept_envelope_joint_frame_mm':{'rear_radius':47.45,'rear_z':[-104,-45.7],'front_radius':55.05,'front_z':[-45.7,182.1]},
            'checks':checks,'method':'All actual OEM solids contained by Boolean difference; swept enclosing volume has no material-volume overlap with stationary solids by per-solid Boolean common. Continuous straight path, nominal geometry only.',
            'excludes':'Cables, connectors absent from source CAD, hands, manufacturing tolerances and alternative poses'}


def validate_geometry(assembled,vendors,base,hardware,free,tools,table):
    all_shapes={**assembled,**vendors,**base};cached={n:cache(s) for n,s in all_shapes.items()}
    result={'static':{},'hardware':{},'tools':{},'motion_samples':[],'contacts':{}}
    for x,y in itertools.combinations(cached,2):
        if x not in assembled and y not in assembled:continue
        result['static'][x+'__'+y]=check(cached[x],cached[y])
    print('Static shapes checked; checking screws and staged tools',flush=True)
    for row in table:
        n=row['id']
        for other,target in cached.items():
            result['hardware'][n+'__'+other]=check(free[n] if other==row['thread_owner'] else hardware[n],target)
        # Reverse foot screws are bench assembled BEFORE bracket meetsJ1/base.
        present={1:['output_adapter','rear_fork'],3:['output_adapter','rear_fork','J1',*base],
                 5:['output_adapter','rear_fork','front_ring','J1','J2',*base]}[row['stage']]
        for other in present:result['tools'][n+'__'+other]=check(tools[n],cached[other])
    for a,b in itertools.combinations(hardware,2):result['hardware'][a+'__'+b]=check(hardware[a],hardware[b])
    contacts=[('J1','output_adapter',[0,0,105.2],[0,0,1]),
              ('output_adapter','rear_fork',[0,0,127.2],[0,0,1]),
              ('rear_fork','J2',[0,-45.7,170],[0,1,0]),
              ('front_ring','J2',[0,-15.5,170],[0,1,0])]
    for a,b,o,z in contacts:
        result['contacts'][a+'__'+b]=face_contact(all_shapes[a],all_shapes[b],o,z)
        assert result['contacts'][a+'__'+b]['shared_planar_face_area_mm2']>10
    early={c+'__'+k:v for c in ['static','hardware','tools'] for k,v in result[c].items() if v['events']}
    if early:
        print('Early geometry errors',json.dumps(early,indent=2),flush=True)
        return result
    print('Static/screw/tool checks clear; checking insertions',flush=True)
    bench=cq.Compound.makeCompound([assembled['output_adapter'],assembled['rear_fork']]+[s for n,s in hardware.items() if n.startswith('FOOT_')])
    stages=[('rear_fork',assembled['rear_fork'],[0,0,1],120,{'output_adapter':assembled['output_adapter']}),
            ('bracket_preassembled',bench,[0,0,1],120,{'J1':vendors['J1'],**base}),
            ('J2',vendors['J2'],[0,1,0],180,{'output_adapter':assembled['output_adapter'],'rear_fork':assembled['rear_fork'],'J1':vendors['J1'],**base,**{n:s for n,s in hardware.items() if not n.startswith('FIX_')}}),
            ('front_ring',assembled['front_ring'],[0,1,0],140,{'output_adapter':assembled['output_adapter'],'rear_fork':assembled['rear_fork'],'J1':vendors['J1'],'J2':vendors['J2'],**base,**{n:s for n,s in hardware.items() if not n.startswith('FIX_')}})]
    for name,moving,axis,start,stationary in stages:
        print('Insertion',name,flush=True);collisions=[];target={k:cache(s) for k,s in stationary.items()}
        if name=='J2':
            proof=continuous_J2_insertion(moving,stationary);result['continuous_J2_insertion']=proof
            collisions=[{'other':n,**r} for n,r in proof['checks'].items() if r['events']]
            result['motion_samples'].append({'moving':'J2','direction_from_final':axis,'start_distance_mm':start,'steps_mm':'continuous swept conservative envelope','stationary':list(stationary),'collisions':collisions,'scope':proof['method']})
            continue
        for dist in sorted(set([0,.1,.5,1,2,*range(5,start+1,5)])):
            probe=moving.translate(tuple(np.asarray(axis)*dist))
            for n,s in target.items():
                r=check(probe,s)
                if r['events']:collisions.append({'translation_mm':dist,'other':n,**r})
        result['motion_samples'].append({'moving':name,'direction_from_final':axis,'start_distance_mm':start,
             'steps_mm':'0,0.1,0.5,1,2 then every5mm','stationary':list(stationary),'collisions':collisions,
             'scope':'discrete insertion, not continuous swept volume; adjacentJ3 not installed at this stage'})
    return result


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def local_parts(assembled):
    transforms={'output_adapter':frame([0,0,105.2],[0,0,1]),
                'rear_fork':frame([0,-59.7,113.2],[0,0,1]),
                'front_ring':frame([0,-15.5,170],[0,1,0])}
    names={'output_adapter':'ODR-L12-OUT-R4','rear_fork':'ODR-L12-FORK-R4','front_ring':'ODR-L12-FRONT-R4'}
    return {names[n]:moved(s,np.linalg.inv(transforms[n])) for n,s in assembled.items()},transforms,names


def section_at_world_z(shape,z):
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
    t=.001;section=shape.intersect(shape_box(300,300,t,[0,0,z]))
    props=GProp_GProps();BRepGProp.VolumeProperties_s(section.wrapped,props)
    area=props.Mass()/t;mat=props.MatrixOfInertia();c=np.array(section.Center().toTuple())
    bb=section.BoundingBox()
    return {'world_z_mm':z,'area_mm2':area,'centroid_world_mm':c.tolist(),
            'Ixx_mm4':mat.Value(1,1)/t-area*t*t/12,'Iyy_mm4':mat.Value(2,2)/t-area*t*t/12,
            'Ixy_mm4':-mat.Value(1,2)/t,'max_x_from_centroid_mm':max(bb.xmax-c[0],c[0]-bb.xmin),
            'max_y_from_centroid_mm':max(bb.ymax-c[1],c[1]-bb.ymin),'slice_thickness_mm':t}


def rib_section_screen(output):
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
    result=[]
    for index,(x,y) in enumerate(POST_XY):
        radius=np.hypot(x,y);T=frame([0,0,105.2],[0,0,1],[x/radius,y/radius,0])
        shape=moved(output,np.linalg.inv(T));rows=[]
        # Use an isolated16mm radial strip cut from the ACTUAL ribbed solid.
        # Material outside the strip is omitted; root is assumed perfectly
        # clamped at the outer edge of the vendor support annulus r42.5.
        for r in np.linspace(42.5,radius-.1,31):
            t=.001;section=shape.intersect(shape_box(t,16,30,[r,0,15]));props=GProp_GProps();BRepGProp.VolumeProperties_s(section.wrapped,props)
            A=props.Mass()/t;I=props.MatrixOfInertia().Value(2,2)/t-A*t*t/12;zc=section.Center().z;bb=section.BoundingBox()
            assert A>0 and I>0
            rows.append({'r_mm':float(r),'area_mm2':A,'Iy_mm4':I,'extreme_z_mm':max(zc-bb.zmin,bb.zmax-zc),'slice_solids':len(section.Solids()),'slice_thickness_mm':t})
        coefficient=max((radius-r['r_mm'])*r['extreme_z_mm']/r['Iy_mm4'] for r in rows)
        compliance=float(np.trapezoid([(radius-r['r_mm'])**2/(70000*r['Iy_mm4']) for r in rows],[r['r_mm'] for r in rows]))
        result.append({'post_number':index+1,'post_radius_mm':float(radius),'stress_per_N_MPa':coefficient,'deflection_per_N_mm':compliance,'samples':rows})
    return result


def load_screen(p,assembled,op,fp):
    placement_path=ROOT/'engineering/generated/link56-study/part-placements.json'
    wrist=json.loads(placement_path.read_text())
    wrist_mass=sum(q['mass_kg_6061'] for q in wrist['instances'].values())
    wrist_com=sum(q['mass_kg_6061']*np.array(q['estimated_COM_world_mm']) for q in wrist['instances'].values())*.001/wrist_mass
    newmass=sum(s.Volume()*DENSITY for s in assembled.values());reserve=.20
    own_hardware_com=sum(s.Volume()*DENSITY*np.array(s.Center().toTuple()) for s in assembled.values())*.001/newmass
    post=POST_XY-POST_XY.mean(axis=0);output=op-op.mean(axis=0);fixed=fp-fp.mean(axis=0)
    def coeff(points):return max(np.linalg.norm(np.linalg.solve(points.T@points,r)) for r in points)
    group_errors=[]
    for points in [post,output,fixed]:
        for angle in np.linspace(0,2*np.pi,721):
            m=np.array([np.cos(angle),np.sin(angle)])*1000
            reactions=points@np.linalg.solve(points.T@points,[-m[1],m[0]])
            recovered=np.array([reactions@points[:,1],-reactions@points[:,0]])
            group_errors.append(float(np.max(np.abs(recovered-m))))
    assert max(group_errors)<1e-8
    # The collar is curved and multiply loaded. Real net slices provide inputs
    # to a transparent straight-cantilever sensitivity, not a curved-ring FEA.
    sections=[section_at_world_z(assembled['rear_fork'],z) for z in [141.3,145,150,155,160,165,170]]
    Imin=min(min(s['Ixx_mm4'],s['Iyy_mm4']) for s in sections);Amin=min(s['area_mm2'] for s in sections)
    assert max(abs(s['Ixy_mm4']) for s in sections)<.01
    bending_coeff=max(np.hypot(s['max_y_from_centroid_mm']/s['Ixx_mm4'],s['max_x_from_centroid_mm']/s['Iyy_mm4']) for s in sections)
    rib_sections=rib_section_screen(assembled['output_adapter'])
    group_centre=np.array([0,-39,127.2]);rows=[]
    for head in [2,3.5,4,4.5]:
        model=arm_parameters(p,head);old_bounds=triangle_bounds(model)[0]
        model['bodies']=[b for b in model['bodies'] if b['id'] not in ['L1_budget','L5_budget']]
        for n,s in assembled.items():model['bodies'].append({'id':'L12_'+n,'mass_kg':s.Volume()*DENSITY,'preceding_joints':1,'com_home_m':(np.array(s.Center().toTuple())*.001).tolist()})
        model['bodies'].append({'id':'L12_hardware_reserve','mass_kg':reserve,'preceding_joints':1,'com_home_m':own_hardware_com.tolist()})
        for n,s in wrist['instances'].items():model['bodies'].append({'id':'L56_'+n,'mass_kg':s['mass_kg_6061'],'preceding_joints':5,'com_home_m':(np.array(s['estimated_COM_world_mm'])*.001).tolist()})
        model['bodies'].append({'id':'L56_hardware_reserve','mass_kg':.10,'preceding_joints':5,'com_home_m':wrist_com.tolist()})
        bounds=triangle_bounds(model)[0];moving=[b for b in model['bodies'] if b['preceding_joints']>=1]
        mass=sum(b['mass_kg'] for b in moving);force=mass*G
        # J1 yaw preserves verticality; the64.8mm vertical J1-J2 offset does
        # not contribute a gravity moment. Add only actual upstream XY offsets.
        upstream=sum(b['mass_kg']*G*np.linalg.norm(np.array(b['com_home_m'])[:2]) for b in moving if b['preceding_joints']==1)
        output_bound=float(bounds[1]+upstream)
        cut_bounds={'J1_output':output_bound,'foot_group_centroid':output_bound+force*.039,
                    'J2_rear_contact':output_bound+force*.0457}
        # For internal shoulder forces the same budget deliberately retains all
        # L12 own mass, even material below a given section: simple over-count.
        uncertainty=head*G*.05+p['payload_net_kg']*G*.1
        gravity_M=1.5*(max(cut_bounds.values())+uncertainty)
        F=1.5*force
        scenarios=[]
        for label,MNm in [('gravity_expanded',gravity_M),('157Nm_catalog_peak_applied_as_separate_interface_action',157.)]:
            M=MNm*1000
            postN=F/4+M*coeff(post);fixedN=F/8+M*coeff(fixed);outputN=F/16+M*coeff(output)
            postA=np.pi*(8**2-3.3**2);postI=np.pi*(8**4-3.3**4)/4
            # The following isolated strip is deliberately reported as a
            # deficiency indicator; load spreading through the complete ribbed
            # plate has NOT been established. It cannot support a pass verdict.
            span=max(np.linalg.norm(xy) for xy in POST_XY)-42.5
            strip_sigma=6*postN*span/(8*6**2)
            strip_delta=postN*span**3/(3*70000*(8*6**3/12))
            collar_sigma=M*bending_coeff+F/Amin
            collar_delta=M*28.8**2/(2*70000*Imin)+F*28.8**3/(3*70000*Imin)
            scenarios.append({'id':label,'moment_Nm':MNm,'force_N':F,
                'M6_post_max_external_axial_N':postN,'fixed_M4_max_external_axial_N':fixedN,
                'output_M4_max_external_axial_N':outputN,'post_nominal_axial_stress_MPa':postN/postA,
                'post_axial_shortening_mm':postN*16/(70000*postA),
                'post_short_column_Euler_N_not_capacity':np.pi**2*70000*postI/16**2,
                'M6_external_stress_at_20_1mm2_MPa':postN/20.1,
                'fixed_M4_external_stress_at_8_78mm2_MPa':fixedN/8.78,
                'output_M4_external_stress_at_8_78mm2_MPa':outputN/8.78,
                'collar_straight_cantilever_sensitivity_MPa':collar_sigma,'collar_sensitivity_deflection_mm':collar_delta,
                'counterfactual_6x8_strip_sensitivity_MPa':strip_sigma,'counterfactual_6x8_strip_deflection_mm':strip_delta,
                'actual_16mm_rib_strip_screening_MPa':postN*max(r['stress_per_N_MPa'] for r in rib_sections),
                'actual_rib_strip_deflection_screening_mm':postN*max(r['deflection_per_N_mm'] for r in rib_sections),
                'rib_stress_below_240MPa_reference':bool(postN*max(r['stress_per_N_MPa'] for r in rib_sections)<240),
                'plate_isolated_strip_span_mm':span,'counterfactual_6x8_strip_exceeds_240MPa_reference':bool(strip_sigma>240),
                'output_total_preload_friction_sensitivity_N':{str(mu):M/(mu*38.5) for mu in [.08,.15,.20]},
                'M6_equal_stiffness_shear_plus_torsion_N':F/4+M*np.max(np.linalg.norm(post,axis=1))/np.sum(post**2)})
        rows.append({'head_mass_kg':head,'head_COM_home_mm':[0,55,760],'net_object_kg':p['payload_net_kg'],
                     'old_triangle_all_Nm':old_bounds.tolist(),'revised_triangle_all_Nm':bounds.tolist(),
                     'all_mass_preceding_J1_kg':mass,'upstream_off_axis_weight_bound_Nm':upstream,
                     'cut_gravity_moment_bounds_Nm':cut_bounds,'COM_uncertainty_Nm':uncertainty,'scenarios':scenarios})
    return {'original_mass_kg':newmass,'hardware_mass_budget_kg':reserve,'L12_hardware_COM_proxy_m':own_hardware_com.tolist(),'L12_hardware_COM_note':'reserve at original metal weighted COM; not measured fastener COM','L1_total_mass_budget_kg':newmass+reserve,
            'old_L1_budget_kg':p['link_budgets_kg'][0],'L56_placement_sha256':sha(placement_path),'L56_hardware_COM_proxy_m':wrist_com.tolist(),'L56_hardware_COM_note':'0.10kg reserve located at metal-part weighted COM for consistency with candidate_mass_model; not a measured fastener COM',
            'L56_mass_budget_kg':sum(s['mass_kg_6061'] for s in wrist['instances'].values())+.10,
            'all_L12_preceding_joints':1,'J2_torque_includes_L12_mass':False,
            'post_group_centroid_world_mm':group_centre.tolist(),'post_group_centred_xy_mm':post.tolist(),
            'post_group_Sxx_Syy_mm2':[float(sum(post[:,0]**2)),float(sum(post[:,1]**2))],
            'group_moment_reconstruction_error_Nmm':max(group_errors),'rear_fork_sections':sections,'rib_strip_actual_net_sections':rib_sections,
            'rib_model':'31 actual BREP radial sections per16mm strip, rootclamped at r42.5; sigma=F*(R-r)*c/I, tipdeflection=F integral[(R-r)^2/(EI)]dr. Excludes support-ring plate compliance, preload/contact/prying, residualstress and fatigue. Not a conservative bound on the complete casting/machined part.',
            'material_E_N_mm2':70000,'material_yield_reference_MPa':240,'study_multiplier':1.5,
            'rear_thread_major_ligament_mm':51-47.7-2,'output_lower_pocket_hole_inner_ligament_mm':38.5-34.8-2.25,'output_upper_hole_inner_ligament_mm':38.5-33-2.25,
            'output_max_head_to_central_opening_radial_gap_mm':38.5-7.22/2-33,'output_cap_recess_to_centre_ligament_mm':38.5-3.9-33,'vendor_boss_nominal_radial_axial_gap_mm':[.3,.5],
            'loadcases':rows,
            'scope':'Gravity bounds for stated point masses; own upstream mass deliberately over-counted for internal cuts.157Nm is a separate pure-interface-action sensitivity, NOT a simultaneous all-axis dynamic bound or continuous holding guarantee.',
            'blocking_strength_item':'Actual16mm rib-strip and collar sensitivities do not resolve full support-annulus compliance, bolt contact/preload, thread strip or fatigue; contact FEA and test still required.',
            'limitations':['No preload/bolt proof/thread-strip/contact-prying qualification','No trajectory inertia, contact impact, stall or fatigue envelope','No full-load or 2kg payload claim','Rated dynamic torque is not zero-speed holding capability']}


def feature_rows(op,fp):
    rows=[]
    def add(part,name,points,z,axis,d,depth,thread=''):
        for i,(x,y) in enumerate(points):rows.append({'part':part,'feature':name,'number':i+1,'x_mm':float(x),'y_mm':float(y),'z_mm':z,'axis':axis,'diameter_mm':d,'depth_mm':depth,'thread':thread})
    add('OUT','J1 clearance',op,0,'+Z',4.5,6)
    add('OUT','J1 cap recess to all material above z4',op,4,'+Z',7.8,'THRU ALL MATERIAL ABOVE Z4')
    add('OUT','foot M6 clearance',POST_XY,0,'+Z',6.6,22)
    add('OUT','central through',[[0,0]],0,'+Z',66,6)
    add('OUT','bottom boss pocket',[[0,0]],0,'+Z',69.6,2.5)
    # Fork local X=worldX,Y=worldY+59.7,Z=worldZ-113.2.
    add('FORK','M6 foot tap',POST_XY+np.array([0,59.7]),14,'+Z',5,15,'M6x1 through14mm foot; flat-bottom pilot15; candidate6H')
    for i,(x,v) in enumerate(fp):rows.append({'part':'FORK','feature':'J2 fixed tap','number':i+1,
        'x_mm':float(x),'y_mm':0,'z_mm':56.8-float(v),'axis':'+Y','diameter_mm':3.3,'depth_mm':14,'thread':'M4x0.7 THRU; candidate6H'})
    add('FRONT','J2 fixed clearance',fp,0,'+Z',4.5,4)
    add('FRONT','OEM assembly head relief',[[51,0],[-51,0],[0,51],[0,-51]],0,'+Z',7.6,4)
    return rows


def export_original(out,assembled,op,fp):
    from build_base_study import export_parts
    parts,transforms,names=local_parts(assembled);info=export_parts(out,parts);meshes={}
    for name,s in parts.items():
        mesh=trimesh.load_mesh(out/(name+'.stl'),process=True);meshes[name]=mesh
        d=ezdxf.new('R2010');d.units=ezdxf.units.MM;ms=d.modelspace()
        bases=[np.array([[1,0,0],[0,1,0]]),np.array([[1,0,0],[0,0,1]]),np.array([[0,1,0],[0,0,1]])]
        for label,basis,offset in zip(['TOP_XY','FRONT_XZ','SIDE_YZ'],bases,[[0,0],[0,-180],[180,-180]]):
            d.layers.new(label)
            for line in projected_edges(mesh,basis):ms.add_line(tuple(line[0]+offset),tuple(line[1]+offset),dxfattribs={'layer':label})
        short=name.split('-')[2]
        for row in feature_rows(op,fp):
            if row['part']==short and row['axis']=='+Z':ms.add_circle((row['x_mm'],row['y_mm']),row['diameter_mm']/2)
            if row['part']==short and row['axis']=='+Y':ms.add_circle((row['x_mm'],row['z_mm']-180),row['diameter_mm']/2)
        ms.add_text(name+' / mm / 1:1 MODEL SPACE / UNLOADED FIT ONLY; NOT RELEASED',dxfattribs={'height':3}).set_placement((-70,-207))
        ms.add_text('Use PDF + feature CSV for dimensions; silhouette edges are not machining cutter paths.',dxfattribs={'height':2.5}).set_placement((-70,-215))
        dp=out/(name+'.dxf');d.saveas(dp);read=ezdxf.readfile(dp);assert not read.audit().errors
        info[name]['dxf_audit_passed']=True;info[name]['sha256'][dp.name]=sha(dp)
    assembly=cq.Compound.makeCompound(list(assembled.values()));ap=out/'ODR-LINK12-original-assembly.step';cq.exporters.export(assembly,str(ap))
    read=cq.importers.importStep(str(ap)).val();assert read.isValid() and len(read.Solids())==3
    placements={n:{'part_id':names[n],'T_world_from_part_mm':transforms[n].tolist(),'preceding_joints':1,
         'estimated_COM_world_mm':list(s.Center().toTuple()),'mass_kg_6061':s.Volume()*DENSITY} for n,s in assembled.items()}
    (out/'part-placements.json').write_text(json.dumps({'revision':REV,'parameters_sha256':PARAM_SHA,'status':'fit/structural research candidate; strength not qualified','instances':placements},indent=2)+'\n')
    rows=feature_rows(op,fp)
    with (out/'hole-features.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    return parts,meshes,info


def write_bom(out,parts,table):
    sources=[
        {'id':'M4x50','part':'Accu SSC-M4-50-12.9','url':'https://www.accu.co.uk/metric-cap-head-screws/16032-SSC-M4-50-12-9','standard':'DIN912','material':'12.9 alloy steel; finish natural','max_head_D_mm':7.22,'head_H_mm':4,'key_AF_mm':3,'minimum_thread_mm':20,'weight_100_grams':570,'catalog_listing_not_stock_confirmation':True},
        {'id':'M6x35','part':'Accu SSC-M6-35-HK-12.9','url':'https://www.accu.co.uk/metric-cap-head-screws/642488-SSC-M6-35-HK-12-9','standard':'ISO4762 / Holokrome','material':'12.9 alloy steel; finish natural','max_head_D_mm':10.22,'head_H_mm':6,'key_AF_mm':5,'minimum_thread_mm':24,'weight_100_grams':990,'catalog_listing_not_stock_confirmation':True},
        {'id':'material','part':'thyssenkrupp EN AW-6061 sheet','url':'https://ucpcdn.thyssenkrupp.com/_legacy/UCPthyssenkruppBAMXUK/assets.files/material-data-sheets/aluminium/aluminium-6061.pdf','pages':[2,3],'values':'density2.70g/cm3,E70000N/mm2; T6 minimum Rp0.2=240MPa in listed ranges; batch certification required'},
        {'id':'RH25','part':'MYACTUATOR RH-25-100-E-B-D 3D-A0 / 2D-A0 p1','url':'https://www.myactuator.com/downloads-rhseries','values':'actual mounting contacts/PCD/hole coordinates; source STEP retained privately; M4 effective output-thread start/end not established'}]
    bom={'revision':REV,'original_parts':[{'id':n,'quantity':1,'candidate_material':'6061-T6','mass_kg':s.Volume()*DENSITY} for n,s in parts.items()],
         'fasteners':[{'source_id':'M4x50','quantity':8,'nominal_free_grip_mm':34.2,'nominal_geometric_engagement_mm':14,'nominal_tip_protrusion_mm':1.8},
                       {'source_id':'M6x35','quantity':4,'nominal_free_grip_mm':22,'nominal_geometric_engagement_mm':13,'nominal_tip_protrusion_mm':0,'remaining_foot_depth_mm':1},
                       {'size':'M4 length TBD','quantity':16,'reason':'Do not infer13mm recess +6mm thread as confirmed effective thread interval'}],
         'known_12_selected_fasteners_catalog_mass_kg':.0852,'all_28_fasteners_mass_budget_kg':.20,
         'sources':sources,'preload_selected':False,'no_purchase_made':True,'printed_parts':'PLA/PETG, no load, no powered joint motion'}
    (out/'bom.json').write_text(json.dumps(bom,ensure_ascii=False,indent=2)+'\n')
    with (out/'screw-stacks.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
    return bom


def make_pdf(path,font,assembled,parts,meshes,evidence,op,fp):
    from reportlab.lib.pagesizes import A3,landscape
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas
    from draw_layout import Sheet,TEAL,GRAY,LIGHT,AMBER
    from pypdf import PdfReader
    pdfmetrics.registerFont(TTFont('Link12CN',str(font)));pdf=canvas.Canvas(str(path),pagesize=landscape(A3),pageCompression=1)
    pdf.setTitle('Odradek J1-J2 shoulder candidate - UNLOADED FIT / NO STRENGTH RELEASE');pdf.setAuthor('Auromix contributors');s=Sheet(pdf,'Link12CN')
    XY=np.array([[1,0,0],[0,1,0]]);XZ=np.array([[1,0,0],[0,0,1]]);YZ=np.array([[0,1,0],[0,0,1]])
    def notes(x,y,lines,size=8.5,step=7):
        for k,t in enumerate(lines):s.text(x,y-k*step,t,size)
    def view(name,basis,origin,scale=1):
        for e in projected_edges(meshes[name],basis):s.line(np.array(origin)+e[0]*scale,np.array(origin)+e[1]*scale,TEAL,.35)
    def dim(a,b,label,offset=(0,0)):
        a,b,off=[np.array(x,dtype=float) for x in [a,b,offset]];s.line(a,a+off,GRAY,.3);s.line(b,b+off,GRAY,.3)
        s.arrow(a+off,b+off,GRAY,.4);s.arrow(b+off,a+off,GRAY,.4);s.text(*((a+b)/2+off+np.array([0,2])),label,8,GRAY,'center')
    def footer(page):
        s.line((15,16),(405,16),GRAY,.4);s.text(15,10,'单位 mm | 无载试装 / 候选加工讨论 | 6061-T6暂定 | 强度、预紧、螺纹和加工圆角未放行',8)
        s.text(405,10,f'{page}/5 | A3 横向 | {REV}',8,align='right');pdf.showPage()
    s.header('J1 → J2 肩架候选','保持J1=[0,0,105.2], +Z；J2=[0,0,170], +Y。实体装配可行不等于承载已验证。',REV)
    for i,(basis,origin,shift) in enumerate([(XZ,[94,84],[0,105.2]),(YZ,[298,84],[0,105.2])]):
        for shape in assembled.values():
            vv,ff=shape.tessellate(.10,.10);mesh=trimesh.Trimesh(vertices=[v.toTuple() for v in vv],faces=ff,process=True)
            for edge in projected_edges(mesh,basis):
                q=(edge-shift)*1.1+origin;s.line(q[0],q[1],TEAL,.35)
        s.text(origin[0]-72,251,'正视XZ / 1.1:1' if i==0 else '侧视YZ / 1.1:1',10,TEAL)
    # Dimension-based fixed flange schematic, never copied vendorCAD.
    q0=np.array([298-45.7*1.1,84+(170-54.7-105.2)*1.1]);q1=np.array([298-15.5*1.1,84+(170+54.7-105.2)*1.1])
    for a,b in [(q0,[q1[0],q0[1]]),([q1[0],q0[1]],q1),(q1,[q0[0],q1[1]]),([q0[0],q1[1]],q0)]:s.line(a,b,GRAY,.4,dash=[2,2])
    notes(315,236,['灰虚线：原厂法兰尺寸包络。','两接触面间距30.2。','原厂实体仅本地检查。'],7.5,6)
    dim([180,84],[180,84+(170-105.2)*1.1],'64.8',offset=[9,0])
    notes(20,66,[f'三件原创估重{evidence["load_screening"]["original_mass_kg"]:.6f} kg；全部紧固件预算0.20 kg；归属 preceding_joints=1。',
                 'J1输出接触Z105.2；输出板顶111.2；支柱顶/叉脚底127.2；叉脚顶141.2。',
                 'J2后接触Y=-45.7、前接触Y=-15.5；后叉退到Y=-59.7；前环到Y=-11.5。',
                 '加强筋根已进入实际接触环；简化筛查仍不能代替接触FEA。本图只允许无载试装和结构评审。'],8.5)
    footer(1)

    s.header('输出板、支柱与筋 / ODR-L12-OUT-R4','局部原点为J1输出接触面；局部XYZ与世界同向。底板、支柱、加强筋为一个原创实体。',REV)
    name='ODR-L12-OUT-R4';view(name,XY,[99,171],1.05);view(name,XZ,[99,73],1.05)
    dim([99-66*1.05,171+66*1.05],[99+66*1.05,171+66*1.05],'132',offset=[0,7])
    s.text(23,251,'顶视 / 正视，1.05:1',9,TEAL)
    notes(18,60,['底板=Ø132并后半132×66矩形，厚6；中心Ø66贯通。',
                 '4×Ø16柱，高16，从z6到22；4×Ø6.6贯通，总跨距22。',
                 '径向筋宽16：从r35顶z14升至柱心顶z22，底z6；根R0.8。',
                 '后叉避让刀体：J2局部R64.5，轴向-60.2～-45.2，只切z≥6。'],7.5,6)
    s.text(206,251,'J1输出孔：16×Ø4.5；帽头Ø7.8铣至底z4',9,TEAL)
    for i,(x,y) in enumerate(op):
        col=i//8;row=i%8;s.text(205+col*100,238-row*8.5,f'{i+1:02d} X{x:+8.4f} Y{y:+8.4f}',8)
    notes(205,158,['PCD77；精确角相位11.34873°+i×22.5°。','沉孔底z4，向上穿全部材料；M4头z4～8。',
                   '底部Ø69.6避让腔仅深2.5；上部Ø66贯通。',
                   '凸台径向/轴向名义间隙0.30/0.50；帽头至贯孔余1.89。',
                   'Ø7.8沉孔与Ø66贯孔余1.60，已消除0.09细边。',
                   '支柱中心X=±57；Y=-52与-26（共4处）。','M6×35由底面装入；从输出底面到叉脚底自由跨22。',
                   '保留16条R0.8筋根圆角；其余工艺根角/刀具可达待评审。',
                   '原厂输出M4长度未定：只核实第一段Ø4.4通道3.5mm。'],8,7)
    footer(2)

    s.header('带脚后叉 / ODR-L12-FORK-R4','局部坐标=世界减[0,-59.7,113.2]；平面孔坐标转换为X=u、Z=56.8-v。',REV)
    name='ODR-L12-FORK-R4';view(name,XZ,[92,101],1.05);view(name,YZ,[239,101],1.05)
    s.text(23,251,'正视XZ / 1.05:1',10,TEAL);s.text(215,251,'侧视YZ / 1.05:1',10,TEAL)
    dim([92-64*1.05,101+120.8*1.05],[92+64*1.05,101+120.8*1.05],'128',offset=[0,6])
    notes(20,90,['环心[0,0,56.8]，轴+Y；OD128/ID95.4；厚14，Y0～14。',
                 '整环底切至Z=0；上顶Z120.8。不得把底切到脚底，低位孔会丢失。',
                 '左右脚各16×42×14：中心X=±57、Y=20.7、Z=21。',
                 '脚范围Y=-0.3～41.7，Z14～28；4×M6贯通脚；Ø5平底孔深15。',
                 '脚孔X±57；Y=7.7与33.7；有效啮合仍需扣除倒角与退刀。',
                 '8×M4×0.7沿Y贯通，底孔Ø3.3；使用右侧u/v真实孔阵。',
                 '固定孔PCD102，最小内缘至M4大径仅1.3，须复核开裂/拔牙。'],8,6)
    s.text(300,247,'原厂固定孔u / v（mm）',9,TEAL)
    for i,(x,y) in enumerate(fp):s.text(300,234-i*9,f'{i+1}: {x:+8.4f} / {y:+8.4f}',8)
    notes(300,151,['叉内孔Ø95.4避让后壳Ø94.8。','径向名义间隙0.30，不是定位配合。',
                   '环后Y0；接触原厂面Y14。','M4×50尖端伸出后面1.8。',
                   '根部内角与工艺圆角待审核。','当前图纸是原形试装资料。'],8,7)
    footer(3)

    s.header('前环与螺钉堆叠','ODR-L12-FRONT-R4；局部原点在J2前安装接触面，+Z沿J2输出方向+世界Y。',REV)
    name='ODR-L12-FRONT-R4';view(name,XY,[100,177],1.25);view(name,XZ,[100,96],1.25)
    dim([100-56*1.25,177+56*1.25],[100+56*1.25,177+56*1.25],'112',offset=[0,5])
    notes(20,80,['OD112/ID90，厚4；8×Ø4.5孔PCD102，坐标同上页u/v。',
                 '另4×Ø7.6让原装帽头：PCD102，0/90/180/270°。',
                 '前环底面贴J2 local z=-15.5；外面local z=-11.5。',
                 '14mm后叉、30.2mm原厂跨距、4mm前环，不借用原厂内部螺纹。'],8)
    notes(205,252,['8×M4×50 / Accu SSC-M4-50-12.9 / DIN912',
                   '头Ø7.22最大×4；3mm内六角；最短螺纹20。',
                   '自由跨距4+30.2=34.2；后叉几何贯穿14；尖端余1.8。',
                   '最短螺纹从头下30处开始，早于34.2接触点。',
                   '贯通厚度不等于完整有效啮合：需扣入口倒角/不完整牙。','',
                   '4×M6×35 / Accu SSC-M6-35-HK-12.9 / ISO4762',
                   '头Ø10.22最大×6；5mm内六角；最短螺纹24。',
                   '从底面反装：6底板+16柱=22；脚厚14；螺钉进入13，距顶1。',
                   '最短螺纹从头下11处开始，覆盖整个候选脚部。',
                   '必须先离机组好；上机后下方扳手通道受底座阻挡。','',
                   '16×J1输出M4：长度待厂家确认；模型只表示已证实自由段。',
                   '尚无预紧扭矩/防松方案/螺纹剥离和原厂夹持许可。'],8.5,8)
    footer(4)

    s.header('装配顺序与强度待解项','几何、可装配性、材料承载是三个不同结论；本页没有负载验证通过标记。',REV)
    load=evidence['load_screening'];r=load['loadcases'][-1];g=r['scenarios'][0]
    notes(20,251,['装配阶段（J3与以上尚未装）：',
                  '1. 离机把后叉从+Z放到四柱上，用4×M6×35从底面预装。',
                  '2. 整体从+Z放到J1输出，16×M4从+Z拧入；长度待确认。',
                  '3. J2由+Y进入后叉，原厂固定后平面贴Y=-45.7。',
                  '4. 前环由+Y装入，8×M4×50从+Y穿过法兰并拧入后叉。',
                  '5. J3及其他连架另做；此处工具结论不覆盖后续满装维护。',
                  '6. 拆反装M6前，必须先卸下整套肩架。'],8.5)
    s.text(20,191,'名义接触面积（Boolean平面交集，mm²）',10,TEAL)
    for i,(key,c) in enumerate(evidence['checks']['contacts'].items()):s.text(20,180-i*8,f'{key}: {c["shared_planar_face_area_mm2"]:.2f}',8)
    notes(20,139,['逐solid碰撞含真实J1/J2及相邻J3/J4，另含原创J1底座。',
                  '28个紧固件：正确排除原创螺纹的预期啮合，其余自由段逐件检查。',
                  '工具直杆：M4 Ø5×60；M6 Ø6×60；不代表手、加长杆或扳手柄。',
                  'J2逐原厂实体包含验证后检查连续扫掠；其余3步离散，均未含公差/线缆。'],8)
    notes(222,251,[f'4.5kg头 + 2kg工件；头COM暂为[0,55,760]mm。',
                   f'更新J2三角界 {r["revised_triangle_all_Nm"][1]:.3f} Nm；J1驱动重力扭矩仍为0。',
                   f'最不利本研究截面重力界 {max(r["cut_gravity_moment_bounds_Nm"].values()):.3f} Nm。',
                   f'头COM±50mm、工件COM100mm再加1.5研究倍率：{g["moment_Nm"]:.3f} Nm。',
                   f'等刚度后脚M6最大外载 {g["M6_post_max_external_axial_N"]:.0f} N。',
                   f'固定M4 / 输出M4：{g["fixed_M4_max_external_axial_N"]:.0f} / {g["output_M4_max_external_axial_N"]:.0f} N。',
                   f'后环直梁等效敏感性：{g["collar_straight_cantilever_sensitivity_MPa"]:.1f} MPa，{g["collar_sensitivity_deflection_mm"]:.3f} mm。',
                   f'真实16mm筋净截面：{g["actual_16mm_rib_strip_screening_MPa"]:.1f} MPa，{g["actual_rib_strip_deflection_screening_mm"]:.3f} mm。',
                   '低于240MPa材料参考值；仍未含接触环柔度、孔口与预紧。',
                   '必须补接触FEA/螺纹/疲劳/实测后才可讨论承载。',
                   '另给157Nm纯接口载荷敏感性；不等于所有电机同时峰值。',
                   '目录动态rated不是持续零速持载额定。'],8.5,8)
    notes(20,66,['候选公差：一般线性±0.10，孔中心±0.05，接触平面度0.05；螺纹建议6H，均待加工/公差审核。',
                 '打印：OUT底面朝床；FORK后面朝床加支撑；FRONT平放。关节由外部托架承重，打印件只手动试配。',
                 '本轮优先闭合真实接触与装配路径；输出板/筋根、预紧、原厂有效螺纹与疲劳仍是阻止制造放行的项目。'],8.2)
    footer(5);pdf.save();read=PdfReader(path);assert len(read.pages)==5 and all(len(x.extract_text())>150 for x in read.pages)


def complete_deliverables(out,font,assembled,op,fp,result,p):
    assert not result['errors'],'Geometry errors must be resolved before candidate drawings'
    parts,meshes,info=export_original(out,assembled,op,fp)
    result['load_screening']=load_screen(p,assembled,op,fp)
    result['export_checks']=info;result['generator_sha256']=sha(Path(__file__))
    result['interface_tools_sha256']=sha(ROOT/'engineering/studies/link_interface_tools.py')
    result['interface_extraction_sha256']=sha(ROOT/'docs/engineering/sources/rh-interface-extraction.json')
    result['bom']=write_bom(out,parts,result['hardware'])
    dependencies=['engineering/build_layout.py','engineering/build_base_study.py','engineering/build_link56_study.py','engineering/mount_interface_study.py','engineering/arm_screening.py','engineering/review_arm_screening.py','engineering/generated/mount-study/ODR-J1-REAR-R4.step','engineering/generated/mount-study/ODR-J1-FRONT-R4.step','engineering/generated/link56-study/part-placements.json']
    result['dependency_sha256']={x:sha(ROOT/x) for x in dependencies}
    result['study_parameters']={'output_plate_base_thickness_mm':6,'centre_through_diameter_mm':66,'bottom_boss_pocket_diameter_depth_mm':[69.6,2.5],'nominal_boss_radial_axial_gap_mm':[.3,.5],'cap_seat_z_mm':4,'cap_recess_diameter_mm':7.8,'post_diameter_height_mm':[16,16],'post_xy_mm':POST_XY.tolist(),'rib_width_mm':16,'rib_root_radius_topz_mm':[35,14],'rib_top_at_post_mm':22,'selected_root_fillet_mm':.8,'rear_ring_OD_ID_t_mm':[128,95.4,14],'foot_width_depth_thickness_mm':[16,42,14],'front_ring_OD_ID_t_mm':[112,90,4]}
    from build_base_study import hardware as base_hardware
    fixed_fasteners,_,_=base_hardware(30,fp.tolist())
    _,_,_,T1,T2=make_parts(next(m for m in json.loads((ROOT/'docs/engineering/sources/rh-interface-extraction.json').read_text())['models'] if m['id']=='RH25-B')['unified_joint_interface'])
    own_fasteners,_,_,_=make_hardware(op,fp,T1,T2)
    ztop=max(x.BoundingBox().zmax for x in fixed_fasteners.values())
    zbottom=min(x.BoundingBox().zmin for x in list(assembled.values())+list(own_fasteners.values()))
    assert zbottom-ztop>1
    result['base_fastener_separation_proof']={'base_fastener_count':len(fixed_fasteners),'max_base_fastener_world_z_mm':ztop,'minimum_link12_part_or_screw_world_z_mm':zbottom,'nominal_z_gap_mm':zbottom-ztop,'method':'Disjoint closed Z intervals; bracket insertion only increasesZ, front-ring insertion preservesZ; reverse M6 tools used off-robot before base is present','scope':'Nominal assemblies; does not grant in-place maintenance or tolerance qualification'}
    result['manufacturing_release']=False;result['strength_qualified']=False
    result['geometric_contact_path_closed']=True;result['output_M4_length_frozen']=False
    if font:
        pdf=out/'ODR-LINK12-candidate-dimensions.pdf';make_pdf(pdf,font,assembled,parts,meshes,result,op,fp);result['pdf_sha256']=sha(pdf)
    (out/'evidence.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    return result


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--rh25-step',required=True,type=Path)
    ap.add_argument('--output',type=Path,default=ROOT/'engineering/generated/link12-study')
    ap.add_argument('--neighbor',action='append',default=[],metavar='MODEL=STEP')
    ap.add_argument('--private-assembly',type=Path);ap.add_argument('--font',type=Path);args=ap.parse_args()
    parameter=ROOT/'engineering/parameters/r4-layout.json';assert hashlib.sha256(parameter.read_bytes()).hexdigest()==PARAM_SHA
    p=json.loads(parameter.read_text());source=ROOT/'docs/engineering/sources/rh-interface-extraction.json'
    models={x['id']:x for x in json.loads(source.read_text())['models']};m=models['RH25-B']
    vendor=load_vendor(args.rh25_step,m);a,op,fp,T1,T2=make_parts(m['unified_joint_interface'])
    v={'J1':moved(vendor,T1),'J2':moved(vendor,T2)}
    for item in args.neighbor:
        key,path=item.split('=',1);shape=load_vendor(Path(path),models[key])
        for joint in p['joints']:
            if joint['model']==key and joint['id'] not in v:v[joint['id']]=moved(shape,frame(joint['origin_mm'],joint['axis']))
    from build_base_study import make_parts as base_parts
    _,base=base_parts(30);base={'base_'+n:s for n,s in base.items()}
    hardware,free,tools,table=make_hardware(op,fp,T1,T2)
    checks=validate_geometry(a,v,base,hardware,free,tools,table)
    errors={category+'__'+k:r for category in ['static','hardware','tools'] for k,r in checks[category].items() if r['events']}
    errors.update({'motion__'+r['moving']:r for r in checks['motion_samples'] if r['collisions']})
    result={'revision':REV,'parameters_sha256':PARAM_SHA,'source_vendor_sha256':hashlib.sha256(args.rh25_step.read_bytes()).hexdigest(),
            'status':'candidate, not manufacturing release','mass_kg_6061':{n:s.Volume()*DENSITY for n,s in a.items()},
            'errors':errors,'checks':checks,'hardware':table,'vendors_checked':list(v),'base_original_parts_checked':list(base),
            'scope':'nominal home assembly; output M4 length unknown; full joint travel and cable harness unverified'}
    args.output.mkdir(exist_ok=True,parents=True);(args.output/'geometry-probe.json').write_text(json.dumps(result,indent=2)+'\n')
    if args.private_assembly:
        dest=args.private_assembly.resolve();assert ROOT not in dest.parents
        dest.parent.mkdir(exist_ok=True,parents=True);assy=cq.Assembly(name='L12_PRIVATE')
        for n,s in {**a,**v,**base,**hardware}.items():assy.add(s,name=n)
        cq.exporters.export(assy.toCompound(),str(dest))
    print(json.dumps({'mass':result['mass_kg_6061'],'errors':errors},indent=2),flush=True)
    complete_deliverables(args.output,args.font,a,op,fp,result,p)


if __name__=='__main__':main()
