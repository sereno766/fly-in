"""Testes do Renderer (cores ANSI e painel por turno)."""

import re
from pathlib import Path
from typing import Tuple

from src.entitie import Map
from src.parser import Parser
from src.renderer import Renderer
from src.simulation import Simulation

ANSI = re.compile(r"\033\[[0-9;]*m")

MAPA = (
    "nb_drones: 2\n"
    "start_hub: start 0 0 [color=green]\n"
    "hub: r 1 0 [zone=restricted color=orange]\n"
    "hub: sem_cor 1 1\n"
    "hub: estranha 2 1 [color=xyzcor]\n"
    "end_hub: goal 2 0 [color=rainbow]\n"
    "connection: start-r\n"
    "connection: r-goal\n"
    "connection: start-sem_cor\n"
    "connection: sem_cor-estranha\n"
    "connection: estranha-goal\n"
)


def _mapa(tmp_path: Path) -> Tuple[Map, int]:
    """Parseia o mapa de teste.

    Args:
        tmp_path: Diretório temporário do pytest.

    Returns:
        Tupla (mapa, nb_drones).
    """
    arquivo = tmp_path / "mapa.txt"
    arquivo.write_text(MAPA, encoding="utf-8")
    return Parser(str(arquivo)).parse()


def _sem_ansi(texto: str) -> str:
    """Remove os códigos de cor ANSI de um texto.

    Args:
        texto: Texto possivelmente colorido.

    Returns:
        O texto puro.
    """
    return ANSI.sub("", texto)


def test_sem_cor_a_linha_fica_identica(tmp_path: Path) -> None:
    """Cor desligada: nenhum caractere a mais no formato exigido."""
    mapa, _ = _mapa(tmp_path)
    linha = "D1-r D2-start-r"

    assert Renderer(mapa, cor=False).format_line(linha) == linha


def test_com_cor_o_texto_continua_o_mesmo(tmp_path: Path) -> None:
    """Cor ligada: tirando os códigos ANSI, sobra a linha original."""
    mapa, _ = _mapa(tmp_path)
    linha = "D1-r D2-start-r D3-goal"

    pintada = Renderer(mapa, cor=True).format_line(linha)

    assert pintada != linha
    assert _sem_ansi(pintada) == linha


def test_cor_conhecida_usa_rgb_do_metadata(tmp_path: Path) -> None:
    """orange vira o código truecolor 255;140;0."""
    mapa, _ = _mapa(tmp_path)

    assert "38;2;255;140;0" in Renderer(mapa, cor=True).paint("r", "orange")


def test_cor_desconhecida_ou_ausente_fica_sem_cor(tmp_path: Path) -> None:
    """Qualquer palavra é cor válida: se não conhecemos, não pinta."""
    mapa, _ = _mapa(tmp_path)
    renderer = Renderer(mapa, cor=True)

    assert renderer.paint("estranha", "xyzcor") == "estranha"
    assert renderer.paint("sem_cor", None) == "sem_cor"


def test_rainbow_pinta_cada_letra(tmp_path: Path) -> None:
    """A cor especial rainbow troca de cor a cada letra."""
    mapa, _ = _mapa(tmp_path)

    pintado = Renderer(mapa, cor=True).paint("goal", "rainbow")

    assert pintado.count("\033[38;2;") == 4
    assert _sem_ansi(pintado) == "goal"


def test_painel_mostra_posicoes_transito_e_entregues(tmp_path: Path) -> None:
    """Depois do turno 1: D1 na conexão start-r, D2 em sem_cor."""
    mapa, nb = _mapa(tmp_path)
    sim = Simulation(mapa, nb)
    sim.apply_turn({"D1": "r", "D2": "sem_cor"})

    painel = Renderer(mapa, cor=False).panel(sim.get_drones(), sim.turn)

    assert painel == (
        "   turno 1 | sem_cor: D2 | start-r ->: D1 | entregues: 0/2"
    )


def test_painel_mostra_tipo_da_zona(tmp_path: Path) -> None:
    """Zonas não-normais aparecem com o tipo entre parênteses."""
    mapa, nb = _mapa(tmp_path)
    sim = Simulation(mapa, nb)
    sim.apply_turn({"D1": "r"})
    sim.apply_turn({})                        # D1 chega na restricted

    painel = Renderer(mapa, cor=False).panel(sim.get_drones(), sim.turn)

    assert "r(restricted): D1" in painel


def test_delivery_turns_registra_turno_da_entrega(tmp_path: Path) -> None:
    """A simulação anota em que turno cada drone chegou na end."""
    mapa, nb = _mapa(tmp_path)
    sim = Simulation(mapa, nb)
    sim.run([
        {"D1": "r", "D2": "sem_cor"},
        {"D2": "estranha"},                  # D1 chega em r sozinho
        {"D1": "goal"},                      # D2 espera 1 turno
        {"D2": "goal"},
    ])

    assert sim.delivery_turns() == {"D1": 3, "D2": 4}


def test_summary_mostra_custo_e_esperas(tmp_path: Path) -> None:
    """Custo = movimentos (restricted conta 2); esperas = resto."""
    mapa, nb = _mapa(tmp_path)
    sim = Simulation(mapa, nb)
    sim.run([
        {"D1": "r", "D2": "sem_cor"},
        {"D2": "estranha"},
        {"D1": "goal"},
        {"D2": "goal"},
    ])

    linhas = Renderer(mapa, cor=False).summary(
        sim.get_drones(), sim.delivery_turns(), sim.turn
    )

    assert linhas == [
        "=== métricas ===",
        "D1: entregue no turno 3 | custo 3 | esperas 0",
        "D2: entregue no turno 4 | custo 3 | esperas 1",
        "turnos totais: 4 | entrega média: 3.5 | movimentos por turno: 1.5",
    ]
