# SPDX-License-Identifier: CC-BY-NC-4.0
"""Freeze project-owned B04 context; never change authoritative base checkout."""
from pathlib import Path
import json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[2];src=ROOT.parent/'odradek/engineering/base_b04/build';out=ROOT/'engineering/arm_a10/context/base_b04';out.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
d=json.loads((src/'manifest.json').read_text());selected=[];files=[]
for p in d['parts']:
 if p['category'] in ['guide','routing','environment'] or p['id'].startswith('ENV-'):continue
 selected.append(p)
 for key in ['step','stl']:
  name=p.get(key)
  if name and (src/name).exists():
   dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src/name,dest);files.append(dict(path=name,sha256=sha(dest)))
meshes=json.loads((src/'cad-surface-meshes.json').read_text());meshes={p['id']:meshes[p['id']] for p in selected if p['id'] in meshes}
(out/'cad-surface-meshes.json').write_text(json.dumps(meshes,separators=(',',':'))+'\n')
(out/'manifest.json').write_text(json.dumps(dict(revision=d.get('revision','B04'),status='read_only_context_not_arm_print_parts',parts=selected),ensure_ascii=False,indent=2)+'\n')
(out/'provenance.json').write_text(json.dumps(dict(capture_date='2026-10-08',source_manifest_sha256=sha(src/'manifest.json'),scope='Project-owned B04 context only; not a new base design or arm print release. M6 interface atZ58.',files=files),indent=2)+'\n')
print('CONTEXT',len(selected),len(files),flush=True)
