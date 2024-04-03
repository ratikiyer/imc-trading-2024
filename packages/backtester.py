from packages.datamodel import OrderDepth, Trade
from packages.datamodel import TradingState
from packages.datamodel import Order
from packages.dataparser import DataParser
from typing import Dict, List
import pandas as pd
import numpy as np

class BackTester:

    trading_states: Dict[int, TradingState]
    parser: DataParser

    def __init__(self, trading_states: Dict[int, TradingState]) -> None:
        self.trading_states = trading_states
        self.parser = DataParser()
    
    def process_trades(df_trades: pd.DataFrame, states: Dict[int, TradingState], time_limit):
        for _, trade in df_trades.iterrows():
            time: int = trade['timestamp']
            if time > time_limit:
                break
            symbol = trade['symbol']
            if symbol not in states[time].market_trades:
                states[time].market_trades[symbol] = []
            trade = Trade(
                    symbol, 
                    trade['price'], 
                    trade['quantity'], 
                    '', #trade['buyer'], 
                    '', #trade['seller'], 
                    time)
            states[time].market_trades[symbol].append(trade)

    def backtest(self):
        
        pass

#backtester = BackTester()