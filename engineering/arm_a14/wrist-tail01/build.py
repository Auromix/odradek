# SPDX-License-Identifier: CC-BY-NC-4.0
"""Shorten the nonload J6 rear tail without changing any motor or clamp datum."""
from pathlib import Path
import json,hashlib,importlib.util
import numpy as np,cadquery as cq,trimesh
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=HERE/'build'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('link_shell_helpers',ROOT/'engineering/arm_a14/link-shell01/build.py');helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(helpers)
def main():
 for folder in ['step','stl-object','print-bed']:(OUT/folder).mkdir(parents=True,exist_ok=True)
 source=ROOT/'engineering/arm_a12/wrist02/build/step/A12-WR02-J6-shield-B.step'
 assert sha(source)==next(x['step_sha256'] for x in json.loads((source.parent.parent/'manifest.json').read_text())['parts'] if x['id']=='A12-WR02-J6-shield-B')
 old=cq.importers.importStep(str(source)).val();s=old.intersect(cq.Solid.makeBox(244,400,400,cq.Vector(-44,-200,-200))).fix()
 assert s.isValid() and len(s.Solids())==1
 id='A14-WT-J6-rear-shield-B';m=helpers.mesh(s);p=OUT/'step'/(id+'.step');cq.exporters.export(s,str(p));stl=OUT/'stl-object'/(id+'.stl');m.export(stl)
 # Rotate the split X plane to bed; guard rests on its planar split edges.
 R=np.array([[0,0,1],[0,1,0],[-1,0,0]],float);v=m.vertices@R.T;t=-v.min(0);v+=t;bed=trimesh.Trimesh(v,m.faces,process=False);bedpath=OUT/'print-bed'/(id+'.stl');bed.export(bedpath)
 item=dict(id=id,frame='J6.fixed',owner=5,role='nonload_wrist_guard_supported_fit',vertices_mm=m.vertices.tolist(),triangles=m.faces.tolist(),bbox_mm=m.bounds.tolist(),solid_count=1,volume_mm3=s.Volume(),mass_kg_uniform_PETG=s.Volume()*1.27e-6,centre_mm=list(s.Center().toTuple()),step_sha256=sha(p),stl_sha256=sha(stl),print_bed_sha256=sha(bedpath),print_transform=dict(rotation=R.tolist(),translation_mm=t.tolist()),print_bbox_mm=bed.bounds.tolist(),source_step_path=str(p.relative_to(ROOT)))
 sourceparts=ROOT/'engineering/arm_a14/link-shell01/build/parts.json';D=json.loads(sourceparts.read_text())
 for x in D['parts']:x['source_step_path']=str((sourceparts.parent/'step'/(x['id']+'.step')).relative_to(ROOT))
 D['parts'].append(item);D['replaces'].append('A12-WR02-J6-shield-B');D['revision']='A14-WRIST-TAIL01';D['parent_parts_sha256']=sha(sourceparts)
 D['source_files'][str(source.relative_to(ROOT))]=sha(source)
 D['tail_change']=dict(old_id='A12-WR02-J6-shield-B',new_id=id,trim_plane_J6_X_mm=-44,old_volume_mm3=old.Volume(),new_volume_mm3=s.Volume(),removed_volume_mm3=old.Volume()-s.Volume(),motor_and_hardware_moved=False,old_guard_A_retained=True)
 D['notes']+=['J6 rear guard B shortened to X>=-44; unchanged paired clamp stations at Y+/-33.5/Z84.7, no motor hole or axis changed.',
  'Rear tail trim makes a larger open service mouth; no connected electrical harness qualification is implied.',
  'LINK-SHELL01 report is historical; WRIST-TAIL01 independently rechecks the combined five owned CAD parts.']
 (OUT/'parts.json').write_text(json.dumps(D,separators=(',',':'))+'\n');print('TAIL_COMPLETE',D['tail_change'],flush=True)
if __name__=='__main__':main()
