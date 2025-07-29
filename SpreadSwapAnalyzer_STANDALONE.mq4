//+------------------------------------------------------------------+
//|                                           SpreadSwapAnalyzer.mq4 |
//|                                         Spread vs Swap Analyzer  |
//|                                              Standalone Version  |
//+------------------------------------------------------------------+
#property copyright "Copyright 2024"
#property link      ""
#property version   "1.00"
#property strict

// הגדרת קבועים אם חסרים
#ifndef SYMBOL_SWAP_ROLLOVER3DAYS
    #define SYMBOL_SWAP_ROLLOVER3DAYS 40
#endif

//+------------------------------------------------------------------+
//| Script program start function                                    |
//+------------------------------------------------------------------+
void OnStart()
{
    // בדיקת היום הנוכחי
    int currentDay = DayOfWeek();
    string currentDayName = GetDayName(currentDay);
    
    // רשימת הזוגות המומלצים
    string profitablePairs = "זוגות מטבע רווחיים:\n";
    profitablePairs += "========================\n";
    profitablePairs += "היום: " + currentDayName + " (" + TimeToString(TimeCurrent(), TIME_DATE) + ")\n\n";
    
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
        int swapMode = (int)MarketInfo(symbol, MODE_SWAPTYPE);
        double swapValueUSD = CalculateSwapInUSD(positiveSwap, swapMode, tickValue, contractSize, MarketInfo(symbol, MODE_BID), symbol);
        
        // בדיקה אם היום הוא יום ריבית משולשת
        int tripleSwapDay = GetTripleSwapDay(symbol);
        bool isTripleSwapToday = (currentDay == tripleSwapDay);
        
        // אם היום יש ריבית משולשת, נכפיל ב-3
        double actualSwapToday = isTripleSwapToday ? swapValueUSD * 3 : swapValueUSD;
        
        // בדיקה האם עלות הספרד קטנה פי 2 מהחזר הריבית
        if(spreadCostUSD < (actualSwapToday / 2.0) && actualSwapToday > 0)
        {
            profitableCount++;
            
            // הוספת הזוג לרשימה
            profitablePairs += StringFormat("%d. %s\n", profitableCount, symbol);
            profitablePairs += StringFormat("   כיוון: %s\n", swapType);
            profitablePairs += StringFormat("   עלות ספרד: $%.2f\n", spreadCostUSD);
            
            if(isTripleSwapToday)
            {
                profitablePairs += StringFormat("   *** היום ריבית משולשת! ***\n");
                profitablePairs += StringFormat("   ריבית להיום: $%.2f (x3)\n", actualSwapToday);
            }
            else
            {
                profitablePairs += StringFormat("   ריבית יומית רגילה: $%.2f\n", swapValueUSD);
                string dayName = GetDayName(tripleSwapDay);
                profitablePairs += StringFormat("   ריבית ב%s: $%.2f (x3)\n", dayName, swapValueUSD * 3);
            }
            
            // יחס הפוך - כמה דולר ריבית על כל דולר ספרד
            double swapToSpreadRatio = actualSwapToday / spreadCostUSD;
            profitablePairs += StringFormat("   יחס ריבית/ספרד: %.2f (מקבלים $%.2f ריבית על כל $1 ספרד)\n", 
                                          swapToSpreadRatio, swapToSpreadRatio);
            profitablePairs += "\n";
        }
    }
    
    // הצגת התוצאות
    if(profitableCount > 0)
    {
        profitablePairs += StringFormat("\nסה\"כ נמצאו %d זוגות רווחיים", profitableCount);
        
        Print(profitablePairs);
        Alert(profitablePairs);
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
//| חישוב הסוואפ בדולרים לפי סוג החישוב                           |
//+------------------------------------------------------------------+
double CalculateSwapInUSD(double swapValue, int swapMode, double tickValue, double contractSize, double price, string symbol)
{
    double baseSwapUSD = 0;
    
    switch(swapMode)
    {
        case 0: // In points
            baseSwapUSD = swapValue * tickValue;
            break;
            
        case 1: // In base currency
            string baseCurrency = StringSubstr(symbol, 0, 3);
            
            if(baseCurrency == "USD")
                baseSwapUSD = swapValue;
            else
            {
                double conversionRate = GetConversionRate(baseCurrency);
                baseSwapUSD = swapValue * conversionRate;
            }
            break;
            
        case 2: // By interest (percentage)
            baseSwapUSD = contractSize * price * swapValue / 100 / 360;
            break;
            
        case 3: // In margin currency
            baseSwapUSD = swapValue;
            break;
            
        default:
            baseSwapUSD = 0;
    }
    
    return baseSwapUSD;
}

//+------------------------------------------------------------------+
//| קבלת היום שבו יש ריבית משולשת                                |
//+------------------------------------------------------------------+
int GetTripleSwapDay(string symbol)
{
    // שימוש בפקודה המובנית של MT4
    int tripleSwapDay = (int)SymbolInfoInteger(symbol, SYMBOL_SWAP_ROLLOVER3DAYS);
    
    // בדיקה שהערך תקין
    if(tripleSwapDay >= 0 && tripleSwapDay <= 6)
    {
        return tripleSwapDay;
    }
    
    // ברירת מחדל לפי סוג הסימבול
    if(IsForexOrMetal(symbol))
    {
        return 3; // רביעי
    }
    else
    {
        return 4; // חמישי למדדים ומניות
    }
}

//+------------------------------------------------------------------+
//| בדיקה אם הסימבול הוא צמד מט"ח או מתכת                       |
//+------------------------------------------------------------------+
bool IsForexOrMetal(string symbol)
{
    // בדיקה למתכות
    if(StringFind(symbol, "XAU") >= 0 || StringFind(symbol, "XAG") >= 0 || 
       StringFind(symbol, "GOLD") >= 0 || StringFind(symbol, "SILVER") >= 0)
        return true;
    
    // בדיקה לצמדי מט"ח - 6 תווים עם מטבעות מוכרים
    if(StringLen(symbol) == 6)
    {
        string base = StringSubstr(symbol, 0, 3);
        string quote = StringSubstr(symbol, 3, 3);
        string currencies = "EUR,USD,GBP,JPY,CHF,CAD,AUD,NZD,SEK,NOK,DKK,PLN,HUF,CZK,TRY,ZAR,MXN,SGD,HKD,RUB,CNH,INR,KRW,BRL";
        
        if(StringFind(currencies, base) >= 0 && StringFind(currencies, quote) >= 0)
            return true;
    }
    
    return false;
}

//+------------------------------------------------------------------+
//| המרת מספר יום לשם היום                                       |
//+------------------------------------------------------------------+
string GetDayName(int dayNumber)
{
    switch(dayNumber)
    {
        case 0: return "ראשון";
        case 1: return "שני";
        case 2: return "שלישי";
        case 3: return "רביעי";
        case 4: return "חמישי";
        case 5: return "שישי";
        case 6: return "שבת";
        default: return "לא ידוע";
    }
}

//+------------------------------------------------------------------+
//| קבלת שער המרה למטבע החשבון                                    |
//+------------------------------------------------------------------+
double GetConversionRate(string baseCurrency)
{
    string accountCurrency = AccountCurrency();
    
    if(baseCurrency == accountCurrency)
        return 1.0;
    
    // נסה למצוא צמד ישיר
    string directPair = baseCurrency + accountCurrency;
    if(MarketInfo(directPair, MODE_BID) > 0)
        return MarketInfo(directPair, MODE_BID);
    
    // נסה צמד הפוך
    string inversePair = accountCurrency + baseCurrency;
    if(MarketInfo(inversePair, MODE_BID) > 0)
        return 1.0 / MarketInfo(inversePair, MODE_BID);
    
    // אם מטבע החשבון הוא USD
    if(accountCurrency == "USD")
    {
        string pairWithUSD = baseCurrency + "USD";
        if(MarketInfo(pairWithUSD, MODE_BID) > 0)
            return MarketInfo(pairWithUSD, MODE_BID);
            
        string usdPair = "USD" + baseCurrency;
        if(MarketInfo(usdPair, MODE_BID) > 0)
            return 1.0 / MarketInfo(usdPair, MODE_BID);
    }
    
    Print("אזהרה: לא נמצא שער המרה עבור ", baseCurrency, " ל-", accountCurrency);
    return 1.0;
}
//+------------------------------------------------------------------+