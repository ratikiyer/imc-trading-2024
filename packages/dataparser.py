from packages.datamodel import OrderDepth, Observation, Symbol, Listing, Trade, Product, Position, TradingState, Order
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

    # Maps time_stamp -> TradingState
    trading_states: Dict[int, TradingState]

    def __init__(self) -> None:
        self.raw_data = {}
        self.trading_data = {}
        self.order_depths = {}
        self.trading_states = {}

    def parse_csv(self, input_file: str):
        self.raw_data = pd.read_csv(input_file, delimiter=';')
        self.raw_data.replace('', np.nan)
        self.trading_data = {time: group for time, group in self.raw_data.groupby('timestamp')}

    def write_csv(self, output_file: str):
        self.raw_data.to_csv(output_file, sep=";", index=False)

    def extract_order_depths(self):
    # Assuming self.order_depths is correctly initialized as an empty dict before this method is called
    
        for timestamp, df in self.trading_data.items():
            if timestamp not in self.order_depths:
                self.order_depths[timestamp] = {}

            for product in df['product'].unique():
                if product not in self.order_depths[timestamp]:
                    self.order_depths[timestamp][product] = OrderDepth()

            for _, row in df.iterrows():
                product = row['product']
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
                        order_depth.sell_orders[ask_price] = order_depth.sell_orders.get(ask_price, 0) + ask_volume
        
        # No need for the incorrect self.order_depths[product] = order_depth line

        # If you need to return self.order_depths, uncomment the next line:
        return self.order_depths

    
    def extract_listings(self, df) -> Dict[Symbol, Listing]:
        pass

    def extract_own_trades(self, df) -> Dict[Symbol, List[Trade]]:
        pass

    def extract_market_trades(self, df) -> Dict[Symbol, List[Trade]]:
        pass

    def extract_positions(self, df) -> Dict[Product, Position]:
        pass

    def extract_observations(self, df) -> Observation:
        pass

    def get_trading_states(self) -> Dict[int, TradingState]:
        for timestamp, df in self.trading_data.items():
            trader_data = ""
            # listings = self.extract_listings(df)
            order_depths = self.extract_order_depths()
            # own_trades = self.extract_own_trades(df)
            # market_trades = self.extract_market_trades(df)
            # position = self.extract_positions(df)
            # observations = self.extract_observations(df)

            listings = {}
            own_trades = {}
            market_trades = {}
            position = {}
            observation = None
            
            # Create a new TradingState object
            trading_state = TradingState(
                traderData=trader_data,
                timestamp=timestamp,
                listings=listings,
                order_depths=order_depths,
                own_trades=own_trades,
                market_trades=market_trades,
                position=position,
                observations=observation
            )

            # Add the new TradingState to the dictionary
            self.trading_states[timestamp] = trading_state

            return self.trading_states