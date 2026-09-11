# Governance — four people, one repo, 24 hours

The thing that kills four-person hackathon teams is not difficulty. It is **merge
conflicts and interface drift**: two people editing the same file, or one person changing
a type that three others depend on without telling them.

Everything below exists to make those two failures impossible rather than unlikely.

---

## 1. Directory ownership — the primary conflict-avoidance mechanism

**People own directories, not features.** Features cut across files; directories do not.
If your task needs a file outside your directory, you do not edit it — you ask the owner.

```
hackx/
├── CLAUDE.md                     SHARED — group change only
├── README.md                     D
├── docs/                         D
│
├── backend/
│   ├── core/                     ══ OWNER: A (engine) ══
│   │   ├── models.py             FROZEN CONTRACT — group change only
│   │   ├── twin.py               clone(), hashing, lineage
│   │   ├── search.py             complete path search (algorithm a)
│   │   ├── walk.py               sampled agent walk (algorithm b)
│   │   └── results.py            Result, Delta, ChangeVerdict
│   │
│   ├── rules/                    ══ OWNER: B (rules & decisions) ══
│   │   ├── techniques.yaml       FROZEN CONTRACT — group change only
│   │   ├── loader.py             YAML -> technique table
│   │   ├── evaluate.py           evaluate_change(), broken-flow detection
│   │   └── optimize.py           constrained portfolio selection
│   │
│   ├── api/                      ══ OWNER: D (integration) ══
│   │   ├── main.py               FastAPI app, startup precompute
│   │   ├── routes.py             the 8 endpoints
│   │   └── cache.py              content-addressed result cache
│   │
│   ├── data/                     ══ OWNER: D ══
│   │   ├── generator.py          synthetic 200-node environment
│   │   └── scenarios/golden.json the demo twin
│   │
│   └── tests/                    A owns fixture + invariants, D owns scenario
│
└── frontend/                     ══ OWNER: C — entire tree ══
    └── src/
        ├── types.ts              generated from models.py, never hand-edited
        ├── api/client.ts
        ├── api/mocks.ts          C's unblocking mechanism
        └── views/
```

Only **three** files are ever touched by more than one person: `CLAUDE.md`,
`models.py`, `techniques.yaml`. Those get the protocol in §2. Everything else has exactly
one owner, so a conflict in it means someone broke the rule.

**Roles in one line each:**

- **A — engine owner.** Correctness of the two algorithms. Reads every line of `core/`
  personally, including AI-generated lines. **A answers the judges' technical questions.**
- **B — rules and decisions.** Technique table with ATT&CK IDs, `evaluate_change`, the
  constrained optimiser. Owns the differentiator logic.
- **C — frontend.** Entire tree. Starts at hour 1 against mocks, never blocked on backend.
- **D — integration and demo.** API wiring, cache, synthetic data, golden scenario,
  rehearsal, and the run sheet. D is also release manager (§5).

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
5. C regenerates `frontend/src/types.ts` from the new models in the same cycle.

**Do not** slip a contract change into a feature PR. That is the single most expensive
mistake available to this team.

Expect two or three of these in the first six hours and near-zero after. If you are still
changing the contract at hour 12, something is wrong with the plan, not the code.

---

## 3. Branching

`main` is always demoable. That is the whole rule; the rest is mechanics.

- Branch names: `a/search-state-space`, `b/evaluate-change`, `c/graph-view`,
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
  `techniques.yaml`, `core/search.py`, or `core/walk.py`. Wrong logic there is invisible
  and poisons every number downstream.
- CI must be green. A red test blocks merge, always, including at hour 22.
- Squash-merge so `main`'s history stays readable.

---

## 5. Integration gates

Fixed wall-clock checkpoints. **D calls them and everyone stops for them.** Fifteen
minutes each, maximum.

| Gate | Hour | Everyone must show |
|---|---|---|
| G0 — Contract | 1 | `models.py` on `main`, `types.ts` generated, all four have pulled |
| G1 — Skeleton | 4 | `/simulate` returns a hardcoded `Result`, frontend renders it from the real API |
| G2 — Engine | 9 | `test_fixture.py` green on `main` |
| G3 — Differentiator | 14 | `evaluate_change` returns both metrics and `broken_flows` |
| G4 — Feature freeze | 18 | Everything merged. No new features after this point, ever |
| G5 — Rehearsal | 21 | Full demo run end to end, under four minutes |

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
- Post a one-line status at each gate. That is the only status reporting required.

---

## 7. Working with AI sessions in parallel

All four of you will be running Claude Code simultaneously in the same repo. That is fine
if, and only if:

- Each session is told its track and its directory, and refuses work outside it.
  Open with: *"Read CLAUDE.md and docs/GOVERNANCE.md. I am track B. Only edit
  `backend/rules/`."*
- Nobody lets a session "tidy up" or refactor files it does not own. Instruct it not to.
- Nobody lets a session edit `models.py` or `techniques.yaml` without the §2 protocol.
  Say so explicitly at the start of the session — it is the single highest-value sentence
  you will type.
- Pull `main` before starting a session, so it reasons about current code rather than the
  repo as it was two hours ago.

**The velocity trap:** four AI sessions generate code far faster than four humans can read
it. At hour 16 you will hit a bug in code nobody wrote and nobody understands. The
countermeasure is the ownership rule plus A personally reading `core/` — those are the
files where a silent error is fatal rather than annoying.

---

## 8. Escalation and cut rules

- **Someone is stuck for 45 minutes:** they stop and swap with whoever is furthest ahead.
  Ego costs you the hackathon; a swap costs you twenty minutes.
- **A track is behind at a gate:** cut scope in that track, never extend the gate. The
  cut order is in `CLAUDE.md` §11.
- **A contract change is proposed after hour 12:** default answer is no. Work around it.
  The cost of re-syncing four branches late exceeds almost any benefit.
- **`main` is broken:** it is everyone's top priority until it is green. Nobody starts new
  work on a broken `main`.
