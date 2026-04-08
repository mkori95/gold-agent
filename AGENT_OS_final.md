# AGENT_OS.md — Personal AI Operating System
### Manikanta's Agentic Development Studio
### Last updated: Session 9 (final)

---

## Stack — Final Decision

| Component | Tool | Why |
|---|---|---|
| Orchestrator | OpenClaw | Runs on Mac Mini 24/7, WhatsApp interface, uses Claude Pro natively |
| Brain | Claude (via Pro subscription) | No Bedrock needed — OpenClaw uses existing Claude Pro account via OAuth |
| Coding hands | Claude Code | Reads repo, writes files, runs tests, fixes errors in a loop |
| Dashboard | Mission Control (builderz-labs) | See tasks, costs, agent activity, approve work |
| Memory | CONTEXT.md + OpenClaw built-in | CONTEXT.md is single source of truth |
| Communication | WhatsApp via OpenClaw gateway | Already on phone, no new app |
| Version control | GitHub (mkori95/gold-agent) | Agents push to branches, you approve PRs |

**Hermes — deferred.** Revisit in 1 month if OpenClaw memory feels insufficient.
**Bedrock — not needed.** Claude Pro subscription covers OpenClaw brain.

---

## Hardware

```
Mac Mini (16GB RAM — ready)
  → Runs 24/7 headless after Day 1 setup
  → OpenClaw installed as system service
  → Claude Code installed globally
  → gold-agent repo cloned locally
  → Access via SSH or screen share from MacBook
```

---

## How It Works

```
You (WhatsApp)
    ↓
OpenClaw (Mac Mini — 24/7)
    ↓ uses Claude Pro as brain
    ↓ triggers Claude Code for coding tasks
    ↓
Claude Code
    → reads gold-agent repo
    → writes files
    → runs tests
    → pushes to branches
    ↓
Reports back to you on WhatsApp
```

### Example flows

```
"fix failing tests"
  OpenClaw → claude code "fix failing tests"
  Claude Code → reads repo, fixes, runs tests
  OpenClaw → "Fixed 3 tests. Branch: fix/tests. Review PR?"

"build the alert-checker Lambda"
  OpenClaw → claude code "build alert-checker Lambda
              following consolidator pattern in CONTEXT.md"
  Claude Code → reads CONTEXT.md + consolidator files
              → writes Lambda skeleton + tests
              → pushes to branch
  OpenClaw → "Done. PR ready for review."

"what's the state of Gold Agent?"
  OpenClaw → reads CONTEXT.md
  OpenClaw → "Phase 1 complete locally.
              AWS setup next.
              3 open PRs waiting for review."
```

---

## Agent Architecture (Simplified)

No separate dev/test/git agents needed.
Claude Code handles all of that natively.

```
OpenClaw (orchestrator)
  → Chief of Staff persona
  → Reads CONTEXT.md first on every task
  → Delegates coding tasks to Claude Code
  → Reports to you via WhatsApp
  → Never deploys to AWS without your approval
  → Daily briefing at 8AM IST
```

---

## Dashboard — Mission Control

```
github: builderz-labs/mission-control
runs: localhost:3000 on Mac Mini
access: via browser on MacBook or iPhone via Tailscale

Shows:
  → Active tasks and status
  → Token usage + cost against AWS credits
  → Agent activity logs
  → Task approval queue (Aegis review)
  → Cron job schedules
```

---

## Rules — Baked Into OpenClaw Persona

```
1. Always read CONTEXT.md before starting any task
2. Never deploy to AWS — prepare commands, ask Manikanta
3. Never commit directly to main — always feature branch
4. If ambiguous — ask before starting
5. Daily briefing at 8AM IST via WhatsApp
6. Update CONTEXT.md suggestions after significant decisions
7. Never spend >$5 API credits without flagging
```

---

## Setup Plan (1 Day)

```
Step 1 — Install OpenClaw on Mac Mini          (1 hour)
  curl -fsSL https://openclaw.ai/install.sh | bash
  openclaw onboard

Step 2 — Connect WhatsApp                      (30 mins)
  openclaw gateway setup
  Follow WhatsApp pairing instructions

Step 3 — Give OpenClaw terminal access         (15 mins)
  Enable bash/terminal tool in OpenClaw settings
  Set working directory to ~/gold-agent

Step 4 — Feed it CONTEXT.md                   (15 mins)
  Add CONTEXT.md as a skill/memory document
  Test: "What is the current state of Gold Agent?"

Step 5 — Install Mission Control               (30 mins)
  git clone builderz-labs/mission-control
  pnpm install && pnpm start
  Connect to OpenClaw runtime

Step 6 — Test full flow                        (15 mins)
  WhatsApp: "run all tests in gold-agent"
  Verify Claude Code runs, reports back
  Check Mission Control shows the task
```

**Total: ~2.5 hours. Same day.**

---

## Parallel Tracks After Setup

```
Track 1 — AWS Setup
  Get Phase 1 live in AWS
  Wire dynamo_writer.py + s3_writer.py with real boto3
  EventBridge schedule
  Credits valid until August 2026

Track 2 — Agent OS in use
  Agents helping build Phase 2 WhatsApp bot
  Daily briefings running
  Mission Control monitoring everything
```

---

## Current Status

```
✅ Claude Pro — active
✅ Claude Code — installed
✅ Mac Mini — ready (16GB RAM)
✅ AWS credits — $220, valid until August 2026
✅ Gold Agent Phase 1 — complete locally, needs AWS deploy
⏳ OpenClaw — to be installed
⏳ Mission Control — to be installed
⏳ AWS setup — next session
⏳ Phase 2 WhatsApp bot — after AWS setup
```

---

## Open Questions for New Chat

```
1. WhatsApp or Telegram for OpenClaw gateway?
   (WhatsApp = what Gold Agent users will use
    Telegram = easier to set up for testing)

2. First task for agents after setup?
   (AWS setup? Or Phase 2 Lambda skeleton?)

3. Tailscale for remote access to Mac Mini?
   (Needed to access Mission Control from phone)
```

---

*Created: Session 9*
*Status: Architecture finalised. Ready to build.*
*Next: New chat → OpenClaw setup + AWS setup in parallel*
*Owner: Manikanta Bharadwaj Koride*
*Repo: mkori95/gold-agent*
