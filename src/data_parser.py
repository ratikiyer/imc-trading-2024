from datamodel import OrderDepth
from datamodel import TradingState
from datamodel import Order
from typing import Dict, List
import pandas as pd
import numpy as np

# This class reads in data from a csv file and stores a list of TradingState objects that can be used for testing
##########################################
# Trading State Information
##########################################
# traderData: str,
# timestamp: Time,
# listings: Dict[Symbol, Listing],
# order_depths: Dict[Symbol, OrderDepth],
# own_trades: Dict[Symbol, List[Trade]],
# market_trades: Dict[Symbol, List[Trade]],
# position: Dict[Product, Position],
# observations: Observation
class DataParser:

    raw_data: pd.DataFrame

    # Each key in the map is a unique timestamp, representing various TradingState objects
    trading_data: Dict[int, pd.DataFrame]

    # Maps time_stamp -> [product_name -> OrderDepth]
    order_depths: Dict[int, Dict[str, OrderDepth]]

    trading_states: Dict[int, TradingState]

    def __init__(self) -> None:
        self.raw_data = {}
        self.trading_data = {}
        self.order_depths = {}
        self.trading_states = {}

    def parse_csv(self, input_file: str):
        self.raw_data = pd.read_csv(input_file, delimiter=',')
        print(self.raw_data.head())
        self.raw_data.replace('', np.nan)
        if "profit_and_loss" in self.raw_data.columns:
            self.raw_data.drop(columns="profit_and_loss", inplace=True)
        self.trading_data = {time: group for time, group in self.raw_data.groupby('timestamp')}

    def write_csv(self, output_file: str):
        self.raw_data.to_csv(self.output_file)

    def fill_order_depths(self):
        for timestamp, df in self.trading_data.items():
            if timestamp not in self.order_depths.keys():
                self.order_depths[timestamp] = {}
            
            for product in df['product'].unique():
                self.order_depths[timestamp][product] = OrderDepth()
            
            for _, row in df.iterrows():
                product = row['product']
                if product not in self.order_depths[timestamp]:
                    self.order_depths[timestamp][product] = OrderDepth()
                
                order_depth = self.order_depths[timestamp][product]
                # Process buy orders
                for i in range(1, 4):
                    bid_price_key = f'bid_price_{i}'
                    bid_volume_key = f'bid_volume_{i}'
                    if pd.notnull(row[bid_price_key]) and pd.notnull(row[bid_volume_key]):
                        bid_price = int(row[bid_price_key])
                        bid_volume = int(row[bid_volume_key])
                        order_depth.buy_orders[bid_price] = order_depth.buy_orders.get(bid_price, 0) + bid_volume
                
                # Process sell orders
                for i in range(1, 4):
                    ask_price_key = f'ask_price_{i}'
                    ask_volume_key = f'ask_volume_{i}'
                    if pd.notnull(row[ask_price_key]) and pd.notnull(row[ask_volume_key]):
                        ask_price = int(row[ask_price_key])
                        ask_volume = int(row[ask_volume_key])
                        order_depth.sell_orders[ask_price] = order_depth.sell_orders.get(ask_price, 0) - ask_volume
