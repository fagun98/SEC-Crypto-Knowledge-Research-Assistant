**CRYPTO REGULATORY INSIGHT**

**CRI Regulatory Ontology**

Taxonomy Specification for Knowledge Base Classification,

Ingestion Pipeline Tagging, and Intelligence Product Consistency

Version 1.0 | April 2026

**CONFIDENTIAL - For Internal CRI Use Only**

Prepared for the CRI Product Team

Crypto Regulatory Insight (CRI)

# **1\. Executive Summary**

This document defines the CRI Regulatory Ontology-a structured classification framework that governs how every document, regulatory event, and stakeholder position is tagged, stored, retrieved, and presented across CRI's intelligence products. The ontology serves as the connective tissue between CRI's Pinecone knowledge base, its RAG chatbot, analytical reports, newsletters, and future research agent capabilities.

The ontology operates on two primary axes. **Axis 1 (Regulatory Domain)** classifies content by the substantive area of law or regulation implicated-what compliance question is at stake. **Axis 2 (Regulatory Lifecycle Stage)** classifies content by where it sits in the regulatory process-from proposed rulemaking through enforcement and potential revocation.

A third dimension-the **Durability Tier**-is applied as a cross-cutting attribute, reflecting CRI's core analytical distinction between Commission-level interpretations (durable) and staff-level guidance (revocable). This durability distinction is the primary value-add CRI offers its clients and must be consistently surfaced across all outputs.

## **1.1 Design Principles**

- **Compliance-Decision Driven:** Domains are defined by the compliance questions clients actually face, not by broad topic labels
- **Durability as Core Lens:** Every tagged document carries a durability assessment distinguishing statutory protections from revocable guidance
- **Machine-Readable and Human-Interpretable:** Tags serve both as Pinecone metadata filters and as user-facing analytical categories
- **Extensible:** New sub-domains and regulatory bodies can be added without restructuring the core taxonomy
- **Cross-Product Consistency:** The same taxonomy drives the chatbot, newsletters, roundtable analysis, and research agent outputs

# **2\. Axis 1: Regulatory Domain Classification**

Regulatory Domains decompose the broad crypto regulatory landscape into the specific legal and compliance questions that drive client decision-making. Each domain maps to identifiable statutory authorities, regulatory bodies, and compliance obligations. Documents may carry multiple domain tags when they span regulatory areas.

| **Domain Code** | **Domain Name**                  | **Core Compliance Question**                                               |
| --------------- | -------------------------------- | -------------------------------------------------------------------------- |
| **AC**          | Asset Classification             | Is this token a security, commodity, stablecoin, collectible, or tool?     |
| **RO**          | Registration & Offering          | What registration or exemption pathway applies to this token offering?     |
| **MS**          | Market Structure                 | What trading venue, broker-dealer, or ATS requirements apply?              |
| **CU**          | Custody & Safeguarding           | How must this asset be held, controlled, and protected for clients?        |
| **SC**          | Stablecoin Regulation            | What issuer licensing, reserve, and redemption rules apply?                |
| **DP**          | DeFi & Protocol Governance       | How do decentralized protocols interact with securities/commodities law?   |
| **CB**          | Cross-Border & International     | How do non-U.S. frameworks (MiCA, FCA) interact with U.S. requirements?    |
| **EL**          | Enforcement & Litigation         | What enforcement precedents and litigation outcomes shape compliance?      |
| **SP**          | Systemic Risk & Prudential       | What macro-prudential, AML/sanctions, and financial stability rules apply? |
| **IP**          | Investor Protection & Disclosure | What disclosure, suitability, and conduct obligations apply?               |

## **2.1 Domain AC: Asset Classification**

Covers all determinations regarding whether a digital asset constitutes a security (investment contract under Howey, note under Reves, profit-sharing arrangement), a commodity, or falls into a non-securities category. This is the foundational domain-classification determines which regulatory regime applies to all downstream activities.

### **Sub-Domains**

| **Code**   | **Sub-Domain**                       | **Scope**                                                                                                                                           |
| ---------- | ------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| **AC-HOW** | Howey Investment Contract Analysis   | Four-prong analysis: investment of money, common enterprise, expectation of profits, efforts of others                                              |
| **AC-REV** | Reves Note Analysis                  | Family resemblance test for instruments structured as notes; implications for DeFi lending protocols                                                |
| **AC-TAX** | Joint SEC-CFTC Taxonomy (March 2026) | Five-category framework: digital commodities, digital collectibles, digital tools, stablecoins, digital securities                                  |
| **AC-DEC** | Sufficient Decentralization          | Analysis of when protocol decentralization dissipates the "efforts of others" prong; control-based framework                                        |
| **AC-SEC** | Secondary Market Status              | Whether tokens that were securities at issuance remain securities in secondary trading; disaggregation of investment contract from underlying token |
| **AC-NFT** | NFT / Collectible Classification     | Facts-and-circumstances analysis for non-fungible tokens; Harper v. O'Neal precedent                                                                |
| **AC-MEM** | Memecoin / Non-Utility Token Status  | SEC CTF staff analysis excluding memecoins from investment contract definition under Howey                                                          |

### **Regulatory Authority & Body Mapping**

- **Statutory Authority:** Securities Act §2(a)(1); Exchange Act §3(a)(10); SEC v. Howey (1946); Reves v. Ernst & Young (1990); SEC Interpretive Release No. 33-11412 (March 2026); Commodity Exchange Act §1a(9)
- **Regulatory Bodies:** SEC (Division of Corporation Finance, Division of Trading and Markets); CFTC; SEC Crypto Task Force
- **CTF Roundtable Mapping:** Roundtable 1 (Securities Status, March 2025); Roundtable 6 (DeFi, June 2025) - directly addresses Howey, Reves, common enterprise, and decentralization arguments from Belton, Cohen, Jennings, Reiners, Seira, and Guillen

## **2.2 Domain RO: Registration & Offering**

Covers the regulatory pathways available for primary distributions of digital assets, including full registration, exemptions (Reg D, Reg S, Reg A+, Reg CF), and proposed safe harbors. Addresses the capital formation lifecycle from token minting through public listing.

### **Sub-Domains**

| **Code**   | **Sub-Domain**                      | **Scope**                                                                                                                                   |
| ---------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| **RO-REG** | Full Registration Pathways          | S-1/S-3 filing requirements, SEC review process for token offerings, disclosure frameworks                                                  |
| **RO-EXM** | Exemptive Relief & Safe Harbors     | Reg D (accredited investors), Reg A+ (mini-IPO), Reg S (offshore), Reg CF (crowdfunding); proposed token-specific exemptions                |
| **RO-DIS** | Offering Disclosure Requirements    | SEC Division of Corp Finance staff statement on crypto offering disclosures (April 2025); required risk factors, token economics disclosure |
| **RO-AIR** | Airdrops, Mining & Staking Receipts | Whether distribution mechanisms (airdrops, mining rewards, staking receipts) constitute securities offerings                                |
| **RO-ICA** | Investment Company Act Implications | When token pools or DeFi protocols trigger ICA registration; BlockFi settlement precedent                                                   |

### **Regulatory Authority & Body Mapping**

- **Statutory Authority:** Securities Act §5, §4(a)(2), Reg D, Reg A+, Reg S, Reg CF; Investment Company Act of 1940
- **Regulatory Bodies:** SEC (Division of Corporation Finance); SEC Crypto Task Force; FINRA (for broker-dealer underwriting obligations)
- **CTF Roundtable Mapping:** Roundtable 2 (Public Offerings, April 2025) - Brennan's interim framework, Guillen's exemptive authority arguments, Garrison's BlockFi reference

## **2.3 Domain MS: Market Structure**

Covers regulatory requirements for venues where digital assets are traded, including national securities exchanges, ATSs, broker-dealers, and decentralized trading protocols. Addresses the transition from the SPBD framework to standard broker-dealer accommodation of digital assets.

### **Sub-Domains**

| **Code**   | **Sub-Domain**               | **Scope**                                                                                                             |
| ---------- | ---------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| **MS-ATS** | ATS Registration & Operation | Requirements for operating an alternative trading system for digital asset securities                                 |
| **MS-BDR** | Broker-Dealer Obligations    | Post-SPBD framework requirements; standard broker-dealer accommodation of digital asset securities and non-securities |
| **MS-DEX** | DEX / AMM Regulatory Status  | Regulatory treatment of decentralized exchanges, automated market makers, and liquidity pools                         |
| **MS-CLE** | Clearing & Settlement        | T+1/T+0 settlement, DLT-based settlement finality, DTCC and blockchain interoperability                               |
| **MS-WAC** | Williams Act & Aggregation   | Token accumulation reporting requirements; Schedule 13D/13G implications for large token holders                      |

### **Regulatory Authority & Body Mapping**

- **Statutory Authority:** Exchange Act §6, §15(a), Reg ATS, Rule 15c3-1 (Net Capital); Williams Act
- **Regulatory Bodies:** SEC (Division of Trading and Markets); FINRA; DTCC
- **CTF Roundtable Mapping:** Roundtable 3 (Trading, April 2025) - Cohen's practical secondary market implications, Garrison's SEC mission focus

## **2.4 Domain CU: Custody & Safeguarding**

Covers how digital assets must be held, controlled, and protected when held on behalf of clients. This domain spans the investment adviser custody rule, broker-dealer customer protection rule, qualified custodian requirements, and the technical infrastructure (MPC, multi-sig, cold storage) for demonstrating possession or control.

### **Sub-Domains**

| **Code**   | **Sub-Domain**                     | **Scope**                                                                                                               |
| ---------- | ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| **CU-IAC** | Investment Adviser Custody Rule    | Rule 206(4)-2 under the Advisers Act; qualified custodian standards for digital assets                                  |
| **CU-BDC** | Broker-Dealer Customer Protection  | Rule 15c3-3 possession or control requirements; February 2026 FAQ clarifications                                        |
| **CU-SPB** | SPBD Framework (Legacy)            | 2020 Special Purpose Broker-Dealer safe harbor; now optional but not rescinded; legacy compliance considerations        |
| **CU-TEC** | Custody Technology Standards       | MPC/multi-sig, cold storage, key management, private key security; DLT-specific control demonstrations                  |
| **CU-UCC** | UCC Treatment                      | UCC Articles 8 & 12 application to digital assets; commercial law certainty for custody arrangements                    |
| **CU-BNK** | Banking Custody & SAB 121 Reversal | OCC, FDIC, Fed treatment of bank custody for digital assets; SAB 121 rescission (SAB 122); bank balance sheet treatment |
| **CU-SIP** | SIPA/SIPC Coverage                 | Applicability of Securities Investor Protection Act to digital asset accounts                                           |

### **Regulatory Authority & Body Mapping**

- **Statutory Authority:** Advisers Act §206(4); Exchange Act Rule 15c3-3; UCC Articles 8, 12; SIPA; SAB 122 (rescinding SAB 121)
- **Regulatory Bodies:** SEC (Divisions of Investment Management, Trading and Markets); FINRA; OCC; FDIC; Federal Reserve
- **CTF Roundtable Mapping:** Roundtable 4 (Custody, April 2025) - central focus; key participants from Fireblocks, Anchorage Digital, BitGo

## **2.5 Domain SC: Stablecoin Regulation**

Covers the comprehensive federal framework for payment stablecoins established by the GENIUS Act (signed July 2025), including issuer licensing, reserve requirements, redemption obligations, yield restrictions, and the dual federal-state oversight structure. Also addresses SEC staff guidance on stablecoin securities status.

### **Sub-Domains**

| **Code**   | **Sub-Domain**                    | **Scope**                                                                                                           |
| ---------- | --------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| **SC-GEN** | GENIUS Act Framework              | Federal licensing as Permitted Payment Stablecoin Issuer (PPSI); OCC and FDIC implementing rules                    |
| **SC-RES** | Reserve & Redemption Requirements | 1:1 backing by high-quality liquid assets; two-business-day redemption; monthly audit requirements                  |
| **SC-YLD** | Yield Restriction                 | Rebuttable presumption against issuer/affiliate yield payments; "earn program" implications                         |
| **SC-THR** | \$10 Billion Threshold            | Mandatory transition to federal supervision for state-qualified issuers exceeding \$10B market cap                  |
| **SC-SEC** | Stablecoin Securities Status      | SEC Division of Corp Finance staff statement (April 2025) on when stablecoin transactions implicate securities laws |
| **SC-TOK** | Tokenized Deposits                | FDIC proposed rule clarifying tokenized deposits are not payment stablecoins; GENIUS Act carve-out                  |

### **Regulatory Authority & Body Mapping**

- **Statutory Authority:** GENIUS Act (Pub. L. signed July 2025); OCC NPRM (March 2026); FDIC NPRM (April 2026)
- **Regulatory Bodies:** OCC; FDIC; Federal Reserve; SEC (Division of Corporation Finance); State regulators (NYDFS, Wyoming)
- **CTF Roundtable Mapping:** Not directly addressed in CTF roundtables, but GENIUS Act compliance mapping is a priority intelligence product for CRI clients

## **2.6 Domain DP: DeFi & Protocol Governance**

Covers the regulatory treatment of decentralized protocols, smart contracts, governance tokens, fee-switch mechanisms, DAOs, and activities like staking, wrapping, and restaking. This domain captures the highest-priority unresolved regulatory questions identified in the March 2026 joint interpretation.

### **Sub-Domains**

| **Code**   | **Sub-Domain**                  | **Scope**                                                                                                                         |
| ---------- | ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| **DP-FEE** | Fee-Switch & Revenue Accrual    | Whether enabling protocol revenue distribution to token holders creates securities; programmatic vs. human-directed value accrual |
| **DP-GOV** | Governance Token Classification | Concentration analysis; whether governance rights create investment contract; voting power as "efforts of others"                 |
| **DP-DAO** | DAO Legal Liability             | Legal entity status of DAOs; liability exposure for governance participants; state DAO legislation                                |
| **DP-STK** | Staking & Restaking             | Reeves test application to staking services; staking receipt tokens; liquid staking derivatives                                   |
| **DP-WRP** | Wrapping & Bridging             | Regulatory treatment of wrapped tokens; cross-chain bridge protocols; custody implications of wrapping                            |
| **DP-LEN** | DeFi Lending & Borrowing        | Regulatory treatment of lending protocols; Reves note analysis for DeFi lending; yield generation                                 |

### **Regulatory Authority & Body Mapping**

- **Statutory Authority:** Howey "efforts of others" prong; Reves note test; SEC CTF discussions; CFTC commodity swap authority
- **Regulatory Bodies:** SEC (Crypto Task Force, Division of Enforcement); CFTC
- **CTF Roundtable Mapping:** Roundtable 6 (DeFi, June 2025) - directly addresses fee-switch (Seira), control framework (Jennings), note analysis (Belton); flagged as highest-priority unresolved gap in March 2026 release

## **2.7 Domain CB: Cross-Border & International**

Covers non-U.S. regulatory frameworks and their interaction with U.S. requirements. Critical for CRI clients operating across jurisdictions or seeking to understand comparative regulatory approaches.

### **Sub-Domains**

| **Code**   | **Sub-Domain**                   | **Scope**                                                                                                     |
| ---------- | -------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| **CB-MCA** | EU MiCA Framework                | CASP authorization, white paper requirements, stablecoin (ART/EMT) rules, July 2026 full enforcement deadline |
| **CB-FCA** | UK FCA Crypto Regime             | FCA registration, financial promotions rules, consumer duty obligations for crypto                            |
| **CB-EQV** | Equivalence & Mutual Recognition | Cross-border regulatory recognition; passporting arrangements; reverse solicitation under MiCA                |
| **CB-TRL** | Travel Rule (International)      | FATF Travel Rule implementation; EU Transfer of Funds Regulation; cross-jurisdictional data sharing           |
| **CB-COM** | Comparative Analysis             | Side-by-side comparison of U.S., EU, UK, and other jurisdictional approaches to specific regulatory questions |

### **Regulatory Authority & Body Mapping**

- **Statutory Authority:** MiCA Regulation (EU 2023/1114); UK Financial Services and Markets Act 2023; FATF Standards
- **Regulatory Bodies:** ESMA; EBA; FCA; FATF; individual EU Member State NCAs
- **CTF Roundtable Mapping:** Not directly covered in CTF roundtables; identified as benchmark gap area requiring expanded KB sources

## **2.8 Domain EL: Enforcement & Litigation**

Tracks enforcement actions, litigation outcomes, settlements, and precedent development. Captures both SEC and CFTC enforcement as well as private litigation. Critical for understanding how regulatory positions are actually applied and for identifying emerging compliance risks.

### **Sub-Domains**

| **Code**   | **Sub-Domain**                       | **Scope**                                                                                             |
| ---------- | ------------------------------------ | ----------------------------------------------------------------------------------------------------- |
| **EL-SEC** | SEC Enforcement Actions              | Enforcement releases, administrative proceedings, settled orders; pattern analysis across token types |
| **EL-CFT** | CFTC Enforcement Actions             | CFTC enforcement against crypto derivatives, DeFi protocols, and unregistered offerings               |
| **EL-LIT** | Private Litigation                   | Class actions, derivative suits, and individual claims (e.g., Harper v. O'Neal for NFTs)              |
| **EL-DIS** | Enforcement Dismissals & Withdrawals | Tracking SEC dismissals (Coinbase, Ripple context); policy lock-in concerns (Reiners)                 |
| **EL-STL** | Settlement Terms & Conditions        | Structured remedies, disgorgement, injunctions, compliance monitor requirements                       |

### **Regulatory Authority & Body Mapping**

- **Statutory Authority:** Securities Act §17(a); Exchange Act §10(b), Rule 10b-5; CEA enforcement provisions
- **Regulatory Bodies:** SEC (Division of Enforcement); CFTC (Division of Enforcement); DOJ (for parallel criminal proceedings); State AGs
- **CTF Roundtable Mapping:** Cross-cutting across all roundtables; Stark's externalities emphasis, Reiners' policy lock-in warnings, Garrison's BlockFi example

## **2.9 Domain SP: Systemic Risk & Prudential**

Covers macro-prudential oversight, AML/sanctions compliance, financial stability assessments, and the interplay between crypto markets and the broader financial system. Addresses jurisdictional boundaries between SEC, CFTC, FinCEN, OFAC, and FSOC.

### **Sub-Domains**

| **Code**   | **Sub-Domain**                | **Scope**                                                                                               |
| ---------- | ----------------------------- | ------------------------------------------------------------------------------------------------------- |
| **SP-AML** | AML / KYC / Sanctions         | BSA compliance, FinCEN requirements, OFAC sanctions screening for digital assets                        |
| **SP-SYS** | FSOC Systemic Risk Assessment | Financial Stability Oversight Council crypto reviews since 2018; interconnectivity analysis             |
| **SP-BNK** | Banking Guardrails            | Federal banking agency restrictions/permissions for bank engagement with digital assets                 |
| **SP-PRI** | Privacy & Surveillance        | Financial surveillance framework; privacy-preserving technology treatment; CTF Roundtable 5 discussions |

### **Regulatory Authority & Body Mapping**

- **Statutory Authority:** Bank Secrecy Act; USA PATRIOT Act; FSOC authority under Dodd-Frank §113; IEEPA (sanctions)
- **Regulatory Bodies:** FinCEN; OFAC; FSOC; OCC; FDIC; Federal Reserve
- **CTF Roundtable Mapping:** Roundtable 5 (Financial Surveillance & Privacy, Dec 2025) - Garrison's jurisdictional boundaries, Stark's externalities, Schiffrin's regulator competency arguments

## **2.10 Domain IP: Investor Protection & Disclosure**

Covers ongoing disclosure obligations, suitability standards, retail investor protections, and the broader investor protection framework. Addresses both registered entity obligations and the emerging disclosure frameworks for crypto assets.

### **Sub-Domains**

| **Code**   | **Sub-Domain**                    | **Scope**                                                                                                  |
| ---------- | --------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| **IP-PER** | Periodic Disclosure Obligations   | 10-K/10-Q equivalents for token projects; ongoing material event reporting                                 |
| **IP-SUI** | Suitability & Conduct Standards   | Broker-dealer suitability obligations; investment adviser fiduciary duty for digital asset recommendations |
| **IP-RET** | Retail Investor Protections       | Specific protections for retail participants; FOMO concerns; Celsius-type victim protections               |
| **IP-MKT** | Marketing & Advertising Standards | Fair and balanced communications about digital assets; social media promotion rules                        |

### **Regulatory Authority & Body Mapping**

- **Statutory Authority:** Exchange Act §13 (periodic reporting); Advisers Act §206 (fiduciary duty); FINRA Rules 2111 (Suitability), 2210 (Communications)
- **Regulatory Bodies:** SEC (Divisions of Corporation Finance, Investment Management); FINRA; CFPB (consumer complaints)
- **CTF Roundtable Mapping:** Cross-cutting; Brummer's regulatory debt concept, Schiffrin's retail investor marketing concerns, Stark's FOMO and victim statements

# **3\. Axis 2: Regulatory Lifecycle Stage**

Every document in the CRI knowledge base is tagged with a lifecycle stage indicating where it sits in the regulatory process. This classification enables CRI to present users with a complete picture of any regulatory topic: here is the final rule, here is the pending proposal that would modify it, here is the staff guidance that is potentially revocable, and here is the enforcement action that shows how it is being applied.

| **Code**     | **Stage**                | **Document Types**                                                                                                                        | **Analytical Significance**                                                                                              |
| ------------ | ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| **PRE**      | Pre-Regulatory / Concept | Concept releases, requests for information, advance notices of proposed rulemaking, CTF roundtable discussions, written input submissions | Not yet a formal regulatory position; informational value for anticipating regulatory direction                          |
| **PROP**     | Proposed                 | Notices of proposed rulemaking (NPRMs), proposed interpretive releases, staff concept papers open for comment                             | Subject to change based on comments; indicates likely regulatory direction but not yet binding                           |
| **INTPR**    | Interpretive / Guidance  | Staff statements, no-action letters, FAQs, Commissioner speeches, SEC/CFTC staff bulletins, SABs                                          | Provides compliance guidance but may be revocable; durability depends on authority level (see Section 4)                 |
| **FINAL**    | Final / Adopted          | Commission-level rules and orders, joint agency interpretive releases (e.g., March 2026 taxonomy), enacted statutes (e.g., GENIUS Act)    | Binding; represents the current authoritative position; highest durability tier                                          |
| **ENFORCED** | Enforced / Litigated     | Enforcement actions, settled orders, court opinions, consent decrees, administrative proceedings                                          | Shows how regulatory positions are applied in practice; may extend or narrow written guidance                            |
| **SUPER**    | Superseded / Revoked     | Withdrawn staff guidance, rescinded SABs (e.g., SAB 121), overturned rules, preempted state laws                                          | Historical context; no longer represents current regulatory position but may remain relevant for understanding evolution |

## **3.1 Lifecycle Transition Tracking**

When a document's lifecycle stage changes (e.g., a proposed rule becomes final, or staff guidance is withdrawn), CRI's ingestion pipeline should create a transition record linking the old and new documents. This enables the research agent to automatically identify when regulatory positions have evolved and to surface the full lineage of a regulatory development to users.

Example: SAB 121 (lifecycle: SUPER, superseded January 2025) → SAB 122 (lifecycle: INTPR, current staff guidance) → February 2026 FAQs (lifecycle: INTPR, elaborating on post-SAB 122 bank custody treatment).

# **4\. Durability Tier Classification**

The durability tier is CRI's signature analytical attribute-the cross-cutting dimension that distinguishes CRI from generic regulatory intelligence products. Every document is assessed for durability: how resistant is this regulatory position to change by a subsequent administration, commission vote, or staff turnover? This assessment directly drives the compliance advice CRI provides to clients.

| **Tier** | **Label**                   | **Includes**                                                                                                         | **Reversal Resistance**                                                                            |
| -------- | --------------------------- | -------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| **T1**   | **Statutory**               | Enacted legislation (GENIUS Act, Securities Act, CEA); can only be changed by Congress                               | Highest; immune to agency-level change                                                             |
| **T2**   | **Commission-Level**        | Commission votes, joint interpretive releases (March 2026 taxonomy), formal rules adopted through notice-and-comment | High; requires new Commission vote to modify; politically costly to reverse                        |
| **T3**   | **Judicial Precedent**      | Court opinions (Howey, Reves, Ripple), consent decrees with precedential value                                       | High; binding on parties; persuasive authority that shapes future enforcement                      |
| **T4**   | **Staff Guidance**          | Staff statements, no-action letters, FAQs, SABs, Commissioner speeches (in personal capacity)                        | Moderate to Low; can be withdrawn by staff without Commission vote; new administration can rescind |
| **T5**   | **Informal / Transitional** | CTF roundtable discussions, written input submissions, concept releases, blog posts                                  | Low; informational only; no binding authority but may signal future direction                      |

## **4.1 Durability Assessment Methodology**

During the CRI enrichment pass (Claude API processing), each ingested document is assessed against three durability factors:

- **Authority Level:** Who issued the document? Congress > Commission vote > Division/Office staff > Individual Commissioner > Staff member
- **Procedural Entrenchment:** Did the document go through notice-and-comment rulemaking, or was it issued unilaterally? APA-compliant rules are harder to reverse
- **Political Economy:** How politically costly would reversal be? Documents that unlock market activity (e.g., the March 2026 taxonomy enabling institutional capital deployment) create policy lock-in that makes reversal practically difficult even if procedurally possible

## **4.2 Client-Facing Durability Indicators**

CRI outputs should surface durability in user-facing interfaces using consistent visual or textual indicators. Suggested implementation:

- **Statutory (T1):** "Legislatively established; requires Congressional action to change"
- **Commission-Level (T2):** "Commission-adopted; durable but subject to future Commission action"
- **Staff Guidance (T4):** "Staff-level guidance; potentially revocable without Commission vote"

# **5\. Document Metadata Schema**

Every document chunk ingested into CRI's Pinecone knowledge base carries the following metadata fields. These fields serve dual purposes: they enable structured retrieval (via Pinecone metadata filtering) and they drive consistent presentation across CRI outputs.

| **Field Name**            | **Type**   | **Values / Format**                                                                                                                                          | **Description**                                                          |
| ------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------ |
| **domain_primary**        | String     | AC, RO, MS, CU, SC, DP, CB, EL, SP, IP                                                                                                                       | Primary regulatory domain (required; single value)                       |
| **domain_secondary**      | String\[\] | Array of domain codes                                                                                                                                        | Additional domains implicated (optional; enables cross-domain retrieval) |
| **subdomain**             | String\[\] | AC-HOW, CU-BDC, etc.                                                                                                                                         | Specific sub-domain tags (one or more)                                   |
| **lifecycle_stage**       | String     | PRE, PROP, INTPR, FINAL, ENFORCED, SUPER                                                                                                                     | Current regulatory lifecycle stage (required)                            |
| **durability_tier**       | String     | T1, T2, T3, T4, T5                                                                                                                                           | Durability assessment (required)                                         |
| **source_type**           | String     | interpretive_release, staff_statement, enforcement_release, rulemaking, legislation, roundtable, written_input, speech, court_opinion, no_action_letter, FAQ | Document classification by type                                          |
| **regulatory_body**       | String\[\] | SEC, CFTC, OCC, FDIC, Fed, ESMA, FCA, Congress, Court                                                                                                        | Issuing regulatory body or bodies                                        |
| **publication_date**      | Date       | ISO 8601 format                                                                                                                                              | Official publication or issuance date                                    |
| **effective_date**        | Date       | ISO 8601 format                                                                                                                                              | Date the regulatory action takes effect (if different from publication)  |
| **comment_deadline**      | Date       | ISO 8601 format                                                                                                                                              | For proposed rules: deadline for public comments                         |
| **supersedes_doc_id**     | String     | Pinecone document ID                                                                                                                                         | Links to the document this one replaces (for lifecycle tracking)         |
| **superseded_by_doc_id**  | String     | Pinecone document ID                                                                                                                                         | Links to the document that replaced this one                             |
| **ctf_roundtable_ref**    | String\[\] | RT1, RT2, RT3, RT4, RT5, RT6                                                                                                                                 | Links to relevant CTF roundtable session(s)                              |
| **participant_positions** | String\[\] | participant_name:position_code                                                                                                                               | Maps roundtable participant positions relevant to this document          |
| **citation_id**           | String     | e.g., SEC-IR-33-11412                                                                                                                                        | CRI-internal unique document reference for citation                      |
| **ingestion_timestamp**   | DateTime   | ISO 8601                                                                                                                                                     | When this document was ingested into the KB                              |
| **validation_status**     | String     | auto, pending_review, validated                                                                                                                              | Whether human domain expert has validated the classification             |

# **6\. CTF Roundtable Integration Matrix**

This matrix maps each of the six SEC Crypto Task Force roundtable sessions to the CRI taxonomy domains. It enables the research agent to track which roundtable positions have been validated, contradicted, or extended by subsequent regulatory developments.

| **Code** | **Roundtable Topic**                        | **Primary Domains** | **Key Sub-Domains**                    | **Key Participants / Notes**                                                |
| -------- | ------------------------------------------- | ------------------- | -------------------------------------- | --------------------------------------------------------------------------- |
| **RT1**  | Securities Status (Mar 2025)                | AC, IP              | AC-HOW, AC-DEC, AC-SEC, AC-NFT         | Belton, Cohen, Jennings, Reiners, Seira, Guillen, Stark, Schiffrin, Brummer |
| **RT2**  | Public Offerings (Apr 2025)                 | RO, AC              | RO-REG, RO-EXM, RO-DIS, RO-AIR         | Focus on registration pathways, exemptive relief, disclosure frameworks     |
| **RT3**  | Trading (Apr 2025)                          | MS, AC              | MS-ATS, MS-BDR, MS-DEX, MS-CLE         | Secondary market structure, ATS requirements, DEX regulatory status         |
| **RT4**  | Custody (Apr 2025)                          | CU, MS              | CU-IAC, CU-BDC, CU-SPB, CU-TEC, CU-UCC | Qualified custodian standards, MPC/multi-sig, SPBD framework                |
| **RT5**  | Tokenization (May 2025)                     | RO, MS, CB          | MS-CLE, RO-REG, CB-COM                 | Tokenized securities, TradFi-DeFi intersection, settlement                  |
| **RT6**  | DeFi (Jun 2025)                             | DP, AC              | DP-FEE, DP-GOV, DP-STK, DP-LEN, AC-DEC | Fee-switch, governance tokens, staking, decentralization analysis           |
| **RT7**  | Financial Surveillance & Privacy (Dec 2025) | SP, IP              | SP-AML, SP-PRI, IP-RET                 | Privacy-preserving technology, financial surveillance recalibration         |

# **7\. Regulatory Event Classification Examples**

The following examples demonstrate how recent regulatory events are classified using the CRI ontology. These serve as reference patterns for the ingestion pipeline's classification logic.

| **Regulatory Event**                                         | **Domain** | **Sub-Domain**         | **Lifecycle** | **Durability** | **Source Type**      |
| ------------------------------------------------------------ | ---------- | ---------------------- | ------------- | -------------- | -------------------- |
| SEC-CFTC Joint Taxonomy (Mar 2026)                           | **AC**     | AC-TAX                 | FINAL         | T2             | interpretive_release |
| GENIUS Act (signed Jul 2025)                                 | **SC**     | SC-GEN                 | FINAL         | T1             | legislation          |
| FDIC GENIUS NPRM (Apr 2026)                                  | **SC**     | SC-RES, SC-TOK         | PROP          | T4→T2          | rulemaking           |
| SEC Division of Corp Fin Stablecoin Statement (Apr 2025)     | **SC**     | SC-SEC                 | INTPR         | T4             | staff_statement      |
| SEC Trading & Markets FAQ on Crypto BD Activities (May 2025) | **CU, MS** | CU-BDC, CU-SPB, MS-BDR | INTPR         | T4             | FAQ                  |
| SAB 122 Rescinding SAB 121 (Jan 2025)                        | **CU**     | CU-BNK                 | INTPR         | T4             | staff_statement      |
| CTF Roundtable 1: Securities Status (Mar 2025)               | **AC**     | AC-HOW, AC-DEC         | PRE           | T5             | roundtable           |
| Coinbase Enforcement Dismissal (Feb 2025)                    | **EL**     | EL-DIS                 | ENFORCED      | T4             | enforcement_release  |
| Harper v. O'Neal (NFT ruling)                                | **AC, EL** | AC-NFT, EL-LIT         | ENFORCED      | T3             | court_opinion        |
| ESMA MiCA Reverse Solicitation Guidelines (Feb 2026)         | **CB**     | CB-MCA, CB-EQV         | FINAL         | T2 (EU)        | rulemaking           |

# **8\. Implementation Guide**

## **8.1 Ingestion Pipeline Integration**

The taxonomy is applied during document ingestion through the CRI three-pass hybrid pipeline:

- **Pass 1 - Agentic Extraction:** Automated parsing extracts document text, identifies source_type and regulatory_body from URL patterns and document headers, and assigns publication_date. Domain and subdomain are pre-classified using keyword matching and document source heuristics (e.g., documents from the SEC Division of Trading and Markets default to MS or CU domains).
- **Pass 2 - Claude API Enrichment:** Each document chunk is processed through a classification prompt that assigns: domain_primary, domain_secondary, subdomain tags, lifecycle_stage, durability_tier, and participant_positions (for roundtable-related content). The enrichment pass also generates a structured impact assessment identifying which existing KB positions this document modifies, validates, or contradicts.
- **Pass 3 - Human Domain Validation:** Amy reviews classification for interpretive documents (lifecycle stages INTPR and FINAL) and flags corrections. Factual documents (enforcement releases with clear outcomes) can flow through with auto-validated status. The validation_status field tracks this workflow.

## **8.2 Pinecone Metadata Filtering**

The taxonomy enables structured queries that go beyond pure semantic search. Example query patterns:

- **"What are the custody requirements for broker-dealers?"** → Filter: domain_primary=CU AND subdomain IN \[CU-BDC, CU-SPB\] AND lifecycle_stage IN \[INTPR, FINAL\] → Returns current guidance, excluding superseded documents
- **"How durable is the current stablecoin framework?"** → Filter: domain_primary=SC → Group by durability_tier → Shows T1 (GENIUS Act statute), T4 (staff statements), and PROP (pending FDIC NPRM) in distinct tiers
- **"What DeFi positions from the roundtables have been addressed?"** → Filter: ctf_roundtable_ref=RT6 → Cross-reference with lifecycle_stage=FINAL or INTPR documents in domain DP → Shows which roundtable positions have been formally addressed

## **8.3 Research Agent Integration**

The CRI research agent uses the taxonomy in its Detect-Validate-Prioritize loop:

- **Detect:** When a new document is ingested, compare its domain and subdomain tags against existing KB entries with lifecycle_stage FINAL or INTPR. Flag conflicts or extensions.
- **Validate:** Use the durability_tier to assess whether the new document has sufficient authority to modify existing positions. A T4 staff statement does not override a T2 Commission release.
- **Prioritize:** Score change signals against client-relevant domains. A CU-domain change with lifecycle FINAL directly affects broker-dealer clients; a CB-domain change with lifecycle PROP is informational for U.S.-focused clients but urgent for cross-border operators.

## **8.4 Cross-Product Output Consistency**

The taxonomy ensures all CRI outputs use the same classification vocabulary:

- **Chatbot responses** are tagged with relevant domains and durability tiers; responses include durability caveats when citing T4 guidance
- **Newsletter content** is organized by domain sections; each item carries its lifecycle stage and durability tier
- **Analytical reports** use the roundtable integration matrix to map positions to regulatory outcomes
- **Research agent alerts** reference specific subdomain codes and lifecycle transitions

# **9\. Unresolved Regulatory Gaps & Taxonomy Roadmap**

The following regulatory areas remain unresolved as of April 2026 and represent priority monitoring targets for CRI's research agent. These gaps are areas where the taxonomy has subdomain codes defined but limited or no FINAL/INTPR lifecycle content in the KB.

## **9.1 High-Priority Gaps (Flagged in March 2026 Joint Interpretation)**

- **DP-FEE (Fee-Switch Revenue Accrual):** The March 2026 taxonomy explicitly deferred guidance on whether enabling protocol revenue distribution to token holders creates a security. This is the single most-requested issue from DeFi-focused clients.
- **DP-STK (Restaking):** Staking receipt tokens and liquid restaking derivatives are not addressed in the taxonomy. Seira's roundtable position on programmatic vs. human-directed value accrual remains the analytical starting point.
- **DP-GOV (Governance Token Concentration):** No formal guidance on when governance token concentration creates sufficient "efforts of others" to trigger securities status. Jennings' control framework is the leading industry proposal but is not adopted.

## **9.2 Medium-Priority Gaps**

- **AC-NFT:** The March 2026 taxonomy defines "digital collectibles" but provides minimal guidance on the boundary between collectibles and securities for fractional or financial NFTs.
- **MS-DEX:** Regulatory status of fully decentralized exchanges and automated market makers remains unclear; no Commission-level position.
- **CU-UCC:** While UCC Article 12 adoption is progressing at the state level, no federal coordination framework exists for digital asset commercial law treatment.
- **CB-COM:** Comparative analysis between U.S. and MiCA frameworks is a gap in CRI's KB content; ESMA is finalizing implementation while U.S. framework is still forming.

## **9.3 Taxonomy Versioning**

This taxonomy is designed to be versioned. Major additions (new domains or lifecycle stages) increment the major version; new subdomains or metadata fields increment the minor version. The current specification is Version 1.0. Anticipated near-term additions include subdomains for CLARITY Act provisions if enacted, and potential new domains for Digital Identity and CBDC if those topics enter the regulatory scope.

# **Appendix A: Regulatory Acronym Reference**

| **Acronym** | **Full Name**                                    |
| ----------- | ------------------------------------------------ |
| **AML**     | Anti-Money Laundering                            |
| **ATS**     | Alternative Trading System                       |
| **BSA**     | Bank Secrecy Act                                 |
| **CASP**    | Crypto-Asset Service Provider (MiCA term)        |
| **CEA**     | Commodity Exchange Act                           |
| **CFTC**    | Commodity Futures Trading Commission             |
| **CTF**     | Crypto Task Force (SEC)                          |
| **DAO**     | Decentralized Autonomous Organization            |
| **DEX**     | Decentralized Exchange                           |
| **DLT**     | Distributed Ledger Technology                    |
| **EBA**     | European Banking Authority                       |
| **ESMA**    | European Securities and Markets Authority        |
| **FCA**     | Financial Conduct Authority (UK)                 |
| **FDIC**    | Federal Deposit Insurance Corporation            |
| **FINRA**   | Financial Industry Regulatory Authority          |
| **FSOC**    | Financial Stability Oversight Council            |
| **ICA**     | Investment Company Act of 1940                   |
| **MiCA**    | Markets in Crypto-Assets Regulation (EU)         |
| **MPC**     | Multi-Party Computation                          |
| **NCA**     | National Competent Authority (MiCA term)         |
| **NPRM**    | Notice of Proposed Rulemaking                    |
| **OCC**     | Office of the Comptroller of the Currency        |
| **OFAC**    | Office of Foreign Assets Control                 |
| **PPSI**    | Permitted Payment Stablecoin Issuer (GENIUS Act) |
| **SAB**     | Staff Accounting Bulletin                        |
| **SIPA**    | Securities Investor Protection Act               |
| **SIPC**    | Securities Investor Protection Corporation       |
| **SPBD**    | Special Purpose Broker-Dealer                    |
| **UCC**     | Uniform Commercial Code                          |