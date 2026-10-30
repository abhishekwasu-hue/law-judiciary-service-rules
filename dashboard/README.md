# प्रस्ताव डॅशबोर्ड — सेटअप (एकदाच)
1. रेपो Settings → Secrets → Actions → `ANTHROPIC_API_KEY` जोडा.
2. Settings → Pages → Source: GitHub Actions. नंतर `dashboard/` बदल push होताच साइट प्रकाशित होते.
3. GitHub → Settings → Developer settings → Fine-grained token (फक्त हा रेपो): Contents R/W, Actions R/W, Metadata R. डॅशबोर्डच्या ⚙ सेटिंगमध्ये टाका.
4. वापर: अपलोड → inbox/ मध्ये PDF जाते → Actions `Process proposal` चालते (Claude Code, रेपोचे CLAUDE.md बंधनकारक) → cases/<CR>/ मध्ये तीन फाइल + status.json → डॅशबोर्डवर डाउनलोड.
गोपनीयता: रेपो private ठेवा; साइट स्वतः डेटा ठेवत नाही, Token शिवाय काहीही दिसत नाही.
