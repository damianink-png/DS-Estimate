# DS Estimate — Kwantflow and Deepnest integration audit (2026-11-02)

## Verified upstream repositories
- Kwantflow: https://github.com/muicci/kwantflow ; package version 0.13.0; GPL-3.0 (repository LICENSE); SvelteKit / Tauri; local-first RFQ and estimating.
- Deepnest: https://github.com/deepnest-next/deepnest ; package version 1.5.6; MIT (repository LICENSE); Electron, native geometry modules, DXF conversion.

## Licensing gate
Do NOT copy Kwantflow GPL-3.0 implementation into DS Estimate or bundle it into a proprietary binary without resolving the GPL obligations. Study its data model and estimator features; implement independent interoperable data adapters where appropriate. If direct GPL code is used/distributed, review corresponding-source and derivative-work obligations first.
Deepnest MIT components may be reused subject to copyright/license notices and dependency-specific licenses (see upstream LICENSES).

## Architecture
1. CAD STEP import: packaged pythonocc-core executable; normalize assembly/part identity and material metadata.
2. CNC: add an independent adapter for Kwantflow-compatible RFQ/BOM and cost breakdown; use DS Estimate's own estimator until licensing and interfaces are resolved. Do not label this as running Kwantflow.
3. Nesting: run actual Deepnest engine in isolated Node/native worker (not its Electron UI), consume DXF polygons with holes, thickness/material, kerf, spacing and sheet sizes; output placements, sheet usage, cut lengths and piercings. The existing src/lib/nesting.mjs is only a strict cost adapter for verified output.
4. Windows distribution: package every required runtime and native module; smoke-test on clean Windows runner.
5. Test fixtures: irregular parts with holes, rotations, duplicates and multiple sheets; independently validate no overlaps, bounds, cut lengths, sheet counts, and cost; separate CNC costing fixtures.

## Acceptance criteria
- No manual installs or admin rights after NSIS installation.
- Import real STEP, extract accurate BOM, material/mass and detect duplicate rotated parts.
- Deepnest returns actual placement geometry and passes non-overlap and boundary tests; do not mark as integrated until verified.
- CNC produces per-operation cost and independently checked totals.
- Installer smoke test exercises STEP, CNC and nesting from packaged application.
