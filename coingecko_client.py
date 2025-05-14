import requests

def get_top_tokens_data():
    token_ids = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
        "XRP": "ripple",
        "OP": "optimism"
    }
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": ",".join(token_ids.values()),
        "vs_currencies": "usd",
        "include_24hr_change": "true"
    }
    response = requests.get(url, params=params)
    data = response.json()
    
    results = []
    for symbol, cg_id in token_ids.items():
        info = data.get(cg_id)
        if info:
            price = info["usd"]
            change = info["usd_24h_change"]
            results.append({
                "symbol": symbol,
                "price": price,
                "change": change
            })
    return results