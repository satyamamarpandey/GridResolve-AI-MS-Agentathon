# Publication readiness report

Prepared 2026-09-19. Nothing has been committed, pushed or published. This is an
assessment, not an action.

## Verdict

**The working tree is safe to publish.** No credential, token, key, connection
string, subscription identifier, tenant identifier, real customer record or local
environment file is present in any tracked or untracked file intended for the
repository.

**Git history does not require a rewrite.** The one historical exposure is a
resource group name, which is not a credential and grants no access. Details and
reasoning below, so the decision is yours on the facts rather than on a blanket
recommendation.

## Working tree scan

| Check | Result |
| --- | --- |
| Hardcoded secrets, API keys, tokens, connection strings | **None** |
| Subscription identifier | **Not present** |
| Tenant identifier | **Not present** |
| Foundry resource name | **Not present**, supplied by environment variable |
| Foundry project name | **Not present**, supplied by environment variable |
| Azure account email | **Not present** |
| `.env` or local settings files | **None exist**, and `.gitignore` excludes the patterns |
| Real customer data | **None**, every identifier is `SYN-` prefixed |
| Confidential company data | **None** |

Two scan matches were reviewed and are intentional:

1. `control-center/src/live/foundryAdapter.test.ts` contains the literal string
   `api_key=abc123`. It is a test fixture that exists to prove the adapter
   **rejects** any payload carrying credential-shaped content. Removing it would
   weaken a security control.
2. `control-center/src/live/foundryAdapter.ts` contains a regex matching
   `api_key`, `bearer`, `access_token` and `client_secret`. That is the detection
   itself.

Both are correct as they stand.

## Git history assessment

### What was checked

Full history, all branches, searched for the live subscription identifier, tenant
identifier, Foundry resource name, Foundry project name and Azure account email.
The identifiers were read from the authenticated CLI session and compared without
being written anywhere.

| Identifier | Present in git history |
| --- | --- |
| Subscription identifier | **No** |
| Tenant identifier | **No** |
| Foundry resource name | **No** |
| Foundry project name | **No** |
| Azure account email | **No** |
| Any credential or token | **No** |

The only GUID anywhere in history is `3e63ea09-8043-4f15-b461-5270e118a58f`,
which is the design system folder name under `control-center/_ds/`. It is not an
Azure identifier.

### The one real exposure

Commit `8dedc37` contains the Azure resource group name in four places: two prose references in status documents and two JSON fields. That
commit is reachable from the public remote, so the name is publicly visible in
history. It is already redacted at HEAD.

### Assessment

A resource group name is not a secret. It grants no access, authenticates
nothing, and Azure resource naming is not treated as confidential by design. An
attacker holding it still needs valid credentials against a tenant they cannot
identify from this repository, because neither the tenant nor the subscription
appears anywhere in history.

The one genuine consideration is that the name embeds a fragment of the account
owner's username, which links the public repository to a personal account naming
convention. The account email itself is not exposed.

### Recommendation

**No history rewrite is required.** A rewrite means force-pushing a rewritten
history to a public repository, which breaks every existing clone and fork,
invalidates existing commit references, and is itself a risky operation. That
cost is not justified by a resource group name.

Rewrite only if you specifically object to the username fragment being
associated with the repository. If you decide to, the safe sequence is a fresh
repository rather than a force-push over the existing one, and it is your call to
make, not something to do automatically.

## What is not yet in the repository

These are gaps in the submission, not safety problems:

- No Foundry portal screenshots captured
- No Control Center screenshots captured
- No narration audio recorded
- The video remains a silent draft with placeholder slides

## Files currently uncommitted

Modified, all from this and the previous validation pass:

`README.md`, `gridresolve_synthetic_pack.json`,
`submission/video/build_video.py`, `submission/video/FINAL_VIDEO_SCRIPT.md`,
`submission/video/FINAL_VIDEO_SUBTITLES.srt`, and eleven files under
`control-center/src/`.

New and untracked:

`scripts/derive_ui_fixtures.py`, `tests/validate_synthetic_data.py`,
`control-center/src/engine/offlineResponder.test.ts`,
`control-center/src/data/fixtures/PROVENANCE.md`, `control-center/src/ds.css`,
`evidence/CAPTURE_CHECKLIST.md`, `docs/FINAL_CHANGE_AUDIT.md`,
`docs/FINAL_VALIDATION_REPORT.md`,
`docs/JUDGE_WALKTHROUGH_SYN-CASE-4003.md`, `docs/PUBLICATION_READINESS.md`,
plus the supplied design system bundle under `control-center/_ds/` and its
companion files.

All are safe to publish. Three zero-byte junk files created by shell redirects
during these sessions were found, verified empty, and removed. No project data
was deleted at any point.
