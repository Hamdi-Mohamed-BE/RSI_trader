#ifndef CALYX_AVA_FUTURES_PORTFOLIO_GUARD_MQH
#define CALYX_AVA_FUTURES_PORTFOLIO_GUARD_MQH

// Ava's futures demo account is netting. These helpers stop separate Calyx EAs
// on the same contract from merging into, or managing, one shared position.
bool AvaPortfolioIsNetting()
  {
   return AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING;
  }

string AvaPortfolioKey(const string symbol,const string suffix)
  {
   return "CALYX_AVA_"+IntegerToString((long)AccountInfoInteger(ACCOUNT_LOGIN))+"_"+
          StringSubstr(symbol,0,18)+"_"+suffix;
  }

// ownership: 0=any, 1=this EA, -1=another EA.
bool AvaPortfolioHasExposure(const string symbol,const long magic,const int ownership)
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || PositionGetString(POSITION_SYMBOL)!=symbol) continue;
      long found=(long)PositionGetInteger(POSITION_MAGIC);
      if(ownership==0 || (ownership>0 && found==magic) || (ownership<0 && found!=magic)) return true;
     }
   for(int i=OrdersTotal()-1;i>=0;i--)
     {
      ulong ticket=OrderGetTicket(i);
      if(ticket==0 || OrderGetString(ORDER_SYMBOL)!=symbol) continue;
      long found=(long)OrderGetInteger(ORDER_MAGIC);
      if(ownership==0 || (ownership>0 && found==magic) || (ownership<0 && found!=magic)) return true;
     }
   return false;
  }

bool AvaPortfolioTryAcquire(const string symbol,const long magic)
  {
   if(!AvaPortfolioIsNetting()) return true;
   if(AvaPortfolioHasExposure(symbol,magic,-1)) return false;
   if(AvaPortfolioHasExposure(symbol,magic,1)) return true;

   string owner_key=AvaPortfolioKey(symbol,"OWNER");
   string time_key=AvaPortfolioKey(symbol,"TIME");
   if(!GlobalVariableCheck(owner_key)) GlobalVariableSet(owner_key,0.0);
   if(!GlobalVariableCheck(time_key)) GlobalVariableSet(time_key,0.0);
   double owner=GlobalVariableGet(owner_key);
   datetime stamp=(datetime)GlobalVariableGet(time_key);
   datetime now=TimeLocal();
   if((long)owner==magic)
     {
      GlobalVariableSet(time_key,(double)now);
      return true;
     }
   if(owner!=0.0)
     {
      if(AvaPortfolioHasExposure(symbol,magic,0) || now-stamp<15) return false;
     }
   if(!GlobalVariableSetOnCondition(owner_key,(double)magic,owner)) return false;
   GlobalVariableSet(time_key,(double)now);
   return true;
  }

void AvaPortfolioReleaseIfIdle(const string symbol,const long magic)
  {
   if(!AvaPortfolioIsNetting()) return;
   string owner_key=AvaPortfolioKey(symbol,"OWNER");
   if(!GlobalVariableCheck(owner_key)) return;
   double owner=GlobalVariableGet(owner_key);
   if((long)owner!=magic) return;
   if(AvaPortfolioHasExposure(symbol,magic,0))
     {
      GlobalVariableSet(AvaPortfolioKey(symbol,"TIME"),(double)TimeLocal());
      return;
     }
   GlobalVariableSetOnCondition(owner_key,0.0,owner);
   GlobalVariableSet(AvaPortfolioKey(symbol,"TIME"),0.0);
  }

#endif
