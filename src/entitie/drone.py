"""Módulo Drone.

Define o enum DroneStatus e a classe Drone, que representa o estado
individual de um drone durante a simulação.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from .connection import Connection
from .zone import Zone


class DroneStatus(Enum):
    """Status possíveis de um drone durante a simulação."""

    WAITING = "waiting"          # parado numa zona (início ou esperando)
    MOVING = "moving"            # acabou de chegar numa zona
    IN_TRANSIT = "in_transit"    # em trânsito numa conexão p/ zona restricted
    DELIVERED = "delivered"      # chegou na zona end, não é mais rastreado


class Drone:
    """Representa o estado individual de um drone na simulação.

    Um movimento para zona restricted leva 2 turnos (regra VII.3):
    no 1º turno o drone fica NA CONEXÃO (start_transit) e no 2º ele
    obrigatoriamente chega na zona (finish_transit). Durante o
    trânsito, current_zone continua sendo a zona de origem.

    Attributes:
        drone_id: Identificador único do drone (ex.: "D1", "D2").
        current_zone: Última zona em que o drone esteve. Durante um
            trânsito, é a zona de ORIGEM (ele ainda não chegou).
        status: Status atual do drone (ver DroneStatus).
        path_history: Lista de nomes de zonas/conexões já visitadas,
            na ordem em que o drone passou por elas.
        turns_taken: Número de turnos em que o drone se moveu.
        current_connection: Conexão onde o drone está em trânsito
            rumo a uma zona restricted. None quando não está.
        transit_target: Zona restricted de destino do trânsito.
            None quando o drone não está em trânsito.
    """

    def __init__(
        self,
        drone_id: str,
        current_zone: Zone,
    ) -> None:
        """Inicializa um Drone na zona inicial (start_hub).

        Args:
            drone_id: Identificador único do drone (ex.: "D1").
            current_zone: Zona onde o drone começa (normalmente a start).
        """
        self.drone_id = drone_id
        self.current_zone = current_zone
        self.status = DroneStatus.WAITING
        self.path_history: List[str] = [current_zone.name]
        self.turns_taken = 0
        self.current_connection: Optional[Connection] = None
        self.transit_target: Optional[Zone] = None

    def move_to(self, zone: Zone) -> None:
        """Move o drone para uma zona adjacente em 1 turno.

        Usado para movimentos normais (zonas normal/priority/end) e,
        internamente, pelo finish_transit() na chegada à restricted.
        Se a zona for a end_hub, o drone é marcado como entregue.

        Args:
            zone: Zona de destino do movimento.
        """
        self.current_zone = zone
        self.path_history.append(zone.name)
        self.turns_taken += 1
        self.status = DroneStatus.MOVING

        if zone.is_end:
            self.mark_delivered()

    def start_transit(self, conn: Connection, target: Zone) -> None:
        """Começa a travessia de uma conexão rumo a uma zona restricted.

        É o 1º dos 2 turnos do movimento: o drone sai da zona atual e
        passa a ocupar a conexão. No turno seguinte ele DEVE chegar
        (finish_transit) — não pode esperar na conexão.

        Args:
            conn: Conexão que o drone vai atravessar.
            target: Zona restricted de destino (do outro lado de conn).

        Raises:
            ValueError: Se o drone já estiver em trânsito.
        """
        if self.is_in_transit():
            raise ValueError(f"Drone {self.drone_id} já está em trânsito")

        self.current_connection = conn
        self.transit_target = target
        self.path_history.append(conn.name)
        self.turns_taken += 1
        self.status = DroneStatus.IN_TRANSIT

    def finish_transit(self) -> None:
        """Conclui a travessia: o drone chega na zona restricted.

        É o 2º turno do movimento iniciado por start_transit().

        Raises:
            ValueError: Se o drone não estiver em trânsito.
        """
        target = self.transit_target
        if target is None:
            raise ValueError(
                f"Drone {self.drone_id} não está em trânsito"
            )

        self.current_connection = None
        self.transit_target = None
        self.move_to(target)

    def is_in_transit(self) -> bool:
        """Verifica se o drone está atravessando uma conexão.

        Returns:
            True se o drone estiver numa conexão rumo a uma restricted.
        """
        return self.current_connection is not None

    def mark_delivered(self) -> None:
        """Marca o drone como entregue (chegou à zona end).

        Drones entregues não são mais rastreados na saída da simulação
        (regra VII.5).
        """
        self.status = DroneStatus.DELIVERED
        self.current_connection = None
        self.transit_target = None

    def is_delivered(self) -> bool:
        """Verifica se o drone já chegou à zona final.

        Returns:
            True se o status do drone for DELIVERED.
        """
        return self.status is DroneStatus.DELIVERED

    def __repr__(self) -> str:
        """Retorna uma representação textual inequívoca do drone (debug)."""
        where = (
            self.current_connection.name
            if self.current_connection is not None
            else self.current_zone.name
        )
        return (
            f"Drone(id={self.drone_id!r}, "
            f"at={where!r}, "
            f"status={self.status.value})"
        )
