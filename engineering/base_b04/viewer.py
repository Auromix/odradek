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

    Unindexed drawArrays permits dense curved CAD without 16-bit index wrapping.
    """
    vertices=np.asarray(mesh.triangles).reshape((-1,3))
    vertex_count=len(vertices)
    normals=np.repeat(np.asarray(mesh.face_normals),3,axis=0)
    faces=None  # Unindexed drawArrays avoids any Uint16 truncation for dense curved CAD.
    return vertices,normals,faces

cadmesh=json.loads((ROOT/'cad-surface-meshes.json').read_text()) if (ROOT/'cad-surface-meshes.json').exists() else {}
payload=[]
for p in data['parts']:
    m=trimesh.load_mesh(ROOT/p['stl'],process=True)
    if p['id'] in cadmesh:
        cm=cadmesh[p['id']];fi=np.asarray(cm['faces']).ravel();vertices=np.asarray(cm['vertices'])[fi];normals=np.asarray(cm['normals'])[fi];faces=None
    else:vertices,normals,faces=flat_render_mesh(m,p['id'])
    id=p['id'];cat=p['category']
    if cat=='environment':group='桌面 / 墙面'
    elif cat=='guide':group='拧紧工具示意'
    elif cat=='routing':group='线束空间'
    elif id.startswith('BRI-'):group='后部接口组件'
    elif cat=='component' or 'PCB' in id:group='PCB / 元件'
    elif cat in ['fastener','hardware']:group='标准件'
    elif id.startswith('B04-30'):group='外罩 / 底座灯'
    elif id.startswith('B04-40'):group='后部接口组件'
    elif id.startswith('B04-20') or id=='ENV-CONTROLLER':group='盒架 / 盒体检具'
    else:group='承力结构'
    q={k:p[k] for k in ['id','material','process','category','color','notes','step','bbox']}
    q.update(group=group,v=encoded(vertices*.001,'<f4'),n=encoded(normals,'<f4'),f=None)
    payload.append(q)
template=(Path(__file__).parent/'viewer-template.html').read_text()
template=template.replace('ODR-BASE-B04-P1','ODR-BASE-'+data['revision']).replace('P1 · 原型装配审查',data['revision']+' · 原型装配审查')
(ROOT/'index.html').write_text(template.replace('__ASSEMBLY_DATA__',json.dumps(payload,separators=(',',':'))))
print('offline viewer:',ROOT/'index.html')
