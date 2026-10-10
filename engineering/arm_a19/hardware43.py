# SPDX-License-Identifier: CC-BY-NC-4.0
"""Ordinary elbow fastener correction, no kinematic or print-part changes."""
from pathlib import Path
import sys,json,math
import numpy as np
import cadquery as cq
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=HERE/'build/hardware43'
sys.path.insert(0,str(HERE));import wrist16 as w
c=w.c;g=c.cad

def main():
 OUT.mkdir(exist_ok=True);path=HERE/'build/assembly25/manifest.json';d=json.loads(path.read_text());assert d['role_counts']['hardware']==504
 (ROOT/'work/arm-a19/assembly25-before-hardware43.json').write_text(path.read_text())
 maps={p['id']:p for p in d['parts']};mounts=json.loads((c.OUT/'cowls04/manifest.json').read_text())['mounts'];bolts=json.loads((c.OUT/'hardware01/manifest.json').read_text())['bolts'];g.OUT=OUT;g.PARTS.clear();g.SHAPES.clear();removed=[];sources={};stacks=[]
 def oldshape(id):
  p=maps[id];source=ROOT/p['step_path'];assert c.sha(source)==p['step_sha256'];sources[p['step_path']]=c.sha(source);removed.append(id);return p,w.r.load(source)
 for k in range(1,5):
  old,shape=oldshape(f'A16-C04-H-J4-{k}');m=next(x for x in mounts if x['joint']=='J4'and x['k']==k);q=np.array(m['p_mm']);n=np.array(m['n']);bearing=q+n*11.5
  shape=g.cyl(q-n*4.5,n,1.5,16).fuse(g.cyl(bearing,n,2.85,1.65)).clean()
  socket=cq.Workplane(g.plane(bearing+n*1.75,-n)).polygon(6,2/math.cos(math.pi/6)).extrude(1.1).val();shape=shape.cut(socket).fix()
  id=f'A19-H43-J4-cover-button-{k}';g.add(id,shape,old['owner'],frame=old['frame'],role='hardware',material=old['material'],mass=shape.Volume()*7.85e-6,note='ISO7380-1 M3x16; nominal headD5.7 H1.65 AF2. Original washer, nut and16mm thread stack unchanged; cosmetic only. Actual supplier dimensions/torque pending.')
  stacks.append(dict(id=id,diameter_mm=3,length_mm=16,grip_and_head_washer_mm=12,nut_height_mm=2.4,thread_beyond_nut_mm=1.6,head_height_mm=1.65,head_diameter_mm=5.7,hex_AF_mm=2))
  old,shape=oldshape(f'A16-H-tube-4-{k}-M4');b=next(x for x in bolts if x['id']==old['id']);p=np.array(b['p_mm']);n=np.array(b['n']);shape=shape.translate((.8*n).tolist());id=f'A19-H43-tube4-{k}-M4'
  g.add(id,shape,old['owner'],frame=old['frame'],role='hardware',material=old['material'],mass=old['mass_kg'],note='ISO4762 M4x35, original bolt moved0.8mm outward by one additional DIN125 M4 washer; original washer retained.')
  washer=g.ring(p+n*(b['plate_grip_mm']+.8),n,4.5,2.2,.8);g.add(id+'-extra-washer',washer,old['owner'],frame=old['frame'],role='hardware',material=old['material'],mass=washer.Volume()*7.85e-6,note='Additional DIN125 M4 washer OD9 ID4.4 H0.8; under bolt head, not inside tube. Original tube crush sleeve and rear washer/nut remain.')
  stacks.append(dict(id=id,diameter_mm=4,length_mm=35,plate_grip_mm=28,total_head_washer_mm=1.6,rear_washer_mm=.8,nut_height_mm=3.2,thread_beyond_nut_mm=1.4))
 parts=[]
 for p in g.PARTS:
  row={k:v for k,v in p.items()if k not in ['vertices_mm','triangles']};f=OUT/'step'/(p['id']+'.step');row.update(step_path=str(f.relative_to(ROOT)),step_sha256=c.sha(f));parts.append(row)
 report=dict(revision='A19-ORDINARY-ELBOW-HARDWARE43',source_baseline_assembly_sha256=c.sha(path),source_sha256=sources,replaces_only=removed,parts=parts,stacks=stacks,print_parts_changed=False,axes_or_limits_changed=False,production_release=False,scope='Four standard cosmetic M3 button screws and four additional ordinaryM4 washers with translated originalM4 bolts. Nominal stack only; current all-pair collision and actual tool checks must be revised before publication as current assembly.')
 (OUT/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');(OUT/'meshes.json').write_text(json.dumps(g.PARTS,separators=(',',':'))+'\n');print('HARDWARE43',len(g.PARTS),flush=True)
if __name__=='__main__':main()
