/**
 * DS Estimate — milling physics model (not a CAM toolpath simulator).
 * Equations: Sandvik Coromant, Milling formulas (metric):
 * n = vc*1000/(pi*D); vf = fz*n*z; Q = ap*ae*vf/1000 [cm3/min].
 * All cutting data MUST come from the tool/material setup; nothing is inferred
 * from a STEP bounding box or OCR.
 */
const positive=(x,name)=>{if(typeof x!=='number'||!Number.isFinite(x)||x<=0)throw new RangeError(name);return x};
export function millingFromCuttingData({
 cuttingSpeedMMin,toolDiameterMm,teeth,feedPerToothMm,axialDepthMm,radialWidthMm,
 removedCm3,maxSpindleRpm=null,maxFeedMmMin=null,cuttingEfficiency=1,
 specificCuttingForceNmm2=null,availableSpindlePowerKw=null
}={}){
 for(const [key,value] of Object.entries({cuttingSpeedMMin,toolDiameterMm,teeth,feedPerToothMm,axialDepthMm,radialWidthMm}))positive(value,key);
 if(!Number.isInteger(teeth))throw new RangeError('teeth');
 if(typeof removedCm3!=='number'||!Number.isFinite(removedCm3)||removedCm3<0)throw new RangeError('removedCm3');
 if(radialWidthMm>toolDiameterMm)throw new RangeError('radialWidthMm exceeds tool diameter');
 if(typeof cuttingEfficiency!=='number'||!Number.isFinite(cuttingEfficiency)||cuttingEfficiency<=0||cuttingEfficiency>1)throw new RangeError('cuttingEfficiency');
 if(maxSpindleRpm!=null)positive(maxSpindleRpm,'maxSpindleRpm');
 if(maxFeedMmMin!=null)positive(maxFeedMmMin,'maxFeedMmMin');
 if(specificCuttingForceNmm2!=null)positive(specificCuttingForceNmm2,'specificCuttingForceNmm2');
 if(availableSpindlePowerKw!=null)positive(availableSpindlePowerKw,'availableSpindlePowerKw');
 const theoreticalRpm=cuttingSpeedMMin*1000/(Math.PI*toolDiameterMm);
 const rpm=maxSpindleRpm==null?theoreticalRpm:Math.min(theoreticalRpm,maxSpindleRpm);
 const theoreticalFeedMmMin=feedPerToothMm*teeth*rpm;
 const feedMmMin=maxFeedMmMin==null?theoreticalFeedMmMin:Math.min(theoreticalFeedMmMin,maxFeedMmMin);
 const theoreticalRemovalCm3Min=axialDepthMm*radialWidthMm*feedMmMin/1000;
 const removalCm3Min=theoreticalRemovalCm3Min*cuttingEfficiency;
 const cuttingMin=removedCm3/removalCm3Min;
 const actualCuttingSpeedMMin=Math.PI*toolDiameterMm*rpm/1000;
 const requiredPowerKw=specificCuttingForceNmm2==null?null:axialDepthMm*radialWidthMm*feedMmMin*specificCuttingForceNmm2/(60*1e6);
 const powerOverload=requiredPowerKw!=null&&availableSpindlePowerKw!=null&&requiredPowerKw>availableSpindlePowerKw;
 return {rpm,feedMmMin,actualCuttingSpeedMMin,theoreticalRemovalCm3Min,removalCm3Min,cuttingMin,
  requiredPowerKw,powerOverload,confidence:'user-cutting-data',limitations:[
   'Q is constant-engagement roughing throughput, not NC-toolpath simulation',
   'Setup, tool changes, rapid moves, drilling, finishing and inspection must be added separately',
   ...(powerOverload?['Estimated cutting power exceeds declared spindle capability']:[])
  ]};
}
