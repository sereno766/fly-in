"""Testes da ReservationTable (agenda de zonas e conexões)."""

from src.entitie import Connection, Zone
from src.reservation import ReservationTable


def test_zona_de_capacidade_1_enche_com_uma_reserva() -> None:
    """Depois de 1 reserva, não cabe mais ninguém naquele turno."""
    agenda = ReservationTable()
    zona = Zone("a", 0, 0)

    assert agenda.zone_free(zona, 1)
    agenda.reserve_zone(zona, 1)
    assert not agenda.zone_free(zona, 1)


def test_max_drones_2_aceita_duas_reservas() -> None:
    """Zona com capacidade 2 só enche na segunda reserva."""
    agenda = ReservationTable()
    zona = Zone("a", 0, 0, max_capacity=2)

    agenda.reserve_zone(zona, 1)
    assert agenda.zone_free(zona, 1)
    agenda.reserve_zone(zona, 1)
    assert not agenda.zone_free(zona, 1)


def test_start_e_end_nunca_enchem() -> None:
    """Start e end têm capacidade ilimitada."""
    agenda = ReservationTable()
    start = Zone("start", 0, 0, is_start=True)
    end = Zone("goal", 1, 0, is_end=True)

    for _ in range(50):
        agenda.reserve_zone(start, 1)
        agenda.reserve_zone(end, 1)

    assert agenda.zone_free(start, 1)
    assert agenda.zone_free(end, 1)


def test_conexao_respeita_max_link_capacity() -> None:
    """Conexão de capacidade 2 aceita 2 travessias no mesmo turno."""
    agenda = ReservationTable()
    conn = Connection(Zone("a", 0, 0), Zone("b", 1, 0), 2)

    agenda.reserve_link(conn, 3)
    assert agenda.link_free(conn, 3)
    agenda.reserve_link(conn, 3)
    assert not agenda.link_free(conn, 3)


def test_turnos_diferentes_nao_se_misturam() -> None:
    """Reservar o turno 1 não ocupa o turno 2."""
    agenda = ReservationTable()
    zona = Zone("a", 0, 0)
    conn = Connection(zona, Zone("b", 1, 0))

    agenda.reserve_zone(zona, 1)
    agenda.reserve_link(conn, 1)

    assert agenda.zone_free(zona, 2)
    assert agenda.link_free(conn, 2)


def test_last_turn_acompanha_a_maior_reserva() -> None:
    """last_turn é o maior turno reservado."""
    agenda = ReservationTable()
    zona = Zone("a", 0, 0)
    conn = Connection(zona, Zone("b", 1, 0))

    assert agenda.last_turn == 0
    agenda.reserve_zone(zona, 4)
    agenda.reserve_link(conn, 2)
    assert agenda.last_turn == 4
