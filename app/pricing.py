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
