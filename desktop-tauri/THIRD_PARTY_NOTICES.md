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
