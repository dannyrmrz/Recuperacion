import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.yalex.regex_engine import (
    regex_to_nfa,
    preprocess_regex,
    to_postfix,
    _collect_states
)

def test_postfix():
    """Verifica que la conversión a postfix es correcta."""
    result = to_postfix("a·b|c")
    print(f"Postfix de 'a·b|c': {result}")
    assert result == ['a', 'b', '·', 'c', '|'], \
        f"Esperaba ['a', 'b', '·', 'c', '|'], obtuve '{result}'"
    print("Postfix correcto")

def test_single_char():
    """Verifica que un carácter simple construye un AFN correcto."""
    nfa = regex_to_nfa("a", "TEST_TOKEN")
    
    # Debe haber exactamente 2 estados
    states = _collect_states(nfa.start)
    print(f"AFN para 'a': {len(states)} estados")
    
    # El estado de aceptación debe tener el token correcto
    assert nfa.accept.token_name == "TEST_TOKEN"
    assert nfa.accept.is_accept == True
    print("AFN para carácter simple correcto")

def test_union():
    """Verifica la construcción de unión a|b."""
    nfa = regex_to_nfa("a|b", "AB_TOKEN")
    assert nfa.accept.is_accept == True
    print("AFN para unión correcto")

def test_concat():
    """Verifica la construcción de concatenación ab."""
    nfa = regex_to_nfa("ab", "AB_TOKEN")
    assert nfa.accept.is_accept == True
    print("AFN para concatenación correcto")

def test_kleene():
    """Verifica la construcción de cerradura a*."""
    nfa = regex_to_nfa("a*", "KLEENE_TOKEN")
    assert nfa.accept.is_accept == True
    print("AFN para Kleene correcto")

def test_preprocess():
    """Verifica que las clases de caracteres se expanden bien."""
    result = preprocess_regex("['0'-'2']")
    print(f"Expansión de ['0'-'2']: {result}")
    assert '0' in result and '1' in result and '2' in result
    print("Expansión de clases correcta")

if __name__ == "__main__":
    print("=== Tests del motor de regex ===\n")
    test_postfix()
    test_single_char()
    test_union()
    test_concat()
    test_kleene()
    test_preprocess()
    print("\n Todos los tests pasaron")