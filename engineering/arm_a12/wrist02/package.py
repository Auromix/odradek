# SPDX-License-Identifier: CC-BY-NC-4.0
"""Verify source binding and bundle only six owned, unpowered fit prototypes."""
from pathlib import Path
import json,hashlib,zipfile,re
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=HERE/'build'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda name:json.loads((OUT/name).read_text())
d=read('manifest.json');digest=sha(OUT/'manifest.json');fit=read('fit-audit.json');printing=read('fit-print-manifest.json');draw=read('drawings/sources.json')
assert fit['manifest_sha256']==printing['wrist_manifest_sha256']==digest
assert fit['all_sampled_checks_passed'] and len(fit['checks'])==24
for p in d['parts']:
 assert sha(OUT/'step'/(p['id']+'.step'))==p['step_sha256']
 assert sha(OUT/'stl-object'/(p['id']+'.stl'))==p['stl_sha256']
for p in printing['parts']:
 assert sha(OUT/'fit-print'/(p['id']+'.stl'))==p['bed_stl_sha256']
for p in draw['parts']:
 assert sha(OUT/'drawings'/(p['id']+'.svg'))==p['svg_sha256']
actual=ROOT/'work/arm-a12/wrist02/actual-motors.blend';public=OUT/'A12-A-wrist02.blend';audit=read('audit.json');render=read('render-source.json');context=read('base-context.json')
assert audit['actual_native_sha256']==read('native-actual-audit.json')['native_sha256']==render['native_sha256']==sha(actual)
assert audit['public_native_sha256']==read('native-public-audit.json')['native_sha256']==sha(public)
assert render['manifest_sha256']==digest
assert audit['base_native_sha256']==render['base_native_sha256']==context['base_native_sha256']
assert sha(ROOT/context['read_only_cache_relative_path'])==context['base_native_sha256']
assert sha(ROOT/context['base_canonical_relative_path'])==context['base_native_sha256'],'Canonical base changed again; refresh context before publication'
for folder in [ROOT/'docs/viewers/arm-body-a12-wrist02',ROOT/'work/arm-a12/wrist02/viewer-actual']:
 html=(folder/'index.html').read_text()
 scripts=re.findall(r'<script src="([^"]+)"',html)
 assert scripts and all('://' not in src and (folder/src).is_file() for src in scripts)
 assert 'id="wrist"' in html and "o.userData.wrist=p.id.startsWith('A12-WR02-')" in html
package=OUT/'wrist02-unpowered-fit.zip'
files=[HERE/'FIT-README.md',OUT/'fit-print-manifest.json',OUT/'fit-audit.json',OUT/'base-context.json',OUT/'drawings/sources.json']
for folder,suffix in [('fit-print','*.stl'),('step','*.step'),('drawings','*.svg')]:files.extend(sorted((OUT/folder).glob(suffix)))
with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
 for path in files:z.write(path,'wrist02-unpowered-fit/'+path.relative_to(HERE).as_posix())
with zipfile.ZipFile(package) as z:assert z.testzip() is None;assert len(z.namelist())==23
report=dict(status='source-linked cosmetic fit prototype only',manifest_sha256=digest,fit_sample_count=24,fit_regression_pass=True,owned_split_parts=6,exact_supplier_groups_unchanged=14,base_revision=context['base_revision'],base_native_sha256=context['base_native_sha256'],actual_native_sha256=sha(actual),public_native_sha256=sha(public),package_sha256=sha(package),package_files=23,print_release=False,load_3kg_qualified=False)
(OUT/'package-audit.json').write_text(json.dumps(report,indent=2)+'\n');print('PACKAGE',report['base_revision'],package.stat().st_size,'bytes; 23 source-linked files')
