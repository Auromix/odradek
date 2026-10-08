# SPDX-License-Identifier: CC-BY-NC-4.0
"""Apply current native construction cleanup without rebuilding or rerendering."""
import ast, bpy, bmesh, struct, json, math
from pathlib import Path
from mathutils import Vector
M=.001
HERE=Path(__file__).resolve().parent
OUT=HERE/'build'/'exterior'
source=ast.parse((HERE/'blender_exterior.py').read_text())
selected=[n for n in source.body if isinstance(n,ast.FunctionDef) and n.name in ('finalize_mesh','write_stl','render_payload')]
exec(compile(ast.Module(body=selected,type_ignores=[]),'native_cleanup','exec'))
manifest=json.loads((OUT/'exterior-manifest.json').read_text())
payload=json.loads((OUT/'render-meshes.json').read_text())
for part in manifest['parts']:
    if part['category']!='custom': continue
    obj=bpy.data.objects[part['id']]
    finalize_mesh(obj)
    write_stl(obj,OUT/part['stl'])
    write_stl(obj,OUT/part['print_stl'],part['print_translation_mm'])
    payload[obj.name]=render_payload(obj)
    if part['viewer_group']=='cover_support': part['wall_nominal_mm']=None
    part['native_cleanup_isolated_triangle_sheets_removed']=obj.get('Isolated Boolean triangle sheets removed',0)
for name in ('exterior-manifest.json','manifest.json'):
    (OUT/name).write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
(OUT/'render-meshes.json').write_text(json.dumps(payload,separators=(',',':')))
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print('NATIVE_CLEANUP_COMPLETE')
