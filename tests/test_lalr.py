import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.yapar.parser_reader import YAParReader
from src.yapar.first_follow  import FirstFollowCalculator
from src.yapar.slr_table     import SLRTable
from src.yapar.lr0_automaton import LR0Automaton
from src.yapar.lalr_table    import LALRTable


def test_lalr_table():
    """Construye y muestra la tabla LALR."""
    print("--- Test Tabla LALR ---")

    yapar_path = os.path.join(ROOT, 'examples', 'sample.yapar')
    reader     = YAParReader(yapar_path)
    calc       = FirstFollowCalculator(reader)
    table      = LALRTable(reader, calc)

    print(table)

    assert len(table.action_table) > 0
    assert len(table.goto_table)   > 0
    print("Tabla LALR construida correctamente")


def test_lalr_vs_slr():
    """
    Compara SLR y LALR para ver la diferencia en número de conflictos.
    LALR debería tener igual o menos conflictos que SLR.
    """
    print("\n--- Comparación SLR vs LALR ---")

    yapar_path = os.path.join(ROOT, 'examples', 'sample.yapar')
    reader     = YAParReader(yapar_path)
    calc       = FirstFollowCalculator(reader)

    # SLR
    lr0       = LR0Automaton(reader)
    slr_table = SLRTable(reader, lr0, calc)

    # LALR
    lalr_table = LALRTable(reader, calc)

    print(f"SLR  — Estados: {len(slr_table.action_table)}, "
          f"Conflictos: {len(slr_table.conflicts)}")
    print(f"LALR — Estados LR(1): {len(lalr_table.lr1_states)}, "
          f"Estados fusionados: {len(lalr_table.states)}, "
          f"Conflictos: {len(lalr_table.conflicts)}")

    # LALR no debería tener MÁS conflictos que SLR
    assert len(lalr_table.conflicts) <= len(slr_table.conflicts), \
        "LALR no debería tener más conflictos que SLR"

    print("LALR tiene igual o menos conflictos que SLR")


if __name__ == "__main__":
    print("=== Tests Tabla LALR ===\n")
    test_lalr_table()
    test_lalr_vs_slr()
    print("Todos los tests pasaron")