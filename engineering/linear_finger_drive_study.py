# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Independent P16/crank kinematics and conditional grasp screening."""
from pathlib import Path
import hashlib
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from grasp_screening import solve_grasp

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/linear-drive-study'
D,A,PHASE=123.,26.,np.deg2rad(68.)


def motion(q):
    alpha=np.asarray(q)-PHASE
    length=np.sqrt(D*D+A*A+2*D*A*np.sin(alpha))
    first=D*A*np.cos(alpha)/length
    second=-D*A*np.sin(alpha)/length-(D*A*np.cos(alpha))**2/length**3
    tilt=np.arctan2(A*np.cos(alpha),D+A*np.sin(alpha))
    return length,first,second,tilt


def inverse(length):
    return np.arcsin((np.asarray(length)**2-D*D-A*A)/(2*D*A))+PHASE


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    source=ROOT/'engineering/generated/contact02-study/study.json';contact=json.loads(source.read_text())
    q=np.linspace(0,np.deg2rad(122),1001);length,j,jj,tilt=motion(q);eps=1e-5
    fd=(motion(q+eps)[0]-motion(q-eps)[0])/(2*eps)
    fd2=(motion(q+eps)[1]-motion(q-eps)[1])/(2*eps)
    tests={'inverse_error_rad':float(np.max(abs(inverse(length)-q))),
           'jacobian_fd_error_mm_per_rad':float(np.max(abs(j-fd))),
           'second_derivative_fd_error_mm_per_rad2':float(np.max(abs(jj-fd2)))}
    assert tests['inverse_error_rad']<1e-12 and tests['jacobian_fd_error_mm_per_rad']<1e-7 and tests['second_derivative_fd_error_mm_per_rad2']<1e-7
    # q-68 is in [-68,54], so cos>0 throughout. L is increasing;
    # its derivative has one internal maximum at sin(alpha)=-A/D.
    # Therefore endpoint minima establish a continuous lever bound.
    endpoints=motion(np.deg2rad([0.,122.]))
    minimum_lever=float(min(endpoints[1]));maxq=PHASE-np.arcsin(A/D)
    minL,maxL=map(float,endpoints[0]);assert minL>99 and maxL<145 and minimum_lever>0
    poses=[]
    for angle in [0.,5.,10.,89.0361186636693,97.79071733445441,102.2192953611798,109.,118.063838,122.]:
        l,lever,_,b=map(float,motion(np.deg2rad(angle)))
        error=np.rad2deg(inverse(np.array([l-.3,l+.3])))-angle
        poses.append({'q_deg':angle,'length_mm':l,'extension_mm':l-97.,'lever_mm_per_rad':lever,
                      'body_tilt_deg':float(np.rad2deg(b)),'300N_ideal_torque_Nm':300*lever*.001,
                      '500N_static_ceiling_ideal_torque_Nm':500*lever*.001,
                      '0p3mm_position_error_angle_deg':error.tolist(),
                      '4p8mm_s_no_load_angular_speed_deg_s':float(np.rad2deg(4.8/lever))})
    cases=[]
    for case in contact['contact_cases']:
        if not case['all_four_paired_pads_first']:continue
        details=case['fingers'];qs=np.deg2rad([f['components']['pad_minus']['q_deg'] for f in details]);lever=motion(qs)[1]*.001
        points=[];normals=[];jac=[];groups=[]
        for index,detail in enumerate(details):
            for part in ['pad_minus','pad_plus']:
                item=detail['components'][part];points.append(np.array(item['point_head_mm'])*.001)
                normals.append(item['normal_on_object']);jac.append(item['jacobian_m_per_rad']);groups.append(index)
        com=np.mean(points,axis=0);com[:2]=0
        # Explicit conservative examples, not measured component mass/friction.
        self_weight=np.array([.15,.15,.10,.10])*9.80665*np.array([.085,.085,.060,.060])
        row={'diameter_mm':case['diameter_mm'],'z_limits_mm':case['z_limits_mm'],
             'q_deg':np.rad2deg(qs).tolist(),'lever_mm_per_rad':(lever*1000).tolist(),'cases':[]}
        for force in [150.,250.,300.]:
            cap=np.maximum(0,force*lever*.85-self_weight)
            for mu in [.3,.4,.6]:
                result=solve_grasp(points,normals,jac,com,[0,0,-39.2266,0,0,0],mu,cap,
                                   minimum_normal_N=1.,contact_to_joint=groups)
                if result['feasible']:
                    tau=np.abs(result['finger_joint_equilibrium_Nm'])
                    result['required_axial_force_including_assumed_loss_and_weight_N']=((tau+self_weight)/(.85*lever)).tolist()
                row['cases'].append({'axial_force_cap_N':force,'mu':mu,'finger_torque_cap_Nm':cap.tolist(),**result})
        cases.append(row)
    result={'revision':'LINEAR-01','status':'independent candidate; not selected or mechanically integrated',
            'inputs_sha256':{str(source.relative_to(ROOT)):hashlib.sha256(source.read_bytes()).hexdigest(),
                             'generator':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
            'crank':{'fixed_body_pin_r_z_mm':[0,-D],'radius_mm':A,'phase_deg':68.,
                     'q_intervals_deg':{'upper':[0,109],'lower':[0,122]},
                     'pin_axis':'local tangential axis, parallel to the finger joint',
                     'closed_actuator_pin_distance_mm':97.,'stroke_mm':50.},
            'continuous_domain':{'alpha_deg':[-68,54],'length_endpoints_mm':[minL,maxL],
                'stroke_margin_mm':[minL-97,147-maxL], 'minimum_lever_mm_per_rad':minimum_lever,
                'maximum_lever_mm_per_rad':float(motion(maxq)[1]),'maximum_lever_q_deg':float(np.rad2deg(maxq)),
                'monotonic_length':True,'no_crank_dead_center':True},
            'regressions':tests,'poses':poses,'grasp_cases':cases,
            'screen_assumptions':{'additional_linkage_efficiency':.85,'upper_moving_mass_kg':.15,
                'upper_COM_radius_m':.085,'lower_moving_mass_kg':.10,'lower_COM_radius_m':.06,
                'payload_kg':2.,'gravity_multiplier':2.,'minimum_normal_force_each_pad_N':1.},
            'catalog':{'candidate':'Actuonix P16-50-256-12-P','voltage_V':12,'mass_each_g':95,
                       'maximum_load_N':300,'maximum_static_N':500,'no_load_speed_mm_s':4.8,
                       'stall_current_A':1.,'maximum_duty_fraction':.20,
                       'repeatability_P_with_LAC_mm':.3,'backlash_mm':.3},
            'timing':{'upper_motion_stroke_mm':float(motion(np.deg2rad(109))[0]-minL),
                      'lower_motion_stroke_mm':maxL-minL,
                      'upper_no_load_time_lower_bound_s':float((motion(np.deg2rad(109))[0]-minL)/4.8),
                      'lower_no_load_time_lower_bound_s':(maxL-minL)/4.8,
                      'time_model':'no acceleration and catalog no-load maximum; actual loaded time is longer'},
            'unresolved':['20 percent maximum duty does not support continuous full-stroke breathing',
                'catalog maximum force is not a continuous force rating',
                'actual pin/bracket/body/harness collision and joint bearing design pending',
                'backdrive force not a safety brake, measured grip relaxation and controlled stop required',
                'P variant needs four motor drivers, feedback acquisition and limit/force control',
                'potentiometer linearity and linkage tolerance not covered by repeatability',
                'four actuators alone 380 g, not total head mass',
                'main EtherCAT and baseline CAD unchanged'],
            'manufacturing_release':False}
    (OUT/'study.json').write_text(json.dumps(result,indent=2)+'\n')
    fig,axes=plt.subplots(2,2,figsize=(12,9),layout='constrained')
    ax=axes[0,0]
    ax.plot(np.rad2deg(q),length,label='Pin distance');ax.axhline(97,color='#9b3126',ls='--');ax.axhline(147,color='#9b3126',ls='--')
    ax.set(xlabel='Finger q / deg',ylabel='Actuator pin distance / mm',title='50 mm stroke with positive end margins');ax.grid(alpha=.2)
    ax=axes[0,1];ax.plot(np.rad2deg(q),j,color='#247d80');ax.set(xlabel='Finger q / deg',ylabel='dL/dq / mm per rad',title='Continuous nonzero transmission arm');ax.grid(alpha=.2)
    ax=axes[1,0]
    for angle,col in [(0,'#8e9ca4'),(98,'#d09537'),(122,'#3b8387')]:
        a=np.deg2rad(angle)-PHASE;tip=np.array([A*np.cos(a),A*np.sin(a)])
        ax.plot([0,tip[0]],[0,tip[1]],color=col,lw=4)
        ax.plot([0,tip[0]],[-D,tip[1]],color=col,lw=2,label=f'q={angle} deg')
        ax.scatter([tip[0]],[tip[1]],color=col)
    ax.scatter([0,0],[0,-D],color='#243b48');ax.set(aspect='equal',xlabel='Root radial offset / mm',ylabel='Root axial offset / mm',title='Pin kinematics only / body envelope excluded');ax.legend()
    ax=axes[1,1]
    for force in [150,250,300]:ax.plot(np.rad2deg(q),force*j*.001*.85-.15*9.80665*.085,label=f'{force} N axial cap')
    ax.axhline(3.6210684565,color='#9b3126',ls='--',label='80 mm case upper torque')
    ax.set(xlabel='Finger q / deg',ylabel='Screened upper torque / Nm',title='Assumed 85% linkage efficiency + self-weight');ax.legend(fontsize=8);ax.grid(alpha=.2)
    fig.suptitle('Linear-01 / four independent actuator candidate / catalog limits are not qualification',fontsize=13)
    fig.savefig(OUT/'linear-drive-study.png',dpi=150);plt.close(fig)
    print(json.dumps({'continuous_domain':result['continuous_domain'],'regressions':tests,'timing':result['timing']},indent=2))
    for c in cases:
        if c['diameter_mm']==80 and c['z_limits_mm'] is None:
            print('80 mm grasp:',[(x['axial_force_cap_N'],x['mu'],x['feasible'],x.get('required_axial_force_including_assumed_loss_and_weight_N')) for x in c['cases']])

if __name__=='__main__':main()
