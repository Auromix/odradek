#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""R4-support-02: axial motors / 90-degree miter spindle feasibility study.
Nominal external envelopes, not tooth-generated CAD or released manufacturing.
Requires numpy and matplotlib; --cad adds cadquery. Shared layout is read-only.
"""
from pathlib import Path
import argparse, hashlib, itertools, json, math
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/gripper-support-02'
EXPECTED='4349d1797b906b67a7bc396fcb84bc439c2d70dd0b337659e552cee293d2dd81'
P=dict(revision='R4-support-02',gear='MMSB1.5-20R + MMSB1.5-20L',module_mm=1.5,teeth=20,
       gear_OD_mm=31.9,gear_bore_mm=12,gear_hub_D_mm=25,gear_E_mm=28,gear_F_mm=18.48,
       gear_G_mm=13.95,gear_H_mm=10.5,gear_I_mm=16.5,gear_b_mm=7,
       alpha_deg=20,beta_deg=35,delta_deg=45,bending_catalog_Nm=7.74,surface_catalog_Nm=7.34,
       torque_screen_Nm=3.7,bearing='SKF 7201 BECBP, adjacent DB pair per shaft',
       bearing_d_mm=12,bearing_D_mm=32,bearing_B_mm=10,bearing_C_N=7610,bearing_C0_N=3800,
       housing_D_mm=40,housing_front_mm=28.5,housing_back_mm=52,
       shaft_shoulder_D_mm=17.3,shaft_E_MPa_assumption=205000,
       coupling='NBK MJC-20CS-EGR-6-10',coupling_D_mm=20,coupling_L_mm=30,coupling_insert_mm=10,
       motor_D_mm=22,motor_body_L_mm=70.1,motor_shaft_L_mm=16.3,
       side_plate_radial_outer_mm=22,nominal_head_reference_D_mm=210,nominal_head_reference_depth_mm=197,
       gap_screen_mm=1)
Z=np.array([0.,0.,1.])
def v(x):return np.asarray(x,dtype=float)
def stack():
    # t is positive from the gear-axis intersection toward each shaft's rear.
    # DB pair is directly adjacent, retaining the catalog's CB matching condition.
    return dict(gear=[9.52,28],gear_tooth_envelope=[9.52,17.5],gear_hub=[17.5,28],
        gear_bore_end=11.5,gear_retention_washer=[10,11.5],gear_retention_bolt=[7.2,10],
        shoulder=[28,30],bearing_A=[30,40],bearing_B=[40,50],bearing_centers=[35,45],
        bearing_pressure_center_span_mm=28, # DB: 2*a, SKF a=14. Not used as a strength approval.
        rear_spacer=[50,52],MB1=[52,53],KM1=[53,57],thread_bay=[52,58],
        input_shaft=[11.5,69],coupling=[59,89],input_coupling_end=[59,69],
        motor_shaft=[79,95.3],motor_body=[95.3,165.4],motor_flange=[93.3,95.3],
        output_shaft=[11.5,69],finger_hub=[59,69],finger_hub_center=64,
        apex_offset_along_finger_axis_mm=64)

def box(name,group,c,axes,half,kind,**kw):
    return dict(name=name,group=group,center=v(c),axes=np.column_stack(axes),half=v(half),kind=kind,**kw)
def corners(p):
    return p['center']+(np.array(list(itertools.product([-1.,1.],repeat=3)))*p['half'])@p['axes'].T

def sat(a,b):
    A=a['axes'];B=b['axes'];D=b['center']-a['center']
    axes=np.concatenate([A.T,B.T,np.cross(A.T[:,None,:],B.T[None,:,:]).reshape(-1,3)])
    axes=axes[np.linalg.norm(axes,axis=1)>1e-9];axes/=np.linalg.norm(axes,axis=1)[:,None]
    return float(max(np.abs(axes@D)-np.abs(axes@A)@a['half']-np.abs(axes@B)@b['half']))

def make_parts(layout,signs):
    parts=[];rows=[];s=stack()
    for i,f in enumerate(layout['head']['fingers']):
        phi=math.radians(f['phi_deg']);er=v([math.cos(phi),math.sin(phi),0]);et=v([-math.sin(phi),math.cos(phi),0]);u=signs[i]*et
        anchor=f['root_radius_mm']*er+f['root_z_mm']*Z;apex=anchor+s['finger_hub_center']*u;name=f['id']
        def cyl(label,origin,axis,lim,r,kind,bore=0,**kw):
            w=np.cross(axis,er)
            parts.append(box(name+'_'+label,i,origin+axis*(sum(lim)/2),[axis,er,w],[(lim[1]-lim[0])/2,r,r],kind,shape='cylinder',bore_mm=bore,**kw))
        def block(label,uc,zc,rc,usize,zsize,rsize,kind):
            parts.append(box(name+'_'+label,i,apex+uc*u+zc*Z+rc*er,[u,Z,er],[usize/2,zsize/2,rsize/2],kind,shape='box'))
        for role,axis in [('input',-Z),('output',-u)]:
            cyl(role+'_gear_tooth_envelope',apex,axis,s['gear_tooth_envelope'],15.95,'gear_envelope',12)
            cyl(role+'_gear_hub',apex,axis,s['gear_hub'],12.5,'gear_hub',12)
            cyl(role+'_gear_front_washer',apex,axis,s['gear_retention_washer'],8,'gear_retention',4.3)
            cyl(role+'_gear_front_bolt_allowance',apex,axis,s['gear_retention_bolt'],3.8,'bolt_allowance')
            cyl(role+'_gear_seat',apex,axis,[11.5,28],6,'shaft')
            cyl(role+'_shaft_shoulder',apex,axis,s['shoulder'],8.65,'shaft_shoulder')
            cyl(role+'_bearing_journal',apex,axis,[30,52],6,'shaft')
            cyl(role+'_thread_bay',apex,axis,s['thread_bay'],6,'shaft_thread')
            cyl(role+'_rear_spacer',apex,axis,s['rear_spacer'],8.65,'spacer',12)
            cyl(role+'_MB1_allowance',apex,axis,s['MB1'],12.5,'lockwasher',12)
            cyl(role+'_KM1',apex,axis,s['KM1'],11,'locknut',12)
            for side in ['A','B']:
                cyl(role+'_bearing_'+side,apex,axis,s['bearing_'+side],16,'bearing',12)
            # Housing has a 32 mm bore and separate two outer-ring abutment lips.
            cyl(role+'_housing',apex,axis,[30,50],20,'housing',32)
            cyl(role+'_housing_front_lip',apex,axis,[28.5,30],20,'housing_lip',27.5)
            cyl(role+'_housing_rear_cap',apex,axis,[50,52],20,'housing_lip',28)
        cyl('input_coupler_tenon',apex,-Z,[58,69],5,'shaft')
        cyl('output_hub_tenon',apex,-u,[58,69],6,'shaft')
        cyl('finger_metal_hub',apex,-u,s['finger_hub'],12,'finger_hub',12)
        cyl('coupling',apex,-Z,s['coupling'],10,'coupling')
        cyl('motor_shaft',apex,-Z,s['motor_shaft'],3,'motor_shaft')
        cyl('motor',apex,-Z,s['motor_body'],11,'motor')
        cyl('motor_flange',apex,-Z,s['motor_flange'],17,'motor_mount',10.5)
        # Two metal side plates connect the cartridge housings behind the mesh.
        # Machined holes, screws, split seams, gear enclosure and seals remain detailed-design work.
        for sign in [-1,1]:
            block('side_plate_input_'+str(sign),-27.5,-40,sign*20,61,24,4,'carrier_plate')
            block('side_plate_output_'+str(sign),-40,-13,sign*20,24,30,4,'carrier_plate')
            block('motor_rail_'+str(sign),0,-72.65,sign*15,6,41.3,4,'motor_mount')
        rows.append(dict(finger=name,root_anchor_mm=anchor,axis_u=u,apex_mm=apex,
            motor_axis_point_mm=apex,motor_front_center_mm=apex-95.3*Z,
            motor_rear_center_mm=apex-165.4*Z,finger_hub_center_mm=apex-64*u,
            input_axis=[0,0,-1],output_axis=(-u),root_z_mm=f['root_z_mm']))
    return parts,rows

def collisions(parts):
    pairs=[]
    for a,b in itertools.combinations(parts,2):
        if a['group']==b['group']:continue
        d=sat(a,b)
        if d<P['gap_screen_mm']-1e-9:pairs.append(dict(a=a['name'],b=b['name'],projection_gap_mm=d))
    return dict(scope='inter-module nominal outer-envelope OBB screen; not moving finger/optical screen',
        tested_pairs=sum(a['group']!=b['group'] for a,b in itertools.combinations(parts,2)),
        required_projection_gap_mm=P['gap_screen_mm'],flagged_pairs=pairs,obb_passes=not pairs)

def radial_max(p):
    # Exact external radial envelope for z-parallel or tangent-axis cylinders and all box corners.
    if p['shape']=='box':return float(max(np.linalg.norm(corners(p)[:,:2],axis=1)))
    axis=p['axes'][:,0];c=p['center'];h,r=p['half'][0:2]
    if abs(axis[2])>.999:return float(np.linalg.norm(c[:2])+r)
    ax=axis[:2];perp=v([-ax[1],ax[0]])
    t=np.dot(c[:2],ax);rr=abs(np.dot(c[:2],perp))
    return math.hypot(rr+r,max(abs(t-h),abs(t+h)))

def envelope(parts):
    pts=np.concatenate([corners(p) for p in parts])
    return dict(nominal_outer_shape_coaxial_diameter_mm=2*max(radial_max(p) for p in parts),
        conservative_obb_diameter_mm=float(2*max(np.linalg.norm(pts[:,:2],axis=1))),
        z_min_mm=float(pts[:,2].min()),z_max_mm=float(pts[:,2].max()),depth_mm=float(np.ptp(pts[:,2])),
        motor_only_coaxial_diameter_mm=2*max(radial_max(p) for p in parts if p['kind']=='motor'),
        largest_radius_component=max(parts,key=radial_max)['name'],
        exclusions='gear enclosure, wiring, boltheads, complete moving fingers, full optical components')

def force(T,delta=45,b=7,d=30):
    a,be,de=map(math.radians,[20,35,delta]);dm=d-b*math.sin(de);Ft=2000*T/dm
    low=Ft/math.cos(be)*(math.tan(a)*math.sin(de)-math.sin(be)*math.cos(de))
    high=Ft/math.cos(be)*(math.tan(a)*math.cos(de)+math.sin(be)*math.sin(de))
    fa2=Ft/math.cos(be)*(math.tan(a)*math.sin(de)+math.sin(be)*math.cos(de))
    fr2=Ft/math.cos(be)*(math.tan(a)*math.cos(de)-math.sin(be)*math.sin(de))
    return dict(torque_Nm=T,mean_pitch_diameter_mm=dm,Ft_N=Ft,convex_Fa_N=low,convex_Fr_N=high,
        concave_Fa_N=fa2,concave_Fr_N=fr2,max_radial_resultant_N=max(math.hypot(Ft,high),math.hypot(Ft,fr2)),max_abs_axial_N=max(abs(low),abs(fa2)))

def bearing_beam(F,x,Fa,T,contact=0):
    # Geometrical center supports, not SKF pressure centers; conservative lever screen only.
    a,b=35.,45.;L=b-a;c=64.
    couple=abs(Fa)*x  # axial force at mean pitch radius adds an overturning couple
    RB=(F*(x-a)+contact*(c-a)-couple)/L;RA=F+contact-RB
    loads=[(x,-F),(a,RA),(b,RB),(c,-contact)]
    moment=lambda q:sum(f*(q-t) for t,f in loads if t<=q)-(couple if q>=x else 0)
    M=max(abs(moment(q)) for q,_ in loads);d=12;E=P['shaft_E_MPa_assumption'];I=math.pi*d**4/64
    # Overhung gear displacement with simple supports, no bearing/housing compliance.
    ell=a-x;deflection=F*ell**2*(ell+L)/(3*E*I)+couple*ell*(3*ell+2*L)/(6*E*I)
    sigma=32*M/(math.pi*d**3);tau=16*T*1000/(math.pi*d**3)
    return dict(gear_radial_N=F,external_axial_N=Fa,contact_N=contact,gear_load_coordinate_t_mm=x,
        axial_force_overturning_couple_Nmm=couple,reaction_A_N=RA,reaction_B_N=RB,max_bending_Nmm=M,gross_bending_MPa=sigma,gross_torsion_MPa=tau,
        gross_axial_MPa=Fa/(math.pi*d*d/4),gross_von_mises_MPa=math.sqrt((sigma+Fa/(math.pi*d*d/4))**2+3*tau**2),gear_deflection_mm_no_contact=deflection if contact==0 else None,
        single_C0_over_max_geometric_radial_reaction=3800/max(abs(RA),abs(RB)),
        limitation='conservative co-aligned radial/axial maxima including eccentric axial moment; not an equivalent bearing load or safety factor; induced thrust, clearance, minimum load, fits, notches, housing compliance and fatigue unresolved')

def mechanics():
    f=force(3.7);x=f['mean_pitch_diameter_mm']/2
    cases=[bearing_beam(f['max_radial_resultant_N']*k,x,f['max_abs_axial_N']*k,3.7*k) for k in [1,1.5,2]]
    contacts=[bearing_beam(f['max_radial_resultant_N'],x,f['max_abs_axial_N'],3.7,c) for c in [-50,50]]
    return dict(gear_force=f,reference_torque_ratio=min(7.74,7.34)/3.7,
        catalog_conditions=dict(rpm=100,cycles='>1e7',bending_bidirectional_stress_factor=2/3,lubricant_cSt_at_50C=100,uniform_motor_and_load=True,reference_only=True),
        proposed_90_deg_in_5s_mean_rpm=3,shaft_bearing_geometric_screen=cases,
        external_contact_50N_each_sign_cases=contacts,
        key_4x4x8_assumption=dict(shear_MPa=2*3700/(12*4*8),bearing_MPa=4*3700/(12*4*8)),
        transmission_sensitivity=[dict(assumed_efficiency=eta,output_Nm_at_3_7Nm_motor=3.7*eta,required_input_Nm_for_3_7Nm_output=3.7/eta) for eta in [.85,.9,.95,1]],
        NBK_twist_deg_at_3_7Nm=math.degrees(3.7/87),SKF_CB_axial_clearance_um=[15,23],
        catalog_parts_without_motors_subtotal_kg=8*.052+16*.036+4*.016+8*(.006+.002))

def mass_budget(parts):
    # Catalog masses override envelope volumes for bought parts. Custom parts are
    # nominal stock/envelope estimates, not weighed manufacturing parts.
    catalog=[dict(item='four motor-gearbox-encoder combinations',qty=4,each_g=151.4,basis='28.9 + 109 + 13.5 g; factory adapter/flange excluded'),
             dict(item='MMSB1.5-20 gears',qty=8,each_g=52,basis='KHK catalog'),
             dict(item='7201 BECBP bearings',qty=16,each_g=36,basis='SKF catalog rounded mass'),
             dict(item='MJC20 couplings',qty=4,each_g=16,basis='NBK largest-bore mass reference, exact 6/10 variant pending'),
             dict(item='KM1 nuts',qty=8,each_g=6,basis='SKF catalog'),
             dict(item='MB1 washers',qty=8,each_g=2,basis='SKF catalog')]
    for r in catalog:r['subtotal_g']=r['qty']*r['each_g']
    density={'shaft':.00785,'shaft_shoulder':.00785,'shaft_thread':.00785,'spacer':.00785,
             'gear_retention':.00785,'bolt_allowance':.00785,'housing':.00270,'housing_lip':.00270,
             'carrier_plate':.00270,'motor_mount':.00270,'finger_hub':.00270}
    categories={}
    for p in parts:
        if p['kind'] not in density:continue
        h=p['half'];vol=math.pi*(h[1]**2-(p.get('bore_mm',0)/2)**2)*2*h[0] if p['shape']=='cylinder' else float(np.prod(2*h))
        categories[p['kind']]=categories.get(p['kind'],0)+vol*density[p['kind']]
    known=sum(r['subtotal_g'] for r in catalog);custom=sum(categories.values())
    located=[]
    def record(label,mass,center,basis):located.append(dict(item=label,mass_g=mass,center_head_mm=v(center).tolist(),basis=basis))
    for p in parts:
        if p['kind'] in density:
            h=p['half'];vol=math.pi*(h[1]**2-(p.get('bore_mm',0)/2)**2)*2*h[0] if p['shape']=='cylinder' else float(np.prod(2*h))
            record(p['name'],vol*density[p['kind']],p['center'],'nominal native envelope volume x assumed density; pockets/keyways omitted')
    for group in range(4):
        group_parts=[p for p in parts if p['group']==group];by={p['name'].split('_',1)[1]:p for p in group_parts};prefix=group_parts[0]['name'].split('_',1)[0]
        front=by['motor']['center']+35.05*Z
        for label,m,c in [('gearhead',109,front-21.8*Z),('motor',28.9,front-51*Z),('encoder',13.5,front-64.25*Z)]:
            record(prefix+'_'+label,m,c,'catalog mass assigned to nominal axial sub-envelope centroid; not vendor measured CoM')
        for role in ['input','output']:
            pp=[by[role+'_gear_tooth_envelope'],by[role+'_gear_hub']]
            weights=[math.pi*(x['half'][1]**2-6**2)*2*x['half'][0] for x in pp]
            record(prefix+'_'+role+'_gear',52,sum(w*p['center'] for w,p in zip(weights,pp))/sum(weights),'catalog mass distributed over nominal gear envelope, not tooth-resolved CoM')
            for side in ['A','B']:record(prefix+'_'+role+'_bearing_'+side,36,by[role+'_bearing_'+side]['center'],'catalog mass at annular native envelope centroid')
            record(prefix+'_'+role+'_KM1',6,by[role+'_KM1']['center'],'catalog mass at nominal nut centroid')
            record(prefix+'_'+role+'_MB1',2,by[role+'_MB1_allowance']['center'],'catalog mass at simplified washer centroid; bent tabs omitted')
        record(prefix+'_coupling',16,by['coupling']['center'],'NBK reference mass at nominal coupling centroid')
    total=sum(x['mass_g'] for x in located);com=sum(x['mass_g']*v(x['center_head_mm']) for x in located)/total
    if not math.isclose(total,known+custom,rel_tol=1e-12):raise AssertionError('mass account mismatch')
    allowances=[('keys, screws, mounting bosses, shims and washers beyond modeled KM/MB and gear front bolt envelopes',40,90),
        ('factory motor adapter/flange and unmodeled connection hardware',20,50),
        ('four structural light fingers and contact pads',180,320),
        ('four LEDs/diffusers, center light/display and thermal spreaders',100,220),
        ('two ZED X One S cameras',72,72),
        ('camera mounts and on-head electrical boards',80,160),
        ('gear covers, lubrication, outer armor and seals',180,330),
        ('head rear carrier, detachable wrist interface and local cable restraint',150,300),
        ('on-head connectors and wiring, excluding long external bench cables',60,120)]
    rows=[dict(item=a,low_g=b,high_g=c,status='planning allowance, not a selected weighed part' if b!=c else 'manufacturer camera nominal 36 g each') for a,b,c in allowances]
    com_ranges=[([-15,-15,-90],[15,65,45]),([-25,-10,-135],[25,75,-65]),([-80,-80,0],[80,100,130]),([-80,-80,0],[80,100,130]),([-60,-60,-40],[60,60,0]),([-65,-65,-90],[65,65,10]),([-40,-40,-120],[40,60,40]),([-30,-30,-180],[30,30,-90]),([-60,-60,-165],[60,60,30])]
    for row,(lo,hi) in zip(rows,com_ranges):row['planning_CoM_head_mm_range']=[lo,hi]
    return dict(catalog_items=catalog,catalog_subtotal_g=known,custom_nominal_gross_by_kind_g=categories,
        custom_nominal_gross_subtotal_g=custom,drive_nominal_gross_estimate_g=known+custom,
        drive_CoM_head_mm_nominal_allocation=com.tolist(),mass_locations=located,
        CoM_limit='Nominal native geometry centroids with catalog masses; not measured/manufacturer CoM. Complete head and moving fingers are absent.',
        density_assumptions_g_per_mm3={'steel':.00785,'aluminum':.00270},
        allowances=rows,complete_head_planning_range_g=[known+custom+sum(r['low_g'] for r in rows),known+custom+sum(r['high_g'] for r in rows)],
        recommended_arm_sensitivity_head_masses_kg=[3.5,4.0,4.5],
        exclusions=['holding brake/positive latch not selected','full on-head four-axis drive boards if external routing changes','actual final CAD mass and measurements'],
        scope='catalog subtotal plus gross custom envelope estimates plus explicit planning allowances; not guaranteed lower/upper physical mass')

def self_checks(m,parts,rows):
    f=m['gear_force'];checks={}
    checks['torque_force_reverse']=math.isclose(f['Ft_N']*f['mean_pitch_diameter_mm']/2000,3.7,rel_tol=1e-12)
    checks['90deg_force_swap']=math.isclose(f['convex_Fa_N'],f['concave_Fr_N'],abs_tol=1e-10) and math.isclose(f['convex_Fr_N'],f['concave_Fa_N'],abs_tol=1e-10)
    # Reproduce KHK Table 12.6 example to its printed rounding.
    test=force(1.6646,math.degrees(math.atan(.5)),15,40)
    checks['KHK_published_example']=abs(test['Ft_N']-100)<.01 and abs(test['convex_Fa_N']+42.8)<.06 and abs(test['convex_Fr_N']-71.1)<.06
    checks['16_bearings']=sum(p['kind']=='bearing' for p in parts)==16
    checks['all_motor_axes_z']=all(np.allclose(r['input_axis'],[0,0,-1]) for r in rows)
    checks['gear_axes_90deg']=all(abs(np.dot(r['input_axis'],r['output_axis']))<1e-12 for r in rows)
    checks['hub_centers_preserve_roots']=all(np.allclose(r['root_anchor_mm'],r['finger_hub_center_mm'],atol=1e-10) for r in rows)
    checks['root_radius_70']=all(math.isclose(np.linalg.norm(r['root_anchor_mm'][:2]),70,abs_tol=1e-10) for r in rows)
    checks['gear_bore_length']=math.isclose(28-11.5,P['gear_I_mm'],abs_tol=1e-12)
    checks['coupler_two_insertions']=math.isclose(89-79,10) and math.isclose(69-59,10)
    checks['shaft_force_moment_balance']=all(abs(c['reaction_A_N']+c['reaction_B_N']-c['gear_radial_N']-c['contact_N'])<1e-8 and abs(c['reaction_B_N']*10-c['gear_radial_N']*(c['gear_load_coordinate_t_mm']-35)-c['contact_N']*29+c['axial_force_overturning_couple_Nmm'])<1e-7 for c in m['shaft_bearing_geometric_screen']+m['external_contact_50N_each_sign_cases'])
    c=m['shaft_bearing_geometric_screen'][0];ell=(35-c['gear_load_coordinate_t_mm'])/1000
    si=(c['gear_radial_N']*ell**2*(ell+.010)/(3*205e9*(math.pi*.012**4/64))+(c['axial_force_overturning_couple_Nmm']/1000)*ell*(3*ell+2*.010)/(6*205e9*(math.pi*.012**4/64)))*1000
    checks['SI_mm_deflection_match']=math.isclose(si,c['gear_deflection_mm_no_contact'],rel_tol=1e-12)
    checks['physical_cylinder_enclosed_by_obb']=all(radial_max(p)<=max(np.linalg.norm(corners(p)[:,:2],axis=1))+1e-8 for p in parts)
    if not all(checks.values()):raise AssertionError(checks)
    return checks

def solid(p,cq):
    c,u,er,h=p['center'],p['axes'][:,0],p['axes'][:,1],p['half']
    if p['shape']=='cylinder':
        sh=cq.Solid.makeCylinder(float(h[1]),float(2*h[0]),cq.Vector(*(c-h[0]*u)),cq.Vector(*u))
        if p.get('bore_mm',0):sh=sh.cut(cq.Solid.makeCylinder(p['bore_mm']/2,float(2*h[0]+.2),cq.Vector(*(c-(h[0]+.1)*u)),cq.Vector(*u)))
        return sh
    plane=cq.Plane(origin=cq.Vector(*c),xDir=cq.Vector(*u),normal=cq.Vector(*p['axes'][:,2]))
    return cq.Workplane(plane).box(*map(float,2*h)).val()

def cad(parts,report,layout):
    import cadquery as cq
    sh={p['name']:solid(p,cq) for p in parts}
    if not all(s.isValid() for s in sh.values()):raise AssertionError('invalid envelope shape')
    exact=[]
    for pair in report['flagged_pairs']:
        a,b=sh[pair['a']],sh[pair['b']]
        exact.append(dict(**pair,distance_mm=a.distance(b),intersection_mm3=a.intersect(b).Volume()))
    min_distance=min((x['distance_mm'] for x in exact),default=float('inf'));min_pair=None
    lookup={(x['a'],x['b']):x['distance_mm'] for x in exact}
    for pa,pb in itertools.combinations(parts,2):
        if pa['group']==pb['group']:continue
        if sat(pa,pb)>min_distance+1e-9:continue
        key=(pa['name'],pb['name']);d=lookup[key] if key in lookup else sh[key[0]].distance(sh[key[1]])
        if d<=min_distance+1e-9:min_distance=min(min_distance,d);min_pair=list(key)
    finger_checks=[]
    for f in layout['head']['fingers']:
        phi=math.radians(f['phi_deg']);er=v([math.cos(phi),math.sin(phi),0]);anchor=f['root_radius_mm']*er+f['root_z_mm']*Z
        L,W=f['length_mm'],f['width_mm'];outline=[(0,-W*.27),(L*.18,-W*.5),(L*.72,-W*.25),(L,-W*.05),(L,W*.05),(L*.72,W*.25),(L*.18,W*.5),(0,W*.27)]
        plane=cq.Plane(origin=cq.Vector(*anchor),xDir=cq.Vector(*er),normal=cq.Vector(*Z))
        body=cq.Workplane(plane).polyline(outline).close().extrude(f['thickness_mm']).val()
        for p in parts:
            # Finger hub and shaft attachment holes are intentionally unfinished;
            # fixed housings/carriers are not allowable attachment intersections.
            if p['kind'] not in ['housing','housing_lip','carrier_plate','motor_mount','motor','coupling','gear_envelope','gear_hub']:continue
            a,b=body.BoundingBox(),sh[p['name']].BoundingBox()
            if any(getattr(a,k+'max')<getattr(b,k+'min') or getattr(b,k+'max')<getattr(a,k+'min') for k in 'xyz'):continue
            vol=body.intersect(sh[p['name']]).Volume()
            if vol>1e-6:finger_checks.append(dict(finger=f['id'],pose_q_deg=0,part=p['name'],intersection_mm3=vol))
    cq.exporters.export(cq.Compound.makeCompound(list(sh.values())),str(OUT/'R4-support-02-envelope.step'))
    cq.exporters.export(cq.Compound.makeCompound([sh[p['name']] for p in parts if p['group']==0]),str(OUT/'single-miter-module.step'))
    back=cq.importers.importStep(str(OUT/'R4-support-02-envelope.step')).val()
    return dict(global_minimum_inter_module_distance_mm=min_distance,global_minimum_inter_module_pair=min_pair,open_pose_finger_housing_collisions=finger_checks,open_pose_finger_test_passes=not finger_checks,valid_components=len(sh),step_reimport_valid=back.isValid(),reimport_solids=len(back.Solids()),exact_outer_envelope_tests=exact,
        exact_inter_module_positive_intersection_count=sum(x['intersection_mm3']>1e-6 for x in exact),
        exact_inter_module_distance_below_1mm_count=sum(x['distance_mm']<1-1e-6 for x in exact),
        scope='nominal envelopes, not teeth, bearing raceways, threaded fasteners or fully closed gearboxes')

def hull(pts):
    pts=sorted(set(map(tuple,pts.tolist())))
    cross=lambda o,a,b:(a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    a=[];b=[]
    for p in pts:
        while len(a)>=2 and cross(a[-2],a[-1],p)<=0:a.pop()
        a.append(p)
    for p in reversed(pts):
        while len(b)>=2 and cross(b[-2],b[-1],p)<=0:b.pop()
        b.append(p)
    return a[:-1]+b[:-1]

def plots(parts,r):
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon,Circle,Rectangle
    colors=dict(motor='#556f83',bearing='#169a90',housing='#bfcbd0',housing_lip='#bfcbd0',gear_envelope='#bf7241',gear_hub='#bf7241',coupling='#e8b044',carrier_plate='#879cac',finger_hub='#dd743f')
    fig,axs=plt.subplots(1,2,figsize=(14,7))
    for ax,xy,title in [(axs[0],(0,1),'XY: same four hinge anchors; motors parallel Z'),(axs[1],(0,2),'XZ: depth exchanged for transverse span')]:
        for p in parts:
            ax.add_patch(Polygon(hull(corners(p)[:,xy]),fc=colors.get(p['kind'],'#83949c'),ec='#33474f',lw=.4,alpha=.23))
        if xy==(0,1):
            ax.add_patch(Circle((0,0),105,fill=False,ec='#d13d42',ls='--',lw=1.5,label='Old nominal D210'))
            ax.add_patch(Circle((0,0),45,fill=False,ec='#48729a',ls=':',lw=1.5,label='D90 core footprint only'))
            for row in r['coordinates']:
                q=row['root_anchor_mm'];ax.plot(q[0],q[1],'ko',ms=4);ax.text(q[0]+3,q[1]+3,row['finger'],fontsize=9)
            ax.legend(loc='lower left',fontsize=8)
        ax.autoscale();ax.set_aspect('equal');ax.grid(alpha=.15);ax.set_title(title,fontsize=10);ax.set_xlabel('X / mm');ax.set_ylabel(('Y' if xy==(0,1) else 'Z')+' / mm')
    e=r['envelope'];fig.suptitle(f"R4-support-02 | FINGER ROOT INTERFACE FAILS OPEN-POSE TEST; NOT RELEASED\nExternal shapes D{e['nominal_outer_shape_coaxial_diameter_mm']:.1f} x depth {e['depth_mm']:.1f} mm; conservative box projections shown",fontsize=12)
    fig.tight_layout(rect=(0,.07,1,.92));fig.text(.025,.02,'Four independent motors; keyed miter shafts; 16 bearings. Moving fingers, optical assembly, covers and wiring require integration. CC BY-NC 4.0',fontsize=9)
    fig.savefig(OUT/'four-miter-layout.svg');fig.savefig(OUT/'four-miter-layout.png',dpi=170);plt.close(fig)
    fig,ax=plt.subplots(figsize=(13,7));s=stack()
    # True-scale u-z single module diagram. u=0 at gear axis intersection.
    for role in ['input','output']:
        for label,lim,width,col in [('gear',s['gear'],31.9,'#bf7241'),('housing',[28.5,52],40,'#bbcbd2'),('bearing A',s['bearing_A'],32,'#169a90'),('bearing B',s['bearing_B'],32,'#169a90'),('shaft',[11.5,69],12,'#647b88')]:
            a,b=lim
            if role=='input':xy=(-width/2,-b);wh=(width,b-a)
            else:xy=(-b,-width/2);wh=(b-a,width)
            ax.add_patch(Rectangle(xy,*wh,fc=col,ec='#35464d',lw=.8,alpha=.7))
    for label,lim,width,col in [('coupler',[59,89],20,'#e8b044'),('motor',[95.3,165.4],22,'#556f83')]:
        a,b=lim;ax.add_patch(Rectangle((-width/2,-b),width,b-a,fc=col,ec='#35464d'));ax.text(38,-(a+b)/2,label,va='center',fontsize=10)
    ax.add_patch(Rectangle((-69,-12),10,24,fc='#dd743f',ec='black'));ax.plot(-64,0,'ko');ax.annotate('Original hinge anchor\nmetal hub centered here',(-64,0),(-104,27),arrowprops=dict(arrowstyle='->'),fontsize=9)
    ax.plot([0,-15,-0],[0,-15,-30],ls=':',color='#c04b45');ax.plot([0,-15,-30],[0,-15,0],ls=':',color='#c04b45')
    ax.plot(0,0,'r+');ax.annotate('90 deg axes / cone apex\n64 mm along hinge axis',(0,0),(18,22),arrowprops=dict(arrowstyle='->'),fontsize=9)
    for x,y1,y2,txt in [(-28,-30,-50,'2 x 10 mm DB'),(30,-59,-89,'30 mm'),(30,-95.3,-165.4,'70.1 mm estimate')]:
        ax.annotate('',(x,y1),(x,y2),arrowprops=dict(arrowstyle='<->',lw=.8));ax.text(x+3,(y1+y2)/2,txt,rotation=90,va='center',fontsize=9)
    ax.set_xlim(-115,78);ax.set_ylim(-178,43);ax.set_aspect('equal');ax.grid(alpha=.16);ax.set_xlabel('Local tangent u / mm');ax.set_ylabel('Local head Z / mm')
    ax.set_title('Single module: adjacent DB spindle pairs, with short overhung gears\nRectangles are nominal envelopes; gear-mesh envelope overlap is intentional, tooth geometry is not modeled',fontsize=11)
    fig.tight_layout();fig.savefig(OUT/'single-miter-stack.svg');fig.savefig(OUT/'single-miter-stack.png',dpi=170);plt.close(fig)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cad',action='store_true');args=ap.parse_args()
    raw=(ROOT/'engineering/parameters/r4-layout.json').read_bytes();sha=hashlib.sha256(raw).hexdigest()
    if sha!=EXPECTED:raise SystemExit('Layout changed; this isolated study requires explicit revision review.')
    layout=json.loads(raw)
    # Mirror-symmetric layouts only. Hand of gear teeth is independent of this spatial orientation.
    comparisons=[]
    for upper,lower in itertools.product([-1,1],repeat=2):
        signs=[upper,-upper,lower,-lower];pp,rr=make_parts(layout,signs);cc=collisions(pp)
        comparisons.append(dict(signs=signs,obb_flag_count=len(cc['flagged_pairs']),worst_gap_mm=min([x['projection_gap_mm'] for x in cc['flagged_pairs']] or [1.])))
    choice=min(comparisons,key=lambda x:(x['obb_flag_count'],-x['worst_gap_mm']))
    parts,rows=make_parts(layout,choice['signs']);m=mechanics();cr=collisions(parts)
    mass=mass_budget(parts)
    result=dict(revision=P['revision'],license='CC-BY-NC-4.0',status='NOT RELEASED: current finger roots collide with fixed supports in open pose; no 2 kg rating',
        source_layout_sha256=sha,parameters=P,local_stack_mm=stack(),sign_candidates=comparisons,
        selected_signs=choice['signs'],coordinates=rows,mechanics=m,mass_budget=mass,envelope=envelope(parts),collisions=cr,
        self_checks=self_checks(m,parts,rows),parts=parts)
    OUT.mkdir(parents=True,exist_ok=True)
    if args.cad:result['cad_qa']=cad(parts,cr,layout)
    plots(parts,result)
    def ser(x):
        if isinstance(x,np.ndarray):return x.tolist()
        raise TypeError(type(x))
    (OUT/'R4-support-02.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,default=ser)+'\n')
    (OUT/'collision-report.json').write_text(json.dumps(dict(revision=P['revision'],source_layout_sha256=sha,obb=cr,cad=result.get('cad_qa')),indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['selected_signs','sign_candidates','envelope','self_checks']},indent=2))
    if args.cad:print(json.dumps(result['cad_qa'],indent=2)[:16000])
if __name__=='__main__':main()
