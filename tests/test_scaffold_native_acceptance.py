"""Regression gates derived from actual PM -> Factory generated-project build failures."""
import json
import pathlib
import tempfile
import unittest

from consumer import adapter as factory

ROOT = pathlib.Path(__file__).resolve().parent.parent


class GeneratedStarterChecks(unittest.TestCase):
    def _materialized(self, tmp, stack):
        bp = json.loads((ROOT / 'tests/fixtures/prompt-maker/golden-react-vite-supabase.json').read_text(encoding='utf-8'))
        if stack == 'flutter-supabase':
            bp['technology_decision']['stack'] = 'flutter-supabase'
        target = pathlib.Path(tmp) / 'generated'
        result = factory.materialize(bp, target, project_date='2026-10-21')
        self.assertEqual(result['status'], 'MATERIALIZED_AND_VALIDATED')
        self.assertTrue(result['materialized'])
        return target

    def test_react_has_nonempty_test_and_eslint_flat_config(self):
        with tempfile.TemporaryDirectory() as directory:
            target = self._materialized(directory, 'react-vite-supabase')
            scripts = json.loads((target / 'package.json').read_text(encoding='utf-8'))['scripts']
            self.assertIn('vitest', scripts['test'])
            self.assertIn('eslint', scripts['lint'])
            self.assertTrue((target / 'eslint.config.js').is_file())
            self.assertIn('@typescript-eslint/parser', (target / 'package.json').read_text(encoding='utf-8'))
            self.assertIn("renderToStaticMarkup", (target / 'tests/unit/app-render.test.tsx').read_text(encoding='utf-8'))
            self.assertIn('no-unused-vars', (target / 'eslint.config.js').read_text(encoding='utf-8'))

    def test_flutter_uses_non_deprecated_supabase_key_without_env_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            target = self._materialized(directory, 'flutter-supabase')
            source = (target / 'lib/main.dart').read_text(encoding='utf-8')
            self.assertIn('publishableKey:', source)
            self.assertNotIn('anonKey:', source)
            self.assertIn("String.fromEnvironment('SUPABASE_ANON_KEY')", source)
            self.assertIn('SUPABASE_ANON_KEY=', (target / '.env.example').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
