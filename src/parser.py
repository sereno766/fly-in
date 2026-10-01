"""Módulo Parser.

Define a classe Parser, responsável por ler o arquivo de mapa e
construir o Map (com todas as Zones e Connections) e nb_drones a
partir dele.
"""

from __future__ import annotations

from typing import Dict, Iterator, Optional, Set, Tuple

from src.entitie import Connection, Zone, ZoneType, Map


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
        para que mensagens de erro apontem para o lugar correto.

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

                if not linha_limpa:
                    continue

                if linha_limpa.startswith("#"):
                    continue

                yield numero, linha_limpa

    def _parse_metadata(
        self, numero: int, texto: str, chaves_validas: Set[str]
    ) -> Tuple[str, Dict[str, str]]:
        """Separa 'parte principal [chave=valor ...]' em duas partes.

        O bloco de metadata é opcional. Se existir, ele precisa abrir
        com '[' e fechar com ']' no FIM da linha, e cada token dentro
        dele precisa ser 'chave=valor', com chave conhecida, valor
        não vazio e sem chaves repetidas.

        Args:
            numero: Número da linha (usado nas mensagens de erro).
            texto: O conteúdo da linha depois do 'prefixo:'.
            chaves_validas: Chaves aceitas nesse tipo de linha.

        Returns:
            Uma tupla (parte_principal, metadata), com a parte antes
            do '[' (sem espaços nas pontas) e o dict chave -> valor.

        Raises:
            ParseError: Se o bloco de metadata estiver mal formado.
        """
        if "[" not in texto:
            if "]" in texto:
                raise ParseError(numero, "']' sem '[' correspondente")
            return texto.strip(), {}

        main_part, metadata_part = texto.split("[", 1)
        metadata_part = metadata_part.strip()

        # o bloco tem que fechar com ']' e ser a última coisa da linha
        if not metadata_part.endswith("]"):
            raise ParseError(
                numero, "bloco de metadata deve terminar com ']'"
            )
        metadata_part = metadata_part[:-1]
        if "[" in metadata_part or "]" in metadata_part:
            raise ParseError(numero, "colchetes extras na metadata")

        meta: Dict[str, str] = {}
        for token in metadata_part.split():
            if "=" not in token:
                raise ParseError(
                    numero,
                    f"metadata inválida: '{token}' (esperado chave=valor)",
                )
            chave, valor = token.split("=", 1)
            if chave not in chaves_validas:
                raise ParseError(
                    numero,
                    f"chave de metadata desconhecida: '{chave}' "
                    f"(aceitas: {', '.join(sorted(chaves_validas))})",
                )
            if not valor:
                raise ParseError(
                    numero, f"metadata '{chave}' sem valor"
                )
            if chave in meta:
                raise ParseError(
                    numero, f"metadata '{chave}' repetida"
                )
            meta[chave] = valor

        return main_part.strip(), meta

    def parse(self) -> Tuple[Map, int]:
        """Percorre o arquivo de mapa e interpreta cada linha.

        Monta o Map completo (todas as Zones e Connections) e
        valida nb_drones. Ao final, garante que o arquivo definiu
        nb_drones, uma start_hub e uma end_hub.

        Returns:
            Uma tupla (mapa, nb_drones) com o Map montado e o
            número de drones lido do arquivo.

        Raises:
            ParseError: Se qualquer linha do arquivo for inválida,
                ou se faltar nb_drones, start_hub ou end_hub.
        """
        mapa = Map()
        nb_drones: Optional[int] = None
        pares_conectados: set[frozenset[str]] = set()
        ultima_linha = 0

        for numero, linha in self._iter_lines():
            ultima_linha = numero

            # sem ':' o split abaixo não teria 2 partes (crash)
            if ":" not in linha:
                raise ParseError(
                    numero, "linha inválida: esperado 'prefixo: valor'"
                )

            prefixo, resto = linha.split(":", 1)
            prefixo = prefixo.strip()
            resto = resto.strip()

            # regra do enunciado: a 1ª linha útil deve ser nb_drones
            if prefixo != "nb_drones" and nb_drones is None:
                raise ParseError(
                    numero, "a primeira linha deve ser 'nb_drones: <n>'"
                )

            if prefixo == "nb_drones":
                if nb_drones is not None:
                    raise ParseError(
                        numero, "nb_drones definido mais de uma vez"
                    )
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
                main_part, meta = self._parse_metadata(
                    numero, resto, {"zone", "color", "max_drones"}
                )

                partes = main_part.split()
                if len(partes) != 3:
                    raise ParseError(
                        numero,
                        f"esperado 'nome x y', recebido "
                        f"{len(partes)} valor(es)",
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

                tipos_validos = {"normal", "blocked", "restricted", "priority"}
                zone_type_str = meta.get("zone", "normal")
                if zone_type_str not in tipos_validos:
                    raise ParseError(
                        numero, f"tipo de zona inválido: '{zone_type_str}'"
                    )

                color = meta.get("color")

                is_start = prefixo == "start_hub"
                is_end = prefixo == "end_hub"

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

                try:
                    mapa.add_zone(zone)
                except ValueError as e:
                    raise ParseError(numero, str(e)) from None

            elif prefixo == "connection":
                main_part, meta = self._parse_metadata(
                    numero, resto, {"max_link_capacity"}
                )

                partes = main_part.split("-", 1)
                if len(partes) != 2:
                    raise ParseError(
                        numero,
                        f"formato de connection inválido: esperado "
                        f"'nome1-nome2', recebido '{main_part}'",
                    )
                nome1, nome2 = partes
                nome1 = nome1.strip()
                nome2 = nome2.strip()

                if nome1 == nome2:
                    raise ParseError(
                        numero,
                        f"connection liga a zona '{nome1}' a ela mesma",
                    )

                if not mapa.has_zone(nome1):
                    raise ParseError(
                        numero,
                        f"connection referencia zona inexistente: '{nome1}'",
                    )
                if not mapa.has_zone(nome2):
                    raise ParseError(
                        numero,
                        f"connection referencia zona inexistente: '{nome2}'",
                    )

                par = frozenset({nome1, nome2})
                if par in pares_conectados:
                    raise ParseError(
                        numero, f"connection duplicada: '{nome1}-{nome2}'"
                    )
                pares_conectados.add(par)

                max_link_capacity = 1
                if "max_link_capacity" in meta:
                    try:
                        max_link_capacity = int(meta["max_link_capacity"])
                    except ValueError:
                        raise ParseError(
                            numero,
                            "max_link_capacity deve ser um inteiro positivo",
                        ) from None
                    if max_link_capacity <= 0:
                        raise ParseError(
                            numero,
                            "max_link_capacity deve ser um inteiro positivo",
                        )

                zone_a = mapa.get_zone(nome1)
                zone_b = mapa.get_zone(nome2)
                conn = Connection(zone_a, zone_b, max_link_capacity)

                try:
                    mapa.add_connection(conn)
                except ValueError as e:
                    raise ParseError(numero, str(e)) from None

            else:
                raise ParseError(numero, f"prefixo desconhecido: '{prefixo}'")

        # validações do arquivo como um todo (não de uma linha só)
        if nb_drones is None:
            raise ParseError(
                ultima_linha, "arquivo vazio: 'nb_drones' não foi definido"
            )
        if not mapa.has_start():
            raise ParseError(ultima_linha, "start_hub não foi definido")
        if not mapa.has_end():
            raise ParseError(ultima_linha, "end_hub não foi definido")

        return mapa, nb_drones
