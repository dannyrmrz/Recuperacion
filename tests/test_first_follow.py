import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.yapar.parser_reader import YAParReader
from src.yapar.first_follow import FirstFollowCalculator


def test_first_follow():
    """
    Verifica FIRST y FOLLOW con el archivo de ejemplo.
    """
    print("--- Test FIRST y FOLLOW ---")

    yapar_path = os.path.join(ROOT, 'examples', 'sample.yapar')
    reader = YAParReader(yapar_path)
    calc = FirstFollowCalculator(reader)

    print(calc)

    # FIRST de terminales siempre es el terminal mismo
    assert 'INT' in calc.get_first('INT'), "FIRST(INT) debe contener INT"

    # FIRST de 'factor' debe incluir INT y LPAREN
    first_factor = calc.get_first('factor')
    print(f"\nFIRST(factor) = {first_factor}")
    assert 'INT' in first_factor, "FIRST(factor) debe contener INT"

    # FOLLOW del símbolo inicial siempre incluye $
    follow_start = calc.get_follow(reader.start_symbol)
    print(f"FOLLOW({reader.start_symbol}) = {follow_start}")
    assert '$' in follow_start, "FOLLOW del símbolo inicial debe contener $"

    print("\n FIRST y FOLLOW correctos")


def test_first_sequence():
    """
    Verifica FIRST de una secuencia de símbolos.
    """
    print("\n--- Test FIRST de secuencia ---")

    yapar_path = os.path.join(ROOT, 'examples', 'sample.yapar')
    reader = YAParReader(yapar_path)
    calc = FirstFollowCalculator(reader)

    # FIRST de ['factor'] debe ser igual a FIRST(factor)
    seq_first = calc.get_first_of_sequence(['factor'])
    direct_first = calc.get_first('factor')
    assert seq_first == direct_first

    print(f"FIRST(['factor']) = {seq_first}")
    print(" FIRST de secuencia correcto")


if __name__ == "__main__":
    print("=== Tests FIRST y FOLLOW ===\n")
    test_first_follow()
    test_first_sequence()
    print("\n Todos los tests pasaron")