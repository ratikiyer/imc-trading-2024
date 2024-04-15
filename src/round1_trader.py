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
    historical_prices = {product: [] for product in PRODUCTS}
    last_4_starfruit = []
    ema_prices = dict()
    for product in PRODUCTS:
        ema_prices[product] = None

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
        coefficients = [0.20756495, 0.19100943, 0.24615352, 0.35041242] #[0.20756495, 0.19100943, 0.24615352, 0.35041242] Good
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
        last_4_weighted += 24.62232685604613 #24.62232685604613 Good


        if (len(order_depth.sell_orders) != 0):
            ask_index = 0
            while (ask_index < len(order_depth.sell_orders) and cpos_bid < self.POSITION_LIMIT[prod]):
                best_ask, best_ask_amount = list(order_depth.sell_orders.items())[ask_index]
                if (best_ask - 1.15 < last_4_weighted and cpos_bid < self.POSITION_LIMIT[prod]): #1.15
                    logger.print("BUY", str(-best_ask_amount) + "x", best_ask)
                    order_list.append(Order(prod, best_ask, min(-best_ask_amount, (self.POSITION_LIMIT[prod] - cpos_bid))))
                    cpos_bid += -1 * best_ask_amount
                    ask_index += 1
                else: break
        
        
        if (len(order_depth.buy_orders) != 0):
            bid_index = 0
            while (bid_index < len(order_depth.buy_orders) and cpos_sell > -self.POSITION_LIMIT[prod]):
                best_bid, best_bid_amount = list(order_depth.buy_orders.items())[bid_index]
                if best_bid + 1.15 > last_4_weighted: #1.15
                    logger.print("SELL", str(best_bid_amount) + "x", best_bid)
                    order_list.append(Order(prod, best_bid, max(-best_bid_amount, -(self.POSITION_LIMIT[prod] + cpos_sell))))
                    cpos_sell += -1 * best_bid_amount
                    bid_index += 1
                else: break
                
        bid_volume = self.POSITION_LIMIT[prod] - cpos_bid
        ask_volume = -self.POSITION_LIMIT[prod] - cpos_sell
        
        market_bids = state.order_depths[prod].buy_orders 
        market_asks = state.order_depths[prod].sell_orders
        best_bid = last_4_weighted
        best_ask = last_4_weighted
        acceptable_price = last_4_weighted
        
        if len(market_asks) == 0 or len(market_bids) == 0: acceptable_price = last_4_weighted
        else:
            best_bid = max(market_bids)
            best_ask = min(market_asks)
        
        if (bid_volume > 0): 
            order_list.append(Order(prod, min(math.floor(last_4_weighted - 2), best_bid + 1), int(bid_volume)))
        if (ask_volume < 0): 
            order_list.append(Order(prod, max(math.ceil(last_4_weighted + 2), best_ask - 1), int(ask_volume)))

        
        return order_list

               
    def amethyst_orders(self, state: TradingState) -> dict[str, List[Order]]:
        """
        Creates and manages buy and sell orders for AMETHYSTS based on their current market status,
        the trading bot's position, and predefined trading parameters.
        """
        product = 'AMETHYSTS'
        orders = {product: []}
        
        spread = 1
        open_spread = 3
        start_trading = 0
        position_limit = 20
        position_spread = 15
        current_position = state.position.get(product,0)
        order_depth: OrderDepth = state.order_depths[product]
        orders: list[Order] = []
        
            
        if state.timestamp >= start_trading:
            if len(order_depth.sell_orders) > 0:
                best_ask = min(order_depth.sell_orders.keys())
                
                if best_ask <= 10000-spread:
                    best_ask_volume = order_depth.sell_orders[best_ask]
                    logger.print("BEST_ASK_VOLUME", best_ask_volume)
                else:
                    best_ask_volume = 0
            else:
                best_ask_volume = 0
                    
            if len(order_depth.buy_orders) > 0:
                best_bid = max(order_depth.buy_orders.keys())
            
                if best_bid >= 10000+spread:
                    best_bid_volume = order_depth.buy_orders[best_bid]
                    logger.print("BEST_BID_VOLUME", best_bid_volume)
                else:
                    best_bid_volume = 0 
            else:
                best_bid_volume = 0
            
            if current_position - best_ask_volume > position_limit:
                best_ask_volume = current_position - position_limit
                open_ask_volume = 0
            else:
                open_ask_volume = current_position - position_spread - best_ask_volume
                
            if current_position - best_bid_volume < -position_limit:
                best_bid_volume = current_position + position_limit
                open_bid_volume = 0
            else:
                open_bid_volume = current_position + position_spread - best_bid_volume
                
            if -open_ask_volume < 0:
                open_ask_volume = 0         
            if open_bid_volume < 0:
                open_bid_volume = 0

            if -best_ask_volume > 0:
                logger.print("BUY", product, str(-best_ask_volume) + "x", best_ask)
                orders.append(Order(product, best_ask, -best_ask_volume))
            if -open_ask_volume > 0:
                logger.print("BUY", product, str(-open_ask_volume) + "x", 10000-open_spread)
                orders.append(Order(product, 10000-open_spread, -open_ask_volume))

            if best_bid_volume > 0:
                logger.print("SELL", product, str(best_bid_volume) + "x", best_bid)
                orders.append(Order(product, best_bid, -best_bid_volume))
            if open_bid_volume > 0:
                logger.print("SELL", product, str(open_bid_volume) + "x", 10000+open_spread)
                orders.append(Order(product, 10000+open_spread, -open_bid_volume))

        return orders
    
    def run(self, state: TradingState):
        result = {}

        result['STARFRUIT'] = self.starfruit_orders(state)
        result['AMETHYSTS'] = self.amethyst_orders(state)
    
        trader_data = "SAMPLE" 
        
        conversions = 1
        logger.flush(state, result, conversions, trader_data)
        return result, conversions, trader_data