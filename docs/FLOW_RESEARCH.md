# FLOW_RESEARCH — टिप्पणीचा ओघ: कार्यासनाच्या जुन्या टिप्पण्यांतील परिच्छेद व वाक्य जोडणी (research only, 05.11.2026)

Abhi (05.11.2026): "टिप्पणीचा ओघ तुटतो … टिप्पणीचा ओघ तुटू नये अशी वाक्यरचना जोडविण्यासाठी प्रयत्न करा".
This file only reports what the Section's own old notes and the GAD manuals show. No rule is changed here. Personal
names from old files and from our samples are replaced by "____".

## 0. स्रोत व पद्धत (data and method)
- **Office notes.** `python3 tools/oldcases_text.py /tmp/old` (193 docx from the seven "सन … प्रकरणे.zip"). 82 files have
  Note / टिप्पणी / नोट in the name; 78 are distinct texts. Inside them the actual office note was cut out as a "block":
  from the opening line ("… अनुसरुन सादर." / "… कृपया पहावे." / "… विचाराधीन आहे.") to "कार्यासन अधिकारी".
  This gave **117 note blocks from 56 C R files** (1,689 own-text paragraphs, quoted lines and table rows left out).
  The table lead-in / lead-out was read again from the docx in body order (python-docx; `oldcases_text.py` puts tables at
  the end): **74 distinct tables** in note files.
- **Read in full** (every paragraph): C R 309-2024, 203-2024, 220-2024, 261-2024, 205-2024, 16-2026, 2-2026, 38-2026,
  6-2026 (part). The others were read through the counts and the 2–3 examples printed per phrase.
- **Counting.** "n / k CR" = n occurrences in k C R files (note blocks only, unless "corpus" is written = all 193 docx,
  letters included). "Sentence-initial" = at the start of a paragraph or after ". " / ":-". Word-boundary matching
  (so "करण्याबाबत" is not counted as "याबाबत").
- **Caveat — template families.** Some notes are copies of one model: C R 220/221/222/223/224-2024 (old pension,
  compassionate); C R 205-2024 / 138-2025 / 45-2026 / 23-2026 / 6-2026 (bailiff pay); C R 225/226-2024 / 38-2026; C R
  261/281/306-2024. A phrase found only in one family is marked "(one family)".
- **Manuals.** GADT = सा.प्र.वि., "टिप्पणी लेखन व पत्रव्यवहार" (`pdf/08-gad-office-procedure/GAD_Tippani-Lekhan-va-Patravyavahar-Marathi.pdf`;
  legacy font, so PDF p.9–19 were rendered at 200 dpi and OCR-read with `tesseract -l mar`; book p. = PDF p. − 4).
  MMOP = Maharashtra Manual of Office Procedures 2023 (`GAD_Maharashtra-Office-Procedure-Manual-2023-English.pdf`, text layer).
  docs/STYLE_RESEARCH.md S1 already covers MMOP §8.1/8.2/8.18; the paras used here are listed in §5.
- **Our samples.** `samples/specs/*.json` note paras (CR66, 122, 128, 130, 131, 133, HTE, WP35697 ×2, COURT_*).

## 1. घटकनिहाय परिच्छेद-प्रारंभ (paragraph openers by note element)

The most frequent paragraph openers in the 117 blocks (own text, sentence-initial): उपरोक्त 83 / 37 CR; सदर 78 / 33;
सबब 59 / 34; तसेच 53 / 21; तथापि 50 / 30; "सदर प्रस्ताव…" 45 / 22; तद्नंतर 26 / 13; वरील 26 / 14; त्यानुसार 26 / 18;
त्यानुषंगाने 25 / 13; "सदर पत्रान्वये" 20 / 17; मान्यतेनंतर 19 / 14; "उपरोक्त प्रस्तावाच्या (अनुषंगाने)" 17 / 16;
"उपरोक्त पत्रान्वये" 13 / 12; "सदर प्रकरणी" 14 / 7; "प्रस्तुत प्रकरणी" 13 / 6; उक्त 11 / 6; परंतु 9 / 7; दरम्यान 8 / 6;
"त्यास अनुसरुन" 6 / 5; याबाबत 4 / 2 (as a paragraph opener; inside sentences 27 / 9); "यासंदर्भात" 1 / 1; मात्र 1 / 1.

| घटक (element) | Opener phrases actually used (count) | Source refs |
|---|---|---|
| परि. 1 (reference) | "<प्राधिकारी> यांच्या पृ.N/प.वि. वरील पत्रास अनुसरुन सादर." (most); "<प्राधिकारी> यांचे दि. __ रोजीचे पत्र कृपया पहावे." (29 / 19 CR "कृपया पहाव…"); returned file: "पूर्वपृष्ठावरील वित्त विभागाच्या अभिप्रायास / टिप्पणीस अनुसरुन सादर." (30 / 23 CR "पूर्वपृष्ठावरील") | C R 220-2024, 2-2026; C R 49-2024, 16-2026; C R 261-2024, 135-2024 |
| परि. 2 — मागणी | "सदर पत्रान्वये <कोण> यांनी … विनंती केली आहे / … प्रस्ताव सादर करण्यात आला आहे." (22 / 17 CR); "उपरोक्त पत्रान्वये …" (13 / 12); then it opens the facts in the same para: "याबाबतची वस्तुस्थिती पुढीलप्रमाणे आहे:-", "सदर पत्रात नमूद केलेल्या बाबी खालीलप्रमाणे आहेत.", "सदर प्रस्तावात खालीलप्रमाणे नमूद करण्यात आले आहे:-" | C R 261-2024, 203-2024, 2-2026; C R 220-2024, 16-2026; C R 6-2026, 16-2026, 203-2024 |
| पार्श्वभूमी / सेवातपशील | Lead-in names the subject and the content: "<व्यक्ती> यांचा सेवा तपशील खालीलप्रमाणे आहे:-", "… यांचा शासकीय सेवेत अनुकंपा तत्वावर नियुक्ती झाल्याचा तपशील खालीलप्रमाणे आहे:-", "… संपूर्ण सेवा तपशील तक्ता स्वरुपात पुढीलप्रमाणे आहे:-" (14 of 74 table lead-ins contain "तपशील") | C R 136-2024, 220-2024 (one family), 170-2022, 85-2023 |
| प्रश्न / आक्षेप | "तथापि, <प्राधिकारी> यांनी उपस्थित केलेल्या आक्षेपानुसार …"; "परंतु, दि. __ रोजी सदर देयक खालील प्रमाणे आक्षेप लावून परत केले."; "<वेतन पडताळणी पथकाने>, “…” असे आक्षेप नोंदविले" (6 / 3 CR, one family) | C R 16-2026; C R 261-2024; C R 225-2024 |
| प्रत्येक प्राधिकाऱ्याचे पत्र | Chain words, each sentence with its own subject: "<A> यांच्या विनंती अर्जाच्या अनुषंगाने <B> यांनी त्यांच्या दि. __ च्या पत्रान्वये …"; "त्यानुसार <C> यांनी त्यांच्या दि. __ च्या पत्रान्वये …"; "त्यानुषंगाने मा. उच्च न्यायालय … यांनी …"; "सदर पत्रास अनुसरून <D> यांचे दि. __ रोजीचे पत्र दि. __ रोजी या कार्यालयास प्राप्त झाले. त्यांच्या पत्रात खालीलप्रमाणे नमुद करण्यात आले आहे:-" ("त्यांच्या पत्रात" 8 / 3 CR) | C R 16-2026; C R 261-2024 (one family) |
| GR / तरतूद | Group lead-in, then one sub-point per GR in date order: "उपरोक्त प्रस्तावाच्या अनुषंगाने खालीलप्रमाणे नमूद करण्यात येत आहे:-" → "(अ) सामान्य प्रशासन विभाग … वेळोवेळी शासन निर्णय निर्गमित करण्यात आले आहेत. त्यानुसार -" → "दिनांक __ च्या शासन निर्णयात …" / "दिनांक __ च्या शासन निर्णयात दिनांक __ चा शासन निर्णय अधिक्रमित करण्यात आला असून …". Other openers: "या प्रकरणी <विभाग> च्या दिनांक __ रोजीच्या शासन परिपत्रकातील बाब क्रमांक __ …" ("या प्रकरणी" 17 / 10 CR); "उपरोक्त संदर्भात शासन निर्णय दि. __ मधील परिच्छेद __ नुसार …" (4 / 3); "उपरोक्त बाबींस अनुसरून, शा.नि. क्र. __ अन्वये …" (3 / 3, one family); "तसेच सदर अधिसूचनेनुसार …" (3 / 3); "त्यानुषंगाने नमूद करण्यात येते की, …" (10 / 5 CR) | C R 16-2026; C R 2-2026; C R 261-2024; C R 205-2024; C R 250-2024, 28-2025, 52-2025 |
| अट → तथ्य (condition lead-in) | Provision, then its condition, then the fact, each one sentence, linked: "सदर शासन परिपत्रकाच्या बाब क्रमांक १ अन्वये …" → "वरील अटीनुसार … सेवा पूर्ण होणे आवश्यक आहे." → "परंतु, सदर प्रकरणात … दि. __ रोजी …" → "त्यानुसार <व्यक्ती> यांनी __ वर्ष, __ महिने एवढी सेवा केलेली आहे." No "अट / प्रस्तावातील स्थिती" table in any office note ("प्रस्तावातील स्थिती": corpus 0) | C R 2-2026 |
| कालक्रम (chronology) | "तद्नंतर" 36 sentence-initial / 18 CR (the office's main word); "त्यानंतर" 20 / 9; "दरम्यान" / "दरम्यानच्या काळात / कालावधीत" 15 / 9; "पुढे" 0 sentence-initial; dates open the sentence: "दि. __ रोजी …" | C R 16-2026, 261-2024, 38-2026; C R 13-2024, 153-2024; C R 170-2022, 220-2023 |
| वित्त / सा.प्र.वि. चे पूर्वीचे अभिप्राय | "उपरोक्त प्रस्तावाच्या अनुषंगाने वित्त विभागाने (सामान्य प्रशासन विभागाने) याच विषयावरील अन्य नस्ती क्र. __ मध्ये पुढीलप्रमाणे अभिप्राय दिले आहेत:- (पृ.N/प.वि.)" (12 / 11 CR "याच विषयावरील अन्य नस्ती"); a contrast is opened with "तथापि, उपरोक्त प्रस्तावाच्या अनुषंगाने …" (5 / 5, one family). Lead-in endings "खालीलप्रमाणे अभिप्राय दिले आहेत:-" are the commonest group lead-in (14 numbered paras); lead-out "उपरोक्त प्रमाणे वित्त विभागाने दिलेल्या “…” या अभिप्रायास अनुसरुन …" (3 / 3) | C R 202-2024, 220-2024, 205-2024; C R 225-2024, 38-2026 |
| "उपरोक्त वस्तुस्थिती" | **"उपरोक्त वस्तुस्थिती पुढीलप्रमाणे आहे:-": 0 in the whole corpus.** "वस्तुस्थिती पुढीलप्रमाणे / खालीलप्रमाणे आहे:-" (13 + 5 corpus) always OPENS the facts, near para 2–3 ("सदर प्रकरणाची / प्रस्तावाची वस्तुस्थिती खालीलप्रमाणे आहे:-"). At the end the office writes "उपरोक्त (सर्व) वस्तुस्थिती विचारात घेता …" or "उपरोक्त परिच्छेद 3, 4 व 5 मधील वस्तुस्थिती विचारात घेता …" (34 hits / 21 files corpus) as the opening clause of the proposal / सबब para | C R 154-2022, 24-2022, 246-2024; C R 116-2021, 261-2024, 28-2025 |
| उपलब्ध नसलेली माहिती | "सदर प्रस्तावाची छाननी केली असता खालीलप्रमाणे त्रुटी आढळून आल्या आहेत." / "उपरोक्त प्रस्तावाची छाननी केली असता पुढील प्रमाणे त्रुटी आढळून येत आहे:-"; "वरील प्रस्तावास अनुसरुन … पुढील बाबींची पूर्तता करण्याबाबत <प्राधिकारी> यांना … कळविण्यास हरकत नसावी"; "उपरोक्त प्रस्तावाच्या अनुषंगाने <प्राधिकारी> यांना खालीलप्रमाणे माहिती उपलब्ध करुन देण्याबाबत … कळविण्यात यावे." ("माहिती उपलब्ध करुन देण्याबाबत" 11 / 6 CR). "…अवलोकन केले असता, त्यामध्ये खालील माहिती आढळून येत नाही:-" (our form): 0 such missing-info uses in office notes | C R 250-2024, 259-2024; C R 309-2024; C R 203-2024, 176-2024 |
| सबब | "सबब, …" 102 sentence-initial / 46 CR; "सबब, उपरोक्त सर्व / परिच्छेद __ मधील वस्तुस्थिती विचारात घेता …"; "सबब, वित्त विभागाने … नमूद केलेल्या …" (7 / 6); end lines "मान्यतेनंतर पत्र निर्गमित करण्यात येईल." (31 / 24 CR "मान्यतेनंतर") / "मान्य झाल्यास पत्र निर्गमित करण्यात येईल." (15 / 15) | C R 116-2021, 154-2022; C R 200-2024, 261-2024; C R 203-2024, 2-2026 |

Connectives inside paragraphs (sentence-initial, blocks): तसेच 161 / 36 CR; तथापि 102 / 37; त्यानुसार 100 / 34; त्यामुळे 84 / 36;
परंतु 54 / 25; त्यानुषंगाने 47 / 19; "त्यास अनुसरुन" 31 / 22; तद्नंतर 36 / 18; याबाबत 27 / 9; मात्र 17 / 8; "सदर प्रकरणी"
16 / 9; "प्रस्तुत प्रकरणी" 14 / 6; "त्याअनुषंगाने" 10 / 6; "यानुषंगाने" 7 / 7; "या अनुषंगाने" 7 / 3; "म्हणजेच" 7 / 6.

## 2. परिच्छेदातील वाक्य-जोडणी (sentence-level linking)

### 2.1 परिच्छेदांची रचना — कमी क्रमांकित परिच्छेद, आत उप-मुद्दे
- **Office:** a note block has a median of **5 numbered paragraphs** (mean 6.2; 110 blocks). Each numbered para is one
  theme. Under it come Word auto-numbered sub-points (median 9.5 lines per block; seen as `w:numPr` in C R 220-2024 and
  2-2026). **120 of 427 numbered paras (28 %)** end with a lead-in ":-" that opens such a group, e.g. "३. सदर प्रस्तावास
  अनुसरुन पुढीलप्रमाणे नमूद करण्यात येत आहे :-" (C R 220-2024), "3. उपरोक्त प्रस्तावाच्या अनुषंगाने खालीलप्रमाणे नमूद
  करण्यात येत आहे:-" (C R 16-2026), "6. सदर प्रकरणास अनुलक्षून पुढीलप्रमाणे नमूद करण्यात येत आहे :-" (C R 205-2024,
  one family).
- **Ours:** median **14 numbered paragraphs** (CR131 10, CR122 10, CR133 11, CR128 13, CR66 14, CR130 16, HTE 18,
  WP35697 21–23). One fact or one quote is often a whole numbered paragraph.
- This is the main structural difference. GADT 4.13(6) (book p.11) says "टिप्पणीला परिच्छेद असावेत व प्रत्येक परिच्छेद हा
  स्वतंत्र मुद्यासाठी असावा." — a मुद्दा = an issue (demand, background, provisions, earlier opinion), not each fact.
  GADT 4.14 (book p.12–13) gives the paragraph plan: (1) reference, (2) points raised and the question for decision,
  (3) rules for / against + earlier decisions, (4) financial burden + budget provision, (5) what is needed to dispose of
  the case, (6) other departments to consult.
- The share of numbered paras that open with a backward word (सदर / उपरोक्त / वरील / तसेच / तथापि / त्यानुसार …) is about
  the same: office 242 / 427 (57 %), ours 112 / 184 (61 %). So the choppy feel does not come from too few connectives
  alone; it comes from many short numbered paras that each restart with a full new subject.

### 2.2 एकच कर्ता पुढे नेणे (one subject carried forward)
Inside a group the office keeps the same subject and names it again in short form, not with a pronoun at the start:
"श्रीमती ____ … यांचा … तपशील खालीलप्रमाणे आहे:-" → "श्रीमती ____ यांचे पती श्री. ____ हे … कार्यरत होते." → "मयत श्री.
____ यांचे वारस म्हणून त्यांच्या पत्नी … यांना … नियुक्ती देण्यात आली." → "श्रीमती ____ यांनी … विनंती अर्ज सादर केले
असल्याचे पत्रात नमूद करण्यात आले आहे." (C R 220-2024). Sentence-initial "त्यांनी" is rare (5 / 3 CR), "त्यांच्या" 16 / 6;
"सदर कर्मचारी" 4 / 4; the possessive "त्यांच्या" inside the sentence is common (166 / 40 CR). Forms used: "श्री. ____ यांच्या
विनंती अर्जाच्या अनुषंगाने …", "सदर कर्मचारी श्री. ____, शिपाई यांनी …" (C R 16-2026, 203-2024).

### 2.3 उतारा कसा आणतात व नंतर कसा पुढे जातात (quote in / out)
- **Lead-in (paragraph before a quoted para):** "… खालीलप्रमाणे अभिप्राय दिले आहेत:-" (14 / 14 CR); "… नमुद करण्यात आले
  आहे:-" (12 / 3, one family); "… मुंबई यांना कळविले आहे:-" (4 / 2); "… खालीलप्रमाणे कथन केले आहे:-" (C R 125-2025).
  Corpus: "खालीलप्रमाणे नमूद" 24 files, "पुढीलप्रमाणे नमूद" 24 files, "असे नमूद करण्यात आले आहे" 15 files, "असे नमूद आहे"
  8 files, "अशी तरतूद आहे" 3 files; **"खालीलप्रमाणे तरतूद आहे" / "पुढीलप्रमाणे तरतूद आहे": 0 files** (ours: 7 times).
- **Inline:** "शासन निर्णय दिनांक __ च्या स्पष्टीकरणामधील मुद्दा क्र. 2 मध्ये असे नमुद करण्यात आले आहे की, “…”" (C R
  6-2026, 23-2026); "… “…” असे नमूद आहे." (C R 205-2024, 28-2025); "दि. __ च्या शासन निर्णयात “…”" (C R 16-2026).
- **Lead-out (the next sentence picks the quote up):** "बाब क्रमांक १२ अन्वये केलेली वरील तरतूद …" (C R 2-2026); "वरील
  अटीनुसार …" (C R 2-2026); "उपरोक्त संदर्भात शासन निर्णय दि. __ मधील परिच्छेद __ नुसार …" (C R 261-2024 family);
  "उपरोक्त प्रमाणे वित्त विभागाने दिलेल्या “…” या अभिप्रायास अनुसरुन …" (C R 225-2024 family); "सदर पत्रास अनुसरून …"
  (C R 261-2024). The quote is never the last thing before a new, unrelated subject.

### 2.4 तक्ता — आधीचे व नंतरचे वाक्य (table lead-in / lead-out; 74 tables)
- **Lead-in:** 57 / 74 end with ":-" (16 with "."). 38 / 74 name what the table holds (तपशील, माहिती, तक्ता, फरक,
  मुद्दे, आर्थिक भार, पदे, साखळी): "सदर दोन्ही कर्मचाऱ्यांचा सेवा तपशील पुढीलप्रमाणे आहे:-" (C R 183-2024), "त्याचा तुलनात्मक
  तक्ता खालीलप्रमाणे आहे:-" (C R 135-2024), "… करण्यासाठी येणारा आर्थिक भार खालील प्रमाणे आहे:-" (C R 28-2025). No
  table without a lead-in sentence was found.
- **Lead-out:** 38 / 71 paragraphs after a table open with a backward word: "वरील अधिकारी / कर्मचाऱ्यांना पदोन्नतीच्या पदावर
  …" (C R 136-2024); "सदर प्रकरणी उपरोक्त तक्त्यात दर्शविल्यानुसार …" (C R 8-2011); "वरील तक्त्यात दर्शविल्याप्रमाणे …"
  (C R 250-2024); "उपरोक्त तक्त्यातील अ.क्र. 4 व ५ च्या अनुषंगाने …" (C R 250-2024); "परि. ५ मधील वस्तुस्थितीच्या अनुषंगाने
  …" (C R 170-2022, 153-2024); "उपरोक्त प्रस्तावाच्या अनुषंगाने …" (C R 183-2024, 104-2022); "तद्नंतर, …" (C R 225-2024
  family); "तथापि, …" (C R 246-2024, 52-2025).

### 2.5 दिनांकांचा क्रम (dates in sequence)
C R 16-2026, para 2 (one theme, seven sub-points, each one step): "<A> … दि. __ रोजी सेवानिवृत्त होणार होते. परंतु, त्यांनी
… विनंती केली." → "श्री. ____ यांच्या विनंती अर्जाच्या अनुषंगाने <B> यांनी त्यांच्या दि. __ च्या पत्रान्वये …" →
"त्यानुसार <C> यांनी त्यांच्या दि. __ च्या पत्रान्वये …" → "त्यानुषंगाने मा. उच्च न्यायालय … यांनी त्यांच्या दि. __ च्या
पत्रान्वये …" → "तथापि, त्यावेळी … पदे रिक्त होती." → "तद्नंतर श्री. ____ हे दि. __ रोजी …" → "तथापि, <D> यांच्या
कार्यालयाने उपस्थित केलेल्या आक्षेपानुसार …". GADT 4.13(7) (book p.11): "घटनांचा उल्लेख कालानुक्रमाने करावा. असे न केल्यास
अर्थ समजणे कठीण जाते."

### 2.6 सावधानता (what NOT to copy from old notes)
Old notes also carry opinion links that our rules forbid (§1.1, SOP banned list): "दिसून येते" (76 in 24 / 77 notes per
docs/AI_TELLS.md B5), "अशा परिस्थितीत … होण्याची शक्यता असल्यामुळे" (C R 16-2026), "… विचारात घेता, … निर्णय … घेता येईल"
(C R 2-2026), "… पुन्हा वित्त विभागाचे अभिप्राय घेणे आवश्यक नाही" (C R 220-2024 family), "आवश्यकता आहे / उचित होईल".
Also ".:-" and "करुन / अनुसरुन" spellings (§4.19). Only the neutral link words are taken.

## 3. आपल्या नमुन्यांतील ओघ तुटण्याचे प्रकार (break types in our samples)

| # | Break type | Example (samples/specs; para no. = printed note para; names → ____) | Office practice |
|---|---|---|---|
| B1 | One fact = one numbered paragraph; each restarts with a full new subject | HTE paras 4–6 and 7–10: "शिवाजी विद्यापीठाच्या पृ.20-21/प.वि. वरील मान्यतेनुसार …", "रयत शिक्षण संस्थेच्या दि. 24.08.1994 च्या नियुक्ती आदेशातील …", "कै. ____ यांना करिअर प्रगती योजनेअंतर्गत …", then "विभागीय सहसंचालक …", "महालेखापाल …", "विभागीय सहसंचालक …", "श्रीमती ____ यांनी …" — 18 numbered paras | median 5 numbered paras, sub-points under a lead-in (§2.1) |
| B2 | Mechanical "<GR> च्या परिच्छेद N मध्ये" starts, one per para | CR130 paras 7–9: "याबाबत वित्त विभागाच्या … शासन निर्णयात “…”", "सदर शासन निर्णयाच्या परिच्छेद 2 मध्ये “…”", "सदर शासन निर्णयाच्या परिच्छेद 3 मध्ये “…”"; CR128 paras 6–7 the same; CR133 paras 5–7 "… नियम 30 (1) मध्ये …", "तसेच, नियम 30 (2) मध्ये …", "नियम 30 (3) मध्ये …". "सदर शासन निर्णयाच्या परिच्छेद" 11 times in the samples | one lead-in for the group, then sub-points; each sub-point linked to the last ("वरील अटीनुसार", "त्यानुसार") (C R 2-2026, 16-2026) |
| B3 | GR / rule paras dropped in with no link to the demand | CR131 paras 5–8: "वित्त विभाग, शासन निर्णय क्र. … च्या परिच्छेद 2 मध्ये खालीलप्रमाणे तरतूद आहे …" (no "याबाबत"), "विशेष वेतनाचा दर …", "म.ना.से. (वेतन) नियम, 1981 च्या नियम 57 (2) मध्ये “…” अशी तरतूद आहे"; CR66 para 9 "म.ना.से. (सुधारित वेतन) नियम, 2019 च्या अनुसूचीनुसार …" | "उपरोक्त प्रस्तावाच्या अनुषंगाने खालीलप्रमाणे नमूद करण्यात येत आहे:-" / "या प्रकरणी …" / "उपरोक्त संदर्भात …" (§1) |
| B4 | Quote with no subject, repeating an earlier para | CR131 para 4: "अर्जात (पृ.5/प.वि.) “प्रभारी अधिक्षक या पदाचे अतिरिक्त काम …” असे नमूद आहे." — para 2 already says the same in words | the quote carries its author ("<कोण> यांनी … खालीलप्रमाणे कथन केले आहे:-", C R 125-2025); a fact is said once (§4.34 (आ)) |
| B5 | "उपरोक्त वस्तुस्थिती पुढीलप्रमाणे आहे:-" appears abruptly after a condition table | CR122 para 8, CR128 11, CR130 14, CR133 9, CR66 12, HTE 16, WP35697 20 (10 in all samples) | phrase 0 in the corpus; office closes with "उपरोक्त (सर्व) वस्तुस्थिती विचारात घेता, …" as the start of the proposal / सबब para (§1) |
| B6 | Condition-table lead-in not in office language | "सदर तरतुदी व प्रस्तावातील स्थिती पुढीलप्रमाणे आहे:-" (CR122), "नियम 30 मधील अटी व प्रस्तावातील स्थिती पुढीलप्रमाणे आहे:-" (CR133) — 6 in samples | "प्रस्तावातील स्थिती" corpus 0; office states condition → fact in linked sentences (C R 2-2026) or a table whose lead-in names the content (§2.4) |
| B7 | "खालीलप्रमाणे / पुढीलप्रमाणे तरतूद आहे" + "अशी तरतूद आहे" pile-up | CR131 paras 5–6, CR122 para 5, CR133 para 5 ("… तरतूद आहे" 7; "अशी तरतूद आहे" 20 in samples) | corpus: "खालीलप्रमाणे तरतूद आहे" 0, "अशी तरतूद आहे" 3 files; "खालीलप्रमाणे नमूद (करण्यात आले) आहे" 24 + 24 files |
| B8 | Para 2 repeats the authority instead of picking up para 1 | CR131 para 2 "प्रमुख जिल्हा व सत्र न्यायाधीश, भंडारा यांनी …" right after para 1 "प्रमुख जिल्हा व सत्र न्यायाधीश, भंडारा यांच्या … पत्रास अनुसरून सादर." | "सदर पत्रान्वये …" (17 CR) / "उपरोक्त पत्रान्वये …" (12 CR); our CR122, CR133 already do this |
| B9 | Missing-info para in a form the office does not use | "सदर प्रकरणी … यांच्या दि. __ रोजीच्या प्रस्तावाचे अवलोकन केले असता, त्यामध्ये खालील माहिती आढळून येत नाही:-" (CR122, 128, 130, 131, 133) | "सदर / उपरोक्त प्रस्तावाची छाननी केली असता खालीलप्रमाणे त्रुटी आढळून आल्या आहेत" (C R 250-2024, 259-2024); "उपरोक्त प्रस्तावाच्या अनुषंगाने … खालीलप्रमाणे माहिती उपलब्ध करुन देण्याबाबत … कळविण्यात यावे" (C R 203-2024). Note: §4.31 fixes "प्रस्तावासोबत खालील माहिती उपलब्ध नाही:-" |
| B10 | List-like run of facts after a table with no lead-out | CR66 paras 5–6 after the table: "खाजगी सचिवांची कर्तव्ये …", "आर्थिक भाराबाबत …"; HTE para 4 after the service table | "वरील …" / "उपरोक्त तक्त्यात दर्शविल्यानुसार …" / "सदर प्रकरणी …" (§2.4) |

What already works: WP35697 (§4.32 (ई)) uses "सदर शासन निर्णयान्वये", "मा. उच्च न्यायालयाच्या उपरोक्त आदेशानुसार", "प्राप्त
माहितीच्या आधारे", "वित्त विभागाच्या उपरोक्त अभिप्रायानुसार", "त्यानंतर" — the closest to office flow; its weakness is
length (21–23 numbered paras).

## 4. इंजिनसाठी नियम-प्रस्ताव (rule proposal, for Abhi's decision; no rule changed yet)

```
F1  Group, then number (GADT 4.13(6), 4.14 bk p.11-13; office median 5 numbered paras, 28 % end ":-"):
    one numbered para per issue (demand / background / authority letters / provisions / earlier opinion /
    missing info / सबब); facts of the same issue go as sub-points (1), (2) under ONE lead-in ending ":-".
F2  Opener table (§1 counts; use only these, pick the one that states the real relation):
    para 2 demand ........ "सदर पत्रान्वये" / "उपरोक्त पत्रान्वये"            (C R 261-2024, 220-2024)
    facts opener ......... "याबाबतची / सदर प्रकरणाची वस्तुस्थिती खालीलप्रमाणे आहे:-" (C R 6-2026, 24-2022)
    letters in a chain ... "<A> यांच्या … अनुषंगाने" → "त्यानुसार" → "त्यानुषंगाने" → "तद्नंतर" (C R 16-2026)
    provisions group ..... "उपरोक्त प्रस्तावाच्या अनुषंगाने खालीलप्रमाणे नमूद करण्यात येत आहे:-" / "या प्रकरणी …"
                           / "उपरोक्त संदर्भात …" (C R 16-2026, 2-2026, 261-2024)
    second GR / para ..... "तसेच, …" ; "सदर शासन निर्णयाच्या … अन्वये" at most once per group (C R 2-2026)
    contrast / objection . "तथापि, …" / "परंतु, …" (37 / 25 CR)
    earlier opinion ...... "उपरोक्त प्रस्तावाच्या अनुषंगाने वित्त विभागाने याच विषयावरील अन्य नस्ती क्र. __ मध्ये
                           पुढीलप्रमाणे अभिप्राय दिले आहेत:-" (C R 202-2024, 205-2024)
    missing info ......... §4.31 wording stays; may open "सदर प्रस्तावाची छाननी केली असता" (C R 250-2024, 259-2024)
    सबब .................. "सबब, उपरोक्त वस्तुस्थिती विचारात घेता, …" (C R 116-2021, 28-2025, 52-2025)
F3  Quote in/out (§2.3): lead-in names the author and ends "… खालीलप्रमाणे नमूद करण्यात आले आहे:-" or inline
    "… मध्ये असे नमूद करण्यात आले आहे की, “…”" / "“…” असे नमूद आहे."; the next sentence picks it up
    ("वरील तरतुदीनुसार", "वरील अटीनुसार", "उपरोक्त प्रमाणे") (C R 2-2026, 6-2026, 225-2024). Not "खालीलप्रमाणे
    तरतूद आहे" (corpus 0). Quotes stay verbatim and complete (§1.1, §4.34 (उ)).
F4  Table in/out (§2.4; 57/74 lead-ins end ":-", 38/71 lead-outs look back): a lead-in sentence naming the
    subject and content ("<कोण> यांचा सेवा तपशील खालीलप्रमाणे आहे:-"); the next para opens "वरील तक्त्यात
    दर्शविल्यानुसार …" / "उपरोक्त तक्त्यातील अ.क्र. __ …" / "सदर प्रकरणी …" (C R 136-2024, 250-2024, 8-2011).
F5  One subject carried forward (§2.2): inside a group repeat the short name ("श्री. ____ यांनी", "सदर
    कर्मचारी") rather than a new full designation; do not start a sentence with a bare "त्यांनी" (5 / 3 CR).
F6  Dates in order (GADT 4.13(7) bk p.11): one step per sentence, "तद्नंतर" (18 CR) / "त्यानंतर" / "दरम्यान".
F7  Do not (GADT 4.13(13) "ठराविक शब्दप्रयोग टाळावेत", 4.16(2); MMOP 11.2(1) p.79 "abruptness, redundancy …
    repetitions … should be avoided"): no same opener in two consecutive paras; no "सदर शासन निर्णयाच्या परिच्छेद N
    मध्ये" chain; no flourish; still one point per sentence and ≤ 40 words (§4.18, GADT 4.13(12) "लांब वाक्ये व
    निबंधासारखी शैली टाळावी"); links state only the record's relation (§1.1) — never "दिसून येते", "अशा
    परिस्थितीत … शक्यता", "आवश्यक नाही", "उचित होईल" (§2.6).
F8  For Abhi (no change without him): (a) §4.29(10) "उपरोक्त वस्तुस्थिती पुढीलप्रमाणे आहे:-" is 0 in the
    office corpus — keep, or fold the 3-6 facts into the सबब para after "उपरोक्त वस्तुस्थिती विचारात घेता,";
    (b) the "अट / प्रस्तावातील स्थिती" table (§4.29(9)) has no office model — keep, or write condition → fact
    sentences as C R 2-2026; (c) sub-points need a spec form (e.g. `note.sub`, already used in HTE) for F1.
```

## 5. मॅन्युअल संदर्भ (manual paras used)
- GADT 4.13(4)–(8), (12), (13) — book p.11 (PDF p.15): reference first; "प्रत्येक परिच्छेद हा स्वतंत्र मुद्यासाठी";
  chronological order; "थोडक्यात व मुद्देसूद … पुनरुक्ती टाळावी"; "लांब वाक्ये व निबंधासारखी शैली टाळावी"; "ठराविक
  शब्दप्रयोग टाळावेत".
- GADT 4.13(14), 4.14 — book p.12–13 (PDF p.16–17): large figures in separate tables; paragraph plan (1)–(6).
- GADT 4.16(1)–(3), (6) — book p.13 (PDF p.17): do not copy the whole incoming letter; no ornate style; "एका परिच्छेदात
  एकापेक्षा जास्त मुद्दे असू नयेत"; end so that a signature alone gives a decision. (4.16(1) touches §1.1 verbatim
  extracts; Abhi decided on 01.11.2026 to keep full GR extracts — HANDOVER; not reopened here.)
- GADT specimen note — book p.14–15 (PDF p.18–19): "… पत्र पाहावे. पत्रान्वये … मान्यतेसाठी सादर केली आहे. संचालकांनी
  सादर केलेल्या योजनेचा तपशील पुढीलप्रमाणे आहे :-" → sub-points (१)–(५) → "२. वरील योजनेतील …".
- MMOP 8.2(5)–(6) p.44, 8.2(7)–(8), (14) p.45 (serially numbered paragraphs; self-contained note), 11.2(1) p.79
  (avoid lengthy sentences, abruptness, redundancy, repetitions), 18.4(2)(d) p.105 (logical sequence: facts → rules →
  suggested action → competent authority → points for decision).
- Scratch scripts (not committed): scratchpad `flow/` (seg.py, blocks.py, op2.py, el.py, ph2.py, tbl.py, rs.py).
