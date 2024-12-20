import requests

def test_connection():
    base_url = "https://api.coinex.com/v2/spot/kline"
    params = {"market": "BTCUSDT", "period": "1min", "limit": 1}
    response = requests.get(base_url, params=params)
    print("Status Code:", response.status_code)
    print("Response Body:", response.text)

test_connection()
