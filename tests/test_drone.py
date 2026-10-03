"""Testes unitários da classe Drone.

Cobre movimento normal, o trânsito em 2 turnos rumo a zonas
restricted (regra VII.3) e a entrega na zona end.
"""

import pytest

from src.entitie import Connection, Drone, DroneStatus, Zone, ZoneType


def _cenario() -> tuple[Zone, Zone, Zone, Zone]:
    """Cria start, uma zona normal, uma restricted e a end.

    Returns:
        Tupla (start, normal, restricted, end).
    """
    start = Zone("start", 0, 0, is_start=True)
    normal = Zone("n", 1, 0)
    restricted = Zone("r", 2, 0, zone_type=ZoneType.RESTRICTED)
    end = Zone("goal", 3, 0, is_end=True)
    return start, normal, restricted, end


def test_drone_comeca_esperando_na_start() -> None:
    """Um drone novo está na start, parado, sem trânsito."""
    start, _, _, _ = _cenario()
    drone = Drone("D1", start)

    assert drone.current_zone is start
    assert drone.status is DroneStatus.WAITING
    assert drone.turns_taken == 0
    assert not drone.is_in_transit()


def test_move_to_zona_normal_custa_um_turno() -> None:
    """move_to troca a zona atual e conta 1 turno."""
    start, normal, _, _ = _cenario()
    drone = Drone("D1", start)

    drone.move_to(normal)

    assert drone.current_zone is normal
    assert drone.turns_taken == 1
    assert drone.path_history == ["start", "n"]


def test_restricted_leva_dois_turnos_passando_pela_conexao() -> None:
    """1º turno: na conexão (ainda na origem). 2º turno: chega."""
    start, normal, restricted, _ = _cenario()
    conn = Connection(normal, restricted)
    drone = Drone("D1", start)
    drone.move_to(normal)

    drone.start_transit(conn, restricted)

    assert drone.is_in_transit()
    assert drone.status is DroneStatus.IN_TRANSIT
    assert drone.current_zone is normal          # ainda não chegou
    assert drone.current_connection is conn

    drone.finish_transit()

    assert not drone.is_in_transit()
    assert drone.current_zone is restricted
    assert drone.transit_target is None
    assert drone.turns_taken == 3                # 1 normal + 2 restricted
    assert drone.path_history == ["start", "n", "n-r", "r"]


def test_chegar_na_end_marca_como_entregue() -> None:
    """move_to na end_hub marca o drone como entregue."""
    start, _, _, end = _cenario()
    drone = Drone("D1", start)

    drone.move_to(end)

    assert drone.is_delivered()


def test_finish_transit_sem_transito_levanta_value_error() -> None:
    """Não dá para concluir um trânsito que não começou."""
    start, _, _, _ = _cenario()
    drone = Drone("D1", start)

    with pytest.raises(ValueError):
        drone.finish_transit()


def test_start_transit_duas_vezes_levanta_value_error() -> None:
    """Um drone em trânsito não pode começar outro trânsito."""
    start, normal, restricted, _ = _cenario()
    conn = Connection(normal, restricted)
    drone = Drone("D1", normal)
    drone.start_transit(conn, restricted)

    with pytest.raises(ValueError):
        drone.start_transit(conn, restricted)
