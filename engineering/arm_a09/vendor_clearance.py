# SPDX-License-Identifier: CC-BY-NC-4.0
"""Read locally cached official CAD for shoulder checks; publish results, never supplier geometry."""
import sys,json,hashlib
from pathlib import Path
import numpy as np
import cadquery as cq
from OCP.gp import gp_Trsf
ROOT=Path(__file__).resolve().parents[2]
PINNED=json.loads((ROOT/'docs/engineering/sources/arm-a05-mechanical-sources.json').read_text())
EXPECTED={entry['local_filename']:entry['sha256'] for entry in PINNED['sources']}
sys.path.insert(0,str(ROOT/'engineering/arm_a07'));import loads as ld
sys.path.insert(0,str(ROOT/'engineering/arm_a08'));import build as helpers
def transformed(s,m):
 t=gp_Trsf();t.SetValues(*map(float,m[:3,:].flatten()));return s.transformShape(cq.Matrix(t))
def run(variant='slim'):
 out=ROOT/'engineering/arm_a09/build'/variant;d=json.loads((out/'manifest.json').read_text());ld.LAYOUT=d['layout'];f,_=ld.fk(d['layout']['poses']['reference'])
 motors={};sources=[]
 for index,file in [(1,'RS04.stp'),(2,'RS03.stp'),(5,'RS00.step'),(6,'RS00.step')]:
  j=d['layout']['joints'][index];inf=helpers.info(j);path=ROOT/'work/arm-a05/vendor'/file
  sha=hashlib.sha256(path.read_bytes()).hexdigest();assert sha==EXPECTED[file],f'Supplier source changed: {file}';raw=np.array(inf['m']['interface_frame']['T_raw_from_interface_mm'],float)
  dest=np.eye(4);dest[:3,:3]=np.column_stack([inf['u'],inf['v'],inf['n']]);dest[:3,3]=inf['out'];local=transformed(cq.importers.importStep(str(path)).val(),dest@np.linalg.inv(raw))
  pos,r=f[j['id']+'.fixed'];world=np.eye(4);world[:3,:3]=r;world[:3,3]=pos;motors[j['id']]=transformed(local,world)
  sources.append(dict(joint=j['id'],file=file,sha256=sha,reference_frame=j['id']+'.fixed'))
 parts={}
 for p in d['parts']:
  if p['id'] not in ['P01-flat-back-plate','P01-flat-top-plate','P01-output-seat','P01-J2-fixed-seat','P02-cross-shoulder-adapter','A03-in-motor-seat','P05-end-carrier','P06-end-carrier','A04-out-motor-seat']:continue
  pos,r=f[p['frame']];m=np.eye(4);m[:3,:3]=r;m[:3,3]=pos
  parts[p['id']]=transformed(cq.importers.importStep(str(out/'step'/f'{p["id"]}.step')).val(),m)
 checks=[dict(a=a+'_actual_supplier_CAD',b=b+'_actual_supplier_CAD',intersection_mm3=motors[a].intersect(motors[b]).Volume()) for a,b in [('J2','J3'),('J6','J7')]]
 for id,s in parts.items():
  for jid,motor in motors.items():
   if (id in ['P01-flat-back-plate','P01-flat-top-plate','P01-output-seat','P01-J2-fixed-seat','P02-cross-shoulder-adapter','A03-in-motor-seat']) != (jid in ['J2','J3']):continue
   checks.append(dict(a=id,b=jid+'_actual_supplier_CAD',intersection_mm3=s.intersect(motor).Volume()))
 report=dict(manifest_sha256=hashlib.sha256((out/'manifest.json').read_bytes()).hexdigest(),sources=sources,pose='reference',checks=checks,status='focused_shoulder_and_wrist_check_only',limitations=['Local source CAD only; not distributed in this package.','Supplier CAD omits actual cable plugs and assembly tolerances.','No bolt head/tool sweeps or full joint-domain qualification.'])
 (out/'vendor-clearance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(checks),flush=True)
if __name__=='__main__':run(sys.argv[1] if len(sys.argv)>1 else 'slim')
