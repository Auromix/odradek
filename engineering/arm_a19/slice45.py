# SPDX-License-Identifier: CC-BY-NC-4.0
"""Run a named slicer reference profile; outputs are private, not printer release G-code."""
from pathlib import Path
import json,hashlib,subprocess,re,csv,time,concurrent.futures
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];WORK=ROOT/'work/arm-a19/slice45';PACK=ROOT/'manufacturing/candidates/arm-body-a19-integrated-fit';RUNTIME=ROOT.parents[1]/'work/r4-runtime'
EXE=RUNTIME/'OrcaSlicer.app/Contents/MacOS/OrcaSlicer';RES=EXE.parents[1]/'Resources/profiles/Prusa'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def profiles():
 idx={json.loads(p.read_text()).get('name',p.stem):p for p in RES.rglob('*.json')};sources={}
 def load(name):
  p=idx[name];sources[str(p.relative_to(RES))]=sha(p);d=json.loads(p.read_text());r=load(d['inherits']) if d.get('inherits') else {};r.update(d);r.pop('inherits',None);return r
 WORK.mkdir(parents=True,exist_ok=True);out=WORK/'profiles';out.mkdir(exist_ok=True)
 changes={'layer_height':'0.2','wall_loops':'4','sparse_infill_density':'25%','sparse_infill_pattern':'gyroid','enable_support':'1','support_type':'normal(auto)','support_on_build_plate_only':'0','brim_width':'5','brim_type':'outer_only'}
 for kind,name in [('machine','Prusa MK4 0.4 nozzle'),('process','0.20mm Standard @MK4'),('filament','Prusa Generic PETG @MK4')]:
  d=load(name)
  if kind=='process':d.update(changes)
  (out/(kind+'.json')).write_text(json.dumps(d,indent=2)+'\n')
 return dict(sources=sources,process_overrides=changes,flattened_private_profiles_sha256={p.name:sha(p)for p in out.glob('*.json')})
def one(item):
 group,p=item;out=WORK/'parts'/p.stem;out.mkdir(parents=True,exist_ok=True);log=out/'slice.log';gc=out/'plate_1.gcode'
 args=[str(EXE),'--load-settings',str(WORK/'profiles/machine.json')+';'+str(WORK/'profiles/process.json'),'--load-filaments',str(WORK/'profiles/filament.json'),'--orient','0','--arrange','1','--slice','0','--outputdir',str(out),str(p)]
 if gc.exists():gc.unlink()
 start=time.time()
 with log.open('w')as fp:r=subprocess.run(args,stdout=fp,stderr=subprocess.STDOUT,timeout=900)
 msg=log.read_text();text=gc.read_text()if gc.exists()else '';exe=text.split('; EXECUTABLE_BLOCK_START')[-1].split('; EXECUTABLE_BLOCK_END')[0]
 stats={}
 for key,pattern in [('layers',r'; total layer number: (\d+)'),('filament_g',r'; total filament used \[g\] = ([0-9.]+)'),('print_time',r'; estimated printing time \(normal mode\) = (.+)'),('first_layer_time',r'; estimated first layer printing time \(normal mode\) = (.+)')]:
  m=re.search(pattern,text);stats[key]=m.group(1)if m else None
 types=sorted(set(re.findall(r';TYPE:(.+)',exe)));haspaths='Outer wall'in types and bool(re.search(r'^G[123].*E[0-9]',exe,re.M))
 record=dict(group=group,id=p.stem,source_stl_path=str(p.relative_to(ROOT)),source_stl_sha256=sha(p),exit_code=r.returncode,nonempty_model_extrusion=haspaths,stats=stats,extrusion_types=types,support_paths_generated=any('Support'in t for t in types),log_sha256=sha(log),private_gcode_sha256=sha(gc)if gc.exists()else None,warnings=[line for line in msg.splitlines()if re.search(r'warning|error|fail',line,re.I)],runtime_seconds=round(time.time()-start,2),slice_completed=r.returncode==0 and haspaths and stats['layers']is not None)
 (out/'audit.json').write_text(json.dumps(record,indent=2)+'\n');print('SLICE45',p.stem,record['slice_completed'],stats,record['warnings'],flush=True);return record

def main():
 profile=profiles();items=[(group,p)for group,folder in [('body','print-bed'),('motor-tube-coupons','calibration-coupons'),('bearing-gauges','j7-bearing-calibration')]for p in sorted((PACK/folder).glob('*.stl'))];assert len(items)==54
 with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:records=list(pool.map(one,items))
 report=dict(revision='A19-REFERENCE-SLICING45',source_assembly_sha256=sha(HERE/'build/assembly25/manifest.json'),source_script_sha256=sha(Path(__file__)),slicer='OrcaSlicer2.4.2',slicer_binary_sha256=sha(EXE),reference_printer='Prusa MK4 0.4 nozzle,250x210x220 mm; not a selected user printer',reference_filament='Prusa Generic PETG @MK4',profiles=profile,orientation='Preserve supplied bed STL orientation; arrange translates in XY, no automatic 3D orientation',records=records,all_slices_completed=all(r['slice_completed']for r in records),physical_print_completed=False,printer_selected=False,production_release=False,scope='Single-part reference-profile slicing and nonempty model extrusion, no physical supports-removal/adhesion/fit/strength verification. G-code retained privately, never offered as ready for unspecified printer. Support paths may contact bores and require removal/recalibration.')
 (HERE/'build/assembly25/slice45.json').write_text(json.dumps(report,indent=2)+'\n');(PACK/'slice45.json').write_text(json.dumps(report,indent=2)+'\n')
 with (PACK/'slice45-summary.csv').open('w')as fp:
  wr=csv.writer(fp);wr.writerow(['group','id','slice_completed','layers','estimated_filament_g','estimated_print_time','support_paths_generated','warnings'])
  for r in records:wr.writerow([r['group'],r['id'],r['slice_completed'],r['stats']['layers'],r['stats']['filament_g'],r['stats']['print_time'],r['support_paths_generated'],' | '.join(r['warnings'])])
 print('SLICE45_DONE',len(records),report['all_slices_completed'],flush=True)
if __name__=='__main__':main()
