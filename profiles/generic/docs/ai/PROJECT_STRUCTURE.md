# بنية المشروع

## الشجرة العامة
```text
project-root/
├── docs/
│   └── ai/                  # ملفات السياق للذكاء الاصطناعي
├── src/
│   ├── app/                 # نقاط الدخول والصفحات
│   ├── components/          # مكونات قابلة لإعادة الاستخدام
│   ├── features/            # وحدات حسب الميزة
│   ├── hooks/               # React hooks
│   ├── lib/                 # أدوات مساعدة
│   ├── services/            # الاتصال بالـ API
│   ├── store/               # إدارة الحالة
│   ├── types/               # الأنواع المشتركة
│   ├── utils/               # دوال مساعدة صغيرة
│   └── styles/              # الأنماط العامة
├── server/                  # الخلفية (إن وُجدت)
│   ├── routes/
│   ├── controllers/
│   ├── services/
│   ├── models/
│   ├── middlewares/
│   └── utils/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── scripts/                 # سكربتات مساعدة
├── public/                  # ملفات ثابتة
├── prisma/ أو drizzle/      # قاعدة البيانات
├── .env.example
├── package.json
└── README.md