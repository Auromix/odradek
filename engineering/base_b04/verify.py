# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Assembly checks, not a substitute for physical proof load or tolerance study."""
import itertools,json,hashlib
from pathlib import Path
from model import make,box,cyl,P,HERE
from build import overlap,components,cables
OUT=HERE/'build'
def main():
    report={'revision':P['revision'],'limitations':['Nominal rigid geometry; no FEA or physical load test.','Sliding paths are sampled, not continuous collision proof.','Fastener thread engagement is intentional; only head/washer free geometry is checked.','Controller is an allocation gauge. Harness plugs, wire compliance and human hands need prototype verification.'], 'cases':[],'failures':[]}
    for thickness in P['desk_thicknesses']:
        ps=make(thickness,environment=True)+components()+cables(); by={p.id:p for p in ps};fail=[];pair_count=0
        rigid=[p for p in ps if p.category not in ['fastener','hardware']]
        for a,b in itertools.combinations(rigid,2):
            if a.category=='component' and b.category=='component':continue
            pair_count+=1;v=overlap(a.shape,b.shape)
            if v>.02:fail.append({'kind':'rigid','a':a.id,'b':b.id,'volume':v})
        for a in [p for p in ps if hasattr(p,'free_shape')]:
            for b in ps:
                if b.category=='fastener':continue
                pair_count+=1;v=overlap(a.free_shape,b.shape)
                if v>.02:fail.append({'kind':'fastener_head_washer','a':a.id,'b':b.id,'volume':v})
        # Long AF6 tool, max shank D10. Handle remains below all structure.
        for x in [-85,85]:
            tool=cyl((x,55,-thickness-114.6),(0,0,-1),5,120)
            for p in ps:
                if p.id.startswith('HW-THRUST-SCREW'):continue
                v=overlap(tool,p.shape)
                if v>.02:fail.append({'kind':'clamp_tool_D10x120','x':x,'b':p.id,'volume':v})
        report['cases'].append({'table_mm':thickness,'tested_pairs':pair_count,'interferences':fail,
          'nominal_foot_bridge_gap_mm':90-thickness-23,'thrust_thread_engagement_mm':22,
          'required_tool':'AF6 long driver, shank <=D10, 120mm unobstructed axial path; handle below cradle'})
        report['failures'].extend(fail)
        print('table',thickness,'failures',len(fail),flush=True)
    ps=make(30,environment=True)+components()+cables();by={p.id:p for p in ps}
    paths=[]
    def sweep(name,moving,fixed,axis,steps):
        events=[];min_gap=1e9
        for s in steps:
            delta=tuple(v*s for v in axis)
            for a in moving:
                sh=a.shape.translate(delta)
                for b in fixed:
                    v=overlap(sh,b.shape)
                    if v>.02:events.append({'step_mm':s,'moving':a.id,'fixed':b.id,'volume':v})
        paths.append({'name':name,'axis':axis,'sample_positions_mm':steps,'interferences':events})
        report['failures'].extend(events)
    # Remove named screws first. Assembly order is an explicit precondition.
    for label in ['REAR','FRONT']:
        moving=[by['B04-301-COVER-'+label]]
        fixed=[p for p in ps if p not in moving and not p.id.startswith('HW-M3-COVER-TOP')]
        sweep('Lift '+label+' cover after removing its screws',moving,fixed,(0,0,1),[.2,1,3,6,10,20,40,80,120])
    moving=[by['ENV-CONTROLLER']]
    fixed=[p for p in ps if p not in moving and p.id!='B04-203-STOP-FRONT' and not (p.id.startswith('HW-M4-STOP') and p.id.endswith('-278')) and p.category!='routing']
    sweep('Controller extraction: remove front stop/strap and unplug all cables',moving,fixed,(0,1,0),[1,5,10,20,40,80,120,180,240])
    data=json.loads((HERE.parent/'electronics/base-b04/mechanical-interface.json').read_text())
    for c in data['connectors']:
        lo=[*c['mated_uv_box'][0],c['mated_z_mm'][0]];hi=[*c['mated_uv_box'][1],c['mated_z_mm'][1]]
        from model import Part
        sh=box(*[lo[i]+P['pcb_origin'][i] for i in range(3)],*[hi[i]-lo[i] for i in range(3)])
        moving=[Part('plug-'+c['ref'],sh,'FR4','reference')]
        fixed=[p for p in ps if not p.id.startswith('PCB-'+c['ref']) and p.id!='B04-301-COVER-REAR' and not p.id.startswith('HW-M3-COVER-TOP')]
        sweep(c['ref']+' plug removal with rear hood removed',moving,fixed,tuple(c['removal_vector']),[1,3,5,10,15,20,30] if c['ref']!='J3' else [1,3,5,10,15,20])
    report['sampled_paths']=paths
    report['inputs_sha256']={f:hashlib.sha256((HERE/f).read_bytes()).hexdigest() for f in ['model.py','parameters.json','build.py']}
    report['passed_nominal_geometry']=not report['failures']
    (OUT/'assembly-verification.json').write_text(json.dumps(report,indent=2))
    print('VERIFICATION',report['passed_nominal_geometry'],'events',len(report['failures']),flush=True)
    assert report['passed_nominal_geometry'],report['failures']
if __name__=='__main__':main()
