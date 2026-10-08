# SPDX-License-Identifier: CC-BY-NC-4.0
"""Bind shipped prototype artifacts to their scoped geometry evidence."""
from pathlib import Path
import hashlib,json,zipfile,re

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'engineering/arm_a10/build'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(name):return json.loads((OUT/(name+'.json')).read_text())
def run():
 digest=sha(OUT/'manifest.json')
 names=['collision-quick','collision-full','collision-supplier','motion-context-audit','print-audit','blender-audit','blender-audit-actual','tool-access-audit','feasibility','archive-audit']
 reports={n:read(n) for n in names}
 assert all(d['manifest_sha256']==digest for d in reports.values())
 for n in ['collision-quick','collision-full','collision-supplier']:
  assert len(reports[n]['checks'])==3
  assert all(not p['overlaps'] for p in reports[n]['checks'].values())
 motion=reports['motion-context-audit'];assert len(motion['path_samples'])==22
 assert all(not p['overlaps'] for p in motion['path_samples'])
 assert len(motion['context_poses'])==3
 assert all(not p['overlaps'] and len(p['intentional_base_thread_fits'])==8 for p in motion['context_poses'])
 assert motion['base_context_manifest_sha256']==sha(ROOT/'engineering/arm_a10/context/base_b04/manifest.json')
 tools=reports['tool-access-audit']['checks'];assert len(tools)==117 and all(not p['overlaps'] for p in tools)
 prints=reports['print-audit'];assert (prints['print_files'],prints['assembly_prints'],prints['fit_coupons'])==(49,33,16)
 for p in prints['parts']:
  assert p['single_component'] and p['watertight']
  assert sha(OUT/p['path'])==p['sha256']
 for n in ['blender-audit','blender-audit-actual']:
  d=reports[n];assert d['saved_native_blend_reopened'] and d['driven_axes']==7 and d['max_FK_position_error_mm']<.0001
 a=reports['archive-audit'];zpath=OUT/a['archive'];assert sha(zpath)==a['sha256']
 with zipfile.ZipFile(zpath) as z:
  assert z.testzip() is None and len(z.namelist())==a['files']
  assert len([n for n in z.namelist() if n.endswith('.stl')])==49
  assert len({n.split('/')[0] for n in z.namelist()})==1
  for p in prints['parts']:
   assert hashlib.sha256(z.read(a['one_root']+'/'+p['path'])).hexdigest()==p['sha256']
  assert z.read(a['one_root']+'/odradek-a10-long-validation.blend')==(OUT/'odradek-a10-long-validation.blend').read_bytes()
  assert z.read(a['one_root']+'/viewer/index.html')==(ROOT/'docs/viewers/arm-body-a10/index.html').read_bytes()
 # Check new documentation links, excluding inline code and web addresses.
 pages=[ROOT/'engineering/arm_a10/README.md',ROOT/'docs/engineering/arm-body-a10-validation.md',ROOT/'docs/concepts/converged/arm-body-a10/README.md']
 for page in pages:
  for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',page.read_text()):
   if '://' not in target:assert (page.parent/target.split('#')[0]).exists(),(page,target)
 artifacts=[zpath,OUT/'odradek-a10-long-validation.blend',ROOT/'docs/viewers/arm-body-a10/index.html',ROOT/'docs/concepts/converged/arm-body-a10/viewer-proof.jpg']
 result=dict(manifest_sha256=digest,status='scoped_digital_fit_prototype_only',report_sha256={n:sha(OUT/(n+'.json')) for n in names},artifact_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in artifacts},print_files=49,assembly_prints=33,fit_coupons=16,named_poses=3,motion_samples=22,nominal_tool_corridors=117,limitations=['No physical print, assembly, harness or load test.','No continuous collision-free workspace or3kg rating.','J2 compact thermal margin and all printed structural strength remain unresolved.'])
 (OUT/'release-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print('RELEASE CHECK PASS',digest)
if __name__=='__main__':run()
