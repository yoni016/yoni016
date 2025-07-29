//+------------------------------------------------------------------+
//|                                           SpreadSwapAnalyzer.mq4 |
//|                                         Spread vs Swap Analyzer  |
//|                                                                  |
//+------------------------------------------------------------------+
#property copyright "Copyright 2024"
#property link      ""
#property version   "1.00"
#property strict

//+------------------------------------------------------------------+
//| Script program start function                                    |
//+------------------------------------------------------------------+
void OnStart()
{
    // רשימת הזוגות המומלצים
    string profitablePairs = "זוגות מטבע רווחיים:\n";
    profitablePairs += "========================\n\n";
    
    int symbolsTotal = SymbolsTotal(true);
    int profitableCount = 0;
    
    // סריקת כל הסימבולים הזמינים
    for(int i = 0; i < symbolsTotal; i++)
    {
        string symbol = SymbolName(i, true);
        
        // וידוא שהסימבול נסחר
        if(!MarketInfo(symbol, MODE_TRADEALLOWED))
            continue;
            
        // חישוב נתוני הסימבול
        double spread = MarketInfo(symbol, MODE_SPREAD);
        double tickValue = MarketInfo(symbol, MODE_TICKVALUE);
        double swapLong = MarketInfo(symbol, MODE_SWAPLONG);
        double swapShort = MarketInfo(symbol, MODE_SWAPSHORT);
        double contractSize = MarketInfo(symbol, MODE_LOTSIZE);
        
        // חישוב עלות הספרד בדולרים עבור לוט 1
        double spreadCostUSD = spread * tickValue;
        
        // בחירת הריבית החיובית (אם קיימת)
        double positiveSwap = 0;
        string swapType = "";
        
        if(swapLong > 0)
        {
            positiveSwap = swapLong;
            swapType = "LONG (קניה)";
        }
        else if(swapShort > 0)
        {
            positiveSwap = swapShort;
            swapType = "SHORT (מכירה)";
        }
        
        // המשך רק אם יש ריבית חיובית
        if(positiveSwap <= 0)
            continue;
            
        // חישוב הריבית בדולרים
        // הסוואפ ב-MT4 יכול להיות בנקודות או באחוזים
        int swapMode = (int)MarketInfo(symbol, MODE_SWAPTYPE);
        double swapValueUSD = 0;
        
        switch(swapMode)
        {
            case 0: // In points
                swapValueUSD = positiveSwap * tickValue;
                break;
                
            case 1: // In base currency
                swapValueUSD = positiveSwap;
                break;
                
            case 2: // By interest
                swapValueUSD = contractSize * MarketInfo(symbol, MODE_BID) * positiveSwap / 100 / 360;
                break;
                
            case 3: // In margin currency
                swapValueUSD = positiveSwap;
                break;
        }
        
        // בדיקה האם עלות הספרד קטנה פי 2 מהחזר הריבית
        if(spreadCostUSD < (swapValueUSD / 2.0) && swapValueUSD > 0)
        {
            profitableCount++;
            
            // הוספת הזוג לרשימה
            profitablePairs += StringFormat("%d. %s\n", profitableCount, symbol);
            profitablePairs += StringFormat("   כיוון: %s\n", swapType);
            profitablePairs += StringFormat("   עלות ספרד: $%.2f\n", spreadCostUSD);
            profitablePairs += StringFormat("   ריבית יומית: $%.2f\n", swapValueUSD);
            profitablePairs += StringFormat("   יחס ריבית/ספרד: %.2f\n", swapValueUSD / spreadCostUSD);
            profitablePairs += "\n";
        }
    }
    
    // הצגת התוצאות
    if(profitableCount > 0)
    {
        profitablePairs += StringFormat("\nסה\"כ נמצאו %d זוגות רווחיים", profitableCount);
        
        // הדפסה לחלון המומחים
        Print(profitablePairs);
        
        // הצגה בהודעת התראה
        Alert(profitablePairs);
        
        // שמירה לקובץ
        SaveToFile(profitablePairs);
    }
    else
    {
        string message = "לא נמצאו זוגות מטבע שעומדים בקריטריונים";
        Print(message);
        Alert(message);
    }
}

//+------------------------------------------------------------------+
//| שמירת התוצאות לקובץ                                            |
//+------------------------------------------------------------------+
void SaveToFile(string content)
{
    string filename = "SpreadSwapAnalysis_" + TimeToString(TimeCurrent(), TIME_DATE) + ".txt";
    int fileHandle = FileOpen(filename, FILE_WRITE | FILE_TXT);
    
    if(fileHandle != INVALID_HANDLE)
    {
        FileWriteString(fileHandle, content);
        FileClose(fileHandle);
        Print("התוצאות נשמרו לקובץ: ", filename);
    }
    else
    {
        Print("שגיאה בפתיחת קובץ לכתיבה");
    }
}

//+------------------------------------------------------------------+
//| פונקציה נוספת לחישוב מפורט עבור זוג בודד                      |
//+------------------------------------------------------------------+
void AnalyzeSinglePair(string symbol)
{
    double spread = MarketInfo(symbol, MODE_SPREAD);
    double tickValue = MarketInfo(symbol, MODE_TICKVALUE);
    double swapLong = MarketInfo(symbol, MODE_SWAPLONG);
    double swapShort = MarketInfo(symbol, MODE_SWAPSHORT);
    double contractSize = MarketInfo(symbol, MODE_LOTSIZE);
    double bid = MarketInfo(symbol, MODE_BID);
    double ask = MarketInfo(symbol, MODE_ASK);
    
    // חישוב עלות הספרד
    double spreadCostUSD = spread * tickValue;
    
    // חישוב הסוואפ לכל כיוון
    int swapMode = (int)MarketInfo(symbol, MODE_SWAPTYPE);
    double swapLongUSD = CalculateSwapInUSD(swapLong, swapMode, tickValue, contractSize, bid);
    double swapShortUSD = CalculateSwapInUSD(swapShort, swapMode, tickValue, contractSize, bid);
    
    // הדפסת הניתוח המפורט
    string analysis = StringFormat("\nניתוח מפורט עבור %s:\n", symbol);
    analysis += "=======================\n";
    analysis += StringFormat("Bid: %.5f | Ask: %.5f\n", bid, ask);
    analysis += StringFormat("Spread: %.0f points = $%.2f\n", spread, spreadCostUSD);
    analysis += StringFormat("Swap Long: %.2f = $%.2f per day\n", swapLong, swapLongUSD);
    analysis += StringFormat("Swap Short: %.2f = $%.2f per day\n", swapShort, swapShortUSD);
    
    if(swapLongUSD > 0 && spreadCostUSD < swapLongUSD / 2.0)
    {
        analysis += "\n✓ קניה רווחית! הספרד קטן מחצי מהריבית היומית";
    }
    else if(swapShortUSD > 0 && spreadCostUSD < swapShortUSD / 2.0)
    {
        analysis += "\n✓ מכירה רווחית! הספרד קטן מחצי מהריבית היומית";
    }
    else
    {
        analysis += "\n✗ לא רווחי - הספרד גבוה מדי ביחס לריבית";
    }
    
    Print(analysis);
}

//+------------------------------------------------------------------+
//| חישוב הסוואפ בדולרים לפי סוג החישוב                           |
//+------------------------------------------------------------------+
double CalculateSwapInUSD(double swapValue, int swapMode, double tickValue, double contractSize, double price)
{
    switch(swapMode)
    {
        case 0: // In points
            return swapValue * tickValue;
            
        case 1: // In base currency
            return swapValue;
            
        case 2: // By interest
            return contractSize * price * swapValue / 100 / 360;
            
        case 3: // In margin currency
            return swapValue;
            
        default:
            return 0;
    }
}
//+------------------------------------------------------------------+