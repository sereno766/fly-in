#!/usr/bin/env python3
"""Ponto de entrada do Fly-in.

Uso:
    ./main.py [--no-color] <arquivo_de_mapa>
"""

from __future__ import annotations

import argparse
import sys
from functools import partial
from typing import List, Optional

from src.parser import ParseError, Parser
from src.pathfinder import NoPathError
from src.renderer import Renderer
from src.reservation import ReservationTable
from src.scheduler import Scheduler
from src.simulation import Simulation, SimulationError


class FlyInApp:
    """Aplicação de linha de comando: lê o mapa, planeja e simula.

    Attributes:
        (privado) _args: Argumentos da linha de comando.
        (privado) _cor: True se a saída deve ser colorida.
    """

    def __init__(self, argv: Optional[List[str]] = None) -> None:
        """Lê os argumentos da linha de comando.

        Args:
            argv: Argumentos (sem o nome do programa). None usa
                sys.argv, que é o caso normal.
        """
        parser = argparse.ArgumentParser(
            description="Simulação de roteamento de drones (Fly-in)."
        )
        parser.add_argument("map", help="arquivo de mapa (.txt)")
        parser.add_argument(
            "--no-color",
            action="store_true",
            help="saída sem cores nem painel (só o formato D<ID>-<zona>)",
        )
        self._args = parser.parse_args(argv)
        # cor só num terminal: redirecionada para arquivo/pipe, a saída
        # fica exatamente no formato exigido, sem códigos ANSI
        self._cor = sys.stdout.isatty() and not self._args.no_color

    def run(self) -> int:
        """Executa o fluxo completo e imprime uma linha por turno.

        Parser -> Scheduler (planeja) -> Simulation (valida e executa)
        -> Renderer (mostra cada turno).

        Returns:
            Código de saída: 0 em caso de sucesso, 1 em caso de erro.
        """
        try:
            mapa, nb_drones = Parser(self._args.map).parse()
            plano = Scheduler(mapa, ReservationTable()).plan_all(nb_drones)
            simulacao = Simulation(mapa, nb_drones)
            renderer = Renderer(mapa, self._cor)
            # partial fixa simulação e renderer: o callback recebe só a linha
            simulacao.run(
                plano, partial(self._mostrar_turno, simulacao, renderer)
            )
            # métricas só no terminal: não podem misturar com o formato
            if self._cor:
                for linha in renderer.summary(simulacao.get_drones(),
                                              simulacao.delivery_turns(),
                                              simulacao.turn):
                    print(linha)
        except ParseError as erro:
            # a mensagem já começa com "Erro de parsing na linha N"
            print(erro, file=sys.stderr)
            return 1
        except (NoPathError, SimulationError) as erro:
            print(f"Erro: {erro}", file=sys.stderr)
            return 1
        except OSError as erro:
            print(
                f"Erro ao ler '{self._args.map}': {erro.strerror}",
                file=sys.stderr,
            )
            return 1
        except KeyboardInterrupt:
            print("\nInterrompido pelo usuário.", file=sys.stderr)
            return 130
        except Exception as erro:
            # rede de segurança: o programa nunca termina com traceback
            print(f"Erro inesperado: {erro}", file=sys.stderr)
            return 1
        return 0

    def _mostrar_turno(
        self, simulacao: Simulation, renderer: Renderer, linha: str
    ) -> None:
        """Imprime a linha de um turno e, no terminal, o painel.

        Chamado pela Simulation depois de cada turno (callback).

        Args:
            simulacao: Simulação em andamento (estado já atualizado).
            renderer: Quem formata a saída.
            linha: Linha do turno no formato D<ID>-<zona>.
        """
        print(renderer.format_line(linha))
        if self._cor:
            print(renderer.panel(simulacao.get_drones(), simulacao.turn))


if __name__ == "__main__":
    sys.exit(FlyInApp().run())
