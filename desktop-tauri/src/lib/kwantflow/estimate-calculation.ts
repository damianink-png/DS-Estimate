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
