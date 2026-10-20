"""Presentation preservation fixtures: historical evidence is not a new build."""
from copy import deepcopy
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

import sync_di_revision as revision


class DIReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=revision.read(revision.ARCHIVE/'BEFORE.json')
        cls.old=revision.read(revision.ARCHIVE/'report-data.json')
        cls.current=revision.read(revision.ROOT/'report-data.json')
        cls.manifest=revision.read(revision.ROOT/'manifest.json')
        cls.html=(revision.CLIENT/'Performance and Setup.html').read_text(encoding='utf-8')

    def test_preserved_all_dataset_evidence_metadata_hashes(self):
        for key,value in revision.historical_fields(self.current).items():
            self.assertEqual(revision.value_hash(value),self.before['historical_fields'][key],key)
        self.assertEqual(self.current['datasets'],self.old['datasets'])
        self.assertEqual(self.current['evidence'],self.old['evidence'])
        self.assertEqual(len(self.current['evidence']),20)

    def test_public_embedded_data_is_current_cached_payload(self):
        public=revision.embedded_data(self.html)
        self.assertEqual(public,self.current)
        for key in ('datasets','evidence','bots','built'):
            self.assertEqual(public[key],self.old[key],key)

    def test_original_presentation_is_recoverably_archived(self):
        for name,sha in self.before['archived_files'].items():
            self.assertEqual(revision.digest(revision.ARCHIVE/name),sha,name)
        archived=revision.embedded_data((revision.ARCHIVE/'Performance and Setup.html').read_text(encoding='utf-8'))
        self.assertEqual(archived['datasets'],self.current['datasets'])

    def test_current_di_off_input_and_previous_di_on_are_distinct(self):
        current=self.current['ea_details']['entries'][revision.SLUG]
        old=self.old['ea_details']['entries'][revision.SLUG]
        self.assertEqual(current['inputs']['InpRequireDIAgreement'],'false')
        self.assertEqual(old['inputs']['InpRequireDIAgreement'],'true')
        self.assertEqual(self.current['current_package']['nasdaq_di_default'],'OFF')
        self.assertEqual(self.current['benchmarkMetadata']['nasdaq_di_agreement'],'ON')
        self.assertFalse(self.current['benchmarkMetadata']['current_binary_backtest'])

    def test_website_reference_not_rewritten_as_di_off(self):
        for slug,current in self.current['ea_details']['entries'].items():
            for key,value in self.old['ea_details']['entries'][slug].items():
                if key!='inputs':self.assertEqual(current[key],value,(slug,key))
        d=self.current['ea_details']['entries'][revision.SLUG]
        self.assertIn('DI',d['description'])
        self.assertIn('DI ON',self.current['current_package']['ea_details'][revision.SLUG]['historical_rule'])

    def test_current_fingerprints_match_public_binaries(self):
        current={b['slug']:b for b in self.current['current_package']['bots']}
        for entry in self.manifest['entries']:
            self.assertEqual(current[entry['slug']]['ex5_sha256'],entry['ex5_sha256'])
            self.assertEqual(revision.digest(revision.CLIENT/entry['expert']),entry['ex5_sha256'])
        self.assertNotEqual(current[revision.SLUG]['ex5_sha256'],
            next(b['ex5_sha256'] for b in self.old['bots'] if b['slug']==revision.SLUG))

    def test_historical_native_sets_prove_di_on(self):
        for mode in ('fixed','balance'):
            for period in ('3m','6m'):
                tag=f'nw-USTEC-{revision.SLUG}-{mode}-{period}'
                text=(revision.ROOT/'tests-native'/tag/(tag+'.set')).read_text(encoding='utf-8-sig')
                self.assertTrue(re.search(r'^InpRequireDIAgreement=true\s*$',text,re.M),tag)

    def test_prominent_no_current_build_performance_claim(self):
        for phrase in ('20 HISTORICAL PRIOR-BUILD BENCHMARKS','Current delivery: Nasdaq 5M DI agreement is OFF',
            'not</b> backtests of the new DI-OFF','Current packaged settings','HISTORICAL PASS',
            'Current delivered client package','Cached website rules · not current client overrides',
            'HISTORICAL LINEAR ESTIMATE — NOT CURRENT-BUILD BACKTEST','Current delivered sizing can exceed selected risk'):
            self.assertTrue(phrase in self.html,phrase)
        self.assertNotIn('Client version: DI14 / EMA12',self.html)
        self.assertIn('The old historical benchmarks had DI ON',self.html)

    def test_preservation_transform_is_idempotent(self):
        transformed=revision.transform(self.current,self.manifest,revision.digest(revision.ROOT/'manifest.json'))
        self.assertEqual(transformed,self.current)
        template=(revision.ROOT/'report.template.html').read_text(encoding='utf-8')
        self.assertEqual(revision.render_cached(transformed,template),self.html)

    def test_rejects_unrequested_licence_or_di_change(self):
        for field in ('licence','di'):
            manifest=deepcopy(self.manifest)
            if field=='licence':manifest['licence']['expires_utc']='2099-01-01'
            else:next(r for r in manifest['entries'] if r['slug']==revision.SLUG)['inputs']['InpRequireDIAgreement']='true'
            with self.assertRaises(AssertionError):revision.transform(self.current,manifest,'x')

    def test_public_delivery_still_has_only_seven_files(self):
        self.assertEqual(len(list(revision.CLIENT.iterdir())),7)
        self.assertEqual(len(list(revision.CLIENT.glob('*.ex5'))),5)
        self.assertFalse(list(revision.CLIENT.glob('*.py')))

    def test_setup_copy_matches_real_prompts_not_unused_helpers(self):
        source=(revision.ROOT/'installer.ps1').read_text(encoding='utf-8-sig')
        target=(revision.ROOT/'auto_setup.ps1').read_text(encoding='utf-8-sig')
        readme=(revision.ROOT/'README.md').read_text(encoding='utf-8')
        self.assertIn("Read-Choice 'MT5 terminal number'",target)
        self.assertIn("Read-Host 'Exact Gold / USD symbol",source)
        self.assertIn("Read-Host 'Exact Nasdaq 100 CFD symbol",source)
        self.assertIn('numbered running-terminal list',readme)
        self.assertIn('manually type the exact Gold/USD and Nasdaq CFD symbols',readme)
        self.assertIn('does **not** run automatic symbol discovery',readme)
        self.assertIn('Select the intended running MT5 from the numbered list',self.html)
        self.assertIn('type the exact Gold and Nasdaq 100 CFD symbol names',self.html)
        self.assertNotIn('Risk-only onboarding: exactly one',readme)

    @unittest.skipUnless(shutil.which('node'),'Node unavailable for isolated DOM fixture')
    def test_javascript_modes_and_current_fingerprints(self):
        code=r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(PATH,'utf8'),elements={};
class E{constructor(){this.children=[];this.attrs={};this.textContent='';this.innerHTML='';this.value='';}getAttribute(k){return this.attrs[k];}setAttribute(k,v){this.attrs[k]=v;}replaceChildren(...x){this.children=x;}append(...x){this.children.push(...x);}addEventListener(){}querySelectorAll(){return [];}scrollIntoView(){}}
for(const hit of html.matchAll(/<[^>]+\bid="([^"]+)"[^>]*>/g)){const e=new E();const box=hit[0].match(/viewBox="([^"]+)"/);if(box)e.attrs.viewBox=box[1];elements[hit[1]]=e;}
Object.assign(elements.risk,{value:'fixed'});elements.period.value='6m';elements.selection.value='all';elements.customBalance.value='10000';elements.customRisk.value='1';
const context=vm.createContext({document:{getElementById:id=>{assert.ok(elements[id],id);return elements[id];},createElement:()=>new E(),createElementNS:()=>new E()},console});
const script=html.slice(html.indexOf('<script>')+8,html.lastIndexOf('</script>'));vm.runInContext(script,context);
assert.match(elements.kind.textContent,/HISTORICAL/);assert.match(elements.scope.textContent,/Nasdaq DI ON/);
assert.match(elements.eaDetailCards.innerHTML,/DI agreement is OFF by default/);
assert.match(elements.eaDetailCards.innerHTML,/InpRequireDIAgreement<\/td><td>false/);
assert.equal(elements.fingerprints.children.length,5);
const manifest=JSON.parse(fs.readFileSync(MANIFEST,'utf8'));
assert.equal(elements.fingerprints.children[3].children.at(-1).textContent,manifest.entries[3].ex5_sha256);
elements.risk.value='balance';elements.period.value='3m';elements.selection.value='nasdaq-5m-candle-momentum';vm.runInContext('render()',context);
assert.match(elements.kind.textContent,/NOT CURRENT DI-OFF EVIDENCE/);assert.match(elements.scope.textContent,/Historical inputs/);
elements.risk.value='custom';elements.customBalance.value='1000';elements.customRisk.value='5';vm.runInContext('render()',context);
assert.match(elements.customNotice.textContent,/NOT an estimate of the current DI-OFF/);
elements.customRisk.value='-1';vm.runInContext('render()',context);assert.match(elements.scope.textContent,/Invalid custom inputs/);
process.stdout.write('Historical modes, current DI metadata and fingerprint DOM verified');
'''
        code=code.replace('PATH',json.dumps(str(revision.CLIENT/'Performance and Setup.html')))
        code=code.replace('MANIFEST',json.dumps(str(revision.ROOT/'manifest.json')))
        result=subprocess.run([shutil.which('node'),'-e',code],text=True,capture_output=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr)


if __name__=='__main__':unittest.main()
