# Design Skills Router Implementation Plan

> For agentic workers: use superpowers:executing-plans for inline implementation.

**Goal:** Create a private skills plugin using the v0.4 tree for supervised UI web decisions.
**Architecture:** One skill + exact tree snapshot + portable JSON ledger + local Python helper; no server.
**Tech Stack:** Python 3 standard library, JSON, Markdown, Agent Plugins 1.0.
**Spec:** SPEC.md

## Global Constraints
Do not edit the v0.4 tree. No implicit approval. No automatic source-skill invocation. No publishing or repository writes. Keep project artifacts outside the plugin.

## Review Focus
- Wrong branch or stale approval must block progress.
- Missing skill receipt or alternatives must block proposal.
- ALL branches stay pending independently.
- Candidate context cannot cross to another component.
- Audit scope and unresolved inventory must prevent implementation readiness.

## Tasks
1. [x] Tests first for packets, traversal, approvals, coverage and integrity; observe missing runtime failure.
2. [x] Implement runner; run the whole test suite and negative cases.
3. [x] Author skill, reference CLI/ledger contracts, examples and limitations; validate packaging and links.
4. [ ] Replay fresh CLI scenario, inspect final ZIP, create private plugin, read back skill and metadata.

No new git remote or user-repository commit is authorized. Independent agent behavior evaluation is unavailable in this harness and must be labelled NOT_RUN.
