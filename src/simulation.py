"""Módulo Simulation.

Define a classe Simulation, o "juiz" da simulação: guarda o estado
de todos os drones, valida e aplica os movimentos de cada turno e
responde perguntas sobre a ocupação de zonas e conexões.

Ela NÃO decide para onde os drones vão — isso é papel do planner.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from src.entitie import Connection, Drone, Map, Zone, ZoneType


class SimulationError(Exception):
    """Levantada quando um movimento viola as regras da simulação."""


class Simulation:
    """Estado e regras da simulação de drones, turno a turno.

    Attributes:
        (privado) _map: O grafo de zonas e conexões.
        (privado) _drones: Todos os drones, na ordem D1..Dn.
        (privado) _by_id: Lookup drone_id -> Drone.
        (privado) _turn: Número de turnos já executados.
        (privado) _last_crossings: drone_id -> nome da conexão que ele
            atravessou (movimento de 1 turno) no último turno.
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
        self._by_id: Dict[str, Drone] = {
            drone.drone_id: drone for drone in self._drones
        }
        self._turn = 0
        self._last_crossings: Dict[str, str] = {}

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
        """Conta o uso de cada conexão no último turno executado.

        Soma os drones que atravessaram a conexão no último turno
        (movimentos de 1 turno) com os que estão em trânsito nela
        agora (rumo a uma zona restricted).

        Returns:
            Dict nome_da_conexao -> nº de drones usando a conexão.
            Conexões sem uso não aparecem.
        """
        uso: Dict[str, int] = {}
        for nome in self._last_crossings.values():
            uso[nome] = uso.get(nome, 0) + 1
        for drone in self._drones:
            conn = drone.current_connection
            if conn is not None:
                uso[conn.name] = uso.get(conn.name, 0) + 1
        return uso

    def apply_turn(self, moves: Dict[str, str]) -> str:
        """Valida e executa um turno da simulação.

        Drones em trânsito chegam à zona restricted automaticamente
        (a chegada é obrigatória, VII.3). Os demais só se movem se
        estiverem em "moves"; quem não aparece fica parado.

        O turno é atômico: TODAS as regras são conferidas antes de
        qualquer drone se mover. Se alguma falhar, nada muda.

        Args:
            moves: drone_id -> nome da zona de destino.

        Returns:
            A linha de saída do turno (ex.: "D1-roof1 D2-hub-roof2"),
            com os movimentos em ordem de drone. Vazia se ninguém
            se moveu.

        Raises:
            SimulationError: Se qualquer movimento violar as regras.
        """
        chegadas = self._validate_arrivals(moves)
        planejados = self._validate_moves(moves)
        self._check_link_capacity(planejados)
        self._check_zone_capacity(chegadas, planejados)

        # tudo válido: aplica (daqui pra baixo nada pode falhar)
        saida: Dict[str, str] = {}
        for drone in chegadas:
            drone.finish_transit()
            saida[drone.drone_id] = drone.current_zone.name

        self._last_crossings = {}
        for drone, conn, destino in planejados:
            if destino.zone_type is ZoneType.RESTRICTED:
                drone.start_transit(conn, destino)
                saida[drone.drone_id] = conn.name
            else:
                drone.move_to(destino)
                saida[drone.drone_id] = destino.name
                self._last_crossings[drone.drone_id] = conn.name

        self._turn += 1
        return " ".join(
            f"{drone.drone_id}-{saida[drone.drone_id]}"
            for drone in self._drones
            if drone.drone_id in saida
        )

    def _validate_arrivals(self, moves: Dict[str, str]) -> List[Drone]:
        """Lista os drones em trânsito, que chegam obrigatoriamente.

        Args:
            moves: Movimentos pedidos para o turno.

        Returns:
            Os drones que estão em trânsito (vão chegar neste turno).

        Raises:
            SimulationError: Se um drone em trânsito for mandado para
                um destino diferente do seu transit_target.
        """
        chegadas: List[Drone] = []
        for drone in self._drones:
            alvo = drone.transit_target
            if alvo is None:
                continue
            pedido = moves.get(drone.drone_id)
            if pedido is not None and pedido != alvo.name:
                raise SimulationError(
                    f"{drone.drone_id} está em trânsito para "
                    f"'{alvo.name}' e não pode ir para '{pedido}'"
                )
            chegadas.append(drone)
        return chegadas

    def _validate_moves(
        self, moves: Dict[str, str]
    ) -> List[Tuple[Drone, Connection, Zone]]:
        """Valida cada movimento pedido, isoladamente.

        Args:
            moves: Movimentos pedidos para o turno.

        Returns:
            Lista (drone, conexão usada, zona destino) dos movimentos
            de drones que NÃO estão em trânsito.

        Raises:
            SimulationError: Drone inexistente ou já entregue, destino
                inexistente, não vizinho ou bloqueado.
        """
        planejados: List[Tuple[Drone, Connection, Zone]] = []
        for drone_id, destino_nome in moves.items():
            drone = self._by_id.get(drone_id)
            if drone is None:
                raise SimulationError(f"drone inexistente: '{drone_id}'")
            if drone.is_delivered():
                raise SimulationError(f"{drone_id} já foi entregue")
            if drone.is_in_transit():
                continue  # já validado em _validate_arrivals

            origem = drone.current_zone.name
            conn = self._map.get_connection(origem, destino_nome)
            if conn is None:
                raise SimulationError(
                    f"{drone_id}: '{destino_nome}' não é vizinha de "
                    f"'{origem}'"
                )
            destino = self._map.get_zone(destino_nome)
            if destino.zone_type is ZoneType.BLOCKED:
                raise SimulationError(
                    f"{drone_id}: zona '{destino_nome}' está bloqueada"
                )
            planejados.append((drone, conn, destino))
        return planejados

    def _check_link_capacity(
        self, planejados: List[Tuple[Drone, Connection, Zone]]
    ) -> None:
        """Confere max_link_capacity das conexões usadas no turno.

        Conta só quem COMEÇA a atravessar neste turno: um drone que
        está chegando de um trânsito já libera a conexão (VII.3).

        Args:
            planejados: Movimentos validados do turno.

        Raises:
            SimulationError: Se alguma conexão passar da capacidade.
        """
        uso: Dict[str, int] = {}
        conexoes: Dict[str, Connection] = {}
        for _, conn, _ in planejados:
            uso[conn.name] = uso.get(conn.name, 0) + 1
            conexoes[conn.name] = conn

        for nome, total in uso.items():
            if total > conexoes[nome].max_link_capacity:
                raise SimulationError(
                    f"conexão '{nome}' com {total} drones "
                    f"(máx {conexoes[nome].max_link_capacity})"
                )

    def _check_zone_capacity(
        self,
        chegadas: List[Drone],
        planejados: List[Tuple[Drone, Connection, Zone]],
    ) -> None:
        """Confere max_drones das zonas no FIM do turno.

        Ocupação final = atual - quem sai + quem chega. Assim, um
        espaço liberado neste turno já pode ser usado neste mesmo
        turno (ex.: uma fila avança um passo por turno).

        Args:
            chegadas: Drones que concluem o trânsito neste turno.
            planejados: Movimentos validados do turno.

        Raises:
            SimulationError: Se alguma zona passar da capacidade.
        """
        ocupacao = self.zone_occupancy()
        for drone, _, destino in planejados:
            ocupacao[drone.current_zone.name] -= 1
            # rumo a restricted: fica na conexão, ainda não chega
            if destino.zone_type is not ZoneType.RESTRICTED:
                ocupacao[destino.name] = ocupacao.get(destino.name, 0) + 1
        for drone in chegadas:
            alvo = drone.transit_target
            if alvo is not None:
                ocupacao[alvo.name] = ocupacao.get(alvo.name, 0) + 1

        for nome, total in ocupacao.items():
            zona = self._map.get_zone(nome)
            if not zona.fits(total):
                raise SimulationError(
                    f"zona '{nome}' com {total} drones "
                    f"(máx {zona.max_capacity})"
                )
