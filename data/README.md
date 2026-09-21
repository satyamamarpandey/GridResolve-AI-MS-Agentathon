# GridResolve AI | Offline UI testing fixtures

These are **frontend-only synthetic UI snapshots for one existing case: SYN-CASE-4003**. They are not additional cases, new policies, production records, model outputs, Foundry run evidence, or new test executions.

The three case files conform to the saved `gridresolve_case_state.schema.json` (Draft 2020-12). Validation was performed offline with `jsonschema`; only the listed top-level fields appear. The required `workflow_version` is `GridResolveAIWorkflow-v4` because the saved uploaded schema requires that exact string. **If the current local control-center or workflow is v5, inspect its current TypeScript import shape/schema and version requirements before importing; do not silently relabel a v4 case state as v5.** This bundle cannot establish the current Vite app's importer type because the local repo was not provided.

## Files
- `SYN-CASE-4003_UI_01_INTAKE.json`: minimal case before local UI simulation.
- `SYN-CASE-4003_UI_02_INVESTIGATING.json`: illustrative synthetic billing/usage/meter evidence and existing policy IDs.
- `SYN-CASE-4003_UI_03_SIMULATED_REJECTION.json`: deliberately unsupported meter-failure claim, shown as a hypothetical failed compliance review and pending specialist review.
- `SYN-CASE-4003_UI_EXPECTATIONS.json`: assertions, **not** an agent input.
- `gridresolve_case_state.schema.json`: a local mirror of the uploaded v4 schema for offline validation.

## Important boundaries
- Do **not** overwrite the canonical `submission/SYN-CASE-4003_input.json`. Its contents should be sent to a workflow unmodified only after explicit run approval.
- Values such as $124/$197 and 720/1,015 kWh are **illustrative for UI testing**, not a claim that they match the current canonical input file.
- Do **not** send the expected outputs or mock compliance result to the model. Load snapshots only in the local UI mock path.
- The simulated rejection is **not evidence that the actual Foundry gate works**, or that a customer message was withheld. No cloud calls were made to prepare or validate this bundle.
- In the frontend, show `Synthetic • UI Simulation • Not Executed` in every mocked runtime pane.
- Inspect current `src` TypeScript types/mock-data imports first and adapt via a local mapper if needed. Do not change real workflow contracts to fit a visual fixture.
