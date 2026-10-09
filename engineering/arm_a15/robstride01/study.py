# SPDX-License-Identifier: CC-BY-NC-4.0
"""All-RobStride gravity screening. This is not a released arm layout."""
from pathlib import Path
import copy, hashlib, json, math, sys
import numpy as np
from scipy.optimize import minimize_scalar

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
OUT = HERE / 'build'
sys.path.insert(0, str(ROOT / 'engineering/arm_a07'))
import loads as ld

SOURCE = ROOT / 'engineering/arm_a11/build/manifest.json'
D = json.loads(SOURCE.read_text())
MODELS = ['RS03', 'RS04', 'RS04', 'RS04', 'RS10P', 'RS02', 'RS00']
SPECS = {
    'RS00': dict(mass_kg=.310, ratio=10, zero_speed_reference_Nm=3.6, page=5),
    'RS02': dict(mass_kg=.380, ratio=7.75, zero_speed_reference_Nm=6, page=13),
    'RS03': dict(mass_kg=.900, ratio=9, zero_speed_reference_Nm=13, page=21),
    'RS04': dict(mass_kg=1.420, ratio=9, zero_speed_reference_Nm=28.5, page=25),
    'RS10P': dict(mass_kg=.460, ratio=25, zero_speed_reference_Nm=9.5, page=35),
}
# Explicit provisional structure allowances, not CAD-measured parts. Owner is
# the last driven joint upstream of this body (J2 rotor -> owner 2).
BUDGET = [
    dict(id='shoulder_adapter', frame='J2.rotor', owner=2, mass_kg=.25, com_mm=[40,0,0]),
    dict(id='upper_frame_covers_hardware', frame='J3.rotor', owner=3, mass_kg=.60, com_mm=[170,0,0]),
    dict(id='fore_frame_covers_hardware', frame='J4.rotor', owner=4, mass_kg=.40, com_mm=[92.5,62,0]),
    dict(id='wrist_adapters_harness', frame='J5.rotor', owner=5, mass_kg=.30, com_mm=[37.5,0,20]),
    dict(id='flange_carrier_harness', frame='J7.rotor', owner=7, mass_kg=.15, com_mm=[65,0,0]),
    dict(id='moving_counterbalance_allowance', frame='J2.rotor', owner=2, mass_kg=.15, com_mm=[50,0,0]),
]

def halton(n,b):
    v=0.; f=1.
    while n:
        f/=b; v+=f*(n%b); n//=b
    return v

def rotations(axis, degrees):
    a=np.asarray(axis,float); a/=np.linalg.norm(a)
    x,y,z=a; K=np.array([[0,-z,y],[z,0,-x],[-y,x,0]])
    h=np.radians(degrees); c=np.cos(h)[:,None,None]; s=np.sin(h)[:,None,None]
    return c*np.eye(3)+(1-c)*np.outer(a,a)+s*K

def batch_gravity(layout, q, payload, budget):
    """Independent batched direct moment summation in SI units."""
    n=len(q); p=np.zeros((n,3)); R=np.broadcast_to(np.eye(3),(n,3,3)).copy()
    origins=[]; axes=[]; frames={'world':(p.copy(),R.copy())}
    for i,j in enumerate(layout['joints']):
        p=p+np.einsum('nij,j->ni',R,j['offset'])
        frames[j['id']+'.fixed']=(p.copy(),R.copy())
        origins.append(p/1000); axes.append(np.einsum('nij,j->ni',R,j['axis']))
        R=R@rotations(j['axis'],q[:,i]+j['zero_deg'])
        frames[j['id']+'.rotor']=(p.copy(),R.copy())
    frames['flange']=(p+np.einsum('nij,j->ni',R,[110,0,0]),R)
    entries=[dict(id=j['id']+'_motor',frame=j['id']+'.fixed',owner=i,
                  mass_kg=j['mass_kg'],com_mm=j['motor_center']) for i,j in enumerate(layout['joints'])]
    entries+=budget
    entries+=[dict(id='payload',frame='flange',owner=7,mass_kg=payload,com_mm=[0,0,0])]
    tau=np.zeros((n,7))
    for b in entries:
        p0,r0=frames[b['frame']]; c=(p0+np.einsum('nij,j->ni',r0,b['com_mm']))/1000
        for i in range(b['owner']):
            moment=np.cross(c-origins[i],[0,0,-9.81*b['mass_kg']])
            tau[:,i]-=np.einsum('ni,ni->n',axes[i],moment)
    return tau

def spring(q2,a=.10,b=.15):
    """Unit-force assist; fixed eye below shoulder, moving eye on J2 rotor.

    The compressed spring pushes eyes apart; its generalized force is
    F * dl/dtheta = -F*a*b*sin(theta)/l. Required motor drive is gravity
    holding torque minus this spring torque, hence +F*a*b*sin(theta)/l.
    """
    theta=np.radians(q2); length=np.sqrt(a*a+b*b+2*a*b*np.cos(theta))
    return a*b*np.sin(theta)/length, length

def maxima(tau,q):
    out=[]
    for i in range(7):
        k=int(np.argmax(abs(tau[:,i])))
        out.append(dict(joint=f'J{i+1}',model=MODELS[i],abs_Nm=float(abs(tau[k,i])),
                        signed_Nm=float(tau[k,i]),q_deg=q[k].tolist(),
                        catalog_zero_speed_reference_Nm=SPECS[MODELS[i]]['zero_speed_reference_Nm']))
    return out

def run():
    layout=copy.deepcopy(D['layout'])
    for j,model in zip(layout['joints'],MODELS):
        j['model']=model; j['mass_kg']=SPECS[model]['mass_kg']
    # Motor centres and joint offsets deliberately remain legacy placeholders.
    # New exact STEP import does not establish new joint assembly COMs.
    q=np.array(list(layout['poses'].values())+
        [[j['limits_deg'][0]+halton(k,b)*(j['limits_deg'][1]-j['limits_deg'][0])
          for j,b in zip(layout['joints'],[2,3,5,7,11,13,17])] for k in range(1,4097)],float)
    cases=[]
    for scale in [0.,1.,1.5]:
        budget=[dict(b,mass_kg=b['mass_kg']*scale) for b in BUDGET]
        raw=[batch_gravity(layout,q,p,budget) for p in [0,3]]
        unit,length=spring(q[:,1])
        # Same constant spring force for empty and loaded conditions. F=0..600 N
        # is an analytical search box, not a purchasable gas-spring specification.
        objective=lambda f:max(float(np.max(abs(t[:,1]+f*unit))) for t in raw)
        opt=minimize_scalar(objective,bounds=(0,600),method='bounded',options={'xatol':1e-8})
        force=float(opt.x); residual=[]
        for t in raw:
            s=t.copy(); s[:,1]+=force*unit; residual.append(s)
        cases.append(dict(structure_budget_scale=scale,structure_budget_mass_kg=sum(b['mass_kg'] for b in budget),
                          uncompensated={str(p):maxima(t,q) for p,t in zip([0,3],raw)},
                          ideal_constant_force_N=force,
                          compensated={str(p):maxima(t,q) for p,t in zip([0,3],residual)},
                          spring_length_sample_mm=[float(length.min()*1000),float(length.max()*1000)]))
    # Verify the independent batch sum against existing recursive solver and
    # virtual work, including an asymmetric posture and empty payload.
    ld.LAYOUT=layout;ld.TARGET['flange_frame']['translation_mm']=[110,0,0]
    ld.structure_entries=lambda:[dict(b,inertia_kg_mm2=np.zeros((3,3)).tolist(),role='provisional_budget') for b in BUDGET]
    err=[];vw=[];sp=[]
    for v in list(layout['poses'].values())+[[23,55,35,-85,68,24,42]]:
        for payload in [0,3]:
            direct=batch_gravity(layout,np.array([v],float),payload,BUDGET)[0]
            recursive=np.array([a['holding_Nm'] for a in ld.evaluate(v,payload)['axes']]);err.append(float(np.max(abs(direct-recursive))))
            for i in range(7):
                plus=v.copy();minus=v.copy();h=1e-4;plus[i]+=h;minus[i]-=h
                value=(ld.potential(plus,payload,[0,0,0])-ld.potential(minus,payload,[0,0,0]))/(2*math.radians(h))
                vw.append(abs(value-direct[i]))
        theta=v[1];h=1e-4;f=300.;a=.10;b=.15
        energy=lambda deg:-f*math.sqrt(a*a+b*b+2*a*b*math.cos(math.radians(deg)))
        derivative=(energy(theta+h)-energy(theta-h))/(2*math.radians(h))
        sp.append(abs(derivative-f*spring(np.array([theta]))[0][0]))
    assert max(err)<1e-8 and max(vw)<1e-6 and max(sp)<1e-6
    report=dict(revision='A15-RS01',supplier_constraint='RobStride only; MYACTUATOR excluded by user',
                catalogue_source=dict(version='2026.09.17',url='https://github.com/RobStride/Product_Information/blob/3f0cae4986e175337c7b03d891b899247b1f2933/灵足时代RS系列产品规格介绍(2026.09.17).pdf',sha256='76c85c3c11f15bf3adc1676d6a4b8c931ffd9c18cec41221f8ea5a8b54e22ea1'),
                target=dict(flange_payload_kg=3,upper_mm=340,fore_mm=185,flange_local_x_mm=110),
                layout_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                models=MODELS,specs=SPECS,motor_mass_kg=sum(SPECS[m]['mass_kg'] for m in MODELS),
                provisional_structure_ledger=BUDGET,samples=len(q),cases=cases,
                spring_analytical_geometry=dict(fixed_anchor_below_J2_mm=150,moving_anchor_on_J2_rotor_mm=100),
                verification=dict(max_recursive_direct_error_Nm=max(err),max_gravity_virtual_work_error_Nm=max(vw),max_spring_virtual_work_error_Nm=max(sp)),
                selection_frozen=False,geometry_released=False,production_release=False,
                limitations=['All samples are unfiltered joint-domain diagnostics, not collision-qualified poses or paths, and sampled maxima are not mathematical upper bounds.',
                    'Motor centres and joint offsets are inherited assumptions; new motor adapter geometry and measured mass split remain pending.',
                    'Structure ledger is an explicit allowance, not manufactured CAD or measured mass. Scale1.5 is sensitivity, not a safety factor.',
                    'Constant-force spring is ideal. No specific spring, attachment, stroke stop, collision, friction, temperature, fatigue or fail-safe has been selected or verified.',
                    'Zero-speed catalogue values do not guarantee enclosed-shell performance; no thermal derating or dynamic/inertia/drive-friction/harness-force qualification.',
                    'Payload is a point at the flange centre. Output-bearing reactions, flange bending and off-centre tools require separate validation.',
                    'RS10P is25:1: native dual encoders retained, but backdrive/impedance and distal packaging must be verified.'])
    OUT.mkdir(exist_ok=True);(OUT/'gravity-study.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('MODELS',MODELS,'MOTOR_MASS',report['motor_mass_kg'])
    for c in cases:
        print('BUDGET',c['structure_budget_mass_kg'],'F',round(c['ideal_constant_force_N'],2))
        for p in ['0','3']:
            print('PAYLOAD',p,'RAW',[round(a['abs_Nm'],3) for a in c['uncompensated'][p]],'COMP',[round(a['abs_Nm'],3) for a in c['compensated'][p]])
    print('VERIFIED',report['verification'])

if __name__=='__main__':run()
