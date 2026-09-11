# Governance — four people, one repo, 24 hours

The thing that kills four-person hackathon teams is not difficulty. It is **merge
conflicts and interface drift**: two people editing the same file, or one person changing
a type that three others depend on without telling them.

Everything below exists to make those two failures impossible rather than unlikely.

---

> **Solo mode (current):** one person owns every directory. §1 is now a *file map*, not a
> people map; §2–§9 apply the moment a second person or a second AI session joins. The
> frozen-contract rule and "run `pytest` before every commit" still hold with one person.

## 1. Directory ownership — the primary conflict-avoidance mechanism

**People own directories, not features.** Features cut across files; directories do not.
If your task needs a file outside your directory, you do not edit it — you ask the owner.

```
digital-twin/                     (repo: UDITGABAA/digital-twin-udit-gaba-, branch main)
├── CLAUDE.md                     the shared brain — contract, algorithms, claims
├── README.md
├── requirements.txt
├── pytest.ini                    pythonpath = .
├── .github/workflows/ci.yml      pytest + dashboard build on every push
├── docs/
│   └── GOVERNANCE.md · IMPLEMENTATION_PLAN.md · INTERFACES.md · DEMO_SCRIPT.md · SLIDES.md · STATUS.md
│
├── scripts/
│   ├── build_golden.py           FinBank story -> scenarios/golden.json + golden_sync.json (never hand-edit the JSON)
│   └── demo.ps1 · demo.sh        one command: install, test (stop if red), build, start both servers
│
├── engine/                       ══ A: engine ══
│   ├── models.py                 FROZEN CONTRACT (+ twin_hash)
│   ├── twin.py                   clone()
│   ├── scenario.py               Scenario(twin, agents, catalogue), load_scenario()
│   ├── search.py                 complete path search (algorithm a) over CompiledEdge
│   ├── walk.py                   route_policy() + plan-then-execute trials (algorithm b)
│   ├── results.py                Result, Delta, diff()
│   └── blast.py                  credential-aware reachability + nx.descendants upper bound
│
├── rules/                        ══ B: rules & decisions ══
│   ├── techniques.yaml           FROZEN CONTRACT (10 entries)
│   ├── loader.py                 YAML -> technique table, grammar validation
│   ├── compile.py                Edge x declared technique x grants x control impacts -> CompiledEdge; matches(); broken_flows()
│   ├── evaluate.py               evaluate_change(): outcomes per agent, confidence, verdict, alternatives
│   └── optimize.py               risk() (deterministic upper bound) + exhaustive constrained optimize()
│
├── server/
│   └── app.py                    ══ D ══ FastAPI; router at "" and "/api"; serves dashboard/dist at "/" if built
│
├── scenarios/                    ══ D ══
│   ├── golden.json               FinBank
│   └── golden_sync.json          FinBank + contractor admin@jump-01 (the sync demo)
│
├── tests/
│   ├── test_fixture.py · test_invariants.py     A
│   ├── test_rules.py · test_evaluate.py         B
│   └── test_scenario.py                         D — pins every number in DEMO_SCRIPT.md
│
└── dashboard/                    ══ C ══ Vite + React + TS + Tailwind; /api proxied to :8000
    └── src/
        ├── types.ts              hand-written mirror of the Pydantic models
        ├── api/client.ts
        ├── App.tsx               state, control picker, scenario/adversary switch, status bar
        └── views/                DecisionCard (hero) · GraphView · EffortChart · OptimizerPanel
```

Only **three** files are ever touched by more than one person: `CLAUDE.md`,
`models.py`, `techniques.yaml` (and `docs/INTERFACES.md`, section-per-owner). Those get the
protocol in §2. Everything else has exactly one owner, so a conflict in it means someone
broke the rule.

**Roles in one line each** (the file map above is what each track owns; in the solo build one
person holds all four):

- **A — engine.** Correctness of the two algorithms over `CompiledEdge`. Answers the judges'
  algorithm questions (state explosion, why effort can go down).
- **B — rules and decisions.** Technique table with ATT&CK ids, `compile.py`,
  `evaluate_change`, the exhaustive optimiser. Answers breakage / confidence / verdict questions.
- **C — dashboard.** Decision card first, then graph, histograms, optimiser.
- **D — integration and demo.** API, scenarios, docs, `test_scenario.py`; calls the gates and
  drives the demo.

### 1.1 Base workflow — what "everyone together first" produced (done)

The base every track builds on is on `main` and verified by `pytest` + CI:
`engine/models.py` (+ `twin_hash`), `rules/techniques.yaml` (10), `docs/INTERFACES.md`,
`scenarios/golden.json` + `golden_sync.json` (from `scripts/build_golden.py`),
`dashboard/src/types.ts` (hand-written; `gen_types.py` was cut). A new contributor: clone,
`pip install -r requirements.txt`, `npm install --prefix dashboard`, `pytest` → 36 green, then
branch `a/…`, `b/…`, `c/…`, `d/…` off `main`.

---

## 2. Contract change protocol

`models.py` and `techniques.yaml` are the interfaces three other people build against.

**To change either one:**

1. Say it out loud in the team channel with the reason and the exact diff. Not a PR — a
   message, first.
2. Get an ack from every person whose track touches it. Silence is not an ack.
3. One person applies it in a PR titled `contract: <what changed>`, merged immediately.
4. Everyone else stops, pulls `main`, rebases, and confirms their branch still builds
   before continuing.
5. C regenerates `dashboard/src/types.ts` from the new models in the same cycle.

**Do not** slip a contract change into a feature PR. That is the single most expensive
mistake available to this team.

Expect two or three of these in the first six hours and near-zero after. If you are still
changing the contract at hour 12, something is wrong with the plan, not the code.

---

## 3. Branching

`main` is always demoable. That is the whole rule; the rest is mechanics.

- Integration branch is `main` of `UDITGABAA/digital-twin-udit-gaba-`. Nothing from the
  old `engine/` is imported by new code — it is read, ported, and deleted in the same PR
  that adds its replacement. No two implementations alive at once.
- Branch names: `a/search-state-space`, `b/compile`, `c/decision-card`,
  `d/golden-scenario`. Owner prefix so anyone can see at a glance who is on what.
- Branch off `main`, never off another feature branch.
- **Small PRs, merged fast.** Target under 400 lines. A branch older than three hours is
  a liability — if you cannot finish, merge the working part behind a flag.
- Rebase on `main` before opening a PR: `git fetch origin && git rebase origin/main`.
- Never force-push `main`. Force-push your own branch freely.
- `.gitignore` from hour zero: `__pycache__/`, `.venv/`, `node_modules/`, `dist/`,
  `.pytest_cache/`, `*.pyc`, `.env`.

**Commit early, commit often.** A commit every 20–30 minutes. At hour 19 you will want a
known-good point to reset to, and it must exist.

---

## 4. Pull requests

Optimise for speed without losing the one check that matters.

- PR body is three lines: what changed, which track, how to verify.
- **One reviewer, 10-minute SLA.** Cross-pairs: A↔B (engine logic), C↔D (integration).
  If your reviewer is heads-down, ping once and merge after ten minutes — except for the
  exceptions below.
- **These always require a real review, no timeout:** anything touching `models.py`,
  `techniques.yaml`, `engine/search.py`, `engine/walk.py`, or `rules/compile.py`. Wrong logic
  there is invisible and poisons every number downstream.
- CI must be green. A red test blocks merge, always, including at hour 22.
- Squash-merge so `main`'s history stays readable.

---

## 5. Integration gates

Fixed wall-clock checkpoints. **D calls them and everyone stops for them.** Fifteen
minutes each, maximum.

| Gate | Hour | Everyone must show |
|---|---|---|
| G0 — Contract | 1.5 | `models.py` v2.1, `techniques.yaml` (10), `docs/INTERFACES.md`, `golden.json` on `main`; `types.ts` present; all four have pulled and pass the three P0 commands |
| G1 — Skeleton | 4 | `/simulate` returns a hardcoded `Result`; the decision card renders it from the real API, mocks off |
| G2 — Engine | 9 | `test_fixture.py`, `test_invariants.py`, `test_rules.py` green on `main` |
| G3 — Differentiator | 14 | `/evaluate-change` on `seg_prod_db_full` returns both metrics, F1 in `broken_flows`, confidence Medium with a named unknown, `recommendation: blocked`, non-empty `alternatives`; the card renders all of it |
| G4 — Feature freeze | 18 | Everything merged: optimiser, matrix, sync. `pytest` green. No new features after this point, ever |
| G5 — Rehearsal | 21 | Full demo run end to end, under four minutes, twice |

**G1 is the one people are tempted to skip and must not.** Proving the frontend can call
the real backend at hour 4 — even with fake data behind it — converts integration from a
hour-18 catastrophe into a hour-4 annoyance. Walking skeleton first, logic after.

**G4 is absolute.** Every hackathon team breaks their demo in the last three hours by
adding one more thing. Hours 18–24 are rehearsal, bug-fixing and the pitch. Nothing else.

---

## 6. Communication

- One channel, and decisions get posted there, not held in someone's head.
- **"I'm blocked" is said within five minutes of being blocked**, not after 40 minutes of
  fighting it alone. Everything is time-boxed here and a silent blocker costs four people.
- When you merge something others depend on, post it: *"evaluate_change is on main."*
- Post a one-line status at each gate in `docs/STATUS.md`. That is the only status
  reporting required.

---

## 7. Working with AI sessions in parallel

All four of you will be running Claude Code simultaneously in the same repo. That is fine
if, and only if:

- Each session is told its track and its directory, and refuses work outside it.
  Open with the session opener in §9.
- Nobody lets a session "tidy up" or refactor files it does not own. Instruct it not to.
- Nobody lets a session edit `models.py` or `techniques.yaml` without the §2 protocol.
  Say so explicitly at the start of the session — it is the single highest-value sentence
  you will type.
- Pull `main` before starting a session, so it reasons about current code rather than
  the repo as it was two hours ago.

**The velocity trap:** four AI sessions generate code far faster than four humans can read
it. At hour 16 you will hit a bug in code nobody wrote and nobody understands. The
countermeasure is the ownership rule plus A personally reading `engine/` and B personally
reading `compile.py` — those are the files where a silent error is fatal rather than
annoying.

---

## 8. Escalation and cut rules

- **Someone is stuck for 45 minutes:** they stop and swap with whoever is furthest ahead.
  Ego costs you the hackathon; a swap costs you twenty minutes.
- **A track is behind at a gate:** cut scope in that track, never extend the gate. The
  cut order is in `CLAUDE.md` §11.
- **A contract change is proposed after hour 12:** default answer is no. Work around it.
  The cost of re-syncing four branches late exceeds almost any benefit.
- **`main` is broken:** it is everyone's top priority until it is green. Nobody starts
  new work on a broken `main`.

---

## 9. AI sessions talking to each other

Four sessions cannot see each other. They communicate through exactly one file and one
habit.

1. **Session opener** — paste verbatim, every session, every time:
   > Read CLAUDE.md, docs/GOVERNANCE.md and docs/INTERFACES.md. I am track **X**. Edit only
   > `<dirs>`. `engine/models.py` and `rules/techniques.yaml` are frozen. If
   > you need a function another track owns and its signature is not in INTERFACES.md, stop
   > and tell me instead of inventing one.

2. **`docs/INTERFACES.md` is the only channel between sessions.** It holds the four
   cross-track signatures with their types. A session that changes a signature edits its
   owner's section of INTERFACES.md **in the same PR** as the code. The human then posts one
   line in the team channel: `[A] route_policy(inventory, agent) is on main`. Everyone
   pulls before their next prompt.

3. **Consumers own their stubs.** Each track keeps a stand-in for what it consumes *inside
   its own directory*, matching the INTERFACES.md signature exactly:
   - C: `dashboard/src/api/mocks.ts` (fake `Result`, fake `ChangeVerdict`)
   - D: `server/stubs.py` (hardcoded `simulate`, `evaluate_change`)
   - B: `rules/_stub_policy.py` (fixed `route_policy` table until A merges)
   - A: hand-built `CompiledEdge` tuples in `tests/test_fixture.py` (no `compile.py` needed)
   Nobody is ever blocked on another track. The stub is deleted in the PR that switches to
   the real thing.

4. **Handoff message is three lines**: what merged · the signature · the command that proves
   it. Example:
   > `compile()` is on main · `compile(twin, techniques, *, naive=False) -> tuple[CompiledEdge, ...]` ·
   > `pytest tests/test_rules.py -q`

5. **`docs/STATUS.md`** — one line per track per gate, written by the human, not the session.

6. **Interface tests are the tripwire.** If `test_rules.py` goes red after A's merge, A broke
   B's interface (or vice versa). Revert, talk, re-merge. Do not "fix forward" in someone
   else's directory.

7. **Naming continues from the existing repo where it fits.** If the old `engine/` already
   uses a name that matches the v2.1 contract (`zone`, `criticality`, technique ids, ATT&CK
   ids), keep it. If it does not match the capability-token grammar or the model names in
   CLAUDE.md §5, the contract wins.

8. **Pre-Prompt Sync Routine (Mandatory before starting any AI session prompt):**
   Before typing a new task or prompt into Claude Code / Antigravity, the developer runs:
   ```bash
   git fetch origin
   git rebase origin/main
   ```
   If a teammate has merged code, the AI session will now see the latest signatures in `docs/INTERFACES.md` and avoid hallucinations.

9. **Agent Deadlock Protocol (When an AI session requests out-of-scope files):**
   - If an AI session says *"I need to edit `rules/compile.py` to make search work"*:
     1. Stop the session immediately.
     2. Remind it: *"You own Track A (`engine/`). Use your local hand-built `CompiledEdge` mock in `tests/test_fixture.py`. Do NOT touch `rules/`."*
   - If an AI session is missing a signature or model field:
     1. Check `docs/INTERFACES.md`.
     2. If absent, message the owner of that track. The owner adds the typed signature to `docs/INTERFACES.md` and commits.
     3. You rebase on `main` and resume.

10. **Per-Track Verification Matrix (Must pass 100% locally before opening PR):**
    - **Track A (Device 1 / Udit):** `pytest tests/test_fixture.py tests/test_invariants.py -v`
    - **Track B (Device 2):** `pytest tests/test_rules.py tests/test_evaluate.py -v`
    - **Track C (Device 3):** `cd dashboard && npm run build` (zero type errors)
    - **Track D (Device 4):** `pytest tests/test_scenario.py && curl.exe http://localhost:8000/docs`

