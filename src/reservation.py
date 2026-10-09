"""Módulo ReservationTable.

Define a tabela de reservas usada pelo planejamento: a "agenda" do
que os drones já planejados ocupam em cada turno.
"""

from __future__ import annotations

from typing import Dict, Tuple

from src.entitie import Connection, Zone


class ReservationTable:
    """Agenda de ocupação de zonas e conexões, turno a turno.

    Attributes:
        (privado) _zones: (nome da zona, turno) -> drones reservados
            ali naquele turno.
        (privado) _links: (nome da conexão, turno) -> drones que
            COMEÇAM a atravessar a conexão naquele turno.
        (privado) _last_turn: Maior turno com alguma reserva.
    """

    def __init__(self) -> None:
        """Cria uma agenda vazia."""
        self._zones: Dict[Tuple[str, int], int] = {}
        self._links: Dict[Tuple[str, int], int] = {}
        self._last_turn = 0

    @property
    def last_turn(self) -> int:
        """Maior turno que tem alguma reserva (0 se a agenda está vazia)."""
        return self._last_turn

    def zone_free(self, zona: Zone, turno: int) -> bool:
        """Verifica se cabe mais um drone na zona naquele turno.

        Args:
            zona: Zona a verificar.
            turno: Turno a verificar.

        Returns:
            True se as reservas + 1 cabem (start e end sempre cabem).
        """
        return zona.fits(self._zones.get((zona.name, turno), 0) + 1)

    def link_free(self, conn: Connection, turno: int) -> bool:
        """Verifica se mais um drone pode começar a atravessar a conexão.

        Args:
            conn: Conexão a verificar.
            turno: Turno em que o drone começaria a travessia.

        Returns:
            True se ainda há capacidade (max_link_capacity) naquele turno.
        """
        usados = self._links.get((conn.name, turno), 0)
        return usados < conn.max_link_capacity

    def reserve_zone(self, zona: Zone, turno: int) -> None:
        """Reserva uma vaga na zona naquele turno.

        Args:
            zona: Zona a reservar.
            turno: Turno da reserva.
        """
        chave = (zona.name, turno)
        self._zones[chave] = self._zones.get(chave, 0) + 1
        self._last_turn = max(self._last_turn, turno)

    def reserve_link(self, conn: Connection, turno: int) -> None:
        """Reserva uma travessia da conexão começando naquele turno.

        Args:
            conn: Conexão a reservar.
            turno: Turno em que a travessia começa.
        """
        chave = (conn.name, turno)
        self._links[chave] = self._links.get(chave, 0) + 1
        self._last_turn = max(self._last_turn, turno)
