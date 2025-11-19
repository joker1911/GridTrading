"""AI-guided trading pipeline built on top of the Juejin Python API.

This module fetches market data via the official Juejin SDK (``gm.api``),
forwards the latest context to a configurable AI HTTP endpoint together
with a push ticket, and executes the AI's buy/sell suggestions while
respecting position constraints.
"""
from __future__ import annotations

import importlib
import importlib.util
import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

from stock import buy as record_buy
from stock import sell as record_sell


@dataclass
class AITradingConfig:
    """Configuration for AI-assisted trading."""

    ai_endpoint: str
    ticket: str
    api_token: Optional[str] = None
    gm_token: Optional[str] = None
    max_position_ratio: float = 0.3
    min_cash_reserve: float = 0.1
    slippage: float = 0.001


@dataclass
class Position:
    quantity: float = 0.0
    cost: float = 0.0


class PositionManager:
    """Tracks holdings, cash, and enforces position sizing limits."""

    def __init__(self, initial_cash: float, *, max_position_ratio: float, min_cash_reserve: float, slippage: float):
        self.cash = initial_cash
        self.positions: Dict[str, Position] = {}
        self.last_prices: Dict[str, float] = {}
        self.max_position_ratio = max_position_ratio
        self.min_cash_reserve = min_cash_reserve
        self.slippage = slippage

    def update_price(self, symbol: str, price: float) -> None:
        self.last_prices[symbol] = price

    def equity(self) -> float:
        holdings_value = sum(pos.quantity * self.last_prices.get(symbol, pos.cost) for symbol, pos in self.positions.items())
        return self.cash + holdings_value

    def position_value(self, symbol: str) -> float:
        if symbol not in self.positions:
            return 0.0
        return self.positions[symbol].quantity * self.last_prices.get(symbol, self.positions[symbol].cost)

    def _max_allocation(self) -> float:
        return self.equity() * (1 - self.min_cash_reserve)

    def _allowed_for_symbol(self, symbol: str) -> float:
        return self.equity() * self.max_position_ratio - self.position_value(symbol)

    def plan_buy(self, symbol: str, price: float, desired_quantity: float) -> float:
        """Return the executable quantity after applying risk controls."""
        self.update_price(symbol, price)
        budget = min(self.cash, self._max_allocation())
        symbol_budget = max(0.0, self._allowed_for_symbol(symbol))
        affordable_quantity = min(budget / price, symbol_budget / price)
        quantity = min(desired_quantity, affordable_quantity)
        return max(0.0, quantity)

    def plan_sell(self, symbol: str, desired_quantity: float) -> float:
        if symbol not in self.positions:
            return 0.0
        return max(0.0, min(self.positions[symbol].quantity, desired_quantity))

    def execute_buy(self, symbol: str, price: float, quantity: float, *, timestamp: Any) -> Optional[float]:
        if quantity <= 0:
            return None
        filled_price = price * (1 + self.slippage)
        cost = filled_price * quantity
        if cost > self.cash:
            return None
        self.cash -= cost
        if symbol in self.positions:
            pos = self.positions[symbol]
            new_quantity = pos.quantity + quantity
            new_cost = (pos.cost * pos.quantity + filled_price * quantity) / new_quantity
            self.positions[symbol] = Position(quantity=new_quantity, cost=new_cost)
        else:
            self.positions[symbol] = Position(quantity=quantity, cost=filled_price)
        record_buy(symbol, quantity, timestamp, filled_price, self.cash, int(self.positions[symbol].quantity))
        return filled_price

    def execute_sell(self, symbol: str, price: float, quantity: float, *, timestamp: Any) -> Optional[float]:
        if quantity <= 0 or symbol not in self.positions:
            return None
        filled_price = price * (1 - self.slippage)
        quantity = min(quantity, self.positions[symbol].quantity)
        revenue = filled_price * quantity
        self.positions[symbol].quantity -= quantity
        self.cash += revenue
        if self.positions[symbol].quantity == 0:
            del self.positions[symbol]
        record_sell(symbol, quantity, timestamp, filled_price, self.cash, int(self.positions.get(symbol, Position()).quantity))
        return filled_price

    def snapshot(self) -> Dict[str, Any]:
        return {
            "cash": self.cash,
            "equity": self.equity(),
            "positions": {symbol: pos.__dict__ for symbol, pos in self.positions.items()},
            "last_prices": self.last_prices,
        }


class AIAdvisor:
    """Handles communication with the external AI decision service."""

    def __init__(self, config: AITradingConfig):
        self.config = config
        self.session = requests.Session()

    def request_decision(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        headers = {"Content-Type": "application/json", "X-Ticket": self.config.ticket}
        if self.config.api_token:
            headers["Authorization"] = f"Bearer {self.config.api_token}"
        response = self.session.post(self.config.ai_endpoint, headers=headers, data=json.dumps(payload), timeout=10)
        response.raise_for_status()
        return response.json()


class JuejinDataProvider:
    """Fetches quotes from the Juejin Python SDK (gm.api)."""

    def __init__(self, token: str):
        gm_api = self._load_gm_api()
        if gm_api is None:
            raise RuntimeError("gm.api is not installed; install the official Juejin SDK to enable live data.")
        gm_api.set_token(token)
        self.gm_api = gm_api

    def latest_close(self, symbol: str) -> float:
        bars = self.gm_api.history(symbol=symbol, frequency="1m", count=1, fields="close")
        if not bars:
            raise RuntimeError(f"No data returned for {symbol}")
        if isinstance(bars, dict) and "close" in bars:
            return float(bars["close"][0])
        if isinstance(bars, list):
            last_bar = bars[-1]
            if isinstance(last_bar, dict) and "close" in last_bar:
                return float(last_bar["close"])
            return float(last_bar)
        return float(getattr(bars, "close")[-1])

    @staticmethod
    def _load_gm_api():
        spec = importlib.util.find_spec("gm.api")
        if spec is None:
            return None
        module = importlib.import_module("gm.api")
        return module


@dataclass
class AIDecision:
    action: str
    quantity: float = 0.0
    reason: Optional[str] = None

    @classmethod
    def from_response(cls, data: Dict[str, Any], default_action: str = "hold") -> "AIDecision":
        action = str(data.get("action", default_action)).lower()
        quantity = float(data.get("quantity", data.get("target_quantity", 0.0)))
        reason = data.get("reason")
        target_position = data.get("target_position")
        if target_position is not None:
            quantity = float(target_position)
        return cls(action=action, quantity=quantity, reason=reason)


class AITrader:
    """Coordinates data collection, AI consultation, and trade execution."""

    def __init__(self, config: AITradingConfig, *, cash: float):
        self.config = config
        self.positions = PositionManager(
            initial_cash=cash,
            max_position_ratio=config.max_position_ratio,
            min_cash_reserve=config.min_cash_reserve,
            slippage=config.slippage,
        )
        self.ai = AIAdvisor(config)
        self.provider: Optional[JuejinDataProvider] = None
        if config.gm_token:
            self.provider = JuejinDataProvider(config.gm_token)

    def step(self, symbol: str, *, timestamp: Any = None) -> Dict[str, Any]:
        price = self._fetch_price(symbol)
        self.positions.update_price(symbol, price)
        context = {
            "symbol": symbol,
            "last_price": price,
            "portfolio": self.positions.snapshot(),
        }
        decision = self.ai.request_decision(context)
        trade = AIDecision.from_response(decision)
        execution_price = self._execute(symbol, trade, price, timestamp=timestamp)
        return {
            "decision": trade.__dict__,
            "execution_price": execution_price,
            "portfolio": self.positions.snapshot(),
        }

    def _execute(self, symbol: str, decision: AIDecision, market_price: float, *, timestamp: Any) -> Optional[float]:
        if decision.action == "buy":
            desired_qty = decision.quantity
            if 0 < decision.quantity < 1:
                desired_qty = (self.positions.equity() * decision.quantity) / market_price
            quantity = self.positions.plan_buy(symbol, market_price, desired_qty)
            return self.positions.execute_buy(symbol, market_price, quantity, timestamp=timestamp)
        if decision.action == "sell":
            quantity = decision.quantity
            if 0 < decision.quantity < 1 and symbol in self.positions.positions:
                quantity = self.positions.positions[symbol].quantity * decision.quantity
            return self.positions.execute_sell(symbol, market_price, quantity, timestamp=timestamp)
        return None

    def _fetch_price(self, symbol: str) -> float:
        if self.provider:
            return self.provider.latest_close(symbol)
        raise RuntimeError("No price provider configured; supply a gm_token to enable Juejin data.")


__all__ = [
    "AITradingConfig",
    "AITrader",
    "AIDecision",
    "PositionManager",
    "JuejinDataProvider",
]
