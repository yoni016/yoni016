//+------------------------------------------------------------------+
//|                                          CheckTripleSwapDay.mq4  |
//|                               בדיקת יום ריבית משולשת           |
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
    string symbol = Symbol();
    
    Print("=== בדיקת יום ריבית משולשת עבור ", symbol, " ===");
    
    // קבלת נתוני הריבית הנוכחיים
    double swapLong = MarketInfo(symbol, MODE_SWAPLONG);
    double swapShort = MarketInfo(symbol, MODE_SWAPSHORT);
    int swapType = (int)MarketInfo(symbol, MODE_SWAPTYPE);
    
    Print("ריבית Long נוכחית: ", swapLong);
    Print("ריבית Short נוכחית: ", swapShort);
    Print("סוג חישוב ריבית: ", GetSwapTypeName(swapType));
    
    // בדיקה באמצעות הפקודה המובנית
    int tripleSwapDay = (int)SymbolInfoInteger(symbol, SYMBOL_SWAP_ROLLOVER3DAYS);
    if(tripleSwapDay >= 0 && tripleSwapDay <= 6)
    {
        Print("\n*** יום ריבית משולשת מהברוקר: ", GetDayNameHebrew(tripleSwapDay), " ***");
    }
    else
    {
        Print("\n*** הברוקר לא מספק מידע על יום ריבית משולשת ***");
    }
    
    // בדיקה ידנית לפי ידע מוקדם על ברוקרים
    string brokerName = AccountCompany();
    Print("\nברוקר: ", brokerName);
    
    // המלצה לפי סוג הסימבול והברוקר
    string recommendation = GetTripleSwapDayRecommendation(symbol, brokerName);
    Print("\nהמלצה: ", recommendation);
    
    // בדיקה לפי הערך הנוכחי
    int currentDay = DayOfWeek();
    string currentDayName = GetDayNameHebrew(currentDay);
    
    Print("\nהיום הוא: ", currentDayName);
    
    // אם הריבית הנוכחית נראית משולשת
    double avgSwap = (MathAbs(swapLong) + MathAbs(swapShort)) / 2.0;
    if(avgSwap > 0)
    {
        // בדרך כלל ריבית משולשת היא בערך פי 3 מהממוצע
        Print("\nטיפ: אם הריבית היום נראית גבוהה במיוחד, כנראה שהיום הוא יום הריבית המשולשת!");
    }
    
    // הצעה לאיסוף נתונים
    Print("\n=== הצעה לאיסוף נתונים ===");
    Print("כדי לזהות בוודאות את יום הריבית המשולשת:");
    Print("1. הרץ סקריפט זה כל יום במשך שבוע");
    Print("2. רשום את ערכי הריבית לכל יום");
    Print("3. היום עם הערך הגבוה ביותר (פי 3 בערך) הוא יום הריבית המשולשת");
}

//+------------------------------------------------------------------+
//| קבלת שם סוג הריבית                                            |
//+------------------------------------------------------------------+
string GetSwapTypeName(int swapType)
{
    switch(swapType)
    {
        case 0: return "בנקודות";
        case 1: return "במטבע הבסיס";
        case 2: return "באחוזים שנתיים";
        case 3: return "במטבע המרג'ין";
        default: return "לא ידוע";
    }
}

//+------------------------------------------------------------------+
//| המלצה ליום ריבית משולשת לפי סימבול וברוקר                    |
//+------------------------------------------------------------------+
string GetTripleSwapDayRecommendation(string symbol, string broker)
{
    // המלצות כלליות
    string baseRecommendation = "";
    
    // בדיקה לפי סוג הסימבול
    if(StringFind(symbol, "XAU") >= 0 || StringFind(symbol, "XAG") >= 0 || 
       StringFind(symbol, "GOLD") >= 0 || StringFind(symbol, "SILVER") >= 0)
    {
        baseRecommendation = "מתכות יקרות - בדרך כלל רביעי";
    }
    else if(StringLen(symbol) == 6 && IsForexPair(symbol))
    {
        baseRecommendation = "צמד מט\"ח - בדרך כלל רביעי";
    }
    else if(StringFind(symbol, "500") >= 0 || StringFind(symbol, "30") >= 0 || 
            StringFind(symbol, "100") >= 0 || StringFind(symbol, "225") >= 0)
    {
        baseRecommendation = "מדדים - בדרך כלל חמישי או שישי";
    }
    else
    {
        baseRecommendation = "סימבול אחר - בדוק עם הברוקר";
    }
    
    // המלצות ספציפיות לברוקרים
    StringToUpper(broker);
    
    if(StringFind(broker, "ICMARKETS") >= 0 || StringFind(broker, "IC MARKETS") >= 0)
    {
        baseRecommendation += "\nIC Markets: מט\"ח ומתכות - רביעי, מדדים - שישי";
    }
    else if(StringFind(broker, "XM") >= 0)
    {
        baseRecommendation += "\nXM: מט\"ח ומתכות - רביעי, מדדים - חמישי";
    }
    else if(StringFind(broker, "EXNESS") >= 0)
    {
        baseRecommendation += "\nExness: מט\"ח - רביעי, מדדים - שישי";
    }
    else if(StringFind(broker, "PEPPERSTONE") >= 0)
    {
        baseRecommendation += "\nPepperstone: מט\"ח ומתכות - רביעי";
    }
    
    return baseRecommendation;
}

//+------------------------------------------------------------------+
//| בדיקה אם זה צמד מט"ח                                          |
//+------------------------------------------------------------------+
bool IsForexPair(string symbol)
{
    string base = StringSubstr(symbol, 0, 3);
    string quote = StringSubstr(symbol, 3, 3);
    
    string currencies = "EUR,USD,GBP,JPY,CHF,CAD,AUD,NZD,SEK,NOK,DKK,PLN,HUF,CZK,TRY,ZAR,MXN,SGD,HKD,RUB,CNH,INR,KRW,BRL";
    
    return StringFind(currencies, base) >= 0 && StringFind(currencies, quote) >= 0;
}

//+------------------------------------------------------------------+
//| קבלת שם היום בעברית                                           |
//+------------------------------------------------------------------+
string GetDayNameHebrew(int day)
{
    switch(day)
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