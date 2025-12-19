from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Iterable, Optional, Set, Tuple

from app.buda_client import Ticker


@dataclass(frozen=True)
class Edge:
    to: str
    rate: Decimal  # multiplicador


Graph = Dict[str, list[Edge]]


def build_graph(tickers: Dict[str, Ticker]) -> Graph:
    """
    Construye un grafo de conversiones:
      - Si existe BASE-QUOTE con precio p:
          BASE -> QUOTE con tasa p
          QUOTE -> BASE con tasa 1/p
    """
    graph: Graph = {}

    def add_edge(currency1: str, currency2: str, rate: Decimal) -> None:
        graph.setdefault(currency1, []).append(Edge(to=currency2, rate=rate))

    for t in tickers.values():
        if t.last_price <= 0:
            continue

        base = t.base.upper()
        quote = t.quote.upper()
        p = t.last_price

        add_edge(base, quote, p)
        add_edge(quote, base, Decimal("1") / p)

    return graph

# Precio para las variaciones en 24 horas
def _price_24h_ago(last_price: Decimal, variation_24h: Decimal) -> Optional[Decimal]:
    # last = prev * (1 + var) => prev = last / (1 + var)
    denom = Decimal("1") + variation_24h
    if denom <= 0:
        return None
    return last_price / denom

# Grafo para las variaciones en 24 horas
def build_graph_24h(tickers: Dict[str, Ticker]) -> Graph:
    """
    Construye un grafo de conversiones de variaciones:
      - Si existe BASE-QUOTE con precio p:
          BASE -> QUOTE con tasa p
          QUOTE -> BASE con tasa 1/p
    """
    graph: Graph = {}

    def add_edge(c1: str, c2: str, rate: Decimal) -> None:
        graph.setdefault(c1, []).append(Edge(to=c2, rate=rate))

    for t in tickers.values():
        pv24 = _price_24h_ago(t.last_price, t.price_variation_24h)
        if pv24 is None or pv24 <= 0:
            continue

        base = t.base.upper()
        quote = t.quote.upper()

        add_edge(base, quote, pv24)
        add_edge(quote, base, Decimal("1") / pv24)

    return graph


def find_rate_max_2_hops(graph: Graph, currency1: str, currency2: str) -> Optional[Decimal]:
    """
    Retorna la tasa multiplicativa para convertir src -> dst.
    Busca rutas de máximo 2 saltos (src->dst o src->X->dst).

    Retorna:
      - Decimal(rate) si existe ruta
      - None si no existe
    """
    currency1 = currency1.upper()
    currency2 = currency2.upper()
    if currency1 == currency2:
        return Decimal("1")

    # BFS con tracking de (node, rate_so_far, depth)
    queue = deque([(currency1, Decimal("1"), 0)])
    visited: Set[Tuple[str, int]] = set([(currency1, 0)])

    while queue:
        node, rate, depth = queue.popleft()
        if depth >= 2:
            continue

        for edge in graph.get(node, []):
            next_node = edge.to
            next_rate = rate * edge.rate
            next_depth = depth + 1

            if next_node == currency2:
                return next_rate

            key = (next_node, next_depth)
            if key not in visited:
                visited.add(key)
                queue.append((next_node, next_rate, next_depth))

    return None
