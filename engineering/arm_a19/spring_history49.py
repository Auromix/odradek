# SPDX-License-Identifier: CC-BY-NC-4.0
"""Keep failed prior spring screens replayable after current fastener mass update."""
from pathlib import Path
import json,hashlib
HERE=Path(__file__).resolve().parent;OUT=HERE/'build/assembly25';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 records=[]
 for name in ['assist33.json','gas39.json']:
  p=OUT/name;d=json.loads(p.read_text());assert d['source_assembly_sha256']==sha(OUT/'baselines/assembly25-v25.json');assert d['source_interval_csv_sha256']==sha(OUT/'baselines/J2-ideal-passive-limit27-v25.csv')
  records.append(dict(report=name,sha256=sha(p),historical_assembly='baselines/assembly25-v25.json',historical_interval_csv='baselines/J2-ideal-passive-limit27-v25.csv',historical_load='baselines/load27-v25.json',current_result=False))
 report=dict(source_current_assembly_sha256=sha(OUT/'manifest.json'),source_checker_sha256=sha(Path(__file__)),records=records,scope='Failed spring screens remain evidence for pre-hardware43 mass inputs only. New fastener mass does not silently relabel old results as current. No spring selected or purchased; production shoulder unresolved.')
 (OUT/'spring-history49.json').write_text(json.dumps(report,indent=2)+'\n');print('SPRING49',len(records))
if __name__=='__main__':main()
