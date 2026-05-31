import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.yalex.regex_engine import regex_to_nfa, nfa_to_dfa, simulate_dfa

def test_single_char():
    """El AFD para 'a' solo acepta la cadena 'a'."""
    nfa = regex_to_nfa("a", "CHAR_A")
    dfa = nfa_to_dfa(nfa)
    
    accepted, token = simulate_dfa(dfa, "a")
    assert accepted == True and token == "CHAR_A"
    
    accepted, token = simulate_dfa(dfa, "b")
    assert accepted == False
    
    print("AFD para carácter simple correcto")

def test_union():
    """El AFD para 'a|b' acepta 'a' y 'b' pero no 'c'."""
    nfa = regex_to_nfa("a|b", "AB")
    dfa = nfa_to_dfa(nfa)
    
    assert simulate_dfa(dfa, "a") == (True, "AB")
    assert simulate_dfa(dfa, "b") == (True, "AB")
    assert simulate_dfa(dfa, "c")[0] == False
    
    print("AFD para unión correcto")

def test_kleene():
    """El AFD para 'a*' acepta '', 'a', 'aa', 'aaa'."""
    nfa = regex_to_nfa("a*", "KLEENE")
    dfa = nfa_to_dfa(nfa)
    
    assert simulate_dfa(dfa, "")[0]   == True
    assert simulate_dfa(dfa, "a")[0]  == True
    assert simulate_dfa(dfa, "aa")[0] == True
    assert simulate_dfa(dfa, "b")[0]  == False
    
    print("AFD para Kleene correcto")

def test_digits():
    """El AFD para dígitos acepta '0'-'9'."""
    nfa = regex_to_nfa("['0'-'9']", "DIGIT")
    dfa = nfa_to_dfa(nfa)
    
    for d in "0123456789":
        accepted, token = simulate_dfa(dfa, d)
        assert accepted == True, f"Debería aceptar '{d}'"
    
    assert simulate_dfa(dfa, "a")[0] == False
    
    print("AFD para dígitos correcto")

def test_integer():
    """El AFD para ['0'-'9']+ acepta '1', '42', '100'."""
    nfa = regex_to_nfa("['0'-'9']+", "INT")
    dfa = nfa_to_dfa(nfa)
    
    assert simulate_dfa(dfa, "1")   == (True, "INT")
    assert simulate_dfa(dfa, "42")  == (True, "INT")
    assert simulate_dfa(dfa, "100") == (True, "INT")
    assert simulate_dfa(dfa, "")[0] == False
    assert simulate_dfa(dfa, "a")[0] == False
    
    print("AFD para enteros correcto")

def test_dfa_info():
    """Muestra información del AFD generado."""
    nfa = regex_to_nfa("['0'-'9']+", "INT")
    dfa = nfa_to_dfa(nfa)
    
    print(f"\n--- AFD para ['0'-'9']+ ---")
    print(f"  Estados totales: {len(dfa.states)}")
    print(f"  Estados de aceptación: {len(dfa.accept_states)}")
    print(f"  Estado inicial: {dfa.start.id}")
    for state in dfa.states:
        trans_str = {sym: s.id for sym, s in state.transitions.items()}
        print(f"  Estado {state.id}: accept={state.is_accept}, "
              f"token={state.token_name}, trans={trans_str}")

if __name__ == "__main__":
    print("=== Tests AFN → AFD ===\n")
    test_single_char()
    test_union()
    test_kleene()
    test_digits()
    test_integer()
    test_dfa_info()
    print("\n Todos los tests pasaron")