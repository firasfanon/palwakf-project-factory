# سجل التغييرات (Changelog)

يوثّق هذا الملف كل تغيير جوهري في قوالب `palwakf-project-factory` عبر إصداراتها،
وفق سياسة الترقيم في `UPDATE_POLICY.md` (PATCH / MINOR / MAJOR).

## [Unreleased] — Prompt Maker consumer adapter (لم يُرقَّم VERSION بعد)

### أُضيف
- `consumer/adapter.py`: مستهلك `FACTORY_CONSUMER_SUBSET_V1` (Blueprint 1.1) بخمس نتائج مجمّدة، توليد حقيقي غير تفاعلي
  عند `MATERIALIZATION_READY` فقط، no-clobber، تهريب حسب صيغة الملف، وprovenance لكل مخرج.
- `consumer/pin/` + `tests/fixtures/prompt-maker/`: نسخ مثبّتة (SHA-256) من عقد Prompt Maker commit `f659f92d` — ليست سلطة عقد.
- `tests/test_consumer_adapter.py`: 38 اختبارًا (مصفوفة fixtures، pin، no-clobber، injection، secret residue، تطابق `generate.sh` القديم مع baseline).
- `.gitattributes` لتثبيت LF على الملفات المثبّتة.

### تغيّر
- `substitute.py`: استُخرجت `build_tokens()` دون تغيير السلوك (يُثبته اختبار التكافؤ).

### حدود معروفة
- لم يُتحقق من `npm install/build/test` للمشروع المولَّد (سجل npm محجوب 403 في بيئة التطوير)؛ فُحص فقط بناء TypeScript النحوي.

## [1.1.0] — إضافة توليد هيكل الكود (Scaffold)

### أُضيف
- مجلد `scaffold/` لكل نمط تقني (`flutter-supabase`, `react-vite-supabase`) يحتوي هيكل كود
  حقيقي يعمل: `pubspec.yaml`/`main.dart`/`app.dart` واختبار widget لـ Flutter، و`package.json`/
  `vite.config.ts`/`App.tsx`/عميل Supabase موحّد لـ React.
- اشتقاق تلقائي للمعرّفات البرمجية من اسم المشروع: `SLUG_SNAKE` (Dart)، `SLUG_KEBAB` (npm)،
  `CLASS_NAME` (PascalCase) — مع إمكانية إدخال معرّف يدوي.
- حماية **no-clobber** عند توليد هيكل الكود: لا يُستبدَل أي ملف موجود مسبقًا في مجلد الإخراج.
- سؤال تفاعلي جديد في `generate.sh`: "هل تريد أيضًا توليد هيكل الكود الأساسي؟".
- عمود "هيكل الكود" في `PROJECTS_REGISTRY.md`.

### تغيّر
- `substitute.py`: كان يستبدل المتغيرات في ملفات `.md` فقط، أصبح يعمل على أي ملف نصي
  (yaml, json, dart, ts/tsx, html...) مع تجاهل آمن للملفات الثنائية.
- `generate.sh`: أعيدت هيكلته ليجمع كل عمليات النسخ (docs/ai + scaffold) قبل تشغيل الاستبدال
  مرة واحدة على كامل مجلد الإخراج بدل تشغيله على `docs/ai` فقط.

### التوافق
لا يوجد كسر توافق — المشاريع المُولَّدة بالإصدار 1.0.0 تبقى صالحة كما هي؛ هذا الإصدار
يضيف قدرة اختيارية جديدة فقط. لذلك رُقِّم **MINOR** وليس **MAJOR**.

## [1.0.0] — الإصدار الأول

### أُضيف
- ثلاثة أنماط تقنية: `generic`، `flutter-supabase`، `react-vite-supabase`.
- `generate.sh`: أداة توليد تفاعلية لحزمة `docs/ai` الكاملة (23 ملفًا) مع استبدال متغيرات
  `{{TOKEN}}` أساسية (اسم المشروع، النوع، الحالة، الهدف، الأنظمة المرتبطة...).
- `substitute.py`: محرك استبدال يعمل على ملفات `.md` فقط.
- `PROJECTS_REGISTRY.md`: سجل مركزي يتحدّث تلقائيًا مع كل توليد.
- `UPDATE_POLICY.md`: سياسة ترقيم الإصدارات وآلية تحديث المشاريع القائمة يدويًا.
