import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.yapar.parser_reader      import YAParReader
from src.yapar.first_follow       import FirstFollowCalculator
from src.yapar.lr0_automaton      import LR0Automaton
from src.yapar.slr_table          import SLRTable
from src.yapar.lalr_table         import LALRTable
from src.yapar.shift_reduce_parser import (
    build_slr_parser, build_lalr_parser
)


def show_results(results, input_tokens):
    """Muestra los resultados de todos los caminos explorados."""
    print(f"\nEntrada: {input_tokens}")
    print(f"Caminos explorados: {len(results)}")

    accepted_paths = [r for r in results if r['accepted']]
    rejected_paths = [r for r in results if not r['accepted']]

    print(f"Caminos aceptados: {len(accepted_paths)}")
    print(f"Caminos rechazados: {len(rejected_paths)}")

    for result in results:
        status = "ACEPTADO" if result['accepted'] else "RECHAZADO"
        print(f"\n  Camino {result['path_id']}: {status}")

        # Mostrar últimos 3 pasos del camino
        last_steps = result['steps'][-3:]
        for step in last_steps:
            conflict_marker = " ⚡CONFLICTO" if step['conflict'] else ""
            print(f"    {step['action']}{conflict_marker}")

        # Mostrar árbol si fue aceptado
        if result['accepted'] and result['tree']:
            print(f"\n  Árbol sintáctico:")
            print(result['tree'].to_string(indent=2))


def test_slr_parser_valid():
    """Prueba el parser SLR con entrada válida."""
    print("--- Test Parser SLR — entrada válida ---")

    yapar_path = os.path.join(ROOT, 'examples', 'sample.yapar')
    reader     = YAParReader(yapar_path)
    calc       = FirstFollowCalculator(reader)
    lr0        = LR0Automaton(reader)
    slr        = SLRTable(reader, lr0, calc)
    parser     = build_slr_parser(reader, slr)

    # "x = 42"
    tokens = ['ID', 'EQUALS', 'INT', '$']
    results = parser.parse(tokens)
    show_results(results, tokens)

    accepted = any(r['accepted'] for r in results)
    assert accepted, "Al menos un camino debería aceptar 'ID EQUALS INT'"
    print("Parser SLR acepta entrada válida")


def test_slr_parser_invalid():
    """Prueba el parser SLR con entrada inválida."""
    print("\n--- Test Parser SLR — entrada inválida ---")

    yapar_path = os.path.join(ROOT, 'examples', 'sample.yapar')
    reader     = YAParReader(yapar_path)
    calc       = FirstFollowCalculator(reader)
    lr0        = LR0Automaton(reader)
    slr        = SLRTable(reader, lr0, calc)
    parser     = build_slr_parser(reader, slr)

    # "= 42 ID" — orden incorrecto
    tokens = ['EQUALS', 'INT', 'ID', '$']
    results = parser.parse(tokens)
    show_results(results, tokens)

    accepted = any(r['accepted'] for r in results)
    assert not accepted, "Ningún camino debería aceptar '= INT ID'"
    print("Parser SLR rechaza entrada inválida")


def test_lalr_parser():
    """Prueba el parser LALR."""
    print("\n--- Test Parser LALR ---")

    yapar_path = os.path.join(ROOT, 'examples', 'sample.yapar')
    reader     = YAParReader(yapar_path)
    calc       = FirstFollowCalculator(reader)
    lalr       = LALRTable(reader, calc)
    parser     = build_lalr_parser(reader, lalr)

    tokens  = ['ID', 'EQUALS', 'INT', '$']
    results = parser.parse(tokens)
    show_results(results, tokens)

    accepted = any(r['accepted'] for r in results)
    assert accepted, "LALR debería aceptar 'ID EQUALS INT'"
    print("Parser LALR correcto")


def test_parallel_conflict():
    """
    Muestra el paralelismo en acción cuando hay conflictos.
    """
    print("\n--- Test paralelismo con conflictos ---")

    yapar_path = os.path.join(ROOT, 'examples', 'sample.yapar')
    reader     = YAParReader(yapar_path)
    calc       = FirstFollowCalculator(reader)
    lr0        = LR0Automaton(reader)
    slr        = SLRTable(reader, lr0, calc)
    parser     = build_slr_parser(reader, slr)

    # Entrada más compleja que puede provocar conflictos
    tokens = ['ID', 'EQUALS', 'INT', 'PLUS', 'INT', '$']
    results = parser.parse(tokens)
    show_results(results, tokens)

    print(f"\nCaminos paralelos explorados: {len(results)}")
    if len(results) > 1:
        print("El parser exploró múltiples caminos en paralelo")
    else:
        print("No hubo conflictos — solo un camino")


if __name__ == "__main__":
    print("=== Tests Parser Shift-Reduce ===\n")
    test_slr_parser_valid()
    test_slr_parser_invalid()
    test_lalr_parser()
    test_parallel_conflict()
    print("Todos los tests completados")