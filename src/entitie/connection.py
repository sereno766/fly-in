"""Módulo Connection.

Define a classe Connection, que representa uma aresta bidirecional
entre duas zonas do grafo de roteamento de drones.
"""

from __future__ import annotations

from .zone import Zone


class Connection:
    """Representa uma conexão (aresta) bidirecional entre duas zonas.

    Attributes:
        zone_a: Uma das zonas ligadas pela conexão.
        zone_b: A outra zona ligada pela conexão.
        max_link_capacity: Número máximo de drones que podem atravessar
            esta conexão simultaneamente (padrão 1).
    """

    def __init__(
        self,
        zone_a: Zone,
        zone_b: Zone,
        max_link_capacity: int = 1,
    ) -> None:
        """Inicializa uma Connection.

        Args:
            zone_a: Uma das zonas ligadas pela conexão.
            zone_b: A outra zona ligada pela conexão.
            max_link_capacity: Máximo de drones simultâneos na conexão
                (padrão 1).

        Raises:
            ValueError: Se max_link_capacity não for um inteiro positivo.
        """
        # Regra do enunciado: max_link_capacity deve ser inteiro positivo
        if max_link_capacity < 1:
            raise ValueError(
                f"max_link_capacity deve ser um inteiro positivo, "
                f"recebido {max_link_capacity}"
            )

        self.zone_a = zone_a
        self.zone_b = zone_b
        self.max_link_capacity = max_link_capacity

    @property
    def name(self) -> str:
        """Nome da conexão no formato 'zona_a-zona_b'.

        É derivado das duas zonas (não é guardado à parte), então
        nunca fica desatualizado. Usado na saída da simulação para
        drones em trânsito rumo a uma zona restricted
        (formato D<ID>-<conexão>).

        Returns:
            Os nomes das duas zonas, na ordem do arquivo, unidos
            por um traço.
        """
        return f"{self.zone_a.name}-{self.zone_b.name}"

    def other_zone(self, zone: Zone) -> Zone:
        """Dada uma das zonas da conexão, retorna a zona do outro lado.

        Args:
            zone: Uma das duas zonas ligadas por esta conexão.

        Returns:
            A zona oposta a "zone" nesta conexão.

        Raises:
            ValueError: Se "zone" não pertencer a esta conexão.
        """
        if zone == self.zone_a:
            return self.zone_b
        if zone == self.zone_b:
            return self.zone_a
        raise ValueError(
            f"Zona '{zone.name}' não pertence a esta conexão "
            f"({self.zone_a.name}-{self.zone_b.name})"
        )

    def connects(self, name1: str, name2: str) -> bool:
        """Verifica se esta conexão liga as duas zonas informadas (por nome).

        A verificação é bidirecional: connects("a", "b") é equivalente
        a connects("b", "a") — isso é o que garante que "a-b" e "b-a"
        sejam tratados como a mesma conexão (regra de parsing).

        Args:
            name1: Nome de uma das zonas.
            name2: Nome da outra zona.

        Returns:
            True se esta conexão liga name1 e name2, em qualquer ordem.
        """
        names = {self.zone_a.name, self.zone_b.name}
        return names == {name1, name2}

    def is_full(self, current: int) -> bool:
        """Verifica se a conexão atingiu sua capacidade de travessia.

        Args:
            current: Número de drones atravessando a conexão no momento.

        Returns:
            True se a conexão não pode aceitar mais um drone agora.
        """
        return current >= self.max_link_capacity

    def __repr__(self) -> str:
        """Retorna uma representação textual inequívoca da conexão (debug)."""
        return (
            f"Connection({self.name}, "
            f"max_link_capacity={self.max_link_capacity})"
        )
