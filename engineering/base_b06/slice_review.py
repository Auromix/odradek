# SPDX-License-Identifier: CC-BY-NC-4.0
"""Audit actual Orca reference slices and package editable review files.
The embedded G-code is for the reference P1S only, not a universal print job.
"""
from pathlib import Path
import json,zipfile,hashlib,shutil,re,xml.etree.ElementTree as ET
import numpy as np,trimesh
from scipy.spatial import cKDTree
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
OUT=HERE/'build/exterior';WORK=ROOT/'work/b06-slicing';DEST=OUT/'slice-review';DEST.mkdir(exist_ok=True)
CFG=ROOT/'work/b06-slice-config'
if not CFG.exists():CFG=DEST/'reference-config'
(DEST/'reference-config').mkdir(exist_ok=True)
for p in sorted(CFG.glob('*.json')):
 if p.resolve()!=(DEST/'reference-config'/p.name).resolve():shutil.copy2(p,DEST/'reference-config'/p.name)
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=[]
for stl in sorted((OUT/'print-parts').glob('*.stl')):
 p=WORK/stl.stem/(stl.stem+'-review.3mf')
 if not p.exists():p=DEST/(stl.stem+'-review.3mf')
 g=p.parent/'plate_1.gcode'
 with zipfile.ZipFile(p) as z:
  assert z.testzip() is None
  gcode=z.read('Metadata/plate_1.gcode')
  if g.exists():assert gcode==g.read_bytes()
  info=json.loads(z.read('Metadata/plate_1.json'));bbox=info['bbox_all']
  assert all(0<=v<=256 for v in bbox),bbox
  settings=json.loads(z.read('Metadata/project_settings.config'))
  assert str(settings['enable_support'])=='1' and str(settings['layer_height'])=='0.2'
  tree=ET.fromstring(z.read('Metadata/model_settings.config'))
  stats=[dict(x.attrib) for x in tree.findall('.//mesh_stat')]
  assert len(stats)==1 and all(int(v)==0 for v in stats[0].values()),stats
  modelpath=next(n for n in z.namelist() if n.startswith('3D/Objects/') and n.endswith('.model'))
  # Reference sliced 3MF preserves one source mesh and advertises production
  # extension p. Do not mislabel it as a generic Core-only 3MF export.
  model=ET.fromstring(z.read(modelpath));ns={'c':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
  vertexcount=len(model.findall('.//c:vertex',ns));tricount=len(model.findall('.//c:triangle',ns))
  assert vertexcount and tricount
  # Compare the actual source triangle soup, independent of reindexing and
  # translation used by the slicer. A current filename/hash alone cannot bind
  # a historical sliced mesh to today's geometry.
  vs=np.array([[float(v.attrib[k]) for k in ('x','y','z')] for v in model.findall('.//c:vertex',ns)])
  ts=np.array([[int(t.attrib[k]) for k in ('v1','v2','v3')] for t in model.findall('.//c:triangle',ns)])
  mesh=trimesh.load_mesh(stl,process=True)
  vs-=vs.min(axis=0);current=mesh.vertices-mesh.vertices.min(axis=0)
  assert len(ts)==len(mesh.faces),('Stale slice triangles',stl.name)
  # Slicer may retain duplicate vertices; map actual coordinates instead of
  # demanding equal indexed vertex counts. Triangle counts/topology must agree.
  error=max(cKDTree(vs).query(current)[0].max(),cKDTree(current).query(vs)[0].max())
  assert error<=.00001,('Stale slice source geometry',stl.name,error)
  # Compare sorted mapped indices rather than rounding near cell boundaries.
  mapping=cKDTree(current).query(vs)[1]
  assert sorted(map(tuple,np.sort(mapping[ts],axis=1)))==sorted(map(tuple,np.sort(mesh.faces,axis=1))),('Stale slice triangle topology',stl.name)
  header=gcode.decode().split('; HEADER_BLOCK_END')[0]
  times=re.search(r'total estimated time: ([^\n]+)',header)
  support=re.findall(r'^; FEATURE: ([^\n]+)',gcode.decode(),re.M)
 if p.resolve()!=(DEST/p.name).resolve():shutil.copy2(p,DEST/p.name)
 rows.append(dict(part=stl.name,source_stl_sha256=digest(stl),slice_3mf_sha256=digest(p),gcode_sha256=hashlib.sha256(gcode).hexdigest(),
   bed_xy_with_brim_support=bbox,mesh_repair_counters=stats[0],source_vertex_count=vertexcount,source_triangle_count=tricount,
   source_mesh_match=True,source_vertex_max_error_mm=float(error),
   estimated_time=times.group(1) if times else None,feature_types=sorted(set(support))))
report=dict(revision=json.loads((OUT/'manifest.json').read_text())['revision'],
 manifest_sha256=digest(OUT/'manifest.json'),slicer='OrcaSlicer2.4.2',reference_machine='Bambu P1S 0.4,256mm cube; not user-selected machine',
 profile_sha256={p.name:digest(p) for p in sorted(CFG.glob('*.json'))},parts=rows,
 pass_=len(rows)==5,limits=['Slice generation/CRC/repair counters/bed bounds only; no physical prints.',
 'Support removal, nut fits, optical transparency and thermal deformation require samples.',
 'Sliced 3MF has the Production extension and reference firmware G-code; select your actual printer before printing.'])
(OUT/'slice-review-checks.json').write_text(json.dumps(report,indent=2)+'\n')
(DEST/'README.txt').write_text('仅用于Orca切片评审；参考P1S0.4/PETG/0.20mm/4墙/20%填充/45°自动支撑/4mm brim。\n3MF含参考机型GCode，必须换成实际打印机后重新切片，不是通用可直接运行的打印任务。\n实际打印前检查支撑可去除性、M2/M3螺母配合和灯窗透明度。\n')
print('REFERENCE_SLICES',len(rows),[(r['part'],r['estimated_time']) for r in rows])
