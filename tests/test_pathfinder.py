"""Testes do PathFinder (Dijkstra para 1 drone)."""

from pathlib import Path

import pytest

from src.parser import Parser
from src.pathfinder import NoPathError, PathFinder


def _caminho(tmp_path: Path, conteudo: str) -> list[str]:
    """Parseia um mapa em texto e devolve o caminho mínimo.

    Args:
        tmp_path: Diretório temporário do pytest.
        conteudo: Conteúdo do arquivo de mapa.

    Returns:
        Os nomes das zonas do caminho, de start até end.
    """
    arquivo = tmp_path / "mapa.txt"
    arquivo.write_text(conteudo, encoding="utf-8")
    mapa, _ = Parser(str(arquivo)).parse()
    return PathFinder(mapa).shortest_path()


def test_linha_reta(tmp_path: Path) -> None:
    """Com um único caminho, ele é o resultado."""
    caminho = _caminho(tmp_path, (
        "nb_drones: 1\n"
        "start_hub: start 0 0\n"
        "hub: a 1 0\n"
        "end_hub: goal 2 0\n"
        "connection: start-a\n"
        "connection: a-goal\n"
    ))

    assert caminho == ["start", "a", "goal"]


def test_escolhe_a_rota_mais_curta(tmp_path: Path) -> None:
    """Entre uma rota de 2 passos e uma de 3, escolhe a de 2."""
    caminho = _caminho(tmp_path, (
        "nb_drones: 1\n"
        "start_hub: start 0 0\n"
        "hub: curto 1 0\n"
        "hub: longo1 1 1\n"
        "hub: longo2 2 1\n"
        "end_hub: goal 2 0\n"
        "connection: start-longo1\n"
        "connection: longo1-longo2\n"
        "connection: longo2-goal\n"
        "connection: start-curto\n"
        "connection: curto-goal\n"
    ))

    assert caminho == ["start", "curto", "goal"]


def test_restricted_ganha_de_rota_normal_mais_longa(
    tmp_path: Path,
) -> None:
    """Via r: 2 + 1 = 3. Via a, b, c: 1 + 1 + 1 + 1 = 4. Vence a r."""
    caminho = _caminho(tmp_path, (
        "nb_drones: 1\n"
        "start_hub: start 0 0\n"
        "hub: r 1 0 [zone=restricted]\n"
        "hub: a 1 1\n"
        "hub: b 2 1\n"
        "hub: c 3 1\n"
        "end_hub: goal 2 0\n"
        "connection: start-r\n"
        "connection: r-goal\n"
        "connection: start-a\n"
        "connection: a-b\n"
        "connection: b-c\n"
        "connection: c-goal\n"
    ))

    assert caminho == ["start", "r", "goal"]


def test_restricted_perde_para_rota_normal_mais_barata(
    tmp_path: Path,
) -> None:
    """Via r: 2 + 1 = 3. Via n: 1 + 1 = 2. Vence a n."""
    caminho = _caminho(tmp_path, (
        "nb_drones: 1\n"
        "start_hub: start 0 0\n"
        "hub: r 1 0 [zone=restricted]\n"
        "hub: n 1 1\n"
        "end_hub: goal 2 0\n"
        "connection: start-r\n"
        "connection: r-goal\n"
        "connection: start-n\n"
        "connection: n-goal\n"
    ))

    assert caminho == ["start", "n", "goal"]


def test_desvia_de_zona_blocked(tmp_path: Path) -> None:
    """A rota curta passa por blocked: usa o desvio, mesmo mais longo."""
    caminho = _caminho(tmp_path, (
        "nb_drones: 1\n"
        "start_hub: start 0 0\n"
        "hub: muro 1 0 [zone=blocked]\n"
        "hub: desvio 1 1\n"
        "hub: d2 2 1\n"
        "end_hub: goal 2 0\n"
        "connection: start-muro\n"
        "connection: muro-goal\n"
        "connection: start-desvio\n"
        "connection: desvio-d2\n"
        "connection: d2-goal\n"
    ))

    assert caminho == ["start", "desvio", "d2", "goal"]


def test_unica_rota_por_blocked_levanta_no_path_error(
    tmp_path: Path,
) -> None:
    """Se só dá para chegar passando por blocked, não há caminho."""
    with pytest.raises(NoPathError):
        _caminho(tmp_path, (
            "nb_drones: 1\n"
            "start_hub: start 0 0\n"
            "hub: muro 1 0 [zone=blocked]\n"
            "end_hub: goal 2 0\n"
            "connection: start-muro\n"
            "connection: muro-goal\n"
        ))


def test_grafo_desconexo_levanta_no_path_error(tmp_path: Path) -> None:
    """Sem nenhuma ligação até a end: NoPathError, sem loop infinito."""
    with pytest.raises(NoPathError):
        _caminho(tmp_path, (
            "nb_drones: 1\n"
            "start_hub: start 0 0\n"
            "hub: a 1 0\n"
            "end_hub: goal 9 9\n"
            "connection: start-a\n"
        ))


# --------------------------------------------------------------------------
# Zonas priority: desempate
# --------------------------------------------------------------------------


@pytest.mark.parametrize("primeira,segunda", [("comum", "vip"),
                                              ("vip", "comum")])
def test_priority_vence_empate(
    tmp_path: Path, primeira: str, segunda: str
) -> None:
    """Mesmo custo: escolhe a rota priority, em qualquer ordem no arquivo."""
    caminho = _caminho(tmp_path, (
        "nb_drones: 1\n"
        "start_hub: start 0 0\n"
        "hub: comum 1 0\n"
        "hub: vip 1 1 [zone=priority]\n"
        "end_hub: goal 2 0\n"
        f"connection: start-{primeira}\n"
        f"connection: {primeira}-goal\n"
        f"connection: start-{segunda}\n"
        f"connection: {segunda}-goal\n"
    ))

    assert caminho == ["start", "vip", "goal"]


def test_priority_nao_vence_caminho_mais_barato(tmp_path: Path) -> None:
    """Priority só desempata: rota normal de custo 2 vence priority de 3."""
    caminho = _caminho(tmp_path, (
        "nb_drones: 1\n"
        "start_hub: start 0 0\n"
        "hub: comum 1 0\n"
        "hub: vip 1 1 [zone=priority]\n"
        "hub: vip2 2 1 [zone=priority]\n"
        "end_hub: goal 2 0\n"
        "connection: start-comum\n"
        "connection: comum-goal\n"
        "connection: start-vip\n"
        "connection: vip-vip2\n"
        "connection: vip2-goal\n"
    ))

    assert caminho == ["start", "comum", "goal"]


def test_mais_priority_vence(tmp_path: Path) -> None:
    """Duas rotas de custo 3: a com 2 zonas priority vence a com 1."""
    caminho = _caminho(tmp_path, (
        "nb_drones: 1\n"
        "start_hub: start 0 0\n"
        "hub: p1 1 0 [zone=priority]\n"
        "hub: n1 2 0\n"
        "hub: p2 1 1 [zone=priority]\n"
        "hub: p3 2 1 [zone=priority]\n"
        "end_hub: goal 3 0\n"
        "connection: start-p1\n"
        "connection: p1-n1\n"
        "connection: n1-goal\n"
        "connection: start-p2\n"
        "connection: p2-p3\n"
        "connection: p3-goal\n"
    ))

    assert caminho == ["start", "p2", "p3", "goal"]
