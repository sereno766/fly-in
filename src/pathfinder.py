"""Módulo PathFinder.

Define a classe PathFinder, que encontra o caminho mais barato
(em turnos) da zona start até a zona end para UM drone, usando o
algoritmo de Dijkstra implementado à mão (sem bibliotecas de grafo).
"""

from __future__ import annotations

import heapq
from typing import Dict, List, Tuple

from src.entitie import Map, ZoneType


class NoPathError(Exception):
    """Levantada quando não existe caminho da start até a end."""


class PathFinder:
    """Busca de caminho mínimo no grafo de zonas (Dijkstra).

    O custo de andar de uma zona para outra é o custo de ENTRAR na
    zona de destino (Zone.movement_cost(): normal/priority = 1,
    restricted = 2). Zonas blocked são ignoradas: nenhum caminho
    entra ou passa por elas.

    Attributes:
        (privado) _map: O grafo de zonas e conexões.
    """

    def __init__(self, mapa: Map) -> None:
        """Guarda o mapa onde as buscas serão feitas.

        Args:
            mapa: Map já montado pelo Parser.
        """
        self._map = mapa

    def shortest_path(self) -> List[str]:
        """Calcula o caminho mais barato da start até a end.

        Usa uma fila de prioridade (heapq). Cada caminho é comparado
        pela chave (custo, -nº_de_zonas_priority): tuplas se comparam
        elemento a elemento, então custo menor sempre vence e, com
        custo igual, vence o caminho com MAIS zonas priority (o
        negativo dele é menor). A cada passo, sai da fila a zona com
        a menor chave até agora.

        Returns:
            Os nomes das zonas do caminho, de "start" até "end".

        Raises:
            NoPathError: Se a end não for alcançável a partir da start.
        """
        start = self._map.get_start().name
        end = self._map.get_end().name

        # chave = (custo, -prioridades); menor chave = caminho melhor
        melhor: Dict[str, Tuple[int, int]] = {start: (0, 0)}
        anterior: Dict[str, str] = {}
        fila: List[Tuple[int, int, str]] = [(0, 0, start)]

        while fila:
            custo_atual, neg_prio, nome = heapq.heappop(fila)
            if nome == end:
                return self._rebuild(anterior, start, end)
            # entrada velha: já achamos um caminho melhor até aqui
            if (custo_atual, neg_prio) > melhor[nome]:
                continue

            zona = self._map.get_zone(nome)
            for conn in self._map.get_neighbors(nome):
                vizinho = conn.other_zone(zona)
                # blocked: inacessível, nunca entra na fila
                if vizinho.zone_type is ZoneType.BLOCKED:
                    continue
                ganho = 1 if vizinho.zone_type is ZoneType.PRIORITY else 0
                nova_chave = (
                    custo_atual + vizinho.movement_cost(),
                    neg_prio - ganho,
                )
                atual = melhor.get(vizinho.name)
                if atual is None or nova_chave < atual:
                    melhor[vizinho.name] = nova_chave
                    anterior[vizinho.name] = nome
                    heapq.heappush(fila, (*nova_chave, vizinho.name))

        raise NoPathError(f"não existe caminho de '{start}' até '{end}'")

    @staticmethod
    def _rebuild(anterior: Dict[str, str], start: str, end: str) -> List[str]:
        """Reconstrói o caminho seguindo "anterior" de trás para frente.

        Args:
            anterior: Zona -> zona de onde se chegou nela.
            start: Nome da zona inicial.
            end: Nome da zona final.

        Returns:
            Os nomes das zonas, de start até end.
        """
        caminho = [end]
        while caminho[-1] != start:
            caminho.append(anterior[caminho[-1]])
        caminho.reverse()
        return caminho
