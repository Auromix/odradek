# SPDX-License-Identifier: CC-BY-NC-4.0
"""Reopen native A09, check source identity and independent analytic FK."""
import bpy,json,hashlib,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];variant='long' if sys.argv[-1]=='long' else 'slim';OUT=ROOT/'engineering/arm_a09/build'/variant
sys.path.insert(0,str(ROOT/'engineering/arm_a07'));import loads as ld
D=json.loads((OUT/'manifest.json').read_text());ld.LAYOUT=D['layout'];ld.TARGET['flange_frame']['translation_mm']=D['flange_from_J7_mm']
sha=hashlib.sha256((OUT/'manifest.json').read_bytes()).hexdigest();assert bpy.context.scene['Source manifest SHA256']==sha
assert bpy.context.scene['Payload target kg']==3 and not bpy.context.scene['Petal head installed']
for p in D['parts']:
 o=bpy.data.objects[p['id']];assert o.parent.name==('Arm_mount_B04' if p['frame']=='world' else p['frame'])
 assert o['role']==p['role'] and len(o.data.vertices)==len(p['vertices_mm'])
assert sum(len(o.animation_data.drivers) for o in bpy.data.objects if o.animation_data)==7
root_r=ld.rotation([0,0,1],90);root_p=np.array([0,135,34.6]);max_error=0
for name,q in D['layout']['poses'].items():
 for i,v in enumerate(q,1):bpy.data.objects[f'J{i}.rotor']['angle_deg']=v;bpy.data.objects[f'J{i}.rotor'].update_tag()
 bpy.context.view_layer.update();f,_=ld.fk(q)
 for key,(p,r) in f.items():
  if key=='world':continue
  obj=bpy.data.objects['Output_flange_DATUM' if key=='flange' else key];m=np.array(obj.matrix_world)
  error=np.linalg.norm(m[:3,3]*1000-(root_p+root_r@p));max_error=max(max_error,float(error));assert error<.001,(name,key,error)
  assert np.max(abs(m[:3,:3]-root_r@r))<1e-5,(name,key)
report=dict(manifest_sha256=sha,part_objects=len(D['parts']),driven_axes=7,poses_checked=list(D['layout']['poses']),max_FK_position_error_mm=max_error,saved_native_blend_reopened=True,status='digital_geometry_only')
(OUT/'blender-audit.json').write_text(json.dumps(report,indent=2)+'\n');print('AUDIT',report)
