//+------------------------------------------------------------------+
//|                                                     SpreadInterestList.mq4 |
//|                                  (c) 2025, Spread-Interest Scanner         |
//|                          Scans MarketWatch for symbols whose overnight   |
//|                          positive swap ≥ 2 × spread cost (per 1 lot).    |
//+------------------------------------------------------------------+
#property strict
#property script_show_inputs

//--- input: only consider symbols with these suffix/prefix filters (optional)
input string IncludePrefix = "";   // Symbols must start with this string (leave blank for all)
input string IncludeSuffix = "";   // Symbols must end   with this string (leave blank for all)

//+------------------------------------------------------------------+
//| Helper: Get positive overnight swap (in USD) for 1 lot            |
//+------------------------------------------------------------------+
double GetPositiveSwap(const string symbol)
  {
   double swapLong  = MarketInfo(symbol,MODE_SWAPLONG);   // in deposit currency, per lot
   double swapShort = MarketInfo(symbol,MODE_SWAPSHORT);  // in deposit currency, per lot

   if(swapLong>0 && swapLong>=swapShort) return swapLong;
   if(swapShort>0)                     return swapShort;
   return 0; // no positive swap
  }

//+------------------------------------------------------------------+
//| Helper: Calculate spread cost (USD) for 1 standard lot            |
//+------------------------------------------------------------------+
double GetSpreadCost(const string symbol)
  {
   int    spreadPoints = (int)MarketInfo(symbol,MODE_SPREAD); // raw spread in points
   double tickValue    = MarketInfo(symbol,MODE_TICKVALUE);   // value of 1 point per lot in USD
   return spreadPoints * tickValue; // cost of spread per 1 lot
  }

//+------------------------------------------------------------------+
//| Script start function                                             |
//+------------------------------------------------------------------+
void OnStart()
  {
   int symbols_total = SymbolsTotal(true); // only MarketWatch symbols

   Print("================ Spread-Interest Scanner =================");
   Print("Symbols where positive swap ≥ 2 × spread cost (per 1 lot):");

   int qualified = 0;

   for(int i=0; i<symbols_total; i++)
     {
      string symbol = SymbolName(i, true);

      // Apply optional prefix/suffix filters
      if(StringLen(IncludePrefix)>0 && StringSubstr(symbol,0,StringLen(IncludePrefix)) != IncludePrefix)
         continue;
      if(StringLen(IncludeSuffix)>0 && StringSubstr(symbol, StringLen(symbol)-StringLen(IncludeSuffix)) != IncludeSuffix)
         continue;

      // Retrieve data
      double spreadCost   = GetSpreadCost(symbol);
      double positiveSwap = GetPositiveSwap(symbol);

      // Check condition: positiveSwap ≥ 2 × spreadCost
      if(positiveSwap >= 2.0*spreadCost && positiveSwap>0)
        {
         qualified++;
         Print(IntegerToString(qualified,3,'0'),": ",symbol,
               " | SpreadCost: $",DoubleToString(spreadCost,2),
               " | PositiveSwap: $",DoubleToString(positiveSwap,2));
        }
     }

   if(qualified==0)
      Print("No symbols meet the criteria.");
   else
      Print("Total qualified symbols: ",qualified);
  }
//+------------------------------------------------------------------+