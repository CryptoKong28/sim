// File: package.json
{
  "name": "dex-simulator-react-app",
  "version": "0.1.0",
  "private": true,
  "dependencies": {
    "react": "^17.0.2",
    "react-dom": "^17.0.2",
    "react-scripts": "4.0.3",
    "axios": "^0.21.1"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject"
  },
  "eslintConfig": {
    "extends": [
      "react-app",
      "react-app/jest"
    ]
  },
  "browserslist": {
    "production": [
      ">0.2%",
      "not dead",
      "not op_mini all"
    ],
    "development": [
      "last 1 chrome version",
      "last 1 firefox version",
      "last 1 safari version"
    ]
  }
}

// File: src/App.js
import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [tokenAddress, setTokenAddress] = useState('');
  const [tokenData, setTokenData] = useState(null);
  const [simulationResult, setSimulationResult] = useState(null);
  const [tradeAmount, setTradeAmount] = useState('');
  const [error, setError] = useState('');

  const getPairs = async (address) => {
    try {
      const response = await axios.get(`https://api.dexscreener.com/latest/dex/tokens/${address}`);
      return response.data.pairs || [];
    } catch (error) {
      console.error('Error fetching data:', error);
      setError('Error fetching token data. Please try again.');
      return [];
    }
  };

  const calculateTotalLiquidity = (pairs) => {
    return pairs.reduce((sum, pair) => sum + parseFloat(pair.liquidity?.usd || 0), 0);
  };

  const getTokenData = async () => {
    const pairs = await getPairs(tokenAddress);
    if (pairs.length === 0) {
      setError('No data found for this token address.');
      return;
    }

    const totalLiquidity = calculateTotalLiquidity(pairs);
    const tokenPrice = parseFloat(pairs[0].priceUsd || 0);
    const tokenSymbol = pairs[0].baseToken?.symbol;

    setTokenData({ totalLiquidity, tokenPrice, tokenSymbol });
    setError('');
  };

  const simulateTrade = () => {
    if (!tokenData) {
      setError('Please fetch token data first.');
      return;
    }

    const { totalLiquidity, tokenPrice, tokenSymbol } = tokenData;
    const sim = new DEXSimulator(totalLiquidity, tokenPrice, tokenSymbol);
    const amount = parseFloat(tradeAmount);

    let result;
    if (amount > 0) {
      result = sim.simulateBuy(amount);
    } else {
      result = sim.simulateSell(-amount);
    }

    const priceChange = (result.price_change_ratio - 1) * 100;
    const xFactor = calculateXFactor(result.price_change_ratio);

    setSimulationResult({ ...result, priceChange, xFactor });
  };

  class DEXSimulator {
    constructor(totalLiquidityUsd, tokenPrice, tokenSymbol) {
      this.tokenSymbol = tokenSymbol;
      this.baseSymbol = "USD";
      this.reserveUsd = totalLiquidityUsd / 2;
      this.reserveToken = this.reserveUsd / tokenPrice;
      this.k = this.reserveUsd * this.reserveToken;
    }

    getPrice() {
      return this.reserveUsd / this.reserveToken;
    }

    simulateBuy(usdAmount) {
      const oldPrice = this.getPrice();
      const newReserveUsd = this.reserveUsd + usdAmount;
      const newReserveToken = this.k / newReserveUsd;
      const tokensOut = this.reserveToken - newReserveToken;

      this.reserveUsd = newReserveUsd;
      this.reserveToken = newReserveToken;

      const newPrice = this.getPrice();
      const priceChangeRatio = newPrice / oldPrice;

      return {
        action: "buy",
        tokensReceived: tokensOut,
        usdSpent: usdAmount,
        oldPrice,
        newPrice,
        price_change_ratio: priceChangeRatio
      };
    }

    simulateSell(tokenAmount) {
      const oldPrice = this.getPrice();
      const newReserveToken = this.reserveToken + tokenAmount;
      const newReserveUsd = this.k / newReserveToken;
      const usdOut = this.reserveUsd - newReserveUsd;

      this.reserveUsd = newReserveUsd;
      this.reserveToken = newReserveToken;

      const newPrice = this.getPrice();
      const priceChangeRatio = newPrice / oldPrice;

      return {
        action: "sell",
        usdReceived: usdOut,
        tokensSpent: tokenAmount,
        oldPrice,
        newPrice,
        price_change_ratio: priceChangeRatio
      };
    }
  }

  const calculateXFactor = (priceChangeRatio) => {
    return priceChangeRatio >= 1 ? priceChangeRatio : -1 / priceChangeRatio;
  };

  const formatPrice = (price) => {
    return price < 1 ? `$${price.toFixed(8)}` : `$${price.toFixed(2)}`;
  };

  return (
    <div className="App">
      <h1>DEX Simulator</h1>
      <div>
        <input
          type="text"
          value={tokenAddress}
          onChange={(e) => setTokenAddress(e.target.value)}
          placeholder="Enter token address"
        />
        <button onClick={getTokenData}>Fetch Token Data</button>
      </div>
      {error && <p className="error">{error}</p>}
      {tokenData && (
        <div>
          <h2>Token Information</h2>
          <p>Total liquidity: ${tokenData.totalLiquidity.toFixed(2)}</p>
          <p>Current {tokenData.tokenSymbol} price: {formatPrice(tokenData.tokenPrice)}</p>
          <div>
            <input
              type="number"
              value={tradeAmount}
              onChange={(e) => setTradeAmount(e.target.value)}
              placeholder="Enter amount to trade (+ for buy, - for sell)"
            />
            <button onClick={simulateTrade}>Simulate Trade</button>
          </div>
        </div>
      )}
      {simulationResult && (
        <div>
          <h2>Simulation Results</h2>
          <p>Action: {simulationResult.action}</p>
          <p>{simulationResult.action === 'buy' ? 'Tokens received' : 'USD received'}: {simulationResult.action === 'buy' ? simulationResult.tokensReceived.toFixed(8) : formatPrice(simulationResult.usdReceived)}</p>
          <p>{simulationResult.action === 'buy' ? 'USD spent' : 'Tokens spent'}: {simulationResult.action === 'buy' ? formatPrice(simulationResult.usdSpent) : simulationResult.tokensSpent.toFixed(8)}</p>
          <p>Old price: {formatPrice(simulationResult.oldPrice)}</p>
          <p>New price: {formatPrice(simulationResult.newPrice)}</p>
          <p>Price change: {simulationResult.priceChange.toFixed(6)}% ({simulationResult.xFactor.toFixed(6)}X)</p>
        </div>
      )}
    </div>
  );
}

export default App;

// File: src/App.css
.App {
  font-family: Arial, sans-serif;
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

input, button {
  margin: 10px 0;
  padding: 5px;
}

.error {
  color: red;
}

// File: public/index.html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#000000" />
    <meta
      name="description"
      content="DEX Simulator React App"
    />
    <title>DEX Simulator</title>
  </head>
  <body>
    <noscript>You need to enable JavaScript to run this app.</noscript>
    <div id="root"></div>
  </body>
</html>

// File: .gitignore
node_modules
build
.env
