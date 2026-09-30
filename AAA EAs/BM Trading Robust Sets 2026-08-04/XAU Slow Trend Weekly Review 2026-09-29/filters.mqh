input double ResearchADXMinimum=0.0;
input bool ResearchDI=false;
input bool ResearchADXRising=false;
input int ResearchExitCooldownHours=0;
input bool ResearchFreshSignal=false;
int researchADX=INVALID_HANDLE;
datetime researchExitTime=0;
int researchBlockedSide=0;
ulong researchPositionID=0;
int researchPositionSide=0;

bool ResearchFilter(const int side)
{
   if(ResearchExitCooldownHours>0 && researchExitTime>0 && TimeCurrent()-researchExitTime<ResearchExitCooldownHours*3600) return false;
   if(ResearchFreshSignal && researchBlockedSide==side) return false;
   if(ResearchADXMinimum==0.0 && !ResearchDI && !ResearchADXRising) return true;
   double adx[1],plus[1],minus[1],previous[1];
   if(CopyBuffer(researchADX,0,1,1,adx)!=1 || CopyBuffer(researchADX,1,1,1,plus)!=1 || CopyBuffer(researchADX,2,1,1,minus)!=1) return false;
   if(!MathIsValidNumber(adx[0]) || !MathIsValidNumber(plus[0]) || !MathIsValidNumber(minus[0])) return false;
   if(adx[0]<ResearchADXMinimum) return false;
   if(ResearchDI && ((side>0 && plus[0]<=minus[0]) || (side<0 && minus[0]<=plus[0]))) return false;
   if(ResearchADXRising && (CopyBuffer(researchADX,0,2,1,previous)!=1 || adx[0]<=previous[0])) return false;
   return true;
}

void ResearchObserve(const int signal)
{
   if(researchBlockedSide!=0 && signal!=researchBlockedSide) researchBlockedSide=0;
   ulong ticket;int side;double entry,sl,tp;datetime opened;
   if(OurPosition(ticket,side,entry,sl,tp,opened))
   {
      researchPositionID=(ulong)PositionGetInteger(POSITION_IDENTIFIER);
      researchPositionSide=side;
   }
   else if(researchPositionID!=0)
   {
      researchExitTime=TimeCurrent();
      researchBlockedSide=researchPositionSide;
      researchPositionID=0;
      // A differing signal at the exit is itself a fresh state.
      if(signal!=researchBlockedSide) researchBlockedSide=0;
   }
}
