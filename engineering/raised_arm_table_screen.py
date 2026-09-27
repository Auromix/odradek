# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Conservative rigid-part support planes for the raised candidate's ten poses.
A positive bound proves separation from an assumed infinite horizontal plane;
a negative bound alone is NOT an exact collision witness.
"""
from pathlib import Path
import hashlib,itertools,json
import cadquery as cq
import numpy as np
from build_layout import moved
from screen_integrated_collisions import box, transform_prefixes
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/raised-arm-table01'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def corners(bounds):return np.array(list(itertools.product(*np.array(bounds).T)))

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 source={}
 def load(path):
  p=ROOT/path;source[path]=sha(p);return read(p)
 old=load('engineering/generated/integrated-collision-study/poses.json')
 for n,h in old['source_sha256'].items():assert sha(ROOT/n)==h,n
 params=load('engineering/generated/raised-arm-integration01/assembly-parameters.json')
 poses=load('engineering/generated/raised-arm-integration01/collision-poses.json')
 pl=load('engineering/generated/shoulder-raise-01/part-placements.json')
 structure={}
 for n,r in old['structure'].items():
  # Fixed anchoring parts intentionally extend below the assumed table Z0;
  # their mounting holes, backing plate and tabletop thickness are separate.
  if n.startswith('BASE_'):continue
  bb=np.array(r['bbox_home_mm'])
  if n.startswith('L12_'):
   x=pl['original_L12_instances'][n[4:]];path=ROOT/'engineering/generated/shoulder-raise-01'/x['file']
   assert sha(path)==x['sha256'];source[str(path.relative_to(ROOT))]=sha(path)
   s=moved(cq.importers.importStep(str(path)).val(),np.array(x['T_world_from_part_mm']));bb=box(s)
  elif n!='J1':bb[:,2]+=35
  structure[n]=dict(bounds=bb,pre=r['pre'])
 results={}
 for state in ['open','closed']:
  suffix='' if state=='open' else '-closed'
  head=load('engineering/generated/head-integrated-03/blender-parts-manifest'+suffix+'.json')
  rows=dict(structure)
  for part in head['parts']:
   bb=np.array(part['bbox_head_mm'])+np.array(params['head_face_world_mm'])
   rows['HEAD_'+part['id']]=dict(bounds=bb,pre=7)
  for name,p in poses['poses'].items():
   if not name.endswith('_'+state):continue
   prefix=transform_prefixes(params,p['angles_deg']);bounds=[]
   for n,r in rows.items():
    T=prefix[r['pre']];points=corners(r['bounds']);world=np.einsum('ij,nj->ni',T[:3,:3],points)+T[:3,3]
    lower=float(world[:,2].min());bounds.append(dict(part=n,z_lower_bound_mm=lower))
   nearest=min(bounds,key=lambda x:x['z_lower_bound_mm'])
   moving_nearest=min([x for x in bounds if rows[x['part']]['pre']>=2],key=lambda x:x['z_lower_bound_mm'])
   results[name]=dict(angles_deg=p['angles_deg'],part_count=len(rows),minimum=nearest,moving_after_J2_minimum=moving_nearest,
      all_part_bounds_positive=nearest['z_lower_bound_mm']>0,
      potentially_below_plane=[x for x in bounds if x['z_lower_bound_mm']<=0])
   print(name,nearest,moving_nearest,flush=True)
 report=dict(revision='RAISED-ARM-TABLE01',assumed_table_surface_world_Z_mm=0,
  method='Transform all eight corners of each home actual-BREP containing AABB; min world Z is a conservative support lower bound for that pose. This is not an interpolated trajectory check.',poses=results,
  source_hashes=source,generator_sha256=sha(Path(__file__)),manufacturing_release=False,
  omissions=['Actual tabletop geometry, mounting cutouts and backing plate interaction are separate; base anchor solids excluded deliberately','No object or tools, arm/base detailed fasteners, wiring or guards','No deflection, tolerance or motion-path margin; no real environment reconstruction'])
 (OUT/'study.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
