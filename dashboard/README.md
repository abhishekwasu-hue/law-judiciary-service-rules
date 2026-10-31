# प्रस्ताव डॅशबोर्ड — Cloudflare सेटअप (ऑफिस firewall साठी; ब्राउझर फक्त workers.dev शी बोलतो)
1. रेपो Settings → Secrets → Actions: `ANTHROPIC_API_KEY` जोडा (Actions मधील प्रक्रियेसाठी).
2. GitHub Fine-grained token (फक्त हा रेपो): Contents R/W, Metadata R.
3. Cloudflare → Workers & Pages → `cloudflare/` फोल्डरने deploy (`npx wrangler deploy` किंवा रेपो जोडून; root = cloudflare).
4. Worker Settings → Variables and Secrets: Secret `GH_TOKEN` (वरचा token), Secret `DASH_PASSWORD` (तुमचा पासवर्ड).
5. Worker ची URL उघडा → 🔑 पासवर्ड टाका.
प्रवाह: अपलोड → Worker → रेपोच्या `inbox/` मध्ये PDF → GitHub Actions `Process proposal` → `cases/<CR>/` मध्ये तीन फाइल + status.json → डॅशबोर्डवर डाउनलोड.
रेपो private ठेवा.
