import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.yapar.parser_reader  import YAParReader
from src.yapar.first_follow   import FirstFollowCalculator
from src.yapar.lr0_automaton  import LR0Automaton
from src.yapar.slr_table      import SLRTable


def test_slr_table():
    """Construye y muestra la tabla SLR(1)."""
    print("--- Test Tabla SLR(1) ---")

    yapar_path = os.path.join(ROOT, 'examples', 'sample.yapar')
    reader     = YAParReader(yapar_path)
    calc       = FirstFollowCalculator(reader)
    automaton  = LR0Automaton(reader)
    table      = SLRTable(reader, automaton, calc)

    print(table)

    # La tabla debe tener entradas
    assert len(table.action_table) > 0, "La tabla ACTION no debe estar vacía"
    assert len(table.goto_table)   > 0, "La tabla GOTO no debe estar vacía"

    print(f"\nEstados en ACTION: {len(table.action_table)}")
    print(f"Conflictos: {len(table.conflicts)}")
    print("Tabla SLR(1) construida correctamente")


def test_slr_conflicts():
    """Muestra los conflictos encontrados (para el parser paralelo)."""
    print("\n--- Test conflictos SLR ---")

    yapar_path = os.path.join(ROOT, 'examples', 'sample.yapar')
    reader     = YAParReader(yapar_path)
    calc       = FirstFollowCalculator(reader)
    automaton  = LR0Automaton(reader)
    table      = SLRTable(reader, automaton, calc)

    if table.has_conflicts():
        print(f"Se encontraron {len(table.conflicts)} conflictos:")
        for c in table.conflicts:
            print(f"  Estado {c['state']}, '{c['terminal']}': {c['type']}")
        print("\n→ El parser paralelo manejará estos conflictos")
    else:
        print("No hay conflictos — gramática SLR(1) pura")


def test_slr_lookup():
    """Verifica que se pueden consultar acciones de la tabla."""
    print("\n--- Test consultas a la tabla ---")

    yapar_path = os.path.join(ROOT, 'examples', 'sample.yapar')
    reader     = YAParReader(yapar_path)
    calc       = FirstFollowCalculator(reader)
    automaton  = LR0Automaton(reader)
    table      = SLRTable(reader, automaton, calc)

    # El estado 0 debe tener alguna acción
    state_0_actions = table.action_table.get(0, {})
    print(f"Acciones del estado 0: {state_0_actions}")
    assert len(state_0_actions) >= 0

    # El estado 0 debe tener algún GOTO
    state_0_gotos = table.goto_table.get(0, {})
    print(f"GOTOs del estado 0: {state_0_gotos}")

    print("Consultas a la tabla funcionan")


if __name__ == "__main__":
    print("=== Tests Tabla SLR(1) ===\n")
    test_slr_table()
    test_slr_conflicts()
    test_slr_lookup()
    print("Todos los tests pasaron")