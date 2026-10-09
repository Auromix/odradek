# SPDX-License-Identifier: CC-BY-NC-4.0
"""Version-bound measured evidence registry. Missing evidence never becomes PASS.

init writes an unmeasured template; evaluate rejects stale fingerprints,
missing metrics, uncalibrated instruments and missing evidence files.
No automatic test here measures or approves physical hardware.
"""
import argparse,json,hashlib,math
from pathlib import Path
from datetime import date
HERE=Path(__file__).resolve().parent;OUT=HERE/'build/qualification';OUT.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def inputs():
    paths=[HERE/'interface-contract.json',HERE/'validation-plan.json',HERE/'build/exterior/manifest.json',HERE/'build/standalone-test/fixture-manifest.json',HERE/'manufacturing.md',HERE/'build/B06-manufacturing-bom.csv',HERE/'build/B06-first-article-traveler.csv',HERE/'build/manufacturing-definition.json']
    paths+=sorted((HERE/'build/exterior/print-parts').glob('*.stl'))
    paths+=sorted((HERE/'build/load-frame/step').glob('B06-*.step'))
    paths+=sorted((HERE/'build/standalone-test/step').glob('*.step'))
    io=HERE.parent/'electronics/base-io-b05';light=HERE.parent/'electronics/base-light-b06'
    paths+=[io/'base-io-b05/base-io-b05.eprj3',io/'local5v/package-envelopes.json',io/'base-io-b05/sch/base-rear-interface01/base-rear-interface01.esch2',io/'base-io-b05/pcb/base-rear-interface01.epcb2',io/'base-io-b05/pcb/PCB1.epcb2',io/'base-io-b05/sch/Schematic1/P1.esch2',light/'pin-nets.json']
    paths+=sorted((io/'manufacturing/b06-io-local5v').glob('*'))+sorted((light/'manufacturing').glob('*'))
    return {str(p.relative_to(HERE.parent)):sha(p) for p in paths if p.is_file()}
def acceptable(v,rule):
    if 'equals' in rule:return type(v)==type(rule['equals']) and v==rule['equals']
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):return False
    return ('min' not in rule or v>=rule['min']) and ('max' not in rule or v<=rule['max'])
def evaluate(plan,record,fp,record_dir):
    issues=[];results=[]
    if record.get('configuration_fingerprint')!=fp:issues.append('Missing/stale hardware definition fingerprint')
    if not record.get('serial_number'):issues.append('Missing base serial number')
    measured=record.get('tests',{})
    for t in plan['tests']:
        r=measured.get(t['id'],{});errors=[]
        for k,rule in t['metrics'].items():
            if not acceptable(r.get('metrics',{}).get(k),rule):errors.append('Missing/failing metric '+k)
        for k in t.get('requires_configuration',[]):
            v=record.get('configuration',{}).get(k)
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 or (v==0 and k not in ('PoC_V','PoC_A')):errors.append('Undefined configuration '+k)
        if not r.get('operator') or not r.get('reviewed_by'):errors.append('Operator/reviewer missing')
        try:
            testdate=date.fromisoformat(r['date'])
            if testdate>date.today():errors.append('Future test date')
        except (KeyError,TypeError,ValueError):testdate=None;errors.append('Test date missing/invalid')
        if not r.get('instruments'):errors.append('Instrument/calibration record missing')
        for instrument in r.get('instruments',[]):
            try:
                calibrated=date.fromisoformat(instrument['calibrated_on']);expires=date.fromisoformat(instrument['calibration_valid_until'])
                if not instrument.get('id') or testdate is None or not calibrated<=testdate<=expires:errors.append('Instrument calibration invalid')
            except (KeyError,TypeError,ValueError):errors.append('Instrument calibration invalid')
        if not r.get('evidence'):errors.append('Measured evidence missing')
        for e in r.get('evidence',[]):
            p=(record_dir/e.get('path','')).resolve()
            if not p.is_file() or e.get('sha256')!=sha(p):errors.append('Evidence absent/stale: '+e.get('path',''))
        results.append({'id':t['id'],'module':t['module'],'arm_required':False,'status':'PASS' if not errors else 'NOT_QUALIFIED','reasons':errors})
    for g in plan['definition_gates']:
        if not g['closed']:issues.append(g['id']+': '+g['needed'])
    passed=not issues and all(r['status']=='PASS' for r in results)
    return {'schema':'odradek.base.qualification.v1','qualification_complete':passed,'production_released':False,
            'status':'REQUIRES_SIGNED_RELEASE_REVIEW' if passed else 'BLOCKED',
            'arm_required':False,'definition_issues':issues,'tests':results,
            'limits':['Evidence/file consistency and numeric criteria only; no proof of record authenticity or independent certification','Even all PASS requires accountable release review; this script does not authorize manufacture or operation']}
def unmeasured(record):
    return (not record.get('serial_number') and all(v is None for v in record.get('configuration',{}).values())
        and all(not t.get('date') and not t.get('operator') and not t.get('reviewed_by')
            and not t.get('instruments') and not t.get('evidence')
            and all(v is None for v in t.get('metrics',{}).values()) for t in record.get('tests',{}).values()))
def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['init','refresh-unmeasured','evaluate']);p.add_argument('--record',type=Path,default=OUT/'unmeasured-template.json');a=p.parse_args()
    plan=json.loads((HERE/'validation-plan.json').read_text());files=inputs()
    fp=hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    (OUT/'definition-fingerprint.json').write_text(json.dumps({'fingerprint':fp,'files':files},indent=2)+'\n')
    if a.mode in ('init','refresh-unmeasured'):
        if a.record.exists():
            if a.mode=='init' or not unmeasured(json.loads(a.record.read_text())):raise SystemExit('Refusing to overwrite an existing/nonempty test record')
        record={'serial_number':None,'configuration_fingerprint':fp,'configuration':plan['configuration'],
                'tests':{t['id']:{'date':None,'operator':None,'reviewed_by':None,'metrics':{k:None for k in t['metrics']},'instruments':[],'evidence':[]} for t in plan['tests']}}
        a.record.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n');print('UNMEASURED_TEMPLATE',a.record)
    else:
        record=json.loads(a.record.read_text());report=evaluate(plan,record,fp,a.record.parent)
        report.update(configuration_fingerprint=fp,record_sha256=sha(a.record),validation_plan_sha256=sha(HERE/'validation-plan.json'))
        (OUT/'qualification-status.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print('PRODUCTION_RELEASE',report['production_released'],'PHYSICAL_PASS',sum(t['status']=='PASS' for t in report['tests']),'/'+str(len(report['tests'])))
if __name__=='__main__':main()
