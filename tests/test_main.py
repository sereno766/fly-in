"""Testes do ponto de entrada (main.py / FlyInApp)."""

from pathlib import Path

import pytest

from main import FlyInApp

RAIZ = Path(__file__).resolve().parents[1]


def test_imprime_uma_linha_por_turno(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """easy/01: 4 linhas no formato D<ID>-<zona>, código 0."""
    codigo = FlyInApp([str(RAIZ / "maps/easy/01_linear_path.txt")]).run()

    saida = capsys.readouterr().out.splitlines()
    assert codigo == 0
    assert saida == [
        "D1-waypoint1",
        "D1-waypoint2 D2-waypoint1",
        "D1-goal D2-waypoint2",
        "D2-goal",
    ]


def test_restricted_aparece_como_conexao(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Drone a caminho de restricted sai como D<ID>-<conexão>."""
    mapa = tmp_path / "mapa.txt"
    mapa.write_text(
        "nb_drones: 1\n"
        "start_hub: start 0 0\n"
        "hub: r 1 0 [zone=restricted]\n"
        "end_hub: goal 2 0\n"
        "connection: start-r\n"
        "connection: r-goal\n",
        encoding="utf-8",
    )

    FlyInApp([str(mapa)]).run()

    assert capsys.readouterr().out.splitlines() == [
        "D1-start-r", "D1-r", "D1-goal",
    ]


def test_arquivo_inexistente_da_erro_sem_crash(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Arquivo que não existe: mensagem no stderr e código 1."""
    codigo = FlyInApp(["nao_existe.txt"]).run()

    assert codigo == 1
    assert "nao_existe.txt" in capsys.readouterr().err


def test_mapa_invalido_mostra_linha_do_erro(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Erro de parsing: mensagem com a linha e código 1."""
    codigo = FlyInApp([str(RAIZ / "maps/broken/dois_starts.txt")]).run()

    assert codigo == 1
    assert "linha 3" in capsys.readouterr().err


def test_grafo_desconexo_da_erro_claro(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Sem caminho até a end: mensagem clara e código 1."""
    mapa = tmp_path / "mapa.txt"
    mapa.write_text(
        "nb_drones: 1\n"
        "start_hub: start 0 0\n"
        "hub: a 1 0\n"
        "end_hub: goal 9 9\n"
        "connection: start-a\n",
        encoding="utf-8",
    )

    codigo = FlyInApp([str(mapa)]).run()

    assert codigo == 1
    assert "não existe caminho" in capsys.readouterr().err
