# SPDX-License-Identifier: CC-BY-NC-4.0
"""Explicit current assembly, source-bound mass and virtual-work verification."""
from pathlib import Path
import json,sys,math,csv
import numpy as np
import cadquery as cq
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=HERE/'build/assembly25'
sys.path.insert(0,str(HERE));import wrist16 as w
c=w.c;f=w.f

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    oldpath=ROOT/'engineering/arm_a18/build/assembly12.json';old=json.loads(oldpath.read_text())
    paths=[HERE/'build/root22/manifest.json',HERE/'build/wrist-core19/manifest.json',HERE/'build/wrist-shell21/manifest.json']
    if (HERE/'build/hardware43/manifest.json').exists():paths.append(HERE/'build/hardware43/manifest.json')
    modules=[json.loads(p.read_text()) for p in paths];root,core,shell=modules[:3];L=core['layout']
    assert shell['layout']==L and shell['source_core_sha256']==c.sha(paths[1])
    removed=sum([d['replaces_only'] for d in modules],[]);assert len(removed)==len(set(removed))
    assert set(removed)<=set(p['id'] for p in old['parts'])
    added=sum([d['parts'] for d in modules],[])
    rows=[dict(p) for p in old['parts'] if p['id'] not in removed]+[dict(p) for p in added]
    assert len(rows)==len({p['id'] for p in rows})
    oldby={p['id']:p for p in old['parts']};oldprints={p['id']:p for p in old['print_audit']}
    for p in rows:
        if p.get('intentional_heatset_target')=='A16-C06-fore-spine-and-J5-ring':p['intentional_heatset_target']='A19-S19-fore-spine-RS03-ring'
        if p['id'].endswith('-X75') and p['id'][:-4] in oldby:
            original=oldby[p['id'][:-4]]
            # Rigidly moved existing purchased items retain original mass and
            # material, including brass inserts; do not assign steel to brass.
            p['mass_kg']=original['mass_kg'];p['material']=original.get('material','inherited purchased envelope')
        source=ROOT/p['step_path'];assert source.exists();p['step_sha256']=c.sha(source)
        if 'volume_mm3' not in p:p['volume_mm3']=w.r.load(source).Volume()
        if p['id'] in oldprints:p['print_audit']=oldprints[p['id']]
        elif p['role'].startswith('printed'):
            if p['id'] in [x['id'] for x in root['parts']]:
                stl=paths[0].parent/(p['id']+'-fit.stl')
            else:stl=source.parent.parent/'print-bed'/(p['id']+'.stl')
            p['print_audit']=dict(id=p['id'],frame=p['frame'],source_step_sha256=p['step_sha256'],print_stl_path=str(stl.relative_to(ROOT)),print_stl_sha256=c.sha(stl),bed_rotation=p.get('print_rotation',root['print_rotation']),bed_translation_mm=p.get('print_translation_mm',root['print_translation_mm']))
    budget=[dict(id=p['id'],owner=p['owner'],frame=p['frame'],mass_kg=p['mass_kg'],com_mm=p['com_mm']) for p in rows]
    for owner,mass,com in [(3,.1,[170,0,11]),(4,.08,[92.5,62,11]),(7,.06,[65,0,0]),(2,.25,[45,-80,0])]:budget.append(dict(id=f'allowance-{owner}',owner=owner,frame=f'J{owner}.rotor',mass_kg=mass,com_mm=com))
    q=np.array(list(L['poses'].values())+[[j['limits_deg'][0]+f.rs.halton(k,b)*(j['limits_deg'][1]-j['limits_deg'][0]) for j,b in zip(L['joints'],[2,3,5,7,11,13,17])] for k in range(1,4097)],float)
    t=f.torque(L,q,3,budget);errors=[]
    def potential(v):
        F=f.frames(L,v);bodies=budget+[dict(frame=j['id']+'.fixed',mass_kg=j['mass_kg'],com_mm=j['motor_center']) for j in L['joints']]
        return sum(x['mass_kg']*9.81*(F[x['frame']]@np.r_[x['com_mm'],1])[2]/1000 for x in bodies)+3*9.81*F['flange'][2,3]/1000
    for v in [L['poses']['attention'],[23,55,35,-85,68,24,42]]:
        expected=f.torque(L,np.array([v],float),3,budget)[0]
        for i in range(7):
            a=v.copy();b=v.copy();h=1e-4;a[i]+=h;b[i]-=h
            errors.append(abs((potential(a)-potential(b))/(2*math.radians(h))-expected[i]))
    assert max(errors)<1e-6
    masses=dict(own_CAD_kg=sum(p['mass_kg'] for p in rows),motors_kg=sum(j['mass_kg'] for j in L['joints']),unmodelled_allowance_kg=.49)
    report=dict(revision='A19-INTEGRATED-ASSEMBLY25',layout=L,base_context=c.base_context(),parts=rows,removed_part_ids=removed,added_part_ids=[p['id'] for p in added],source_manifests_sha256={str(p.relative_to(ROOT)):c.sha(p) for p in [oldpath]+paths},role_counts={role:sum(p['role']==role for p in rows) for role in sorted({p['role'] for p in rows})},mass_estimates=masses,estimated_bare_mass_kg=sum(masses.values()),payload_at_flange_centre_kg=3,static_sample_count=len(q),sampled_max_abs_Nm=np.max(abs(t),axis=0).tolist(),virtual_work_max_error_Nm=max(errors),budget=budget,production_release=False,collision_status='pending integrated changed-pair review',limits=['Print-density supported-fit assembly only; static motor nominal COM and0.49kg harness/remaining allowances are estimates.','No metal-contact/bolt preload/thermal/braking/physical-load or dynamic harness qualification.','The root22 finite-element report uses older A18 loads; do not treat it as this assembly stress proof.'])
    (OUT/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    with (OUT/'assembly-ledger.csv').open('w') as fp:
        writer=csv.DictWriter(fp,fieldnames=['id','frame','role','material','mass_kg','step_path']);writer.writeheader();writer.writerows({k:p.get(k,'') for k in writer.fieldnames} for p in rows)
    print('ASSEMBLY25',len(rows),report['role_counts'],report['estimated_bare_mass_kg'],report['sampled_max_abs_Nm'],flush=True)
if __name__=='__main__':main()
