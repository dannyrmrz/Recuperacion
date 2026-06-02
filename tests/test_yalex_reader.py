import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.yalex.lexer import YALexReader

def test_reader():
    # Usar el archivo de ejemplo que ya creamos
    yalex_path = os.path.join(ROOT, 'examples', 'sample.yalex')
    reader = YALexReader(yalex_path)

    print(reader)  # Ver qué leyó

    # Verificar que leyó definiciones
    assert 'digit' in reader.definitions, "Debería haber leído 'digit'"
    assert 'letter' in reader.definitions, "Debería haber leído 'letter'"

    # Verificar que leyó reglas
    assert len(reader.rules) > 0, "Debería haber leído al menos una regla"

    # Verificar que la expansión funciona
    expanded = reader.expand_definitions()
    print("\n--- Reglas expandidas ---")
    for pattern, token in expanded:
        print(f"  '{pattern}' → {token}")

    print("\n Test pasado correctamente")

if __name__ == "__main__":
    test_reader()