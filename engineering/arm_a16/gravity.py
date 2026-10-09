# SPDX-License-Identifier: CC-BY-NC-4.0
"""Actual prototype-CAD mass screening; not a metal design or payload rating."""
import json,copy,sys,math,numpy as np
from scipy.optimize import minimize_scalar
import common as c
sys.path.insert(0,str(c.ROOT/'engineering/arm_a15/robstride01'));import study as rs

def main():
    budget=[];sources=[]
    for name in ['root01','skeleton01','covers01']:
        p=c.OUT/name/'manifest.json';D=json.loads(p.read_text());sources.append(dict(path=str(p.relative_to(c.ROOT)),sha256=c.sha(p)))
        budget += [dict(id=x['id'],owner=x['owner'],frame=x['frame'],mass_kg=x['mass_kg'],com_mm=x['com_mm'],mass_kind='prototype uniform printed CAD or purchased stock material') for x in D['parts']]
    for owner,mass,com in [(2,.02,[30,30,0]),(3,.10,[170,0,0]),(4,.08,[92.5,62,0]),(5,.07,[40,0,0]),(6,.04,[50,0,0]),(7,.04,[65,0,0]),(2,.25,[45,-80,0])]:
        budget.append(dict(id=f'undeveloped_allowance_{owner}_{mass}',owner=owner,frame=f'J{owner}.rotor',mass_kg=mass,com_mm=com,mass_kind='stated allowance, not CAD or supplier confirmation'))
    L=c.L;named=list(L['poses'].values());q=np.array(named+[[j['limits_deg'][0]+rs.halton(k,b)*(j['limits_deg'][1]-j['limits_deg'][0]) for j,b in zip(L['joints'],[2,3,5,7,11,13,17])] for k in range(1,4097)],float)
    raw=[rs.batch_gravity(L,q,p,budget) for p in [0,3]]
    def potential(v,payload):
        F=c.frames(v);bodies=budget+[dict(frame=j['id']+'.fixed',mass_kg=j['mass_kg'],com_mm=j['motor_center']) for j in L['joints']]
        value=sum(x['mass_kg']*9.81*(F[x['frame']]@np.r_[x['com_mm'],1])[2]/1000 for x in bodies)
        value+=payload*9.81*(F['J7.rotor']@np.array([110,0,0,1]))[2]/1000
        return value
    errors=[]
    for v in named+[[23,55,35,-85,68,24,42]]:
        t=rs.batch_gravity(L,np.array([v],float),3,budget)[0]
        for i in range(7):
            a=v.copy();b=v.copy();h=1e-4;a[i]+=h;b[i]-=h
            errors.append(abs((potential(a,3)-potential(b,3))/(2*math.radians(h))-t[i]))
    assert max(errors)<1e-6
    theta=np.radians(q[:,1]);a=.065;b=(L['joints'][1]['offset'][2]+75)/1000
    length=np.sqrt(a*a+b*b+2*a*b*np.cos(theta));lever=a*b*np.sin(theta)/length;compression=(.264-length)/.1
    def worst(f1):
        values=[]
        for prog in [1,1.6]:
            for temp in [0,50]:
                for tolerance in [.9,1.1]:
                    for friction in [-30,30]:
                        force=f1*(1+(prog-1)*compression)*(1+.0035*(temp-20))*tolerance+friction
                        values.append(max(float(np.max(abs(t[:,1]+force*lever))) for t in raw))
        return max(values)
    opt=minimize_scalar(worst,bounds=(50,420),method='bounded')
    maxima=np.max(abs(raw[1]),axis=0).tolist();refs=[rs.SPECS[j['model']]['zero_speed_reference_Nm'] for j in L['joints']]
    result=dict(revision=L['id'],layout=L,sources=sources,prototype_CAD_and_allowance_ledger=budget,
      motor_catalogue_mass_kg=sum(j['mass_kg'] for j in L['joints']),own_CAD_mass_kg=sum(b['mass_kg'] for b in budget if b['mass_kind'].startswith('prototype')),
      remaining_allowance_kg=.6,unfiltered_sample_count=len(q),loaded3kg_sampled_abs_max_Nm=maxima,
      catalogue_zero_speed_reference_Nm=refs,proposed_gas_spring_order_F1_N=float(opt.x),proposed_force_envelope_worst_shoulder_Nm=float(worst(opt.x)),
      virtual_work_max_error_Nm=max(errors),geometry_qualified_workspace=False,selection_frozen=False,production_release=False,
      limits=['These masses are the actual uniform plastic CAD plus purchased tube assumptions, not a metal skeleton mass model. Density substitution does not qualify metal manufacture.',
       'Hardware/harness and moving spring mount remain an explicit0.6kg allowance. Internal motor CG and mass split are unmeasured midpoint proxies.',
       'Gas force progression1..1.6,F1+/-10%,0..50C,friction+/-30N are proposed procurement/test assumptions, not supplier guarantees.',
       'No static torque value proves thermal holding, dynamics, brake/fall behavior, enclosure cooling, bearing reactions, material strength or continuous collision/cable clearance. Plastic fit remains unpowered and unloaded.'])
    (c.OUT/'gravity.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('CAD_MASS',result['own_CAD_mass_kg'],'RAW3',maxima,'SPRING_ASSUMPTION',opt.x,worst(opt.x),'VIRTUALWORK',max(errors),flush=True)

if __name__=='__main__':main()
