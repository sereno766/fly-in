"""Testes unitários da classe Simulation (estado inicial e consultas)."""

from src.entitie import Connection, Map, Zone, ZoneType
from src.simulation import Simulation


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
