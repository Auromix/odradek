# SPDX-License-Identifier: CC-BY-NC-4.0
"""Bind unchanged drawing and coupon sources to current assembly, retaining historical reports."""
from pathlib import Path
import json,hashlib,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=HERE/'build/assembly25';PACK=ROOT/'manufacturing/candidates/arm-body-a19-integrated-fit'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 d=json.loads((OUT/'manifest.json').read_text());index={p['id']:p for p in d['parts']};draw=PACK/'drawings/drawing-source-audit.json';data=json.loads(draw.read_text());pages=[]
 for p in data['pages']:
  row=index[p['id']];assert p['step_sha256']==row['step_sha256']==sha(ROOT/row['step_path']);assert p['frame']==row['frame'];pages.append(dict(id=p['id'],page=p['page'],current_source_step=row['step_path'],sha256=row['step_sha256']))
 assert len(pages)==47
 gau=PACK/'j7-bearing-calibration/manifest.json';g=json.loads(gau.read_text())
 for id,p in g['source_current_body_parts'].items():assert sha(ROOT/p['step'])==p['sha256']==index[id]['step_sha256']
 bridge=dict(revision='A19-UNCHANGED-DRAWING-SOURCE-BRIDGE46',source_assembly_sha256=sha(OUT/'manifest.json'),source_checker_sha256=sha(Path(__file__)),historical_drawing_audit_sha256=sha(draw),historical_assembly_sha256=data['source_assembly_sha256'],pdf_sha256=data['pdf_sha256'],all_47_part_STEP_and_frames_identical=True,pages=pages,bearing_gauge_manifest_sha256=sha(gau),bearing_gauge_current_source_parts_identical=True,production_release=False,scope='No regenerated drawings or altered historical audit. Hardware43 changes only screws/washers; all47 drawing parts and current J7 calibration-source STEP match byte for byte. Native hole table remains geometric, no screw bill/GD&T update implied.')
 assert bridge['pdf_sha256']==sha(PACK/'drawings/47-current-part-fit-drawings.pdf');(PACK/'drawings/current-source-bridge46.json').write_text(json.dumps(bridge,indent=2)+'\n')
 for folder in ['wrist-core19','wrist-shell21']:
  p=HERE/'build'/folder/'review20.json';old=json.loads(p.read_text());old['integrated_report']='engineering/arm_a19/build/assembly25/review20.json';old['integrated_report_sha256']=sha(OUT/'review20.json');old['scope']='Current134 finite changed-pair evidence, unchanged-pair exact baseline inheritance plus hardware43 incremental check. No full-workspace, continuous, harness or physical qualification.';p.write_text(json.dumps(old,indent=2)+'\n')
 print('BRIDGE46',len(pages))
if __name__=='__main__':main()
