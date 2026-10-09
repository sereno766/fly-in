#!/usr/bin/env python3
"""Ponto de entrada do Fly-in.

Uso:
    ./main.py <arquivo_de_mapa>
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from src.parser import ParseError, Parser
from src.pathfinder import NoPathError
from src.reservation import ReservationTable
from src.scheduler import Scheduler
from src.simulation import Simulation, SimulationError


class FlyInApp:
    """Aplicação de linha de comando: lê o mapa, planeja e simula."""

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
        self._args = parser.parse_args(argv)

    def run(self) -> int:
        """Executa o fluxo completo e imprime uma linha por turno.

        Parser -> Scheduler (planeja) -> Simulation (valida e executa).

        Returns:
            Código de saída: 0 em caso de sucesso, 1 em caso de erro.
        """
        try:
            mapa, nb_drones = Parser(self._args.map).parse()
            plano = Scheduler(mapa, ReservationTable()).plan_all(nb_drones)
            for linha in Simulation(mapa, nb_drones).run(plano):
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
        return 0


if __name__ == "__main__":
    sys.exit(FlyInApp().run())
