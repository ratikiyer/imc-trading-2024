from datamodel import TradingState
from datamodel import Trade
from datamodel import Order
from datamodel import OrderDepth
from typing import Dict, List
import pandas as pd
import numpy as np
import statistics as stat
import math
import jsonpickle

# Add more products and position limits as the game continues
PRODUCTS = ["AMETHYSTS", "STARFRUIT"]
POSITION_LIMITS = {"AMETHYSTS" : 20, "STARFRUIT" : 20}

# Maximum capacity that can be stored in a cache
MAX_CACHE_CAPACITY = 10

class Trader:
    
    # Exponential time decay factor of importance weighting
    # Goal is to find optimal lambda_value that reflects accurate time weighting
    lambda_value : int = 1
    # Keep track of:
    #   1. Net position of a product (-: short position, +: long position)
    #   2. Absolute value of the quantity of buy and sell orders on a product
    position : Dict[str, int] = {product : 0 for product in PRODUCTS}
    volume_traded : Dict[str, int] = {product : 0 for product in PRODUCTS}
    # Map the person's user_id -> (product_name -> importance)
    # Map is reset and calculated on new data at every TradingState iteration (might have to change)
    person_importance : Dict[str, Dict[str, float]]
    # Use cache system for querying mids for a certain product (improves efficiency)
    #   Ex. cache: Dict[str, List[int]] = {"BANANAS" : [10, 11, 11, 12, 11, 9, 13, 11]}
    #       If len(cache["BANANAS"]) >= MAX_CACHE_CAPACITY -> pop oldest element

    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        print("Trader Data: " + state.traderData)
        print("Observation Data: " + str(state.observations))

        # Initialize the person_importance map with the trades in the most recent TradingState
        self.person_importance = self.calculate_person_importance(self, state)
        
        result = {}
        for product in state.order_depths:
            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []

            # Logic for finding the true value (EV) of a product and store in acceptable_price
            acceptable_price: int = ...
            print("Acceptable price : " + str(acceptable_price))
            print("Buy Order depth : " + str(len(order_depth.buy_orders)) + ", Sell order depth : " + str(len(order_depth.sell_orders)))
        

        # Return a map from product_name -> Order
        return result
    
    def calculate_person_importance(self, state: TradingState) -> Dict[str, Dict[str, float]]:
        person_importance: Dict[str, Dict[str, float]] = {}
        for product in PRODUCTS:
            product_vol = 0
            last_trade : Trade
            for trade in state.market_trades[product]:
                if (trade.buyer == trade.seller):
                    continue 
                user_id_buy, user_id_sell = trade.buyer, trade.seller
            
                person_importance.setdefault(user_id_buy, {}).setdefault(product, 0)
                person_importance[user_id_buy][product] += abs(trade.quantity)
                
                person_importance.setdefault(user_id_sell, {}).setdefault(product, 0)
                person_importance[user_id_sell][product] += abs(trade.quantity)
            
            product_vol = sum(person_importance[user_id][product] for user_id in person_importance.keys())
            
            if last_trade.timestamp < self.time:
                elapsed_time = self.time - last_trade.timestamp
                for user_id in person_importance:
                    if product in person_importance[user_id]:
                        person_importance[user_id][product] = ((person_importance[user_id][product] / product_vol) 
                                                                * np.exp(-self.lambda_value * elapsed_time / 100) 
                                                                * (1 - np.exp(self.lambda_value)))
        
        return person_importance
    
    def calculate_cache(self, state: TradingState) -> Dict[str, List[int]]:
        for product in PRODUCTS:
            sorted_trades = sorted(state.market_trades[product], key=lambda time : trade.timestamp, reverse=True)[:MAX_CACHE_CAPACITY]
            cache: Dict[str, List[int]] = {}
            cache[product] = []
            for trade in sorted_trades:
                while len(cache[product]) >= MAX_CACHE_CAPACITY:
                    cache[product].pop()
                cache[product].insert(0, trade.price)
                
        return cache