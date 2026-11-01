> Source: Advanced Research report, 2026-11-01 (chat "מחקר: כלי לצנזור קבצים מקומי"). Market, competitors, business model, legal landscape. Superseded where it conflicts with build-plan.md v3.0.

# Tomer Censors: Consultation Report and Devil's Advocate Review

**Bottom line:** The problem is real and the timing is good, but the product as described (a generic offline name-replacer on a USB stick, with a hidden usage counter) is the weakest version of the idea. The version that can win is a Hebrew-first, document-faithful, reversible pseudonymization tool for small Israeli professional firms, sold as a per-seat annual subscription with offline-verifiable licenses and prepaid volume packs, not secret royalties. Since October 2026 you have direct competitors shipping the same core concept in English and French, and the detection models themselves are becoming free commodities. Your edge has to be Hebrew, file fidelity, Israeli compliance evidence, and trust, not "a small neural net that runs offline."

## TL;DR

- **Demand is real but the legal premise is narrower than you think.** The Israel Bar's September 2026 ethics opinion says anonymization is "neither absolute nor dichotomous", and per Haim Ravia's summary, informed client consent is still required before using restricted client data on an open AI platform "including where anonymization was performed or is being considered." Your tool reduces risk and supports compliance; it does not make uploading legal by itself. Sell it as a data-minimization layer with an audit trail, not as a permission slip.
- **The market is getting crowded fast and the models are free.** Conseal (US, launched October 23, 2026, $29.99 per device per month), AnonymFiles (France, €290 per seat per year, fully offline, pre-launch), anonym.legal (EU, €3 to €29 per month, lists Hebrew), and Poly (Israeli Hebrew legal AI with built-in anonymization, cloud) already exist, and OpenAI and Fastino released Apache 2.0 PII models in 2026. The open gap is Hebrew-quality detection plus morphology-aware consistent pseudonymization, faithful DOCX/PDF output, and rehydration, for Israeli lawyers, accountants, and clinics.
- **Drop the hidden counter; use a subscription with signed offline licenses.** A secret counter you cannot read is unenforceable, and in a privacy product it is a trust-killer. Use annual per-seat licenses that expire and renew with a signed code (offline challenge-response or QR), plus optional prepaid signed credit packs for batch volume, plus a visible signed usage statement for site licenses at renewal. That gives you recurring revenue without network access to documents.

## Key Findings

1. **Regulators in Israel explicitly treat "remove the names" as insufficient.** The Israel Bar's first opinion (May 2024) told lawyers to keep identifying details such as names, addresses, trademarks, business partners and family history out of AI inputs. The expanded opinion (published September 2026) defines "restricted information" by reference to section 3 of the Privacy Protection Law as amended by Amendment 13, warns that sharing restricted information with an external AI provider may be construed as an impermissible waiver of confidentiality or privilege, and says omitting a client's name or another identifier does not guarantee sufficient anonymization. Your product must handle quasi-identifiers and context, not just named entities, and must produce evidence of what was done.
2. **Pseudonymized data is still personal data for the user.** Under GDPR Recital 26 logic and the CJEU's EDPS v SRB judgment (C-413/23 P, September 4, 2025), pseudonymized data stays personal data for the party holding the key (your user, who keeps the mapping table). The Court accepted it may be non-personal from the recipient's perspective (the AI vendor) only if the recipient has no reasonable means to re-identify. With rich legal or medical narratives that is a high bar.
3. **Re-identification by LLMs is now cheap.** In "Large-scale online deanonymization with LLMs" (arXiv 2602.16800, February 2026), Lermen, Paleka, Swanson, Aerni, Carlini and Tramèr report that LLM methods achieve "up to 68% recall at 90% precision compared to near 0% for the best non-LLM method"; a secondary write-up puts the cost at roughly $1 to $4 per profile, which I could not confirm in the paper itself. Separately, Tianshi Li of Northeastern University ("Agentic LLMs as Powerful Deanonymizers", arXiv 2601.05918, January 2026) found that of 125 scientist transcripts in Anthropic's public Interviewer dataset, 24 mentioned at least one publication, and off-the-shelf agentic LLMs re-identified 6 of those 24. One nuance in your favor: the same literature notes that even the best LLMs struggled to re-identify anonymized court decisions, so legal documents are harder to crack than social media posts, but not safe by default.
4. **Off-the-shelf models are good but not good enough on legal text.** OpenAI's Privacy Filter (April 22, 2026, Apache 2.0, 1.5B total / 50M active parameters) reports 96% F1 on the PII-Masking-300k benchmark, but Fastino's own comparison shows legal-domain recall of only 0.72 for its GLiNER2-PII, 0.64 for OpenAI Privacy Filter and 0.43 for NVIDIA's GLiNER PII. That means roughly a quarter or more of sensitive spans could be missed on legal text without domain tuning. Neither is documented as strong on Hebrew.
5. **Hebrew is your moat, and the building blocks exist.** DictaBERT has NER and a joint model that does prefix segmentation plus NER; HalleluBERT reports NER F1 of 87.06 on the NEMO benchmark; DictaLM 3.0 ships open 1.7B, 12B and 24B models, including a 1.7B GGUF build that runs on CPU. Clalit's open-source HebSafeHarbor already de-identifies Hebrew clinical text, but a December 2025 paper reports it "sometimes missed certain names and locations" and over-masked. Nobody has nailed high-recall, morphology-aware Hebrew pseudonymization for documents.
6. **Large firms are solving this with enterprise AI; small firms are not.** Meitar calls itself the first Israeli firm to partner with Harvey, and Herzog Fox & Neeman announced Harvey adoption on October 14, 2025. OpenAI offers enterprise no-training defaults, in-region data residency (expanded January 16, 2026) and zero data retention for eligible API customers. Israel has roughly 90,000 licensed lawyers, about 76,000 active, and most work in small practices that will not buy Harvey. That is your beachhead.

## 1. Market and Competition

### The landscape in late 2026

The space splits into four groups:

- **Enterprise de-identification platforms** (Private AI, now rebranded Limina; Tonic Textual; Protecto; Skyflow; John Snow Labs for healthcare). Strong engines, cloud or container deployment, sales-led pricing, built for data pipelines, not for a lawyer with a Word file.
- **Enterprise GenAI security / DLP gateways** (Prompt Security, Lasso, Nightfall, Strac, Lakera). These sit between employees and ChatGPT and block or redact prompts. Israel is a hotbed: Calcalist reported in August 2025 that SentinelOne was acquiring Prompt Security "in a blue-and-white deal valued at approximately $250 million" (Globes put it at $250 to $300 million), even though Prompt had raised only $23 million; the deal completed on September 5, 2025, and Lasso, Aim and Pillar were fielding offers. These target CISOs at large companies, not small firms, and they mostly redact rather than produce a usable pseudonymized document.
- **Prosumer local "anonymize before ChatGPT" apps**, the category you are entering. This category barely existed in 2024 and is now filling up.
- **Free open-source building blocks** (Microsoft Presidio, Philter, GLiNER, OpenAI Privacy Filter, HebSafeHarbor). Fastino Labs' May 14, 2026 press release, issued alongside the Apache 2.0 release of GLiNER2-PII, quoted the company saying it is open-sourcing "because the entire industry benefits when this layer becomes a commodity." Treat detection as a commodity input.

### Competitor table

| Product | Origin | What it does | Deployment | Hebrew | Pricing (public where available) |
|---|---|---|---|---|---|
| Conseal (Sprintfour) | US | Redact or anonymize with consistent labels like [PERSON_1], restore from local mapping file, live detection while typing in any app | Local desktop (Win/macOS); internet only for license validation and updates | Not stated | $29.99 per device per month, all features |
| AnonymFiles | France | Folder-level anonymization, side-by-side review, OCR for scans, EML/MSG, XLSX, PPTX, metadata stripping, rehydration of AI answers | Fully offline, no online license check, no telemetry (pre-launch) | Not stated | Pro €290/seat/year; Team €240/seat/year from 3 seats; Enterprise and OEM per-seat royalty on quote |
| anonym.legal | EU | Presidio-based detection, desktop app, Office add-in, Chrome extension, MCP server, reversible encryption | Its own comparison page says the desktop app's detection runs on its servers | Listed among 48 languages, including RTL | Free (200 tokens), €3, €15, €29 per month, token-based |
| Poly (polylm.com) | Israel | Hebrew legal AI drafting platform with optional automatic anonymization of uploaded files; works only on the anonymized version | Cloud SaaS | Yes, native | Not obtained |
| HebSafeHarbor (Clalit / 8400) | Israel | Open-source Hebrew clinical de-identification (Presidio + HebSpacy/AlephBERT + rules) | Self-hosted | Yes | Free |
| Private AI / Limina | Canada | Enterprise PII detection across 50+ languages, text/docs/images/audio | Cloud, VPC, on-prem container | Not confirmed | Enterprise quote only |
| Tonic Textual | US | NER-based redaction, reversible tokenization, synthesis for AI pipelines | Cloud, self-hosted, AWS AMI | Not confirmed | Free $5/month credits; $29/month plan with $25 credits; pay-as-you-go per 1,000 words; Vendr estimates enterprise at $20,000 to $35,000 per year |
| Prompt Security (SentinelOne), Lasso | Israel | Enterprise GenAI DLP / firewall for all prompts | Enterprise SaaS / agents | Probably | Enterprise quote |
| Microsoft Presidio, Philter, OpenAI Privacy Filter, GLiNER2-PII | Open source | Detection engines | Self-hosted | Weak or none out of the box | Free (MIT / Apache 2.0) |

Other EU players with the same pitch include Weblaw (Switzerland, consistent pseudonyms and restore, built for legal), Pseudonymizer.eu and Nymiz.

### Where the gap actually is

Be honest with yourself: "offline" alone is no longer a differentiator. Conseal and AnonymFiles already do local processing, and AnonymFiles even markets itself as "the only truly 100% offline tool" with no license check. What nobody visibly offers yet:

1. **High-recall Hebrew and mixed Hebrew/English detection**, with prefix-aware matching (ו/ה/ב/ל/מ/ש/כש attached to names), Israeli identifiers (Teudat Zehut with checksum, Israeli IBAN, license plates, Israeli phone formats, company numbers ח.פ.), and Hebrew surrogate names that inflect correctly.
2. **Faithful round-trip of real Israeli professional documents**: RTL DOCX with tracked changes, footnotes and headers; scanned Hebrew PDFs; court forms.
3. **Compliance evidence aligned with the Israel Bar opinion and Amendment 13**: a per-document report of what was detected, what the user approved, what residual risks were flagged, and a client-consent template.
4. **Israeli go-to-market**: Hebrew UI, Hebrew support, local invoicing, bar association and accountant association channels.

### The threat from enterprise AI and local LLMs

Does enterprise AI with no-training and zero-retention guarantees shrink your market? Partly, at the top. Large firms (Meitar, Herzog) buy Harvey or ChatGPT Enterprise with contractual protections, and their security teams accept that. But three things keep demand alive:

- **Small firms cannot or will not buy enterprise plans.** Conseal's launch pitch rests on ABA data that 7 in 10 US lawyers at law firms work solo or in firms of 10 or fewer. Israel's profile is similar: lots of solo and boutique practices among roughly 76,000 active lawyers.
- **The Bar opinion still requires vetting the provider and, where risk exists, informed consent.** Even on business plans, minimizing what you send is good practice, and clients (especially insurers, banks, government bodies) increasingly demand it in outside-counsel guidelines.
- **Retention promises are not confidentiality guarantees.** The New York Times v. OpenAI preservation order showed that consumer and non-ZDR data can be swept into litigation holds (Enterprise and ZDR were excluded). Pseudonymization is defense in depth.

Fully local LLMs are a bigger long-term threat: if a 24B Hebrew model like DictaLM 3.0 runs well on a firm's own box, why send anything to the cloud? Today the quality gap to frontier models is still large for complex legal reasoning, and most office laptops cannot run 24B models well. But plan for this: your product should also work as the privacy layer in front of a firm's own local or private model, not only in front of ChatGPT.

## 2. Target Customers and the Real Rules

### Lawyers (best first segment)

- **Israel Bar Association.** May 2024 preliminary opinion: verify outputs, limit AI to general queries, keep client-identifying data out, get consent for personal data. September 2026 expanded opinion (opinion 60-24): defines restricted information broadly; says anonymization is not absolute and re-identification may remain possible "depending on the type of information, the combination of data points, information available from other sources"; requires examining the provider's terms, storage, deletion and protections; requires informed consent where risk exists; and bars AI agents from making substantive legal decisions without human supervision. Israeli courts have already sanctioned lawyers for improper AI use, and the Supreme Court's Ramat Gan ruling put the fault on "uncontrolled use without appropriate verification."
- **ABA Formal Opinion 512 (July 2024).** Lawyers must understand whether information entered will be visible to the provider or affect other users' answers, and get informed consent before inputting confidential information into self-learning tools. The Oregon State Bar's Formal Opinion 2025-205 says that when using an open model without client consent, lawyers need to anonymize or redact information the client considers sensitive. That is direct regulatory language you can quote in marketing for US expansion.

**What this means:** your product turns "I can't use AI on this file" into "I can use AI on this file after a documented minimization step, with client consent where needed." That is valuable, but it is a workflow and evidence product, not a magic legality switch.

### Doctors, clinics, hospitals

- **Israel.** The Ministry of Health has no comprehensive clinical AI regulation; it relies on circulars (secondary use of medical data 1/2018 and 2/2018, cloud computing, cyber protection), non-binding AI principles from April 2023, and February 2026 principles for AI-based interventional trials. Hospitals and HMOs have strict information security units and will be slow, procurement-heavy buyers. Clalit already built HebSafeHarbor in-house, which tells you large HMOs may build rather than buy.
- **HIPAA (US).** Safe Harbor requires removing 18 identifier types, including all date elements except year and geographic units smaller than a state, plus no actual knowledge of re-identifiability. Surrogate names are fine, but date shifting is not Safe Harbor compliant; it needs Expert Determination by a qualified statistician. If data is not de-identified, sending it to an AI vendor requires a Business Associate Agreement. So for US healthcare, your "keep dates useful" feature puts users outside Safe Harbor. Be explicit about this in the UI.

**Verdict:** healthcare is attractive but a second-wave market. Private clinics, therapists, and medical-legal experts (e.g. doctors writing expert opinions for courts) are reachable; hospitals are a 12 to 24 month sale.

### Accountants, financial analysts, insurance, HR, government

- **Accountants and tax advisors** are an underrated Israeli segment: heavy document load (financial statements, tax assessments, payroll), strong confidentiality duties, small practices, price-sensitive, and less served by legal-tech vendors. Numbers matter here, which raises the numeric-replacement challenge (see section 4).
- **Insurance claims, HR, and investigations** have lots of personal data and are often subject to Amendment 13's new obligations (DPO appointment in defined cases, board oversight, PPA enforcement). Government is a long-cycle, tender-driven buyer; skip it for now.

### GDPR, the EU AI Act, and Israeli privacy law

- **GDPR.** Recital 26: pseudonymized data is personal data; truly anonymous data is out of scope. After EDPS v SRB, identifiability is assessed relative to who holds the data and what means they reasonably have, but the controller who did the pseudonymization (your user) still holds personal data and still has transparency duties. Your tool is a security measure under Articles 25 and 32, not an exit from GDPR.
- **EU AI Act.** A pseudonymization tool is not a high-risk system under Annex III. Low relevance.
- **Israel PPL and Amendment 13** (in force August 14, 2025). Expanded definitions, PPA powers to investigate and fine, mandatory DPO in defined cases, and criminal exposure for some violations. The PPA's April 2025 draft AI guidance says a legal basis is required at every stage of the AI lifecycle and specifically warns about inference attacks. For your customers, using a minimization tool is evidence of reasonable security and privacy by design.

### What a compliance officer or IT security team will ask before approving

1. Does it make any network connection? Prove it (firewall test, published network scope, third-party pen test).
2. Is the binary signed? Is there an installer that our endpoint management (Intune, SCCM, Jamf) can deploy?
3. Where is the mapping table stored, how is it encrypted, who can open it, and how is it deleted?
4. What are the measured recall and precision on documents like ours, in Hebrew?
5. What does the user see before export? Is human review mandatory?
6. Who is the vendor, are they solvent, and do they carry cyber/E&O insurance?

Plan to answer all of these in a two-page security whitepaper from day one.

## 3. Technical Approach and Models

### Recommended architecture: a layered, high-recall pipeline

1. **Document parsing layer** (format-specific, see section 5).
2. **Deterministic layer**: regex plus validators. Teudat Zehut (9 digits with Luhn-style check digit), credit cards (Luhn), IBAN (mod-97; Israeli IBANs are IL plus 21 characters), Israeli phone numbers, emails, URLs, license plates, company and association numbers, bank account and branch patterns, case numbers (court docket formats), dates. These are near-100% precision and recall for structured identifiers, and cheap.
3. **NER ensemble**: DictaBERT-NER or DictaBERT-joint for Hebrew (the joint model gives you prefix segmentation, which you need), plus GLiNER2-PII or OpenAI Privacy Filter for English and mixed text. Union the outputs: in this product a false positive costs a click, a false negative costs a leak.
4. **Contextual LLM pass (optional, "deep mode")**: a small local instruct model (DictaLM 3.0 1.7B for Hebrew, or a Qwen/Gemma/Phi class model of 1.5B to 4B for English) to catch quasi-identifiers the NER misses: job titles, "the CEO of company X", rare diseases, small towns, unique events, and to classify "realm of activity" for the industry-generalization option. Run it as a reviewer that flags spans, not as a rewriter, to keep output deterministic.
5. **Entity resolution and coreference layer** (your real IP; see section 4).
6. **Human review UI** with every detection highlighted, confidence shown, one-click add/remove, and "apply to all occurrences."
7. **Writer layer** that puts surrogates back into the original format.

### Hebrew-specific problems you must solve

- **Prefixes**: "ולכהן", "שמשה", "בתל אביב". Detect on segmented morphemes, replace only the base, keep the prefix. DictaBERT-joint and the NEMO morpheme-level benchmark exist precisely for this.
- **Names that are common words**: אור, טל, שמש, ים, ברק, שקד, גל. Context matters; this is where NER plus LLM beats dictionaries.
- **No capitalization** and frequent transliteration variants (כהן / Cohen / Kohen; יעקב / Yaakov / Jacob).
- **Gendered morphology**: if "שרה" becomes a male surrogate, verbs and adjectives in the text no longer agree, which both confuses the AI and leaks that a swap happened. Choose surrogates with the same gender, and ideally the same cultural origin (Hebrew, Arabic, Russian-origin names in Israel carry demographic signals; swapping them can either break the AI's reasoning or, worse, distort a discrimination case).

### Hardware reality

Target an ordinary office laptop: 8 to 16 GB RAM, no GPU, Windows 11. A BERT-base NER model in ONNX Runtime with INT8 quantization runs comfortably on CPU at document speed. GLiNER2-PII (205M to 300M parameters) is also fine on CPU. OpenAI Privacy Filter's 50M active parameters are efficient at inference but its 1.5B total weights cost memory and disk. A 1.7B LLM in Q4 GGUF (about 1 to 1.5 GB) via llama.cpp is usable on CPU for a flagging pass but slow for long documents; make deep mode optional and chunked. Your background in ONNX, quantization and kernel work is a real advantage here: fast, small, reliable local inference on mediocre hardware is exactly the engineering most competitors will do badly.

### Evaluation: the metric that matters

- **Recall (on direct identifiers) is the critical metric.** A tool with 99% precision and 90% recall leaks one in ten names. Set public targets such as 99%+ recall on direct identifiers in your Hebrew test set, measured at the entity level and the document level ("percentage of documents with zero leaked direct identifiers"), and report it honestly.
- **Build your own Hebrew benchmark.** There is no public Hebrew legal/medical PII benchmark that matches your use case. Create a synthetic but realistic set (contracts, pleadings, medical summaries, emails, WhatsApp transcripts) with annotations, plus a small set of real documents from pilot firms evaluated on their premises. This dataset is a durable asset and a moat; Protegrity's critique of OpenAI's release makes the same point that PII detection is "way more of a high-quality data generation problem than it is a model architecture problem." Use public sets (PII-Masking-300k, SPY, REDACT, PIIBench) only as English sanity checks.

## 4. Pseudonymization Quality: Angles You Probably Have Not Considered

- **Coreference and variants.** "Jacob Cohen", "Jacob", "Mr. Cohen", "J. Cohen", "Cohen's", "jacob.cohen@firm.co.il", "@jcohen", initials "י.כ.", Hebrew inflections and possessives. All must map to one surrogate with consistent form ("Donald Miller", "Donald", "Mr. Miller", "D. Miller", "donald.miller@..."). Pronouns usually stay, which is fine if gender is preserved.
- **Family relations.** If Jacob Cohen and Rachel Cohen are spouses, the surrogates should share a surname, or the AI's reasoning about the family breaks.
- **Surrogate collisions.** Never pick a surrogate that appears elsewhere in the document (or the whole case folder) or is a real party, judge, or public figure. Keep a per-matter dictionary.
- **Consistency across a folder and across time.** A case has 40 files and lasts 2 years. The mapping must persist per matter, so the same person gets the same surrogate in every file and every session. This is both a feature and the most sensitive asset in the system.
- **Dates.** Option A: shift all dates in a document or matter by the same random offset, preserving intervals and weekdays if possible (deadlines and limitation periods still compute). Option B: generalize to month/year. Warn that date shifting breaks references to real-world events (holidays, laws in force, war periods) and is not HIPAA Safe Harbor.
- **Numbers.** Amounts, ages, percentages, and ratios carry meaning. Offer modes: keep, scale all amounts by one hidden factor (ratios preserved, absolute values hidden), bucket (age 40 to 45), or mask. For accountants, scaling preserves the analysis; for legal claims, an amount may itself be identifying (a NIS 3,417,000 judgment is searchable).
- **Quasi-identifiers and the mosaic effect.** "The only female cardiologist at the hospital in Kiryat Shmona" identifies someone with no names at all. The Bar opinion explicitly flags "the combination of data points." Offer a generalization mode (town to district, specific hospital to "a public hospital in the north", job title to function) and a residual-risk warning panel that lists remaining quasi-identifiers. You cannot guarantee anonymity; you can surface the risk.
- **Public vs private entities.** Courts, laws, government ministries, and cited precedents should normally stay (OpenAI's model and Weblaw's product both make this distinction). Replacing "the Supreme Court" or a statute destroys utility.
- **The privacy/utility trade-off is the product.** Your "censorship level" idea is right, but present it as named presets per profession ("Litigation memo", "Contract review", "Medical summary", "Financial statement") rather than abstract levels, and show a preview of what the AI will see.
- **Rehydration is a killer feature, but also your biggest new risk.** Pasting the AI answer back and restoring real names locally is what turns a redaction tool into a daily workflow tool; Conseal and AnonymFiles both have it, so it is table stakes, not a differentiator. Watch for: the AI inventing new names (no mapping, left as-is, flagged), the AI inflecting a Hebrew surrogate in a form you did not generate (needs morphology-aware reverse matching), and partial matches ("Miller" vs "Millers"). The mapping file must be encrypted at rest (for example AES-256-GCM with a key protected by Windows DPAPI or macOS Keychain, or a user passphrase), scoped per matter, auto-expiring, and never written next to the exported document. A mapping file emailed with the document undoes everything.

## 5. File Format Fidelity

- **DOCX** is the core of Israeli legal work and the place to beat competitors. Handle body, headers, footers, footnotes, endnotes, comments, tracked changes (insertions and deletions both contain text; deleted text is a classic leak), text boxes, fields, hyperlinks, document properties (author, company, last modified by), custom XML, and embedded objects (an embedded Excel sheet inside a Word file). Names split across runs (formatting changes mid-word) are the common technical trap. Strategy: offer "accept all changes and strip comments" as the safe default.
- **PDF**: text PDFs need true removal of the text from content streams, not a black box overlay; AnonymFiles' page shows the classic failure where copy-paste recovers text under a drawn box. Also strip metadata, annotations, form fields, attachments, and hidden layers. The safest approach for an AI-bound copy is to regenerate a clean PDF or simply export DOCX/TXT, since the AI does not need the original layout.
- **Scanned PDFs and images** need local OCR. Hebrew RTL OCR quality varies substantially across Tesseract, PaddleOCR and docTR; test them on real Israeli court scans and faxes before committing, and treat OCR errors as a recall risk (a misread name will not be detected). This is a v2 feature.
- **XLSX/CSV**: cell-level detection, column-type inference ("this column is ID numbers"), sheet names, comments, hidden sheets and columns, pivot caches, and formulas that reference sensitive cells.
- **Email (EML/MSG)**: headers (From/To/CC are names and emails), signatures, quoted threads, and attachments (recursive processing or exclusion; AnonymFiles excludes attachments and flags them). PowerPoint needs slide text, speaker notes and images.
- **Hidden leaks people forget**: the file name itself ("Cohen_v_Levi_draft3.docx"), EXIF in images, thumbnails, and folder paths in metadata. Rename outputs neutrally by default.

Pragmatic MVP decision: DOCX in, DOCX out, plus text PDF in, DOCX/TXT out. That covers most legal work.

## 6. Offline and USB Deployment Reality

**The USB idea should be dropped as the primary delivery method.** Many corporate, hospital and government environments block USB mass storage through endpoint policy, and Windows SmartScreen and application control policies routinely block unsigned executables run from removable media. Antivirus engines also flag unsigned PyInstaller-style bundles as suspicious. A product that only works from a USB stick will fail at exactly the security-conscious customers you want. It also creates practical problems: lost sticks, slow I/O for multi-GB models, and no clean update path.

What to do instead:

- **Signed installer** (MSIX or MSI for Windows, notarized DMG for macOS) deployable via Intune, SCCM or Jamf. Code-signing certificate with EV or a cloud signing service to reduce SmartScreen friction. Budget for this from the start.
- **"Offline mode" as a verifiable property, not a delivery medium.** The app makes zero network calls during processing, and you prove it: publish the network scope, let customers run it with the network cable unplugged or a firewall rule, ship a built-in "network self-test" screen, and commission a third-party pen test once you have revenue. AnonymFiles' "turn off Wi-Fi, nothing changes" demo is the right marketing instinct.
- **Optional firm server** (Windows service or Docker on a local box) for firms that want central licensing, shared matter dictionaries, and batch processing. This is also your natural upsell.
- **Air-gapped environments** (defense, some government): signed offline update bundles (software plus models) delivered by file, verified with your public key. Here a USB stick is fine as a transport for updates and license renewals, not as the runtime.

Vendor certifications (SOC 2, ISO 27001) are expensive and mostly unnecessary while you process zero customer data on your servers. Use that as a selling point and defer certifications until a large customer requires them. A clear security whitepaper, SBOM, signed builds, and a pen-test letter will satisfy most small and mid-size buyers.

## 7. Business Model and Monetization

### Why the "hidden counter only I can see" is weak

1. **You cannot read it.** If the device is offline, the only way the number reaches you is if the customer sends it. If the customer has to send it, it is not hidden, and they control whether it arrives.
2. **It is easy to defeat.** Local counters are reset by reinstalling, restoring a VM snapshot, rolling back the clock, or patching the binary. Without a hardware secure element, a determined user wins.
3. **It is a trust disaster for a privacy product.** Your entire value proposition is "nothing hidden happens with your data." A secret counter, once discovered (and security teams do inspect binaries), undermines the product and could be argued to be undisclosed data collection.
4. **Buyers dislike unpredictable metered bills.** Small firms want a fixed monthly price; procurement at larger organizations prefers fixed annual subscriptions they can budget.

### Monetization mechanisms for offline software

| Mechanism | How it works offline | Recurring revenue? | Tamper resistance | Buyer acceptance | Fit for you |
|---|---|---|---|---|---|
| Perpetual license, one-time fee | Signed license file bound to machine fingerprint | No | Medium | High, but declining | Poor: your own worry, one-time is not enough |
| Perpetual + annual maintenance (typically around 18 to 25% of license price) | Updates and new models only for active maintenance | Partly | Medium | High in enterprise, familiar to IT | OK for enterprise/government tier |
| **Annual or monthly per-seat subscription with expiring signed license** | License file carries an expiry date and seat count, signed with your private key; renewal via online activation or offline challenge-response (app shows a code or QR, user gets a signed renewal code from your portal on any phone) | **Yes** | Medium-high (clock rollback detectable via monotonic checks and file timestamps; cracking possible but not worth it for professionals) | **High; this is the market norm** (Conseal, AnonymFiles, anonym.legal all use it) | **Primary model** |
| **Prepaid usage credit packs** | You sell signed tokens (e.g. 1,000 document credits); app decrements locally and refuses when exhausted; new pack = new signed code | **Yes, usage-based** | Medium (snapshot/rollback can replay credits; mitigate with hash-chained local ledger and binding to install ID) | Good for batch users (e-discovery, archives, insurers) | **Add-on for heavy volume** |
| Hardware dongle with metered unit counter (Wibu CodeMeter, Thales Sentinel) | Secure element on a USB dongle decrements counts; usage synced when connected | Yes | High | Low-medium (USB blocked, dongles lost, adds cost per unit) | Only for air-gapped, high-value customers |
| Signed tamper-evident usage report with contractual audit / true-up | App keeps a hash-chained, signed usage log visible to the customer; customer exports it at renewal; contract allows audit and annual true-up | Yes | Medium (relies on contract more than crypto) | High for site licenses; familiar from enterprise software true-ups | **Use for firm-wide and enterprise licenses** |
| Optional license-only check-in ping | Tiny outbound call carrying only license ID and counts, never document data; customer can disable and fall back to offline renewal | Yes | Medium-high | Mixed: some buyers want zero network, many accept license validation (Conseal does it) | Offer as default for small firms, with offline alternative |
| OEM / per-seat royalty | Your engine embedded in another vendor's product (legal DMS, practice management, legal AI) | **Yes, true royalties** | Contractual | High | **Your best route to real royalties** |

### Recommended model

- **Core: per-seat subscription.** For Israel, roughly NIS 99 to 149 per seat per month, or around NIS 1,000 to 1,400 per seat per year paid annually. This sits between AnonymFiles (€290 per year) and Conseal ($29.99 per month, about $360 per year). Free 14-day trial; small firm bundles.
- **Setup or onboarding fee** for firm deployments (your "one-time payment"): installation, custom dictionaries (client names, matter names), training. This is legitimate one-time revenue without giving away perpetual rights.
- **Usage component where it fits naturally:** prepaid signed credit packs for bulk processing (whole case archives, discovery sets), and for site licenses a visible signed usage statement reviewed at renewal (true-up if seats or volume exceeded).
- **Royalties through OEM:** license your Hebrew engine per seat or per document to Israeli legal-tech and legal-AI vendors (Poly, Nevo, Takdin, practice-management software, Israeli legal AI startups) and to the enterprise DLP companies that lack good Hebrew. That is where "royalties per use" actually happens, because your partner's cloud already meters usage.

Tamper resistance: aim for "honest people stay honest." Sign licenses with Ed25519, bind to a soft machine fingerprint, detect clock rollback, obfuscate lightly, and enforce through contracts with firms.

Revenue reality check: 1,000 paying seats at around $300 per year is about $300,000 per year. That is a solid bootstrapped business but not venture scale without OEM deals, international expansion, or moving up to firm-wide gateways.

## 8. Legal and Liability Risks for You

- **Missed entity leads to a leak.** This is the risk that can end the company. Mitigations: mandatory review step before export (you cannot export without approving), clear positioning as "assistive minimization with human review, not guaranteed anonymization" (OpenAI's own model card says Privacy Filter is "not an anonymization, compliance, or a safety guarantee"), terms of service with limitation of liability capped at fees paid and disclaimer of consequential damages, a published measured recall figure with its limits, and professional liability (tech E&O) plus cyber insurance once you have customers. Consumer-protection rules may limit disclaimers for individuals; get an Israeli lawyer to draft terms.
- **Marketing claims.** Never say "anonymized", "GDPR compliant", "HIPAA compliant", or "safe to upload" unconditionally. Say "reduces identifiable information", "supports compliance", "documents your minimization step."
- **Medical device classification.** A text-minimization tool that makes no diagnostic or treatment claims is very unlikely to be a medical device in Israel, the US or the EU. Avoid clinical claims.
- **Open-source model licenses.** Apache 2.0 models (OpenAI Privacy Filter, GLiNER2-PII, Qwen 2.5/3 small models, DictaLM 3.0, which Dicta releases under a permissive license) are safe for commercial use; check each model card. Llama and Gemma use custom licenses with acceptable-use policies and attribution terms; usable, but read them. Watch dataset-driven license changes: a Basque fine-tune of GLiNER2-PII switched from Apache 2.0 to CC BY-NC-SA in October 2026 because of its training data. Verify DictaBERT's license before shipping it in a paid product.
- **Your employer (flag this first, not last).** Under section 132 of Israel's Patents Law, a "service invention" made by an employee "in consequence of his service and during the period of his service" belongs to the employer absent agreement otherwise, and your employment contract almost certainly has broader IP assignment, moonlighting, and conflict-of-interest clauses. As a compiler/ML engineer at a large tech company, an ML inference product is close enough to your day job to create real risk. Before writing serious code: read your contract, do not use employer hardware, time, code, or confidential knowledge, and get a written waiver or acknowledgement from your employer. Investors and acquirers will check this in due diligence. This is general information, not legal advice; spend a few thousand shekels on an Israeli employment/IP lawyer now.
- **Company formation.** An Israeli Ltd. is standard if you take Israel Innovation Authority money or investors; a licensed sole proprietorship (עוסק מורשה) is fine for early pilots but offers no liability shield. Given the leak-liability profile, incorporate before selling.

## 9. Go-to-Market

- **First customers: Israeli solo and small law firms (1 to 20 lawyers), then accountants.** Short sales cycle (days to weeks), owner decides, pain is acute, and the Bar opinion just made the issue front-page in the profession. Large firms already have Harvey and IT committees. Hospitals are 12 to 24 months.
- **Pilots:** 10 to 20 design-partner firms, free for 2 to 3 months in exchange for weekly feedback and permission to measure recall on their real documents on their premises.
- **Channels:** Israel Bar Association continuing education and district committees (an AI ethics talk after the new opinion is an easy invitation), legal-tech resellers and IT integrators who already service small firms, the Institute of Certified Public Accountants in Israel, legal publishers (Nevo, Takdin) as OEM or distribution partners, and LinkedIn/WhatsApp communities of lawyers.
- **Funding:** the Israel Innovation Authority's Tnufa page offers a "conditional grant of up to NIS 200,000 over a period of 12 months (80% of the approved budget)" and says entrepreneurs "do not have to leave their current job to establish a company"; secondary guides (Velo Labs, Outstand) add that the grant is repaid only through 3% royalties on revenue. That fits your situation well, subject to your employer issue.
- **Naming and positioning.** "Tomer Censors" has two problems: "censor" implies suppression of speech, which professionals and regulators do not want associated with client files, and it does not translate the value (use AI safely). The Bar opinion uses "התממה" (anonymization). Consider a name that signals trust and AI use, and run a trademark check in Israel, the US and EU. Position as "the safe way to use ChatGPT and Claude on client files, in Hebrew."
- **Demo that sells:** take a real-looking Hebrew pleading, run it, show the AI working on the pseudonymized version, paste the answer back, real names reappear, unplug the network cable during the demo.

### Product variants, ranked by priority

1. **Desktop app** (Windows first; Israeli law firms are overwhelmingly Windows and Word).
2. **Word add-in** (process the open document in place, then copy to AI). Lawyers live in Word.
3. **Clipboard / live mode** (detect and pseudonymize text pasted into the ChatGPT or Claude desktop apps or browser; Conseal's "Live Detect" shows demand).
4. **Firm server and local gateway** that sits between users and ChatGPT/Claude/the firm's own model, auto-redacting outgoing prompts and auto-rehydrating answers. Browser extensions and an MCP server for agents come later.

## 10. Better and Alternative Ways to Reach the Goal

- **Local privacy gateway (strongest long-term version).** Instead of "censor a file, upload, paste back," the user works normally in ChatGPT or Claude (or via the API inside the firm's tools), and a local proxy pseudonymizes every outgoing message and attachment and rehydrates every response. Higher engineering cost, much higher stickiness, natural per-seat pricing.
- **Be the Hebrew privacy engine inside other products (OEM).** Israeli legal-AI platforms (Poly, Nevo's AI, which Nevo says is used by almost all Israeli judges), DMS vendors, and the GenAI security vendors (Prompt/SentinelOne, Lasso) need good Hebrew detection. Licensing your engine gives you true usage royalties and sidesteps small-firm sales. This may be the best business even if the desktop app is your showcase.
- **Compliance evidence as a product.** Generate a per-document "minimization report": entities found by type, what the user approved, residual-risk flags, model version, timestamp, hash of the output. Pair it with a client-consent template aligned with the Bar opinion. This turns your tool from "nice to have" into "the thing I show if a client or the Bar asks."

## Things You Probably Did Not Think Of

1. The Israel Bar now says removing names is not enough and requires informed client consent for open AI platforms even when anonymization was performed. Your tool does not remove the consent step; it should help document it.
2. Pseudonymized data stays personal data for your user under GDPR and Israeli law, because they hold the mapping table.
3. The mapping file is the crown jewel. A stolen or emailed mapping file plus the AI chat history equals a full breach.
4. Hebrew prefixes and gender agreement mean naive string replacement both misses names and leaks that substitution happened.
5. Deleted tracked changes, comments, document properties and file names leak identities even if the body is perfect.
6. Black-box PDF redaction often leaves the text underneath.
7. Quasi-identifiers (small town plus profession plus rare event) re-identify people with no names, and LLM agents now do this cheaply.
8. Date shifting breaks HIPAA Safe Harbor, and replacing amounts can destroy the analysis for accountants.
9. The AI's answer may contain inflected or invented names the rehydrator cannot map.
10. USB execution is blocked in exactly the security-conscious places you want to sell to.
11. A hidden counter in a privacy tool is a reputational landmine if a security team finds it.
12. Detection models are now free and commoditized; OpenAI and Fastino are giving them away.
13. Direct competitors launched or announced in 2026 with almost your exact pitch (Conseal, AnonymFiles), and an Israeli legal-AI platform (Poly) already offers built-in Hebrew anonymization.
14. Your employment contract and section 132 of the Patents Law may give your employer a claim.
15. "Censor" is the wrong word for the value you create and may hurt sales.
16. The best royalty stream is probably OEM licensing to other vendors, not metering end users.

## Key Risks, Ranked by Severity

| Rank | Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|---|
| 1 | Missed identifier leads to a client data leak and a claim against you | Critical | High over time (no system has 100% recall) | Layered detection, mandatory review, honest recall reporting, limitation of liability, E&O/cyber insurance, never promise anonymity |
| 2 | Employer IP claim (section 132, contract) | Critical | Medium | Lawyer review and written waiver before serious development; clean-room separation |
| 3 | Commoditization and fast followers (Conseal, AnonymFiles, Poly, free models, Microsoft/OpenAI adding built-in redaction) | High | High | Compete on Hebrew quality, DOCX fidelity, Israeli compliance evidence, distribution and OEM; move fast |
| 4 | Legal premise erodes (enterprise AI with ZDR becomes acceptable; Bar requires consent regardless) | High | Medium | Position as defense in depth and evidence layer; support private/local models too |
| 5 | Hebrew recall falls short in real documents | High | Medium | Build proprietary Hebrew benchmark, pilot on real files, morphology-aware pipeline |
| 6 | Deployment friction (IT blocks, AV false positives, unsigned binaries) | Medium-high | High if USB-based | Signed installers, MDM deployment, security whitepaper |
| 7 | Over-redaction makes AI output useless, users abandon the tool | Medium | Medium | Profession presets, public-entity allowlists, preview, utility testing |
| 8 | Mapping file compromise | Medium-high | Low-medium | Encryption at rest, OS keystore, per-matter scope, expiry, never co-located with exports |
| 9 | Founder bandwidth (full-time job plus product plus sales) | Medium | High | Narrow MVP, Tnufa funding, consider a co-founder with legal-market sales experience |

## Recommended Phased Plan

**Phase 0 (weeks 0 to 2): clear the runway**
- Review your employment contract with an Israeli IP/employment lawyer; get a written acknowledgement or waiver from your employer.
- Interview 15 to 20 Israeli lawyers and accountants (solo to 20-person firms): what files, what AI they use today, would they pay NIS 100+ per month, what would their client or insurer require.
- Pick a new name and check trademarks.

**Phase 1 (weeks 2 to 8): MVP for Hebrew legal documents**
- Windows desktop app, signed installer.
- Input: DOCX and text PDF. Output: DOCX and TXT. Tracked changes accepted, comments and metadata stripped, neutral file names.
- Detection: Israeli validators and regex, DictaBERT-joint for Hebrew, GLiNER2-PII or OpenAI Privacy Filter for English, union of outputs.
- Consistent per-matter surrogates with gender-matched Hebrew and English name lists, prefix-aware replacement, email/handle variants.
- Review UI with mandatory approval; rehydration of pasted AI answers; encrypted local mapping store.
- Proprietary Hebrew test set (start with about 200 annotated synthetic documents); publish recall and precision internally every build.
- Zero network calls; built-in network self-test.

**Phase 2 (months 2 to 4): pilots and evidence**
- 10 to 20 design-partner firms; measure recall on real documents on their machines; iterate on misses.
- Add per-document minimization report and a client-consent template reviewed by an Israeli lawyer.
- Apply for Tnufa.
- Draft terms of service, privacy notice, security whitepaper.

**Phase 3 (months 4 to 6): paid launch in Israel**
- Per-seat subscription (around NIS 99 to 149 per month, discounted annual), signed expiring licenses with online or QR/offline renewal, onboarding fee for firm deployments.
- Word add-in; XLSX and EML/MSG support; date shifting and numeric scaling modes; quasi-identifier warnings via an optional local LLM pass.
- Bar association and accountant association talks; first reseller.
- Buy E&O and cyber insurance.

**Phase 4 (months 6 to 12): expand and add recurring depth**
- Local OCR for scanned Hebrew PDFs; PowerPoint.
- Firm server with shared matter dictionaries, central licensing, usage statements for true-up; prepaid credit packs for bulk processing.
- First OEM conversations: Israeli legal-AI and legal-publisher platforms, GenAI DLP vendors needing Hebrew.

**Phase 5 (year 2): gateway and international**
- Local privacy gateway that auto-pseudonymizes prompts and auto-rehydrates answers for ChatGPT, Claude and private models; MCP server for agents.
- English-market launch leaning on ABA 512 and Oregon 2025-205 language, plus Arabic as a natural adjacent RTL language.

## Caveats

- Several competitors are very new: Conseal launched on October 23, 2026 (source is its own press release on LawSites), and AnonymFiles was still pre-launch; their claims are self-reported and unverified. Poly's customer claims are vendor marketing and its pricing was not obtained.
- Model accuracy figures (OpenAI Privacy Filter, GLiNER2-PII) are vendor-reported on specific benchmarks; none is validated on Hebrew legal documents. Treat them as directional.
- Israeli lawyer counts vary by source: about 90,000 licensed and about 76,000 active per Bar data cited by Robus and LawBuzz, while News1 reported that license numbers passed 100,000 in October 2024 and court data shows about 66,000 active.
- The Israel Bar opinion text was reviewed through summaries by Pearl Cohen and Haim Ravia rather than the full Hebrew original; read the original (opinion 60-24) before quoting it in marketing.
- Nothing in this report is legal advice; employment IP, terms of service, and medical-sector questions need an Israeli lawyer.

## Sources

- [pearlcohen](https://www.pearlcohen.com/israel-bar-association-issues-an-expanded-ethics-opinion-on-lawyers-use-of-ai/)
- [polylm](https://www.polylm.com/blog/document-anonymization-ai-data-protection)
- [anonym](https://anonym.legal/features)
- [lawnext](https://www.lawnext.com/2026/10/conseal-a-new-on-device-privacy-app-masks-sensitive-client-data-before-it-reaches-ai-tools-like-chatgpt-and-claude.html)
- [anonym](https://anonym.legal/compare/protecto)
- [anonymfiles](https://anonymfiles.com/en/)
- [fastino](https://fastino.ai/blog/gliner2-pii-open-source-privacy-filtering-with-pii-detection)
- [prnewswire](https://www.prnewswire.com/news-releases/fastino-labs-creator-of-gliner-releases-two-state-of-the-art-language-models-1-000x-smaller-than-frontier-302772349.html)
- [pearlcohen](https://www.pearlcohen.com/israeli-bar-associations-ethical-guidelines-on-using-ai/)
- [law](https://www.law.co.il/news/2026/09/19/israel-bar-ethics-rules-for-ai-use/)
- [goodwinlaw](https://www.goodwinlaw.com/en/insights/publications/2025/09/alerts-technology-dpc-personal-data-or-not)
- [twobirds](https://www.twobirds.com/en/insights/2025/eu-the-srb-decision-a-new-era-for-personal-data-and-data-processing-agreements)
- [arxiv](https://arxiv.org/html/2602.16800v1)
- [openai](https://openai.com/index/introducing-openai-privacy-filter/)
- [letsdatascience](https://letsdatascience.com/news/openai-releases-privacy-filter-for-pii-masking-17c0d474)
- [fastino](https://fastino.ai/models/gliner2-pii)
- [arxiv](https://arxiv.org/pdf/2510.21372)
- [huggingface](https://huggingface.co/dicta-il/dictabert-ner)
- [huggingface](https://huggingface.co/dicta-il/dictabert-joint)
- [dicta](https://dicta.org.il/publications/DictaLM_3_0___Techincal_Report.pdf)
- [huggingface](https://huggingface.co/dicta-il/DictaLM-3.0-1.7B-Thinking-GGUF)
- [arxiv](https://arxiv.org/pdf/2604.21352)
- [arxiv](https://arxiv.org/pdf/2512.11502)
- [herzoglaw](https://herzoglaw.co.il/en/news-and-insights/herzog-expands-legal-tech-capabilities-with-harvey-ai/)
- [meitar](https://meitar.com/en/meitar-and-harvey-announce-partnership-to-employ-legal-ai-technology/)
- [openai](https://openai.com/index/introducing-data-residency-in-europe/)
- [robus](https://www.robus.co.il/%D7%93%D7%95%D7%B4%D7%97-%D7%A9%D7%A0%D7%AA%D7%99-2024-%D7%A4%D7%A2%D7%99%D7%9C%D7%95%D7%AA-%D7%91%D7%99%D7%A0%D7%9C%D7%90%D7%95%D7%9E%D7%99%D7%AA-%D7%91%D7%A1%D7%A7%D7%98%D7%95%D7%A8-%D7%94%D7%9E/)
- [lawbuzz](https://lawbuzz.co.il/lawnews/162054/)
- [edenai](https://www.edenai.co/post/best-document-redaction-apis)
- [anonym](https://anonym.legal/pricing)
- [anonym](https://anonym.legal/blog/presidio-vs-anonym-legal-managed-saas-roi-2025)
- [anonym](https://anonym.legal/terms)
- [polylm](https://www.polylm.com/law)
- [deepwiki](https://deepwiki.com/8400TheHealthNetwork/HebSafeHarbor)
- [tonic](https://www.tonic.ai/pricing)
- [vendr](https://www.vendr.com/marketplace/tonicai)
- [codeables](https://codeables.dev/article/tonic-pricing-what-s-included-in-structural-vs-textual-vs-fabricate)
- [weblaw](https://weblaw.ch/en/produkte/anonymisierung)
- [nymiz](https://www.nymiz.com/ai-and-data-anonymization/)
- [pseudonymizer](https://pseudonymizer.eu/)
- [meetily](https://meetily.ai/llm-privacy/openai)
- [spellbook](https://spellbook.com/learn/is-chatgpt-private)
- [dataguidance](https://www.dataguidance.com/news/israel-bar-association-publishes-opinion-use-ai)
- [calcalistech](https://www.calcalistech.com/ctechnews/article/hkyl4iftmx)
- [nycbar](https://www.nycbar.org/wp-content/uploads/2025/05/20221469-AnalysisEthicsGuidanceAI.pdf)
- [thelegalprompts](https://thelegalprompts.com/blog/ai-legal-ethics-bar-association-guidelines)
- [osbar](https://www.osbar.org/_docs/ethics/2025-205.pdf)
- [lexology](https://www.lexology.com/library/detail.aspx?g=bf850c35-d439-4cdd-a53d-a6792f4f5467)
- [chambers](https://practiceguides.chambers.com/practice-guides/digital-healthcare-2026/israel)
- [legal500](https://www.legal500.com/intelligence/israel/food-drugs-healthcare-life-sciences/israel-life-sciences-&-healthcare-%E2%80%93-regulatory-overview-2026)
- [sidley](https://datamatters.sidley.com/2025/10/10/eu-court-of-justice-issues-landmark-judgment-on-concept-of-personal-data/)
- [taylorwessing](https://www.taylorwessing.com/en/insights-and-events/insights/2025/09/analysis-of-the-cjeu-judgment)
- [ebnlaw](https://www.ebnlaw.co.il/media-center/draft-guidance-from-the-israeli-privacy-protection-authority/)
- [nemko](https://digital.nemko.com/regulations/ai-regulation-israel)
- [bigid](https://bigid.com/blog/what-israel-amendment-13-means-for-businesses-in-2025/)
- [chambers](https://practiceguides.chambers.com/practice-guides/data-protection-privacy-2026/israel)
- [huggingface](https://huggingface.co/fastino/gliner2-privacy-filter-PII-multi)
- [replicate](https://replicate.com/zeke/openai-privacy-filter/readme)
- [protegrity](https://www.protegrity.com/blog/open-ai-privacy-filter-protegrity-pii-and-the-data-lesson/)
- [helpnetsecurity](https://www.helpnetsecurity.com/2026/04/23/openai-privacy-filter-personally-identifiable-information/)
- [wibu](https://www.wibu.com/magazine/keynote-articles/article/detail/license-monitoring-with-codemeter.html)
- [wibu](https://www.wibu.systems/smart-licensing/license-models/flexible-software-licensing-with-pay-as-per-use/)
- [wibu](https://www.wibu.com/products/codemeter-license-management/codemeter-license-reporting.html)
- [wibu](https://www.wibu.com/us/wibu-systems-webinars/consumption-based-licensing.html)
- [github](https://github.com/openai/privacy-filter/wiki)
- [c-sharpcorner](https://www.c-sharpcorner.com/news/openai-releases-privacy-filter-an-openweight-model-for-pii-detection)
- [researchgate](https://www.researchgate.net/publication/400395547_Dicta-LM_30_Advancing_The_Frontier_of_Hebrew_Sovereign_LLMs)
- [huggingface](https://huggingface.co/tknika/gliner2-PII-basque)
- [wipo](https://www.wipo.int/wipolex/en/text/495413)
- [lexology](https://www.lexology.com/library/detail.aspx?g=80178348-af89-43dc-b263-694089c6b91d)
- [nevo](https://www.nevo.co.il/)
- [arxiv](https://arxiv.org/pdf/2601.05918)
- [asanify](https://asanify.com/global-employer-of-record/israel/employment-laws/)
- [news1](https://www.news1.co.il/Archive/001-D-491922-00.html)
- [topdin](https://www.topdin.co.il/lawyers/stats)
