# Custody AI Agent: MVP Scope, Timeline & Sample Newsletter

## Executive Summary

This document outlines the Minimum Viable Product (MVP) scope for the Custody AI Agent, a regulatory intelligence product that tracks SEC, CFTC, and banking regulator developments affecting crypto custody. The MVP focuses on delivering immediate value to custodians, broker-dealers, and RIAs while building toward the full enforcement pattern database.

**Target Launch**: 12 weeks from start
**Target Customers**: Crypto custodians, broker-dealers entering crypto, RIAs with crypto exposure
**Pricing Model**: $1,500-5,000/month subscription (tiered by organization size)

---

## Part 1: MVP Scope

### Core Value Proposition

> "Never be surprised by a custody rule change again. Get interpreted regulatory intelligence—not just alerts—from someone who understands how the SEC actually thinks."

### MVP Feature Set

#### Tier 1: Must Have (Launch)

| Feature | Description | Effort |
|---------|-------------|--------|
| **Weekly Custody Digest** | Curated newsletter covering all custody-relevant developments | Medium |
| **Regulatory Tracker Dashboard** | Living document of all custody rules, guidance, no-action letters | Medium |
| **Alert System** | Email alerts on breaking custody developments | Low |
| **Guidance Library** | Searchable archive of SEC/CFTC custody statements with plain-English summaries | Medium |

#### Tier 2: Should Have (Month 2-3)

| Feature | Description | Effort |
|---------|-------------|--------|
| **Enforcement Database (Custody)** | Historical custody-related enforcement with pattern analysis | High |
| **Compliance Gap Analyzer** | Self-assessment tool mapping business model to regulatory requirements | Medium |
| **Peer Comparison** | Anonymous benchmarking against similar firms | Medium |

#### Tier 3: Nice to Have (Post-MVP)

| Feature | Description | Effort |
|---------|-------------|--------|
| **API Access** | Programmatic access to regulatory data | High |
| **Custom Alerts** | User-defined alert rules | Medium |
| **Consultation Booking** | Schedule calls with regulatory experts | Low |

### MVP Data Coverage

**Primary Sources (Automated Ingestion)**:
```
SEC.gov
├── Crypto Task Force releases
├── Division of Trading & Markets statements
├── Division of Investment Management guidance
├── No-action letters (custody-related)
├── Litigation releases (custody violations)
├── Commissioner speeches (custody mentions)
└── Proposed/final rules (custody-related)

CFTC.gov
├── Press releases (custody, segregation)
├── Staff letters (FCM custody)
├── No-action letters
└── Enforcement (segregation violations)

Banking Regulators (Manual Review Initially)
├── OCC interpretive letters
├── FDIC guidance
├── Federal Reserve supervision letters
└── State banking department releases (NY, WY)
```

**Taxonomy: Custody-Specific Topics**

```
CUSTODY_TOPICS = {
    "SAB_121_122": {
        "description": "Balance sheet treatment of custodied crypto",
        "status": "SAB 121 rescinded Jan 2025; SAB 122 in effect",
        "relevance": "CRITICAL"
    },
    "RULE_15C3_3": {
        "description": "Broker-dealer customer protection rule",
        "subtopics": ["physical_possession", "control_locations", "special_purpose_bd"],
        "status": "New guidance Dec 2025",
        "relevance": "CRITICAL"
    },
    "ADVISERS_ACT_CUSTODY": {
        "description": "RIA custody rule (Rule 206(4)-2)",
        "subtopics": ["qualified_custodian", "state_trust_companies", "surprise_exam"],
        "status": "State trust company NAL Sep 2025",
        "relevance": "HIGH"
    },
    "CFTC_SEGREGATION": {
        "description": "Customer fund segregation requirements",
        "subtopics": ["rule_1.20", "digital_asset_collateral", "FCM_requirements"],
        "status": "New collateral guidance Dec 2025",
        "relevance": "HIGH"
    },
    "QUALIFIED_CUSTODIAN": {
        "description": "Who qualifies as custodian for various purposes",
        "subtopics": ["banks", "broker_dealers", "trust_companies", "state_chartered"],
        "status": "Evolving",
        "relevance": "HIGH"
    },
    "KEY_MANAGEMENT": {
        "description": "Private key security requirements",
        "subtopics": ["policies_procedures", "MPC", "HSM", "cold_storage"],
        "status": "Addressed in Dec 2025 BD statement",
        "relevance": "HIGH"
    },
    "TOKENIZATION_CUSTODY": {
        "description": "Custody of tokenized securities",
        "subtopics": ["DTC_pilot", "transfer_agent", "entitlement_model"],
        "status": "DTC NAL Dec 2025",
        "relevance": "MEDIUM-HIGH"
    }
}
```

### What MVP Does NOT Include

- Full enforcement database (custody subset only)
- Real-time regulatory tracking (weekly batch)
- API access
- International regulatory coverage
- Banking regulator automation (manual initially)
- Custom white-label reports

---

## Part 2: Development Timeline

### 12-Week MVP Timeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        12-WEEK MVP DEVELOPMENT TIMELINE                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  WEEK 1-2: FOUNDATION                                                        │
│  ├── Set up data ingestion from SEC.gov (RSS, web scrape)                   │
│  ├── Create custody topic taxonomy and keyword filters                       │
│  ├── Build basic database schema                                            │
│  ├── Design newsletter template                                             │
│  └── Identify 10 target beta customers from roundtable contacts             │
│                                                                              │
│  WEEK 3-4: CONTENT ENGINE                                                    │
│  ├── Backfill historical custody guidance (2020-present)                    │
│  ├── Write plain-English summaries for key documents                        │
│  ├── Create "Custody Regulatory Landscape" overview document                │
│  ├── Build guidance library with search                                     │
│  └── Draft first newsletter (Week 4)                                        │
│                                                                              │
│  WEEK 5-6: BETA LAUNCH                                                       │
│  ├── Send first newsletter to beta customers (Week 5)                       │
│  ├── Collect feedback via calls                                             │
│  ├── Iterate on format/content based on feedback                            │
│  ├── Add CFTC coverage                                                      │
│  └── Build simple alert system (email)                                      │
│                                                                              │
│  WEEK 7-8: ENFORCEMENT LAYER                                                 │
│  ├── Build custody enforcement database (historical)                        │
│  ├── Tag enforcement actions with custody topics                            │
│  ├── Create enforcement trend analysis for custody                          │
│  ├── Add "Cases to Watch" section to newsletter                             │
│  └── Second beta newsletter (Week 8)                                        │
│                                                                              │
│  WEEK 9-10: DASHBOARD & POLISH                                               │
│  ├── Build regulatory tracker dashboard (Notion/Airtable or custom)         │
│  ├── Create compliance gap self-assessment                                  │
│  ├── Add banking regulator coverage (manual)                                │
│  ├── Refine alert triggers                                                  │
│  └── Third beta newsletter (Week 10)                                        │
│                                                                              │
│  WEEK 11-12: LAUNCH                                                          │
│  ├── Convert beta customers to paid                                         │
│  ├── Launch marketing (LinkedIn, industry publications)                     │
│  ├── Finalize pricing tiers                                                 │
│  ├── Set up payment processing                                              │
│  └── Official launch newsletter (Week 12)                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Milestones

| Week | Milestone | Success Criteria |
|------|-----------|------------------|
| 2 | Data pipeline operational | SEC releases auto-ingested within 24 hours |
| 4 | First newsletter drafted | Beta customers confirm value |
| 6 | Beta feedback collected | 5+ detailed feedback sessions completed |
| 8 | Enforcement layer live | Historical custody enforcement searchable |
| 10 | Dashboard functional | Beta customers using self-service |
| 12 | Paid launch | 3+ paying customers at launch |

### Resource Requirements

| Role | Hours/Week | Weeks | Notes |
|------|------------|-------|-------|
| You (Regulatory Analysis) | 15-20 | 12 | Content, interpretation, customer calls |
| Developer (Part-time) | 20-30 | 12 | Data pipeline, dashboard, alerts |
| Designer (Contract) | 10 | 2 | Newsletter template, dashboard UI |
| **Total Hours** | ~500 | 12 | |

### Technology Stack (Recommended)

| Component | Tool | Cost/Month | Notes |
|-----------|------|------------|-------|
| Database | Supabase or Airtable | $0-50 | Start simple, migrate later |
| Newsletter | Beehiiv or Substack | $0-100 | Built-in subscription management |
| Dashboard | Notion or Retool | $0-100 | Fast to build, professional look |
| Alerts | SendGrid + Zapier | $0-50 | Email automation |
| Web Scraping | Apify or custom Python | $50-100 | SEC/CFTC data collection |
| Hosting | Vercel or Railway | $0-50 | If custom dashboard |
| **Total** | | **$50-450** | MVP infrastructure |

---

## Part 3: Sample Newsletter

Below is a complete sample newsletter for the Custody AI Agent, formatted for Week 1 of January 2026.

---

# 🔐 Custody Intelligence Weekly
## The Regulatory Digest for Crypto Custodians
### Week of January 6-10, 2026 | Issue #1

---

*Welcome to the inaugural issue of Custody Intelligence Weekly. Each week, we synthesize the regulatory developments that matter for crypto custody—so you can focus on building, not monitoring the Federal Register.*

---

## 📊 This Week at a Glance

| Metric | This Week | YTD 2026 |
|--------|-----------|----------|
| SEC custody-related releases | 1 | 1 |
| CFTC custody/collateral releases | 0 | 0 |
| No-action letters | 0 | 0 |
| Enforcement actions (custody) | 0 | 0 |
| Banking regulator guidance | 0 | 0 |

**Bottom Line**: Quiet week following holiday. No new custody guidance, but the December developments continue to reshape the landscape.

---

## 🔥 Top Story: December Custody Guidance Now In Effect

If you were on vacation, here's what you missed:

### Broker-Dealer "Physical Possession" Statement (Dec 17, 2025)

The SEC Division of Trading & Markets issued its most significant custody guidance since 2020, clarifying how broker-dealers can satisfy Rule 15c3-3's "physical possession" requirement for crypto asset securities.

**What Changed**: Previously, BDs faced uncertainty about whether holding private keys constituted "possession." The new statement provides a clear framework:

**Five Conditions for "Physical Possession"**:

1. **Exclusive Key Access**: Policies ensuring no other party (including customers or affiliates) can access private keys or transfer assets without BD authorization

2. **Technology Assessment**: Documented evaluation of the DLT/blockchain before custodying assets, including:
   - Protocol governance and upgrade mechanisms
   - Security vulnerabilities
   - Network reliability
   - Repeated at "reasonable intervals"

3. **Industry Best Practices**: Key management controls consistent with industry standards (implicit reference to SOC 2, ISO 27001)

4. **Business Continuity**: Plans ensuring continued access to customer assets during disruptions

5. **Problem Awareness**: No actual knowledge of material security or operational weaknesses in the DLT

**Who This Affects**:
- ✅ Broker-dealers seeking to custody crypto securities
- ✅ Crypto custodians partnering with BDs
- ✅ Token issuers with securities tokens
- ⚠️ Does NOT cover non-security crypto assets

**What This Means for You**:

| If You Are... | Action Item |
|---------------|-------------|
| Broker-dealer | Review key management policies against the 5 conditions; document DLT assessments |
| Crypto custodian | Consider BD partnerships; your infrastructure may enable BD custody |
| RIA | This doesn't change your qualified custodian requirements (yet) |
| Token issuer | BDs can now more easily custody your security tokens |

**Gap Alert**: The statement addresses "possession" but the earlier May 2025 FAQ addressed "control." Make sure you understand both pathways.

📄 **[Read the full statement →](https://www.sec.gov/newsroom/speeches-statements/trading-markets-121725-statement-custody-crypto-asset-securities-broker-dealers)**

📄 **[Commissioner Peirce's commentary →](https://www.sec.gov/newsroom/speeches-statements/peirce-121725-no-longer-special)**

---

## 📋 Regulatory Tracker Update

### Rules & Guidance Currently in Effect

| Guidance | Effective | Status | Impact |
|----------|-----------|--------|--------|
| **SAB 122** | Jan 23, 2025 | ✅ Active | Rescinded SAB 121; crypto custody no longer auto-liability |
| **BD Custody FAQ (Control)** | May 15, 2025 | ✅ Active | BDs can use qualifying control locations (banks) |
| **State Trust Company NAL** | Sep 30, 2025 | ✅ Active | RIAs can use state trust companies as qualified custodians |
| **BD Custody Statement (Possession)** | Dec 17, 2025 | ✅ Active | Framework for BD "physical possession" |
| **DTC Tokenization NAL** | Dec 11, 2025 | ✅ Active | DTC can tokenize security entitlements (pilot 2H 2026) |
| **CFTC Digital Asset Collateral** | Dec 8, 2025 | ✅ Active | FCMs can accept BTC, ETH, stablecoins as collateral |

### Pending/Expected Developments

| Expected Development | Timeline | Confidence | Source |
|---------------------|----------|------------|--------|
| SEC "Regulation Crypto" proposal | Q1-Q2 2026 | Medium | Atkins Nov 2025 speech |
| CFTC collateral pilot expansion | Q1 2026 | High | Dec 8 announcement |
| DTC tokenization pilot launch | H2 2026 | High | DTC NAL |
| Updated BD custody rule (formal) | 2026-2027 | Medium | Peirce Dec 2025 statement |

---

## ⚖️ Enforcement Watch: Custody Cases

### Active Cases to Monitor

| Case | Status | Issue | Next Event |
|------|--------|-------|------------|
| **SEC v. Silvergate (settled)** | Closed | Misleading crypto custody disclosures | N/A - Settled 2024 |
| **SEC v. Voyager (bankruptcy)** | Distribution | Customer asset segregation | Ongoing distributions |
| **CFTC v. Celsius** | Pending | Customer fund commingling | Trial TBD |
| **SEC v. FTX (executives)** | Sentencing | Misappropriation of customer assets | Ellison/Wang sentencing 2025 |

### Custody Enforcement Trends

**2025 Pattern**: Zero new custody-specific enforcement actions filed by SEC in 2025. All custody-related matters involved fraud allegations (misappropriation, commingling) rather than technical custody rule violations.

**Interpretation**: The SEC under Chairman Atkins is not pursuing custody technicalities. Focus remains on fraud. However, this could change once clearer rules are in place—compliance failures will be harder to excuse.

**Risk Areas Still Elevated**:
- Customer asset commingling (Celsius/Voyager pattern)
- Misleading custody disclosures to investors
- Failure to disclose custody risks in public filings

---

## 🏦 Banking Regulator Corner

### OCC/FDIC/Fed: No New Guidance This Week

The banking regulators remain quiet on crypto custody. Key outstanding questions:

- Will OCC issue updated interpretive letter on national bank crypto custody?
- Will FDIC lift informal pressure on banks serving crypto?
- Will Fed clarify master account access for crypto custodians?

**What We're Watching**: Treasury's implementation of the GENIUS Act (stablecoin legislation) may force banking regulator action on custody standards for stablecoin reserves.

### State Spotlight: Wyoming

Wyoming's Special Purpose Depository Institutions (SPDIs) remain the only state-chartered path to becoming a crypto-native qualified custodian. Current SPDIs:
- Kraken Financial
- Custodia Bank (pending Fed master account litigation)
- Wyoming Deposit & Transfer

**Update**: No new SPDI applications announced this week.

---

## 🔮 What's Coming

### January 2026 Calendar

| Date | Event | Relevance |
|------|-------|-----------|
| Jan 15 | SEC open meeting (tentative) | Possible crypto agenda items |
| Jan 20 | CFTC collateral pilot weekly report due | First data on BTC/ETH/USDC collateral usage |
| Jan 21 | Crypto Task Force 1-year anniversary | Expect retrospective/forward-looking statements |
| TBD | SEC Spring regulatory agenda | Will signal custody rulemaking timeline |

### Questions We're Tracking

1. **Will SEC propose formal custody rule amendments in 2026?**
   - Commissioner Peirce called for it in Dec 17 statement
   - Currently relying on staff guidance, not formal rules

2. **How will DTC tokenization pilot affect custody landscape?**
   - If successful, could centralize tokenized security custody
   - Competition implications for crypto-native custodians

3. **Will banking regulators engage or stay silent?**
   - OCC hasn't issued crypto guidance since 2021
   - Crypto custody increasingly happening outside banking system

---

## 💡 Compliance Action Items

### This Week's To-Do List

- [ ] **Review BD custody statement** if you're a broker-dealer or partner with one
- [ ] **Document DLT assessments** for any blockchain you custody assets on
- [ ] **Update policies** to reflect "industry best practices" for key management
- [ ] **Calendar** the Crypto Task Force anniversary (Jan 21) for potential announcements

### Standing Items

- [ ] Monitor SEC.gov/crypto-task-force weekly
- [ ] Review 8-K filings from public crypto companies for disclosed inquiries
- [ ] Track peer company custody arrangements for benchmarking

---

## 📚 Resource Library

### Essential Reading (Custody-Specific)

| Document | Date | Summary |
|----------|------|---------|
| [BD Physical Possession Statement](https://sec.gov/...) | Dec 2025 | 5 conditions for BD crypto custody |
| [BD Control FAQ](https://sec.gov/...) | May 2025 | Control locations for crypto securities |
| [State Trust Company NAL](https://sec.gov/...) | Sep 2025 | RIA custody with state trust companies |
| [SAB 122](https://sec.gov/...) | Jan 2025 | Rescinded SAB 121 |
| [CFTC Collateral Guidance](https://cftc.gov/...) | Dec 2025 | Digital assets as derivatives collateral |
| [DTC Tokenization NAL](https://sec.gov/...) | Dec 2025 | Securities tokenization pilot |

### Deep Dives

- **[Understanding Rule 15c3-3 for Crypto]** - Our explainer on the customer protection rule
- **[Qualified Custodian Matrix]** - Who qualifies as QC for different purposes
- **[SAB 121 → 122: What Changed]** - Accounting treatment comparison

---

## 📬 Feedback & Questions

This is Issue #1—we want to make this valuable for you.

**Reply to this email** with:
- Topics you want covered
- Format preferences
- Regulatory questions you're wrestling with

**Schedule a call**: [Book 15 minutes](https://calendly.com/...) to discuss your specific custody compliance questions.

---

## About Custody Intelligence Weekly

Published by [Your Company], founded by a former SEC/CFTC regulatory professional with 10+ years of experience in financial technology oversight.

**Why trust us?** We've been on the inside. We know how staff thinks about these issues, what signals enforcement, and what's actually coming versus what's just noise.

---

**Subscription Tiers**:
- 📧 **Weekly Digest** (this newsletter): $1,500/month
- 📊 **Digest + Dashboard Access**: $3,000/month  
- 🔔 **Full Access** (Digest + Dashboard + Alerts + Quarterly Calls): $5,000/month

[Upgrade Your Subscription →]

---

*© 2026 [Your Company]. All rights reserved.*

*Disclaimer: This newsletter is for informational purposes only and does not constitute legal advice. Consult with qualified legal counsel for advice specific to your situation.*

---

# End of Sample Newsletter

---

## Part 4: Go-to-Market Strategy

### Beta Customer Targets (From Roundtable Analysis)

**Tier 1: Direct Outreach** (High likelihood of conversion)

| Contact | Organization | Why Target |
|---------|--------------|------------|
| Baylor Myers | BitGo | Former Treasury; understands policy value |
| Jason Allegrante | Fireblocks | CLO; needs compliance intelligence |
| Ryan Louvar | WisdomTree | CLO; ETF issuer with custody needs |
| Terrence Dempsey | Fidelity Digital Assets | TradFi custodian entering crypto |

**Tier 2: Warm Outreach** (May need introduction)

| Contact | Organization | Why Target |
|---------|--------------|------------|
| Neel Maitra | Dechert LLP | Former SEC; could validate/refer |
| Zach Zweihorn | Davis Polk | Custody practice lead |
| Rachel Anderika | Anchorage Digital | Crypto-native bank |
| Mark Greenberg | Kraken | Exchange with custody services |

### Pricing Validation

| Tier | Price | Value Proposition | Target Customer |
|------|-------|-------------------|-----------------|
| **Basic** | $1,500/mo | Weekly newsletter + archive | Small custodians, RIAs |
| **Professional** | $3,000/mo | + Dashboard + alerts | Mid-size custodians, BDs |
| **Enterprise** | $5,000/mo | + Quarterly calls + custom | Large institutions |

**Validation Question for Beta Calls**: "If this newsletter existed last year, would it have helped you prepare for SAB 121 rescission? What would you have paid to know that was coming?"

### Launch Marketing

**LinkedIn Strategy**:
- Post weekly insights from newsletter (teaser content)
- Comment on SEC/CFTC announcements with interpretation
- Connect with compliance officers at target companies

**Content Marketing**:
- Guest posts on industry publications (The Block, CoinDesk, Blockworks)
- Podcast appearances discussing regulatory landscape
- Free "2025 Custody Regulatory Year in Review" report as lead magnet

**Industry Events**:
- DC Fintech Week (Chris Brummer's event)
- Consensus
- Digital Asset Summit

---

## Success Metrics

### MVP Success Criteria (Week 12)

| Metric | Target | Stretch |
|--------|--------|---------|
| Beta customers | 10 | 20 |
| Paid conversions | 3 | 5 |
| Monthly recurring revenue | $4,500 | $10,000 |
| Newsletter open rate | 50% | 60% |
| Customer NPS | 40+ | 50+ |

### 6-Month Goals

| Metric | Target |
|--------|--------|
| Paying customers | 15-20 |
| MRR | $30,000-50,000 |
| Expansion to Trading Agent | Launched |
| Enforcement database | Full crypto coverage |

---

*MVP Scope Document v1.0 | January 2026*
