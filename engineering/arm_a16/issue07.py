# SPDX-License-Identifier: CC-BY-NC-4.0
"""Selected whole-body manufacturing data identity audit, no physical release."""
import csv,json,hashlib,zipfile
from pathlib import Path
import fitz,trimesh
import common as c
from assembly_sources import collect

def main():
    O=c.ROOT/'manufacturing/selected/arm-body-a16-fit';record=json.loads((O/'manifest.json').read_text())
    rows,sources,operations=collect(last='skins06');assert record['layout']==c.L and record['replacement_chain']==operations
    assert [p['id'] for p in rows]==[p['id'] for p in record['parts']]
    for path,digest in record['source_sha256'].items():assert c.sha(c.ROOT/path)==digest,path
    assert record['base_context']==c.base_context()
    assert len(list((O/'step').glob('*.step')))==len(rows)==541
    for p in rows:assert c.sha(O/'step'/(p['id']+'.step'))==c.sha(c.ROOT/p['step_path'])
    printable=[p for p in rows if p['role'].startswith('printed')]
    assert len(printable)==len(list((O/'print-bed').glob('*.stl')))==41
    for p in record['print_parts']:
        file=O/'print-bed'/(p['id']+'.stl');assert c.sha(file)==p['print_stl_sha256']
        m=trimesh.load(file,force='mesh');assert m.is_watertight and m.is_winding_consistent and len(m.split())==1
        assert max(m.extents)<250 and abs(m.bounds[0,2])<1e-4
    draws=fitz.open(O/'drawings/41-print-part-fit-drawings.pdf');assert len(draws)==41
    for i,p in enumerate(record['print_parts']):
        text=draws[i].get_text()
        expected={'A16-R101-base-adapter':'A16-R101 BASE ADAPTER','A16-R103-J1-output-pedestal':'A16-R103 J1 OUTPUT PEDESTAL'}.get(p['id'],p['id'])
        assert expected in text,(i,p['id'])
    assert len(fitz.open(O/'drawings/3-stock-cut-drill-fit-drawings.pdf'))==3
    with (O/'assembly-BOM.csv').open() as f:bom=list(csv.DictReader(f));assert len(bom)==541
    assert {p['id'] for p in bom}=={p['id'] for p in rows}
    with (O/'actuator-candidate-list.csv').open() as f:actuators=list(csv.DictReader(f));assert len(actuators)==7
    with (O/'cover-mount-table.csv').open() as f:mounts=list(csv.DictReader(f));assert len(mounts)==36
    public=json.loads((O/'records/public-native07-audit.json').read_text())
    assert public['own_meshes']==541 and public['canonical_base_meshes']==221 and not public['supplier_mesh_data_present']
    assert c.sha(c.ROOT/public['public_native_path'])==public['public_native_sha256']
    assert public['canonical_world_geometry_unchanged']
    motion=json.loads((O/'records/motion07.json').read_text());assert motion['sampled_clear'] and motion['sample_count']==26
    native=json.loads((O/'records/native-modules-audit.json').read_text())
    assert c.sha(c.ROOT/native['native_path'])==native['native_sha256']
    assert native['own_part_count']==541 and native['canonical_base_world_geometry_unchanged']
    for field in ['production_release','physical_print_qualified','thermal_payload_qualified','whole_motion_qualified','connected_harness_qualified','metal_manufacturing_qualified']:assert record[field] is False
    archive=O/'A16-complete-body-supported-fit.zip'
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for line in z.read('SHA256SUMS.txt').decode().splitlines():
            digest,name=line.split('  ',1);assert hashlib.sha256(z.read(name)).hexdigest()==digest
            assert c.sha(O/name)==digest,name
        assert z.read('manifest.json')==(O/'manifest.json').read_bytes()
    report=dict(layout=c.L,selected_manifest_sha256=c.sha(O/'manifest.json'),archive_sha256=c.sha(archive),
        audit_script_sha256=c.sha(Path(__file__)),own_part_count=541,printed_count=41,stock_piece_count=6,nominal_hardware_count=494,
        printed_drawing_pages=41,stock_drawing_pages=3,cover_mount_axes=36,actuator_candidates=7,
        source_chain_pass=True,closed_bed_meshes_pass=True,BOM_drawing_ID_pass=True,archive_CRC_SHA_pass=True,
        private_native_source_identity_pass=True,public_native_no_supplier_mesh_data=True,canonical_base_world_identity_pass=True,
        sampled_motion_clear=True,sampled_motion_count=26,
        physical_assembly_qualified=False,production_release=False,
        scope='Digital source, selected content and archive audit only. Not a printing, assembly, full-motion, harness, electrical, load or production test.')
    (c.OUT/'assembly07-audit.json').write_text(json.dumps(report,indent=2)+'\n');print('ISSUE07_PASS',541,41,6,494,';41+3drawing pages;36mount axes;26motion samples',flush=True)

if __name__=='__main__':main()
