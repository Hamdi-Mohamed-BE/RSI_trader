// Frozen v0.1 signal definitions. Every argument comes from CLOSED H1 candles.
int MomentumSignal(double c1,double c2,double e20_1,double e20_2,double trend50,double trend200,double strength,double plus,double minus)
{
 if(strength<25.0)return 0;
 if(trend50>trend200 && c1>trend50 && plus>minus && c2<=e20_2 && c1>e20_1)return 1;
 if(trend50<trend200 && c1<trend50 && minus>plus && c2>=e20_2 && c1<e20_1)return -1;
 return 0;
}
int ChangeSignal(double f1,double f2,double s1,double s2,double oscillator)
{
 if(f2<=s2 && f1>s1 && oscillator>50.0)return 1;
 if(f2>=s2 && f1<s1 && oscillator<50.0)return -1;
 return 0;
}
int BreakoutSignal(double c,double hi20,double lo20,double tr,double atr1,double atr2)
{
 if(atr2<=0 || tr<1.5*atr2 || atr1<=atr2)return 0;
 if(c>hi20)return 1;
 if(c<lo20)return -1;
 return 0;
}
double RoundedLots(double raw,double minlot,double maxlot,double step)
{
 if(raw<=0 || minlot<=0 || maxlot<minlot || step<=0)return 0;
 double v=MathMax(minlot,MathCeil(raw/step-1e-9)*step);
 double top=MathFloor(maxlot/step+1e-9)*step;
 return NormalizeDouble(MathMin(v,top),8);
}
bool SignalSelfTest()
{
 if(MomentumSignal(110,99,105,100,106,101,25,30,10)!=1)return false;
 if(MomentumSignal(90,101,95,100,94,99,25,10,30)!=-1)return false;
 if(MomentumSignal(110,99,105,100,106,101,24.99,30,10)!=0)return false;
 if(MomentumSignal(110,101,105,100,106,101,25,30,10)!=0)return false;
 if(ChangeSignal(102,99,101,100,51)!=1)return false;
 if(ChangeSignal(98,101,99,100,49)!=-1)return false;
 if(ChangeSignal(102,99,101,100,50)!=0)return false;
 if(BreakoutSignal(111,110,90,15,11,10)!=1)return false;
 if(BreakoutSignal(89,110,90,15,11,10)!=-1)return false;
 if(BreakoutSignal(110,110,90,15,11,10)!=0)return false;
 if(BreakoutSignal(111,110,90,14.99,11,10)!=0)return false;
 if(BreakoutSignal(111,110,90,15,10,10)!=0)return false;
 if(MathAbs(RoundedLots(.005,.01,200,.01)-.01)>1e-8)return false;
 if(MathAbs(RoundedLots(.014,.01,200,.01)-.02)>1e-8)return false;
 if(MathAbs(RoundedLots(.02,.01,200,.01)-.02)>1e-8)return false;
 if(MathAbs(RoundedLots(201,.01,200,.01)-200)>1e-8)return false;
 return true;
}
