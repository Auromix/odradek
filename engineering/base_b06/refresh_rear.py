# SPDX-License-Identifier: CC-BY-NC-4.0
"""Rebuild only the rear lid in an existing B06 native scene.

Uses the identical generator functions and frozen master; no STL repair.
"""
import ast,bpy,bmesh,json,math,struct,sys
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent;OUT=Path(bpy.data.filepath).parent
D=json.loads((OUT/'manifest.json').read_text())
if D['revision'] != 'B06-COMPACT-02':
    raise RuntimeError('This historical partial rebuild is only for COMPACT-02. Use blender_compact.py for the current rear service module.')
M=.001;CENTER=(0,75);INNER_RADIUS=84;WALL=3;SEGMENTS=240
SCENE=bpy.context.scene;PARAMETERS=D['parameters']
COLLECTIONS={c.name:c for c in bpy.data.collections}
MATERIALS={k:bpy.data.materials[name] for k,name in [('armor','Graphite armor / finish reference'),('rear','Rear enclosure graphite'),('support','Black exterior carrier'),('hardware','Black screw hardware'),('nut','Purchased nut reference'),('lens','Amber light-window appearance'),('collar','Titanium-grey collar')]}
for name in ('geometry.py','blender_compact.py'):
    path=HERE/name;mod=ast.parse(path.read_text())
    funcs=ast.Module(body=[n for n in mod.body if isinstance(n,ast.FunctionDef)],type_ignores=[])
    exec(compile(funcs,str(path),'exec'),globals())
DESCRIPTORS=[];PAYLOAD={};REAR_MOUNTS=[(-60,-29),(60,-29)]
bpy.data.objects.remove(bpy.data.objects['B06-304-REAR-LID'],do_unlink=True)
lid=copy_mesh(bpy.data.objects['Native_Shield_Solid_Master'],'B06-304-REAR-LID')
boolean(lid,box('Rear lid partition',((-66.6,-80,-10),(66.6,-22.4,100))),'INTERSECT')
boolean(lid,rounded_rect_prism('Cable egress',((-54,-8),(54,18)),(-80,-25),4,'XZ'),'DIFFERENCE')
from mathutils.bvhtree import BVHTree
tree=BVHTree.FromObject(lid,bpy.context.evaluated_depsgraph_get())
for x,y in REAR_MOUNTS:
    hit,_,_,_=tree.ray_cast(Vector((x*M,y*M,.2)),Vector((0,0,-1)))
    boss(lid,x,y,hit.z/M-1)
notes=next(p['notes'] for p in D['parts'] if p['id']==lid.name)
add(lid,'独立后部检修盖','rear_lid','rear',notes)
D['parts']=[DESCRIPTORS[0] if p['id']==lid.name else p for p in D['parts']]
for name in ('manifest.json','exterior-manifest.json'):(OUT/name).write_text(json.dumps(D,ensure_ascii=False,indent=2)+'\n')
payload=json.loads((OUT/'render-meshes.json').read_text());payload.update(PAYLOAD)
(OUT/'render-meshes.json').write_text(json.dumps(payload,separators=(',',':')))
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
