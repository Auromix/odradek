#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Export original-only carrier02 assemblies and inspect revised part meshes."""
import csv,json,hashlib
from pathlib import Path
import numpy as np
import cadquery as cq
import trimesh
import p16_carrier02_study as c2
c01,p16,st=c2.c01,c2.p16,c2.st
OUT,ROOT=c2.OUT,c2.ROOT

def export(f,roots,fixed,closed):
 name='P16-CARRIER-02-'+('closed' if closed else 'open')+'.step';ass=cq.Assembly(name=name[:-5]);rows=[]
 for k,s in fixed.items():ass.add(s,name=k,color=cq.Color(.5,.58,.62));rows.append((k,s))
 for i,ff in enumerate(f):
  q=ff['closure_study_deg'] if closed else 0.
  for k,s in roots[i][0].items():
   sh=st.place(s,ff,st.SIGNS[i],q);n=ff['id']+'_'+k;ass.add(sh,name=n,color=cq.Color(*((1,.65,.12) if 'LED' in k else (.25,.65,.5) if 'pad' in k else (.35,.45,.5))));rows.append((n,sh))
  for k,s in p16.envelopes(q).items():
   sh=st.place(s,ff,st.SIGNS[i]);n=ff['id']+'_P16_envelope_'+k;ass.add(sh,name=n,color=cq.Color(.12,.16,.18));rows.append((n,sh))
 ass.save(str(OUT/name));rt=cq.importers.importStep(str(OUT/name)).val();assert rt.isValid() and len(rt.Solids())==len(rows)
 return dict(filename=name,valid=rt.isValid(),solid_count=len(rt.Solids()),roundtrip_volume_delta_mm3=rt.Volume()-sum(s.Volume() for k,s in rows)),rows

def main():
 f,_,base,fixed,mods,om=c01.nominal();roots=[c2.root_parts(ff) for ff in f];out=dict(revision='P16-CARRIER-02',exports=[],parts=[])
 for closed in [False,True]:
  qa,rows=export(f,roots,fixed,closed);out['exports'].append(qa);print(qa,flush=True)
 # Revised original parts only; others inherit unchanged carrier01 QA.
 for i in [0,2]:
  for k in ['metal_blade_with_narrow_tongue','integral_steel_crank_spindle']:
   name=f[i]['id']+'_'+k;s=roots[i][0][k];path=OUT/(name+'.step');cq.exporters.export(s,str(path));vv,ff=s.tessellate(.08,.05);mesh=trimesh.Trimesh(np.array([x.toTuple() for x in vv]),np.array(ff),process=True);mesh.merge_vertices(digits_vertex=6)
   qa=dict(part=name,valid=s.isValid(),solids=len(s.Solids()),volume_mm3=s.Volume(),bbox_mm=[x.tolist() for x in st.bb(s)],mesh_watertight=bool(mesh.is_watertight),mesh_bodies=int(mesh.body_count),step_sha256=hashlib.sha256(path.read_bytes()).hexdigest());assert qa['valid'] and qa['solids']==1 and qa['mesh_watertight'] and qa['mesh_bodies']==1;out['parts'].append(qa)
 # Recompute only changed rows; bought masses and the P16 centroid proxy remain clearly inherited.
 ledger=list(csv.DictReader((c01.OUT/'mass-ledger.csv').open()));changed=[]
 for r in ledger:
  for i,ff in enumerate(f):
   for k in ['metal_blade_with_narrow_tongue','integral_steel_crank_spindle']:
    if r['part']==ff['id']+'_'+k:
     s=roots[i][0][k];m=s.Volume()*st.DENSITY[roots[i][1][k]];p=st.place(s,ff,st.SIGNS[i]).Center().toTuple();r.update(mass_g=m,head_com_x_mm=p[0],head_com_y_mm=p[1],head_com_z_mm=p[2],method='carrier02 original nominal volume * density');changed.append(r['part'])
 with (OUT/'mass-ledger.csv').open('w') as fp:
  w=csv.DictWriter(fp,fieldnames=ledger[0].keys());w.writeheader();w.writerows(ledger)
 total=sum(float(x['mass_g']) for x in ledger);com=sum(float(x['mass_g'])*np.array([float(x['head_com_'+a+'_mm']) for a in 'xyz']) for x in ledger)/total
 out['mass']=dict(modeled_mass_g=total,home_COM_proxy_head_mm=com.tolist(),changed_rows=changed,planning_remaining_mass_g=[235,520],whole_head_planning_g=[total+235,total+520],limitations='Catalog P16 mass mapped to envelope centroid proxy; other retained catalog/nominal-volume assumptions from carrier01. No J7 mass, parent24mm extension, integrated real distal lamps/pad retention or harness. Head face and J7 planes unchanged: J7 contact Z-140, face Z0.')
 out['sources_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [c01.OUT/'mass-ledger.csv',ROOT/'engineering/parameters/r4-layout.json',Path(__file__),ROOT/'engineering/p16_carrier02_study.py']}
 (OUT/'qa-mass.json').write_text(json.dumps(out,indent=2)+'\n');print(out['mass'],flush=True)
if __name__=='__main__':main()
