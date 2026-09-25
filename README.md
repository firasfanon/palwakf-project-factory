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
│   ├── generic/docs/ai/          # القاعدة الكاملة (23+ ملف توثيق)
│   ├── flutter-supabase/
│   │   ├── docs/ai/              # تراكب: TECH_STACK, PROJECT_STRUCTURE,
│   │   │                            CODING_CONVENTIONS, ENVIRONMENT فقط
│   │   └── scaffold/             # هيكل كود Flutter جاهز (pubspec.yaml, lib/, test/...)
│   └── react-vite-supabase/
│       ├── docs/ai/              # نفس فكرة التراكب
│       └── scaffold/             # هيكل كود React+Vite جاهز (package.json, src/...)
├── generate.sh                   # أداة التوليد التفاعلية (توثيق + هيكل كود اختياري)
├── substitute.py                 # محرك استبدال المتغيرات {{TOKEN}} — يعمل على أي ملف نصي
├── PROJECTS_REGISTRY.md          # سجل مركزي يتوسّع مع كل مشروع جديد
├── UPDATE_POLICY.md              # كيف تنتشر تحديثات القوالب على المشاريع القائمة
└── VERSION                       # إصدار المصنع الحالي
```

## هيكل الكود (Scaffold) — ما يتولّد فعليًا
عند اختيار نمط `flutter-supabase` أو `react-vite-supabase` والموافقة على توليد الهيكل:
- **Flutter**: `pubspec.yaml` باسم Dart صحيح (snake_case مُشتق تلقائيًا)، `lib/main.dart` يهيّئ Supabase،
  `lib/app/` بصنف تطبيق باسم PascalCase مُشتق، بنية `features/data/domain/presentation`، اختبار widget أساسي.
- **React+Vite**: `package.json` باسم npm صحيح (kebab-case)، `vite.config.ts`، `tsconfig.json`،
  عميل Supabase موحّد في `src/lib/supabase.ts`، بنية `features/api/`، صفحة بداية تعمل فعليًا.
- **الحماية**: التوليد لا يستبدل أي ملف موجود مسبقًا (no-clobber) — آمن للاستخدام على مشروع قائم جزئيًا،
  وسيُعلمك إن تجاهل ملفات موجودة.
- **الاشتقاق التلقائي للمعرّفات**: تكتب اسم المشروع بالعربية أو الإنجليزية بحرية، والأداة تشتق تلقائيًا
  معرّف Dart (`snake_case`) ومعرّف npm (`kebab-case`) واسم الصنف (`PascalCase`) — أو أدخل معرّفًا يدويًا إن أردت.
- **نمط `generic`**: لا يملك `scaffold/` عمدًا — الحزمة التقنية غير محددة، فلا معنى لتوليد كود.

## إضافة نمط تقني جديد (مثلًا: Node.js API)
1. أنشئ `profiles/node-api/docs/ai/` — ضع فيه فقط الملفات المختلفة عن `generic`
   (عادة: TECH_STACK.md, PROJECT_STRUCTURE.md, CODING_CONVENTIONS.md, ENVIRONMENT.md).
2. اختياريًا، أنشئ `profiles/node-api/scaffold/` بهيكل كود جاهز (مثل `package.json`, `src/index.ts`)
   — استخدم `{{SLUG_KEBAB}}` أو `{{SLUG_SNAKE}}` و`{{CLASS_NAME}}` و`{{PROJECT_NAME}}` كمتغيرات جاهزة
   دون أي تعديل على `substitute.py`.
3. أضف خيار النمط الجديد في `generate.sh` (قسم `case "$PROFILE_CHOICE"`).
4. ارفع رقم إصدار المصنع في `VERSION` (MINOR — انظر UPDATE_POLICY.md).

## إضافة متغير {{TOKEN}} جديد
1. أضف المفتاح في `tokens = {...}` داخل `substitute.py`.
2. استخدم `{{TOKEN_NAME}}` في أي ملف `.md` داخل `profiles/`.
3. إن احتاج المتغير إدخالًا من المستخدم، أضف `read -rp` مقابلًا في `generate.sh` ومرّره
   ضمن `config` في نفس الملف.

## العلاقة بالحوكمة العامة (Drive) و`workspace_manager`
هذا المصنع مصدر حقيقة **لبنية التوثيق فقط** (كيف تبدو `docs/ai` لأي مشروع جديد).
هو ليس بديلاً عن الحوكمة الاستراتيجية على Drive، ولا عن `TASKS.md`/`DECISIONS.md` الفعليين
داخل كل مشروع بعد التوليد — تلك تبقى مسؤولية كل مشروع بمجرد أن يُنشأ.
راجع `UPDATE_POLICY.md` لفهم حدود الأتمتة الحالية عن قصد.
