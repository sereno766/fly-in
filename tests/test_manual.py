from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.parser import Parser, ParseError

# --- Caso de sucesso ---
p = Parser("maps/easy/01_linear_path.txt")
mapa, resultado = p.parse()
print("nb_drones lido:", resultado)
assert resultado == 2, f"Esperava 2, veio {resultado}"
print("✅ Teste 1 passou (mapa válido)")

try:
    Parser("maps/broken/dois_starts.txt").parse()
    print("❌ Teste FALHOU — deveria ter levantado ParseError")
except ParseError as e:
    print(f"✅ Teste passou: {e}")