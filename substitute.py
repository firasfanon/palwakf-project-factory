#!/usr/bin/env python3
"""
محرك استبدال المتغيرات لمصنع المشاريع (palwakf-project-factory).
يقرأ ملف إعداد JSON، ويستبدل {{TOKEN}} في كل ملف نصي داخل مجلد الإخراج
(md, yaml, json, dart, ts/tsx, html, .env.example, .gitignore... أي ملف قابل للقراءة كنص UTF-8).
لا يعتمد على مكتبات خارجية — Python القياسية فقط.
"""
import json
import sys
from pathlib import Path

SKIP_DIR_NAMES = {".git", "node_modules", ".dart_tool", "build", "dist"}


def build_related_systems_rows(related_systems):
    if not related_systems:
        return "| — | — | لا توجد أنظمة مرتبطة حاليًا |"
    rows = []
    for entry in related_systems:
        parts = (entry.split(":") + ["", ""])[:3]
        name, link_type, note = [p.strip() for p in parts]
        rows.append(f"| {name} | {link_type or '—'} | {note or '—'} |")
    return "\n".join(rows)


def build_tokens(config):
    """يبني خريطة المتغيرات من ملف الإعداد (مستخرَجة من main دون تغيير السلوك)."""
    db_shared = config.get("DB_SHARED", False)
    related_systems = config.get("RELATED_SYSTEMS", [])
    return {
        "PROJECT_NAME": config.get("PROJECT_NAME", "[اسم المشروع]"),
        "PROJECT_TYPE": config.get("PROJECT_TYPE", "[نوعه]"),
        "PROJECT_STATUS": config.get("PROJECT_STATUS", "[الحالة]"),
        "PROJECT_OWNER": config.get("PROJECT_OWNER", "[المسؤول]"),
        "PROJECT_DATE": config.get("PROJECT_DATE", "[YYYY-MM-DD]"),
        "PROJECT_GOAL": config.get("PROJECT_GOAL", "[ما الذي يحله المشروع ولمن؟]"),
        "PROFILE_NAME": config.get("PROFILE_NAME", "generic"),
        "FACTORY_VERSION": config.get("FACTORY_VERSION", "0.0.0"),
        "DB_SHARED_NOTE": "نعم — راجع جدول الأنظمة المرتبطة أدناه قبل أي تعديل بنيوي" if db_shared else "لا",
        "RELATED_SYSTEMS_ROWS": build_related_systems_rows(related_systems),
        "SLUG_SNAKE": config.get("SLUG_SNAKE", "my_project"),
        "SLUG_KEBAB": config.get("SLUG_KEBAB", "my-project"),
        "CLASS_NAME": config.get("CLASS_NAME", "MyProject"),
    }


def main():
    if len(sys.argv) != 3:
        print("الاستخدام: python3 substitute.py <target_dir> <config.json>", file=sys.stderr)
        sys.exit(1)

    target_dir = Path(sys.argv[1])
    config_path = Path(sys.argv[2])

    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    tokens = build_tokens(config)

    all_files = [
        p for p in target_dir.rglob("*")
        if p.is_file() and not any(part in SKIP_DIR_NAMES for part in p.parts)
    ]
    if not all_files:
        print(f"⚠️  لم أجد أي ملف داخل {target_dir}", file=sys.stderr)
        sys.exit(1)

    changed = 0
    skipped_binary = 0
    for file_path in all_files:
        try:
            text = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, IsADirectoryError):
            skipped_binary += 1
            continue
        original = text
        for key, value in tokens.items():
            text = text.replace("{{" + key + "}}", value)
        if text != original:
            file_path.write_text(text, encoding="utf-8")
            changed += 1

    print(f"✅ تم استبدال المتغيرات في {changed} ملف من أصل {len(all_files)} "
          f"(تجاهلت {skipped_binary} ملفًا ثنائيًا).")


if __name__ == "__main__":
    main()
