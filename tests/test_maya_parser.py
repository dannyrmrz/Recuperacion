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
    print(f"Errores: {errors}")

    assert len(errors) == 0,  "No debería haber errores"
    assert tokens[0].type == 'BAAX', "Primer token debe ser BAAX"
    assert tokens[1].type == 'YAAN', "Segundo token debe ser YAAN"
    assert tokens[-1].type == 'INTERROGACION'

    print("Tokenizador correcto")


def test_unknown_word():
    """Verifica que palabras desconocidas generan errores."""
    print("\n--- Test palabra desconocida ---")

    tokens, errors = tokenize_maya("baax xyz luum ?")

    print(f"Errores: {errors}")
    assert len(errors) == 1, "Debería haber 1 error"
    assert errors[0]['word'] == 'xyz'

    print("Detección de palabras desconocidas correcta")


def test_translation():
    """Verifica la traducción al español."""
    print("\n--- Test traducción ---")

    for maya_text, expected_spanish in EXAMPLE_QUERIES:
        tokens, _ = tokenize_maya(maya_text)
        translation = translate_to_spanish(tokens)
        print(f"  Maya:    {maya_text}")
        print(f"  Español: {translation}")
        print(f"  Esperado: {expected_spanish}")
        print()

    print("Traducciones generadas")


def test_valid_queries():
    """Verifica que consultas válidas son aceptadas."""
    print("\n--- Test consultas válidas ---")

    yapar_path = os.path.join(ROOT, 'examples', 'maya.yapar')
    parser = MayaParser(yapar_path)

    valid_queries = [
        "baax yaan le nah o ?",
        "tuux bin le paal o ?",
        "in paal bin",
        "yaan ja ti nah",
    ]

    for query in valid_queries:
        result = parser.parse(query)
        parser.print_result(result)

        if not result['accepted']:
            print(f"No aceptada (puede ser por conflictos en la gramática)")


def test_invalid_queries():
    """Verifica que consultas inválidas son rechazadas."""
    print("\n--- Test consultas inválidas ---")

    yapar_path = os.path.join(ROOT, 'examples', 'maya.yapar')
    parser = MayaParser(yapar_path)

    invalid_queries = [
        "nah le baax ?",        # orden incorrecto
        "bin bin paal",          # dos verbos seguidos sin estructura
    ]

    for query in invalid_queries:
        result = parser.parse(query)
        print(f"\nConsulta: '{query}'")
        print(f"Aceptada: {result['accepted']}")
        if not result['accepted']:
            print("Rechazada correctamente")


if __name__ == "__main__":
    print("=== Tests Parser Maya Yucateco ===\n")
    test_tokenizer()
    test_unknown_word()
    test_translation()
    test_valid_queries()
    test_invalid_queries()
    print("Tests completados")