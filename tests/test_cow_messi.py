# Pruebas de analisis sintactico para COW y MessiScript.
# El objetivo es demostrar que el parser puede analizar estos lenguajes sin errores lexicos ni sintacticos.

import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.parsers.cow_parser   import COWParser,   tokenize_cow,   EXAMPLE_PROGRAMS as COW_EXAMPLES
from src.parsers.messi_parser import MessiParser, tokenize_messi, EXAMPLE_PROGRAMS as MESSI_EXAMPLES

# TESTS COW
def test_cow_tokenizer():
    """Verifica que el tokenizador reconoce las 12 instrucciones."""
    print("--- Test tokenizador COW ---")

    code   = "moo MoO MOO moO mOo OOM"
    tokens, errors = tokenize_cow(code)

    print(f"Tokens: {[t.type for t in tokens]}")
    assert len(errors) == 0, "No debe haber errores"
    assert len(tokens) == 6, "Debe haber 6 tokens"
    assert tokens[0].type == 'INSTR_moo'
    assert tokens[2].type == 'INSTR_MOO'
    print("Tokenizador COW correcto")


def test_cow_all_12_instructions():
    """Verifica que las 12 instrucciones son reconocidas."""
    print("\n--- Test las 12 instrucciones COW ---")

    code   = "moo mOo moO mOO Moo MOo MoO MOO OOO MMM OOM oom"
    tokens, errors = tokenize_cow(code)

    print(f"Tokens ({len(tokens)}): {[t.type for t in tokens]}")
    assert len(errors) == 0,  "No debe haber errores"
    assert len(tokens) == 12, "Deben ser exactamente 12"
    print("Las 12 instrucciones reconocidas")


def test_cow_invalid_instruction():
    """Verifica que instrucciones no validas generan errores."""
    print("\n--- Test instruccion invalida COW ---")

    code   = "moo MoO INVALID moO"
    tokens, errors = tokenize_cow(code)

    print(f"Errores: {errors}")
    assert len(errors) == 1
    assert errors[0]['word'] == 'INVALID'
    print("Instruccion invalida detectada")


def test_cow_valid_programs():
    """Prueba los programas de ejemplo de COW con el parser LALR."""
    print("\n--- Test programas COW validos ---")

    yapar_path = os.path.join(ROOT, 'examples', 'cow.yapar')
    parser     = COWParser(yapar_path)

    for example in COW_EXAMPLES:
        print(f"\n  Programa: '{example['name']}'")
        print(f"  Descripcion: {example['description']}")
        result = parser.parse(example['code'])
        parser.print_result(result)

        status = "VALIDO" if result['accepted'] else "INVALIDO"
        print(f"  -> {status}")


def test_cow_empty_program():
    """Verifica que un programa vacio es rechazado."""
    print("\n--- Test programa COW vacio ---")

    yapar_path = os.path.join(ROOT, 'examples', 'cow.yapar')
    parser     = COWParser(yapar_path)

    result = parser.parse("")
    print(f"Errores: {result['errors']}")
    assert not result['accepted']
    print("Programa vacio rechazado correctamente")

# TESTS MESSISCRIPT
def test_messi_tokenizer_basic():
    """Verifica que el tokenizador reconoce comandos basicos."""
    print("\n--- Test tokenizador MessiScript basico ---")

    code   = "La agarra Messi. La pisa Messi. Le pega Messiiiii... gol!"
    tokens, errors = tokenize_messi(code)

    print(f"Tokens: {[(t.type, t.line) for t in tokens]}")
    types = [t.type for t in tokens]

    assert 'CMD_INICIO' in types, "Debe tener CMD_INICIO"
    assert 'CMD_PISA'   in types, "Debe tener CMD_PISA"
    assert 'CMD_FIN'    in types, "Debe tener CMD_FIN"
    print("Tokenizador MessiScript correcto")


def test_messi_va_command():
    """Verifica que el comando 'va messi' con contenido se tokeniza bien."""
    print("\n--- Test comando VA MESSI ---")

    code = "La agarra Messi. Va Messi, moviendo la pelota con clase. Le pega Messiiiii... gol!"
    tokens, _ = tokenize_messi(code)

    types = [t.type for t in tokens]
    print(f"Tokens: {types}")

    assert 'CMD_VA'      in types, "Debe tener CMD_VA"
    assert 'CONTENIDO'   in types, "Debe tener CONTENIDO para el valor"
    print("Comando VA MESSI tokenizado correctamente")


def test_messi_normalize():
    """Verifica que acentos y signos especiales no rompen el tokenizador."""
    print("\n--- Test normalizacion de acentos ---")

    # Con acentos y signos especiales como en el repositorio original
    code = "La agarra Messi. ¡Le pega Messiiiii... gol!"
    tokens, errors = tokenize_messi(code)

    types = [t.type for t in tokens]
    print(f"Tokens: {types}")
    print(f"Errores: {errors}")

    assert 'CMD_INICIO' in types
    assert 'CMD_FIN'    in types
    print("Normalizacion correcta")


def test_messi_valid_programs():
    """
    Prueba los programas de ejemplo oficiales del repositorio.
    Estos son los mismos programas que usa el interprete original.
    """
    print("\n--- Test programas MessiScript del repositorio ---")

    yapar_path = os.path.join(ROOT, 'examples', 'messi.yapar')
    parser     = MessiParser(yapar_path)

    for example in MESSI_EXAMPLES:
        print(f"\n  Programa: '{example['name']}'")
        print(f"  Descripcion: {example['description']}")
        result = parser.parse(example['code'])
        parser.print_result(result)

        status = "VALIDO" if result['accepted'] else "INVALIDO"
        print(f"  -> {status}")


def test_messi_invalid_no_start():
    """Verifica que un programa sin CMD_INICIO es invalido."""
    print("\n--- Test MessiScript sin inicio ---")

    yapar_path = os.path.join(ROOT, 'examples', 'messi.yapar')
    parser     = MessiParser(yapar_path)

    # No empieza con "la agarra messi"
    code   = "La pisa Messi. Le pega Messiiiii... gol!"
    result = parser.parse(code)

    print(f"Comandos: {result['commands']}")
    assert not result['accepted'], "Debe rechazar programa sin inicio"
    print("Programa sin inicio rechazado correctamente")


def test_messi_invalid_no_end():
    """Verifica que un programa sin CMD_FIN es invalido."""
    print("\n--- Test MessiScript sin fin ---")

    yapar_path = os.path.join(ROOT, 'examples', 'messi.yapar')
    parser     = MessiParser(yapar_path)

    # No termina con "le pega messiiiii... gol!"
    code   = "La agarra Messi. La pisa Messi."
    result = parser.parse(code)

    print(f"Comandos: {result['commands']}")
    assert not result['accepted'], "Debe rechazar programa sin fin"
    print("Programa sin fin rechazado correctamente")

# MAIN
if __name__ == "__main__":
    print("=== Pruebas de analisis sintactico: COW y MessiScript ===\n")

    print("COW LANGUAGE")
    print("-" * 40)
    test_cow_tokenizer()
    test_cow_all_12_instructions()
    test_cow_invalid_instruction()
    test_cow_valid_programs()
    test_cow_empty_program()

    print("\n\nMESSISCRIPT")
    print("-" * 40)
    test_messi_tokenizer_basic()
    test_messi_va_command()
    test_messi_normalize()
    test_messi_valid_programs()
    test_messi_invalid_no_start()
    test_messi_invalid_no_end()

    print("\nPruebas COW y MessiScript completadas")