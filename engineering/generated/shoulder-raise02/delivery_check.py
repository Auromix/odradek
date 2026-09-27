#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Freeze only this research branch; validate files without modifying old studies."""
from pathlib import Path
import sys,json,re,numpy as np,cadquery as cq
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from shoulder_raise_study import ROOT,sha,properties
OUT=Path(__file__).resolve().parent
if '--prepare' in sys.argv:
 # Only our two stage2 reports are removed before rebuilding stage1, so the
 # stage1 artifact table never accidentally hashes a superseded stage2 result.
 for name in ['ready-manifest.json','supplement.json']:(OUT/name).unlink(missing_ok=True)
 print('Prepared this branch: removed prior stage2 reports only.');raise SystemExit(0)
q=json.loads((OUT/'qa.json').read_text());m=json.loads((OUT/'part-placements.json').read_text());s=json.loads((OUT/'section-comparison.json').read_text());supp=json.loads((OUT/'supplement.json').read_text())
for p,h in m['source_hashes'].items():assert sha(ROOT/p)==h,p
for p,h in q['artifacts'].items():assert sha(OUT/p)==h,p
for p,h in supp['source_hashes'].items():assert sha(ROOT/p)==h,p
assert q['continuous_local_motion_preserved'] and q['minimum_external_gap_mm']>3.9999
checks=[]
for n,r in m['instances'].items():
 p=OUT/r['file'];assert sha(p)==r['sha256'];sld=cq.importers.importStep(str(p)).val();assert sld.isValid() and len(sld.Solids())==1;g=properties(sld,r['material'],r['density_kg_mm3']);err=abs(g['mass_kg']-r['mass_kg']);assert err<1e-10;assert np.max(abs(np.array(g['com_world_m'])-r['com_world_m']))<1e-8;assert np.max(abs(np.array(g['inertia_about_COM_world_axes_kg_m2'])-r['inertia_about_COM_world_axes_kg_m2']))<1e-10;checks.append(dict(id=n,mass_roundtrip_error_kg=err,com_roundtrip_max_error_m=float(np.max(abs(np.array(g['com_world_m'])-r['com_world_m']))),inertia_roundtrip_max_error_kg_m2=float(np.max(abs(np.array(g['inertia_about_COM_world_axes_kg_m2'])-r['inertia_about_COM_world_axes_kg_m2'])))))
a=cq.importers.importStep(str(OUT/'SHOULDER-RAISE02-original-assembly.step')).val();assert a.isValid() and len(a.Solids())==39
I=np.array(m['aggregate_original_metal']['inertia_about_COM_world_axes_kg_m2']);assert np.max(abs(I-I.T))<1e-12 and min(np.linalg.eigvalsh(I))>0
assert len(s['actual_net_slices'])==157 and s['actual_span_mm']==77.8 and s['unit_check']
doc=ROOT/'docs/engineering/shoulder-raise02-study.md';text=doc.read_text();assert '最终数值正在' not in text
links=[]
for target in re.findall(r'\]\(([^)]+)\)',text):
 if target.startswith(('http:','https:','#')):continue
 dest=(doc.parent/target.split('#')[0]).resolve();assert dest.exists(),dest;links.append(str(dest.relative_to(ROOT)))
result=dict(revision='SHOULDER-RAISE02',status='READY-for-research-review-not-manufacture',license='CC-BY-NC-4.0',required_notice='Odradek — Auromix contributors (https://github.com/Auromix/odradek)',generator_sha256=sha(ROOT/'engineering/shoulder_raise02_study.py'),doc_sha256=sha(doc),all_main_and_supplement_sources_unchanged=True,all_main_artifact_hashes_match=True,STEP_original_part_roundtrip=checks,assembly_original_and_hardware_solid_count=len(a.Solids()),aggregate_inertia_PSD=True,local_document_links_checked=links,geometry_domain_deg=[-90,90],critical_unresolved=['Tail mating plugs/cables/service envelope within1.3mm-to-body region','M4x100 exactapprovedPN/grade/effective thread and length tolerance','OEM allowed clamp and actual contact/preload/settlement/fatigue','6061 raw90mm thickstock guarantee and manufacturing review','Complete revised wholearm mass/dynamics/global collision integration'],manufacturing_release=False,FEA_performed=False,files={p.name:sha(p) for p in OUT.iterdir() if p.is_file() and p.name not in ['ready-manifest.json','run.log','probe.py']})
(OUT/'ready-manifest.json').write_text(json.dumps(result,indent=2)+'\n');print('READY',result['generator_sha256'],len(result['files']),m['aggregate_original_metal']['mass_kg'])
