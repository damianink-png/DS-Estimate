/* Extracted from Kwantflow GPL-3.0 src/lib/state/quote.svelte.ts.
 * https://github.com/muicci/kwantflow
 * This is the upstream estimate arithmetic, isolated from the Svelte/DB store.
 */
import type { CostComponent, TakeoffItem, Estimate } from './types.js';
import { Decimal } from 'decimal.js';
Decimal.set({ precision: 20, rounding: Decimal.ROUND_HALF_UP });
const dec = (value: number | string | Decimal) => {
 const parsed = new Decimal(value);
 if (!parsed.isFinite()) throw new RangeError('Kwantflow estimate input must be finite');
 return parsed;
};

export function costComponentUnitCost(component: CostComponent): number {
 return dec(component.quantity).mul(component.unit_rate).toNumber();
}
export function operationCost(component: CostComponent): number {
 return costComponentUnitCost(component);
}
export function takeoffItemUnitCost(item: TakeoffItem): number {
 return item.cost_components.reduce((sum, component) => sum.plus(costComponentUnitCost(component)), dec(0)).toNumber();
}
export function takeoffItemTotal(item: TakeoffItem): number {
 return dec(item.quantity).mul(takeoffItemUnitCost(item)).toNumber();
}
export function estimateTotalCost(est: Estimate): number {
 return est.takeoff_items.reduce((sum, item) => sum.plus(takeoffItemTotal(item)), dec(0)).toNumber();
}


/* Original Kwantflow GPL-3.0 quote.svelte.ts category markup logic.
 * Upstream: https://github.com/muicci/kwantflow/blob/main/src/lib/state/quote.svelte.ts
 * Retained category semantics and fallback to general markup.
 */
function estimateCategoryCost(est: Estimate, category: string): number {
 return est.takeoff_items
  .reduce((sum, item) => {
   const unitCost = item.cost_components
    .filter((component) => component.category === category)
    .reduce((cost, component) => cost.plus(costComponentUnitCost(component)), dec(0));
   return sum.plus(unitCost.mul(item.quantity));
  }, dec(0))
  .toNumber();
}

export function estimateTotalPrice(
 est: Estimate,
 generalMarkupPercent: number,
 materialMarkupPercent: number | null,
 labourMarkupPercent: number | null,
 equipmentMarkupPercent: number | null,
 subcontractMarkupPercent: number | null
): number {
 const categories: Array<{ key: string; markup: number | null }> = [
  { key: 'material', markup: materialMarkupPercent },
  { key: 'labour', markup: labourMarkupPercent },
  { key: 'equipment', markup: equipmentMarkupPercent },
  { key: 'subcontract', markup: subcontractMarkupPercent },
  { key: 'misc', markup: null }
 ];
 let total = dec(0);
 for (const { key, markup } of categories) {
  const categoryCost = estimateCategoryCost(est, key);
  if (categoryCost === 0) continue;
  const rate = markup != null ? markup : generalMarkupPercent;
  total = total.plus(dec(categoryCost).mul(dec(1).plus(dec(rate).div(100))));
 }
 return total.toNumber();
}
