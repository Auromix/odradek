# SPDX-License-Identifier: CC-BY-NC-4.0
"""Electrical candidate arithmetic, separate from routing qualification."""
from pathlib import Path
import sys,json,math
HERE=Path(__file__).resolve().parent;OUT=HERE/'build/assembly25'
sys.path.insert(0,str(HERE));import wrist16 as w
c=w.c

def main():
 source=HERE.parents[1]/'work/arm-a19/HS-RG178-BU.pdf';lengths=[1.5,2.4,3.0];records=[]
 for length in lengths:
  records.append(dict(length_assumption_m=length,nominal_bare_cable_loss_dB={str(f):length*(1.414*math.sqrt(f)+.173*f)for f in [1.5,3]},nominal_cable_loop_DC_ohm=(742+53)*length/1000,cable_mass_two_channels_kg=2*.0084*length))
 report=dict(revision='A19-GMSL-CABLE-SCREEN41',source_assembly_sha256=c.sha(OUT/'manifest.json'),source_checker_sha256=c.sha(Path(__file__)),cable=dict(manufacturer='HUBER+SUHNER',part_number='22510043',identifier='RG_178_B/U',OD_mm=1.8,OD_tolerance_mm=.1,impedance_ohm=50,impedance_tolerance_ohm=2,frequency_max_GHz=3,static_radius_mm=10,repeated_radius_mm=18,dynamic_radius_original_text='<27mm, interpretation and life not verified',conductor_DC_ohm_km=742,shield_DC_ohm_km=53,web_extra_DC_value_conflicts_with_PDF=True),source_pdf_sha256=c.sha(source),source_pdf_date='2026-03-12',source_url='https://www.hubersuhner.com/Asset/eyJpZGVudGlmaWVyIjoxMTY0NDksInR5cGUiOiJhc3NldCJ9/5uPHdE9YtZiMGuxL/H%2BS_RG_178_BU_EN.PDF',channel_spec_url='https://www.analog.com/media/en/technical-documentation/user-guides/gmsl2-channel-specification-user-guide.pdf',module_cable_loss_limit_dB=dict(GMSL2_3Gbps_at_1_5GHz=15.5,GMSL2_6Gbps_at_3GHz=17),module_applied_band_max_GHz=dict(GMSL2_3Gbps=2,GMSL2_6Gbps=3.5),assumed_lengths=records,assembly_length_selected=False,actual_loss_measured=False,dynamic_life_verified=False,torsion_verified=False,connector_crimp_verified=False,PoC_current_selected=False,purchase_selected=False,production_release=False,scope='Nominal bare-cable arithmetic only, no connector/PCB/PoC/passive loss or impedance/return-loss/ripple/crosstalk measurement. Lengths are scenarios, not released cuts.3GHz cable catalogue does not qualify6Gbps full3.5GHz applied band.')
 (OUT/'wire41.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
