// app.js — Davomat PWA v2 (yangi dizayn: nav, qidiruv, stat-kartochkalar, dark mode)
"use strict";

const API = ""; // shu domenning o'zi (mobile_api xizmat qiladi)
const $ = (s, r = document) => r.querySelector(s);

// ─────────── holat ───────────
const store = {
  get token() { return localStorage.getItem("tok") || ""; },
  set token(v) { v ? localStorage.setItem("tok", v) : localStorage.removeItem("tok"); },
  get role() { return localStorage.getItem("role") || ""; },
  set role(v) { localStorage.setItem("role", v || ""); },
  get name() { return localStorage.getItem("name") || ""; },
  set name(v) { localStorage.setItem("name", v || ""); },
  get lang() { return localStorage.getItem("lang") || "uz"; },
  set lang(v) { localStorage.setItem("lang", v); },
  get theme() { return localStorage.getItem("theme") || "light"; },
  set theme(v) { localStorage.setItem("theme", v); },
  get card() { return localStorage.getItem("card") || ""; },
  set card(v) { localStorage.setItem("card", v || ""); },
  get photo() { return localStorage.getItem("photo") || ""; },
  set photo(v) { v ? localStorage.setItem("photo", v) : localStorage.removeItem("photo"); },
  get viewAll() { return localStorage.getItem("va") || ""; },
  set viewAll(v) { v ? localStorage.setItem("va", v) : localStorage.removeItem("va"); },
};
const canViewAll = () => store.role === "hr" || store.role === "director" || store.role === "super_admin" || store.viewAll === "1";
// super_admin — HR'ning barcha huquqlariga ega (+ kirish/chiqishni tuzatish)
const isAdminRole = () => store.role === "hr" || store.role === "super_admin";

function applyTheme() {
  const dark = store.theme === "dark";
  document.body.classList.toggle("dark", dark);
  // Sahifa foni (html) — zoom/overscroll chetlarida oq ko'rinmasin
  document.documentElement.style.background = dark ? "#0D1B2A" : "#EEF2F6";
}
applyTheme();

// ─────────── tarjimalar ───────────
const T = {
  uz: {
    appName: "Davomat", agency: (window.ORG && window.ORG.name) || "Milliy malaka tizimini rivojlantirish instituti",
    signin: "Kirish", loginHint: "JSHSHIR va parolingizni kiriting",
    login: "JSHSHIR (14 raqam)", password: "Parol", enter: "Kirish",
    wrong: "Login yoki parol noto'g'ri", fillAll: "Login va parolni kiriting",
    changeTitle: "Parolni o'zgartiring", changeHint: "Xavfsizlik uchun yangi parol o'rnating",
    newPass: "Yangi parol", newPass2: "Parolni takrorlang", save: "Saqlash",
    passShort: "Parol kamida 6 belgi", passMismatch: "Parollar mos emas",
    pwBtn: "Parolni o'zgartirish", pwSaved: "Parol o'zgartirildi ✓", pwFail: "Parol o'zgartirilmadi",
    today: "Bugun", monthly: "Oylik statistika",
    st_ishda: "Ishdasiz", st_tushlikda: "Tushlik tanaffusi", st_chiqib: "Chiqib ketdingiz",
    st_yoq: "Belgilanmagan", st_kelmagan: "Bugun belgilanmagan",
    firstIn: "Birinchi kirish", noEvents: "Bugun harakat yo'q",
    m_hours: "Ish soati", m_days: "Ish kunlari", m_late: "Kechikish", m_absent: "Kelmagan",
    rankTitle: "Reyting o'rningiz", rankHours: "ish soatlari bo'yicha", rankLate: "kechikish bo'yicha",
    rankOutOf: "dan", rankNone: "Hozircha reyting yo'q",
    rankAll: "Umumiy reyting", rankTap: "Barchani ko'rish ›", rankMe: "Siz",
    annTitle: "E'lon",
    daysTitle: "Kunlik davomat", daysTap: "Kunlar bo'yicha ko'rish ›",
    daysIn: "kirdi", daysOut: "chiqdi", daysNone: "Bu oyda ma'lumot yo'q",
    daysLoad: "Yuklanmoqda…", daysErr: "Ma'lumot olinmadi",
    monthPick: "Oy", ratBuilding: "Bu oy hisoblanmoqda… biroz kuting",
    calOk: "Ishlagan",
    admSurvey: "So'rovnoma", svLink: "Ovoz berish havolasi", svNew: "Yangi so'rovnoma",
    svTitle: "So'rovnoma nomi", svQuestion: "Savol (ixtiyoriy)", svCreate: "Yaratish",
    svOpen: "Ochiq", svClosed: "Yakunlangan", svClose: "Yakunlash", svReopen: "Qayta ochish",
    svVotes: "ovoz", svTurnout: "ishtirok", svNone: "Hali so'rovnoma yaratilmagan",
    svResult: "Natija", svNotVoted: "Ovoz bermaganlar", svWho: "Kim kimga ovoz berdi",
    svCloseAsk: "So'rovnomani yakunlaysizmi? Natija barcha xodimlarga e'lon qilinadi.",
    svDelAsk: "So'rovnoma va barcha ovozlar o'chiriladi. Davom etasizmi?",
    svCopy: "Havolani nusxalash", svCopied: "Nusxalandi",
    svInfo: "nomzod · ovoz berish huquqiga ega",
    svCand: "nomzod", svVoters: "ovoz beruvchi",
    svWord: "Word", svQuestions: "savol", svAnswers: "javob",
    svOwnLink: "Havola", svList: "ro'yxat", svAll: "Barcha so'rovnomalar",
    admEmpOut: "Xodimni chiqarish",
    empOutHint: "Ishdan bo'shagan xodimni tizimdan butunlay chiqaradi: dashboard, reyting, kechikkanlar, so'rovnoma — hammasidan yo'qoladi. Hisobi ham o'chiriladi va qayta yaratilmaydi.",
    empOutFind: "Xodimni tanlang yoki JSHSHIR kiriting",
    empOutBtn: "Tizimdan chiqarish",
    empOutAsk: "butunlay chiqariladi. Davom etasizmi?",
    empOutWarn: "Diqqat: o'tgan oylar hisoboti va so'rovnoma ovozlari saqlanib qoladi, lekin xodim barcha ro'yxatlardan yo'qoladi. Bu amalni ortga qaytarib bo'lmaydi.",
    empOutOk: "Tizimdan chiqarildi",
    admRating: "Reyting", dayUnit: "kun", admRatingHint: "Oylik reyting — ish soatlari bo'yicha. Qatorni bosib xodim kunlarini ko'rish mumkin.",
    admLateList: "Kechikuvchilar", admLateHint: "Oylik kechikish reytingi — eng ko'p kechikkandan boshlab.",
    hShort: "soat", mShort: "daq",
    lateTimes: "marta", lateExcused: "uzrli", lateBy: "kech", lateTapHint: "Xodim ustiga bosing — qaysi kuni nechida kelgani ko'rinadi.", lateNoneMon: "Bu oyda kechikkan yo'q 👍",
    lateTadbirHint: "🎤 tugmasi — o'sha kuni xodim tadbirda bo'lgan bo'lsa belgilang. Kechikish bekor qilinadi va to'liq ish kuni (8 soat) yoziladi.",
    lateTadbirAsk: "shu kun tadbirda deb belgilansinmi?", lateTadbirOk: "Tadbirda deb belgilandi ✓",
    calTadbirBtn: "Tadbirda deb belgilash", calTadbir: "Tadbirda",
    yqTitle: "Yo'qlama", yqHint: "Tadbir nomini yozing, xodimlarni belgilang, hujjatni yuklab oling.",
    yqName: "Tadbir nomi", yqDate: "Sana", yqTime: "Vaqti (ixtiyoriy)", yqPlace: "Joyi (ixtiyoriy)",
    yqOpen: "Ro'yxatni ochish", yqNew: "Yangi yo'qlama", yqSave: "Saqlash",
    yqAll: "Jami", yqYes: "Bor", yqNo: "Yo'q", yqSaved: "Saqlandi ✓",
    yqNameShort: "Tadbir nomini yozing (kamida 3 belgi)",
    yqDocx: "Word (.docx) yuklab olish", yqPdf: "PDF yuklab olish",
    yqPrev: "Oldingi yo'qlamalar", yqNone: "Hali yo'qlama o'tkazilmagan",
    yqDel: "O'chirish", yqDelAsk: "Bu yo'qlama o'chirilsinmi?",
    yqAttended: "Qatnashdi", yqMissed: "Qatnashmadi",
    yqReasons: "Qatnashmaganlar javobi",
    yqConductor: "Yo'qlamani o'tkazdi", yqConductorHint: "Yo'qlamani o'tkazgan xodimni tanlang va imzolatib oling. Imzo hujjatga tushadi.",
    yqSignBtn: "Tanlash va imzolash", yqSignedOk: "Imzolandi ✓",
    yqWasThere: "Tadbirda qatnashdingiz", yqNoAction: "Yo'qlamada belgilangansiz. Hech qanday amal talab etilmaydi.",
    yqWhyNot: "Nima uchun qatnashmadingiz?", yqWhyDesc: "Yo'qlamada qatnashmagan deb belgilangansiz. Sababini yozing.",
    yqWhyPh: "Sababini yozing…", yqAnswerSent: "Javobingiz yuborildi",
    yqHrReview: "Kadrlar bo'limi ko'rib chiqmoqda.",
    explSign: "Xodim imzosi", explPdfOpen: "Imzolangan PDF ni ochish",
    expKindExit: "Erta chiqish",
    updated: "Yangilandi",
    c_inside: "Ishda", c_lunch: "Tushlik", c_out: "Chiqqan", c_late: "Kech", c_absent: "Kelmagan",
    c_interns: "Amaliyotchilar", c_safari: "Xizmat safari", c_tatil: "Mehnat ta'tili",
    exFrom2: "dan", exTo2: "gacha", excusedTag: "Sababli",
    nobody: "Hech kim yo'q", loading: "Yuklanmoqda…",
    expAsk: "So'rash", expAsked: "So'raldi", expDone: "✓ Javob berdi",
    expTitle: "Tushuntirish xati", expNeed: "Sizdan tushuntirish so'raldi",
    expKindLate: "Kechikish", expKindAbsent: "Kelmaslik", expKindExit: "Binoni tark etish",
    expPlaceholder: "Sababni yozing (kamida 10 belgi)…",
    expSend: "Yuborish", expSent: "Tushuntirish yuborildi ✓",
    expShort: "Kamida 10 belgi yozing", expFail: "Yuborilmadi, qayta urinib ko'ring",
    expAskFail: "So'rov yuborilmadi",
    expSentAt: "Yuborilgan", expClose: "Yopish",
    expPdf: "PDF (imzolangan xat)", expWord: "Word (barcha xatlari)",
    expDelete: "🗑 O'chirish", expDeleteQ: "Tushuntirish butunlay o'chirilsinmi?",
    tlTitle: "Bugungi harakatlar", tlIn: "Kirish", tlOut: "Chiqish",
    navHome: "Bosh", navStaff: "Xodimlar", navExp: "Tushuntirish",
    searchPh: "Xodim qidirish…",
    cameAt: "{t} da keldi", leftAt: "{t} da chiqdi",
    expWait: "Kutilmoqda", noExp: "Tushuntirish so'rovlari yo'q",
    selfTitle: "Sabab yozish", selfHint: "Kechikish yoki kelmaslik sababini oldindan HR ga yozib qo'ying (masalan: ertaga kechikaman)",
    selfSent: "Sabab yuborildi ✓", selfWrote: "✍️ O'zi yozdi",
    sigLabel: "Imzo", sigClear: "Tozalash", sigNeed: "Imzo chizing",
    cancelReq: "Qaytarib olish", cancelConfirm: "So'rov qaytarib olinsinmi?",
    allStaff: "Barcha xodimlar", expListTitle: "Tushuntirishlar",
    navAdmin: "Boshqaruv", admTitle: "HR Boshqaruv",
    navRep: "Hisobot", repTitle: "Hisobotlar",
    admBroadcast: "Xabar yuborish", admBroadcastHint: "Barcha xodimlarga Telegram orqali e'lon yuboriladi",
    admExempt: "Ta'til & Safari", admReason: "Izoh qo'shish", admExitReason: "Chiqqanlar izohi",
    admLate: "Kechikish uzrli", admHolidays: "Bayramlar", admHidden: "Dashboard ko'rinish",
    admWorktime: "Ish vaqti", admExpl: "Tushuntirishlar arxivi", admMonitor: "Monitoring",
    admAdd: "Qo'shish", admRemove: "O'chirish", admSave: "Saqlash", admSend: "Yuborish",
    admConfirmSend: "Xabar {n} kishiga yuborilsinmi?", admSentRes: "Yuborildi: {s} · Xato: {f}",
    admPickEmp: "Xodimni qidiring…", admNote: "Izoh (ixtiyoriy)", admActive: "Faol", admUpcoming: "Kelgusi",
    admEmptyList: "Ro'yxat bo'sh", admDone: "Bajarildi ✓", admFail: "Xatolik, qayta urinib ko'ring",
    admTypeRuxsat: "🏖 Mehnat ta'tili", admTypeSafari: "✈️ Safari", admTypeTadbir: "🎤 Tadbir",
    admTadbirHint: "Tadbir/seminarda bo'lgan xodimlarni belgilang. Ular o'sha kuni kechikkan hisoblanmaydi va to'liq ish kuni (8 soat) yoziladi.",
    admPickMany: "Xodimlarni tanlang (bir nechta)", admSelected: "Tanlangan",
    admSearchEmp: "Qidirish…", admPickNone: "Hech kim tanlanmadi",
    admFrom: "Boshlanish", admTo: "Tugash", admHolName: "Bayram nomi",
    admMonOn: "▶️ Yoqish", admMonOff: "⏸ To'xtatish", admMonState: "Holat",
    admOnn: "✅ yoqilgan", admOff: "⏸ o'chirilgan", admLastCheck: "Oxirgi tekshiruv",
    admNvrRefresh: "🔄 NVR'dan yangilash", admNvrRefreshing: "Yangilanmoqda…",
    admNvrRefreshOk: "Yangilandi", admNvrRefreshFail: "Xato",
    admAttEdit: "Kirish/chiqishni tuzatish",
    admAttEditHint: "Xodim va sanani tanlang — kerakli kirish/chiqish vaqtini kiriting. Bo'sh qoldirsangiz, o'sha maydon bo'yicha tuzatish o'chiriladi.",
    admAttIn: "Kirish", admAttOut: "Chiqish", admAttActual: "Haqiqiy",
    admAttClear: "Tuzatishni o'chirish",
    admExcused: "✅ Uzrli", admNotExcused: "Uzrli deb belgilash", admToggleHide: "Yashirish", admToggleShow: "Ko'rsatish",
    admReasonHint: "Bugungi kun uchun qisqa izoh (dashboardda ko'rinadi). Bo'sh saqlansa — o'chiriladi.",
    admWtHint: "Xodim uchun maxsus ish boshlanish vaqti (masalan 13:00). Bo'sh saqlansa — o'chiriladi.",
    admPending: "🔴 Kutilmoqda", admReviewed: "✅ Ko'rilgan", admMarkOk: "✅ Ko'rildi", admReopen: "🔄 Qayta ochish",
    admPhoto: "Rasm yuklash", admOlim: "Olimlar (PhD/DSc)",
    admPhotoPick: "📷 Rasm tanlash / suratga olish", admPhotoSaved: "Rasm saqlandi ✓",
    admPhotoApi: "🔄 Rasmni tortish", admPhotoApiOk: "Rasm yuklandi ✓",
    admPhotoApiNo: "Topilmadi — qo'lda yuklang",
    admCurrentPhoto: "Joriy rasm", admOlimList: "Belgilangan olimlar", admNoOlim: "Hozircha belgilanmagan",
    admPickFirst: "Avval xodimni tanlang", admDegNone: "Yo'q",
    admInterns: "Amaliyotchilar (faol)", admInternActive: "Faol", admInternInactive: "Faol emas",
    admInternHint: "«Faol emas» belgilanganlar dashboard va ilovada ko'rinmaydi.",
    exitTitle: "Binoni tark etish", exitAt: "Chiqqan vaqt",
    exitPromptMsg: "Siz ish vaqtida binoni 10 daqiqadan ortiq tark etdingiz. Sababini yozing:",
    exitPh: "Masalan: bankka chiqdim / do'konga chiqdim",
    exitSend: "Yuborish", exitSent: "Sabab yuborildi ✓", exitShort: "Kamida 3 belgi",
    exitMy: "Chiqish izohim", exitPending: "Kutilmoqda", exitAccepted: "Qabul qilindi", exitRejected: "Sababsiz — tushuntirish so'raldi",
    admExitReasons: "Chiqish izohlari",
    exitAccept: "✅ Qabul qilish", exitShow: "📌 Chiqish izohiga qo'shish", exitReject: "❌ Sababsiz (tushuntirish so'rash)",
    exitNone: "Chiqish izohlari yo'q", exitNoteHint: "Izoh (ixtiyoriy)…",
    admResetPw: "Parol tiklash", admResetBtn: "Parolni tiklash",
    admResetHint: "Xodim parolini unutsa — tiklang. Vaqtinchalik parol beriladi; xodim birinchi kirishда o'zgartiradi.",
    admResetDone: "Yangi vaqtinchalik parol:",
    admNewAcc: "Yangi hisob", admNewAccBtn: "Hisob yaratish",
    admNewAccHint: "Yangi xodimga hisob oching. JSHSHIR (PINFL) kiriting — boshlang'ich parol raqamning oxirgi 6 tasi bo'ladi; xodim birinchi kirishда o'zgartiradi. (Odatda tizim yangi xodimларга avtomatik hisob ochadi — bu qo'lда ochish uchun.)",
    admNewAccPin: "JSHSHIR (PINFL, 14 raqam)", admNewAccName: "Ism (ixtiyoriy — bo'sh qoldirsa avtomatik topiladi)",
    admNewAccDone: "Hisob yaratildi. Login:", admNewAccPass: "Parol:",
    admNewAccExists: "Bu JSHSHIR uchun hisob allaqachon mavjud.",
    admEmpAdd: "Xodim qo'shish",
    admEmpAddHint: "Yangi xodimni ro'yxatga qo'shing. Ma'lumotlar users.xlsx ga yoziladi va hisob avtomatik ochiladi. Rasmni keyin \"Rasm yuklash\"дан yuklaysiz.",
    empFam: "Familiya", empIsm: "Ism", empSharif: "Sharif (ota ismi)",
    empPin: "JSHSHIR (PINFL, 14 raqam)", empRole: "Lavozim", empCat: "Turkum",
    empWork: "Ish boshlanishi (masalan 09:00)", empTg: "Telegram ID (ixtiyoriy)",
    empRoleEmp: "Oddiy xodim", empRoleHr: "HR / Rahbariyat", empRoleDir: "Direktor",
    empCatOddiy: "Oddiy", empCatHaydovchi: "Haydovchi", empCatRahbar: "Rahbar", empCatMasofaviy: "Masofaviy",
    empAddBtn: "Qo'shish", empAddDone: "Xodim qo'shildi ✓",
    empAddReq: "Familiya, ism va JSHSHIR to'ldiring",
    empPhotoOk: "📷 Rasm yuklandi", empPhotoNo: "📷 Rasmni Boshqaruv → \"Rasm yuklash\" orqali qo'shing",
    admAccounts: "Hisoblar", admAccountsHint: "Barcha hisoblar. Qidiring va keraksizини (xato ochilgan / ishдан ketган) o'chiring.",
    accSearch: "Ism yoki JSHSHIR bo'yicha qidirish…", accDelete: "O'chirish",
    accDelConfirm: "Bu hisob o'chirilsinmi? Xodim endi kira olmaydi.", accDeleted: "Hisob o'chirildi",
    accNone: "Hisob topilmadi", accInactive: "Faol emas",
    navBron: "Bron", navAriza: "Ariza", arzTitle: "Arizalarim", arzReviewTitle: "Arizalar",
    arzNew: "Yangi ariza", arzType: "Ariza turi",
    arzT_tatil: "Mehnat ta'tili", arzT_ruxsat: "Ruxsat", arzT_moddiy: "Moddiy yordam", arzT_erkin: "Erkin ariza",
    arzTextPh: "Arizangizni yozing…", arzFrom: "Boshlanish", arzTo: "Tugash",
    arzSend: "Yuborish", arzSent: "Ariza yuborildi ✓", arzShort: "Matn kamida 5 belgi",
    arzNone: "Arizalar yo'q", arzMyNone: "Sizda ariza yo'q",
    arzPending: "Kutilmoqda", arzApproved: "Qabul qilindi", arzRejected: "Rad etildi",
    arzApprove: "✅ Qabul qilish", arzReject: "❌ Rad etish", arzReopen: "🔄 Qayta ochish",
    arzResponse: "Javob / izoh (ixtiyoriy)…", arzResponseLbl: "Rahbariyat javobi",
    arzCancelQ: "Ariza qaytarib olinsinmi?",
    arzDelete: "🗑 O'chirish", arzDeleteQ: "Ariza butunlay o'chirilsinmi?",
    months: ["yanvar","fevral","mart","aprel","may","iyun","iyul","avgust","sentyabr","oktyabr","noyabr","dekabr"],
    days: ["yakshanba","dushanba","seshanba","chorshanba","payshanba","juma","shanba"],
  },
  ru: {
    appName: "Учёт", agency: (window.ORG && (window.ORG.name_ru || window.ORG.name)) || "Институт развития национальной системы квалификаций",
    signin: "Вход", loginHint: "Введите ПИНФЛ и пароль",
    login: "ПИНФЛ (14 цифр)", password: "Пароль", enter: "Войти",
    wrong: "Неверный логин или пароль", fillAll: "Введите логин и пароль",
    changeTitle: "Смените пароль", changeHint: "Установите новый пароль для безопасности",
    newPass: "Новый пароль", newPass2: "Повторите пароль", save: "Сохранить",
    passShort: "Пароль минимум 6 символов", passMismatch: "Пароли не совпадают",
    pwBtn: "Сменить пароль", pwSaved: "Пароль изменён ✓", pwFail: "Пароль не изменён",
    today: "Сегодня", monthly: "Статистика за месяц",
    st_ishda: "Вы на работе", st_tushlikda: "Обеденный перерыв", st_chiqib: "Вы ушли",
    st_yoq: "Нет отметки", st_kelmagan: "Сегодня нет отметки",
    firstIn: "Первый вход", noEvents: "Сегодня событий нет",
    m_hours: "Часы работы", m_days: "Рабочих дней", m_late: "Опоздания", m_absent: "Отсутствия",
    rankTitle: "Ваше место в рейтинге", rankHours: "по часам работы", rankLate: "по опозданиям",
    rankOutOf: "из", rankNone: "Пока нет рейтинга",
    rankAll: "Общий рейтинг", rankTap: "Показать всех ›", rankMe: "Вы",
    annTitle: "Объявление",
    daysTitle: "Посещаемость по дням", daysTap: "Смотреть по дням ›",
    daysIn: "вход", daysOut: "выход", daysNone: "За этот месяц нет данных",
    daysLoad: "Загрузка…", daysErr: "Не удалось получить данные",
    monthPick: "Месяц", ratBuilding: "Месяц рассчитывается… подождите",
    calOk: "Отработано",
    admSurvey: "Опрос", svLink: "Ссылка для голосования", svNew: "Новый опрос",
    svTitle: "Название опроса", svQuestion: "Вопрос (необязательно)", svCreate: "Создать",
    svOpen: "Открыт", svClosed: "Завершён", svClose: "Завершить", svReopen: "Открыть снова",
    svVotes: "голосов", svTurnout: "участие", svNone: "Опросов пока нет",
    svResult: "Результат", svNotVoted: "Не проголосовали", svWho: "Кто за кого голосовал",
    svCloseAsk: "Завершить опрос? Результат будет объявлен всем сотрудникам.",
    svDelAsk: "Опрос и все голоса будут удалены. Продолжить?",
    svCopy: "Копировать ссылку", svCopied: "Скопировано",
    svInfo: "кандидатов · имеют право голоса",
    svCand: "кандидатов", svVoters: "голосующих",
    svWord: "Word", svQuestions: "вопросов", svAnswers: "ответов",
    svOwnLink: "Ссылка", svList: "список", svAll: "Все опросы",
    admEmpOut: "Удалить сотрудника",
    empOutHint: "Полностью удаляет уволенного сотрудника: дашборд, рейтинг, опоздания, опросы — отовсюду. Учётная запись тоже удаляется.",
    empOutFind: "Выберите сотрудника или введите ПИНФЛ",
    empOutBtn: "Удалить из системы",
    empOutAsk: "будет полностью удалён. Продолжить?",
    empOutWarn: "Внимание: отчёты прошлых месяцев и голоса в опросах сохранятся, но сотрудник исчезнет из всех списков. Действие необратимо.",
    empOutOk: "Удалён из системы",
    admRating: "Рейтинг", dayUnit: "дн.", admRatingHint: "Месячный рейтинг по рабочим часам. Нажмите строку, чтобы увидеть дни сотрудника.",
    admLateList: "Опоздавшие", admLateHint: "Месячный рейтинг опозданий — начиная с самых частых.",
    hShort: "ч", mShort: "мин",
    lateTimes: "раз", lateExcused: "уважит.", lateBy: "опозд.", lateTapHint: "Нажмите на сотрудника — увидите день и время прихода.", lateNoneMon: "В этом месяце опозданий нет 👍",
    lateTadbirHint: "Кнопка 🎤 — отметьте, если в этот день сотрудник был на мероприятии. Опоздание снимается, засчитывается полный день (8 часов).",
    lateTadbirAsk: "отметить этот день как мероприятие?", lateTadbirOk: "Отмечено как мероприятие ✓",
    calTadbirBtn: "Отметить как мероприятие", calTadbir: "Мероприятие",
    yqTitle: "Перекличка", yqHint: "Введите название мероприятия, отметьте сотрудников, скачайте документ.",
    yqName: "Название мероприятия", yqDate: "Дата", yqTime: "Время (необязательно)", yqPlace: "Место (необязательно)",
    yqOpen: "Открыть список", yqNew: "Новая перекличка", yqSave: "Сохранить",
    yqAll: "Всего", yqYes: "Был", yqNo: "Не был", yqSaved: "Сохранено ✓",
    yqNameShort: "Введите название (мин. 3 символа)",
    yqDocx: "Скачать Word (.docx)", yqPdf: "Скачать PDF",
    yqPrev: "Предыдущие переклички", yqNone: "Перекличек пока нет",
    yqDel: "Удалить", yqDelAsk: "Удалить эту перекличку?",
    yqAttended: "Присутствовал", yqMissed: "Отсутствовал",
    yqReasons: "Ответы отсутствовавших",
    yqConductor: "Перекличку провёл", yqConductorHint: "Выберите сотрудника, проводившего перекличку, и подпишите. Подпись попадёт в документ.",
    yqSignBtn: "Выбрать и подписать", yqSignedOk: "Подписано ✓",
    yqWasThere: "Вы присутствовали на мероприятии", yqNoAction: "Вы отмечены в перекличке. Действий не требуется.",
    yqWhyNot: "Почему вы не присутствовали?", yqWhyDesc: "Вы отмечены как отсутствовавший. Укажите причину.",
    yqWhyPh: "Укажите причину…", yqAnswerSent: "Ваш ответ отправлен",
    yqHrReview: "Отдел кадров рассматривает.",
    explSign: "Подпись сотрудника", explPdfOpen: "Открыть подписанный PDF",
    expKindExit: "Ранний уход",
    updated: "Обновлено",
    c_inside: "На работе", c_lunch: "Обед", c_out: "Ушли", c_late: "Опозд.", c_absent: "Нет",
    c_interns: "Практиканты", c_safari: "Командировка", c_tatil: "Трудовой отпуск",
    exFrom2: "с", exTo2: "по", excusedTag: "Уважит.",
    nobody: "Никого нет", loading: "Загрузка…",
    expAsk: "Запросить", expAsked: "Запрошено", expDone: "✓ Ответил",
    expTitle: "Объяснительная", expNeed: "От вас запрошена объяснительная",
    expKindLate: "Опоздание", expKindAbsent: "Отсутствие", expKindExit: "Выход из здания",
    expPlaceholder: "Укажите причину (мин. 10 символов)…",
    expSend: "Отправить", expSent: "Объяснительная отправлена ✓",
    expShort: "Минимум 10 символов", expFail: "Не отправлено, попробуйте снова",
    expAskFail: "Запрос не отправлен",
    expSentAt: "Отправлено", expClose: "Закрыть",
    expPdf: "PDF (подписанное письмо)", expWord: "Word (все письма)",
    expDelete: "🗑 Удалить", expDeleteQ: "Удалить объяснительную полностью?",
    tlTitle: "Движения за сегодня", tlIn: "Вход", tlOut: "Выход",
    navHome: "Главная", navStaff: "Сотрудники", navExp: "Объяснит.",
    searchPh: "Поиск сотрудника…",
    cameAt: "пришёл в {t}", leftAt: "ушёл в {t}",
    expWait: "Ожидается", noExp: "Запросов на объяснительную нет",
    selfTitle: "Указать причину", selfHint: "Заранее сообщите HR о причине опоздания или отсутствия (например: завтра опоздаю)",
    selfSent: "Причина отправлена ✓", selfWrote: "✍️ Сам написал",
    sigLabel: "Подпись", sigClear: "Очистить", sigNeed: "Поставьте подпись",
    cancelReq: "Отозвать", cancelConfirm: "Отозвать запрос?",
    allStaff: "Все сотрудники", expListTitle: "Объяснительные",
    navAdmin: "Админ", admTitle: "Управление HR",
    navRep: "Отчёты", repTitle: "Отчёты",
    admBroadcast: "Рассылка", admBroadcastHint: "Объявление будет отправлено всем сотрудникам в Telegram",
    admExempt: "Отпуск & Командировки", admReason: "Добавить примечание", admExitReason: "Примечание ушедшим",
    admLate: "Опоздание уважит.", admHolidays: "Праздники", admHidden: "Видимость на дашборде",
    admWorktime: "Рабочее время", admExpl: "Архив объяснительных", admMonitor: "Мониторинг",
    admAdd: "Добавить", admRemove: "Удалить", admSave: "Сохранить", admSend: "Отправить",
    admConfirmSend: "Отправить сообщение {n} сотрудникам?", admSentRes: "Отправлено: {s} · Ошибки: {f}",
    admPickEmp: "Поиск сотрудника…", admNote: "Примечание (необязательно)", admActive: "Активные", admUpcoming: "Предстоящие",
    admEmptyList: "Список пуст", admDone: "Готово ✓", admFail: "Ошибка, попробуйте снова",
    admTypeRuxsat: "🏖 Трудовой отпуск", admTypeSafari: "✈️ Командировка", admTypeTadbir: "🎤 Мероприятие",
    admTadbirHint: "Отметьте сотрудников на мероприятии/семинаре. В этот день опоздание не считается, засчитывается полный рабочий день (8 часов).",
    admPickMany: "Выберите сотрудников (несколько)", admSelected: "Выбрано",
    admSearchEmp: "Поиск…", admPickNone: "Никто не выбран",
    admFrom: "Начало", admTo: "Конец", admHolName: "Название праздника",
    admMonOn: "▶️ Включить", admMonOff: "⏸ Остановить", admMonState: "Статус",
    admOnn: "✅ включён", admOff: "⏸ выключен", admLastCheck: "Последняя проверка",
    admNvrRefresh: "🔄 Обновить из NVR", admNvrRefreshing: "Обновление…",
    admNvrRefreshOk: "Обновлено", admNvrRefreshFail: "Ошибка",
    admAttEdit: "Исправить приход/уход",
    admAttEditHint: "Выберите сотрудника и дату — введите нужное время прихода/ухода. Если поле пустое, исправление по нему удаляется.",
    admAttIn: "Приход", admAttOut: "Уход", admAttActual: "Фактически",
    admAttClear: "Удалить исправление",
    admExcused: "✅ Уважит.", admNotExcused: "Отметить уважительным", admToggleHide: "Скрыть", admToggleShow: "Показать",
    admReasonHint: "Короткое примечание на сегодня (видно на дашборде). Пустое — удаляет.",
    admWtHint: "Особое время начала работы (напр. 13:00). Пустое — удаляет.",
    admPending: "🔴 Ожидает", admReviewed: "✅ Просмотрено", admMarkOk: "✅ Просмотрено", admReopen: "🔄 Переоткрыть",
    admPhoto: "Загрузить фото", admOlim: "Учёные (PhD/DSc)",
    admPhotoPick: "📷 Выбрать / снять фото", admPhotoSaved: "Фото сохранено ✓",
    admPhotoApi: "🔄 Загрузить фото", admPhotoApiOk: "Фото загружено ✓",
    admPhotoApiNo: "Не найдено — загрузите вручную",
    admCurrentPhoto: "Текущее фото", admOlimList: "Отмеченные учёные", admNoOlim: "Пока не отмечено",
    admPickFirst: "Сначала выберите сотрудника", admDegNone: "Нет",
    admInterns: "Практиканты (активные)", admInternActive: "Активен", admInternInactive: "Неактивен",
    admInternHint: "«Неактивные» не показываются на дашборде и в приложении.",
    exitTitle: "Выход из здания", exitAt: "Время выхода",
    exitPromptMsg: "Вы покинули здание более чем на 10 минут в рабочее время. Укажите причину:",
    exitPh: "Например: вышел в банк / в магазин",
    exitSend: "Отправить", exitSent: "Причина отправлена ✓", exitShort: "Минимум 3 символа",
    exitMy: "Моя причина выхода", exitPending: "Ожидает", exitAccepted: "Принято", exitRejected: "Без причины — запрошена объяснительная",
    admExitReasons: "Причины выхода",
    exitAccept: "✅ Принять", exitShow: "📌 Добавить в причины выхода", exitReject: "❌ Без причины (запросить объясн.)",
    exitNone: "Причин выхода нет", exitNoteHint: "Примечание (необязательно)…",
    admResetPw: "Сброс пароля", admResetBtn: "Сбросить пароль",
    admResetHint: "Если сотрудник забыл пароль — сбросьте. Выдаётся временный пароль; сотрудник сменит его при первом входе.",
    admResetDone: "Новый временный пароль:",
    navBron: "Бронь", navAriza: "Заявка", arzTitle: "Мои заявки", arzReviewTitle: "Заявки",
    arzNew: "Новая заявка", arzType: "Тип заявки",
    arzT_tatil: "Трудовой отпуск", arzT_ruxsat: "Разрешение", arzT_moddiy: "Мат. помощь", arzT_erkin: "Свободная заявка",
    arzTextPh: "Напишите заявку…", arzFrom: "Начало", arzTo: "Конец",
    arzSend: "Отправить", arzSent: "Заявка отправлена ✓", arzShort: "Минимум 5 символов",
    arzNone: "Заявок нет", arzMyNone: "У вас нет заявок",
    arzPending: "Ожидает", arzApproved: "Одобрено", arzRejected: "Отклонено",
    arzApprove: "✅ Одобрить", arzReject: "❌ Отклонить", arzReopen: "🔄 Переоткрыть",
    arzResponse: "Ответ / примечание…", arzResponseLbl: "Ответ руководства",
    arzCancelQ: "Отозвать заявку?",
    arzDelete: "🗑 Удалить", arzDeleteQ: "Удалить заявку полностью?",
    months: ["января","февраля","марта","апреля","мая","июня","июля","августа","сентября","октября","ноября","декабря"],
    days: ["воскресенье","понедельник","вторник","среда","четверг","пятница","суббота"],
  },
};
const t = (k) => (T[store.lang] && T[store.lang][k]) ?? T.uz[k] ?? k;

// ─────────── API ───────────
async function api(path, { method = "GET", body = null, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth && store.token) headers["Authorization"] = "Bearer " + store.token;
  const res = await fetch(API + path, {
    method, headers, body: body ? JSON.stringify(body) : null,
  });
  let data = null;
  try { data = await res.json(); } catch (e) {}
  if (res.status === 401) { store.token = ""; }
  return { status: res.status, data };
}

// ─────────── util ───────────
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, c =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const initials = (name) => {
  const p = String(name || "").trim().split(/\s+/);
  return ((p[0] || "")[0] || "?") + ((p[1] || "")[0] || "");
};
function avatar(row) {
  const p = row && (row.photo || row.photo_url || row.photo_file);
  const ini = esc(initials(row && (row.full_name || row.name)));
  if (p && /^https?:\/\//.test(p)) return `<img src="${esc(p)}" alt="" onerror="this.parentNode.textContent='${ini}'">`;
  if (p) return `<img src="photos/${esc(p)}" alt="" onerror="this.parentNode.textContent='${ini}'">`;
  return ini;
}
const timeShort = (s) => (s && s !== "-" ? String(s).slice(0, 5) : "");
const UZ_MON_SHORT = ["yan", "fev", "mar", "apr", "may", "iyun", "iyul", "avg", "sen", "okt", "noy", "dek"];
function fmtDayMon(d) {
  const m = String(d || "").match(/^(\d{4})-(\d{2})-(\d{2})/);
  return m ? `${parseInt(m[3], 10)}-${UZ_MON_SHORT[parseInt(m[2], 10) - 1]}` : (d || "");
}
function expKindName(k) {
  return k === "late" ? t("expKindLate") : (k === "exit" ? t("expKindExit") : t("expKindAbsent"));
}
function fmtName(s) {
  // ISM FAMILIYA → Ism Familiya; "o'g'li/qizi" kichik harfda qoladi
  const KEEP = { ogli: 1, ugli: 1, qizi: 1, kizi: 1 };
  return String(s || "").trim().split(/\s+/).map(w => {
    const lw = w.toLowerCase();
    const key = lw.replace(/[’'‘`ʻ]/g, "");
    if (KEEP[key]) return lw;
    return lw.charAt(0).toUpperCase() + lw.slice(1);
  }).join(" ");
}
function lateDelay(time, workStart) {
  const a = String(time || "").match(/^(\d{1,2}):(\d{2})/);
  const b = String(workStart || "").match(/^(\d{1,2}):(\d{2})/);
  if (!a || !b) return "";
  let m = (+a[1] * 60 + +a[2]) - (+b[1] * 60 + +b[2]);
  if (m <= 0) return "";
  const h = Math.floor(m / 60), mm = m % 60;
  return ((h ? h + " " + t("hShort") + " " : "") + (mm ? mm + " " + t("mShort") : "")).trim();
}
function shortName(s) {
  // Reyting uchun: faqat FAMILIYA va ISM ("Aliyev Sardor").
  // Sharif ("Baxtiyor o'g'li") tashlanadi — telefonda qatorga sig'sin.
  const parts = fmtName(s).split(/\s+/).filter(Boolean);
  return parts.slice(0, 2).join(" ") || fmtName(s);
}
function todayLine() {
  const d = new Date();
  return `${d.getDate()} ${t("months")[d.getMonth()]}, ${t("days")[d.getDay()]}`;
}
function toMin(hhmmss) {
  const m = String(hhmmss || "").match(/^(\d{1,2}):(\d{2})/);
  return m ? (+m[1]) * 60 + (+m[2]) : null;
}
function lateMinutes(emp) {
  // ish boshlanishiga nisbatan necha daqiqa kech kelgan
  if (!emp) return null;
  const a = toMin(emp.first_entry), b = toMin(emp.work_start);
  if (a == null || b == null) return null;
  const d = a - b;
  return d > 0 ? d : null;
}
function skeleton(n) {
  let h = "";
  for (let i = 0; i < (n || 6); i++)
    h += `<div class="sk"><div class="c shimmer"></div><div style="flex:1"><div class="l1 shimmer"></div><div class="l2 shimmer"></div></div></div>`;
  return `<div class="sec">${h}</div>`;
}

// ─────────── LOGIN ekrani ───────────
function viewLogin(errMsg) {
  document.body.classList.remove("app-shell", "wide-page");
  const app = $("#app");
  app.innerHTML = `
    <div class="auth">
      <div class="brand">
        <img class="logo-lg" src="logo.png" alt="">
        <div><h1>${t("appName")}</h1><p>${t("agency")}</p></div>
      </div>
      <div class="card">
        <h2>${t("signin")}</h2>
        <p class="sub">${t("loginHint")}</p>
        <div id="err"></div>
        <div class="field"><label>${t("login")}</label>
          <input id="lg" inputmode="numeric" maxlength="14"
                 autocomplete="off" autocorrect="off" autocapitalize="off"
                 spellcheck="false" name="lg-no-fill"
                 placeholder="••••••••••••••"></div>
        <div class="field"><label>${t("password")}</label>
          <input id="pw" type="password" autocomplete="new-password"
                 placeholder="••••••"></div>
        <button class="btn" id="go">${t("enter")}</button>
      </div>
      <div class="lang">
        <button data-l="uz" class="${store.lang === "uz" ? "on" : ""}">O'zbekcha</button>
        <button data-l="ru" class="${store.lang === "ru" ? "on" : ""}">Русский</button>
      </div>
    </div>`;
  if (errMsg) $("#err").innerHTML = `<div class="err">${esc(errMsg)}</div>`;
  $("#go").onclick = doLogin;
  $("#pw").addEventListener("keydown", (e) => { if (e.key === "Enter") doLogin(); });
  app.querySelectorAll(".lang button").forEach(b =>
    b.onclick = () => { store.lang = b.dataset.l; render(); });
}

async function doLogin() {
  const lg = $("#lg").value.trim(), pw = $("#pw").value;
  if (!lg || !pw) return viewLogin(t("fillAll"));
  $("#go").disabled = true; $("#go").textContent = t("loading");
  const { status, data } = await api("/api/mobile/login", { method: "POST", auth: false, body: { login: lg, password: pw } });
  if (status === 200 && data && data.token) {
    store.token = data.token; store.role = data.role; store.name = data.name;
    store.card = lg; store.photo = ""; store.viewAll = data.view_all ? "1" : "";
    if (data.must_change) return viewChange();
    render();
  } else {
    viewLogin((data && data.error) || t("wrong"));
  }
}

// ─────────── Parol o'zgartirish ───────────
function viewChange() {
  $("#app").innerHTML = `
    <div class="auth">
      <div class="brand"><div class="mark">N</div>
        <div><h1>${t("appName")}</h1><p>${esc(fmtName(store.name))}</p></div></div>
      <div class="card">
        <h2>${t("changeTitle")}</h2><p class="sub">${t("changeHint")}</p>
        <div id="err"></div>
        <div class="field"><label>${t("newPass")}</label><input id="p1" type="password"></div>
        <div class="field"><label>${t("newPass2")}</label><input id="p2" type="password"></div>
        <button class="btn" id="sv">${t("save")}</button>
      </div>
    </div>`;
  $("#sv").onclick = async () => {
    const a = $("#p1").value, b = $("#p2").value;
    if (a.length < 6) return ($("#err").innerHTML = `<div class="err">${t("passShort")}</div>`);
    if (a !== b) return ($("#err").innerHTML = `<div class="err">${t("passMismatch")}</div>`);
    const { status } = await api("/api/mobile/password", { method: "POST", body: { new_password: a } });
    if (status === 200) render();
  };
}

// ─────────── Parolni o'zgartirish (istalgan vaqtda, modal) ───────────
function changePwModal() {
  openModal(`
    <h3 style="margin:0 0 4px">${t("changeTitle")}</h3>
    <div class="adm-modmeta">${t("changeHint")}</div>
    <div id="pwErr"></div>
    <input class="adm-inp" id="pwn1" type="password" placeholder="${t("newPass")}">
    <input class="adm-inp" id="pwn2" type="password" placeholder="${t("newPass2")}">
    <button class="btn adm-primary" id="pwSave">${t("save")}</button>`);
  const err = (m) => { const e = $("#pwErr"); if (e) e.innerHTML = `<div class="err">${esc(m)}</div>`; };
  $("#pwSave").onclick = async () => {
    const a = $("#pwn1").value, b = $("#pwn2").value;
    if (a.length < 6) return err(t("passShort"));
    if (a !== b) return err(t("passMismatch"));
    const btn = $("#pwSave"); btn.disabled = true; btn.textContent = "…";
    const { status } = await api("/api/mobile/password", { method: "POST", body: { new_password: a } });
    if (status === 200) {
      const bg = document.querySelector(".modal-bg"); if (bg) bg.remove();
      admToast(t("pwSaved"));
    } else { btn.disabled = false; btn.textContent = t("save"); err(t("pwFail")); }
  };
}

// ─────────── App shell (gradient header + pastki nav) ───────────
let nav = "home"; // home | staff | exp
let VIEW_GEN = 0;  // har render() da oshadi — eski yuklashlarni bekor qiladi

function shell(inner) {
  const isHR = canViewAll();
  // Moslashuvchan dizayn uchun: sahifa turi va keng ro'yxat belgisi
  const bc = document.body.classList;
  bc.add("app-shell");
  bc.toggle("wide-page", nav === "staff" || (nav === "home" && isHR));
  document.body.dataset.page = nav;
  const av = store.photo
    ? `<img src="photos/${esc(store.photo)}" alt="" onerror="this.parentNode.textContent='${esc(initials(store.name))}'">`
    : esc(initials(store.name));
  const isAdmin = isAdminRole();
  // Rahbariyat (direktor, o'rinbosarlar) ham panelga kiradi — faqat ko'rish uchun
  const navItems = [
    { id: "home", ico: "🏠", lbl: t("navHome") },
    ...(isHR ? [{ id: "staff", ico: "👥", lbl: t("navStaff") }] : []),
    { id: "exp", ico: "📝", lbl: t("navExp"), badge: true },
    { id: "ariza", ico: "📨", lbl: t("navAriza"), badge2: isHR },
    ...(isAdmin ? [{ id: "admin", ico: "⚙️", lbl: t("navAdmin") }]
       : isHR ? [{ id: "admin", ico: "📊", lbl: t("navRep") }] : []),
  ];
  const navHtml = navItems.map(n => `
    <div class="bn ${nav === n.id ? "on" : ""}" data-nav="${n.id}">
      <span class="i ${(n.badge || n.badge2 || n.badge3) ? "nav-badge-wrap" : ""}">${n.ico}${n.badge ? `<span class="nav-badge" id="navBadge" style="display:none"></span>` : ""}${n.badge2 ? `<span class="nav-badge" id="navBadge2" style="display:none"></span>` : ""}${n.badge3 ? `<span class="nav-badge" id="navBadge3" style="display:none"></span>` : ""}</span>${n.lbl}
    </div>`).join("");
  return `
    <div class="top">
      <div class="tophead">
        <div class="brandline">
          <img class="logo" src="logo.png" alt="">
          <div class="btxt"><b>${t("appName").toUpperCase()}</b><span>${t("agency")}</span></div>
        </div>
        <div class="acts">
          <button class="iconbtn" id="theme">${store.theme === "dark" ? "☀️" : "🌙"}</button>
          <button class="iconbtn" id="lang">${store.lang === "uz" ? "RU" : "UZ"}</button>
          <button class="iconbtn" id="rf">⟳</button>
          <button class="iconbtn" id="pwbtn" title="${t("pwBtn")}">🔑</button>
          <button class="iconbtn" id="out">⎋</button>
        </div>
      </div>
      <div class="who">
        <div class="av">${av}</div>
        <div><b>${esc(fmtName(store.name))}</b><span>${store.role === "employee" ? "" : store.role.toUpperCase() + " · "}${todayLine()}</span></div>
      </div>
    </div>
    <div class="wrap">${inner}</div>
    <div class="bottomnav" data-brand="${esc(t("appName").toUpperCase())}" style="grid-template-columns:repeat(${navItems.length},1fr)">${navHtml}</div>`;
}
function bindShell() {
  $("#theme").onclick = () => { store.theme = store.theme === "dark" ? "light" : "dark"; applyTheme(); const b = $("#theme"); if (b) b.textContent = store.theme === "dark" ? "☀️" : "🌙"; };
  $("#lang").onclick = () => { store.lang = store.lang === "uz" ? "ru" : "uz"; render(); };
  $("#rf").onclick = async () => {
    const b = $("#rf");
    b.disabled = true;
    try { await api("/api/mobile/refresh_nvr", { method: "POST" }); } catch (e) {}
    b.disabled = false;
    render();
  };
  const pb = $("#pwbtn"); if (pb) pb.onclick = changePwModal;
  $("#out").onclick = async () => { await api("/api/mobile/logout", { method: "POST" }); store.token = ""; store.photo = ""; store.viewAll = ""; render(); };
  document.querySelectorAll(".bn").forEach(b =>
    b.onclick = () => { if (b.dataset.nav === "admin") admSection = "menu"; nav = b.dataset.nav; render(); });
}
function setNavBadge(n) {
  const el = $("#navBadge");
  if (!el) return;
  if (n > 0) { el.textContent = n > 9 ? "9+" : String(n); el.style.display = "grid"; }
  else el.style.display = "none";
}
function setNavBadge2(n) {
  const el = $("#navBadge2");
  if (!el) return;
  if (n > 0) { el.textContent = n > 9 ? "9+" : String(n); el.style.display = "grid"; }
  else el.style.display = "none";
}
// Bron: qatnashchi sifatida qo'shilgan, hali ko'rilmagan yig'ilishlar
let BRON_BADGE_AT = 0, BRON_N = 0;
function paintBronBadge() {
  const el = $("#navBadge3");
  if (!el) return;
  el.textContent = BRON_N > 9 ? "9+" : String(BRON_N);
  el.style.display = BRON_N > 0 ? "grid" : "none";
}
async function refreshBronBadge(force) {
  if (!store.token) return;
  paintBronBadge();
  if (!force && Date.now() - BRON_BADGE_AT < 60000) return;   // daqiqada 1 marta
  BRON_BADGE_AT = Date.now();
  try {
    const { status, data } = await api("/api/mobile/bron/notices");
    if (status === 200) { BRON_N = ((data && data.items) || []).length; paintBronBadge(); }
  } catch (e) {}
}
async function refreshArizaBadge() {
  if (!canViewAll()) return;
  try { const { data } = await api("/api/mobile/ariza/all"); setNavBadge2((data && data.pending) || 0); } catch (e) {}
}

// ─────────── umumiy modal ───────────
function openModal(html) {
  const overlay = document.createElement("div");
  overlay.className = "modal-bg";
  overlay.innerHTML = `<div class="modal">${html}<button class="btn m-close">${t("expClose")}</button></div>`;
  overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };
  overlay.querySelector(".m-close").onclick = () => overlay.remove();
  document.body.appendChild(overlay);
}
function timelineModal(emp) {
  const tl = emp.timeline || [];
  const tlHtml = tl.length ? `<div class="tl">` + tl.map(e => `
      <div class="row">
        <span class="pill ${e.kind === "in" ? "in" : "out"}">${e.kind === "in" ? "→ " + t("tlIn") : "← " + t("tlOut")}</span>
        <span class="t">${esc(e.time)}</span>
      </div>`).join("") + `</div>`
    : `<div class="empty">${t("noEvents")}</div>`;
  // Rasm yuklash va PhD/DSc belgilash — endi "Boshqaruv" bo'limida.
  openModal(`
    <div class="m-head">
      <div class="av big">${avatar(emp)}</div>
      <div><b>${esc(fmtName(emp.full_name) || "?")}</b><br>
        <span class="m-sub">${t("firstIn")}: ${esc(timeShort(emp.first_entry) || "—")}</span></div>
    </div>
    <div id="tmMonthly"></div>
    <h3>${t("tlTitle")}</h3>
    ${tlHtml}`);
  // HR/rahbar: oylik kechikish/kelmaslik kunlari (bosib ko'rish mumkin)
  const card = String(emp.card_number || "");
  if (canViewAll() && card) {
    api("/api/mobile/monthly/" + encodeURIComponent(card)).then(({ status, data }) => {
      if (status !== 200 || !data || !data.monthly) return;
      const late = (data.monthly.late && data.monthly.late.late_days) || [];
      const abs = (data.monthly.work && data.monthly.work.absent_days_list) || [];
      const box = document.querySelector(".modal-bg:last-of-type #tmMonthly");
      if (!box) return;
      box.innerHTML = `
        <div class="pi clickable" id="tmLate"><div class="nm"><b>⏰ ${t("m_late")}</b></div><span class="badge late">${late.length}</span></div>
        <div class="pi clickable" id="tmAbs"><div class="nm"><b>✖️ ${t("m_absent")}</b></div><span class="badge abs">${abs.length}</span></div>
        <div class="pi clickable" id="tmDays"><div class="nm"><b>🗓 ${t("daysTitle")}</b></div><span class="badge ok">›</span></div>`;
      const l = box.querySelector("#tmLate"); if (l) l.onclick = () => lateDaysModal(late, fmtName(emp.full_name), card);
      const a = box.querySelector("#tmAbs"); if (a) a.onclick = () => absentDaysModal(abs, fmtName(emp.full_name));
      const dd = box.querySelector("#tmDays"); if (dd) dd.onclick = () => daysModal(card, fmtName(emp.full_name));
    }).catch(() => {});
  }
}
// ─────────── Rasm yuklash (HR, modal ichida) ───────────
function bindPhotoUpload() {
  const box = document.querySelector(".modal-bg:last-of-type .photoup");
  if (!box) return;
  const btn = box.querySelector(".photoup-btn");
  const inp = box.querySelector(".photoup-inp");
  const msg = box.querySelector(".photoup-msg");
  btn.onclick = () => inp.click();
  inp.onchange = () => {
    const file = inp.files && inp.files[0];
    if (!file) return;
    btn.disabled = true; btn.textContent = t("loading");
    const img = new Image();
    const url = URL.createObjectURL(file);
    img.onload = async () => {
      // telefon rasmini kichraytiramiz (maks 600px, JPEG)
      const MAX = 600;
      const k = Math.min(1, MAX / Math.max(img.width, img.height));
      const cv = document.createElement("canvas");
      cv.width = Math.round(img.width * k); cv.height = Math.round(img.height * k);
      cv.getContext("2d").drawImage(img, 0, 0, cv.width, cv.height);
      URL.revokeObjectURL(url);
      const dataUrl = cv.toDataURL("image/jpeg", 0.85);
      const { status, data } = await api("/api/mobile/photo/upload", {
        method: "POST", body: { card: box.dataset.card, image: dataUrl },
      });
      btn.disabled = false; btn.textContent = "📷 Rasm yuklash";
      if (status === 200 && data && data.ok) {
        msg.innerHTML = `<div class="exp-ok">Rasm saqlandi ✓</div>`;
        // modal avatarini darhol yangilaymiz
        const av = document.querySelector(".modal-bg:last-of-type .av.big");
        if (av) av.innerHTML = `<img src="${dataUrl}" alt="">`;
      } else if (status === 404 || status === 405) {
        msg.innerHTML = `<div class="err">Server yangilanmagan — mobile_api.py ni qayta ishga tushiring</div>`;
      } else if (status === 413) {
        msg.innerHTML = `<div class="err">Rasm juda katta</div>`;
      } else {
        msg.innerHTML = `<div class="err">${esc((data && data.error) || `Yuklanmadi (xato ${status})`)}</div>`;
      }
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      btn.disabled = false; btn.textContent = "📷 Rasm yuklash";
      msg.innerHTML = `<div class="err">Rasm o'qilmadi</div>`;
    };
    img.src = url;
  };
}

function expModal(req) {
  const kindLbl = expKindName(req.kind);
  // Har kunga alohida IMZOLANGAN rasmiy PDF xati
  const expId = req.req_id
    || ((req.date && req.card_number && req.kind) ? `${req.date}_${req.card_number}_${req.kind}` : "");
  const pdfBtn = canViewAll() && expId
    ? `<a class="btn pdfbtn" href="/api/mobile/explain/pdf/${encodeURIComponent(expId)}?token=${encodeURIComponent(store.token)}" target="_blank">📄 ${t("expPdf")}</a>`
    : "";
  // Ixtiyoriy: barcha xatlar yig'ilgan Word
  const wordBtn = canViewAll() && req.card_number
    ? `<a class="btn wordbtn secondary" href="/api/mobile/explain/word/${esc(String(req.card_number))}?token=${encodeURIComponent(store.token)}" target="_blank">🗂 ${t("expWord")}</a>`
    : "";
  const delBtn = canViewAll() && expId
    ? `<button class="arz-del-btn" id="expDelBtn">${t("expDelete")}</button>` : "";
  openModal(`
    <h3>📝 ${t("expTitle")}</h3>
    <div class="m-meta"><b>${esc(fmtName(req.full_name) || "")}</b><br>
      ${kindLbl} · ${esc(req.date || "")}
      ${req.submitted_at ? `<br>${t("expSentAt")}: ${esc(req.submitted_at)}` : ""}</div>
    <div class="m-text">${esc(req.explanation || "—")}</div>
    ${pdfBtn}${wordBtn}${delBtn}`);
  const db = $("#expDelBtn");
  if (db) db.onclick = async () => {
    if (!confirm(t("expDeleteQ"))) return;
    const { status } = await api("/api/mobile/explain/delete", { method: "POST", body: { id: expId } });
    if (status === 200) {
      const bg = document.querySelector(".modal-bg"); if (bg) bg.remove();
      admToast(t("admDone")); render();
    } else admToast(t("admFail"), false);
  };
}

// ─────────── Kechikish / kelmaslik kunlari (bosilganda) ───────────
function lateDaysModal(list, who, card, workStart) {
  // HR bo'lsa — har bir kechikkan kunni "Tadbirda" deb belgilash mumkin
  const hr = canViewAll() && card;
  const rows = (list && list.length) ? list.map(d => `
    <div class="pi"><div class="nm"><b>${esc(fmtDayMon(d.date))}</b>
      <span>${esc(timeShort(d.time) || d.time || "")}${(() => {
        const dl = lateDelay(d.time, workStart || d.work_start);
        return dl ? ` · ${dl} ${t("lateBy")}` : "";
      })()}</span></div>
      ${d.excused ? `<span class="badge ok">${t("excusedTag")}</span>` : `<span class="badge late">${t("m_late")}</span>`}
      ${hr ? `<button class="ld-tadbir" data-d="${esc(d.date)}" title="${t("admTypeTadbir")}">🎤</button>` : ""}
    </div>`).join("")
    : `<div class="empty">${t("noEvents")}</div>`;
  const hint = hr ? `<div class="adm-hint" style="margin:-2px 0 8px">${t("lateTadbirHint")}</div>` : "";
  openModal(`<h3>⏰ ${t("m_late")}${who ? " · " + esc(who) : ""} · ${(list || []).length}</h3>${hint}${rows}`);
  if (!hr) return;
  document.querySelectorAll(".modal-bg:last-of-type .ld-tadbir").forEach(b => b.onclick = async (e) => {
    e.stopPropagation();
    const date = b.dataset.d;
    if (!confirm(`${fmtDayMon(date)} — ${t("lateTadbirAsk")}`)) return;
    b.disabled = true; b.textContent = "…";
    const { status, data } = await api("/api/mobile/admin/exemptions/add", {
      method: "POST",
      body: { card, type: "tadbir", date_from: date, date_to: date, note: "" },
    });
    if (status === 200) { b.textContent = "✓"; admToast(t("lateTadbirOk")); }
    else { b.disabled = false; b.textContent = "🎤"; admToast((data && data.error) || t("admFail"), false); }
  });
}
function absentDaysModal(list, who) {
  const rows = (list && list.length) ? list.map(d => `
    <div class="pi"><div class="nm"><b>${esc(fmtDayMon(d))}</b></div>
      <span class="badge abs">${t("m_absent")}</span></div>`).join("")
    : `<div class="empty">${t("noEvents")}</div>`;
  openModal(`<h3>✖️ ${t("m_absent")}${who ? " · " + esc(who) : ""} · ${(list || []).length}</h3>${rows}`);
}

// ─── Kunlik davomat: qaysi kuni nechada kelib-ketgan ───
const MON_UZ = ["Yanvar","Fevral","Mart","Aprel","May","Iyun","Iyul","Avgust","Sentabr","Oktabr","Noyabr","Dekabr"];
function ymLabel(ym) {
  const m = String(ym || "").match(/^(\d{4})-(\d{2})$/);
  return m ? `${MON_UZ[parseInt(m[2], 10) - 1]} ${m[1]}` : (ym || "");
}
function ymList(n) {
  const out = [], d = new Date();
  for (let i = 0; i < n; i++) {
    out.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`);
    d.setMonth(d.getMonth() - 1);
  }
  return out;
}
async function daysModal(card, who, ym) {
  ym = ym || ymList(1)[0];
  const opts = ymList(12).map(m => `<option value="${m}"${m === ym ? " selected" : ""}>${ymLabel(m)}</option>`).join("");
  const head = `<h3 style="margin:0 0 4px">🗓 ${t("daysTitle")}${who ? " · " + esc(who) : ""}</h3>
    <select class="adm-inp" id="dyMonth" style="margin:8px 0 10px">${opts}</select>
    <div id="dyBody"><div class="empty">${t("daysLoad")}</div></div>`;
  openModal(head);
  const bind = () => {
    const sel = $("#dyMonth");
    if (sel) sel.onchange = () => daysModal(card, who, sel.value);
  };
  bind();
  const { status, data } = await api(`/api/mobile/days/${encodeURIComponent(card)}?month=${ym}`);
  const body = $("#dyBody");
  if (!body) return;
  if (status !== 200 || !data) { body.innerHTML = `<div class="empty">${(data && data.error) || t("daysErr")}</div>`; return bind(); }

  const byDate = {};
  (data.days || []).forEach(d => byDate[d.date] = d);

  // ── Kalendar to'ri (dushanbadan boshlanadi) ──
  const [Y, M] = ym.split("-").map(Number);
  const first = new Date(Y, M - 1, 1);
  const lead = (first.getDay() + 6) % 7;              // Du=0
  const total = new Date(Y, M, 0).getDate();
  const todayIso = new Date().toISOString().slice(0, 10);

  let cells = "";
  for (let i = 0; i < lead; i++) cells += `<div class="cal-c cal-empty"></div>`;
  for (let d = 1; d <= total; d++) {
    const iso = `${Y}-${String(M).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    const rec = byDate[iso];
    const dow = new Date(Y, M - 1, d).getDay();
    const weekend = (dow === 0 || dow === 6);
    const future = iso > todayIso;
    let cls = "cal-c";
    if (rec) cls += rec.tadbir ? " cal-tadbir" : (rec.late ? " cal-late" : " cal-ok");
    else if (weekend) cls += " cal-wknd";
    else if (future) cls += " cal-fut";
    else cls += " cal-abs";
    const tm = rec ? `<i>${esc(rec.in || "—")}</i>` : "";
    cells += `<div class="${cls}" data-d="${iso}"><b>${d}</b>${tm}</div>`;
  }

  const WD = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"];
  body.innerHTML = `
    <div class="cal-wd">${WD.map(w => `<span>${w}</span>`).join("")}</div>
    <div class="cal-grid">${cells}</div>
    <div class="cal-legend">
      <span><i class="lg lg-ok"></i>${t("calOk")}</span>
      <span><i class="lg lg-late"></i>${t("m_late")}</span>
      <span><i class="lg lg-abs"></i>${t("m_absent")}</span>
      <span><i class="lg lg-tadbir"></i>${t("calTadbir")}</span>
    </div>
    <div id="calDet" class="cal-det"></div>`;

  const det = $("#calDet");
  const isHr = canViewAll();
  const show = (iso) => {
    const r = byDate[iso];
    if (!r) { det.innerHTML = `<div class="empty" style="padding:8px">${esc(fmtDayMon(iso))} — ${t("daysNone")}</div>`; return; }
    const evs = (r.events || []).map(e =>
      `<span class="cal-ev ${e.kind}">${e.kind === "in" ? "→" : "←"} ${esc(e.t)}</span>`).join("");
    // HR: shu kunni "Tadbirda" deb belgilash (kechikish bekor bo'ladi, 8 soat yoziladi)
    const tadbirBtn = (isHr && !r.tadbir)
      ? `<button class="btn secondary" id="calTadbir" data-d="${esc(iso)}" style="margin-top:10px">🎤 ${t("calTadbirBtn")}</button>`
      : "";
    det.innerHTML = `
      <div class="cal-det-h"><b>${esc(fmtDayMon(iso))}</b>
        ${r.tadbir ? `<span class="badge" style="background:#e0f2fe;color:#0369a1">🎤 ${t("calTadbir")}</span>` : (r.late ? `<span class="badge late">${t("m_late")}</span>` : "")}
        <span class="badge ok" style="font-family:'JetBrains Mono',monospace">${esc(r.hours)}</span></div>
      <div class="cal-det-b">${evs || "—"}</div>
      ${tadbirBtn}`;
    const tb = det.querySelector("#calTadbir");
    if (tb) tb.onclick = async () => {
      if (!confirm(`${fmtDayMon(iso)} — ${t("lateTadbirAsk")}`)) return;
      tb.disabled = true; tb.textContent = "…";
      const { status, data } = await api("/api/mobile/admin/exemptions/add", {
        method: "POST",
        body: { card, type: "tadbir", date_from: iso, date_to: iso, note: "" },
      });
      if (status === 200) { admToast(t("lateTadbirOk")); daysModal(card, who, ym); }
      else { tb.disabled = false; tb.textContent = "🎤 " + t("calTadbirBtn"); admToast((data && data.error) || t("admFail"), false); }
    };
  };
  document.querySelectorAll("#dyBody .cal-c[data-d]").forEach(c => c.onclick = () => {
    document.querySelectorAll("#dyBody .cal-c").forEach(x => x.classList.remove("sel"));
    c.classList.add("sel"); show(c.dataset.d);
  });
  // Oxirgi ma'lumotli kunni ko'rsatamiz
  const last = (data.days || [])[0];
  if (last) {
    const el = document.querySelector(`#dyBody .cal-c[data-d="${last.date}"]`);
    if (el) el.classList.add("sel");
    show(last.date);
  }
  bind();
}

// ─── Umumiy reyting (hamma o'rinni ko'radi, soat yashirin) ───
async function ratingModal(ym) {
  const opts = (sel) => ymList(12).map(m =>
    `<option value="${m}"${m === sel ? " selected" : ""}>${ymLabel(m)}</option>`).join("");
  const shell = (inner, cur) => `<h3 style="margin:0 0 4px">🏆 ${t("rankAll")}</h3>
    <select class="adm-inp" id="rtMonth" style="margin:8px 0 10px">${opts(cur)}</select>
    <div id="rtBody">${inner}</div>`;
  const bind = (cur) => { const s = $("#rtMonth"); if (s) s.onchange = () => ratingModal(s.value); };

  const cur0 = ym || ymList(1)[0];
  openModal(shell(`<div class="empty">${t("daysLoad")}</div>`, cur0));
  bind(cur0);

  const { status, data } = await api("/api/mobile/rating" + (ym ? "?month=" + ym : ""));
  const cur = (data && data.year_month) || cur0;
  const put = (inner) => { const b = $("#rtBody"); if (b) b.innerHTML = inner; bind(cur); };
  if (status !== 200 || !data) return put(`<div class="empty">${t("rankNone")}</div>`);
  if (data.building) return put(`<div class="empty">⏳ ${t("ratBuilding")}</div>`);
  const rows = (data.rating || []);
  if (!rows.length) return put(`<div class="empty">${t("rankNone")}</div>`);
  const html = rows.map(r => {
    const medal = r.pos === 1 ? "🥇" : r.pos === 2 ? "🥈" : r.pos === 3 ? "🥉" : r.pos;
    // Soat faqat HR/rahbarga yoki o'ziga (backend yubormasa — ko'rinmaydi)
    const hrs = r.total_hours_str
      ? `<span class="badge ok" style="font-family:'JetBrains Mono',monospace">${esc(r.total_hours_str)}</span>` : "";
    const meTag = r.me ? `<span class="badge late" style="margin-left:6px">${t("rankMe")}</span>` : "";
    // Telefonda qulay bo'lishi uchun rasm ko'rsatilmaydi — faqat familiya va ism
    return `<div class="pi rt-row" style="${r.me ? "background:var(--acc-soft,rgba(20,140,150,.10));border-radius:10px" : ""}">
      <div class="rt-pos" style="font-size:${r.pos <= 3 ? "17px" : "13px"}">${medal}</div>
      <div class="nm" style="flex:1"><b>${esc(shortName(r.full_name))}</b>${meTag}</div>
      ${hrs}</div>`;
  }).join("");
  put(`<div style="font-size:12px;color:var(--text-2);margin:-2px 0 8px">${t("rankHours")} · ${data.total}</div>${html}`);
}

// ─────────── STATUS xaritalari ───────────
const STATUS_MAP = {
  ishda: { cls: "green", key: "st_ishda" },
  tushlikda: { cls: "amber", key: "st_tushlikda" },
  ishda_emas: { cls: "slate", key: "st_chiqib" },
  kelmagan: { cls: "red", key: "st_kelmagan" },
  nomalum: { cls: "slate", key: "st_yoq" },
};
const RING = { ishda: "g", tushlikda: "a", ishda_emas: "s", kelmagan: "r" };
const BADGE = {
  ishda: { cls: "ok", key: "c_inside" },
  tushlikda: { cls: "late", key: "c_lunch" },
  ishda_emas: { cls: "out", key: "c_out" },
  kelmagan: { cls: "abs", key: "c_absent" },
};

// ─────────── XODIM: Bosh sahifa ───────────
async function viewMe() {
  const __g = VIEW_GEN;   // eskirgan yuklash yangi bo'limni bosib ketmasin
  $("#app").innerHTML = shell(skeleton(4)); bindShell();
  const { status, data } = await api("/api/mobile/me");
  if (status !== 200 || !data) { if (status === 401) return render(); return; }
  if (data.photo_file) store.photo = data.photo_file;
  // avval kirgan o'rinbosarlar uchun: huquq kelsa HR ko'rinishiga o'tamiz
  if (data.view_all && store.viewAll !== "1") { store.viewAll = "1"; return render(); }
  const expRes = await api("/api/mobile/explain/my");
  const myReqs = (expRes.data && expRes.data.requests) || [];
  const expPending = myReqs.filter(r => r.status === "pending");
  const olimList = await fetchOlimlar();
  const today = data.today || {}; const st = STATUS_MAP[today.status] || STATUS_MAP.nomalum;
  const tl = (today.timeline || []);
  const mw = (data.monthly && data.monthly.work) || null;
  const ml = (data.monthly && data.monthly.late) || null;

  const heroMeta = today.first_entry && today.first_entry !== "-"
    ? `${t("firstIn")}: <b>${esc(today.first_entry)}</b>`
    : t("noEvents");
  const myReasonHtml = today.reason
    ? `<div class="sec reason-sec"><h3>💬 ${t("admReason")}</h3><p class="reason-txt">${esc(today.reason)}</p></div>`
    : "";
  // Binoni tark etish (10+ daqiqa) — sabab so'rovi yoki yozilgan izoh holati
  const exStatusCls = (s) => s === "accepted" ? "ok" : (s === "rejected" ? "abs" : "late");
  const exStatusLbl = (s) => s === "accepted" ? t("exitAccepted") : (s === "rejected" ? t("exitRejected") : t("exitPending"));
  const exitHtml = data.exit_prompt
    ? `<div class="sec exit-sec">
         <h3>🚪 ${t("exitTitle")}</h3>
         <p class="adm-hint">${t("exitPromptMsg")}${data.exit_prompt.exit_time ? " (" + t("exitAt") + ": " + esc(timeShort(data.exit_prompt.exit_time)) + ")" : ""}</p>
         <textarea class="adm-inp adm-ta" id="exitText" rows="2" placeholder="${t("exitPh")}"></textarea>
         <button class="btn adm-primary" id="exitSendBtn">${t("exitSend")}</button>
       </div>`
    : (data.my_exit
        ? `<div class="sec"><h3>🚪 ${t("exitMy")}</h3>
             <p class="reason-txt">${esc(data.my_exit.text)}</p>
             <span class="badge ${exStatusCls(data.my_exit.status)}" style="margin-top:6px;display:inline-block">${exStatusLbl(data.my_exit.status)}</span>
           </div>`
        : "");

  const tlHtml = tl.length ? `<div class="tl">` + tl.map(e => `
      <div class="row">
        <span class="pill ${e.kind === "in" ? "in" : "out"}">${e.kind === "in" ? "→ " + t("tlIn") : "← " + t("tlOut")}</span>
        <span class="t">${esc(e.time)}</span>
      </div>`).join("") + `</div>`
    : `<div class="empty">${t("noEvents")}</div>`;

  const hoursNum = mw ? esc(mw.total_hours_str || "0:00") : "—";
  const daysNum = mw ? esc(String(mw.days_worked ?? "—")) : "—";
  const lateNum = ml ? esc(String(ml.late_count ?? 0)) : "0";
  const absNum = mw ? esc(String(mw.absent_days ?? 0)) : "—";

  // HR e'lonlari (Telegram bot o'rniga — ilova ichida ko'rinadi)
  const anns = (data.announcements || []);
  const annHtml = anns.length ? anns.map(a => `
    <div class="sec ann-box">
      <div class="ann-head">📢 ${t("annTitle")}${a.date ? " · " + esc(fmtDayMon(a.date)) : ""}</div>
      <div class="ann-text">${esc(a.text)}</div>
    </div>`).join("") : "";

  // Yo'qlama: qatnashgan bo'lsa tasdiq, qatnashmagan bo'lsa sabab so'raladi
  const yqs = (data.yoqlama || []);
  const yqHtml = yqs.slice(0, 3).map(y => {
    const meta = `${esc(y.title)} · ${esc(fmtDayMon(y.date))}${y.time ? " · " + esc(y.time) : ""}`;
    if (y.attended) {
      return `<div class="sec yq-card ok">
        <div class="yq-t">✅ ${t("yqWasThere")}</div>
        <div class="yq-e">${meta}</div>
        <div class="yq-d">${t("yqNoAction")}</div></div>`;
    }
    if (y.answered) {
      return `<div class="sec yq-card sent">
        <div class="yq-t">${t("yqAnswerSent")}</div>
        <div class="yq-e">${meta}</div>
        <div class="yq-d">"${esc(y.reason || "")}"</div>
        <div class="yq-d" style="color:var(--primary)">${t("yqHrReview")}</div></div>`;
    }
    return `<div class="sec yq-card ask" data-yq="${esc(y.id)}">
      <div class="yq-t">${t("yqWhyNot")}</div>
      <div class="yq-e">${meta}</div>
      <div class="yq-d">${t("yqWhyDesc")}</div>
      <textarea class="adm-inp yq-in" rows="3" placeholder="${t("yqWhyPh")}"></textarea>
      <button class="btn adm-primary yq-send" style="margin-top:2px">${t("exitSend")}</button></div>`;
  }).join("");

  // Reyting o'rni (dashboard oylik reytingidagi joyi)
  const rk = (data.monthly && data.monthly.rank) || null;
  let rankHtml = "";
  if (rk && rk.work_pos) {
    const medal = rk.work_pos === 1 ? "🥇" : rk.work_pos === 2 ? "🥈" : rk.work_pos === 3 ? "🥉" : "🏆";
    const lateLine = rk.late_pos
      ? `<div style="font-size:13px;color:var(--text-2);margin-top:4px">⏰ ${rk.late_pos} <span style="opacity:.7">${t("rankOutOf")} ${rk.late_total}</span> · ${t("rankLate")}</div>`
      : "";
    rankHtml = `<div class="sec clickable" id="rankCard" style="display:flex;align-items:center;gap:14px">
        <div style="font-size:34px;font-weight:800;line-height:1;font-family:'JetBrains Mono',monospace">${medal}${rk.work_pos}<span style="font-size:16px;font-weight:600;color:var(--text-2)"> / ${rk.work_total}</span></div>
        <div style="flex:1">
          <div style="font-weight:700">${t("rankTitle")}</div>
          <div style="font-size:13px;color:var(--text-2)">🏆 ${t("rankHours")}</div>
          ${lateLine}
          <div style="font-size:12px;color:var(--acc);font-weight:700;margin-top:5px">${t("rankTap")}</div>
        </div>
      </div>`;
  }

  if (__g !== VIEW_GEN) return;
  $("#app").innerHTML = shell(`
    ${olimlarHtml(olimList)}
    <div class="hero ${st.cls}">
      <div class="dot"></div>
      <div class="lbl">${t("today")}</div>
      <div class="big">${t(st.key)}</div>
      <div class="meta">${heroMeta}</div>
    </div>
    ${yqHtml}
    ${annHtml}
    ${expFormsHtml(expPending)}
    ${exitHtml}
    ${myReasonHtml}
    <div class="sec">
      <h3>${t("today")}</h3>
      ${tlHtml}
    </div>
    ${rankHtml}
    <div class="sec">
      <h3>${t("monthly")} ${data.monthly && data.monthly.year_month ? "· " + esc(data.monthly.year_month) : ""}</h3>
      <div class="tiles">
        <div class="tile"><div class="n">${hoursNum}</div><div class="k">${t("m_hours")}</div></div>
        <div class="tile"><div class="n">${daysNum}</div><div class="k">${t("m_days")}</div></div>
        <div class="tile warn clickable" id="lateTile"><div class="n">${lateNum}</div><div class="k">${t("m_late")} ›</div></div>
        <div class="tile clickable" id="absTile"><div class="n">${absNum}</div><div class="k">${t("m_absent")} ›</div></div>
      </div>
      <button class="btn secondary" id="daysBtn" style="margin-top:10px">🗓 ${t("daysTap")}</button>
    </div>
    <button class="btn secondary" id="mePwBtn" style="margin-top:2px">🔑 ${t("pwBtn")}</button>
    <div class="foot">${t("updated")}: ${esc(timeShort(data.updated_at) || data.updated_at || "")}</div>
  `);
  bindShell();
  setNavBadge(expPending.length);
  bindExpForms();
  bindOlimlarSlider();
  const mePw = $("#mePwBtn");
  if (mePw) mePw.onclick = changePwModal;
  const lateD = (data.monthly && data.monthly.late && data.monthly.late.late_days) || [];
  const absD = (data.monthly && data.monthly.work && data.monthly.work.absent_days_list) || [];
  document.querySelectorAll(".yq-card.ask").forEach(box => {
    const btn = box.querySelector(".yq-send"), ta = box.querySelector(".yq-in");
    if (!btn || !ta) return;
    btn.onclick = async () => {
      const text = (ta.value || "").trim();
      if (text.length < 3) return admToast(t("exitShort"), false);
      btn.disabled = true; btn.textContent = "…";
      const { status, data: d } = await api("/api/mobile/yoqlama/reason", {
        method: "POST", body: { id: box.dataset.yq, text },
      });
      if (status === 200) { admToast(t("exitSent")); viewMe(); }
      else { btn.disabled = false; btn.textContent = t("exitSend"); admToast((d && d.error) || t("admFail"), false); }
    };
  });
  const rc = $("#rankCard"); if (rc) rc.onclick = () => ratingModal();
  const db = $("#daysBtn");
  if (db) db.onclick = () => daysModal(store.card || (data.me && data.me.card_number) || "", fmtName(store.name));
  const lt = $("#lateTile"); if (lt) lt.onclick = () => lateDaysModal(lateD, fmtName(store.name));
  const at = $("#absTile"); if (at) at.onclick = () => absentDaysModal(absD, fmtName(store.name));
  const exBtn = $("#exitSendBtn");
  if (exBtn) exBtn.onclick = async () => {
    const text = ($("#exitText").value || "").trim();
    if (text.length < 3) return admToast(t("exitShort"), false);
    exBtn.disabled = true; exBtn.textContent = "…";
    const { status, data: d } = await api("/api/mobile/exit/submit", { method: "POST", body: { text } });
    if (status === 200) { admToast(t("exitSent")); viewMe(); }
    else { exBtn.disabled = false; exBtn.textContent = t("exitSend"); admToast((d && d.error) || t("admFail"), false); }
  };
}

// ─────────── Imzo chizish paneli (canvas) ───────────
function sigPadHtml() {
  return `
    <div class="sigpad">
      <div class="sigpad-head"><span>✍️ ${t("sigLabel")}</span>
        <button type="button" class="sig-clear">${t("sigClear")}</button></div>
      <canvas class="sig-canvas"></canvas>
    </div>`;
}

function initSigPad(root) {
  const cv = root.querySelector(".sig-canvas");
  if (!cv) return null;
  const dpr = window.devicePixelRatio || 1;
  const w = cv.parentElement.clientWidth - 2 || 300, h = 130;
  cv.width = w * dpr; cv.height = h * dpr;
  cv.style.width = w + "px"; cv.style.height = h + "px";
  const cx = cv.getContext("2d");
  cx.scale(dpr, dpr);
  cx.fillStyle = "#ffffff"; cx.fillRect(0, 0, w, h);
  cx.strokeStyle = "#12233D"; cx.lineWidth = 2.2; cx.lineCap = "round"; cx.lineJoin = "round";
  let drawing = false, strokes = 0, last = null;
  const pos = (e) => {
    const r = cv.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  };
  cv.addEventListener("pointerdown", (e) => {
    e.preventDefault(); cv.setPointerCapture(e.pointerId);
    drawing = true; last = pos(e); strokes++;
  });
  cv.addEventListener("pointermove", (e) => {
    if (!drawing) return;
    e.preventDefault();
    const p = pos(e);
    cx.beginPath(); cx.moveTo(last.x, last.y); cx.lineTo(p.x, p.y); cx.stroke();
    last = p;
  });
  const stop = () => { drawing = false; };
  cv.addEventListener("pointerup", stop);
  cv.addEventListener("pointercancel", stop);
  cv.style.touchAction = "none";
  const clearBtn = root.querySelector(".sig-clear");
  const clear = () => { cx.fillStyle = "#fff"; cx.fillRect(0, 0, w, h); strokes = 0; };
  if (clearBtn) clearBtn.onclick = clear;
  return {
    isEmpty: () => strokes === 0,
    dataURL: () => cv.toDataURL("image/png"),
    clear,
  };
}

// tushuntirish yozish formalari (pending so'rovlar uchun)
function expFormsHtml(reqs) {
  return (reqs || []).map(r => `
    <div class="sec exp" data-rid="${esc(r.req_id)}">
      <h3>📝 ${t("expTitle")}</h3>
      <div class="exp-need">${t("expNeed")}:
        <b>${expKindName(r.kind)}</b> · ${esc(r.date)}
        ${r.note ? `<div class="exp-note">${esc(r.note)}</div>` : ""}
      </div>
      <textarea class="exp-text" rows="4" placeholder="${t("expPlaceholder")}"></textarea>
      ${sigPadHtml()}
      <div class="exp-err"></div>
      <button class="btn exp-send">${t("expSend")}</button>
    </div>`).join("");
}
function bindExpForms() {
  document.querySelectorAll(".sec.exp").forEach(sec => {
    const btn = sec.querySelector(".exp-send");
    if (!btn) return;
    const pad = initSigPad(sec);
    btn.onclick = async () => {
      const text = sec.querySelector(".exp-text").value.trim();
      const errBox = sec.querySelector(".exp-err");
      if (text.length < 10) { errBox.innerHTML = `<div class="err">${t("expShort")}</div>`; return; }
      if (pad && pad.isEmpty()) { errBox.innerHTML = `<div class="err">${t("sigNeed")}</div>`; return; }
      btn.disabled = true; btn.textContent = t("loading");
      const { status: st2, data: d2 } = await api("/api/mobile/explain/submit", {
        method: "POST", body: { req_id: sec.dataset.rid, text, signature: pad ? pad.dataURL() : "" },
      });
      if (st2 === 200) {
        sec.innerHTML = `<div class="exp-ok">${t("expSent")}</div>`;
      } else {
        btn.disabled = false; btn.textContent = t("expSend");
        errBox.innerHTML = `<div class="err">${esc((d2 && d2.error) || t("expFail"))}</div>`;
      }
    };
  });
}

// ─────────── XODIM: o'zi sabab yozishi (oldindan) ───────────
let selfKind = "late";

function selfFormHtml() {
  const today = todayISO();
  const d = new Date(); d.setDate(d.getDate() + 1);
  const tomorrow = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  return `
    <div class="sec" id="selfSec">
      <h3>➕ ${t("selfTitle")}</h3>
      <div class="exp-need">${t("selfHint")}</div>
      <div class="selfrow">
        <input type="date" id="selfDate" value="${tomorrow}" min="${today}">
        <div class="degbtns" style="margin:0;flex:1">
          <button class="degbtn ${selfKind === "late" ? "on" : ""}" data-k="late">${t("expKindLate")}</button>
          <button class="degbtn ${selfKind === "absent" ? "on" : ""}" data-k="absent">${t("expKindAbsent")}</button>
        </div>
      </div>
      <textarea class="exp-text" id="selfText" rows="3" placeholder="${t("expPlaceholder")}"></textarea>
      ${sigPadHtml()}
      <div id="selfErr"></div>
      <button class="btn" id="selfSend">${t("expSend")}</button>
    </div>`;
}

function bindSelfForm() {
  const sec = $("#selfSec");
  if (!sec) return;
  const pad = initSigPad(sec);
  sec.querySelectorAll(".degbtn").forEach(b => {
    b.onclick = () => {
      selfKind = b.dataset.k;
      sec.querySelectorAll(".degbtn").forEach(x => x.classList.toggle("on", x === b));
    };
  });
  $("#selfSend").onclick = async () => {
    const text = $("#selfText").value.trim();
    const date = $("#selfDate").value;
    const err = $("#selfErr");
    if (text.length < 10) { err.innerHTML = `<div class="err">${t("expShort")}</div>`; return; }
    if (pad && pad.isEmpty()) { err.innerHTML = `<div class="err">${t("sigNeed")}</div>`; return; }
    const btn = $("#selfSend");
    btn.disabled = true; btn.textContent = t("loading");
    const { status, data } = await api("/api/mobile/explain/self", {
      method: "POST", body: { kind: selfKind, date, text, signature: pad ? pad.dataURL() : "" },
    });
    if (status === 200 && data && data.ok) {
      sec.innerHTML = `<div class="exp-ok">${t("selfSent")}</div>`;
      setTimeout(() => viewMyExp(), 900);
    } else {
      btn.disabled = false; btn.textContent = t("expSend");
      err.innerHTML = `<div class="err">${esc((data && data.error) || t("expFail"))}</div>`;
    }
  };
}

// ─────────── XODIM: Tushuntirishlarim ───────────
async function viewMyExp() {
  const __g = VIEW_GEN;   // eskirgan yuklash yangi bo'limni bosib ketmasin
  $("#app").innerHTML = shell(skeleton(3)); bindShell();
  const { status, data } = await api("/api/mobile/explain/my");
  if (status !== 200 || !data) { if (status === 401) return render(); return; }
  const reqs = data.requests || [];
  const pending = reqs.filter(r => r.status === "pending");
  const answered = reqs.filter(r => r.status === "answered");
  const ansHtml = answered.length ? `
    <div class="sec">
      <h3>${t("expListTitle")}</h3>
      ${answered.map(r => {
        const eid = r.req_id || ((r.date && r.card_number && r.kind) ? `${r.date}_${r.card_number}_${r.kind}` : "");
        const pdf = eid
          ? `<a class="badge ok" style="text-decoration:none" href="/api/mobile/explain/pdf/${encodeURIComponent(eid)}?token=${encodeURIComponent(store.token)}" target="_blank">📄 PDF</a>`
          : `<span class="badge ok">✓</span>`;
        return `<div class="pi">
          <div class="nm"><b>${expKindName(r.kind)} · ${esc(r.date)}</b>
            <span>${esc(r.answered_at || "")}</span></div>
          ${pdf}
        </div>`;
      }).join("")}
    </div>` : "";
  if (__g !== VIEW_GEN) return;
  $("#app").innerHTML = shell(`
    ${expFormsHtml(pending)}
    ${selfFormHtml()}
    ${ansHtml}
    ${(!pending.length && !answered.length) ? `<div class="sec"><div class="empty">${t("noExp")}</div></div>` : ""}
  `);
  bindShell();
  setNavBadge(pending.length);
  bindExpForms();
  bindSelfForm();
}

// ─────────── OLIMLAR KARUSELI ───────────
// Faqat HR belgilagan PhD/DSc xodimlar aylanadi (olimlar.json — server orqali).
// HR belgilashi: Xodimlar ro'yxatida xodimni bosib, modaldagi 🎓 tugmalar.
let olimMap = {}; // card_number -> degree ("phd"|"dsc")

const DEGREE_LBL = { phd: "Falsafa doktori (PhD)", dsc: "Fan doktori (DSc)" };

const OLIM_BGICON = `<svg class="olim-bgicon" viewBox="0 0 153 136" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M0 0L55.3618 16.4333V42.5L153 13.0333V52.7L55.3618 81.6V96.3333L153 66.8667V106.533L55.3618 136L54.8586 109.933L0 93.5V54.4L55.3618 70.2667V56.6667L0 39.6667V0Z" fill="rgba(255,255,255,0.18)"/></svg>`;

function olimCardHtml(o) {
  const ini = esc(initials(o.full_name));
  const photo = o.photo_file
    ? `<img class="olim-photo" src="photos/${esc(o.photo_file)}" alt="" onerror="this.outerHTML='<div class=&quot;olim-photo-fb&quot;>${ini}</div>'">`
    : `<div class="olim-photo-fb">${ini}</div>`;
  return `<article class="olim-card">${photo}<div class="olim-body">${OLIM_BGICON}<p class="olim-name">${esc(fmtName(o.full_name))}</p><p class="olim-sub">${esc(DEGREE_LBL[o.degree] || "")}</p></div></article>`;
}

function olimlarHtml(list) {
  if (!list || !list.length) return "";
  // Yarim lenta ekran enidan keng bo'lishi kerak — kam olim bo'lsa ro'yxatni takrorlaymiz
  const need = Math.ceil((window.innerWidth || 390) / 330) + 1;
  let half = [];
  while (half.length < Math.max(list.length, need)) half = half.concat(list);
  // cheksiz aylanish: yarim lenta 2 marta chiziladi; tezlik: har kartaga ~8s
  const dur = Math.max(30, half.length * 8);
  const cards = [...half, ...half].map(olimCardHtml).join("");
  return `
    <div class="olimlar-wrap">
      <div class="olimlar-head"><span class="dot"></span><h3>Tashkilot olimlari</h3></div>
      <div class="olimlar-slider"><div class="olimlar-track" style="animation-duration:${dur}s">${cards}</div></div>
    </div>`;
}

// Karuselni joyida (sahifani qayta chizmasdan) yangilash
async function refreshOlimlarStrip() {
  const list = await fetchOlimlar();
  const html = olimlarHtml(list);
  const cur = document.querySelector(".olimlar-wrap");
  if (cur) {
    if (html) cur.outerHTML = html; else cur.remove();
  } else if (html) {
    const stats = document.querySelector(".stats");
    if (stats) stats.insertAdjacentHTML("beforebegin", html);
  }
  bindOlimlarSlider();
}

// Olimlar karuseli — avtomat yuradi, lekin barmoq/sichqoncha bilan surish mumkin
let _olimRAF = null;
function bindOlimlarSlider() {
  if (_olimRAF) { cancelAnimationFrame(_olimRAF); _olimRAF = null; }
  const slider = document.querySelector(".olimlar-slider");
  const track = slider && slider.querySelector(".olimlar-track");
  if (!slider || !track) return;
  let dragging = false, paused = false, startX = 0, startScroll = 0, resumeTimer = null;
  let pos = slider.scrollLeft || 0;   // float hisoblagich (kasrli harakat yo'qolmasin)
  const half = () => track.scrollWidth / 2;
  const wrap = () => {
    const h = half();
    if (h > 0) { if (pos >= h) pos -= h; else if (pos < 0) pos += h; }
  };
  const pauseAuto = () => { paused = true; if (resumeTimer) clearTimeout(resumeTimer); };
  const resumeSoon = () => { if (resumeTimer) clearTimeout(resumeTimer); resumeTimer = setTimeout(() => { paused = false; }, 1600); };
  const step = () => {
    if (!paused && !dragging) {
      pos += 0.5;                     // ~30px/soniya avtomat aylanish
      wrap();
      slider.scrollLeft = pos;
    }
    _olimRAF = requestAnimationFrame(step);
  };
  // Sichqoncha bilan ushlab surish (desktop)
  slider.addEventListener("pointerdown", (e) => {
    if (e.pointerType !== "mouse") { pauseAuto(); return; } // touch — tabiiy scroll
    dragging = true; pauseAuto(); slider.classList.add("dragging");
    startX = e.clientX; startScroll = slider.scrollLeft;
    try { slider.setPointerCapture(e.pointerId); } catch (_) {}
  });
  slider.addEventListener("pointermove", (e) => {
    if (!dragging) return;
    e.preventDefault();
    slider.scrollLeft = startScroll - (e.clientX - startX);
  });
  const endDrag = () => {
    if (dragging) { dragging = false; slider.classList.remove("dragging"); }
    pos = slider.scrollLeft; wrap();   // qo'l harakatidan keyin hisoblagichni moslash
    resumeSoon();
  };
  slider.addEventListener("pointerup", endDrag);
  slider.addEventListener("pointercancel", endDrag);
  slider.addEventListener("pointerleave", () => { if (dragging) endDrag(); });
  // Barmoq bilan surish (mobil) — tabiiy scroll, faqat avto to'xtaydi
  slider.addEventListener("touchstart", pauseAuto, { passive: true });
  slider.addEventListener("touchend", () => { pos = slider.scrollLeft; resumeSoon(); }, { passive: true });
  _olimRAF = requestAnimationFrame(step);
}

async function fetchOlimlar() {
  const { status, data } = await api("/api/mobile/olimlar");
  const list = (status === 200 && data && data.olimlar) || [];
  olimMap = {};
  list.forEach(o => { olimMap[String(o.card_number)] = o.degree; });
  return list;
}

async function setOlim(card, degree) {
  const { status } = await api("/api/mobile/olimlar/set", { method: "POST", body: { card, degree } });
  return status === 200;
}

// ─────────── HR: Bosh / Xodimlar ───────────
let hrFilter = "inside"; // inside | lunch | out | late | absent
let searchQ = "";

async function viewHR(staffMode) {
  const __g = VIEW_GEN;   // eskirgan yuklash yangi bo'limni bosib ketmasin
  $("#app").innerHTML = shell(skeleton(6)); bindShell();
  const { status, data } = await api("/api/mobile/all");
  if (status === 403) { nav = "home"; return viewMe(); }
  if (status !== 200 || !data) { if (status === 401) return render(); return; }
  const reqRes = await api("/api/mobile/explain/requests");
  const allReqs = (reqRes.data && reqRes.data.requests) || [];
  const olimList = await fetchOlimlar();
  // Faqat BUGUNGI tushuntirish so'rovlari — har kechikish uchun yangi tushuntirish kerak.
  const _todayReq = todayISO();
  const reqMap = {};
  allReqs.forEach(r => { if (String(r.date || "") === _todayReq) reqMap[`${r.card_number}_${r.kind}`] = r; });

  const empMap = {};
  (data.employees || []).forEach(e2 => { empMap[String(e2.card_number)] = e2; });
  if (!store.photo && empMap[store.card] && empMap[store.card].photo_file)
    store.photo = empMap[store.card].photo_file;

  const lists = {
    inside: data.at_work || [], lunch: data.lunch || [], out: data.not_at_work || [],
    late: data.late || [], absent: data.absent || [],
    interns: data.interns || [], safari: data.safari || [], tatil: data.tatil || [],
  };
  const impliedSt = { inside: "ishda", lunch: "tushlikda", out: "ishda_emas", late: "", absent: "kelmagan" };

  const statsHtml = `
    <div class="stats">
      <div class="stat g ${!staffMode && hrFilter === "inside" ? "on" : ""}" data-f="inside"><div class="ico">💼</div><div class="n">${lists.inside.length}</div><div class="k">${t("c_inside").toUpperCase()}</div></div>
      <div class="stat a ${!staffMode && hrFilter === "lunch" ? "on" : ""}" data-f="lunch"><div class="ico">🍽</div><div class="n">${lists.lunch.length}</div><div class="k">${t("c_lunch").toUpperCase()}</div></div>
      <div class="stat ${!staffMode && hrFilter === "out" ? "on" : ""}" data-f="out"><div class="ico">🚶</div><div class="n">${lists.out.length}</div><div class="k">${t("c_out").toUpperCase()}</div></div>
      <div class="stat a ${!staffMode && hrFilter === "late" ? "on" : ""}" data-f="late"><div class="ico">⏰</div><div class="n">${lists.late.length}</div><div class="k">${t("c_late").toUpperCase()}</div></div>
      <div class="stat r ${!staffMode && hrFilter === "absent" ? "on" : ""}" data-f="absent"><div class="ico">✖️</div><div class="n">${lists.absent.length}</div><div class="k">${t("c_absent").toUpperCase()}</div></div>
    </div>
    <div class="chips">
      ${lists.interns.length ? `<button class="chip ${!staffMode && hrFilter === "interns" ? "on" : ""}" data-f="interns">🎓 ${t("c_interns")} · ${lists.interns.length}</button>` : ""}
      <button class="chip ${!staffMode && hrFilter === "safari" ? "on" : ""}" data-f="safari">✈️ ${t("c_safari")} · ${lists.safari.length}</button>
      <button class="chip ${!staffMode && hrFilter === "tatil" ? "on" : ""}" data-f="tatil">🏖 ${t("c_tatil")} · ${lists.tatil.length}</button>
    </div>`;

  const subText = (r, stKey, listKey) => {
    if (listKey === "safari" || listKey === "tatil") {
      const df = fmtDayMon(r.date_from), dt = fmtDayMon(r.date_to || r.date_from);
      const range = df ? `${df} → ${dt}` : "";
      return r.note ? `${range}${range ? " · " : ""}${esc(r.note)}` : range;
    }
    const cameT = timeShort(r.first_entry);
    if (stKey === "ishda_emas") {
      const leftT = timeShort(r.last_event_time || r.exit_time || r.since);
      if (leftT) return t("leftAt").replace("{t}", leftT);
    }
    if (!cameT) return "";
    return t("cameAt").replace("{t}", cameT);
  };

  const rowHtml = (r, listKey) => {
    const emp = empMap[String(r.card_number)] || r;
    const stKey = emp.status || impliedSt[listKey] || "ishda";
    const ring = listKey === "safari" ? "s" : listKey === "tatil" ? "a"
      : (RING[stKey] || "s");
    let right;
    if (listKey === "late" || listKey === "absent") {
      const key = `${r.card_number}_${listKey}`;
      const req = reqMap[key];
      if (req && req.status === "answered") right = `<button class="badge ok viewbtn" data-key="${esc(key)}">${t("expDone")}</button>`;
      else if (req && req.status === "pending") right = `<button class="badge out cancelbtn2" data-card="${esc(r.card_number)}" data-kind="${listKey}">${t("expAsked")} ✖</button>`;
      else right = `<button class="askbtn" data-card="${esc(r.card_number)}" data-kind="${listKey}">📝 ${t("expAsk")}</button>`;
    } else if (listKey === "safari") {
      right = `<span class="badge out">✈️</span>`;
    } else if (listKey === "tatil") {
      right = `<span class="badge late">🏖</span>`;
    } else if (listKey === "interns") {
      const inside = stKey === "ichkarida" || stKey === "ishda";
      right = `<span class="badge ${inside ? "ok" : "out"}">${inside ? t("c_inside") : t("c_out")}</span>`;
    } else {
      const b = BADGE[stKey] || BADGE.ishda;
      right = `<span class="badge ${b.cls}">${t(b.key)}</span>`;
    }
    // Izoh (HR yozgan) + uzrli belgisi — dashboard bilan bir xil
    const reasonHtml = r.reason
      ? `<div class="pi-reason">💬 ${esc(r.reason)}</div>` : "";
    const excusedHtml = r.excused
      ? `<span class="excused-tag">✓ ${t("excusedTag")}</span>` : "";
    return `
      <div class="pi clickable" data-card="${esc(r.card_number)}">
        <div class="ring ${ring}"><div class="av">${avatar(emp)}</div></div>
        <div class="nm"><b>${esc(fmtName(r.full_name || r.name) || "?")}${olimMap[String(r.card_number)] ? " 🎓" : ""}${excusedHtml}</b>
          <span>${subText(r, stKey, listKey)}</span>${reasonHtml}</div>
        ${right}
      </div>`;
  };

  const titleOf = () => staffMode
    ? `${t("allStaff")} · ${(data.employees || []).length}`
    : `${t("c_" + hrFilter)} · ${(lists[hrFilter] || []).length}`;

  const buildList = () => {
    const src = staffMode ? (data.employees || []) : (lists[hrFilter] || []);
    const listKey = staffMode ? "all" : hrFilter;
    const q = searchQ.trim().toLowerCase();
    const rows = q ? src.filter(r => String(r.full_name || "").toLowerCase().includes(q)) : src;
    return rows.length ? rows.map(r => rowHtml(r, listKey)).join("") : `<div class="empty">${t("nobody")}</div>`;
  };

  if (__g !== VIEW_GEN) return;
  $("#app").innerHTML = shell(`
    ${olimlarHtml(olimList)}
    ${statsHtml}
    <div class="search"><input id="sq" placeholder="${t("searchPh")}" value="${esc(searchQ)}"></div>
    <div class="sec">
      <h3 id="listTitle">${titleOf()}</h3>
      <div id="plist">${buildList()}</div>
    </div>
    <div class="foot">${t("updated")}: ${esc(timeShort(data.updated_at) || data.updated_at || "")}</div>
  `);
  bindShell();
  setNavBadge(allReqs.filter(r => r.status === "answered" && String(r.date || "") === todayISO()).length);
  refreshArizaBadge();
  bindOlimlarSlider();

  const bindList = () => {
    document.querySelectorAll("#plist .pi.clickable").forEach(row => {
      row.onclick = (ev) => {
        if (ev.target.closest(".askbtn") || ev.target.closest(".viewbtn")) return;
        const emp = empMap[row.dataset.card];
        if (emp) timelineModal(emp);
      };
    });
    document.querySelectorAll("#plist .viewbtn").forEach(b => {
      b.onclick = () => { const req = reqMap[b.dataset.key]; if (req) expModal(req); };
    });
    document.querySelectorAll("#plist .askbtn").forEach(b => {
      b.onclick = async () => {
        b.disabled = true; b.textContent = "…";
        const { status: st2, data: d2 } = await api("/api/mobile/explain/request", {
          method: "POST", body: { card: b.dataset.card, kind: b.dataset.kind },
        });
        if (st2 === 200) {
          reqMap[`${b.dataset.card}_${b.dataset.kind}`] = { status: "pending", req_id: (d2 && d2.req_id) || "" };
          $("#plist").innerHTML = buildList();
          bindList();
        } else {
          b.disabled = false; b.textContent = `📝 ${t("expAsk")}`;
          alert((d2 && d2.error) || t("expAskFail"));
        }
      };
    });
    // yuborilgan so'rovni qaytarib olish ("So'raldi ✖")
    document.querySelectorAll("#plist .cancelbtn2").forEach(b => {
      b.onclick = async (ev) => {
        ev.stopPropagation();
        if (!confirm(t("cancelConfirm"))) return;
        const key = `${b.dataset.card}_${b.dataset.kind}`;
        const req = reqMap[key] || {};
        const rid = req.req_id || `${todayISO()}_${b.dataset.card}_${b.dataset.kind}`;
        b.disabled = true;
        const { status: st2, data: d2 } = await api("/api/mobile/explain/cancel", {
          method: "POST", body: { req_id: rid },
        });
        if (st2 === 200) {
          delete reqMap[key];
          $("#plist").innerHTML = buildList();
          bindList();
        } else {
          b.disabled = false;
          alert((d2 && d2.error) || "Bekor qilinmadi");
        }
      };
    });
  };
  bindList();

  const applyFilter = (f, el) => {
    hrFilter = f;
    if (staffMode) { nav = "home"; render(); return; }
    document.querySelectorAll(".stat, .chip").forEach(x => x.classList.remove("on"));
    if (el) el.classList.add("on");
    $("#listTitle").textContent = titleOf();
    $("#plist").innerHTML = buildList();
    bindList();
  };
  document.querySelectorAll(".stat").forEach(sEl => {
    sEl.onclick = () => applyFilter(sEl.dataset.f, sEl);
  });
  document.querySelectorAll(".chip").forEach(cEl => {
    cEl.onclick = () => applyFilter(cEl.dataset.f, cEl);
  });
  $("#sq").oninput = (e) => {
    searchQ = e.target.value;
    $("#plist").innerHTML = buildList();
    bindList();
  };
}

// ─────────── HR: Tushuntirishlar ro'yxati (kunlik) ───────────
const todayISO = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};
let expDate = ""; // tanlangan kun (standart: bugun)

async function viewExpList() {
  const __g = VIEW_GEN;   // eskirgan yuklash yangi bo'limni bosib ketmasin
  $("#app").innerHTML = shell(skeleton(4)); bindShell();
  const { status, data } = await api("/api/mobile/explain/requests");
  if (status === 403) { nav = "home"; return render(); }
  if (status !== 200 || !data) { if (status === 401) return render(); return; }
  if (!expDate) expDate = todayISO();
  const all = (data.requests || []);
  // faqat tanlangan kunning so'rovlari ko'rsatiladi
  const reqs = all.filter(r => String(r.date || "") === expDate).sort((a, b) =>
    String(b.requested_at || "").localeCompare(String(a.requested_at || "")));
  const isToday = expDate === todayISO();
  const rows = reqs.length ? reqs.map(r => `
    <div class="pi ${r.status === "answered" ? "clickable" : ""}" data-rid="${esc(r.req_id)}">
      <div class="nm"><b>${esc(fmtName(r.full_name) || r.card_number)}</b>
        <span>${expKindName(r.kind)} · ${esc(r.date || "")}</span></div>
      ${r.status === "answered"
        ? `<span class="badge ok">${r.self ? t("selfWrote") : t("expDone")}</span>`
        : `<button class="badge late cancelbtn" data-rid="${esc(r.req_id)}">${t("expWait")} ✖</button>`}
    </div>`).join("") : `<div class="empty">${t("noExp")}</div>`;
  if (__g !== VIEW_GEN) return;
  $("#app").innerHTML = shell(`
    <div class="sec" style="margin-top:14px">
      <div class="exp-head">
        <h3>${t("expListTitle")} · ${reqs.length}</h3>
        <div class="expdate">
          <input type="date" id="expDateInp" value="${esc(expDate)}" max="${todayISO()}">
          ${isToday ? `<span class="expdate-today">bugun</span>` : `<button class="expdate-reset" id="expToday">bugunga</button>`}
        </div>
      </div>
      ${rows}
    </div>`);
  bindShell();
  setNavBadge(all.filter(r => r.status === "answered" && String(r.date || "") === todayISO()).length);
  const byId = {};
  reqs.forEach(r => { byId[r.req_id] = r; });
  document.querySelectorAll(".pi.clickable").forEach(row => {
    row.onclick = () => { const r = byId[row.dataset.rid]; if (r) expModal(r); };
  });
  // kutilayotgan so'rovni qaytarib olish
  document.querySelectorAll(".cancelbtn").forEach(b => {
    b.onclick = async (ev) => {
      ev.stopPropagation();
      if (!confirm(t("cancelConfirm"))) return;
      b.disabled = true;
      const { status: st2, data: d2 } = await api("/api/mobile/explain/cancel", {
        method: "POST", body: { req_id: b.dataset.rid },
      });
      if (st2 === 200) viewExpList();
      else { b.disabled = false; alert((d2 && d2.error) || "Bekor qilinmadi"); }
    };
  });
  const inp = $("#expDateInp");
  if (inp) inp.onchange = () => { if (inp.value) { expDate = inp.value; viewExpList(); } };
  const tb = $("#expToday");
  if (tb) tb.onclick = () => { expDate = todayISO(); viewExpList(); };
}

// ═════════════════════════ HR BOSHQARUV (admin) ═════════════════════════
let admSection = "menu";   // menu | broadcast | exempt | reason | exit_reason | late | holidays | hidden | worktime | expl | monitor
let admEmployees = [];      // {card_number, full_name, ...} — picker uchun
const admToast = (msg, ok = true) => {
  const el = document.createElement("div");
  el.className = "adm-toast " + (ok ? "ok" : "err");
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 2600);
};

async function admLoadEmployees() {
  if (admEmployees.length) return admEmployees;
  const { status, data } = await api("/api/mobile/all");
  if (status === 200 && data) admEmployees = (data.employees || []).slice();
  return admEmployees;
}

// Xodim tanlash inputi (datalist bilan). Qaytaradi: input id -> card
function admEmpPickerHtml(id) {
  const opts = admEmployees.map(e =>
    `<option value="${esc(fmtName(e.full_name))} — ${esc(e.card_number)}"></option>`).join("");
  return `<input class="adm-inp" id="${id}" list="${id}_dl" placeholder="${t("admPickEmp")}" autocomplete="off">
    <datalist id="${id}_dl">${opts}</datalist>`;
}
function admPickedCard(id) {
  const v = ($("#" + id) || {}).value || "";
  const m = v.match(/—\s*(\d{6,})\s*$/);
  if (m) return m[1];
  // faqat raqam kiritilgan bo'lsa
  const only = v.trim();
  if (/^\d{6,}$/.test(only)) return only;
  // ism bo'yicha topish
  const q = only.toLowerCase();
  const hit = admEmployees.find(e => fmtName(e.full_name).toLowerCase() === q);
  return hit ? hit.card_number : "";
}

const ADM_TILES = [
  { id: "exempt", ico: "🗂", key: "admExempt" },
  { id: "reason", ico: "📝", key: "admReason" },
  { id: "exit_reason", ico: "🚪", key: "admExitReason" },
  { id: "late", ico: "⏰", key: "admLate" },
  { id: "holidays", ico: "🎉", key: "admHolidays" },
  { id: "hidden", ico: "👁", key: "admHidden" },
  { id: "worktime", ico: "🕐", key: "admWorktime" },
  { id: "photo", ico: "📷", key: "admPhoto" },
  { id: "olim", ico: "🎓", key: "admOlim" },
  { id: "exit", ico: "🚪", key: "admExitReasons" },
  { id: "resetpw", ico: "🔓", key: "admResetPw" },
  { id: "yoqlama", ico: "✅", key: "yqTitle" },
  { id: "reyting", ico: "🏆", key: "admRating", view: true },
  { id: "latelist", ico: "⏰", key: "admLateList", view: true },
  { id: "empadd", ico: "👤", key: "admEmpAdd" },
  { id: "newacc", ico: "🆕", key: "admNewAcc" },
  { id: "accounts", ico: "🗑", key: "admAccounts" },
  { id: "empout", ico: "🚫", key: "admEmpOut" },
  { id: "expl", ico: "📋", key: "admExpl" },
  { id: "monitor", ico: "📡", key: "admMonitor" },
  { id: "attedit", ico: "🛠", key: "admAttEdit", superOnly: true },
];

async function viewAdmin() {
  const __g = VIEW_GEN;
  $("#app").innerHTML = shell(skeleton(3)); bindShell();
  await admLoadEmployees();
  if (__g !== VIEW_GEN) return;
  if (admSection === "menu") return admRenderMenu();
  return admRenderSection();
}

async function admRenderMenu() {
  const viewOnly = !isAdminRole();
  const list = (viewOnly ? ADM_TILES.filter(x => x.view) : ADM_TILES)
    .filter(x => !x.superOnly || store.role === "super_admin");
  const ov = viewOnly ? {} : ((await api("/api/mobile/admin/overview")).data || {});
  const badges = {
    monitor: ov.monitor_enabled ? t("admOnn") : t("admOff"),
    holidays: ov.holidays_count || 0,
    exempt: ov.active_exemptions || 0,
    expl: ov.pending_explanations || 0,
  };
  const tiles = list.map(x => {
    let sub = "";
    if (x.id === "monitor") sub = `<span class="adm-tb">${badges.monitor}</span>`;
    else if (x.id === "holidays" && badges.holidays) sub = `<span class="adm-tb">${badges.holidays}</span>`;
    else if (x.id === "exempt" && badges.exempt) sub = `<span class="adm-tb">${badges.exempt}</span>`;
    else if (x.id === "expl" && badges.expl) sub = `<span class="adm-tb warn">${badges.expl}</span>`;
    return `<div class="adm-tile" data-sec="${x.id}">
      <div class="adm-ico">${x.ico}</div><div class="adm-lbl">${t(x.key)}</div>${sub}</div>`;
  }).join("");
  $("#app").innerHTML = shell(`
    <div class="sec" style="margin-top:14px">
      <h3>${t(viewOnly ? "repTitle" : "admTitle")}</h3>
      <div class="adm-grid">${tiles}</div>
    </div>`);
  bindShell();
  document.querySelectorAll(".adm-tile").forEach(el =>
    el.onclick = () => { admSection = el.dataset.sec; viewAdmin(); });
}

function admBackHead(titleKey) {
  return `<div class="adm-head">
    <button class="adm-back" id="admBack">‹</button>
    <h3>${t(titleKey)}</h3></div>`;
}
function admBindBack() {
  const b = $("#admBack");
  if (b) b.onclick = () => { admSection = "menu"; viewAdmin(); };
}

async function admRenderSection() {
  const map = {
    broadcast: admSecBroadcast, exempt: admSecExempt, reason: () => admSecReason(false),
    exit_reason: () => admSecReason(true), late: admSecLate, holidays: admSecHolidays,
    hidden: admSecHidden, worktime: admSecWorktime, photo: admSecPhoto, olim: admSecOlim,
    interns: admSecInterns, exit: admSecExitReasons, resetpw: admSecResetPw, newacc: admSecNewAcc, accounts: admSecAccounts, empadd: admSecEmpAdd, empout: admSecEmpOut, latelist: admSecLateList, reyting: admSecRating, survey: admSecSurvey, yoqlama: admSecYoqlama,
    expl: admSecExpl, monitor: admSecMonitor, attedit: admSecAttendanceEdit,
  };
  // Rahbariyat faqat ko'rish bo'limlarini ocha oladi
  if (!isAdminRole()) {
    const allowed = ADM_TILES.filter(x => x.view).map(x => x.id);
    if (!allowed.includes(admSection)) { admSection = "menu"; return viewAdmin(); }
  } else if (admSection === "attedit" && store.role !== "super_admin") {
    admSection = "menu"; return viewAdmin();
  }
  const fn = map[admSection];
  if (!fn) { admSection = "menu"; return viewAdmin(); }
  return fn();
}

// ─── Xabar yuborish ───
function admSecBroadcast() {
  $("#app").innerHTML = shell(`
    ${admBackHead("admBroadcast")}
    <div class="sec">
      <p class="adm-hint">${t("admBroadcastHint")}</p>
      <textarea class="adm-inp adm-ta" id="bcText" rows="5" placeholder="…"></textarea>
      <button class="btn adm-primary" id="bcSend">${t("admSend")}</button>
    </div>`);
  bindShell(); admBindBack();
  $("#bcSend").onclick = async () => {
    const text = ($("#bcText").value || "").trim();
    if (text.length < 3) return admToast(t("admFail"), false);
    const btn = $("#bcSend"); btn.disabled = true; btn.textContent = "…";
    const { status, data } = await api("/api/mobile/admin/broadcast", { method: "POST", body: { text } });
    btn.disabled = false; btn.textContent = t("admSend");
    if (status === 200 && data) {
      admToast(t("admSentRes").replace("{s}", data.sent).replace("{f}", data.failed));
      $("#bcText").value = "";
    } else admToast((data && data.error) || t("admFail"), false);
  };
}

// ─── Ruxsat & Safari ───
async function admSecExempt() {
  $("#app").innerHTML = shell(skeleton(3)); bindShell();
  const { data } = await api("/api/mobile/admin/exemptions");
  const active = (data && data.active) || [];
  const upcoming = (data && data.upcoming) || [];
  const tIcon = (ty) => ty === "safari" ? "✈️" : ty === "tadbir" ? "🎤" : "🏖";
  const recRow = (r) => `<div class="adm-row">
    <div class="adm-rmain"><b>${esc(fmtName(r.full_name) || r.card_number)}</b>
      <span>${tIcon(r.type)} ${esc(r.date_from)} → ${esc(r.date_to)}${r.note ? " · " + esc(r.note) : ""}</span></div>
    <button class="adm-del" data-id="${esc(r.id)}">✕</button></div>`;
  const listHtml = (arr, titleKey) => arr.length
    ? `<div class="adm-sub">${t(titleKey)}</div>` + arr.map(recRow).join("") : "";
  const today = todayISO();
  $("#app").innerHTML = shell(`
    ${admBackHead("admExempt")}
    <div class="sec">
      <div class="adm-seg" id="exType">
        <button class="on" data-v="ruxsat">${t("admTypeRuxsat")}</button>
        <button data-v="safari">${t("admTypeSafari")}</button>
        <button data-v="tadbir">${t("admTypeTadbir")}</button>
      </div>
      <div id="exPickOne">${admEmpPickerHtml("exCard")}</div>
      <div id="exPickMany" style="display:none">
        <p class="adm-hint">${t("admTadbirHint")}</p>
        <input class="adm-inp" id="exQ" placeholder="${t("admSearchEmp")}">
        <div id="exList" class="adm-multilist"></div>
        <div class="adm-sub" id="exSelCount">${t("admSelected")}: 0</div>
      </div>
      <div class="adm-2col">
        <label>${t("admFrom")}<input type="date" class="adm-inp" id="exFrom" value="${today}"></label>
        <label>${t("admTo")}<input type="date" class="adm-inp" id="exTo" value="${today}"></label>
      </div>
      <input class="adm-inp" id="exNote" placeholder="${t("admNote")}">
      <button class="btn adm-primary" id="exAdd">${t("admAdd")}</button>
    </div>
    <div class="sec">
      ${(active.length || upcoming.length) ? listHtml(active, "admActive") + listHtml(upcoming, "admUpcoming")
        : `<div class="empty">${t("admEmptyList")}</div>`}
    </div>`);
  bindShell(); admBindBack();
  let exType = "ruxsat";
  const picked = new Set();   // tadbir uchun ko'p tanlov

  const drawMany = () => {
    const q = (($("#exQ") || {}).value || "").trim().toLowerCase();
    const list = admEmployees.filter(e => !q || fmtName(e.full_name).toLowerCase().includes(q)
      || String(e.card_number).includes(q));
    $("#exList").innerHTML = list.map(e => {
      const c = String(e.card_number);
      return `<label class="adm-chk"><input type="checkbox" data-c="${esc(c)}"${picked.has(c) ? " checked" : ""}>
        <span>${esc(fmtName(e.full_name))}</span></label>`;
    }).join("") || `<div class="empty">—</div>`;
    document.querySelectorAll("#exList input[type=checkbox]").forEach(cb => cb.onchange = () => {
      const c = cb.dataset.c;
      cb.checked ? picked.add(c) : picked.delete(c);
      $("#exSelCount").textContent = `${t("admSelected")}: ${picked.size}`;
    });
    $("#exSelCount").textContent = `${t("admSelected")}: ${picked.size}`;
  };

  document.querySelectorAll("#exType button").forEach(b => b.onclick = () => {
    exType = b.dataset.v;
    document.querySelectorAll("#exType button").forEach(x => x.classList.toggle("on", x === b));
    const many = exType === "tadbir";
    $("#exPickOne").style.display = many ? "none" : "";
    $("#exPickMany").style.display = many ? "" : "none";
    if (many) { drawMany(); $("#exQ").oninput = drawMany; }
  });

  $("#exAdd").onclick = async () => {
    const body0 = { type: exType, date_from: $("#exFrom").value, date_to: $("#exTo").value, note: $("#exNote").value };
    if (exType === "tadbir") {
      if (!picked.size) return admToast(t("admPickNone"), false);
      const btn = $("#exAdd"); btn.disabled = true; btn.textContent = "…";
      let ok = 0, fail = 0;
      for (const card of picked) {
        const { status } = await api("/api/mobile/admin/exemptions/add", { method: "POST", body: { ...body0, card } });
        status === 200 ? ok++ : fail++;
      }
      btn.disabled = false; btn.textContent = t("admAdd");
      admToast(`${t("admDone")} · ${ok}${fail ? " / " + fail + " ✕" : ""}`, !fail);
      return admSecExempt();
    }
    const card = admPickedCard("exCard");
    if (!card) return admToast(t("admPickEmp"), false);
    const { status, data: d } = await api("/api/mobile/admin/exemptions/add", { method: "POST", body: { ...body0, card } });
    if (status === 200) { admToast(t("admDone")); admSecExempt(); }
    else admToast((d && d.error) || t("admFail"), false);
  };
  document.querySelectorAll(".adm-del").forEach(b => b.onclick = async () => {
    const { status } = await api("/api/mobile/admin/exemptions/remove", { method: "POST", body: { id: b.dataset.id } });
    if (status === 200) { admToast(t("admDone")); admSecExempt(); } else admToast(t("admFail"), false);
  });
}

// ─── Izoh / Chiqqanlar izohi ───
async function admSecReason(isExit) {
  $("#app").innerHTML = shell(skeleton(3)); bindShell();
  const { data } = await api("/api/mobile/admin/reasons");
  const store2 = (data && (isExit ? data.exit_reasons : data.reasons)) || {};
  const endpoint = isExit ? "/api/mobile/admin/exit_reason" : "/api/mobile/admin/reason";
  const titleKey = isExit ? "admExitReason" : "admReason";
  const rows = Object.entries(store2).map(([card, info]) => `<div class="adm-row">
    <div class="adm-rmain"><b>${esc(fmtName(info.full_name) || card)}</b><span>${esc(info.text)}</span></div>
    <button class="adm-del" data-card="${esc(card)}">✕</button></div>`).join("");
  $("#app").innerHTML = shell(`
    ${admBackHead(titleKey)}
    <div class="sec">
      <p class="adm-hint">${t("admReasonHint")}</p>
      ${admEmpPickerHtml("rsCard")}
      <input class="adm-inp" id="rsText" placeholder="${t("admReason")}…">
      <button class="btn adm-primary" id="rsSave">${t("admSave")}</button>
    </div>
    <div class="sec">${rows || `<div class="empty">${t("admEmptyList")}</div>`}</div>`);
  bindShell(); admBindBack();
  $("#rsSave").onclick = async () => {
    const card = admPickedCard("rsCard");
    if (!card) return admToast(t("admPickEmp"), false);
    const { status } = await api(endpoint, { method: "POST", body: { card, text: $("#rsText").value } });
    if (status === 200) { admToast(t("admDone")); admSecReason(isExit); } else admToast(t("admFail"), false);
  };
  document.querySelectorAll(".adm-del").forEach(b => b.onclick = async () => {
    const { status } = await api(endpoint, { method: "POST", body: { card: b.dataset.card, text: "" } });
    if (status === 200) { admToast(t("admDone")); admSecReason(isExit); } else admToast(t("admFail"), false);
  });
}

// ─── Kechikish uzrli (toggle) ───
async function admSecLate() {
  $("#app").innerHTML = shell(skeleton(3)); bindShell();
  const { data } = await api("/api/mobile/all");
  const exRes = await api("/api/mobile/admin/late_excused");
  const exSet = new Set(((exRes.data && exRes.data.excused) || []).map(String));
  const late = ((data && data.late) || []).map(r => ({ ...r, late_excused: exSet.has(String(r.card_number)) }));
  const rows = late.length ? late.map(r => `<div class="adm-row">
    <div class="adm-rmain"><b>${esc(fmtName(r.full_name) || r.card_number)}</b>
      <span>${timeShort(r.first_entry) ? t("cameAt").replace("{t}", timeShort(r.first_entry)) : ""}</span></div>
    <button class="adm-toggle ${r.late_excused ? "on" : ""}" data-card="${esc(r.card_number)}">
      ${r.late_excused ? t("admExcused") : t("admNotExcused")}</button></div>`).join("")
    : `<div class="empty">${t("nobody")}</div>`;
  $("#app").innerHTML = shell(`${admBackHead("admLate")}<div class="sec">${rows}</div>`);
  bindShell(); admBindBack();
  document.querySelectorAll(".adm-toggle").forEach(b => b.onclick = async () => {
    b.disabled = true;
    const { status, data: d } = await api("/api/mobile/admin/late_excused", { method: "POST", body: { card: b.dataset.card } });
    b.disabled = false;
    if (status === 200 && d) {
      b.classList.toggle("on", d.excused);
      b.textContent = d.excused ? t("admExcused") : t("admNotExcused");
      admToast(t("admDone"));
    } else admToast(t("admFail"), false);
  });
}

// ─── Bayramlar ───
async function admSecHolidays() {
  $("#app").innerHTML = shell(skeleton(3)); bindShell();
  const { data } = await api("/api/mobile/admin/holidays");
  const items = (data && data.holidays) || [];
  const rows = items.length ? items.map(h => `<div class="adm-row">
    <div class="adm-rmain"><b>${esc(h.date)}</b><span>${esc(h.name)}</span></div>
    <button class="adm-del" data-date="${esc(h.date)}">✕</button></div>`).join("")
    : `<div class="empty">${t("admEmptyList")}</div>`;
  $("#app").innerHTML = shell(`
    ${admBackHead("admHolidays")}
    <div class="sec">
      <input type="date" class="adm-inp" id="holDate" value="${todayISO()}">
      <input class="adm-inp" id="holName" placeholder="${t("admHolName")}">
      <button class="btn adm-primary" id="holAdd">${t("admAdd")}</button>
    </div>
    <div class="sec">${rows}</div>`);
  bindShell(); admBindBack();
  $("#holAdd").onclick = async () => {
    const { status } = await api("/api/mobile/admin/holidays/add", { method: "POST", body: { date: $("#holDate").value, name: $("#holName").value } });
    if (status === 200) { admToast(t("admDone")); admSecHolidays(); } else admToast(t("admFail"), false);
  };
  document.querySelectorAll(".adm-del").forEach(b => b.onclick = async () => {
    const { status } = await api("/api/mobile/admin/holidays/remove", { method: "POST", body: { date: b.dataset.date } });
    if (status === 200) { admToast(t("admDone")); admSecHolidays(); } else admToast(t("admFail"), false);
  });
}

// ─── Dashboard ko'rinish (yashirish) ───
async function admSecHidden() {
  $("#app").innerHTML = shell(skeleton(3)); bindShell();
  const [{ data: hd }] = [await api("/api/mobile/admin/hidden")];
  const hidden = (hd && hd.hidden) || [];
  const hiddenSet = new Set(hidden.map(h => String(h.card)));
  const rows = hidden.length ? hidden.map(h => `<div class="adm-row">
    <div class="adm-rmain"><b>${esc(fmtName(h.full_name) || h.card)}</b><span>${t("admToggleShow")}?</span></div>
    <button class="adm-toggle on" data-card="${esc(h.card)}">${t("admToggleShow")}</button></div>`).join("") : "";
  $("#app").innerHTML = shell(`
    ${admBackHead("admHidden")}
    <div class="sec">
      ${admEmpPickerHtml("hdCard")}
      <button class="btn adm-primary" id="hdAdd">${t("admToggleHide")}</button>
    </div>
    <div class="sec">${rows || `<div class="empty">${t("admEmptyList")}</div>`}</div>`);
  bindShell(); admBindBack();
  const toggle = async (card) => {
    const { status } = await api("/api/mobile/admin/hidden/toggle", { method: "POST", body: { card } });
    if (status === 200) { admToast(t("admDone")); admSecHidden(); } else admToast(t("admFail"), false);
  };
  $("#hdAdd").onclick = () => {
    const card = admPickedCard("hdCard");
    if (!card) return admToast(t("admPickEmp"), false);
    if (hiddenSet.has(String(card))) return admToast(t("admDone"));
    toggle(card);
  };
  document.querySelectorAll(".adm-toggle").forEach(b => b.onclick = () => toggle(b.dataset.card));
}

// ─── Ish vaqti override ───
async function admSecWorktime() {
  $("#app").innerHTML = shell(skeleton(3)); bindShell();
  const { data } = await api("/api/mobile/admin/worktime");
  const items = (data && data.overrides) || [];
  const rows = items.length ? items.map(o => `<div class="adm-row">
    <div class="adm-rmain"><b>${esc(fmtName(o.full_name) || o.card)}</b><span>🕐 ${esc(o.time)}</span></div>
    <button class="adm-del" data-card="${esc(o.card)}">✕</button></div>`).join("")
    : `<div class="empty">${t("admEmptyList")}</div>`;
  $("#app").innerHTML = shell(`
    ${admBackHead("admWorktime")}
    <div class="sec">
      <p class="adm-hint">${t("admWtHint")}</p>
      ${admEmpPickerHtml("wtCard")}
      <input class="adm-inp" id="wtTime" type="time" value="09:00">
      <button class="btn adm-primary" id="wtSave">${t("admSave")}</button>
    </div>
    <div class="sec">${rows}</div>`);
  bindShell(); admBindBack();
  $("#wtSave").onclick = async () => {
    const card = admPickedCard("wtCard");
    if (!card) return admToast(t("admPickEmp"), false);
    const { status } = await api("/api/mobile/admin/worktime/set", { method: "POST", body: { card, time: $("#wtTime").value } });
    if (status === 200) { admToast(t("admDone")); admSecWorktime(); } else admToast(t("admFail"), false);
  };
  document.querySelectorAll(".adm-del").forEach(b => b.onclick = async () => {
    const { status } = await api("/api/mobile/admin/worktime/set", { method: "POST", body: { card: b.dataset.card, time: "" } });
    if (status === 200) { admToast(t("admDone")); admSecWorktime(); } else admToast(t("admFail"), false);
  });
}

// ─── Amaliyotchilar (faol / faol emas) ───
async function admSecInterns() {
  $("#app").innerHTML = shell(skeleton(4)); bindShell();
  const { data } = await api("/api/mobile/admin/interns");
  const items = (data && data.interns) || [];
  const dmy = (s) => s ? s.slice(8, 10) + "." + s.slice(5, 7) : "";
  const why = (r) => r.reason === "auto"
      ? `🤖 Avtomatik: ${(data && data.auto_days) || 10} kundan beri kelmagan${r.last_seen ? ` (oxirgi: ${dmy(r.last_seen)})` : ""}`
    : r.reason === "manual" ? "✋ HR tomonidan nofaol qilingan"
    : r.reason === "xlsx" ? "📄 interns.xlsx da nofaol"
    : `${t("admInternActive")}${r.last_seen ? ` · oxirgi kelgan: ${dmy(r.last_seen)}` : ""}`;
  // Tartib: faollar, keyin avtomatik, keyin qo'lda nofaol
  const ord = { "": 0, auto: 1, manual: 2, xlsx: 3 };
  items.sort((a, b) => (ord[a.reason || ""] - ord[b.reason || ""]) || String(a.full_name).localeCompare(String(b.full_name)));
  const rows = items.length ? items.map(r => `<div class="adm-row">
      <div class="adm-rmain"><b>${esc(fmtName(r.full_name) || r.card)}</b>
        <span>${esc(why(r))}</span></div>
      <button class="adm-toggle ${r.active ? "on" : ""}" data-card="${esc(r.card)}" data-active="${r.active ? 1 : 0}">
        ${r.active ? t("admInternActive") : t("admInternInactive")}</button></div>`).join("")
    : `<div class="empty">${t("admEmptyList")}</div>`;
  $("#app").innerHTML = shell(`
    ${admBackHead("admInterns")}
    <div class="sec">
      <p class="adm-hint">${t("admInternHint")}</p>
      <p class="adm-hint">🤖 ${(data && data.auto_days) || 10} kun ichida turniketdan o'tmagan amaliyotchi avtomatik nofaol bo'ladi
        va qaytib kelganda o'zi faollashadi. Qayta faol qilsangiz — shu kundan yana ${(data && data.auto_days) || 10} kun sanaladi.</p>
      <div class="adm-sub">${t("admInternActive")}: ${(data && data.active) || 0} / ${(data && data.count) || 0}</div>
      ${rows}
    </div>`);
  bindShell(); admBindBack();
  document.querySelectorAll(".adm-toggle").forEach(b => b.onclick = async () => {
    const cur = b.dataset.active === "1";
    b.disabled = true;
    const { status } = await api("/api/mobile/admin/intern_active", {
      method: "POST", body: { card: b.dataset.card, active: !cur },
    });
    if (status === 200) { admToast(t("admDone")); admSecInterns(); }
    else { b.disabled = false; admToast(t("admFail"), false); }
  });
}

// ─── Parol tiklash (xodim parolini unutganda) ───
async function admSecResetPw() {
  await admLoadEmployees();
  $("#app").innerHTML = shell(`
    ${admBackHead("admResetPw")}
    <div class="sec">
      <p class="adm-hint">${t("admResetHint")}</p>
      ${admEmpPickerHtml("rpCard")}
      <button class="btn adm-primary" id="rpBtn">${t("admResetBtn")}</button>
      <div id="rpResult"></div>
    </div>`);
  bindShell(); admBindBack();
  $("#rpBtn").onclick = async () => {
    const card = admPickedCard("rpCard");
    if (!card) return admToast(t("admPickEmp"), false);
    const btn = $("#rpBtn"); btn.disabled = true; btn.textContent = "…";
    const { status, data } = await api("/api/mobile/admin/reset_password", { method: "POST", body: { card } });
    btn.disabled = false; btn.textContent = t("admResetBtn");
    if (status === 200 && data) {
      $("#rpResult").innerHTML = `<div class="exp-ok" style="margin-top:12px;font-size:15px">
        ${t("admResetDone")} <b style="font-size:22px;letter-spacing:2px">${esc(data.password)}</b></div>`;
      admToast(t("admDone"));
    } else admToast((data && data.error) || t("admFail"), false);
  };
}

// ─── Yangi xodim hisobi (qo'lда, PINFL orqali) ───
async function admSecNewAcc() {
  $("#app").innerHTML = shell(`
    ${admBackHead("admNewAcc")}
    <div class="sec">
      <p class="adm-hint">${t("admNewAccHint")}</p>
      <input class="adm-inp" id="naPin" inputmode="numeric" maxlength="14" placeholder="${t("admNewAccPin")}">
      <input class="adm-inp" id="naName" style="margin-top:8px" placeholder="${t("admNewAccName")}">
      <button class="btn adm-primary" id="naBtn" style="margin-top:10px">${t("admNewAccBtn")}</button>
      <div id="naResult"></div>
    </div>`);
  bindShell(); admBindBack();
  $("#naBtn").onclick = async () => {
    const card = ($("#naPin").value || "").replace(/\D/g, "");
    const name = ($("#naName").value || "").trim();
    if (card.length < 6) return admToast(t("admNewAccPin"), false);
    const btn = $("#naBtn"); btn.disabled = true; btn.textContent = "…";
    const { status, data } = await api("/api/mobile/admin/create_account", { method: "POST", body: { card, name } });
    btn.disabled = false; btn.textContent = t("admNewAccBtn");
    if (status === 200 && data) {
      $("#naResult").innerHTML = `<div class="exp-ok" style="margin-top:12px;font-size:15px">
        ${esc(data.name || "")}<br>${t("admNewAccDone")} <b>${esc(data.card)}</b><br>
        ${t("admNewAccPass")} <b style="font-size:22px;letter-spacing:2px">${esc(data.password)}</b></div>`;
      admToast(t("admDone"));
    } else admToast((data && data.error) || t("admFail"), false);
  };
}

// ═══════════════ YO'QLAMA (HR) ═══════════════
// 1) Tadbir nomini yozish  2) Ro'yxatni belgilash  3) Word/PDF yuklab olish

async function admSecYoqlama() {
  $("#app").innerHTML = shell(skeleton(3)); bindShell();
  const { data } = await api("/api/mobile/admin/yoqlama");
  const items = (data && data.items) || [];
  const today = todayISO();
  const prev = items.length
    ? items.map(x => `<div class="pi clickable yq-item" data-id="${esc(x.id)}">
        <div class="nm"><b>${esc(x.title)}</b>
          <span>${esc(fmtDayMon(x.date))}${x.time ? " · " + esc(x.time) : ""}</span></div>
        <span class="badge ok">${x.yes}/${x.total}</span></div>`).join("")
    : `<div class="empty">${t("yqNone")}</div>`;

  $("#app").innerHTML = shell(`
    ${admBackHead("yqTitle")}
    <div class="sec">
      <p class="adm-hint">${t("yqHint")}</p>
      <input class="adm-inp" id="yqName" placeholder="${t("yqName")}">
      <div class="adm-2col" style="margin-top:8px">
        <label>${t("yqDate")}<input type="date" class="adm-inp" id="yqDate" value="${today}"></label>
        <label>${t("yqTime")}<input class="adm-inp" id="yqTime" placeholder="15:00"></label>
      </div>
      <input class="adm-inp" id="yqPlace" style="margin-top:8px" placeholder="${t("yqPlace")}">
      <button class="btn adm-primary" id="yqGo" style="margin-top:10px">${t("yqOpen")}</button>
    </div>
    <div class="sec">
      <div class="adm-sub">${t("yqPrev")}</div>
      ${prev}
    </div>`);
  bindShell(); admBindBack();

  $("#yqGo").onclick = async () => {
    const title = ($("#yqName").value || "").trim();
    if (title.length < 3) return admToast(t("yqNameShort"), false);
    const b = $("#yqGo"); b.disabled = true; b.textContent = "…";
    const { status, data: d } = await api("/api/mobile/admin/yoqlama/create", {
      method: "POST",
      body: { title, date: $("#yqDate").value, time: ($("#yqTime").value || "").trim(),
              place: ($("#yqPlace").value || "").trim() },
    });
    b.disabled = false; b.textContent = t("yqOpen");
    if (status === 200 && d && d.id) admYoqlamaEdit(d.id);
    else admToast((d && d.error) || t("admFail"), false);
  };
  document.querySelectorAll(".yq-item").forEach(el =>
    el.onclick = () => admYoqlamaEdit(el.dataset.id));
}

// ─── Ro'yxatni belgilash ───
let _yqMarks = {}, _yqItem = null, _yqQ = "";

async function admYoqlamaEdit(yid) {
  $("#app").innerHTML = shell(skeleton(4)); bindShell();
  const { status, data } = await api(`/api/mobile/admin/yoqlama/${encodeURIComponent(yid)}`);
  if (status !== 200 || !data || !data.item) { admToast(t("admFail"), false); return admSecYoqlama(); }
  _yqItem = data.item;
  _yqMarks = Object.assign({}, _yqItem.marks || {});
  _yqQ = "";
  yqRender();
}

function yqRender() {
  const it = _yqItem;
  const emps = it.employees || [];
  const total = emps.length;
  const yes = emps.filter(e => _yqMarks[e.card_number]).length;
  const q = _yqQ.trim().toLowerCase();
  const list = emps.filter(e => !q || fmtName(e.full_name).toLowerCase().includes(q)
    || String(e.card_number).includes(q));

  $("#app").innerHTML = shell(`
    <div class="adm-head"><button class="adm-back" id="admBack">‹</button>
      <h2>${esc(it.title)}</h2></div>
    <div class="sec">
      <div class="adm-sub">${esc(fmtDayMon(it.date))}${it.time ? " · " + esc(it.time) : ""}${it.place ? " · " + esc(it.place) : ""}</div>
      <div class="tiles" style="margin-top:8px">
        <div class="tile"><div class="n">${total}</div><div class="k">${t("yqAll")}</div></div>
        <div class="tile" style="background:var(--ok-bg)"><div class="n" id="yqCntY">${yes}</div><div class="k">${t("yqYes")}</div></div>
        <div class="tile warn"><div class="n" id="yqCntN">${total - yes}</div><div class="k">${t("yqNo")}</div></div>
      </div>
      <input class="adm-inp" id="yqQ" style="margin-top:10px" placeholder="${t("admSearchEmp")}" value="${esc(_yqQ)}">
      <div id="yqList" class="yq-list">${yqRows(list)}</div>
      <button class="btn adm-primary" id="yqSave" style="margin-top:10px">${t("yqSave")}</button>
    </div>
    <div class="sec">
      <div class="adm-sub">${t("yqConductor")}</div>
      <p class="adm-hint">${t("yqConductorHint")}</p>
      ${admEmpPickerHtml("yqWho")}
      ${it.conductor ? `<div class="yq-signed">✓ ${esc(fmtName(it.conductor.full_name))}${it.signature_file ? " · " + t("yqSignedOk") : ""}</div>` : ""}
      ${sigPadHtml()}
      <button class="btn adm-primary" id="yqSign">${t("yqSignBtn")}</button>
      <a class="btn secondary" id="yqDocx" style="display:block;text-align:center;text-decoration:none">${t("yqDocx")}</a>
      <a class="btn secondary" id="yqPdf" style="display:block;text-align:center;text-decoration:none">${t("yqPdf")}</a>
      <button class="arz-del-btn" id="yqDel">${t("yqDel")}</button>
    </div>
    ${yqReasonsHtml(it)}`);
  bindShell();
  $("#admBack").onclick = admSecYoqlama;
  $("#yqQ").oninput = (e) => { _yqQ = e.target.value; yqRedraw(); };
  yqBindRows();

  const base = `/api/mobile/admin/yoqlama/doc/${encodeURIComponent(it.id)}?token=${encodeURIComponent(store.token)}`;
  $("#yqDocx").href = base + "&fmt=docx"; $("#yqDocx").target = "_blank";
  $("#yqPdf").href = base + "&fmt=pdf";   $("#yqPdf").target = "_blank";

  // Yo'qlamani o'tkazgan xodim + uning imzosi
  admLoadEmployees().then(() => {
    const dl = document.getElementById("yqWho_dl");
    if (dl) dl.innerHTML = admEmployees.map(e =>
      `<option value="${esc(fmtName(e.full_name))} — ${esc(e.card_number)}"></option>`).join("");
    if (it.conductor && $("#yqWho")) {
      $("#yqWho").value = `${fmtName(it.conductor.full_name)} — ${it.conductor.card_number}`;
    }
  });
  const sigSec = document.querySelector(".sec .sigpad") ? document.querySelectorAll(".sec")[1] : null;
  const pad = sigSec ? initSigPad(sigSec) : null;
  $("#yqSign").onclick = async () => {
    const card = admPickedCard("yqWho");
    if (!card) return admToast(t("admPickEmp"), false);
    const b = $("#yqSign"); b.disabled = true; b.textContent = "…";
    const { status, data: d } = await api("/api/mobile/admin/yoqlama/sign", {
      method: "POST",
      body: { id: it.id, card, signature: pad ? pad.dataURL() : "" },
    });
    b.disabled = false; b.textContent = t("yqSignBtn");
    if (status === 200) { admToast(t("yqSignedOk")); admYoqlamaEdit(it.id); }
    else admToast((d && d.error) || t("admFail"), false);
  };

  $("#yqSave").onclick = async () => {
    const b = $("#yqSave"); b.disabled = true; b.textContent = "…";
    const { status } = await api("/api/mobile/admin/yoqlama/mark", {
      method: "POST", body: { id: it.id, marks: _yqMarks },
    });
    b.disabled = false; b.textContent = t("yqSave");
    admToast(status === 200 ? t("yqSaved") : t("admFail"), status === 200);
  };
  $("#yqDel").onclick = async () => {
    if (!confirm(t("yqDelAsk"))) return;
    const { status } = await api("/api/mobile/admin/yoqlama/delete", {
      method: "POST", body: { id: it.id },
    });
    if (status === 200) { admToast(t("admDone")); admSecYoqlama(); }
    else admToast(t("admFail"), false);
  };
}

// Qatnashmaganlarning javoblari (HR ko'radi)
function yqReasonsHtml(it) {
  const rs = it.reasons || {};
  const keys = Object.keys(rs);
  if (!keys.length) return "";
  const byCard = {};
  (it.employees || []).forEach(e => byCard[String(e.card_number)] = e.full_name);
  const rows = keys.map(c => {
    const r = rs[c] || {};
    return `<div class="pi"><div class="nm">
        <b>${esc(fmtName(byCard[c] || c))}</b>
        <span>"${esc(r.text || "")}"</span></div></div>`;
  }).join("");
  return `<div class="sec"><div class="adm-sub">${t("yqReasons")} · ${keys.length}</div>${rows}</div>`;
}

function yqRows(list) {
  return list.map(e => {
    const c = String(e.card_number), on = !!_yqMarks[c];
    return `<div class="pi yq-row" style="align-items:center">
      <div class="nm" style="flex:1"><b>${esc(fmtName(e.full_name))}</b></div>
      <div class="yq-tg">
        <button data-c="${esc(c)}" data-v="1" class="${on ? "y" : ""}">${t("yqYes")}</button>
        <button data-c="${esc(c)}" data-v="0" class="${!on ? "n" : ""}">${t("yqNo")}</button>
      </div></div>`;
  }).join("") || `<div class="empty">—</div>`;
}

function yqRedraw() {
  const emps = _yqItem.employees || [];
  const q = _yqQ.trim().toLowerCase();
  const list = emps.filter(e => !q || fmtName(e.full_name).toLowerCase().includes(q)
    || String(e.card_number).includes(q));
  $("#yqList").innerHTML = yqRows(list);
  const yes = emps.filter(e => _yqMarks[e.card_number]).length;
  $("#yqCntY").textContent = yes;
  $("#yqCntN").textContent = emps.length - yes;
  yqBindRows();
}

function yqBindRows() {
  document.querySelectorAll("#yqList .yq-tg button").forEach(b => b.onclick = () => {
    _yqMarks[b.dataset.c] = (b.dataset.v === "1");
    yqRedraw();
  });
}

// ─── Kechikuvchilar reytingi (oylik, eng ko'pdan) ───
// ─── Xodimni tizimdan butunlay chiqarish ───
async function admSecEmpOut() {
  $("#app").innerHTML = shell(`
    ${admBackHead("admEmpOut")}
    <div class="sec">
      <p class="adm-hint">${t("empOutHint")}</p>
      <div class="sv-new">
        ${admEmpPickerHtml("eoPick")}
        <button class="adm-btn danger" id="eoBtn">${t("empOutBtn")}</button>
      </div>
      <div class="warn-box">${t("empOutWarn")}</div>
      <div id="eoRes"></div>
    </div>`);
  bindShell(); admBindBack();

  $("#eoBtn").onclick = async () => {
    const raw = ($("#eoPick").value || "").trim();
    const m = /(\d{9,})\s*$/.exec(raw);
    const card = m ? m[1] : raw.replace(/\D/g, "");
    if (card.length < 9) return admToast(t("empOutFind"), false);
    const emp = admEmployees.find(e => String(e.card_number) === card);
    const who = emp ? fmtName(emp.full_name) : card;
    if (!confirm(`${who} — ${t("empOutAsk")}`)) return;
    $("#eoBtn").disabled = true;
    const { status, data } = await api("/api/mobile/admin/employee_remove",
      { method: "POST", body: { card } });
    $("#eoBtn").disabled = false;
    if (status !== 200 || !data || data.error) {
      $("#eoRes").innerHTML = `<div class="empty">${esc((data && data.error) || t("admFail"))}</div>`;
      return admToast((data && data.error) || t("admFail"), false);
    }
    admEmployees = [];
    admToast(t("empOutOk"));
    const rows = Object.entries(data.cleaned || {})
      .map(([k, v]) => `<div class="pi"><div class="nm" style="flex:1"><b>${esc(k)}</b></div>
        <span class="badge ok">${esc(String(v))}</span></div>`).join("");
    $("#eoRes").innerHTML = `
      <div class="adm-sub" style="margin:14px 0 6px">✓ ${esc(data.full_name || who)}</div>
      ${rows}
      ${data.backup ? `<p class="adm-hint" style="margin-top:8px">Nusxa: ${esc(data.backup)}</p>` : ""}`;
    $("#eoPick").value = "";
    admLoadEmployees();
  };
}

// ─── So'rovnoma (ovoz berish) ───
function svAnketaResult(d) {
  const qs = (d.questions || []).map(q => {
    if (q.type === "text") {
      const list = (q.answers || []).map(a =>
        `<div class="pi" style="align-items:flex-start"><div class="nm" style="flex:1">
          <b style="font-weight:500;white-space:pre-wrap">${esc(a.text)}</b>
          <span>${esc(shortName(a.name))}</span></div></div>`).join("")
        || `<div class="empty">${t("rankNone")}</div>`;
      return `<details class="sv-det"><summary>${q.no}. ${esc(q.text)} · ${q.answered}</summary>
        ${list}</details>`;
    }
    if (q.type === "scale") {
      const mx = Math.max(1, ...(q.options || []).map(o => o.count));
      return `<div style="margin:14px 0 4px"><b style="font-size:13.5px">${q.no}. ${esc(q.text)}</b>
        <div class="adm-hint" style="margin:2px 0 8px">
          <b style="font-size:15px;color:var(--text,#111)">${q.avg}</b> / ${q.max} ·
          ${q.answered} ${t("svAnswers")}</div>
        ${(q.options || []).map(o => `
          <div class="sv-bar"><div class="sv-bar-top">
            <b style="width:18px">${o.text}</b><span style="flex:1"></span>
            <em>${o.count} · ${o.percent}%</em>
            <button class="sv-act lst" data-q="${esc(q.id)}" data-v="${esc(o.text)}"
              title="${t("svList")}">⬇</button></div>
          <div class="sv-bar-bg"><i style="width:${Math.round(o.count / mx * 100)}%"></i></div>
          </div>`).join("")}</div>`;
    }
    const max = Math.max(1, ...(q.options || []).map(o => o.count));
    const bars = (q.options || []).filter(o => o.count).map(o => `
      <div class="sv-bar">
        <div class="sv-bar-top"><span style="flex:1">${esc(o.text)}</span>
          <em>${o.count} · ${o.percent}%</em>
          <button class="sv-act lst" data-q="${esc(q.id)}" data-v="${esc(o.text)}"
            title="${t("svList")}">⬇</button></div>
        <div class="sv-bar-bg"><i style="width:${Math.round(o.count / max * 100)}%"></i></div>
      </div>`).join("") || `<div class="empty">${t("rankNone")}</div>`;
    const oth = (q.other_texts || []).length ? `
      <details class="sv-det" style="margin:2px 0 10px">
        <summary>«Boshqa» javoblari · ${q.other_texts.length}</summary>
        ${q.other_texts.map(x => `<div class="pi"><div class="nm" style="flex:1">
          <b style="font-weight:500">${esc(x.text)}</b>
          <span>${esc(shortName(x.name))}</span></div></div>`).join("")}
      </details>` : "";
    return `<div style="margin:14px 0 4px"><b style="font-size:13.5px">${q.no}. ${esc(q.text)}</b>
      <div class="adm-hint" style="margin:2px 0 8px">${q.answered} ${t("svAnswers")}</div>
      ${bars}${oth}</div>`;
  }).join("");
  const nv = (d.not_voted || []).length ? `
    <details class="sv-det"><summary>${t("svNotVoted")} · ${d.not_voted.length}</summary>
      ${d.not_voted.map(v => `<div class="pi"><div class="nm" style="flex:1">
        <b>${esc(shortName(v.full_name))}</b>
        <span>${esc(v.department || "")}</span></div></div>`).join("")}
    </details>` : "";
  openModal(`<h3 style="margin:0 0 2px">📝 ${esc(d.title)}</h3>
    <p class="adm-hint" style="margin:0 0 4px">
      ${d.active ? "🟢 " + t("svOpen") : "⚪ " + t("svClosed")} ·
      ${d.total_votes}/${d.eligible} · ${d.turnout}%</p>
    <button class="adm-btn sm" id="svDoc" style="margin:0 0 10px">⬇ ${t("svWord")}</button>
    ${qs}${nv}`);
  const b = document.querySelector(".modal-bg:last-of-type #svDoc");
  if (b) b.onclick = () => downloadAuth(
    "/api/mobile/admin/surveys/doc?id=" + encodeURIComponent(d.id));
  document.querySelectorAll(".modal-bg:last-of-type .sv-act.lst").forEach(el =>
    el.onclick = (e) => {
      e.preventDefault(); e.stopPropagation();
      downloadAuth("/api/mobile/admin/surveys/answer_doc?id=" + encodeURIComponent(d.id)
        + "&q=" + encodeURIComponent(el.dataset.q)
        + "&value=" + encodeURIComponent(el.dataset.v));
    });
}

async function downloadAuth(url) {
  admToast("…");
  try {
    const r = await fetch(url, { headers: { Authorization: "Bearer " + store.token } });
    if (!r.ok) return admToast(t("admFail"), false);
    const blob = await r.blob();
    const cd = r.headers.get("Content-Disposition") || "";
    const m = /filename="?([^"]+)"?/.exec(cd);
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = m ? m[1] : "hisobot.docx";
    document.body.appendChild(a); a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
  } catch (e) { admToast(t("admFail"), false); }
}

async function admSecSurvey() {
  const isHr = isAdminRole();
  $("#app").innerHTML = shell(`
    ${admBackHead("admSurvey")}
    <div class="sec"><div id="svBody"><div class="empty">${t("daysLoad")}</div></div></div>`);
  bindShell(); admBindBack();

  const { status, data } = await api("/api/mobile/admin/surveys");
  const body = $("#svBody");
  if (!body) return;
  if (status !== 200 || !data) {
    body.innerHTML = `<div class="empty">${(data && data.error) || t("admFail")}</div>`; return;
  }
  const link = location.origin + (data.link || "/ovoz");
  const list = data.surveys || [];

  const linkBox = `
    <div class="sv-link">
      <div class="adm-sub" style="margin:0 0 6px">${t("svLink")} · ${t("svAll")}</div>
      <code id="svUrl">${esc(link)}</code>
      <button class="adm-btn sm" id="svCopy">${t("svCopy")}</button>
      <p class="adm-hint" style="margin:8px 0 0">${data.candidates} ${t("svInfo")}: ${data.voters}</p>
    </div>`;

  const kinds = data.kinds || [];
  const akForms = ((kinds.find(k => k.id === "anketa") || {}).forms || []).filter(f => f.id);
  const tplBox = !isHr ? "" : `
    <div class="sv-new">
      <div class="adm-sub">📝 Anketa shablonlari</div>
      <p class="adm-hint" style="margin:0 0 10px">Savollarni shu yerda o'zingiz tuzasiz. Saqlangan anketa
        yuqoridagi "So'rovnoma turi → So'rovnoma (savollar bilan)" ro'yxatida chiqadi.</p>
      ${akForms.map(f => `
        <div class="ak-tpl">
          <div class="nm"><b>${esc(f.title)}</b><span>${f.questions} ta savol</span></div>
          <button class="sv-act ak-ed" data-id="${esc(f.id)}" title="Tahrirlash">✏️</button>
          <button class="sv-act ak-cp" data-id="${esc(f.id)}" title="Nusxa olib yangisini tuzish">📄</button>
          <button class="sv-act del ak-del" data-id="${esc(f.id)}" title="O'chirish">🗑</button>
        </div>`).join("")}
      <button class="adm-btn" id="akNew" style="margin-top:8px">➕ Yangi anketa tuzish</button>
    </div>`;
  const newBox = !isHr ? "" : `
    <div class="sv-new">
      <div class="adm-sub">${t("svNew")}</div>
      <select class="adm-inp" id="svK">${kinds.map((k, i) =>
        `<option value="${esc(k.id)}"${i ? "" : " selected"}>${esc(k.name)}</option>`).join("")}</select>
      <select class="adm-inp hidden" id="svF"></select>
      <p class="adm-hint" id="svKinfo" style="margin:-4px 0 8px"></p>
      <input class="adm-inp" id="svT" placeholder="${t("svTitle")}">
      <input class="adm-inp" id="svQ" placeholder="${t("svQuestion")}">
      <button class="adm-btn" id="svAdd">${t("svCreate")}</button>
    </div>`;

  const rows = list.length ? list.map(x => `
    <div class="pi clickable sv-row" data-id="${esc(x.id)}" style="align-items:center">
      <div class="nm" style="flex:1"><b>${esc(x.title)}</b>
        <span>${x.active ? "🟢 " + t("svOpen") : "⚪ " + t("svClosed")} ·
          ${x.total_votes}/${x.eligible} ${t("svVotes")} · ${x.turnout}% ${t("svTurnout")}</span></div>
      ${x.active ? `<button class="sv-act lnk" data-l="${esc(link)}?s=${esc(x.id)}"
          title="${t("svOwnLink")}">🔗</button>` : ""}
      ${isHr ? `<button class="sv-act" data-a="${x.active ? "close" : "reopen"}" data-id="${esc(x.id)}"
          >${x.active ? t("svClose") : t("svReopen")}</button>
        <button class="sv-act del" data-a="delete" data-id="${esc(x.id)}">🗑</button>` : ""}
    </div>`).join("") : `<div class="empty">${t("svNone")}</div>`;

  body.innerHTML = linkBox + newBox + tplBox + rows;

  const akN = $("#akNew");
  if (akN) akN.onclick = () => akEditor("", false);
  document.querySelectorAll(".ak-ed").forEach(b => b.onclick = () => akEditor(b.dataset.id, false));
  document.querySelectorAll(".ak-cp").forEach(b => b.onclick = () => akEditor(b.dataset.id, true));
  document.querySelectorAll(".ak-del").forEach(b => b.onclick = async () => {
    if (!confirm("Bu anketa shablonini o'chirasizmi?\n(O'tkazilgan so'rovnomalar natijasi saqlanib qoladi)")) return;
    const r = await api("/api/mobile/admin/anketa/delete", { method: "POST", body: { id: b.dataset.id } });
    if (r.status === 200 && r.data && r.data.ok) { admToast(t("admDone")); admSecSurvey(); }
    else admToast((r.data && r.data.error) || t("admFail"), false);
  });

  const cp = $("#svCopy");
  if (cp) cp.onclick = () => {
    navigator.clipboard.writeText(link).then(() => admToast(t("svCopied")))
      .catch(() => admToast(link, true));
  };
  const ksel = $("#svK");
  const fsel = $("#svF");
  const fillKind = () => {
    const k = kinds.find(x => x.id === (ksel && ksel.value)) || kinds[0];
    if (!k) return;
    const forms = k.forms || [];
    if (fsel) {
      if (forms.length) {
        fsel.innerHTML = forms.map((f, i) =>
          `<option value="${esc(f.id)}"${i ? "" : " selected"}>${esc(f.title)} · ${f.questions} ${t("svQuestions")}</option>`).join("");
        fsel.classList.remove("hidden");
        fsel.onchange = () => {
          const f = forms.find(x => x.id === fsel.value);
          if (f) { $("#svT").value = f.title;
            $("#svKinfo").textContent = `${f.questions} ${t("svQuestions")} · ${k.voters} ${t("svVoters")}`; }
        };
      } else fsel.classList.add("hidden");
    }
    const f0 = forms.length ? forms[0] : null;
    if (f0) { $("#svT").value = f0.title; }
    else $("#svT").value = k.title || k.name;
    $("#svQ").value = k.question || "";
    $("#svQ").style.display = k.id === "anketa" ? "none" : "";
    $("#svKinfo").textContent = `${f0 ? f0.questions : k.candidates} ${
      k.id === "anketa" ? t("svQuestions") : t("svCand")} · ${k.voters} ${t("svVoters")}`;
  };
  if (ksel) { ksel.onchange = fillKind; fillKind(); }
  const add = $("#svAdd");
  if (add) add.onclick = async () => {
    const title = ($("#svT").value || "").trim();
    if (!title) return admToast(t("svTitle"), false);
    add.disabled = true;
    const r = await api("/api/mobile/admin/surveys/create",
      { method: "POST", body: { title, question: ($("#svQ").value || "").trim(),
                                kind: ksel ? ksel.value : "leader",
                                form_id: (fsel && !fsel.classList.contains("hidden"))
                                  ? fsel.value : "" } });
    add.disabled = false;
    if (r.status === 200) { admToast(t("admDone")); admSecSurvey(); }
    else admToast((r.data && r.data.error) || t("admFail"), false);
  };
  document.querySelectorAll(".sv-act").forEach(b => b.onclick = async (e) => {
    e.stopPropagation();
    const a = b.dataset.a;
    if (a === "close" && !confirm(t("svCloseAsk"))) return;
    if (a === "delete" && !confirm(t("svDelAsk"))) return;
    b.disabled = true;
    const r = await api("/api/mobile/admin/surveys/action",
      { method: "POST", body: { id: b.dataset.id, action: a } });
    if (r.status === 200) { admToast(t("admDone")); admSecSurvey(); }
    else { b.disabled = false; admToast((r.data && r.data.error) || t("admFail"), false); }
  });
  document.querySelectorAll(".sv-act.lnk").forEach(b => b.onclick = (e) => {
    e.stopPropagation();
    const u = b.dataset.l;
    navigator.clipboard.writeText(u).then(() => admToast(t("svCopied") + ": " + u))
      .catch(() => admToast(u, true));
  });
  document.querySelectorAll(".sv-row").forEach(el => el.onclick = () => svResult(el.dataset.id));
}

// ─────────── Anketa konstruktori (JSONsiz, oddiy forma) ───────────
const AK_TYPES = [
  ["one", "🔘 Bitta javob tanlanadi"],
  ["many", "☑️ Bir nechta javob tanlash mumkin"],
  ["scale", "⭐ 1 dan 5 gacha baho"],
  ["text", "✍️ Erkin javob (o'zi yozadi)"],
  ["section", "📌 Bo'lim sarlavhasi (savol emas)"],
];
let AK = null;          // tahrirlanayotgan anketa
let AK_DIRTY = false;

function akNewQ(type) {
  return type === "section"
    ? { type: "section", text: "", hint: "" }
    : { type: type || "one", text: "", hint: "", required: true,
        options: [], other: false, min_label: "", max_label: "" };
}

async function akEditor(id, copy) {
  AK_DIRTY = false;
  if (id) {
    const { status, data } = await api("/api/mobile/admin/anketa/get?id=" + encodeURIComponent(id));
    if (status !== 200 || !data) return admToast((data && data.error) || t("admFail"), false);
    AK = data;
    if (copy) { AK.id = ""; AK.title = AK.title + " (nusxa)"; AK_DIRTY = true; }
  } else {
    AK = { id: "", title: "", subtitle: "", intro: "", items: [akNewQ("one")] };
  }
  akRender();
}

// Ekrandagi qiymatlarni AK ga yig'ish
function akCollect() {
  if (!AK) return;
  const v = (sel) => { const e = $(sel); return e ? e.value : ""; };
  AK.title = v("#akTitle"); AK.subtitle = v("#akSub"); AK.intro = v("#akIntro");
  document.querySelectorAll(".ak-q").forEach(el => {
    const it = AK.items[+el.dataset.i];
    if (!it) return;
    const g = (c) => el.querySelector(c);
    it.text = g(".ak-text") ? g(".ak-text").value : "";
    it.hint = g(".ak-hint") ? g(".ak-hint").value : "";
    if (g(".ak-opts")) it.options = g(".ak-opts").value.split("\n").map(s => s.trim()).filter(Boolean);
    if (g(".ak-other")) it.other = g(".ak-other").checked;
    if (g(".ak-req")) it.required = g(".ak-req").checked;
    if (g(".ak-min")) it.min_label = g(".ak-min").value;
    if (g(".ak-max")) it.max_label = g(".ak-max").value;
  });
}

function akRender() {
  let n = 0;
  const cards = AK.items.map((it, i) => {
    const isSec = it.type === "section";
    if (!isSec) n++;
    const typeSel = `<select class="adm-inp ak-type">${AK_TYPES.map(([k, l]) =>
      `<option value="${k}"${k === it.type ? " selected" : ""}>${l}</option>`).join("")}</select>`;
    const tools = `<span class="ak-tools">
        <button class="sv-act ak-up" title="Yuqoriga"${i ? "" : " disabled"}>↑</button>
        <button class="sv-act ak-dn" title="Pastga"${i < AK.items.length - 1 ? "" : " disabled"}>↓</button>
        <button class="sv-act del ak-rm" title="O'chirish">🗑</button></span>`;
    let extra = "";
    if (it.type === "one" || it.type === "many") {
      extra = `
        <label class="ak-lbl">Javob variantlari — <b>har birini yangi qatorga</b> yozing</label>
        <textarea class="adm-inp ak-opts" rows="${Math.max(3, (it.options || []).length + 1)}"
          placeholder="Masalan:&#10;Ha&#10;Yo'q&#10;Bilmayman">${esc((it.options || []).join("\n"))}</textarea>
        <label class="adm-chk"><input type="checkbox" class="ak-other"${it.other ? " checked" : ""}>
          <span>"Boshqa" varianti ham bo'lsin (xodim o'zi yozadi)</span></label>`;
    } else if (it.type === "scale") {
      extra = `
        <div class="ak-scale">${[1, 2, 3, 4, 5].map(x => `<i>${x}</i>`).join("")}</div>
        <div class="ak-two">
          <input class="adm-inp ak-min" placeholder="1 = Qoniqarsiz" value="${esc(it.min_label || "")}">
          <input class="adm-inp ak-max" placeholder="5 = Juda yaxshi" value="${esc(it.max_label || "")}">
        </div>`;
    }
    return `
      <div class="ak-q${isSec ? " sec" : ""}" data-i="${i}">
        <div class="ak-qh"><b>${isSec ? "📌 Bo'lim" : n + "-savol"}</b>${tools}</div>
        ${typeSel}
        <textarea class="adm-inp ak-text" rows="2" placeholder="${isSec
          ? "Bo'lim nomi, masalan: I. Ish sharoitlari" : "Savol matnini yozing"}">${esc(it.text || "")}</textarea>
        ${extra}
        <input class="adm-inp ak-hint" placeholder="${isSec ? "Izoh (ixtiyoriy)" :
          "Izoh (ixtiyoriy)"}" value="${esc(it.hint || "")}">
        ${isSec ? "" : `<label class="adm-chk"><input type="checkbox" class="ak-req"${it.required ? " checked" : ""}>
          <span>Majburiy savol (javobsiz yuborib bo'lmaydi)</span></label>`}
      </div>`;
  }).join("");

  $("#app").innerHTML = shell(`
    <div class="adm-head"><button class="adm-back" id="akBack">‹</button>
      <h3>${AK.id ? "Anketani tahrirlash" : "Yangi anketa"}</h3></div>
    <div class="sec ak-wrap">
      <div class="sv-new">
        <label class="ak-lbl">Anketa nomi *</label>
        <input class="adm-inp" id="akTitle" placeholder="Masalan: Ish sharoitlari va takliflar" value="${esc(AK.title || "")}">
        <label class="ak-lbl">Qisqa tavsif (ixtiyoriy)</label>
        <input class="adm-inp" id="akSub" placeholder="Masalan: 2-3 daqiqa vaqt oladi" value="${esc(AK.subtitle || "")}">
        <label class="ak-lbl">Xodimlarga kirish so'zi (ixtiyoriy)</label>
        <textarea class="adm-inp" id="akIntro" rows="3" placeholder="So'rovnoma nima uchun o'tkazilayotgani haqida 1-2 gap">${esc(AK.intro || "")}</textarea>
      </div>
      ${cards}
      <div class="ak-add">
        <button class="adm-btn" id="akAddQ">➕ Savol qo'shish</button>
        <button class="adm-btn ghost" id="akAddS">📌 Bo'lim qo'shish</button>
      </div>
      <div class="ak-save">
        <button class="adm-btn ghost" id="akPrev">👁 Ko'rinishi</button>
        <button class="adm-btn" id="akSave">💾 Saqlash</button>
      </div>
      <p class="adm-hint">Saqlangandan keyin anketani "Yangi so'rovnoma" bo'limida tanlab ishga tushirasiz.
        O'tkazilgan so'rovnomalar natijasiga tahrir ta'sir qilmaydi.</p>
    </div>`);
  bindShell();

  const rerender = () => { akCollect(); AK_DIRTY = true; akRender(); };
  $("#akBack").onclick = () => {
    akCollect();
    if (AK_DIRTY && !confirm("Saqlanmagan o'zgarishlar yo'qoladi. Chiqasizmi?")) return;
    AK = null; admSecSurvey();
  };
  document.querySelectorAll(".ak-wrap input, .ak-wrap textarea").forEach(e =>
    e.addEventListener("input", () => { AK_DIRTY = true; }));
  document.querySelectorAll(".ak-q").forEach(el => {
    const i = +el.dataset.i;
    el.querySelector(".ak-type").onchange = (e) => {
      akCollect();
      const old = AK.items[i], nt = e.target.value;
      const nq = akNewQ(nt);
      nq.text = old.text; nq.hint = old.hint;
      if (nt !== "section") { nq.options = old.options || []; nq.other = !!old.other;
        nq.required = old.required !== undefined ? old.required : true; }
      AK.items[i] = nq; AK_DIRTY = true; akRender();
    };
    el.querySelector(".ak-up").onclick = () => { akCollect();
      [AK.items[i - 1], AK.items[i]] = [AK.items[i], AK.items[i - 1]]; AK_DIRTY = true; akRender(); };
    el.querySelector(".ak-dn").onclick = () => { akCollect();
      [AK.items[i + 1], AK.items[i]] = [AK.items[i], AK.items[i + 1]]; AK_DIRTY = true; akRender(); };
    el.querySelector(".ak-rm").onclick = () => {
      akCollect();
      const it = AK.items[i];
      if ((it.text || (it.options || []).length) && !confirm("Shu savolni o'chirasizmi?")) return;
      AK.items.splice(i, 1); AK_DIRTY = true; akRender();
    };
  });
  const addItem = (type) => {
    akCollect(); AK.items.push(akNewQ(type)); AK_DIRTY = true; akRender();
    const last = document.querySelectorAll(".ak-q .ak-text");
    if (last.length) { last[last.length - 1].focus(); last[last.length - 1].scrollIntoView({ block: "center", behavior: "smooth" }); }
  };
  $("#akAddQ").onclick = () => {
    // Oldingi savol turini takrorlaymiz — ketma-ket bir xil savollar qulay
    const prev = [...AK.items].reverse().find(x => x.type !== "section");
    addItem(prev ? prev.type : "one");
  };
  $("#akAddS").onclick = () => addItem("section");
  $("#akPrev").onclick = () => { akCollect(); akPreview(); };
  $("#akSave").onclick = async () => {
    akCollect();
    const b = $("#akSave"); b.disabled = true;
    const r = await api("/api/mobile/admin/anketa/save", { method: "POST", body: AK });
    b.disabled = false;
    if (r.status === 200 && r.data && r.data.ok) {
      AK_DIRTY = false; AK = null; admToast("✅ Anketa saqlandi"); admSecSurvey();
    } else admToast((r.data && r.data.error) || t("admFail"), false);
  };
}

// Xodim ko'radigan ko'rinishning soddalashtirilgan nusxasi
function akPreview() {
  let n = 0;
  const body = AK.items.map(it => {
    if (it.type === "section")
      return it.text ? `<div class="ak-pv-sec">${esc(it.text)}</div>` : "";
    n++;
    const opts = [...(it.options || []), ...(it.other ? ["Boshqa: ______"] : [])];
    let ans = "";
    if (it.type === "one" || it.type === "many")
      ans = opts.map(o => `<div class="ak-pv-opt">${it.type === "one" ? "○" : "☐"} ${esc(o)}</div>`).join("")
        || `<div class="ak-pv-warn">⚠️ Javob variantlari yozilmagan</div>`;
    else if (it.type === "scale")
      ans = `<div class="ak-scale">${[1, 2, 3, 4, 5].map(x => `<i>${x}</i>`).join("")}</div>
        <div class="ak-pv-lbl"><span>${esc(it.min_label || "Qoniqarsiz")}</span><span>${esc(it.max_label || "Juda yaxshi")}</span></div>`;
    else ans = `<div class="ak-pv-txt">Javob yozish maydoni</div>`;
    return `<div class="ak-pv-q"><b>${n}. ${esc(it.text || "(savol matni yo'q)")}${it.required ? " <em>*</em>" : ""}</b>
      ${it.hint ? `<p>${esc(it.hint)}</p>` : ""}${ans}</div>`;
  }).join("");
  openModal(`<h3 style="margin:0 0 4px">${esc(AK.title || "(nomsiz anketa)")}</h3>
    ${AK.subtitle ? `<p class="adm-hint" style="margin:0 0 6px">${esc(AK.subtitle)}</p>` : ""}
    ${AK.intro ? `<p style="font-size:13.5px;margin:0 0 10px">${esc(AK.intro)}</p>` : ""}
    <div class="ak-pv">${body || `<div class="empty">Savol yo'q</div>`}</div>`);
}

async function svResult(id) {
  openModal(`<div class="empty">${t("daysLoad")}</div>`);
  const { status, data } = await api("/api/mobile/admin/surveys/results?id=" + encodeURIComponent(id));
  if (status !== 200 || !data) return openModal(`<div class="empty">${t("admFail")}</div>`);
  if (data.kind === "anketa") return svAnketaResult(data);
  const rt = (data.rating || []).filter(r => r.votes > 0 || data.active === false);
  const max = Math.max(1, ...(data.rating || []).map(r => r.votes));
  const bars = rt.map(r => `
    <div class="sv-bar">
      <div class="sv-bar-top">
        <b>${r.pos === 1 ? "🥇" : r.pos === 2 ? "🥈" : r.pos === 3 ? "🥉" : r.pos}</b>
        <span>${esc(shortName(r.full_name))}</span>
        <em>${r.votes} · ${r.percent}%</em>
      </div>
      <div class="sv-bar-bg"><i style="width:${Math.round(r.votes / max * 100)}%"></i></div>
    </div>`).join("") || `<div class="empty">${t("rankNone")}</div>`;

  const who = (data.votes || []).length ? `
    <details class="sv-det"><summary>${t("svWho")} · ${data.votes.length}</summary>
      ${data.votes.map(v => `<div class="pi"><div class="nm" style="flex:1">
        <b>${esc(shortName(v.voter_name))}</b>
        <span>→ ${esc(shortName(v.choice_name))}</span></div>
        <span class="badge">${esc(String(v.at).slice(5, 16))}</span></div>`).join("")}
    </details>` : "";
  const nv = (data.not_voted || []).length ? `
    <details class="sv-det"><summary>${t("svNotVoted")} · ${data.not_voted.length}</summary>
      ${data.not_voted.map(v => `<div class="pi"><div class="nm" style="flex:1">
        <b>${esc(shortName(v.full_name))}</b>
        <span>${esc(v.department || "")}</span></div></div>`).join("")}
    </details>` : "";

  openModal(`<h3 style="margin:0 0 2px">🗳 ${esc(data.title)}</h3>
    <p class="adm-hint" style="margin:0 0 10px">
      ${data.active ? "🟢 " + t("svOpen") : "⚪ " + t("svClosed")} ·
      ${data.total_votes}/${data.eligible} ${t("svVotes")} · ${data.turnout}% ${t("svTurnout")}</p>
    ${bars}${who}${nv}`);
}

// ─── HR/rahbar: umumiy reyting (soatlari bilan) ───
async function admSecRating(ym) {
  ym = ym || ymList(1)[0];
  const opts = ymList(12).map(m =>
    `<option value="${m}"${m === ym ? " selected" : ""}>${ymLabel(m)}</option>`).join("");
  $("#app").innerHTML = shell(`
    ${admBackHead("admRating")}
    <div class="sec">
      <p class="adm-hint">${t("admRatingHint")}</p>
      <select class="adm-inp" id="arMonth">${opts}</select>
      <div id="arBody" style="margin-top:10px"><div class="empty">${t("daysLoad")}</div></div>
    </div>`);
  bindShell(); admBindBack();
  const bind = () => { const sl = $("#arMonth"); if (sl) sl.onchange = () => admSecRating(sl.value); };
  bind();

  const { status, data } = await api("/api/mobile/rating?month=" + ym);
  const body = $("#arBody");
  if (!body) return;
  if (status !== 200 || !data) { body.innerHTML = `<div class="empty">${(data && data.error) || t("admFail")}</div>`; return bind(); }
  if (data.building) { body.innerHTML = `<div class="empty">⏳ ${t("ratBuilding")}</div>`; return bind(); }
  const rows = data.rating || [];
  if (!rows.length) { body.innerHTML = `<div class="empty">${t("rankNone")}</div>`; return bind(); }

  body.innerHTML = `<div class="adm-sub">${t("rankHours")} · ${data.total}</div>` + rows.map(r => {
    const medal = r.pos <= 3 ? ["🥇", "🥈", "🥉"][r.pos - 1] : r.pos;
    const dw = r.days_worked ? `<span>${r.days_worked} ${t("dayUnit")}</span>` : "";
    const cn = r.card_number ? ` clickable" data-c="${esc(r.card_number)}"` : '"';
    return `<div class="pi rt-row${cn} style="align-items:center">
      <div class="rt-pos" style="font-size:${r.pos <= 3 ? "17px" : "13px"}">${medal}</div>
      <div class="nm" style="flex:1"><b>${esc(shortName(r.full_name))}</b>${dw}</div>
      <span class="badge ok" style="font-family:'JetBrains Mono',monospace">${esc(r.total_hours_str || "")}</span>
    </div>`;
  }).join("");

  const byCard = {};
  rows.forEach(r => { if (r.card_number) byCard[r.card_number] = r; });
  body.querySelectorAll(".rt-row.clickable").forEach(el => {
    el.onclick = () => {
      const c = el.dataset.c, r = byCard[c];
      if (r) daysModal(c, shortName(r.full_name), ym);
    };
  });
  bind();
}

async function admSecLateList(ym) {
  ym = ym || ymList(1)[0];
  const opts = ymList(12).map(m =>
    `<option value="${m}"${m === ym ? " selected" : ""}>${ymLabel(m)}</option>`).join("");
  $("#app").innerHTML = shell(`
    ${admBackHead("admLateList")}
    <div class="sec">
      <p class="adm-hint">${t("admLateHint")}</p>
      <select class="adm-inp" id="llMonth">${opts}</select>
      <div id="llBody" style="margin-top:10px"><div class="empty">${t("daysLoad")}</div></div>
    </div>`);
  bindShell(); admBindBack();
  const bind = () => { const s = $("#llMonth"); if (s) s.onchange = () => admSecLateList(s.value); };
  bind();

  const { status, data } = await api("/api/mobile/late?month=" + ym);
  const body = $("#llBody");
  if (!body) return;
  if (status !== 200 || !data) { body.innerHTML = `<div class="empty">${(data && data.error) || t("admFail")}</div>`; return bind(); }
  if (data.building) { body.innerHTML = `<div class="empty">⏳ ${t("ratBuilding")}</div>`; return bind(); }
  const rows = data.late || [];
  if (!rows.length) { body.innerHTML = `<div class="empty">${t("lateNoneMon")}</div>`; return bind(); }

  body.innerHTML = `<div class="adm-sub">${t("admLateList")} · ${data.total}</div>`
    + `<div class="adm-hint" style="margin:2px 0 8px">${t("lateTapHint")}</div>` + rows.map(r => {
    const medal = r.pos <= 3 ? ["🥇", "🥈", "🥉"][r.pos - 1] : r.pos;
    const exc = r.late_excused ? `<span> · ${r.late_excused} ${t("lateExcused")}</span>` : "";
    // Telefonda qulay bo'lishi uchun rasm yo'q — faqat familiya va ism
    return `<div class="pi clickable ll-row rt-row" data-c="${esc(r.card_number)}" style="align-items:center">
      <div class="rt-pos" style="font-size:${r.pos <= 3 ? "17px" : "13px"}">${medal}</div>
      <div class="nm" style="flex:1"><b>${esc(shortName(r.full_name))}</b>
        <span>${r.work_start ? esc(String(r.work_start).slice(0, 5)) : ""}${exc}</span></div>
      <span class="badge late" style="font-weight:800">${r.late_count} ${t("lateTimes")}</span>
    </div>`;
  }).join("");

  const byCard = {};
  rows.forEach(r => byCard[r.card_number] = r);
  document.querySelectorAll("#llBody .ll-row").forEach(el => el.onclick = () => {
    const r = byCard[el.dataset.c];
    if (r) lateDaysModal(r.late_days || [], shortName(r.full_name), r.card_number, r.work_start);
  });
  bind();
}

// ─── Xodim qo'shish (users.xlsx ga) ───
async function admSecEmpAdd() {
  $("#app").innerHTML = shell(`
    ${admBackHead("admEmpAdd")}
    <div class="sec">
      <p class="adm-hint">${t("admEmpAddHint")}</p>
      <input class="adm-inp" id="eFam" placeholder="${t("empFam")}">
      <input class="adm-inp" id="eIsm" style="margin-top:8px" placeholder="${t("empIsm")}">
      <input class="adm-inp" id="eShr" style="margin-top:8px" placeholder="${t("empSharif")}">
      <input class="adm-inp" id="ePin" inputmode="numeric" maxlength="14" style="margin-top:8px" placeholder="${t("empPin")}">
      <select class="adm-inp" id="eRole" style="margin-top:8px">
        <option value="employee">${t("empRoleEmp")}</option>
        <option value="hr">${t("empRoleHr")}</option>
        <option value="director">${t("empRoleDir")}</option>
      </select>
      <select class="adm-inp" id="eCat" style="margin-top:8px">
        <option value="oddiy">${t("empCatOddiy")}</option>
        <option value="haydovchi">${t("empCatHaydovchi")}</option>
        <option value="rahbar">${t("empCatRahbar")}</option>
        <option value="masofaviy">${t("empCatMasofaviy")}</option>
      </select>
      <input class="adm-inp" id="eWork" style="margin-top:8px" placeholder="${t("empWork")}">
      <button class="btn adm-primary" id="eBtn" style="margin-top:10px">${t("empAddBtn")}</button>
      <div id="eResult"></div>
    </div>`);
  bindShell(); admBindBack();
  $("#eBtn").onclick = async () => {
    const familya = ($("#eFam").value || "").trim();
    const ism = ($("#eIsm").value || "").trim();
    const sharif = ($("#eShr").value || "").trim();
    const card = ($("#ePin").value || "").replace(/\D/g, "");
    if (!familya || !ism || card.length < 9) return admToast(t("empAddReq"), false);
    const body = {
      familya, ism, sharif, card,
      role: $("#eRole").value, category: $("#eCat").value,
      work_start: ($("#eWork").value || "").trim(),
    };
    const btn = $("#eBtn"); btn.disabled = true; btn.textContent = "…";
    const { status, data } = await api("/api/mobile/admin/employee_add", { method: "POST", body });
    btn.disabled = false; btn.textContent = t("empAddBtn");
    if (status === 200 && data) {
      const photoLine = data.photo ? t("empPhotoOk") : t("empPhotoNo");
      $("#eResult").innerHTML = `<div class="exp-ok" style="margin-top:12px;font-size:15px">
        ${t("empAddDone")}<br>${esc(data.name || "")}<br>
        ${t("admNewAccDone")} <b>${esc(data.card)}</b><br>
        ${t("admNewAccPass")} <b style="font-size:22px;letter-spacing:2px">${esc(data.password)}</b>
        <div style="font-size:12px;margin-top:8px;opacity:.85">${photoLine}</div></div>`;
      admToast(t("admDone"));
      ["eFam","eIsm","eShr","ePin","eWork"].forEach(id => { const el = $("#"+id); if (el) el.value = ""; });
    } else admToast((data && data.error) || t("admFail"), false);
  };
}

// ─── Hisoblar (ro'yxat + o'chirish) ───
let _accCache = [];
async function admSecAccounts() {
  $("#app").innerHTML = shell(skeleton(4)); bindShell();
  const { data } = await api("/api/mobile/admin/accounts_list");
  _accCache = (data && data.accounts) || [];
  $("#app").innerHTML = shell(`
    ${admBackHead("admAccounts")}
    <div class="sec">
      <p class="adm-hint">${t("admAccountsHint")}</p>
      <input class="adm-inp" id="accQ" placeholder="${t("accSearch")}">
      <div id="accList" style="margin-top:10px"></div>
    </div>`);
  bindShell(); admBindBack();
  const roleTag = (r) => r === "hr" ? "HR" : r === "director" ? "Rahbar" : r === "super_admin" ? "Super Admin" : "";
  const draw = () => {
    const q = ($("#accQ").value || "").trim().toLowerCase();
    const rows = _accCache.filter(a =>
      !q || (a.name || "").toLowerCase().includes(q) || String(a.card).includes(q));
    if (!rows.length) { $("#accList").innerHTML = `<div class="empty">${t("accNone")}</div>`; return; }
    $("#accList").innerHTML = rows.map(a => `
      <div class="pi" style="align-items:center">
        <div class="nm"><b>${esc(fmtName(a.name) || a.card)}</b>
          <span>${esc(a.card)}${roleTag(a.role) ? " · " + roleTag(a.role) : ""}${a.active ? "" : " · " + t("accInactive")}</span></div>
        <button class="arz-del-btn" data-card="${esc(a.card)}" style="margin:0;padding:6px 12px">${t("accDelete")}</button>
      </div>`).join("");
    document.querySelectorAll("#accList .arz-del-btn").forEach(b => b.onclick = () => accDelete(b.dataset.card));
  };
  draw();
  $("#accQ").oninput = draw;
}
async function accDelete(card) {
  if (!confirm(t("accDelConfirm"))) return;
  const { status, data } = await api("/api/mobile/admin/delete_account", { method: "POST", body: { card } });
  if (status === 200) {
    _accCache = _accCache.filter(a => String(a.card) !== String(card));
    admToast(t("accDeleted"));
    const q = ($("#accQ") && $("#accQ").value || "").trim().toLowerCase();
    const rows = _accCache.filter(a => !q || (a.name || "").toLowerCase().includes(q) || String(a.card).includes(q));
    if ($("#accList")) $("#accList").innerHTML = rows.length ? rows.map(a => `
      <div class="pi" style="align-items:center">
        <div class="nm"><b>${esc(fmtName(a.name) || a.card)}</b><span>${esc(a.card)}</span></div>
        <button class="arz-del-btn" data-card="${esc(a.card)}" style="margin:0;padding:6px 12px">${t("accDelete")}</button>
      </div>`).join("") : `<div class="empty">${t("accNone")}</div>`;
    document.querySelectorAll("#accList .arz-del-btn").forEach(b => b.onclick = () => accDelete(b.dataset.card));
  } else admToast((data && data.error) || t("admFail"), false);
}

// ─── Chiqish izohlari (xodim yozgan) ───
async function admSecExitReasons() {
  $("#app").innerHTML = shell(skeleton(4)); bindShell();
  const { data } = await api("/api/mobile/admin/exit/list");
  const items = (data && data.requests) || [];
  const badge = (st) => st === "accepted" ? `<span class="badge ok">${t("exitAccepted")}</span>`
    : st === "rejected" ? `<span class="badge abs">${t("exitRejected")}</span>`
    : `<span class="badge late">${t("exitPending")}</span>`;
  const rows = items.length ? items.map(r => `<div class="pi clickable arz-item" data-id="${esc(r.id)}">
      <div class="nm"><b>${esc(fmtName(r.full_name) || r.card_number)}</b>
        <span>${esc((r.text || "").slice(0, 42))}${r.exit_time ? " · " + esc(timeShort(r.exit_time)) : ""}</span></div>
      ${badge(r.status)}</div>`).join("") : `<div class="empty">${t("exitNone")}</div>`;
  $("#app").innerHTML = shell(`
    ${admBackHead("admExitReasons")}
    <div class="sec" style="margin-top:14px"><h3>${t("admExitReasons")} · ${items.length}</h3>${rows}</div>`);
  bindShell(); admBindBack();
  const byId = {}; items.forEach(r => byId[r.id] = r);
  document.querySelectorAll(".arz-item").forEach(el => el.onclick = () => exitReviewModal(byId[el.dataset.id]));
}

function exitReviewModal(r) {
  if (!r) return;
  openModal(`
    <h3 style="margin:0 0 6px">${esc(fmtName(r.full_name) || r.card_number)}</h3>
    <div class="adm-modmeta">🚪 ${esc(r.date || "")}${r.exit_time ? " · " + t("exitAt") + ": " + esc(timeShort(r.exit_time)) : ""}</div>
    <div class="adm-modbody">${esc(r.text || "")}</div>
    <input class="adm-inp" id="exNote" style="margin-top:10px" placeholder="${t("exitNoteHint")}" value="${esc(r.hr_note || "")}">
    <button class="btn adm-primary" id="exAccept" style="margin-top:2px">${t("exitAccept")}</button>
    <button class="btn secondary" id="exShow">${t("exitShow")}</button>
    <button class="arz-del-btn" id="exReject">${t("exitReject")}</button>`);
  const doRev = async (action) => {
    const note = ($("#exNote") || {}).value || "";
    const { status } = await api("/api/mobile/admin/exit/review", { method: "POST", body: { id: r.id, action, note } });
    if (status === 200) {
      const bg = document.querySelector(".modal-bg"); if (bg) bg.remove();
      admToast(t("admDone")); admSecExitReasons();
    } else admToast(t("admFail"), false);
  };
  const a = $("#exAccept"); if (a) a.onclick = () => doRev("accept");
  const s = $("#exShow"); if (s) s.onclick = () => doRev("show");
  const j = $("#exReject"); if (j) j.onclick = () => doRev("reject");
}

// ─── Tushuntirishlar arxivi ───
let admExplMonth = "";
async function admSecExpl() {
  $("#app").innerHTML = shell(skeleton(4)); bindShell();
  if (!admExplMonth) admExplMonth = todayISO().slice(0, 7);
  const { data } = await api("/api/mobile/admin/explanations?month=" + admExplMonth);
  const recs = (data && data.records) || [];
  const kindTxt = (k) => k === "late" ? t("expKindLate") : (k === "exit" ? "🚪" : t("expKindAbsent"));
  const rows = recs.length ? recs.map(r => `<div class="adm-row adm-expl" data-id="${esc(r.exp_id)}" data-st="${esc(r.status)}">
    <div class="adm-rmain"><b>${esc(fmtName(r.full_name) || r.card_number)}</b>
      <span>${kindTxt(r.type)} · ${esc(r.date || "")}</span></div>
    <span class="adm-stbadge ${r.status === "pending" ? "warn" : "ok"}">${r.status === "pending" ? t("admPending") : t("admReviewed")}</span>
    </div>`).join("") : `<div class="empty">${t("noExp")}</div>`;
  $("#app").innerHTML = shell(`
    ${admBackHead("admExpl")}
    <div class="sec">
      <input type="month" class="adm-inp" id="explMonth" value="${esc(admExplMonth)}" max="${todayISO().slice(0,7)}">
      <div id="explList" style="margin-top:10px">${rows}</div>
    </div>`);
  bindShell(); admBindBack();
  $("#explMonth").onchange = (e) => { if (e.target.value) { admExplMonth = e.target.value; admSecExpl(); } };
  const byId = {}; recs.forEach(r => byId[r.exp_id] = r);
  document.querySelectorAll(".adm-expl").forEach(row => row.onclick = () => admExplModal(byId[row.dataset.id]));
}

function admExplModal(r) {
  if (!r) return;
  const isPending = r.status === "pending";
  const kindTxt = r.type === "late" ? t("expKindLate")
    : r.type === "exit" ? t("expKindExit") : t("expKindAbsent");
  const pdfUrl = `/api/mobile/explain/pdf/${encodeURIComponent(r.exp_id)}?token=${encodeURIComponent(store.token)}`;
  // Xodimning qo'lyozma imzosi — bo'lsa ko'rsatamiz
  const sigHtml = r.signature_file
    ? `<div class="adm-sub" style="margin-top:10px">${t("explSign")}</div>
       <div class="expl-sig"><img src="/api/mobile/signature/${encodeURIComponent(r.exp_id)}?token=${encodeURIComponent(store.token)}" alt=""
         onerror="this.parentNode.parentNode.removeChild(this.parentNode)"></div>`
    : "";
  openModal(`
    <h3 style="margin:0 0 8px">${esc(fmtName(r.full_name) || r.card_number)}</h3>
    <div class="adm-modmeta">${esc(r.date || "")} · ${kindTxt}</div>
    <div class="adm-modbody">${esc(r.explanation || "—")}</div>
    ${sigHtml}
    <a class="btn secondary" href="${pdfUrl}" target="_blank"
       style="margin-top:10px;display:block;text-align:center;text-decoration:none">📄 ${t("explPdfOpen")}</a>
    <button class="btn ${isPending ? "adm-primary" : ""}" id="explToggle">${isPending ? t("admMarkOk") : t("admReopen")}</button>`);
  $("#explToggle").onclick = async () => {
    const { status } = await api("/api/mobile/admin/explanations/status", {
      method: "POST", body: { exp_id: r.exp_id, status: isPending ? "reviewed" : "pending" },
    });
    if (status === 200) { document.querySelector(".modal-bg").remove(); admToast(t("admDone")); admSecExpl(); }
    else admToast(t("admFail"), false);
  };
}

// ─── Monitoring ───
async function admSecMonitor() {
  $("#app").innerHTML = shell(skeleton(2)); bindShell();
  const { data } = await api("/api/mobile/admin/overview");
  const on = !!(data && data.monitor_enabled);
  $("#app").innerHTML = shell(`
    ${admBackHead("admMonitor")}
    <div class="sec">
      <div class="adm-monrow">
        <span>${t("admMonState")}</span>
        <b class="${on ? "adm-on" : "adm-offc"}">${on ? t("admOnn") : t("admOff")}</b>
      </div>
      <div class="adm-monrow"><span>${t("admLastCheck")}</span><b>${esc((data && data.monitor_last_checked) || "—")}</b></div>
      <button class="btn ${on ? "" : "adm-primary"}" id="monToggle">${on ? t("admMonOff") : t("admMonOn")}</button>
      <button class="btn adm-primary" id="nvrRefreshBtn" style="margin-top:10px">${t("admNvrRefresh")}</button>
      <div id="nvrRefreshMsg" class="adm-sub"></div>
    </div>`);
  bindShell(); admBindBack();
  $("#monToggle").onclick = async () => {
    const { status } = await api("/api/mobile/admin/monitor", { method: "POST", body: { enabled: !on } });
    if (status === 200) { admToast(t("admDone")); admSecMonitor(); } else admToast(t("admFail"), false);
  };
  $("#nvrRefreshBtn").onclick = async () => {
    const btn = $("#nvrRefreshBtn"), msg = $("#nvrRefreshMsg");
    btn.disabled = true; btn.textContent = t("admNvrRefreshing"); msg.textContent = "";
    const { status, data: r } = await api("/api/mobile/admin/nvr_refresh", { method: "POST" });
    btn.disabled = false; btn.textContent = t("admNvrRefresh");
    if (status === 200 && r && r.ok) {
      admToast(t("admNvrRefreshOk"));
      msg.textContent = `${t("admNvrRefreshOk")}: ${r.employees}/${r.total_queried} xodim, ${r.events} hodisa (${r.date})`;
    } else {
      admToast(t("admNvrRefreshFail"), false);
      msg.textContent = (r && r.error) || t("admNvrRefreshFail");
    }
  };
}

// ─── Kirish/chiqishni qo'lda tuzatish (faqat super_admin) ───
async function admSecAttendanceEdit() {
  $("#app").innerHTML = shell(`
    ${admBackHead("admAttEdit")}
    <div class="sec">
      <p class="adm-hint">${t("admAttEditHint")}</p>
      ${admEmpPickerHtml("aeCard")}
      <input type="date" class="adm-inp" id="aeDate" value="${todayISO()}" style="margin-top:8px">
      <div id="aeInfo" class="adm-sub"></div>
      <div class="adm-2col" style="margin-top:8px">
        <label>${t("admAttIn")}<input type="time" class="adm-inp" id="aeIn"></label>
        <label>${t("admAttOut")}<input type="time" class="adm-inp" id="aeOut"></label>
      </div>
      <button class="btn adm-primary" id="aeSave" style="margin-top:10px">${t("admSave")}</button>
      <button class="btn" id="aeClear" style="margin-top:8px">${t("admAttClear")}</button>
    </div>`);
  bindShell(); admBindBack();

  const load = async () => {
    const card = admPickedCard("aeCard");
    const date = $("#aeDate").value;
    if (!card || !date) { $("#aeInfo").textContent = ""; return; }
    const { status, data } = await api(`/api/mobile/admin/attendance_edit?card=${encodeURIComponent(card)}&date=${encodeURIComponent(date)}`);
    if (status !== 200 || !data) { $("#aeInfo").textContent = ""; return; }
    $("#aeInfo").innerHTML = `<b>${esc(data.full_name)}</b> — ${t("admAttActual")}: ${esc(data.actual_in || "—")} / ${esc(data.actual_out || "—")}`;
    $("#aeIn").value = data.override_in || "";
    $("#aeOut").value = data.override_out || "";
  };
  $("#aeCard").onchange = load;
  $("#aeDate").onchange = load;

  $("#aeSave").onclick = async () => {
    const card = admPickedCard("aeCard");
    if (!card) return admToast(t("admPickEmp"), false);
    const body = { card, date: $("#aeDate").value, in: $("#aeIn").value, out: $("#aeOut").value };
    const { status, data } = await api("/api/mobile/admin/attendance_edit", { method: "POST", body });
    if (status === 200) { admToast(t("admDone")); load(); }
    else admToast((data && data.error) || t("admFail"), false);
  };
  $("#aeClear").onclick = async () => {
    const card = admPickedCard("aeCard");
    if (!card) return admToast(t("admPickEmp"), false);
    const body = { card, date: $("#aeDate").value, in: "", out: "" };
    const { status, data } = await api("/api/mobile/admin/attendance_edit", { method: "POST", body });
    if (status === 200) { admToast(t("admDone")); load(); }
    else admToast((data && data.error) || t("admFail"), false);
  };
}

// ─── Rasm yuklash (xodim rasmini HR yuklaydi) ───
async function admSecPhoto() {
  await admLoadEmployees();
  $("#app").innerHTML = shell(`
    ${admBackHead("admPhoto")}
    <div class="sec">
      ${admEmpPickerHtml("phCard")}
      <div id="phPrev" class="adm-photoprev"></div>
      <button class="btn adm-primary" id="phPick">${t("admPhotoPick")}</button>
      <input type="file" id="phFile" accept="image/*" capture="environment" style="display:none">
      <div id="phMsg"></div>
    </div>`);
  bindShell(); admBindBack();
  const showPrev = () => {
    const card = admPickedCard("phCard");
    const emp = admEmployees.find(e => String(e.card_number) === String(card));
    const prev = $("#phPrev");
    if (emp && emp.photo_file)
      prev.innerHTML = `<div class="adm-sub">${t("admCurrentPhoto")}</div>
        <img class="adm-photoimg" src="photos/${esc(emp.photo_file)}?t=${Date.now()}" alt="">`;
    else prev.innerHTML = "";
  };
  $("#phCard").oninput = showPrev;
  $("#phCard").onchange = showPrev;
  if ($("#phApi")) $("#phApi").onclick = async () => {
    const card = admPickedCard("phCard");
    if (!card) return admToast(t("admPickFirst"), false);
    const b = $("#phApi"); b.disabled = true; b.textContent = "…";
    const { status, data } = await api("/api/mobile/admin/photo_fetch_api", { method: "POST", body: { card } });
    b.disabled = false; b.textContent = t("admPhotoApi");
    if (status === 200 && data) {
      admToast(t("admPhotoApiOk"));
      const emp = admEmployees.find(e => String(e.card_number) === String(card));
      if (emp) emp.photo_file = data.photo_file;
      showPrev();
    } else admToast((data && data.error) || t("admPhotoApiNo"), false);
  };
  $("#phPick").onclick = () => {
    if (!admPickedCard("phCard")) return admToast(t("admPickFirst"), false);
    $("#phFile").click();
  };
  $("#phFile").onchange = () => {
    const card = admPickedCard("phCard");
    if (!card) return admToast(t("admPickFirst"), false);
    const file = $("#phFile").files && $("#phFile").files[0];
    if (!file) return;
    const btn = $("#phPick"); btn.disabled = true; btn.textContent = t("loading");
    const img = new Image(); const url = URL.createObjectURL(file);
    img.onload = async () => {
      const MAX = 600, k = Math.min(1, MAX / Math.max(img.width, img.height));
      const cv = document.createElement("canvas");
      cv.width = Math.round(img.width * k); cv.height = Math.round(img.height * k);
      cv.getContext("2d").drawImage(img, 0, 0, cv.width, cv.height);
      URL.revokeObjectURL(url);
      const dataUrl = cv.toDataURL("image/jpeg", 0.85);
      const { status, data } = await api("/api/mobile/photo/upload", { method: "POST", body: { card, image: dataUrl } });
      btn.disabled = false; btn.textContent = t("admPhotoPick");
      if (status === 200 && data && data.ok) {
        admToast(t("admPhotoSaved"));
        const emp = admEmployees.find(e => String(e.card_number) === String(card));
        if (emp && data.photo_file) emp.photo_file = data.photo_file;
        $("#phPrev").innerHTML = `<div class="adm-sub">${t("admCurrentPhoto")}</div>
          <img class="adm-photoimg" src="${dataUrl}" alt="">`;
      } else if (status === 404 || status === 405) {
        admToast("Server yangilanmagan — mobile_api.py qayta ishga tushiring", false);
      } else admToast((data && data.error) || t("admFail"), false);
    };
    img.onerror = () => { URL.revokeObjectURL(url); btn.disabled = false; btn.textContent = t("admPhotoPick"); admToast(t("admFail"), false); };
    img.src = url;
  };
}

// ─── Olimlar (PhD/DSc belgilash) ───
async function admSecOlim() {
  $("#app").innerHTML = shell(skeleton(3)); bindShell();
  await admLoadEmployees();
  const list = await fetchOlimlar();
  const rows = list.length ? list.map(o => {
    const emp = admEmployees.find(e => String(e.card_number) === String(o.card_number));
    const nm = fmtName((emp && emp.full_name) || o.full_name || o.card_number);
    return `<div class="adm-row">
      <div class="adm-rmain"><b>${esc(nm)}</b><span>${esc(String(o.degree || "").toUpperCase())}</span></div>
      <button class="adm-del" data-card="${esc(o.card_number)}">✕</button></div>`;
  }).join("") : `<div class="empty">${t("admNoOlim")}</div>`;
  $("#app").innerHTML = shell(`
    ${admBackHead("admOlim")}
    <div class="sec">
      ${admEmpPickerHtml("olCard")}
      <div class="adm-seg" id="olDeg">
        <button data-v="phd">PhD</button>
        <button data-v="dsc">DSc</button>
        <button data-v="">${t("admDegNone")}</button>
      </div>
    </div>
    <div class="sec"><div class="adm-sub">${t("admOlimList")} · ${list.length}</div>${rows}</div>`);
  bindShell(); admBindBack();
  document.querySelectorAll("#olDeg button").forEach(b => b.onclick = async () => {
    const card = admPickedCard("olCard");
    if (!card) return admToast(t("admPickFirst"), false);
    document.querySelectorAll("#olDeg button").forEach(x => x.disabled = true);
    const ok = await setOlim(card, b.dataset.v);
    if (ok) { admToast(t("admDone")); admSecOlim(); }
    else { document.querySelectorAll("#olDeg button").forEach(x => x.disabled = false); admToast(t("admFail"), false); }
  });
  document.querySelectorAll(".adm-del").forEach(b => b.onclick = async () => {
    const ok = await setOlim(b.dataset.card, "");
    if (ok) { admToast(t("admDone")); admSecOlim(); } else admToast(t("admFail"), false);
  });
}

// ═════════════════════════ ARIZA (xodim <-> HR/rahbar) ═════════════════════════
const arizaTypeLbl = (ty) => t("arzT_" + ty) || ty;
function arizaStatusBadge(st) {
  if (st === "approved") return `<span class="badge ok">${t("arzApproved")}</span>`;
  if (st === "rejected") return `<span class="badge abs">${t("arzRejected")}</span>`;
  return `<span class="badge late">${t("arzPending")}</span>`;
}
function arizaDates(r) {
  if (!r.date_from) return "";
  const to = (r.date_to && r.date_to !== r.date_from) ? " → " + r.date_to : "";
  return ` · ${r.date_from}${to}`;
}
function arizaRow(r, isReview) {
  const main = isReview
    ? `<b>${esc(fmtName(r.full_name) || r.card_number)}</b><span>${esc(arizaTypeLbl(r.type))}${esc(arizaDates(r))}</span>`
    : `<b>${esc(arizaTypeLbl(r.type))}</b><span>${esc((r.text || "").slice(0, 46))}${esc(arizaDates(r))}</span>`;
  const right = (!isReview && r.status === "pending")
    ? `<button class="badge out arz-cancel" data-id="${esc(r.id)}">✖</button>`
    : arizaStatusBadge(r.status);
  return `<div class="pi clickable arz-item" data-id="${esc(r.id)}">
      <div class="nm">${main}</div>${right}</div>`;
}

// ─── Xodim: mening arizalarim ───
async function viewArizaMy() {
  const __g = VIEW_GEN;   // eskirgan yuklash yangi bo'limni bosib ketmasin
  $("#app").innerHTML = shell(skeleton(3)); bindShell();
  const { status, data } = await api("/api/mobile/ariza/my");
  if (status !== 200 || !data) { if (status === 401) return render(); return; }
  const reqs = data.requests || [];
  const rows = reqs.length ? reqs.map(r => arizaRow(r, false)).join("") : `<div class="empty">${t("arzMyNone")}</div>`;
  if (__g !== VIEW_GEN) return;
  $("#app").innerHTML = shell(`
    <div class="sec" style="margin-top:14px">
      <button class="btn adm-primary" id="arzNewBtn">➕ ${t("arzNew")}</button>
    </div>
    <div class="sec"><h3>${t("arzTitle")} · ${reqs.length}</h3>${rows}</div>`);
  bindShell();
  $("#arzNewBtn").onclick = arizaFormModal;
  const byId = {}; reqs.forEach(r => byId[r.id] = r);
  document.querySelectorAll(".arz-item").forEach(el => el.onclick = (ev) => {
    if (ev.target.closest(".arz-cancel")) return;
    arizaViewModal(byId[el.dataset.id]);
  });
  document.querySelectorAll(".arz-cancel").forEach(b => b.onclick = async (ev) => {
    ev.stopPropagation();
    if (!confirm(t("arzCancelQ"))) return;
    const { status: st } = await api("/api/mobile/ariza/cancel", { method: "POST", body: { id: b.dataset.id } });
    if (st === 200) viewArizaMy(); else admToast(t("admFail"), false);
  });
}

// ─── Xodim: yangi ariza formasi ───
function arizaFormModal() {
  const types = ["tatil", "ruxsat", "moddiy", "erkin"];
  const segs = types.map((ty, i) => `<button class="${i === 0 ? "on" : ""}" data-v="${ty}">${t("arzT_" + ty)}</button>`).join("");
  openModal(`
    <h3 style="margin:0 0 10px">${t("arzNew")}</h3>
    <div class="adm-sub">${t("arzType")}</div>
    <div class="adm-seg arz-types" id="arzTypes" style="flex-wrap:wrap;gap:6px">${segs}</div>
    <div id="arzDates" class="adm-2col">
      <label>${t("arzFrom")}<input type="date" class="adm-inp" id="arzFrom"></label>
      <label>${t("arzTo")}<input type="date" class="adm-inp" id="arzTo"></label>
    </div>
    <textarea class="adm-inp adm-ta" id="arzText" rows="4" placeholder="${t("arzTextPh")}"></textarea>
    ${sigPadHtml()}
    <button class="btn adm-primary" id="arzSendBtn">${t("arzSend")}</button>`);
  let curType = "tatil";
  const dates = $("#arzDates");
  const modal = document.querySelector(".modal-bg:last-of-type .modal") || document.querySelector(".modal");
  const pad = initSigPad(modal);
  const upd = () => { dates.style.display = (curType === "tatil" || curType === "ruxsat") ? "grid" : "none"; };
  upd();
  document.querySelectorAll("#arzTypes button").forEach(b => b.onclick = () => {
    curType = b.dataset.v;
    document.querySelectorAll("#arzTypes button").forEach(x => x.classList.toggle("on", x === b));
    upd();
  });
  $("#arzSendBtn").onclick = async () => {
    const text = ($("#arzText").value || "").trim();
    if (text.length < 5) return admToast(t("arzShort"), false);
    if (!pad || pad.isEmpty()) return admToast(t("sigNeed"), false);
    const body = { type: curType, text, signature: pad.dataURL() };
    if (curType === "tatil" || curType === "ruxsat") {
      body.date_from = $("#arzFrom").value; body.date_to = $("#arzTo").value;
      if (!body.date_from) return admToast(t("arzFrom"), false);
    }
    const btn = $("#arzSendBtn"); btn.disabled = true; btn.textContent = "…";
    const { status, data } = await api("/api/mobile/ariza/create", { method: "POST", body });
    if (status === 200) {
      const bg = document.querySelector(".modal-bg"); if (bg) bg.remove();
      admToast(t("arzSent")); viewArizaMy();
    } else { btn.disabled = false; btn.textContent = t("arzSend"); admToast((data && data.error) || t("admFail"), false); }
  };
}

// ─── Xodim: o'z arizasini ko'rish (javob bilan) ───
function arizaViewModal(r) {
  if (!r) return;
  const resp = r.response
    ? `<div class="adm-modbody" style="margin-top:10px"><b>${t("arzResponseLbl")}:</b> ${esc(r.response)}</div>` : "";
  const pdfBtn = r.id
    ? `<a class="btn secondary" href="/api/mobile/ariza/pdf/${encodeURIComponent(r.id)}?token=${encodeURIComponent(store.token)}" target="_blank">📄 ${t("expPdf")}</a>`
    : "";
  openModal(`
    <h3 style="margin:0 0 6px">${esc(arizaTypeLbl(r.type))}</h3>
    <div class="adm-modmeta">${arizaStatusBadge(r.status)} · ${esc(r.created_at || "")}${esc(arizaDates(r))}</div>
    <div class="adm-modbody">${esc(r.text || "")}</div>
    ${resp}${pdfBtn}`);
}

// ─── HR/rahbar: arizalarni ko'rib chiqish ───
async function viewArizaReview() {
  const __g = VIEW_GEN;   // eskirgan yuklash yangi bo'limni bosib ketmasin
  $("#app").innerHTML = shell(skeleton(4)); bindShell();
  const { status, data } = await api("/api/mobile/ariza/all");
  if (status === 403) { nav = "home"; return render(); }
  if (status !== 200 || !data) { if (status === 401) return render(); return; }
  const reqs = data.requests || [];
  const rows = reqs.length ? reqs.map(r => arizaRow(r, true)).join("") : `<div class="empty">${t("arzNone")}</div>`;
  if (__g !== VIEW_GEN) return;
  $("#app").innerHTML = shell(`
    <div class="sec" style="margin-top:14px"><h3>${t("arzReviewTitle")} · ${reqs.length}</h3>${rows}</div>`);
  bindShell(); setNavBadge2(data.pending || 0);
  const byId = {}; reqs.forEach(r => byId[r.id] = r);
  document.querySelectorAll(".arz-item").forEach(el => el.onclick = () => arizaReviewModal(byId[el.dataset.id]));
}

// ─── HR/rahbar: ariza qabul/rad modal ───
function arizaReviewModal(r) {
  if (!r) return;
  const isPending = r.status === "pending";
  const btns = isPending
    ? `<button class="arz-approve">${t("arzApprove")}</button><button class="arz-reject">${t("arzReject")}</button>`
    : `<button class="arz-reopen">${t("arzReopen")}</button>`;
  const pdfBtn = r.id
    ? `<a class="btn secondary" href="/api/mobile/ariza/pdf/${encodeURIComponent(r.id)}?token=${encodeURIComponent(store.token)}" target="_blank">📄 ${t("expPdf")}</a>`
    : "";
  openModal(`
    <h3 style="margin:0 0 6px">${esc(fmtName(r.full_name) || r.card_number)}</h3>
    <div class="adm-modmeta">${arizaStatusBadge(r.status)} · ${esc(arizaTypeLbl(r.type))} · ${esc(r.created_at || "")}${esc(arizaDates(r))}</div>
    <div class="adm-modbody">${esc(r.text || "")}</div>
    ${pdfBtn}
    <input class="adm-inp" id="arzResp" style="margin-top:10px" placeholder="${t("arzResponse")}" value="${esc(r.response || "")}">
    <div class="adm-seg" style="margin-top:2px">${btns}</div>
    <button class="arz-del-btn" id="arzDelBtn">${t("arzDelete")}</button>`);
  const doReview = async (st) => {
    const resp = ($("#arzResp") || {}).value || "";
    const { status } = await api("/api/mobile/ariza/review", { method: "POST", body: { id: r.id, status: st, response: resp } });
    if (status === 200) {
      const bg = document.querySelector(".modal-bg"); if (bg) bg.remove();
      admToast(t("admDone")); viewArizaReview();
    } else admToast(t("admFail"), false);
  };
  const ap = document.querySelector(".arz-approve"); if (ap) ap.onclick = () => doReview("approved");
  const rj = document.querySelector(".arz-reject"); if (rj) rj.onclick = () => doReview("rejected");
  const ro = document.querySelector(".arz-reopen"); if (ro) ro.onclick = () => doReview("pending");
  const dl = $("#arzDelBtn");
  if (dl) dl.onclick = async () => {
    if (!confirm(t("arzDeleteQ"))) return;
    const { status } = await api("/api/mobile/ariza/delete", { method: "POST", body: { id: r.id } });
    if (status === 200) {
      const bg = document.querySelector(".modal-bg"); if (bg) bg.remove();
      admToast(t("admDone")); viewArizaReview();
    } else admToast(t("admFail"), false);
  };
}

// ─────────── router ───────────
// ═════════════════════ 📅 BRON (Zoom xonalar) ═════════════════════
const BR = { tab: "book", day: "", night: false, myScope: "upcoming",
             allFrom: "", allTo: "", stFrom: "", stTo: "", stRoom: 0, st: null };
const BR_WD = ["Yakshanba", "Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba"];
const BR_WDS = ["Ya", "Du", "Se", "Ch", "Pa", "Ju", "Sh"];
function brIso(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
function brAdd(iso, n) { const d = new Date(iso + "T00:00"); d.setDate(d.getDate() + n); return brIso(d); }
function brDayLabel(iso, long) {
  const d = new Date(iso + "T00:00"), today = brIso(new Date());
  const dm = `${String(d.getDate()).padStart(2, "0")}.${String(d.getMonth() + 1).padStart(2, "0")}`;
  if (iso === today) return long ? `Bugun, ${dm}` : "Bugun";
  if (iso === brAdd(today, 1)) return long ? `Ertaga, ${dm}` : "Ertaga";
  return long ? `${BR_WD[d.getDay()]}, ${dm}` : `${BR_WDS[d.getDay()]} ${dm}`;
}
const brStatusCls = { active: "ok", completed: "done", cancelled: "off", no_show: "bad" };

async function viewBron() {
  const __g = VIEW_GEN;
  $("#app").innerHTML = shell(`<div class="sec"><div class="empty">${t("daysLoad")}</div></div>`);
  bindShell();
  if (!BR.day) BR.day = brIso(new Date());
  const { status, data } = await api("/api/mobile/bron/state?date=" + BR.day);
  if (__g !== VIEW_GEN) return;
  if (status !== 200 || !data) {
    $("#app").innerHTML = shell(`<div class="sec"><div class="empty">${(data && data.error) || t("admFail")}</div></div>`);
    return bindShell();
  }
  BR.data = data;
  BR.day = data.date;
  if (!data.view_all && (BR.tab === "all" || BR.tab === "stats")) BR.tab = "book";
  BRON_N = data.notices || 0;

  const tabs = [["book", "🗓 Bron qilish"], ["my", "📋 Mening bronlarim"],
    ...(data.view_all ? [["all", "🏢 Barcha bronlar"], ["stats", "📊 Statistika"]] : [])];
  $("#app").innerHTML = shell(`
    <div class="sec br">
      <div class="br-head">
        <h3>📅 Zoom xonalarni bron qilish</h3>
      </div>
      <div id="brNotice"></div>
      <div class="br-tabs">${tabs.map(([k, l]) =>
        `<button class="${BR.tab === k ? "on" : ""}" data-t="${k}">${l}${k === "my" && BRON_N
          ? ` <b class="br-dot">${BRON_N}</b>` : ""}</button>`).join("")}</div>
      <div id="brBody"></div>
    </div>`);
  bindShell();
  document.querySelectorAll(".br-tabs button").forEach(b => b.onclick = () => {
    BR.tab = b.dataset.t;
    document.querySelectorAll(".br-tabs button").forEach(x => x.classList.toggle("on", x === b));
    brBody();
  });
  brNotices();
  brBody();
}

function brBody() {
  if (BR.tab === "my") return brMy();
  if (BR.tab === "all") return brAll();
  if (BR.tab === "stats") return brStats();
  return brBook();
}

// Qatnashchi sifatida qo'shilganlik haqida xabar
async function brNotices() {
  const box = $("#brNotice");
  if (!box) return;
  const { status, data } = await api("/api/mobile/bron/notices");
  const items = (status === 200 && data && data.items) || [];
  BRON_N = items.length; paintBronBadge();
  if (!items.length) { box.innerHTML = ""; return; }
  box.innerHTML = `<div class="br-notice">
      <b>🔔 Sizni yig'ilishga qo'shishdi</b>
      ${items.map(b => `<div class="br-nrow">
        <span>${esc(brDayLabel(b.date, true))} · <b>${b.start}–${b.end}</b> · ${esc(b.room_name)}</span>
        <em>${esc(shortName(b.owner_name))}${b.title ? " — " + esc(b.title) : ""}</em></div>`).join("")}
      <button class="adm-btn sm" id="brSeen">✓ Tushunarli</button></div>`;
  $("#brSeen").onclick = async () => {
    await api("/api/mobile/bron/notices/seen", { method: "POST", body: {} });
    BRON_N = 0; paintBronBadge(); box.innerHTML = "";
    const dot = document.querySelector(".br-dot"); if (dot) dot.remove();
  };
}

// ─── Bron qilish: kunlar + xonalar jadvali ───
function brBook() {
  const d = BR.data, body = $("#brBody");
  if (!body) return;
  const nowIso = d.now;
  const days = d.days.map(x => `<button class="${x === d.date ? "on" : ""}" data-d="${x}">${esc(brDayLabel(x))}</button>`).join("");
  const rooms = d.rooms.map(r => {
    const slots = r.slots.map((s, i) => {
      const h = +s.start.slice(0, 2);
      if (!BR.night && (h < 7 || h >= 21) && !(!s.free && !s.past)) return "";
      const cls = s.past ? "past" : s.free ? "free" : s.mine ? "mine" : "busy";
      const tip = s.free ? (s.past ? "O'tgan" : "Bo'sh") : "Band: " + s.by;
      return `<button class="br-slot ${cls}" data-r="${r.id}" data-i="${i}" title="${esc(tip)}">
        <b>${s.start}</b>${!s.free ? `<span>${esc(shortName(s.by).split(" ")[0])}</span>` : ""}</button>`;
    }).join("");
    const free = r.slots.filter(s => s.free && !s.past).length;
    return `<div class="br-room">
      <div class="br-rh"><b>🎥 ${esc(r.name)}</b><span>${free ? free / 2 + " soat bo'sh" : "bo'sh vaqt yo'q"}</span></div>
      <div class="br-grid">${slots || `<div class="empty">—</div>`}</div></div>`;
  }).join("");
  body.innerHTML = `
    ${d.can_book ? "" : `<div class="br-warn">ℹ️ ${esc(d.why || "Bron qilish imkoni yo'q")}. Jadvalni faqat ko'rishingiz mumkin.</div>`}
    <div class="br-days">${days}</div>
    <div class="br-legend">
      <span><i class="free"></i>Bo'sh</span><span><i class="busy"></i>Band</span>
      <span><i class="mine"></i>Sizniki</span><span><i class="past"></i>O'tgan</span>
      <label><input type="checkbox" id="brNight"${BR.night ? " checked" : ""}> Tungi soatlar</label>
    </div>
    ${rooms ? `<div class="br-rooms2">${rooms}</div>` : `<div class="empty">Faol xona yo'q</div>`}
    <p class="adm-hint">Bo'sh vaqtni bosing → davomiylikni tanlang. Bron ${BR.data.confirm_window} daqiqa ichida
      "Boshladim" bosilmasa bekor bo'ladi.</p>`;
  body.querySelectorAll(".br-days button").forEach(b => b.onclick = () => { BR.day = b.dataset.d; viewBron(); });
  $("#brNight").onchange = (e) => { BR.night = e.target.checked; brBook(); };
  body.querySelectorAll(".br-slot").forEach(b => b.onclick = () => {
    const r = d.rooms.find(x => String(x.id) === b.dataset.r);
    const s = r && r.slots[+b.dataset.i];
    if (!s) return;
    if (!s.free) return admToast((s.mine ? "Sizning broningiz: " : "Band: ") + fmtName(s.by), !!s.mine);
    if (s.past) return admToast("Bu vaqt o'tib ketgan", false);
    if (!d.can_book) return admToast(d.why || "Bron qilish imkoni yo'q", false);
    brCreateModal(r, s);
  });
}

async function brCreateModal(room, slot) {
  const start = `${BR.data.date}T${slot.start}`;
  const { data } = await api(`/api/mobile/bron/durations?room=${room.id}&start=${encodeURIComponent(start)}`);
  const durs = (data && data.durations) || [];
  if (!durs.length) return admToast("Bu vaqtdan boshlab xona bo'sh emas", false);
  const all = BR.data.durations;
  const lbl = (m) => m < 60 ? `${m} daqiqa` : `${m / 60} soat`;
  const endOf = (m) => { const d = new Date(start); d.setMinutes(d.getMinutes() + m);
    return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`; };
  let dur = durs.includes(60) ? 60 : durs[0];
  const picked = [];
  openModal(`
    <h3 style="margin:0 0 4px">🎥 ${esc(room.name)}</h3>
    <p class="adm-hint" style="margin:0 0 12px">${esc(brDayLabel(BR.data.date, true))} · boshlanishi <b>${slot.start}</b></p>
    <label class="ak-lbl">Davomiylik</label>
    <div class="br-durs">${all.map(m => `<button data-m="${m}" ${durs.includes(m) ? "" : "disabled"}
       class="${m === dur ? "on" : ""}">${lbl(m)}<small>${durs.includes(m) ? "gacha " + endOf(m) : "band"}</small></button>`).join("")}</div>
    <label class="ak-lbl">Mavzu (ixtiyoriy)</label>
    <input class="adm-inp" id="brTitle" maxlength="150" placeholder="Masalan: Loyiha muhokamasi">
    <label class="ak-lbl">Qatnashchilar (ixtiyoriy)</label>
    <p class="adm-hint" style="margin:0 0 6px">Qo'shilgan hamkasbga ilovada xabar boradi, bron uning ro'yxatida ham ko'rinadi.</p>
    <div class="br-chips" id="brChips"></div>
    <input class="adm-inp" id="brQ" placeholder="Xodim ismini yozing…" autocomplete="off">
    <div class="br-found" id="brFound"></div>
    <button class="adm-btn" id="brGo" style="margin-top:6px">✅ Bron qilish</button>`);
  const M = document.querySelector(".modal-bg:last-of-type");
  const q = (s) => M.querySelector(s);
  M.querySelectorAll(".br-durs button").forEach(b => b.onclick = () => {
    if (b.disabled) return;
    dur = +b.dataset.m;
    M.querySelectorAll(".br-durs button").forEach(x => x.classList.toggle("on", x === b));
  });
  const chips = () => {
    q("#brChips").innerHTML = picked.map((p, i) =>
      `<span class="br-chip">${esc(shortName(p.name))}<button data-i="${i}">×</button></span>`).join("");
    q("#brChips").querySelectorAll("button").forEach(b => b.onclick = () => { picked.splice(+b.dataset.i, 1); chips(); });
  };
  let timer = null;
  q("#brQ").oninput = (e) => {
    clearTimeout(timer);
    const v = e.target.value.trim();
    if (v.length < 2) { q("#brFound").innerHTML = ""; return; }
    timer = setTimeout(async () => {
      const r = await api("/api/mobile/bron/people?q=" + encodeURIComponent(v));
      const items = ((r.data && r.data.items) || []).filter(x => !picked.some(p => p.card === x.card));
      q("#brFound").innerHTML = items.length ? items.map(x =>
        `<div class="br-person" data-c="${esc(x.card)}" data-n="${esc(x.name)}"><b>${esc(fmtName(x.name))}</b><span>${esc(x.department)}</span></div>`).join("")
        : `<div class="adm-hint" style="margin:6px 2px">Topilmadi</div>`;
      q("#brFound").querySelectorAll(".br-person").forEach(el => el.onclick = () => {
        picked.push({ card: el.dataset.c, name: el.dataset.n });
        q("#brQ").value = ""; q("#brFound").innerHTML = ""; chips(); q("#brQ").focus();
      });
    }, 250);
  };
  q("#brGo").onclick = async () => {
    const b = q("#brGo"); b.disabled = true;
    const r = await api("/api/mobile/bron/create", { method: "POST", body: {
      room: room.id, start, duration: dur, title: q("#brTitle").value.trim(),
      participants: picked.map(p => p.card) } });
    b.disabled = false;
    if (r.status === 200) {
      M.remove();
      admToast(`✅ Bron qilindi: ${slot.start}–${endOf(dur)}`);
      viewBron();
    } else {
      admToast((r.data && r.data.error) || t("admFail"), false);
      if (r.status === 409) { M.remove(); viewBron(); }
    }
  };
}

// ─── Bron kartasi (mening / barcha) ───
function brCard(b, opts = {}) {
  const who = b.is_owner ? "" : `<div class="br-who">👤 ${esc(fmtName(b.owner_name))}${b.owner_department
    ? ` · <span>${esc(b.owner_department)}</span>` : ""}</div>`;
  const parts = b.participants.length ? `<div class="br-parts">👥 ${b.participants.map(p => esc(shortName(p.name))).join(", ")}</div>` : "";
  const btns = [
    b.can_confirm ? `<button class="adm-btn sm br-conf" data-id="${b.id}">▶ Boshladim</button>` : "",
    b.can_cancel ? `<button class="sv-act del br-cancel" data-id="${b.id}">${opts.hr && !b.is_owner ? "HR: bekor qilish" : "Bekor qilish"}</button>` : "",
  ].join("");
  const hint = b.status === "active" && !b.confirmed
    ? `<div class="br-hint">⏱ ${b.start} dan keyin ${b.confirm_deadline} gacha "Boshladim" bosilmasa, bron bekor bo'ladi</div>`
    : b.status === "active" && b.confirmed ? `<div class="br-hint ok">✓ Boshlangan${b.running ? " — hozir davom etmoqda" : ""}</div>` : "";
  return `<div class="br-card">
    <div class="br-ct">
      <div><b>${b.start}–${b.end}</b> <span class="br-date">${esc(brDayLabel(b.date, true))}</span></div>
      <span class="br-st ${brStatusCls[b.status] || ""}">${esc(b.status_uz)}${b.cancelled_by_hr ? " (HR)" : ""}</span>
    </div>
    <div class="br-rn">🎥 ${esc(b.room_name)}${b.title ? ` · <i>${esc(b.title)}</i>` : ""}</div>
    ${who}${parts}${hint}
    ${btns ? `<div class="br-btns">${btns}</div>` : ""}
  </div>`;
}
function brBindCards(root, reload) {
  root.querySelectorAll(".br-conf").forEach(b => b.onclick = async () => {
    b.disabled = true;
    const r = await api("/api/mobile/bron/confirm", { method: "POST", body: { id: +b.dataset.id } });
    if (r.status === 200) { admToast("✅ Yig'ilish boshlandi"); reload(); }
    else { b.disabled = false; admToast((r.data && r.data.error) || t("admFail"), false); }
  });
  root.querySelectorAll(".br-cancel").forEach(b => b.onclick = async () => {
    if (!confirm("Bronni bekor qilmoqchimisiz?")) return;
    b.disabled = true;
    const r = await api("/api/mobile/bron/cancel", { method: "POST", body: { id: +b.dataset.id } });
    if (r.status === 200) { admToast("Bron bekor qilindi"); reload(); }
    else { b.disabled = false; admToast((r.data && r.data.error) || t("admFail"), false); }
  });
}

async function brMy() {
  const body = $("#brBody");
  body.innerHTML = `<div class="br-sub">
      <button class="${BR.myScope === "upcoming" ? "on" : ""}" data-s="upcoming">Kelgusi</button>
      <button class="${BR.myScope === "past" ? "on" : ""}" data-s="past">O'tgan</button></div>
    <div id="brList"><div class="empty">${t("daysLoad")}</div></div>`;
  body.querySelectorAll(".br-sub button").forEach(b => b.onclick = () => { BR.myScope = b.dataset.s; brMy(); });
  const { data } = await api("/api/mobile/bron/my?scope=" + BR.myScope);
  const items = (data && data.items) || [];
  const list = $("#brList");
  if (!list) return;
  list.innerHTML = items.length ? `<div class="br-cards">${items.map(b => brCard(b)).join("")}</div>`
    : `<div class="empty">${BR.myScope === "upcoming" ? "Kelgusi bronlaringiz yo'q" : "O'tgan bronlar yo'q"}</div>`;
  brBindCards(list, brMy);
}

async function brAll() {
  const body = $("#brBody");
  const today = brIso(new Date());
  if (!BR.allFrom) { BR.allFrom = today; BR.allTo = brAdd(today, 7); }
  body.innerHTML = `<div class="br-range">
      <input type="date" class="adm-inp" id="brAF" value="${BR.allFrom}">
      <input type="date" class="adm-inp" id="brAT" value="${BR.allTo}">
      <button class="adm-btn sm" id="brAGo">Ko'rsatish</button></div>
    <div id="brList"><div class="empty">${t("daysLoad")}</div></div>`;
  $("#brAGo").onclick = () => { BR.allFrom = $("#brAF").value || today; BR.allTo = $("#brAT").value || BR.allFrom; brAll(); };
  const { data } = await api(`/api/mobile/bron/all?from=${BR.allFrom}&to=${BR.allTo}`);
  const items = (data && data.items) || [];
  const list = $("#brList");
  if (!list) return;
  if (!items.length) { list.innerHTML = `<div class="empty">Bu davrda bron yo'q</div>`; return; }
  const byDay = {};
  items.forEach(b => (byDay[b.date] = byDay[b.date] || []).push(b));
  list.innerHTML = Object.keys(byDay).sort().map(dy => `
    <div class="br-dayh">${esc(brDayLabel(dy, true))} <span>${byDay[dy].length} ta</span></div>
    <div class="br-cards">${byDay[dy].map(b => brCard(b, { hr: true })).join("")}</div>`).join("");
  brBindCards(list, brAll);
}

async function brStats() {
  const body = $("#brBody");
  const today = brIso(new Date());
  if (!BR.stFrom) { BR.stFrom = brAdd(today, -29); BR.stTo = today; }
  body.innerHTML = `<div class="empty">${t("daysLoad")}</div>`;
  const { status, data } = await api(`/api/mobile/bron/stats?from=${BR.stFrom}&to=${BR.stTo}&room=${BR.stRoom || 0}`);
  if (status !== 200 || !data) { body.innerHTML = `<div class="empty">${(data && data.error) || t("admFail")}</div>`; return; }
  const s = data.summary;
  const tile = (v, l, c = "") => `<div class="br-tile ${c}"><b>${v}</b><span>${l}</span></div>`;
  const maxR = Math.max(1, ...data.rooms.map(r => r.hours));
  const tbl = (rows, col) => rows.length ? `<div class="br-tbl"><div class="br-tr h"><span>${col}</span><span>Bron</span><span>Soat</span><span>Kelinmadi</span></div>
    ${rows.map(r => `<div class="br-tr"><span>${esc(col === "Xodim" ? fmtName(r.name) : r.name)}</span><span>${r.bookings}</span><span>${r.hours}</span><span>${r.no_show || ""}</span></div>`).join("")}</div>`
    : `<div class="empty">Ma'lumot yo'q</div>`;
  const hmax = Math.max(1, ...data.heatmap.flat());
  const hours = [];
  for (let h = 7; h < 21; h++) hours.push(h);
  const heat = `<div class="br-heat"><div class="br-hr"><i></i>${hours.map(h => `<i>${h}</i>`).join("")}</div>
    ${[1, 2, 3, 4, 5, 6, 0].map(w => { const wi = (w + 6) % 7;   // backend: 0=Du
      return `<div class="br-hr"><i>${BR_WDS[w]}</i>${hours.map(h => { const n = data.heatmap[wi][h];
        return `<i class="c" style="--a:${(n / hmax).toFixed(2)}" title="${n} ta">${n || ""}</i>`; }).join("")}</div>`; }).join("")}</div>`;
  body.innerHTML = `
    <div class="br-range">
      <input type="date" class="adm-inp" id="brSF" value="${BR.stFrom}">
      <input type="date" class="adm-inp" id="brST" value="${BR.stTo}">
      <select class="adm-inp" id="brSR"><option value="0">Barcha xonalar</option>${data.all_rooms.map(r =>
        `<option value="${r.id}"${+BR.stRoom === r.id ? " selected" : ""}>${esc(r.name)}${r.active ? "" : " (o'chirilgan)"}</option>`).join("")}</select>
      <button class="adm-btn sm" id="brSGo">Ko'rsatish</button>
    </div>
    <div class="br-pre">
      <button data-p="7">Oxirgi 7 kun</button><button data-p="30">Oxirgi 30 kun</button><button data-p="m">Shu oy</button>
    </div>
    <div class="br-tiles">
      ${tile(s.total, "Jami bronlar")}${tile(s.completed, "Yakunlangan", "ok")}
      ${tile(s.no_show, "Kelinmagan", "bad")}${tile(s.cancelled, "Bekor qilingan", "off")}
      ${tile(s.no_show_rate + "%", "Kelmaslik ulushi")}${tile(s.hours, "Jami soat")}
    </div>
    <div class="br-exp">
      <button class="adm-btn ghost sm" id="brX">⬇ Excel</button>
      <button class="adm-btn ghost sm" id="brW">⬇ Word</button>
    </div>
    <div class="adm-sub">Xonalar · bandlik 24 soatga nisbatan</div>
    ${data.rooms.map(r => `<div class="br-rbar"><div><b>${esc(r.name)}</b><em>${r.bookings} bron · ${r.hours} soat · ${r.occupancy}%</em></div>
      <div class="sv-bar-bg"><i style="width:${(r.hours / maxR * 100).toFixed(0)}%"></i></div></div>`).join("")}
    <div class="adm-sub" style="margin-top:14px">Eng gavjum soatlar</div>${heat}
    <div class="adm-sub" style="margin-top:14px">Bo'limlar kesimida</div>${tbl(data.departments, "Bo'lim")}
    <div class="adm-sub" style="margin-top:14px">Xodimlar kesimida</div>${tbl(data.employees.slice(0, 30), "Xodim")}
    ${BR.data.is_hr ? `<div class="adm-sub" style="margin-top:14px">Xonalarni boshqarish</div><div id="brRooms"></div>` : ""}`;
  $("#brSGo").onclick = () => { BR.stFrom = $("#brSF").value || BR.stFrom; BR.stTo = $("#brST").value || BR.stTo;
    BR.stRoom = +$("#brSR").value || 0; brStats(); };
  body.querySelectorAll(".br-pre button").forEach(b => b.onclick = () => {
    const p = b.dataset.p;
    BR.stTo = today;
    BR.stFrom = p === "m" ? today.slice(0, 8) + "01" : brAdd(today, -(+p - 1));
    BR.stRoom = +$("#brSR").value || 0; brStats();
  });
  const q = `from=${data.from}&to=${data.to}&room=${BR.stRoom || 0}`;
  $("#brX").onclick = () => downloadAuth("/api/mobile/bron/export?format=xlsx&" + q);
  $("#brW").onclick = () => downloadAuth("/api/mobile/bron/export?format=docx&" + q);
  if (BR.data.is_hr) brRoomsAdmin(data.all_rooms);
}

function brRoomsAdmin(rooms) {
  const box = $("#brRooms");
  if (!box) return;
  box.innerHTML = `${rooms.map(r => `<div class="ak-tpl">
      <div class="nm"><b>${esc(r.name)}</b><span>${r.active ? "🟢 faol" : "⚪ o'chirilgan — bron qilinmaydi"}</span></div>
      <button class="sv-act br-ren" data-id="${r.id}" data-n="${esc(r.name)}" title="Nomini o'zgartirish">✏️</button>
      <button class="sv-act br-tog" data-id="${r.id}" data-a="${r.active ? 0 : 1}">${r.active ? "O'chirish" : "Yoqish"}</button>
    </div>`).join("")}
    <div class="br-range" style="margin-top:10px"><input class="adm-inp" id="brNewRoom" placeholder="Yangi xona nomi">
      <button class="adm-btn sm" id="brAddRoom">➕ Qo'shish</button></div>`;
  const send = async (body) => {
    const r = await api("/api/mobile/bron/rooms", { method: "POST", body });
    if (r.status === 200) { admToast(t("admDone")); brStats(); }
    else admToast((r.data && r.data.error) || t("admFail"), false);
  };
  box.querySelectorAll(".br-ren").forEach(b => b.onclick = () => {
    const n = prompt("Xonaning yangi nomi:", b.dataset.n);
    if (n && n.trim()) send({ action: "rename", id: +b.dataset.id, name: n.trim() });
  });
  box.querySelectorAll(".br-tog").forEach(b => b.onclick = () => {
    if (b.dataset.a === "0" && !confirm("Xona o'chirilsa, unga yangi bron qilib bo'lmaydi. Mavjud bronlar saqlanadi. Davom etasizmi?")) return;
    send({ action: "toggle", id: +b.dataset.id, active: b.dataset.a === "1" });
  });
  $("#brAddRoom").onclick = () => { const n = $("#brNewRoom").value.trim(); if (n) send({ action: "add", name: n }); };
}

function render() {
  VIEW_GEN++;
  applyTheme();
  if (!store.token) return viewLogin();
  const isHR = canViewAll();
  if (isHR) {
    if (nav === "admin") return viewAdmin();
    if (nav === "ariza") return viewArizaReview();
    if (nav === "staff") return viewHR(true);
    if (nav === "exp") return viewExpList();
    return viewHR(false);
  }
  if (nav === "ariza") return viewArizaMy();
  if (nav === "exp") return viewMyExp();
  nav = "home";
  return viewMe();
}

// PWA service worker
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("sw.js").catch(() => {}));
}

render();
