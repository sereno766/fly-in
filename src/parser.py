"""Módulo Parser.

Define a classe Parser, responsável por ler o arquivo de mapa e,
nas próximas etapas, construir o Map e a lista de Drones a partir
dele.

Esta versão já lê nb_drones, start_hub, end_hub e hub, montando os
objetos Zone correspondentes. Connections e a montagem final do Map
ficam para o próximo cartão.
"""

from __future__ import annotations

from typing import Iterator, Optional, Tuple

from .entitie import Zone, ZoneType


class ParseError(Exception):
    """Levantada quando o conteúdo do arquivo de mapa é inválido.

    Attributes:
        line: Número da linha do arquivo onde o erro ocorreu.
    """

    def __init__(self, line: int, message: str) -> None:
        """Inicializa o erro com o número da linha e a causa.

        Args:
            line: Número da linha onde o problema foi encontrado.
            message: Descrição do que está errado nessa linha.
        """
        self.line = line
        super().__init__(f"Erro de parsing na linha {line}: {message}")


class Parser:
    """Lê e interpreta um arquivo de mapa.

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

    def parse(self) -> Optional[int]:
        """Percorre o arquivo de mapa e interpreta cada linha.

        Por enquanto, monta as instâncias de Zone (a partir de
        start_hub/end_hub/hub) e valida nb_drones. A montagem do
        Map e o parsing de connection ficam para o próximo cartão.

        Returns:
            O valor de nb_drones lido do arquivo (ou None se a linha
            nb_drones ainda não tiver sido processada).

        Raises:
            ParseError: Se qualquer linha do arquivo for inválida.
        """
        nb_drones: Optional[int] = None

        for numero, linha in self._iter_lines():
            prefixo, resto = linha.split(":", 1)
            prefixo = prefixo.strip()
            resto = resto.strip()

            if prefixo == "nb_drones":
                try:
                    valor = int(resto)
                except ValueError:
                    raise ParseError(
                        numero, "nb_drones deve ser um número inteiro positivo"
                    ) from None
                if valor <= 0:
                    raise ParseError(
                        numero, "nb_drones deve ser um número inteiro positivo"
                    )
                nb_drones = valor

            elif prefixo in ("start_hub", "hub", "end_hub"):
                # separa "nome x y" de "[metadata]"
                if "[" in resto:
                    main_part, metadata_part = resto.split("[", 1)
                    metadata_part = metadata_part.rstrip("]").strip()
                else:
                    main_part = resto
                    metadata_part = ""

                partes = main_part.split()
                if len(partes) != 3:
                    raise ParseError(
                        numero,
                        f"esperado 'nome x y', recebido {len(partes)} valor(es)",
                    )

                nome, x_str, y_str = partes

                if "-" in nome:
                    raise ParseError(
                        numero, f"nome de zona '{nome}' não pode conter traço"
                    )

                try:
                    x = int(x_str)
                    y = int(y_str)
                except ValueError:
                    raise ParseError(
                        numero, "coordenadas x/y devem ser inteiras"
                    ) from None

                # transforma metadata_part num dict {chave: valor}
                meta: dict[str, str] = {}
                if metadata_part:
                    for token in metadata_part.split():
                        if "=" not in token:
                            raise ParseError(
                                numero,
                                f"metadata inválida: '{token}' "
                                "(esperado chave=valor)",
                            )
                        chave, valor_meta = token.split("=", 1)
                        meta[chave] = valor_meta

                # valida zone_type
                tipos_validos = {"normal", "blocked", "restricted", "priority"}
                zone_type_str = meta.get("zone", "normal")
                if zone_type_str not in tipos_validos:
                    raise ParseError(
                        numero, f"tipo de zona inválido: '{zone_type_str}'"
                    )

                # color é livre, sem validação
                color = meta.get("color")

                is_start = prefixo == "start_hub"
                is_end = prefixo == "end_hub"

                # max_drones: ignorado (nem lido) em start_hub/end_hub
                max_capacity = 1
                if not is_start and not is_end and "max_drones" in meta:
                    try:
                        max_capacity = int(meta["max_drones"])
                    except ValueError:
                        raise ParseError(
                            numero, "max_drones deve ser um inteiro positivo"
                        ) from None
                    if max_capacity <= 0:
                        raise ParseError(
                            numero, "max_drones deve ser um inteiro positivo"
                        )

                zone = Zone(
                    name=nome,
                    x=x,
                    y=y,
                    zone_type=ZoneType(zone_type_str),
                    color=color,
                    max_capacity=max_capacity,
                    is_start=is_start,
                    is_end=is_end,
                )

                print(zone)  # DEBUG temporário — remover no próximo cartão

            elif prefixo == "connection":
                continue  # fica para o próximo cartão

            else:
                raise ParseError(numero, f"prefixo desconhecido: '{prefixo}'")

        return nb_drones