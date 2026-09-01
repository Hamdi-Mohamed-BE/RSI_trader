#ifndef HAMA_PER_EA_SAFE_REGIME_FILTER_MQH
#define HAMA_PER_EA_SAFE_REGIME_FILTER_MQH

// This completed-D1 gate is local to this EA chart. The newest completed
// daily state is forecast from older transitions only, avoiding lookahead.
input group "Per-EA Safe Mode - completed D1 Markov gate"
input bool   InpUseMarkovRegimeFilter=false;
input int    InpMarkovReturnWindow=40;
input double InpMarkovThreshold=0.05;
input double InpMarkovSignalGate=0.05;
input int    InpMarkovMinLabels=252;
input int    InpMarkovHistoryBars=2600;

int HAMA_SafeRegimeStateAt(double &closes[],const int index)
{
   double older=closes[index+InpMarkovReturnWindow];
   if(older<=0.0) return 1;
   double rolling_return=closes[index]/older-1.0;
   if(rolling_return>InpMarkovThreshold) return 2;
   if(rolling_return<-InpMarkovThreshold) return 0;
   return 1;
}

bool HAMA_SafeRegimeAllowsDirection(const int direction)
{
   if(!InpUseMarkovRegimeFilter) return true;
   int available=Bars(_Symbol,PERIOD_D1)-1;
   int requested=MathMin(InpMarkovHistoryBars,available);
   if(requested<=InpMarkovReturnWindow+InpMarkovMinLabels) return false;

   double closes[];
   ArraySetAsSeries(closes,true);
   int copied=CopyClose(_Symbol,PERIOD_D1,1,requested,closes);
   int labels=copied-InpMarkovReturnWindow;
   if(labels<=InpMarkovMinLabels) return false;

   double counts[3][3];
   for(int row=0;row<3;row++)
      for(int col=0;col<3;col++) counts[row][col]=0.0;

   int oldest=labels-1;
   for(int newer=oldest-1;newer>=1;newer--)
   {
      int from=HAMA_SafeRegimeStateAt(closes,newer+1);
      int to=HAMA_SafeRegimeStateAt(closes,newer);
      counts[from][to]+=1.0;
   }

   int state=HAMA_SafeRegimeStateAt(closes,0);
   double total=counts[state][0]+counts[state][1]+counts[state][2];
   if(total<=0.0) return false;
   double signal=(counts[state][2]-counts[state][0])/total;
   return (direction>0 ? signal>InpMarkovSignalGate : signal<-InpMarkovSignalGate);
}

#endif
