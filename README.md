# 🏭 مصنع مشاريع PalWakf

أداة لتوليد حزمة `docs/ai` كاملة ومُعبّأة جزئيًا لأي مشروع جديد، بدل نسخ قوالب فارغة يدويًا
في كل مرة. تدعم عدة أنماط حزم تقنية، وتُبقي سجلًا مركزيًا بكل مشروع أُنشئ.

## الاستخدام السريع
```bash
bash generate.sh
```
ستُسأل عن اسم المشروع، نوعه، النمط التقني، ومسار الإخراج، وستحصل على `docs/ai/` جاهزة
مباشرة داخل مشروعك.

## الأنماط المتوفرة حاليًا
| النمط | الاستخدام |
|---|---|
| `generic` | أي مشروع بلا حزمة تقنية محددة مسبقًا — تملأ TECH_STACK.md يدويًا |
| `flutter-supabase` | تطبيقات Flutter تستخدم Supabase كخلفية |
| `react-vite-supabase` | تطبيقات ويب React + Vite تستخدم Supabase |

## بنية المصنع
```text
palwakf-project-factory/
├── profiles/                     # نمط لكل حزمة تقنية
│   ├── generic/docs/ai/          # القاعدة الكاملة (23+ ملف)
│   ├── flutter-supabase/docs/ai/ # تراكب: TECH_STACK, PROJECT_STRUCTURE,
│   │                                CODING_CONVENTIONS, ENVIRONMENT فقط
│   └── react-vite-supabase/docs/ai/  # نفس فكرة التراكب
├── generate.sh                   # أداة التوليد التفاعلية
├── substitute.py                 # محرك استبدال المتغيرات {{TOKEN}}
├── PROJECTS_REGISTRY.md          # سجل كل مشروع وُلِّد (يُحدَّث تلقائيًا)
├── UPDATE_POLICY.md              # كيف تنتشر تحديثات القوالب على المشاريع القائمة
└── VERSION                       # إصدار المصنع الحالي
```

## إضافة نمط تقني جديد (مثلًا: Node.js API)
1. أنشئ `profiles/node-api/docs/ai/`.
2. ضع فيه فقط الملفات التي تختلف عن `generic` (عادة: TECH_STACK.md, PROJECT_STRUCTURE.md,
   CODING_CONVENTIONS.md, ENVIRONMENT.md).
3. أضف خيار النمط الجديد في `generate.sh` (قسم `case "$PROFILE_CHOICE"`).
4. ارفع رقم إصدار المصنع في `VERSION` (MINOR — انظر UPDATE_POLICY.md).

## العلاقة بالحوكمة العامة (Drive) و`workspace_manager`
هذا المصنع مصدر حقيقة **لبنية التوثيق فقط** (كيف تبدو `docs/ai` لأي مشروع جديد).
هو ليس بديلاً عن الحوكمة الاستراتيجية على Drive، ولا عن `TASKS.md`/`DECISIONS.md` الفعليين
داخل كل مشروع بعد التوليد — تلك تبقى مسؤولية كل مشروع بمجرد أن يُنشأ.
راجع `UPDATE_POLICY.md` لفهم حدود الأتمتة الحالية عن قصد.
