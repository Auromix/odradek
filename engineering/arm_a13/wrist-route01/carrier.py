# SPDX-License-Identifier: CC-BY-NC-4.0
"""Plastic trial carrier with complete nominal J6 fixed-head sweep relief."""
from pathlib import Path
import sys,json,hashlib,importlib.util,math
import cadquery as cq,numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=HERE/'build';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'engineering/arm_a11'));import interfaces as c
spec=importlib.util.spec_from_file_location('fit',ROOT/'engineering/arm_a13/j7-fit01/build.py');fit=importlib.util.module_from_spec(spec);spec.loader.exec_module(fit)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();source=ROOT/'engineering/arm_a13/j7-fit01/build/step/A13-J7-105-carrier.step'
s=cq.importers.importStep(str(source)).val();before=s.Volume();b=c.legacy
# Fixed screw axes remain parallel to J6-Z throughout yaw. In J7.fixed, J6 origin is X=-25.
# Head occupies Z35.2..38.2. Include washer extent up to38.7 and0.4 clearance each side.
relief=b.ring([-25,0,34.8],[0,0,1],28.9,21.1,4.3)
s=s.cut(relief).clean().fix();assert s.isValid() and len(s.Solids())==1
id='A13-J7-108-yaw-clearance-carrier'
for folder in ['step','stl-object','print-bed']:(OUT/folder).mkdir(exist_ok=True)
step=OUT/'step'/(id+'.step');cq.exporters.export(s,str(step));m=fit.mesh(s);m.export(OUT/'stl-object'/(id+'.stl'))
R=np.array([[0,0,-1],[0,1,0],[1,0,0]],float);bed=m.copy();bed.vertices=bed.vertices@R.T;T=-bed.bounds[0];bed.apply_translation(T);bed.export(OUT/'print-bed'/(id+'.stl'))
assert bed.is_watertight and bed.is_winding_consistent and bed.volume>0 and max(bed.extents)<230
report=dict(id=id,frame='J7.fixed',role='modified_print_trial_carrier',replaces='A13-J7-105-carrier',
 source=str(source.relative_to(ROOT)),source_sha256=sha(source),step_sha256=sha(step),object_stl_sha256=sha(OUT/'stl-object'/(id+'.stl')),print_stl_sha256=sha(OUT/'print-bed'/(id+'.stl')),
 vertices_mm=m.vertices.tolist(),triangles=m.faces.tolist(),volume_mm3=s.Volume(),removed_volume_mm3=before-s.Volume(),removed_fraction=(before-s.Volume())/before,
 bbox_mm=m.bounds.tolist(),centroid_mm=list(s.Center().toTuple()),print_size_mm=bed.extents.tolist(),print_rotation=R.tolist(),print_translation_mm=T.tolist(),
 full_head_sweep_relief=dict(axis='+Z',axis_origin_J7_mm=[-25,0,0],R_inner_mm=21.1,R_outer_mm=28.9,z_mm=[34.8,39.1],radial_clearance_nominal_mm=.4),
 full_sweep_cutter_check_mm3=sum(z.Volume() for z in s.intersect(relief).Solids()),
 changes=['No motor size, bearing seat, axis, mounting-hole or tool-plane change','Annular pocket replaces discrete-angle local head interference'],
 metal_structure_release=False,physical_trial_pass=False)
assert report['full_sweep_cutter_check_mm3']<.05
(OUT/'carrier-manifest.json').write_text(json.dumps(report,separators=(',',':'))+'\n')
print('CARRIER',report['removed_volume_mm3'],report['removed_fraction'],bed.extents.tolist(),flush=True)
