//+------------------------------------------------------------------+
//| גרסה שסורקת רק צמדי מט"ח                                      |
//+------------------------------------------------------------------+
bool IsForexPair(string symbol)
{
    // רשימת מטבעות עיקריים
    string currencies[] = {"EUR", "USD", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD", 
                          "SEK", "NOK", "DKK", "PLN", "HUF", "CZK", "TRY", "ZAR",
                          "MXN", "SGD", "HKD", "RUB", "CNH", "INR", "KRW", "BRL"};
    
    // בדיקה שהסימבול מכיל 6 תווים (סטנדרט לצמדי מט"ח)
    if(StringLen(symbol) != 6)
        return false;
    
    // בדיקת 3 התווים הראשונים
    string base = StringSubstr(symbol, 0, 3);
    string quote = StringSubstr(symbol, 3, 3);
    
    bool baseFound = false;
    bool quoteFound = false;
    
    // חיפוש המטבעות ברשימה
    for(int i = 0; i < ArraySize(currencies); i++)
    {
        if(base == currencies[i]) baseFound = true;
        if(quote == currencies[i]) quoteFound = true;
    }
    
    return baseFound && quoteFound;
}

// בתוך הלולאה הראשית, הוסף:
void OnStart()
{
    // ... קוד קיים ...
    
    for(int i = 0; i < symbolsTotal; i++)
    {
        string symbol = SymbolName(i, true);
        
        // סינון רק צמדי מט"ח
        if(!IsForexPair(symbol))
            continue;
            
        // ... המשך הקוד ...
    }
}