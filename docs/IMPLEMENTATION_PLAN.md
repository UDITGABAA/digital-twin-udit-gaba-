# Security Digital Twin Implementation Plan v2.1 — Security Change Sandbox

**Problem Statement:** CyberSecurity & Defence System (PS #13) — Security Digital Twin for Threat Vector Assessment  
**Core Concept:** A Security Change Sandbox that joins security risk reduction with business service flow breakage to answer the Change Advisory Board question: *What can I deploy safely, within budget, and how sure are we?*

---

## 1. System Architecture & Dual-Algorithm Design

The system rejects the naive assumption that attack path existence equals compromise risk. Instead, it evaluates change across two complementary algorithms and a business dependency graph:

```
                          ┌────────────────────────┐
                          │   Scenario Definition  │
                          │  (Assets, Edges, Flows)│
                          └───────────┬────────────┘
                                      │
                                      ▼
                          ┌────────────────────────┐
                          │  Digital Twin Snapshot │
                          │  (Immutable, Hashable) │
                          └─────┬────────────┬─────┘
                                │            │
            ┌───────────────────┘            └───────────────────┐
            ▼                                                    ▼
┌───────────────────────┐                            ┌───────────────────────┐
│ Algorithm A: Search   │                            │  Algorithm B: Walk    │
│ Complete State Search │                            │  Sampled Agent Walk   │
│ (node, capabilities)  │                            │  Monte Carlo (N=1000) │
│ Headline Path Count   │                            │  Attacker Cost Dist.  │
└───────────┬───────────┘                            └───────────┬───────────┘
            │                                                    │
            └───────────────────┬────────────────────────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │    evaluate_change()   │
                    │   - Path Reduction %   │
                    │   - Attacker Cost %    │
                    │   - Substituted Paths  │
                    │   - Broken Flows (>=4) │
                    └───────────┬────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │      ChangeVerdict     │
                    │ deploy | blocked | rev │
                    └────────────────────────┘
```

### The Two Non-Negotiable Algorithms
1. **Algorithm A (Complete Path Search — `core/search.py`):**
   - Runs once per twin snapshot, cached.
   - State space: `(node, frozenset(capabilities_held))`.
   - Bounded by `max_depth=8`, `max_states=5000`.
   - Produces exact path inventories, choke points, and the required `naive_path_reduction_pct`.
2. **Algorithm B (Sampled Agent Walk — `core/walk.py`):**
   - Used for all Monte Carlo statistics and adaptive simulation.
   - Attacker makes local probabilistic choices based on held capabilities and noise budgets.
   - Produces `honest_cost_increase_pct`, empirical time-to-compromise, and attacker substitution routes.
   - **Rule:** Never execute Algorithm A inside the Algorithm B sampling loop.

---

## 2. Team Ownership & Tracks

To prevent merge conflicts during intensive parallel implementation, work is partitioned by directory:

| Track | Lead / Role | Owned Directory | Primary Focus |
|---|---|---|---|
| **Track A** | Engine Owner | `backend/core/` | Core twin data structures, immutability, hashing, Algorithm A (search), Algorithm B (walk), Results/Delta types. |
| **Track B** | Rules & Decisions | `backend/rules/` | MITRE ATT&CK technique catalog, YAML loader, `evaluate_change`, broken-flow detector, constrained optimizer. |
| **Track C** | Frontend Lead | `frontend/` | React 18, TypeScript, Tailwind CSS, React Flow graph view, Recharts cost histograms, change advisory console. |
| **Track D** | Integration & Data | `backend/api/`, `backend/data/`, `docs/` | FastAPI REST endpoints, caching, synthetic data generator, FinBank golden scenario, demo script. |

**Shared Contract Files (Group consensus protocol required to edit):**
- `CLAUDE.md`
- `backend/core/models.py`
- `backend/rules/techniques.yaml`

---

## 3. Development Gates (G0 – G5)

| Gate | Target Milestone | Verification Requirement |
|---|---|---|
| **G0 — Contract Freeze** | Phase 0 | `models.py` frozen on `main`, `techniques.yaml` validated, `frontend/src/types.ts` generated. |
| **G1 — Walking Skeleton** | Phase 1 & 10 | `/simulate` returns hardcoded `Result` from FastAPI; frontend fetches and renders live API data. |
| **G2 — Engine Correctness** | Phase 3 & 4 | `tests/test_fixture.py` and `tests/test_invariants.py` green on `main`. |
| **G3 — The Differentiator** | Phase 6 | `evaluate_change` returns security metrics AND identifies non-empty `broken_flows` with `recommendation: "blocked"`. |
| **G4 — Feature Freeze** | Phase 12 | Zero new feature code merged; all PRs closed; full test suite passing. |
| **G5 — Rehearsal & Pitch** | Phase 13 | Full end-to-end demo executed cleanly under 4 minutes; hot-standby system prepared. |

---

## 4. FinBank Golden Scenario

The primary demonstration topology models an enterprise banking environment with high-value transactional assets, identities, and mission-critical business dependencies:

### 1. Assets (9 Core Entities)
- `asset-web-portal`: Online Banking Web Portal (DMZ, customer facing)
- `asset-api-gateway`: Core Banking API Gateway (Application Zone)
- `asset-auth-service`: OAuth2 / OIDC Token Issuer (Application Zone)
- `asset-core-banking-db`: Production Financial Ledger Database (Data Secure Zone, Crown Jewel)
- `asset-payment-processor`: SWIFT / ACH Clearing Engine (Application Zone)
- `asset-admin-jumpbox`: Privileged Bastion Jump Host (Management Zone)
- `asset-corp-workstation`: Corporate Financial Analyst Workstation (Corporate LAN)
- `asset-backup-vault`: Disaster Recovery Cloud Storage Vault (Cold Storage Zone, Crown Jewel)
- `asset-siem-server`: Central Security Log & Audit Collector (Management Zone)

### 2. Identities (4 Personas)
- `id-user-customer`: Retail Banking Customer
- `id-user-analyst`: Financial Operations Analyst
- `id-user-admin`: Lead Cloud Infrastructure Administrator (Tier-0)
- `id-svc-payment-app`: Core Payment Processing Service Account

### 3. Business Service Flows (`ServiceFlow` — The Differentiator)
Legitimate operational traffic that must remain uninterrupted:
- `flow-web-api`: Customer portal to API Gateway (Criticality: 4)
- `flow-api-auth`: API Gateway token validation to Auth Service (Criticality: 5)
- `flow-pay-db`: Payment Processor transaction ledger commits to Core Banking DB (Criticality: 5 — **Never Break**)
- `flow-svc-db`: Backend batch transaction verification to Core Banking DB (Criticality: 4)
- `flow-jump-vault`: Nightly backup snapshot archival from Jumpbox to Backup Vault (Criticality: 3)

### 4. Golden Change Narrative for Demonstration
1. **The Proposed Change:** Enforce strict cross-subnet network segmentation blocking all direct non-whitelisted traffic between Application Zone and Data Secure Zone.
2. **Naive Metric:** Attack paths from `corp-workstation` to `core-banking-db` drop by 80% (`naive_path_reduction_pct = 80%`). A standard security tool says: *"Deploy immediately."*
3. **The Sandbox Verdict:** The change severs `flow-pay-db` (Criticality 5), halting payment settlement. `evaluate_change()` flags `broken_flows: [flow-pay-db]`, sets `recommendation: "blocked"`, and discovers attacker route substitution via the admin jumpbox.
4. **Constrained Optimization:** The optimizer recommends deploying MFA on the Jumpbox + EDR on Workstations + Database Column Encryption. Security increases by 65%, cost is within budget, and zero business service flows are broken (`recommendation: "deploy"`).

---

## 5. Existing Engine Migration Strategy

The Phase 1 & 2 prototype codebase (`engine/`, `scenarios/`) proved graph ingestion, deterministic traversal, and basic control toggling. The migration into v2.1 structure proceeds as follows:

```
LEGACY STRUCTURE                              TARGET v2.1 STRUCTURE
engine/models.py         ──────────────▶      backend/core/models.py (Frozen, Immutable Tuples)
engine/twin.py           ──────────────▶      backend/core/twin.py (Lineage, Hashing, Cloning)
engine/attacker.py       ──────────────▶      backend/core/walk.py & backend/core/search.py
engine/rules.py          ──────────────▶      backend/rules/loader.py & evaluate.py
engine/attack_path.py    ──────────────▶      backend/core/search.py (Algorithm A)
scenarios/scenario.json  ──────────────▶      backend/data/scenarios/golden.json
tests/test_*.py          ──────────────▶      backend/tests/
```

### Migration Principles
1. **Preserve Validated Logic:** Existing graph semantics and node resolution helpers migrate intact.
2. **Immutable Guarantee:** Replace `list` and `set` fields in models with `tuple` and `frozenset` to ensure hashability and zero mutation leaks.
3. **Clean Decoupling:** Decouple the rule dictionary into `backend/rules/techniques.yaml` mapped to MITRE ATT&CK IDs.
4. **Zero Phase 1/2 Regressions:** Ensure all 30 existing test cases continue passing against the migrated backend modules.

---

## 6. Phase-by-Phase Implementation Plan

---

### Phase 0 — Contract and Repository Freeze
- **Objective:** Establish frozen data contracts, MITRE technique schemas, directory structure, and shared repositories before writing any feature code.
- **Tasks:**
  1. Freeze `backend/core/models.py` with immutable, hashable models (`Asset`, `Identity`, `Edge`, `ServiceFlow`, `Control`, `Agent`, `Twin`).
  2. Draft initial `backend/rules/techniques.yaml` with MITRE ATT&CK IDs (e.g., T1021.001, T1078, T1059).
  3. Validate contract types and generate initial TypeScript definitions (`frontend/src/types.ts`).
  4. Ensure directory ownership rules and pre-commit linting are in place.
- **Files Involved:**
  - `backend/core/models.py`
  - `backend/rules/techniques.yaml`
  - `frontend/src/types.ts`
  - `CLAUDE.md`, `docs/GOVERNANCE.md`
- **Deliverables:** Validated, frozen Pydantic models and YAML technique catalog.
- **Verification / Tests:**
  ```bash
  python -c "from backend.core.models import Twin; print(Twin.model_json_schema())"
  ```
- **Exit Criteria (Gate G0):** Models schema exports cleanly; `frontend/src/types.ts` matches Python models; all team members rebase on `main`.
- **Dependencies:** None.
- **Responsibilities:** All tracks (A, B, C, D) participate and agree.

---

### Phase 1 — Existing Engine Migration
- **Objective:** Migrate existing prototype logic (`engine/`, `scenarios/scenario.json`) into the v2.1 modular package architecture (`backend/core/`, `backend/data/`) without breaking behavior.
- **Tasks:**
  1. Migrate FinBank entities and relationships to `backend/data/scenarios/golden.json` adding `flows` for business dependencies.
  2. Refactor `engine/twin.py` into `backend/core/twin.py` supporting deterministic content hashing (`twin.hash()`) and immutable `clone()`.
  3. Port `AttackerState` and traversal rule models into `backend/core/` supporting frozen state tuples.
  4. Verify existing 30 test assertions against the new directory structure.
- **Files Involved:**
  - `backend/core/twin.py`
  - `backend/core/models.py`
  - `backend/data/scenarios/golden.json`
  - `backend/tests/test_migration.py`
- **Deliverables:** Migrated core package with deterministic snapshot cloning and golden scenario.
- **Verification / Tests:**
  ```bash
  pytest backend/tests/test_migration.py -v
  ```
- **Exit Criteria:** All 30 existing test cases pass against `backend/core/`; twin cloning produces independent hashable instances.
- **Dependencies:** Phase 0.
- **Responsibilities:** Track A (Lead) assisted by Track D.

---

### Phase 2 — Rule Loader and Compiler
- **Objective:** Parse and compile declarative MITRE ATT&CK techniques from YAML into an efficient in-memory lookup table.
- **Tasks:**
  1. Implement `backend/rules/loader.py` to read `techniques.yaml` and validate against Pydantic schema.
  2. Implement technique compiler indexing prerequisite capabilities, granted privileges, costs, success rates, and blocking controls.
  3. Add ATT&CK matrix validation ensuring each technique maps to a recognized tactic ID.
  4. Write unit tests asserting proper error handling on malformed technique definitions.
- **Files Involved:**
  - `backend/rules/techniques.yaml`
  - `backend/rules/loader.py`
  - `backend/tests/test_rules_loader.py`
- **Deliverables:** Validated technique catalog containing at least 12 realistic enterprise techniques.
- **Verification / Tests:**
  ```bash
  pytest backend/tests/test_rules_loader.py -v
  ```
- **Exit Criteria:** Techniques load without schema errors; indexed table accessible by technique ID in $O(1)$ time.
- **Dependencies:** Phase 0.
- **Responsibilities:** Track B.

---

### Phase 3 — Stateful Attack Path Search (Algorithm A)
- **Objective:** Implement complete state-space path search (Algorithm A) exploring reachable attack paths with cycle prevention and capability requirements.
- **Tasks:**
  1. Write `tests/test_fixture.py` FIRST with a hand-calculated 6-node graph with known paths.
  2. Implement `backend/core/search.py` with state `(node, frozenset(capabilities_held))`.
  3. Enforce strict bounded exploration (`max_depth=8`, `max_states=5000`) with explicit truncation exceptions.
  4. Compute headline metrics: critical path count, shortest hop distance, choke-point edge frequencies.
- **Files Involved:**
  - `backend/core/search.py`
  - `backend/tests/test_fixture.py`
  - `backend/tests/test_search.py`
- **Deliverables:** Complete deterministic attack path discovery engine.
- **Verification / Tests:**
  ```bash
  pytest backend/tests/test_fixture.py backend/tests/test_search.py -v
  ```
- **Exit Criteria (Gate G2 Part 1):** `test_fixture.py` passes with exact asserted path counts; zero infinite loops on cyclic topologies.
- **Dependencies:** Phase 1, Phase 2.
- **Responsibilities:** Track A.

---

### Phase 4 — Agent Simulation (Algorithm B)
- **Objective:** Implement sampled Monte Carlo agent random walk simulation (Algorithm B) modeling adaptive adversaries.
- **Tasks:**
  1. Implement `backend/core/walk.py` with agent profiles (`Agent`: skill, noise budget, objective).
  2. Implement local edge scoring and probabilistic selection based on technique cost and control efficacy.
  3. Support seeded RNG for 100% deterministic test replayability.
  4. Optimize inner loop to execute $N=1000$ walks in under 1 second.
- **Files Involved:**
  - `backend/core/walk.py`
  - `backend/tests/test_walk.py`
  - `backend/tests/test_invariants.py`
- **Deliverables:** High-performance agent random walk simulation engine.
- **Verification / Tests:**
  ```bash
  pytest backend/tests/test_walk.py backend/tests/test_invariants.py -v
  ```
- **Exit Criteria (Gate G2 Part 2):** 1000 trials complete in $<1.0\text{s}$; identical seeds produce identical distributions; invariant tests pass.
- **Dependencies:** Phase 1, Phase 2.
- **Responsibilities:** Track A.

---

### Phase 5 — Results and Metrics
- **Objective:** Define and compute structured simulation results, cost distributions, and before/after deltas.
- **Tasks:**
  1. Implement `backend/core/results.py` defining frozen `Result` and `Delta` models.
  2. Compute `p_success`, `mean_cost`, `p90_cost`, `cost_distribution` histogram bins, and `weighted_risk`.
  3. Implement `diff(before: Result, after: Result) -> Delta` calculating:
     - `naive_path_reduction_pct` (headline path count reduction)
     - `honest_cost_increase_pct` (attacker effort increase)
     - `substituted_paths` (new emergent paths taken by the attacker)
- **Files Involved:**
  - `backend/core/results.py`
  - `backend/tests/test_results.py`
- **Deliverables:** Analytics computation module producing comparative change deltas.
- **Verification / Tests:**
  ```bash
  pytest backend/tests/test_results.py -v
  ```
- **Exit Criteria:** `diff()` correctly reports path reductions and isolates substituted paths between twin states.
- **Dependencies:** Phase 3, Phase 4.
- **Responsibilities:** Track A.

---

### Phase 6 — Control Evaluation (The Differentiator)
- **Objective:** Implement `evaluate_change()` joining security risk reduction with business service flow breakage.
- **Tasks:**
  1. Implement `backend/rules/evaluate.py` with `evaluate_change(twin, controls, agents) -> ChangeVerdict`.
  2. Clone twin with proposed controls applied; re-run Algorithm A and Algorithm B.
  3. Intersect control scope and blocked techniques with the twin's `ServiceFlow` set to identify `broken_flows`.
  4. Implement business impact verdict logic:
     - If any broken flow has `criticality >= 4`: `recommendation = "blocked"`
     - If security improves with zero broken flows: `recommendation = "deploy"`
     - Otherwise: `recommendation = "review"`
- **Files Involved:**
  - `backend/rules/evaluate.py`
  - `backend/tests/test_evaluate.py`
- **Deliverables:** Core change evaluation engine delivering the product differentiator.
- **Verification / Tests:**
  ```bash
  pytest backend/tests/test_evaluate.py -v
  ```
- **Exit Criteria (Gate G3):** Evaluating network segmentation on golden scenario detects broken payment ledger flow and outputs `recommendation: "blocked"`.
- **Dependencies:** Phase 1, Phase 2, Phase 5.
- **Responsibilities:** Track B.

---

### Phase 7 — Confidence and Verdict Engine
- **Objective:** Calculate statistical confidence intervals and risk scoring for change advisory board decisions.
- **Tasks:**
  1. Implement confidence calculation based on sample size, control efficacy variance, and path coverage.
  2. Output clear explainability text detailing *why* a change is blocked or approved.
  3. Formulate structured `ChangeVerdict` payload for frontend rendering.
- **Files Involved:**
  - `backend/rules/verdict.py`
  - `backend/tests/test_verdict.py`
- **Deliverables:** Explainable decision support engine with confidence bounds.
- **Verification / Tests:**
  ```bash
  pytest backend/tests/test_verdict.py -v
  ```
- **Exit Criteria:** Every verdict includes `confidence` score $[0.0, 1.0]$ and plain-English justification.
- **Dependencies:** Phase 6.
- **Responsibilities:** Track B.

---

### Phase 8 — Control Optimizer
- **Objective:** Implement constrained portfolio optimization selecting the most effective defensive controls under budget and operational constraints.
- **Tasks:**
  1. Implement `backend/rules/optimize.py` providing `optimize_controls(twin, candidate_controls, budget, max_broken_criticality=3)`.
  2. Implement greedy selection prioritizing risk reduction per dollar spent while hard-blocking any control that severs flows $\ge 4$.
  3. Contrast output against naive unconstrained top-N ranking to demonstrate business value.
- **Files Involved:**
  - `backend/rules/optimize.py`
  - `backend/tests/test_optimize.py`
- **Deliverables:** Constrained knapsack optimization module for security controls.
- **Verification / Tests:**
  ```bash
  pytest backend/tests/test_optimize.py -v
  ```
- **Exit Criteria:** Optimizer selects high-impact controls without exceeding budget or breaking critical business flows.
- **Dependencies:** Phase 6, Phase 7.
- **Responsibilities:** Track B.

---

### Phase 9 — Blast Radius and Continuous Sync
- **Objective:** Implement immediate blast radius calculation and dynamic environment update synchronization.
- **Tasks:**
  1. Implement `backend/core/blast_radius.py` computing downstream compromised assets using `nx.descendants` and asset criticality rollups.
  2. Implement continuous synchronization endpoint re-importing updated scenario JSON and detecting security regression.
  3. Provide lineage tree tracking (`twin.parent_id`) across successive changes.
- **Files Involved:**
  - `backend/core/blast_radius.py`
  - `backend/core/sync.py`
  - `backend/tests/test_blast_radius.py`
- **Deliverables:** Blast radius analyzer and delta sync module.
- **Verification / Tests:**
  ```bash
  pytest backend/tests/test_blast_radius.py -v
  ```
- **Exit Criteria:** Blast radius returns downstream compromise set in $<50\text{ms}$; sync re-import successfully detects introduced vulnerabilities.
- **Dependencies:** Phase 1, Phase 3.
- **Responsibilities:** Track A (Blast Radius), Track D (Sync).

---

### Phase 10 — API and Backend Integration
- **Objective:** Expose the digital twin engine via high-performance FastAPI REST endpoints with caching.
- **Tasks:**
  1. Implement `backend/api/main.py` and `backend/api/routes.py` with the 8 agreed routes:
     - `GET /twin/{id}`
     - `POST /twin/{id}/clone`
     - `POST /simulate`
     - `POST /evaluate-change`
     - `POST /optimize`
     - `GET /matrix/{twin_id}`
     - `GET /blast-radius/{asset_id}`
     - `GET /lineage/{twin_id}`
  2. Implement content-addressed cache in `backend/api/cache.py` keyed by `(twin_hash, agent_id, seed, n)`.
  3. Configure CORS middleware for local frontend development.
  4. Precompute golden scenario simulation at application startup for instant demo response.
- **Files Involved:**
  - `backend/api/main.py`
  - `backend/api/routes.py`
  - `backend/api/cache.py`
  - `backend/tests/test_api.py`
- **Deliverables:** Fully functional FastAPI backend with content-addressed caching.
- **Verification / Tests:**
  ```bash
  pytest backend/tests/test_api.py -v
  ```
- **Exit Criteria (Gate G1 / Integration):** All 8 endpoints return valid schema-conforming JSON responses; cached responses return in $<10\text{ms}$.
- **Dependencies:** Phase 3, 4, 5, 6, 8, 9.
- **Responsibilities:** Track D.

---

### Phase 11 — Frontend Dashboard
- **Objective:** Build an intuitive, high-impact security change advisory dashboard in React 18, TypeScript, and Tailwind CSS.
- **Tasks:**
  1. Scaffold frontend with Vite, TypeScript, Tailwind, Lucide icons, and React Flow.
  2. Implement interactive network topology graph displaying assets, zones, and animated attack paths.
  3. Build the Change Advisory Console displaying `ChangeVerdict`, `broken_flows` warning alerts, and recommendation badges.
  4. Build Recharts visualization with overlaid before/after attacker cost histograms.
  5. Implement control optimizer panel and matrix heatmap view.
- **Files Involved:**
  - `frontend/src/App.tsx`
  - `frontend/src/views/TopologyView.tsx`
  - `frontend/src/views/ChangeConsole.tsx`
  - `frontend/src/views/OptimizerView.tsx`
  - `frontend/src/components/CostHistogram.tsx`
  - `frontend/src/api/client.ts`
- **Deliverables:** Interactive web interface displaying graph, simulation metrics, and change verdicts.
- **Verification / Tests:**
  ```bash
  cd frontend && npm run build
  ```
- **Exit Criteria:** Frontend builds with zero TypeScript errors; renders topology and live simulation results fetched from FastAPI backend.
- **Dependencies:** Phase 0 (types), Phase 10 (API).
- **Responsibilities:** Track C.

---

### Phase 12 — Testing and Hardening
- **Objective:** Execute rigorous integration testing, performance profiling, edge-case validation, and feature freeze.
- **Tasks:**
  1. Implement `backend/tests/test_scenario.py` verifying the golden demo scenario against exact run sheet values.
  2. Profile performance to ensure end-to-end simulation returns under 2 seconds.
  3. Build "Reset Demo" mechanism to quickly restore pristine scenario state between judging demonstrations.
  4. Enforce strict Feature Freeze (Gate G4).
- **Files Involved:**
  - `backend/tests/test_scenario.py`
  - `backend/tests/test_invariants.py`
  - Entire repository
- **Deliverables:** Hardened codebase with zero test failures and pinned scenario assertions.
- **Verification / Tests:**
  ```bash
  pytest -v
  ```
- **Exit Criteria (Gate G4 — Feature Freeze):** 100% test pass rate across all suites; zero new feature PRs accepted.
- **Dependencies:** Phases 1–11.
- **Responsibilities:** All tracks (A, B, C, D).

---

### Phase 13 — Final Demo Integration
- **Objective:** Rehearse the timed 4-minute presentation, calibrate demonstration narratives, prepare fallback assets, and finalize pitch slides.
- **Tasks:**
  1. Conduct full timed rehearsals (under 4 minutes) executing the exact FinBank change narrative.
  2. Verify oral answers to core judge technical questions (prior art boundaries, state explosion, model confidence).
  3. Capture high-resolution video backup of a complete clean demo run.
  4. Configure secondary laptop as local hot-standby.
- **Files Involved:**
  - `docs/DEMO_SCRIPT.md`
  - `docs/RUNBOOK.md`
- **Deliverables:** Polished 4-minute presentation, synchronized slide deck, and fallback recording.
- **Verification / Tests:**
  - Timed dry-run completion $<240\text{s}$ with both terminals (`uvicorn` and `npm run dev`) active.
- **Exit Criteria (Gate G5):** Flawless end-to-end execution during final team rehearsal.
- **Dependencies:** Phase 12.
- **Responsibilities:** All tracks (D leads presentation flow; A defends technical questions).

---

## 7. Final Definition of Done

The project is considered complete when all of the following conditions are satisfied:

- [ ] **Data Contract & Architecture:**
  - `backend/core/models.py` uses frozen Pydantic models with immutable `tuple` and `frozenset` collections.
  - Techniques are defined externally in `backend/rules/techniques.yaml` with valid MITRE ATT&CK IDs.
- [ ] **Dual Algorithms Implemented & Decoupled:**
  - Algorithm A (`core/search.py`) discovers complete state-space attack paths bounded by depth and state limits.
  - Algorithm B (`core/walk.py`) performs fast Monte Carlo sampled walks without invoking global search.
- [ ] **Business Service Flow Differentiation:**
  - `ServiceFlow` dependencies are tracked with criticality ratings.
  - `evaluate_change()` correctly flags broken flows $\ge 4$ and blocks unsafe security changes.
- [ ] **Decision & Optimization Support:**
  - Constrained optimizer selects portfolios maximizing security while guaranteeing zero business flow breakage.
  - Confidence intervals and explainable verdict justifications accompany every evaluation.
- [ ] **API & Frontend Delivery:**
  - FastAPI serves all 8 endpoints with content-addressed caching.
  - React Flow renders topology and animated attack paths; Recharts renders overlaid cost histograms.
- [ ] **Test Coverage & Stability:**
  - Fixture tests, invariant tests, and scenario tests pass with 100% success rate.
  - Zero unhandled exceptions or infinite loops on cyclic topologies.
- [ ] **Demo Preparedness:**
  - Golden scenario executes cleanly in under 4 minutes.
  - Backup video recording and hot-standby system prepared.
