# SPDX-License-Identifier: CC-BY-NC-4.0
"""Export plastic copies of original metal geometry for unpowered dimensional checks."""
from pathlib import Path
import json,sys,hashlib,zipfile
import trimesh
ROOT=Path(__file__).resolve().parents[2]
def run(variant='slim'):
 out=ROOT/'engineering/arm_a09/build'/variant;file=out/'manifest.json';d=json.loads(file.read_text());fit=out/'fit-only-stl';fit.mkdir(exist_ok=True);files=[]
 for p in d['parts']:
  if p['role'] in ['motor_envelope','hardware']:continue
  if p['role'].startswith('printed'):path=out/'stl'/f'{p["id"]}.stl'
  else:
   path=fit/f'{p["id"]}.stl';mesh=trimesh.Trimesh(p['vertices_mm'],p['triangles'],process=True);assert mesh.is_watertight;mesh.export(path)
  files.append(dict(id=p['id'],source_role=p['role'],source_material=p['material'],frame=p['frame'],stl_path=path.relative_to(out).as_posix(),usage='unpowered_dimensional_check_only'))
 readme='''# A09 配合与外形检查包\n\n所有STL均为mm。本包不是完整整臂装配套件，不能用于3kg负载验证。\n\nfit-only-stl是金属设计件的塑料几何副本；其模型载荷计算仍采用金属密度，不能套用于打印副本。motor_envelope与hardware没有打印文件。\n\n先检查电机孔位、定位端面、支架避让与整体比例；端座紧固件、配合公差、关节支承、罩壳分件/固定及线束未冻结。未经固定的板件不可上电运行。\n\n长侧板可在打印平台上对角摆放；外壳/空心管可能需要支撑或二次分件。包络能放入平台不证明可无支撑打印。打印前逐件确定朝向和配合补偿。\n'''
 (out/'fit-review-README.md').write_text(readme);(out/'fit-review-manifest.json').write_text(json.dumps(dict(variant=variant,manifest_sha256=hashlib.sha256(file.read_bytes()).hexdigest(),files=files,status='dimensional_checks_not_complete_assembly_kit'),ensure_ascii=False,indent=2)+'\n')
 name=f'odradek-a09-{variant}-fit-review';archive=out/(name+'.zip')
 with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
  for p in [out/'fit-review-README.md',out/'fit-review-manifest.json']+[out/f['stl_path'] for f in files]:z.write(p,name+'/'+p.relative_to(out).as_posix())
 with zipfile.ZipFile(archive) as z:assert z.testzip() is None;assert len([n for n in z.namelist() if n.endswith('.stl')])==len(files)
 print('FIT REVIEW',variant,len(files),'STL',archive.stat().st_size)
if __name__=='__main__':run(sys.argv[1] if len(sys.argv)>1 else 'slim')
