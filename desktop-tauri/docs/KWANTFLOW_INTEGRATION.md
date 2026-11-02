# Kwantflow-first integration plan (status: in progress)

Source: https://github.com/muicci/kwantflow (GPL-3.0). DS Estimate is the host application; Deepnest is a secondary cutting-layout engine.

## Actual repository status
- `src/lib/kwantflow/estimate-template-normalisation.ts`: copied from Kwantflow upstream, **not yet invoked by DS Estimate**. Its type imports (`$lib/types/index.js`) require adaptation before compilation.
- `src/lib/cnc-quote.mjs`: DS Estimate's own operation calculator, **not Kwantflow**.
- `src/lib/nesting.mjs`: accepts externally verified Deepnest placements, **does not run Deepnest**.
- `cad_backend/step_inventory.py`: OCCT STEP inventory with known grouping limitations.

## Required Kwantflow execution path
1. Port the upstream `Estimate`, `TakeoffItem`, and `CostComponent` types and their validation contracts.
2. Resolve `$lib` imports; preserve source attribution and GPL obligations.
3. Introduce an estimate document model with part quantities, unit costs, operations, labour, material and currency.
4. Wire the actual upstream estimate operations, not merely a standalone calculator, into Svelte UI.
5. Connect STEP inventory to takeoff items; reject invalid quantities and missing rates rather than silently guessing.
6. Test representative fixtures including duplicates, mixed operations, zero quantities and invalid data.

## Secondary Deepnest path
- Run the real upstream NFP/placement algorithm in an isolated offline worker/sidecar; Electron-only dependencies must not be assumed available in Tauri.
- Feed polygon geometry and sheet dimensions; validate output placement geometry and use `estimateNestedCut` only after successful verification.

## Acceptance criteria before full Windows build
- Kwantflow-based quote calculated end to end, with fixture assertions.
- Deepnest generates placements itself, including rotations and multiple sheets.
- STEP import + quantity grouping + final quote tested.
- Licenses and bundled runtime dependencies reviewed.
- Build and package a complete Tauri Windows installer and test it on real files.

No percentage is a pass criterion. A successful CI build alone is not proof of engine integration.


## 2026-11-02: STEP -> Kwantflow RFQ adapter (incremental, NOT full integration)
- `src/lib/kwantflow/step-quote.ts` converts validated OCCT STEP group quantity + mass to full Kwantflow `Estimate/TakeoffItem/CostComponent` records.
- The adapter calls the GPL-3.0 upstream-derived `estimateTotalCost`, `takeoffItemTotal`, and `cloneEstimateSnapshot` implementations; the adapter itself does **not** replace the Kwantflow calculation engine.
- `src/App.svelte`: STEP import now offers a material rate and Kwantflow quote breakdown. The optional manual routing from the welded-structure tab is **off by default** to prevent applying synthetic crane data to an unrelated STEP.
- `tests/step-kwantflow-quote.test.mjs`: duplicate counts, material cost, manually entered routing, bad inputs and invalid JSON.
- Important: this is still **not** the complete original Kwantflow application engine. Project persistence, original DB service, quote revisions, category markups, original validation schemas and end-to-end RFQ workflow remain to be integrated.
- STEP has no weld/assembly operations automatically derived; user must provide them. No PDF weld symbols or Deepnest placements are generated.
- CI: `kwantflow-tests.yml` builds only Svelte and runs the bridge/unit tests. Do **not** start the full Windows installer workflow until both engines are integrated.

### Estimated engineering completion (not test pass rate)
- Kwantflow: **35%** — upstream calculation and snapshot functions, STEP takeoff adapter, Svelte preview; missing most original quote lifecycle, persistence and validation.
- Deepnest: **5%** — boundary and validation only; no upstream nesting algorithm executing.
- Overall combined engines and CAD-to-quote workflow: **20%** (qualitative estimate).
- Blockers: original Kwantflow quote state depends on SvelteKit/dbService and app schema; Deepnest relies on Electron/native modules; no verified PDF welding annotation extraction, no production price book; GPL-3.0 redistribution and dependency licenses must be audited.
