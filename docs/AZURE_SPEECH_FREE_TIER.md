# Azure Speech Free Tier (F0) Investigation

Date: 2026-09-19
Status: RESEARCH ONLY. No Azure Speech resource was created. Voice Live was not invoked.
Purpose: determine whether Azure Speech could power the GridResolve AI voice interface
at zero cost, and record why the browser Web Speech API was used instead.

Sources are Microsoft first-party pages, retrieved 2026-09-19:

- Pricing: https://azure.microsoft.com/en-us/pricing/details/speech/
- Quotas and limits: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-services-quotas-and-limits
  (page metadata shows `ms.date: 2026-09-09`, so it is current)

## 1. Free tier monthly allowances

| Capability | Free (F0) allowance |
| --- | --- |
| Real-time speech to text | 5 audio hours per month |
| Custom speech to text | Shares the same 5 audio hours |
| Speech translation | 5 audio hours per month |
| Neural text to speech | 0.5 million characters per month |
| Batch transcription | Not available on F0 |
| Batch synthesis | Not available on F0 |
| Text-to-speech avatar, batch and real time | Not available on F0 |

The pricing page states directly that free audio hours for speech to text are
shared between Standard and Custom, and that Batch is not supported on the free
tier.

## 2. F0 throughput limits

These are the limits that actually decide feasibility. All are documented as not
adjustable for F0.

| Quota | Free (F0) | Standard (S0) |
| --- | --- | --- |
| Concurrent real-time speech-to-text requests, base model | 1 | 100, adjustable |
| Concurrent real-time speech-to-text requests, custom endpoint | 1 | 100, adjustable |
| Text-to-speech transactions | 20 per 60 seconds | 30 per second, adjustable to 1,000 |
| Maximum audio produced per TTS request | 10 minutes | 10 minutes |
| Distinct voice and audio tags per SSML | 50 | 50 |
| SSML message size per turn, WebSocket | 64 KB | 64 KB |
| Custom model deployments per resource | 1 | 50 |
| Speech datasets | 2 | 500 |

The quotas page states plainly: "The quotas and limits for Free (F0) Azure Speech
resources aren't adjustable."

A concurrency limit of exactly 1 for real-time speech to text is the decisive
number. A single F0 resource can serve one live conversation at a time. That is
fine for a demonstration and unusable for a contact center, which is the actual
production context for GridResolve AI.

## 3. Voice Live on F0

Voice Live is listed with F0 marked **Not applicable** on every quota:

| Quota | Free (F0) | Standard (S0) |
| --- | --- | --- |
| New connections per minute | Not applicable | 30 |
| Maximum connection length | Not applicable | 60 minutes per session |
| Tokens per minute | Not applicable | 120,000 (formula: NCPM x 4,000) |

Conclusion: **Voice Live requires a Standard (S0) resource.** There is no free
path to Voice Live. This alone rules it out under the zero-spend constraint, and
it was not invoked.

## 4. Overage behavior

This matters more than the allowance, because the risk is a surprise charge.

Microsoft support guidance on Microsoft Q&A states that exceeding the F0 monthly
quota does not automatically start billing. The service throttles or rejects
further requests, typically returning HTTP 429, until the monthly cycle resets.
Moving to paid usage requires manually changing the resource to S0.

Confidence note: this is a Microsoft Q&A answer from Microsoft staff, not a
contractual pricing statement. It is consistent with how F0 tiers behave across
Foundry Tools, but it was treated as strong guidance rather than as a guarantee.
Under the project rule "when cost behavior is uncertain, skip the action", the
resource was not created regardless, so the question never became load bearing.

A separate note on HTTP 429: the quotas page warns that most 429 errors on
text-to-speech standard voices come from backend capacity for a specific voice in
a region, not from quota. So a 429 cannot be read as proof of quota exhaustion.

## 5. Resource creation requirements

Creating an F0 Speech resource requires:

- An Azure subscription.
- A resource group.
- A region selection. Not every capability exists in every region, and the
  guidance recommends using a voice in its native region for reliability.
- Accepting a resource that issues keys and an endpoint.

Two constraints that were not confirmed from a first-party quota table and are
therefore recorded as unverified:

- The number of F0 Speech resources permitted per subscription per region. The
  community signal is one, and Microsoft Q&A threads exist about being unable to
  recreate an F0 resource after deleting one, but no authoritative table was
  found. UNVERIFIED.
- Regional availability of the F0 tier specifically, as opposed to the service.
  UNVERIFIED.

Neither was chased further, because the resource was not going to be created.

## 6. Why this matters for credential handling

An Azure Speech resource issues a subscription key. The browser-side pattern that
Microsoft samples commonly show puts either that key or a short-lived token into
client JavaScript.

For GridResolve AI that is prohibited outright. The project rule is: never place
Azure credentials in browser JavaScript, never expose access tokens, never use a
hardcoded API key, prefer Microsoft Entra authentication through a backend.

Using Azure Speech from the Control Center would therefore require a backend
token broker before a single word could be transcribed. That is real work, it
needs a hosting resource, and the hosting resource costs money. The dependency
chain is the point: a free speech tier does not make a free speech feature.

## 7. Decision

**Azure Speech was not provisioned. The browser Web Speech API was used instead.**

| Factor | Azure Speech F0 | Browser Web Speech API |
| --- | --- | --- |
| Cost | Free within allowance, with a paid dependency chain | Free |
| Resource to create | Yes | No |
| Credential handling | Requires a backend token broker | None, no credential exists |
| Concurrency | 1 real-time STT stream | Per browser, not a shared quota |
| Setup time | Hours, including the broker | Already working |
| Production honesty | Would look like production without being it | Clearly labelled as a browser capability |

The last row decided it. Wiring F0 Speech into a demonstration would let the
submission imply a production speech path that does not exist. The browser API
demonstrates the same interaction contract and is labelled as exactly what it is.

## 8. What is implemented in the Control Center

Implemented in `control-center/src/views/CustomerAssistant.tsx`:

- Speech to text through `SpeechRecognition` or `webkitSpeechRecognition`, feature
  detected at runtime. The microphone button is disabled when the API is absent.
- Text to speech through `window.speechSynthesis`, behind an opt-in checkbox that
  is disabled when the API is absent.
- Text entry is always available and is the primary path. Voice is an enhancement,
  never a requirement, so the view is fully usable with no speech support at all.
- Failures are surfaced as readable messages rather than swallowed: no recognition
  API, microphone permission denied, recognition failed to start, synthesis
  refused.
- A status panel states plainly that Azure Speech is NOT PROVISIONED and Voice
  Live is NOT INVOKED, so a viewer cannot mistake the demonstration for a
  service integration.

No separate voice agent was created. A voice agent would have no independently
testable responsibility here: it would only move audio in and out of the same
deterministic responder, so it would add a component without adding a behavior
worth testing.

## 9. Browser speech recognition privacy

This is a genuine limitation and is recorded rather than glossed.

Chrome and Edge implementations of `SpeechRecognition` send captured audio to a
cloud service operated by the browser vendor for transcription. The Web Speech
API specification does not require on-device processing, and the browser does not
promise it. Practical consequences:

- Audio spoken into the demonstration may leave the machine, handled by the
  browser vendor rather than by this application or by Azure.
- The application never receives, stores or transmits the audio itself. It
  receives only the resulting transcript string, which stays in browser memory
  and in the per-case local memory record.
- The microphone requires explicit user permission, per request in most browsers.
- Because only synthetic utility case dialogue is spoken, no real customer data
  can be exposed by this path.

For a production deployment this is not acceptable for customer calls, and the
production target is a backend-mediated speech service rather than browser
recognition. That is stated in the production roadmap rather than implied away.

## 10. If Azure Speech were adopted later

Sequence, for the record, not performed:

1. Stand up a backend token broker that exchanges a Microsoft Entra identity for
   a short-lived Speech token. No key ever reaches the browser.
2. Create the Speech resource in a region where the chosen neural voice is native.
3. Start on F0 for functional validation only, accepting concurrency of 1.
4. Move to S0 before any multi-user testing, because F0 concurrency of 1 makes
   concurrent testing meaningless.
5. Budget against $15 per million characters for text to speech, the unit price
   used in Microsoft's own quota estimation example.
6. Implement 429 retry with backoff, which the quotas page calls out as a
   best practice every implementation should have.

Execution status: PREPARED_NOT_EXECUTED_DUE_TO_ZERO_COST_CONSTRAINT.
