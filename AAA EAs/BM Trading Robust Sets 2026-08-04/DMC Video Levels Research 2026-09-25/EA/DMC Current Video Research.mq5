#property copyright "Native MT5 port prepared from the AAA Final strategy configuration"
#property version   "1.00"
// Research copy 2026-09-25: production DmC wrapper + video-levels research engine (new inputs default off)
#property strict
#define AAA_STRATEGY_ID 3
#define AAA_STRATEGY_NAME "AAA Final DmC"
#define AAA_DEFAULT_ENABLED true
#define AAA_DEFAULT_RISK 1.0
#define AAA_DEFAULT_RR 1.7
#define AAA_DEFAULT_MAGIC 1082601
#define AAA_DEFAULT_MARKOV_FILTER true
input bool InpAdaptivePortfolioControls=false;
#include "AAA_Final_Strategy_Engine.mqh"
