# Claude Session Handover

**Project:** ai-spend-governance-control-plane — GitHub Architecture Repo
**Date:** March 2026
**Repo:** https://github.com/BoAina/ai-spend-governance-control-plane

---

## What Was Built

A fully populated public GitHub repository exploring architectural patterns for governed AI operating inside real-time financial authorization systems. The repo is positioned as independent architecture research — not a job application artifact — and is designed to demonstrate deep fintech systems thinking to a technical hiring audience.

---

## The Core Thesis

Financial AI can reason probabilistically, but the movement of money must always be governed by deterministic authorization systems.

The repo explores the structural shift from ERP post-transaction reconciliation (Oracle, Workday, SAP) to real-time fintech authorization platforms, and how AI systems can safely participate in financial workflows through a governance control plane.

The four-layer model:

```
AI Reasons
↓
Policy Decides
↓
Authorization Executes
↓
Ledger Records
```

---

## Repository Structure

```
/architecture
   control_plane_diagram.md         — Core governance control plane architecture
   financial_control_evolution.md   — ERP → Fintech → AI Governance progression

/scenarios
   expense_workflow_example.md      — Full trace of an AI-governed card transaction
   procurement_policy_example.md    — Multi-step public sector procurement workflow

/evolution
   v1_expense_agent.md              — AI classifies receipts, no policy enforcement
   v2_embedded_policy.md            — Policy embedded in AI agent (the wrong approach)
   v3_policy_gate.md                — Policy extracted into separate deterministic layer
   v4_real_time_authorization.md    — Policy gate at point-of-spend, before money moves
   v5_governance_control_plane.md   — Centralized governance across multiple AI agents

/src
   policy_gate.py                   — Working Python prototype of deterministic policy gate

/docs
   ai-financial-governance-architecture.md — Full architecture paper

README.md                           — Main repo document (see below)
RESEARCH.md                         — Open questions and ongoing exploration notes
```

---

## README Sections

The README is the primary artifact. It contains:

1. **Core thesis and badges**
2. **Navigation** — anchor links to all sections
3. **Governance Control Plane diagram** — Mermaid flowchart (renders on GitHub)
4. **Financial Control Evolution diagram** — ERP → Fintech → AI Governance
5. **Core Architecture Principle** — four-layer model
6. **Example Financial Workflow** — SaaS purchase scenario walkthrough
7. **The Architecture Problem** — probabilistic vs deterministic tension
8. **Architecture Progression** — V1→V5 summary
9. **Public Sector Compliance Constraints** — FedRAMP, FISMA, CJIS, HIPAA, SOC 2 table
10. **ERP Integration Patterns** — Mermaid diagram + three named integration patterns + Python prototype
11. **Real-World Architecture Reference** — describes Generation 2 platforms generically (no company named — deliberate plausible deniability)
12. **Open Questions & Roadmap** — five unresolved architectural questions, links to RESEARCH.md
13. **Repository Structure**
14. **Full Architecture Paper**
15. **About Ainalabs**
16. **Author**

---

## Key Decisions Made

**Plausible deniability on Ramp**
The author works at Oracle and is applying to Ramp. The repo contains no direct reference to Ramp by name. The "Real-World Architecture Reference" section describes Generation 2 fintech platforms generically. Anyone in the industry will recognize Ramp immediately, but the repo reads as independent industry research, not a targeted application artifact.

**Generic section title**
The section was originally titled "Real-World Architecture Reference: Ramp" — renamed to "Real-World Architecture Reference" for the same reason.

**RESEARCH.md as intellectual depth signal**
The open questions document signals ongoing curiosity and rigorous thinking. It includes five unresolved architectural questions that demonstrate the author is thinking beyond what is already solved.

**V1→V5 progression**
Staged evolution from simple AI expense agent to full governance control plane. Each version has its own document explaining the architecture, what changed, and why the approach is insufficient before the next evolution.

**Python policy gate prototype**
Both in the README and as a standalone `/src/policy_gate.py` — demonstrates Python proficiency and systems thinking. The gate is purely deterministic with structured audit output, reinforcing the core thesis.

---

## Navigation Links

All navigation links in the README use GitHub anchor format (e.g., `#financial-control-evolution`). The previous version had broken ChatGPT URLs — these were all replaced.

---

## What Is NOT in the Repo Yet

Based on RESEARCH.md, the following directions are identified but not yet built:

- FedRAMP control mapping document
- Formal state machine model of the policy gate
- Comparative analysis of Generation 2 platforms against the V1→V5 progression

---

## Suggested Next Steps

1. **Add a `/compliance` folder** with a FedRAMP Moderate control mapping — this directly mirrors what a public sector SC would produce in an RFP response and would make the repo even more targeted to the role.

2. **Add a second Python module** — something like `erp_sync.py` modeling the ERP write-back pattern after authorization. Keeps the `/src` folder from feeling sparse.

3. **Update README navigation** if any new sections are added — the anchor link format must match the exact heading text (lowercase, spaces to hyphens).

4. **Do not add Ramp by name** anywhere in the repo. The plausible deniability decision was intentional.

---

## Context: Why This Repo Was Built

Built as part of a Ramp Solutions Consultant (Public Sector) application. The repo is designed to demonstrate:

- Deep understanding of Ramp's core architectural thesis (pre-spend authorization vs ERP reconciliation)
- AI governance thinking relevant to Ramp's product roadmap
- Public sector compliance knowledge (FedRAMP, FISMA, CJIS)
- Python and systems architecture proficiency
- Independent intellectual initiative

The repo is referenced in the resume under Selected Projects and in the recruiter re-engagement email to John Buller (GTM Talent at Ramp).

---

*Handover prepared by Claude - claude.ai - March 2026*
