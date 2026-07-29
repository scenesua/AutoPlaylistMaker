"""Fill missing locale entries from en-US using Google Translate.

Existing human translations are never overwritten. Format placeholders are
masked during translation and validated before a locale file is replaced.
"""

from __future__ import annotations

import json
import argparse
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parent
LOCALE_DIR = ROOT / "locales"
TARGET_LANGUAGES = {
    "ko-KR": "ko",
    "ja-JP": "ja",
    "zh-CN": "zh-CN",
    "zh-TW": "zh-TW",
    "es-ES": "es",
    "fr-FR": "fr",
    "it-IT": "it",
    "de-DE": "de",
    "ru-RU": "ru",
    "ar": "ar",
}
PLACEHOLDER = re.compile(r"\{[^{}]+\}")
_THREAD_STATE = threading.local()


def _get(data, dotted_key):
    current = data
    for part in dotted_key.split("."):
        current = current[part]
    return current


def _set(data, dotted_key, value):
    parts = dotted_key.split(".")
    current = data
    for part in parts[:-1]:
        current = current.setdefault(part, {})
    current[parts[-1]] = value


def _flatten(data, prefix=""):
    result = {}
    for key, value in data.items():
        dotted = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            result.update(_flatten(value, dotted))
        else:
            result[dotted] = value
    return result


def _translate(session, text, target):
    placeholders = PLACEHOLDER.findall(text)
    masked = text
    for index, placeholder in enumerate(placeholders):
        masked = masked.replace(placeholder, f" ZXPH{index}XZ ", 1)
    response = None
    for attempt in range(5):
        response = session.get(
            "https://translate.googleapis.com/translate_a/single",
            params={
                "client": "gtx", "sl": "en", "tl": target,
                "dt": "t", "q": masked,
            },
            timeout=20,
        )
        if response.ok:
            break
        time.sleep(0.5 * (attempt + 1))
    response.raise_for_status()
    translated = "".join(item[0] for item in response.json()[0] if item[0])
    for index, placeholder in enumerate(placeholders):
        translated = re.sub(
            rf"ZXPH{index}XZ", placeholder, translated,
            flags=re.IGNORECASE,
        )
    if sorted(PLACEHOLDER.findall(translated)) != sorted(placeholders):
        raise ValueError(
            f"placeholder mismatch: {placeholders!r} -> "
            f"{PLACEHOLDER.findall(translated)!r}"
        )
    return translated.strip()


def _translate_worker(text, target):
    session = getattr(_THREAD_STATE, "session", None)
    if session is None:
        session = requests.Session()
        _THREAD_STATE.session = session
    return _translate(session, text, target)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force-keys",
        help="JSON mapping of locale codes to keys that should be retranslated",
    )
    parser.add_argument(
        "--workers", type=int, default=8,
        help="Concurrent translation requests (default: 8)",
    )
    args = parser.parse_args()
    forced = {}
    if args.force_keys:
        forced = json.loads(
            Path(args.force_keys).read_text(encoding="utf-8")
        )
    source = json.loads(
        (LOCALE_DIR / "en-US.json").read_text(encoding="utf-8")
    )
    source_flat = _flatten(source)
    for locale, target in TARGET_LANGUAGES.items():
        path = LOCALE_DIR / f"{locale}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        missing = sorted(
            (set(source_flat) - set(_flatten(data)))
            | set(forced.get(locale, []))
        )
        values = [_get(source, key) for key in missing]
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            translated_values = pool.map(
                lambda value, language=target: _translate_worker(
                    value, language
                ),
                values,
            )
            translations = list(translated_values)
        for index, (key, translated) in enumerate(
            zip(missing, translations, strict=True), 1
        ):
            _set(data, key, translated)
            print(f"{locale} {index}/{len(missing)} {key}")
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
