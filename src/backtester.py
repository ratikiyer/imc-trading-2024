from datamodel import OrderDepth
from datamodel import TradingState
from datamodel import Order
from trader import Trader
from typing import Dict, List
import pandas as pd
import numpy as np

class BackTester:

    trading_states: Dict[int, TradingState]

    def __init__(self, trading_states: Dict[int, TradingState]) -> None:
        self.trading_states = trading_states
    
    def backtest(self):
        
        pass