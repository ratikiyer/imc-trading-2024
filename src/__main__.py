import sys
sys.path.insert(0, '/Users/ratikiyer/Documents/UIUC/IMC/imc_trading_2024')
from packages.datamodel import (Time, Symbol, Product, Position, UserId, ObservationValue,
                                TradingState, Trade, Listing, Order, OrderDepth, Observation, ConversionObservation)
from packages.dataparser import DataParser
from packages.logger import Logger
from trader import Trader
from typing import Dict, List
import pandas as pd
import tabulate
import csv

def main():
    
    file_in = "./data/tutorial_data.csv"
    file_out = "./data/tutorial_results_data.csv"
    parser = DataParser()

    parser.parse_csv(file_in)
    trading_states: Dict[int, TradingState] = parser.get_trading_states()
    for timestep in trading_states.keys():
        state = trading_states[timestep]
        print(state.toJSON())



    trader = Trader()
        
    # parser.write_csv(file_out)
    # print(parser.trading_data[678900])

    # parser.fill_order_depths()
    # buy_orders: Dict[int, int] = parser.order_depths[678900]["BANANAS"].buy_orders
    # sell_orders: Dict[int, int] = parser.order_depths[678900]["BANANAS"].sell_orders

    # print("Buy Order Depth:\n")
    # for price in buy_orders.keys():
    #     print("Price: " + str(price) + " -> Quantity: " + str(buy_orders[price]) + '\n')
    
    # print("Sell Order Depth:\n")
    # for price in sell_orders.keys():
    #     print("Price: " + str(price) + " -> Quantity: " + str(sell_orders[price]) + '\n')
    


    

if __name__ == "__main__":
    main()