# SPDX-License-Identifier: CC-BY-NC-4.0
# Attribution: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Read-only vendor inputs. No third-party STEP is copied into this repository.
Usage: python verify_vendor.py --vendor-dir /path/to/work/r5-light-joint01
"""
from pathlib import Path
import argparse,json,hashlib,zipfile,xml.etree.ElementTree as E
import cadquery as cq
ROOT=Path(__file__).resolve().parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def cells(path):
    ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(path) as z:
        ss=[''.join(t.itertext()) for t in E.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si',ns)]
        out={}
        for c in E.fromstring(z.read('xl/worksheets/sheet1.xml')).findall('.//s:c',ns):
            v=c.find('s:v',ns)
            if v is not None:out[c.attrib['r']]=ss[int(v.text)] if c.attrib.get('t')=='s' else v.text
        return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--vendor-dir',type=Path,required=True);args=ap.parse_args()
    data=json.loads((ROOT/'docs/engineering/sources/r5-light-joint01.json').read_text());v=args.vendor_dir
    checked=[]
    for s in data['sources']:
        if 'repository_path' in s:p=ROOT/s['repository_path']
        else:p=v/Path(*Path(s['local_only_path']).parts[2:])
        assert p.exists(),p
        assert sha(p)==s['sha256'],p
        checked.append(s['id'])
    d=cells(v/'parameters.xlsx');values=[]
    for model,col,ratio_col in zip(data['candidate_models'],['J','T','AB'],['L','V','AD']):
        for cell,key in [(col+'15','with_brake_mass_kg'),(col+'12','without_brake_mass_kg'),(ratio_col+'6','gear_continuous_rated_Nm'),(ratio_col+'4','gear_repeated_start_stop_peak_Nm'),(ratio_col+'7','gear_momentary_shock_limit_Nm')]:
            assert abs(float(d[cell])-model[key])<1e-12,(cell,key)
            values.append([model['short_model'],cell,key,float(d[cell])])
    bbox=[]
    for r in data['cad_readback']:
        p=v/r['path'];assert sha(p)==r['sha256'];s=cq.importers.importStep(str(p)).val();bb=s.BoundingBox()
        assert s.isValid();assert len(s.Solids())==r['solids']
        dims=[bb.xlen,bb.ylen,bb.zlen]
        assert max(abs(a-b) for a,b in zip(dims,r['bbox_span_mm']))<1e-5
        bbox.append(dict(file=r['path'],valid=True,solids=len(s.Solids()),bbox_span_mm=dims))
    print(json.dumps(dict(source_hash_checks=checked,official_parameter_cell_checks=values,STEP_readback=bbox,passed=True),indent=2,ensure_ascii=False))
if __name__=='__main__':main()
