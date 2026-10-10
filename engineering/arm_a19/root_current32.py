# SPDX-License-Identifier: CC-BY-NC-4.0
"""Reuse exact root meshes for updated assembly loads plus root metal weight."""
from pathlib import Path
import sys,json
HERE=Path(__file__).resolve().parent;OUT=HERE/'build/assembly25'
sys.path.insert(0,str(HERE));import root_p2_23 as p
def main():
    path=OUT/'load27.json';d=json.loads(path.read_text())
    assert d['source_assembly_sha256']==p.c.sha(OUT/'manifest.json')
    assert d['source_root_manifest_sha256']==p.c.sha(HERE/'build/root22/manifest.json')
    d['include_metal_root_self_weight']=True;records=[]
    for size in [4,3]:
        result=p.solve(size,d);records.append(result);(OUT/f'root32-mesh-{size}.json').write_text(json.dumps(result,indent=2)+'\n');print('ROOT32',size,[(x['case'],x['maximum_all_dof_displacement_mm']) for x in result['cases']],flush=True)
    changes=[dict(case=b['case'],displacement_change_fraction=abs(b['maximum_all_dof_displacement_mm']-a['maximum_all_dof_displacement_mm'])/b['maximum_all_dof_displacement_mm'],energy_change_fraction=abs(b['strain_energy_Nmm']-a['strain_energy_Nmm'])/b['strain_energy_Nmm']) for a,b in zip(records[0]['cases'],records[1]['cases'])]
    report=dict(revision='A19-CURRENT-ROOT32-P2',source_assembly_sha256=d['source_assembly_sha256'],source_load27_sha256=p.c.sha(path),source_root_manifest_sha256=d['source_root_manifest_sha256'],source_solver_sha256=p.c.sha(HERE/'root_p2_23.py'),meshes=records,refinement=changes,root_material=d['material'],body_weight_model='Metal root volume gravity included. Rest of arm masses from current prototype CAD and nominal motor/allowance budget.',production_release=False,scope='Static current gravity loads with ideal four rigid washer supports and distributed annular motor traction. No spring loads/contact/preload/table clamp compliance/dynamics/fatigue or physical qualification; singular peak stress is not acceptance.')
    (OUT/'root32.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
