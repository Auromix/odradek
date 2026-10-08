# SPDX-License-Identifier: CC-BY-NC-4.0
"""Exact local boxes transformed as eight corners give conservative world boxes."""
from pathlib import Path
import json,hashlib,cadquery as cq
import interfaces as c

def run():
 d=json.loads((c.OUT/'manifest.json').read_text());out={}
 for p in d['parts']:
  if p['role']=='fit_coupon':continue
  path=c.OUT/'step'/(p['id']+'.step');s=cq.importers.importStep(str(path)).val();bb=s.BoundingBox()
  out[p['id']]=dict(step_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bounds_mm=[bb.xmin,bb.ymin,bb.zmin,bb.xmax,bb.ymax,bb.zmax])
 vendor=json.loads((c.OUT/'motor-import-audit.json').read_text())
 for a in vendor['actuators']:
  for suffix in ['stator','external-output']:
   path=c.ROOT/'work/arm-a10/vendor'/(a['joint']+'-'+suffix+'.step')
   out[a['joint']+'-supplier-'+suffix]=dict(step_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bounds_mm=a['bbox_joint_mm'],scope='Full-motor exact local box, conservative for the geometrically partitioned subgroup.')
 path=c.ROOT/'work/arm-a10/local-bounds.json';path.write_text(json.dumps(out,indent=2)+'\n');print('BOUNDS',len(out),flush=True)
if __name__=='__main__':run()
