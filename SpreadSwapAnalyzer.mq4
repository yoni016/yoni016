//+------------------------------------------------------------------+
//|                                            SpreadSwapAnalyzer.mq4 |
//|                                   Copyright 2024, Your Company   |
//|                                             https://www.mql5.com |
//+------------------------------------------------------------------+
#property copyright "Copyright 2024, Your Company"
#property link      "https://www.mql5.com"
#property version   "1.00"
#property strict
#property indicator_chart_window

// הגדרת מערכים לאחסון צמדי המטבע
string symbols[] = {
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD",
    "EURJPY", "GBPJPY", "EURGBP", "EURAUD", "EURCHI", "EURCHF", "EURCAD",
    "GBPAUD", "GBPCAD", "GBPCHF", "AUDCAD", "AUDJPY", "CADJPY", "CHFJPY",
    "NZDJPY", "AUDCHF", "AUDNZD", "CADCHF", "NZDCAD", "NZDCHF"
};

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("=== נתוני ספרד וריבית לילה ===");
    AnalyzeSymbols();
    return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| פונקציה לניתוח צמדי המטבע                                        |
//+------------------------------------------------------------------+
void AnalyzeSymbols()
{
    string goodSymbols = "";
    int goodCount = 0;
    
    Print("בודק " + IntegerToString(ArraySize(symbols)) + " צמדי מטבע...");
    Print("----------------------------------------");
    
    for(int i = 0; i < ArraySize(symbols); i++)
    {
        string symbol = symbols[i];
        
        // בדיקה אם הסימבול זמין
        if(!SymbolSelect(symbol, true))
        {
            Print("סימבול " + symbol + " לא זמין");
            continue;
        }
        
        // חישוב ספרד בדולרים
        double spreadUSD = CalculateSpreadInUSD(symbol);
        if(spreadUSD <= 0)
        {
            Print(symbol + ": שגיאה בחישוב ספרד");
            continue;
        }
        
        // קבלת נתוני ריבית לילה
        double swapLong = SymbolInfoDouble(symbol, SYMBOL_SWAP_LONG);
        double swapShort = SymbolInfoDouble(symbol, SYMBOL_SWAP_SHORT);
        
        // חישוב הריבית החיובית בדולרים
        double positiveSwapUSD = CalculatePositiveSwapInUSD(symbol, swapLong, swapShort);
        
        // הדפסת נתונים
        Print(symbol + ":");
        Print("  ספרד: $" + DoubleToString(spreadUSD, 2));
        Print("  ריבית קנייה: " + DoubleToString(swapLong, 2));
        Print("  ריבית מכירה: " + DoubleToString(swapShort, 2));
        Print("  ריבית חיובית בדולרים: $" + DoubleToString(positiveSwapUSD, 2));
        
        // בדיקה אם הספרד קטן פי 2 מהריבית
        if(positiveSwapUSD > 0 && spreadUSD * 2 < positiveSwapUSD)
        {
            Print("  ✓ מתאים! הספרד ($" + DoubleToString(spreadUSD, 2) + 
                  ") קטן פי 2 מהריבית ($" + DoubleToString(positiveSwapUSD, 2) + ")");
            
            if(goodCount > 0) goodSymbols += ", ";
            goodSymbols += symbol;
            goodCount++;
        }
        else
        {
            Print("  ✗ לא מתאים");
        }
        Print("----------------------------------------");
    }
    
    // הדפסת הרשימה הסופית
    Print("");
    Print("=== רשימת צמדי מטבע מתאימים ===");
    if(goodCount > 0)
    {
        Print("נמצאו " + IntegerToString(goodCount) + " צמדי מטבע מתאימים:");
        Print(goodSymbols);
    }
    else
    {
        Print("לא נמצאו צמדי מטבע מתאימים בתנאים הנוכחיים");
    }
}

//+------------------------------------------------------------------+
//| חישוב ספרד בדולרים ללוט 1                                        |
//+------------------------------------------------------------------+
double CalculateSpreadInUSD(string symbol)
{
    double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
    double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
    
    if(ask <= 0 || bid <= 0) return 0;
    
    double spread = ask - bid;
    double tickValue = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
    double tickSize = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
    
    if(tickSize <= 0) return 0;
    
    // חישוב ספרד בדולרים
    double spreadInTicks = spread / tickSize;
    double spreadUSD = spreadInTicks * tickValue;
    
    return spreadUSD;
}

//+------------------------------------------------------------------+
//| חישוב הריבית החיובית בדולרים                                      |
//+------------------------------------------------------------------+
double CalculatePositiveSwapInUSD(string symbol, double swapLong, double swapShort)
{
    double positiveSwap = 0;
    
    // מציאת הריבית החיובית
    if(swapLong > 0 && swapLong > swapShort)
        positiveSwap = swapLong;
    else if(swapShort > 0 && swapShort > swapLong)
        positiveSwap = swapShort;
    else
        return 0; // אין ריבית חיובית
    
    // המרה לדולרים
    double swapUSD = ConvertSwapToUSD(symbol, positiveSwap);
    
    return swapUSD;
}

//+------------------------------------------------------------------+
//| המרת ריבית לדולרים                                               |
//+------------------------------------------------------------------+
double ConvertSwapToUSD(string symbol, double swapValue)
{
    // אם הצמד כבר בדולרים או הדולר הוא המטבע השני
    if(StringSubstr(symbol, 3, 3) == "USD")
    {
        return swapValue;
    }
    
    // אם הדולר הוא המטבע הראשון
    if(StringSubstr(symbol, 0, 3) == "USD")
    {
        double currentPrice = SymbolInfoDouble(symbol, SYMBOL_BID);
        if(currentPrice > 0)
            return swapValue / currentPrice;
    }
    
    // עבור צמדים אחרים - ננסה להמיר דרך USD
    string baseCurrency = StringSubstr(symbol, 0, 3);
    string quoteCurrency = StringSubstr(symbol, 3, 3);
    
    // חיפוש צמד המרה מתאים
    string conversionSymbol = quoteCurrency + "USD";
    if(SymbolSelect(conversionSymbol, false))
    {
        double conversionRate = SymbolInfoDouble(conversionSymbol, SYMBOL_BID);
        if(conversionRate > 0)
            return swapValue * conversionRate;
    }
    
    conversionSymbol = "USD" + quoteCurrency;
    if(SymbolSelect(conversionSymbol, false))
    {
        double conversionRate = SymbolInfoDouble(conversionSymbol, SYMBOL_BID);
        if(conversionRate > 0)
            return swapValue / conversionRate;
    }
    
    // אם לא הצלחנו להמיר, נחזיר את הערך המקורי
    return swapValue;
}

//+------------------------------------------------------------------+
//| Custom indicator iteration function                              |
//+------------------------------------------------------------------+
int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long &tick_volume[],
                const long &volume[],
                const int &spread[])
{
    return(rates_total);
}

//+------------------------------------------------------------------+
//| פונקציה לעדכון ידני של הניתוח                                    |
//+------------------------------------------------------------------+
void UpdateAnalysis()
{
    Print("");
    Print("=== עדכון ניתוח ===");
    Print("זמן: " + TimeToString(TimeCurrent()));
    AnalyzeSymbols();
}

//+------------------------------------------------------------------+
//| טיימר לעדכון תקופתי                                              |
//+------------------------------------------------------------------+
void OnTimer()
{
    UpdateAnalysis();
}

//+------------------------------------------------------------------+
//| פונקציה להתחלה                                                   |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    Print("=== סיום ניתוח ספרד וריבית ===");
}