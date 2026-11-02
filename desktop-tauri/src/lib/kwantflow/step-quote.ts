/* DS Estimate STEP -> Kwantflow RFQ adapter (host code, NOT upstream Kwantflow).
 * Uses upstream GPL-3.0 estimate arithmetic and snapshot functions.
 * STEP only supplies verified group quantity and unit mass. Rates and routing
 * are explicit user inputs; no welding, machining or PDF features are inferred.
 */
import { estimateTotalCost, estimateTotalPrice, takeoffItemTotal } from './estimate-calculation.js';
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
export interface ProductionOperation {
 name: string; setupMin?: number; cycleMinPerPart?: number;
 ratePlnHour?: number; setupRatePlnHour?: number;
 toolingPlnBatch?: number; consumablesPlnPart?: number;
 category?: 'equipment' | 'labour' | 'subcontract';
}
export interface StepQuoteInputs {
 materialRatePlnKg: number; ratePlnHour: number;
 /** Manual stock purchase allowance, not inferred from finished STEP volume. */
 stockAllowancePercent?: number;
 /** Optional per-group purchased stock mass (kg per piece); overrides stock allowance. */
 stockKgPerPart?: Record<string, number>;
 /** Setup is charged once per distinct geometry and operation; cycle is per occurrence. */
 groupOperations?: Record<string, ProductionOperation[]>;
 routing?: QuoteRouting;
 markup?: { mode?: 'markup' | 'grossMargin'; generalPercent?: number; materialPercent?: number | null; labourPercent?: number | null; equipmentPercent?: number | null; subcontractPercent?: number | null };
}
export interface StepQuoteResult {
 estimate: Estimate;
 totalCostPln: number;
 sellingPricePln: number;
 markupAmountPln: number;
 achievedGrossMarginPercent: number;
 materialCostPln: number;
 routingCostPln: number;
 purchasedStockMassKg: number;
 stockWasteMassKg: number;
 setupCostPln: number;
 perPartOperationCostPln: number;
 consumablesCostPln: number;
 toolingCostPln: number;
 groups: Array<{ geometryId: string; quantity: number; unitMassKg: number; totalMassKg: number; stockKgPerPart: number; costPln: number }>;
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
 const stockAllowancePercent=nonnegative(inputs.stockAllowancePercent??0,'stockAllowancePercent');
 if (stockAllowancePercent>1000) throw new RangeError('stockAllowancePercent exceeds 1000');
 const overrides=inputs.stockKgPerPart??{};
 const processes=inputs.groupOperations??{};
 for (const key of Object.keys(overrides)) if (!ids.has(key)) throw new Error('Nieznana grupa półfabrykatu: '+key);
 for (const key of Object.keys(processes)) if (!ids.has(key)) throw new Error('Nieznana grupa operacji: '+key);
 const purchasedGroups=groups.map(g=>{
  const stock=nonnegative(overrides[g.geometryId]??g.unitMassKg*(1+stockAllowancePercent/100),'stockKgPerPart');
  if (stock+1e-8<g.unitMassKg) throw new RangeError('Półfabrykat lżejszy od detalu: '+g.geometryId);
  return {...g,stockKgPerPart:stock};
 });
 const takeoff_items:TakeoffItem[]=purchasedGroups.map(g=>{
  const id='step-group-'+g.index;
  return item(id,g.geometryId,g.quantity,'szt.',[
   component(id+'-material',id,'Materiał zakupiony (półfabrykat)','material',g.stockKgPerPart,'kg',inputs.materialRatePlnKg)
  ],{geometryId:g.geometryId,unitMassKg:g.unitMassKg,stockKgPerPart:g.stockKgPerPart,source:'STEP: masa gotowa; masa zakupu: jawne założenie'});
 });
 const routing=inputs.routing??{};
 const routingKeys: Array<[keyof QuoteRouting,string,string]>=[
  ['assemblyMin','Montaż','labour'],['weldingMin','Spawanie','labour'],
  ['cuttingMin','Cięcie','equipment'],['cncMin','Obróbka CNC','equipment'],
  ['finishingMin','Wykończenie i kontrola','labour']
 ];
 let routingCostPln=0;
 let setupCostPln=0,perPartOperationCostPln=0,consumablesCostPln=0,toolingCostPln=0;
 for(const g of purchasedGroups){
  const operations=processes[g.geometryId]??[];
  if(!Array.isArray(operations))throw new TypeError('groupOperations must contain arrays');
  for(const [index,op] of operations.entries()){
   if(!op || typeof op.name!=='string' || !op.name.trim())throw new TypeError('Missing operation name');
   const category=op.category??'equipment';
   if(!['equipment','labour','subcontract'].includes(category))throw new RangeError('operation category');
   const setup=nonnegative(op.setupMin??0,'setupMin'),cycle=nonnegative(op.cycleMinPerPart??0,'cycleMinPerPart');
   const rate=nonnegative(op.ratePlnHour??inputs.ratePlnHour,'ratePlnHour');
   const setupRate=nonnegative(op.setupRatePlnHour??rate,'setupRatePlnHour');
   const tooling=nonnegative(op.toolingPlnBatch??0,'toolingPlnBatch');
   const consumables=nonnegative(op.consumablesPlnPart??0,'consumablesPlnPart');
   const id='process-'+g.index+'-'+index;
   const items:TakeoffItem[]=[];
   if(cycle||consumables){
    const comps:CostComponent[]=[];
    if(cycle)comps.push(component(id+'-cycle',id,op.name+' — cykl',category,cycle/60,'h',rate));
    if(consumables)comps.push(component(id+'-consumables',id,op.name+' — materiały pomocnicze','misc',1,'szt.',consumables));
    items.push(item(id,op.name+' — '+g.geometryId,g.quantity,'szt.',comps,{source:'manual operation per part',geometryId:g.geometryId}));
   }
   if(setup||tooling){
    const batchId=id+'-batch';const comps:CostComponent[]=[];
    if(setup)comps.push(component(batchId+'-setup',batchId,op.name+' — przezbrojenie',category,setup/60,'h',setupRate));
    if(tooling)comps.push(component(batchId+'-tool',batchId,op.name+' — oprzyrządowanie','equipment',1,'partia',tooling));
    items.push(item(batchId,op.name+' — przygotowanie partii '+g.geometryId,1,'partia',comps,{source:'manual once per geometry group',geometryId:g.geometryId}));
   }
   for(const row of items){takeoff_items.push(row);routingCostPln+=takeoffItemTotal(row)}
   setupCostPln+=setup/60*setupRate;
   perPartOperationCostPln+=cycle/60*rate*g.quantity;
   consumablesCostPln+=consumables*g.quantity;
   toolingCostPln+=tooling;
  }
 }
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
 const materialCostPln=purchasedGroups.reduce((s,g)=>s+g.stockKgPerPart*g.quantity*inputs.materialRatePlnKg,0);
 const purchasedStockMassKg=purchasedGroups.reduce((s,g)=>s+g.stockKgPerPart*g.quantity,0);
 const stockWasteMassKg=purchasedStockMassKg-inventory.totalMassKg;
 const totalCostPln=estimateTotalCost(estimate);
 const markup=inputs.markup??{};
 const validMarkup=(v: number | null | undefined, name: string): number | null => {
  if (v == null) return null;
  if (!Number.isFinite(v) || v < -100) throw new RangeError(name);
  return v;
 };
 const mode=markup.mode??'markup';
 if(!['markup','grossMargin'].includes(mode))throw new RangeError('pricing mode');
 const effectiveMarkup=(value: number | null): number | null=>{
  if(value==null)return null;
  if(mode==='grossMargin'){
   if(value<0||value>=100)throw new RangeError('grossMargin must be 0.. <100');
   return value/(100-value)*100;
  }
  return value;
 };
 const general=effectiveMarkup(validMarkup(markup.generalPercent??0,'generalPercent'))??0;
 const material=effectiveMarkup(validMarkup(markup.materialPercent,'materialPercent'));
 const labour=effectiveMarkup(validMarkup(markup.labourPercent,'labourPercent'));
 const equipment=effectiveMarkup(validMarkup(markup.equipmentPercent,'equipmentPercent'));
 const subcontract=effectiveMarkup(validMarkup(markup.subcontractPercent,'subcontractPercent'));
 const sellingPricePln=estimateTotalPrice(estimate,general,material,labour,equipment,subcontract);
 const achievedGrossMarginPercent=sellingPricePln>0?100*(sellingPricePln-totalCostPln)/sellingPricePln:0;
 if (Math.abs(totalCostPln-materialCostPln-routingCostPln)>Math.max(1e-6,totalCostPln*1e-9))
  throw new Error('Niespójność składników kosztorysu');
 return {estimate,totalCostPln,sellingPricePln,markupAmountPln:sellingPricePln-totalCostPln,achievedGrossMarginPercent,materialCostPln,routingCostPln,
  purchasedStockMassKg,stockWasteMassKg,setupCostPln,perPartOperationCostPln,consumablesCostPln,toolingCostPln,
  groups:purchasedGroups.map(g=>({geometryId:g.geometryId,quantity:g.quantity,unitMassKg:g.unitMassKg,totalMassKg:g.totalMassKg,stockKgPerPart:g.stockKgPerPart,costPln:g.stockKgPerPart*g.quantity*inputs.materialRatePlnKg})),
  provenance:['B-Rep STEP: ilość, grupowanie i masa','Kwantflow GPL-3.0: wycena pozycji i snapshot','DS Estimate: koszt masy zakupu, przezbrojenie na partię, cykl na sztukę, normy i stawki podane jawnie (nieodczytane z STEP/PDF)']};
}
