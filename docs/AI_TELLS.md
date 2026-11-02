# AI_TELLS — engine drafts compared with the Section's own notes and letters (research only, 02.11.2026)

## Data and method
- **Ours.** We built six samples with `tools/build_note_letter.py`: CR66, 122, 128, 130, 131 and 133 of 2026. The outputs are in `scratchpad/aitells/CR*/`. Each was split into three parts: the note body (up to "संबंधित माहिती"), the related block ("संबंधित माहिती (संदर्भासाठी)") and the letter. The letter part covers 5 letters, because CR66 has no letter. The six note bodies hold 3,827 words (2,914 after quotes are removed).
- **Office.** These are the .docx files in the seven `सन … प्रकरणे.zip` archives. They were de-duplicated by text, which left 183 docs. The 77 note files have "Note/टिप्पणी/नोट" in the name (168,603 words). There are 90 letter parts: 76 letter files plus letters found inside other files (57,526 words).
- **Cross-check.** `Medical bill notes and draft.zip` holds 47 more office docx files. They were checked only for "—", "–", ";", "→", "स्रोत" and "जसाच्या तसा".
- **Scripts.** The scripts are in `scratchpad/scripts/` (seg.py, metrics.py, fmt.py). Rates are per 1,000 words ("/1kw"). "x/77 docs" means x office note files contain the feature at least once.
- **Not used.** `precedent-library/` was not used as an office source. We built it ourselves, so it is not an office original.
- **Caveats.**
  - Office note files often hold several versions of a note, with pasted GR text. Their counts include some quoted text, unless "quotes removed" is stated.
  - Office alignment that is inherited from a style was not resolved. It shows as "None".
  - Sentence splitting is approximate, because of Marathi abbreviation dots.
- **Names.** Personal names from old cases are replaced by ____.

## A. The most visible tells (a senior reads them on paper)

| # | Feature | Ours (count / example) | Office (count / example, C R no.) | Recommendation |
|---|---|---|---|---|
| A1 | Em dash "—" | **73 in total.** Note bodies have 11 (5/6 docs), e.g. CR131 "(पृ.13/प.वि.; नियम 56 — पृ.12/प.वि.)" and CR128 "(… (प्र. क्र. 95) — पृ.20-21/प.वि.; दि. 11.01.2023 — …)". The related block has 61 (6/6 docs), e.g. every item heading "म.ना.से. (निवृत्तिवेतन) नियम, 1982 — नियम 10(1)". Letters have 1 (CR130 "(श्री. देशमुख — उमेदवार क्रमांक 45)"). | **0** in 77 notes and 90 letters. **0** in the 47 medical-zip docx. | Never put "—" in our own text. Use "," or ":-", or restructure the sentence, e.g. "नियम 56 (पृ.12/प.वि.)". Lint could flag "—" outside quotes. |
| A2 | Semicolon ";" in our own Marathi text | Note bodies: 21 (5.5/1kw, 6/6 docs). Examples: the inline list "उपलब्ध नाही:- (1) …; (2) …; (3) …" (4/6 docs) and "(पृ.8/प.वि.; शासन निर्णय पृ.19/प.वि.)". Letters: 7, e.g. CR131 list items "…आदेशाची प्रत;". Related block: 46. | Notes: 18 in total (0.1/1kw, 6/77 docs), almost all inside quoted English rule text, e.g. "Rules, 1981;". Letters: 3 (3/90). Office list items end with "." (331 in notes, 127 in letters) or ","; none ends with ";". Medical zip: 11 in 47k words. | Do not use ";" in our own Marathi text. Put list items on separate lines ("(1)\t…", ending with "." or ","), as in C R 6-2026 Note para 2 "(1)… (2)… (3)…". Note: the ";" list-ending in letters comes from the CR131 sample (§4.20). Abhi decides whether to change it to "." or ",". |
| A3 | Inline numbered list in one paragraph "(1)…; (2)…" | 4/6 notes (CR122, 128, 130, 133). | 0/77 notes. Office notes put each item on its own line ("(1)\t…", "१.\t…"). | Render the list as separate lines, or as a table only. |
| A4 | The same list given twice (inline para + table) | CR131: para 9 "उपलब्ध नाही:-" is followed by a 5-row table with the same items. CR122/128/130/133 have the inline list, and the letter repeats it as a table. | Not observed as a fixed pattern. Each office note gives the missing items once. | One form only in the note. |
| A5 | Explanatory meta-words in the related block | "स्रोत" 30 (6/6). "जसाच्या तसा" 14 (5/6). "पॅकेज PDF पृ." 27 (6/6). "पूर्वोदाहरण" 12 (4/6). "पूर्वोदाहरण-ग्रंथालय, संग्रह ०२" 5 (3/6). "उपलब्ध नाही — मागवावे" 5. "छापील पृ." 4. "टीप :" 3. "मूळ … उपलब्ध नाही" 15. "finance.maharashtra.gov.in" 1. "→" 5 (2/6). "नस्तीत दिसत नाही" 1. | "स्रोत", "जसाच्या तसा", "पॅकेज PDF", "पूर्वोदाहरण", "ग्रंथालय", "→": **0** in all 167 office parts. The heading "संबंधित माहिती (संदर्भासाठी)": **0/77**. "संदर्भासाठी" appears only as "…प्रत संदर्भासाठी जोडण्यात आली…". | The block itself is mandated (§4.4, §4.11), so this is Abhi's decision. If kept: remove the words "स्रोत:", "जसाच्या तसा", "पूर्वोदाहरण-ग्रंथालय / संग्रह", "→", "टीप", "मागवावे" and web addresses. Cite as the office does: "(वित्त विभाग, शासन निर्णय क्र.…, दि.…, परि.…, पृ.N/प.वि.)". The internal library name and status notes ("उपलब्ध नाही — मागवावे") belong in the Study file only. |
| A6 | Cross-reference from the note body to the related block | "(पृ.20/प.वि.; संबंधित माहिती अ.क्र.4)" in 3/6 notes (5 times). | 0/77. | Drop "संबंधित माहिती अ.क्र.N". Keep only "पृ.N/प.वि.". |
| A7 | How often page references appear | "पृ.N/प.वि." 7.55/1kw. "(पृ." 12.0/1kw. 6/6 docs. All counts exclude quotes. | 2.80/1kw and 3.07/1kw (64/77 and 39/77 docs). | Ours cite about 3–4 times as often. Give one reference per document at its first mention, not after every clause. |
| A8 | "पृ./प.वि." column in fact tables | 5 of 16 tables (CR122, 130 ×2, 131, 133), with "-" or "(अर्जात नमूद)" in the cells. | 1 of 137 tables (C R 104-2022: "पृष्ठ क्रमांक"). Office tables start "अ.क्र." (81), "Sr.No." (10), "अ. क्र." (4). | Drop the page column. Put the reference once in the sentence before the table. |
| A9 | Linking words (quotes removed) | "तथापि" 0, "परंतु" 0, "त्यानुषंगाने" 0, "त्यानुसार" 1 (1/6), "अनुषंगाने" 1/6, "पुढीलप्रमाणे" 0, "कृपया" 0, "तरी," 0. | "तथापि" 51/77. "परंतु" 39/77. "त्यानुषंगाने" 28/77. "त्यानुसार" 55/77. "अनुषंगाने" 72/77. "पुढीलप्रमाणे" 41/77. "कृपया (पहावे/पहावीत)" 45/77. "तरी," 25/77. | Our paragraphs read as unconnected fact lines. Allow these office connectives where facts follow from each other. This is language, not opinion, but it touches §4.18 "one point per sentence", so Abhi decides. |
| A10 | Signature line in the letter | "अवर सचिव ,महाराष्ट्र शासन" (space before the comma) in 5/5. This is mandated by §4.5. | "अवर सचिव, महाराष्ट्र शासन" 46 of 49 (24 have a double space before शासन). "अवर सचिव ,महाराष्ट्र शासन" 3 of 49. | Abhi decides. The office majority form is "अवर सचिव, महाराष्ट्र शासन". |
| A11 | Bold and centre on "विषय" / "संदर्भ" | Both lines fully bold and centred in 5/5 (§4.10). | "विषय": fully bold in 0 of ~141. Only the label is bold ("partbold") in 57. Explicitly centred in 47. "संदर्भ": fully bold in 0 and explicitly centred in 0. | A user rule (30.10.2026). Office practice is a bold label at most. Abhi decides. |
| A12 | Drafter's signature in the note | "का. अ. (श्रीम. कऱ्हाडे)" (§4.6). | 64/77 notes have "( ____ )" on one line and "कार्यासन अधिकारी" on the next. The short form is always "का.अ.(श्रीमती ____)" / "का.अ. (श्रीम.____)", with no space inside "का.अ." The spaced "का. अ." form: 0. The chain is "अ.स. (श्री.वडनेरकर)", with no space after "श्री." in 46/77 notes and a space in 16/77. "उ.वि.स.-नि-उ.स." / "उ.वि.स. नि.उ.स." | Abhi decides. At minimum use "का.अ." (no inner space), which matches all office short forms. |
| A13 | Copy line in letters | "प्रत : निवड नस्ती" (one line). | 7 single-line forms. Many lists: "प्रत :- १) … २) निवड नस्ती", with Devanagari numerals. | No change is required. When there are several copies, use the office form "१) … २) निवड नस्ती". |

## B. Rule-mandated differences (INSTRUCTIONS §4.18–4.25 follow GR 10.11.2022; office practice differs; listed for Abhi's decision only)

| # | Feature | Ours | Office | Note |
|---|---|---|---|---|
| B1 | ":-" vs ".:-" | ".:-" 0. ":-" 6.3/1kw (notes). | ".:-" 275 times in 58/77 notes and 49 in 38/90 letters. ":-" 524 (71/77). | Our form is correct per the GR, so ".:-" is not needed. Office "खालीलप्रमाणे आहे.:-" is common. |
| B2 | "करून / अनुसरून / प्रारूप" vs "करुन / अनुसरुन / प्रारुप" | करून 5, करुन 2. अनुसरून 6/6, अनुसरुन 0 (note). प्रारूप 5/6, प्रारुप 0. | करुन 358 (52/77) vs करून 215 (30/77). अनुसरुन 277 (68/77) vs अनुसरून 33 (21/77). प्रारुप 113 (59/77) vs प्रारूप 6 (5/77). "उपलब्ध करुन देण्या" 88 vs "करून" 3. | Office spells these mostly the old way; ours follows §4.19/§4.25. Keep (rule). |
| B3 | Space after abbreviation dots | "दि. 25.03.2026": spaced 89, unspaced 7. "श्री. X": 30 spaced, 0 unspaced. "मा. उच्च": 24 spaced, 5 unspaced. | "दि.30.10.2025" unspaced 1,826 vs spaced 175 (91% unspaced). "श्री.X" unspaced 1,377 vs spaced 321. "मा.उच्च" unspaced 678 vs spaced 241. "शासन निर्णय क्र." spaced 29 vs unspaced 12. | Ours follows the rule. Office mostly omits the space, which makes ours visibly "cleaner". Rule kept; Abhi decides. |
| B4 | Digits | Own text is all Latin digits (6/6 first+last paras). Devanagari appears only in quotes. | Own text often mixes scripts: first+last body para mixed in 48/77, Latin only in 26/77, e.g. "दि.१६.05.२०…", "२.\t", "१)". Para numbers: Latin "N." 596, Devanagari "N." 363. | Full consistency is itself unlike office text, but it is not wrong. Low priority. No change suggested. |
| B5 | Banned words | "दिसून येते" 0 (banned, SOP Step 4). | "दिसून येते" 76 times in 24/77 notes. | The office uses it often. The ban is the owner's rule; for information only. |
| B6 | Font | DVOT-SurekhMR in 6/6 (§4.2). | Dominant run font in office notes: Sakal Marathi 42/81, style default 22, DVOT-SurekhMR 3. In letters: style default 33, Sakal Marathi 23, DVOT-Surekh 9, DVOT-SurekhMR 3. | A user rule; for information. |
| B7 | Letterhead e-mail | lnjd.desk6-mh@mah.gov.in (§4.5). | "<user>@nic.in" 126 times vs the desk address 2. | A user rule; for information. |

## C. Features where ours already matches the office (not tells; numbers for the record)

| Feature | Ours | Office |
|---|---|---|
| Sentence length (quotes collapsed; approximate) | Note: median 20, mean 24.8, p90 48 words. Letter: median 11. | Note: median 20, mean 24.1, p90 46. Letter: median 10. |
| Body paragraph length | Median 35 words, mean 42. | Median 34 words, mean 41.8. |
| Curly quotes “ ” | 12/1kw (5/6 docs). | 3.5/1kw (61/77). Straight " 1.9/1kw (35/77). Ours quote more often, as a direct result of §4.1 verbatim extracts. |
| Opening "…यांच्या पृ.N/प.वि. वरील … पत्रास अनुसरून सादर." | 4/6, with all 6 ending "…अनुसरून सादर.". | 28/77 end "…अनुसरुन सादर.". Other office openings: "…पत्र कृपया पहावे/पहावा/पहावीत." (≈13), "…विचाराधीन आहे." (≈6), "…अवलोकन व्हावे." (1). A uniform opening is not a tell, but the office varies it. |
| Closing "…कळविण्याबाबतच्या पत्राचे प्रारूप पृ.      /प.वि. वर मान्यतेस्तव सादर. मान्य झाल्यास पत्र निर्गमित करण्यात येईल." | 5/5 information notes. | "कळविण्याबाबतच्या पत्राचे प्रारुप" 53 times. "मान्य झाल्यास पत्र निर्गमित" 17. "मान्यतेनंतर पत्र निर्गमित" 28. A blank "पृ.      /प.वि." is common in office notes (≈30+). |
| "सदर", "उपरोक्त" | 5.0 and 1.3/1kw. | 7.3 and 2.3/1kw. Same register. |
| Tables | 16 tables, all headed "अ.क्र.", median 6 rows. | 137 tables in 39/77 notes and 21/90 letters. "अ.क्र." heads 81. Median 6 rows. |
| Letter opening | "उपरोक्त विषयाबाबत संदर्भाधीन पत्रास अनुसरून आपणांस कळविण्यात येते की, …" | "उपरोक्त विषयाबाबत, संदर्भाधीन पत्रास अनुसरुन आपणांस…" 14. "…आपल्या संदर्भाधीन पत्रातील विनंतीनुसार" 31. |
| "विषय :-" / "संदर्भ :-" label spacing | "विषय :-" | "विषय :-" 126, "विषय:-" 20. "संदर्भ :-" 42, "संदर्भ:-" 21. |
| Header line | "विधि व न्याय विभाग/का.6" | 13 identical. Variants: "… / का.6" 15, "…/का-6" 14, "वि.व न्या.वि./का.६" 14. |
| "होय/नाही" column in the letter table | CR131 letter row 4 "(होय/नाही)". | 0 in the office corpus ("किंवा कसे" is used instead: 14/90 letters). Minor; "किंवा कसे" alone is the office form. |

## D. File and metadata tells (visible in Word File → Info / Properties, or on forensic inspection)

| # | Feature | Ours (6/6 identical) | Office | Recommendation |
|---|---|---|---|---|
| D1 | Author / Last modified by (core.xml) | Both empty. | Both set in 162/162 office docx (names not reported). | Set them on build. The value is Abhi's choice (e.g. the desk's usual account name); do not invent one. |
| D2 | Created / Modified / Revision / TotalTime | All six identical, copied from the template: created 2025-05-06T06:20Z, modified 2026-07-16T07:25Z, revision 16, TotalTime 247 min, lastPrinted 2025-08-11. | Different per file. Revision median 94 (notes) and 37 (letters). | Set created and modified to the build time. Reset revision and TotalTime, or remove them. |
| D3 | app.xml statistics | Pages=1, Words=1056, Paragraphs=14 in all 6 (stale; the real notes are 2–4 pages). | Updated by Word (Application "Microsoft Office Word", AppVersion 14.0000 in 151/162, 15.0000 in 11). | Remove or recompute Pages/Words/Lines, or let LibreOffice/Word re-save. |
| D4 | XML declaration style | `<?xml version='1.0' …?>` (single quotes, lxml/python-docx) in core.xml and document.xml, 6/6. | Double quotes in 162/162 (Word). | Forensic only. A re-save in Word or LibreOffice normalises it. |
| D5 | rsid attributes on paragraphs | 35–58% of paragraphs (median 54%). Only the template's paragraphs carry them; generated ones have none. | 100% of paragraphs in 162/162. | Forensic only. Disappears after a re-save in Word (uncertain for LibreOffice). |
| D6 | Word auto-numbering (numPr) | 0 docs. | 69/81 notes and 31/81 letters use numPr somewhere (28% of note paragraphs). Manual "2.\t" is also common. | Low priority. Not visible on paper. |
| D7 | Italic / underline | Italic 0. Underline only in the template parts. | Italic in 38/81 notes, underline in 80/81 notes (e.g. "विषय" / headings). | Low priority. No change suggested without Abhi's word. |

## Uncertain / not measured
- Office notes include senior remarks and pasted GR text. So the frequencies of "हरकत नसावी" (36/77), "मान्यतेनंतर" (35/77) and "पूर्वपृष्ठावरील" (33/77) may partly reflect later-stage notes, not first notes. Our six are all first notes.
- Paragraph alignment inherited from styles was not resolved for office files.
- The rsid/XML-declaration tells are only visible to someone opening the docx internals. Their effect after Abhi edits and re-saves in Word was not tested.
