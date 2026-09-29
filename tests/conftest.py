"""Configuração compartilhada dos testes.

Garante que a raiz do projeto esteja no sys.path, para que
'from src...' funcione independente de onde o pytest for executado.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
