import collections
from collections import defaultdict
import random
import math
import copy
import numpy as np
import json
from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState, ConversionObservation
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
    POSITION_LIMIT = {"AMETHYSTS" : 20,
                      "STARFRUIT" : 20,
                      "ORCHIDS" : 100,
                      'CHOCOLATE': 250,
                      'STRAWBERRIES': 350,
                      'ROSES': 60,
                      'GIFT_BASKET': 60}
    PRODUCTS = ['AMETHYSTS', 'STARFRUIT', 'ORCHIDS', 'CHOCOLATE', 'STRAWBERRIES', 'ROSES', 'GIFT_BASKET']
    DEFAULT_PRICES = {
    'AMETHYSTS' : 10000,
    'STARFRUIT' : 5000,
    'ORCHIDS' : 1200,
    }
    historical_prices = {product: [] for product in PRODUCTS}
    last_4_starfruit = []
    ema_prices = dict()
    for product in PRODUCTS:
        ema_prices[product] = None
    ema_param = 0.5

    orchid_avg_price: float = 0.0
    orchid_total_position: int = 0

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
    

    def starfruit_orders(self, state: TradingState) -> dict[str, List[Order]]:
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

        white_noise = np.random.normal(0,0.01)
        last_4_weighted += white_noise


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
    
    def max_orchid_pos(self, state: TradingState) -> int:
        product = "ORCHIDS"
        current_position = state.position.get(product, 0)
        order_depth = state.order_depths[product]
        return min(self.POSITION_LIMIT[product] - current_position, -order_depth.sell_orders[price])
    
    def humidity_effect(self, humidity: float) -> float:
        adjustment: float
        if humidity >= 60 and humidity <= 80:
            adjustment = 0
        elif humidity < 60:
            adjustment = + abs(humidity - 60) * 1.02 / 5
        else:
            adjustment = abs(humidity - 80) * 1.02 / 5
        return adjustment
    

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

    
    def orchids_arbitrage(self, state: TradingState) -> list[Order]:
        prod = "ORCHIDS"
        conv: int = 0
        orders = []
        order_depth = state.order_depths[prod]
        buy_orders = order_depth.buy_orders
        transport_fee = state.observations.conversionObservations[prod].transportFees
        import_tarrif = state.observations.conversionObservations[prod].importTariff
        lowest_ask_conv = state.observations.conversionObservations[prod].askPrice
        cpos = state.position.get(prod)

        self.update_ema_prices(state, prod)
        ema_price = self.ema_prices[prod]

        if buy_orders:
            highest_bid_orderbook = max(buy_orders.keys())
            profit2 = highest_bid_orderbook - lowest_ask_conv - import_tarrif - transport_fee
            logger.print("profit2:" + str(profit2))

            if highest_bid_orderbook:
                orders.append(Order(prod, highest_bid_orderbook, -buy_orders[highest_bid_orderbook]))
                self.orchid_total_position += highest_bid_orderbook * buy_orders[highest_bid_orderbook]
                if cpos:
                    self.orchid_avg_price = self.orchid_total_position / cpos
            logger.print("order arb: " + str(conv))

        return orders
        

    def orchid_orders(self, state: TradingState):
        conv: int = 0
        prod = "ORCHIDS"
        orders = []
        
        cpos = state.position.get(prod)

        # if state.observations.conversionObservations[prod].humidity < 60 or state.observations.conversionObservations[prod].humidity > 80:
        #     price = min(order_depth.sell_orders.keys())
        #     quantity = min(self.POSITION_LIMIT[prod] - cpos, -order_depth.sell_orders[price])
        #     orders.append(Order(prod, price, quantity))
        # elif state.observations.conversionObservations[prod].humidity < 60 or state.observations.conversionObservations[prod].humidity > 80:
        #     price = max(order_depth.buy_orders.keys())
        #     quantity = min(self.POSITION_LIMIT[prod] - cpos, -order_depth.buy_orders[price])
        #     orders.append(Order(prod, price, quantity))
        transport_fee = state.observations.conversionObservations[prod].transportFees
        import_tarrif = state.observations.conversionObservations[prod].importTariff
        orders = self.orchids_arbitrage(state)
        logger.print(str(cpos))
        ask_conv = state.observations.conversionObservations[prod].askPrice
        logger.print(cpos)
        if cpos and cpos < 0 and (ask_conv - import_tarrif - transport_fee < self.orchid_avg_price):
            conv = -cpos
        logger.print(f'Conversions: {conv}')
        return orders, conv


    def gift_basket_arbitrage(self, state: TradingState):
        prod = 'GIFT_BASKET'
        cpos_basket = state.position.get(prod)
        orders = {'CHOCOLATE': 0, 'STRAWBERRIES' : 0, 'ROSES' : 0, 'GIFT_BASKET' : 0}

        basket_buy_orders = state.order_depths['GIFT_BASKET'].buy_orders
        basket_sell_orders = state.order_depths['GIFT_BASKET'].sell_orders
        basket_mid_price: float
        basket_highest_bid: float
        basket_lowest_ask: float
        if basket_buy_orders and basket_sell_orders:
            basket_highest_bid =  max(basket_buy_orders.keys())
            basket_lowest_ask = min(basket_sell_orders.keys())
            basket_mid_price = (basket_highest_bid + basket_lowest_ask) / 2

        straw_buy_orders = state.order_depths['STRAWBERRIES'].buy_orders
        straw_sell_orders = state.order_depths['STRAWBERRIES'].sell_orders
        straw_mid_price: float
        straw_highest_bid: float
        straw_lowest_ask: float
        if straw_buy_orders and straw_sell_orders:
            straw_highest_bid =  max(straw_buy_orders.keys())
            straw_lowest_ask = min(straw_sell_orders.keys())
            straw_mid_price = ( straw_highest_bid + straw_lowest_ask ) / 2
        
        choc_buy_orders = state.order_depths['CHOCOLATE'].buy_orders
        choc_sell_orders = state.order_depths['CHOCOLATE'].sell_orders
        choc_mid_price: float
        choc_highest_bid: float
        choc_lowest_ask: float
        if choc_sell_orders and choc_buy_orders:
            choc_highest_bid = max(choc_buy_orders.keys())
            choc_lowest_ask = min(choc_sell_orders.keys())
            choc_mid_price = (choc_highest_bid + choc_lowest_ask) / 2

        rose_buy_orders = state.order_depths['ROSES'].buy_orders
        rose_sell_orders = state.order_depths['ROSES'].sell_orders
        rose_mid_price: float
        rose_highest_bid: float
        rose_lowest_ask: float
        if rose_buy_orders and rose_sell_orders:
            rose_highest_bid = max(rose_buy_orders.keys()) 
            rose_lowest_ask = min(rose_sell_orders.keys())
            rose_mid_price = (rose_highest_bid + rose_lowest_ask) / 2


        if basket_lowest_ask < (4*choc_highest_bid + 6*straw_highest_bid + rose_highest_bid):
            orders['GIFT_BASKET'].append(Order('GIFT_BASKET', basket_lowest_ask, 1))
            orders['CHOCOLATE'].append(Order('CHOCOLATE', choc_highest_bid, -4))
            orders['STRAWBERRIES'].append(Order('STRAWBERRIES', straw_highest_bid, -6))
            orders['ROSES'].append(Order('ROSES', rose_highest_bid, -1))

        return orders

        
        

    def run(self, state: TradingState):
        result = {}
        conversions = 0

        # result['STARFRUIT'] = self.starfruit_orders(state)
        # result['AMETHYSTS'] = self.amethyst_orders(state)
        # result['ORCHIDS'], conversions = self.orchid_orders(state)
        result = self.gift_basket_arbitrage(state)
    
        trader_data = "SAMPLE"
        logger.print("run: " + str(conversions))
        logger.flush(state, result, conversions, trader_data)
        return result, conversions, trader_data