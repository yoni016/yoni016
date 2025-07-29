//+------------------------------------------------------------------+
//|                                           SpreadSwapAnalyzer.mq4 |
//|                                         Spread vs Swap Analyzer  |
//|                                                                  |
//+------------------------------------------------------------------+
#property copyright "Copyright 2024"
#property link      ""
#property version   "1.00"
#property strict

#include "TripleSwapSettings.mqh"

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
        double swapValueUSD = CalculateSwapInUSD(positiveSwap, swapMode, tickValue, contractSize, MarketInfo(symbol, MODE_BID), symbol);
        
        // בדיקה האם עלות הספרד קטנה פי 2 מהחזר הריבית
        if(spreadCostUSD < (swapValueUSD / 2.0) && swapValueUSD > 0)
        {
            profitableCount++;
            
            // הוספת הזוג לרשימה
            profitablePairs += StringFormat("%d. %s\n", profitableCount, symbol);
            profitablePairs += StringFormat("   כיוון: %s\n", swapType);
            profitablePairs += StringFormat("   עלות ספרד: $%.2f\n", spreadCostUSD);
            profitablePairs += StringFormat("   ריבית יומית ממוצעת: $%.2f\n", swapValueUSD);
            
            // חישוב הריבית לפני הממוצע (ריבית רגילה)
            double dailySwapBeforeAvg = swapValueUSD * 7.0 / 8.0; // חישוב הפוך מהממוצע
            int tripleDay = GetTripleSwapDay(symbol);
            string dayName = GetDayName(tripleDay);
            
            profitablePairs += StringFormat("   ריבית ביום רגיל: $%.2f\n", dailySwapBeforeAvg);
            profitablePairs += StringFormat("   ריבית ב%s (x3): $%.2f\n", dayName, dailySwapBeforeAvg * 3);
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
    double swapLongUSD = CalculateSwapInUSD(swapLong, swapMode, tickValue, contractSize, bid, symbol);
    double swapShortUSD = CalculateSwapInUSD(swapShort, swapMode, tickValue, contractSize, bid, symbol);
    
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
double CalculateSwapInUSD(double swapValue, int swapMode, double tickValue, double contractSize, double price, string symbol)
{
    double baseSwapUSD = 0;
    
    switch(swapMode)
    {
        case 0: // In points
            baseSwapUSD = swapValue * tickValue;
            break;
            
        case 1: // In base currency
            // הריבית ניתנת במטבע הבסיס, צריך להמיר ל-USD
            // לדוגמה: ב-CADJPY הריבית תהיה ב-CAD וצריך להמיר לדולר
            string baseCurrency = StringSubstr(symbol, 0, 3);
            
            // אם מטבע הבסיס הוא כבר USD, אין צורך בהמרה
            if(baseCurrency == "USD")
                baseSwapUSD = swapValue;
            else
            {
                // אחרת, נמיר למטבע החשבון (בדרך כלל USD)
                // נחפש את שער ההמרה
                double conversionRate = GetConversionRate(baseCurrency);
                baseSwapUSD = swapValue * conversionRate;
            }
            break;
            
        case 2: // By interest (percentage)
            // חישוב לפי אחוז שנתי
            baseSwapUSD = contractSize * price * swapValue / 100 / 360;
            break;
            
        case 3: // In margin currency
            // הריבית במטבע המרג'ין (בדרך כלל USD)
            baseSwapUSD = swapValue;
            break;
            
        default:
            baseSwapUSD = 0;
    }
    
    // חישוב הממוצע היומי כולל הריבית המשולשת
    return CalculateDailyAverageSwap(baseSwapUSD, symbol);
}

//+------------------------------------------------------------------+
//| חישוב ממוצע יומי של הסוואפ כולל ימים עם ריבית משולשת        |
//+------------------------------------------------------------------+
double CalculateDailyAverageSwap(double dailySwap, string symbol)
{
    // קבלת היום שבו יש ריבית משולשת
    int tripleSwapDay = GetTripleSwapDay(symbol);
    
    if(tripleSwapDay == -1)
    {
        // אין יום עם ריבית משולשת
        return dailySwap;
    }
    
    // חישוב הממוצע השבועי
    // 5 ימים רגילים + יום אחד עם ריבית משולשת (שזה עוד 2 ימים)
    // סה"כ: 5 + 3 = 8 ימי ריבית ב-7 ימים
    double weeklySwap = (5 * dailySwap) + (3 * dailySwap);
    double averageDailySwap = weeklySwap / 7.0;
    
    return averageDailySwap;
}

//+------------------------------------------------------------------+
//| קבלת היום שבו יש ריבית משולשת                                |
//+------------------------------------------------------------------+
int GetTripleSwapDay(string symbol)
{
    // ברוב הברוקרים:
    // צמדי מט"ח ומתכות - רביעי (3)
    // מדדים ומניות - חמישי (4) או שישי (5)
    
    // בדיקה אם זה צמד מט"ח או מתכת
    if(IsForexOrMetal(symbol))
    {
        return 3; // רביעי (0=ראשון, 1=שני, 2=שלישי, 3=רביעי)
    }
    
    // למדדים ומניות - בדרך כלל חמישי
    // ניתן להתאים לפי הברוקר הספציפי
    return 4; // חמישי
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
    
    // אם מטבע הבסיס זהה למטבע החשבון
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
    
    // אם מטבע החשבון הוא USD, נסה למצוא צמדים עם USD
    if(accountCurrency == "USD")
    {
        // חיפוש XXXUSD
        string pairWithUSD = baseCurrency + "USD";
        if(MarketInfo(pairWithUSD, MODE_BID) > 0)
            return MarketInfo(pairWithUSD, MODE_BID);
            
        // חיפוש USDXXX
        string usdPair = "USD" + baseCurrency;
        if(MarketInfo(usdPair, MODE_BID) > 0)
            return 1.0 / MarketInfo(usdPair, MODE_BID);
    }
    
    // אם לא נמצא, החזר 1 (אזהרה: זה לא מדויק)
    Print("אזהרה: לא נמצא שער המרה עבור ", baseCurrency, " ל-", accountCurrency);
    return 1.0;
}
//+------------------------------------------------------------------+