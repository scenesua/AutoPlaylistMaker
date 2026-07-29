import os
import sys
import json
import logging
import threading
from functools import lru_cache

RTL_LOCALES = {'ar'}
logger = logging.getLogger(__name__)

def _locale_dir():
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, 'locales')

LOCALE_DIR = _locale_dir()
_PREF_FILE = os.path.join(os.path.expanduser("~"), ".autoplaylistmaker_lang")

DEFAULT_LOCALE = "ko-KR"
FALLBACK_LOCALE = "en-US"

_SUPPORTED = [
    ("ko-KR", "한국어"),
    ("en-US", "English"),
    ("ja-JP", "日本語"),
    ("zh-CN", "简体中文"),
    ("zh-TW", "繁體中文"),
    ("es-ES", "Español"),
    ("fr-FR", "Français"),
    ("it-IT", "Italiano"),
    ("de-DE", "Deutsch"),
    ("ru-RU", "Русский"),
    ("ar", "العربية"),
]

LOCALE_NAMES = dict(_SUPPORTED)
SUPPORTED_LOCALES = [code for code, _ in _SUPPORTED]

_PLURAL_LOCALES = {
    'en-US': lambda n: 0 if n == 1 else 1,
    'ko-KR': lambda n: 0,
    'ja-JP': lambda n: 0,
    'zh-CN': lambda n: 0,
    'zh-TW': lambda n: 0,
    'es-ES': lambda n: 0 if n == 1 else 1,
    'fr-FR': lambda n: 0 if n in (0, 1) else 1,
    'it-IT': lambda n: 0 if n == 1 else 1,
    'de-DE': lambda n: 0 if n == 1 else 1,
    'ru-RU': lambda n: 0 if n % 10 == 1 and n % 100 != 11 else 1,
    'ar':    lambda n: 0 if n == 1 else (1 if n == 2 else (2 if n >= 3 and n <= 10 else 3)),
}


def _detect_system_locale():
    import locale as _lc
    try:
        raw, _ = _lc.getdefaultlocale()
        if not raw:
            return None
        code = raw.replace('_', '-')
        if code in SUPPORTED_LOCALES:
            return code
        short = code.split('-')[0]
        for c in SUPPORTED_LOCALES:
            if c.startswith(short):
                return c
        return None
    except Exception:
        return None


def _load_pref():
    try:
        with open(_PREF_FILE, 'r', encoding='utf-8') as f:
            return json.load(f).get('lang', '')
    except FileNotFoundError:
        return ''
    except (OSError, json.JSONDecodeError):
        logger.exception("Failed to load language preference from %s", _PREF_FILE)
        return ''


def _save_pref(locale):
    try:
        with open(_PREF_FILE, 'w', encoding='utf-8') as f:
            json.dump({'lang': locale}, f)
    except OSError:
        logger.exception("Failed to save language preference to %s", _PREF_FILE)


@lru_cache(maxsize=len(SUPPORTED_LOCALES))
def _load_locale_data(locale):
    path = os.path.join(LOCALE_DIR, f"{locale}.json")
    if os.path.isfile(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            logger.exception("Failed to load locale file: %s", path)
    return {}


class I18n:
    def __init__(self):
        self._lock = threading.Lock()
        self._locale = DEFAULT_LOCALE
        self._data = {}
        self._fallback_data = {}
        self._listeners = []
        self._load()

    def _load(self):
        pref = _load_pref()
        if pref in SUPPORTED_LOCALES:
            self._locale = pref
        elif _detect_system_locale():
            sys_loc = _detect_system_locale()
            if sys_loc:
                self._locale = sys_loc
        self._data = _load_locale_data(self._locale)
        self._fallback_data = _load_locale_data(FALLBACK_LOCALE)

    def _resolve(self, key):
        return self._resolve_from(self._data, key) or self._resolve_from(
            self._fallback_data, key
        )

    @staticmethod
    def _resolve_from(data, key):
        parts = key.split('.')
        d = data
        for p in parts:
            if isinstance(d, dict):
                d = d.get(p)
            else:
                d = None
                break
        if d is not None and isinstance(d, str):
            return d
        return None

    def t(self, translation_key, **kwargs):
        raw = self._resolve(translation_key)
        if raw is None:
            logger.error("Missing translation key: %s (locale=%s)",
                         translation_key, self._locale)
            raw = f"?{translation_key}?"
        if kwargs:
            try:
                return raw.format(**kwargs)
            except (KeyError, ValueError):
                logger.exception(
                    "Translation format mismatch: %s (locale=%s, kwargs=%s)",
                    translation_key, self._locale, sorted(kwargs),
                )
                return raw
        return raw

    def n(self, key_singular, key_plural, count, **kwargs):
        plural_fn = _PLURAL_LOCALES.get(self._locale, _PLURAL_LOCALES[DEFAULT_LOCALE])
        idx = plural_fn(count)
        if idx == 0:
            raw = self._resolve(key_singular)
        else:
            raw = self._resolve(key_plural)
        if raw is None:
            raw = f"?{key_singular}?" if idx == 0 else f"?{key_plural}?"
        kwargs.setdefault('count', count)
        try:
            return raw.format(**kwargs)
        except (KeyError, ValueError):
            logger.exception(
                "Plural translation format mismatch: %s/%s (locale=%s)",
                key_singular, key_plural, self._locale,
            )
            return raw

    @property
    def locale(self):
        return self._locale

    @locale.setter
    def locale(self, value):
        if value not in SUPPORTED_LOCALES:
            value = DEFAULT_LOCALE
        with self._lock:
            self._locale = value
            self._data = _load_locale_data(value)
        _save_pref(value)
        self._notify()

    def is_rtl(self):
        return self._locale in RTL_LOCALES

    def get_rtl_direction(self):
        return 'rtl' if self.is_rtl() else 'ltr'

    def get_name(self, locale=None):
        return LOCALE_NAMES.get(locale or self._locale, locale or self._locale)

    def choice_id(self, value, choices, default=None):
        """Return a stable choice ID from an ID or any supported translation."""
        if value in choices:
            return value
        for locale in SUPPORTED_LOCALES:
            data = _load_locale_data(locale)
            for choice_id, translation_key in choices.items():
                if self._resolve_from(data, translation_key) == value:
                    return choice_id
        return default if default is not None else next(iter(choices), value)

    @property
    def native_name(self):
        return LOCALE_NAMES.get(self._locale, self._locale)

    def on_change(self, callback):
        self._listeners.append(callback)

    def off_change(self, callback):
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify(self):
        for cb in self._listeners:
            try:
                cb(self._locale)
            except Exception:
                logger.exception("Language-change listener failed: %r", cb)

    def format_number(self, n, decimals=0):
        locale = self._locale
        formatted = f"{n:,.{decimals}f}" if decimals else f"{n:,}"
        if locale == 'ar':
            formatted = formatted.replace(',', '،')
        return formatted

    def format_duration(self, total_seconds):
        total = int(total_seconds)
        h = total // 3600
        m = (total % 3600) // 60
        s = total % 60
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"

    def format_eta(self, remaining):
        remaining = int(remaining)
        if remaining <= 0:
            return ""
        h = remaining // 3600
        m = (remaining % 3600) // 60
        s = remaining % 60
        parts = []
        if h > 0:
            parts.append(self.t('time.hours', count=h, n=h))
        if m > 0:
            parts.append(self.t('time.minutes', count=m, n=m))
        if s > 0 or not parts:
            parts.append(self.t('time.seconds', count=s, n=s))
        if parts:
            return self.t('time.remaining', time=' '.join(parts))
        return ""


_i18n = None
_lock = threading.Lock()


def get_instance():
    global _i18n
    if _i18n is None:
        with _lock:
            if _i18n is None:
                _i18n = I18n()
    return _i18n


def t(translation_key, **kwargs):
    return get_instance().t(translation_key, **kwargs)


def n(key_singular, key_plural, count, **kwargs):
    return get_instance().n(key_singular, key_plural, count, **kwargs)


def choice_id(value, choices, default=None):
    return get_instance().choice_id(value, choices, default)
