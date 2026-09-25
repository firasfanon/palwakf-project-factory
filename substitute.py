#!/usr/bin/env python3
"""
محرك استبدال المتغيرات لمصنع المشاريع (palwakf-project-factory).
يقرأ ملف إعداد JSON، ويستبدل {{TOKEN}} في كل ملفات .md داخل مجلد الإخراج.
لا يعتمد على مكتبات خارجية — Python القياسية فقط.
"""
import json
import sys
from pathlib import Path


def build_related_systems_rows(related_systems):
    """يحوّل قائمة أنظمة إلى صفوف جدول Markdown."""
    if not related_systems:
        return "| — | — | لا توجد أنظمة مرتبطة حاليًا |"
    rows = []
    for entry in related_systems:
        parts = (entry.split(":") + ["", ""])[:3]
        name, link_type, note = [p.strip() for p in parts]
        rows.append(f"| {name} | {link_type or '—'} | {note or '—'} |")
    return "\n".join(rows)


def main():
    if len(sys.argv) != 3:
        print("الاستخدام: python3 substitute.py <target_dir> <config.json>", file=sys.stderr)
        sys.exit(1)

    target_dir = Path(sys.argv[1])
    config_path = Path(sys.argv[2])

    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    db_shared = config.get("DB_SHARED", False)
    related_systems = config.get("RELATED_SYSTEMS", [])

    tokens = {
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
    }

    md_files = list(target_dir.rglob("*.md"))
    if not md_files:
        print(f"⚠️  لم أجد أي ملف .md داخل {target_dir}", file=sys.stderr)
        sys.exit(1)

    changed = 0
    for file_path in md_files:
        text = file_path.read_text(encoding="utf-8")
        original = text
        for key, value in tokens.items():
            text = text.replace("{{" + key + "}}", value)
        if text != original:
            file_path.write_text(text, encoding="utf-8")
            changed += 1

    print(f"✅ تم استبدال المتغيرات في {changed} ملف من أصل {len(md_files)}.")


if __name__ == "__main__":
    main()
