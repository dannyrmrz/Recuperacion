import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.parsers.valorant_parser import (
    ValorantParser, tokenize_valorant, EXAMPLE_PROGRAMS
)


def test_tokenizer_basic():
    """Verifica que el tokenizador reconoce keywords y operadores."""
    print("--- Test tokenizador básico ---")

    tokens, errors = tokenize_valorant("ability credits kills plant 10")
    print(f"Tokens: {tokens}")

    assert len(errors)       == 0,          "No debe haber errores"
    assert tokens[0].type    == 'ABILITY',  "Token 0: ABILITY"
    assert tokens[1].type    == 'CREDITS',  "Token 1: CREDITS"
    assert tokens[2].type    == 'ID',       "Token 2: ID"
    assert tokens[3].type    == 'PLANT',    "Token 3: PLANT"
    assert tokens[4].type    == 'INT',      "Token 4: INT"
    print("Tokenizador básico correcto")


def test_tokenizer_keywords():
    """Verifica que keywords no se confunden con identificadores."""
    print("\n--- Test keywords vs identificadores ---")

    tokens, _ = tokenize_valorant("gg ggez round roundwin")
    types     = [t.type for t in tokens]
    print(f"Tokens: {types}")

    assert types[0] == 'GG',    "'gg' → GG"
    assert types[1] == 'ID',    "'ggez' → ID"
    assert types[2] == 'ROUND', "'round' → ROUND"
    assert types[3] == 'ID',    "'roundwin' → ID"
    print("Keywords vs identificadores correcto")


def test_tokenizer_comments():
    """Verifica que los comentarios son ignorados."""
    print("\n--- Test comentarios ---")

    code = (
        "// Comentario ignorado\n"
        "ability credits x plant 5\n"
        "callout x"
    )
    tokens, errors = tokenize_valorant(code)
    types = [t.type for t in tokens]
    print(f"Tokens: {types}")

    assert 'ABILITY' in types, "Debe tener ABILITY"
    assert 'CALLOUT' in types, "Debe tener CALLOUT"
    print("Comentarios ignorados")


def test_tokenizer_errors():
    """Verifica que caracteres no reconocidos generan errores."""
    print("\n--- Test errores léxicos ---")

    tokens, errors = tokenize_valorant("ability credits x plant 5 @ 3")
    print(f"Errores: {errors}")

    assert len(errors)         == 1,   "Debe haber 1 error"
    assert errors[0]['char']   == '@', "Error en '@'"
    print("Errores léxicos detectados")


def test_valid_programs():
    """Prueba programas de ejemplo con LALR."""
    print("\n--- Test programas válidos (LALR) ---")

    yapar_path = os.path.join(ROOT, 'examples', 'valorant.yapar')
    parser     = ValorantParser(yapar_path)

    for example in EXAMPLE_PROGRAMS:
        print(f"\n  Programa: '{example['name']}'")
        result = parser.parse(example['code'])
        parser.print_result(result)
        status = "Válido" if result['accepted'] else "No aceptado"
        print(f"  → {status}")


def test_invalid_syntax():
    """Verifica que código con sintaxis incorrecta es rechazado."""
    print("\n--- Test sintaxis inválida (LALR) ---")

    yapar_path = os.path.join(ROOT, 'examples', 'valorant.yapar')
    parser     = ValorantParser(yapar_path)

    invalid = [
        "ability credits x plant",   # plant sin valor
        "spike gg callout x gg",      # spike sin condición
        "plant ability credits x 5",  # orden incorrecto
    ]

    for code in invalid:
        result = parser.parse(code)
        status = "Rechazado" if not result['accepted'] else "Aceptado (inesperado)"
        print(f"\n  '{code}'")
        print(f"  → {status}")


def test_lalr_info():
    """Muestra información del autómata LALR generado."""
    print("\n--- Info LALR ValorantScript ---")

    yapar_path = os.path.join(ROOT, 'examples', 'valorant.yapar')
    parser     = ValorantParser(yapar_path)
    lalr       = parser.lalr_table

    print(f"  Estados LR(1) generados:   {len(lalr.lr1_states)}")
    print(f"  Estados LALR (fusionados): {len(lalr.states)}")
    print(f"  Conflictos LALR:           {len(lalr.conflicts)}")
    print("LALR info correcta")


def test_parallel_parsing():
    """Muestra el parser paralelo en acción si hay conflictos."""
    print("\n--- Test parser paralelo (LALR) ---")

    yapar_path = os.path.join(ROOT, 'examples', 'valorant.yapar')
    parser     = ValorantParser(yapar_path)

    code = (
        "ability credits x plant 5\n"
        "ability credits y plant x + 3 - 1\n"
        "callout y"
    )
    result   = parser.parse(code)
    parser.print_result(result)

    total    = len(result['paths'])
    accepted = sum(1 for r in result['paths'] if r['accepted'])
    print(f"\nCaminos explorados: {total} ({accepted} aceptados)")


if __name__ == "__main__":
    print("=== Tests ValorantScript Parser (LALR) ===\n")
    test_tokenizer_basic()
    test_tokenizer_keywords()
    test_tokenizer_comments()
    test_tokenizer_errors()
    test_valid_programs()
    test_invalid_syntax()
    test_lalr_info()
    test_parallel_parsing()
    print("\n Tests completados")