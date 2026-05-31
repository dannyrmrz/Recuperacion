# tests/test_lr0.py

import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.yapar.parser_reader import YAParReader
from src.yapar.lr0_automaton import LR0Automaton


def test_lr0():
    """Construye y muestra el autómata LR(0)."""
    print("--- Test Autómata LR(0) ---")

    # Usamos la gramática original (con recursión izquierda)
    # LR(0) sí puede manejarla
    yapar_path = os.path.join(ROOT, 'examples', 'sample.yapar')
    reader = YAParReader(yapar_path)
    automaton = LR0Automaton(reader)

    print(automaton)

    # Verificaciones básicas
    assert len(automaton.states) > 0, "Debería haber al menos un estado"
    assert automaton.initial_state is not None, "Debería haber estado inicial"

    print(f"Total de estados: {len(automaton.states)}")
    print("Autómata LR(0) construido correctamente")


def test_lr0_items():
    """Verifica que el estado inicial tiene los ítems correctos."""
    print("\n--- Test ítems del estado inicial ---")

    yapar_path = os.path.join(ROOT, 'examples', 'sample.yapar')
    reader = YAParReader(yapar_path)
    automaton = LR0Automaton(reader)

    initial = automaton.initial_state
    print(f"Estado inicial (Estado 0):")
    for item in sorted(initial.items, key=str):
        print(f"  {item}")

    # El estado inicial debe tener el ítem aumentado
    augmented_item_found = any(
        item.non_terminal == automaton.augmented_start
        for item in initial.items
    )
    assert augmented_item_found, "El estado inicial debe tener el ítem aumentado S' → • S"

    print("Estado inicial correcto")


def test_lr0_transitions():
    """Verifica que los estados tienen transiciones."""
    print("\n--- Test transiciones ---")

    yapar_path = os.path.join(ROOT, 'examples', 'sample.yapar')
    reader = YAParReader(yapar_path)
    automaton = LR0Automaton(reader)

    # El estado inicial debe tener transiciones
    assert len(automaton.initial_state.transitions) > 0, \
        "El estado inicial debe tener transiciones"

    print("Transiciones del estado inicial:")
    for symbol, dest in sorted(automaton.initial_state.transitions.items()):
        print(f"  --{symbol}--> Estado {dest.id}")

    print("Transiciones correctas")


if __name__ == "__main__":
    print("=== Tests Autómata LR(0) ===\n")
    test_lr0()
    test_lr0_items()
    test_lr0_transitions()
    print("Todos los tests pasaron")