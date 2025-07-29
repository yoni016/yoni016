//+------------------------------------------------------------------+
//|                                          TripleSwapSettings.mqh  |
//|                              הגדרות ריבית משולשת לברוקרים      |
//+------------------------------------------------------------------+

// הגדרות ברירת מחדל לימי ריבית משולשת
// 0=ראשון, 1=שני, 2=שלישי, 3=רביעי, 4=חמישי, 5=שישי, 6=שבת

// רוב הברוקרים - צמדי מט"ח ומתכות
#define DEFAULT_FOREX_TRIPLE_DAY 3  // רביעי

// מדדים ומניות
#define DEFAULT_INDEX_TRIPLE_DAY 4  // חמישי

// ברוקרים ספציפיים - ניתן להתאים לפי הצורך
// דוגמאות:

// IC Markets
#define ICMARKETS_FOREX_TRIPLE_DAY 3
#define ICMARKETS_INDEX_TRIPLE_DAY 5

// XM
#define XM_FOREX_TRIPLE_DAY 3
#define XM_INDEX_TRIPLE_DAY 4

// Exness
#define EXNESS_FOREX_TRIPLE_DAY 3
#define EXNESS_INDEX_TRIPLE_DAY 5

// פונקציה לקבלת יום הריבית המשולשת לפי ברוקר
int GetBrokerTripleSwapDay(string symbol, string brokerName = "")
{
    // אם לא צוין ברוקר, השתמש בברירת מחדל
    if(brokerName == "")
        brokerName = AccountCompany();
    
    // המר לאותיות גדולות
    StringToUpper(brokerName);
    
    bool isForexOrMetal = IsForexOrMetal(symbol);
    
    // בדיקה לפי שם הברוקר
    if(StringFind(brokerName, "ICMARKETS") >= 0 || StringFind(brokerName, "IC MARKETS") >= 0)
    {
        return isForexOrMetal ? ICMARKETS_FOREX_TRIPLE_DAY : ICMARKETS_INDEX_TRIPLE_DAY;
    }
    else if(StringFind(brokerName, "XM") >= 0)
    {
        return isForexOrMetal ? XM_FOREX_TRIPLE_DAY : XM_INDEX_TRIPLE_DAY;
    }
    else if(StringFind(brokerName, "EXNESS") >= 0)
    {
        return isForexOrMetal ? EXNESS_FOREX_TRIPLE_DAY : EXNESS_INDEX_TRIPLE_DAY;
    }
    
    // ברירת מחדל
    return isForexOrMetal ? DEFAULT_FOREX_TRIPLE_DAY : DEFAULT_INDEX_TRIPLE_DAY;
}

// פונקציה לבדיקה אם לסימבול יש ריבית משולשת
bool HasTripleSwap(string symbol)
{
    // רוב הסימבולים כן מקבלים ריבית משולשת
    // ניתן להוסיף חריגים כאן אם יש
    
    // דוגמה: קריפטו לפעמים לא מקבל ריבית משולשת
    if(StringFind(symbol, "BTC") >= 0 || StringFind(symbol, "ETH") >= 0 || 
       StringFind(symbol, "CRYPTO") >= 0)
    {
        return false;
    }
    
    return true;
}
//+------------------------------------------------------------------+