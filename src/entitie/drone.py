"""Módulo Drone.

Define o enum DroneStatus e a classe Drone, que representa o estado
individual de um drone durante a simulação.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from .zone import Zone


class DroneStatus(Enum):
    """Status possíveis de um drone durante a simulação."""

    WAITING = "waiting"          # esperando (sem mover neste turno)
    MOVING = "moving"            # se movendo para uma zona normal
    IN_TRANSIT = "in_transit"    # em trânsito numa conexão p/ zona restricted
    DELIVERED = "delivered"      # chegou na zona end, não é mais rastreado


class Drone:
    """Representa o estado individual de um drone na simulação.

    Attributes:
        drone_id: Identificador único do drone (ex.: "D1", "D2").
        current_zone: Zona em que o drone está localizado no momento.
        status: Status atual do drone (ver DroneStatus).
        path_history: Lista de nomes de zonas/conexões já visitadas,
            na ordem em que o drone passou por elas.
        turns_taken: Número total de turnos que o drone já usou.
        transit_turns_left: Turnos restantes até o drone chegar ao
            destino, quando está atravessando uma conexão restricted
            (2 turnos). None quando o drone não está em trânsito.
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
        self.transit_turns_left: Optional[int] = None

    def move_to(self, zone: Zone) -> None:
        """Move o drone para uma nova zona, atualizando seu estado.

        Se a zona de destino for RESTRICTED, o drone entra em trânsito
        (IN_TRANSIT) e deve levar exatamente 2 turnos para chegar —
        sem poder esperar no meio do caminho (regra VII.3). Para as
        demais zonas, o movimento é imediato (MOVING).

        Args:
            zone: Zona de destino do movimento.
        """
        # zona restricted: entra em trânsito por 2 turnos (regra do enunciado)
        cost = zone.movement_cost()
        if cost == 2:
            self.status = DroneStatus.IN_TRANSIT
            self.transit_turns_left = 2
        else:
            self.status = DroneStatus.MOVING
            self.transit_turns_left = None

        self.current_zone = zone
        self.path_history.append(zone.name)
        self.turns_taken += cost

        # se a zona de destino for a end_hub, marca como entregue
        if zone.is_end:
            self.mark_delivered()

    def mark_delivered(self) -> None:
        """Marca o drone como entregue (chegou à zona end).

        Drones entregues não são mais rastreados na saída da simulação
        (regra VII.5).
        """
        self.status = DroneStatus.DELIVERED
        self.transit_turns_left = None

    def is_delivered(self) -> bool:
        """Verifica se o drone já chegou à zona final.

        Returns:
            True se o status do drone for DELIVERED.
        """
        return self.status is DroneStatus.DELIVERED

    def __repr__(self) -> str:
        """Retorna uma representação textual inequívoca do drone (debug)."""
        return (
            f"Drone(id={self.drone_id!r}, "
            f"zone={self.current_zone.name!r}, "
            f"status={self.status.value})"
        )
