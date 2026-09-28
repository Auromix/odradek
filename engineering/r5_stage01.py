#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Fold-then-radial path synthesis, not an implemented actuator or released cam.

Pitch curves, unloaded nominal path dynamics and ideal differential algebra are
kept separate. No manufactured groove, roller, cable or complete head is implied.
"""
from pathlib import Path
import csv, hashlib, itertools, json, math
import numpy as np
from scipy.optimize import minimize_scalar
from scipy.special import comb
from shapely.geometry import LineString
import ezdxf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/r5-stage01'
FORM=ROOT/'engineering/generated/r5-petal-form02'
G=9.80665
R_OPEN,R_FOLD,R_MIN,ZROOT=91.,66.,31.,20.
CAM_ARM,CAM_PHASE=8.,-math.pi/4
PHIS=[45,135,225,315]
KINDS=['upper','upper','lower','lower']
HANDS=[1,-1,-1,1]
NAMES=['UR','UL','LL','LR']
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(name,data):
    (OUT/name).write_text(json.dumps(data,indent=2,ensure_ascii=False,default=lambda x:x.tolist() if isinstance(x,np.ndarray) else x.item())+'\n')
def csvout(name, rows):
    with (OUT/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def h5(u):return 10*u**3-15*u**4+6*u**5
def d5(u):return 30*u**2*(1-u)**2
def dd5(u):return 60*u*(1-u)*(1-2*u)
def fold(R):
    """q(R), dq/dR, d²q/dR² in radians and mm; C² joins at R66 and R91."""
    u=np.clip((R_OPEN-np.asarray(R))/(R_OPEN-R_FOLD),0,1)
    return np.pi/2*h5(u), -np.pi/2*d5(u)/25, np.pi/2*dd5(u)/625
def cam(R):
    q,qr,qrr=fold(R);p=q+CAM_PHASE;a=CAM_ARM
    c=np.column_stack((R+a*np.cos(p),ZROOT+a*np.sin(p)))
    c1=np.column_stack((1-a*np.sin(p)*qr,a*np.cos(p)*qr))
    c2=np.column_stack((-a*np.cos(p)*qr**2-a*np.sin(p)*qrr,-a*np.sin(p)*qr**2+a*np.cos(p)*qrr))
    speed=np.linalg.norm(c1,axis=1)
    k=(c1[:,0]*c2[:,1]-c1[:,1]*c2[:,0])/speed**3
    ca=np.cos(p)/speed
    return c,c1,c2,k,np.degrees(np.arccos(np.clip(ca,-1,1)))
def er_et(phi):
    p=np.radians(phi);return np.array([np.cos(p),np.sin(p),0]),np.array([-np.sin(p),np.cos(p),0])
def fold_separation(parameters,r_min=66.):
    """Analytic sufficient projection bounds for independent R>=66, q in [0,pi/2].
    For every prism vertex x>=0,z<=9.5: x cos(q)-(z-3.5)sin(q)>=-6.
    This loose bound uses actual outline transverse extrema, not mesh sampling.
    """
    rows=[]
    for i,j in itertools.combinations(range(4),2):
        ea,ta=er_et(PHIS[i]);eb,tb=er_et(PHIS[j]);n=(ea-eb)/np.linalg.norm(ea-eb)
        ya=np.array(parameters[KINDS[i]]['outline_knots_mm'])[:,1]*HANDS[i]
        yb=np.array(parameters[KINDS[j]]['outline_knots_mm'])[:,1]*HANDS[j]
        bound=(r_min-6)*(n@ea-n@eb)+min(ya*(n@ta))-max(yb*(n@tb))
        rows.append(dict(pair=NAMES[i]+'-'+NAMES[j],normal=n,minimum_projection_gap_mm=float(bound)))
    assert min(x['minimum_projection_gap_mm'] for x in rows)>0
    return rows
BERNSTEIN_SPEED_MM_S=[0.,0.,378.998876,0.,0.,188.755374,387.828233,244.417517,0.,0.]
def dynamics(study,timing='quintic'):
    """Path-coordinate Lagrange calculation for synchronous bare-petal motion.
    s=91-R [m] is the closing coordinate. No cam/cable/drive mass is included.
    """
    t=np.linspace(0,1,40001);first=t<=.5;u=np.where(first,2*t,2*t-1)
    s=np.where(first,.06*(1-h5(u)),.06*h5(u))
    sd=np.where(first,-.12*d5(u),.12*d5(u));sdd=np.where(first,-.24*dd5(u),.24*dd5(u))
    if timing=='bernstein9':
        u=np.where(first,1-2*t,2*t-1)
        def basis(n):return np.array([comb(n,i)*u**i*(1-u)**(n-i) for i in range(n+1)]).T
        co=np.array(BERNSTEIN_SPEED_MM_S)/1000
        assert abs(sum(co)-1.2)<1e-12
        s=basis(10)@np.r_[0.,.05*np.cumsum(co)]
        sd=(basis(9)@co)*np.where(first,-1,1)
        sdd=basis(8)@(18*np.diff(co))
    R=R_OPEN-1000*s;q,qr,qrr=fold(R);qs=-1000*qr;qss=1e6*qrr
    H=np.zeros(len(t));Hp=H.copy();gradU=H.copy();momentum=np.zeros((len(t),3));curves=[]
    for kind,phi,hand in zip(KINDS,PHIS,HANDS):
        material=study['parts'][kind]['known_material_subtotal'];m=material['mass_kg']
        x,y,z=np.array(material['COM_local_m'])-[0,0,.0035]
        y*=hand;I=float(material['inertia_COM_local_axes_kg_m2'][1][1]);er,et=er_et(phi)
        A=-x*np.sin(q)-z*np.cos(q);B=x*np.cos(q)-z*np.sin(q)
        vr=-1+A*qs;vz=B*qs
        ar=-B*qs**2+A*qss;az=A*qs**2+B*qss
        H+=m*(vr*vr+vz*vz)+I*qs*qs
        Hp+=2*m*(vr*ar+vz*az)+2*I*qs*qss
        gradU+=m*G*vz;momentum+=m*(vr[:,None]*er+vz[:,None]*[0,0,1])
    F=H*sdd+.5*Hp*sd**2+gradU
    U=np.zeros(len(t))
    for kind in KINDS:
        material=study['parts'][kind]['known_material_subtotal'];m=material['mass_kg'];x,_,z=np.array(material['COM_local_m'])-[0,0,.0035]
        U+=m*G*(.02+x*np.sin(q)+z*np.cos(q))
    E=.5*H*sd*sd+U
    from scipy.integrate import cumulative_trapezoid
    work=cumulative_trapezoid(F*sd,t,initial=0);energy_error=max(abs(work-(E-E[0])))
    assert energy_error<1e-5
    lead=.004;rpm=sd*60/lead;ideal_torque=F*lead/(2*np.pi)
    qd=qs*sd;qdd=qss*sd*sd+qs*sdd
    rows=[dict(time_s=t[i],root_radius_mm=R[i],q_deg=np.degrees(q[i]),closing_s_m=s[i],speed_m_s=sd[i],acceleration_m_s2=sdd[i],q_speed_rad_s=qd[i],q_accel_rad_s2=qdd[i],synchronous_equivalent_mass_kg=H[i],ideal_path_force_N=F[i],hypothetical_lead4_rpm=rpm[i],hypothetical_lead4_ideal_motor_torque_Nm=ideal_torque[i]) for i in range(0,len(t),20)]
    summary=dict(timing=timing,bernstein_speed_mm_s=BERNSTEIN_SPEED_MM_S if timing=='bernstein9' else None,period_s=1.,radial_travel_mm=60.,peak_speed_mm_s=max(abs(sd))*1000,peak_accel_m_s2=max(abs(sdd)),peak_q_speed_deg_s=np.degrees(max(abs(qd))),peak_q_accel_rad_s2=max(abs(qdd)),peak_ideal_path_force_N=max(abs(F)),RMS_ideal_path_force_N=np.sqrt(np.trapezoid(F*F,t)),peak_hypothetical_lead4_rpm=max(abs(rpm)),peak_hypothetical_lead4_ideal_motor_torque_Nm=max(abs(ideal_torque)),work_energy_max_residual_J=energy_error,scope='Synchronous known bare-petal material only, head gravity -Z; excludes cams, carriers, cables, pulleys, screw, rotor, friction, contact and head acceleration. Equal branch positions are imposed, not guaranteed by a passive differential.',one_second_hardware_qualification=False)
    return rows,summary,(t,R,q,sd,qd,qdd,F)
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    study=json.loads((FORM/'study.json').read_text());par=json.loads((FORM/'parameters.json').read_text());radial=json.loads((FORM/'radial-study.json').read_text())
    for r in radial['containment']:
        assert sha(FORM/r['source_step'])==r['source_sha256'];assert r['outside_convex_prism_mm3']<1e-4
    sep=fold_separation(par)
    all_phase_sep=fold_separation(par,31.)
    R=np.linspace(31,91,12001);c,c1,c2,kap,alpha=cam(R)
    pitch=LineString(c);offset=3.15
    assert pitch.is_simple and min(c1[:,0])>0
    # Independent 1D bounded search refines dense candidate extrema; this is
    # explicitly numerical screening, not an interval curvature certificate.
    def refine(values,fn,mode='min'):
        k=int(np.argmin(values) if mode=='min' else np.argmax(values));lo=R[max(0,k-2)];hi=R[min(len(R)-1,k+2)]
        sign=1 if mode=='min' else -1;res=minimize_scalar(lambda x:sign*fn(x),bounds=(lo,hi),method='bounded',options={'xatol':1e-12})
        return {'radius_input_mm':float(res.x),'value':float(fn(res.x)),'method':'12001-point seed plus bounded local refinement; not a global interval proof'}
    ar=refine(alpha,lambda r:cam(np.array([r]))[4][0],'max')
    kr=refine(abs(kap),lambda r:abs(cam(np.array([r]))[3][0]),'max')
    groove=pitch.buffer(offset,resolution=32);assert groove.is_valid
    # Offset illustrations include assumed running clearance, not a released
    # cutter or selected roller. Explicit endpoints and annotation in DXF.
    d=ezdxf.new('R2010');d.units=4;m=d.modelspace()
    m.add_lwpolyline(c.tolist(),dxfattribs={'layer':'PITCH_REFERENCE'})
    m.add_lwpolyline(list(groove.exterior.coords),close=True,dxfattribs={'layer':'NOMINAL_SLOT_REFERENCE'})
    m.add_text('REFERENCE ONLY: 6 mm follower + 0.30 mm diametral clearance assumed; no selected bearing',dxfattribs={'height':1.2,'insert':(28,34)})
    d.saveas(OUT/'fixed-fold-guide-pitch-reference.dxf')
    csvout('fixed-guide-pitch.csv',[dict(root_radius_mm=R[i],pitch_r_mm=c[i,0],pitch_z_mm=c[i,1],q_deg=np.degrees(fold(R[i])[0]),curvature_per_mm=kap[i],pressure_angle_deg=alpha[i]) for i in range(0,len(R),10)])
    # A rigid scroll is a comparison route, not a claim of adaptation to boxes.
    offset_R=13.;thmax=np.radians(80.);k=np.log((91-offset_R)/(31-offset_R))/thmax
    theta=np.linspace(0,thmax,4001);r=(91-offset_R)*np.exp(-k*theta)
    scrolls=[LineString(np.column_stack((r*np.cos(np.radians(phi)-theta),r*np.sin(np.radians(phi)-theta)))) for phi in PHIS]
    pairs=[dict(pair=NAMES[i]+'-'+NAMES[j],sampled_polyline_centerline_distance_mm=scrolls[i].distance(scrolls[j]),nominal_width_subtracted_gap_mm=scrolls[i].distance(scrolls[j])-2*offset) for i,j in itertools.combinations(range(4),2)]
    N=2*2*G/(4*.4);K=10.
    force_rows=[]
    for width in [50,65,80,100,120]:
        contact_R=width/2+6;T=4*N*k*(contact_R-offset_R)/1000
        force_rows.append(dict(width_mm=width,contact_radius_mm=contact_R,normal_each_N=N,total_normal_N=4*N,assumed_mu=.4,gravity_factor=2.,ideal_scroll_torque_Nm=T,assumed_spring_N_per_mm=K,spring_compression_at_normal_mm=N/K,radial_command_for_that_spring_mm=contact_R-N/K,ideal_two_tier_differential_input_force_N=4*N,ideal_lead4_hold_motor_torque_Nm=4*N*.004/(2*np.pi)))
    rectangular=[]
    for w,h in [(50,50),(50,80),(50,120),(80,120),(120,120)]:
        gap=abs(w-h)/2
        rectangular.append(dict(width_mm=w,depth_mm=h,opposed_pair_contact_radius_difference_mm=gap,early_pair_extra_force_if_rigid_common_drive_and_10N_per_mm_spring_N=K*gap,terminal_offset_from_adjacent_pair_mean_mm=gap/2,ideal_mean_contact_radius_mm=(w+h)/4+6,pulley_center_stroke_is_not_inferred=True))
    csvout('contact-force-scenarios.csv',force_rows);csvout('rectangular-box-counterexamples.csv',rectangular)
    rows,dyn,series=dynamics(study);csvout('synchronous-empty-cycle.csv',rows)
    b_rows,b_dyn,b_series=dynamics(study,'bernstein9');csvout('synchronous-bernstein-cycle.csv',b_rows)
    findings=dict(revision='R5-STAGE01',source_hashes={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),FORM/'study.json',FORM/'parameters.json',FORM/'radial-study.json']},parameters=dict(root_R_open_mm=91,root_R_folded_mm=66,root_R_grip_min_mm=31,root_Z_mm=20,fold_cam_crank_mm=8,fold_cam_phase_deg=-45,assumed_follower_D_mm=6,assumed_slot_width_mm=6.3),fold_stage_continuous_petal_separation=sep,fold_stage_min_projection_gap_mm=min(s['minimum_projection_gap_mm'] for s in sep),object_approach_proof='For bare petal points in fold stage, radial projection on own er >= R-6 >=60 mm; centered cylinder D<=120 and square yaw45 side<=120 support at <=60. This excludes precontact petal/object volume intersection, not hub/mechanism/object intersection. Different widths may contact during radial stage.',cam=dict(pressure_angle_max=ar,minimum_curvature_radius_mm=1/kr['value'],curvature_max=kr,sampled_minimum_dr_dR=float(min(c1[:,0])),pitch_is_simple_polyline=bool(pitch.is_simple),nominal_buffer_is_valid=bool(groove.is_valid),nominal_minimum_local_offset_regularity_margin=1-offset*kr['value'],bearing_selected=False,offset_solid_not_manufacturing_geometry=True),rigid_scroll_comparison=dict(root_to_pitch_offset_mm=offset_R,rotation_deg=80,logarithmic_slope_k=k,constant_pressure_angle_deg=np.degrees(np.arctan(k)),minimum_pitch_curvature_radius_mm=18*np.sqrt(1+k*k),nominal_plate_outside_D_mm=2*(78+offset+3),nominal_18mm_bore_to_slot_radial_clearance_mm=18-offset-9,slot_pair_polyline_distances=pairs,finite_slot_contact_and_strength_unverified=True,rectangular_box_adaptation=False),ideal_differential=dict(equations=['R1 + R2 = 2*yA','R3 + R4 = 2*yB','yA + yB = 2*u','sum(Ri) = 4*u'],force_relation='For massless frictionless pulleys with parallel straight strands: Ti=N and input force=4*N. Constants from cable routing are absorbed into coordinate zeros.',active_DOF=1,passive_redistribution_DOF=3,synchronized_motion_guaranteed=False,physical_routing_selected=False,ordinary_urdf_mimic_is_not_contact_differential=True),force_scenarios=force_rows,rectangular_examples=rectangular,synchronous_path_dynamics=dyn,unresolved=['Complete fixed-cam, follower and radial carrier 3D packaging','Guide pressure/curvature interval certification and tolerances','Physical passive differential and cable bending/creep/life','Selected actuator transmission and its full moving mass','Series compliance, contact force sensing and power-loss retention','Real gripping friction and luminous stack strength','Final fully closed visual posture; minimum aperture here is 50 mm'])
    findings['all_independent_phase_continuous_separation']=all_phase_sep
    findings['all_independent_phase_minimum_gap_mm']=min(x['minimum_projection_gap_mm'] for x in all_phase_sep)
    findings['cam']['assembly_branch_requirement']='Actual q must be constrained to [0,90] deg. Outside that range an alternative q=270 deg-q(tau) can lie on the same slot. Nominal local determinant a*cos(q-45deg)>=sqrt(32) mm/rad. Real angular stops, assembly keying and backlash control are not designed.'
    findings['synchronous_bernstein_dynamics']=b_dyn
    findings['timing_optimization_scope']='Frozen Bernstein coefficients came from a bounded local SLSQP sample-based minimax search, not a global optimum or certified continuous hardware limit. Reproduction uses the explicit polynomial, not an optimizer dependency.'
    dump('study.json',findings)
    fig,ax=plt.subplots(2,2,figsize=(12,8));fig.suptitle('R5-STAGE01 / candidate pitch geometry and actuation constraints')
    ax[0,0].plot(R,np.degrees(fold(R)[0]),color='#d59322');ax[0,0].set(xlabel='Root radius R [mm]',ylabel='Petal angle [deg]',title='R91→66: fold; R66→31: parallel grip')
    ax[0,1].fill(*np.array(groove.exterior.coords).T,color='#cccccc');ax[0,1].plot(c[:,0],c[:,1],color='#a57518');ax[0,1].axis('equal');ax[0,1].set(xlabel='Radial coordinate [mm]',ylabel='Z [mm]',title='Fixed pitch guide / assumed Ø6 follower')
    ax[1,0].plot(R,alpha,color='#33586e');ax[1,0].set(xlabel='Root radius [mm]',ylabel='Pressure angle [deg]',title='Oscillating follower; numerical screening')
    for name,curve in zip(NAMES,scrolls):ax[1,1].plot(*np.array(curve.coords).T,label=name)
    ax[1,1].add_patch(plt.Circle((0,0),9,fill=False,color='gray'));ax[1,1].axis('equal');ax[1,1].set(title='Rigid scroll comparison / no box adaptation',xlabel='X [mm]',ylabel='Y [mm]');ax[1,1].legend(ncol=4,fontsize=8)
    for a in ax.flat:a.grid(alpha=.2)
    fig.tight_layout();fig.savefig(OUT/'path-and-cam.png',dpi=160);fig.savefig(OUT/'path-and-cam.pdf');plt.close(fig)
    t,R,q,sd,qd,qdd,F=series;fig,ax=plt.subplots(3,2,figsize=(12,10));fig.suptitle('1 s imposed synchronous empty path / hardware feasibility NOT established')
    for a,y,title,unit in zip(ax.flat,[R,np.degrees(q),1000*sd,np.degrees(qd),qdd,F],['Root radius','Petal angle','Radial speed','Petal speed','Petal acceleration','Bare-petal ideal path force'],['mm','deg','mm/s','deg/s','rad/s²','N']):a.plot(t,y,color='#3a5864');a.set(title=title,ylabel=unit,xlabel='Time [s]');a.grid(alpha=.2)
    fig.tight_layout();fig.savefig(OUT/'synchronous-cycle.png',dpi=160);fig.savefig(OUT/'synchronous-cycle.pdf');plt.close(fig)
    t,R,q,sd,qd,qdd,F=b_series;fig,ax=plt.subplots(3,2,figsize=(12,10));fig.suptitle('1 s Bernstein timing candidate / imposed synchrony, bare-petal dynamics only')
    for a,y,title,unit in zip(ax.flat,[R,np.degrees(q),1000*sd,np.degrees(qd),qdd,F],['Root radius','Petal angle','Radial speed','Petal speed','Petal acceleration','Bare-petal ideal path force'],['mm','deg','mm/s','deg/s','rad/s²','N']):a.plot(t,y,color='#3a5864');a.set(title=title,ylabel=unit,xlabel='Time [s]');a.grid(alpha=.2)
    fig.tight_layout();fig.savefig(OUT/'bernstein-cycle.png',dpi=160);fig.savefig(OUT/'bernstein-cycle.pdf');plt.close(fig)
    print(json.dumps({'bernstein_dynamics':b_dyn},indent=2))
    print(json.dumps({'cam':findings['cam'],'fold_separation_min_mm':findings['fold_stage_min_projection_gap_mm'],'dynamic':dyn,'force_scenarios':force_rows,'rectangles':rectangular},indent=2))
if __name__=='__main__':main()
