"""Módulo Scheduler.

Define a classe Scheduler, que planeja o caminho de um drone NO
TEMPO (quando ele está em cada zona), respeitando o que os drones
planejados antes dele já reservaram na ReservationTable.

A busca é o mesmo Dijkstra do PathFinder, mas cada estado agora é
(turno, zona) e "esperar parado" também é uma opção.
"""

from __future__ import annotations

import heapq
from typing import Dict, List, Optional, Tuple

from src.entitie import Map, ZoneType
from src.pathfinder import NoPathError, PathFinder
from src.reservation import ReservationTable

# Um passo do caminho no tempo: (turno, nome da zona)
Passo = Tuple[int, str]


class Scheduler:
    """Planeja caminhos no tempo e os converte em movimentos por turno.

    Attributes:
        (privado) _map: O grafo de zonas e conexões.
        (privado) _agenda: Reservas dos drones já planejados.
        (privado) _custo_minimo: Turnos do caminho mais barato da
            start até a end com o mapa vazio (via PathFinder).
    """

    def __init__(self, mapa: Map, agenda: ReservationTable) -> None:
        """Prepara o scheduler e confere se a end é alcançável.

        Args:
            mapa: Map já montado pelo Parser.
            agenda: Tabela de reservas compartilhada entre os drones.

        Raises:
            NoPathError: Se não existir caminho da start até a end
                (grafo desconexo ou só passando por zonas blocked).
        """
        self._map = mapa
        self._agenda = agenda
        caminho = PathFinder(mapa).shortest_path()
        self._custo_minimo = sum(
            mapa.get_zone(nome).movement_cost() for nome in caminho[1:]
        )

    def plan_all(self, nb_drones: int) -> List[Dict[str, str]]:
        """Planeja D1..Dn em ordem, cada um reservando seu caminho.

        Quem planeja primeiro reserva primeiro: cada drone procura o
        caminho que chega mais cedo SEM bater nas reservas dos
        anteriores. Assim os drones se espalham sozinhos por rotas
        paralelas quando a rota curta está cheia, ou esperam a vez.

        Args:
            nb_drones: Quantidade de drones.

        Returns:
            Os movimentos por turno, no formato de apply_turn().
        """
        caminhos: Dict[str, List[Passo]] = {}
        for i in range(1, nb_drones + 1):
            caminho = self.plan_drone()
            self.reserve(caminho)
            caminhos[f"D{i}"] = caminho
        return self.to_moves(caminhos)

    def plan_drone(self) -> List[Passo]:
        """Acha o caminho que chega MAIS CEDO na end, sem conflitos.

        Dijkstra no espaço (turno, zona): o custo de um estado é o
        turno em que o drone chega nele. A chave da fila é
        (turno, -nº_priority), então com o mesmo turno de chegada
        vence o caminho com mais zonas priority.

        Limite: depois de agenda.last_turn o mapa está vazio, então
        esperar na start (ilimitada) até lá e seguir o caminho mínimo
        SEMPRE chega até last_turn + custo_minimo. Estados depois desse
        turno nunca são necessários, e a busca sempre termina.

        Returns:
            O caminho como lista de (turno, zona), de (0, start) até a
            end. Esperas aparecem como a mesma zona em turnos seguidos;
            uma ida para restricted pula de t para t + 2.

        Raises:
            NoPathError: Se nada chegar na end dentro do limite (não
                deveria acontecer; protege contra loop infinito).
        """
        start = self._map.get_start().name
        end = self._map.get_end().name
        limite = self._agenda.last_turn + self._custo_minimo

        inicio: Passo = (0, start)
        melhor: Dict[Passo, int] = {inicio: 0}          # estado -> -prio
        anterior: Dict[Passo, Optional[Passo]] = {inicio: None}
        fila: List[Tuple[int, int, str]] = [(0, 0, start)]

        while fila:
            turno, neg_prio, nome = heapq.heappop(fila)
            if nome == end:
                return self._rebuild((turno, nome), anterior)
            # entrada velha: esse estado já foi alcançado com mais priority
            if neg_prio > melhor[(turno, nome)]:
                continue

            for chegada, destino, ganho in self._options(nome, turno):
                if chegada > limite:
                    continue
                estado = (chegada, destino)
                nova_prio = neg_prio - ganho
                atual = melhor.get(estado)
                if atual is None or nova_prio < atual:
                    melhor[estado] = nova_prio
                    anterior[estado] = (turno, nome)
                    heapq.heappush(fila, (chegada, nova_prio, destino))

        raise NoPathError(
            f"nenhum caminho até '{end}' dentro de {limite} turnos"
        )

    def reserve(self, caminho: List[Passo]) -> None:
        """Registra o caminho de um drone na agenda.

        Para cada passo (t1, z1) -> (t2, z2): o drone ocupa z2 no turno
        t2 e, se mudou de zona, começa a atravessar a conexão z1-z2 no
        turno t1 + 1 (na restricted, t2 = t1 + 2 e no turno t1 + 1 ele
        está na conexão, não numa zona).

        Args:
            caminho: Caminho devolvido por plan_drone().
        """
        for (t1, z1), (t2, z2) in zip(caminho, caminho[1:]):
            self._agenda.reserve_zone(self._map.get_zone(z2), t2)
            if z1 != z2:
                conn = self._map.get_connection(z1, z2)
                if conn is not None:
                    self._agenda.reserve_link(conn, t1 + 1)

    @staticmethod
    def to_moves(caminhos: Dict[str, List[Passo]]) -> List[Dict[str, str]]:
        """Converte os caminhos no formato aceito por apply_turn().

        Args:
            caminhos: drone_id -> caminho no tempo.

        Returns:
            Um dict por turno (índice 0 = turno 1) com drone_id -> zona
            de destino do movimento que COMEÇA naquele turno. Drones
            parados ou chegando de uma restricted não aparecem (a
            chegada é automática no juiz).
        """
        if not caminhos:
            return []
        total = max(caminho[-1][0] for caminho in caminhos.values())
        turnos: List[Dict[str, str]] = [{} for _ in range(total)]
        for drone_id, caminho in caminhos.items():
            for (t1, z1), (_, z2) in zip(caminho, caminho[1:]):
                if z1 != z2:
                    turnos[t1][drone_id] = z2
        return turnos

    def _options(self, nome: str, turno: int) -> List[Tuple[int, str, int]]:
        """Lista o que o drone pode fazer estando em "nome" no "turno".

        Args:
            nome: Zona atual.
            turno: Turno atual.

        Returns:
            Lista de (turno de chegada, zona, 1 se priority senão 0).
            Inclui esperar parado, se a zona ainda couber o drone.
        """
        zona = self._map.get_zone(nome)
        opcoes: List[Tuple[int, str, int]] = []

        # esperar: continuar na mesma zona no turno seguinte
        if self._agenda.zone_free(zona, turno + 1):
            opcoes.append((turno + 1, nome, 0))

        for conn in self._map.get_neighbors(nome):
            destino = conn.other_zone(zona)
            if destino.zone_type is ZoneType.BLOCKED:
                continue
            # a travessia começa no turno seguinte
            if not self._agenda.link_free(conn, turno + 1):
                continue
            # restricted: t + 2 (1 turno na conexão + chegada)
            chegada = turno + destino.movement_cost()
            if not self._agenda.zone_free(destino, chegada):
                continue
            ganho = 1 if destino.zone_type is ZoneType.PRIORITY else 0
            opcoes.append((chegada, destino.name, ganho))
        return opcoes

    @staticmethod
    def _rebuild(
        fim: Passo, anterior: Dict[Passo, Optional[Passo]]
    ) -> List[Passo]:
        """Reconstrói o caminho seguindo "anterior" de trás para frente.

        Args:
            fim: Estado final (turno, zona).
            anterior: Estado -> estado de onde se chegou nele.

        Returns:
            O caminho do início até "fim", em ordem.
        """
        caminho: List[Passo] = []
        atual: Optional[Passo] = fim
        while atual is not None:
            caminho.append(atual)
            atual = anterior[atual]
        caminho.reverse()
        return caminho
