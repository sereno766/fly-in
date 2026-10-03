"""Testes da classe Simulation: estado inicial, consultas e apply_turn()."""

from pathlib import Path

import pytest

from src.entitie import Connection, Map, Zone, ZoneType
from src.parser import Parser
from src.simulation import Simulation, SimulationError


def _mapa_linear() -> Map:
    """Monta start - a - r(restricted) - goal, ligados em linha.

    Returns:
        O Map montado.
    """
    mapa = Map()
    start = Zone("start", 0, 0, is_start=True)
    a = Zone("a", 1, 0)
    r = Zone("r", 2, 0, zone_type=ZoneType.RESTRICTED)
    goal = Zone("goal", 3, 0, is_end=True)
    for zona in (start, a, r, goal):
        mapa.add_zone(zona)
    mapa.add_connection(Connection(start, a))
    mapa.add_connection(Connection(a, r))
    mapa.add_connection(Connection(r, goal))
    return mapa


def test_drones_comecam_todos_na_start() -> None:
    """D1..Dn são criados na ordem, todos na start."""
    sim = Simulation(_mapa_linear(), 3)

    drones = sim.get_drones()

    assert [d.drone_id for d in drones] == ["D1", "D2", "D3"]
    assert all(d.current_zone.name == "start" for d in drones)
    assert sim.turn == 0


def test_ocupacao_inicial_tudo_na_start() -> None:
    """No início, só a start está ocupada e nenhuma conexão está em uso."""
    sim = Simulation(_mapa_linear(), 3)

    assert sim.zone_occupancy() == {"start": 3}
    assert sim.connection_usage() == {}


def test_simulacao_nao_comeca_terminada() -> None:
    """Com drones na start, a simulação ainda não terminou."""
    sim = Simulation(_mapa_linear(), 2)

    assert not sim.is_finished()


def test_get_drones_devolve_copia() -> None:
    """Esvaziar a lista devolvida não remove drones da simulação."""
    sim = Simulation(_mapa_linear(), 2)

    sim.get_drones().clear()

    assert len(sim.get_drones()) == 2


def test_ocupacao_ignora_entregues_e_conta_transito_na_conexao() -> None:
    """Entregue some da contagem; em trânsito conta na conexão."""
    mapa = _mapa_linear()
    sim = Simulation(mapa, 3)
    d1, d2, _ = sim.get_drones()
    a, r = mapa.get_zone("a"), mapa.get_zone("r")

    d1.move_to(mapa.get_end())                    # entregue
    d2.move_to(a)
    conn_ar = next(c for c in mapa.get_neighbors("a") if c.connects("a", "r"))
    d2.start_transit(conn_ar, r)

    assert sim.zone_occupancy() == {"start": 1}
    assert sim.connection_usage() == {"a-r": 1}


def test_termina_quando_todos_entregues() -> None:
    """is_finished() vira True quando todo drone chega na end."""
    mapa = _mapa_linear()
    sim = Simulation(mapa, 2)

    for drone in sim.get_drones():
        drone.move_to(mapa.get_end())

    assert sim.is_finished()


# --------------------------------------------------------------------------
# apply_turn(): o juiz
# --------------------------------------------------------------------------


def _sim(tmp_path: Path, conteudo: str) -> Simulation:
    """Parseia um mapa em texto e cria a Simulation.

    Args:
        tmp_path: Diretório temporário do pytest.
        conteudo: Conteúdo do arquivo de mapa.

    Returns:
        A Simulation pronta, com nb_drones do próprio mapa.
    """
    arquivo = tmp_path / "mapa.txt"
    arquivo.write_text(conteudo, encoding="utf-8")
    mapa, nb_drones = Parser(str(arquivo)).parse()
    return Simulation(mapa, nb_drones)


LINHA = (
    "nb_drones: 3\n"
    "start_hub: start 0 0\n"
    "hub: a 1 0\n"
    "hub: b 2 0\n"
    "end_hub: goal 3 0\n"
    "connection: start-a\n"
    "connection: a-b\n"
    "connection: b-goal\n"
)


def test_fila_avanca_um_passo_por_turno(tmp_path: Path) -> None:
    """Espaço liberado no turno pode ser usado no mesmo turno (VII.3)."""
    sim = _sim(tmp_path, LINHA)

    assert sim.apply_turn({"D1": "a"}) == "D1-a"
    assert sim.apply_turn({"D1": "b", "D2": "a"}) == "D1-b D2-a"
    assert sim.apply_turn(
        {"D1": "goal", "D2": "b", "D3": "a"}
    ) == "D1-goal D2-b D3-a"
    assert sim.apply_turn({"D2": "goal", "D3": "b"}) == "D2-goal D3-b"
    assert sim.apply_turn({"D3": "goal"}) == "D3-goal"

    assert sim.is_finished()
    assert sim.turn == 5


def test_drones_parados_sao_omitidos_da_saida(tmp_path: Path) -> None:
    """Turno sem movimentos gera linha vazia, mas conta como turno."""
    sim = _sim(tmp_path, LINHA)

    assert sim.apply_turn({}) == ""
    assert sim.turn == 1


def test_saida_em_ordem_de_drone(tmp_path: Path) -> None:
    """A linha sai em ordem D1, D2... mesmo se o dict vier fora de ordem."""
    sim = _sim(tmp_path, LINHA)
    sim.apply_turn({"D1": "a"})

    assert sim.apply_turn({"D2": "a", "D1": "b"}) == "D1-b D2-a"


def test_dois_drones_na_mesma_zona_de_capacidade_1(tmp_path: Path) -> None:
    """Zona com max_drones=1 não aceita 2 drones (VII.2)."""
    conteudo = LINHA.replace(
        "connection: start-a\n",
        "connection: start-a [max_link_capacity=2]\n",
    )
    sim = _sim(tmp_path, conteudo)

    with pytest.raises(SimulationError, match="zona 'a'"):
        sim.apply_turn({"D1": "a", "D2": "a"})


def test_turno_invalido_nao_altera_nada(tmp_path: Path) -> None:
    """Se uma regra falha, nenhum drone se move (turno atômico)."""
    sim = _sim(tmp_path, LINHA)

    with pytest.raises(SimulationError):
        sim.apply_turn({"D1": "a", "D2": "goal"})   # D2: goal não é vizinha

    assert sim.turn == 0
    assert sim.zone_occupancy() == {"start": 3}


def test_zona_com_max_drones_2_aceita_dois(tmp_path: Path) -> None:
    """max_drones=2 e max_link_capacity=2 deixam 2 drones entrarem."""
    conteudo = (
        LINHA.replace("hub: a 1 0\n", "hub: a 1 0 [max_drones=2]\n")
        .replace(
            "connection: start-a\n",
            "connection: start-a [max_link_capacity=2]\n",
        )
    )
    sim = _sim(tmp_path, conteudo)

    assert sim.apply_turn({"D1": "a", "D2": "a"}) == "D1-a D2-a"
    assert sim.zone_occupancy()["a"] == 2


def test_capacidade_de_conexao(tmp_path: Path) -> None:
    """Conexão com capacidade 1 não deixa 2 drones atravessarem juntos."""
    conteudo = LINHA.replace("hub: a 1 0\n", "hub: a 1 0 [max_drones=2]\n")
    sim = _sim(tmp_path, conteudo)

    with pytest.raises(SimulationError, match="conexão 'start-a'"):
        sim.apply_turn({"D1": "a", "D2": "a"})


def test_troca_de_lugar_bloqueada_pela_conexao(tmp_path: Path) -> None:
    """Dois drones trocando de zona usam a mesma conexão: capacidade 1."""
    sim = _sim(tmp_path, LINHA)
    sim.apply_turn({"D1": "a"})
    sim.apply_turn({"D1": "b", "D2": "a"})

    with pytest.raises(SimulationError, match="conexão 'a-b'"):
        sim.apply_turn({"D1": "a", "D2": "b"})


def test_zona_bloqueada_e_inacessivel(tmp_path: Path) -> None:
    """Nenhum drone pode entrar numa zona blocked."""
    conteudo = LINHA.replace("hub: a 1 0\n", "hub: a 1 0 [zone=blocked]\n")
    sim = _sim(tmp_path, conteudo)

    with pytest.raises(SimulationError, match="bloqueada"):
        sim.apply_turn({"D1": "a"})


def test_destino_nao_vizinho(tmp_path: Path) -> None:
    """Só é possível ir para uma zona conectada à atual."""
    sim = _sim(tmp_path, LINHA)

    with pytest.raises(SimulationError, match="não é vizinha"):
        sim.apply_turn({"D1": "b"})


def test_drone_inexistente_ou_entregue(tmp_path: Path) -> None:
    """Ids desconhecidos e drones já entregues são recusados."""
    sim = _sim(tmp_path, LINHA)

    with pytest.raises(SimulationError, match="inexistente"):
        sim.apply_turn({"D9": "a"})

    sim.apply_turn({"D1": "a"})
    sim.apply_turn({"D1": "b"})
    sim.apply_turn({"D1": "goal"})
    with pytest.raises(SimulationError, match="entregue"):
        sim.apply_turn({"D1": "b"})


# --------------------------------------------------------------------------
# Zonas restricted (2 turnos)
# --------------------------------------------------------------------------


RESTRITO = (
    "nb_drones: 2\n"
    "start_hub: start 0 0\n"
    "hub: r 1 0 [zone=restricted max_drones=2]\n"
    "end_hub: goal 2 0\n"
    "connection: start-r\n"
    "connection: r-goal [max_link_capacity=2]\n"
)


def test_exemplo_do_enunciado_fila_na_conexao_restricted(
    tmp_path: Path,
) -> None:
    """Exemplo VII.3: D2 começa a travessia no turno em que D1 chega."""
    sim = _sim(tmp_path, RESTRITO)

    assert sim.apply_turn({"D1": "r"}) == "D1-start-r"
    assert sim.connection_usage() == {"start-r": 1}

    # D1 chega sozinho (obrigatório) e libera a conexão para D2
    assert sim.apply_turn({"D2": "r"}) == "D1-r D2-start-r"
    assert sim.apply_turn({}) == "D2-r"
    assert sim.zone_occupancy() == {"r": 2}


def test_restricted_conta_dois_turnos_no_drone(tmp_path: Path) -> None:
    """Entrar na restricted custa 2 turnos."""
    sim = _sim(tmp_path, RESTRITO)
    sim.apply_turn({"D1": "r"})
    sim.apply_turn({})

    d1 = sim.get_drones()[0]
    assert d1.current_zone.name == "r"
    assert d1.turns_taken == 2


def test_transito_nao_pode_mudar_de_destino(tmp_path: Path) -> None:
    """Drone na conexão não pode esperar nem ir para outro lugar."""
    sim = _sim(tmp_path, RESTRITO)
    sim.apply_turn({"D1": "r"})

    with pytest.raises(SimulationError, match="em trânsito"):
        sim.apply_turn({"D1": "start"})


def test_chegada_em_restricted_lotada_e_erro(tmp_path: Path) -> None:
    """Se a restricted encher, a chegada obrigatória é inválida."""
    conteudo = (
        RESTRITO.replace("[zone=restricted max_drones=2]", "[zone=restricted]")
        .replace("connection: start-r\n",
                 "connection: start-r [max_link_capacity=2]\n")
    )
    sim = _sim(tmp_path, conteudo)
    sim.apply_turn({"D1": "r", "D2": "r"})   # os dois na conexão

    with pytest.raises(SimulationError, match="zona 'r'"):
        sim.apply_turn({})                    # chegariam 2 numa zona de 1


def test_connection_usage_mostra_ultimo_turno(tmp_path: Path) -> None:
    """Base do --capacity-info: quem atravessou no último turno."""
    sim = _sim(tmp_path, LINHA)
    sim.apply_turn({"D1": "a"})

    assert sim.connection_usage() == {"start-a": 1}

    sim.apply_turn({})
    assert sim.connection_usage() == {}


def test_mapas_oficiais_easy_rodam_com_movimentos_na_mao(
    tmp_path: Path,
) -> None:
    """Mapa easy/01 do subject: 2 drones em fila chegam em 4 turnos."""
    raiz = Path(__file__).resolve().parents[1]
    mapa, nb = Parser(str(raiz / "maps/easy/01_linear_path.txt")).parse()
    sim = Simulation(mapa, nb)

    linhas = [
        sim.apply_turn({"D1": "waypoint1"}),
        sim.apply_turn({"D1": "waypoint2", "D2": "waypoint1"}),
        sim.apply_turn({"D1": "goal", "D2": "waypoint2"}),
        sim.apply_turn({"D2": "goal"}),
    ]

    assert linhas[-1] == "D2-goal"
    assert sim.is_finished()
    assert sim.turn == 4      # = ótimo do subject
