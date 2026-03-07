# Research Notes & Ongoing Exploration

This document captures the open questions, evolving thinking, and areas of active exploration in this repository. It is intentionally incomplete — the goal is to document what is still being figured out, not just what has been resolved.

---

## Why This Exists

Architecture explorations are most useful when they track not just conclusions but the questions that led to them. This file is a running log of the problems that feel unsolved, the assumptions worth questioning, and the directions worth pursuing.

---

## Open Architectural Questions

### 1. Policy Gate Conflict Resolution
When two compliance frameworks produce conflicting authorization rules, how should the policy gate resolve them?

For example: a HIPAA requirement may mandate that certain healthcare-adjacent transactions require additional review, while a department spend policy auto-approves transactions under a dollar threshold. If a transaction satisfies the dollar threshold but triggers the HIPAA rule, which takes precedence?

**Current assumption:** Regulatory compliance rules always supersede organizational spend policy. But the mechanism for declaring and enforcing rule precedence in a multi-framework environment is not yet modeled.

**Open question:** Should precedence be a static hierarchy compiled into the policy gate, or a dynamic resolution layer that reasons about rule conflicts at evaluation time?

---

### 2. AI Classification Failure Modes
The governance control plane assumes that AI classification is the input to the policy gate — but what happens when the AI is wrong?

Three failure scenarios to model:

- **Misclassification with high confidence** — AI classifies a restricted vendor as an approved one with 0.92 confidence. Policy gate approves based on incorrect input.
- **Low confidence with no escalation path** — AI returns 0.55 confidence. Policy gate escalates, but no approver is available (e.g., off-hours, public sector holiday).
- **Novel transaction type** — AI has no strong classification signal (new vendor category, unusual spend pattern). What is the default policy gate behavior?

**Current assumption:** Low confidence triggers escalation. But the escalation path itself needs governance — who approves the approver queue, and what happens when it stalls?

---

### 3. Latency vs. Compliance Trade-offs in Real-Time Authorization
V4 introduces real-time authorization with a target pipeline latency under 100ms. But some compliance checks — particularly vendor registry lookups and budget commitment validation — may require external calls that exceed this budget.

**Open question:** What is the right architecture for compliance checks that cannot complete within the authorization window? Options include:

- Pre-fetch and cache compliance state (introduces staleness risk)
- Two-phase authorization (provisional approval followed by async compliance verification)
- Hard block until compliance check completes (latency impact on user experience)

Each option involves a trade-off between compliance rigor and operational usability that is not yet resolved in this model.

---

### 4. Multi-Entity Policy Governance
The current model assumes a single organizational policy context. Public sector deployments frequently involve multiple entities — a federal agency with sub-agencies, a state with municipal subdivisions, a university system with multiple campuses — each with their own budget codes, approval hierarchies, and compliance requirements.

**Open question:** How should the governance control plane handle policy inheritance and override across organizational hierarchies? Should child entities inherit parent policy with override capability, or maintain fully independent policy contexts that are audited separately?

---

### 5. Auditability of the Policy Compiler
The policy gate is deterministic, but the policy compiler — the component that translates human-readable policy documents into compiled rules — may not be. If AI is used to assist policy compilation (interpreting regulatory text, extracting rules from procurement documents), the compiler itself introduces probabilistic behavior upstream of the deterministic gate.

**Open question:** Does the governance model need to extend upstream to include auditability of the policy compilation process, not just policy evaluation?

---

## Assumptions Worth Revisiting

- **"Deterministic" is binary.** The current model treats authorization as fully deterministic or fully probabilistic. In practice, some authorization decisions may be probabilistic by design (fraud scoring, anomaly-based holds). The model may need a third category: *governed probabilistic decisions* with defined confidence thresholds and mandatory audit trails.

- **The ledger is downstream only.** The current architecture treats ERP/ledger systems as write targets. But in practice, ledger data feeds back into policy (e.g., updated budget balances, historical spend patterns). The feedback loop between ledger state and policy compilation is not yet modeled.

- **Human escalation is always available.** Several scenarios assume a human approver is reachable within a defined SLA. In practice, escalation queues can stall. The governance model should define what happens to held transactions when escalation times out.

---

## Directions Worth Pursuing

- **Mapping this architecture to a specific compliance framework** (FedRAMP Moderate or High) in enough detail to produce a control mapping document — the kind a public sector procurement team would request in an RFP response.

- **Modeling the policy gate as a formal state machine** — transitions, terminal states, and invariants — to make the determinism claim more rigorous and testable.

- **Mapping where leading spend management and corporate card platforms sit on the V1→V5 progression** — and explicitly charting the gap between what Generation 2 platforms offer today and what a full V5 governance control plane would require. This comparison would make the architecture model more grounded and testable against real production systems.

---

*This document is updated as the exploration develops. Open questions are more valuable than premature answers.*
