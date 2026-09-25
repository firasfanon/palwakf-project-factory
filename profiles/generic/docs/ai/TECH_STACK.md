# الحزمة التقنية

## اللغات
- [TypeScript 5.x] — [لماذا]
- [SQL] — [لماذا]

## الواجهة (Frontend)
- الإطار: [React 18 / Next.js 14]
- إدارة الحالة: [Zustand / Redux Toolkit / React Query]
- التنسيق: [Tailwind CSS / CSS Modules]
- مكونات UI: [shadcn/ui / MUI / مخصص]
- النماذج: [React Hook Form + Zod]
- التوجيه: [React Router / Next App Router]
- البناء: [Vite / Next]
- السبب: [لماذا اخترنا هذه]

## الخلفية (Backend)
- Runtime: [Node.js 20]
- الإطار: [Express / Fastify / NestJS]
- ORM: [Prisma / Drizzle / TypeORM]
- المصادقة: [JWT / NextAuth / Clerk]
- المهام الخلفية: [BullMQ / ...]
- السبب: [لماذا]

## قاعدة البيانات
- الأساسية: [PostgreSQL 16]
- الكاش: [Redis 7]
- البحث: [Postgres FTS / Meilisearch]
- السبب: [لماذا]

## الأدوات
- Package manager: [pnpm]
- Bundler: [Vite / Turbopack]
- Linter: [ESLint]
- Formatter: [Prettier]
- اختبارات: [Vitest + Playwright]
- CI: [GitHub Actions]
- المراقبة: [Sentry / Logtail]

## الاستضافة
- الواجهة: [Vercel]
- الخلفية: [Railway / Fly.io]
- قاعدة البيانات: [Neon / Supabase]
- التخزين: [S3 / R2]

## المكتبات المسموحة
| المكتبة | الاستخدام | ملاحظات |
|---|---|---|
| zod | التحقق من المدخلات | إلزامي |
| date-fns | التواريخ | لا تستخدم moment |
| lodash-es | أدوات | عند الضرورة فقط |

## المكتبات الممنوعة
- [moment.js] — ثقيل ومهمل.
- [jQuery] — لا حاجة.
- [أي مكتبة UI ضخمة بدون موافقة].

## الإصدارات
- Node: >=20
- pnpm: >=9
- TypeScript: 5.4+

## قواعد الترقية
- لا ترفع إصدارًا رئيسيًا بدون ADR.
- ثبّت الإصدارات في lockfile.
- راجع التغييرات Breaking قبل الترقية.