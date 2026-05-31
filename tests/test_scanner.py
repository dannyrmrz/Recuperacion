import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.yalex.lexer import YALexReader
from src.yalex.scanner import build_scanner_from_yalex, Scanner, Token
from src.yalex.regex_engine import regex_to_nfa, nfa_to_dfa


def test_scanner_manual():
    """
    Prueba el scanner construyendo los AFDs manualmente
    sin usar un archivo .yalex.
    """
    print("--- Test scanner manual ---")

    tokens_patterns = [
        ("['0'-'9']+",               "INT"),
        ("['a'-'z']['a'-'z''0'-'9']*", "ID"),
        ("'+'",                      "PLUS"),
        ("'-'",                      "MINUS"),
        ("'='",                      "EQUALS"),
        ("' '",                      None),    # espacio → ignorar
    ]

    dfa_list = []
    for pattern, token_name in tokens_patterns:
        nfa = regex_to_nfa(pattern, token_name)
        dfa = nfa_to_dfa(nfa)
        dfa_list.append((dfa, token_name))

    # Nombrado 'my_scanner' para no chocar con el módulo 'scanner' importado
    my_scanner = Scanner(dfa_list)

    source = "x = 42 + y"
    tokens, errors = my_scanner.tokenize(source)

    print(f"Código fuente: '{source}'")
    print("Tokens encontrados:")
    for token in tokens:
        print(f"  {token}")

    if errors:
        print("Errores:")
        for err in errors:
            print(f"  {err['message']}")

    real_tokens = [t for t in tokens if t.type != 'EOF']

    assert len(real_tokens) == 5, f"Esperaba 5 tokens, obtuve {len(real_tokens)}"
    assert real_tokens[0].type == 'ID'     and real_tokens[0].value == 'x'
    assert real_tokens[1].type == 'EQUALS' and real_tokens[1].value == '='
    assert real_tokens[2].type == 'INT'    and real_tokens[2].value == '42'
    assert real_tokens[3].type == 'PLUS'   and real_tokens[3].value == '+'
    assert real_tokens[4].type == 'ID'     and real_tokens[4].value == 'y'

    print("Scanner manual correcto")


def test_scanner_from_yalex():
    """
    Prueba el scanner usando el archivo .yalex de ejemplo.
    """
    print("\n--- Test scanner desde .yalex ---")

    # Ruta absoluta al archivo .yalex
    yalex_path = os.path.join(ROOT, 'examples', 'sample.yalex')
    reader = YALexReader(yalex_path)

    # Construir el scanner desde el archivo .yalex
    my_scanner = build_scanner_from_yalex(reader)

    source = "x = 42 + y"
    tokens, errors = my_scanner.tokenize(source)

    print(f"Código fuente: '{source}'")
    print("Tokens encontrados:")
    for token in tokens:
        print(f"  {token}")

    if errors:
        print("Errores encontrados:")
        for err in errors:
            print(f"  {err['message']}")
    else:
        print("Sin errores")

    print("Scanner desde .yalex correcto")


def test_error_reporting():
    """
    Verifica que el scanner reporta errores con línea y columna.
    """
    print("\n--- Test reporte de errores ---")

    tokens_patterns = [
        ("['0'-'9']+", "INT"),
        ("' '",         None),   # espacio → ignorar
    ]

    dfa_list = []
    for pattern, token_name in tokens_patterns:
        nfa = regex_to_nfa(pattern, token_name)
        dfa = nfa_to_dfa(nfa)
        dfa_list.append((dfa, token_name))

    my_scanner = Scanner(dfa_list)

    # '@' no está definido → debería generar un error
    source = "42 @ 10"
    tokens, errors = my_scanner.tokenize(source)

    assert len(errors) == 1, f"Esperaba 1 error, obtuve {len(errors)}"
    assert errors[0]['char'] == '@'
    assert errors[0]['line'] == 1

    print(f"Error detectado: {errors[0]['message']}")
    print("Reporte de errores correcto")


if __name__ == "__main__":
    print("=== Tests del Scanner ===\n")
    test_scanner_manual()
    test_scanner_from_yalex()
    test_error_reporting()
    print("\n Todos los tests pasaron")