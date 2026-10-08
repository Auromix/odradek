# SPDX-License-Identifier: CC-BY-NC-4.0
"""Incremental rebuild of identified parts from current original BREP cache.
Full clean build applies identical moving-relief rules through refine.py.
"""
import json,hashlib,cadquery as cq
import interfaces as c
import refine
b=c.legacy;ids=['P03-proximal-socket','P04-proximal-socket']
d=json.loads((c.OUT/'manifest.json').read_text());oldsha=hashlib.sha256((c.OUT/'manifest.json').read_bytes()).hexdigest()
r=json.loads((c.OUT/'collision-full.json').read_text());assert r['manifest_sha256']==oldsha
# Preserve exact certified rigid-pair geometry, never seed changed shapes.
hashes={p['id']:hashlib.sha256((c.OUT/'step'/(p['id']+'.step')).read_bytes()).hexdigest() for p in d['parts'] if p['role']!='fit_coupon'}
cert=dict(manifest_sha256=oldsha,source_report=r,report_sha256=hashlib.sha256((c.OUT/'collision-full.json').read_bytes()).hexdigest(),step_hashes=hashes,overlaps=r['checks']['idle']['overlaps'],scope='Old full named-pose report proves rigid-owner relative geometry; only exact unchanged STEP hashes can be reused.')
cache=c.ROOT/'work/arm-a10';cache.mkdir(parents=True,exist_ok=True);(cache/'certified-static-pairs.json').write_text(json.dumps(cert,indent=2)+'\n')
b.OUT=c.OUT;b.L=c.L;b.I=c.I;b.PARTS[:]=d['parts'];b.SHAPES.clear()
for p in d['parts']:b.SHAPES[p['id']]=cq.importers.importStep(str(c.OUT/'step'/(p['id']+'.step'))).val()
refine.refine(ids)
d['parts']=b.PARTS;d['incremental_refinement']=dict(parts=ids,from_manifest_sha256=oldsha,rule_file='engineering/arm_a10/refine.py',rule_sha256=hashlib.sha256((c.ROOT/'engineering/arm_a10/refine.py').read_bytes()).hexdigest())
(c.OUT/'manifest.json').write_text(json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n');brief={k:v for k,v in d.items() if k!='parts'};brief['parts']=[{k:v for k,v in p.items() if k not in ['vertices_mm','triangles']} for p in b.PARTS];(c.OUT/'parts.json').write_text(json.dumps(brief,ensure_ascii=False,indent=2)+'\n')
print('PATCHED',ids,flush=True)
