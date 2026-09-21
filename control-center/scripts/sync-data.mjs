// Copies canonical project data into src/data/generated so the app has a single
// source of truth. Never hand-edit the generated files.
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const ROOT = join(here, "..", "..");
const OUT = join(here, "..", "src", "data", "generated");
mkdirSync(OUT, { recursive: true });

const json = (p) => JSON.parse(readFileSync(join(ROOT, p), "utf8"));
const jsonl = (p) =>
  readFileSync(join(ROOT, p), "utf8")
    .split("\n")
    .filter((l) => l.trim())
    .map((l) => JSON.parse(l));

const write = (name, data) => {
  writeFileSync(join(OUT, name), JSON.stringify(data, null, 1));
  const n = Array.isArray(data) ? data.length : Object.keys(data).length;
  console.log(`  ${name.padEnd(26)} ${n} entries`);
};

console.log("syncing canonical data ->", OUT);
write("syntheticPack.json", json("gridresolve_synthetic_pack.json"));
write("caseInput.json", json("submission/SYN-CASE-4003_input.json"));
write("manifest.json", json("gridresolve_submission_manifest.json"));

const evals = jsonl("gridresolve_evaluation_suite.jsonl");
write("evaluationSuite.json", {
  meta: evals.find((r) => r._meta)?._meta ?? {},
  cases: evals.filter((r) => !r._meta),
});

const red = jsonl("gridresolve_red_team_pack.jsonl");
write("redTeamPack.json", {
  meta: red.find((r) => r._meta)?._meta ?? {},
  attacks: red.filter((r) => !r._meta),
});

// UI test fixtures. These are a SEPARATE path from the canonical data above.
// They carry workflow_version "GridResolveAIWorkflow-v4" and SYN- prefixed
// identifiers, and are deliberately NOT relabelled to match the canonical v5
// engine. They are display-only snapshots for local frontend testing.
const FIX = join(here, "..", "src", "data", "fixtures");
mkdirSync(FIX, { recursive: true });
const writeFixture = (name, data) => {
  writeFileSync(join(FIX, name), JSON.stringify(data, null, 1));
  console.log(`  fixtures/${name.padEnd(16)} ${Object.keys(data).length} keys`);
};

console.log("syncing UI test fixtures ->", FIX);
writeFixture("intake.json", json("data/SYN-CASE-4003_UI_01_INTAKE.json"));
writeFixture("investigating.json", json("data/SYN-CASE-4003_UI_02_INVESTIGATING.json"));
writeFixture("rejection.json", json("data/SYN-CASE-4003_UI_03_SIMULATED_REJECTION.json"));
writeFixture("expectations.json", json("data/SYN-CASE-4003_UI_EXPECTATIONS.json"));

console.log("done. generated files are build artifacts, do not edit by hand.");
