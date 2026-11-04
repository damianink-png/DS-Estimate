import material from './material.mjs';
import purchased from './purchased.mjs';
import cutting from './cutting.mjs';
import bending from './bending.mjs';
import cnc from './cnc.mjs';
import assembly from './assembly.mjs';
import welding from './welding.mjs';
import postweld from './postweld.mjs';
import coating from './coating.mjs';
import quality from './quality.mjs';
import logistics from './logistics.mjs';
import engineering from './engineering.mjs';

/** One dedicated adapter per independent estimation stage. */
export const MODULES=Object.freeze([
 material,purchased,cutting,bending,cnc,assembly,welding,postweld,coating,quality,logistics,engineering
]);
export const DEFAULT_RATES=Object.freeze({
 materialPriceKg:null,
 cutting:388,bending:388,cnc:388,assembly:120,welding:145,
 postweld:145,coating:150,quality:140,logistics:120,engineering:145
});
