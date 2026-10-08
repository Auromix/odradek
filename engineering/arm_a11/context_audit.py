import sys
# SPDX-License-Identifier: CC-BY-NC-4.0
"""Reopened native assembly -> current shared base surface check at named poses.
BVH surface intersections are not solid containment, flexible-cable or load proof.
"""
import bpy,json,hashlib,itertools
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from context_source import canonical_repo
CANONICAL=canonical_repo()
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'engineering/arm_a11/build'
D=json.loads((OUT/'manifest.json').read_text());base=CANONICAL/'engineering/base_b05/build/exterior/exterior-manifest.json';B=json.loads(base.read_text())
assert bpy.context.scene['Source manifest SHA256']==hashlib.sha256((OUT/'manifest.json').read_bytes()).hexdigest()
assert bpy.context.scene['Canonical base manifest SHA256']==hashlib.sha256(base.read_bytes()).hexdigest()

def data(o):
 verts=[o.matrix_world@v.co for v in o.data.vertices];faces=[p.vertices[:] for p in o.data.polygons]
 lo=[min(v[k] for v in verts) for k in range(3)];hi=[max(v[k] for v in verts) for k in range(3)]
 return verts,faces,lo,hi
bases=[]
for p in B['parts']:
 o=bpy.data.objects[p['id']];v,f,lo,hi=data(o);bases.append((p['id'],lo,hi,BVHTree.FromPolygons(v,f,all_triangles=False,epsilon=0)))
checks=[]
for pose,q in D['layout']['poses'].items():
 for i,angle in enumerate(q,1):o=bpy.data.objects[f'J{i}.rotor'];o['angle_deg']=angle;o.update_tag()
 bpy.context.view_layer.update();hits=[];minz=1000
 for p in D['parts']:
  if p['role']=='fit_coupon':continue
  o=bpy.data.objects[p['id']];v,f,lo,hi=data(o);minz=min(minz,lo[2]*1000);tree=None
  for id,bl,bh,bt in bases:
   if any(hi[k]<=bl[k]+1e-8 or bh[k]<=lo[k]+1e-8 for k in range(3)):continue
   if tree is None:tree=BVHTree.FromPolygons(v,f,all_triangles=False,epsilon=0)
   pairs=tree.overlap(bt)
   if pairs:hits.append(dict(arm=p['id'],base=id,triangle_pairs=len(pairs)))
 checks.append(dict(pose=pose,min_arm_z_mm=minz,surface_intersections=hits,table_z0_clear=minz>=0))
 print('BASE_CONTEXT',checks[-1],flush=True)
r=dict(manifest_sha256=hashlib.sha256((OUT/'manifest.json').read_bytes()).hexdigest(),base_manifest_sha256=hashlib.sha256(base.read_bytes()).hexdigest(),base_revision=B['revision'],checks=checks,scope='Own CAD parts/analytic motor envelope vs current canonical base native surface, plus vertex table Z0 at3 named poses. Surface BVH does not prove solid containment, tolerance or load safety.',head_excluded=True,complete_assembly_qualified=False)
(OUT/'base-context-audit.json').write_text(json.dumps(r,indent=2)+'\n')
