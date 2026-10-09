# SPDX-License-Identifier: CC-BY-NC-4.0
"""Reproducible local fit package; no supplier CAD or powered/load release."""
from pathlib import Path
import json,hashlib,shutil,zipfile,csv,xml.etree.ElementTree as ET
import trimesh
import numpy as np
HERE=Path(__file__).resolve().parent;OUT=HERE/'build';ROOT=HERE.parents[2]
CORE=HERE.parent/'j7-fit01/build';PREV=HERE.parent/'tool-if01/build'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
D=json.loads((OUT/'manifest.json').read_text());digest=sha(OUT/'manifest.json');audit=json.loads((OUT/'fit-audit.json').read_text())
assert not audit['overlaps'] and audit['manifest_sha256']==digest and len(audit['checks'])==442
assert D['tool_plane_shift_from_IF01_mm']==44.3 and not D['whole_arm_TCP_updated']
for rel,h in D['source_hashes'].items():assert sha(ROOT/rel)==h
for p in D['parts']:
 for folder,ext,key in [('step','.step','step_sha256'),('stl-object','.stl','object_stl_sha256'),('print-bed','.stl','print_stl_sha256')]:assert sha(OUT/folder/(p['id']+ext))==p[key]
 m=trimesh.load(OUT/'print-bed'/(p['id']+'.stl'),force='mesh')
 assert m.is_watertight and m.is_winding_consistent and m.volume>0
 assert len(trimesh.graph.connected_components(m.face_adjacency,nodes=np.arange(len(m.faces)),engine='scipy'))==1
 assert min(m.bounds[0])>=-.0001 and max(m.extents)<230
for path in (OUT/'drawings').glob('*.svg'):ET.parse(path)
drawing=json.loads((OUT/'drawings/sources.json').read_text());assert drawing['manifest_sha256']==digest
for p in drawing['parts']:assert sha(OUT/'drawings'/(p['id']+'.svg'))==p['svg_sha256']
assert sha(OUT/'drawings/recessed-section.svg')==drawing['section_svg_sha256']
for name,native in [('native-public-audit.json',OUT/'A13-TOOL-IF02.blend'),('native-actual-audit.json',ROOT/'work/arm-a13/tool-if02/actual-RS00-recessed-interface.blend')]:
 r=json.loads((OUT/name).read_text());assert r['manifest_sha256']==digest and r['native_sha256']==sha(native)
render=json.loads((OUT/'render-source.json').read_text());assert render['manifest_sha256']==digest
assert render['native_sha256']==sha(ROOT/'work/arm-a13/tool-if02/actual-RS00-recessed-interface.blend')
for name,h in render['images'].items():assert sha(OUT/name)==h
# A purchase/fit list for THIS interface only. Core motor/bearing fasteners are in FIT01.
bom=[('M4x20 socket screw',3,'Inherited core clamp; verify 0.8 mm tip gap'),('M4x35 socket screw',4,'Dummy tool stack only; recalculate for actual head'),('M4 nut',7,'Nominal 7 across flats x3.2 thick'),('M4 washer',7,'OD8.8 ID4.3 thickness0.8'),('M3x10 socket screw',2,'Front dorsal cover'),('M3x10 button head screw',2,'Rear cover; nominal head OD5.7 H1.65'),('M3x12 socket screw',2,'Face insert'),('M3 nut',6,'Nominal 5.5 across flats x2.4 thick'),('M3 washer',6,'OD7 ID3.2 thickness0.5'),('Steel pin D3x6',1,'Inherited core clock pin; retention trial'),('Steel pin D3x8',1,'Tool clock pin; retention trial'),('HFM AMK21A-103Z5-y',2,'Sizing candidate only; A/C coding and mount pending'),('HFM AMS11A-103Z5-y',2,'Sizing candidate only; actual cable assembly pending')]
with (OUT/'interface-hardware.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['item','quantity','fit_note']);w.writerows(bom)
# Nominal solid-CAD volumes are not sliced print mass or load capacity.
owned=[p for p in D['parts'] if p['role']!='fit_coupon'];vol=sum(p['volume_mm3'] for p in owned)
mass=dict(scope='Five new interface parts only, excludes inherited core, metal hardware, connectors and actual head',solid_cad_volume_mm3=vol,
 hypothetical_solid_PETG_mass_g=vol*.00127,assumed_density_g_per_cm3=1.27,actual_print_mass=False,
 centroid_mm=[sum(p['volume_mm3']*p['centroid_mm'][a] for p in owned)/vol for a in range(3)],
 tool_side_subset_ids=[p['id'] for p in owned if p['id'].startswith(('A13-IF-304','A13-IF-305'))],whole_arm_mass_model_updated=False)
(OUT/'nominal-volume.json').write_text(json.dumps(mass,indent=2)+'\n')
files=[HERE/'README.md',OUT/'interface.json',OUT/'parts.csv',OUT/'interface-hardware.csv',OUT/'nominal-volume.json',OUT/'manifest.json',OUT/'fit-audit.json',OUT/'drawings/sources.json',OUT/'A13-TOOL-IF02.blend',OUT/'native-public-audit.json',OUT/'native-actual-audit.json',OUT/'render-source.json']
for name in ['build.py','blender.py','audit_native.py','drawings.py','package.py']:files.append(HERE/name)
for folder,glob in [('step','*.step'),('print-bed','*.stl'),('drawings','*.svg')]:files.extend(sorted((OUT/folder).glob(glob)))
for name in ['recessed-closed.png','recessed-service.png','recessed-section.png']:files.append(OUT/name)
inherited=[]
for folder,idlist in [(CORE,['A13-J7-101-bearing-housing','A13-J7-102-bearing-retainer','A13-J7-103-output-journal','A13-J7-104-inner-spacer','A13-J7-105-carrier']),(PREV,['A13-IF-107-piloted-flange'])]:
 old=json.loads((folder/'manifest.json').read_text())
 for id in idlist:
  p=next(p for p in old['parts'] if p['id']==id)
  for source_folder,new_folder,ext,key in [('step','inherited-step','.step','step_sha256'),('print-bed','inherited-print-bed','.stl','print_stl_sha256')]:
   src=folder/source_folder/(id+ext);assert sha(src)==p[key]
   dst=OUT/new_folder/src.name;dst.parent.mkdir(exist_ok=True);shutil.copyfile(src,dst);files.append(dst)
   inherited.append(dict(path=str(dst.relative_to(HERE)),sha256=sha(dst),source=str(src.relative_to(ROOT))))
assert len(inherited)==12
# Context for inherited parts remains self-contained; old module ZIPs are not mixed in.
for folder,label in [(CORE,'j7-fit01'),(PREV,'tool-if01')]:
 for name in ['README.md','build/parts.csv']:
  src=folder.parent/name;dst=OUT/'inherited-context'/label/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst);files.append(dst)
 for src in sorted((folder/'drawings').glob('*.svg')):
  if src.name.startswith(tuple(p['path'].split('/')[-1].split('.')[0] for p in inherited if p['source'].startswith(str(folder.relative_to(ROOT))))):
   dst=OUT/'inherited-context'/label/'drawings'/src.name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst);dst.write_text('\n'.join(t.rstrip() for t in dst.read_text().splitlines())+'\n');files.append(dst)
ledger=OUT/'package-files.json';ledger.write_text(json.dumps(dict(manifest_sha256=digest,files=[dict(path=str(p.relative_to(HERE)),sha256=sha(p)) for p in files],
 inherited=inherited,connector_envelopes_only=True,electrical_release=False,standalone_source_reproduction=False,
 reproduction='Scripts require the parent repository and pinned local vendor sources; exported prints are independent'),indent=2)+'\n');files.append(ledger)
package=OUT/'TOOL-IF02-recessed-fit.zip'
with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,'TOOL-IF02-recessed-fit/'+p.relative_to(HERE).as_posix())
with zipfile.ZipFile(package) as z:
 assert z.testzip() is None
 assert not any('vendor/' in n or 'actual-RS00' in n for n in z.namelist())
 assert sum(n.endswith('.step') for n in z.namelist())==14
 assert sum(n.endswith('.stl') for n in z.namelist())==14
report=dict(manifest_sha256=digest,package_sha256=sha(package),package_files=len(files),new_print_files=8,inherited_print_files=6,
 exact_local_checks=len(audit['checks']),physical_trial_pass=False,exact_connector_retention=False,dynamic_harness_pass=False,
 complete_arm_print_release=False,load_3kg_pass=False)
(OUT/'package-audit.json').write_text(json.dumps(report,indent=2)+'\n');print('PACKAGE',len(files),package.stat().st_size,'bytes')
