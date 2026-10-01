"""Testes unitários do Parser.

Cobre o caminho feliz (mapa válido) e os principais casos de erro
exigidos pelo enunciado: nb_drones inválido, tipos de zona inválidos,
nomes com traço, start_hub/end_hub duplicados, connections
duplicadas ou referenciando zonas inexistentes, e metadata inválida.
"""

from pathlib import Path

import pytest

from src.entitie import ZoneType
from src.parser import ParseError, Parser


def _write_map(tmp_path: Path, content: str) -> str:
    """Escreve um mapa de teste num arquivo temporário e retorna o caminho.

    Args:
        tmp_path: Diretório temporário fornecido pelo pytest.
        content: Conteúdo do arquivo de mapa.

    Returns:
        Caminho (str) do arquivo criado.
    """
    map_file = tmp_path / "mapa.txt"
    map_file.write_text(content, encoding="utf-8")
    return str(map_file)


# --------------------------------------------------------------------------
# Caminho feliz: mapa válido
# --------------------------------------------------------------------------


def test_mapa_valido_parseia_corretamente(tmp_path: Path) -> None:
    """Um mapa bem formado deve parsear sem erros e montar o Map certo."""
    conteudo = (
        "nb_drones: 2\n"
        "start_hub: start 0 0 [color=green]\n"
        "hub: meio 1 0 [color=blue]\n"
        "end_hub: goal 2 0 [color=red]\n"
        "connection: start-meio\n"
        "connection: meio-goal [max_link_capacity=2]\n"
    )
    caminho = _write_map(tmp_path, conteudo)

    mapa, nb_drones = Parser(caminho).parse()

    assert nb_drones == 2
    assert mapa.get_start().name == "start"
    assert mapa.get_end().name == "goal"
    assert mapa.has_zone("meio")

    vizinhos_meio = mapa.get_neighbors("meio")
    assert len(vizinhos_meio) == 2

    conexao_final = next(
        c for c in vizinhos_meio if c.connects("meio", "goal")
    )
    assert conexao_final.max_link_capacity == 2


def test_zone_type_restricted_e_priority_sao_aceitos(tmp_path: Path) -> None:
    """Tipos de zona restricted e priority devem ser reconhecidos."""
    conteudo = (
        "nb_drones: 1\n"
        "start_hub: a 0 0\n"
        "hub: b 1 0 [zone=restricted]\n"
        "hub: c 2 0 [zone=priority]\n"
        "end_hub: d 3 0\n"
        "connection: a-b\n"
        "connection: b-c\n"
        "connection: c-d\n"
    )
    caminho = _write_map(tmp_path, conteudo)

    mapa, _ = Parser(caminho).parse()

    assert mapa.get_zone("b").zone_type == ZoneType.RESTRICTED
    assert mapa.get_zone("c").zone_type == ZoneType.PRIORITY


def test_max_drones_ignorado_em_start_hub(tmp_path: Path) -> None:
    """max_drones malformado em start_hub/end_hub não deve dar erro."""
    conteudo = (
        "nb_drones: 1\n"
        "start_hub: a 0 0 [max_drones=abc]\n"
        "end_hub: b 1 0 [max_drones=-5]\n"
        "connection: a-b\n"
    )
    caminho = _write_map(tmp_path, conteudo)

    mapa, _ = Parser(caminho).parse()

    assert mapa.get_start().name == "a"
    assert mapa.get_end().name == "b"


# --------------------------------------------------------------------------
# Erros de nb_drones
# --------------------------------------------------------------------------


def test_nb_drones_negativo_levanta_parse_error(tmp_path: Path) -> None:
    """nb_drones negativo deve levantar ParseError na linha correta."""
    conteudo = (
        "nb_drones: -3\nstart_hub: a 0 0\nend_hub: b 1 0\nconnection: a-b\n"
    )
    caminho = _write_map(tmp_path, conteudo)

    with pytest.raises(ParseError) as exc_info:
        Parser(caminho).parse()

    assert exc_info.value.line == 1


def test_nb_drones_nao_numerico_levanta_parse_error(tmp_path: Path) -> None:
    """nb_drones que não é um número deve levantar ParseError."""
    conteudo = (
        "nb_drones: abc\nstart_hub: a 0 0\nend_hub: b 1 0\n"
        "connection: a-b\n"
    )
    caminho = _write_map(tmp_path, conteudo)

    with pytest.raises(ParseError) as exc_info:
        Parser(caminho).parse()

    assert exc_info.value.line == 1


# --------------------------------------------------------------------------
# Erros de zona
# --------------------------------------------------------------------------


def test_tipo_de_zona_invalido_levanta_parse_error(tmp_path: Path) -> None:
    """zone=<tipo desconhecido> deve levantar ParseError."""
    conteudo = (
        "nb_drones: 1\n"
        "start_hub: a 0 0\n"
        "hub: b 1 0 [zone=invalido]\n"
        "end_hub: c 2 0\n"
        "connection: a-b\n"
        "connection: b-c\n"
    )
    caminho = _write_map(tmp_path, conteudo)

    with pytest.raises(ParseError) as exc_info:
        Parser(caminho).parse()

    assert exc_info.value.line == 3


def test_nome_de_zona_com_traco_levanta_parse_error(tmp_path: Path) -> None:
    """Nomes de zona não podem conter traço."""
    conteudo = "nb_drones: 1\nstart_hub: nome-invalido 0 0\nend_hub: b 1 0\n"
    caminho = _write_map(tmp_path, conteudo)

    with pytest.raises(ParseError) as exc_info:
        Parser(caminho).parse()

    assert exc_info.value.line == 2


def test_coordenadas_nao_inteiras_levanta_parse_error(tmp_path: Path) -> None:
    """Coordenadas x/y que não são inteiras devem levantar ParseError."""
    conteudo = "nb_drones: 1\nstart_hub: a x y\nend_hub: b 1 0\n"
    caminho = _write_map(tmp_path, conteudo)

    with pytest.raises(ParseError) as exc_info:
        Parser(caminho).parse()

    assert exc_info.value.line == 2


def test_nome_de_zona_duplicado_levanta_parse_error(tmp_path: Path) -> None:
    """Duas zonas com o mesmo nome devem levantar ParseError."""
    conteudo = (
        "nb_drones: 1\n"
        "start_hub: a 0 0\n"
        "hub: a 1 1\n"
        "end_hub: b 2 0\n"
    )
    caminho = _write_map(tmp_path, conteudo)

    with pytest.raises(ParseError) as exc_info:
        Parser(caminho).parse()

    assert exc_info.value.line == 3


def test_dois_start_hub_levanta_parse_error(tmp_path: Path) -> None:
    """Duas zonas start_hub no mesmo mapa devem levantar ParseError."""
    conteudo = (
        "nb_drones: 1\n"
        "start_hub: a 0 0\n"
        "start_hub: b 1 0\n"
        "end_hub: c 2 0\n"
    )
    caminho = _write_map(tmp_path, conteudo)

    with pytest.raises(ParseError) as exc_info:
        Parser(caminho).parse()

    assert exc_info.value.line == 3


def test_dois_end_hub_levanta_parse_error(tmp_path: Path) -> None:
    """Duas zonas end_hub no mesmo mapa devem levantar ParseError."""
    conteudo = (
        "nb_drones: 1\n"
        "start_hub: a 0 0\n"
        "end_hub: b 1 0\n"
        "end_hub: c 2 0\n"
    )
    caminho = _write_map(tmp_path, conteudo)

    with pytest.raises(ParseError) as exc_info:
        Parser(caminho).parse()

    assert exc_info.value.line == 4


def test_mapa_sem_start_hub_levanta_parse_error(tmp_path: Path) -> None:
    """Sem start_hub, o próprio parse() deve levantar ParseError."""
    conteudo = "nb_drones: 1\nhub: a 0 0\nend_hub: b 1 0\nconnection: a-b\n"
    caminho = _write_map(tmp_path, conteudo)

    with pytest.raises(ParseError, match="start_hub"):
        Parser(caminho).parse()


def test_mapa_sem_end_hub_levanta_parse_error(tmp_path: Path) -> None:
    """Sem end_hub, o próprio parse() deve levantar ParseError."""
    conteudo = "nb_drones: 1\nstart_hub: a 0 0\nhub: b 1 0\nconnection: a-b\n"
    caminho = _write_map(tmp_path, conteudo)

    with pytest.raises(ParseError, match="end_hub"):
        Parser(caminho).parse()


# --------------------------------------------------------------------------
# Erros de connection
# --------------------------------------------------------------------------


def test_connection_formato_invalido_levanta_parse_error(
    tmp_path: Path,
) -> None:
    """connection sem o traço separador deve levantar ParseError."""
    conteudo = (
        "nb_drones: 1\n"
        "start_hub: a 0 0\n"
        "end_hub: b 1 0\n"
        "connection: somenteumnome\n"
    )
    caminho = _write_map(tmp_path, conteudo)

    with pytest.raises(ParseError) as exc_info:
        Parser(caminho).parse()

    assert exc_info.value.line == 4


def test_connection_zona_inexistente_levanta_parse_error(
    tmp_path: Path,
) -> None:
    """connection referenciando zona não definida deve levantar ParseError."""
    conteudo = (
        "nb_drones: 1\n"
        "start_hub: a 0 0\n"
        "end_hub: b 1 0\n"
        "connection: a-naoexiste\n"
    )
    caminho = _write_map(tmp_path, conteudo)

    with pytest.raises(ParseError) as exc_info:
        Parser(caminho).parse()

    assert exc_info.value.line == 4


def test_connection_duplicada_ordem_invertida_levanta_parse_error(
    tmp_path: Path,
) -> None:
    """connection a-b seguida de b-a deve ser detectada como duplicata."""
    conteudo = (
        "nb_drones: 1\n"
        "start_hub: a 0 0\n"
        "end_hub: b 1 0\n"
        "connection: a-b\n"
        "connection: b-a\n"
    )
    caminho = _write_map(tmp_path, conteudo)

    with pytest.raises(ParseError) as exc_info:
        Parser(caminho).parse()

    assert exc_info.value.line == 5


def test_connection_max_link_capacity_invalido_levanta_parse_error(
    tmp_path: Path,
) -> None:
    """max_link_capacity não positivo deve levantar ParseError."""
    conteudo = (
        "nb_drones: 1\n"
        "start_hub: a 0 0\n"
        "end_hub: b 1 0\n"
        "connection: a-b [max_link_capacity=0]\n"
    )
    caminho = _write_map(tmp_path, conteudo)

    with pytest.raises(ParseError) as exc_info:
        Parser(caminho).parse()

    assert exc_info.value.line == 4


def test_connection_metadata_invalida_levanta_parse_error(
    tmp_path: Path,
) -> None:
    """Token de metadata sem '=' deve levantar ParseError."""
    conteudo = (
        "nb_drones: 1\n"
        "start_hub: a 0 0\n"
        "end_hub: b 1 0\n"
        "connection: a-b [tokeninvalido]\n"
    )
    caminho = _write_map(tmp_path, conteudo)

    with pytest.raises(ParseError) as exc_info:
        Parser(caminho).parse()

    assert exc_info.value.line == 4


# --------------------------------------------------------------------------
# Outros erros
# --------------------------------------------------------------------------


def test_prefixo_desconhecido_levanta_parse_error(tmp_path: Path) -> None:
    """Uma linha com prefixo não reconhecido deve levantar ParseError."""
    conteudo = "nb_drones: 1\nfoo: bar\n"
    caminho = _write_map(tmp_path, conteudo)

    with pytest.raises(ParseError) as exc_info:
        Parser(caminho).parse()

    assert exc_info.value.line == 2


def test_arquivo_inexistente_levanta_file_not_found_error() -> None:
    """Um caminho de arquivo inexistente deve levantar FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        Parser("maps/este_arquivo_nao_existe.txt").parse()


# --------------------------------------------------------------------------
# Estrutura do arquivo (nb_drones, ':' e arquivo vazio)
# --------------------------------------------------------------------------


def test_linha_sem_dois_pontos_levanta_parse_error(tmp_path: Path) -> None:
    """Linha sem ':' deve virar ParseError, não ValueError (crash)."""
    conteudo = "nb_drones: 2\nstart_hub: a 0 0\nconnection a-b\n"
    caminho = _write_map(tmp_path, conteudo)

    with pytest.raises(ParseError) as exc_info:
        Parser(caminho).parse()

    assert exc_info.value.line == 3


def test_nb_drones_fora_da_primeira_linha_levanta_parse_error(
    tmp_path: Path,
) -> None:
    """A primeira linha útil precisa ser nb_drones."""
    conteudo = "start_hub: a 0 0\nnb_drones: 2\nend_hub: b 1 0\n"
    caminho = _write_map(tmp_path, conteudo)

    with pytest.raises(ParseError) as exc_info:
        Parser(caminho).parse()

    assert exc_info.value.line == 1


def test_nb_drones_depois_de_comentario_e_aceito(tmp_path: Path) -> None:
    """Comentários e linhas vazias antes de nb_drones são permitidos."""
    conteudo = (
        "# comentario\n"
        "\n"
        "nb_drones: 2\n"
        "start_hub: a 0 0\n"
        "end_hub: b 1 0\n"
        "connection: a-b\n"
    )
    caminho = _write_map(tmp_path, conteudo)

    _, nb_drones = Parser(caminho).parse()

    assert nb_drones == 2


def test_nb_drones_repetido_levanta_parse_error(tmp_path: Path) -> None:
    """nb_drones definido duas vezes deve levantar ParseError."""
    conteudo = "nb_drones: 2\nnb_drones: 3\n"
    caminho = _write_map(tmp_path, conteudo)

    with pytest.raises(ParseError) as exc_info:
        Parser(caminho).parse()

    assert exc_info.value.line == 2


def test_arquivo_vazio_levanta_parse_error(tmp_path: Path) -> None:
    """Arquivo só com comentários não define nb_drones: ParseError."""
    caminho = _write_map(tmp_path, "# nada aqui\n\n")

    with pytest.raises(ParseError, match="nb_drones"):
        Parser(caminho).parse()


# --------------------------------------------------------------------------
# Sintaxe do bloco de metadata
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "linha_hub",
    [
        "hub: c 2 0 [zone=normal",          # sem ']'
        "hub: c 2 0 [color=red] lixo",      # texto depois do ']'
        "hub: c 2 0 color=red]",            # ']' sem '['
        "hub: c 2 0 [foo=bar]",             # chave desconhecida
        "hub: c 2 0 [max_drone=2]",         # erro de digitação na chave
        "hub: c 2 0 [color=]",              # valor vazio
        "hub: c 2 0 [color=red color=blue]",  # chave repetida
        "hub: c 2 0 [[color=red]]",         # colchetes extras
    ],
)
def test_metadata_mal_formada_levanta_parse_error(
    tmp_path: Path, linha_hub: str
) -> None:
    """Qualquer bloco de metadata mal formado deve levantar ParseError."""
    conteudo = (
        "nb_drones: 1\n"
        "start_hub: a 0 0\n"
        "end_hub: b 1 0\n"
        f"{linha_hub}\n"
    )
    caminho = _write_map(tmp_path, conteudo)

    with pytest.raises(ParseError) as exc_info:
        Parser(caminho).parse()

    assert exc_info.value.line == 4


def test_metadata_de_zona_em_connection_levanta_parse_error(
    tmp_path: Path,
) -> None:
    """connection só aceita max_link_capacity, não chaves de zona."""
    conteudo = (
        "nb_drones: 1\n"
        "start_hub: a 0 0\n"
        "end_hub: b 1 0\n"
        "connection: a-b [color=red]\n"
    )
    caminho = _write_map(tmp_path, conteudo)

    with pytest.raises(ParseError) as exc_info:
        Parser(caminho).parse()

    assert exc_info.value.line == 4


def test_metadata_vazia_e_aceita(tmp_path: Path) -> None:
    """Um bloco '[]' vazio é válido e usa os valores padrão."""
    conteudo = (
        "nb_drones: 1\n"
        "start_hub: a 0 0 []\n"
        "end_hub: b 1 0\n"
        "connection: a-b []\n"
    )
    caminho = _write_map(tmp_path, conteudo)

    mapa, _ = Parser(caminho).parse()

    assert mapa.get_neighbors("a")[0].max_link_capacity == 1


def test_connection_para_a_mesma_zona_levanta_parse_error(
    tmp_path: Path,
) -> None:
    """connection: a-a (zona ligada a ela mesma) deve levantar ParseError."""
    conteudo = (
        "nb_drones: 1\n"
        "start_hub: a 0 0\n"
        "end_hub: b 1 0\n"
        "connection: a-a\n"
    )
    caminho = _write_map(tmp_path, conteudo)

    with pytest.raises(ParseError) as exc_info:
        Parser(caminho).parse()

    assert exc_info.value.line == 4


def test_todos_os_mapas_do_subject_parseiam() -> None:
    """Todos os mapas oficiais (fora de maps/broken) devem ser válidos."""
    raiz = Path(__file__).resolve().parents[1] / "maps"
    mapas = [
        m for m in sorted(raiz.rglob("*.txt")) if m.parent.name != "broken"
    ]

    assert mapas, "nenhum mapa encontrado em maps/"
    for mapa_path in mapas:
        _, nb_drones = Parser(str(mapa_path)).parse()
        assert nb_drones > 0
