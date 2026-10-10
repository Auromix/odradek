# SPDX-License-Identifier: CC-BY-NC-4.0
"""Check actual reference extrusion XY bounds, excluding printer start/end purges."""
from pathlib import Path
import json,hashlib,sys
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PACK=ROOT/'manufacturing/candidates/arm-body-a19-integrated-fit';WORK=ROOT/'work/arm-a19/slice45';sys.path.insert(0,str(HERE));from slice_layers47 import read
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 source=HERE/'build/assembly25/slice45.json';d=json.loads(source.read_text());records=[]
 for r in d['records']:
  p=WORK/'parts'/r['id']/'plate_1.gcode';assert sha(p)==r['private_gcode_sha256'];layers,arcs=read(p);points=np.array([q for l in layers.values()for s in l for q in s[:2]]);assert len(points)>0 and arcs==0
  low=points.min(axis=0)-.25;high=points.max(axis=0)+.25;fits=bool(np.all(low>=0)and np.all(high<=[250,210])and max(layers)<=220)
  assert len(layers)==int(r['stats']['layers']),(r['id'],len(layers),r['stats']['layers'])
  records.append(dict(id=r['id'],gcode_sha256=sha(p),parsed_extrusion_layers=len(layers),XY_bounds_with_0p25mm_line_radius_mm=[low.tolist(),high.tolist()],max_layer_z_mm=max(layers),reference_extrusion_inside_bed=fits));print('BED48',r['id'],fits,flush=True)
 report=dict(source_slice45_sha256=sha(source),source_checker_sha256=sha(Path(__file__)),source_parser_sha256=sha(HERE/'slice_layers47.py'),records=records,all_reference_extrusions_inside_bed=all(r['reference_extrusion_inside_bed']for r in records),production_release=False,scope='Actual linear noncustom model/support/brim extrusion segments on reference250x210 bed,0.25mm line radius margin; all54layer counts match slicer markers,0arc omission. Does not assess hardware purge/prime regions, actual printer/firmware, adherence, support removal or physical print.')
 (HERE/'build/assembly25/slice-bed48.json').write_text(json.dumps(report,indent=2)+'\n');(PACK/'slice-bed48.json').write_text(json.dumps(report,indent=2)+'\n');print('BED48_DONE',len(records),report['all_reference_extrusions_inside_bed'],flush=True)
if __name__=='__main__':main()
