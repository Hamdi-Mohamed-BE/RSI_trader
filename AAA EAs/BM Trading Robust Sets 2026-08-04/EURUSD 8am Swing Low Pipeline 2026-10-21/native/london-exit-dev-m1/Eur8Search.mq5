#property strict
#property version "1.00"
#property description "Research only (2026-10-21). EURUSD 8am swing-low pipeline engine: compiled case table, InpCase selects one configuration."
#include <Trade/Trade.mqh>

input int    InpCase=0;
input string InpTag="eur8";
input double InpRiskPct=1.0;
input int    InpServerUtcOffsetHours=0;
input int    InpMaximumDeviationPoints=50;
input long   InpMagic=2110261;

#define NF 24
const int NC=87;
const double Cases[87][NF]={
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,0.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,0.0,2.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,0.0,3.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,0.0,4.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,0.0,6.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,0.0,8.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,0.0,0.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,0.5,8.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,0.75,8.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,1.0,8.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,1.25,8.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,1.5,8.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,2.0,8.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,2.5,8.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,3.0,8.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,4.0,8.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,5.0,8.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,6.0,8.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,0.5,0.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,0.75,0.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,1.0,0.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,1.25,0.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,1.5,0.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,2.0,0.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,2.5,0.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,3.0,0.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,4.0,0.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,5.0,0.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,6.0,0.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,0.0,1.0,0.0,0.0,2.0,0.5,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,0.0,2.0,0.0,0.0,2.0,0.5,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,0.0,3.0,0.0,0.0,2.0,0.5,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,0.0,4.0,0.0,0.0,2.0,0.5,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,0.0,6.0,0.0,0.0,2.0,0.5,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,0.0,8.0,0.0,0.0,2.0,0.5,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,0.0,0.0,1.0,0.0,2.0,0.5,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,0.5,8.0,0.0,0.0,2.0,0.5,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,0.75,8.0,0.0,0.0,2.0,0.5,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,1.0,8.0,0.0,0.0,2.0,0.5,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,1.25,8.0,0.0,0.0,2.0,0.5,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,1.5,8.0,0.0,0.0,2.0,0.5,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,2.0,8.0,0.0,0.0,2.0,0.5,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,2.5,8.0,0.0,0.0,2.0,0.5,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,3.0,8.0,0.0,0.0,2.0,0.5,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,4.0,8.0,0.0,0.0,2.0,0.5,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,5.0,8.0,0.0,0.0,2.0,0.5,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,6.0,8.0,0.0,0.0,2.0,0.5,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,0.5,0.0,1.0,0.0,2.0,0.5,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,0.75,0.0,1.0,0.0,2.0,0.5,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,1.0,0.0,1.0,0.0,2.0,0.5,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,1.25,0.0,1.0,0.0,2.0,0.5,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,1.5,0.0,1.0,0.0,2.0,0.5,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,2.0,0.0,1.0,0.0,2.0,0.5,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,2.5,0.0,1.0,0.0,2.0,0.5,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,3.0,0.0,1.0,0.0,2.0,0.5,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,4.0,0.0,1.0,0.0,2.0,0.5,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,5.0,0.0,1.0,0.0,2.0,0.5,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,6.0,0.0,1.0,0.0,2.0,0.5,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,0.0,1.0,0.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,0.0,2.0,0.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,0.0,3.0,0.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,0.0,4.0,0.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,0.0,6.0,0.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,0.0,8.0,0.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,0.0,0.0,1.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,0.5,8.0,0.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,0.75,8.0,0.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,1.0,8.0,0.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,1.25,8.0,0.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,1.5,8.0,0.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,2.0,8.0,0.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,2.5,8.0,0.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,3.0,8.0,0.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,4.0,8.0,0.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,5.0,8.0,0.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,6.0,8.0,0.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,0.5,0.0,1.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,0.75,0.0,1.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,1.0,0.0,1.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,1.25,0.0,1.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,1.5,0.0,1.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,2.0,0.0,1.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,2.5,0.0,1.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,3.0,0.0,1.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,4.0,0.0,1.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,5.0,0.0,1.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0},
{0.0,8.0,0.0,30.0,2.0,4.0,1.0,0.0,2.0,0.0,2.0,0.0,0.5,0.5,6.0,0.0,1.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0}
};

int gClock,gHour,gMinute,gN,gW,gLL,gDir,gEntry,gStopType,gExitMode,gTrend,gAtrRegime,gDow;
ENUM_TIMEFRAMES gTf;
double gEntryK,gEntryExpH,gStopVal,gMinStop,gTpR,gHoldH,gBeR,gTrailAtr,gTrailStartR,gAdxMin;
CTrade trade;
int hAtr=INVALID_HANDLE,hE200=INVALID_HANDLE,hE50=INVALID_HANDLE,hD20=INVALID_HANDLE,hAdx=INVALID_HANDLE;
datetime lastDay=0,lastClose=0,pendingExpiry=0,lastManage=0;
ulong pendingTicket=0;
double posDist=0;
long days=0,freshLow=0,freshHigh=0,placed=0,filtered=0,skippedStops=0,skippedMargin=0,placeFails=0,closeFails=0,modifyFails=0,expiredOrders=0;

void Apply(){
   gClock=(int)Cases[InpCase][0];gHour=(int)Cases[InpCase][1];gMinute=(int)Cases[InpCase][2];
   int tf=(int)Cases[InpCase][3];gTf=tf==15?PERIOD_M15:(tf==30?PERIOD_M30:PERIOD_H1);
   gN=(int)Cases[InpCase][4];gW=(int)Cases[InpCase][5];gLL=(int)Cases[InpCase][6];gDir=(int)Cases[InpCase][7];
   gEntry=(int)Cases[InpCase][8];gEntryK=Cases[InpCase][9];gEntryExpH=Cases[InpCase][10];
   gStopType=(int)Cases[InpCase][11];gStopVal=Cases[InpCase][12];gMinStop=Cases[InpCase][13];
   gTpR=Cases[InpCase][14];gHoldH=Cases[InpCase][15];gExitMode=(int)Cases[InpCase][16];
   gBeR=Cases[InpCase][17];gTrailAtr=Cases[InpCase][18];gTrailStartR=Cases[InpCase][19];
   gTrend=(int)Cases[InpCase][20];gAdxMin=Cases[InpCase][21];gAtrRegime=(int)Cases[InpCase][22];gDow=(int)Cases[InpCase][23];
}

datetime LastSunday(int year,int month){MqlDateTime t={};t.year=year;t.mon=month;t.day=31;datetime x=StructToTime(t);MqlDateTime d;TimeToStruct(x,d);return x-(datetime)(d.day_of_week*86400);}
datetime NthSunday(int year,int month,int n){MqlDateTime t={};t.year=year;t.mon=month;t.day=1;datetime x=StructToTime(t);MqlDateTime d;TimeToStruct(x,d);return x+(datetime)((((7-d.day_of_week)%7)+7*(n-1))*86400);}
datetime London(datetime utc){MqlDateTime d;TimeToStruct(utc,d);datetime on=LastSunday(d.year,3)+3600,off=LastSunday(d.year,10)+3600;return utc+((utc>=on&&utc<off)?3600:0);}
datetime NewYork(datetime utc){MqlDateTime d;TimeToStruct(utc,d);datetime on=NthSunday(d.year,3,2)+7*3600,off=NthSunday(d.year,11,1)+6*3600;return utc-5*3600+((utc>=on&&utc<off)?3600:0);}
datetime Utc(datetime server){return server-(datetime)((long)InpServerUtcOffsetHours*3600);}
datetime Local(datetime server){return gClock==0?London(Utc(server)):NewYork(Utc(server));}
double Price(double p){double t=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);return NormalizeDouble(MathRound(p/t)*t,_Digits);}
double Buf(int h,int buffer,int shift){double v[];if(h==INVALID_HANDLE||CopyBuffer(h,buffer,shift,1,v)!=1)return EMPTY_VALUE;return v[0];}

bool PivotLow(int k,int n){double x=iLow(_Symbol,gTf,k);if(x<=0)return false;
   for(int j=1;j<=n;j++){if(k-j<1)return false;if(!(x<iLow(_Symbol,gTf,k-j))||!(x<iLow(_Symbol,gTf,k+j)))return false;}return true;}
bool PivotHigh(int k,int n){double x=iHigh(_Symbol,gTf,k);if(x<=0)return false;
   for(int j=1;j<=n;j++){if(k-j<1)return false;if(!(x>iHigh(_Symbol,gTf,k-j))||!(x>iHigh(_Symbol,gTf,k+j)))return false;}return true;}
int FreshLow(){
   for(int k=gN+1;k<=gN+gW;k++){
      if(!PivotLow(k,gN))continue;
      if(gLL==0)return k;
      for(int p=k+1;p<=k+200;p++)if(PivotLow(p,gN))return iLow(_Symbol,gTf,k)<iLow(_Symbol,gTf,p)?k:-1;
      return -1;
   }
   return -1;
}
int FreshHigh(){
   for(int k=gN+1;k<=gN+gW;k++){
      if(!PivotHigh(k,gN))continue;
      if(gLL==0)return k;
      for(int p=k+1;p<=k+200;p++)if(PivotHigh(p,gN))return iHigh(_Symbol,gTf,k)>iHigh(_Symbol,gTf,p)?k:-1;
      return -1;
   }
   return -1;
}
bool HasPosition(){for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);if(t&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==InpMagic)return true;}return false;}
bool PendingAlive(){if(pendingTicket==0)return false;if(OrderSelect(pendingTicket))return true;pendingTicket=0;return false;}

bool FilterOk(bool longSide,const MqlDateTime &l){
   if((gDow==1&&l.day_of_week==1)||(gDow==2&&l.day_of_week==5)||(gDow==3&&(l.day_of_week==1||l.day_of_week==5)))return false;
   if(gTrend==1){double e=Buf(hE200,0,1),c=iClose(_Symbol,PERIOD_H1,1);if(e==EMPTY_VALUE||c<=0)return false;if(longSide?c<=e:c>=e)return false;}
   if(gTrend==2){double a=Buf(hE50,0,1),b=Buf(hE50,0,6);if(a==EMPTY_VALUE||b==EMPTY_VALUE)return false;if(longSide?a<=b:a>=b)return false;}
   if(gTrend==3){double e=Buf(hD20,0,1),c=iClose(_Symbol,PERIOD_D1,1);if(e==EMPTY_VALUE||c<=0)return false;if(longSide?c<=e:c>=e)return false;}
   if(gAdxMin>0){double a=Buf(hAdx,0,1);if(a==EMPTY_VALUE||a<gAdxMin)return false;}
   if(gAtrRegime>0){double v[];if(CopyBuffer(hAtr,0,1,100,v)!=100)return false;double cur=v[99];ArraySort(v);double med=(v[49]+v[50])/2.0;
      if(gAtrRegime==1&&cur<med)return false;if(gAtrRegime==2&&cur>=med)return false;}
   return true;
}

double StopDistance(bool buy,double entry,double stopPrice,double atr){
   double d=gStopType==0?(buy?entry-stopPrice:stopPrice-entry):gStopVal*atr;
   return MathMax(d,gMinStop*atr);
}

bool Volume(bool buy,double entry,double sl,double &volume){
   double unit=0,margin=0;ENUM_ORDER_TYPE type=buy?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,sl,unit)||unit>=0){skippedStops++;return false;}
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),mn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),mx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double goal=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPct/100.0;
   volume=NormalizeDouble(MathMax(mn,MathCeil((goal/-unit-1e-10)/step)*step),8);
   if(volume>mx||!OrderCalcMargin(type,_Symbol,volume,entry,margin)||margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE)){skippedMargin++;return false;}
   return true;
}

bool OpenMarket(bool buy,double stopPrice,double atr,string cm){
   MqlTick q;if(!SymbolInfoTick(_Symbol,q)||q.ask<=0||q.bid<=0)return false;
   double entry=buy?q.ask:q.bid,dist=StopDistance(buy,entry,stopPrice,atr);
   double sl=Price(buy?entry-dist:entry+dist),tp=gTpR>0?Price(buy?entry+gTpR*dist:entry-gTpR*dist):0;
   double gap=MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*_Point;
   if((buy&&(q.bid-sl<=gap||(tp>0&&tp-q.bid<=gap)))||(!buy&&(sl-q.ask<=gap||(tp>0&&q.ask-tp<=gap)))){skippedStops++;return false;}
   double volume=0;if(!Volume(buy,entry,sl,volume))return false;
   trade.SetExpertMagicNumber(InpMagic);
   bool ok=buy?trade.Buy(volume,_Symbol,0,sl,tp,cm):trade.Sell(volume,_Symbol,0,sl,tp,cm);
   if(!ok||trade.ResultRetcode()!=TRADE_RETCODE_DONE){placeFails++;return false;}
   posDist=dist;placed++;return true;
}

bool OpenPending(bool buy,double price,double stopPrice,double atr,string cm){
   MqlTick q;if(!SymbolInfoTick(_Symbol,q)||q.ask<=0||q.bid<=0)return false;
   price=Price(price);
   double gap=MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*_Point;
   bool limit=gEntry==1;
   if(limit&&((buy&&price>=q.ask-gap)||(!buy&&price<=q.bid+gap))){skippedStops++;return false;}
   if(!limit&&((buy&&price<=q.ask+gap)||(!buy&&price>=q.bid-gap))){skippedStops++;return false;}
   double dist=StopDistance(buy,price,stopPrice,atr);
   double sl=Price(buy?price-dist:price+dist),tp=gTpR>0?Price(buy?price+gTpR*dist:price-gTpR*dist):0;
   double volume=0;if(!Volume(buy,price,sl,volume))return false;
   trade.SetExpertMagicNumber(InpMagic);bool ok;
   if(limit)ok=buy?trade.BuyLimit(volume,price,_Symbol,sl,tp,ORDER_TIME_GTC,0,cm):trade.SellLimit(volume,price,_Symbol,sl,tp,ORDER_TIME_GTC,0,cm);
   else ok=buy?trade.BuyStop(volume,price,_Symbol,sl,tp,ORDER_TIME_GTC,0,cm):trade.SellStop(volume,price,_Symbol,sl,tp,ORDER_TIME_GTC,0,cm);
   if(!ok||trade.ResultRetcode()!=TRADE_RETCODE_DONE){placeFails++;return false;}
   pendingTicket=trade.ResultOrder();pendingExpiry=TimeCurrent()+(datetime)(gEntryExpH*3600);posDist=dist;placed++;return true;
}

bool InTradeSession(){
   datetime now=TimeCurrent(),from=0,to=0;MqlDateTime d;TimeToStruct(now,d);long sec=(long)(now%86400);
   for(uint i=0;SymbolInfoSessionTrade(_Symbol,(ENUM_DAY_OF_WEEK)d.day_of_week,i,from,to);i++)if(sec>=(long)from&&sec<(long)to)return true;
   return false;
}

void ManagePending(){
   if(!PendingAlive())return;
   if(TimeCurrent()>=pendingExpiry){if(trade.OrderDelete(pendingTicket))expiredOrders++;pendingTicket=0;}
}

void ManageStops(){
   if(gBeR<=0&&gTrailAtr<=0)return;
   datetime m=TimeCurrent()/60;if(m==lastManage)return;lastManage=m;
   MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;
   double atr=Buf(hAtr,0,1);
   for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);
      if(!t||PositionGetString(POSITION_SYMBOL)!=_Symbol||PositionGetInteger(POSITION_MAGIC)!=InpMagic)continue;
      bool buy=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY;double open=PositionGetDouble(POSITION_PRICE_OPEN),sl=PositionGetDouble(POSITION_SL),tp=PositionGetDouble(POSITION_TP);
      double move=buy?q.bid-open:open-q.ask,ns=sl;
      if(gBeR>0&&move>=gBeR*posDist)ns=buy?MathMax(ns,open):(ns==0?open:MathMin(ns,open));
      if(gTrailAtr>0&&atr!=EMPTY_VALUE&&move>=gTrailStartR*posDist){double tr=buy?q.bid-gTrailAtr*atr:q.ask+gTrailAtr*atr;ns=buy?MathMax(ns,tr):MathMin(ns,tr);}
      ns=Price(ns);
      double gap=MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*_Point;
      if(MathAbs(ns-sl)<_Point/2||(buy&&q.bid-ns<=gap)||(!buy&&ns-q.ask<=gap))continue;
      if(!trade.PositionModify(t,ns,tp))modifyFails++;
   }
}

void TimeExits(){
   datetime now=TimeCurrent();if(now-lastClose<30||!InTradeSession())return;
   for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);
      if(!t||PositionGetString(POSITION_SYMBOL)!=_Symbol||PositionGetInteger(POSITION_MAGIC)!=InpMagic)continue;
      datetime opened=(datetime)PositionGetInteger(POSITION_TIME);bool due=false;
      if(gHoldH>0&&now-opened>=(long)(gHoldH*3600))due=true;
      if(gExitMode==1){datetime lo=Local(opened),ln=Local(now);int endMin=gClock==0?16*60+30:17*60;MqlDateTime n;TimeToStruct(ln,n);
         if(ln-ln%86400>lo-lo%86400||n.hour*60+n.min>=endMin)due=true;}
      if(!due)continue;
      lastClose=now;
      if(!trade.PositionClose(t)||trade.ResultRetcode()!=TRADE_RETCODE_DONE){
         if(trade.ResultRetcode()!=TRADE_RETCODE_POSITION_CLOSED&&trade.ResultRetcode()!=TRADE_RETCODE_MARKET_CLOSED)closeFails++;}
   }
}

void Evaluate(){
   datetime now=TimeCurrent(),loc=Local(now);MqlDateTime l;TimeToStruct(loc,l);
   if(l.day_of_week<1||l.day_of_week>5)return;
   int mins=l.hour*60+l.min,anchor=gHour*60+gMinute;if(mins<anchor||mins>=anchor+60)return;
   datetime day=loc-loc%86400;if(day==lastDay)return;lastDay=day;days++;
   double atr=Buf(hAtr,0,1);if(atr==EMPTY_VALUE||atr<=0)return;
   int kl=FreshLow(),kh=FreshHigh();
   if(kl>0)freshLow++;
   if(kh>0)freshHigh++;
   if(HasPosition()||PendingAlive())return;
   bool goLong=(gDir==0||gDir==2)&&kl>0,goShort=(gDir==1&&kh>0)||(gDir==2&&kl<0&&kh>0);
   if(!goLong&&!goShort)return;
   if(!FilterOk(goLong,l)){filtered++;return;}
   MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;
   double stopPrice=gStopType==0?(goLong?iLow(_Symbol,gTf,kl)-gStopVal*atr:iHigh(_Symbol,gTf,kh)+gStopVal*atr):0;
   if(gEntry==0)OpenMarket(goLong,stopPrice,atr,goLong?"EUR8P LONG":"EUR8P SHORT");
   else if(gEntry==1)OpenPending(goLong,goLong?q.ask-gEntryK*atr:q.bid+gEntryK*atr,stopPrice,atr,goLong?"EUR8P LIMIT LONG":"EUR8P LIMIT SHORT");
   else OpenPending(goLong,goLong?iHigh(_Symbol,gTf,1):iLow(_Symbol,gTf,1),stopPrice,atr,goLong?"EUR8P STOP LONG":"EUR8P STOP SHORT");
}

int OnInit(){
   if(!MQLInfoInteger(MQL_TESTER)||InpCase<0||InpCase>=NC||InpRiskPct<=0||InpRiskPct>5)return INIT_PARAMETERS_INCORRECT;
   Apply();
   if(gN<1||gW<1||gDir<0||gDir>2||gEntry<0||gEntry>2||(gHoldH<=0&&gExitMode==0&&gTpR<=0))return INIT_PARAMETERS_INCORRECT;
   hAtr=iATR(_Symbol,PERIOD_H1,14);hE200=iMA(_Symbol,PERIOD_H1,200,0,MODE_EMA,PRICE_CLOSE);hE50=iMA(_Symbol,PERIOD_H1,50,0,MODE_EMA,PRICE_CLOSE);
   hD20=iMA(_Symbol,PERIOD_D1,20,0,MODE_EMA,PRICE_CLOSE);hAdx=iADX(_Symbol,PERIOD_H1,14);
   if(hAtr==INVALID_HANDLE||hE200==INVALID_HANDLE||hE50==INVALID_HANDLE||hD20==INVALID_HANDLE||hAdx==INVALID_HANDLE)return INIT_FAILED;
   if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)return INIT_FAILED;
   trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   return INIT_SUCCEEDED;
}

void OnTick(){
   TimeExits();ManagePending();ManageStops();Evaluate();
}

string Tag(){return InpTag+"-"+(string)InpCase;}
double OnTester(){
   HistorySelect(0,TimeCurrent());
   int out=FileOpen(Tag()+"-deals.csv",FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,',');
   if(out==INVALID_HANDLE)return -1e99;
   FileWrite(out,"ticket","position_id","epoch","entry","type","volume","price","profit","commission","swap","fee","reason","initial_sl","initial_tp");
   for(int i=0;i<HistoryDealsTotal();i++){
      ulong deal=HistoryDealGetTicket(i);if(deal==0)continue;
      long entry=HistoryDealGetInteger(deal,DEAL_ENTRY);if(entry!=DEAL_ENTRY_IN&&entry!=DEAL_ENTRY_OUT)continue;
      if(HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol)continue;
      ulong order=(ulong)HistoryDealGetInteger(deal,DEAL_ORDER);
      FileWrite(out,deal,HistoryDealGetInteger(deal,DEAL_POSITION_ID),(long)HistoryDealGetInteger(deal,DEAL_TIME),entry,HistoryDealGetInteger(deal,DEAL_TYPE),
         HistoryDealGetDouble(deal,DEAL_VOLUME),HistoryDealGetDouble(deal,DEAL_PRICE),HistoryDealGetDouble(deal,DEAL_PROFIT),HistoryDealGetDouble(deal,DEAL_COMMISSION),
         HistoryDealGetDouble(deal,DEAL_SWAP),HistoryDealGetDouble(deal,DEAL_FEE),HistoryDealGetInteger(deal,DEAL_REASON),HistoryOrderGetDouble(order,ORDER_SL),HistoryOrderGetDouble(order,ORDER_TP));
   }
   FileClose(out);
   out=FileOpen(Tag()+"-stats.csv",FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,',');if(out==INVALID_HANDLE)return -1e99;
   FileWrite(out,"net","equity_dd","balance_dd","failed_entries","balance","open_position","trades","mt5_sharpe","days","fresh_low","fresh_high","placed","filtered","skipped_stops","skipped_margin","close_fails","modify_fails","expired_orders");
   FileWrite(out,TesterStatistics(STAT_PROFIT),TesterStatistics(STAT_EQUITY_DDREL_PERCENT),TesterStatistics(STAT_BALANCE_DDREL_PERCENT),placeFails,AccountInfoDouble(ACCOUNT_BALANCE),
      (int)HasPosition(),TesterStatistics(STAT_TRADES),TesterStatistics(STAT_SHARPE_RATIO),days,freshLow,freshHigh,placed,filtered,skippedStops,skippedMargin,closeFails,modifyFails,expiredOrders);
   FileClose(out);
   return TesterStatistics(STAT_PROFIT);
}
