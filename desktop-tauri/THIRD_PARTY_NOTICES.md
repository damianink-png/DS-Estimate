# DS Estimate desktop-tauri — upstream attribution and license notice

## Kwantflow (GPL-3.0)
Original project: https://github.com/muicci/kwantflow
Original license: GNU General Public License version 3.0.
Full license text: [COPYING](./COPYING).

The following files include code extracted/adapted from Kwantflow, with
upstream paths indicated in their headers:
- `src/lib/kwantflow/estimate-calculation.ts` — arithmetic functions from `src/lib/state/quote.svelte.ts`.
- `src/lib/kwantflow/estimate-snapshot.ts` — adapted from `src/lib/utils/estimate-snapshot.ts`.
- `src/lib/kwantflow/estimate-template-normalisation.ts` — adapted from upstream estimate template normalization.
- `src/lib/kwantflow/types.ts` — local subset/compatibility types extracted from upstream.

`src/lib/kwantflow/step-quote.ts` is a DS Estimate adapter, not upstream code.
The host application's use of GPL-covered modules requires GPL compliance
for any covered distribution; do not assume that simply including a notice
settles every source, dependency or binary distribution obligation.

## Deepnest (not integrated)
Upstream: https://github.com/deepnest-next/deepnest
No actual Deepnest placement engine is bundled or running in this project.
Review upstream and transitive dependency licenses before integration.

## DS Compare 0.6.4 interface patterns

The DS Estimate 0.3 desktop workspace adapts the dark/light palette, navigation,
native multi-file picker, drop-event lifetime handling, and window work-area sizing
from the user's DS Compare project: `damianink-png/test`, branch
`build/dscompare-0.6.4-20261105`, commit
`1cae4bc` (`portable/frontend/style.css`, `api.ts`, `main.rs`).
Comparison, registration, WebGL previews and DS Compare's launcher are not presented
as estimation engines. The existing pythonocc-core/OCCT estimator remains the single
CAD backend, and the existing Kwantflow costing adapter remains in use.

Lucide icons: lucide-svelte 0.468.0, ISC license (upstream lucide-icons/lucide).

## Steel Section Database — included data in DS Estimate 0.4

Copyright (c) 2026 Adam Koudelka. MIT License; full text is distributed as
`licenses/steel-section-database-MIT.txt`.
Source: https://github.com/ulmewix/Steel_Section_Database
Pinned commit: 524172a3fff6a2c4da03f56a577402aa3a88876a.
1792 primary section records and computed section areas were converted to
`src/lib/data/steel-sections.json` by `scripts/import-section-catalog.py`.
Designation/geometry matching is DS Estimate code and is not a certification of
the product standard, delivery process, steel grade or catalogue availability.

## Reviewed, not distributed

RoboWeldAR weld seam proposal (Apache-2.0), FreeCAD SheetMetal (LGPL-2.1-or-later),
FreeCAD CAM (LGPL-2.1-or-later), and Deepnest (MIT) were reviewed as documented in
`docs/OPEN_SOURCE_MODULE_AUDIT.md`. No weights, CUDA pipeline, full FreeCAD runtime,
or Deepnest Electron engine are included. New geometric contact detection and
analytic shop-time estimators are independent DS Estimate implementations.
