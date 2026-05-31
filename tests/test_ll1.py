import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.yapar.parser_reader import YAParReader
from src.yapar.first_follow import FirstFollowCalculator
from src.yapar.ll1_table import LL1Table, LL1Parser


def test_ll1_table():
    """Construye y muestra la tabla LL(1) con gramática sin recursión izquierda."""
    print("--- Test tabla LL(1) ---")

    # Usamos la gramática LL(1) — sin recursión izquierda
    yapar_path = os.path.join(ROOT, 'examples', 'sample_ll1.yapar')
    reader = YAParReader(yapar_path)
    calc   = FirstFollowCalculator(reader)
    table  = LL1Table(reader, calc)

    print(table)

    if table.is_ll1():
        print("\n La gramática ES LL(1) — sin conflictos")
    else:
        print(f"\n La gramática NO es LL(1): {len(table.conflicts)} conflictos")
        for c in table.conflicts:
            p1 = ' '.join(c['production1'][1])
            p2 = ' '.join(c['production2'][1])
            print(f"  [{c['non_terminal']}][{c['terminal']}]: '{p1}' vs '{p2}'")


def test_ll1_parser_valid():
    """Prueba el parser LL(1) con una entrada válida."""
    print("\n--- Test parser LL(1) — entrada válida ---")

    yapar_path = os.path.join(ROOT, 'examples', 'sample_ll1.yapar')
    reader = YAParReader(yapar_path)
    calc   = FirstFollowCalculator(reader)
    table  = LL1Table(reader, calc)
    parser = LL1Parser(table)

    # "x = 42" → debería aceptar
    tokens = ['ID', 'EQUALS', 'INT', '$']
    accepted, steps = parser.parse(tokens)

    print(f"Entrada: {tokens}")
    print(f"\n{'Pila':45} {'Entrada restante':25} {'Acción'}")
    print('-' * 90)
    for step in steps:
        stack_str = str(step['stack'])
        input_str = str(step['input'])
        print(f"{stack_str:45} {input_str:25} {step['action']}")

    result = " ACEPTADO" if accepted else " RECHAZADO"
    print(f"\nResultado: {result}")
    assert accepted == True, "Debería aceptar 'ID EQUALS INT'"


def test_ll1_parser_invalid():
    """Prueba el parser LL(1) con una entrada inválida."""
    print("\n--- Test parser LL(1) — entrada inválida ---")

    yapar_path = os.path.join(ROOT, 'examples', 'sample_ll1.yapar')
    reader = YAParReader(yapar_path)
    calc   = FirstFollowCalculator(reader)
    table  = LL1Table(reader, calc)
    parser = LL1Parser(table)

    # "= 42 x" → debería rechazar (orden incorrecto)
    tokens = ['EQUALS', 'INT', 'ID', '$']
    accepted, steps = parser.parse(tokens)

    print(f"Entrada: {tokens}")
    last_step = steps[-1] if steps else {}
    print(f"Último paso: {last_step.get('action', '')}")

    result = "RECHAZADO correctamente" if not accepted else "Debería haber rechazado"
    print(f"Resultado: {result}")
    assert accepted == False, "Debería rechazar '= INT ID'"


if __name__ == "__main__":
    print("=== Tests LL(1) ===\n")
    test_ll1_table()
    test_ll1_parser_valid()
    test_ll1_parser_invalid()
    print("Todos los tests completados")