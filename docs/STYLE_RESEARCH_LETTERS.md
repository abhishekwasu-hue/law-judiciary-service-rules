# STYLE_RESEARCH_LETTERS.md — शासकीय पत्राचे स्वरूप व आदरार्थी भाषा (संशोधन, 01.11.2026)

Scope: only the **letter (पत्र)**: its structure, salutation, request formulas, reminders, and how to address the High Court
registry and Principal District Judges. GAD noting structure and general Marathi usage are covered by the other two research
files. This file changes no rule. Every proposed change below waits for Abhi's decision (OWNER_RULES A.5). The Section's own
format (§4.5, `tools/mkdocs.py`, template z7_0273) wins over any outside source unless Abhi decides otherwise.

## 1. Sources

| # | Source | Where (verifiable) | Status |
|---|---|---|---|
| S1 | GAD, *Maharashtra Manual of Office Procedures, 2023* (English) | GAD site: https://cdnbbsr.s3waas.gov.in/s398e6f17209029f4ae6dc9d88ec8eac2c/uploads/2023/06/2023060954.pdf; repo copy: `pdf/08-gad-office-procedure/GAD_Maharashtra-Office-Procedure-Manual-2023-English.pdf`. Cited: Ch.10 §10.1(1), (7) (PDF p.62, 64); Appendix 10.1, 10.3, 10.9 (PDF p.68, 70, 76); Ch.11 §11.2(1), §11.4(3), (6), (8), §11.6 (PDF p.79–81); §12.1(3), Ch.13 "await" (PDF p.82, 86); §21.14 (PDF p.120) | Official (GAD) |
| S2 | GAD, *टिप्पणी लेखन व पत्रव्यवहार* (Book of Noting and Drafting in Mantralaya, Marathi). Preface signed by the Chief Secretary; its specimen letter is dated January 1989 | GAD site: https://cdnbbsr.s3waas.gov.in/s398e6f17209029f4ae6dc9d88ec8eac2c/uploads/2023/06/2023060442.pdf; repo copy: `pdf/08-gad-office-procedure/GAD_Tippani-Lekhan-va-Patravyavahar-Marathi.pdf`. It uses a legacy font, so it was read from page images: book p.N = PDF p.N+4. Cited: प्रकरण 11 परि. 11.1 (book p.27), 11.1(12) and 11.2–11.4 (p.28), 11.6(1)–(8) (p.29); प्रकरण 12 परि. 12.3 (p.30) and the specimen letter (p.31) | Official (GAD); older edition |
| S3 | Vikaspedia (C-DAC/MeitY portal), "मसुदालेखन व टिप्पणी" — शासकीय पत्रलेखन-प्रकार | https://education.vikaspedia.in/viewcontent/education/93893e93993f92494d92f93e93593f93792f940-93893094d93591593e939940/93893e93993f92494d92f93e91a947-92a94d93091593e930/92e93894192693e932947916928-935-91f93f92a94d92a923940?lgn=mr | Secondary (Government of India portal, not a Maharashtra rule). It only confirms S1/S2 |
| S4 | The Section's own earlier letters (repo zips `सन … प्रकरणे.zip`, 90 letters with "महोदय"). Reminders: C R 170-2024 (स्मरणपत्र-1), C R 309-2024 (स्मरणपत्र), C R 28-2025 (स्मरणपत्र-1), C R 34-2026 (स्मरणपत्र: १, signed by the अवर सचिव) | `python tools/oldcases_text.py <dir>`; counts below were made with a script over `<dir>/t/*.txt` | Section practice. Use the language only; never names or ids in a note |
| — | Web search for a GAD/Marathi Bhasha circular on the honorific "मा.", on "महोदया", or on a Marathi reminder form | Several searches (marathi.gov.in, gr.maharashtra.gov.in, Yashada): **no such circular found** | Points that rest only on S4 are marked "प्रचलित पद्धत (स्रोत नाही)" |

Yashada: the CPTP SO syllabus (https://www.yashada.org/cptp/PDF/home_page_links/cptp_so_semII.pdf) lists "Book of Drafting and
Noting in Mantralaya" as a training subject. That book is S2. Yashada has no separate letter specimen online.

## 2. What the sources say (verbatim or close; with location)

1. **Parts of a letter** — S2 11.6 (p.29):
   - (2) क्रमांक व दिनांक;
   - (3) the addressee's name or designation, with the full address;
   - (4) “पत्राचा विषय व संदर्भ—हे दोन्ही स्वतंत्रपणे पत्रातील मजकुराबाहेर लिहिल्यास चटकन ध्यानात येतात”;
   - (5) “पत्राच्या सुरुवातीला अभिवादन "महोदय किंवा महोदया" असे लिहून व पत्राच्या शेवटी "आपला विश्वासू" असे लिहून नाव व पदनाम लिहून त्यावर सही करणे”;
   - (7) सही करून त्याखाली अधिकाऱ्याचे नाव व पदनाम;
   - (8) a priority heading if the letter is urgent, important or confidential.

   S1 §11.4(8): a letter to a government officer carries the **name and designation** of the sender.
2. **Points and table** — S2 11.1(12) (p.28): “माहिती किंवा जादा तपशील मागविणारे पत्र असेल तर ज्या मुद्यांवर माहिती पाहिजे ते मुद्दे अनुक्रमांक देऊन १,२,३,४ अशा पद्धतीने द्यावेत. शक्य तेथे प्रपत्र देऊन माहिती प्रपत्रात मागवावी”. S2 11.6(6): each point in a separate paragraph, and the end of the letter states exactly which information or decision is needed.
3. **Courtesy towards courts** — S2 12.3 (p.30): ordinary letters are used for “न्यायालये” and others, and “… न्यायालये, लोकायुक्त, लोकसेवा आयोग, वगैरेंशी पत्रव्यवहार करताना विशेष सौजन्यपूर्वक भाषा वापरणे जरूर आहे”. S1 §10.1(1): letters “to the High Court” use the ordinary letter form (Appendix 10.1: “Sir, … Yours faithfully, … Under Secretary to the Government of Maharashtra”).
4. **Language** — S2 11.1 (p.27):
   - A-B-C: अचूकपणा, संक्षिप्तपणा, स्पष्टपणा;
   - “वाक्ये लहान व साधी असावीत”;
   - “एका परिच्छेदात एकच मुद्दा”;
   - “पत्र स्वयंपूर्ण असावे”.

   S1 §11.2(1): avoid “lengthy sentences, abruptness, redundancy, circumlocution”.
5. **References** — S1 §11.4(3) (PDF p.80):
   - quote the number and date of the letter being answered, or of the last letter in the series;
   - when there are several references, list them separately;
   - “The subject should be mentioned invariably in all communications including reminders and demi official letters.”
6. **Reminders** — S1 §21.14 (PDF p.120): reminders on cases kept in "await" are issued "promptly on due dates". Ch.13 (PDF p.86): each case in await is marked with the date its reminder is due. S1 §10.1(7) and S3: a **demi-official letter** is used "when a series of official reminders fail to elicit the information called for". S1 §10.1(1): "routine communications and reminders may be signed by Under Secretaries".
7. **Section practice (S4; counts from 90 old letters)** — प्रचलित पद्धत:

   | Item | Count in old letters |
   |---|---|
   | Salutation "महोदय," | 174 |
   | Salutation "महोदया" | 0 |
   | Sign-off "आपला," (male signer) / "आपली," (female signer) | 55 / 110 |
   | Sign-off "आपला विश्वासू" | 0 |
   | Ending "…करुन देण्यात यावी, ही विनंती." | 22 |
   | Ending "…सादर करावा/करावी." (no "ही विनंती") | about 10 |
   | "तात्काळ" / "तातडीने" / "अतितात्काळ" | 11 / 1 / 1 |
   | "लवकरात लवकर" | 3 |

   High Court in the addressee block:
   - "उच्च न्यायालय (अपील शाखा)" (2026 letters) is the most common;
   - "मा.उच्च न्यायालय" appears in about 20 old addressee blocks;
   - in running text, "मा.उच्च न्यायालय" occurs 257 times and plain "उच्च न्यायालय" 438 times (mixed).

   Copy line: "प्रत : निवड नस्ती" appears 10 times. Copies to the प्रमुख जिल्हा व सत्र न्यायाधीश appear 15 or more times, e.g. "प्रत : प्रमुख जिल्हा व सत्र न्यायाधीश, … यांना आवश्यक कार्यवाहीसाठी" (C R 34-2026, an अवर सचिव letter) and "… यांना योग्य त्या कार्यवाहीस्तव".
8. **Section reminder wording (S4)** — reminder heading "स्मरणपत्र-1" placed above the क्रमांक line. Reference: "या कार्यासनाचे समक्रमांकाचे पत्र दि.__". Body examples:
   - "संदर्भाधीन पत्रान्वये … विचारणा करण्यात आलेली माहिती अद्याप अप्राप्त आहे. तरी, सदर माहिती लवकरात लवकर शासनास उपलब्ध करुन देण्यात यावी, ही विनंती." (C R 309-2024)
   - "तरी वरील विषयाबाबत सदर अभिप्राय कळविण्याची विनंती या स्मरणपत्राद्वारे करण्यात येत आहे." (C R 170-2024)

## 3. Comparison with the repo — findings

Repo state today:
- `tools/mkdocs.py` (lines 170–201) adds fixed text: "प्रति,", "विषय :-" and "संदर्भ :-" (bold, centred), "महोदय,", the intro, the points, "आपला,", "( राजेश वडनेरकर )" / "अवर सचिव ,महाराष्ट्र शासन", the optional `enclosure`, and "प्रत : निवड नस्ती".
- `tools/templates/LETTER_TEMPLATE.docx`: its text paragraphs are all "____" except the letterhead (महाराष्ट्र शासन / विधि व न्याय विभाग / address / दूरध्वनी). So the fixed wording lives only in mkdocs.py and INSTRUCTIONS §4.5.
- `tools/lint_spec.py` letter checks:
  - ref_no pattern;
  - to, subject and refs present;
  - intro starts with "उपरोक्त विषयाबाबत संदर्भाधीन";
  - intro contains "आपणांस कळविण्यात येते की,";
  - intro contains "ही विनंती";
  - intro ends with ":-";
  - "तात्काळ";
  - "सौ.";
  - "श्री." spacing.

| # | Finding | Before (sample) → After | Type | Conflicts with Section format? | Priority |
|---|---|---|---|---|---|
| F1 | The structure of samples CR122/128/130/131/133 matches S1/S2 in full: क्रमांक/दिनांक, प्रति, विषय and संदर्भ outside the body, "महोदय,", numbered points or a table (S2 11.1(12)), and name + designation under the signature (S1 §11.4(8)) | No change | — | No | — |
| F2 | The request formula in all 5 samples ("…शासनास उपलब्ध करुन देण्यात यावी/यावीत, ही विनंती.:-") is the Section's most frequent courteous form (S4) and fits S2 12.3 (special courtesy towards courts) | No change. Keep the lint check | — | No | — |
| F3 | **Bare imperative endings.** Old letters end "…शासनास सादर करावा." without "ही विनंती" about 10 times. Lint today checks "ही विनंती" in `intro` only, not in `points` or `closing`. No sample has a bare ending today | Lint: in letter text (quotes removed), flag `(करावी\|करावा\|करावे\|द्यावी\|द्यावा\|द्यावे\|पाठवावी\|पाठवावा\|पाठवावे\|कळवावे\|कळवावी)\s*[.।]` → "…करण्यात यावी, ही विनंती." (§4.18) | Lint | No | High |
| F4 | **Urgency words.** Lint bans only "तात्काळ". Old letters also use "तातडीने" and "अतितात्काळ". S2 12.3 calls for special courtesy | Extend `LETTER_STYLE_RULES` to `तात्काळ\|तातडीने\|अतितात्काळ\|त्वरित\|ताबडतोब\|अविलंब\|विनाविलंब\|सत्वर`. A polite alternative already used by the Section is "लवकरात लवकर" (C R 309-2024). No sample hits today | Lint | No | High |
| F5 | **"कै." spacing.** CR133 has "कै.मिलिंद रामचंद्र गवळे" (in the subject and table row 1). §4.18 requires a space after "श्री."/"श्रीमती" but does not cover "कै." | CR133: "कै.मिलिंद" → "कै. मिलिंद". Lint `कै\.(?=\S)` → "'कै.' नंतर जागा (§4.18)". INSTRUCTIONS §4.18: add "कै." to the spacing sentence | Rule (small addition) + sample + lint | No | Medium |
| F6 | **Reminders (स्मरणपत्र) are not supported.** mkdocs has no reminder heading, and lint has no reminder variant. S1 requires the subject in reminders and timely reminders on due dates. S4 has a settled Section form (heading "स्मरणपत्र-1" above the क्रमांक; reference "या कार्यासनाचे समक्रमांकाचे पत्र दि.__"; body "…माहिती अद्याप अप्राप्त आहे. तरी, सदर माहिती लवकरात लवकर शासनास उपलब्ध करुन देण्यात यावी, ही विनंती.") | Proposal: optional spec field `letter.reminder: N` → mkdocs prints "स्मरणपत्र-N" above the क्रमांक line. Lint for reminders: refs[0] contains "समक्रमांकाचे"; intro contains "अद्याप अप्राप्त" and "ही विनंती". Add a sample `samples/specs/<CR>_reminder.json` when the first real reminder is approved. After repeated reminders the next step is a D.O. letter (S1 §10.1(7)) — record that as a fact; do not decide it | Tool + lint + rule (new item) | Not in the template (the Section's old reminders show the heading) — **निर्णय हवा** | High (new feature) |
| F7 | **Copy to the प्रमुख जिल्हा व सत्र न्यायाधीश when a letter goes through the High Court.** CR122 and CR130 ask the HC to get information "प्रमुख जिल्हा व सत्र न्यायाधीश, … यांच्याकडून प्राप्त करुन". The Section's own letters then often add "प्रत : प्रमुख जिल्हा व सत्र न्यायाधीश, … यांना आवश्यक कार्यवाहीसाठी" (S4, incl. C R 34-2026). mkdocs and §4.5 allow only "प्रत : निवड नस्ती" | Proposal: optional `letter.copies: ["प्रमुख जिल्हा व सत्र न्यायाधीश, जिल्हा व सत्र न्यायालय, ठाणे यांना आवश्यक कार्यवाहीसाठी"]` printed above "निवड नस्ती" | Rule §4.5 + tool | **निर्णय हवा** (§4.5 states "प्रत : निवड नस्ती" only) | Medium |
| F8 | **Closing "आपला," vs GAD "आपला विश्वासू".** S2 11.6(5) prescribes "आपला विश्वासू" (S1 appendices: "Yours faithfully"). The Section's template, §4.5 and all 90 old letters use "आपला," / "आपली," (0 × "विश्वासू") | Keep "आपला," (Section format wins) | — | **निर्णय हवा** only if Abhi wants the GAD form; default: no change | Low |
| F9 | **"महोदय" vs "महोदया".** S2 11.6(5) gives "महोदय किंवा महोदया". The Section always writes "महोदय," because letters go to designations, not persons. mkdocs hard-codes "महोदय," | Keep. Optional future field `letter.salutation` only if Abhi wants "महोदया" for a named woman officer | — | **निर्णय हवा** (low) | Low |
| F10 | **"मा." for the High Court and judges.** There is no official circular (searches found none). Section practice (S4) is mixed: about 37% "मा.उच्च न्यायालय" in running text; "मा.मुख्य न्यायमूर्ती" / "मा.प्रशासकीय न्यायाधीश" are used consistently (CR128 point 5 already does this). In the addressee block, 2026 letters and all samples use plain "उच्च न्यायालय (अपील शाखा)". CR128 subject: "उच्च न्यायालय, मुंबई व खंडपीठ नागपूर, औरंगाबाद यांच्या आस्थापनेवरील…" | Proposal (prachalit): "मा." before मुख्य न्यायमूर्ती / न्यायमूर्ती / प्रशासकीय न्यायाधीश / प्रशासकीय न्यायाधीश समिती everywhere. Lint warning `(?<!मा\.)(?<!मा\. )(मुख्य न्यायमूर्ती\|न्यायमूर्ती\|प्रशासकीय न्यायाधीश)` (letter + note, outside quotes). For "मा.उच्च न्यायालय" in the subject/body: optional, no lint until Abhi decides. Addressee block: no change | Lint (judges) + rule | **निर्णय हवा** — prachalit only, स्रोत नाही. For the court name in the subject/body: Abhi to decide | Medium |
| F11 | **PDJ addressee block is inconsistent.** CR131: "प्रमुख जिल्हा व सत्र न्यायाधीश, / भंडारा." CR133: "… / जिल्हा न्यायालय, / लातूर." Section practice (S4): mostly "प्रमुख जिल्हा व सत्र न्यायाधीश, / जिल्हा व सत्र न्यायालय, / <जिल्हा>." | Samples: use the 3-line S4 form (e.g. CR133 "जिल्हा न्यायालय," → "जिल्हा व सत्र न्यायालय,"; CR131 add that line). If the proposal letterhead shows the court's own name, use that — prachalit | Sample | No (to-block is free text in the template) | Low |
| F12 | **Several references.** S1 §11.4(3) says to list them separately. S4 numbers them ("१.…", "२.…"). CR128 has one reference split over two lines ("आपली पत्रे क्र.… व" / "क्र.…, दि.21.10.2026"); since both letters share one date, this is acceptable | Rule text (optional): when references have different dates, number them "1) …", "2) …". Lint: if `len(refs)>1` and any two refs carry different "दि." values, require a leading "1)"/"2)" | Lint (optional) | No | Low |
| F13 | **Signatory in reminders.** S1 §10.1(1): "routine communications and reminders may be signed by Under Secretaries". The current fixed signatory (अवर सचिव) already fits | No change | — | No | — |

## 4. Lint candidates (exact patterns, for `tools/lint_spec.py`)

Apply to letter strings after `QUOTE_RE.sub` (quotes are exempt, as in §4.18). Message prefix "पत्राची भाषा —" or "आदरार्थी उल्लेख —".

| Id | Pattern | Message | Today's sample hits |
|---|---|---|---|
| L1 (F3) | `(करावी\|करावा\|करावे\|द्यावी\|द्यावा\|द्यावे\|पाठवावी\|पाठवावा\|पाठवावे\|कळवावे\|कळवावी)\s*[.।]` | आदेशात्मक शेवट — "…करण्यात यावी, ही विनंती." (§4.18) | 0 |
| L2 (F4) | `तात्काळ\|तातडीने\|अतितात्काळ\|त्वरित\|ताबडतोब\|अविलंब\|विनाविलंब\|सत्वर` (replaces the single "तात्काळ") | तातडीदर्शक शब्द नको; "लवकरात लवकर" | 0 |
| L3 (F5) | `कै\.(?=\S)` (letter + note) | 'कै.' नंतर जागा | CR133 subject, CR133 table row 1 |
| L4 (F10, after decision) | `(?<!मा\.)(?<!मा\. )(मुख्य न्यायमूर्ती\|न्यायमूर्ती\|प्रशासकीय न्यायाधीश)` | न्यायमूर्ती/प्रशासकीय न्यायाधीश यांच्यापूर्वी "मा." | 0 |
| L5 (F6, after decision) | if `letter.reminder`: refs[0] must match `समक्रमांकाचे`; intro must match `अद्याप\s+अप्राप्त` and `ही विनंती` | स्मरणपत्राची रचना | n/a |
| L6 (F12, optional) | `len(refs)>1` and different `दि\.\s*[0-9.]+` values → each ref starts `^[0-9१-९]+\)` | संदर्भ क्रमांकित करा | 0 |

The regexes were tested on all 5 sample letters. Only L3 hits (CR133). Running L4 on the addressee lines would hit "उच्च न्यायालय", which is why L4 covers only judges' titles and leaves out the court name.

## 5. Conflicts needing Abhi's decision (निर्णय हवा)

1. **F6 reminders** — add a "स्मरणपत्र-N" heading and reminder wording to mkdocs, lint and INSTRUCTIONS? (Default: yes, in the Section's own S4 form.)
2. **F7 copy line** — allow "प्रत : प्रमुख जिल्हा व सत्र न्यायाधीश, … यांना आवश्यक कार्यवाहीसाठी" above "निवड नस्ती" when a letter goes through the HC? (§4.5 now says "प्रत : निवड नस्ती" only. Default: no change until he decides.)
3. **F10 "मा."** — use "मा." before न्यायमूर्ती / प्रशासकीय न्यायाधीश always (lint L4)? Also "मा.उच्च न्यायालय" in the subject/body? (No official source; Section practice is mixed. Default: judges yes, court name unchanged.)
4. **F8 / F9** — GAD's "आपला विश्वासू" and "महोदया" vs the Section's "आपला," and "महोदय,". (Default: keep the Section form.)

## 6. Priority

1. High, no decision needed: L1, L2 (lint only; zero sample hits, so nothing breaks).
2. Medium: F5 (CR133 "कै. " fix + L3 + a one-word addition to §4.18); F11 sample addressee consistency.
3. After decision: F6 reminders (tool + lint + rule), F7 copies, F10 "मा." (L4).
4. Low / no change: F8, F9, F12.
