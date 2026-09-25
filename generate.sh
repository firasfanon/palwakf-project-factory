#!/usr/bin/env bash
# مصنع المشاريع — يولّد docs/ai (وهيكل الكود الأساسي إن رغبت) لمشروع جديد أو قائم.
# الاستخدام: bash generate.sh

set -euo pipefail

FACTORY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROFILES_DIR="$FACTORY_DIR/profiles"
FACTORY_VERSION="$(cat "$FACTORY_DIR/VERSION" 2>/dev/null || echo "0.0.0")"
REGISTRY_FILE="$FACTORY_DIR/PROJECTS_REGISTRY.md"

echo "🏭 مصنع مشاريع PalWakf — الإصدار $FACTORY_VERSION"
echo "════════════════════════════════════════════"
echo

read -rp "اسم المشروع (يمكن أن يكون عربيًا): " PROJECT_NAME
if [[ -z "$PROJECT_NAME" ]]; then
  echo "❌ اسم المشروع إلزامي." >&2
  exit 1
fi

read -rp "معرّف المشروع بالإنجليزية (يُستخدم في pubspec.yaml/package.json — اتركه فارغًا للاشتقاق التلقائي): " PROJECT_SLUG_INPUT

read -rp "نوع المشروع (web/mobile/api/cli) [web]: " PROJECT_TYPE
PROJECT_TYPE=${PROJECT_TYPE:-web}

read -rp "حالة المشروع (تخطيط/تطوير/صيانة) [تطوير]: " PROJECT_STATUS
PROJECT_STATUS=${PROJECT_STATUS:-تطوير}

read -rp "المسؤول عن المشروع: " PROJECT_OWNER

read -rp "هدف المشروع (سطر أو سطران): " PROJECT_GOAL

echo
echo "اختر النمط التقني:"
echo "  1) generic              — غير محدد الحزمة (تملأ TECH_STACK يدويًا، بلا هيكل كود جاهز)"
echo "  2) flutter-supabase     — Flutter + Supabase"
echo "  3) react-vite-supabase  — React + Vite + Supabase"
read -rp "اختيارك [1]: " PROFILE_CHOICE
PROFILE_CHOICE=${PROFILE_CHOICE:-1}

case "$PROFILE_CHOICE" in
  1) PROFILE_NAME="generic" ;;
  2) PROFILE_NAME="flutter-supabase" ;;
  3) PROFILE_NAME="react-vite-supabase" ;;
  *) echo "❌ اختيار غير صحيح." >&2; exit 1 ;;
esac

if [[ ! -d "$PROFILES_DIR/$PROFILE_NAME" ]]; then
  echo "❌ النمط $PROFILE_NAME غير موجود في $PROFILES_DIR" >&2
  exit 1
fi

echo
read -rp "هل يشارك هذا المشروع قاعدة بيانات مع أنظمة أخرى؟ (y/n) [n]: " DB_SHARED_ANSWER
DB_SHARED_ANSWER=${DB_SHARED_ANSWER:-n}
if [[ "$DB_SHARED_ANSWER" =~ ^[yY]$ ]]; then
  DB_SHARED=true
else
  DB_SHARED=false
fi

RELATED_SYSTEMS_JSON="[]"
if [[ "$DB_SHARED" == "true" ]]; then
  echo "أدخل الأنظمة المرتبطة، كل نظام في سطر بصيغة: اسم النظام:نوع الارتباط:ملاحظة"
  echo "(اترك السطر فارغًا وانتقل بالضغط على Enter عندما تنتهي)"
  RELATED_SYSTEMS=()
  while true; do
    read -rp "> " ENTRY
    [[ -z "$ENTRY" ]] && break
    RELATED_SYSTEMS+=("$ENTRY")
  done
  if [[ ${#RELATED_SYSTEMS[@]} -gt 0 ]]; then
    RELATED_SYSTEMS_JSON=$(python3 -c "
import json, sys
print(json.dumps(sys.argv[1:], ensure_ascii=False))
" "${RELATED_SYSTEMS[@]}")
  fi
fi

# هل يوجد هيكل كود جاهز (scaffold) لهذا النمط؟
SCAFFOLD_DIR="$PROFILES_DIR/$PROFILE_NAME/scaffold"
GENERATE_SCAFFOLD="n"
if [[ -d "$SCAFFOLD_DIR" ]]; then
  echo
  read -rp "هل تريد أيضًا توليد هيكل الكود الأساسي (pubspec.yaml أو package.json + بنية المجلدات)؟ (y/n) [y]: " SCAFFOLD_ANSWER
  SCAFFOLD_ANSWER=${SCAFFOLD_ANSWER:-y}
  [[ "$SCAFFOLD_ANSWER" =~ ^[yY]$ ]] && GENERATE_SCAFFOLD="y"
fi

echo
read -rp "مسار مجلد الإخراج (سيُنشأ فيه docs/ai وهيكل الكود): " OUTPUT_DIR
if [[ -z "$OUTPUT_DIR" ]]; then
  echo "❌ مسار الإخراج إلزامي." >&2
  exit 1
fi

PROJECT_DATE="$(date +%Y-%m-%d)"
mkdir -p "$OUTPUT_DIR"

# 1) وثّق docs/ai: القاعدة العامة أولًا، ثم تراكب النمط المختار فوقها
mkdir -p "$OUTPUT_DIR/docs/ai"
cp -r "$PROFILES_DIR/generic/docs/ai/." "$OUTPUT_DIR/docs/ai/"
if [[ "$PROFILE_NAME" != "generic" ]]; then
  cp -r "$PROFILES_DIR/$PROFILE_NAME/docs/ai/." "$OUTPUT_DIR/docs/ai/"
fi

# 2) هيكل الكود (اختياري) — لا يستبدل أي ملف موجود مسبقًا (no-clobber)
SCAFFOLD_APPLIED="false"
if [[ "$GENERATE_SCAFFOLD" == "y" ]]; then
  BEFORE_COUNT=$(find "$OUTPUT_DIR" -type f | wc -l)
  cp -rn "$SCAFFOLD_DIR/." "$OUTPUT_DIR/"
  AFTER_COUNT=$(find "$OUTPUT_DIR" -type f | wc -l)
  SCAFFOLD_APPLIED="true"
  if [[ "$AFTER_COUNT" -lt $((BEFORE_COUNT + $(find "$SCAFFOLD_DIR" -type f | wc -l))) ]]; then
    echo "ℹ️  بعض ملفات الهيكل كانت موجودة مسبقًا في $OUTPUT_DIR ولم تُستبدل (لحماية عملك الحالي)."
  fi
fi

# 3) اشتقاق المعرّفات البرمجية (slug) + بناء ملف الإعداد + الاستبدال الفعلي
if [[ "$DB_SHARED" == "true" ]]; then
  DB_SHARED_PY="True"
else
  DB_SHARED_PY="False"
fi

CONFIG_FILE="$(mktemp)"
python3 -c "
import json, re

name = '''$PROJECT_NAME'''
slug_input = '''$PROJECT_SLUG_INPUT'''.strip()
raw = slug_input or name
raw = raw.lower()
raw = re.sub(r'[^a-z0-9]+', '_', raw).strip('_')
if not raw:
    raw = 'my_project'
if raw[0].isdigit():
    raw = 'p_' + raw
slug_snake = raw
slug_kebab = raw.replace('_', '-')
class_name = ''.join(part.capitalize() for part in raw.split('_') if part) or 'MyProject'

config = {
    'PROJECT_NAME': name,
    'PROJECT_TYPE': '''$PROJECT_TYPE''',
    'PROJECT_STATUS': '''$PROJECT_STATUS''',
    'PROJECT_OWNER': '''$PROJECT_OWNER''',
    'PROJECT_DATE': '''$PROJECT_DATE''',
    'PROJECT_GOAL': '''$PROJECT_GOAL''',
    'PROFILE_NAME': '''$PROFILE_NAME''',
    'FACTORY_VERSION': '''$FACTORY_VERSION''',
    'DB_SHARED': $DB_SHARED_PY,
    'RELATED_SYSTEMS': $RELATED_SYSTEMS_JSON,
    'SLUG_SNAKE': slug_snake,
    'SLUG_KEBAB': slug_kebab,
    'CLASS_NAME': class_name,
}
with open('$CONFIG_FILE', 'w', encoding='utf-8') as f:
    json.dump(config, f, ensure_ascii=False)
print(f'   المعرّف البرمجي المشتق: {slug_snake} (Dart) / {slug_kebab} (npm) / {class_name} (اسم الصنف)')
"

python3 "$FACTORY_DIR/substitute.py" "$OUTPUT_DIR" "$CONFIG_FILE"
rm -f "$CONFIG_FILE"

# 4) سجّل المشروع في السجل المركزي بالمصنع
if [[ ! -f "$REGISTRY_FILE" ]]; then
  echo "⚠️  لم أجد $REGISTRY_FILE — تأكد من وجوده في مجلد المصنع." >&2
else
  printf '| %s | %s | %s | %s | %s | %s | %s |\n' \
    "$PROJECT_NAME" "$PROFILE_NAME" "$PROJECT_STATUS" "$PROJECT_DATE" "$OUTPUT_DIR" "$DB_SHARED" "$SCAFFOLD_APPLIED" \
    >> "$REGISTRY_FILE"
  echo "📋 سُجِّل المشروع في $REGISTRY_FILE"
fi

echo
echo "🎉 تم توليد المشروع بنجاح في: $OUTPUT_DIR"
echo "   النمط المستخدم: $PROFILE_NAME"
echo "   هيكل الكود: $([ "$SCAFFOLD_APPLIED" == "true" ] && echo "تم توليده" || echo "لم يُطلب")"
echo "   الخطوة التالية: افتح docs/ai/00_MASTER_CONTEXT.md وأكمل الحقول بين [أقواس]،"
echo "   ثم اتبع docs/ai/IMPLEMENTATION_PLAN.md لتفعيل الحزمة فعليًا."
