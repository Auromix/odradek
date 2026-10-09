# SPDX-License-Identifier: CC-BY-NC-4.0
"""Native cap construction simplification; JSON streams, never failed STLs."""
import sys,json,numpy as np,manifold3d as md
p=json.load(sys.stdin)
v=np.asarray(p['vertices_mm'],dtype=np.float32);f=np.asarray(p['triangles'],dtype=np.uint32)
s=md.Manifold(md.Mesh(vert_properties=v,tri_verts=f))
assert s.status()==md.Error.NoError,s.status()
assert len(s.decompose())==1,'Disconnected native source cap'
r=s.simplify(.001);assert r.status()==md.Error.NoError
assert len(r.decompose())==1
m=r.to_mesh();delta=r.volume()-s.volume()
assert abs(delta)<max(.01,s.volume()*1e-4),delta
print(json.dumps({'vertices_mm':m.vert_properties[:,:3].tolist(),'triangles':m.tri_verts.tolist(),'volume_delta_mm3':delta}))
