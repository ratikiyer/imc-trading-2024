import datamodel
from trader import Trader
from data_parser import DataParser
from typing import Dict, List
import pandas as pd
import tabulate
import csv

def main():
    file_in: str = "./data/2023_price_data_round_1_day_1.csv"
    file_out: str = "./data/edited_2023_price_data_round_1_day_1.csv"
    parser = DataParser()

    parser.parse_csv(file_in)

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