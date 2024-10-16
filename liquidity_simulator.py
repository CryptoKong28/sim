import sys
import requests
import math
import csv

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

def main():
    if len(sys.argv) != 3:
        print("Usage: python liquidity_simulator.py <name> <token_address>")
        sys.exit(1)

    name = sys.argv[1]
    token_address = sys.argv[2]

    total_liquidity, token_price, token_symbol = get_token_data(token_address)

    if total_liquidity and token_price and token_symbol:
        print(f"Total liquidity for {name}: ${total_liquidity:,.2f}")
        print(f"Current {token_symbol} price: {format_price(token_price)}")

        sim = DEXSimulator(total_liquidity, token_price, token_symbol)

        try:
            amount = float(input("Enter the amount of USD to trade (positive for buy, negative for sell): "))
            if amount == 0:
                print("Trade amount cannot be zero.")
                sys.exit(1)

            if amount > 0:
                result = sim.simulate_buy(amount)
                print(f"\nSimulation Results for buying {token_symbol}:")
                print(f"{token_symbol} received: {result['tokens_received']:.8f}")
                print(f"USD spent: ${result['usd_spent']:.2f}")
            else:
                amount = -amount  # Convert to positive for calculation
                result = sim.simulate_sell(amount)
                print(f"\nSimulation Results for selling {token_symbol}:")
                print(f"USD received: ${result['usd_received']:.2f}")
                print(f"{token_symbol} spent: {result['tokens_spent']:.8f}")

            print(f"Old price: {format_price(result['old_price'])}")
            print(f"New price: {format_price(result['new_price'])}")
            price_change = (result['price_change_ratio'] - 1) * 100
            x_factor = calculate_x_factor(result['price_change_ratio'])
            print(f"Price change: {price_change:.6f}% ({x_factor:.6f}X)")

            # Save results to CSV
            csv_file = "simulation_results.csv"
            fieldnames = [
                "action", "usd_amount", "token_amount", "old_price", "new_price",
                "price_change_percent", "x_factor"
            ]

            data = {
                "action": result.get("action"),
                "usd_amount": result.get("usd_spent", result.get("usd_received", 0)),
                "token_amount": result.get("tokens_received", result.get("tokens_spent", 0)),
                "old_price": result.get("old_price"),
                "new_price": result.get("new_price"),
                "price_change_percent": price_change,
                "x_factor": x_factor
            }

            # Check if file exists to write header
            write_header = False
            try:
                with open(csv_file, 'x', newline='') as csvfile:
                    write_header = True
            except FileExistsError:
                pass

            with open(csv_file, 'a', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                if write_header:
                    writer.writeheader()
                writer.writerow(data)

            print(f"\nSimulation results have been saved to {csv_file}.")

        except ValueError:
            print("Invalid input. Please enter a valid number.")

    else:
        print("Unable to fetch token data or run simulation.")

if __name__ == "__main__":
    main()
