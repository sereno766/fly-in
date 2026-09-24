"""Pacote entities do projeto Fly-in.

Reexporta as classes de dados principais (Zone, Connection, Drone)
para facilitar os imports no resto do projeto.

Exemplo de uso em outro módulo:
    from entities import Zone, ZoneType, Connection, Drone, DroneStatus
"""

from .zone import BlockedZoneError, Zone, ZoneType
from .connection import Connection
from .drone import Drone, DroneStatus

__all__ = [
    "Zone",
    "ZoneType",
    "BlockedZoneError",
    "Connection",
    "Drone",
    "DroneStatus",
]