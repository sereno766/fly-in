"""Módulo Map.

Define a classe Map, que representa o grafo próprio de zonas e
conexões da rede de drones (sem usar networkx/graphlib).
"""

from __future__ import annotations

from typing import Dict, List, Optional

from entities import Connection, Zone


class ZoneNotFoundError(Exception):
    """Levantada quando uma zona não é encontrada pelo nome no Map."""


class Map:
    """Representa o grafo de zonas e conexões da rede de drones.

    Estrutura interna (privada, nunca exposta diretamente):
        _zones: mapeia nome -> Zone, para lookup O(1) por nome.
        _adjacency: mapeia nome da zona -> lista de Connections que a
            tocam. Cada Connection aparece em DUAS entradas (uma para
            cada zona que ela liga), pois é bidirecional.
        _start_zone / _end_zone: cache direto da zona inicial/final.
    """

    def __init__(self) -> None:
        """Inicializa um Map vazio (nenhuma zona/conexão ainda)."""
        self._zones: Dict[str, Zone] = {}
        self._adjacency: Dict[str, List[Connection]] = {}
        self._start_zone: Optional[Zone] = None
        self._end_zone: Optional[Zone] = None

    def add_zone(self, zone: Zone) -> None:
        """Adiciona uma zona ao Map.

        Args:
            zone: A zona a ser adicionada.

        Raises:
            ValueError: Se já existir uma zona com o mesmo nome, ou
                se já houver uma start_hub/end_hub definida e a nova
                zona tentar ser outra (regra: exatamente 1 de cada).
        """
        # 1. nome duplicado
        if self.has_zone(zone.name):
            raise ValueError(f"Zona '{zone.name}' já foi adicionada")

        # 2. garantir exatamente 1 start_hub
        if zone.is_start:
            if self._start_zone is not None:
                raise ValueError(
                    "Já existe uma zona start_hub definida "
                    f"('{self._start_zone.name}')"
                )
            self._start_zone = zone

        # 3. garantir exatamente 1 end_hub
        if zone.is_end:
            if self._end_zone is not None:
                raise ValueError(
                    "Já existe uma zona end_hub definida "
                    f"('{self._end_zone.name}')"
                )
            self._end_zone = zone

        # 4. guardar a zona
        self._zones[zone.name] = zone

        # 5. inicializar a lista de adjacência vazia
        self._adjacency[zone.name] = []

    def add_connection(self, conn: Connection) -> None:
        """Adiciona uma conexão entre duas zonas já existentes no Map.

        Args:
            conn: A conexão a ser adicionada. zone_a e zone_b devem
                já ter sido adicionadas via add_zone().

        Raises:
            ValueError: Se zone_a ou zone_b não existirem ainda no
                Map (regra do parser: conexões só ligam zonas já
                definidas anteriormente).
        """
        if not self.has_zone(conn.zone_a.name):
            raise ValueError(
                f"Não é possível conectar: zona '{conn.zone_a.name}' "
                "ainda não foi definida"
            )
        if not self.has_zone(conn.zone_b.name):
            raise ValueError(
                f"Não é possível conectar: zona '{conn.zone_b.name}' "
                "ainda não foi definida"
            )

        # a MESMA instância de conn entra nos dois lados — é o que
        # mantém a conexão consistente (bidirecional) sem duplicar dados
        self._adjacency[conn.zone_a.name].append(conn)
        self._adjacency[conn.zone_b.name].append(conn)

    def has_zone(self, name: str) -> bool:
        """Verifica se existe uma zona com o nome informado.

        Args:
            name: Nome da zona a procurar.

        Returns:
            True se a zona existe no Map.
        """
        return name in self._zones

    def get_zone(self, name: str) -> Zone:
        """Retorna a zona com o nome informado.

        Args:
            name: Nome da zona a buscar.

        Returns:
            A Zone correspondente.

        Raises:
            ZoneNotFoundError: Se não existir zona com esse nome.
        """
        try:
            return self._zones[name]
        except KeyError:
            raise ZoneNotFoundError(
                f"Nenhuma zona encontrada com o nome '{name}'"
            ) from None

    def get_neighbors(self, zone_name: str) -> List[Connection]:
        """Retorna as conexões que tocam a zona informada.

        Args:
            zone_name: Nome da zona cujas conexões você quer ver.

        Returns:
            Uma NOVA lista (cópia) com as Connections dessa zona —
            nunca a lista interna original (encapsulamento).

        Raises:
            ZoneNotFoundError: Se a zona não existir no Map.
        """
        # valida existência (reaproveita get_zone, que já levanta o erro certo)
        self.get_zone(zone_name)
        return list(self._adjacency[zone_name])

    def get_start(self) -> Zone:
        """Retorna a zona inicial (start_hub) do Map.

        Returns:
            A Zone marcada como is_start=True.

        Raises:
            ValueError: Se nenhuma zona start_hub foi definida ainda.
        """
        if self._start_zone is None:
            raise ValueError("Nenhuma zona start_hub foi definida no Map")
        return self._start_zone

    def get_end(self) -> Zone:
        """Retorna a zona final (end_hub) do Map.

        Returns:
            A Zone marcada como is_end=True.

        Raises:
            ValueError: Se nenhuma zona end_hub foi definida ainda.
        """
        if self._end_zone is None:
            raise ValueError("Nenhuma zona end_hub foi definida no Map")
        return self._end_zone

    def __repr__(self) -> str:
        """Retorna uma representação textual inequívoca do Map (debug)."""
        n_connections = sum(len(v) for v in self._adjacency.values()) // 2
        return (
            f"Map(zonas={len(self._zones)}, conexoes={n_connections}, "
            f"start={self._start_zone.name if self._start_zone else None}, "
            f"end={self._end_zone.name if self._end_zone else None})"
        )