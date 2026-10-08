# SPDX-License-Identifier: CC-BY-NC-4.0
"""Reopen both native models and compare seven frames with independent FK."""
from pathlib import Path
import bpy,json,sys,math,hashlib
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent/'build';ACTUAL='--actual' in sys.argv
native=ROOT/'work/arm-a12/whole-style01/actual-motors.blend' if ACTUAL else OUT/'A12-A-whole-style.blend'
bpy.ops.wm.open_mainfile(filepath=str(native));L=json.loads((OUT/'style-surfaces.json').read_text())['layout'];checks=[]
for name,qs in L['poses'].items():
 for j,q in zip(L['joints'],qs):bpy.data.objects[j['id']+'.rotor']['angle_deg']=q;bpy.data.objects[j['id']+'.rotor'].update_tag()
 bpy.context.view_layer.update();transform=Matrix.Translation((0,.075,.0346)) @ Matrix.Rotation(math.pi/2,4,'Z');errors=[]
 for j,q in zip(L['joints'],qs):
  transform=transform @ Matrix.Translation(Vector(j['offset'])*.001)
  fixed=bpy.data.objects[j['id']+'.fixed'].matrix_world;errors.append(max(abs(fixed[a][b]-transform[a][b]) for a in range(4) for b in range(4)))
  axis='XYZ'[j['axis'].index(1)];transform=transform @ Matrix.Rotation(math.radians(q+j['zero_deg']),4,axis)
  rotor=bpy.data.objects[j['id']+'.rotor'].matrix_world;errors.append(max(abs(rotor[a][b]-transform[a][b]) for a in range(4) for b in range(4)))
 assert max(errors)<2e-6,(name,errors);checks.append(dict(pose=name,max_transform_element_error=max(errors)))
count=len([o for o in bpy.data.collections['05_Official_Motors_LOCAL'].objects if o.type=='MESH']);assert count==(14 if ACTUAL else 0)
styles=bpy.data.collections['A12_WHOLE_STYLE_Editable_Surfaces'].objects;assert len(styles)==17
assert not bpy.context.scene['Whole style full collisions checked'] and not bpy.context.scene['3kg qualified']
report=dict(native_sha256=hashlib.sha256(native.read_bytes()).hexdigest(),actual_supplier_groups=count,new_style_surfaces=len(styles),fk_checks=checks,scope='Native reopen, seven-axis driver/FK integrity only; not collision or load proof')
(OUT/('native-actual-audit.json' if ACTUAL else 'native-public-audit.json')).write_text(json.dumps(report,indent=2)+'\n');print('NATIVE_AUDIT',ACTUAL,len(checks),count)
