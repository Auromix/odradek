#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Independent mass, service-gauge, part-drawing and shape QA for P16-CARRIER-01."""
import csv,hashlib,itertools,json,math
from pathlib import Path
import numpy as np
import cadquery as cq
import p16_carrier_study as cs
import p16_packaging_study as p16
import gripper_root_support_study as st
ROOT,OUT=cs.ROOT,cs.OUT

def mass(f,roots,base,fixed,om):
    rows=[]
    def add(n,s,m,method):rows.append(dict(part=n,mass_g=float(m),head_center_mm=list(s.Center().toTuple()),method=method))
    for n,s in fixed.items():
        if 'keepout' in n or 'reservation' in n:continue
        if n.endswith(('bearing_A','bearing_B')):m=36;method='SKF catalog'
        elif n.endswith('base_SBSM_pin'):m=4;method='NBK catalog'
        else:
            material=om.get(n, 'aluminum' if n in ['main_carrier','J7_existing_adapter'] or n.endswith(('base_bracket','bearing_outer_cap')) else 'steel')
            m=s.Volume()*st.DENSITY[material];method='original nominal volume * '+material+' density'
        add(n,s,m,method)
    for i,ff in enumerate(f):
        for n,s in roots[i][0].items():
            material=roots[i][1][n]
            if material=='optical_placeholder':continue
            m={'tip_SBSM_pin':3.5,'KM1':6.,'MB1':2.}.get(n,s.Volume()*st.DENSITY[material]);add(ff['id']+'_'+n,st.place(s,ff,st.SIGNS[i]),m,'catalog' if n in ['tip_SBSM_pin','KM1','MB1'] else 'original nominal volume * '+material+' density')
        add(ff['id']+'_P16',st.place(st.comp(p16.envelopes(0).values()),ff,st.SIGNS[i]),95.,'catalog95g; centroid proxy from envelope ONLY')
    for sign in [-1,1]:add('camera_'+str(sign),fixed[f'camera_{sign}_physical_keepout'],36.,'catalog36g; centroid proxy from conservative envelope ONLY')
    total=sum(r['mass_g'] for r in rows);COM=sum(r['mass_g']*np.array(r['head_center_mm']) for r in rows)/total
    exclusions=[dict(item='central display and diffuser / mounting still TBD',mass_g=[25,60],COM_head_box_mm=[[-8,-8,-12],[8,8,1]]),dict(item='four complete lamp PCBs/diffusers/retained soft pads',mass_g=[80,160],COM_head_box_mm=[[-20,-10,10],[20,35,125]]),dict(item='head-carried cable/FAKRA/strain relief',mass_g=[50,120],COM_head_box_mm=[[-30,-30,-100],[30,30,-10]]),dict(item='armor/guards/remaining retention fasteners',mass_g=[80,180],COM_head_box_mm=[[-15,-15,-65],[15,15,40]])]
    lo=total+sum(r['mass_g'][0] for r in exclusions);hi=total+sum(r['mass_g'][1] for r in exclusions)
    return dict(modeled_mass_g=total,open_COM_proxy_head_mm=COM.tolist(),J7_excluded_mass_g=780.,rows=rows,unmodeled_budget_items=exclusions,complete_head_planning_range_g=[lo,hi],limits='Not measured. Catalog mass plus uniform-density original geometry; camera and actuator internal COM unknown. PCB/pad/armor/harness ranges are planning allocations, not supplier data. J7 mass excluded to avoid double counting arm. Modelled mass is a partial sum, not a rigorous mathematical minimum after redesign.')


def gauge(name,shape,obstacles):
    hits=[];gaps=[];target=None
    if '_M3_cap_driver_' in name:target=name.split('_M3_cap_driver_')[0]+'_M3_cap_bolt_'+name.rsplit('_',1)[1]
    if '_M4_base_driver_' in name:target=name.split('_M4_base_driver_')[0]+'_M4_base_bolt_'+name.rsplit('_',1)[1]
    for n,s in obstacles.items():
        if n==target:continue
        gap=shape.distance(s);gaps.append((gap,n))
        if gap<1e-6:
            v=shape.intersect(s).Volume()
            if v>1e-4:hits.append(dict(part=n,intersection_mm3=v))
    g,n=min(gaps);return dict(name=name,intended_target_excluded=target,passes=not hits,nearest_part=n,minimum_gap_mm=g,positive_intersections=hits)


def service(f,roots,base,fixed):
    gauges=[]
    # Front optical assembly removed (disconnect FAKRA/power first); finger home and P16 bodies retained.
    obs={k:s for k,s in fixed.items() if not (k.startswith('camera_') or k.startswith('display_') or k=='removable_optical_frame' or k.startswith('optic_M3_nut_front') or k.startswith('optic_M3_washer_front'))}
    for i,ff in enumerate(f):
        for k,s in roots[i][0].items():obs[ff['id']+'_'+k]=st.place(s,ff,st.SIGNS[i])
        for k,s in p16.envelopes(0).items():obs[ff['id']+'_P16_'+k]=st.place(s,ff,st.SIGNS[i])
    m=next(x for x in json.loads((ROOT/'docs/engineering/sources/rh-interface-extraction.json').read_text())['models'] if x['id']=='RH14-N');ui=m['unified_joint_interface']
    # Source uses nested output flange properties; discover exact recorded array rather than rebuild angles.
    points=[r['xy_mm'] for r in ui['output_holes']['points']]
    assert points and len(points)==8
    for j,(x,y) in enumerate(points):gauges.append(gauge(f'J7_M3_driver_D6_L171_{j}',cs.C(3,171,(x,y,-130.8),(0,0,1)),obs))
    for i,ff in enumerate(f):
        for j,a in enumerate([45,135,225,315]):
            x,z=20*math.cos(math.radians(a)),20*math.sin(math.radians(a));tool=st.place(cs.C(2,35,(x,41.5,z),(0,1,0)),ff,st.SIGNS[i]);gauges.append(gauge(ff['id']+f'_M3_cap_driver_D4_L35_{j}',tool,obs))
        # Actuator disconnected and removed before base bolt access. Ø4 gauge includes 3mm hex diagonal.
        noact={k:s for k,s in obs.items() if not (k.startswith(ff['id']+'_P16_') or k.startswith(ff['id']+'_base_SBSM'))}
        for x in [-10,10]:gauges.append(gauge(ff['id']+f'_M4_base_driver_D4_L40_{x}',st.place(cs.C(2,40,(x,-18,-139.2),(0,0,1)),ff,st.SIGNS[i]),noact))
    return dict(gauges=gauges,all_gauges_clear=all(x['passes'] for x in gauges),conditions='Exact swept straight cylinders, not points. Specified dimensions are tool-selection requirements; handles, socket wall torque capability and hand ergonomics unverified. Optical front module disconnected/removed first. P16 removed for base bolts. Cap screws checked at q=0. J7 eight M3 lengths remain unselected because manufacturer thread-start and runout unavailable.')


def screen():
    E=69000.;I=20**4/12-math.pi*14**4/64;A=20**2-math.pi*14**2/4
    rows=[]
    for L,F,M in itertools.product([126.,152.],[300.,600.],[0.,5400.]):
        stress=(F*L+M)*10/I;delta=F*L**3/(3*E*I)+M*L**2/(2*E*I)
        assert abs(stress*I/10-F*L-M)<1e-7
        rows.append(dict(L_mm=L,F_N=F,tip_couple_Nmm=M,nominal_extreme_fiber_MPa=stress,tip_deflection_mm=delta))
    return dict(stem_area_mm2=A,stem_second_moment_mm4=I,E_MPa_assumed=E,cases=rows,shaft=dict(solid_journal_D_mm=12,solid_critical_span_u_mm=[5,34],end_lock_slot_width_depth_mm=[3.2,1.6],end_slot_u_mm=[35.8,42],former_D10_innerM4_removed=True),limits='Simple independent cantilever sensitivities, not actual frame equilibrium or proof. Local bridge remains6x6 nominal and changes to steel; notch/fillet/cyclic load and assembled compliance require analysis. Source material basis follows structure-screening; alloy/temper for root spindle not frozen. Bearing actual pressure-center/load/preload analysis still required.')


def main():
    f,roots,base,fixed,mods,om=cs.nominal();data=dict(revision='P16-CARRIER-01',mass=mass(f,roots,base,fixed,om),section_screen=screen());print('mass',data['mass']['modeled_mass_g'],data['mass']['open_COM_proxy_head_mm'],flush=True)
    data['coordinate_contract']=dict(head_origin='face center; +Z forward',J7_output_contact_head_mm=[0,0,-140],adapter_front_head_z_mm=-130,carrier_min_head_z_mm=-154,world_J7_output_if_baseline_mm=[0,55,640],world_face_if_baseline_mm=[0,55,780],mandatory_face_translation_mm=0,note='No forced translation with current J7-only geometry check; rear legs extend14mm behind output plane. LINK67 and full wrist movement require separate validation. Any subsequent extra offset Delta must move face/TCP/COM together.')
    data['service']=service(f,roots,base,fixed);print('service',data['service']['all_gauges_clear'],flush=True)
    (OUT/'review.json').write_text(json.dumps(data,indent=2)+'\n')
    with (OUT/'mass-ledger.csv').open('w',newline='') as o:
        w=csv.writer(o);w.writerow(['part','mass_g','head_com_x_mm','head_com_y_mm','head_com_z_mm','method'])
        for r in data['mass']['rows']:w.writerow([r['part'],r['mass_g'],*r['head_center_mm'],r['method']])
if __name__=='__main__':main()
