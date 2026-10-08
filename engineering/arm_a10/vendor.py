# SPDX-License-Identifier: CC-BY-NC-4.0
"""Import exact pinned supplier STEP into an ignored local geometry cache.
Supplier assets retain their own rights; no supplier tessellation is published.
"""
from pathlib import Path
import hashlib,json,numpy as np,cadquery as cq,trimesh
from OCP.gp import gp_Trsf
import interfaces as c
CACHE=c.ROOT/'work/arm-a10/vendor';CACHE.mkdir(parents=True,exist_ok=True)
EXPECTED={s['local_filename']:s for s in c.SOURCE['sources']}

def transform(shape,m):
 t=gp_Trsf();t.SetValues(*map(float,m[:3,:].flatten()));return shape.transformShape(cq.Matrix(t))

def mesh(s):
 vv,tt=s.tessellate(.20,.25)
 return dict(vertices_mm=[list(v.toTuple()) for v in vv],triangles=[list(t) for t in tt])

def run():
 data=[];audit=[];raw={}
 for inf in c.I:
  j=inf['j'];f=inf['m']['step_file'];path=c.ROOT/'work/arm-a05/vendor'/f
  sha=hashlib.sha256(path.read_bytes()).hexdigest();assert sha==EXPECTED[f]['sha256']
  if f not in raw:
   wp=cq.importers.importStep(str(path));solids=[s for root in wp.vals() for s in root.Solids()];assert solids
   raw[f]=cq.Compound.makeCompound(solids)
  dest=np.eye(4);dest[:3,:3]=np.column_stack([inf['u'],inf['v'],inf['n']]);dest[:3,3]=inf['out']
  T=dest@np.linalg.inv(np.array(inf['m']['interface_frame']['T_raw_from_interface_mm']))
  full=transform(raw[f],T)
  # External output boss and locating pins follow rotor; full casing remains fixed.
  proj=inf['m']['interface_frame']['output_to_housing_front_mm']
  rotor_zone=c.legacy.cyl(inf['out']-inf['n']*proj,inf['n'],inf['pilot']+.01,proj+4)
  fs=[];rs=[]
  for source_solid in full.Solids():
   front=source_solid.intersect(rotor_zone);rear=source_solid.cut(rotor_zone)
   if front.Volume()>1e-7:rs.extend(front.Solids())
   if rear.Volume()>1e-7:fs.extend(rear.Solids())
  rotor=cq.Compound.makeCompound(rs);fixed=cq.Compound.makeCompound(fs)
  for name,s,frame in [('stator',fixed,j['id']+'.fixed'),('external-output',rotor,j['id']+'.rotor')]:
   if s.Volume()<1e-4:continue
   m=mesh(s);data.append(dict(id=j['id']+'-supplier-'+name,frame=frame,model=j['model'],role='supplier_visual_reference',source_sha256=sha,**m))
   cq.exporters.export(s,str(CACHE/(j['id']+'-'+name+'.step')))
  cq.exporters.export(full,str(CACHE/(j['id']+'-full.step')))
  bb=full.BoundingBox();source=c.SOURCE['models'][j['model']]
  source_volume=sum(s.Volume() for s in full.Solids());error=abs(source_volume-sum(s.Volume() for s in fixed.Solids())-sum(s.Volume() for s in rotor.Solids()));print(j['id'],'partition volume error',error,'relative',error/source_volume,flush=True)
  assert error<max(.5,source_volume*1e-4)
  rawdatum=np.array(source['interface_frame']['T_raw_from_interface_mm'])@np.array([0,0,0,1]);mapped=T@rawdatum;assert np.linalg.norm(mapped[:3]-inf['out'])<1e-8
  audit.append(dict(joint=j['id'],model=j['model'],file=f,source_url=EXPECTED[f]['url'],source_sha256=sha,T_joint_from_raw_mm=T.tolist(),volume_mm3=source_volume,bbox_joint_mm=[bb.xmin,bb.ymin,bb.zmin,bb.xmax,bb.ymax,bb.zmax],partition_volume_error_mm3=error,source_solids=len(raw[f].Solids()),imported_scale=1.0,interface_origin_error_mm=float(np.linalg.norm(mapped[:3]-inf['out']))))
 for item in audit:
  item['partition_cache']=dict(stator=f'work/arm-a10/vendor/{item["joint"]}-stator.step',external_output=f'work/arm-a10/vendor/{item["joint"]}-external-output.step')
 (CACHE/'meshes.json').write_text(json.dumps(data,separators=(',',':'))+'\n')
 report=dict(official_repo=c.SOURCE['official_repository'],pinned_commit=c.SOURCE['commit'],actuators=audit,geometry_status='exact STEP externally partitioned for visual output motion',partition_note='Geometric output-boss/pin partition does not establish internal rotor/stator mass or encoder zero. At mechanical reference pose the two parts reconstruct the original source.',distribution='Local cache and full-supplier Blender remain in ignored work/. Public reproduction uses importer and pinned source URLs, original model uses original analytic envelopes.')
 (c.OUT/'motor-import-audit.json').write_text(json.dumps(report,indent=2)+'\n')
 print('VENDOR IMPORT',len(audit),'motors',len(data),'mesh groups',flush=True)
if __name__=='__main__':run()
