# SPDX-License-Identifier: CC-BY-NC-4.0
"""Check that this fit issue contains current source data, never certify load."""
import hashlib,json,zipfile
import common as c

def main():
    c.base_context()
    paths=['root01/manifest.json','root01/review.json','skeleton01/manifest.json',
        'skeleton01/review.json','hardware01/manifest.json','hardware01/review.json',
        'covers02/manifest.json','covers02/review.json','covers02/review-hardware.json',
        'routing01/manifest.json','gravity.json','shoulder02.json',
        'manufacture01/print-audit.json','native-audit.json','base-independent-check.json']
    records={};checked=0
    for name in paths:
        path=c.OUT/name;d=json.loads(path.read_text());assert d['layout']==c.L,name
        records[name]=c.sha(path)
        for field in ['source_sha256','source_files','sources']:
            source=d.get(field,{})
            pairs=source.items() if isinstance(source,dict) else [(x['path'],x['sha256']) for x in source]
            for relative,digest in pairs:
                assert c.sha(c.ROOT/relative)==digest,(name,relative,'stale source')
                checked+=1
        if 'vendor_audit_sha256' in d:
            assert d['vendor_audit_sha256']==c.sha(c.OUT/'vendor-audit.json')
        if 'gravity_sha256' in d:
            assert d['gravity_sha256']==c.sha(c.OUT/'gravity.json')
        assert not d.get('production_release',False),name
    n=json.loads((c.OUT/'native-audit.json').read_text())
    assert c.sha(c.ROOT/n['native_path'])==n['native_sha256']
    for name,digest in n['images'].items():assert c.sha(c.OUT/(name+'.png'))==digest
    assert n['canonical_base_world_geometry_unchanged']
    archives=[]
    for relative in ['root01/A16-root-supported-fit.zip','manufacture01/A16-core-supported-fit.zip']:
        path=c.OUT/relative
        with zipfile.ZipFile(path) as z:
            assert z.testzip() is None
            lines=z.read('SHA256SUMS.txt').decode().splitlines()
            for line in lines:
                digest,name=line.split('  ',1)
                assert hashlib.sha256(z.read(name)).hexdigest()==digest,(relative,name)
            archives.append(dict(path=str(path.relative_to(c.ROOT)),sha256=c.sha(path),verified_members=len(lines)))
    report=dict(layout=c.L,report_sha256=records,checked_source_hashes=checked,
        archives=archives,digital_issue_current=True,
        scope='Current CAD/report/native/image provenance and archive integrity only. Not a manufacturing or hardware acceptance test.',
        physical_print_fit_qualified=False,connected_harness_qualified=False,
        continuous_motion_qualified=False,thermal_payload_qualified=False,production_release=False)
    (c.OUT/'issue-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print('DIGITAL_FIT_ISSUE',checked,'source hashes;2 archives; production remains false',flush=True)

if __name__=='__main__':main()
