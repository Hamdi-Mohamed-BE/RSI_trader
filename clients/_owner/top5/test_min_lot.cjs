// Execute the actual sizing function body with broker APIs mocked; no MT5/orders.
const fs=require('fs'),assert=require('assert');
const src=fs.readFileSync(__dirname+'/ClientGuard.mqh','utf8');
let body=src.split('double ClientSizedVolume(')[1].split('bool ClientOwnPosition')[0];
body=body.slice(body.indexOf('{')+1,body.lastIndexOf('}'))
 .replace(/\bdouble\b/g,'let')
 .replace('OrderCalcProfit(type,_Symbol,1,entry,stop,unit)','(unit=-broker.lossPerLot,broker.calcOK)');
let broker,logs;
const SymbolInfoDouble=(_,key)=>broker[key];
const ClientRiskCash=()=>broker.risk;
const PrintFormat=(...args)=>logs.push(args);
const MathFloor=Math.floor,MathAbs=Math.abs,MathMin=Math.min;
const NormalizeDouble=(v,n)=>Number(v.toFixed(n));
const _Symbol='TEST',ORDER_TYPE_BUY=0,ORDER_TYPE_SELL=1;
const SYMBOL_VOLUME_STEP='step',SYMBOL_VOLUME_MIN='min',SYMBOL_VOLUME_MAX='max';
const sizing=eval('(function(type,entry,stop){'+body+'})');
function test(risk,lossPerLot,expected){broker={risk,lossPerLot,step:.01,min:.01,max:100,calcOK:true};logs=[];assert.strictEqual(sizing(0,100,90),expected);}
test(50,7000,.01);assert(logs.length===1); // $70 planned risk at minimum.
test(50,1000,.05);assert(logs.length===0);
test(55,1000,.05);assert(logs.length===0); // Still round DOWN above minimum.
test(70,7000,.01);assert(logs.length===0);
assert.strictEqual(sizing(0,100,0),0);
broker.calcOK=false;assert.strictEqual(sizing(0,100,90),0);
broker.calcOK=true;broker.risk=0;assert.strictEqual(sizing(0,100,90),0);
console.log('PASS: actual sizing body with mocked broker APIs: min-lot excess warning, exact/between steps, invalid stops/calculation/risk remain blocked.');
