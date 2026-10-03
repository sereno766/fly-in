"""Módulo Simulation.

Define a classe Simulation, o "juiz" da simulação: guarda o estado
de todos os drones, valida e aplica os movimentos de cada turno e
responde perguntas sobre a ocupação de zonas e conexões.

Ela NÃO decide para onde os drones vão — isso é papel do planner.
"""

from __future__ import annotations

from typing import Dict, List

from src.entitie import Drone, Map


class SimulationError(Exception):
    """Levantada quando um movimento viola as regras da simulação."""


class Simulation:
    """Estado e regras da simulação de drones, turno a turno.

    Attributes:
        (privado) _map: O grafo de zonas e conexões.
        (privado) _drones: Todos os drones, na ordem D1..Dn.
        (privado) _turn: Número de turnos já executados.
    """

    def __init__(self, mapa: Map, nb_drones: int) -> None:
        """Cria nb_drones drones (D1..Dn), todos na zona start.

        Args:
            mapa: Map já montado pelo Parser.
            nb_drones: Quantidade de drones (inteiro positivo).
        """
        self._map = mapa
        start = mapa.get_start()
        self._drones: List[Drone] = [
            Drone(f"D{i}", start) for i in range(1, nb_drones + 1)
        ]
        self._turn = 0

    @property
    def turn(self) -> int:
        """Número de turnos já executados (0 antes do primeiro)."""
        return self._turn

    def get_drones(self) -> List[Drone]:
        """Retorna os drones da simulação.

        Returns:
            Uma NOVA lista (cópia) com todos os drones — mexer nela
            não altera a simulação (encapsulamento).
        """
        return list(self._drones)

    def is_finished(self) -> bool:
        """Verifica se todos os drones chegaram à zona end.

        Returns:
            True quando não há mais nenhum drone a ser rastreado.
        """
        return all(drone.is_delivered() for drone in self._drones)

    def zone_occupancy(self) -> Dict[str, int]:
        """Conta quantos drones estão em cada zona agora.

        A contagem é calculada na hora a partir dos drones (em vez
        de um contador guardado), então nunca fica dessincronizada.
        Drones entregues não são mais rastreados (VII.5) e drones em
        trânsito estão na conexão, não numa zona.

        Returns:
            Dict nome_da_zona -> nº de drones. Zonas vazias não
            aparecem.
        """
        ocupacao: Dict[str, int] = {}
        for drone in self._drones:
            if drone.is_delivered() or drone.is_in_transit():
                continue
            nome = drone.current_zone.name
            ocupacao[nome] = ocupacao.get(nome, 0) + 1
        return ocupacao

    def connection_usage(self) -> Dict[str, int]:
        """Conta quantos drones estão em trânsito em cada conexão agora.

        Returns:
            Dict nome_da_conexao -> nº de drones em trânsito nela.
            Conexões vazias não aparecem.
        """
        uso: Dict[str, int] = {}
        for drone in self._drones:
            conn = drone.current_connection
            if conn is None:
                continue
            uso[conn.name] = uso.get(conn.name, 0) + 1
        return uso
