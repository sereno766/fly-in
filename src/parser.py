"""Módulo Parser.

Define a classe Parser, responsável por ler o arquivo de mapa e,
nas próximas etapas, construir o Map e a lista de Drones a partir
dele.

Esta primeira versão contém apenas o leitor de arquivo base: abre
o arquivo com context manager e itera linha a linha, ignorando
comentários (#) e linhas vazias, preservando o número da linha
original do arquivo (útil para mensagens de erro no próximo cartão).
"""

from __future__ import annotations

from typing import Iterator, Tuple


class Parser:
    """Lê e (nas próximas etapas) interpreta um arquivo de mapa.

    Attributes:
        (privado) _filepath: Caminho do arquivo de mapa a ser lido.
    """

    def __init__(self, filepath: str) -> None:
        """Inicializa o Parser com o caminho do arquivo a ler.

        Args:
            filepath: Caminho para o arquivo de mapa (.txt).
        """
        self._filepath = filepath

    def _iter_lines(self) -> Iterator[Tuple[int, str]]:
        """Itera sobre as linhas úteis do arquivo de mapa.

        Abre o arquivo com um context manager (fechamento automático
        garantido mesmo se ocorrer erro no meio da leitura) e produz,
        uma de cada vez, o número da linha original no arquivo junto
        com seu conteúdo já limpo (sem espaços nas pontas).

        Linhas em branco e linhas de comentário (iniciadas com "#")
        são ignoradas, mas NÃO contam como "puladas" na numeração:
        o número de linha sempre reflete a posição real no arquivo,
        para que futuras mensagens de erro apontem para o lugar
        correto (ex.: "erro na linha 7").

        Yields:
            Tuplas (numero_da_linha, conteudo_da_linha), apenas para
            linhas não vazias e que não são comentário.

        Raises:
            FileNotFoundError: Se o arquivo em self._filepath não
                existir (o erro nativo do Python já é claro o
                suficiente aqui, por isso não é reenvelopado).
        """
        with open(self._filepath, "r", encoding="utf-8") as f:
            for numero, linha in enumerate(f, start=1):
                linha_limpa = linha.strip()

                # ignora linhas vazias
                if not linha_limpa:
                    continue

                # ignora comentários
                if linha_limpa.startswith("#"):
                    continue

                yield numero, linha_limpa
