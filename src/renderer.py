"""Módulo Renderer.

Define a classe Renderer, responsável pela representação visual da
simulação no terminal: pinta os nomes das zonas com a cor do metadata
(códigos ANSI truecolor) e mostra, a cada turno, onde está cada drone.

A cor é só "decoração": com a cor desligada, a saída é exatamente o
formato exigido (D<ID>-<zona>), sem nenhum caractere a mais.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from src.entitie import Drone, Map, ZoneType

# nome da cor (metadata color=...) -> RGB
CORES: Dict[str, Tuple[int, int, int]] = {
    "red": (220, 50, 47),
    "darkred": (170, 20, 20),
    "crimson": (220, 20, 60),
    "maroon": (160, 30, 40),
    "orange": (255, 140, 0),
    "gold": (255, 200, 0),
    "yellow": (230, 210, 40),
    "brown": (150, 90, 40),
    "green": (50, 180, 80),
    "lime": (150, 230, 50),
    "cyan": (40, 190, 200),
    "blue": (40, 120, 230),
    "purple": (150, 60, 200),
    "violet": (200, 120, 240),
    "magenta": (210, 60, 180),
    "pink": (255, 130, 180),
    "white": (230, 230, 230),
    "gray": (150, 150, 150),
    "grey": (150, 150, 150),
    # preto puro some em terminal escuro: usa um cinza escuro
    "black": (100, 100, 100),
}

# sequência usada pela cor especial "rainbow" (uma cor por letra)
ARCO_IRIS = ["red", "orange", "yellow", "green", "blue", "purple"]

RESET = "\033[0m"
NEGRITO = "\033[1m"
APAGADO = "\033[2m"


class Renderer:
    """Formata a saída da simulação, com ou sem cores.

    Attributes:
        (privado) _map: O grafo, para achar a cor e o tipo de cada zona.
        (privado) _cor: True se deve emitir códigos de cor ANSI.
    """

    def __init__(self, mapa: Map, cor: bool) -> None:
        """Prepara o renderer.

        Args:
            mapa: Map já montado pelo Parser.
            cor: True para colorir (normalmente: saída é um terminal).
        """
        self._map = mapa
        self._cor = cor

    def paint(self, texto: str, cor: Optional[str]) -> str:
        """Pinta um texto com uma cor do metadata.

        Args:
            texto: Texto a pintar.
            cor: Nome da cor (ex.: "red"). None ou cor desconhecida
                deixam o texto sem cor (qualquer palavra é uma cor
                válida no mapa, então não é erro).

        Returns:
            O texto com os códigos ANSI, ou o próprio texto se a cor
            estiver desligada ou for desconhecida.
        """
        if not self._cor or cor is None:
            return texto
        if cor == "rainbow":
            return "".join(
                self._ansi(letra, CORES[ARCO_IRIS[i % len(ARCO_IRIS)]])
                for i, letra in enumerate(texto)
            )
        rgb = CORES.get(cor.lower())
        if rgb is None:
            return texto
        return self._ansi(texto, rgb)

    def format_line(self, linha: str) -> str:
        """Pinta a linha de um turno sem mudar o texto.

        Cada movimento é "D<ID>-<zona>" ou "D<ID>-<zona_a-zona_b>"
        (em trânsito para uma restricted). O ID nunca tem traço, então
        o primeiro "-" separa o drone do destino.

        Args:
            linha: Linha devolvida por Simulation.apply_turn().

        Returns:
            A mesma linha, com o drone em negrito e o destino na cor da
            zona (conexões em trânsito aparecem apagadas).
        """
        if not self._cor:
            return linha
        partes: List[str] = []
        for movimento in linha.split():
            drone, destino = movimento.split("-", 1)
            if self._map.has_zone(destino):
                cor = self._map.get_zone(destino).color
                destino_fmt = self.paint(destino, cor)
            else:
                destino_fmt = f"{APAGADO}{destino}{RESET}"
            partes.append(f"{NEGRITO}{drone}{RESET}-{destino_fmt}")
        return " ".join(partes)

    def panel(self, drones: List[Drone], turno: int) -> str:
        """Resumo visual do estado depois de um turno.

        Mostra (na ordem em que os drones aparecem) quais drones estão
        em cada zona ocupada (com a cor e o tipo da zona), quem está em
        trânsito numa conexão e quantos já foram entregues.

        Args:
            drones: Todos os drones da simulação.
            turno: Número do turno que acabou de ser executado.

        Returns:
            Uma linha de texto (pintada se a cor estiver ligada).
        """
        por_zona: Dict[str, List[str]] = {}
        em_transito: Dict[str, List[str]] = {}
        entregues = 0
        for drone in drones:
            if drone.is_delivered():
                entregues += 1
            elif drone.current_connection is not None:
                nome = drone.current_connection.name
                em_transito.setdefault(nome, []).append(drone.drone_id)
            else:
                nome = drone.current_zone.name
                por_zona.setdefault(nome, []).append(drone.drone_id)

        blocos: List[str] = []
        for nome, ids in por_zona.items():
            zona = self._map.get_zone(nome)
            tipo = ""
            if zona.zone_type is not ZoneType.NORMAL:
                tipo = f"({zona.zone_type.value})"
            rotulo = self.paint(nome, zona.color) + tipo
            blocos.append(f"{rotulo}: {' '.join(ids)}")
        for nome, ids in em_transito.items():
            blocos.append(f"{nome} ->: {' '.join(ids)}")
        blocos.append(f"entregues: {entregues}/{len(drones)}")

        prefixo = f"   turno {turno} |"
        if self._cor:
            prefixo = f"{APAGADO}{prefixo}{RESET}"
        return f"{prefixo} " + " | ".join(blocos)

    def summary(
        self,
        drones: List[Drone],
        entregas: Dict[str, int],
        total_turnos: int,
    ) -> List[str]:
        """Métricas do fim da simulação.

        Para cada drone: turno da entrega, movimentos (= custo do
        caminho, já que restricted conta 2) e esperas (turnos parados
        antes de chegar). No fim, os totais e médias.

        Args:
            drones: Todos os drones da simulação.
            entregas: drone_id -> turno em que chegou na end.
            total_turnos: Turnos totais da simulação.

        Returns:
            As linhas do resumo (pintadas se a cor estiver ligada).
        """
        titulo = "=== métricas ==="
        linhas = [f"{NEGRITO}{titulo}{RESET}" if self._cor else titulo]
        movimentos = 0
        for drone in drones:
            chegou = entregas.get(drone.drone_id, total_turnos)
            esperas = chegou - drone.turns_taken
            movimentos += drone.turns_taken
            linhas.append(
                f"{drone.drone_id}: entregue no turno {chegou} | "
                f"custo {drone.turns_taken} | esperas {esperas}"
            )

        media = sum(entregas.values()) / len(entregas) if entregas else 0.0
        por_turno = movimentos / total_turnos if total_turnos else 0.0
        linhas.append(
            f"turnos totais: {total_turnos} | entrega média: "
            f"{media:.1f} | movimentos por turno: {por_turno:.1f}"
        )
        return linhas

    @staticmethod
    def _ansi(texto: str, rgb: Tuple[int, int, int]) -> str:
        """Envolve o texto num código ANSI truecolor.

        Args:
            texto: Texto a pintar.
            rgb: Cor (vermelho, verde, azul), de 0 a 255.

        Returns:
            O texto pintado, terminando com o reset de cor.
        """
        r, g, b = rgb
        return f"\033[38;2;{r};{g};{b}m{texto}{RESET}"
