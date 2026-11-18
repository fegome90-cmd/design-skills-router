# Design Skills Router — upgrade design

Date: 2026-11-10 · Status: DESIGN_FOR_APPROVAL · No deployment authorised.

## Intent
Improve the existing Router's reliability without adding a catalogue, database, server or general agent framework. The requested phase is planning and testing. Product/runtime implementation and promotion remain separate gates.

The baseline is private plugin `plugins_6af0bd3b7e3c81918ab86be10f68159e`, release `pluginrel_6af0faaf85c48191b74563d41eeeb7ea`, version 0.2.1. Its canonical v0.4 tree, inventories, policies, icons and invocation settings are preserved.

## What changed after inspection
1. Source provenance, conditional relationships, UNKNOWN, selective invalidation, read-only doctor and human phase gates already exist. Do not implement them again.
2. The delivered release's test suite does not reproduce the historical all-green result: 127 tests ran; 122 passed, three failed and two errored. The five affected tests hard-code target 0.2.0 while the installed source is 0.2.1. The release preparer correctly refuses the downgrade.
3. Replacing only test target versions with the next patch of the source version restores all 127 test outcomes. This is a local test-only experiment, not an updated official plugin.
4. `design-tree` is discoverable and readable in this conversation's skill catalogue. Fresh-conversation activation and another agent's gate obedience remain unverified.
5. The current verification enum describes evidence method (`OBSERVED`, `STATIC`, `NOT_VERIFIED`), not an explicit pass/fail verdict. Four executable probes demonstrate that proposed outcome metadata currently has no enforcement. This is a new contract requirement, not evidence that v0.2.1 violated a promised outcome schema.

## Approaches considered
- **Documentation and tests only:** smallest change; appropriate for release reproducibility and routing observations, but cannot enforce failed required checks.
- **Small extension of the current helper:** selected recommendation. Reuse contracts, policy hashing, existing phase gates and explicit migration. Add one pure verification module, not another routing engine.
- **New orchestrator/catalogue/global tool interceptor:** rejected. It duplicates responsibilities and cannot be justified by the identified problems.

The selection is a recommendation for approval, not an assertion that Felipe approved an unseen design.

## Delivery boundaries
**Increment A:** release-test portability and a host routing evaluation pack. A patch candidate is sufficient; no behaviour/permission change.
**Increment B:** explicit verification outcomes with a guarded ledger compatibility change. A minor candidate (not a major redesign) is appropriate. Do not hide this inside a documentation patch.
**Increment C:** learning-candidate procedure, documentation-only initially. No automatic instruction mutation.

Do not require a successful host test before conducting isolated local experiments; do require it before claiming host functionality or closing the corresponding promotion gate.

## Verification outcome contract
Keep existing source provenance and method fields. Introduce `proposal.verification_results` with schema `design-tree-checks/1`, containing checks identified by ID. Each check records `result`, `method`, `scope`, `environment`, `observed_at`, `evidence_refs`, and `reason`. Allowed results: `PASS`, `FAIL`, `NOT_APPLICABLE`, `UNVERIFIED`. Methods: `STATIC_REVIEW`, `LOCAL_TEST`, `BROWSER_OBSERVATION`, `DEVICE_OBSERVATION`, `HOST_OBSERVATION`. Scopes: `helper`, `browser`, `device`, `host`.

Required obligations come from supplementary `contracts.json.verification_requirements`, not from an agent setting `required=false` in its own result. Each obligation has a unique ID, `applies_to` node IDs, `scope`, `allowed_methods`, `when` predicates, source/justification and explicit rules for non-applicability. Include normative requirements in the relevant `policy_hash`; do not modify v0.4. Do not seed unreviewed universal checks across all 82 references.

A schema validator accepts honest failure/unverified records for diagnosis but does not permit them to close a required obligation. Missing results do not mean PASS. Local tests cannot certify a host/device observation. Evidence references must resolve to actual version-bound artefacts, not a non-empty string. A false applicability decision requires supporting facts; UNKNOWN remains blocking. Re-read artefact bytes at preparation, acceptance and readiness evaluation.

The four delivered RED probes are exploratory integration constraints against the old runtime. During implementation, bind their synthetic requirement to the approved requirement contract and add the missing positive/negative tests specified in the plan. Their legacy `required` field is NOT authoritative.

## Backward compatibility
Do not relabel existing `OBSERVED` or `STATIC` records as PASS. Integrating the new normative outcome contract requires a new minor ledger schema (`design-tree-ledger/0.3`) so an older runtime rejects it rather than silently ignoring new checks. Extend the existing copy-based migration: preserve the complete old ledger/history, sources and verified files; start the new state in manual mode; grant no approvals. Old 0.1 and 0.2 states remain inspectable and migrate only explicitly to a new destination. Keep the original unchanged. If this migration exceeds the approved increment, stop after Increment A; do not remove compatibility guards to simplify delivery.

## Invocation and context
Preserve explicit invocation (`disable-model-invocation: true`, `allow_implicit_invocation: false`). A maintenance request uses the manual/doctor, never the product-design Q00 questionnaire. Unrelated backend/editorial work does not silently activate design skills. Do not add a regex classifier and describe its tests as tests of a real LLM. Build a labelled host-case pack, then collect observed transcripts/tool traces.

Maintain manual/guided/phase_auto, existing reservations and exact human gates. Evidence/knowledge cannot confer write or publication authority. There is no new autonomy level.

## Learning candidates
When a repeatable defect yields useful knowledge, prepare a candidate outside the installed plugin. Record source release, owning document, reproduction, before/after evidence, proposed small diff, affected rules and status `PROPOSED`. Separate proposing, approving and applying. Initially use a Markdown template and existing maintenance/release workflow; no queue service, importer or automatic edits.

## Non-goals
No CVA installation; no Joe Bell repository import; no external skill database; no new plugin; no UI redesign; no icon/prompt/audience change; no Library/GitHub writes; no real project ledgers; no production actions. Source and result integrity do not authenticate a person or establish aesthetic quality.

## Gates
G0: current source/equivalence and baseline evidence. G1: approval of this design and implementation plan. G2: local RED→GREEN, regression and distributed-artifact verification. G3: required host observations. G4: explicit promotion authority, guarded update and readback. Today's work reaches G0 and prepares G1. Nothing grants G4.


---

## 2026-11-10 amendment · Human-observed usability and three levels

**Status:** User requirement incorporated into the successor plan; implementation pending. Supersedes only the previous prioritization of fresh-host discovery as P0.

**Observation:** Felipe reports successfully using Design Skills Router and explicitly describes the burden of being asked to answer the roughly 80 reference/decision prompts. This is user-reported live-use evidence (`USER_OBSERVED`), not an independently reproducible host trace or a blanket PASS for specific test cases. Do not dismiss or overwrite this observation with `UNVERIFIED` automation results.

**Goal:** The 82 references remain available to the router without becoming 82 user-facing questions. Each of the three existing assistance levels must produce a different interruption policy, while preserving exact human authority boundaries.

**Default experience vs. persisted authorization:** When a new UI-design request does not specify a level, **recommend `guided` in one brief framing**. The persisted `assistance_level` and `grant-template` CLI default remain `manual` until an explicit, scope-bound delegation grant is recorded with a user receipt. A recommendation is not a grant. If a suitable scope-bound grant is already active, reuse it; do not ask again.

**Acceptance:**
- `manual`: node-level decisions are presented to the user; independent reading/test operations already authorized do not require per-tool questions.
- `guided`: reversible decisions within a valid grant are handled provisionally by the agent. Ask about strategic/reserved decisions and once at the phase gate; group related questions into one concise exchange without inventing approvals.
- `phase_auto`: within the approved phase, decide provisionally and perform allowed actions until the phase gate. No implicit next phase.
- For all levels: one requirement/component per record; maintain source provenance, 82 visible dispositions, verification outcomes and exact reservations. Lack of evidence remains blocking where required; unsupported paths remain blocked. No publication, destructive writes, spend, credential use or new project scope without separate authority.
- `resume`, migration and `revoke` remain `manual` until fresh explicit delegation. Do not infer reauthorization from a saved preference, past conversation, `ok`, or the assistant's recommendation.
- Maintain a short, explicit UX evaluation sheet with question counts, preventable interruptions, resolved decisions and gate compliance. No metric is considered measured without a transcript/observed trace and user permission to retain it.

**Non-goals:** No fourth assistance level; no tree redesign; no CVA, database, classifier, new plugin, broad autonomy or package publish in this amendment.

**Release sequencing:** The delivered 0.3.0 guarded overlay remains immutable as a prior candidate. The amended UX behavior, if implemented, produces a new candidate and separate verification report; official release 0.2.1 stays untouched until a future explicit promotion.
