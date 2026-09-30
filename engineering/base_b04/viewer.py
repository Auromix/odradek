# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Self-contained, offline WebGL assembly viewer; no CDN or external library."""
import base64,json
from pathlib import Path
import numpy as np
import trimesh
ROOT=Path(__file__).resolve().parent/'build'
data=json.loads((ROOT/'manifest.json').read_text())
def encoded(v,dtype):return base64.b64encode(np.asarray(v,dtype=dtype).tobytes()).decode()

def flat_render_mesh(mesh, part_id):
    """Preserve CAD edges: share no render vertices across triangle faces.

    The viewer uses WebGL 1 UNSIGNED_SHORT element indices. Check the expanded
    vertex count before conversion so a later, denser export cannot wrap its
    indices silently. This affects display shading only, not the source mesh.
    """
    vertices=np.asarray(mesh.triangles).reshape((-1,3))
    vertex_count=len(vertices)
    if vertex_count>65536:
        raise ValueError(f'{part_id}: flat shading requires {vertex_count} vertices; '
                         'WebGL Uint16 supports at most 65536. Split this mesh '
                         'into draw chunks or add Uint32 index support first.')
    normals=np.repeat(np.asarray(mesh.face_normals),3,axis=0)
    faces=np.arange(vertex_count,dtype=np.uint16).reshape((-1,3))
    return vertices,normals,faces

payload=[]
for p in data['parts']:
    m=trimesh.load_mesh(ROOT/p['stl'],process=True)
    vertices,normals,faces=flat_render_mesh(m,p['id'])
    id=p['id'];cat=p['category']
    if cat=='environment':group='桌面 / 墙面'
    elif cat=='routing':group='线束空间'
    elif cat=='component' or 'PCB' in id:group='PCB / 元件'
    elif cat in ['fastener','hardware']:group='标准件'
    elif id.startswith('B04-301'):group='外罩'
    elif id.startswith('B04-20') or id=='ENV-CONTROLLER':group='盒架 / 盒体检具'
    else:group='承力结构'
    q={k:p[k] for k in ['id','material','process','category','color','notes','step','bbox']}
    q.update(group=group,v=encoded(vertices*.001,'<f4'),n=encoded(normals,'<f4'),f=encoded(faces,'<u2'))
    payload.append(q)
template=(Path(__file__).parent/'viewer-template.html').read_text()
(ROOT/'index.html').write_text(template.replace('__ASSEMBLY_DATA__',json.dumps(payload,separators=(',',':'))))
print('offline viewer:',ROOT/'index.html')
