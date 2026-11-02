/* DS Estimate STEP -> Kwantflow RFQ adapter (host code, NOT upstream Kwantflow).
 * Uses upstream GPL-3.0 estimate arithmetic and snapshot functions.
 * STEP only supplies verified group quantity and unit mass. Rates and routing
 * are explicit user inputs; no welding, machining or PDF features are inferred.
 */
import { estimateTotalCost, takeoffItemTotal } from './estimate-calculation.js';
import { cloneEstimateSnapshot } from './estimate-snapshot.js';
import type { CostComponent, Estimate, TakeoffItem } from './types.js';

export interface StepGroup { geometryId: string; quantity: number; massKg: number }
export interface StepInventory {
 source: string; count: number; totalMassKg: number;
 groups: StepGroup[]; solids?: unknown[]; limitations?: string[];
}
export interface QuoteRouting {
 assemblyMin?: number; weldingMin?: number; cuttingMin?: number;
 cncMin?: number; finishingMin?: number;
}
export interface StepQuoteInputs {
 materialRatePlnKg: number; ratePlnHour: number;
 routing?: QuoteRouting;
}
export interface StepQuoteResult {
 estimate: Estimate;
 totalCostPln: number;
 materialCostPln: number;
 routingCostPln: number;
 groups: Array<{ geometryId: string; quantity: number; unitMassKg: number; totalMassKg: number; costPln: number }>;
 provenance: string[];
}
const nonnegative = (value: number, name: string, positive=false): number => {
 if (!Number.isFinite(value) || value < 0 || (positive && value === 0)) throw new RangeError(name);
 return value;
};
const component = (id: string, itemId: string, name: string, category: string, quantity: number, unit: string, unitRate: number): CostComponent => ({
 id, takeoff_item_id:itemId, name, description:'', category, source_type:'manual',
 source_id:null, quantity, unit, unit_rate:unitRate, formula:{},
 metadata:{origin:'DS Estimate STEP quote adapter', rate_source:'user'}, sort_order:0
});
const item = (id: string, name: string, quantity: number, unit: string, components: CostComponent[], properties: Record<string,unknown>): TakeoffItem => ({
 id, estimate_asset_id:'step-import', name, description:'', quantity, unit,
 properties, sort_order:0, cost_components:components
});
export function parseStepInventory(json: string): StepInventory {
 let parsed: unknown;
 try { parsed=JSON.parse(json); } catch { throw new Error('Niepoprawny JSON silnika STEP'); }
 if (!parsed || typeof parsed !== 'object') throw new Error('Brak danych STEP');
 return parsed as StepInventory;
}
export function buildStepQuote(inventory: StepInventory, inputs: StepQuoteInputs): StepQuoteResult {
 if (!inventory || !Array.isArray(inventory.groups) || !inventory.groups.length)
  throw new Error('Brak zweryfikowanych grup części STEP');
 nonnegative(inputs.materialRatePlnKg,'materialRatePlnKg',true);
 nonnegative(inputs.ratePlnHour,'ratePlnHour',true);
 if (!Number.isInteger(inventory.count) || inventory.count < 1) throw new RangeError('count');
 nonnegative(inventory.totalMassKg,'totalMassKg');
 const ids=new Set<string>();
 let count=0, mass=0;
 const groups=inventory.groups.map((g,index)=>{
  if (typeof g.geometryId !== 'string' || !g.geometryId.trim() || ids.has(g.geometryId)) throw new Error('Powielony lub pusty geometryId');
  ids.add(g.geometryId);
  if (!Number.isSafeInteger(g.quantity) || g.quantity < 1) throw new RangeError('quantity');
  nonnegative(g.massKg,'massKg',true);
  count+=g.quantity;
  mass+=g.quantity*g.massKg;
  return {geometryId:g.geometryId,quantity:g.quantity,unitMassKg:g.massKg,totalMassKg:g.quantity*g.massKg,index};
 });
 if (count!==inventory.count) throw new Error('Liczba wystąpień STEP nie zgadza się z grupami');
 if (Math.abs(mass-inventory.totalMassKg)>Math.max(1e-6,inventory.totalMassKg*1e-5))
  throw new Error('Masa STEP nie zgadza się z grupami');
 const takeoff_items:TakeoffItem[]=groups.map(g=>{
  const id='step-group-'+g.index;
  return item(id,g.geometryId,g.quantity,'szt.',[
   component(id+'-material',id,'Materiał wg masy B-Rep','material',g.unitMassKg,'kg',inputs.materialRatePlnKg)
  ],{geometryId:g.geometryId,unitMassKg:g.unitMassKg,source:'STEP verified geometry group'});
 });
 const routing=inputs.routing??{};
 const routingKeys: Array<[keyof QuoteRouting,string,string]>=[
  ['assemblyMin','Montaż','labour'],['weldingMin','Spawanie','labour'],
  ['cuttingMin','Cięcie','equipment'],['cncMin','Obróbka CNC','equipment'],
  ['finishingMin','Wykończenie i kontrola','labour']
 ];
 let routingCostPln=0;
 for (const [key,label,category] of routingKeys) {
  const minutes=nonnegative(routing[key]??0,String(key));
  if (!minutes) continue;
  const id='route-'+key;
  const row=item(id,label,1,'operacja',[
   component(id+'-cost',id,label,category,minutes/60,'h',inputs.ratePlnHour)
  ],{source:'manual routing', minutes, automatic:false});
  takeoff_items.push(row);
  routingCostPln+=takeoffItemTotal(row);
 }
 const estimate=cloneEstimateSnapshot({
  asset_id:'step-import',scope_summary:'Wycena STEP — masa i jawna technologia',
  notes:'STEP dostarcza wyłącznie ilości i masy. Technologia i stawki podane ręcznie.',
  currency_code:'PLN',takeoff_items
 });
 const materialCostPln=groups.reduce((s,g)=>s+g.totalMassKg*inputs.materialRatePlnKg,0);
 const totalCostPln=estimateTotalCost(estimate);
 if (Math.abs(totalCostPln-materialCostPln-routingCostPln)>Math.max(1e-6,totalCostPln*1e-9))
  throw new Error('Niespójność składników kosztorysu');
 return {estimate,totalCostPln,materialCostPln,routingCostPln,
  groups:groups.map(g=>({geometryId:g.geometryId,quantity:g.quantity,unitMassKg:g.unitMassKg,totalMassKg:g.totalMassKg,costPln:g.totalMassKg*inputs.materialRatePlnKg})),
  provenance:['B-Rep STEP: ilość, grupowanie i masa','Kwantflow GPL-3.0: wycena pozycji i snapshot','DS Estimate: jawne normy technologiczne i stawki (nieodczytane z STEP/PDF)']};
}
