# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Read frozen CAD and screen discrete complete-arm poses; no trajectory approval.

Original link/base CAD and HEAD03 are read from exported STEP, never rebuilt.
Supply private OEM paths as repeated --model ID=PATH; raw OEM CAD is not exported.
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import cadquery as cq
import numpy as np
from scipy.spatial.transform import Rotation
from OCP.XCAFDoc import XCAFDoc_DocumentTool,XCAFDoc_ShapeTool
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDF import TDF_LabelSequence
from OCP.TDataStd import TDataStd_Name
from OCP.IFSelect import IFSelect_RetDone
from build_layout import frame,moved
from mount_interface_study import load_vendor
from studies.link_interface_tools import check,cache
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/integrated-collision-study'
THRESHOLD=1e-4

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def box(s):
 b=s.BoundingBox();return np.array([[b.xmin,b.ymin,b.zmin],[b.xmax,b.ymax,b.zmax]])

def named_step(path):
 """Flat XCAF assembly exported by this project; preserve exact BREP names."""
 doc=TDocStd_Document(TCollection_ExtendedString('BinXCAF'));reader=STEPCAFControl_Reader()
 assert reader.ReadFile(str(path))==IFSelect_RetDone and reader.Transfer(doc)
 tool=XCAFDoc_DocumentTool.ShapeTool_s(doc.Main());roots=TDF_LabelSequence();tool.GetFreeShapes(roots);assert roots.Length()==1
 labels=TDF_LabelSequence();assert XCAFDoc_ShapeTool.GetComponents_s(roots.Value(1),labels)
 out={}
 for i in range(1,labels.Length()+1):
  label=labels.Value(i);attr=TDataStd_Name();assert label.FindAttribute(TDataStd_Name.GetID_s(),attr)
  name=attr.Get().ToExtString();assert name not in out
  shape=cq.Shape.cast(XCAFDoc_ShapeTool.GetShape_s(label));assert shape.isValid() and len(shape.Solids())==1
  out[name]=shape
 return out

def transform_prefixes(p,angles):
 """Independent millimetre product of fixed-home revolute screw transforms."""
 T=np.eye(4);out=[T.copy()]
 for j,a in zip(p['joints'],angles):
  R=Rotation.from_rotvec(np.array(j['axis'])*np.deg2rad(a)).as_matrix();q=np.array(j['origin_mm']);local=np.eye(4);local[:3,:3]=R;local[:3,3]=q-R@q;T=T@local;out.append(T.copy())
 return out

def load_structure(paths):
 ppath=ROOT/'engineering/parameters/r4-layout.json';p=json.loads(ppath.read_text());hashes={str(ppath.relative_to(ROOT)):sha(ppath)};rows={};sources={}
 def source(path):hashes[str(path.relative_to(ROOT))]=sha(path)
 for link in ['12','23','34','45','56','67']:
  folder=ROOT/f'engineering/generated/link{link}-study';placement=folder/'part-placements.json';ev=folder/'evidence.json';source(placement);source(ev);e=json.loads(ev.read_text());assert not e['errors']
  for name,r in json.loads(placement.read_text())['instances'].items():
   path=folder/(r['part_id']+'.step');source(path);assert sha(path)==e['export_checks'][r['part_id']]['sha256'][path.name]
   s=cq.importers.importStep(str(path)).val();T=np.array(r['T_world_from_part_mm']);s=moved(s,T);assert s.isValid() and len(s.Solids())==1
   rows['L'+link+'_'+name]={'shape':s,'pre':int(link[0]),'group':'L'+link,'representation':'original nominal metal BREP','source':str(path.relative_to(ROOT))}
 assert len(rows)==24
 path=ROOT/'engineering/generated/base-study/ODR-BASE-ORIGINAL-ASSEMBLY.step';source(path);base=named_step(path);assert len(base)==8
 for n,s in base.items():rows['BASE_'+n]={'shape':s,'pre':0,'group':'BASE','representation':'original nominal metal BREP','source':str(path.relative_to(ROOT))}
 path=ROOT/'docs/engineering/sources/rh-interface-extraction.json';source(path);models={m['id']:m for m in json.loads(path.read_text())['models']}
 vendor={}
 for key,path in paths.items():
  vendor[key]=load_vendor(path,models[key]);sources[key]={'filename':path.name,'sha256':sha(path),'solid_count':len(vendor[key].Solids()),'local_only':True}
 for i,j in enumerate(p['joints']):
  rows[j['id']]={'shape':moved(vendor[j['model']],frame(j['origin_mm'],j['axis'])),'pre':i,'group':j['id'],'representation':'actual OEM BREP assembly; internal solids kept','source':'private OEM '+j['model']}
 return p,rows,hashes,sources

def load_head(label):
 folder=ROOT/'engineering/generated/head-integrated-03';manifest=folder/('blender-parts-manifest'+('' if label=='open' else '-closed')+'.json');path=folder/('HEAD-INTEGRATED03-'+label+'.step');report=folder/'export-mass.json';data=json.loads(manifest.read_text());export=json.loads(report.read_text());assert sha(path)==export['states'][label]['STEP']['sha256']
 shapes=named_step(path);assert len(shapes)==697 and set(shapes)=={p['id'] for p in data['parts']};rows={};errors=[];T=np.eye(4);T[:3,3]=data['head_face_world_mm']
 for p in data['parts']:
  s=shapes[p['id']];volume=abs(s.Volume()-p['shape_volume_mm3']);bbdelta=float(abs(box(s)-np.array(p['bbox_head_mm'])).max());assert volume<1e-3 and bbdelta<.01,(p['id'],volume,bbdelta)
  rows['HEAD_'+p['id']]={'shape':moved(s,T),'pre':7,'group':p['group'],'representation':p['representation'],'material':p['material'],'source':str(path.relative_to(ROOT))}
  errors.append({'id':p['id'],'volume_error_mm3':volume,'bbox_max_error_mm':bbdelta})
 return rows,{str(x.relative_to(ROOT)):sha(x) for x in [manifest,path,report]},errors

def expected_interface(a,b):
 """Tag expected mates; do not suppress any positive-volume intersection."""
 for x,y in [(a,b),(b,a)]:
  if x.startswith('L') and y.startswith('J'):
   l=x[1:3];n=int(y[1:])
   if n in [int(l[0]),int(l[1])]:return 'Candidate link-to-own-adjacent joint interface; contact expected only at specified mounting faces'
  if x.startswith('BASE_') and y=='J1':return 'Anchored base-to-J1 fixed mounting interface'
  if x=='HEAD_J7_existing_adapter' and y=='J7':return 'Head adapter-to-J7 output interface'
  if x.split('_')[0]==y.split('_')[0] and x.startswith(('L','BASE')):return 'Same original structural assembly; nominal mating surfaces may touch'
 return None

def pose_screen(p,structure,head,angles):
 pre=transform_prefixes(p,angles);allrows={**structure,**head};posed={n:{**r,'shape':moved(r['shape'],pre[r['pre']])} for n,r in allrows.items()};boxes={n:box(r['shape']) for n,r in posed.items()};cached={};events=[];contacts=[];boolean_count=0;total=0;pruned=0;tested=[]
 pairs=list(itertools.combinations(structure,2))+[(a,b) for a in head for b in structure]
 for a,b in pairs:
  total+=1;A,B=boxes[a],boxes[b];overlap=np.maximum(0,np.minimum(A[1],B[1])-np.maximum(A[0],B[0]));upper=float(np.prod(overlap));tag=expected_interface(a,b)
  if upper<=THRESHOLD:
   pruned+=1
   if tag and np.max(np.maximum(A[0]-B[1],B[0]-A[1]))<1e-6:contacts.append({'a':a,'b':b,'ownership':tag,'status':'candidate mating-plane pair; box tangency only, face area retained in original interface studies'})
   continue
  for n in [a,b]:
   if n not in cached:cached[n]=cache(posed[n]['shape'])
  q=check(cached[a],cached[b]);boolean_count+=q['boolean_count'];tested.append({'a':a,'b':b,'solid_pairs':q['pair_count'],'booleans':q['boolean_count'],'intersection_mm3':q['solid_pair_intersection_sum_mm3']})
  if q['events']:
   events.append({'a':a,'b':b,'a_group':posed[a]['group'],'b_group':posed[b]['group'],'a_representation':posed[a]['representation'],'b_representation':posed[b]['representation'],'expected_interface':tag,**q})
  elif tag:contacts.append({'a':a,'b':b,'ownership':tag,'status':'positive volume absent; exact face contacts are checked in source studies'})
 return {'angles_deg':angles,'part_pair_count':total,'AABB_intersection_volume_pruned':pruned,'narrowphase_part_pairs':len(tested),'solid_boolean_count':boolean_count,'events':events,'contacts_ownership':contacts,'narrowphase_pairs':tested,'scope':'All structural inter-part pairs and every head part against structure. No head-head or OEM internal-internal revalidation; head internal fit evidence is separate. Positive events at expected interfaces are NEVER suppressed.'}

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--model',action='append',required=True,metavar='ID=PATH');ap.add_argument('--out',type=Path,default=OUT);args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=True)
 paths={n:Path(q) for n,q in (s.split('=',1) for s in args.model)};p,structure,hashes,vendor=load_structure(paths)
 result={'revision':'INTEGRATED-COLLISION01','source_sha256':hashes,'vendor_sources':vendor,'method':'Exact exported BREP per-solid Boolean common, AABB safe rejection only; reporting threshold1e-4mm3','structure_part_count':len(structure),'structure':{n:{k:v for k,v in r.items() if k!='shape'}|{'bbox_home_mm':box(r['shape']).tolist(),'solids':len(r['shape'].Solids())} for n,r in structure.items()},'poses':{},'head_import_qa':{},'manufacturing_release':False,'trajectory_qualified':False}
 for label in ['open','closed']:
  print('Loading head',label,flush=True);head,h,qa=load_head(label);result['source_sha256'].update(h);result['head_import_qa'][label]=qa
  for name,q in p['poses_deg'].items():
   print('Pose',name,label,flush=True);r=pose_screen(p,structure,head,q);result['poses'][name+'_'+label]=r;print('=>',len(r['events']),'event pairs',r['solid_boolean_count'],'booleans',flush=True)
   (args.out/'poses.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 result['generator_sha256']=sha(Path(__file__));(args.out/'poses.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':main()
