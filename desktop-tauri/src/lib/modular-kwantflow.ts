/**
 * Isolated Kwantflow integration. Existing GPL-3.0 calculation engine handles
 * decimal pricing. Inputs are ONLY already known costs from separate modules:
 * missing work remains missing, excluded modules never contribute.
 */
import {estimateTotalCost} from './kwantflow/estimate-calculation.js';

export function kwantflowKnownCost(report: any): number {
 const takeoff_items=report.modules.filter((m:any)=>!m.omitted).flatMap((m:any)=>
  m.rows.filter((r:any)=>r.costPln!==null).map((r:any)=>({
   id:m.id+':'+r.key,estimate_asset_id:'modular',name:r.name,
   description:r.evidence,quantity:1,unit:'operation',
   properties:{source:m.id,evidence:r.evidence},sort_order:0,
   cost_components:[{
    id:m.id+':'+r.key+':cost',takeoff_item_id:m.id+':'+r.key,
    category:m.id==='material'?'material':m.id==='purchased'?'subcontract':'labour',
    source_type:r.manuallyEdited?'manual':'estimate',
    name:r.name,description:r.detail,quantity:r.kind==='time'?r.value:1,
    unit:r.kind==='time'?'h':'szt.',
    unit_rate:r.kind==='time'?r.rate:r.value,
    formula:{},metadata:{confidence:r.evidence}
   }]
  }))
 );
 return estimateTotalCost({
  asset_id:'modular-quote',scope_summary:'Known, partial costs only',
  notes:'Unverified or missing operations are omitted, never treated as zero',
  takeoff_items
 });
}
