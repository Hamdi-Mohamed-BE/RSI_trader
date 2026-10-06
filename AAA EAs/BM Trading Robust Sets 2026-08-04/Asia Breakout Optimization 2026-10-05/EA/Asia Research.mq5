#property strict
#property version "1.00"
#define AAA_STRATEGY_ID 2
#define AAA_STRATEGY_NAME "AAA Final Asia Breakout"
#define AAA_DEFAULT_ENABLED true
#define AAA_DEFAULT_RISK 1.0
#define AAA_DEFAULT_RR 3.0
#define AAA_DEFAULT_MAGIC 290729
#define AAA_DEFAULT_MARKOV_FILTER true
input bool InpAdaptivePortfolioControls=false;
#include "AAA_Final_Strategy_Engine.mqh"
