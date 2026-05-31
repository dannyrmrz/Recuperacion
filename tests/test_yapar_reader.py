import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.yapar.parser_reader import YAParReader


def test_reader():
    """Verifica que el lector extrae bien tokens y gramática."""
    print("--- Test YAPar reader ---")

    yapar_path = os.path.join(ROOT, 'examples', 'sample.yapar')
    reader = YAParReader(yapar_path)

    print(reader)

    # Verificar que leyó los tokens
    assert 'INT' in reader.tokens,  "Debería haber leído INT"
    assert 'PLUS' in reader.tokens, "Debería haber leído PLUS"
    assert 'ID' in reader.tokens,   "Debería haber leído ID"

    # Verificar que leyó producciones
    assert len(reader.grammar) > 0, "Debería haber leído producciones"

    # Verificar que tiene símbolo inicial
    assert reader.start_symbol is not None, "Debería tener símbolo inicial"
    print(f"\nSímbolo inicial: {reader.start_symbol}")

    # Verificar que distingue terminales de no terminales
    terminals = reader.get_terminals()
    non_terminals = reader.get_non_terminals()
    print(f"Terminales: {terminals}")
    print(f"No terminales: {non_terminals}")

    # Un terminal NO debe ser no terminal y viceversa
    overlap = terminals & non_terminals
    assert len(overlap) == 0, f"Hay símbolos en ambos conjuntos: {overlap}"

    print("\n YAPar reader correcto")


def test_productions():
    """Verifica que las producciones se extraen correctamente."""
    print("\n--- Test producciones ---")

    yapar_path = os.path.join(ROOT, 'examples', 'sample.yapar')
    reader = YAParReader(yapar_path)

    # Verificar producciones de 'expresion'
    prods = reader.get_productions_for('expresion')
    print(f"Producciones de 'expresion': {prods}")
    assert len(prods) > 0, "Debería haber producciones para 'expresion'"

    print(" Producciones correctas")


if __name__ == "__main__":
    print("=== Tests del YAPar Reader ===\n")
    test_reader()
    test_productions()
    print("\n Todos los tests pasaron")