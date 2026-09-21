# Foundry Local Feasibility Analysis

Date: 2026-09-19
Decision: **DOCUMENTED AND SKIPPED.** Foundry Local was not installed, no model
weights were downloaded, no driver was installed, and no Windows setting was
changed.

## 1. Why it was considered

Foundry Local runs Microsoft Foundry models on the local machine. If it were
practical here it would remove the central limitation of this submission: that
no agent has ever actually run. Local inference costs no Azure money, so a run
would not violate the zero-spend constraint.

That made it worth measuring rather than assuming.

## 2. Measured hardware

Taken from this machine on 2026-09-19, not estimated.

| Component | Measured | Assessment for local inference |
| --- | --- | --- |
| CPU | Intel Core Ultra 5 226V, 8 cores, 8 threads | Capable. Lunar Lake generation, includes an NPU. |
| RAM installed | 15.52 GB | Adequate in principle |
| **RAM free** | **2.11 GB** | **Blocking.** See section 3. |
| GPU | Intel Arc 130V integrated | Shares system memory, so it competes for the same scarce RAM |
| Disk C: free | 25.9 GB | Tight. Model cache defaults to the user profile on C:. |
| Disk D: free | 168.5 GB | Available, but relocating the cache is a configuration change |
| Foundry CLI | Not installed | Would need installing |

## 3. The blocking constraint

Free RAM is 2.11 GB of 15.52 GB installed. The session has already been
interrupted once today: the Vite dev server was terminated by the harness because
the system reported critically low memory.

A small quantized model, roughly 3 to 4 billion parameters at 4-bit, needs
approximately 2.5 to 4 GB resident before context. That exceeds what is free.
The realistic outcomes are:

- Heavy paging to a C: drive that has 25.9 GB free, which is slow and writes
  tens of gigabytes.
- The operating system reclaiming memory from the user's open applications.
- Another harness termination mid-task, five days before the deadline.

The integrated Arc GPU does not rescue this. It has no dedicated VRAM and draws
from the same system memory pool, so GPU offload moves the pressure rather than
relieving it.

## 4. What installation would actually require

1. Install the Foundry Local CLI. Not present.
2. Download model weights, several GB, onto a C: drive with 25.9 GB free.
3. Possibly relocate the model cache to D:, which is a configuration change.
4. Free several GB of RAM, which would mean closing the user's applications.
   Prohibited by the operating rules for this session.
5. Rewrite the nine agent definitions against a local endpoint, since the
   deployed Foundry agents point at a hosted gpt-5-mini deployment.

Step 5 is the one usually overlooked. Foundry Local would not execute
GridResolveAIWorkflow v5. The workflow is a Foundry cloud resource referencing
cloud agents. Running locally means standing up a parallel implementation, which
is the Agent Framework migration in `docs/AGENT_FRAMEWORK_MIGRATION.md`, not a
configuration switch.

## 5. What a local run would and would not prove

Would prove:

- That the agent instructions produce usable output.
- That the evidence and policy citation contract survives a real model.
- That the compliance gate rejects an ungrounded draft in practice.

Would not prove:

- Anything about the deployed Foundry configuration. A different model on
  different hardware through a different orchestrator is a different system.
- Any claim of the form "GridResolveAIWorkflow v5 was executed". Presenting a
  local run as a Foundry run would be precisely the misrepresentation this
  project is built to avoid.

So the honest label for a local run would be `OFFLINE_DEMONSTRATION`, which is
the label the Control Center already carries. The marginal gain over what exists
is therefore smaller than it first appears.

## 6. Decision

Skipped. Reasoning, in order of weight:

1. Insufficient free RAM, with a memory-pressure termination already recorded
   today.
2. The submission video is unfinished and is the higher priority with five days
   remaining.
3. A local run cannot be labelled as a Foundry run, so it does not convert
   CONFIGURED_NOT_RUN into RUNTIME_PROVEN.
4. It requires installing software, downloading weights and changing
   configuration, all of which the current operating rules restrict.

## 7. If revisited

Preconditions before attempting:

- At least 6 GB free RAM, verified immediately before starting.
- Model cache relocated to D:, which has 168.5 GB free.
- A small quantized model chosen deliberately, not the largest that fits.
- The result labelled `OFFLINE_DEMONSTRATION` in every artifact.
- The submission video finished first.

Execution status: PREPARED_NOT_EXECUTED. Reason: insufficient free memory and
higher priority work, not cost.
