# ENGINE_BRIEF — binding rules for one engine run
From INSTRUCTIONS.md [I§.n], PROPOSAL_SOP.md [SOP step], tools/PROPOSAL_PROMPT.md. The source wins on conflict.

## 1. Sources and text [I1]
- [I1.1] Nothing of your own: no information, meaning, opinion or conclusion. GR/rule/circular/judgment text is
  copied verbatim — no change, abridging or cutting.
- [I1.2] Every extract carries its source: GR/rule no. + date, page no., para (rule/sub-rule) no.; judgment: court,
  case no., date, para.
- [I1.3] Only official Govt of India / Maharashtra GRs, rules, court orders; no third-party sources (confidential).
- [I1.4] Not readable / not available -> write "वाचन अपूर्ण / उपलब्ध नाही"; never guess.
- [I3] All government text in Devanagari Marathi (only an affidavit / parawise reply in English). Fewest words.
- [I5] Precedent library first for the same subject: quote earlier Finance/GAD opinions with ref no./date verbatim;
  never decide "take opinion again / not" yourself; old-case names/diagnoses -> "____".

## 2. Order of work [SOP1–SOP7]
1. [SOP1] Read every proposal page as an image. Stamps, inward nos., handwritten remarks, dates, amounts: read twice;
   unclear = "अस्पष्ट". निर्देशपत्र (p.1): C R no., file no. (e.g. संकीर्ण-2026/979/प्र.क्र.130/का.6), subject.
   "पृथक पत्र" = a proposal page. Facts: sender, channel (High Court or direct), letter nos./dates
   with page nos., demand, employee/post/dates/amounts, enclosures, earlier file of this Section.
2. [SOP2] List every GR/rule/circular/order cited + those needed to decide. Search pdf/, pdf/gr/INDEX.tsv,
   register/ (00-INDEX.md) [I1.5], service-rules/, precedent-library/ (00-INDEX first), old-case index (earlier
   Finance/GAD opinion, earlier file of the same employee). Read the GR page before quoting; quote verbatim with no., date,
   page, para. Court orders: api.sci.gov.in, bombayhighcourt.nic.in only.
3. [I4.14] GR missing -> fetch it yourself, without asking: lines `code <सांकेतांक>` / `search <from> <to> <words>` /
   `dept …` in tools/gr-request.txt, then `python3 tools/gr_request.py` (official URL
   gr.maharashtra.gov.in/Site/Upload/Government%20Resolutions/Marathi/<code>.pdf; archive.org collection
   maharashtragr; last 2 code digits = dept: 05 Finance, 12 L&J). Only the GRs needed; add them to the package.
   Only if still not found: "उपलब्ध नाही — मागवावे" (+ ask its सांकेतांक in ONE line).
4. [SOP3][I4.9][I4.15] Letter ONLY if information ESSENTIAL to decide/approve is missing; ask only that, as an
   empty table; nothing supplementary or "nice to have"; never what Govt/this dept already has (own GRs, official
   orders). Addressee as the proposal came: via HC "प्रबंधक …, उच्च न्यायालय (अपील शाखा), मुंबई", else the
   District Judge. Information letter first; Finance/GAD file later. No letter -> note onward for approval:
   Finance ("वित्त विभागाच्या मान्यतेस्तव", add अ.मु.स. (वित्त); model CR66 sample), or GAD (सा.प्र.वि.), or a
   reply on an existing opinion.
5. [SOP4] Note + letter spec (copy the nearest samples/specs/*.json) -> lint -> build. [SOP5] package PDF.
   [SOP6] Study. [SOP7] verify (section 6).
6. [I8] Medical reimbursement -> medical-bill/: 00-INDEX.docx first; Medical-Bill-Samples.docx same-type sample,
   wording unchanged, fill only "____"; deficiency -> Format-1 (note + information letter); outside rules /
   delayed / out-of-state -> Format-2 (सा.आ.वि. "एक विशेष बाब"; अ.मु.स. (वित्त) only when going to Finance/PHD);
   never the sample's name/hospital/diagnosis; drop non-applicable paras, renumber; GR quotes from old files =
   marked not verified with the original GR.

## 3. Note (टिप्पणी) [SOP4]
- [I4.3] Desk sample format (note of C R 66-2025, letter with letterhead logo); ready-made; only the proposal's
  facts and the precedents' language; no extra information.
- Para 1: "<authority> यांच्या पृ.__/प.वि. वरील दि. __ रोजीच्या पत्रास अनुसरून सादर." (or "…पत्रासोबत प्राप्त …
  पत्रास अनुसरून सादर."). Short numbered paras. Facts/posts/periods/amounts in TABLES:
  `{"table": [[...],[...]], "bold_last": true}` in note.paras. GR text verbatim in “ ” + "(पृ.N/प.वि.)". Earlier
  record of the same matter = a fact with its reference.
- Page refs: only "पृ.N/प.वि.", N = page of the returned PDF (proposal 1..n, then GR pages; from <pdf>.map.json).
  Never "पॅकेज PDF" in the note body or the letter. No repo paths, no internal ids (z6_0235 …).
- Banned (closed list, = tools/lint_spec.py BANNED): "दिसून येते", "असे दिसते", "पडताळणी केली असता",
  "माझ्या मते", "मला वाटते", "असे वाटते", "ठरवावे", "कदाचित", "बहुधा"; also no commentary, theory,
  arithmetic explanation or advice.
- Missing info para: "प्रस्तावासोबत खालील माहिती उपलब्ध नाही:- (1)…; (2)…".
- Last para, exactly one of:
  (a) "सबब, उपरोक्त माहिती तक्त्याच्या स्वरूपात … कळविण्याबाबतच्या पत्राचे प्रारूप पृ.      /प.वि. वर मान्यतेस्तव
  सादर. मान्य झाल्यास पत्र निर्गमित करण्यात येईल."
  (b) "सबब, … प्रस्ताव वित्त विभागाच्या मान्यतेस्तव सादर करण्यात येत आहे."
  (c) order draft only: section 4b.
- [I4.6] note.signers in order, all LEFT, normal page (no mirror): का. अ. (श्रीम. कऱ्हाडे) / अ.स. (श्री. वडनेरकर)
  / उ.वि.स. नि. उ.स. (श्री. बोंद्रे) / प्र.स. व वि.प. (श्री. खटी); then "अ.मु.स. (वित्त)" ONLY when the file goes
  to Finance (last para (b)); otherwise never.
- [I4.4] `related` = "संबंधित माहिती (संदर्भासाठी)" at the note's end: verbatim GR/rule/precedent extracts with
  source; each ends with exactly "(पॅकेज PDF पृ. N)" ("(पॅकेज PDF पृ. N-M)" / "(पॅकेज PDF पृ. N,M)"), or
  "(पॅकेज PDF मध्ये नाही)" when not in the package [I4.11]. No repo paths, internal ids or old-case names.

- [I4.18] Language: short sentences, one point each, clear subject ("<authority> यांनी … सादर केला आहे."); "श्रीमती" not "सौ."; one space after "श्री."/"श्रीमती"; name as in the proposal (Marathi initials e.g. "ह. ना. आपटे" if the proposal has them, else as written); missing-information list as a table; letter: no "तात्काळ", request "…उपलब्ध करून देण्यात यावी, ही विनंती." Quotes stay verbatim. Model: samples/specs/CR131_2026_special-pay_info-letter.json.

- [I4.19] Marathi forms (GR कपासू-2020/प्र.क्र.56/भाषा-2, दि. 10.11.2022), outside quotes: "दि. 17.09.2026", "क्र. 108", running "प्र. क्र."; ":-" not ".:-"; "करून", "प्रारूप". Exempt: quotes/extracts, पृ.N/प.वि., file nos. and tokens with '/' or '-', signers, dates, GR codes.

## 4. Letter [SOP4][I4.5][I4.10]
- ref_no "संकिर्ण-2026/<file no>/प्र.क्र.<n>/का.6"; date "__.__.2026"; to; subject; refs ("आपले पत्र क्र. …, दि. …").
- intro: "उपरोक्त विषयाबाबत संदर्भाधीन पत्रास अनुसरून आपणांस कळविण्यात येते की, सदर प्रकरणी पुढील कार्यवाहीसाठी
  खालील माहिती … उपलब्ध करून देण्यात यावी, ही विनंती:-"; points = empty table or a few short points (essential only,
  official language of earlier files, tables where needed [I4.15]).
- [I4.20] Letter table = data to fill in only (dates, figures, periods, yes/no, numbers). Documents (प्रत /
  प्रमाणपत्र / अहवाल) after the table: point "	तसेच, खालील कागदपत्रे उपलब्ध करून देण्यात यावीत, ही विनंती:-", then "1)	…" items; split mixed rows. Model: CR131.
- [I4.21] Reminder: `letter.reminder: N` (refs/intro: lint msg). [I4.22] To the HC with info from a District Judge →
  `letter.copies` (lint msg). [I4.23] "मा." before उच्च न्यायालय / न्यायमूर्ती / प्रशासकीय न्यायाधीश in own text (not
  letter.to, "उच्च न्यायालय (… शाखा)", quotes). [I4.24] "शुद्धिपत्रक". Models: CR122, CR130.
- The tool adds, never hand-write: विषय and संदर्भ bold + centre [I4.10]; "आपला," (never "आपली"), then
  "( राजेश वडनेरकर )" / "अवर सचिव ,महाराष्ट्र शासन", then "प्रत : निवड नस्ती"; letterhead
  "दूरध्वनी क्र. :- ०२२-२२793230   Email ID :- lnjd.desk6-mh@mah.gov.in" [I4.5].

## Marathi language rules [I4.25]
Own text of note/letter only; “…” quotes and `related` extracts stay verbatim, never "corrected" [I1.1].
Sources: GR22 = मराठी भाषा विभाग GR कपासू-2020/प्र.क्र.56/भाषा-2, दि. 10.11.2022; C18 = परिपत्रक
मभावा-2018/प्र.क्र.47/भाषा-2, दि. 07.05.2018; R = शासनमान्य शुद्धलेखन नियम (text: GADT परिशिष्ट 1 = नियम 1–14;
15–18: docs/STYLE_RESEARCH_LANG.md §5.2); GADT = सा.प्र.वि. "टिप्पणी लेखन व पत्रव्यवहार" (book p.); GADM =
कार्यालयीन कार्यपद्धती नियमपुस्तिका (मराठी) परि.; RP = राजभाषा परिचय, भाषा संचालनालय 1988 (book p.).
- Anusvara: R1–2 only where pronounced [GADT p.54]; R3 plural oblique and respectful plural:
  "आपणांस", "यांना", "यांचे" (not "आपणास") [GADT p.55]; R4 none otherwise.
- ऱ्हस्व-दीर्घ: R5 "पद्धती", "बुद्धी"; compound first member short: "मंत्रिमंडळ" [GADT p.55–56, 65]; R7 "न्यायाधीश",
  "अधीक्षक", "परीक्षा", "निरीक्षक" [GADT p.56, 64–65]; R8 verb -ऊन: "करून", "अनुसरून"; "प्रारूप", "स्वरूप"
  [R8, §5.2].
- R10 "कोणता", "एखादा"; R12 "करण्यासाठी", "करण्याबाबत" (not "करणेसाठी/करणेबाबत") [GADT p.58]; R14 "कदाचित";
  abbreviations without halant: "एम.ए.", "पीएच.डी." [R14, §5.2]; R16 "राहणे", "पाहणे"; R17 "इत्यादी" [§5.2].
- Common errors [GADT p.63–65]: "वरिष्ठ", "कनिष्ठ", "जादा" (not "ज्यादा"), "तात्कालिक", "उद्धृत", "कलम 3 अनुसार".
- Conjuncts [GR22 परिशिष्ट दोन p.17–18]: "द्ध" never "ध्द" ("पद्धत", "शुद्धिपत्रक"); "द्य"; "कऱ्हाडे".
- Punctuation [GR22 परिशिष्ट तीन p.20–21]: space after an abbreviation dot (अ.क्र. 23): "दि. 17.09.2026", "क्र. 108"; no space around "-"
  (अ.क्र. 7) or in file nos.; ":-" never ".:-". GR अ.क्र. 6 puts a space before ":"; the approved form "उपलब्ध नाही:-"
  [I4.19] stays until Abhi decides. Exemptions: [I4.19].
- Words [C18 p.3 सूचना 4–5, प्रपत्र 1 p.7]: Marathi initials ("ह. ना. आपटे", not "एच. एन. आपटे") and designations;
  कोश terms, not English words; "Act" = "अधिनियम", "Rules" = "नियम", "Regulations" = "विनियम" [GADT p.61]; no literal
  English idioms ("In this connection it may be stated that") [GADT 3.5(3) p.7, 4.13(13) p.11].
- Grammar: one प्रयोग per sentence: "<authority> यांनी … सादर केला आहे." or "… सादर करण्यात आला आहे.", never
  "शासनाने … मान्यता देण्यात आली" [GADT p.58, 60–61; RP p.190–192]. Passive/विध्यर्थ verb agrees with the object:
  "माहिती … देण्यात यावी", "कागदपत्रे … यावीत"; several objects -> the last [GADT p.61; RP p.176–177].
- Noting [GADT 4.14 p.12–13; GADM 26(4) p.11]: paper and its reference -> issue -> rule/GR and earlier decisions ->
  financial burden -> missing information -> proposal. Numbered short paras, one point each; simple sentences, one
  idea each; no "या संबंधात", "असे म्हणता येईल की", "हे नमूद करता येईल की" [GADM 26(7)–(8) p.11]. Suggest, never
  opine [GADM 26(5)]; no ornate/vague words [GADT 4.16(2) p.13]; big figures in tables [GADT 4.13(14) p.12].
- Drafting: clear, brief, no repetition [GADM 51(1) p.21]; subject in every letter incl. reminders [GADM 53(3) p.22];
  information asked as numbered points / a form [GADT 11.1(12) p.28]. Persons and officers in respectful plural:
  "यांनी", "त्यांचे", never "त्याने/तिचे" [R3].
- Checks: tools/lint_spec.py, tools/verify_outputs.py.

## 4b. Court cases and order drafts [SOP4b] (docs/COURT_AND_ORDERS_RESEARCH.md B7–B10; ENGINE_PROMPT section)
- Court matter (GP/AGP/HC/MAT notice: रिट याचिका, मूळ अर्ज/O.A., अवमान याचिका, SLP): note para 1 "<सहायक सरकारी वकील,
  …> यांच्या पृ.N/प.वि. वरील दि. __ रोजीच्या पत्रास अनुसरून सादर.", "पार्श्वभूमी थोडक्यात खालीलप्रमाणे आहे:-" + numbered
  facts (B9). Facts suffice -> spec `parawise` (English; Rule 58(3) every point; Rule 58(4) Note (ii) elaborate facts with
  rule/GR refs, never "denied"/"not admitted" alone, documents enclosed; recommendation oppose / not oppose) + letter to
  the GP/AGP forwarding it. Essential facts missing -> info-letter first [I4.15], no `parawise`. Rule 58(4): to the GP
  within two weeks / before the notice date — hearing date in Study part 0. Signers [I4.6] (B10).
- Order draft: spec `order` (gr / corrigendum / circular / memo / notification) ONLY when the record shows the decision
  or concurrence in hand, or the instruction asks (B7). Last para (c): "सबब, … शासन निर्णयाचे (ज्ञापनाचे /
  शुद्धिपत्रकाचे / परिपत्रकाचे / अधिसूचनेचे) प्रारूप पृ.      /प.वि. वर मान्यतेस्तव सादर." (notification: "अधिसूचनेची मराठी व इंग्रजी
  प्रारूपे पृ. …")
- Missing petition no./date/संकेतांक etc. -> "____" + `warnings`; never stop. Build: tools/build_parawise.py,
  tools/build_order.py (lint_spec.py lints both keys). status.json `outputs_extra`.

## 5. Outputs and tools
- [I4.12] Three files: <PREFIX>_Study.docx, <PREFIX>_Note_and_Letter.docx (letter if needed), package PDF;
  optional <PREFIX>_Parawise.docx / <PREFIX>_Order_Draft.docx (section 4b).
- [I4.1] One Word file: note, then the letter on a new page with letterhead:
  `python3 tools/build_note_letter.py spec.json OUTDIR PREFIX` (look at its PDF preview).
- [I4.2] Font DVOT-SurekhMR in every Word file (ascii/hAnsi/cs/eastAsia); builders set it, never override.
- [I4.7][I4.11][SOP5] Package: `python3 tools/pkg3.py <proposal.pdf> enclosures.json "OUTDIR/<original name>"`:
  proposal scan first (untouched), then ONLY the relevant original GR/rule/order pages (page 1 with no./date + the
  quoted paras' pages); no separator/title/index pages; "पृ. N / एकूण" stamps; bookmarks; YELLOW highlight on
  quoted lines only (marks = exact text-layer lines unique on the page). Scanned/legacy-font/repeated text:
  `python3 tools/highlight.py <pdf> marks.json` (lines / ocr / rect). Render GR pages to PNG and look.
- [I4.13] Nothing on your own initiative: no box/frame/extra marking; nothing on proposal pages.
- [I4.16] Package file name = the original proposal file name; strip only a random upload prefix (e.g.
  `11ae057d-`); never `<PREFIX>_Proposal_with_GRs.pdf`.
- [I4.8][I4.17][SOP6] Study: `python3 tools/build_study.py study.json OUTDIR/<PREFIX>_Study.docx`; read scanned
  pages as images. Headings exactly, in order (भाग 1 on: each on a new page):
  - "भाग 0 — वरिष्ठांसाठी ब्रीफिंग" (1–2 pages, bullets only): (अ) proposal in one line — who, what, from whom;
    (आ) key-facts table (dates, period, amount, posts); (इ) provision/GR — no., date, exact condition in one line,
    पृ./प.वि.; (ई) each approval condition पूर्ण / अपूर्ण / माहिती नाही (facts only); (उ) competent authority
    (dept / Finance / GAD / cabinet) + basis; (ऊ) financial burden; (ए) earlier similar case / Finance-GAD
    opinion; (ऐ) proposed action + essential points asked; (ओ) likely seniors' questions with answers from
    provisions/facts. Optional simple chart here only; note/letter use tables.
  - "भाग 1 — प्रस्तावाचे मराठी रूपांतर (जसेच्या तसे)": page-wise, verbatim; English translated (names/laws/GR nos.
    in brackets); "[हस्तलिखित शेरा: …]", "[शिक्का: …]", "[अस्पष्ट]".
  - "भाग 2 — प्रस्तावाचा गोषवारा": from/to/letter no.+date; demand in one para; employee/posts/amounts/dates table;
    documents attached and NOT attached/incomplete (page refs).
  - "भाग 3 — लागू तरतुदी (जसाच्या तसा उतारा + स्रोत)": extract, source (no., date, page, para), repo path,
    status (मूळ वाचले / सारांशावरून / not verified), "(पॅकेज PDF पृ. N)"; missing -> "उपलब्ध नाही — मागवावे".
  - "भाग 4 — शंका / माहिती-मागणी": numbered, each with reason + page ref; only what is really needed.
  - "भाग 5 — टिप्पणी (नोंद) मसुदा" (= the note), "भाग 6 — पत्र मसुदा(दे)" (= the letter; blank no./date),
    "भाग 7 — पडताळणी-नोंद": what was read from images, numbers/dates checked twice, unclear items, provisions
    not found.

## 6. Checks [SOP4][SOP7]
- Before every build: `python3 tools/lint_spec.py spec.json --study study.json --pages <package pages>` until
  "LINT OK".
- `python3 tools/verify_outputs.py OUTDIR PREFIX "OUTDIR/<original name>" <proposal pages> --original-name "<name>"`
  must print ALL OK (fonts, ids/paths, page-ref ranges, signer chain, letter, Study headings, name, stamps,
  bookmarks, annotations).
- Then re-read every number and date against its page image.

On any doubt, read the full source file named in the tag.
