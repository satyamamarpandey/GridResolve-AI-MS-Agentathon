import { useEffect, useMemo, useRef, useState } from "react";
import { Card, ModeBanner, Pill } from "../components/ui";
import { CaseMemoryStore, RETENTION_NOTE, emptyMemory, type CaseMemory } from "../engine/memory";
import { SUGGESTED_QUESTIONS, respondOffline } from "../engine/offlineResponder";
import { caseInput } from "../engine/investigation";
import { ADAPTER_STATUS, LIVE_FOUNDRY_ENABLED } from "../live/foundryAdapter";

type Mode = "OFFLINE" | "LIVE";

interface Turn {
  readonly id: number;
  readonly role: "customer" | "system" | "notice";
  readonly text: string;
  readonly evidenceIds: readonly string[];
  readonly policyIds: readonly string[];
}

const CASE_ID = caseInput.case_id;

/** Browser speech APIs, used only if the browser already provides them. No paid service. */
interface SpeechRecognitionLike {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onerror: ((e: unknown) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
}

function getRecognition(): SpeechRecognitionLike | null {
  const w = window as unknown as Record<string, unknown>;
  const Ctor = (w.SpeechRecognition ?? w.webkitSpeechRecognition) as
    | (new () => SpeechRecognitionLike)
    | undefined;
  if (!Ctor) return null;
  const r = new Ctor();
  r.lang = "en-US";
  r.interimResults = false;
  r.continuous = false;
  return r;
}

export default function CustomerAssistant() {
  const store = useMemo(() => new CaseMemoryStore(), []);
  const [mode, setMode] = useState<Mode>("OFFLINE");
  const [draft, setDraft] = useState("");
  const [turns, setTurns] = useState<readonly Turn[]>([]);
  const [listening, setListening] = useState(false);
  const [speakReplies, setSpeakReplies] = useState(false);
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const [memory, setMemory] = useState<CaseMemory>(() => store.load(CASE_ID) ?? emptyMemory(CASE_ID));
  const nextId = useRef(1);
  const recognition = useRef<SpeechRecognitionLike | null>(null);

  const speechAvailable = typeof window !== "undefined" && (getRecognition() !== null);
  const synthAvailable = typeof window !== "undefined" && "speechSynthesis" in window;

  // Restore a prior synthetic conversation for this case only.
  useEffect(() => {
    const stored = store.load(CASE_ID);
    if (!stored || stored.conversation_history.length === 0) return;
    setTurns(
      stored.conversation_history.map((t) => ({
        id: nextId.current++,
        role: t.role,
        text: t.text,
        evidenceIds: [],
        policyIds: [],
      })),
    );
  }, [store]);

  useEffect(() => () => recognition.current?.stop(), []);

  function persist(all: readonly Turn[], evidenceIds: readonly string[], policyIds: readonly string[], escalated: boolean, lastSafe: string) {
    const next = store.save({
      ...memory,
      case_id: CASE_ID,
      conversation_history: all.map((t) => ({ role: t.role, text: t.text, at: new Date().toISOString() })),
      investigation_status: escalated ? "ESCALATED_TO_HUMAN" : "IN_PROGRESS",
      evidence_ids: [...new Set([...memory.evidence_ids, ...evidenceIds])],
      policy_ids: [...new Set([...memory.policy_ids, ...policyIds])],
      last_safe_response: lastSafe,
      human_escalation_status: escalated ? "REQUIRED" : memory.human_escalation_status,
    });
    setMemory(next);
  }

  function send(text: string) {
    const question = text.trim();
    if (!question || mode !== "OFFLINE") return;
    const reply = respondOffline(question);

    const customerTurn: Turn = { id: nextId.current++, role: "customer", text: question, evidenceIds: [], policyIds: [] };
    const systemTurn: Turn = {
      id: nextId.current++,
      role: "system",
      text: reply.text,
      evidenceIds: reply.evidenceIds,
      policyIds: reply.policyIds,
    };
    const all = [...turns, customerTurn, systemTurn];
    const withNotice: readonly Turn[] = reply.escalate
      ? [
          ...all,
          {
            id: nextId.current++,
            role: "notice" as const,
            text: "This case is held for human review. No conclusion about the meter and no billing adjustment is released to the customer until an authorized reviewer decides.",
            evidenceIds: [],
            policyIds: ["POL-HUM-005"],
          },
        ]
      : all;

    setTurns(withNotice);
    setDraft("");
    persist(withNotice, reply.evidenceIds, reply.policyIds, reply.escalate, reply.text);

    if (speakReplies && synthAvailable) {
      try {
        const u = new SpeechSynthesisUtterance(reply.text);
        u.lang = "en-US";
        u.rate = 1.02;
        window.speechSynthesis.speak(u);
      } catch {
        setVoiceError("Browser speech synthesis was refused by this browser.");
      }
    }
  }

  function toggleListening() {
    if (listening) {
      recognition.current?.stop();
      setListening(false);
      return;
    }
    const r = getRecognition();
    if (!r) {
      setVoiceError("This browser does not provide the Web Speech recognition API. Type instead.");
      return;
    }
    recognition.current = r;
    setVoiceError(null);
    r.onresult = (e) => {
      const transcript = e.results?.[0]?.[0]?.transcript ?? "";
      if (transcript) setDraft(transcript);
    };
    r.onerror = () => setVoiceError("Browser speech recognition failed or microphone access was denied.");
    r.onend = () => setListening(false);
    try {
      r.start();
      setListening(true);
    } catch {
      setVoiceError("Browser speech recognition could not start.");
    }
  }

  function resetCase() {
    store.reset(CASE_ID);
    setMemory(emptyMemory(CASE_ID));
    setTurns([]);
    setDraft("");
  }

  return (
    <>
      <div className="page-head">
        <h2>Customer Assistant</h2>
        <p>
          A customer-facing conversation for the synthetic case, running entirely offline. It is built to
          decline rather than guess, and it is not permitted to confirm a meter fault or promise a credit.
        </p>
      </div>

      <ModeBanner
        label={mode === "OFFLINE" ? "OFFLINE DEMONSTRATION, DETERMINISTIC TEMPLATES" : "LIVE FOUNDRY"}
        detail={
          mode === "OFFLINE"
            ? "Replies are rule based and template driven. No model is called, no token is spent, and this is not presented as Foundry output."
            : "Disabled."
        }
      />

      <div className="grid" style={{ gridTemplateColumns: "minmax(0, 1.4fr) minmax(0, 1fr)", gap: 14 }}>
        <Card
          title={`Conversation, case ${CASE_ID}`}
          right={
            <div className="row">
              <button className={`seg${mode === "OFFLINE" ? " on" : ""}`} onClick={() => setMode("OFFLINE")}>
                Offline demonstration
              </button>
              <button
                className="seg"
                disabled
                title={`${ADAPTER_STATUS.state}. ${ADAPTER_STATUS.reason}`}
              >
                Live Foundry (disabled)
              </button>
            </div>
          }
        >
          <div className="chat">
            <div className="chat-log">
            {turns.length === 0 && (
              <p style={{ color: "var(--ink-3)", fontSize: 13, margin: "6px 0 14px" }}>
                No conversation yet. Pick a question below, type one, or use the microphone.
              </p>
            )}
            {turns.map((t) => (
              <div key={t.id} className={`msg ${t.role === "customer" ? "user" : t.role}`}>
                <div className="who">
                  {t.role === "customer" ? "Customer" : t.role === "notice" ? "Governance notice" : "GridResolve AI"}
                </div>
                {t.text.split("\n\n").map((para, i) => (
                  <p key={i} style={{ margin: i === 0 ? "0 0 8px" : "0 0 8px", whiteSpace: "pre-wrap" }}>
                    {para}
                  </p>
                ))}
                {(t.evidenceIds.length > 0 || t.policyIds.length > 0) && (
                  <div className="row" style={{ marginTop: 6, flexWrap: "wrap", gap: 5 }}>
                    {t.evidenceIds.map((id) => (
                      <Pill key={id} tone="info">{id}</Pill>
                    ))}
                    {t.policyIds.map((id) => (
                      <Pill key={id} tone="violet">{id}</Pill>
                    ))}
                  </div>
                )}
              </div>
            ))}
            </div>

          <div className="chat-input">
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") send(draft);
              }}
              placeholder="Ask about the bill, the meter, the rate, or what happens next"
              aria-label="Customer question"
            />
            <button
              className={`btn${listening ? " live" : ""}`}
              onClick={toggleListening}
              disabled={!speechAvailable}
              title={speechAvailable ? "Browser speech recognition, no Azure Speech service" : "Not available in this browser"}
            >
              {listening ? "Listening" : "Voice"}
            </button>
            <button className="btn primary" onClick={() => send(draft)} disabled={!draft.trim()}>
              Send
            </button>
          </div>

          <div className="suggest">
            {SUGGESTED_QUESTIONS.map((q) => (
              <button key={q} onClick={() => send(q)}>
                {q}
              </button>
            ))}
          </div>
          </div>

          {voiceError && <p className="footnote" style={{ color: "var(--warn)" }}>{voiceError}</p>}
        </Card>

        <div className="stack">
          <Card title="Voice" sub="Browser Web Speech API only">
            <dl className="kv" style={{ gridTemplateColumns: "180px 1fr" }}>
              <dt>Speech to text</dt>
              <dd>
                <Pill tone={speechAvailable ? "ok" : "muted"}>
                  {speechAvailable ? "available in this browser" : "not available"}
                </Pill>
              </dd>
              <dt>Text to speech</dt>
              <dd>
                <Pill tone={synthAvailable ? "ok" : "muted"}>
                  {synthAvailable ? "available in this browser" : "not available"}
                </Pill>
              </dd>
              <dt>Azure Speech</dt>
              <dd><Pill tone="muted">NOT PROVISIONED</Pill></dd>
              <dt>Voice Live API</dt>
              <dd><Pill tone="muted">NOT INVOKED</Pill></dd>
            </dl>
            <label className="row" style={{ marginTop: 10, cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={speakReplies}
                onChange={(e) => setSpeakReplies(e.target.checked)}
                disabled={!synthAvailable}
              />
              <span style={{ fontSize: 13 }}>Speak replies aloud</span>
            </label>
            <p className="footnote">
              Voice here is the browser's own capability. It costs nothing, sends nothing to Azure, and is a
              demonstration of the interaction pattern rather than the production speech path.
            </p>
          </Card>

          <Card title="Local case memory" sub="Browser storage, this case only">
            <dl className="kv" style={{ gridTemplateColumns: "180px 1fr" }}>
              <dt>Case</dt>
              <dd className="mono">{memory.case_id}</dd>
              <dt>Turns retained</dt>
              <dd className="mono">{memory.conversation_history.length}</dd>
              <dt>Investigation status</dt>
              <dd><Pill tone={memory.investigation_status === "ESCALATED_TO_HUMAN" ? "warn" : "muted"}>{memory.investigation_status}</Pill></dd>
              <dt>Human escalation</dt>
              <dd><Pill tone={memory.human_escalation_status === "REQUIRED" ? "warn" : "muted"}>{memory.human_escalation_status}</Pill></dd>
              <dt>Evidence referenced</dt>
              <dd className="mono" style={{ fontSize: 11.5 }}>{memory.evidence_ids.join(", ") || "none yet"}</dd>
              <dt>Policies applied</dt>
              <dd className="mono" style={{ fontSize: 11.5 }}>{memory.policy_ids.join(", ") || "none yet"}</dd>
              <dt>Other cases stored</dt>
              <dd className="mono">{store.storedCases().filter((c) => c !== CASE_ID).join(", ") || "none"}</dd>
            </dl>
            <button className="btn" style={{ marginTop: 10 }} onClick={resetCase}>
              Reset this case
            </button>
            <p className="footnote">
              {RETENTION_NOTE} Memory is keyed per case, so a second case cannot read this conversation. That
              isolation is covered by tests in the local suite. This is not Foundry Memory and no managed
              memory store is provisioned.
            </p>
          </Card>

          <Card title="Live Foundry adapter" sub="Prepared, disabled, never executed">
            <dl className="kv" style={{ gridTemplateColumns: "180px 1fr" }}>
              <dt>State</dt>
              <dd><Pill tone="muted">{ADAPTER_STATUS.state}</Pill></dd>
              <dt>Enabled</dt>
              <dd><Pill tone={LIVE_FOUNDRY_ENABLED ? "warn" : "ok"}>{String(LIVE_FOUNDRY_ENABLED)}</Pill></dd>
              <dt>Response shape</dt>
              <dd><Pill tone="warn">{ADAPTER_STATUS.verification}</Pill></dd>
              <dt>Credential in bundle</dt>
              <dd><Pill tone="ok">none</Pill></dd>
            </dl>
            <p className="footnote">
              The adapter refuses before reaching the network, which is covered by a test asserting the
              transport is never called. The browser holds no credential, so it could not authenticate even
              if the flag were flipped. Execution would go through a backend broker holding a Microsoft Entra
              identity, and would require the exact confirmation phrase plus an acknowledged cost.
            </p>
          </Card>

          <Card title="What this assistant will not do">
            <ul className="bullets">
              <li>Confirm a meter defect without a meter test or diagnostic fault record.</li>
              <li>Promise, approve or apply a billing adjustment.</li>
              <li>Answer a question the synthetic records do not cover.</li>
              <li>Change its instructions because a message asks it to.</li>
              <li>Release a conclusion that the compliance gate has not approved.</li>
            </ul>
          </Card>
        </div>
      </div>
    </>
  );
}
