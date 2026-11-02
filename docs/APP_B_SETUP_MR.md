# प्रस्ताव कक्ष (App B) — सेटअप मार्गदर्शक (एक पान)

कोडमध्ये कोणतीही key नाही. सर्व keys ॲपच्या **Settings** स्क्रीनवर भरायच्या (Cloudflare KV `SETTINGS` मध्ये साठतात). GitHub repo secrets **लागत नाहीत**. github.com कार्यालयात बंद असल्याने (आ) व (इ) घरून/फोनवरून एकदाच करा.

## (अ) Supabase प्रकल्प
1. supabase.com → New project. Region: Mumbai नसल्यास जवळचा — सध्याचा प्रकल्प `vxkktnymewcvcqysilgx` **Tokyo (ap-northeast-1)** मध्ये (तयार करताना Mumbai उपलब्ध नव्हता). Project ref (URL मधील `abcd...`) नोंदवा.
2. Schema + seed — दोनपैकी एक:
   - **SQL Editor:** `supabase/migrations/20261101000001_init.sql`, `20261101000002_backup.sql`, `20261101000003_optional_case_fields.sql` (C R क्र./वर्ष/विषय ऐच्छिक), `20261101000004_reliability.sql` (प्रत्येक run चा खर्च/turns, थेट insert बंद), नंतर `supabase/seed.sql` — क्रमाने पेस्ट करून Run. (सध्याच्या प्रकल्पात 0001–0004 लावलेले आहेत; नवीन migration आल्यास फक्त तीच Run करा.)
   - **CLI:** `supabase/config.toml` मध्ये `PASTE_SUPABASE_PROJECT_REF` जागी ref; मग `npx supabase login` → `npx supabase link --project-ref <ref>` → `npx supabase db push --include-seed`.
3. Database → Extensions → **pg_cron** चालू आहे का पाहा (backup migration ते चालू करते).
4. Authentication → Sign In / Providers → **Email** चालू. Email Templates → Magic Link मध्ये `{{ .Token }}` (6 अंकी OTP) असावा. (02.11.2026: Supabase मध्ये नमुना बदलण्यासाठी आधी custom SMTP लागतो — Gmail: myaccount.google.com → Security → 2-Step Verification → App passwords; Supabase → Authentication → Emails → Set up SMTP: Host `smtp.gmail.com`, Port `465`, Username = Gmail पत्ता, Password = App password, Sender name `प्रस्ताव कक्ष`.)
5. Authentication → URL Configuration → **Site URL** = Worker ची `https://prastav-kaksha.<नाव>.workers.dev` लिंक (इ-४ नंतर भरा); तीच Redirect URLs मध्ये.
6. Project Settings → API: **Project URL**, **anon key**, **service_role key** नोंदवा (फक्त ई-३ मध्ये भरण्यासाठी).

## (आ) GitHub token (घरून, एकदाच)
1. github.com → Settings → Developer settings → Fine-grained tokens → Generate.
2. Repository access: **Only select repositories** → `abhishekwasu-hue/law-judiciary-service-rules`.
3. Permissions: **Actions: Read and write**, **Contents: Read and write**, **Metadata: Read-only**. मुदत: 1 वर्ष.
4. Repo **private** च ठेवा (Settings → General → Danger Zone मध्ये तपासा).

## (इ) Cloudflare deploy (घरून, Node.js 20+, wrangler 4)
- PowerShell मध्ये `npx` "running scripts is disabled" अशी चूक देत असल्यास `npx.cmd` वापरा (उदा. `npx.cmd wrangler login`, `npx.cmd wrangler deploy`).
- सध्याचे ॲप: https://prastav-kaksha.abhi-desk.workers.dev
1. `npx wrangler login` (ब्राउझरमध्ये Allow).
2. `cd cloudflare` → `npx wrangler kv namespace create SETTINGS` → छापलेला `id` `cloudflare/wrangler.toml` मधील `PASTE_KV_NAMESPACE_ID` जागी पेस्ट.
3. रेपोच्या मुख्य फोल्डरमधून: `powershell -ExecutionPolicy Bypass -File scripts\deploy.ps1`
   (हेच हाताने: `cd dashboard-app` → `npm ci` → `npm run build` → `cd ..\cloudflare` → `npx wrangler deploy`).
4. शेवटी छापलेली `https://...workers.dev` लिंक = ॲपचा पत्ता (अ-५ मध्ये भरा).

## (ई) पहिली सुरुवात (कार्यालयातूनही चालेल)
1. लिंक उघडा → "प्रारंभिक सेटअप" स्क्रीन दिसते (यामुळे KV मध्ये setup code तयार होतो).
2. Cloudflare dashboard → Storage & Databases → **Workers KV** → `SETTINGS` → key `setup_code` → value कॉपी.
3. सेटअप फॉर्म: setup code + Supabase URL + anon key + service_role key + तुमचा email → जतन. (नंतर setup बंद होतो.)
4. Email वरील OTP ने लॉगिन (हा email = owner).
5. **Settings:** GitHub repo `abhishekwasu-hue/law-judiciary-service-rules`, branch `main`, GitHub token (आ), Anthropic API key, model (मुख्य मॉडेल — नोंद/पत्र/GR; रिकामे = claude-opus-5-5) → जतन. Keys पुन्हा दिसत नाहीत — फक्त "set" व शेवटचे 4 अक्षर.
   - **स्वस्त मॉडेल (model_light):** पाने वाचणे, भाग 1 व यांत्रिक कामासाठी; रिकामे = claude-haiku-5-5.
   - **कमाल खर्च ($) (budget_usd):** 0 पेक्षा जास्त, कमाल 20; रिकामे = 0.75 (सध्या 1.5). ही मर्यादा फक्त इशारा देते ("खर्च-मर्यादा ओलांडली — दर्जा राखण्यासाठी"); run थांबत नाही, दर्जा कमी होत नाही.

## (उ) चाचणी
1. "नवीन प्रस्ताव" → नमुना PDF अपलोड (कमाल 50 MB; फाइलनाव बदलत नाही).
2. Run → स्थिती थेट बदलते: queued → running (पायरी दिसते) → done.
3. तीन फाइल डाउनलोड: `<PREFIX>_Study.docx`, `<PREFIX>_Note_and_Letter.docx`, मूळ नावाची GR सह PDF.

## (ऊ) दैनिक backup
- रोज 02:00 IST (20:30 UTC) pg_cron सर्व तक्त्यांच्या (cases, case_files, runs, letters, activity, members, gr_library) ओळी JSON मध्ये `backups` तक्त्यात ठेवते; शेवटचे 30 राहतात. फाइल्स (Storage) यात नाहीत.
- तपासा: SQL Editor → `select id, taken_at from backups order by taken_at desc;` • लगेच घ्या: `select take_backup();`
- Job दिसतो: `select * from cron.job;` • ब्राउझरला backups दिसत नाहीत (RLS).

## (ए) अडचणी
| लक्षण | उपाय |
|---|---|
| deploy.ps1: "KV id अजून भरलेला नाही" | इ-२ करा; `wrangler.toml` मध्ये id पेस्ट करा. |
| सेटअप: "setup code wrong" | KV मधील `setup_code` पुन्हा कॉपी करा (जागा/ओळ नको); लिंक एकदा उघडल्यावरच code तयार होतो. |
| OTP email येत नाही / लिंकवर परत जात नाही | Spam पाहा; अ-४ Email चालू व `{{ .Token }}`; अ-५ Site URL = workers.dev लिंक. |
| Run "failed" / queued मध्येच | Settings मधील GitHub token (आ-३ परवानग्या, मुदत) व Anthropic key तपासा; GitHub → Actions → "Process proposal" लॉग (घरून). |
| लॉगिन झाले पण यादी रिकामी / "not a member" | Owner email (ई-3) व लॉगिन email एकच हवा; सहकाऱ्यांना Settings → सदस्य मधून आमंत्रण द्या. |
