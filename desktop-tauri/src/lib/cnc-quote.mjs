/** CNC operation cost breakdown adapter for Kwantflow RFQ integration.
 * Standalone DS Estimate logic; not upstream Kwantflow execution.
 */
export function estimateCncOperations(operations, { hourlyRatePln = 388, setupRatePln = hourlyRatePln } = {}) {
  if (!Array.isArray(operations)) throw new TypeError('operations must be an array');
  const valid = n => typeof n === 'number' && Number.isFinite(n) && n >= 0;
  if (!valid(hourlyRatePln) || !valid(setupRatePln)) throw new RangeError('invalid hourly rate');
  const lines = operations.map((op, i) => {
    const { name = `Operation ${i+1}`, setupMinutes = 0, cycleMinutes, quantity = 1 } = op;
    if (![setupMinutes, cycleMinutes, quantity].every(valid) || !Number.isInteger(quantity))
      throw new RangeError(`invalid operation ${i+1}`);
    const setupCostPln = setupMinutes / 60 * setupRatePln;
    const machiningCostPln = cycleMinutes * quantity / 60 * hourlyRatePln;
    return { name, quantity, setupMinutes, cycleMinutes, setupCostPln, machiningCostPln, totalCostPln: setupCostPln + machiningCostPln };
  });
  return { lines, totalCostPln: lines.reduce((sum, line) => sum + line.totalCostPln, 0) };
}
