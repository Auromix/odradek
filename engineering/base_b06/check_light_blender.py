# SPDX-License-Identifier: CC-BY-NC-4.0
"""Measure actual roof above the new PCB pocket on reopened native loft."""
import bpy,json,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
OUT=Path(bpy.data.filepath).parent
src=bpy.data.objects['Native_Shield_Loft_Source']
tree=BVHTree.FromObject(src,bpy.context.evaluated_depsgraph_get())
samples=[]
for ix in range(103):
 for iy in range(61):
  x=-25.5+.5*ix;y=154+.25*iy
  # The original LED window is intentionally open and contains the lens.
  if abs(x)<19 and 162<y<168:continue
  p,_,_,_=tree.ray_cast(Vector((x*.001,y*.001,.2)),Vector((0,0,-1)))
  if p is None:raise ValueError('Pocket extends beyond original surface')
  samples.append([x,y,p.z*1000-46.173])
minimum=min(samples,key=lambda a:a[2])
assert minimum[2]>=2.7,minimum
report={'manifest_sha256':hashlib.sha256((OUT/'manifest.json').read_bytes()).hexdigest(),
 'vertical_roof_above_pocket_mm':minimum,'sample_count':len(samples),
 'pcb_z_mm':[44.073,45.673],'gh_mated_top_budget_z_mm':52.973,
 'M2_underhead_z_mm':42.073,'M2_tip_z_mm':50.073,'M2_nut_z_mm':[47.073,48.673],
 'nominal_thread_engagement_mm':1.6,'light_screw_quantity':2,
 'pass':True,'limits':['Vertical sampled roof clearance, not normal wall thickness or strength.',
 'STEP-library component shapes/bounding boxes are separately checked by solid-fit-checks.',
 'No assembled crimp/lead bend, optical gasket, adhesive, brightness or thermal qualification.']}
(OUT/'light-fit-checks.json').write_text(json.dumps(report,indent=2)+'\n')
print('LIGHT_ROOF_CHECK',minimum,len(samples))
