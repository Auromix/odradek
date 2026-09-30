# SPDX-License-Identifier: CC-BY-NC-4.0
# Attribution: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""B04 independent nominal statics/section screening. N, mm, MPa internally.

This does not make CAD, run FEA, qualify a tabletop, or certify a payload.
Run with Python 3 + numpy: python engineering/base_b04/calculations/calculate.py
All generated files stay beside this script. No other project files are changed.
"""
from __future__ import annotations
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
G = 9.80665

CONTRACT = {
    "revision": "B04-CALC-04-contained-pads-solid34mm-C-spine",
    "status": "nominal research screen; no production or tabletop release",
    "coordinates": "x left/right; +y into desk; desk rear y=0; desk top z=0; mm",
    "J1_load_point_mm": [0., 135., 58.],
    "J1_force_N": {"vertical_down": 500., "horizontal_magnitude": 100.},
    "vertical_down_intervals_N": {"J1":[0.,500.],"base":[0.,100.],"removable_box":[0.,29.41995]},
    "J1_moment_Nm": {"pitch_Mx_separate_case": 100., "roll_My_separate_case": 100., "yaw_Mz_both_cases": 30.},
    "load_definition": "500 N is a stipulated whole-arm applied envelope, not measured weight; base and box are additional. Pitch and roll 100 Nm are separate cases, each combined with horizontal 100 N and yaw 30 Nm.",
    "base_weight_reserve_N": 100.,
    "base_reserve_COM_xy_bounds_mm": [[-128.,128.],[-42.,290.]],
    "base_reserve_note": "Design reserve, not weighed mass or CAD integration. Entire reserve is adversarially placed within the base envelope for each separate scalar bound; extrema need not coincide. It includes base/tray metal, fasteners, cover, pads and harness, excludes the 3 kg box.",
    "external_box_mass_kg": 3., "external_box_COM_mm": [0.,195.,-145.],
    "desk_thickness_examples_mm": [15.,30.,60.],
    "upper_pad_rectangles_mm": [[-96.5,-53.5,8.,162.],[53.5,96.5,8.,162.]],
    "upper_analysis_rectangles_mm": [[-96.5,-53.5,11.,159.],[53.5,96.5,11.,159.]],
    "upper_pad_model": "compatible pressure field restricted to two 43x148 inner rectangles, resultant x=+-75; subset avoids pad R3 corners, deck taper, counterbores/cover screw entries. Nominal pad is43x154 R3. No lower-face friction credited.",
    "lower_screw_axes_xy_mm": [[-85.,55.],[85.,55.]],
    "lower_pad_plate_mm": [70.,90.,8.], "lower_liner_mm": 2.,
    "preload_each_screw_N": [500.,1000.,1500.,2000.,2500.,3000.,4000.],
    "preload_relative_imbalance": [0.,0.1,0.2],
    "table_friction_sensitivity": [0.1,0.2,0.3,0.4],
    "clamp_preload_definition": "P is the mean actual retained compressive force under the evaluated load; PL/PR=P(1+-epsilon). These examples do not predict load-dependent redistribution from an installation torque.",
    "side_plate_thickness_mm": 10.,
    "side_plate_YZ_polygon_mm": [[-42.,-118.],[98.,-118.],[98.,-80.],[-8.,-80.],[-8.,2.],[98.,2.],[98.,30.],[-42.,30.]],
    "side_inner_radius_mm": 5.,
    "deck_mm": [220.,256.,12.], "deck_y_range_mm": [-38.,218.],
    "crossbeam_mm": [220.,68.,22.], "crossbeam_y_range_mm": [22.,90.], "crossbeam_z_range_mm": [-112.,-90.],
    "upper_side_M6_y_mm": [15.,45.,75.], "upper_side_M6_z_mm": 8.,
    "beam_side_M8_y_mm": [40.,75.], "beam_side_M8_z_mm": -101.,
    "side_screw_engagement_nominal_mm": 13.4,
    "interface_annulus_OD_ID_t_mm": [160.,60.,12.],
    "interface_holes": {"count":8,"PCD_mm":120.,"angle_start_deg":22.5,"thread":"M6; mating module and bolt length not frozen"},
    "pillars_xy_mm": [[-45.,90.],[45.,90.],[-45.,180.],[45.,180.]],
    "pillar_OD_length_mm": [22.,32.],
    "pillar_engagement_upper_lower_mm": [11.4,12.5],
    "bottom_M8_counterbore": {"diameter_mm":15.,"depth_mm":8.5,"seat_z_mm":10.5,"remaining_web_mm":3.5,"head_nominal_OD_mm":13.,"clearance_mm":8.5},
    "box_sidearm_mm": {"thickness":8.,"beam_height":20.,"beam_y_end":285.,"root_y":-6.,"attachment_y":[10.,50.],"attachment_z":-88.,"M6_nominal_steel_engagement_mm":6.4},
    "materials": {"Al_6061_T651":{"yield_MPa":240.,"E_MPa":70000.,"density_kg_m3":2700.},"S355J2_plus_N_10mm":{"yield_MPa":355.,"E_MPa":210000.,"density_kg_m3":7850.},"DIN6332_5_8":{"supplier_yield_MPa":400.,"E_MPa_assumption":210000.}},
}

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write_json(name, obj): (HERE/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+"\n")
def write_csv(name, rows):
    if not rows:return
    with (HERE/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def read_and_check_cad():
    """Consume root's current manifest/parameter records; fail on stale geometry.

    Section formula constants are only applicable to the checked geometry. This
    explicit contract check is preferable to silently recalculating an unrelated
    new topology using old beam formulae.
    """
    folder=HERE.parent
    prm=json.loads((folder/'parameters.json').read_text())
    man=json.loads((folder/'build/manifest.json').read_text())
    assert man['parameters_sha256']==sha(folder/'parameters.json'), 'manifest parameters are stale'
    assert prm['load_axis']==CONTRACT['J1_load_point_mm']
    assert prm['load_envelope']=={'vertical_N':500,'horizontal_N':100,'pitch_or_roll_Nm':100,'yaw_Nm':30}
    assert prm['side_profile_yz']==CONTRACT['side_plate_YZ_polygon_mm']
    assert prm['clamp_axes']==CONTRACT['lower_screw_axes_xy_mm']
    assert prm['flange_posts']==CONTRACT['pillars_xy_mm']
    assert prm['side_thickness']==10 and prm['side_corner_radius']==5
    assert prm['deck_z']==[2,14]
    assert prm['flange']=={'center':[0,135],'outer_d':160,'bore_d':60,'z':[46,58],'tap_pcd':120,'tap_count':8,'tap_phase_degrees':22.5}
    parts={p['id']:p for p in man['parts']}
    def bbox(id,lo,hi):
        b=parts[id]['bbox'];assert np.allclose(b['min'],lo,atol=2e-6) and np.allclose(b['max'],hi,atol=2e-6),id
    bbox('B04-101-DECK',[-110,-38,2],[110,218,14])
    bbox('B04-103-BRIDGE',[-110,22,-112],[110,90,-90])
    bbox('B04-104-FLANGE',[-80,55,46],[80,215,58])
    for sign in [-1,1]:
        bbox(f'B04-106-TOPPAD-{sign}',[sign*75-21.5,8,0],[sign*75+21.5,162,2])
        t=prm['nominal_desk_thickness']
        bbox(f'B04-107-PRESSPAD-{sign}',[sign*85-35,10,-t-10],[sign*85+35,100,-t-2])
    controller=prm['controller_gauge']
    CONTRACT['external_box_COM_mm']=[controller['min'][i]+controller['size'][i]/2 for i in range(3)]
    assert CONTRACT['external_box_COM_mm']==[0,195,-145]
    assert controller['mass_limit_kg']==3
    deck_features=parts['B04-101-DECK']['features']
    cbores=[f for f in deck_features if 'CBORE D15' in f.get('callout','')]
    assert len(cbores)==4
    assert all(f['model_depth_mm']==8.5 and f['model_diameter_mm']==15 for f in cbores)
    side_holes=[f for f in deck_features if f.get('callout','').startswith('M6')]
    assert sorted([f['entry_xyz'][1] for f in side_holes])==[15,15,45,45,75,75]
    assert all(f['entry_xyz'][2]==8 for f in side_holes)
    for hand in ['L','R']:
        fp=parts[f'B04-102-CPLATE-{hand}']['features']
        cradle=[f for f in fp if 'CRADLE' in f.get('callout','')]
        assert sorted([f['entry_xyz'][1:] for f in cradle])==[[10,-88],[50,-88]], 'old rear-spine holes or changed lower-arm contract'
    # Guaranteed inner-rectangle clearances: M8 bottom cbore and cover countersinks.
    assert 53.5-(45+15/2)==1.
    assert (100-6.3/2)-96.5>.34
    assert 159 < 170-4 # avoids rounded taper transition as well
    selected=[p for p in man['parts'] if p['category'] not in ['envelope','environment']]
    nominal_mass=sum(p['mass_kg']*p.get('quantity',1) for p in selected if p.get('mass_kg') is not None)
    unassigned=[p['id'] for p in selected if p.get('mass_kg') is None]
    assert nominal_mass*G<100, 'known modeled base mass exceeds design reserve'
    return {'parameters_sha256':sha(folder/'parameters.json'),'manifest_sha256':sha(folder/'build/manifest.json'),
            'model_source_sha256':sha(folder/'model.py'),'nominal_model_mass_kg':nominal_mass,
            'modeled_weight_N':nominal_mass*G,'reserve_unallocated_N':100-nominal_mass*G,
            'unassigned_mass_ids':unassigned,
            'mass_note':'nominal CAD+hardware envelopes; excludes controller gauge and PCB/other envelope entries; not a certified mass upper bound',
            'verified':'load datum, scalar envelopes, post/bolt coordinates, side profile, critical bbox, D15x8.5 bottom counterbores, pad and pressure-plate bbox',
            'inner_rectangles_note':'analytical contained subregions avoid known open holes/taper; actual pressure needs contact film; no full CAD contact solution'}

def pressure_field(N, cop, y0, y1, width=50.):
    """1D linear compression-only foundation, uniform across strip width.

    Pressure shape is a diagnostic compatible field, NOT actual contact FEA.
    Returns affine q(y)=a+b*y over [lo,hi], integrated force N.
    """
    if N<=0 or not y0<cop<y1:return {"possible":False,"reason":"nonpositive N or COP at/outside support"}
    L=y1-y0;c=(y0+y1)/2;e=cop-c
    if abs(e)<=L/6:
        b=12*N*e/(width*L**3);a=N/(width*L)-b*c;lo,hi=y0,y1
    elif cop<c:
        lo=y0;hi=y0+3*(cop-y0);b=-2*N/(width*(hi-lo)**2);a=-b*hi
    else:
        hi=y1;lo=y1-3*(y1-cop);b=2*N/(width*(hi-lo)**2);a=-b*lo
    qlo=a+b*lo;qhi=a+b*hi
    return {"possible":True,"lo_mm":lo,"hi_mm":hi,"length_mm":hi-lo,"a_MPa":a,"b_MPa_per_mm":b,"peak_MPa":max(qlo,qhi),"mean_full_area_MPa":N/(width*L)}

def contact_rows():
    c=CONTRACT;H=100.;z=58.;a=75.;rows=[]
    for P,family,epsilon,W,Wb,Wbox in itertools.product(c['preload_each_screw_N'],['pitch','roll'],c['preload_relative_imbalance'],[0.,500.],[0.,100.],[0.,3*G]):
        Wt=W+Wb+Wbox;Wy_min=W*135+Wb*(-42)+Wbox*195.;Wy_max=W*135+Wb*290+Wbox*195.
        Mx=(100000. if family=='pitch' else 0.)+z*H
        My=(100000. if family=='roll' else 0.)+z*H+Wb*128.+85.*2*P*epsilon
        N=2*P+Wt
        yc_min=(2*P*55+Wy_min-Mx)/N;yc_max=(2*P*55+Wy_max+Mx)/N
        n_min=(N-My/a)/2;n_max=(N+My/a)/2
        fields=[pressure_field(n,y,11.,159.,43.) for n,y in itertools.product([n_min,n_max],[yc_min,yc_max])]
        possible=all(f['possible'] for f in fields)
        demand=H/2+(30000.+H*max(abs(135-yc_min),abs(135-yc_max)))/(2*a)
        for mu in c['table_friction_sensitivity']:
            rows.append(dict(P_mean_each_N=P,epsilon=epsilon,family=family,mu=mu,J1_W_N=W,base_W_N=Wb,box_W_N=Wbox,total_upper_N=N,upper_min_each_N=n_min,upper_max_each_N=n_max,
                upper_COP_y_min_mm=yc_min,upper_COP_y_max_mm=yc_max,
                compression_field_exists=possible,upper_contact_length_min_mm=min([f['length_mm'] for f in fields if f['possible']],default=0),
                upper_peak_pressure_MPa=max([f['peak_MPa'] for f in fields if f['possible']],default=None),
                lower_uniform_pressure_max_MPa=P*(1+epsilon)/(70*90),required_tangential_force_each_bound_N=demand,
                available_friction_each_min_N=max(n_min,0)*mu,friction_sufficient_for_this_field=bool(possible and mu*n_min>=demand),
                required_mu=demand/n_min if n_min>0 else None))
    return rows

def all_weight_envelopes(rows):
    """N_i is affine in weights; COP is linear-fractional with positive denominator.
    Their extrema over a rectangular weight box occur at vertices. Combining
    separate extrema (which need not coexist) then bounds the constructed linear
    pressure peak and tangential demand for every intermediate weight.
    """
    out=[]
    for P,eps,fam,mu in itertools.product(CONTRACT['preload_each_screw_N'],CONTRACT['preload_relative_imbalance'],['pitch','roll'],CONTRACT['table_friction_sensitivity']):
        group=[r for r in rows if (r['P_mean_each_N'],r['epsilon'],r['family'],r['mu'])==(P,eps,fam,mu)]
        ymin=min(r['upper_COP_y_min_mm'] for r in group);ymax=max(r['upper_COP_y_max_mm'] for r in group)
        nmin=min(r['upper_min_each_N'] for r in group);nmax=max(r['upper_max_each_N'] for r in group)
        fields=[pressure_field(nmax,y,11.,159.,43.) for y in [ymin,ymax]]
        possible=nmin>0 and all(f['possible'] for f in fields)
        demand=max(r['required_tangential_force_each_bound_N'] for r in group)
        out.append(dict(P_mean_each_N=P,epsilon=eps,family=fam,mu=mu,upper_COP_y_min_mm=ymin,upper_COP_y_max_mm=ymax,
                        upper_min_each_N=nmin,upper_max_each_N=nmax,compression_field_exists_all_weights=possible,
                        pressure_peak_bound_MPa=max([f['peak_MPa'] for f in fields if f['possible']],default=None),
                        friction_required_each_bound_N=demand,friction_available_each_min_N=max(nmin,0)*mu,
                        sufficient_field_all_weights=bool(possible and mu*nmin>=demand),required_mu=demand/nmin if nmin>0 else None))
    return out

def torque_rows():
    # Basic ISO metric geometry. Not a tolerance guarantee. Endpoint friction is not the whole 25mm foot radius.
    d=12.;p=1.75;d2=d-0.6495190528*p;tan_l=p/(math.pi*d2)
    rows=[]
    for T,mu,r in itertools.product([.5,1.,1.5,2.,2.5,3.,4.,5.,6.],[.08,.12,.16,.20],[0.,2.,4.]):
        m=mu/math.cos(math.pi/6);coeff=d2/2*(tan_l+m)/(1-tan_l*m)+mu*r
        P=T*1000/coeff
        rows.append(dict(torque_Nm=T,thread_mu=mu,tip_mu_assumed_equal=mu,effective_tip_friction_radius_mm=r,torque_per_force_mm=coeff,P_each_N=P))
    return rows

def thread_screen(d,p,L_nom,force):
    # Half-circumference cylinder proxy, not a certified stripping equation.
    D1=d-1.0825317547*p;Le=max(L_nom-2*p,0);A=math.pi*D1*Le/2
    return dict(d_mm=d,pitch_mm=p,nominal_engagement_mm=L_nom,assumed_full_thread_mm=Le,proxy_shear_area_mm2=A,
                axial_force_N=force,mean_proxy_shear_MPa=force/A if A else None,
                limitation="half-circumference shear proxy; first-thread concentration, root tolerances, splitting, actual full-thread depth and cyclic wear not resolved")

def section_rows():
    rows=[];E=70000.;Es=210000.;L=220.;b=68.;h=22.;I=b*h**3/12;Z=b*h*h/6
    for P in CONTRACT['preload_each_screw_N']:
        # Simply supported crossbeam with symmetric loads 25 mm inboard of end support planes.
        moment=P*25.;deflection=P*25*(3*L**2-4*25**2)/(24*E*I)
        # Solid revised C-spine: direct tensile P at y55, centroid y-25.
        A=10*34.;Zc=10*34**2/6;sig=P/A+P*80/Zc
        # Both upper/lower bolt groups have resultant y55 once their eccentric couples are retained.
        lower_sig=P*63/(10*38**2/6);upper_sig=P*63/(10*28**2/6)
        # REJECTED predecessor only: original30mm rear spine pierced byM6 at y-18.
        intervals=[(-38.,-21.),(-15.,-8.)];A_net=sum(10*(v-u) for u,v in intervals)
        yc_net=sum(10*(v*v-u*u)/2 for u,v in intervals)/A_net
        I_net=sum(10*((v-yc_net)**3-(u-yc_net)**3)/3 for u,v in intervals)
        Z_net=I_net/max(abs(-38-yc_net),abs(-8-yc_net))
        net_sig=P/A_net+P*(55-yc_net)/Z_net
        # Revised real lower-armM6 hole at(y10,z-88): section through6mm major diameter.
        zi=[(-118.,-91.),(-85.,-80.)];Az=sum(10*(v-u) for u,v in zi)
        zc=sum(10*(v*v-u*u)/2 for u,v in zi)/Az
        Iz=sum(10*((v-zc)**3-(u-zc)**3)/3 for u,v in zi);Zz=Iz/max(abs(-118-zc),abs(-80-zc))
        lower_net=P*(55-10)/Zz
        # Tip pad: uniform bearing load, 90mm direction, free cantilever overhang from a 25mm contact footprint.
        q=P/(70*90);ell=(90-25)/2;pad_sig=3*q*ell**2/8**2;pad_delta=1.5*q*ell**4/(E*8**3)
        # Castigliano bending compliance for stated discrete bolt-force shares.
        def arm_flex(lengths,shares,Iarm):
            v=0.;knots=sorted({0.,*lengths})
            for a,b in zip(knots[:-1],knots[1:]):
                active=[(l,w) for l,w in zip(lengths,shares) if l>b-1e-8]
                A0=sum(l*w for l,w in active);B0=sum(w for l,w in active)
                v+=A0*A0*(b-a)-A0*B0*(b*b-a*a)+B0*B0*(b**3-a**3)/3
            return P*v/(Es*Iarm)
        delta_arms=arm_flex([23.,53.,83.],[1/6,1/3,1/2],10*28**3/12)+arm_flex([48.,83.],[4/7,3/7],10*38**3/12)
        rear_flex=P*80**2*82/(Es*(10*34**3/12))+P*82/(Es*A)
        rows.append(dict(P_each_N=P,crossbeam_gross_bend_MPa=moment/Z,crossbeam_hole_section_proxy_MPa=moment/((b-12)*h*h/6),crossbeam_midspan_mm=deflection,
                         C_spine_preload_nominal_MPa=sig,C_spine_Kt1p5_proxy_MPa=1.5*sig,C_spine_Kt2_proxy_MPa=2*sig,
                         rejected_old_spine_hole_nominal_MPa=net_sig,rejected_old_spine_hole_Kt2_sensitivity_MPa=2*net_sig,
                         lower_arm_new_M6_section_net_area_mm2=Az,lower_arm_new_M6_section_Z_mm3=Zz,lower_arm_new_M6_section_MPa=lower_net,
                         C_spine_add_50Nm_each_nominal_MPa=sig+50000/Zc,
                         C_lower_arm_nominal_MPa=lower_sig,C_upper_arm_nominal_MPa=upper_sig,C_arm_only_opening_proxy_mm=delta_arms,C_U_frame_opening_proxy_mm=delta_arms+rear_flex,
                         pressure_plate_uniform_model_MPa=pad_sig,pressure_plate_overhang_proxy_mm=pad_delta,
                         M12_neck_compression_MPa=P/(math.pi*7.2**2/4),M12_al_thread_proxy_shear_MPa=thread_screen(12,1.75,22,P)['mean_proxy_shear_MPa']))
    return rows

def bolt_groups(P=2500.):
    As6=math.pi/4*(6-.9382*1)**2;As8=math.pi/4*(8-.9382*1.25)**2
    # Upper side M6 group: force P at y55, group y45. Additional whole-arm moment split equally is a deliberately separate load-path screen.
    y=np.array([15.,45.,75.]);dy=y-y.mean();S=sum(dy**2)
    f=P/3+P*(55-45)*dy/S
    external_Mx=(100000.+100*(58-8))/2;vertical_bound=max(abs(f))+external_Mx*max(abs(dy))/S+((100000.+100*(58-8))/230)/3
    shear_bound=math.hypot(vertical_bound,100/6+(30000+100*(135-45))/(230*3))
    # Lower side M8 group; symmetric support at x+-110, screw loads at x+-85.
    y8=np.array([40.,75.]);dy8=y8-y8.mean();f8=P/2+P*(55-y8.mean())*dy8/sum(dy8**2)
    # At J1 top annulus, bound unknown bend direction and retained eight equally stiff axial links.
    ring_R=60.;n=8;ring_tension=100000*ring_R/(n*ring_R**2/2)
    ring_shear=100/n+30000/(n*ring_R)
    # Four posts at +-45; compressive and tensile reactions due to separate x/y bending.
    post_m=100000.+100*(58-14);post_comp=500/4+post_m*45/(4*45**2);post_tens=post_m*45/(4*45**2)
    post_shear=100/4+30000/(4*math.hypot(45,45));post_Z=math.pi*(22**4-8**4)/(32*22);post_A=math.pi*(22**2-8**2)/4
    return {'evaluation_P_each_N':P,'bolt_shear_areas_mm2':{'M6':As6,'M8':As8},
        'side_upper_M6':{'preload_only_each_vertical_N':f.tolist(),'preload_force_sum_N':sum(f),'moment_about_group_Nmm':float(sum(f*dy)),
                        'with_separate_external_path_screen_max_shear_N':shear_bound,'average_thread_section_shear_MPa':shear_bound/As6,
                        'thread_proxy_for_assembly_axial_preload_4000N':thread_screen(6,1,13.4,4000),
                        'note':'500 N at J1 is normally reacted by table and is not added again as a side clamp load. External-Mx half/all roll shared by side spacing are alternative gross path demands; C/deck contact stiffness and prying not solved. 4kN bolt assembly preload is sensitivity only, not prescribed torque.'},
        'side_lower_M8':{'each_vertical_N':f8.tolist(),'thread_section_shear_MPa':max(abs(f8))/As8,'thread_proxy_for_assembly_axial_preload_6000N':thread_screen(8,1.25,13.4,6000)},
        'J1_eight_M6_ring':{'elastic_group_tension_bound_at_W0_N':ring_tension,'shear_vector_triangle_bound_N':ring_shear,'note':'no favorable500N deducted for uplift; requires actual matched mating flange, preload and contact circle; bolt length not frozen'},
        'four_pillars':{'max_compression_N':post_comp,'max_uplift_N':post_tens,'shear_each_triangle_bound_N':post_shear,
                        'solid_minus_8mm_axial_hole_area_mm2':post_A,'post_max_compression_MPa':post_comp/post_A,'post_bending_proxy_MPa':post_shear*32/post_Z,
                        'upper_M8_assembly_6000N_thread_proxy':thread_screen(8,1.25,11.4,6000),'lower_M8_assembly_6000N_thread_proxy':thread_screen(8,1.25,12.5,6000),
                        'note':'rigid plate/equal stiffness axial group;100Nm+100N*(58-14) transferred to bottom plane, W500 for compression/W0 for uplift. Axial and cantilever post-bending proxies are separate load-sharing extremes, not one solved3Dframe; lower bolt is a socket cap in a counterbore'},
        'tray_3kg':{'vertical_force_total_N':3*G,'each_sidearm_root_moment_Nmm':1.5*G*(195.+6),
                     'beam_bend_MPa':1.5*G*(195.+6)/(8*20**2/6),
                     'beam_at_box_COM_deflection_mm':1.5*G*(195.+6)**3/(3*70000*(8*20**3/12)),
                     'each_M6_attachment_max_vertical_shear_N':1.5*G/2+1.5*G*(195.-30)/40,
                     'M6_steel_thread_proxy_at_2000N_assembly_preload':thread_screen(6,1,6.4,2000),
                     'note':'3kg box only; tray/arm own weight and hand/service pull must be added; 5kg total-load sensitivity is obtained by multiplying these values by5/3'},
        'gross_plate_metrics':{'deck_220wide_12thick_100Nm_MPa':100000/(220*12**2/6),'deck_100wide_strip_100Nm_MPa':100000/(100*12**2/6),
                              'annulus_diametral_net_width_mm':160-60,'annulus_net_section_100Nm_MPa':100000/((160-60)*12**2/6),
                              'note':'net/gross section indices only; central hole, post bearing, plate load spreading and bolt prying not bounded'}}

def thin_web_rows():
    A=math.pi*(13**2-8.5**2)/4;Apunch=math.pi*13*3.5;uplift=bolt_groups()['four_pillars']['max_uplift_N'];rows=[]
    for preload in [4000.,6000.,8000.,12000.]:
        F=preload+uplift
        rows.append(dict(M8_actual_axial_preload_N=preload,added_post_uplift_N=uplift,head_load_screen_N=F,
                         web_thickness_mm=3.5,head_annular_bearing_area_mm2=A,mean_head_bearing_MPa=F/A,
                         nominal_punch_perimeter_area_mm2=Apunch,mean_punch_shear_MPa=F/Apunch,
                         note='nominal D13 head, D8.5 clearance, 3.5 web; direct post contact can alter this force path; no prying/corner concentration or thin-annulus failure theorem'))
    return rows

def screw_geometry():
    rows=[]
    for t in CONTRACT['desk_thickness_examples_mm']:
        # DIN6311 flat contact face is against plate underside. Screw pin tip e=4.6 below that plane.
        contact=-t-10;tip=contact-4.6;end=tip-100;firstfull=tip-10
        Lfree=tip-(-90);droot=12-1.226869*1.75;I=math.pi*droot**4/64
        rows.append(dict(table_t_mm=t,pad_flat_contact_z_mm=contact,foot_lowest_z_mm=contact-13,
                         screw_pin_tip_z_mm=tip,screw_drive_end_z_mm=end,approx_first_full_thread_z_mm=firstfull,
                         nominal_full_thread_overlap_in_beam_mm=max(0,min(firstfull,-90)-max(end,-112)),
                         screw_free_length_from_beam_top_mm=Lfree,conservative_Euler_K2_N=math.pi**2*210000*I/(2*Lfree)**2,
                         drive_end_projection_below_beam_mm=-112-end,foot_to_beam_gap_mm=contact-13-(-90)))
    return rows

def validate():
    results=[]
    # Numerical integration independently checks closed-form force/moment over full and partial contact.
    maxF=maxM=0.
    for N,cop in itertools.product([500.,2500.],[6.,36.2,55.,100.,150.,194.]):
        f=pressure_field(N,cop,5,195);y=np.linspace(f['lo_mm'],f['hi_mm'],10001);q=f['a_MPa']+f['b_MPa_per_mm']*y
        Fn=np.trapezoid(50*q,y);Mn=np.trapezoid(50*q*y,y)
        maxF=max(maxF,abs(Fn-N));maxM=max(maxM,abs(Mn-N*cop))
    assert maxF<1e-6 and maxM<.01
    results.append({'test':'partial/full contact numerical force and first-moment integrals','max_force_error_N':maxF,'max_moment_error_Nmm':maxM,'pass':True})
    # Vector moment checks do not reuse scalar pressure formulas.
    rng=np.random.default_rng(404);err=0.;force_err=0.;bound_violation=0.
    envelope={r['family']:r for r in all_weight_envelopes(contact_rows()) if r['P_mean_each_N']==2500 and r['epsilon']==.1 and r['mu']==.2}
    for _ in range(500):
        P=2500.;eps=rng.uniform(-.1,.1);PL=P*(1-eps);PR=P*(1+eps);angle=rng.uniform(0,2*math.pi);H=np.array([100*math.cos(angle),100*math.sin(angle),0.]);
        M=np.array([0.,0.,rng.uniform(-30000,30000)]);axis=int(rng.integers(0,2));M[axis]=rng.choice([-1,1])*100000.
        W=rng.uniform(0,500.);wb=rng.uniform(0,100.);wc=rng.uniform(0,3*G);rb=np.array([rng.uniform(-128,128),rng.uniform(-42,290),0.]);rc=np.array([0.,195.,-145.])
        external=np.cross(np.array([0.,135,58]),H+np.array([0,0,-W]))+M+np.cross(rb,[0,0,-wb])+np.cross(rc,[0,0,-wc])
        N=PL+PR+W+wb+wc;xc=(external[1]+85*(PR-PL))/N;yc=((PL+PR)*55-external[0])/N
        NL=(N-N*xc/75)/2;NR=N-NL
        Tz=-(M[2]+(yc-135)*H[0]) # equal opposing Fy couple around upper COP
        forces=[np.array([-H[0]/2,-H[1]/2-Tz/150,NL]),np.array([-H[0]/2,-H[1]/2+Tz/150,NR])]
        reaction=sum((np.cross(np.array([x,yc,0.]),f) for x,f in zip([-75,75],forces)),np.zeros(3))
        reaction+=np.cross([-85,55,0],[0,0,-PL])+np.cross([85,55,0],[0,0,-PR])
        err=max(err,float(np.max(np.abs(external+reaction))))
        force_err=max(force_err,float(np.max(np.abs(sum(forces)+H+np.array([0,0,-(W+wb+wc+PL+PR)])))))
        e=envelope['pitch' if axis==0 else 'roll']
        field=pressure_field(max(NL,NR),yc,11,159,43)
        assert field['possible']
        bound_violation=max(bound_violation,e['upper_COP_y_min_mm']-yc,yc-e['upper_COP_y_max_mm'],
                            e['upper_min_each_N']-min(NL,NR),max(NL,NR)-e['upper_max_each_N'],
                            field['peak_MPa']-e['pressure_peak_bound_MPa'])
    assert err<1e-7 and force_err<1e-8
    results.append({'test':'500 independent vector force/moment equilibrium witnesses including unequal clamps','max_moment_residual_Nmm':err,'max_force_residual_N':force_err,'pass':True})
    assert bound_violation<1e-8
    results.append({'test':'500 interior-weight states below analytical combined scalar envelope','maximum_positive_violation':bound_violation,'pass':True})
    b=bolt_groups();assert abs(b['side_upper_M6']['preload_force_sum_N']-2500)<1e-9
    assert abs(b['side_upper_M6']['moment_about_group_Nmm']-25000)<1e-9
    assert all(r['nominal_full_thread_overlap_in_beam_mm']==22 for r in screw_geometry())
    results.append({'test':'bolt force/moment sums and three nominal screw engagement stacks','pass':True})
    # Rejected predecessor is reproduced explicitly, not silently erased.
    old=max(0,(105800-500*(135-50))/(2*(55-50)))
    new=max(0,(105800-500*(135-5))/(2*(55-5)))
    assert old==6330 and new==408
    results.append({'test':'rejected/support-updated preload necessary inequality','old_each_N':old,'new_J1_only_each_N':new,'pass':True})
    return results

def main():
    cad=read_and_check_cad()
    write_json('contract.json',CONTRACT)
    contacts=contact_rows();envelopes=all_weight_envelopes(contacts);torque=torque_rows();sections=section_rows();sg=screw_geometry();tests=validate()
    write_csv('contact-sensitivity.csv',contacts);write_csv('torque-force-sensitivity.csv',torque)
    write_csv('all-weight-contact-envelope.csv',envelopes)
    write_csv('metal-section-sensitivity.csv',sections);write_csv('screw-stack.csv',sg)
    write_csv('thin-web-M8.csv',thin_web_rows())
    write_json('bolts-and-sections.json',bolt_groups())
    local_refs=['engineering/generated/r5-body01/study.json','engineering/generated/r5-body01/body-only-model.json','engineering/generated/shoulder-raise03/mass-properties.json']
    hashes={s:sha(ROOT/s) for s in local_refs if (ROOT/s).exists()}
    source_manifest=HERE/'sources.json'
    if source_manifest.exists():hashes['engineering/base_b04/calculations/sources.json']=sha(source_manifest)
    out={'status':CONTRACT['status'],'contract_sha256':sha(HERE/'contract.json'),'script_sha256':sha(__file__),'cad_contract_checks':cad,
         'inputs_sha256':hashes,'tests':tests,'tables':{'contact_rows':len(contacts),'torque_rows':len(torque),'sections':len(sections)},
         'bounds':{'note':'No load amplification added again to the stated 100Nm/500N envelope; source arm gravity is reference, not extra load.',
                   'total_applied_vertical_including_base_reserve_box_N':500+100+3*G,
                   'source_body_including_J1_excluding_old_base_kg':17.264287919717244,
                   'source_old_fixed_base_removed_kg':4.259645819283661},
         'not_closed':['tabletop local/global strength','measured rubber friction/compression and creep','retained clamp-force redistribution with applied moments','actual bolt axial preload and joint slip/prying','3D stress concentration at C-root R5 and flange holes','fatigue, stop dynamics and vibration','J1 exact mating interface and payload certification'],
         'output_sha256':{n:sha(HERE/n) for n in ['contract.json','contact-sensitivity.csv','all-weight-contact-envelope.csv','torque-force-sensitivity.csv','metal-section-sensitivity.csv','screw-stack.csv','bolts-and-sections.json','thin-web-M8.csv']}}
    write_json('results.json',out)
    print(json.dumps({'status':out['status'],'validation':tests,'P2500_mu02_all_weight_bounds':[r for r in envelopes if r['P_mean_each_N']==2500 and r['mu']==.2]},indent=2))

if __name__=='__main__':main()
