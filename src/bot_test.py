import collections
from collections import defaultdict
import random
import math
import copy
import numpy as np
import json
from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState
from typing import Any, Dict, List

class Logger:
    def __init__(self) -> None:
        self.logs = ""

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: dict[Symbol, list[Order]], conversions: int, trader_data: str) -> None:
        print(json.dumps([
            self.compress_state(state),
            self.compress_orders(orders),
            conversions,
            trader_data,
            self.logs,
        ], cls=ProsperityEncoder, separators=(",", ":")))

        self.logs = ""

    def compress_state(self, state: TradingState) -> list[Any]:
        return [
            state.timestamp,
            state.traderData,
            self.compress_listings(state.listings),
            self.compress_order_depths(state.order_depths),
            self.compress_trades(state.own_trades),
            self.compress_trades(state.market_trades),
            state.position,
            self.compress_observations(state.observations),
        ]

    def compress_listings(self, listings: dict[Symbol, Listing]) -> list[list[Any]]:
        compressed = []
        for listing in listings.values():
            compressed.append([listing["symbol"], listing["product"], listing["denomination"]])

        return compressed

    def compress_order_depths(self, order_depths: dict[Symbol, OrderDepth]) -> dict[Symbol, list[Any]]:
        compressed = {}
        for symbol, order_depth in order_depths.items():
            compressed[symbol] = [order_depth.buy_orders, order_depth.sell_orders]

        return compressed

    def compress_trades(self, trades: dict[Symbol, list[Trade]]) -> list[list[Any]]:
        compressed = []
        for arr in trades.values():
            for trade in arr:
                compressed.append([
                    trade.symbol,
                    trade.price,
                    trade.quantity,
                    trade.buyer,
                    trade.seller,
                    trade.timestamp,
                ])

        return compressed

    def compress_observations(self, observations: Observation) -> list[Any]:
        conversion_observations = {}
        for product, observation in observations.conversionObservations.items():
            conversion_observations[product] = [
                observation.bidPrice,
                observation.askPrice,
                observation.transportFees,
                observation.exportTariff,
                observation.importTariff,
                observation.sunlight,
                observation.humidity,
            ]

        return [observations.plainValueObservations, conversion_observations]

    def compress_orders(self, orders: dict[Symbol, list[Order]]) -> list[list[Any]]:
        compressed = []
        for arr in orders.values():
            for order in arr:
                compressed.append([order.symbol, order.price, order.quantity])

        return compressed
logger = Logger()




class Trader:
    POSITION_LIMIT = {"AMETHYSTS" : 20, "STARFRUIT" : 20}
    DEFAULT_PRICES = {
    'AMETHYSTS' : 10000,
    'STARFRUIT' : 5000
    }
    last_5_starfruit = []
    
    def get_position(self, product, state : TradingState):
        return state.position.get(product, 0)    
    
    def get_mid_price(self, product, state : TradingState):
        default_price = self.DEFAULT_PRICES[product]

        if product not in state.order_depths:
            return default_price
        
        market_bids = state.order_depths[product].buy_orders 
        if len(market_bids) == 0:
            # There are no bid orders in the market (midprice undefined)
            return default_price
              
        market_asks = state.order_depths[product].sell_orders
        if len(market_asks) == 0:
            # There are no bid orders in the market (mid_price undefined)
            return default_price
        
        best_bid = max(market_bids)
        best_ask = min(market_asks)
        return (best_bid + best_ask)/2

    def starfruit_orders(self, state: TradingState):
        prod = 'STARFRUIT'
        order_depth: OrderDepth = state.order_depths[prod]
        order_list: List[Order] = []
        starfruits_limit = self.POSITION_LIMIT[prod]
        default_price = 5000
        cpos = self.get_position(prod, state)
        
        self.last_5_starfruit.append(self.get_mid_price(prod, state))
        if (len(self.last_5_starfruit) > 3): self.last_5_starfruit = self.last_5_starfruit[1:]
        
        last_5_average = sum(self.last_5_starfruit) / len(self.last_5_starfruit)

        if (len(order_depth.sell_orders) != 0):
            best_ask, best_ask_amount = list(order_depth.sell_orders.items())[0]
            if (int(best_ask) < last_5_average and cpos < self.POSITION_LIMIT[prod]):
                logger.print("BUY", str(-best_ask_amount) + "x", best_ask)
                order_list.append(Order(prod, best_ask, -best_ask_amount))
                cpos += -1 * best_ask_amount
                
        if (len(order_depth.buy_orders) != 0):
            best_bid, best_bid_amount = list(order_depth.buy_orders.items())[0]
            if int(best_bid) > last_5_average:
                logger.print("SELL", str(best_bid_amount) + "x", best_bid)
                order_list.append(Order(prod, best_bid, -best_bid_amount))
                
        return order_list
               
    def amethyst_orders(self, state: TradingState):
        orders = {'AMETHYSTS' : []}
        prod = 'AMETHYSTS'
        order_depth: OrderDepth = state.order_depths[prod]
        order_list: List[Order] = []
        acceptable_price = 10000
        amethysts_limit = self.POSITION_LIMIT[prod]

        cpos = self.get_position(prod, state)
        max_purchasable = self.POSITION_LIMIT['AMETHYSTS'] - cpos
        logger.print(f'{order_depth.sell_orders}, {order_depth.buy_orders}')

        if len(order_depth.sell_orders) != 0:
            ask_index = 0
            while (cpos < self.POSITION_LIMIT['AMETHYSTS']):
                best_ask, best_ask_amount = list(order_depth.sell_orders.items())[ask_index]
                if int(best_ask) < acceptable_price:
                    logger.print("BUY", str(-best_ask_amount) + "x", best_ask)
                    order_list.append(Order(prod, best_ask, -best_ask_amount))
                    cpos += -1 * best_ask_amount
                    ask_index += 1
                else: break
    
        if len(order_depth.buy_orders) != 0:
            bid_index = 0
            while (int(list(order_depth.buy_orders.items())[bid_index][0]) > acceptable_price):
                best_bid, best_bid_amount = list(order_depth.buy_orders.items())[bid_index]
                if int(best_bid) > acceptable_price:
                    logger.print("SELL", str(best_bid_amount) + "x", best_bid)
                    order_list.append(Order(prod, best_bid, -best_bid_amount))
                    bid_index += 1
        
        orders[prod] = order_list

        return order_list
    
    def run(self, state: TradingState):
        #print("traderData: " + state.traderData)
        #print("Observations: " + str(state.observations))

				# Orders to be placed on exchange matching engine
        result = {}
        # for product in state.order_depths:
        #     if (product == "AMETHYSTS"): continue

        #     order_depth: OrderDepth = state.order_depths[product]
        #     orders: List[Order] = []
        #     acceptable_price = 100000  # Participant should calculate this value
        #     #print("Acceptable price : " + str(acceptable_price))
        #     #print("Buy Order depth : " + str(len(order_depth.buy_orders)) + ", Sell order depth : " + str(len(order_depth.sell_orders)))
    
        #     if len(order_depth.sell_orders) != 0:
        #         best_ask, best_ask_amount = list(order_depth.sell_orders.items())[0]
        #         if int(best_ask) < acceptable_price:
        #             #print("BUY", str(-best_ask_amount) + "x", best_ask)
        #             orders.append(Order(product, best_ask, -best_ask_amount))
    
        #     if len(order_depth.buy_orders) != 0:
        #         best_bid, best_bid_amount = list(order_depth.buy_orders.items())[0]
        #         if int(best_bid) > acceptable_price:
        #             #print("SELL", str(best_bid_amount) + "x", best_bid)
        #             orders.append(Order(product, best_bid, -best_bid_amount))
            
        #     result[product] = orders

        result['STARFRUIT'] = self.starfruit_orders(state)
        result['AMETHYSTS'] = self.amethyst_orders(state)
    
		    # String value holding Trader state data required. 
				# It will be delivered as TradingState.traderData on next execution.
        trader_data = "SAMPLE" 
        
				# Sample conversion request. Check more details below. 
        conversions = 1
        logger.flush(state, result, conversions, trader_data)
        return result, conversions, trader_data
