from packages.datamodel import OrderDepth, Order, Trade, TradingState
from packages.logger import logger
from typing import Dict, List
import pandas as pd
import numpy as np
import statistics as stat
import math
import jsonpickle
import collections

# Add more products and position limits as the game continues
PRODUCTS = ["AMETHYST", "STARFRUIT"]
POSITION_LIMITS = {"AMETHYST" : 20, "STARFRUIT" : 20}

MAX_CACHE_SIZE = 4


class Trader:
    
    # Keep track of:
    #   1. Net position of a product (-: short position, +: long position)
    #   2. Absolute value of the quantity of buy and sell orders on a product
    position : Dict[str, int] = {product : 0 for product in PRODUCTS}
    volume_traded : Dict[str, int] = {product : 0 for product in PRODUCTS}
    # Map the person's user_id -> (product_name -> importance)
    # Map is reset and calculated on new data at every TradingState iteration (might have to change)
    # person_importance : Dict[str, Dict[str, float]]
    starfruit_cache: Dict[int, float] = {}

    def calculate_amethyst_orders(self, order_depth: OrderDepth) -> List[Order]:
        orders = []
        if min(order_depth.sell_orders.items()) < 10000:
            quantity =  -(POSITION_LIMITS["AMETHYST"] - self.position["AMETHYST"])
            order = Order("AMETHYST", min(order_depth.sell_orders.items()), quantity)
            orders.append(order)
        elif max(order_depth.buy_orders.items() > 10000):
            quantity =  (POSITION_LIMITS["AMETHYST"] - self.position["AMETHYST"])
            order = Order("AMETHYST", max(order_depth.buy_orders.items()), quantity)
            orders.append(order)
        
        return orders
    
    def calculate_starfruit_price(self) -> int:
        importance = [-0.01869561,  0.0455032 ,  0.16316049,  0.8090892]
        intercept = 4.481696494462085
        nxt_price = intercept
        for i, val in enumerate(self.bananas_cache):
            nxt_price += val * importance[i]

        return int(round(nxt_price))
    
    def calculate_starfruit_orders(self, product, order_depth, acc_bid, acc_ask, LIMIT) -> List[Order]:
        orders: list[Order] = []

        osell = collections.OrderedDict(sorted(order_depth.sell_orders.items()))
        obuy = collections.OrderedDict(sorted(order_depth.buy_orders.items(), reverse=True))

        sell_vol, best_sell_pr = self.values_extract(osell)
        buy_vol, best_buy_pr = self.values_extract(obuy, 1)

        cpos = self.position[product]

        for ask, vol in osell.items():
            if ((ask <= acc_bid) or ((self.position[product]<0) and (ask == acc_bid+1))) and cpos < LIMIT:
                order_for = min(-vol, LIMIT - cpos)
                cpos += order_for
                assert(order_for >= 0)
                orders.append(Order(product, ask, order_for))

        undercut_buy = best_buy_pr + 1
        undercut_sell = best_sell_pr - 1

        bid_pr = min(undercut_buy, acc_bid) # we will shift this by 1 to beat this price
        sell_pr = max(undercut_sell, acc_ask)

        if cpos < LIMIT:
            num = LIMIT - cpos
            orders.append(Order(product, bid_pr, num))
            cpos += num
        
        cpos = self.position[product]
        

        for bid, vol in obuy.items():
            if ((bid >= acc_ask) or ((self.position[product]>0) and (bid+1 == acc_ask))) and cpos > -LIMIT:
                order_for = max(-vol, -LIMIT-cpos)
                # order_for is a negative number denoting how much we will sell
                cpos += order_for
                assert(order_for <= 0)
                orders.append(Order(product, bid, order_for))

        if cpos > -LIMIT:
            num = -LIMIT-cpos
            orders.append(Order(product, sell_pr, num))
            cpos += num

        return orders
    
    def calculate_orders(self, product, order_depth, bid, ask) -> List[Order]:
        if product == "AMETHYST":
            return self.calculate_amethyst_orders(self, order_depth)
        elif product == "STARFRUIT":
            return self.calculate_starfruit_orders(self, "STARFRUIT", order_depth, bid, ask, POSITION_LIMITS[product])

    def run(self, state: TradingState):
        #print("traderData: " + state.traderData)
        #print("Observations: " + str(state.observations))

		# Orders to be placed on exchange matching engine
        result = {}
        for product in state.order_depths:
            if (product == "AMETHYSTS"): continue

            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []
            acceptable_price = 100000  # Participant should calculate this value
            #print("Acceptable price : " + str(acceptable_price))
            #print("Buy Order depth : " + str(len(order_depth.buy_orders)) + ", Sell order depth : " + str(len(order_depth.sell_orders)))
    
            if len(order_depth.sell_orders) != 0:
                best_ask, best_ask_amount = list(order_depth.sell_orders.items())[0]
                if int(best_ask) < acceptable_price:
                    #print("BUY", str(-best_ask_amount) + "x", best_ask)
                    orders.append(Order(product, best_ask, -best_ask_amount))
    
            if len(order_depth.buy_orders) != 0:
                best_bid, best_bid_amount = list(order_depth.buy_orders.items())[0]
                if int(best_bid) > acceptable_price:
                    #print("SELL", str(best_bid_amount) + "x", best_bid)
                    orders.append(Order(product, best_bid, -best_bid_amount))
            
            result[product] = orders

        result['AMETHYSTS'] = self.calculate_amethyst_orders(state)
    
		    # String value holding Trader state data required. 
				# It will be delivered as TradingState.traderData on next execution.
        trader_data = "SAMPLE" 
        
				# Sample conversion request. Check more details below. 
        conversions = 1
        logger.flush(state, result, conversions, trader_data)
        return result, conversions, trader_data
    


    # def calculate_person_importance(self, state: TradingState) -> Dict[str, Dict[str, float]]:
    #     person_importance: Dict[str, Dict[str, float]] = {}
    #     for product in PRODUCTS:
    #         product_vol = 0
    #         last_trade : Trade
    #         for trade in state.market_trades[product]:
    #             if (trade.buyer == trade.seller):
    #                 continue 
    #             user_id_buy, user_id_sell = trade.buyer, trade.seller
            
    #             person_importance.setdefault(user_id_buy, {}).setdefault(product, 0)
    #             person_importance[user_id_buy][product] += abs(trade.quantity)
                
    #             person_importance.setdefault(user_id_sell, {}).setdefault(product, 0)
    #             person_importance[user_id_sell][product] += abs(trade.quantity)
            
    #         product_vol = sum(person_importance[user_id][product] for user_id in person_importance.keys())
            
    #         if last_trade.timestamp < self.time:
    #             elapsed_time = self.time - last_trade.timestamp
    #             for user_id in person_importance:
    #                 if product in person_importance[user_id]:
    #                     person_importance[user_id][product] = ((person_importance[user_id][product] / product_vol) 
    #                                                             * np.exp(-self.lambda_value * elapsed_time / 100) 
    #                                                             * (1 - np.exp(self.lambda_value)))
        
    #     return person_importance