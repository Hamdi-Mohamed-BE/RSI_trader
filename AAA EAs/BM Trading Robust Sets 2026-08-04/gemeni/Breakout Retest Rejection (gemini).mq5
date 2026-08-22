//+------------------------------------------------------------------+
//|                                  PriceAction_BOS_Retest.mq5      |
//|                                  Copyright 2026                  |
//|                                  https://www.mql5.com            |
//+------------------------------------------------------------------+
#property copyright "Copyright 2026"
#property link      "https://www.mql5.com"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

//--- Input Parameters (Optimizer Compatible)
input group "--- EA Settings ---"
input ulong    InpMagicNumber       = 888101;     // Magic Number
input double   InpRiskPercent       = 1.0;        // Risk per Trade (% Balance)
input double   InpFixedLot          = 0.01;        // Fixed Lot (0 = Dynamic Risk %)

input group "--- Market Structure Parameters ---"
input ENUM_TIMEFRAMES InpHTF       = PERIOD_H4;   // Higher Timeframe Context
input ENUM_TIMEFRAMES InpLTF       = PERIOD_H1;   // Entry Timeframe
input int      InpSwingLeft         = 5;          // Swing Point Bars Left
input int      InpSwingRight        = 2;          // Swing Point Bars Right
input int      InpRetestTolerance   = 150;        // Retest Zone Tolerance (in Points)

input group "--- Candle Rejection Settings ---"
input double   InpPinBarWickRatio   = 1.0;       // Pin Bar Wick Ratio (min % of total length)
input double   InpMarubozuBodyRatio = 0.80;       // Marubozu Body Ratio (min % of total length)
input double   InpMaxCandleATRMult  = 2.5;        // Max Candle Size vs ATR Filter

input group "--- Risk & Exit Parameters ---"
input int      InpAtrPeriod         = 21;         // ATR Period for SL Buffer
input double   InpAtrMultiplier     = 0.20;       // ATR SL Buffer Multiplier
input double   InpRiskRewardRatio   = 2.0;        // Take Profit Risk-to-Reward Ratio

//--- Global Variables
CTrade         m_trade;
int            m_atrHandle = INVALID_HANDLE;
datetime       m_lastBarTime = 0;

// Structure State Tracking
double         m_htfResistance = 0.0;
double         m_htfSupport    = 0.0;
double         m_h1SwingHigh   = 0.0;
double         m_h1SwingLow    = 0.0;
bool           m_bosBullish    = false;
bool           m_bosBearish    = false;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
  {
   m_trade.SetExpertMagicNumber(InpMagicNumber);
   
   // Initialize ATR Indicator
   m_atrHandle = iATR(_Symbol, InpLTF, InpAtrPeriod);
   if(m_atrHandle == INVALID_HANDLE)
     {
      Print("Error creating ATR handle.");
      return(INIT_FAILED);
     }

   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   if(m_atrHandle != INVALID_HANDLE)
      IndicatorRelease(m_atrHandle);
  }

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
  {
  //Show Equity and Balance
   Comment ( StringFormat ( "Equity is %.2f and Balance is %.2f", AccountInfoDouble (ACCOUNT_EQUITY), AccountInfoDouble(ACCOUNT_BALANCE)));  
   // Check for new H1 bar open to prevent duplicate execution within the same candle
   datetime currentBarTime = iTime(_Symbol, InpLTF, 0);
   if(currentBarTime == m_lastBarTime) return;

   // Ensure bar context is synchronized
   if(iBars(_Symbol, InpLTF) < 100) return;

   // 1. Check if a position with this Magic Number is already open
   if(HasOpenPosition()) return;

   // 2. Update Market Structures
   UpdateHTFStructure();
   UpdateH1Structure();

   // 3. Execution logic runs on bar open (checking index 1 - completed candle)
   m_lastBarTime = currentBarTime;

   // 4. Process Trading Signals
   CheckForBuySetup();
   CheckForSellSetup();
  }

//+------------------------------------------------------------------+
//| Check if position already exists for this EA                     |
//+------------------------------------------------------------------+
bool HasOpenPosition()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      if(PositionGetSymbol(i) == _Symbol && PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
         return true;
     }
   return false;
  }

//+------------------------------------------------------------------+
//| Higher Timeframe Context Identification                          |
//+------------------------------------------------------------------+
void UpdateHTFStructure()
  {
   int highestIdx = iHighest(_Symbol, InpHTF, MODE_HIGH, 50, 1);
   int lowestIdx  = iLowest(_Symbol, InpHTF, MODE_LOW, 50, 1);

   if(highestIdx > 0 && lowestIdx > 0)
     {
      m_htfResistance = iHigh(_Symbol, InpHTF, highestIdx);
      m_htfSupport    = iLow(_Symbol, InpHTF, lowestIdx);
     }
  }

//+------------------------------------------------------------------+
//| H1 Structure & BOS Identification                               |
//+------------------------------------------------------------------+
void UpdateH1Structure()
  {
   int swingHighIdx = -1;
   int swingLowIdx  = -1;

   // Identify Swing High
   for(int i = InpSwingRight + 1; i < 50; i++)
     {
      bool isHigh = true;
      double candidateHigh = iHigh(_Symbol, InpLTF, i);

      for(int j = 1; j <= InpSwingLeft; j++)
         if(iHigh(_Symbol, InpLTF, i + j) >= candidateHigh) { isHigh = false; break; }
      for(int j = 1; j <= InpSwingRight; j++)
         if(iHigh(_Symbol, InpLTF, i - j) >= candidateHigh) { isHigh = false; break; }

      if(isHigh) { swingHighIdx = i; break; }
     }

   // Identify Swing Low
   for(int i = InpSwingRight + 1; i < 50; i++)
     {
      bool isLow = true;
      double candidateLow = iLow(_Symbol, InpLTF, i);

      for(int j = 1; j <= InpSwingLeft; j++)
         if(iLow(_Symbol, InpLTF, i + j) <= candidateLow) { isLow = false; break; }
      for(int j = 1; j <= InpSwingRight; j++)
         if(iLow(_Symbol, InpLTF, i - j) <= candidateLow) { isLow = false; break; }

      if(isLow) { swingLowIdx = i; break; }
     }

   if(swingHighIdx != -1) m_h1SwingHigh = iHigh(_Symbol, InpLTF, swingHighIdx);
   if(swingLowIdx != -1)  m_h1SwingLow  = iLow(_Symbol, InpLTF, swingLowIdx);

   // Check BOS (Candle Close beyond swing level)
   double close1 = iClose(_Symbol, InpLTF, 1);
   if(m_h1SwingHigh > 0 && close1 > m_h1SwingHigh)
      m_bosBullish = true;
   else if(close1 < m_h1SwingLow)
      m_bosBullish = false;

   if(m_h1SwingLow > 0 && close1 < m_h1SwingLow)
      m_bosBearish = true;
   else if(close1 > m_h1SwingHigh)
      m_bosBearish = false;
  }

//+------------------------------------------------------------------+
//| Check BUY Signal Conditions                                      |
//+------------------------------------------------------------------+
void CheckForBuySetup()
  {
   if(!m_bosBullish || m_h1SwingHigh == 0) return;

   // Retest Check: Price returned near broken resistance level
   double low1 = iLow(_Symbol, InpLTF, 1);
   double tolerance = InpRetestTolerance * _Point;
   if(low1 > (m_h1SwingHigh + tolerance)) return; // Has not pulled back close enough

   // Rejection Confirmation Check on Candle 1
   if(!IsBullishRejection(1)) return;

   // ATR Filter check for excess candle size
   double atr = GetATR(1);
   double candleSize = iHigh(_Symbol, InpLTF, 1) - iLow(_Symbol, InpLTF, 1);
   if(atr > 0 && candleSize > (InpMaxCandleATRMult * atr)) return;

   // Calculate Stop Loss & Take Profit
   double entryPrice = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double slPrice    = iLow(_Symbol, InpLTF, 1) - (atr * InpAtrMultiplier);
   double riskDist   = entryPrice - slPrice;

   if(riskDist <= 0) return;

   double tpPrice = entryPrice + (riskDist * InpRiskRewardRatio);
   double lotSize = CalculateLotSize(riskDist);

   // Execute Buy
   m_trade.Buy(lotSize, _Symbol, entryPrice, slPrice, tpPrice, "BOS Retest Buy");
  }

//+------------------------------------------------------------------+
//| Check SELL Signal Conditions                                     |
//+------------------------------------------------------------------+
void CheckForSellSetup()
  {
   if(!m_bosBearish || m_h1SwingLow == 0) return;

   // Retest Check: Price returned near broken support level
   double high1 = iHigh(_Symbol, InpLTF, 1);
   double tolerance = InpRetestTolerance * _Point;
   if(high1 < (m_h1SwingLow - tolerance)) return; // Has not pulled back close enough

   // Rejection Confirmation Check on Candle 1
   if(!IsBearishRejection(1)) return;

   // ATR Filter check for excess candle size
   double atr = GetATR(1);
   double candleSize = iHigh(_Symbol, InpLTF, 1) - iLow(_Symbol, InpLTF, 1);
   if(atr > 0 && candleSize > (InpMaxCandleATRMult * atr)) return;

   // Calculate Stop Loss & Take Profit
   double entryPrice = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double slPrice    = iHigh(_Symbol, InpLTF, 1) + (atr * InpAtrMultiplier);
   double riskDist   = slPrice - entryPrice;

   if(riskDist <= 0) return;

   double tpPrice = entryPrice - (riskDist * InpRiskRewardRatio);
   double lotSize = CalculateLotSize(riskDist);

   // Execute Sell
   m_trade.Sell(lotSize, _Symbol, entryPrice, slPrice, tpPrice, "BOS Retest Sell");
  }

//+------------------------------------------------------------------+
//| Bullish Rejection Pattern Recognition                            |
//+------------------------------------------------------------------+
bool IsBullishRejection(int shift)
  {
   double openP  = iOpen(_Symbol, InpLTF, shift);
   double closeP = iClose(_Symbol, InpLTF, shift);
   double highP  = iHigh(_Symbol, InpLTF, shift);
   double lowP   = iLow(_Symbol, InpLTF, shift);

   double totalRange = highP - lowP;
   if(totalRange <= 0) return false;

   double bodyRange  = MathAbs(closeP - openP);
   double lowerWick  = MathMin(openP, closeP) - lowP;

   // 1. Bullish Pin Bar (Long lower wick)
   bool isPinBar = (lowerWick / totalRange) >= InpPinBarWickRatio;

   // 2. Bullish Engulfing
   double prevOpen  = iOpen(_Symbol, InpLTF, shift + 1);
   double prevClose = iClose(_Symbol, InpLTF, shift + 1);
   bool isEngulfing = (prevClose < prevOpen) && (closeP > openP) && (closeP >= prevOpen) && (openP <= prevClose);

   // 3. Bullish Marubozu
   bool isMarubozu = (closeP > openP) && ((bodyRange / totalRange) >= InpMarubozuBodyRatio);

   return (isPinBar || isEngulfing || isMarubozu);
  }

//+------------------------------------------------------------------+
//| Bearish Rejection Pattern Recognition                            |
//+------------------------------------------------------------------+
bool IsBearishRejection(int shift)
  {
   double openP  = iOpen(_Symbol, InpLTF, shift);
   double closeP = iClose(_Symbol, InpLTF, shift);
   double highP  = iHigh(_Symbol, InpLTF, shift);
   double lowP   = iLow(_Symbol, InpLTF, shift);

   double totalRange = highP - lowP;
   if(totalRange <= 0) return false;

   double bodyRange  = MathAbs(closeP - openP);
   double upperWick  = highP - MathMax(openP, closeP);

   // 1. Bearish Pin Bar (Long upper wick)
   bool isPinBar = (upperWick / totalRange) >= InpPinBarWickRatio;

   // 2. Bearish Engulfing
   double prevOpen  = iOpen(_Symbol, InpLTF, shift + 1);
   double prevClose = iClose(_Symbol, InpLTF, shift + 1);
   bool isEngulfing = (prevClose > prevOpen) && (closeP < openP) && (closeP <= prevOpen) && (openP >= prevClose);

   // 3. Bearish Marubozu
   bool isMarubozu = (closeP < openP) && ((bodyRange / totalRange) >= InpMarubozuBodyRatio);

   return (isPinBar || isEngulfing || isMarubozu);
  }

//+------------------------------------------------------------------+
//| Get ATR Value Helper Function                                    |
//+------------------------------------------------------------------+
double GetATR(int shift)
  {
   double atrBuf[];
   ArraySetAsSeries(atrBuf, true);
   if(CopyBuffer(m_atrHandle, 0, shift, 1, atrBuf) > 0)
      return atrBuf[0];
   return 0.0;
  }

//+------------------------------------------------------------------+
//| Dynamic Position Size / Money Management Calculation              |
//+------------------------------------------------------------------+
double CalculateLotSize(double slDistanceInPrice)
  {
   if(InpFixedLot > 0.0) return InpFixedLot;

   double balance     = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskAmount  = balance * (InpRiskPercent / 100.0);
   double tickSize    = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tickValue   = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double minLot      = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot      = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lotStep     = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

   if(tickSize == 0 || tickValue == 0) return minLot;

   double lossPerLot  = (slDistanceInPrice / tickSize) * tickValue;
   if(lossPerLot <= 0) return minLot;

   double calculatedLot = riskAmount / lossPerLot;
   calculatedLot = MathFloor(calculatedLot / lotStep) * lotStep;

   return MathMin(maxLot, MathMax(minLot, calculatedLot));
  }
//+------------------------------------------------------------------+