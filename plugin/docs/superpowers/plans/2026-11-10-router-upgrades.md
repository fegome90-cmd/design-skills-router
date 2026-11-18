# Design Skills Router — Assisted Experience Upgrade Implementation Plan (revision 2)

> **For agentic workers:** Use `superpowers:executing-plans` for a bounded inline implementation. Follow RED→GREEN for behavior changes and stop at publication, destructive writes, or privilege changes. This file supersedes the earlier plan for **future work**; the original plan is preserved as `2026-11-10-router-upgrades-original.md`.

**Goal:** Turn the 82-reference decision tree into a genuinely assisted experience, with three useful interruption levels rather than dozens of user questions, without weakening phase gates or source/verification discipline.

**Architecture:** Reuse `design-tree`, its existing `assistance.py`, `runner.py`, contracts, CLI, three modes and v0.4 tree. First test conversation-level routing/interruptions and clarify the skill instructions; change Python only if reproduced tests expose a real policy defect. Keep the delivered 0.3.0 guarded overlay as an immutable prior candidate.

**Tech Stack:** Python 3 standard library + unittest, Markdown, JSON host-case fixtures, existing Agent Skills plugin. No added dependency.

**Spec:** `../../DESIGN.md` (the section “2026-11-10 amendment · Human-observed usability and three levels” is normative for this revision).

## User observation and revised priority

Felipe has tested the Router in real use and reports that it works. The actual pain is being prompted to answer the many questions derived from its approximately 82 skill references. The three existing assistance levels were requested specifically to address this. Treat this as **USER_OBSERVED live-use feedback**; it is not an independent test trace, nor does the absence of one invalidate the user's experience.

**New P0: predictable assistance and fewer avoidable interruptions.** Fresh-host activation verification moves from P0 to a follow-up evaluation task; it is not an argument for creating a second router or revalidating the existence of a skill already used by the user.

| Level | User-facing behavior | Binding boundary |
|---|---|---|
| `manual` | User decides pending nodes; minimize repetitive context and avoid prompting for every authorized read. | Each unresolved node awaits exact confirmation. |
| `guided` | Agent handles reversible choices provisionally and presents strategic/reserved issues, grouped when appropriate. | Requires an actual active, scope-bound delegation; phase gate remains human. |
| `phase_auto` | Agent works autonomously within one authorized phase, then delivers one reviewable phase package. | Cannot auto-accept the phase or open the next one; external actions still separately gated. |

**Default UX decision:** Recommend `guided` during a **single initial framing** when the user has not stated a level. This is a *suggested conversational starting point*, **not** a switch in persisted authority. `runner.new_state`, `grant_template` and `resume` stay `manual` until the user explicitly provides a delegation grant. When the user has already specified `manual`, `guided` or `phase_auto`, do not ask again. Existing valid grants are reused within their exact scope. If the user does not approve the recommendation, remain manual.

## Status of previous plan (reference only; do not redo)

| Earlier task | 2026-11-10 candidate evidence | New priority |
|---|---|---|
| T1 release portability | Implemented in guarded 0.3.0 candidate; version tests no longer aim at downgrades. | No new action except regression. |
| T2 host-case structure | 12 labelled cases available; independent host execution not collected. | Extend for UX levels; do not represent labels as measured behavior. |
| T3 typed verification / migration | Candidate implemented and locally tested; `design-tree-ledger/0.3`, conservative migration and `PASS/FAIL/N/A/UNVERIFIED`. | Preserve without modification unless regression. |
| T4 learning proposals | External `PROPOSED` template in candidate; no autoedits. | Preserve. |
| T5 package audit | Previous report: 166/166 local tests in split groups; binary assets not included. | Reverify the *new* candidate before claiming final success. |

**Important:** The official private plugin was still v0.2.1 at last read; the 0.3.0 candidate is a `GUARDED_OVERLAY`, not a standalone ZIP. Previous local PASS does not prove new UX behavior.

## Global constraints

- Plugin ID: `plugins_6af0bd3b7e3c81918ab86be10f68159e`. Read current release before any future update; no update is authorized here.
- Preserve the canonical `skills/design-tree/references/tree-v0.4/*`, `baseline-lock.json`, 82 dispositions, existing pins and evidence provenance.
- Preserve the **three** levels and their real meaning. No fourth level, no new catalog, classifier, database, global tool guard, CVA dependency or Superpowers workflow at runtime.
- Do not turn the tree into a form. Its decisions remain traceable in the external ledger even when they are not user-facing questions.
- Preserve `manual` for initial state, resume, revoke and migration; never invent a grant, user receipt, authority escalation or auto-acceptance.
- Do not require a question for an already authorized read, test or reversible choice inside a valid mandate; do stop for strategic/reserved decisions, changed scope/stack, cost, sensitive access, destructive writes, publication and phase gates.
- Preserve phase boundaries and existing rights: `guided` and `phase_auto` perform **provisional** decisions; no implicit authority for next phase.
- Work in an isolated copy. No modifications to official plugin, GitHub or Library; no new real project ledger unless requested.
- Host feedback must be classified as `USER_OBSERVED`, `TRACE_VERIFIED` or `UNVERIFIED`; user feedback is valid evidence of lived UX but is not a substitute for a specific reproducible host trace.

## Review focus (risks worth pinning)

1. **Guided recommendation accidentally grants autonomy.** Check that `new_state`, `grant_template` CLI, `resume` and `revoke` still default to manual and `delegate` is blocked without a valid receipt (Task A).
2. **82 references become 82 user questions.** In `guided` and `phase_auto`, check question count and aggregate decision recording; never equate skipped prompts with skipped obligations (Tasks B/C).
3. **A user already selected a mode but is asked again.** Test explicit level, valid grant reuse and a single initial framing for missing level (Task B).
4. **Agent crosses strategic or phase gates to save questions.** Test reserved decisions, phase acceptance, phase transitions, unsupported routes and high-impact actions (Tasks A/C).
5. **Synthetic policy counts are mistaken for host usability measurements.** Keep local tests separate from fresh-chat observations and user-reported feedback; retain private traces only with permission (Task C).

## Task A — Authority-preserving assistance regression (P0)

**Files:** Read `skills/design-tree/scripts/assistance.py` and `runner.py`; extend `tests/test_assistance.py`, `tests/test_assistance_scenarios.py` **only if needed**. No production modification is expected if the current contract already passes. Update `skills/design-tree/references/ASSISTANCE.md` only to clarify UX recommendation versus persisted level.

**Interfaces:** Consume `assistance_action(state: dict, node: dict, action: str) -> dict`, `Router.new_state(...)`, `Router.grant_template(state, phase_id, level='manual')`, `Router.grant_assistance(state, grant, receipt)` and `Router.revoke_delegation(state, reason)`; do not change their meaning.

- [ ] Add or identify executable tests asserting `manual` after initialization, recovery and revoke; absence of delegation blocks `delegate`; a guided grant must be signed by an exact user receipt and scoped to its phase.
- [ ] Add negative tests for `reserved_decisions`, changed phase/scope, unavailable evidence, unapproved publication and unauthorized next phase. Assert no phantom approval is created.
- [ ] Run targeted `python3 -B -m unittest -v tests.test_assistance tests.test_assistance_scenarios tests.test_recovery_contracts`; record exact test IDs, exit status, and RED only if behavior is genuinely missing.
- [ ] If a defect is reproduced, make **one** bounded fix and rerun the targeted tests. Otherwise keep the Python code unchanged.
- [ ] **Gate A:** preserving `manual` authority is proven by actual execution; no default-grant regression.

## Task B — Single-framing behavior and level-aware questioning (P0)

**Files:** Modify `skills/design-tree/SKILL.md` (project-design section only), `skills/design-tree/references/ASSISTANCE.md`, `PILOT.md`; extend `tests/fixtures/host-routing-cases.json` and `tests/test_host_cases.py`. Keep maintenance instructions, `agents/openai.yaml` and v0.4 sources intact.

**Interfaces:** Existing names `manual`, `guided`, `phase_auto` and existing grant schema remain unchanged. This task changes *how the agent frames and asks*, not the helper's permission boundary.

- [ ] RED: add fixture checks for a new design request without level, a request explicitly choosing each level, an active granted scope, a recovered state requiring new mandate, and an unrelated editorial/backend task. Assert case schema, expected questions/interruptions and forbidden behaviors; fixture checks do not claim LLM compliance.
- [ ] Write concise skill instructions: on new design requests with unspecified level, recommend `guided` **once** in a single framing (scope, phase, deliverable, reservations); obtain exact delegation before any delegated decision. When level is explicit, obey it with no repeated selection. When prior project/context answers a question, reuse it instead of asking.
- [ ] Write concise mode behavior: `manual` asks for decisions, `guided` asks only about reserved/strategic and final gates, `phase_auto` works until its phase gate. Group related strategic questions for readability **without** merging independent approvals or omitting underlying records. No Q00 on plugin maintenance.
- [ ] GREEN: run `python3 -B -m unittest -v tests.test_host_cases tests.test_maintenance`; all cases pass. Confirm tests are testing instructions/fixtures and never assert unobserved live behavior as PASS.
- [ ] **Gate B:** normal conversations have a clear assisted path while `manual` authorization remains invariant.

## Task C — UX acceptance: measure interruptions, not invocation existence (P1)

**Files:** Extend `skills/design-tree/references/PILOT.md` with a minimal UX scorecard and `tests/fixtures/host-routing-cases.json`; produce a **separate external** observation log (never inside the shipped plugin). Reuse the 12 existing cases rather than a second test framework.

**Interfaces:** Each observation records `{case_id, level, release_id, user_or_trace_source, scope, observed_at, question_count, avoidable_questions, pending_strategic_questions, node_decisions_recorded, phase_gate_respected, result, trace_refs}`. Unavailable fields are `null`/`UNVERIFIED`, not zero/PASS.

- [ ] Construct two comparable design tasks with the same 12 reversible decision nodes and one phase gate, plus a reserved decision and explicit scope change. Keep the expected choice/receipt semantics unchanged across levels.
- [ ] Test locally that `manual` requires exact node approvals and guided/phase_auto can provisionally resolve the same 12 reversible nodes with a valid grant, without false phase acceptance. **This is policy, not measured chat turns.**
- [ ] When live evaluation is available, observe six fresh-chat cases: new request/no level, explicit manual, explicit guided, explicit phase_auto, resumed project and maintenance. Record real question counts, duplicated context requests, and human gate behavior. Do not copy private chats elsewhere without authorization.
- [ ] Accept `guided` UX only if the agent avoids one-question-per-reversible-node and stops for all reserved/strategic and phase gates; accept `phase_auto` only if it stays inside one phase and stops at exit. Judge meaningful task completion, not the smallest raw number of questions.
- [ ] Label Felipe's reported successful usage `USER_OBSERVED` and preserve as primary UX feedback. Any cases lacking real traces remain `UNVERIFIED`. Report the two separately.
- [ ] **Gate C:** evidence distinguishes functional code tests, host usability, user observation and outstanding gaps; no new publication implied.

## Task D — Regression, package, and review (P1)

**Files:** New candidate only; write release-specific verification report **outside historical logs**, no changes to baseline or existing versioned audit reports.

- [ ] Run the unit tests including A/B/C's newly added tests. If a single full run is interrupted, use non-overlapping module batches and preserve original exit codes; do not treat a timeout as PASS.
- [ ] Build a candidate from the verified source; extract/read back and rerun targeted tests on the output, not just on the source directory.
- [ ] Compare protected hashes/manifest identity, source pins and version policies. The three missing icons mean a guarded overlay **must not be called standalone**; recover verified official binaries before any proposed full-package publication.
- [ ] Review the entire diff against this plan with an independent reviewer if available; otherwise label it `self-review`, report limitations and give findings severity. Fix any important finding with RED→GREEN and rerun regression.
- [ ] **Gate D:** local test evidence and remaining host gaps are explicit; no auto-promotion. A future official update requires separate user approval, current `expected_release_id`, readback and host checks.

## Decision summary and handoff

- **Chosen approach:** assisted behavior through current contracts and narrowly scoped skill instructions, rather than a new rater/agent or weakening the decision tree.
- **User-facing recommended level:** `guided` for a new design request without a stated mode; this recommendation is **not an authorization**. Explicit modes always win.
- **Current code/official status:** 0.3.0 guarded candidate from the preceding implementation; official release was 0.2.1 when checked. This revised plan does **not** deploy or implement these new UX changes.
- **Next action:** run Task A→D against an isolated copy; report measured question burden and phase behavior before requesting a separate promotion decision.
