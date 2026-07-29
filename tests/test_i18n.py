import json
import unittest
from pathlib import Path

import i18n
from check_locales import check_locales


class I18nIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.original_locale = i18n.get_instance().locale

    def tearDown(self):
        i18n.get_instance().locale = self.original_locale

    def test_all_locales_have_complete_keys_and_matching_placeholders(self):
        errors, warnings = check_locales()
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        self.assertIn('de-DE', i18n.SUPPORTED_LOCALES)
        self.assertIn('ru-RU', i18n.SUPPORTED_LOCALES)
        self.assertEqual(len(i18n.SUPPORTED_LOCALES), 11)

    def test_every_locale_resolves_every_english_key(self):
        locale_dir = Path(i18n.LOCALE_DIR)
        english = json.loads(
            (locale_dir / 'en-US.json').read_text(encoding='utf-8')
        )

        def flatten(data, prefix=''):
            result = {}
            for key, value in data.items():
                dotted = f'{prefix}.{key}' if prefix else key
                if isinstance(value, dict):
                    result.update(flatten(value, dotted))
                else:
                    result[dotted] = value
            return result

        keys = flatten(english)
        instance = i18n.get_instance()
        for locale in i18n.SUPPORTED_LOCALES:
            instance.locale = locale
            for key in keys:
                self.assertIsNotNone(instance._resolve(key), (locale, key))
                self.assertFalse(instance._resolve(key).startswith('?'))

    def test_choice_id_accepts_legacy_labels_from_every_locale(self):
        choices = {
            'count': 'render.loopCount',
            'target': 'render.loopTarget',
        }
        instance = i18n.get_instance()
        for locale in i18n.SUPPORTED_LOCALES:
            instance.locale = locale
            for stable_id, key in choices.items():
                self.assertEqual(
                    i18n.choice_id(i18n.t(key), choices),
                    stable_id,
                )


if __name__ == '__main__':
    unittest.main()
