# SPDX-License-Identifier: CC-BY-NC-4.0
"""Synthetic parser checks only. Never stored as physical qualification."""
import copy,tempfile,unittest
from pathlib import Path
from datetime import date
from qualification import acceptable,evaluate,sha,unmeasured
class EvidenceGate(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.folder=Path(self.tmp.name)
        f=self.folder/'SYNTHETIC.txt';f.write_text('Synthetic unit-test evidence; not hardware measurements')
        self.plan={'tests':[{'id':'X','module':'test','metrics':{'current':{'min':1}},'requires_configuration':['continuous_current_A']}],'definition_gates':[]}
        self.record={'serial_number':'SYNTHETIC','configuration_fingerprint':'same','configuration':{'continuous_current_A':1},'tests':{'X':{
            'metrics':{'current':1},'operator':'SYNTHETIC','reviewed_by':'SYNTHETIC','date':date.today().isoformat(),
            'instruments':[{'id':'SYNTHETIC','calibrated_on':'2020-01-01','calibration_valid_until':'2099-01-01'}],
            'evidence':[{'path':f.name,'sha256':sha(f)}]}}}
    def tearDown(self):self.tmp.cleanup()
    def test_numeric_rejects_bool_null_nan(self):
        for x in (True,None,float('nan')):self.assertFalse(acceptable(x,{'min':0}))
    def test_template_refresh_rejects_measurements(self):
        self.assertTrue(unmeasured({}))
        self.assertFalse(unmeasured(self.record))
        self.assertFalse(unmeasured({"tests":{"X":{"metrics":{"value":0}}}}))
    def test_unmeasured_does_not_pass(self):self.assertFalse(evaluate(self.plan,{},'same',self.folder)['qualification_complete'])
    def test_stale_definition_does_not_pass(self):self.assertFalse(evaluate(self.plan,self.record,'changed',self.folder)['qualification_complete'])
    def test_tampered_evidence_does_not_pass(self):
        (self.folder/'SYNTHETIC.txt').write_text('changed')
        self.assertFalse(evaluate(self.plan,self.record,'same',self.folder)['qualification_complete'])
    def test_expired_calibration_does_not_pass(self):
        r=copy.deepcopy(self.record);r['tests']['X']['instruments'][0]['calibration_valid_until']='2020-01-02'
        self.assertFalse(evaluate(self.plan,r,'same',self.folder)['qualification_complete'])
    def test_definition_blocker_does_not_pass(self):
        p=copy.deepcopy(self.plan);p['definition_gates']=[{'id':'DEF','closed':False,'needed':'missing'}]
        self.assertFalse(evaluate(p,self.record,'same',self.folder)['qualification_complete'])
    def test_complete_record_never_auto_releases(self):
        result=evaluate(self.plan,self.record,'same',self.folder)
        self.assertTrue(result['qualification_complete']);self.assertFalse(result['production_released'])
if __name__=='__main__':unittest.main()
