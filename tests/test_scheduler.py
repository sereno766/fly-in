"""Testes do Scheduler: caminhos no tempo, reservas e o juiz."""

from pathlib import Path
from typing import Dict, List, Tuple

import pytest

from src.entitie import Map
from src.parser import Parser
from src.pathfinder import NoPathError
from src.reservation import ReservationTable
from src.scheduler import Passo, Scheduler
from src.simulation import Simulation

RAIZ = Path(__file__).resolve().parents[1]


def _mapa(tmp_path: Path, conteudo: str) -> Tuple[Map, int]:
    """Parseia um mapa escrito em texto.

    Args:
        tmp_path: Diretório temporário do pytest.
        conteudo: Conteúdo do arquivo de mapa.

    Returns:
        Tupla (mapa, nb_drones).
    """
    arquivo = tmp_path / "mapa.txt"
    arquivo.write_text(conteudo, encoding="utf-8")
    return Parser(str(arquivo)).parse()


def _planejar(mapa: Map, nb: int) -> Dict[str, List[Passo]]:
    """Planeja D1..Dn em ordem, cada um reservando seu caminho.

    Args:
        mapa: Mapa parseado.
        nb: Quantidade de drones.

    Returns:
        drone_id -> caminho no tempo.
    """
    scheduler = Scheduler(mapa, ReservationTable())
    caminhos: Dict[str, List[Passo]] = {}
    for i in range(1, nb + 1):
        caminho = scheduler.plan_drone()
        scheduler.reserve(caminho)
        caminhos[f"D{i}"] = caminho
    return caminhos


def _juiz(mapa: Map, nb: int, moves: List[Dict[str, str]]) -> List[str]:
    """Executa os movimentos no juiz, que valida cada turno.

    Args:
        mapa: Mapa parseado.
        nb: Quantidade de drones.
        moves: Movimentos por turno.

    Returns:
        As linhas de saída de cada turno.
    """
    sim = Simulation(mapa, nb)
    linhas = [sim.apply_turn(m) for m in moves]
    assert sim.is_finished()
    return linhas


LINHA = (
    "nb_drones: 2\n"
    "start_hub: start 0 0\n"
    "hub: a 1 0\n"
    "end_hub: goal 2 0\n"
    "connection: start-a\n"
    "connection: a-goal\n"
)


def test_um_drone_vai_direto(tmp_path: Path) -> None:
    """Sem outros drones, o caminho no tempo não tem esperas."""
    mapa, _ = _mapa(tmp_path, LINHA)

    caminho = Scheduler(mapa, ReservationTable()).plan_drone()

    assert caminho == [(0, "start"), (1, "a"), (2, "goal")]


def test_segundo_drone_espera_a_vaga(tmp_path: Path) -> None:
    """Zona 'a' tem capacidade 1: D2 espera 1 turno na start."""
    mapa, nb = _mapa(tmp_path, LINHA)

    caminhos = _planejar(mapa, nb)

    assert caminhos["D1"] == [(0, "start"), (1, "a"), (2, "goal")]
    assert caminhos["D2"] == [(0, "start"), (1, "start"), (2, "a"),
                              (3, "goal")]


def test_to_moves_e_juiz_aceitam_o_plano(tmp_path: Path) -> None:
    """Os movimentos gerados passam por todas as regras do juiz."""
    mapa, nb = _mapa(tmp_path, LINHA)

    moves = Scheduler.to_moves(_planejar(mapa, nb))

    assert moves == [{"D1": "a"}, {"D1": "goal", "D2": "a"},
                     {"D2": "goal"}]
    assert _juiz(mapa, nb, moves) == ["D1-a", "D1-goal D2-a", "D2-goal"]


def test_restricted_leva_dois_turnos(tmp_path: Path) -> None:
    """Ida para restricted pula de t para t + 2 e sai pela conexão."""
    mapa, nb = _mapa(tmp_path, (
        "nb_drones: 1\n"
        "start_hub: start 0 0\n"
        "hub: r 1 0 [zone=restricted]\n"
        "end_hub: goal 2 0\n"
        "connection: start-r\n"
        "connection: r-goal\n"
    ))

    caminhos = _planejar(mapa, nb)
    moves = Scheduler.to_moves(caminhos)

    assert caminhos["D1"] == [(0, "start"), (2, "r"), (3, "goal")]
    assert _juiz(mapa, nb, moves) == ["D1-start-r", "D1-r", "D1-goal"]


def test_fila_na_conexao_restricted_exemplo_do_enunciado(
    tmp_path: Path,
) -> None:
    """VII.3: D2 começa a travessia no turno em que D1 chega."""
    mapa, nb = _mapa(tmp_path, (
        "nb_drones: 2\n"
        "start_hub: start 0 0\n"
        "hub: r 1 0 [zone=restricted max_drones=2]\n"
        "end_hub: goal 2 0\n"
        "connection: start-r\n"
        "connection: r-goal\n"
    ))

    linhas = _juiz(mapa, nb, Scheduler.to_moves(_planejar(mapa, nb)))

    assert linhas[:2] == ["D1-start-r", "D1-r D2-start-r"]


def test_desvia_de_blocked(tmp_path: Path) -> None:
    """A busca no tempo também nunca entra em zona blocked."""
    mapa, nb = _mapa(tmp_path, (
        "nb_drones: 1\n"
        "start_hub: start 0 0\n"
        "hub: muro 1 0 [zone=blocked]\n"
        "hub: desvio 1 1\n"
        "end_hub: goal 2 0\n"
        "connection: start-muro\n"
        "connection: muro-goal\n"
        "connection: start-desvio\n"
        "connection: desvio-goal\n"
    ))

    caminho = _planejar(mapa, nb)["D1"]

    assert [zona for _, zona in caminho] == ["start", "desvio", "goal"]


def test_prefere_priority_no_empate(tmp_path: Path) -> None:
    """Chegando no mesmo turno, prefere passar pela priority."""
    mapa, nb = _mapa(tmp_path, (
        "nb_drones: 1\n"
        "start_hub: start 0 0\n"
        "hub: comum 1 0\n"
        "hub: vip 1 1 [zone=priority]\n"
        "end_hub: goal 2 0\n"
        "connection: start-comum\n"
        "connection: comum-goal\n"
        "connection: start-vip\n"
        "connection: vip-goal\n"
    ))

    caminho = _planejar(mapa, nb)["D1"]

    assert [zona for _, zona in caminho] == ["start", "vip", "goal"]


def test_mapa_oficial_easy_01_no_otimo() -> None:
    """easy/01 (2 drones em linha): 4 turnos, validados pelo juiz."""
    mapa, nb = Parser(str(RAIZ / "maps/easy/01_linear_path.txt")).parse()

    linhas = _juiz(mapa, nb, Scheduler.to_moves(_planejar(mapa, nb)))

    assert len(linhas) == 4


# --------------------------------------------------------------------------
# plan_all(): distribuição de D1..Dn
# --------------------------------------------------------------------------


def test_drones_se_dividem_entre_rotas_paralelas(tmp_path: Path) -> None:
    """Duas rotas iguais de capacidade 1: D1 e D2 saem juntos, uma cada."""
    mapa, nb = _mapa(tmp_path, (
        "nb_drones: 2\n"
        "start_hub: start 0 0\n"
        "hub: cima 1 1\n"
        "hub: baixo 1 -1\n"
        "end_hub: goal 2 0\n"
        "connection: start-cima\n"
        "connection: cima-goal\n"
        "connection: start-baixo\n"
        "connection: baixo-goal\n"
    ))

    moves = Scheduler(mapa, ReservationTable()).plan_all(nb)

    assert sorted(moves[0].values()) == ["baixo", "cima"]
    assert len(_juiz(mapa, nb, moves)) == 2


def test_muitos_drones_num_gargalo_terminam(tmp_path: Path) -> None:
    """20 drones numa fila de capacidade 1: 1 chega por turno, sem travar."""
    mapa, nb = _mapa(tmp_path, LINHA.replace("nb_drones: 2", "nb_drones: 20"))

    linhas = _juiz(mapa, nb, Scheduler(mapa, ReservationTable()).plan_all(nb))

    assert len(linhas) == 21      # 2 turnos do D1 + 1 por drone a mais


def test_grafo_desconexo_levanta_no_path_error(tmp_path: Path) -> None:
    """Sem caminho até a end: erro claro já ao criar o Scheduler."""
    mapa, _ = _mapa(tmp_path, (
        "nb_drones: 2\n"
        "start_hub: start 0 0\n"
        "hub: a 1 0\n"
        "end_hub: goal 9 9\n"
        "connection: start-a\n"
    ))

    with pytest.raises(NoPathError):
        Scheduler(mapa, ReservationTable())


OTIMOS: Dict[str, int] = {
    "easy/01_linear_path.txt": 4,
    "easy/02_simple_fork.txt": 4,
    "easy/03_basic_capacity.txt": 4,
    "medium/01_dead_end_trap.txt": 8,
    "medium/02_circular_loop.txt": 10,
    "medium/03_priority_puzzle.txt": 6,
    "hard/01_maze_nightmare.txt": 13,
    "hard/02_capacity_hell.txt": 16,
    "hard/03_ultimate_challenge.txt": 26,
    "challenger/01_the_impossible_dream.txt": 43,
}


@pytest.mark.parametrize("arquivo,otimo", sorted(OTIMOS.items()))
def test_mapas_oficiais_validos_e_no_otimo(arquivo: str, otimo: int) -> None:
    """Cada mapa do subject passa pelo juiz no nº ótimo de turnos."""
    mapa, nb = Parser(str(RAIZ / "maps" / arquivo)).parse()

    linhas = _juiz(mapa, nb, Scheduler(mapa, ReservationTable()).plan_all(nb))

    assert len(linhas) == otimo
