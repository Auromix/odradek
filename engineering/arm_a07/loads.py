# SPDX-License-Identifier: CC-BY-NC-4.0
"""Bare-arm flange load bookkeeping. SI force/moments; geometry in mm."""
from pathlib import Path
import json, math, hashlib
import numpy as np
from functools import lru_cache

ROOT=Path(__file__).resolve().parents[2]
LAYOUT=json.loads((ROOT/'engineering/parameters/arm-a05-layout.json').read_text())
TARGET=json.loads((ROOT/'engineering/parameters/arm-a07-target.json').read_text())
BUDGET=json.loads((ROOT/'engineering/parameters/arm-a06-load-budget.json').read_text())
CATALOG=json.loads((ROOT/'docs/engineering/sources/arm-a04-qdd.json').read_text())

def rotation(axis,deg):
    a=np.asarray(axis,float); a/=np.linalg.norm(a)
    x,y,z=a; h=math.radians(deg); c,s=math.cos(h),math.sin(h)
    k=np.array([[0,-z,y],[z,0,-x],[-y,x,0]])
    return c*np.eye(3)+(1-c)*np.outer(a,a)+s*k

def fk(q):
    p=np.zeros(3); r=np.eye(3); frames={'world':(p.copy(),r.copy())}; joints=[]
    for j,a in zip(LAYOUT['joints'],q):
        p=p+r@np.array(j['offset']); frames[j['id']+'.fixed']=(p.copy(),r.copy())
        joints.append((p.copy()/1000,r@np.array(j['axis'])))
        r=r@rotation(j['axis'],a+j['zero_deg']); frames[j['id']+'.rotor']=(p.copy(),r.copy())
    f=TARGET['flange_frame']; p0,r0=frames[f['parent']]
    frames['flange']=(p0+r0@np.array(f['translation_mm']),r0)
    return frames,joints

@lru_cache(maxsize=1)
def structure_entries():
    manifest=ROOT/'engineering/arm_a08/build/manifest.json'
    if not manifest.exists():return []
    data=json.loads(manifest.read_text())
    return [{k:b[k] for k in ['id','frame','owner','mass_kg','com_mm','inertia_kg_mm2','role']} for b in data['parts'] if b['role'] in ['printed_structure','printed_cover','hardware']]

def ledger(payload,com):
    entries=[]
    for i,j in enumerate(LAYOUT['joints']):
        entries.append(dict(id=j['id']+'_motor',frame=j['id']+'.fixed',owner=i,mass_kg=j['mass_kg'],com_mm=j['motor_center'],kind='motor'))
    if structure_entries():
        for b in structure_entries():
            entries.append(dict(id=b['id'],frame=b['frame'],owner=b['owner'],mass_kg=b['mass_kg'],com_mm=b['com_mm'],kind=b['role'],inertia_kg_mm2=b['inertia_kg_mm2']))
    else:
        for b in BUDGET['structure_groups']:
            entries.append(dict(id=b['id'],frame=b['frame'],owner=int(b['frame'][1]),mass_kg=b['mass_kg'],com_mm=b['com_mm'],kind='budget'))
    entries.append(dict(id='external_flange_load',frame='flange',owner=7,mass_kg=payload,com_mm=com,kind='payload'))
    return entries

def mass_matrix(q):
    frames,joints=fk(q);H=np.zeros((7,7))
    for b in ledger(3,[0,0,0]):
        pos,r=frames[b['frame']];c=(pos+r@np.array(b['com_mm']))/1000
        jv=np.zeros((3,7));jw=np.zeros((3,7))
        for i,(p,a) in enumerate(joints):
            if b['owner']>=i+1:jv[:,i]=np.cross(a,c-p);jw[:,i]=a
        if b['kind']=='motor':
            m=next(j for j in LAYOUT['joints'] if j['id']+'_motor'==b['id']);rad=m['diameter_mm']/2000;half=m['length_mm']/2000
            # Conservative enclosure-bound tensor; not measured rotor inertia.
            ib=np.eye(3)*b['mass_kg']*(rad*rad+half*half)
        elif b['kind']=='payload':
            ib=np.eye(3)*3*.05**2 # external payload inside 50mm COM-centred sphere, assumption only
        else:ib=np.array(b.get('inertia_kg_mm2',np.zeros((3,3))))*1e-6
        H+=b['mass_kg']*(jv.T@jv)+jw.T@(r@ib@r.T)@jw
    reflected=[]
    for i,j in enumerate(LAYOUT['joints']):
        a=next(a for a in CATALOG['actuators'] if a['model']=='RobStride'+j['model'][2:]);bound=j['mass_kg']*(j['diameter_mm']/2000)**2*a['reduction_ratio']**2
        H[i,i]+=bound;reflected.append(bound)
    return H,reflected

def dynamic_screen(q):
    H,rotor=mass_matrix(q);eps=1e-4;dH=np.zeros((7,7,7))
    for k in range(7):
        p=q.copy();m=q.copy();p[k]+=math.degrees(eps);m[k]-=math.degrees(eps)
        dH[k]=(mass_matrix(p)[0]-mass_matrix(m)[0])/(2*eps)
    gamma=np.zeros((7,7,7))
    for i in range(7):
        for j in range(7):
            for k in range(7):gamma[i,j,k]=.5*(dH[k,i,j]+dH[j,i,k]-dH[i,j,k])
    a=math.radians(TARGET['proposed_motion_screening']['joint_acceleration_deg_s2']);v=math.radians(TARGET['proposed_motion_screening']['joint_speed_deg_s'])
    bound=np.sum(abs(H),axis=1)*a+np.sum(abs(gamma),axis=(1,2))*v*v
    return dict(additional_torque_bound_Nm=bound.tolist(),mass_matrix_kg_m2=H.tolist(),reflected_rotor_enclosure_bound_kg_m2=rotor,assumptions=['Rigid uniform CAD mass/inertia plus conservative motor envelope tensor.','Rotor reflected inertia overbounds using entire catalogue motor mass at housing radius; mass split remains unknown.','Payload is a 3kg mass bounded within a 50mm radius sphere about its COM.','25deg/s and30deg/s2 each joint are provisional screening conditions.','Bound excludes friction, cable forces, contact loads and thermal capacity.'])

def evaluate(q,payload=3,com=(0,0,0)):
    frames,joints=fk(q); entries=ledger(payload,com); xyz=[]
    for b in entries:
        p,r=frames[b['frame']]; xyz.append((p+r@np.array(b['com_mm']))/1000)
    axes=[]; next_p=None; F=np.zeros(3); M=np.zeros(3)
    for i in range(6,-1,-1):
        p,a=joints[i]
        if next_p is not None:M=M+np.cross(next_p-p,F)
        for b,c in zip(entries,xyz):
            if b['owner']==i+1:
                f=np.array([0,0,-9.81*b['mass_kg']]); F=F+f; M=M+np.cross(c-p,f)
        direct=sum((np.cross(c-p,[0,0,-9.81*b['mass_kg']]) for b,c in zip(entries,xyz) if b['owner']>=i+1),np.zeros(3))
        assert np.linalg.norm(M-direct)<1e-8
        drive=-float(a@M); bend=float(np.linalg.norm(M-a*(a@M)))
        axes.append(dict(joint='J'+str(i+1),holding_Nm=drive,abs_holding_Nm=abs(drive),bending_Nm=bend,force_N=F.tolist(),moment_Nm=M.tolist()))
        next_p=p
    return dict(q_deg=q,axes=list(reversed(axes)),flange_mm=frames['flange'][0].tolist(),total_mass_kg=sum(b['mass_kg'] for b in entries))

def potential(q,payload,com):
    f,_=fk(q)
    return sum(b['mass_kg']*9.81*(f[b['frame']][0]+f[b['frame']][1]@np.array(b['com_mm']))[2]/1000 for b in ledger(payload,com))

def main():
    presets={k:evaluate(v) for k,v in LAYOUT['poses'].items()}
    errors=[]
    for q in list(LAYOUT['poses'].values())+[[23,55,35,-85,68,24,42]]:
        r=evaluate(q,3,[50,25,10]); h=1e-4
        for i,a in enumerate(r['axes']):
            p=q.copy();m=q.copy();p[i]+=h;m[i]-=h
            d=(potential(p,3,[50,25,10])-potential(m,3,[50,25,10]))/(2*math.radians(h))
            errors.append(abs(d-a['holding_Nm']))
    assert max(errors)<1e-6
    table=[]
    for x in TARGET['com_screening_mm']['axial']:
        for rho in TARGET['com_screening_mm']['radial']:
            table.append(dict(com_mm=[x,rho,0],reference=evaluate(LAYOUT['poses']['reference'],3,[x,rho,0]),payload_only_roll_upper_Nm=3*9.81*rho/1000,payload_only_flange_bending_reference_Nm=3*9.81*x/1000))
    def halton(n,b):
        v=0;f=1
        while n>0:f/=b;v+=f*(n%b);n//=b
        return v
    maxima=[dict(abs_holding_Nm=-1) for _ in range(7)]
    for k in range(1,1025):
        q=[j['limits_deg'][0]+halton(k,b)*(j['limits_deg'][1]-j['limits_deg'][0]) for j,b in zip(LAYOUT['joints'],[2,3,5,7,11,13,17])]
        e=evaluate(q)
        for i,a in enumerate(e['axes']):
            if a['abs_holding_Nm']>maxima[i]['abs_holding_Nm']:maxima[i]=dict(**a,q_deg=q)
    for e in presets.values():
        for i,a in enumerate(e['axes']):
            if a['abs_holding_Nm']>maxima[i]['abs_holding_Nm']:maxima[i]=dict(**a,q_deg=e['q_deg'])
    dyn={k:dynamic_screen(q) for k,q in LAYOUT['poses'].items()}
    # Radial reactions of isolated J7 bearing pair, external load only.
    x1,x2=39.7,50.7;xf=TARGET['flange_frame']['translation_mm'][0];F=3*9.81
    reactions=dict(centre_spacing_mm=x2-x1,nominal_flange_external_load_N=F,front_reaction_N=F*(xf-x1)/(x2-x1),rear_reaction_N=F-F*(xf-x1)/(x2-x1),source_C0r_N=4100,note='Radial statics only; excludes prototype journal/cage stiffness, motor-bearing load sharing, axial load, preload and misalignment.')
    source=ROOT/'engineering/arm_a08/build/manifest.json'
    data=dict(revision='A07',source_manifest_sha256=hashlib.sha256(source.read_bytes()).hexdigest() if source.exists() else None,target=TARGET,presets=presets,com_screening=table,mass_ledger=ledger(3,[0,0,0]),sampled_gravity_maxima=maxima,sampling_note='1024 unfiltered Halton joint-domain samples +3 presets; not global maxima or collision-qualified workspace.',dynamic_screening=dyn,j7_bearing_radial_screen=reactions,verification=dict(recursive_direct_agree=True,max_virtual_work_error_Nm=max(errors)),limitations=['No enclosed holding rating.','COM grid is demand, not allowable payload envelope.','Actual rotor inertia, output bearing limits and friction remain unverified.','Structure uses CAD volume/density assumptions if A08 manifest exists; otherwise explicit A06 budget.'])
    out=ROOT/'docs/engineering/analysis/arm-a07-loads.json';out.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(reference=presets['reference'],verification=data['verification']),ensure_ascii=False))

if __name__=='__main__':main()
