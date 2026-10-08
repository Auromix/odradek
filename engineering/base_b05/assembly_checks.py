# SPDX-License-Identifier: CC-BY-NC-4.0
"""Check nominal fastening algebra; deliberately not a collision/strength test."""
import json, hashlib
from pathlib import Path
OUT=Path(__file__).resolve().parent/'build'/'exterior'
contract=json.loads((OUT/'mounting-contract.json').read_text())
mounts=contract['mounts']+contract['deck_fixings']
records=[]
for i,m in enumerate(mounts,1):
    nut_top=m.get('nut_top',m['seat_top']-2.6);nut_bottom=nut_top-2.4
    lo=m['head_floor']+1.65 if m.get('upward') else m['head_floor']-m['length']
    hi=lo+m['length'] if m.get('upward') else m['head_floor']
    engagement=max(0,min(hi,nut_top)-max(lo,nut_bottom))
    records.append(dict(index=i,owner=m['owner'],position_xy_mm=[m['x'],m['y']],nominal_nut_engagement_mm=engagement,full_nut_height_covered=engagement>=2.4-1e-6))
nominal=dict(screw_hole_diameter_clearance_mm=3.4-3.,button_well_diameter_clearance_mm=6.6-5.7,nut_flats_clearance_mm=5.8-5.5,nut_height_clearance_mm=2.8-2.4,pin_socket_diameter_clearance_mm=3.1-2.8,pin_depth_clearance_mm=2.3-2.,collar_post_hole_diameter_clearance_mm=9.4-9.)
result=dict(schema='odradek.exterior-fastening-check.v1',revision='B05-EXTERIOR-SHAPE-06',source_sha256=hashlib.sha256((OUT/'mounting-contract.json').read_bytes()).hexdigest(),scope='Nominal hardware dimension and engagement arithmetic only',fastener_count=len(records),mounts=records,nominal_clearances=nominal,nominal_hardware_arithmetic_pass=all(x['full_nut_height_covered'] for x in records) and all(x>0 for x in nominal.values()),complete_collision_checked=False,physical_assembly_checked=False,load_checked=False,pcb_component_integration_checked=False,notes=['Thread geometry is simplified; these dimensions do not establish preload or stripping strength','Printed hole compensation, underside contact surfaces, nut insertion and tool paths require actual unpowered fit trials'])
(OUT/'assembly-checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('NOMINAL_HARDWARE_ARITHMETIC',result['nominal_hardware_arithmetic_pass'],len(records))
