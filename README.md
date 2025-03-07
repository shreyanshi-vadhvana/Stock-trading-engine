
# Real-time Stock Trading Engine

A lightweight, thread-safe matching engine for simulating real-time stock trading.

## What's This?

I built this project to learn more about how stock exchanges actually match buy and sell orders. Turns out it's pretty fascinating stuff! This is a simplified version that focuses on the core matching algorithm and thread safety - two things that are critical in real trading systems.

## Features

- Fast O(n) order matching algorithm
- Thread-safe implementation for concurrent trading
- Support for up to 1024 different stocks
- No dependencies on dictionaries or hash maps (built from scratch!)
- Handles partial fills and maintains proper time priority
- Written in pure Python

## How It Works

The engine maintains separate buy and sell order lists for each stock symbol. When you add an order, it:

1. Places it in the appropriate list (buy or sell)
2. Sorts the orders based on price-time priority
3. Attempts to match with existing orders

Buy orders are sorted by price (high to low) and time (oldest first), while sell orders are sorted by price (low to high) and time (oldest first).

The matching algorithm follows standard market rules:
- A buy order matches with a sell order when the buy price >= sell price
- The trade executes at the sell order's price (the price that was there first)
- Orders can be partially filled


## Running the Simulation

To run a quick simulation with multiple threads placing random orders:
If using Mac:

```
python3 stock_trading_prj.py
```

If using Windows:
```
python stock_trading_prj.py
```

This will spawn a bunch of simulated traders hammering the system with random orders and show you the execution results.
