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
    PRODUCTS = ['AMETHYSTS', 'STARFRUIT']
    DEFAULT_PRICES = {
    'AMETHYSTS' : 10000,
    'STARFRUIT' : 5000
    }
    last_4_starfruit = []
    ema_prices = dict()
    for product in PRODUCTS:
        ema_prices[product] = None
    ema_param = 0.5
    
    def update_ema_prices(self, state : TradingState, prod):
        """
        Update the exponential moving average of the prices of each product.
        """
        mid_price = self.get_mid_price(prod, state)
            # Update ema price
        if self.ema_prices[prod] is None:
            self.ema_prices[prod] = self.DEFAULT_PRICES[prod]
        else:
            self.ema_prices[prod] = self.ema_param * mid_price + (1-self.ema_param) * self.ema_prices[prod]

    def get_position(self, product, state : TradingState):
        return state.position.get(product, 0)    
    
    def get_mid_price(self, product, state : TradingState):
        default_price = self.ema_prices[product]
        if (default_price is None):
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
        coefficients = [0.19351935, 0.25166263, 0.22349804, 0.330427031]
        cpos_bid = self.get_position(prod, state)
        cpos_sell = self.get_position(prod, state)
        cpos = cpos_sell
        
        logger.print(f'{order_depth.sell_orders}, {order_depth.buy_orders}')

        self.last_4_starfruit.append(self.get_mid_price(prod, state))
        if (len(self.last_4_starfruit) > 4): self.last_4_starfruit = self.last_4_starfruit[1:]
        
        last_4_average = sum(self.last_4_starfruit) / len(self.last_4_starfruit)
        
        coef_index = 0
        last_4_weighted = 0
        while (coef_index < len(self.last_4_starfruit)):
            last_4_weighted += coefficients[coef_index] * self.last_4_starfruit[coef_index]
            coef_index += 1
        last_4_weighted += 4.392
        
        self.update_ema_prices(state, prod)
        ema_price = self.ema_prices[prod]
        logger.print(f"LAST 4: {self.last_4_starfruit}, EMA: {ema_price}, WEIGHTED: {last_4_weighted}, AVERAGE: {last_4_average}")

        if (len(order_depth.sell_orders) != 0):
            ask_index = 0
            while (ask_index < len(order_depth.sell_orders) and cpos_bid < self.POSITION_LIMIT[prod]):
                best_ask, best_ask_amount = list(order_depth.sell_orders.items())[ask_index]
                if (int(best_ask) < ema_price and cpos_bid < self.POSITION_LIMIT[prod]):
                    logger.print("BUY", str(-best_ask_amount) + "x", best_ask)
                    order_list.append(Order(prod, best_ask, min(-best_ask_amount, (self.POSITION_LIMIT[prod] - cpos_bid))))
                    cpos_bid += -1 * best_ask_amount
                    ask_index += 1
                else: break
        
        
        if (len(order_depth.buy_orders) != 0):
            bid_index = 0
            while (bid_index < len(order_depth.buy_orders) and cpos_sell > -self.POSITION_LIMIT[prod]):
                best_bid, best_bid_amount = list(order_depth.buy_orders.items())[bid_index]
                if int(best_bid) > ema_price:
                    logger.print("SELL", str(best_bid_amount) + "x", best_bid)
                    order_list.append(Order(prod, best_bid, max(-best_bid_amount, -(self.POSITION_LIMIT[prod] + cpos_sell))))
                    cpos_sell += -1 * best_bid_amount
                    bid_index += 1
                else: break
                
        bid_volume = self.POSITION_LIMIT[prod] - cpos_bid
        ask_volume = -self.POSITION_LIMIT[prod] - cpos_sell
        
        market_bids = state.order_depths[prod].buy_orders 
        market_asks = state.order_depths[prod].sell_orders
        best_bid = ema_price
        best_ask = ema_price
        acceptable_price = ema_price
        
        if len(market_asks) == 0 or len(market_bids) == 0: acceptable_price = ema_price
        else:
            best_bid = max(market_bids)
            best_ask = min(market_asks)
        
        # if (cpos > 0):
        #     order_list.append(Order(prod, min(math.floor(ema_price - 2), best_bid + 1), int(bid_volume)))
        
        if (bid_volume > 0): 
            order_list.append(Order(prod, min(math.floor(ema_price - 2), best_bid + 1), int(bid_volume)))
        if (ask_volume < 0): 
            order_list.append(Order(prod, max(math.ceil(ema_price + 2), best_ask - 1), int(ask_volume)))

        
        return order_list
               
    def amethyst_orders(self, state: TradingState):
        orders = {'AMETHYSTS' : []}
        prod = 'AMETHYSTS'
        bid_flag = False
        sell_flag = False
        order_depth: OrderDepth = state.order_depths[prod]
        order_list: List[Order] = []
        acceptable_price = 10000
        amethysts_limit = self.POSITION_LIMIT[prod]

        cpos_bid = self.get_position(prod, state)
        cpos_sell = self.get_position(prod, state)
        #max_purchasable = self.POSITION_LIMIT['AMETHYSTS'] - cpos
        logger.print(f'{order_depth.sell_orders}, {order_depth.buy_orders}')

        if len(order_depth.sell_orders) != 0:
            ask_index = 0
            while (cpos_bid < self.POSITION_LIMIT['AMETHYSTS']):
                best_ask, best_ask_amount = list(order_depth.sell_orders.items())[ask_index]
                if int(best_ask) < acceptable_price:
                    logger.print("BUY", str(-best_ask_amount) + "x", best_ask)
                    order_list.append(Order(prod, best_ask, -best_ask_amount))
                    cpos_bid += -1 * best_ask_amount
                    ask_index += 1
                    bid_flag = True
                else: break
                
        
        if len(order_depth.buy_orders) != 0:
            bid_index = 0
            while (cpos_sell > -self.POSITION_LIMIT['AMETHYSTS']):
                best_bid, best_bid_amount = list(order_depth.buy_orders.items())[bid_index]
                if int(best_bid) > acceptable_price:
                    logger.print("SELL", str(best_bid_amount) + "x", best_bid)
                    order_list.append(Order(prod, best_bid, -best_bid_amount))
                    cpos_sell += -1 * best_bid_amount
                    bid_index += 1
                    sell_flag = True
                else: break
                    
        bid_volume = self.POSITION_LIMIT[prod] - cpos_bid
        ask_volume = -self.POSITION_LIMIT[prod] - cpos_sell
        
        market_bids = state.order_depths[prod].buy_orders 
        market_asks = state.order_depths[prod].sell_orders
        best_bid = 10000
        best_ask = 10000

        if len(market_asks) == 0 or len(market_bids) == 0: acceptable_price = 10000
        else:
            best_bid = max(market_bids)
            best_ask = min(market_asks)
            acceptable_price = int((best_bid + best_ask)/2)
        
        if (bid_volume > 0): 
            #if (acceptable_price < 10000):
            order_list.append(Order(prod, min(acceptable_price - 2, best_bid + 1), int(bid_volume)))
            #else: order_list.append(Order(prod, 9999, int(bid_volume)))
        if (ask_volume < 0): 
            #if (acceptable_price > 10000):
            #order_list.append(Order(prod, acceptable_price + 1, int(ask_volume/2)))
            order_list.append(Order(prod, max(acceptable_price + 2, best_ask - 1), int(ask_volume)))
            #else: order_list.append(Order(prod, 10001, int(ask_volume)))

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