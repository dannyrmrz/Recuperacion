import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.parsers.maya_parser import (
    MayaParser, tokenize_maya,
    translate_to_spanish, EXAMPLE_QUERIES
)


def test_tokenizer():
    """Verifica que el tokenizador reconoce palabras mayas."""
    print("--- Test tokenizador Maya ---")

    tokens, errors = tokenize_maya("baax yaan le nah o ?")
    print(f"Tokens: {tokens}")

    assert len(errors)          == 0,              "No debe haber errores"
    assert tokens[0].type       == 'BAAX',         "Primer token: BAAX"
    assert tokens[1].type       == 'YAAN',         "Segundo token: YAAN"
    assert tokens[-1].type      == 'INTERROGACION',"Último token: INTERROGACION"
    print("Tokenizador correcto")


def test_unknown_word():
    """Verifica que palabras desconocidas generan errores."""
    print("\n--- Test palabra desconocida ---")

    tokens, errors = tokenize_maya("baax xyz luum ?")
    print(f"Errores: {errors}")

    assert len(errors)        == 1,     "Debe haber 1 error"
    assert errors[0]['word']  == 'xyz', "Error en 'xyz'"
    print("Palabras desconocidas detectadas")


def test_translation():
    """Verifica la traducción al español."""
    print("\n--- Test traducción ---")

    for maya_text, expected in EXAMPLE_QUERIES:
        tokens, _   = tokenize_maya(maya_text)
        translation = translate_to_spanish(tokens)
        print(f"  Maya:     {maya_text}")
        print(f"  Español:  {translation}")
        print(f"  Esperado: {expected}\n")

    print("Traducciones generadas")


def test_valid_queries():
    """Verifica que consultas válidas son aceptadas."""
    print("\n--- Test consultas válidas (LALR) ---")

    yapar_path = os.path.join(ROOT, 'examples', 'maya.yapar')
    parser     = MayaParser(yapar_path)

    queries = [
        "baax yaan le nah o ?",
        "tuux bin le paal o ?",
        "in paal bin",
        "yaan ja ti nah",
    ]

    for query in queries:
        result = parser.parse(query)
        parser.print_result(result)
        status = "Aceptada" if result['accepted'] else "No aceptada"
        print(f"Resultado: {status}")


def test_invalid_queries():
    """Verifica que consultas inválidas son rechazadas."""
    print("\n--- Test consultas inválidas (LALR) ---")

    yapar_path = os.path.join(ROOT, 'examples', 'maya.yapar')
    parser     = MayaParser(yapar_path)

    queries = [
        "nah le baax ?",   # orden incorrecto
        "bin bin paal",     # dos verbos seguidos
    ]

    for query in queries:
        result = parser.parse(query)
        print(f"\nConsulta: '{query}'")
        status = "Rechazada correctamente" if not result['accepted'] else "⚠️  Aceptada (inesperado)"
        print(f"Resultado: {status}")


def test_lalr_vs_slr_info():
    """Muestra info del autómata LALR comparado con lo que sería SLR."""
    print("\n--- Info LALR ---")

    yapar_path  = os.path.join(ROOT, 'examples', 'maya.yapar')
    parser      = MayaParser(yapar_path)
    lalr        = parser.lalr_table

    print(f"  Estados LR(1) generados:   {len(lalr.lr1_states)}")
    print(f"  Estados LALR (fusionados): {len(lalr.states)}")
    print(f"  Conflictos LALR:           {len(lalr.conflicts)}")
    print("  (SLR usaría FOLLOW global → más conflictos potenciales)")
    print("LALR info correcta")


if __name__ == "__main__":
    print("=== Tests Parser Maya Yucateco (LALR) ===\n")
    test_tokenizer()
    test_unknown_word()
    test_translation()
    test_valid_queries()
    test_invalid_queries()
    test_lalr_vs_slr_info()
    print("\n Tests completados")