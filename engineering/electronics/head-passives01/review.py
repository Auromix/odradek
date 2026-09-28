#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Independent BOM/net-map and nodal-KCL verification; NumPy required.

Optional manufacturer-PDF verification uses --vendor-source-dir for the local
reference folder. Semiconductor PDF siblings are explicitly mapped below.
Source files are not redistributed; absent PDFs do not count as verified.
"""
from pathlib import Path
import argparse,csv,hashlib,itertools,json
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
D=ROOT/'engineering/electronics/head-passives01'; P=D.parent/'head-ctrl02'
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--vendor-source-dir',type=Path)
args=ap.parse_args(); W=args.vendor_source_dir
rd=lambda p:list(csv.DictReader(p.open()))
cat=json.loads((D/'catalog.json').read_text()); check=json.loads((D/'selection-check.json').read_text()); m=json.loads((D/'manifest.json').read_text())
a=rd(P/'bom.csv'); b=rd(D/'bom-selected.csv'); o=rd(D/'selection-overlay.csv'); g=rd(D/'parts-grouped.csv'); pn=rd(P/'pin-net.csv')
am={r['ref']:r for r in a};bm={r['ref']:r for r in b};om={r['ref']:r for r in o};pm={}
for p in pn: pm.setdefault(p['ref'],{})[p['pin']]=p['net']
assert len(am)==len(bm)==len(a)==len(b)==242
assert len(o)==len(om)==193 and set(om)=={r['ref'] for r in a if r['mpn']=='TBD'}
assert all(bm[r['ref']]==r for r in a if r['mpn']!='TBD')
assert all(r['mpn']!='TBD' for r in b)
for r in o:
 ref=r['ref']; part=cat['parts'][r['mpn']]
 assert r['original_value']==am[ref]['value']
 assert r['selected_value']==bm[ref]['value']
 assert r['quantity']==am[ref]['qty']==bm[ref]['qty']=='1'
 assert r['original_footprint']==am[ref]['footprint']
 assert r['footprint_candidate']==bm[ref]['footprint']==part['footprint_candidate']
 assert json.loads(r['body_max_mm'])==part.get('body_max_mm')
 assert set(pm[ref])=={'1','2'} and [r['pin1_net'],r['pin2_net']]==[pm[ref]['1'],pm[ref]['2']]
 if ref[0] in 'RC': assert r['original_value'].split()[0]==r['selected_value'].split()[0]
 if ref[0]=='C':
  def voltage(x):return float(next(w[:-1] for w in x.split() if w.endswith('V')))
  assert voltage(r['selected_value'])>=voltage(r['original_value'])
assert sum(ref[0]=='R' for ref in om)==106 and sum(ref[0]=='C' for ref in om)==84
assert {r['ref'] for r in o if r['original_footprint']!=r['footprint_candidate']}=={'C6','C45','C51','C57','C63','C82','C83','C84','JP1','JP2','JP3'}
assert len(g)==len({r['mpn'] for r in o})==23
for r in g:
 actual={x['ref'] for x in o if x['mpn']==r['mpn']}
 assert set(r['references'].split())==actual and len(actual)==int(r['quantity'])
hundred=[r for r in o if r['original_value']=='100k']
assert len(hundred)==18 and {r['mpn'] for r in hundred}=={'RT0603BRD07100KL'}
assert cat['parts']['RT0603BRD07100KL']['tolerance_percent']==.1 and cat['parts']['RT0603BRD07100KL']['tcr_ppm_per_K']==25
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for path,h in m['files'].items():assert sha(ROOT/path)==h,path
for path,h in check['input_hashes'].items():assert sha(ROOT/path)==h,path
# Solve nodal KCL: drive source node at 1V, divider B, ADC C; Ron=0 joins B/C exactly.
def solve_network(rip,rt,rb,rd,ron):
 if ron==0:
  v= np.linalg.solve(np.array([[1/rt+1/rb+1/rd]]),np.array([1/rt]))[0];vb=vc=v
 else:
  A=np.array([[1/rt+1/rb+1/ron,-1/ron],[-1/ron,1/ron+1/rd]])
  vb,vc=np.linalg.solve(A,np.array([1/rt,0.]))
 source_i=(0 if rip is None else 1/rip)+(1-vb)/rt
 return 1/source_i,vc
lo=.999*(1-25e-6*45);hi=1.001*(1+25e-6*45)
rows=[]
for f in itertools.product((lo,hi),repeat=4):
 for ron,v,a_gain in itertools.product((0.,4.5),(.99,1.01),(.925,1.075)):
  reff,ratio=solve_network(*(np.array([6490,100000,100000,100000])*f),ron)
  rows.append((2.5*v/(.00045*a_gain*reff),ratio))
assert len(rows)==128
s=check['resistor_temperature_study']
ind={'ipropi_trip_study_A':[min(x[0] for x in rows),max(x[0] for x in rows)],'ipropi_ADC_ratio_study':[min(x[1] for x in rows),max(x[1] for x in rows)]}
vm=[]
for ft,fb,fd,ron in itertools.product((lo,hi),(lo,hi),(lo,hi),(0.,4.5)):
 rt,rb,rd=100000*ft,20000*fb,100000*fd
 _,ratio=solve_network(None,rt,rb,rd,ron);off=np.linalg.solve([[1/rt+1/rb]],[1/rt])[0]
 vm.append((ratio,off))
ind.update(VM_on_ratio_study=[min(x[0] for x in vm),max(x[0] for x in vm)],VM_off_ratio_study=[min(x[1] for x in vm),max(x[1] for x in vm)],R26_ohm_study=[.1*.99*(1-800e-6*45),.1*1.01*(1+800e-6*45)])
for k,v in ind.items(): assert np.allclose(v,s[k],rtol=0,atol=5e-12),(k,v,s[k])
maxerr=max(abs(x-y) for k,v in ind.items() for x,y in zip(v,s[k]))
# Every hashed local official source is checked, including semiconductor references in their existing folders.
sourcepass=[]
if W is not None:
 exceptions={'DRV8874':W.parent/'r4-head-drive/drv8874.pdf','LAN9252-DS':W.parent/'r4-head-lighting/lan9252.pdf','LAN9252-SQFN-checklist':W/'LAN9252-SQFN-checklist-RevB.pdf','LAN9252-EVB':W.parent/'r4-head-ctrl02/reference.pdf'}
 for k,v in cat['sources'].items():
  if v.get('sha256'):
   p=exceptions.get(k,W/(k+'.pdf'));assert sha(p)==v['sha256'],k;sourcepass.append(k)
result=dict(coverage=193,preserved_existing=49,precision_100k_count=18,package_changes=11,manifest_hashes=len(m['files']),input_hashes=len(check['input_hashes']),official_local_hashes=len(sourcepass),nodal_corner_count=len(rows),vm_corner_count=len(vm),max_difference=maxerr,independent_numeric=ind)
result.update(manufacturing_release=False, source_PDFs_checked=W is not None, review_method='Independent nodal KCL; no import of selection current_network', reviewed_manifest_sha256=sha(D/'manifest.json'), reviewer_script_sha256=sha(Path(__file__)), reviewed_document_sha256=sha(ROOT/'docs/engineering/hardware/head-passives01.md'))
(D/'independent-review.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
