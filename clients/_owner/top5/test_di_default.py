"""Client-only DI default regression; never opens or modifies an MT5 account."""
import base64
import json
import re
import unittest

from build import ROOT, CLIENT, SLUGS, client_source_defaults, read, sha

NASDAQ='nasdaq-5m-candle-momentum'


class SourceDefaults(unittest.TestCase):
    def test_client_nasdaq_true_becomes_false(self):
        source='input bool InpRequireDIAgreement=true; // keep the opt-in input\n'
        self.assertEqual(client_source_defaults(source,NASDAQ),source.replace('=true','=false'))

    def test_false_is_idempotent(self):
        source='input bool   InpRequireDIAgreement=false;\n'
        self.assertEqual(client_source_defaults(source,NASDAQ),source)

    def test_unrelated_strategy_unchanged(self):
        source='input bool InpRequireDIAgreement=true;\n'
        for slug in SLUGS:
            if slug!=NASDAQ:self.assertEqual(client_source_defaults(source,slug),source)

    def test_missing_input_fails_closed(self):
        with self.assertRaises(AssertionError):client_source_defaults('input bool Other=true;',NASDAQ)

    def test_duplicate_input_fails_closed(self):
        with self.assertRaises(AssertionError):
            client_source_defaults('input bool InpRequireDIAgreement=true;\n'*2,NASDAQ)


class PublishedDefaults(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads((ROOT/'manifest.json').read_text())

    def test_manifest_and_embedded_bat_default(self):
        bat=read(CLIENT/'Install Top 5.bat')
        encoded=re.search(r"FromBase64String\('([A-Za-z0-9+/=]+)'\)",bat)
        self.assertIsNotNone(encoded)
        public=json.loads(base64.b64decode(encoded[1]))
        self.assertEqual(public['entries'],self.manifest['entries'])
        row=next(r for r in public['entries'] if r['slug']==NASDAQ)
        self.assertEqual(row['inputs']['InpRequireDIAgreement'],'false')
        self.assertEqual(row['inputs']['InpDIPeriod'],'14')
        self.assertEqual(row['client_input_overrides'],{'InpRequireDIAgreement':'false'})

    def test_generated_mql_default_and_clean_compile(self):
        row=next(r for r in self.manifest['entries'] if r['slug']==NASDAQ)
        wrapper=ROOT/'build'/row['expert'].replace('.ex5','.mq5')
        direct=re.findall(r'#include\s+"(src_[^"]+)"',read(wrapper))
        self.assertEqual(len(direct),1)
        source=read(wrapper.parent/direct[0])
        self.assertRegex(source,r'input\s+bool\s+InpRequireDIAgreement\s*=\s*false\s*;')
        self.assertNotRegex(source,r'input\s+bool\s+InpRequireDIAgreement\s*=\s*true\s*;')
        self.assertIn('if(!InpRequireDIAgreement) return true;',source)
        self.assertRegex(read(wrapper.with_suffix('.log')),r'\b0 errors, 0 warnings\b')
        self.assertEqual(sha(wrapper.with_suffix('.ex5')),row['ex5_sha256'])
        self.assertEqual(sha(CLIENT/row['expert']),row['ex5_sha256'])

    def test_licence_risk_and_other_binaries_preserved(self):
        self.assertEqual(self.manifest['licence'],json.loads((ROOT/'licence.json').read_text()))
        self.assertEqual(self.manifest['licence']['expires_utc'],'2026-10-30T17:39:14+00:00')
        self.assertEqual(self.manifest['guard_sha256'],'7ff350425b3ec7809c6cb8af0605be4b75d92fdce6b1233a7d1b9de60c79b32b')
        self.assertEqual(sha(ROOT/'ClientGuard.mqh'),self.manifest['guard_sha256'])
        expected={
            'gold-overnight-value-area':'1c0e90d43059c690b995b117c0833cc585c5ec792b198d4869718f1cda44dad6',
            'xau-rsi-vwap':'59b9b404ab2f4dcb4ae957f275b99dfb4fb121f0b3ea3529cdb8455725b94b71',
            'nasdaq-overnight':'9d72a13d4588bf60d39602424e01ec8c8c3c92064c2ecb2f2e749bbd168e6a56',
            'orb-volume-profile':'327576834e36756b5d217c74da25342d3a911a80f85395d7c14eac5368c9bbad',
        }
        for row in self.manifest['entries']:
            self.assertEqual(row['inputs']['ClientRiskMode'],'0')
            self.assertEqual(row['inputs']['ClientRiskValue'],'50')
            if row['slug'] in expected:
                self.assertEqual(row['ex5_sha256'],expected[row['slug']])
                self.assertEqual(sha(CLIENT/row['expert']),expected[row['slug']])


if __name__=='__main__':unittest.main()
