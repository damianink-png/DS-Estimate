/* Types extracted from Kwantflow GPL-3.0 src/lib/types/index.ts.
 * https://github.com/muicci/kwantflow
 * Unit/category aliases are local compatibility placeholders pending full schema migration.
 */
export type UnitCode = string;
export type CostComponentCategory = string;
export type CostComponentSourceType = string;
export interface CostComponent {
 id: string; takeoff_item_id: string; category: CostComponentCategory;
 source_type: CostComponentSourceType; source_id?: string | null;
 name: string; description: string; quantity: number; unit: UnitCode;
 unit_rate: number; source_unit_rate_decimal?: string | null;
 source_currency_code?: string | null; fx_rate_snapshot_id?: string | null;
 formula: Record<string, unknown>; metadata: Record<string, unknown>;
 sort_order?: number;
}
export interface TakeoffItem {
 id: string; estimate_asset_id: string; parent_id?: string | null;
 wbs_node_id?: string | null; cost_code_id?: string | null;
 applied_preset_id?: string | null; applied_preset_name?: string | null;
 name: string; description: string; quantity: number; unit: UnitCode;
 properties: Record<string, unknown>; sort_order: number;
 cost_components: CostComponent[];
}
export interface Estimate {
 asset_id: string; scope_summary: string; notes: string;
 classification_system_id?: string | null; wbs_root_node_id?: string | null;
 applied_template_id?: string | null; applied_template_name?: string | null;
 currency_code?: string | null; takeoff_items: TakeoffItem[];
}
export interface EstimateTemplatePayload {
 scope_summary: string; notes: string; classification_system_id?: string | null;
 wbs_root_node_id?: string | null; takeoff_items: TakeoffItem[];
}
