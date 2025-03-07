import threading
import random
import time
from queue import Queue
import concurrent.futures

# Constants
MAX_STOCKS = 1024
STOCK_PREFIX = "STOCK"

# Order class to represent a buy or sell order
class Order:
    def __init__(self, transaction_id, order_type, stock_index, quantity, price):
        self.transaction_id = transaction_id
        self.order_type = order_type  
        self.stock_index = stock_index
        self.quantity = quantity
        self.price = price
        self.creation_time = time.time()
        self.completed = False

class OrderBook:
    def __init__(self, max_stocks):
        self.max_stocks = max_stocks
        self.buy_orders = [[] for _ in range(max_stocks)]
        self.sell_orders = [[] for _ in range(max_stocks)]
        # Locks for each stock to manage concurrency
        self.stock_locks = [threading.RLock() for _ in range(max_stocks)]
        self.completed_trades = Queue()
        self.transaction_counter = 0
        self.counter_lock = threading.Lock()

    def get_next_transaction_id(self):
        with self.counter_lock:
            transaction_id = self.transaction_counter
            self.transaction_counter += 1
            return transaction_id

    def addOrder(self, order_type, ticker_symbol, quantity, price):
        stock_index = self._symbol_to_index(ticker_symbol)
        
        # Validate inputs
        if stock_index < 0 or stock_index >= self.max_stocks:
            raise ValueError(f"Invalid ticker symbol: {ticker_symbol}")
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        if price <= 0:
            raise ValueError("Price must be positive")
        if order_type not in ["BUY", "SELL"]:
            raise ValueError("Order type must be 'BUY' or 'SELL'")
        
        transaction_id = self.get_next_transaction_id()
        new_order = Order(transaction_id, order_type, stock_index, quantity, price)
        
        # Adding order to the appropriate list and attempt to match
        with self.stock_locks[stock_index]:
            if order_type == "BUY":
                self.buy_orders[stock_index].append(new_order)
                # Sort buy orders by price (descending) and timestamp (ascending)
                self.buy_orders[stock_index].sort(key=lambda x: (-x.price, x.creation_time))
            else:  # SELL
                self.sell_orders[stock_index].append(new_order)
                # Sort sell orders by price (ascending) and timestamp (ascending)
                self.sell_orders[stock_index].sort(key=lambda x: (x.price, x.creation_time))
            
            # Match orders for this stock
            self.matchOrder(stock_index)
        
        return transaction_id

    def matchOrder(self, stock_index):
        # This function matches buy and sell orders for a specific stock
        # It assumes the lock for this stock is already acquired
        
        buy_list = self.buy_orders[stock_index]
        sell_list = self.sell_orders[stock_index]
        
        # Time complexity: O(n) where n is the number of orders for this stock
        # Since we're processing each order at most once
        
        buy_pointer, sell_pointer = 0, 0
        while buy_pointer < len(buy_list) and sell_pointer < len(sell_list):
            current_buy = buy_list[buy_pointer]
            current_sell = sell_list[sell_pointer]
            
            # Skip already matched orders
            if current_buy.completed:
                buy_pointer += 1
                continue
            if current_sell.completed:
                sell_pointer += 1
                continue
            
            # Check if orders match
            if current_buy.price >= current_sell.price:
                # Orders match, process the trade
                traded_shares = min(current_buy.quantity, current_sell.quantity)
                
                # Update quantities
                current_buy.quantity -= traded_shares
                current_sell.quantity -= traded_shares
                
                # Record the trade
                self.completed_trades.put({
                    "buy_transaction_id": current_buy.transaction_id,
                    "sell_transaction_id": current_sell.transaction_id,
                    "stock_index": stock_index,
                    "ticker_symbol": self._index_to_symbol(stock_index),
                    "quantity": traded_shares,
                    "price": current_sell.price,  # Trade executes at the sell price
                    "execution_time": time.time()
                })
                
                # Mark orders as completed if fully executed
                if current_buy.quantity == 0:
                    current_buy.completed = True
                    buy_pointer += 1
                if current_sell.quantity == 0:
                    current_sell.completed = True
                    sell_pointer += 1
            else:
                # No more matches possible (lowest sell price > highest buy price)
                break
        
        # Remove completed orders
        self.buy_orders[stock_index] = [order for order in buy_list if not order.completed]
        self.sell_orders[stock_index] = [order for order in sell_list if not order.completed]

    def _symbol_to_index(self, ticker_symbol):
        # Convert ticker symbol to index (0-1023)
        if not ticker_symbol.startswith(STOCK_PREFIX):
            return -1
        try:
            index = int(ticker_symbol[len(STOCK_PREFIX):])
            if 0 <= index < self.max_stocks:
                return index
            return -1
        except ValueError:
            return -1

    def _index_to_symbol(self, index):
        # Convert index to ticker symbol
        return f"{STOCK_PREFIX}{index}"

    def get_market_depth(self, ticker_symbol):
        stock_index = self._symbol_to_index(ticker_symbol)
        if stock_index < 0 or stock_index >= self.max_stocks:
            raise ValueError(f"Invalid ticker symbol: {ticker_symbol}")
        
        with self.stock_locks[stock_index]:
            buy_snapshot = [(o.price, o.quantity) for o in self.buy_orders[stock_index]]
            sell_snapshot = [(o.price, o.quantity) for o in self.sell_orders[stock_index]]
        
        return {
            "ticker": ticker_symbol,
            "buy_orders": buy_snapshot,
            "sell_orders": sell_snapshot
        }

# Simulator to generate random orders
class MarketSimulator:
    def __init__(self, order_book, num_brokers=10):
        self.order_book = order_book
        self.num_brokers = num_brokers
        self.running = True
        self.brokers = []

    def broker_activity(self, broker_id):
        while self.running:
            # Generate random order parameters
            order_type = random.choice(["BUY", "SELL"])
            stock_index = random.randint(0, MAX_STOCKS - 1)
            ticker_symbol = f"{STOCK_PREFIX}{stock_index}"
            quantity = random.randint(1, 100)
            price = random.uniform(1.0, 1000.0)
            
            try:
                transaction_id = self.order_book.addOrder(order_type, ticker_symbol, quantity, price)
                print(f"Broker {broker_id} placed {order_type} order {transaction_id}: {ticker_symbol} x {quantity} @ ${price:.2f}")
            except Exception as e:
                print(f"Order placement error: {e}")
            
            # Sleep for a random time to simulate varying trading frequencies
            time.sleep(random.uniform(0.1, 1.0))

    def trade_reporter(self):
        while self.running:
            try:
                # Non-blocking check for executed trades
                if not self.order_book.completed_trades.empty():
                    trade = self.order_book.completed_trades.get(block=False)
                    print(f"TRADE EXECUTED: {trade['ticker_symbol']} - {trade['quantity']} shares @ ${trade['price']:.2f}")
                else:
                    time.sleep(0.1)
            except Exception as e:
                print(f"Trade reporting error: {e}")

    def start_simulation(self):
        # Start broker threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.num_brokers + 1) as executor:
            # Start the trade reporting thread
            reporter_future = executor.submit(self.trade_reporter)
            
            # Start broker threads
            broker_futures = [executor.submit(self.broker_activity, i) for i in range(self.num_brokers)]
            
            try:
                # Run for a specified time
                time.sleep(30)  # Run for 30 seconds
                self.running = False
                
                # Wait for all futures to complete
                concurrent.futures.wait([reporter_future] + broker_futures)
            except KeyboardInterrupt:
                print("Simulation terminating...")
                self.running = False

# Main function to run the trading system
def main():
    # Create the order book
    market = OrderBook(MAX_STOCKS)
    
    # Create and start the simulator
    simulator = MarketSimulator(market, num_brokers=5)
    
    print("Starting market simulation...")
    simulator.start_simulation()
    
    # Display some statistics after the simulation
    total_trades = market.completed_trades.qsize()
    print(f"\nSimulation complete. Total trades executed: {total_trades}")
    
    # Sample some active stocks
    for i in range(5):
        stock_index = random.randint(0, MAX_STOCKS - 1)
        ticker_symbol = f"{STOCK_PREFIX}{stock_index}"
        try:
            market_data = market.get_market_depth(ticker_symbol)
            print(f"\nMarket depth for {ticker_symbol}:")
            print(f"Buy orders: {len(market_data['buy_orders'])}")
            print(f"Sell orders: {len(market_data['sell_orders'])}")
        except Exception as e:
            print(f"Error retrieving market depth: {e}")

if __name__ == "__main__":
    main()