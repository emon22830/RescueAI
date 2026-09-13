---
doc: product
version: 1
updated: 2026-09-14
status: active
---

# What we are building

A project's real state is never in one place. Linear says *In Progress*. The Slack thread
says the API contract changed three weeks ago. The spec in Drive still describes the old
one. Nobody is lying — nobody is looking at all six places at once.

This is not a chatbot that answers questions about projects. It is a system that
continuously rebuilds a project's state from evidence. Chat is one view onto that state;
the state exists whether anyone asks or not.

## The loop

```
Collect evidence → Normalize → Cross-reference → PROJECT STATE
                                                      │
                                  Progress · Blockers · Risks
                                                      ↓
                                             Recovery plan
                                                      ↓
                                            Human approval
                                                      ↓
                                      Actions written back
                                                      ↓
                                 Re-sync → new state ──┐
                                            ↑──────────┘
```

## Where the value is

Not in summarizing each app — every app already does that. It is in the sentence no
single app can produce:

> The payment API is blocked because the requirements changed after implementation
> started. It is on the critical path for launch, and the launch review is in six days.

That requires Slack + Gmail + Drive + Linear + Calendar at the same time.

## The rule that follows from it

The system never says "the project is at risk". It says why, and shows the messages,
issues and documents that prove it. A finding with no evidence is a bug.

## Demo scenario

One controlled project, "SaaS Product Launch", seeded in the real connected workspaces:

| App | What it holds |
|---|---|
| Slack | Team discussion of a payment API blocker |
| Gmail | A PM communicating a requirements change |
| Drive | Requirements v3 with the changed payment requirement |
| Linear | 10–15 issues; PAY-124 overdue |
| GitHub | Payment-related PR activity showing the engineering picture |
| Calendar | An upcoming launch review |

The agent must discover all of it through the real integrations.
