/** Deepnest integration boundary: accepts placements from an actual nesting engine.
 * Never represents a rectangular heuristic as a Deepnest result.
 * All dimensions in millimeters; costs in PLN.
 */
const positive = (v, name) => { if (!Number.isFinite(v) || v <= 0) throw new RangeError(name); return v; };
export function estimateNestedCut(job, layout) {
  if (!layout || layout.engine !== 'deepnest' || layout.verified !== true)
    throw new Error('Brak zweryfikowanego wyniku silnika Deepnest');
  const { sheetWidthMm, sheetHeightMm, sheetCostPln, feedMmMin, pierceSeconds=0, ratePlnHour=388 } = job;
  const sheetArea = positive(sheetWidthMm,'sheetWidthMm') * positive(sheetHeightMm,'sheetHeightMm');
  positive(feedMmMin,'feedMmMin'); positive(ratePlnHour,'ratePlnHour');
  if (!Array.isArray(layout.placements) || !layout.placements.length) throw new Error('Brak rozmieszczeń');
  const sheets = new Set(); let area = 0, contour = 0, pierces = 0;
  for (const p of layout.placements) {
    if (!Number.isInteger(p.sheetIndex) || p.sheetIndex < 0) throw new RangeError('sheetIndex');
    sheets.add(p.sheetIndex);
    area += positive(p.areaMm2,'areaMm2');
    contour += positive(p.cutLengthMm,'cutLengthMm');
    if (!Number.isInteger(p.pierces) || p.pierces < 0) throw new RangeError('pierces');
    pierces += p.pierces;
  }
  if (area > sheets.size*sheetArea + 1e-6) throw new Error('Powierzchnia detali przekracza arkusze');
  const cuttingMinutes = contour / feedMmMin + pierces * pierceSeconds / 60;
  const materialCost = sheets.size * positive(sheetCostPln,'sheetCostPln');
  return { sheets: sheets.size, utilization: area/(sheets.size*sheetArea), contourMm: contour,
    pierces, cuttingMinutes, materialCost, machineCost: cuttingMinutes*ratePlnHour/60,
    totalCost: materialCost+cuttingMinutes*ratePlnHour/60 };
}
