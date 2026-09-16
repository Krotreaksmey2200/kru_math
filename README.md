# 🤖 Telegram Math Bot: ដេរីវេនៃអនុគមន៍ (Derivative of Functions)

> ប្រព័ន្ធស្វ័យប្រវត្តិតាម Telegram សម្រាប់លោកគ្រូអ្នកគ្រូបង្រៀនគណិតវិទ្យា (ថ្នាក់ទី១១ ទី១២ និងត្រៀមប្រឡងបាក់ឌុប) ក្នុងការចែករំលែករូបមន្ត និងលំហាត់ដេរីវេ ជាមួយដំណោះស្រាយលម្អិតមួយជំហានៗ។

---

## 🌟 លក្ខណៈពិសេសចម្បង (Key Features)

1. **🔒 Group Privacy Protection (ការការពារភាពឯកជនក្នុងគ្រុប)**
   - **Mechanism A (Direct Message Delivery):** នៅពេលសិស្សសួរ ឬចុចមើលដំណោះស្រាយក្នុងគ្រុប បូតនឹងផ្ញើដំណោះស្រាយទៅកាន់ **សារផ្ទាល់ខ្លួន (DM)** របស់សិស្សនោះភ្លាមៗ ដើម្បីកុំឱ្យបែកធ្លាយចម្លើយដល់សិស្សដទៃ។ បន្ទាប់មក បូតផ្ញើសារជូនដំណឹងក្នុងគ្រុបថា _«ដំណោះស្រាយត្រូវបានផ្ញើទៅកាន់សារផ្ទាល់ខ្លួនរបស់អ្នកហើយ»_ ហើយសារនេះនឹង **លុបដោយស្វ័យប្រវត្តិក្នង ៨ វិនាទី**។
   - **Deep-link Fallback:** បើសិនសិស្សមិនទាន់បានចុច Start បូតក្នុង DM ពីមុនមក បូតនឹងបង្ហាញប៊ូតុង `[ 📖 បើកមើលដំណោះស្រាយក្នុង DM ]` (`t.me/bot?start=ex_1`) ដើម្បីឱ្យសិស្សចុចទៅបើកមើលដោយផ្ទាល់។
   - **Mechanism B (Inline Query Mode):** សិស្សអាចវាយ `@botusername sin(x)` ឬ `@botusername លំហាត់១` ក្នុងគ្រុបណាមួយ ដើម្បីមើលរូបមន្ត និងដំណោះស្រាយជាលក្ខណៈឯកជនភ្លាមៗ។

2. **⚡️ Dynamic Lesson Updates (កែប្រែ/បន្ថែមមេរៀនដោយមិនបាច់សរសេរកូដ)**
   - **Admin-only Commands:** លោកគ្រូអាចបន្ថែម ឬលុបលំហាត់ដោយផ្ទាល់ពី Telegram តាមរយៈពាក្យបញ្ជា `/add`, `/delete`, `/stats`, `/broadcast` ដោយសុវត្ថិភាពតាមរយៈ Telegram User ID។
   - **Google Sheets Live Sync:** អាចភ្ជាប់ជាមួយ Google Sheet របស់លោកគ្រូ។ រាល់ពេលបន្ថែមលំហាត់ក្នុង Spreadsheet គ្រាន់តែវាយ `/sync_sheets` នោះបូតនឹង Update ស្វ័យប្រវត្តិ។
   - **SQLite Database:** រក្សាទុកទិន្នន័យយ៉ាងរឹងមាំ មិនបាត់បង់ទិន្នន័យពេល Restart។

3. **📚 មូលដ្ឋានទិន្នន័យរូបមន្ត និងលំហាត់ដេរីវេ**
   - រូបមន្តគ្រឹះ (Power Rule, Constant, 1/x, $\sqrt{x}$)
   - ច្បាប់ផលបូក ផលគុណ ផលចែក ($u \pm v$, $u \cdot v$, $u/v$)
   - ដេរីវេបណ្ដាក់ (Chain Rule: $f(g(x))$, $u^n$)
   - អនុគមន៍ត្រីកោណមាត្រ ($\sin x$, $\cos x$, $\tan x$)
   - អិចស្បូណង់ស្យែល និងលោការីត ($e^x$, $\ln x$)
   - លំហាត់គំរូត្រៀមប្រឡងបាក់ឌុប រួមជាមួយដំណើរការដោះស្រាយមួយជំហានៗ។

---

## 📁 រចនាសម្ព័ន្ធគម្រោង (Project Architecture)

```text
Telegram_bot/
├── bot.py                  # ច្រកចូលកម្មវិធីចម្បង (Main Telegram application & polling)
├── config.py               # ការកំណត់អថេរបរិស្ថាន (Config & environment variables)
├── database.py             # SQLite database layer & User tracking
├── sheets_sync.py          # Google Sheets synchronization engine
├── lessons.json            # មូលដ្ឋានទិន្នន័យរូបមន្ត និងលំហាត់ដំបូង (Initial Seed)
├── web_server.py           # HTTP Health-check server (សម្រាប់ Render/Koyeb)
├── handlers/
│   ├── __init__.py
│   ├── start_help.py       # /start, /help, deep-linking handler
│   ├── exercises.py        # ម៉ឺនុយរូបមន្ត លំហាត់ និងប៊ូតុងចុច (Interactive keyboards)
│   ├── search.py           # ស្វែងរកតាមពាក្យគន្លឹះ (Keyword & math search)
│   ├── group_privacy.py    # ប្រព័ន្ធបញ្ជូនដំណោះស្រាយទៅ DM & auto-delete notice
│   ├── inline_query.py     # មុខងារ Inline (@botusername query)
│   └── admin.py            # ពាក្យបញ្ជាសម្រាប់លោកគ្រូ (Teacher Admin)
├── requirements.txt        # Python dependencies
├── Procfile                # កំណត់ដំណើរការសម្រាប់ Cloud Hosting
├── Dockerfile              # Container deployment config
├── render.yaml             # Render 1-click blueprint
├── .env.example            # គំរូ File កំណត់ Token
└── README.md               # ឯកសារណែនាំលម្អិត
```

---

## 🚀 របៀបដំឡើង BotFather លើ Telegram (សំខាន់ខ្លាំង)

ដើម្បីឱ្យបូតដំណើរការមុខងារ Group Privacy និង Inline Mode បានពេញលេញ សូមកំណត់តាមជំហានខាងក្រោមជាមួយ [@BotFather](https://t.me/BotFather):

### ១. បង្កើត Bot ថ្មី
1. ចូលទៅកាន់ [@BotFather](https://t.me/BotFather) រួចផ្ញើ `/newbot`
2. ដាក់ឈ្មោះបូត (ឧទាហរណ៍៖ `Math Derivative Assistant`)
3. ដាក់ username បូត (ត្រូវបញ្ចប់ដោយ `bot`, ឧទាហរណ៍៖ `bacii_derivative_bot`)
4. អ្នកនឹងទទួលបាន **HTTP API Token** (ឧទាហរណ៍៖ `7123456789:AAFx...`) -> ចម្លងទុកសម្រាប់ដាក់ក្នុង `BOT_TOKEN`

### ២. បិទ Group Privacy (Disable Group Privacy Mode)
> ⚠️ **ចាំបាច់ត្រូវធ្វើ៖** បើមិនបិទ Privacy ទេ បូតនឹងមិនអាចអានសារសំណួររបស់សិស្សក្នុងគ្រុបបានឡើយ!
1. ក្នុង [@BotFather](https://t.me/BotFather) ផ្ញើ `/setprivacy`
2. ជ្រើសរើស username បូតរបស់អ្នក
3. ចុចជ្រើសរើស **Disable** (អ្នកនឹងឃើញសារ `Privacy mode is now disabled`)

### ៣. បើកដំណើរការ Inline Mode
> 💡 សម្រាប់ឱ្យសិស្សវាយ `@botusername keyword` ក្នុងគ្រុបដើម្បីមើលដំណោះស្រាយជាឯកជន
1. ក្នុង [@BotFather](https://t.me/BotFather) ផ្ញើ `/setinline`
2. ជ្រើសរើស username បូតរបស់អ្នក
3. វាយបញ្ចូលពាក្យ Placeholder ឧទាហរណ៍៖ `ស្វែងរករូបមន្ត ឬលំហាត់ដេរីវេ...`

### ៤. កំណត់បញ្ជីពាក្យបញ្ជា (Menu Commands)
ផ្ញើ `/setcommands` ទៅកាន់ [@BotFather](https://t.me/BotFather) រួច Paste បញ្ជីនេះ៖
```text
start - បើកម៉ឺនុយមេរៀន និងលំហាត់ (Start)
formulas - រូបមន្តដេរីវេទាំងអស់ (Formulas)
exercises - លំហាត់អនុវត្តដេរីវេ (Exercises)
search - ស្វែងរករូបមន្ត/លំហាត់ (Search)
help - ជំនួយ និងរបៀបប្រើប្រាស់ (Help)
admin - ផ្ទាំងគ្រប់គ្រងលោកគ្រូ (Admin Only)
stats - មើលស្ថិតិសិស្ស និងលំហាត់ (Stats)
```

### ៥. ស្វែងរក Telegram User ID របស់លោកគ្រូ
1. ចូលទៅកាន់ [@userinfobot](https://t.me/userinfobot) រួចចុច Start
2. ចម្លងលេខ **Id** របស់អ្នក (ឧទាហរណ៍៖ `189283741`) -> យកមកដាក់ក្នុង `TEACHER_ADMIN_ID`

---

## 💻 របៀបតេស្តដំណើរការលើម៉ាស៊ីនផ្ទាល់ខ្លួន (Local Run)

### ជំហានទី១៖ Clone / បើក Folder គម្រោង
```bash
cd Telegram_bot
```

### ជំហានទី២៖ បង្កើត Virtual Environment និងដំឡើង Library
```bash
python3 -m venv venv
source venv/bin/activate   # លើ Mac/Linux
# ឬ .\venv\Scripts\activate លើ Windows

pip install -r requirements.txt
```

### ជំហានទី៣៖ បង្កើត File `.env`
ចម្លងពី `.env.example`:
```bash
cp .env.example .env
```
បើក file `.env` រួចបំពេញ៖
```env
BOT_TOKEN=លេខ_Token_ពី_BotFather
TEACHER_ADMIN_ID=លេខ_ID_របស់លោកគ្រូ
```

### ជំហានទី៤៖ បើកដំណើរការ Bot
```bash
python bot.py
```
អ្នកនឹងឃើញ Log បញ្ជាក់ថាបូតបានភ្ជាប់ជាមួយ Database និងដំណើរការ Long-polling ជោគជ័យ!

---

## 🌐 ការដាក់ឱ្យដំណើរការ ២៤/៧ ដោយឥតគិតថ្លៃ (Free 24/7 Deployment)

### ជម្រើសទី១៖ ដាក់លើ [Render.com](https://render.com) (ងាយស្រួលបំផុត)
គម្រោងនេះមាន build-in `web_server.py` (Port 8080) រួចជាស្រេច ដូច្នេះលោកគ្រូអាចដាក់ជា **Web Service (Free Tier)** បានដោយរលូន៖

1. បង្កើតគណនីលើ [Render.com](https://render.com)
2. Push កូដគម្រោងនេះទៅកាន់ **GitHub Repository** របស់អ្នក
3. លើ Render Dashboard ចុច **New +** -> ជ្រើសរើស **Web Service**
4. ជ្រើសរើស GitHub Repository នៃ Telegram Bot របស់អ្នក
5. កំណត់ការ Settings៖
   - **Name:** `math-telegram-bot`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bot.py`
   - **Instance Type:** `Free`
6. ចុចលើ **Advanced** -> **Add Environment Variable**៖
   - `BOT_TOKEN` = `លេខ_Token_របស់អ្នក`
   - `TEACHER_ADMIN_ID` = `លេខ_Telegram_ID_របស់អ្នក`
   - `ENABLE_WEB_SERVER` = `true`
   - `PORT` = `8080`
7. ចុច **Create Web Service**! បូតនឹងដំណើរការ ២៤/៧។

---

### ជម្រើសទី២៖ ដាក់លើ [Koyeb.com](https://koyeb.com) (100% Free Worker / Web)
1. បង្កើតគណនីលើ [Koyeb.com](https://koyeb.com)
2. ចុច **Create Service** -> ជ្រើសរើស **GitHub**
3. ជ្រើសរើស Repo គម្រោងរបស់អ្នក
4. Koyeb នឹង Detect រកឃើញ `Dockerfile` ឬ `Procfile` ដោយស្វ័យប្រវត្តិ
5. បន្ថែម Environment Variables:
   - `BOT_TOKEN`
   - `TEACHER_ADMIN_ID`
6. ចុច **Deploy**!

---

## 📊 របៀបភ្ជាប់ Google Sheets សម្រាប់បន្ថែមលំហាត់ងាយៗ

លោកគ្រូអាចបញ្ចូលលំហាត់ថ្មីៗតាមរយៈ Google Sheets ដោយមិនបាច់ចូលកែ Code ឡើយ៖

1. បង្កើត Google Sheet ថ្មីមួយ ដោយដាក់ឈ្មោះជួរឈរ (Columns) ដូចខាងក្រោម៖
   | code | category_id | title | problem | hints | solution_steps | final_answer | difficulty | keywords |
   | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
   | លំហាត់៩ | trig | ដេរីវេនៃ tan(2x) | គណនាដេរីវេ y = tan(2x) | ប្រើ (tan u)' = u'/cos²u | 1. u = 2x => u'=2 \|\| 2. y' = 2/cos²(2x) | y' = 2/cos²(2x) | មធ្យម | tan, tan(2x), លំហាត់៩ |

   *(ចំណាំ៖ ក្នុងជួរ `solution_steps` លោកគ្រូអាចខណ្ឌជំហាននីមួយៗដោយសញ្ញា `||`)*

2. ចូលទៅកាន់ម៉ឺនុយ **File** -> **Share** -> **Publish to web**
3. ត្រង់ Link ជ្រើសរើស **Entire Document** (ឬ Sheet1) ហើយប្ដូរពី Web page ទៅជា **Comma-separated values (.csv)**
4. ចុច **Publish** រួចចម្លងតំណភ្ជាប់ (URL) នោះ
5. ចូលទៅ Telegram ផ្ញើទៅកាន់បូតរបស់អ្នក៖
   ```text
   /sync_sheets https://docs.google.com/spreadsheets/d/e/.../pub?output=csv
   ```
6. បូតនឹងទាញយកលំហាត់ថ្មីៗទាំងអស់ចូល Database ភ្លាមៗ!

---

## 👨‍🏫 បញ្ជីពាក្យបញ្ជាសម្រាប់លោកគ្រូ (Admin Commands)

- `/admin` - បើក Dashboard គ្រប់គ្រង
- `/stats` - មើលចំនួនសិស្សដែលកំពុងប្រើ និងចំនួនដងនៃការស្វែងរក
- `/add` - បង្ហាញទម្រង់សម្រាប់បញ្ចូលលំហាត់ថ្មី
- `/delete <code_or_id>` - លុបលំហាត់ចេញពីប្រព័ន្ធ (ឧទាហរណ៍៖ `/delete លំហាត់៩`)
- `/broadcast <សារ>` - ផ្ញើសារប្រកាសទៅកាន់សិស្សទាំងអស់ដែលធ្លាប់ Start បូត
- `/backup` - ទាញយក File JSON រក្សាទុកទិន្នន័យទាំងអស់
- `/sync_sheets` - Sync ទិន្នន័យពី Google Sheets

---

## 👨‍💻 អ្នកអភិវឌ្ឍន៍ & អាជ្ញាប័ណ្ណ (License)
គម្រោងនេះត្រូវបានបង្កើតឡើងសម្រាប់ជាជំនួយដល់ការអប់រំគណិតវិទ្យានៅកម្ពុជា។ អាចយកទៅប្រើប្រាស់ កែច្នៃ និងចែករំលែកដោយសេរី (MIT License)។
