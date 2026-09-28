#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Fast source/accounting audit; CAD probes are reproduced by check_stack.py."""
import ast,csv,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent

def main():
 ast.parse((OUT/'check_stack.py').read_text())
 j=json.loads((OUT/'stack-check.json').read_text())
 s=json.loads((ROOT/'docs/engineering/sources/r5-petal-hardware01.json').read_text())
 for name,h in j['source_hashes'].items():
  assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,name
 assert len(j['fastener_probes'])==16
 for p in j['fastener_probes']:
  for k,v in p.items():
   if 'overlap_mm3' in k:assert abs(v)<1e-6,(p,k,v)
 assert j['flange_stack_sensitivity_not_supplier_tolerances'][4]['interpretation']=='zero preload'
 assert all(not v for v in j['qualified'].values())
 assert all(v is None for v in s['actual_object_friction'].values())
 ids={x['id'] for x in s['sources']};assert len(ids)==len(s['sources'])==13
 rows=list(csv.DictReader((OUT/'candidate-bom.csv').open()));assert len(rows)==11
 for row in rows:
  for id in row['source_ids'].split(';'):assert id=='FORM01' or id in ids,id
 doc=ROOT/'docs/engineering/hardware/r5-petal-hardware01.md'; links=[]
 for a in re.findall(r'\]\(([^)]+)\)',doc.read_text()):
  if not a.startswith('http'):assert (doc.parent/a).exists(),a;links.append(a)
 result=dict(revision='R5-PETAL-HW01',source_hash_count=len(j['source_hashes']),probe_count=16,material_primary_source_count=13,bom_row_count=11,local_doc_link_count=len(links),unknown_object_friction_preserved=True,release_flags_all_false=True,all_recorded_solid_probe_overlaps_below_mm3=1e-6,zero_preload_case_classified_correctly=True,pass_scope='Artifact consistency and reproducible nominal isolated-petal CAD gauges; not actual material, tool or manufacturing qualification.')
 (OUT/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
