# DS Estimate — welded assemblies and weld-length validation plan

Status: TEST PLAN ONLY. No automatic PDF weld-symbol recognition or weld-length detection is claimed to be implemented.

## Source A — WeldProjects MAGN-000-002
PDF: https://weldprojects.com/wp-content/uploads/2025/04/MAGN-000-002_A-1-Booklet.pdf
- Preserve source PDF as CI fixture only if license permits; otherwise download at run time with explicit checksum and provenance.
- Manually transcribe BOM, weld annotations, view/section identifiers, quantities and dimensions into an independently reviewed ground-truth CSV/JSON.
- Verify inches to mm: 1.5 in = 38.1 mm, 0.25 in = 6.35 mm. **These are individual callout dimensions, not the total weld length.**
- For each weld callout: process, joint ID, a/z leg/throat interpretation, length, pitch, number of repetitions, all-around, both-sides, intermittent and reference drawing page.
- Sum total weld length as sum(segment length × count × occurrence × side factor), after deduplication of callouts referring to the same physical joint.
- Check 15 fabricated parts + 4 pins against the source BOM before treating those quantities as ground truth.
- Independent quote baseline is preliminary 1494 PLN net, not a verified supplier quotation; keep material, cutting, drilling, fit-up, MAG welding, finishing and markup as separate entries.

## Source B — CADXchange welded support
Reference: https://cadxchange.net/resources/samples/welded-structure-drawing
- First confirm the source is downloadable and licenses allow use. Require original DWG/PDF and any STEP, not screenshots.
- Manually label every weld symbol, throat/leg size, sides, all-around and joint length, and make a ground-truth table.
- If DWG is unavailable, mark source BLOCKED and never fabricate a result.

## Test cases / acceptance gates
1. Source provenance and accessible PDF/DWG/STEP; fail closed if unavailable.
2. BOM parts and quantity, material, geometry units, mass: compare against manual drawing takeoff.
3. Weld-symbol detection: recall and precision per callout; no silently omitted or invented welds.
4. ISO 2553 semantics: a vs z, arrow vs other side, both sides, continuous vs intermittent, all-around; manual review required for ambiguity.
5. Weld length in mm per unique joint and summed total, with expected values independently transcribed from drawings; tolerance max(1 mm, 1%) per joint for fully dimensioned joints.
6. Weld volume and mass: fillet idealized throat a -> section a², leg z -> section z²/2, times length; document modeling assumptions and exclude double counting.
7. Welding time: process MAG 135, effective deposition rate and setup/positioning separated; compare to a documented shop-rate scenario, not an invented vendor quote.
8. Cost report: compare independent estimate by material/cutting/drilling/fit-up/welding/finishing/markup; display differences per category and total.
9. Compiled Windows EXE test: execute actual packaged CAD engine on STEP, parse output, then invoke compiled Tauri app's actual import/quote path when implemented; JS arithmetic tests do NOT count.
10. Negative controls: unwelded touching faces, duplicated callouts, mixed units, missing PDF sheet, intermittent welds, both sides, all-around, rotated assembly and invalid STEP.
11. Report artifacts: source hash, ground-truth JSON, per-joint weld ledger CSV, result JSON, screenshots/logs, Windows installer, PASS/FAIL/BLOCKED status for each gate.

## Current implementation boundary
Current compiled OCCT engine inventories STEP solids and mass only. It does not parse PDF weld symbols or calculate weld lengths. Until a real implementation exists, the weld-length and CAD-to-quote gates MUST be reported BLOCKED/NOT IMPLEMENTED, not PASS.
