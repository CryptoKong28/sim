import requests
import math
import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs

def get_pairs(token_address: str):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data.get('pairs', [])
    else:
        print(f"Error: Unable to fetch data. Status code: {response.status_code}")
        return []

def calculate_total_liquidity(pairs):
    return sum(float(pair.get('liquidity', {}).get('usd', 0)) for pair in pairs if float(pair.get('liquidity', {}).get('usd', 0)) > 0)

class DEXSimulator:
    def __init__(self, total_liquidity_usd, token_price, token_symbol):
        self.token_symbol = token_symbol
        self.base_symbol = "USD"
        
        # Calculate initial reserves
        self.reserve_usd = total_liquidity_usd / 2
        self.reserve_token = self.reserve_usd / token_price
        self.k = self.reserve_usd * self.reserve_token

    def get_price(self):
        return self.reserve_usd / self.reserve_token

    def simulate_buy(self, usd_amount):
        old_price = self.get_price()
        new_reserve_usd = self.reserve_usd + usd_amount
        new_reserve_token = self.k / new_reserve_usd
        tokens_out = self.reserve_token - new_reserve_token

        self.reserve_usd = new_reserve_usd
        self.reserve_token = new_reserve_token

        new_price = self.get_price()
        price_change_ratio = new_price / old_price

        return {
            "action": "buy",
            "tokens_received": tokens_out,
            "usd_spent": usd_amount,
            "old_price": old_price,
            "new_price": new_price,
            "price_change_ratio": price_change_ratio
        }

    def simulate_sell(self, token_amount):
        old_price = self.get_price()
        new_reserve_token = self.reserve_token + token_amount
        new_reserve_usd = self.k / new_reserve_token
        usd_out = self.reserve_usd - new_reserve_usd

        self.reserve_usd = new_reserve_usd
        self.reserve_token = new_reserve_token

        new_price = self.get_price()
        price_change_ratio = new_price / old_price

        return {
            "action": "sell",
            "usd_received": usd_out,
            "tokens_spent": token_amount,
            "old_price": old_price,
            "new_price": new_price,
            "price_change_ratio": price_change_ratio
        }

def format_price(price):
    return f"${price:.8f}" if price < 1 else f"${price:.2f}"

def get_token_data(token_address):
    pairs = get_pairs(token_address)
    if not pairs:
        return None, None, None

    total_liquidity = calculate_total_liquidity(pairs)
    token_price = float(pairs[0].get('priceUsd', 0))
    token_symbol = pairs[0].get('baseToken', {}).get('symbol')

    return total_liquidity, token_price, token_symbol

def calculate_x_factor(price_change_ratio):
    if price_change_ratio >= 1:
        return price_change_ratio
    else:
        return -1 / price_change_ratio

def simulate_trade(token_address, amount):
    total_liquidity, token_price, token_symbol = get_token_data(token_address)

    if total_liquidity and token_price and token_symbol:
        sim = DEXSimulator(total_liquidity, token_price, token_symbol)

        if amount > 0:
            result = sim.simulate_buy(amount)
        else:
            result = sim.simulate_sell(-amount)

        price_change = (result['price_change_ratio'] - 1) * 100
        x_factor = calculate_x_factor(result['price_change_ratio'])

        return {
            "total_liquidity": total_liquidity,
            "token_price": token_price,
            "token_symbol": token_symbol,
            "simulation_result": result,
            "price_change_percent": price_change,
            "x_factor": x_factor
        }
    else:
        return {"error": "Unable to fetch token data or run simulation."}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        # Parse query parameters
        query_components = parse_qs(self.path.split('?')[-1])
        token_address = query_components.get('token_address', [''])[0]
        amount = float(query_components.get('amount', ['0'])[0])

        if not token_address:
            self.wfile.write(json.dumps({"error": "Missing token_address parameter"}).encode())
            return

        result = simulate_trade(token_address, amount)
        self.wfile.write(json.dumps(result).encode())

# This line is not needed for Vercel deployment
# if __name__ == "__main__":
#     main()
