# Office task (कार्यालयीन काम) — binding rules for one run (case `work_type` "office")

Abhi's decision of 20.11.2026 (INSTRUCTIONS.md §4.48): the page's separate tab "कार्यालयीन काम" takes everyday clerical
work that is NOT a proposal — move the information of 2-3 documents into a given format, collate data, calculate from
figures, show data in a neat table, make a PPT. Outputs (run `outputs`): Excel (`xlsx`), Word (`docx`), PPT (`pptx`), PDF
(`pdf`); `[]` = answer only, in the run summary. Config: tools/office_work.json. Worker procedure: docs/DESK_WORKER.md §3b.
OWNER_RULES.md applies in full; the proposal rules (note, letter, Study, package, PROPOSAL_SOP) do NOT apply, except where
a line below names them.

## 1. Sources and figures (OWNER_RULES A.1-A.4)
1. Read every input completely before doing anything: each source document (`extra_doc`), Abhi's format / sample file
   (`template`) and, on a later run, the previous result (`office_output`). Scans / images: every page as an image (OCR
   only to help, DESK_WORKER §3 step 1 tools); Excel every sheet incl. hidden ones (openpyxl); Word every paragraph and
   table incl. headers / footers (python-docx); PPT every slide and its notes. Numbers, dates, names: read twice.
2. Nothing of your own: no guessed, assumed, rounded or "typical" value; no fact, opinion or conclusion the inputs do not
   carry. Keep apart what the data shows and what it does not show.
3. Every figure is traceable to its source: file name + page (PDF / Word) or sheet + cell (Excel) or slide (PPT).
4. A value the inputs do not give, or that cannot be read -> "____" in the output + a run warning
   "पडताळणी अपूर्ण — <file>: <what> (<where>) उपलब्ध नाही / अस्पष्ट". Never invented, never left out silently.
5. Two inputs disagree on a value -> both are shown with their sources (Excel: the पडताळणी sheet; Word / PPT: a short
   line where the value is used) + a warning; no choice of your own.
6. Instruction vs these rules: the rule wins + warning "पडताळणी अपूर्ण — सूचना '…' नियम … मुळे लागू केली नाही".
   Anything not stated by Abhi (extra columns, totals, charts, colours beyond §4, comments) is not added (A.5) — except
   the पडताळणी sheet (§2.3), which is always there.

## 2. Excel (`xlsx`)
1. Every calculated value is a LIVE Excel formula (`=SUM(B2:B9)`, `=B4-C4`, `=ROUND(D2*12,0)`), never a typed result.
   Only the source figures are typed in, as numbers (not text). Percentages / averages / differences likewise formulas.
2. No error value: tools/office_check.py recalculates the workbook with LibreOffice and fails on #REF! #DIV/0! #VALUE!
   #NAME? #N/A #NUM! #NULL!. Guard a division whose divisor may be 0 or "____" with `=IF(C2=0,"____",B2/C2)` only where
   the input really has such a row.
3. Sheet "पडताळणी" in every workbook that has a number or formula: one row per source figure — sheet!cell where it is
   used, the value, the source (file name, page / sheet!cell / slide), and "____" rows for the missing ones (§1.4). Its
   header row: "अ.क्र. | आकडा (शीट!सेल) | मूल्य | स्रोत (फाइल, पृ. / शीट!सेल)". Formula cells need no row (the formula
   is its own trace); a total checked against a total printed in a source gets a row comparing both with a formula.
4. A template given (`template`, xlsx / xls / csv): fill THAT workbook — its sheets, headers, column order, merged cells,
   number formats and print settings stay as they are; nothing redesigned, renamed or reordered. Only empty cells are
   filled and formula cells added where the template expects totals. The पडताळणी sheet is added at the end.
5. No template: one table per sheet, header row bold and frozen; numbers stored as numbers, dates as dates (shown
   `dd.mm.yyyy`); column widths fitting the text.

## 3. Word (`docx`) and PDF (`pdf`)
1. A template given (docx / doc): fill it, keep its layout, headings, tables and styles; never redesign it.
2. Marathi text follows the office language rules of INSTRUCTIONS.md §4.18 (short sentences, one point each, clear
   subject, respectful plural, "श्रीमती"), §4.19 (forms "दि. 17.09.2026", "क्र. 108", ":-", "करून", "प्रारूप") and §4.25
   (शुद्धलेखन: "आपणांस", "करण्याबाबत", "पद्धती", "द्ध" never "ध्द"; Marathi initials and designations). Text copied from
   a source stays as in the source (§1.1 of INSTRUCTIONS).
3. Numbers first: tables for figures (amounts, counts, periods); a few bullets for points; no theory or long prose.
4. PDF: made from the Word / Excel output with LibreOffice (`soffice --headless --convert-to pdf`) when both are asked,
   else built directly (anthropic pdf skill). DVOT-SurekhMR and Times New Roman are not installed in the cloud session:
   a PDF rendered there uses fallback fonts -> office_check WARN; write the warning "पडताळणी अपूर्ण — PDF: DVOT-SurekhMR /
   Times New Roman फॉन्ट उपलब्ध नसल्याने PDF पर्यायी फॉन्टमध्ये — Word/Excel फाइलवरून PDF पुन्हा तयार करावी, ही विनंती".

## 4. PPT (`pptx`)
1. A template given (pptx / ppt): its masters, layouts and order are used as they are.
2. Numbers first (OWNER_RULES D.2): one message per slide as its title, the figures in a table or chart, a few short
   bullets; no paragraphs of prose. Charts only from the figures in the inputs (each chart's figures also in a table or the
   workbook).
3. Logical colours by meaning (OWNER_RULES D.2), also for charts in Excel / Word: increase / surplus / complete = green, decrease / shortfall / pending = red, neutral =
   grey / dark blue; the same meaning keeps the same colour on every slide.

## 5. Fonts (decision 3, all office outputs)
- Marathi / Devanagari text: DVOT-SurekhMR. English / Latin text: Times New Roman (the default font for English).
- Word: the common font rule of the proposal Word files (INSTRUCTIONS §4.49, tools/font_rule.py; styles, headers,
  footers too): Marathi text (with its digits / punctuation) DVOT-SurekhMR on all four w:rFonts attributes; English text
  ascii = hAnsi = Times New Roman, cs = eastAsia = DVOT-SurekhMR (a mixed run is split); a digits-only run follows its
  paragraph (Times New Roman when the paragraph has no Devanagari).
- PPT: a:latin = Times New Roman, a:cs = DVOT-SurekhMR. Excel: a cell has one font — a cell with Devanagari text
  DVOT-SurekhMR, any other cell Times New Roman (theme latin / cs likewise).
- After building with any tool: `python3 tools/office_fonts.py <every output file>` (fixes fonts AND blanks metadata in
  place; a template's own fonts are normalised to this rule as well), then tools/office_check.py.

## 6. No AI trace, metadata (INSTRUCTIONS §4.27 (उ), tools/clean_meta.py)
- No word in any output that shows automated or AI work (Claude, Anthropic, AI, LLM, GPT, Gemini, "मॉडेल", "स्वयंचलित",
  "प्रणालीने तयार", generated …), no working note ("TODO", "पडताळणी अपूर्ण", "इशारा"), no comments, no tracked changes,
  no "—" / "→" in own text, no URLs. Open points go ONLY into the run `warnings` and the summary.
- Metadata blank: title, subject, keywords, comments, category; author / last modified by = env DOC_AUTHOR or empty;
  Application an Office name. tools/office_fonts.py does this; office_check verifies it.

## 7. File names, language, summary
- One file per asked output type unless the instruction asks for more; `original_name` = a meaningful Marathi (or the
  instruction's) name from the task, e.g. "जिल्हानिहाय_विवरण.xlsx"; the same name as the previous result on a correction
  run (it becomes the next version). No "Office_Output", "final", "v2", dates or ids in the name.
- Output language = the language of the template, else of the instruction; English only when the instruction or the
  template is English (then the same rules, English official style, Times New Roman).
- A later run on the same task = correction / continuation: start from the newest `office_output` files, change only
  what the instruction asks, keep everything else identical (same layout, same figures, same sources).
- Run summary (≤ 2000 chars, Marathi): what was produced (file names, sheets / slides, key totals as numbers), or the
  answer itself for `outputs` [], each figure with its source in brackets; then the count of open points. Never a
  figure in the summary that is not in an input or computed by a formula from them.
