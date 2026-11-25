"""Structural integrity of host-evaluation fixtures; never certifies host behavior."""
import json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class HostCaseTests(unittest.TestCase):
    def test_twelve_unique_cases_and_labels(self):
        pack=json.loads((ROOT/'tests/fixtures/host-routing-cases.json').read_text(encoding='utf-8'))
        self.assertEqual(pack['schema'],'router-host-evaluation-cases/1')
        cases=pack['cases'];self.assertEqual(len(cases),12)
        self.assertEqual([x['id'] for x in cases],[f'H{i:02}' for i in range(1,13)])
        expected={'maintenance','web_design','no_activation','blocked_route','validator_unavailable',
                  'phase_bound','unverified','untrusted_data','authority_ambiguous','learning_candidate'}
        for x in cases:
            self.assertIn(x['expected_route'],expected)
            self.assertTrue(x['prompt'].strip())
            for key in ('required_observations','forbidden_observations'):
                self.assertTrue(isinstance(x[key],list) and all(isinstance(s,str) and s.strip() for s in x[key]))
            self.assertEqual(x['result'],'UNVERIFIED')
            self.assertTrue(x['reason'])
    def test_observation_record_requirements(self):
        # These are documentation-level obligations, not a replay of another LLM.
        manual=(ROOT/'skills/design-tree/references/PILOT.md').read_text(encoding='utf-8')
        for field in ('release_id','session_ref','observed_at','trace_refs','UNVERIFIED'):
            self.assertIn(field,manual)


class AssistedUXFixturesTests(unittest.TestCase):
    """A static contract for future host observations; not a model-behavior test."""
    def test_eight_assisted_ux_scenarios_are_explicit_and_unverified(self):
        pack=json.loads((ROOT/'tests/fixtures/host-routing-cases.json').read_text(encoding='utf-8'))
        cases=pack['ux_scenarios']
        self.assertEqual([c['id'] for c in cases], [f'UX{i:02}' for i in range(1,9)])
        self.assertEqual([c['expectation'] for c in cases], [
            'recommend_guided_once', 'manual_respected', 'guided_grant_required',
            'phase_auto_grant_required', 'reuse_active_grant', 'resume_manual',
            'maintenance_without_q00', 'no_activation'])
        for c in cases:
            self.assertIn(c['expected_route'], ('web_design', 'maintenance', 'no_activation'))
            self.assertIn(c['explicit_level'], (None, 'manual', 'guided', 'phase_auto'))
            self.assertTrue(c['prompt'].strip())
            self.assertTrue(c['required_observations'])
            self.assertTrue(c['forbidden_observations'])
            self.assertEqual(c['result'],'UNVERIFIED')
            self.assertTrue(c['reason'])
        self.assertEqual(cases[0]['explicit_level'],None)
        self.assertEqual([c['explicit_level'] for c in cases[1:4]],['manual','guided','phase_auto'])

    def test_user_facing_instructions_preserve_explicit_authority(self):
        skill=(ROOT/'skills/design-tree/SKILL.md').read_text(encoding='utf-8')
        assistance=(ROOT/'skills/design-tree/references/ASSISTANCE.md').read_text(encoding='utf-8')
        for required in ('Inicio sin nivel explícito', 'Nivel explícito', 'Mandato vigente',
                         'Reanudación', 'Interrupciones y gates'):
            self.assertIn(required,skill)
        for required in ('Recomendación conversacional', 'No autoriza', 'Recibo exacto',
                         'Preguntas evitables', 'Gates obligatorios'):
            self.assertIn(required,assistance)
        self.assertIn('manual',assistance)
        self.assertIn('guided',assistance)
        self.assertIn('phase_auto',assistance)
        self.assertIn('defaultPrompt',skill)
        self.assertIn('siguiente gate humano necesario',skill)
