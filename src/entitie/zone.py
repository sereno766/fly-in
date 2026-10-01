"""Módulo Zone.

Define o enum ZoneType e a classe Zone, que representa um único
nó (hub) no grafo de roteamento de drones.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional


class ZoneType(Enum):
    """Tipos de zona válidos aceitos pelo parser do mapa."""

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"


class BlockedZoneError(Exception):
    """Levantada quando movement_cost() é chamado em uma zona bloqueada."""


class Zone:
    """Representa uma única zona (nó) na rede de drones.

    Attributes:
        name: Identificador único da zona.
        x: Coordenada X da zona.
        y: Coordenada Y da zona.
        zone_type: O ZoneType desta zona.
        color: Cor opcional usada na representação visual.
        max_capacity: Número máximo de drones permitidos simultaneamente.
            Ignorado (tratado como ilimitado) quando is_start ou is_end
            é True.
        is_start: True se esta for a única zona start_hub.
        is_end: True se esta for a única zona end_hub.
    """

    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        zone_type: ZoneType = ZoneType.NORMAL,
        color: Optional[str] = None,
        max_capacity: int = 1,
        is_start: bool = False,
        is_end: bool = False,
    ) -> None:
        """Inicializa uma Zone.

        Args:
            name: Identificador único da zona (sem traços ou espaços).
            x: Coordenada X (inteiro).
            y: Coordenada Y (inteiro).
            zone_type: Tipo da zona. Padrão: NORMAL.
            color: String de cor opcional usada na saída visual.
            max_capacity: Máximo de drones simultâneos (padrão 1).
                Ignorado quando is_start ou is_end é True.
            is_start: True se esta for a única zona start_hub.
            is_end: True se esta for a única zona end_hub.

        Raises:
            ValueError: Se max_capacity não for um inteiro positivo.
        """
        # Regra do enunciado: max_drones deve ser inteiro positivo
        if max_capacity < 1:
            raise ValueError(
                f"max_capacity deve ser um inteiro positivo, "
                f"recebido {max_capacity}"
            )

        self.name = name
        self.x = x
        self.y = y
        self.zone_type = zone_type
        self.color = color
        self.max_capacity = max_capacity
        self.is_start = is_start
        self.is_end = is_end

    def movement_cost(self) -> int:
        """Retorna o custo em turnos para entrar nesta zona.

        Returns:
            1 para zonas NORMAL e PRIORITY, 2 para zonas RESTRICTED.

        Raises:
            BlockedZoneError: Se a zona for BLOCKED (não pode ser
                acessada — qualquer caminho que a use é inválido).
        """
        # blocked: inacessível, nunca deveria ser "custada"
        if self.zone_type is ZoneType.BLOCKED:
            raise BlockedZoneError(
                f"Zona '{self.name}' está bloqueada e não pode ser acessada"
            )
        # restricted: custa 2 turnos (regra VII.3 do enunciado)
        if self.zone_type is ZoneType.RESTRICTED:
            return 2
        # normal e priority: custam 1 turno
        return 1

    def is_full(self, current: int) -> bool:
        """Verifica se esta zona atingiu sua capacidade de ocupação.

        As zonas start e end nunca são consideradas cheias: elas têm
        capacidade ilimitada, independente de max_capacity.

        Args:
            current: Número de drones ocupando a zona no momento.

        Returns:
            True se a zona não pode aceitar mais um drone agora.
        """
        # Exceção do enunciado: start e end são ilimitadas
        if self.is_start or self.is_end:
            return False
        return current >= self.max_capacity

    def __eq__(self, other: object) -> bool:
        """Duas zonas são iguais se e somente se têm o mesmo nome."""
        if not isinstance(other, Zone):
            return NotImplemented
        return self.name == other.name

    def __hash__(self) -> int:
        """Gera o hash da Zone a partir do seu nome único."""
        return hash(self.name)

    def __repr__(self) -> str:
        """Retorna uma representação textual inequívoca da zona (debug)."""
        return (
            f"Zone(name={self.name!r}, x={self.x}, y={self.y}, "
            f"zone_type={self.zone_type.value}, "
            f"max_capacity={self.max_capacity})"
        )
