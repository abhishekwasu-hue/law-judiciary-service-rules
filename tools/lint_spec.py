#!/usr/bin/env python3
"""lint_spec.py <spec.json> [--study study.json] [--pages N] [--allow-missing-part1] [--details FILE]
Pre-build lint: checks spec.json (note/letter, format: tools/mkdocs.py docstring) and study.json (tools/build_study.py
docstring) against the rules that tools/verify_outputs.py checks on the built files (PROPOSAL_SOP.md Step 4,
INSTRUCTIONS.md §4), so problems are fixed before building. spec.json may be "-" to lint only --study.
Prints one line per problem "<JSON path>: <rule> — <detail>"; "LINT OK" and exit 0 when there is none, exit 1 otherwise.
Warnings (WARN level, below) are printed as "WARN <JSON path>: <message>" and never change the exit code.
Windows: `py tools/lint_spec.py ...`; runner: `python3 tools/lint_spec.py ...`.

Rules (spec.json)
  - no internal file ids (z<digit>_<4 digits>) and no repo paths (register/, service-rules/, precedent-library/, pdf/,
    repo, रेपो) in any note / related / letter text
  - no BANNED word in the note body (first, paras, sub, closing) or the letter
  - C27 (02.11.2026): no "पॅकेज" (anywhere, quotes too) and, outside “…” quotes, no warning / working word (DRAFT_WORDS:
    package PDF, इशारा, पडताळणी अपूर्ण, मागवावे, वाचन अपूर्ण, अस्पष्ट, पडताळलेले नाही, टीप :, warning, TODO; 03.11.2026:
    स्रोत, जसाच्या तसा, जसेच्या तसे, जशीच्या तशी) and no AI word
    (AI_WORDS: AI, Claude, Anthropic, मॉडेल, model, स्वयंचलित, automatic, engine, प्रणालीने तयार, generated, LLM, GPT,
    Gemini) and no typographic / working tell (TELL_WORDS: em dash "—", arrows "→", web addresses http/www except the
    official "www.maharashtra.gov.in" line, "छापील पृ.") in the note body, the letter and the related heading/source; the
    verbatim related "text" only for "पॅकेज PDF".
    Related source: ends with " (पृ.N/प.वि.)" (N, N-M, N,M; Devanagari digits) or has no page marker
    (related_source_problems). The Study keeps "(पॅकेज PDF पृ. N)".
  - पृ. references: same accepted forms as verify_outputs ("पृ.N/प.वि.", "पृ. N / प.वि.", lists, ranges, Devanagari
    digits, blank "पृ.      /प.वि."); "“…”" quotes are skipped in related; page range 1..N only with --pages N
  - note.first ends with "सादर."; no letter number in it — "क्र." / "क्रमांक" + a token with "/" outside quotes and
    पृ.N/प.वि. (a petition / application / case no. excepted) (§4.29(1), audit 05.11.2026 Q-F7 / R-F2)
  - C1 (Abhi 05.11.2026, option आ; §4.29(1)/(5), §4.30(7), §4.36): no incoming letter number anywhere else in the note
    body either (paras incl. table cells, sub, closing; outside quotes and पृ.N/प.वि.): "क्र." / "क्रमांक" + a token with a
    digit or "/" within 4 words after or 6 words before a पत्र-word (पत्र, पत्रास, पत्रान्वये, स्मरणपत्र …); GR / case /
    order / point words right before "क्र." (शासन निर्णय, परिपत्रक, आदेश — order nos. are kept, Abhi 05.11.2026 "आदेशाचे
    क्रमांक ठेवा" —, याचिका, अर्ज, प्र. क्र., अ.क्र., मुद्दा …), a U.O.
    reference of any department / another desk's reference no. ("अनौपचारिक संदर्भ क्र. …", "कार्यासन … संदर्भ क्र. …";
    Abhi 05.11.2026 — kept) and the Section's own file no. ("संकिर्ण-…") excepted (note_letter_no_hits)
  - C2 (Abhi 05.11.2026, option आ; §4.18, §4.31(अ)): the missing-info para lists its items inline after ":-" — "(1) …;
    (2) …." (error when no inline "(1)"; WARN for a table right after the para; missing_inline_problems)
  - last note para (note.closing if not blank, else the last text item of note.paras) is one of the SOP forms:
    "सबब, … पत्राचे प्रारूप पृ.  /प.वि. वर मान्यतेस्तव सादर. मान्य झाल्यास पत्र निर्गमित करण्यात येईल." or
    "सबब, … वित्त विभागाच्या मान्यतेस्तव सादर करण्यात येत आहे." or (several drafts, INSTRUCTIONS §4.28, 03.11.2026)
    "सबब, … पत्राचे प्रारूप व शासन निर्णयाचे प्रारूप पृ.  /प.वि. वर मान्यतेस्तव सादर." (two or more of पत्राचे / स्मरणपत्राचे /
    <order kinds below>, the first optionally followed by "प्रारूप", then "," / "व", any words, the last kind + "प्रारूप(े)";
    optionally "मान्य झाल्यास … निर्गमित करण्यात येईल / येतील.") or (order draft, 02.11.2026, docs/COURT_AND_ORDERS_RESEARCH.md
    R3 (c), B7) "सबब, … <शासन निर्णयाचे / शुद्धिपत्रकाचे / परिपत्रकाचे / ज्ञापनाचे / अधिसूचनेचे / आदेशाचे / पृष्ठांकनाचे /
    प्रसिद्धीपत्रकाचे / पूरकपत्राचे (04.11.2026, docs/FORMS_RESEARCH_ORDERS.md)> प्रारूप पृ.  /प.वि. वर
    मान्यतेस्तव सादर." or "सबब, … अधिसूचनेची मराठी व इंग्रजी प्रारूपे पृ.  /प.वि. वर मान्यतेस्तव सादर." (optionally "… मान्य झाल्यास … निर्गमित करण्यात येईल.")
    or (02.11.2026, audit A1 H5 — SOP Step 3 routes) "सबब, … <वित्त / सामान्य प्रशासन / सार्वजनिक आरोग्य> विभागाच्या
    <मान्यतेस्तव / मान्यतेसाठी / अभिप्रायास्तव / अभिप्रायार्थ / सहमतीस्तव> सादर (करण्यात येत आहे)." or (INSTRUCTIONS §8.3,
    Format-2) "… सार्वजनिक आरोग्य विभागास विनंती करण्यास हरकत नसावी. (मान्यतेस्तव सादर.)" or (approval within the department,
    no draft) "सबब, … मान्यतेस्तव सादर." or (file closure) "सबब, … नस्ती बंद करण्यास मान्यता असावी."; a bare note.closing
    "मान्यतेस्तव सादर." is read together with the last para; §4.37 (05.11.2026, D2): each form may be preceded by the lead
    "उपरोक्त (सर्व) वस्तुस्थिती विचारात घेता, <decisive facts>." (read from its "सबब," / as "सबब," — last_core)
  - spec "order" / "orders" (§4.28) / "parawise" (optional, 02.11.2026): CLI only — tools/lint_order.py lint_order(spec) /
    tools/lint_parawise.py lint_parawise(spec) are imported lazily and their lines added; a missing module is a
    "WARN" line, never an error (lint_extras)
  - note.signers == INSTRUCTIONS §4.6 chain (+ "अ.मु.स. (वित्त)" last); "अ.मु.स. (वित्त)" present <=> the last para sends
    the file to Finance or to the Public Health Department (§4.6, §8.3; finance_route: "वित्त विभागाच्या मान्यतेस्तव /
    अभिप्रायास्तव / सहमतीस्तव …", "… विभागास विनंती", "सार्वजनिक आरोग्य विभागाच्या …")
  - §4.19 (text outside quotes; note body, letter, related heading/source — not the verbatim related text): no '.:-'
    (use ':-'), 'करून' not 'करुन', 'प्रारूप' not 'प्रारुप', 'अनुसरून' not 'अनुसरुन', one space after 'दि.' / 'क्र.' / 'प्र. क्र.' in running text
    (file/letter nos. and other tokens with '/' or '-' left exactly); missing-info para (05.11.2026) "सदर प्रकरणी <प्राधिकारी>
    यांच्या दि. <DD.MM.YYYY> रोजीच्या प्रस्तावाचे अवलोकन केले असता, त्यामध्ये खालील माहिती आढळून येत नाही:- (1) …; (2) …."
    (":-" right after "नाही"; the old opener "प्रस्तावासोबत खालील माहिती उपलब्ध नाही:-" is still read as that para + WARN
    "जुने रूप"; the 40-word WARN counts that para only up to ":-")
  - "letter" (one object) and / or "letters" (list, INSTRUCTIONS §4.28, 03.11.2026: e.g. a letter and a स्मरणपत्र in one
    run; paths letters[i].…): every rule below applies to each letter; "letter" + "letters" together is an error
  - letter (when present): ref_no संकिर्ण-<year>/<file no>/प्र.क्र.<n>/का.6 ("संकीर्ण-" also accepted; "____" blanks);
    to, subject, refs present; intro starts "उपरोक्त विषयाबाबत संदर्भाधीन", contains "आपणांस कळविण्यात येते की," and ends
    with ":-" when there are points; "ही विनंती" only in an information-request letter (points / table / reminder, or the
    intro asks "… उपलब्ध करून देण्यात यावी"; requests_info) — a reply / conveying letter needs none
  - letter "kind": "do" (अर्धशासकीय पत्र; docs/FORMS_RESEARCH_DO_UO.md; lint_do_letter) — instead of the intro rules:
    ref_no (desk form), subject, to (addressee at the foot), body (list, first person: मी / मला / माझ्या …), salutation
    "प्रिय श्री. … / प्रिय महोदय," when given; intro / points / closing / reminder / copies / enclosure are errors; an
    unknown kind is an error; the note's last para names it "अर्धशासकीय पत्राचे" (§4.28 WARN)
  - note "uo" (अनौपचारिक संदर्भ; uo_problems): keys to / no / date / desk / from (text); "to" = a department ending
    "विभाग"; the last para sends the file to that department
  - §4.20: no document (प्रत / प्रमाणपत्र / अहवाल) in a data row of a letter.points table (outside quotes); documents go
    after the table as a numbered list introduced by DOC_INTRO
  - §4.21 स्मरणपत्र (letter.reminder): refs[0] has "या कार्यासनाचे समक्रमांकाचे पत्र", intro has "अद्याप अप्राप्त" and
    "ही विनंती"
  - §4.22 letter to the High Court that asks information from a District Judge ("प्रमुख जिल्हा व सत्र न्यायाधीश, <place>
    यांच्याकडून"): letter.copies has "प्रमुख जिल्हा व सत्र न्यायाधीश, जिल्हा व सत्र न्यायालय, <place> यांना आवश्यक
    कार्यवाहीसाठी"
  - §4.23 "मा." (note body and letter outside quotes; not letter.to / refs / copies): before मुख्य न्यायमूर्ती /
    न्यायमूर्ती / प्रशासकीय न्यायाधीश (one "मा." before the whole phrase: "मा. प्रशासकीय न्यायमूर्ती समिती"; "निवृत्त
    न्यायमूर्ती" not a title), and before उच्च न्यायालय… (the court itself; office designations "उच्च न्यायालय (… शाखा)",
    "उच्च न्यायालय, … शाखा / खंडपीठ …", "<पद>, उच्च न्यायालय" excepted); a doubled "मा." is an error
  - §4.24 "शुद्धिपत्रक" (not शुध्दिपत्रक / शुद्धीपत्रक / शुद्धपत्रक) — also in the related heading/source (outside quotes)
  - "ध्द" -> "द्ध" (error; मराठी भाषा विभाग GR दि. 10.11.2022) — not in a person's name (after श्री. / श्रीमती / कै. /
    डॉ., §4.18 name as in the proposal) and not inside quotes
  - §4.31 (03.11.2026): missing information / documents only in ONE para — the missing-info para above (MISSING_HEAD_RE;
    old or new opener; with its table / sub-points); elsewhere in the note body (first, paras, tables, sub, closing; outside “…”
    quotes) no "नमूद नाही", "जोडलेले / जोडलेल्या नाहीत", "उपलब्ध नाही", "प्रस्तावासोबत नाही(त)", "प्रत नाही", "सादर
    केलेली नाही" remark (MISSING_REMARK_RE; a missing table value is "____"); two such paras is an error; WARN when that
    para is not just before the last para (missing_scatter)
WARN level (spec.json; note body and letter, text outside quotes; related and signers not checked; warn_hits / fix_warn;
  शुद्धलेखनाचे 18 नियम, docs/STYLE_RESEARCH_LANG.md §5.2; numbered after the §3 proposals L1–L10):
  - L11 नियम 12: "…णेसाठी / …णेबाबत / …णेकरिता" -> "…ण्यासाठी / …ण्याबाबत / …ण्याकरिता" (also a letter subject taken
    from the proposal, e.g. "मिळणेबाबत" — warning only)
  - L12 नियम 14: halant before an abbreviation dot ("एम्.ए.", "पीएच्.डी.") -> "एम.ए.", "पीएच.डी."
  - L13 नियम 3 (आदरार्थी): त्याने/तिने -> त्यांनी, त्याचे/तिचे -> त्यांचे, त्याला/तिला -> त्यांना, त्याच्या/तिच्या -> त्यांच्या
  - L14 नियम 1–4 (अनुस्वार): "आपणास" -> "आपणांस"; "यांनां" / "यानां" -> "यांना"
  - C32 §4.34 (03.11.2026, relevance + एकसंध flow; flow_warnings): note-body table header with a "पृ./प.वि." / "पृ."
    column; "पृष्ठांकन" / "माहितीकरिता देण्यात" outside quotes; quote-gluing "तसेच, “" / "” व “"; a quoted “…”
    containing "…" / "..." (note body and related extracts)
  - §4.37 (05.11.2026, owner decisions D1–D4, docs/FLOW_RESEARCH.md; flow_warnings, table_shape_warnings,
    para_count_warnings, para2_warnings): "जुने रूप §4.37" for the list "उपरोक्त वस्तुस्थिती पुढीलप्रमाणे आहे:-" and for a
    condition table (header "अट" + "… स्थिती"); a prayers table (header "प्रार्थना") -> "§4.37 मुद्देनिहाय"; a note table
    whose data cells are mostly not figures (figure_cell: digits, short "22 वर्षे" / "____"), unless a service-detail header (नाव / पद / पदनाम /
    नियुक्ती / दिनांक / कालावधी); more than 10 numbered paras; para 2 of a note answering a letter not opening "सदर
    पत्रान्वये" / "उपरोक्त पत्रान्वये" (court / legislature notes excepted: §4.32 (अ) petition sentence)
  - §4.28 (03.11.2026): the note's last para names every draft in the spec (letter "पत्राचे", reminder "स्मरणपत्राचे",
    order kinds "शासन निर्णयाचे / शुद्धिपत्रकाचे / …", parawise "परिच्छेदनिहाय"; drafts_unnamed)
  - audit 05.11.2026 (docs/AUDIT_2026-11-05.md; samples' known findings: tests/test_lint_spec.py AUDIT_KNOWN_WARNS):
    Q-F6 "उल्लेख (केलेला) नाही" / "आढळून येत / आले नाही" outside the missing-info para (MISSING_REMARK_WARN_RE);
    (Q-F8 "उपरोक्त वस्तुस्थिती" 3–6 items: dropped 05.11.2026 with the list itself, §4.37 D2);
    Q-F9 own-text sentence (outside quotes; note body strings, letter intro / points / closing / body) of more than 40
    words (an abbreviation dot after a one-akshara word does not end a sentence); Q-F11 court note (spec "parawise" /
    "affidavit"): para 2 without "प्रतिवादी क्र."; with "parawise" also para 3 not "… मागण्या …:-" + the prayers as
    sub-points "(अ) …" (note.sub, or inline) (§4.32 (आ), §4.37);
    Q-F12 a letter to a "वकील" with a copy to the High Court Registry (§4.35; on_behalf_of: lint_parawise /
    lint_affidavit); Q-F19 no demand word in para 1–2 (court note: 1–3) when para 1 answers an incoming letter / petition
    (§4.30(3)); Q-F21 "पूर्वोदाहरण-ग्रंथालय" in a related heading / source
Output (audit S-F3): --details FILE (or env CASE_DETAILS_FILE) — full lines appended to FILE, stdout with every quoted
  segment replaced by its length (redact / out; the same switch in lint_parawise, lint_affidavit, verify_outputs,
  extract_check). Without it the output is unchanged.
Desk (C30, 03.11.2026): spec "desk" names the profile tools/desks/<id>.json (absent = law-desk6, the Desk-6 values above);
  the signer chain, the finance signer (in place of "अ.मु.स. (वित्त)") and the letter ref_no form come from it; an unknown
  desk id is an error ("desk: desk profile — …").
Rules (study.json): parts with headings भाग 0 … भाग 7 (--allow-missing-part1: भाग 1 may be absent); no internal ids;
  पृ. references as above ("“…”" skipped).
The constants and check functions below are the ONE definition shared with tools/verify_outputs.py."""
import json
import re
import sys

# ---------------- shared rule definitions (also used by verify_outputs.py) ----------------
import os as _os
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import desk as _desk  # noqa: E402 — C30 (03.11.2026): desk profiles tools/desks/<id>.json (spec "desk", default law-desk6)
_D0 = _desk.load_desk(None)
# the default desk's chain as literals (tests/test_engine_brief.py parses them); = tools/desks/law-desk6.json signers /
# finance_signer (tests/test_desks.py checks); per spec: desk_signers(desk)
SIGNERS = ["(अ.मा. वसू)", "क. अ. (अ.का.)", "अ.स. (श्री. वडनेरकर)", "उ.वि.स. नि. उ.स. (श्री. बोंद्रे)", "सचिव व व. वि. स. (श्री. बिले)"]
AMS = "अ.मु.स. (वित्त)"
FIN = "वित्त विभागाच्या मान्यतेस्तव"
# closed list (PROPOSAL_SOP.md Step 4 "Banned words") — keep both lists identical
BANNED = ["दिसून येते", "असे दिसते", "पडताळणी केली असता", "माझ्या मते", "मला वाटते", "असे वाटते", "ठरवावे", "कदाचित", "बहुधा"]
RELATED = "संबंधित माहिती (संदर्भासाठी)"
PKG = "पॅकेज PDF"
ID_RE = re.compile(r"z\d_\d{4}")
REPO_RE = re.compile(r"(register/|service-rules/|precedent-library/|(?<![A-Za-z])pdf/|(?<![A-Za-z])repo(?![A-Za-z])|रेपो)", re.I)
D = r"[0-9०-९]+"
NUMLIST = rf"{D}(?:\s*(?:-|–|ते|,)\s*{D})*"
REF_LOOSE = re.compile(r"पृ\.((?:(?!पृ\.)[^/\n]){0,40}?)/\s*प\.वि\.")   # inner part never holds another "पृ." (C27: "पृ. 22, नियम … (पृ.31/प.वि.)")
REF_PKG = re.compile(rf"पॅकेज PDF\s*पृ\.\s*({NUMLIST})")
REF_NO = _desk.letter_ref_re(_D0)   # default desk (profile letter.ref_pattern): संकिर्ण|संकीर्ण-<year>/<file no>/प्र.क्र.<n>/का.6;
# blanks "____" when the C R / file no. is not in the proposal (ENGINE_PROMPT rule 5); both spellings: the file no. is
# copied as the निर्देशपत्र writes it ("संकीर्ण-2026/979/…" or "संकिर्ण-…") — audit A1, 02.11.2026
QUOTE_RE = re.compile(r"“[^”]*”")
PART_RE = re.compile(r"\s*भाग\s*([0-9०-९])(?![0-9०-९])")
LH_EMAIL = _D0["letter"]["email"]   # default desk; per desk: profile letter.email ("" = not known, not checked)
# last-para forms (PROPOSAL_SOP Step 4), tolerant of the wording between the fixed parts
LAST_LETTER_RE = re.compile(r"^सबब\s*,.*पत्राचे\s+प्रारूप\s+पृ\.[^/]{0,40}/\s*प\.वि\.\s*वर\s+मान्यतेस्तव\s+सादर\s*\.\s*"
                            r"मान्य\s+झाल्यास\s+पत्र\s+निर्गमित\s+करण्यात\s+येईल\s*\.$", re.S)
LAST_FIN_RE = re.compile(r"^सबब\s*,.*वित्त\s+विभागाच्या\s+मान्यतेस्तव\s+सादर\s+करण्यात\s+येत\s+आहे\s*\.$", re.S)
# order draft on the file (02.11.2026; R3 (c): "…शासन निर्णयाचे प्रारुप पृ.  /प.वि.वर मान्यतेस्तव सादर.")
# "अधिसूचनेची मराठी व इंग्रजी प्रारूपे" = B6 notification (Marathi + English text)
# 04.11.2026: पृष्ठांकनाचे / प्रसिद्धीपत्रकाचे / पूरकपत्राचे (new order types, docs/FORMS_RESEARCH_ORDERS.md); कार्यालयीन
# आदेशाचे = "आदेशाचे"; शपथपत्राचे / उत्तराचे (tools/build_affidavit.py, tools/build_lq.py)
ORDER_DRAFT_KINDS = (r"(?:(?:शासन\s+)?(?:निर्णयाचे|शुद्धिपत्रकाचे|परिपत्रकाचे|ज्ञापनाचे|अधिसूचनेचे|आदेशाचे|पृष्ठांकनाचे"
                     r"|प्रसिद्धीपत्रकाचे|पूरकपत्राचे)\s+प्रारूप"
                     r"|अधिसूचनेची\s+मराठी\s+व\s+इंग्रजी\s+प्रारूपे"
                     r"|शपथपत्राचे\s+प्रारूप|उत्तराचे\s+प्रारूप)")
LAST_ORDER_RE = re.compile(rf"^सबब\s*,.*{ORDER_DRAFT_KINDS}\s+पृ\.[^/]{{0,40}}/\s*प\.वि\.\s*वर\s+मान्यतेस्तव\s+सादर"
                           r"(?:\s+करण्यात\s+येत\s+आहे)?\s*\.(?:\s*मान्य\s+झाल्यास\s+[^.]{0,120}निर्गमित\s+करण्यात\s+येईल\s*\.)?$", re.S)
# 02.11.2026 (audit A1 H5): the other SOP Step 3 routes, in the Section's wording (old notes /tmp/old, medical-bill
# Format-1/2, Medical-Bill-Samples.docx): "… विभागाच्या मान्यतेस्तव / अभिप्रायास्तव / अभिप्रायार्थ / सहमतीस्तव सादर (करण्यात येत आहे)."
# for वित्त / सामान्य प्रशासन / सार्वजनिक आरोग्य विभाग; सा.आ.वि. "एक विशेष बाब" ("… सार्वजनिक आरोग्य विभागास विनंती करण्यास
# हरकत नसावी. मान्यतेस्तव सादर." — Format-2 para 8; its opening "प्रस्तुत प्रकरणातील उक्त वस्तुस्थिती विचारात घेता," is kept);
# approval within the department ("सबब, … मान्यतेस्तव सादर." — no draft: a draft takes the प्रारूप forms above); file closure.
_SADAR = r"सादर(?:\s+करण्यात\s+येत\s+आहे)?\s*\."
_ACTION = r"(?:मान्यतेस्तव|मान्यतेसाठी|अभिप्रायास्तव|अभिप्रायार्थ|अभिप्रायासाठी|सहमतीस्तव|सहमतीसाठी)"
DEPTS = r"(?:वित्त|सामान्य\s+प्रशासन|सार्वजनिक\s+आरोग्य)\s+विभाग"
LAST_DEPT_RE = re.compile(rf"^सबब\s*,.*{DEPTS}(?:\s+व\s+{DEPTS})?ाच्या\s+{_ACTION}\s+{_SADAR}$", re.S)
LAST_PHD_RE = re.compile(r"^(?:सबब\s*,|.*विचारात\s+घेता\s*,).*सार्वजनिक\s+आरोग्य\s+विभागा(?:स|ला)\s+(?:पुन:श्च\s+)?विनंती\s+"
                         rf"करण्यास\s+हरकत\s+नसावी\s*\.(?:\s*मान्यतेस्तव\s+{_SADAR})?$", re.S)
LAST_DEPT_APPROVAL_RE = re.compile(rf"^सबब\s*,(?!.*प्रार[ुू]प).*(?:मान्यतेस्तव|मान्यतेसाठी)\s+{_SADAR}$", re.S)
LAST_CLOSE_RE = re.compile(r"^सबब\s*,.*(?:नस्ती\s*बंद|नस्तीबंद)[^.]*(?:मान्यता\s+असावी|मान्यतेस्तव\s+सादर|सादर)\s*\.$", re.S)
# INSTRUCTIONS §4.28 (03.11.2026, Abhi: "user multiple option choose karel"): one last para naming every draft made, e.g.
# "सबब, … पत्राचे प्रारूप व शासन निर्णयाचे प्रारूप पृ.      /प.वि. वर मान्यतेस्तव सादर." (two or more drafts)
_DRAFT_KIND = (r"(?:(?:शासन\s+)?(?:निर्णयाचे|शुद्धिपत्रकाचे|परिपत्रकाचे|ज्ञापनाचे|अधिसूचनेचे|आदेशाचे|पृष्ठांकनाचे"
               r"|प्रसिद्धीपत्रकाचे|पूरकपत्राचे)|पत्राचे|पत्रांचे|"
               r"स्मरणपत्राचे|अधिसूचनेची\s+मराठी\s+व\s+इंग्रजी|शपथपत्राचे|उत्तराचे)")
_DRAFT_ITEM = rf"{_DRAFT_KIND}(?:\s+प्रारूपे?)?"
LAST_COMBINED_RE = re.compile(rf"^सबब\s*,.*{_DRAFT_ITEM}(?:\s*,\s*|\s+व\s+)[^.]{{0,160}}?{_DRAFT_KIND}\s+प्रारूपे?\s+"
                              r"पृ\.[^/]{0,40}/\s*प\.वि\.\s*वर\s+मान्यतेस्तव\s+सादर(?:\s+करण्यात\s+येत\s+आहे)?\s*\."
                              r"(?:\s*मान्य\s+झाल्यास\s+[^.]{0,160}निर्गमित\s+करण्यात\s+(?:येईल|येतील)\s*\.)?$", re.S)
# §4.37 (Abhi 05.11.2026, D2 "2अ"): the last para may open with the office lead "उपरोक्त (सर्व) वस्तुस्थिती विचारात घेता, …"
# (FLOW_RESEARCH §1: 34 hits / 21 files) — "उपरोक्त वस्तुस्थिती विचारात घेता, <decisive facts>. सबब, <action>." or
# "उपरोक्त वस्तुस्थिती विचारात घेता, सबब, …" or "उपरोक्त वस्तुस्थिती विचारात घेता, <action>." ("सबब, उपरोक्त वस्तुस्थिती
# विचारात घेता, …" already starts with "सबब,"). The forms below are matched on the para with that lead normalised to
# "सबब, …" (last_core); the endings are unchanged.
LAST_LEAD_RE = re.compile(r"^उपरोक्त\s+(?:सर्व\s+)?(?:परिच्छेद[^,]{0,40}\s+)?वस्तुस्थिती\s+विचारात\s+घेता\s*,\s*")


def last_core(t):
    """The last para with a leading "उपरोक्त वस्तुस्थिती विचारात घेता, …" normalised: the text from the first "सबब," on,
    else "सबब, " + the rest (§4.37 D2)."""
    t = t or ""
    m = LAST_LEAD_RE.match(t)
    if not m:
        return t
    k = re.search(r"सबब\s*,", t[m.end():])
    return t[m.end() + k.start():] if k else "सबब, " + t[m.end():]


class _LeadTolerant:
    """A LAST_* regex whose .match() reads the para through last_core (§4.37 D2); .pattern / .search as the regex."""
    def __init__(self, rx):
        self.rx, self.pattern = rx, rx.pattern

    def match(self, t):
        return self.rx.match(last_core(t))

    def search(self, t):
        return self.rx.search(last_core(t))


LAST_FORMS = tuple(_LeadTolerant(r) for r in (LAST_LETTER_RE, LAST_COMBINED_RE, LAST_FIN_RE, LAST_ORDER_RE, LAST_DEPT_RE,
                                              LAST_PHD_RE, LAST_DEPT_APPROVAL_RE, LAST_CLOSE_RE))
BARE_CLOSING_RE = re.compile(r"^(?:प्रस्ताव\s+)?मान्यतेस्तव\s+सादर\s*\.?$")   # Format-1/2: "मान्यतेस्तव सादर." as its own line
# अ.मु.स. (वित्त) route (§4.6, §8.3 "फक्त नस्ती वित्त/सा.आ.वि. कडे जाताना"): the last para sends the file to Finance or to PHD
_ROUTE_TAIL = rf"(?:च्या\s+{_ACTION}|स\s+(?:पुन:श्च\s+)?विनंती|कडे\s+(?:पाठवि|सादर))"
FIN_ROUTE_RE = re.compile(rf"वित्त\s+विभागा{_ROUTE_TAIL}|सामान्य\s+प्रशासन\s+विभाग\s+व\s+वित्त\s+विभागाच्या\s+{_ACTION}")
PHD_ROUTE_RE = re.compile(rf"सार्वजनिक\s+आरोग्य\s+विभागा{_ROUTE_TAIL}")
INTRO_START = "उपरोक्त विषयाबाबत संदर्भाधीन"
INTRO_HAS = "आपणांस कळविण्यात येते की,"
# Missing-information para (Abhi 05.11.2026, replaces the fixed opener "प्रस्तावासोबत खालील माहिती उपलब्ध नाही:-"):
# "सदर प्रकरणी <प्राधिकारी> यांच्या दि. <DD.MM.YYYY> रोजीच्या प्रस्तावाचे अवलोकन केले असता, त्यामध्ये खालील माहिती आढळून
# येत नाही:- (1) …; (2) …." — recognised by MISSING_NEW_RE; the old opener is still recognised (same §4.31 rules) + WARN.
MISSING_HEAD = "त्यामध्ये खालील माहिती आढळून येत नाही"   # fixed core of the new opener; ":-" follows it
MISSING_OLD_HEAD = "प्रस्तावासोबत खालील माहिती उपलब्ध नाही"   # old opener (no longer used — WARN)
MISSING_FORM = ("सदर प्रकरणी <प्राधिकारी> यांच्या दि. <DD.MM.YYYY> रोजीच्या प्रस्तावाचे अवलोकन केले असता, "
                "त्यामध्ये खालील माहिती आढळून येत नाही:- (1)…; (2)….")
MISSING_NEW_RE = re.compile(r"अवलोकन\s+केले\s+असता,?\s+त्यामध्ये\s+खालील\s+(?:माहिती|कागदपत्रे)"
                            r"(?:\s+(?:व|आणि)\s+(?:माहिती|कागदपत्रे))?\s+आढळून\s+येत\s+नाहीत?(?![ऀ-ॿ])")
MISSING_NEW_COLON_RE = re.compile(MISSING_NEW_RE.pattern + r"\s*:-")
MISSING_OLD_MSG = ("जुने रूप — §4.31 (05.11.2026): 'सदर प्रकरणी <प्राधिकारी> यांच्या दि. __ रोजीच्या प्रस्तावाचे अवलोकन केले "
                   "असता, त्यामध्ये खालील माहिती आढळून येत नाही:- (1) …; (2) ….'")
# §4.31 (Abhi 03.11.2026: "… te vishisht ekach paragraph mdhe discuss kravi"): missing information / documents only in ONE
# para opening "प्रस्तावासोबत खालील माहिती (/ कागदपत्रे) उपलब्ध नाही(त)", just before the last para; elsewhere in the note
# body no remark of the kinds below (outside “…” quotes); a missing table value is "____"
MISSING_OLD_RE = re.compile(r"^(?:[0-9०-९]+\.\s*)?प्रस्तावासोबत\s+खालील\s+(?:माहिती|कागदपत्रे)(?:\s+(?:व|आणि)\s+(?:माहिती|कागदपत्रे))?"
                            r"\s+उपलब्ध\s+नाहीत?(?![ऀ-ॿ])")
# a para is the missing-info para when it opens with the old form, or carries the new core within its first 400
# characters before the first ":-" (the authority and date come before it)
MISSING_HEAD_RE = re.compile(r"^(?:[0-9०-९]+\.\s*)?(?:" + MISSING_OLD_RE.pattern.split(")?", 1)[1]
                             + r"|(?:(?!:-).){0,400}?" + MISSING_NEW_RE.pattern + r")")
_NAHI = r"नाहीत?(?![ऀ-ॿ])"
_LELA = r"लेल(?:े|ी|ा|्या)"
MISSING_REMARK_RE = re.compile(rf"नमूद\s+(?:के{_LELA}\s+)?{_NAHI}|जोड{_LELA}\s+{_NAHI}|जोडण्यात\s+आ{_LELA}\s+{_NAHI}"
                               rf"|उपलब्ध\s+(?:करून\s+दि{_LELA}\s+)?{_NAHI}|प्रस्तावासोबत\s+{_NAHI}"
                               rf"|(?<![ऀ-ॿ])प्रती?\s+{_NAHI}|सादर\s+(?:के{_LELA}|करण्यात\s+आ{_LELA})\s+{_NAHI}")
# audit 05.11.2026 Q-F6 (WARN level — the approved HTE sample uses "… उल्लेख नाही" in two facts): the same remark in
# other words
MISSING_REMARK_WARN_RE = re.compile(rf"उल्लेख\s+(?:के{_LELA}\s+)?{_NAHI}|आढळून\s+(?:येत|आल[ेाी]|आ{_LELA})\s+{_NAHI}")
MISSING_ONE_MSG = ("उपलब्ध नसलेली माहिती / कागदपत्रे फक्त एकाच '… अवलोकन केले असता, त्यामध्ये खालील माहिती आढळून येत नाही:-' परिच्छेदात "
                   "(शेवटच्या परिच्छेदाच्या आधी); इतरत्र असा शेरा नको, तक्त्यात '____' (§4.31)")
# INSTRUCTIONS §4.20 (02.11.2026): letter table only for data to fill in; documents after the table as a numbered list
DOC_RE = re.compile(r"प्रत(?![्िृ])|प्रमाणपत्र|अहवाल")   # प्रत / प्रती(सह) — not प्रत्यक्ष, प्रतिनियुक्ती
DOC_INTRO = "तसेच, खालील कागदपत्रे उपलब्ध करून देण्यात यावीत, ही विनंती:-"
DOC_MSG = "कागदपत्रे तक्त्यात नको — तक्त्यानंतर यादीत (§4.20)"


def num(s):
    return int(s.translate(str.maketrans("०१२३४५६७८९", "0123456789")))


def ns(s):
    return re.sub(r"\s+", " ", s).strip()


def ref_problems(text, npages, label, skip_quotes=False):
    """पृ. reference problems in text; npages None = syntax / reversed-range only (no package range check)."""
    if skip_quotes:
        text = QUOTE_RE.sub(" ", text)
    probs = []
    lists = []
    for mt in REF_LOOSE.finditer(text):
        inner = mt.group(1).strip()
        if not re.search(r"[0-9०-९]", inner):
            continue  # blank placeholder "पृ.      /प.वि." or table header "पृ./प.वि."
        if not re.fullmatch(NUMLIST, inner):
            probs.append(f"{label}: unparsed reference '{mt.group(0)}'"); continue
        lists.append((mt.group(0), inner))
    for mt in REF_PKG.finditer(text):
        lists.append((mt.group(0), mt.group(1)))
    for whole, inner in lists:
        for part in re.split(r"\s*,\s*", inner):
            ends = [num(x) for x in re.split(r"\s*(?:-|–|ते)\s*", part) if x.strip()]
            if len(ends) == 2 and ends[0] > ends[1]:
                probs.append(f"{label}: reversed range '{whole}'")
            if npages is not None:
                for n in ends:
                    if not 1 <= n <= npages:
                        probs.append(f"{label}: '{whole}' — page {n} outside package (1-{npages})")
    return probs


QUOTE_RE = re.compile(r"“[^”]*”|\"[^\"]*\"")
def unquoted(text):
    """Text outside “…” quotes (verbatim extracts keep their own wording)."""
    return QUOTE_RE.sub(" ", text or "")


# 02.11.2026 (audit A1): a person's name is written as in the proposal (§4.18) — "ध्द" in a name (e.g. "श्री. अ. बुध्दे")
# is not an error. Name span = after श्री. / श्रीमती / श्रीम. / कै. / डॉ. up to the next comma, ")" or "यांनी / यांचे / यांना /
# यांच्या / यांचा / यांची" (at most 60 characters; no such end: the next three words).
NAME_RE = re.compile(r"(?<![ऀ-ॿ])(?:श्री\.|श्रीमती|श्रीम\.|कै\.|डॉ\.)"
                     r"(?:[^,)\n]{0,60}?(?=,|\)|\s+यां(?:नी|चे|ना|च्या|चा|ची)(?![ऀ-ॿ])|$)|(?:\s*[^\s,)]+){1,3})")
DHD_RE = re.compile(r"ध्द")


def unnamed(text):
    """Text with person-name spans blanked (only for the "ध्द" rule)."""
    return NAME_RE.sub(" ", text or "")


# INSTRUCTIONS §4.18 (01.11.2026): respectful, clear official Marathi
STYLE_RULES = [
    (re.compile(r"सौ\."), "आदरार्थी उल्लेख — 'सौ.' ऐवजी 'श्रीमती' (§4.18)"),
    (re.compile(r"(?<![ऀ-ॿ])कै\.(?=\S)"), "आदरार्थी उल्लेख — 'कै.' नंतर एक जागा (§4.18)"),
    # मराठी भाषा विभाग GR कपासू-2020/प्र.क्र.56/भाषा-2, दि.10.11.2022 (docs/STYLE_RESEARCH_LANG.md)
    (DHD_RE, "शुद्धलेखन — 'ध्द' ऐवजी 'द्ध' (मराठी भाषा विभाग GR दि.10.11.2022)"),
    (re.compile(r"(?<![ऀ-ॿ])श्री\.(?=[^\s(])"), "आदरार्थी उल्लेख — 'श्री.' नंतर एक जागा; नाव प्रस्तावात आहे तसे (§4.18)"),
    (re.compile(r"शुद्धीपत्र|शुद्धपत्र|शुध्दिपत्र|शुध्दीपत्र"), "शुद्धलेखन — 'शुद्धिपत्रक' (§4.24)"),
]
LETTER_STYLE_RULES = [
    # GAD टिप्पणी लेखन व पत्रव्यवहार 12.3: letters to courts in "विशेष सौजन्यपूर्वक भाषा" (docs/STYLE_RESEARCH_LETTERS.md)
    (re.compile(r"अतितात्काळ|तात्काळ|तातडीने|त्वरित|ताबडतोब|विनाविलंब|अविलंब|सत्वर"),
     "पत्राची भाषा — 'तात्काळ / तातडीने / त्वरित…' नको; 'लवकरात लवकर' वापरा (§4.18)"),
    (re.compile(r"(?:करावी|करावा|करावे|द्यावी|द्यावा|द्यावे|यावी|यावीत|यावे|पाठवावी|पाठवावे|कळवावे)\s*\.(?!:-)"),
     "पत्राची भाषा — थेट आदेशात्मक शेवट; '…, ही विनंती.' अशी विनंतीपूर्वक मांडणी हवी (§4.18)"),
]
REQUEST = "ही विनंती"
ASK_RE = re.compile(r"उपलब्ध\s+करून\s+देण्यात\s+याव|पाठविण्यात\s+याव|कळविण्यात\s+याव|मागविण्यात\s+(?:आलेली|येत)")


def requests_info(letter, intro):
    """True for an information-request letter (§4.18 "…, ही विनंती." required): it has points / a table, is a reminder,
    or the intro asks ("… उपलब्ध करून देण्यात यावी"). A reply / forwarding / conveying letter ("… कळविण्यात येते की, …"
    with no request) needs no "ही विनंती" (audit A1, 02.11.2026)."""
    L = letter if isinstance(letter, dict) else {}
    return bool(points_ask(L.get("points")) or L.get("reminder") or ASK_RE.search(unquoted(intro or "")))


# 03.11.2026 (C30, §4.28 (अ)): an intimation / status letter (e.g. the present status to the Lokayukta office) has
# numbered points that only state facts; points count as a request only when they hold a table or ask wording
POINT_ASK_RE = re.compile(r"उपलब्ध\s+करून|पाठविण्यात\s+याव|कळविण्यात\s+याव|मागविण्यात")


def points_ask(points):
    """True when letter points ask for something: a table (data to fill in, §4.20) or ask wording (POINT_ASK_RE)
    outside quotes. points: the spec list ({"table"} / str items); True = a legacy "has points" flag."""
    if points is True:
        return True
    for pt in points if isinstance(points, list) else []:
        if isinstance(pt, dict) and pt.get("table") is not None:
            return True
        if isinstance(pt, str) and POINT_ASK_RE.search(unquoted(pt)):
            return True
    return False


def style_hits(text, letter=False):
    t = unquoted(text)
    out = [msg for rx, msg in STYLE_RULES if (rx.search(unnamed(t)) if rx is DHD_RE else rx.search(t))]
    if letter:
        out += [msg for rx, msg in LETTER_STYLE_RULES if rx.search(t)]
    return out


# INSTRUCTIONS §4.19 (01.11.2026) — मराठी भाषा विभाग GR कपासू-2020/प्र.क्र.56/भाषा-2, दि. 10.11.2022 (परिशिष्ट तीन,
# अ.क्र. 23: संक्षेपचिन्हानंतर जागा). Applied to text outside “…” quotes only; one definition for lint, verify and the
# sample normaliser (fix_lang).
# "अनुसरून" — शुद्धलेखन नियम 8 (धातूचे -ऊन रूप; docs/STYLE_RESEARCH_LANG.md §5.2), 02.11.2026
SPELL_419 = {"करुन": "करून", "प्रारुप": "प्रारूप", "अनुसरुन": "अनुसरून"}
COLON_DASH_RE = re.compile(r"(?<!प\.वि)(?<!क्र)(?<!दि)\.:-")   # ".:-" -> ":-" (abbreviation dots such as प.वि. kept)
ABBR_PREFIXES = ("प्र.क्र.", "क्र.", "दि.")                         # running-text abbreviations that take a space
CODE_RE = re.compile(r"/|[0-9A-Za-zऀ-ॿ_]-[0-9A-Za-zऀ-ॿ_]")      # file/letter nos., codes: left exactly
OPEN_CH = "(“‘[\"'"
ABBR_NEXT = re.compile(r"[0-9०-९A-Za-zऀ-ॿ_(]")


def _abbr_fix_token(tok):
    """Spaced form of one whitespace token, or None when it needs no change (§4.19 abbreviation rule)."""
    core = tok.lstrip(OPEN_CH); lead = tok[:len(tok) - len(core)]
    pre = next((p for p in ABBR_PREFIXES if core.startswith(p)), None)
    if pre is None or CODE_RE.search(core):
        return None
    rest = core[len(pre):]
    spaced = "प्र. क्र." if pre == "प्र.क्र." else pre
    if rest and ABBR_NEXT.match(rest):
        return lead + spaced + " " + rest
    return lead + spaced + rest if spaced != pre else None


def abbr_hits(text):
    """Tokens in running text with no space after 'दि.' / 'क्र.' / 'प्र.क्र.' (quotes, codes with '/' or '-' skipped)."""
    return [mt.group(0) for mt in re.finditer(r"\S+", unquoted(text)) if _abbr_fix_token(mt.group(0)) is not None]


def _fix_plain(t):
    for a, b in SPELL_419.items():
        t = t.replace(a, b)
    t = COLON_DASH_RE.sub(":-", t)
    return re.sub(r"\S+", lambda mt: _abbr_fix_token(mt.group(0)) or mt.group(0), t)


def fix_lang(text):
    """text with the §4.19 forms applied outside “…” / "…" quotes (quoted extracts unchanged)."""
    out, pos = [], 0
    for mt in QUOTE_RE.finditer(text):
        out += [_fix_plain(text[pos:mt.start()]), mt.group(0)]; pos = mt.end()
    out.append(_fix_plain(text[pos:]))
    return "".join(out)


def lang_hits(text):
    """§4.19 problems in text (outside quotes)."""
    t = unquoted(text); out = []
    for a, b in SPELL_419.items():
        if a in t: out.append(f"शुद्धलेखन — '{a}' ऐवजी '{b}' (§4.19)")
    if COLON_DASH_RE.search(t): out.append("विरामचिन्ह — '.:-' ऐवजी ':-' (§4.19)")
    hits = abbr_hits(text)
    if hits: out.append(f"संक्षेपचिन्हानंतर एक जागा — 'दि. 17.09.2026', 'क्र. 108', 'प्र. क्र.' (§4.19): {hits[:3]}")
    return out


# WARN level (02.11.2026): शुद्धलेखनाचे 18 नियम (महामंडळ; शासन मान्यता 1962/1972; docs/STYLE_RESEARCH_LANG.md §5.2).
# Warnings are printed as "WARN <path>: …" and never fail lint or verify. Scope: note body and letter, text outside quotes
# (related — GR titles and extracts — and the signer chain are not checked). Numbered after the §3 proposals L1–L10.
DEV = "\u0900-\u097f"
_SRC = "(STYLE_RESEARCH_LANG §5.2)"
WARN_RULES = [
    # (id, regex, fix(match) -> replacement, message(match))
    ("L11", re.compile(rf"(?<![{DEV}])([{DEV}]*?)णे(साठी|बाबत|करिता)"),
     lambda mt: mt.group(1) + "ण्या" + mt.group(2),
     lambda mt, fx: f"शुद्धलेखन नियम 12 — '{mt.group(0)}' ऐवजी '{fx}' (प्रस्तावातील विषय-रूप असले तरी सूचना) {_SRC}"),
    ("L12", re.compile(rf"(?<![{DEV}])([{DEV}]*?[{DEV}])\u094d\."),   # consonant (or a stray vowel sign, "बी्.") + halant + "."
     lambda mt: mt.group(1) + ".",
     lambda mt, fx: f"शुद्धलेखन नियम 14 — इंग्रजी शब्द/पदवीच्या संक्षेपात पाय मोडका नको: '{mt.group(0)}' ऐवजी '{fx}' (उदा. एम.ए., पीएच.डी.) {_SRC}"),
    ("L13", re.compile(rf"(?<![{DEV}])(त्याने|तिने|त्याचे|तिचे|त्याला|तिला|त्याच्या|तिच्या)(?![{DEV}])"),
     lambda mt: {"त्याने": "त्यांनी", "तिने": "त्यांनी", "त्याचे": "त्यांचे", "तिचे": "त्यांचे", "त्याला": "त्यांना",
                 "तिला": "त्यांना", "त्याच्या": "त्यांच्या", "तिच्या": "त्यांच्या"}[mt.group(1)],
     lambda mt, fx: f"शुद्धलेखन नियम 3 (आदरार्थी) — अधिकारी/व्यक्तीसाठी '{mt.group(0)}' ऐवजी '{fx}' {_SRC}"),
    ("L14", re.compile(rf"(?<![{DEV}])(आपणास|यांनां|यानां)(?![{DEV}])"),
     lambda mt: {"आपणास": "आपणांस", "यांनां": "यांना", "यानां": "यांना"}[mt.group(1)],
     lambda mt, fx: f"शुद्धलेखन नियम 1–4 (अनुस्वार, आदरार्थी) — '{mt.group(0)}' ऐवजी '{fx}' {_SRC}"),
]


def warn_hits(text):
    """WARN-level messages for text outside “…” / "…" quotes (one per distinct word and rule)."""
    t = unquoted(text); out = []
    for _, rx, fix, msg in WARN_RULES:
        for mt in rx.finditer(t):
            m_ = msg(mt, fix(mt))
            if m_ not in out:
                out.append(m_)
    return out


def fix_warn(text):
    """text with the WARN-level forms applied outside “…” / "…" quotes (quoted extracts unchanged)."""
    def fix(t):
        for _, rx, f, _m in WARN_RULES:
            t = rx.sub(f, t)
        return t
    out, pos = [], 0
    for mt in QUOTE_RE.finditer(text):
        out += [fix(text[pos:mt.start()]), mt.group(0)]; pos = mt.end()
    out.append(fix(text[pos:]))
    return "".join(out)


# INSTRUCTIONS §4.23 (Abhi, 02.11.2026): "मा." before the High Court and judges (Section practice; docs/STYLE_RESEARCH_LETTERS.md F10)
# 02.11.2026 (audit A1): one "मा." before the whole title phrase counts — "मा. प्रशासकीय न्यायमूर्ती समिती", "मा. मुख्य
# न्यायमूर्ती" (the phrase starts at its qualifier, so fix_ma never puts a second "मा." inside it); "निवृत्त / सेवानिवृत्त
# न्यायमूर्ती" (a person's description) is not a title; an office designation is excepted: "उच्च न्यायालय (… शाखा)",
# "उच्च न्यायालय, अपील / मूळ शाखा", "उच्च न्यायालय, खंडपीठ …" and "<पद>, उच्च न्यायालय" ("प्रबंधक (कार्मिक), उच्च न्यायालय",
# "सहायक सरकारी वकील, उच्च न्यायालय"). The letter's address-like fields (to, refs, copies) are not checked (lint_spec).
_JUDGE_QUAL = r"(?:(?:प्रशासकीय|मुख्य|प्रभारी|वरिष्ठ)\s+)?"
MA_JUDGE_RE = re.compile(rf"(?<![ऀ-ॿ])(?<!निवृत्त )(?<!निवृत्त)(?<!निवृत्त मुख्य )(?<!निवृत्त प्रशासकीय ){_JUDGE_QUAL}न्यायमूर्ती|(?<![ऀ-ॿ])प्रशासकीय\s+न्यायाधीश")
MA_COURT_RE = re.compile(r"(?<![ऀ-ॿ])(?:मुंबई\s+)?उच्च\s+न्यायालय(?!\s*\()(?![ऀ-ॿ]*\s*,\s*(?:[ऀ-ॿ]+\s+)?(?:शाखा|खंडपीठ))")
MA_BEFORE = re.compile(r"मा\.\s?$")
MA_DESIG_BEFORE = re.compile(r"(?:प्रबंधक|निबंधक|रजिस्ट्रार|वकील|अभियोक्ता|अधिकारी|अधीक्षक|सचिव|लेखापाल|न्यायमूर्ती|न्यायाधीश)"
                             r"(?:\s*\([^)]{0,40}\))?\s*,\s*$")
MA_DOUBLE_RE = re.compile(r"मा\.\s?मा\.|(?:प्रशासकीय|मुख्य)\s+मा\.\s?न्यायमूर्ती")


VS_RE = re.compile(r"विरुद्ध|(?<![A-Za-z])(?:v|vs|V|Vs|VS)\.?(?=\s)|(?<![A-Za-z])versus(?![A-Za-z])")


def case_title_party(t, start, end, reach=80):
    """True when t[start:end] (e.g. "उच्च न्यायालय") is a party name in a case title "<A> विरुद्ध <B>" (also "v." / "vs" /
    "versus"): "विरुद्ध" within `reach` characters after it (party A) or before it (party B) with no bracket, line break
    or "।" between — e.g. "(पंजाब व हरियाणा उच्च न्यायालय व इतर विरुद्ध जगदेव सिंग)" (§4.23 does not apply to party names)."""
    stop = re.compile(r"[()\n।]")
    after = t[end:end + reach]
    cut = stop.search(after)
    if VS_RE.search(after[:cut.start()] if cut else after):
        return True
    before = t[max(0, start - reach):start]
    cuts = list(stop.finditer(before))
    return bool(VS_RE.search(before[cuts[-1].end():] if cuts else before))


def _ma_spans(t, court=True):
    out = []
    for m in MA_JUDGE_RE.finditer(t):
        if not MA_BEFORE.search(t[max(0, m.start() - 5):m.start()]):
            out.append((m.start(), m.group(0)))
    if court:
        for m in MA_COURT_RE.finditer(t):
            before = t[max(0, m.start() - 70):m.start()]
            if case_title_party(t, m.start(), m.end()):   # a party in a case title "<A> विरुद्ध <B>" (C30, 03.11.2026)
                continue
            if not MA_BEFORE.search(before[-5:]) and not MA_DESIG_BEFORE.search(before):
                out.append((m.start(), m.group(0)))
    return sorted(out)


def ma_hits(text, court=True):
    """§4.23: occurrences outside quotes without "मा." before them; a doubled "मा." inside a title phrase."""
    t = unquoted(text)
    hits = [w for _, w in _ma_spans(t, court)]
    out = [f"आदरार्थी उल्लेख — 'मा. {sorted(set(hits))[0]}' (मा. उच्च न्यायालय / मा. न्यायमूर्ती; §4.23)"] if hits else []
    dbl = MA_DOUBLE_RE.search(t)
    if dbl:
        out.append(f"आदरार्थी उल्लेख — दुहेरी 'मा.': '{dbl.group(0)}' (एकच 'मा.' पूर्ण पदनामापूर्वी, उदा. 'मा. प्रशासकीय न्यायमूर्ती समिती'; §4.23)")
    return out


def fix_ma(text, court=True):
    """text with "मा. " inserted where §4.23 needs it (outside quotes); never a second "मा." inside a title phrase."""
    def fix(t):
        t = re.sub(r"मा\.\s?मा\.\s?", "मा. ", t)
        t = re.sub(r"(प्रशासकीय|मुख्य)\s+मा\.\s?(न्यायमूर्ती)", r"\1 \2", t)
        for pos, _ in reversed(_ma_spans(t, court)):
            t = t[:pos] + "मा. " + t[pos:]
        return t
    out, pos = [], 0
    for mt in QUOTE_RE.finditer(text):
        out += [fix(text[pos:mt.start()]), mt.group(0)]; pos = mt.end()
    out.append(fix(text[pos:]))
    return "".join(out)


# §4.21 स्मरणपत्र / §4.22 copy to the District Judge when the letter goes through the High Court
REMINDER_REF = "या कार्यासनाचे समक्रमांकाचे पत्र"
REMINDER_HAS = "अद्याप अप्राप्त"
DJ_FROM_RE = re.compile(r"प्रमुख\s+जिल्हा\s+व\s+सत्र\s+न्यायाधीश\s*,\s*([^\s,]+)\s+यांच्याकडून")
COPY_END = "यांना आवश्यक कार्यवाहीसाठी"


def dj_copy(place):
    return f"प्रमुख जिल्हा व सत्र न्यायाधीश, जिल्हा व सत्र न्यायालय, {place} {COPY_END}"


def letters_of(spec):
    """[(path, letter)]: "letter" -> ("letter", L); "letters" (list, §4.28) -> ("letters[i]", L) — the order of
    tools/mkdocs.py letters_of."""
    if not isinstance(spec, dict):
        return []
    out = [("letter", spec["letter"])] if spec.get("letter") else []
    ls = spec.get("letters")
    if isinstance(ls, list):
        out += [(f"letters[{i}]", x) for i, x in enumerate(ls) if x]
    return out


def letter_strings(spec):
    return [x for path, L in letters_of(spec) for x in strings(L, path)]


def banned_hits(text):
    return [w for w in BANNED if w in text]


# C27 (Abhi, 02.11.2026: "Noting drafting mdhe kontahi ishara, package pdf ase शब्द नकोत"; addendum "वरिष्ठ अधिकाऱ्याला
# असे वाटू नये, की AI che kam aahe"): no warning / working remark, no package word and no AI / automation word in the
# drafts (note body, संबंधित माहिती heading/source, letter, order / parawise drafts). The Study and status.json may keep them.
# "पॅकेज" is an error anywhere in these texts (quotes too; the verbatim related "text" only for "पॅकेज PDF"); the other
# words only outside “…” verbatim quotes. Unknown value -> "____"; an unavailable source is left out of the note.
PKG_WORD = "पॅकेज"
_LAT = r"(?<![A-Za-z])"
_LAT_END = r"(?![A-Za-z])"
DRAFT_WORDS = [   # (label, regex) — warning / working remarks (contract C27 §2)
    ("package PDF", re.compile(r"package\s*PDF", re.I)),
    ("इशारा", re.compile(r"इशारा")),
    ("पडताळणी अपूर्ण", re.compile(r"पडताळणी\s+अपूर्ण")),
    ("मागवावे", re.compile(r"मागवावे")),
    ("वाचन अपूर्ण", re.compile(r"वाचन\s+अपूर्ण")),
    ("अस्पष्ट", re.compile(r"अस्पष्ट")),
    ("पडताळलेले नाही", re.compile(r"पडताळलेले\s+नाही")),
    ("टीप :", re.compile(r"(?<![ऀ-ॿ])टीप\s*:")),
    ("warning", re.compile(_LAT + r"warnings?" + _LAT_END, re.I)),
    ("TODO", re.compile(_LAT + r"TODO" + _LAT_END, re.I)),
    # Abhi 03.11.2026 ("स्रोत/जसाच्या तसा काढा"; office notes never use them — docs/AI_TELLS.md)
    ("स्रोत", re.compile(r"स्रोत")),
    ("जसाच्या तसा", re.compile(r"जसाच्या\s+तसा")),
    ("जसेच्या तसे", re.compile(r"जसेच्या\s+तसे")),
    ("जशीच्या तशी", re.compile(r"जशीच्या\s+तशी")),
]
AI_WORDS = [      # (label, regex) — AI / automation words (contract C27 §4)
    ("AI", re.compile(_LAT + r"A\.?I\.?" + _LAT_END)),
    ("Claude", re.compile(_LAT + r"Claude", re.I)),
    ("Anthropic", re.compile(r"Anthropic", re.I)),
    ("मॉडेल", re.compile(r"मॉडेल")),
    ("model", re.compile(_LAT + r"models?" + _LAT_END, re.I)),
    ("स्वयंचलित", re.compile(r"स्वयंचलित")),
    ("automatic", re.compile(_LAT + r"automatic", re.I)),
    ("engine", re.compile(_LAT + r"engines?" + _LAT_END, re.I)),
    ("प्रणालीने तयार", re.compile(r"प्रणालीने\s+तयार")),
    ("generated", re.compile(_LAT + r"generated" + _LAT_END, re.I)),
    ("LLM", re.compile(_LAT + r"LLMs?" + _LAT_END)),
    ("GPT", re.compile(_LAT + r"(?:Chat)?GPT", re.I)),
    ("Gemini", re.compile(_LAT + r"Gemini" + _LAT_END, re.I)),
]
# lead's decision (research AI_TELLS, 02.11.2026): typographic / working tells in own text — the em dash (0 in the office's
# own notes), arrows, web addresses (the official GR website line "www.maharashtra.gov.in" of an order draft excepted) and
# the printed-page note "छापील पृ." (a source names the GR page as "पृ. N")
TELL_WORDS = [
    ("—", re.compile(r"—")),
    ("→", re.compile(r"[→⇒➔]")),
    ("http/www", re.compile(r"https?://|(?<![A-Za-z0-9.])www\.(?!maharashtra\.gov\.in)", re.I)),
    ("छापील पृ.", re.compile(r"छापील\s+पृ")),
]
DRAFT_MSG = "मसुद्यात इशारा / कामाचा शेरा / पॅकेज / AI शब्द नको (C27; अस्पष्ट मूल्य -> '____', उपलब्ध नसलेला स्रोत नोंदीत नाही)"


def draft_word_hits(text, quotes=False):
    """C27 words in a draft text: "पॅकेज" anywhere (quotes too unless quotes=True), the warning / working and AI words
    outside “…” / "…" quotes. quotes=True: the text is a verbatim extract (related "text") — only "पॅकेज PDF" counts."""
    t = text or ""
    if quotes:
        return [PKG] if PKG in t else []
    out = [PKG_WORD] if PKG_WORD in t else []
    u = unquoted(t)
    out += [lab for lab, rx in DRAFT_WORDS + AI_WORDS + TELL_WORDS if rx.search(u) and lab not in out]
    return out


ai_words_hits = lambda text: [lab for lab, rx in AI_WORDS if rx.search(unquoted(text or ""))]   # noqa: E731 — verify / metadata

# C27 §1: a संबंधित माहिती source ends with " (पृ.N/प.वि.)" (N, N-M, N,M) when its page is in the returned PDF, else it
# carries no page marker at all
REL_SRC_END = re.compile(rf"\(\s*पृ\.\s*{NUMLIST}\s*/\s*प\.वि\.\s*\)\s*\.?\s*$")


def related_source_problems(source):
    """C27 §1: page marker form of one related source (problems; [] = ok)."""
    s = (source or "").strip()
    marks = list(REF_LOOSE.finditer(unquoted(s)))
    if not marks and PKG not in s:
        return []
    if PKG in s:
        return ["page marker — '(पॅकेज PDF …)' नको; पानाचा संदर्भ ' (पृ.N/प.वि.)', परत केलेल्या PDF मध्ये पान नसल्यास "
                "कोणताही पान-संदर्भ नाही (C27)"]
    if len(marks) > 1 or not REL_SRC_END.search(s):
        return ["page marker — स्रोताच्या शेवटी फक्त एकदा ' (पृ.N/प.वि.)' (N, N-M, N,M); पान नसल्यास पान-संदर्भ नाही (C27)"]
    return []


def id_hits(text):
    return sorted(set(ID_RE.findall(text)))


def repo_hits(text):
    return sorted(set(mt.group(0) for mt in REPO_RE.finditer(text)))


def desk_signers(desk=None):
    """(signer chain, finance signer) of a desk profile (dict or id; None = law-desk6), whitespace-normalised like ns()."""
    p = desk if isinstance(desk, dict) else _desk.load_desk(desk)
    return [ns(x) for x in p["signers"]], ns(p["finance_signer"])


def signer_problems(tail, has_ams, desk=None):
    """tail = the signer lines in order (§4.6; the desk profile's chain, C30)."""
    sg, ams = desk_signers(desk)
    exp = sg + ([ams] if has_ams else [])
    return [] if [ns(x) for x in tail] == exp else [f"signer block {list(tail)} != {exp}"]


def finance_route(last):
    """True when the last para sends the file to Finance (मान्यतेस्तव / अभिप्रायास्तव / सहमतीस्तव …) or to the Public Health
    Department (INSTRUCTIONS §4.6, §8.3: अ.मु.स. (वित्त) "फक्त नस्ती वित्त/सा.आ.वि. कडे जाताना")."""
    t = unquoted(last or "")
    return FIN in t or bool(FIN_ROUTE_RE.search(t) or PHD_ROUTE_RE.search(t))


def finance_problems(last, has_ams, desk=None):
    fin = finance_route(last)
    AMS = desk_signers(desk)[1]
    return [] if fin == has_ams else [f"'{AMS}' {'present' if has_ams else 'absent'} but last para "
                                      f"{'sends' if fin else 'does not send'} the file to वित्त विभाग / सार्वजनिक आरोग्य विभाग "
                                      f"('{FIN}' / '… अभिप्रायास्तव' / '… विभागास विनंती'; §4.6, §8.3)"]


def part_no(text):
    mt = PART_RE.match(text or "")
    return num(mt.group(1)) if mt else None


def heading_problems(have, allow_missing=()):
    return [f"heading भाग {i} missing" for i in range(8) if i not in have and i not in allow_missing]


# ---------------- spec walking ----------------
def strings(obj, path):
    """(path, text) for every string inside obj (lists, dicts, table rows)."""
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, list):
        for i, x in enumerate(obj):
            yield from strings(x, f"{path}[{i}]")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if k == "bold_last":
                continue
            yield from strings(v, f"{path}.{k}" if path else k)


def lint_spec(spec, pages=None):
    P = []
    if not isinstance(spec, dict) or not isinstance(spec.get("note"), dict):
        return ["note: structure — spec has no 'note' object"]
    n = spec["note"]
    try:   # C30: the desk profile (spec "desk"); an unknown id is an error and the default desk's rules are used
        dk = _desk.desk_of(spec)
    except ValueError as e:
        P.append(f"desk: desk profile — {e}"); dk = _D0
    body = [x for k in ("first", "paras", "sub", "closing", "uo") if k in n for x in strings(n[k], f"note.{k}")]
    related = list(strings(spec.get("related", []), "related"))
    letter = letter_strings(spec)
    signers = list(strings(n.get("signers", []), "note.signers"))

    for path, t in body + related + letter + signers:
        for x in id_hits(t): P.append(f"{path}: internal id — '{x}'")
        for x in repo_hits(t): P.append(f"{path}: repo path/word — '{x}'")
    for path, t in body + letter:
        for w in banned_hits(t): P.append(f"{path}: banned word — '{w}'")
    # C27 (02.11.2026): no warning / working / package / AI word in the drafts — note body, letter, related heading/source
    # (outside quotes; "पॅकेज" anywhere); the verbatim related "text" only for "पॅकेज PDF"
    rel_txt = [(pth, t) for pth, t in related if re.search(r"\.text(\[|$)", pth)]
    for path, t in body + letter + [(pth, t) for pth, t in related if (pth, t) not in rel_txt]:
        for w in draft_word_hits(t):
            P.append(f"{path}: draft word — '{w}' — {DRAFT_MSG}")
    for path, t in rel_txt:
        for w in draft_word_hits(t, quotes=True):
            P.append(f"{path}: draft word — '{w}' — {DRAFT_MSG}")
    # C27 §1: related source ends with " (पृ.N/प.वि.)" or carries no page marker
    for i, it in enumerate(spec.get("related") or []):
        if isinstance(it, dict) and isinstance(it.get("source"), str):
            P += [f"related[{i}].source: {x}" for x in related_source_problems(it["source"])]
    for path, t in body:
        P += [f"{path}: {m}" for m in style_hits(t)]
    for path, t in letter:
        P += [f"{path}: {m}" for m in style_hits(t, letter=True)]
    # §4.23: the letter's address-like fields (to, refs, copies) are not checked (audit A1, 02.11.2026)
    for path, t in body + [(pth, t) for pth, t in letter
                           if not re.match(r"letters?(?:\[\d+\])?\.(?:to|refs|copies)(?:\[|$)", pth)]:
        P += [f"{path}: {m}" for m in ma_hits(t)]
    rel_own = [(pth, t) for pth, t in related if not re.search(r"\.text(\[|$)", pth)]  # extracts (.text) are verbatim
    for path, t in body + letter + rel_own:
        P += [f"{path}: {m}" for m in lang_hits(t)]
    for path, t in rel_own:   # §4.24 "शुद्धिपत्रक" also in the related heading/source (own text outside quotes)
        P += [f"{path}: {msg}" for rx, msg in STYLE_RULES if "4.24" in msg and rx.search(unquoted(t))]
    for path, t in body:
        u = ns(unquoted(t))
        if u.startswith(MISSING_OLD_HEAD) and not ns(t).startswith(MISSING_OLD_HEAD + ":-"):
            P.append(f"{path}: missing-info para — form '{MISSING_FORM}' (§4.19)")
        elif MISSING_HEAD_RE.match(u) and MISSING_NEW_RE.search(u) and not MISSING_NEW_COLON_RE.search(ns(t)):
            P.append(f"{path}: missing-info para — form '{MISSING_FORM}' (§4.19)")
    P += missing_scatter(note_seq(n))[0]   # §4.31 (03.11.2026)
    for path, t in body + letter:
        P += [f"{path}: पृ. reference — {x.split(': ', 1)[1]}" for x in ref_problems(t, pages, path)]
    for path, t in related:
        P += [f"{path}: पृ. reference — {x.split(': ', 1)[1]}" for x in ref_problems(t, pages, path, skip_quotes=True)]

    # first / last para
    first = n.get("first")
    if not isinstance(first, str) or not first.strip():
        P.append("note.first: structure — first para missing")
    elif not first.strip().endswith("सादर."):
        P.append("note.first: first para — must end with 'सादर.'")
    if isinstance(first, str):
        P += [f"note.first: {x}" for x in first_letter_no_problems(first)]   # §4.29(1), audit 05.11.2026 Q-F7 / R-F2
    P += note_letter_no_problems(n)   # C1 (05.11.2026): no incoming letter no. anywhere in the note body
    P += missing_inline_problems(n)[0]   # C2 (05.11.2026): missing-info items inline, not a table
    paras = n.get("paras", [])
    if not isinstance(paras, list):
        P.append("note.paras: structure — must be a list"); paras = []
    lpath, last = last_para(n)
    lastn = ns(last)
    if not any(r.match(lastn) for r in LAST_FORMS):
        P.append(f"{lpath}: last para — not one of the SOP forms ('सबब, … पत्राचे प्रारूप पृ.  /प.वि. वर मान्यतेस्तव सादर. "
                 f"मान्य झाल्यास पत्र निर्गमित करण्यात येईल.' / 'सबब, … वित्त विभागाच्या मान्यतेस्तव सादर करण्यात येत आहे.' / "
                 f"'सबब, … शासन निर्णयाचे प्रारूप पृ.  /प.वि. वर मान्यतेस्तव सादर.' / 'सबब, … सामान्य प्रशासन विभागाच्या "
                 f"मान्यतेस्तव / वित्त विभागाच्या अभिप्रायास्तव सादर.' / '… सार्वजनिक आरोग्य विभागास विनंती करण्यास हरकत नसावी. "
                 f"मान्यतेस्तव सादर.' / 'सबब, … मान्यतेस्तव सादर.' / 'सबब, … नस्ती बंद करण्यास मान्यता असावी.')")

    # signers + Finance
    sg = n.get("signers")
    if not isinstance(sg, list):
        P.append("note.signers: signer chain (§4.6) — missing"); sg = []
    sg = [ns(x) if isinstance(x, str) else x for x in sg]
    has_ams = desk_signers(dk)[1] in sg
    P += [f"note.signers: signer chain (§4.6) — {x}" for x in signer_problems(sg, has_ams, dk)]
    P += [f"{lpath}: अ.मु.स. (वित्त) <=> Finance last para — {x}" for x in finance_problems(lastn, has_ams, dk)]

    P += uo_problems(n, lastn, lpath)   # अनौपचारिक संदर्भ (note "uo")

    # letters ("letter" and / or "letters", §4.28)
    if spec.get("letter") and spec.get("letters"):
        P.append("letters: structure — give either 'letter' or 'letters' (list), not both (§4.28)")
    if "letters" in spec and not isinstance(spec.get("letters"), (list, type(None))):
        P.append("letters: structure — must be a list of letter objects (§4.28)")
    for lp, L in letters_of(spec):
        P += lint_letter(L, lp, dk)
    return P


# अर्धशासकीय पत्र (letter "kind": "do"; docs/FORMS_RESEARCH_DO_UO.md): GAD "टिप्पणी लेखन व पत्रव्यवहार" परि. 12.26–12.29 and
# specimen (book p.43–44, PDF p.47–48); MMOP 2023 §10.1(7)(a) "written in the first person" (PDF p.64), §11.4(3) "The subject
# should be mentioned invariably in all communications including reminders and demi official letters" (PDF p.80)
LETTER_KINDS = ("do",)
DO_SALUTATION_RE = re.compile(r"^प्रिय\s+(?:श्री\.|श्रीमती|महोदय|महोदया)")   # 12.27 "प्रिय श्री."; 12.28 "प्रिय महोदय"
DO_FIRST_PERSON_RE = re.compile(r"(?<![ऀ-ॿ])(?:मी|मला|माझे|माझी|माझा|माझ्या[ऀ-ॿ]*)(?![ऀ-ॿ])")
DO_OFFICIAL_ONLY = ("intro", "points", "closing", "reminder", "copies", "enclosure")   # ordinary-letter keys


def lint_do_letter(L, lp, dl):
    """problems of ONE अर्धशासकीय पत्र (kind "do") at JSON path lp; dl = desk profile["letter"]."""
    P = []
    rn = L.get("ref_no")
    if not isinstance(rn, str) or not re.fullmatch(dl["ref_pattern"], rn.strip()):
        P.append(f"{lp}.ref_no: ref no. — not {dl['ref_hint']}: '{rn}'")
    if not isinstance(L.get("subject"), str) or not L["subject"].strip():
        P.append(f"{lp}.subject: अर्धशासकीय पत्र — 'subject' missing (MMOP §11.4(3): subject invariably, D.O. letters too)")
    to = L.get("to")
    if not isinstance(to, list) or not any(isinstance(x, str) and x.strip() for x in to):
        P.append(f"{lp}.to: अर्धशासकीय पत्र — addressee name / designation / office lines missing (printed at the foot, left)")
    sal = L.get("salutation")
    if sal is not None and (not isinstance(sal, str) or not DO_SALUTATION_RE.match(ns(sal))):
        P.append(f"{lp}.salutation: अर्धशासकीय पत्र — 'प्रिय श्री. <नाव>,' / 'प्रिय महोदय,' (GAD परि. 12.27–12.28)")
    fr = L.get("from")
    if fr is not None and not (isinstance(fr, dict) and all(isinstance(fr.get(k, ""), str) for k in ("name", "designation"))):
        P.append(f"{lp}.from: अर्धशासकीय पत्र — {{'name': …, 'designation': …}}")
    bd = L.get("body")
    texts = [x for x in (bd if isinstance(bd, list) else []) if isinstance(x, str) and x.strip()]
    if not texts:
        P.append(f"{lp}.body: अर्धशासकीय पत्र — 'body' (list of paragraphs) missing or empty")
    elif not any(DO_FIRST_PERSON_RE.search(unquoted(t)) for t in texts):
        P.append(f"{lp}.body: अर्धशासकीय पत्र — first person (मी / मला / माझ्या …) required (MMOP §10.1(7)(a))")
    for k in DO_OFFICIAL_ONLY:
        if L.get(k):
            P.append(f"{lp}.{k}: अर्धशासकीय पत्र — '{k}' belongs to the ordinary letter; use 'body' (the specimen has no "
                     f"{k})")
    return P


def lint_letter(L, lp="letter", desk=None):
    """problems of ONE letter object at JSON path lp ("letter" or "letters[i]"); desk = profile (dict / id; None = law-desk6)."""
    P = []
    if not isinstance(L, dict):
        return [f"{lp}: structure — must be an object"]
    dl = (desk if isinstance(desk, dict) else _desk.load_desk(desk))["letter"]
    kind = L.get("kind")
    if kind is not None and kind not in LETTER_KINDS:
        return [f"{lp}.kind: letter kind — '{kind}' unknown (absent = ordinary letter; 'do' = अर्धशासकीय पत्र)"]
    if kind == "do":
        return lint_do_letter(L, lp, dl)
    rn = L.get("ref_no")
    if not isinstance(rn, str) or not re.fullmatch(dl["ref_pattern"], rn.strip()):
        P.append(f"{lp}.ref_no: ref no. — not {dl['ref_hint']}: '{rn}'")
    for k in ("to", "refs"):
        v = L.get(k)
        if not isinstance(v, list) or not any(isinstance(x, str) and x.strip() for x in v):
            P.append(f"{lp}.{k}: letter field — '{k}' missing or empty")
    if not isinstance(L.get("subject"), str) or not L["subject"].strip():
        P.append(f"{lp}.subject: letter field — 'subject' missing or empty")
    intro = L.get("intro")
    if not isinstance(intro, str) or not intro.strip():
        P.append(f"{lp}.intro: letter field — 'intro' missing or empty")
    else:
        it = ns(intro)
        if not it.startswith(INTRO_START):
            P.append(f"{lp}.intro: intro wording — must start with '{INTRO_START}'")
        if INTRO_HAS not in it:
            P.append(f"{lp}.intro: intro wording — must contain '{INTRO_HAS}'")
        if requests_info(L, it) and REQUEST not in unquoted(it):
            P.append(f"{lp}.intro: पत्राची भाषा — माहिती मागताना '…, {REQUEST}.' अशी विनंतीपूर्वक मांडणी हवी (§4.18)")
        if L.get("points") and not it.endswith(":-"):
            P.append(f"{lp}.intro: intro wording — must end with ':-' before the points")
    # §4.21 स्मरणपत्र
    if L.get("reminder"):
        r0 = (L.get("refs") or [""])[0] if isinstance(L.get("refs"), list) else ""
        if REMINDER_REF not in ns(str(r0)):
            P.append(f"{lp}.refs[0]: स्मरणपत्र (§4.21) — संदर्भ '{REMINDER_REF} दि. __'")
        if isinstance(intro, str) and (REMINDER_HAS not in intro or REQUEST not in intro):
            P.append(f"{lp}.intro: स्मरणपत्र (§4.21) — '… माहिती {REMINDER_HAS} आहे. … {REQUEST}.'")
    # §4.22 via the High Court, information from a District Judge -> copy line
    to_txt = " ".join(x for x in (L.get("to") or []) if isinstance(x, str))
    if "उच्च न्यायालय" in to_txt:
        copies = [ns(x) for x in (L.get("copies") or []) if isinstance(x, str)]
        for place in {m.group(1) for path, t in strings(L, lp) for m in DJ_FROM_RE.finditer(ns(unquoted(t)))}:
            if not any(place in c and c.endswith(COPY_END) for c in copies):
                P.append(f"{lp}.copies: प्रत (§4.22) — '{dj_copy(place)}'")
    pts = L.get("points") if isinstance(L.get("points"), list) else []
    for i, pt in enumerate(pts):
        if isinstance(pt, dict) and isinstance(pt.get("table"), list):
            for r, row in enumerate(pt["table"][1:], 1):
                for c, cell in enumerate(row if isinstance(row, list) else []):
                    if isinstance(cell, str) and DOC_RE.search(unquoted(cell)):
                        P.append(f"{lp}.points[{i}].table[{r}][{c}]: {DOC_MSG} — '{DOC_INTRO}'")
    return P


# अनौपचारिक संदर्भ (note "uo"; docs/FORMS_RESEARCH_DO_UO.md): MMOP 2023 §9.1(1), (4) (PDF p.57) — inter-departmental
# references are made unofficially, with a note signed by the officer "precisely specifying the points on which the opinion
# of the other department is sought"; GADT परि. 5.2 (book p.16, PDF p.20) — those points at the end of the note.
# Block = NPM परिशिष्ट-8 form foot (book p.77, PDF p.84; tools/mkdocs.py uo_lines)
UO_KEYS = ("to", "no", "date", "desk", "from")
UO_DEPT_RE = re.compile(r"^(.+?)\s*विभाग\s*$")


def uo_problems(n, lastn, lpath="note.paras"):
    """problems of note["uo"] (absent = none); lastn = the note's last para (normalised)."""
    u = n.get("uo")
    if u is None:
        return []
    if not isinstance(u, dict):
        return ["note.uo: अनौपचारिक संदर्भ — must be an object {'to', 'no', 'date', 'desk', 'from'}"]
    P = [f"note.uo.{k}: अनौपचारिक संदर्भ — unknown key (allowed: {', '.join(UO_KEYS)})" for k in u if k not in UO_KEYS]
    P += [f"note.uo.{k}: अनौपचारिक संदर्भ — text ('____' when not known)" for k in UO_KEYS
          if k in u and not isinstance(u[k], str)]
    to = u.get("to")
    if not isinstance(to, str) or not to.strip() or to.strip() == "____":
        P.append("note.uo.to: अनौपचारिक संदर्भ — the department the file is sent to (e.g. 'वित्त विभाग')")
    elif not UO_DEPT_RE.match(ns(to)):
        P.append(f"note.uo.to: अनौपचारिक संदर्भ — a department name ending 'विभाग' (printed '… विभागाकडे अनौपचारिक "
                 f"संदर्भ', NPM परिशिष्ट-8): '{to}'")
    else:
        dep = ns(to)
        if dep not in lastn:
            P.append(f"{lpath}: अनौपचारिक संदर्भ — the last para must "
                     f"send the file to '{dep}' (the points for its opinion / concurrence at the end of the note, "
                     f"GADT परि. 5.2; MMOP §9.1(4))")
    return P


def note_seq(n):
    """The note body in print order: [(JSON path, text, is_para)] — is_para False for a table cell / sub-point / other
    non-string item, which belongs to the para before it (§4.31)."""
    seq = []
    f = n.get("first")
    if isinstance(f, str) and f.strip():
        seq.append(("note.first", f, True))
    paras = n.get("paras") if isinstance(n.get("paras"), list) else []
    sub = n.get("sub") if isinstance(n.get("sub"), dict) else {}
    for i, x in enumerate(paras):
        if isinstance(x, str):
            if x.strip():
                seq.append((f"note.paras[{i}]", x, True))
        else:
            seq += [(pth, t, False) for pth, t in strings(x, f"note.paras[{i}]") if t.strip()]
        seq += [(pth, t, False) for pth, t in strings(sub.get(str(i), []), f"note.sub.{i}") if t.strip()]
    c = n.get("closing")
    if isinstance(c, str) and c.strip():
        seq.append(("note.closing", c, True))
    return seq


def missing_scatter(seq):
    """§4.31: (problems, warnings) for an ordered note body seq [(label, text, is_para)] (lint: note_seq; verify: the
    docx blocks). The missing-info para (MISSING_HEAD_RE) owns the non-para blocks after it (its table / sub-points).
    Problems: a MISSING_REMARK_RE remark outside “…” quotes in any other block; more than one missing-info para.
    Warning: the missing-info para is not just before the last para."""
    heads = [i for i, (_, t, isp) in enumerate(seq) if isp and MISSING_HEAD_RE.match(ns(unquoted(t)))]
    P, W, owned = [], [], set()
    for h in heads[1:]:
        P.append(f"{seq[h][0]}: missing-info para — more than one ({seq[heads[0]][0]} too); {MISSING_ONE_MSG}")
    for h in heads:
        owned.add(h); j = h + 1
        while j < len(seq) and not seq[j][2]:
            owned.add(j); j += 1
    for i, (lab, t, _) in enumerate(seq):
        if i not in owned:
            for m in MISSING_REMARK_RE.finditer(unquoted(t)):
                P.append(f"{lab}: missing-info remark — '{m.group(0)}' — {MISSING_ONE_MSG}")
            for m in MISSING_REMARK_WARN_RE.finditer(unquoted(t)):   # Q-F6: WARN level
                W.append(f"{lab}: missing-info remark — '{m.group(0)}' — {MISSING_ONE_MSG}")
    if heads:
        after = [i for i in range(max(owned) + 1, len(seq)) if seq[i][2]]
        if len(after) != 1:
            W.append(f"{seq[heads[-1]][0]}: missing-info para — should stand just before the last (सबब) para (§4.31)")
    return P, W


def last_para(n):
    """(JSON path, text) of the note's last para: note.closing if not blank (a bare "मान्यतेस्तव सादर." read together
    with the last text item of note.paras), else the last text item of note.paras."""
    paras = n.get("paras", []) if isinstance(n.get("paras", []), list) else []
    closing = n.get("closing")
    idx = [i for i, x in enumerate(paras) if isinstance(x, str)]
    lpath, last = (f"note.paras[{idx[-1]}]", paras[idx[-1]]) if idx else ("note.paras", "")
    if isinstance(closing, str) and closing.strip():
        if BARE_CLOSING_RE.match(ns(closing)) and idx:   # Format-1/2: "… हरकत नसावी." + "मान्यतेस्तव सादर." line
            lpath, last = "note.closing", last + " " + closing
        else:
            lpath, last = "note.closing", closing
    return lpath, last


# §4.28 (03.11.2026): the note's last para names every draft made — spec draft -> words that name it (WARN level)
ORDER_NAMES = {"gr": ("निर्णयाचे",), "corrigendum": ("शुद्धिपत्रकाचे",), "circular": ("परिपत्रकाचे",),
               "memo": ("ज्ञापनाचे",), "notification": ("अधिसूचनेचे", "अधिसूचनेची"),
               "endorsement": ("पृष्ठांकनाचे",), "office_order": ("आदेशाचे",), "press_note": ("प्रसिद्धीपत्रकाचे",),
               "addendum": ("पूरकपत्राचे",)}


def drafts_unnamed(spec):
    """Drafts in the spec ("letter"/"letters", "order"/"orders", "parawise", "affidavit", "lq") that the note's last para does not name."""
    if not isinstance(spec, dict) or not isinstance(spec.get("note"), dict):
        return []
    last = ns(unquoted(last_para(spec["note"])[1]))
    miss = []
    for lp, L in letters_of(spec):
        rem = isinstance(L, dict) and L.get("reminder")
        do = isinstance(L, dict) and L.get("kind") == "do"
        words = ("अर्धशासकीय पत्राचे",) if do else \
            ("स्मरणपत्राचे", "पत्राचे", "पत्रांचे") if rem else ("पत्राचे", "पत्रांचे")
        if not any(w in last for w in words):
            miss.append(f"{lp} ({'अर्धशासकीय पत्र' if do else 'स्मरणपत्र' if rem else 'पत्र'})")
    orders = ([spec["order"]] if isinstance(spec.get("order"), dict) else []) + \
             [o for o in (spec.get("orders") if isinstance(spec.get("orders"), list) else []) if isinstance(o, dict)]
    for o in orders:
        words = ORDER_NAMES.get(o.get("type"), ())
        if words and not any(w in last for w in words):
            miss.append(f"order {o.get('type')}")
    if spec.get("parawise") and "परिच्छेदनिहाय" not in last:
        miss.append("parawise (परिच्छेदनिहाय अभिप्राय)")
    if spec.get("affidavit") and "शपथपत्राचे" not in last:
        miss.append("affidavit (शपथपत्राचे प्रारूप)")
    if spec.get("lq") and "उत्तराचे" not in last:
        miss.append("lq (प्रश्नाच्या उत्तराचे प्रारूप)")
    return miss


# C32 §4.34 (Abhi 03.11.2026: "vinakarna upyogache naslele sandarbh noting mdhe dakhwile aahet … eksandh pna nahi"):
# relevance + एकसंध flow — WARN level only (never an error; verify_outputs prints the same as "WARN: …"). Note body:
# a table whose header row has a "पृ./प.वि." / "पृ." column (the ref goes in the sentence before the table); forwarding
# trivia "पृष्ठांकन" / "माहितीकरिता देण्यात" outside quotes; quote-gluing "तसेच, “" / "” व “" (one quote per sentence);
# §4.37 (Abhi 05.11.2026, D2/D3): the old summary list "उपरोक्त वस्तुस्थिती पुढीलप्रमाणे आहे:-" (0 in the office corpus,
# FLOW_RESEARCH §1) and the "अट / प्रस्तावातील स्थिती" condition table ("प्रस्तावातील स्थिती": corpus 0) -> "जुने रूप §4.37";
# a court prayers table (header "प्रार्थना") -> "§4.37 मुद्देनिहाय". Note body and related extracts: a quoted “…”
# containing "…" or "..." (a shortened quote, §1.1).
PAGE_COL_RE = re.compile(r"^\s*(?:पृ|पृष्ठ)\s*\.?\s*(?:क्र\s*\.?\s*)?(?:/\s*प\s*\.\s*वि\s*\.?)?\s*$")
TRIVIA_RE = re.compile(r"पृष्ठांकन(?!ाचे\s+प्रारूप|\s+निर्गमित)|माहितीकरिता\s+देण्यात")  # 04.11.2026: the endorsement draft itself ([I4.33]) is not trivia
GLUE_RE = re.compile(r"तसेच\s*,\s*“|”\s*व\s*“")
SUMMARY_HEAD_RE = re.compile(r"उपरोक्त\s+वस्तुस्थिती\s+(?:पुढीलप्रमाणे|खालीलप्रमाणे)")   # the old list (§4.37: WARN)
COND_HDR_RE = re.compile(r"(?<![ऀ-ॿ])(?:अट|अटी|परिस्थिती)(?![ऀ-ॿ])")   # a condition cell ("अट", "परिच्छेद 12 मधील परिस्थिती")
STATUS_HDR_RE = re.compile(r"स्थिती")   # + ANOTHER cell "प्रस्तावातील स्थिती" / "… वस्तुस्थिती" = the old condition table


def is_condition_header(cells):
    """True for the old "अट / प्रस्तावातील स्थिती" condition-table header (§4.29(9) before 05.11.2026)."""
    cs = [c for c in cells or [] if isinstance(c, str)]
    return any(COND_HDR_RE.search(c) and any(STATUS_HDR_RE.search(d) for k, d in enumerate(cs) if k != i)
               for i, c in enumerate(cs))


PRAYER_HDR_RE = re.compile(r"प्रार्थना")
OLD437 = "जुने रूप §4.37"
CURLY_QUOTE_RE = re.compile(r"“[^”]*”")
SHORT_QUOTE_RE = re.compile(r"…|\.\.\.")
FLOW_SRC = "(§4.34)"


def flow_warnings(seq, headers=(), related=()):
    """C32 §4.34 WARN-level findings. seq = the note body in print order [(label, text, is_para)] (lint: note_seq;
    verify: the docx blocks); headers = [(label, [header cells])] of each note-body table; related = [(label, text)] of
    the related extracts (only the shortened-quote rule). Returns ["<label>: <message>"]; never errors."""
    W = []
    def add(x):
        if x not in W:
            W.append(x)
    for lab, cells in headers:
        for c in cells or []:
            if isinstance(c, str) and PAGE_COL_RE.match(c):
                add(f"{lab}: table column '{c.strip()}' — no पृ./प.वि. column; give the reference once in the sentence "
                    f"before the table {FLOW_SRC}")
        cs = [c for c in cells or [] if isinstance(c, str)]
        if is_condition_header(cs):
            add(f"{lab}: condition table ('अट / … स्थिती') — {OLD437}: state each condition and the proposal's fact in "
                f"linked sentences / sub-points ('वरील अटीनुसार …; परंतु, सदर प्रकरणात …')")
        if any(PRAYER_HDR_RE.search(c) for c in cs):
            add(f"{lab}: prayers table — §4.37 मुद्देनिहाय: the prayers as sub-points '(अ) …; (आ) …' in petition order "
                f"(§4.32(आ))")
    for lab, t, _ in seq:
        for m in TRIVIA_RE.finditer(unquoted(t)):
            add(f"{lab}: forwarding detail '{m.group(0)}' — endorsement nos. / copies-for-information are not needed "
                f"to decide the demand {FLOW_SRC}")
        if GLUE_RE.search(t or ""):
            add(f"{lab}: quote-gluing ('तसेच, “…' / '” व “') — one quote per sentence, with its own subject {FLOW_SRC}")
    for lab, t in list((lab, t) for lab, t, _ in seq) + list(related):
        for m in CURLY_QUOTE_RE.finditer(t or ""):
            if SHORT_QUOTE_RE.search(m.group(0)):
                add(f"{lab}: shortened quote ('…' / '...' inside “…”) — quote the passage in full (§1.1) {FLOW_SRC}")
                break
    for lab, t, isp in seq:
        if isp and SUMMARY_HEAD_RE.search(unquoted(t)):
            add(f"{lab}: 'उपरोक्त वस्तुस्थिती पुढीलप्रमाणे आहे:-' list — {OLD437}: the last para opens 'उपरोक्त "
                f"वस्तुस्थिती विचारात घेता, …' with the decisive facts in one or two short sentences, then 'सबब, …'")
    return W


# §4.37 D3 (Abhi 05.11.2026: "तक्ता टेबल यामध्ये माहिती संख्या विषयक आकडेमोड असेल तरच योग्य वाटते …"; "सेवा अ"): a
# note-body table is for numerical / calculation data or the service-detail table. Heuristic (WARN only), chosen for
# few false positives (tried on all samples/specs tables, 05.11.2026): a data cell is a "figure" when at least a quarter
# of its non-space characters are digits (ASCII / Devanagari: "27.05.2025", "रु.60,000") or it is short (<= 20 chars)
# and holds a digit or a "____" blank ("22 वर्षे", an unknown figure); a long sentence with one date in it is words. A
# serial-number column ("अ.क्र." / "क्र.") is skipped (always digits), and so is the label column of a key-value table
# ("तपशील | माहिती": the labels are words by nature, the values decide). A table is flagged only with at least 2 data
# cells and fewer than half of them figures — amount, period, post-count and pay tables are mostly figures, while a
# condition / duties / demands / correspondence / opinions table is words. Any header cell naming नाव / पद / पदनाम /
# नियुक्ती / दिनांक / कालावधी marks the service-detail (or a dated) table and is never flagged. Old condition and
# prayers tables already carry their own §4.37 message (flow_warnings) and are not counted twice.
SERVICE_HDR_RE = re.compile(r"(?<![ऀ-ॿ])(?:नाव|पद|नियुक्ती|दिनांक|कालावधी)")
SERIAL_HDR_RE = re.compile(r"^\s*(?:अ\s*\.?\s*क्र|अनु\s*\.?\s*क्र|क्र\s*\.|क्रमांक\s*$|Sr\.?|S\.\s*No)")
NUMERIC_CELL_RE = re.compile(r"[0-9०-९]|_{3,}")
LABEL_HDR_RE = re.compile(r"^\s*(?:तपशील|बाब|विवरण|घटक)\s*$")


def figure_cell(c):
    t = re.sub(r"\s", "", c or "")
    if not t:
        return False
    nd = len(re.findall(r"[0-9०-९]", t))
    return nd * 4 >= len(t) or (len(t) <= 20 and bool(NUMERIC_CELL_RE.search(t)))


def table_shape_warnings(tables):
    """tables = [(label, rows)] (rows = list of cell lists, row 0 = header) -> §4.37 D3 WARN strings."""
    W = []
    for lab, rows in tables:
        if not rows or not isinstance(rows[0], list):
            continue
        hdr = [c if isinstance(c, str) else "" for c in rows[0]]
        if any(SERVICE_HDR_RE.search(c) for c in hdr) or any(PRAYER_HDR_RE.search(c) for c in hdr) or \
                is_condition_header(hdr):
            continue
        skip = {k for k, c in enumerate(hdr) if SERIAL_HDR_RE.match(c)}
        rest = [k for k in range(len(hdr)) if k not in skip]
        if len(rest) >= 2 and LABEL_HDR_RE.match(hdr[rest[0]]):
            skip.add(rest[0])
        cells = [c.strip() for r in rows[1:] if isinstance(r, list) for k, c in enumerate(r)
                 if k not in skip and isinstance(c, str) and c.strip()]
        if len(cells) >= 2 and sum(figure_cell(c) for c in cells) * 2 < len(cells):
            W.append(f"{lab}: descriptive table — §4.37 मुद्देनिहाय: tables only for figures (amounts, arrears, recovery, "
                     f"burden, pay, post counts, periods) or the service-detail table; conditions, duties, demands, "
                     f"chronology and opinions as linked sentences / sub-points")
    return W


def note_table_rows(n):
    """[(JSON path, rows)] of every {"table": [...]} in the note body (as note_tables, with all rows)."""
    out = []
    def walk(o, path):
        if isinstance(o, dict):
            if isinstance(o.get("table"), list) and o["table"] and isinstance(o["table"][0], list):
                out.append((f"{path}.table", o["table"]))
            for k, v in o.items():
                if k != "table":
                    walk(v, f"{path}.{k}")
        elif isinstance(o, list):
            for i, x in enumerate(o):
                walk(x, f"{path}[{i}]")
    for k in ("first", "paras", "sub", "closing"):
        if k in n:
            walk(n[k], f"note.{k}")
    return out


# §4.37 D1 (Abhi 05.11.2026, "1अ"): one issue per numbered para, its facts as sub-points (note.sub); office median 5
# numbered paras (FLOW_RESEARCH §2.1; ~5–8 for an ordinary proposal). Soft WARN above MAX_NUMBERED (para 1 + every
# printed numbered para; note.closing is printed without a number and not counted).
MAX_NUMBERED = 10


def para_count_warnings(n):
    paras = n.get("paras") if isinstance(n.get("paras"), list) else []
    k = 1 + sum(1 for x in paras if isinstance(x, str) and x.strip())
    if k > MAX_NUMBERED:
        return [f"note.paras: {k} numbered paras — §4.37 D1: one issue per numbered para, its facts as sub-points "
                f"(note.sub); about 5–8 for an ordinary proposal (office median 5)"]
    return []


# §4.37 D4 (Abhi 05.11.2026, "4अ"): when para 1 answers an incoming letter, para 2 (the first numbered para) opens
# "सदर पत्रान्वये …" (FLOW_RESEARCH §1: 20 / 17 CR) or, when para 1 cites several letters, "उपरोक्त पत्रान्वये …" (13 / 12)
# — who asks what, one sentence. Not for court notes (para 2 = the §4.32 (अ) petition sentence; also any note whose
# para 2 names a petition / respondents) or a legislature question note (spec "lq").
PARA2_OPEN_RE = re.compile(r"^(?:सदर|उपरोक्त|वरील)\s+(?:पत्रां?न्वये|पत्रां?द्वारे|पत्रांअन्वये)")
FIRST_LETTER_RE = re.compile(r"पत्रां?स\s+अनुसरून|पत्रासोबत|पत्रांसोबत")


def para2_warnings(spec):
    n = spec.get("note") if isinstance(spec, dict) and isinstance(spec.get("note"), dict) else None
    if n is None or spec.get("parawise") or spec.get("affidavit") or spec.get("lq"):
        return []
    if not FIRST_LETTER_RE.search(unquoted(n.get("first") or "")):
        return []
    paras = n.get("paras") if isinstance(n.get("paras"), list) else []
    idx = [i for i, x in enumerate(paras) if isinstance(x, str) and x.strip()]
    if not idx:
        return []
    t = ns(unquoted(paras[idx[0]]))
    if PARA2_OPEN_RE.match(t) or re.search(r"याचिका|प्रतिवादी\s+क्र\.", t):
        return []
    return [f"note.paras[{idx[0]}]: para 2 — §4.37 D4: open 'सदर पत्रान्वये …' ('उपरोक्त पत्रान्वये …' when para 1 cites "
            f"several letters): who asks what, one sentence"]


def note_tables(n):
    """[(JSON path, header row)] of every {"table": [...]} in the note body (first, paras, sub, closing)."""
    out = []
    def walk(o, path):
        if isinstance(o, dict):
            if isinstance(o.get("table"), list) and o["table"] and isinstance(o["table"][0], list):
                out.append((f"{path}.table[0]", o["table"][0]))
            for k, v in o.items():
                if k != "table":
                    walk(v, f"{path}.{k}")
        elif isinstance(o, list):
            for i, x in enumerate(o):
                walk(x, f"{path}[{i}]")
    for k in ("first", "paras", "sub", "closing"):
        if k in n:
            walk(n[k], f"note.{k}")
    return out


# ---------------- audit 05.11.2026 (docs/AUDIT_2026-11-05.md Part 3 / Part 9) ----------------
# Q-F7 / R-F2 (ERROR): INSTRUCTIONS §4.29(1) (Abhi 04.11.2026: "नोंदीच्या पहिल्याच पॅराग्राफ मध्ये पत्राचा क्रमांक … आवश्यकता
# नाही दिनांक जरी नमूद केला तरी होईल"): note.first names each covering letter by authority, date and पृ.N/प.वि. only — no
# letter number ("क्र." / "क्रमांक" followed by a token with "/"), outside quotes and outside the पृ.N/प.वि. references.
# A petition / application / case number ("याचिका क्र. 35697/2026") is not a letter number.
FIRST_LETTER_NO_RE = re.compile(r"(?<![ऀ-ॿ])(?:क्र\.|क्रमांक)\s*:?\s*-?\s*(\S*/\S*)")
CASE_NO_BEFORE_RE = re.compile(r"(?:याचिका|अर्ज|अपील|प्रकरण|दावा|petition|application)\s*(?:\([^)]{0,20}\)\s*)?$", re.I)
FIRST_LETTER_NO_MSG = ("first para — पत्राचा क्रमांक नको, दिनांक व पृ.N/प.वि. पुरेसे (§4.29(1), 04.11.2026)")


def first_letter_no_problems(first):
    """§4.29(1): letter numbers in note.first (outside quotes and पृ.N/प.वि.); [] = ok."""
    t = REF_LOOSE.sub(" ", unquoted(first or ""))
    out = []
    for m in FIRST_LETTER_NO_RE.finditer(t):
        if CASE_NO_BEFORE_RE.search(t[max(0, m.start() - 30):m.start()].rstrip()):
            continue
        if any(UO_REF_WORD_RE.match(_word(w)) for w in t[:m.start()].split()[-4:]):   # U.O. / other desk ref (05.11.2026)
            continue
        out.append(f"{FIRST_LETTER_NO_MSG}: letter no. at character {m.start()}")
    return out


# C1 (Abhi 05.11.2026, option आ — INSTRUCTIONS §4.29(1)/(5), §4.30(7), §4.36; ERROR): no incoming letter number anywhere in
# the note body (first, paras incl. table cells, sub, closing) — every letter is cited by authority, date and पृ.N/प.वि.
# only. A letter number = "क्र." / "क्रमांक" + a token with a digit or "/" that stands within 4 words after a पत्र-word
# (पत्र, पत्रा, पत्रास, पत्रान्वये, स्मरणपत्र, अ.शा.पत्र …; not परिपत्रक / शुद्धिपत्रक / पत्रक) or within 6 words before
# one ("क्र. 12/2026 दि. … रोजीच्या पत्रान्वये"). Not a letter number: the word right before "क्र." is a GR / case /
# order word (शासन निर्णय, परिपत्रक, अधिसूचना, आदेश, याचिका, अर्ज, अपील, प्रकरण, दावा, प्र. क्र., अ.क्र., नस्ती, उमेदवार,
# नियम, सांकेतांक …) or a point / para / page word ("पत्रातील मुद्दा क्र. 2", परिच्छेद, पृष्ठ, प्रश्न …); a U.O. reference
# of any department or another desk's reference number — one of the 4 words before "क्र." is "संदर्भ" / "अनौपचारिक" /
# "कार्यासन…" / "U.O." / "यु.ओ." (Abhi 05.11.2026: "अनौपचारिक संदर्भाचा क्रमांक ठेवायचा असतो … इतर कार्यासनाचा जरी संदर्भ
# क्रमांक असेल तरी तो सुद्धा नमूद करावा लागत असतो" — kept in the note); or the number is the Section's own file no.
# ("संकिर्ण-…" / "संकीर्ण-…"). Text inside “…”
# quotes, पृ.N/प.वि. references, "संबंधित माहिती" and the letter (ref_no, refs "आपले पत्र क्र. …") are not checked.
LETTER_WORD_RE = re.compile(r"(?<![ऀ-ॿ])(?:स्मरण)?पत्र(?!क)[ऀ-ॿ]*")
NOTE_NO_RE = re.compile(r"(?<![ऀ-ॿ])(?:क्र\.|क्रमांक)\s*:?\s*-?\s*(\S*[/0-9०-९]\S*)")
NOT_LETTER_WORD_RE = re.compile(r"^(?:प्र\.?|अ\.?|जी\.?आर\.?|याचिक|अर्ज|अपील|प्रकरण|दाव|निर्णय|परिपत्रक|शुद्धिपत्रक|पूरकपत्र"
                                r"|अधिसूचन|आदेश|सांकेतांक|नस्ती|उमेदवार|नियम|ज्ञापन|कलम|खाते|मुद्द|परिच्छेद|परि\.|खंड|पृष्ठ|पान|तक्त|अनुक्र|प्रश्न"
                                r"|petition|application|g\.?r\.?)",
                                re.I)
OWN_FILE_NO_RE = re.compile(r"^संकि?ी?र्ण-")
UO_BLANK_RE = re.compile(r"(?:अनौपचारिक\s+)?संदर्भ\s+(?:क्र\.|क्रमांक)\s*:?\s*-?\s*_{2,}(?![_/\-0-9A-Za-zऀ-ॿ])")   # wholly blank no.
UO_BLANK_MSG = ("अनौपचारिक / इतर कार्यासनाचा संदर्भ क्रमांक अभिलेखावर असल्यासच; नसल्यास ओळ किंवा '____' नको "
                "(वापरकर्ता, 05.11.2026, §4.36)")
UO_REF_WORD_RE = re.compile(r"^(?:संदर्भ|अनौपचारिक|कार्यासन\S*|का\.\s?[0-9०-९]+|U\.?\s?O\.?|यु\.\s?ओ\.?|अ\.\s?सं\.?)$", re.I)
NOTE_LETTER_NO_MSG = ("टिप्पणीत पत्राचा क्रमांक नको — प्राधिकारी, दिनांक व पृ.N/प.वि. पुरेसे "
                      "(§4.29(1)/(5), §4.30(7), 05.11.2026 C1 पर्याय आ)")


def _word(w):
    return w.strip(",;:()[]{}\"'“”‘’")


def note_letter_no_hits(text):
    """C1: incoming letter numbers in one note string (outside quotes and पृ.N/प.वि.) -> list of matched snippets."""
    t = REF_LOOSE.sub(" ", unquoted(text or ""))
    out = []
    for m in NOTE_NO_RE.finditer(t):
        tok = _word(m.group(1))
        if OWN_FILE_NO_RE.match(tok):
            continue
        head = t[:m.start()]
        before = [_word(w) for w in head.split()]
        if head and not head[-1].isspace() and before:   # "प्र.क्र." / "अ.क्र.": the same token's prefix
            prev = before[-1]
        else:
            prev = before[-1] if before else ""
        if prev and NOT_LETTER_WORD_RE.match(prev):
            continue
        if any(UO_REF_WORD_RE.match(w) for w in before[-4:]):   # U.O. / another desk's reference no. — kept
            continue
        hit = any(LETTER_WORD_RE.search(w) for w in before[-4:])
        if not hit:
            for w in [_word(x) for x in t[m.end():].split()][:6]:
                if NOTE_NO_RE.match(w) or w in ("क्र.", "क्रमांक") or NOT_LETTER_WORD_RE.match(w):
                    break
                if LETTER_WORD_RE.search(w):
                    hit = True; break
        if hit:
            out.append(ns(t[max(0, m.start() - 25):m.end()]))
    return out


def note_letter_no_problems(n):
    """C1 over the note body except note.first (first_letter_no_problems covers it): [] = ok."""
    P = []
    for k in ("paras", "sub", "closing"):
        if k in n:
            for path, t in strings(n[k], f"note.{k}"):
                P += [f"{path}: incoming letter no. '{x}' — {NOTE_LETTER_NO_MSG}" for x in note_letter_no_hits(t)]
    return P


# C2 (Abhi 05.11.2026, option आ — INSTRUCTIONS §4.18, §4.31(अ), §4.36): the missing-info para lists its items inline
# "… त्यामध्ये खालील माहिती आढळून येत नाही:- (1) …; (2) …." — not a table (ERROR: no inline "(1)" after ":-"; WARN: a
# table right after the para). The letter's information-request table (§4.20) is unchanged.
MISSING_INLINE_RE = re.compile(r":-\s*\(\s*[1१]\s*\)")
MISSING_INLINE_MSG = ("missing-info para — items inline '(1) …; (2) ….', not a table "
                      "(§4.18, §4.31(अ), 05.11.2026 C2 पर्याय आ)")


def missing_inline_problems(n):
    """C2: (problems, warnings) for the spec note's missing-info para(s)."""
    P, W = [], []
    paras = n.get("paras") if isinstance(n.get("paras"), list) else []
    for i, x in enumerate(paras):
        if not (isinstance(x, str) and MISSING_HEAD_RE.match(ns(unquoted(x)))):
            continue
        if not MISSING_INLINE_RE.search(ns(x)):
            P.append(f"note.paras[{i}]: {MISSING_INLINE_MSG}")
        nxt = paras[i + 1] if i + 1 < len(paras) else None
        if isinstance(nxt, dict) and "table" in nxt:
            W.append(f"note.paras[{i + 1}]: table after the missing-info para — items inline '(1) …; (2) ….' "
                     f"(§4.31(अ), 05.11.2026 C2 पर्याय आ)")
    return P, W


# Q-F8 (05.11.2026): the "उपरोक्त वस्तुस्थिती" 3–6 item count is dropped with the list itself (§4.37 D2; the old list
# now gets the "जुने रूप §4.37" WARN in flow_warnings).


# Q-F9 (WARN, §4.18 / §4.32(इ) "एका वाक्यात एक मुद्दा (40 शब्दांपेक्षा लांब वाक्य नको)"): own-text sentence (outside “…”
# quotes) of more than 40 words in the note body or a letter. A dot after a one-akshara word ("दि.", "क्र.", "पृ.", "श्री.",
# "प.वि.", initials) is an abbreviation, not a sentence end.
LONG_SENTENCE = 40
_C = "क-हक़-य़"
ONE_AKSHARA_RE = re.compile(rf"(?:[{_C}]़?(?:्[{_C}]़?)*[ा-ौॢॣ]?|[ऄ-औ])[ऀ-ः]?")
ABBR_WORDS = {"श्रीम", "No", "Nos", "Rs", "Dr", "Mr", "Mrs", "Ms", "vs", "v", "Sr", "St", "viz", "etc", "i.e", "e.g"}
SENT_END_RE = re.compile(r"[.।?!](?=\s|$)")


def sentences(text):
    """Own-text sentences of text (quotes removed): split at "." / "।" / "?" / "!" before a space or the end, except an
    abbreviation dot (one-akshara word or ABBR_WORDS)."""
    t = unquoted(text or "")
    t = re.sub(r"^\s*(?:[0-9०-९]+\.|\(\s*[0-9०-९]+\s*\))\s*", "", t)
    out, start = [], 0
    for m in SENT_END_RE.finditer(t):
        if m.group(0) == ".":
            w = re.search(r"([A-Za-z.]+|[ऀ-ॿ]+)$", t[start:m.start()])
            if w and (w.group(1) in ABBR_WORDS or ONE_AKSHARA_RE.fullmatch(w.group(1))
                      or (len(w.group(1)) == 1 and w.group(1).isalpha())):
                continue
        out.append(t[start:m.end()]); start = m.end()
    if t[start:].strip():
        out.append(t[start:])
    return [s for s in (x.strip() for x in out) if s]


def long_sentence_warnings(items):
    """items = [(label, text)] -> WARN strings (label, sentence no., word count only — no text, audit S-F3)."""
    W = []
    for lab, t in items:
        if MISSING_HEAD_RE.match(ns(unquoted(t))) and ":-" in t:   # 05.11.2026: its inline list is one sentence by design
            t = t[:t.index(":-") + 2]
        for k, s in enumerate(sentences(t), 1):
            nw = len([w for w in s.split() if re.search(r"[0-9A-Za-zऀ-ॿ_]", w)])
            if nw > LONG_SENTENCE:
                W.append(f"{lab}: sentence {k} has {nw} words — one point per sentence, at most {LONG_SENTENCE} words "
                         f"(§4.18, §4.32(इ))")
    return W


# Q-F11 (WARN, §4.32 (अ)/(आ)): a court note (spec with "parawise" / "affidavit") — para 2 names the respondents in order
# ("… यांना प्रतिवादी क्र. 1, …") and para 3 lists the prayers ("सदर याचिकेद्वारे याचिकाकर्त्यांनी पुढीलप्रमाणे प्रमुख मागण्या …:-"
# + the prayers as sub-points "(अ) …; (आ) …" — note.sub of that para or inline markers; §4.37 D3 "प्रार्थना अ", 05.11.2026;
# an old prayers table still counts here and gets its own "§4.37 मुद्देनिहाय" WARN in flow_warnings).
# Model: samples/specs/WP35697_2026_old-pension_finance-opinion.json.
RESP_RE = re.compile(r"प्रतिवादी\s+क्र\.")
PRAYER_HEAD_RE = re.compile(r"मागण्या")
SUBPOINT_RE = re.compile(r"\(\s*(?:[अ-औ]|[0-9०-९]+|[a-z])\s*\)")


def court_shape_warnings(spec):
    if not isinstance(spec, dict) or not (spec.get("parawise") or spec.get("affidavit")):
        return []
    n = spec.get("note") if isinstance(spec.get("note"), dict) else {}
    paras = n.get("paras") if isinstance(n.get("paras"), list) else []
    idx = [i for i, x in enumerate(paras) if isinstance(x, str) and x.strip()]
    W = []
    if not idx or not RESP_RE.search(unquoted(paras[idx[0]])):
        W.append(f"note.paras[{idx[0] if idx else 0}]: court note para 2 — the petition and its respondents in order in "
                 f"flowing sentences ('… यांना प्रतिवादी क्र. 1, … यांना प्रतिवादी क्र. 2 … करण्यात आले आहे (पृ.N/प.वि.).'; "
                 f"§4.32(अ))")
    if not spec.get("parawise"):
        return W   # affidavit stage: the prayers were tabled in the earlier parawise note (para 3 checked with "parawise")
    ok3 = False
    if len(idx) > 1 and PRAYER_HEAD_RE.search(unquoted(paras[idx[1]])):
        sub = n.get("sub") if isinstance(n.get("sub"), dict) else {}
        nxt = paras[idx[1] + 1] if idx[1] + 1 < len(paras) else None
        hdr = nxt.get("table")[0] if isinstance(nxt, dict) and isinstance(nxt.get("table"), list) and nxt["table"] \
            and isinstance(nxt["table"][0], list) else []
        tail = unquoted(paras[idx[1]]).split(":-", 1)[-1] if ":-" in paras[idx[1]] else ""
        ok3 = bool([t for t in sub.get(str(idx[1]), []) if isinstance(t, str) and t.strip()]) \
            or bool(SUBPOINT_RE.search(tail)) or any(isinstance(c, str) and "प्रार्थना" in c for c in hdr)
    if not ok3:
        W.append(f"note.paras[{idx[1] if len(idx) > 1 else 1}]: court note para 3 — 'सदर याचिकेद्वारे याचिकाकर्त्यांनी "
                 f"पुढीलप्रमाणे प्रमुख मागण्या केल्या आहेत (पृ.N/प.वि.):-' + the prayers as sub-points '(अ) …; (आ) …' "
                 f"(§4.32(आ), §4.37)")
    return W


# Q-F12 (WARN, §4.35): the joint affidavit is on behalf of the State respondents only — the High Court Registry
# (महाप्रबंधक / प्रबंधक / Registrar) is not part of it: no remarks on its behalf, no copy of the GP letter to it
REGISTRY_RE = re.compile(r"महाप्रबंधक|प्रबंधक|निबंधक|Registrar|High\s+Court|उच्च\s+न्यायालय", re.I)
REGISTRY_MSG = ("the High Court Registry (महाप्रबंधक / प्रबंधक / Registrar) is not part of the State's joint affidavit — "
                "nothing on its behalf, no copy to it (§4.35)")


def registry_hits(text, copy_line=False):
    """True when text names the High Court Registry; in a copy line a "… सरकारी वकील, उच्च न्यायालय" address is not it."""
    t = unquoted(text or "")
    if copy_line and "वकील" in t and not re.search(r"महाप्रबंधक|प्रबंधक|निबंधक|Registrar", t, re.I):
        return False
    return bool(REGISTRY_RE.search(t))


def gp_letter_copy_warnings(spec):
    """§4.35: a letter to the Government Pleader (letter.to names a "वकील") — no copy to the High Court Registry."""
    W = []
    for lp, L in letters_of(spec):
        if not isinstance(L, dict) or "वकील" not in " ".join(x for x in (L.get("to") or []) if isinstance(x, str)):
            continue
        for i, c in enumerate(L.get("copies") or []):
            if isinstance(c, str) and registry_hits(c, copy_line=True):
                W.append(f"{lp}.copies[{i}]: {REGISTRY_MSG}")
    return W


# Q-F19 (WARN, §4.30(3)): the demand in one short sentence right after para 1 — para 1 or 2 (court note: para 3, the
# prayers) names it. Low-noise keyword test.
DEMAND_RE = re.compile(r"मागणी|मागण्या|मागितल|विनंती|अनुतोष|शिफारस|याचिका|प्रश्न"
                       r"|सादर\s+(?:केला|केली|केले|केलेला|केलेली|करण्यात)"
                       r"|(?:करण्या|मिळण्या|देण्या|ठेवण्या)(?:बाबत|ची|चा|चे|स)(?![ऀ-ॿ])")

INCOMING_RE = re.compile(r"पत्रां?स|पत्रासोबत|पत्रान्वये|निवेदन|अर्ज|याचिका|नोटी[सश]")


def demand_warnings(spec):
    n = spec.get("note") if isinstance(spec, dict) and isinstance(spec.get("note"), dict) else None
    if n is None:
        return []
    paras = n.get("paras") if isinstance(n.get("paras"), list) else []
    idx = [i for i, x in enumerate(paras) if isinstance(x, str) and x.strip()]
    court = bool(spec.get("parawise") or spec.get("affidavit"))
    if not court and not INCOMING_RE.search(unquoted(n.get("first") or "")):
        return []   # the department's own initiative (a GR to endorse, an office order): no one asks anything
    look = [n.get("first") or ""] + [paras[i] for i in idx[:2 if court else 1]]
    if any(DEMAND_RE.search(unquoted(t)) for t in look if isinstance(t, str)):
        return []
    return [f"note.paras[{idx[0] if idx else 0}]: demand — give the demand in one short sentence right after para 1 "
            f"(who asks what; §4.30(3))"]


# Q-F21 (WARN): the precedent library is an internal working collection — a related source names the office record
# (C R no. / letter no. and date), not "पूर्वोदाहरण-ग्रंथालय" (§4.4 "स्वतःच्या मनाने काम करू नये"; INSTRUCTIONS §7.1)
LIBRARY_RE = re.compile(r"पूर्वोदाहरण\s*-?\s*ग्रंथालय|precedent[\s-]*library", re.I)


def library_ref_warnings(spec):
    W = []
    for i, it in enumerate((spec or {}).get("related") or []):
        if not isinstance(it, dict):
            continue
        for k in ("heading", "source"):
            if isinstance(it.get(k), str) and LIBRARY_RE.search(it[k]):
                W.append(f"related[{i}].{k}: 'पूर्वोदाहरण-ग्रंथालय' — name the office record (C R / letter no., date), "
                         f"not the internal library (§4.4)")
    return W


def lint_warnings(spec):
    """WARN-level findings "<JSON path>: <message>" (note body and letter outside quotes); never errors."""
    if not isinstance(spec, dict) or not isinstance(spec.get("note"), dict):
        return []
    n = spec["note"]
    body = [x for k in ("first", "paras", "sub", "closing") if k in n for x in strings(n[k], f"note.{k}")]
    letter = letter_strings(spec)
    W = [f"{path}: {m}" for path, t in body + letter for m in warn_hits(t)]
    W += missing_scatter(note_seq(n))[1]   # §4.31 placement
    W += missing_inline_problems(n)[1]   # C2 (05.11.2026): a table after the missing-info para
    for path, t in body:   # 05.11.2026: the old opener is no longer used
        if MISSING_OLD_RE.match(ns(unquoted(t))):
            W.append(f"{path}: missing-info para — {MISSING_OLD_MSG}")
    for path, t in body:   # Abhi 05.11.2026: a U.O. ref no. only when the record has one — never a "____" placeholder
        if UO_BLANK_RE.search(unquoted(t)):
            W.append(f"{path}: blank U.O. reference no. — {UO_BLANK_MSG}")
    for path, t in body + letter_strings(spec):   # Abhi 05.11.2026: "रिट याचिका क्र. N/YYYY" — no "(लॉजिंग)"
        if "लॉजिंग" in unquoted(t):
            W.append(f"{path}: 'लॉजिंग' — "
                     f"फक्त 'रिट याचिका क्र. <N>/<YYYY>' (वापरकर्ता, 05.11.2026, §4.32(अ))")
    rel_txt = [(pth, t) for pth, t in strings(spec.get("related", []), "related") if re.search(r"\.text(\[|$)", pth)]
    W += flow_warnings(note_seq(n), note_tables(n), rel_txt)   # C32 §4.34 relevance + flow
    W += [f"{last_para(n)[0]}: last para — does not name the draft {d} (§4.28: name every draft made, e.g. "
          f"'पत्राचे प्रारूप व शासन निर्णयाचे प्रारूप पृ.      /प.वि. वर मान्यतेस्तव सादर.')" for d in drafts_unnamed(spec)]
    # §4.37 (05.11.2026, D1/D3/D4): descriptive tables, numbered-para count, para 2 opener
    W += table_shape_warnings(note_table_rows(n))
    W += para_count_warnings(n)
    W += para2_warnings(spec)
    # audit 05.11.2026: Q-F9 long sentences, Q-F11 court para 2/3, Q-F12 registry copies, Q-F19 demand, Q-F21 library refs
    own = [(p, t) for p, t in body if not re.search(r"\.table\[", p)]
    own += [(p, t) for p, t in letter if re.match(r"letters?(?:\[\d+\])?\.(?:intro|points\[\d+\]|closing|body\[\d+\])$", p)]
    W += long_sentence_warnings(own)
    W += court_shape_warnings(spec)
    W += gp_letter_copy_warnings(spec)
    W += demand_warnings(spec)
    W += library_ref_warnings(spec)
    return W


def lint_study(study, pages=None, allow_missing_part1=False):
    P = []
    if not isinstance(study, dict) or not isinstance(study.get("parts"), list):
        return ["study.parts: structure — study has no 'parts' list"]
    have = set()
    for i, part in enumerate(study["parts"]):
        h = part.get("heading") if isinstance(part, dict) else None
        k = part_no(h) if isinstance(h, str) else None
        if k is None:
            P.append(f"study.parts[{i}].heading: study heading — not 'भाग N …': '{h}'")
        else:
            have.add(k)
    P += [f"study.parts: study headings भाग 0-7 — {x}" for x in heading_problems(have, (1,) if allow_missing_part1 else ())]
    for path, t in strings(study, "study"):
        for x in id_hits(t): P.append(f"{path}: internal id — '{x}'")
        P += [f"{path}: पृ. reference — {x.split(': ', 1)[1]}" for x in ref_problems(t, pages, path, skip_quotes=True)]
    return P


# spec key -> tools/<module>.py, error function, optional WARN-level function names
EXTRA_LINTS = ((("order", "orders"), "lint_order", ("lint_order_warnings", "warnings_order")),   # "orders": §4.28
               (("parawise",), "lint_parawise", ("warnings_parawise", "lint_parawise_warnings")),
               (("affidavit",), "lint_affidavit", ("warnings_affidavit",)),   # 04.11.2026: tools/build_affidavit.py
               (("lq",), "lint_lq", ("warnings_lq",)))                       # 04.11.2026: tools/build_lq.py
_IN_EXTRA = []


def lint_extras(spec):
    """(problems, warnings) of tools/lint_order.py / tools/lint_parawise.py for the optional spec keys "order" /
    "parawise". Imported lazily: a missing module or a crash is a warning, never an error. Re-entry guard (a module
    that calls lint_spec back must not loop)."""
    probs, warns = [], []
    if not isinstance(spec, dict) or _IN_EXTRA:
        return probs, warns
    import importlib
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    _IN_EXTRA.append(1)
    try:
        for keys, mod, wnames in EXTRA_LINTS:
            keys = (keys,) if isinstance(keys, str) else keys   # one key or a tuple of keys
            if all(spec.get(k) in (None, "", [], {}) for k in keys):
                continue
            key = "/".join(k for k in keys if spec.get(k) not in (None, "", [], {}))
            try:
                module = importlib.import_module(mod)
                fn = getattr(module, mod)
            except Exception as e:
                warns.append(f"{key}: tools/{mod}.py not available — '{key}' not linted ({str(e)[:80]})"); continue
            try:
                res = fn(spec)
            except Exception as e:
                probs.append(f"{key}: {mod} — crashed: {str(e)[:160]}"); continue
            if isinstance(res, tuple) and len(res) == 2 and all(isinstance(x, (list, tuple)) for x in res):
                res, w = res; warns += [str(x) for x in w]
            if isinstance(res, str):
                res = [res]
            probs += [str(x) for x in (res or [])]
            wf = next((getattr(module, n) for n in wnames if callable(getattr(module, n, None))), None)
            if wf is not None:
                try:
                    warns += [str(x) for x in (wf(spec) or [])]
                except Exception as e:
                    warns.append(f"{key}: {wf.__name__} — crashed: {str(e)[:120]}")
    finally:
        _IN_EXTRA.pop()
    return probs, warns


# ---------------- audit 05.11.2026 S-F3: no case text in CI logs ----------------
# With a details file (--details FILE, or env CASE_DETAILS_FILE), the full lines (quote text, subjects, ref nos.) are
# appended to that file and stdout gets the same lines with every quoted segment ('…', “…”, ‘…’) replaced by its length
# "'<N ch>'" — check names, JSON paths, block / page numbers and counts stay. Without one, output is unchanged (local use,
# the engine's own repair loop). Shared by lint_spec, lint_parawise, lint_affidavit, verify_outputs, extract_check.
DETAILS_ENV = "CASE_DETAILS_FILE"
_DETAILS = []
REDACT_RE = re.compile(r"'[^'\n]*'|“[^”\n]*”|‘[^’\n]*’")


def redact(line):
    """line with each quoted segment replaced by its length (S-F3)."""
    return REDACT_RE.sub(lambda m: f"'<{len(m.group(0)) - 2} ch>'", str(line))


def details_arg(argv):
    """Remove "--details FILE" from argv (a list, changed in place); -> the file (argv, else env CASE_DETAILS_FILE) or None."""
    path = None
    while "--details" in argv:
        i = argv.index("--details")
        path = argv[i + 1] if i + 1 < len(argv) else None
        del argv[i:i + 2]
    return path or _os.environ.get(DETAILS_ENV) or None


def set_details(path, tool=""):
    """Start redacted output: full lines go to `path` (appended; a header line names the tool)."""
    del _DETAILS[:]
    if path:
        _DETAILS.append(path)
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"== {tool}\n")
        except OSError as e:
            print(f"details file not writable ({e.__class__.__name__}) — output redacted only", file=sys.stderr)


def details_active():
    return bool(_DETAILS)


def out(line, shown=None):
    """Print one output line: the full line, or (details file active) `shown` / redact(line) on stdout and the full line
    into the file."""
    if not _DETAILS:
        print(line); return
    try:
        with open(_DETAILS[0], "a", encoding="utf-8") as f:
            f.write(str(line) + "\n")
    except OSError:
        pass
    print(shown if shown is not None else redact(line))



def load(path):
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def main(argv):
    args = argv[1:]
    set_details(details_arg(args), "lint_spec " + " ".join(args))   # S-F3
    spec_path = study_path = None; pages = None; allow1 = False
    try:
        while args:
            a = args.pop(0)
            if a == "--study": study_path = args.pop(0)
            elif a == "--pages": pages = int(args.pop(0))
            elif a == "--allow-missing-part1": allow1 = True
            elif a.startswith("--") or spec_path is not None: raise ValueError(a)
            else: spec_path = a
    except (IndexError, ValueError):
        print(__doc__); return 2
    if spec_path is None:
        print(__doc__); return 2
    probs = []; warns = []
    if spec_path not in (None, "-"):
        try:
            warns = lint_warnings(load(spec_path))
        except Exception:
            warns = []   # the JSON error is reported below
    def spec_lint(o):
        p = lint_spec(o, pages)
        xp, xw = lint_extras(o)
        warns.extend(xw)
        return p + xp
    for path, fn in ((spec_path if spec_path != "-" else None, spec_lint),
                     (study_path, lambda o: lint_study(o, pages, allow1))):
        if path is None:
            continue
        try:
            obj = load(path)
        except Exception as e:
            probs.append(f"{path}: JSON — {e}"); continue
        probs += fn(obj)
    for p in probs:
        out(p)
    for w in warns:
        out("WARN " + w)
    if not probs:
        print("LINT OK")
    return 1 if probs else 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main(sys.argv))
