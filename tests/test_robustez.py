"""Testes de robustez: mapas próprios, arquivos malformados e carga.

Garante a regra mais importante da avaliação: o programa NUNCA cai com
uma exceção não tratada — todo erro vira mensagem clara e código 1.
"""

from pathlib import Path
from typing import Dict, List

import pytest

from main import FlyInApp
from src.parser import Parser
from src.pathfinder import NoPathError
from src.reservation import ReservationTable
from src.scheduler import Scheduler
from src.simulation import Simulation

MAPAS = Path(__file__).resolve().parents[1] / "maps"


def _turnos(arquivo: Path, nb: int = 0) -> List[str]:
    """Planeja e executa um mapa no juiz.

    Args:
        arquivo: Caminho do mapa.
        nb: Quantidade de drones; 0 usa a do arquivo.

    Returns:
        As linhas de saída (uma por turno).
    """
    mapa, nb_arquivo = Parser(str(arquivo)).parse()
    nb = nb or nb_arquivo
    plano = Scheduler(mapa, ReservationTable()).plan_all(nb)
    return Simulation(mapa, nb).run(plano)


# --------------------------------------------------------------------------
# Mapas próprios (maps/custom)
# --------------------------------------------------------------------------


CUSTOM: Dict[str, int] = {
    "01_cycle.txt": 7,             # 4 drones, 1 entra em 'a' por turno
    "02_multi_bottleneck.txt": 11,  # 6 drones por 3 gargalos em fila
    "04_only_restricted.txt": 7,   # conexão r1-r2 passa 1 por turno
    "05_blocked_detour.txt": 5,    # desvio pela priority, 3 drones
}


@pytest.mark.parametrize("nome,esperado", sorted(CUSTOM.items()))
def test_mapas_proprios(nome: str, esperado: int) -> None:
    """Cada mapa próprio termina, passa pelo juiz e no nº esperado."""
    assert len(_turnos(MAPAS / "custom" / nome)) == esperado


def test_mapa_proprio_desconexo_da_erro() -> None:
    """Grafo desconexo: NoPathError, sem loop infinito."""
    with pytest.raises(NoPathError):
        _turnos(MAPAS / "custom" / "03_disconnected.txt")


def test_ciclo_nao_faz_drone_girar() -> None:
    """No mapa com ciclo, nenhum drone visita a mesma zona 2 vezes."""
    mapa, nb = Parser(str(MAPAS / "custom" / "01_cycle.txt")).parse()
    plano = Scheduler(mapa, ReservationTable()).plan_all(nb)
    sim = Simulation(mapa, nb)
    sim.run(plano)

    for drone in sim.get_drones():
        assert len(drone.path_history) == len(set(drone.path_history))


# --------------------------------------------------------------------------
# Arquivos malformados (maps/broken) — nunca podem derrubar o programa
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "arquivo", sorted(p.name for p in (MAPAS / "broken").glob("*.txt"))
)
def test_mapa_quebrado_vira_erro_claro(
    arquivo: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """Todo mapa quebrado: código 1, mensagem de parsing, sem saída."""
    codigo = FlyInApp([str(MAPAS / "broken" / arquivo)]).run()

    capturado = capsys.readouterr()
    assert codigo == 1
    assert capturado.err.startswith("Erro de parsing")
    assert capturado.out == ""


def test_arquivo_vazio_nao_fala_em_linha_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Erro do arquivo inteiro não aponta uma 'linha 0' sem sentido."""
    FlyInApp([str(MAPAS / "broken" / "arquivo_vazio.txt")]).run()

    erro = capsys.readouterr().err
    assert "no arquivo" in erro
    assert "linha 0" not in erro


def test_diretorio_no_lugar_do_mapa_nao_derruba(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Passar uma pasta em vez de arquivo também é erro tratado."""
    assert FlyInApp([str(tmp_path)]).run() == 1
    assert "Erro" in capsys.readouterr().err


# --------------------------------------------------------------------------
# Alta concorrência: muitos drones, pouca capacidade
# --------------------------------------------------------------------------


def test_muitos_drones_em_mapa_de_capacidade_1() -> None:
    """300 drones num mapa onde tudo tem capacidade 1: 1 chega por turno."""
    linhas = _turnos(MAPAS / "easy" / "01_linear_path.txt", nb=300)

    # 3 turnos para o primeiro chegar + 1 turno por drone a mais
    assert len(linhas) == 3 + 299


@pytest.mark.parametrize("arquivo", [
    "hard/01_maze_nightmare.txt",
    "hard/03_ultimate_challenge.txt",
    "challenger/01_the_impossible_dream.txt",
])
def test_200_drones_nos_mapas_dificeis(arquivo: str) -> None:
    """200 drones nos mapas mais difíceis: termina e o juiz aceita."""
    assert len(_turnos(MAPAS / arquivo, nb=200)) > 0
