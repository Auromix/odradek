#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Independent original-STEP endpoint check and generated artifact checksum record."""
import argparse,hashlib,json
from pathlib import Path
import cadquery as cq
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/p16-packaging-study'
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--vendor-dir',type=Path,default=ROOT.parents[1]/'work/p16-reference');args=ap.parse_args()
    p=json.loads((OUT/'study.json').read_text())
    assert all(p['checks'].values())
    assert all(x.get('passes',True) for x in p['native_CAD_interface_samples'])
    assert all(x['passes'] for x in p['internal_rigid_assembly_checks'])
    assert all(v['certified'] for checks in p['own_module_continuous_checks'].values() for v in checks.values())
    assert p['generator_sha256']==hashlib.sha256((ROOT/'engineering/p16_packaging_study.py').read_bytes()).hexdigest()
    a=cq.importers.importStep(str(args.vendor_dir/'p16_50mm_in.stp')).val().Solids()
    b=cq.importers.importStep(str(args.vendor_dir/'p16_50mm_out.stp')).val().Solids();rows=[]
    assert len(a)==11 and len(b)==12
    for i in range(11):
        old=a[i].translate((0,0,50 if i>=9 else 0));new=b[i]
        diff=old.cut(new).Volume()+new.cut(old).Volume()
        rows.append(dict(solid=i,expected_translation_mm=50 if i>=9 else 0,symmetric_difference_mm3=diff))
        assert diff<1e-5
    qa=dict(all_checks_pass=True,primary_script_sha256=p['generator_sha256'],source_assets_redistributed=False,
            files={x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in OUT.iterdir() if x.is_file() and x.name!='qa.json'},
            native_end_state_interpolation_crosscheck=rows)
    (OUT/'qa.json').write_text(json.dumps(qa,indent=2)+'\n')
    print('Full result flags and eleven source endpoint solids verified.')
if __name__=='__main__':main()
