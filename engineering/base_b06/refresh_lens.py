# SPDX-License-Identifier: CC-BY-NC-4.0
"""Rebuild only the optical lens in an existing B06 native scene.

Uses the identical generator functions and frozen master; no STL repair.
"""
import ast,bpy,bmesh,json,math,struct,sys
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent;OUT=Path(bpy.data.filepath).parent
D=json.loads((OUT/'manifest.json').read_text())
M=.001;CENTER=(0,75);INNER_RADIUS=84;WALL=3;SEGMENTS=240
SCENE=bpy.context.scene;PARAMETERS=D['parameters']
COLLECTIONS={c.name:c for c in bpy.data.collections}
MATERIALS={k:bpy.data.materials[name] for k,name in [('armor','Graphite armor / finish reference'),('rear','Rear enclosure graphite'),('support','Black exterior carrier'),('hardware','Black screw hardware'),('nut','Purchased nut reference'),('lens','Amber light-window appearance'),('collar','Titanium-grey collar')]}
for name in ('geometry.py','blender_compact.py'):
    path=HERE/name;mod=ast.parse(path.read_text())
    funcs=ast.Module(body=[n for n in mod.body if isinstance(n,ast.FunctionDef)],type_ignores=[])
    exec(compile(funcs,str(path),'exec'),globals())
DESCRIPTORS=[];PAYLOAD={}
bpy.data.objects.remove(bpy.data.objects['B06-306-LIGHT-LENS'],do_unlink=True)
master=bpy.data.objects['Native_Shield_Solid_Master']
lens=light_lens(master);lens.name='B06-306-LIGHT-LENS'

if bpy.data.objects.get('B06-308-LENS-RETAINER'):bpy.data.objects.remove(bpy.data.objects['B06-308-LENS-RETAINER'],do_unlink=True)
bar=lamp_retainer(master,lens)
add(lens,'琥珀透光灯窗','cover','lens',['Curved closed optical blank; separate inner retaining bar; optical PCB pending'])
add(bar,'灯窗内藏压条','cover_support','support',['Two M2x6 screws into cover pilot bosses; nominal0.3mm seat allowance; centre pad0.4mm below glass; compliant optical shim required; physical fit coupon required'])
changes={p['id']:p for p in DESCRIPTORS}
D['parts']=[changes.pop(p['id'],p) for p in D['parts']];D['parts'].extend(changes.values())
D['scope']=D['parameters']['prototype_scope']='Five printed cosmetic/PCB locating parts; frozen A11 root and full-size I/O; no load chassis or PCB release'
for name in ('manifest.json','exterior-manifest.json'):(OUT/name).write_text(json.dumps(D,ensure_ascii=False,indent=2)+'\n')
payload=json.loads((OUT/'render-meshes.json').read_text());payload.update(PAYLOAD)
(OUT/'render-meshes.json').write_text(json.dumps(payload,separators=(',',':')))
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
