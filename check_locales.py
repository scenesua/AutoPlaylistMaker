"""Static integrity checks for AutoPlaylistMaker locale JSON files."""

from __future__ import annotations

import json
import re
import string
import sys
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOCALE_DIR = ROOT / "locales"
SOURCE_LOCALE = "en-US"
KEY_PATTERN = re.compile(r"""\bt\(\s*["']([^"']+)["']""")
RAW_KEY_PATTERN = re.compile(r"\?[A-Za-z][A-Za-z0-9_.-]+\?")
BAD_PLACEHOLDER_PATTERNS = (
    re.compile(r"\{\{[A-Za-z_][^{}]*\}\}"),
    re.compile(r"\$\{[A-Za-z_][^{}]*\}"),
    re.compile(r"%(?:\([^)]+\))?[sd]"),
)
KO_FORBIDDEN = (
    "이페큫", "이페귷", "이페크", "이펙트", "이팩트",
    "켈리", "켜리", "번짝", "효과과",
    "켈기", "까빡", "캄롯", "횟와", "占",
)
TERM_GLOSSARY = {
    "ko-KR": {
        "design.title": "디자인/효과 편집",
        "design.preview": "미리보기",
        "render.title": "렌더링",
        "dist.auto": "자동 분배",
        "dist.manual": "수동 분배",
    },
    "en-US": {
        "design.title": "Design & Effects",
        "design.preview": "Preview",
        "render.title": "Render",
    },
    "ja-JP": {
        "design.title": "デザイン＆エフェクト",
        "design.preview": "プレビュー",
        "render.title": "レンダリング",
    },
    "zh-CN": {
        "design.title": "设计与特效",
        "design.preview": "预览",
        "render.title": "渲染",
    },
    "zh-TW": {
        "design.title": "設計與特效",
        "design.preview": "預覽",
        "render.title": "渲染",
    },
    "de-DE": {
        "design.title": "Design & Effekte",
        "design.preview": "Vorschau",
        "render.title": "Rendern",
        "common.cancel": "Abbrechen",
    },
    "ru-RU": {
        "design.title": "Дизайн и эффекты",
        "design.preview": "Предварительный просмотр",
        "render.title": "Рендеринг",
        "common.cancel": "Отмена",
    },
}


def _load_json_with_duplicate_check(path):
    duplicates = []

    def pairs_hook(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                duplicates.append(key)
            result[key] = value
        return result

    data = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=pairs_hook,
    )
    return data, duplicates


def _flatten(value, prefix=""):
    result = {}
    for key, child in value.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(child, dict):
            result.update(_flatten(child, path))
        else:
            result[path] = child
    return result


def _fields(value):
    if not isinstance(value, str):
        return set()
    return {
        name.split(".", 1)[0].split("[", 1)[0]
        for _, name, _, _ in string.Formatter().parse(value)
        if name
    }


def check_locales():
    errors = []
    warnings = []
    locales = {}
    for path in sorted(LOCALE_DIR.glob("*.json")):
        try:
            data, duplicates = _load_json_with_duplicate_check(path)
            if duplicates:
                errors.append(
                    f"{path.name}: duplicate key(s): "
                    + ", ".join(sorted(set(duplicates)))
                )
            locales[path.stem] = _flatten(data)
        except UnicodeDecodeError as error:
            errors.append(f"{path.name}: invalid UTF-8: {error}")
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"{path.name}: invalid JSON: {error}")

    if SOURCE_LOCALE not in locales:
        return [f"missing source locale: {SOURCE_LOCALE}"], warnings

    source = locales[SOURCE_LOCALE]
    for locale, values in locales.items():
        missing = sorted(set(source) - set(values))
        orphaned = sorted(set(values) - set(source))
        if missing:
            warnings.append(
                f"{locale}: {len(missing)} fallback key(s): "
                + ", ".join(missing)
            )
        if orphaned:
            errors.append(
                f"{locale}: orphan key(s): " + ", ".join(orphaned)
            )
        for key in sorted(set(source) & set(values)):
            value = values[key]
            if not isinstance(value, str):
                errors.append(
                    f"{locale}: non-string value: {key} "
                    f"({type(value).__name__})"
                )
                continue
            if value == "":
                errors.append(f"{locale}: empty value: {key}")
            if (
                value.strip() in {"null", "None", "undefined"}
                and key != "common.none"
            ):
                errors.append(f"{locale}: invalid sentinel value: {key}")
            if "\ufffd" in value:
                errors.append(f"{locale}: replacement character: {key}")
            if value != unicodedata.normalize("NFC", value):
                errors.append(f"{locale}: non-NFC Unicode: {key}")
            if RAW_KEY_PATTERN.search(value):
                errors.append(f"{locale}: raw translation key in {key}")
            for pattern in BAD_PLACEHOLDER_PATTERNS:
                if (
                    key != "project.defaultNameFormat"
                    and pattern.search(value)
                ):
                    errors.append(
                        f"{locale}: invalid placeholder syntax: {key}"
                    )
            if _fields(value) != _fields(source[key]):
                errors.append(
                    f"{locale}: placeholder mismatch: {key} "
                    f"{_fields(value)} != {_fields(source[key])}"
                )

    korean = locales.get("ko-KR", {})
    for key, value in korean.items():
        for forbidden in KO_FORBIDDEN:
            if forbidden in value:
                errors.append(
                    f"ko-KR: forbidden term {forbidden!r}: {key}"
                )

    for locale, expected in TERM_GLOSSARY.items():
        values = locales.get(locale, {})
        for key, required_value in expected.items():
            if values.get(key) != required_value:
                errors.append(
                    f"{locale}: glossary mismatch: {key}: "
                    f"{values.get(key)!r} != {required_value!r}"
                )

    if locales.get("zh-CN") == locales.get("zh-TW"):
        errors.append("zh-CN and zh-TW resources must remain distinct")

    used_keys = set()
    for path in ROOT.glob("*.py"):
        used_keys.update(KEY_PATTERN.findall(path.read_text(encoding="utf-8")))
    for key in sorted(used_keys - set(source)):
        errors.append(f"source code uses undefined key: {key}")

    return errors, warnings


def main():
    errors, warnings = check_locales()
    for message in warnings:
        print(f"WARNING: {message}")
    for message in errors:
        print(f"ERROR: {message}")
    print(
        f"locale integrity: {len(errors)} error(s), "
        f"{len(warnings)} warning(s)"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
