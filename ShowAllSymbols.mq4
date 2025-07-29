//+------------------------------------------------------------------+
//|                                              ShowAllSymbols.mq4  |
//|                           הצגת כל הסימבולים במערכת            |
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
    Print("=== רשימת כל הסימבולים במערכת ===");
    
    int total = SymbolsTotal(true);
    Print("סה\"כ סימבולים ב-Market Watch: ", total);
    
    for(int i = 0; i < total; i++)
    {
        string symbol = SymbolName(i, true);
        double bid = MarketInfo(symbol, MODE_BID);
        double ask = MarketInfo(symbol, MODE_ASK);
        double spread = MarketInfo(symbol, MODE_SPREAD);
        bool tradeable = MarketInfo(symbol, MODE_TRADEALLOWED);
        
        Print(i+1, ". ", symbol, 
              " | Bid: ", DoubleToString(bid, (int)MarketInfo(symbol, MODE_DIGITS)),
              " | Ask: ", DoubleToString(ask, (int)MarketInfo(symbol, MODE_DIGITS)),
              " | Spread: ", spread,
              " | ניתן למסחר: ", tradeable ? "כן" : "לא");
    }
    
    Print("\n=== סיכום לפי סוגים ===");
    
    int forexCount = 0, metalCount = 0, indexCount = 0, otherCount = 0;
    
    for(int i = 0; i < total; i++)
    {
        string symbol = SymbolName(i, true);
        
        // זיהוי סוג הסימבול
        if(StringFind(symbol, "XAU") >= 0 || StringFind(symbol, "XAG") >= 0 || 
           StringFind(symbol, "GOLD") >= 0 || StringFind(symbol, "SILVER") >= 0)
            metalCount++;
        else if(StringLen(symbol) == 6 && IsForexSymbol(symbol))
            forexCount++;
        else if(StringFind(symbol, "500") >= 0 || StringFind(symbol, "30") >= 0 || 
                StringFind(symbol, "100") >= 0 || StringFind(symbol, "225") >= 0)
            indexCount++;
        else
            otherCount++;
    }
    
    Print("צמדי מט\"ח: ", forexCount);
    Print("מתכות: ", metalCount);
    Print("מדדים: ", indexCount);
    Print("אחר: ", otherCount);
}

//+------------------------------------------------------------------+
//| בדיקה אם זה סימבול מט"ח                                        |
//+------------------------------------------------------------------+
bool IsForexSymbol(string symbol)
{
    string base = StringSubstr(symbol, 0, 3);
    string quote = StringSubstr(symbol, 3, 3);
    
    string currencies = "EUR,USD,GBP,JPY,CHF,CAD,AUD,NZD,SEK,NOK,DKK,PLN,HUF,CZK,TRY,ZAR,MXN,SGD,HKD,RUB,CNH,INR,KRW,BRL";
    
    return StringFind(currencies, base) >= 0 && StringFind(currencies, quote) >= 0;
}
//+------------------------------------------------------------------+