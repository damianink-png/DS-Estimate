export function calculateWeld({lengthM,throatMm,depositionKgH,arcFactor,setupMin}) {
  const values=[lengthM,throatMm,depositionKgH,arcFactor,setupMin];
  if(values.some(v=>!Number.isFinite(v)) || lengthM<0 || throatMm<0 || depositionKgH<=0 || arcFactor<=0 || arcFactor>1 || setupMin<0) throw new RangeError('Nieprawidłowe parametry spawania');
  const massKg=lengthM*throatMm*throatMm*0.00785;
  const arcMinutes=massKg/depositionKgH*60;
  return {massKg,arcMinutes,totalMinutes:arcMinutes/arcFactor+setupMin};
}