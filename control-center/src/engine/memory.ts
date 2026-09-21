/**
 * LOCAL SYNTHETIC CASE MEMORY.
 *
 * Browser-local storage of synthetic case conversations. This is not Foundry
 * Memory, no managed memory store is provisioned, and no embedding model is called.
 * Records are keyed per case so one case can never read another's conversation.
 */
export interface StoredTurn {
  readonly role: "customer" | "system" | "notice";
  readonly text: string;
  readonly at: string;
}

export interface CaseMemory {
  readonly case_id: string;
  readonly conversation_history: readonly StoredTurn[];
  readonly investigation_status: string;
  readonly evidence_ids: readonly string[];
  readonly policy_ids: readonly string[];
  readonly last_safe_response: string;
  readonly human_escalation_status: string;
  readonly updated_at: string;
}

const PREFIX = "gridresolve.case.v1.";
const CASE_ID = /^SYN-CASE-\d{4}$/;
export const RETENTION_NOTE =
  "Synthetic conversation data is held in this browser only, is never transmitted, and is cleared by Reset or by clearing site data.";

/** Minimal storage interface so tests can supply an in-memory double. */
export interface KeyValueStore {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
  key(index: number): string | null;
  readonly length: number;
}

const memoryFallback = (): KeyValueStore => {
  const map = new Map<string, string>();
  return {
    getItem: (k) => map.get(k) ?? null,
    setItem: (k, v) => void map.set(k, v),
    removeItem: (k) => void map.delete(k),
    key: (i) => [...map.keys()][i] ?? null,
    get length() {
      return map.size;
    },
  };
};

const defaultStore = (): KeyValueStore => {
  try {
    if (typeof localStorage !== "undefined") {
      localStorage.setItem(PREFIX + "__probe", "1");
      localStorage.removeItem(PREFIX + "__probe");
      return localStorage;
    }
  } catch {
    // private browsing or blocked storage, fall back to memory
  }
  return memoryFallback();
};

export class CaseMemoryStore {
  private readonly store: KeyValueStore;

  constructor(store: KeyValueStore = defaultStore()) {
    this.store = store;
  }

  private keyFor(caseId: string): string {
    if (!CASE_ID.test(caseId)) {
      throw new Error(`refusing to use a non synthetic case id: ${caseId}`);
    }
    return PREFIX + caseId;
  }

  load(caseId: string): CaseMemory | null {
    const raw = this.store.getItem(this.keyFor(caseId));
    if (!raw) return null;
    try {
      const parsed = JSON.parse(raw) as CaseMemory;
      // Isolation guard: a record that does not match its own key is discarded.
      return parsed.case_id === caseId ? parsed : null;
    } catch {
      return null;
    }
  }

  save(memory: CaseMemory): CaseMemory {
    const record: CaseMemory = { ...memory, updated_at: new Date().toISOString() };
    this.store.setItem(this.keyFor(record.case_id), JSON.stringify(record));
    return record;
  }

  reset(caseId: string): void {
    this.store.removeItem(this.keyFor(caseId));
  }

  /** Case ids currently held. Used by the UI to show what is stored. */
  storedCases(): readonly string[] {
    const out: string[] = [];
    for (let i = 0; i < this.store.length; i += 1) {
      const k = this.store.key(i);
      if (k?.startsWith(PREFIX)) out.push(k.slice(PREFIX.length));
    }
    return out.filter((c) => CASE_ID.test(c)).sort();
  }

  clearAll(): void {
    for (const c of this.storedCases()) this.reset(c);
  }
}

export const emptyMemory = (caseId: string): CaseMemory => ({
  case_id: caseId,
  conversation_history: [],
  investigation_status: "INTAKE",
  evidence_ids: [],
  policy_ids: [],
  last_safe_response: "",
  human_escalation_status: "NOT_REQUIRED",
  updated_at: new Date().toISOString(),
});
