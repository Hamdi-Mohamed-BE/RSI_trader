#define CALYX_DEFAULT_ADX true
#define CALYX_DEFAULT_ADX_LEVEL 25.0
#define CALYX_DEFAULT_DI false
#define CALYX_DEFAULT_ADX_TF ((ENUM_TIMEFRAMES)16388)
#property copyright "Native MT5 port prepared from the AAA Final strategy configuration"
#property version   "1.00"
#property strict
#define AAA_STRATEGY_ID 1
#define AAA_STRATEGY_NAME "AAA Final EMA3"
#define AAA_DEFAULT_ENABLED true
#define AAA_DEFAULT_RISK 1.0
#define AAA_DEFAULT_RR 1.7
#define AAA_DEFAULT_MAGIC 3082026
input bool InpAdaptivePortfolioControls=false;
#include "AAA_Final_Strategy_Engine.mqh"
