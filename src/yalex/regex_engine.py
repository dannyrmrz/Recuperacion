# Implementa el algoritmo de Thompson para convertir una expresión regular en un AFN 

# El proceso es:
# 1. Tomar la regex como texto
# 2. Convertirla a notación postfix (más fácil de procesar)
# 3. Construir el AFN usando el algoritmo de Thompson

class State:
    """
    Representa un estado del autómata.
    
    Cada estado tiene:
    - id: número único para identificarlo
    - transitions: diccionario de {símbolo: [lista de estados destino]}
      El símbolo puede ser un carácter ('a', 'b') o 'ε' para épsilon
    - is_accept: si es un estado de aceptación (estado final)
    - token_name: si es estado de aceptación, qué token produce
    """
    
    # Contador global para dar IDs únicos a cada estado
    _counter = 0
    
    def __init__(self):
        self.id = State._counter
        State._counter += 1
        self.transitions = {}   # {'a': [state1, state2], 'ε': [state3]}
        self.is_accept = False
        self.token_name = None  # Solo relevante si is_accept = True
    
    def add_transition(self, symbol, state):
        """
        Agrega una transición desde este estado.
        symbol: el carácter o 'ε'
        state: el estado destino
        """
        if symbol not in self.transitions:
            self.transitions[symbol] = []
        self.transitions[symbol].append(state)
    
    def __repr__(self):
        return f"State({self.id}, accept={self.is_accept})"


class NFA:
    """
    Representa un AFN completo.
    Tiene un estado inicial y un estado de aceptación.
    (Thompson siempre produce AFNs con exactamente 1 estado de aceptación)
    """
    
    def __init__(self, start, accept):
        self.start = start    # Estado inicial
        self.accept = accept  # Estado de aceptación

def preprocess_regex(regex):
    # Paso 1: PRIMERO expandir clases ['0'-'9'] → (0|1|...|9)
    # porque adentro de los corchetes también hay comillas simples
    regex = expand_char_classes(regex)
    
    # Paso 2: DESPUÉS convertir literales sueltos '+' → \+
    # ya no hay corchetes que interfieran
    regex = _handle_quoted_literals(regex)
    
    # Paso 3: agregar concatenación explícita
    regex = add_concat_operator(regex)
    
    return regex


def _handle_quoted_literals(regex):
    """
    Convierte caracteres entre comillas simples a forma escapada.
    
    En el archivo .yalex, los caracteres literales van entre comillas:
        '+' significa el carácter más, NO el operador kleene+
        '*' significa el carácter asterisco, NO el operador kleene*
    
    Nosotros los convertimos a \\c (con backslash) para distinguirlos
    de los operadores durante el procesamiento.
    
    Ejemplos:
        '+' → \\+
        'a' → \\a
        '*' → \\*
    """
    result = []
    i = 0
    
    while i < len(regex):
        # ¿Encontramos una comilla simple?
        if regex[i] == "'" and i + 2 < len(regex) and regex[i + 2] == "'":
            char = regex[i + 1]
            # Agregar con backslash para marcarlo como literal
            result.append('\\')
            result.append(char)
            i += 3  # saltar toda la secuencia 'c'
        else:
            result.append(regex[i])
            i += 1
    
    return ''.join(result)


def expand_char_classes(regex):
    """
    Convierte clases de caracteres al formato de unión.
    
    Ejemplos:
        ['0'-'9']  →  (0|1|2|3|4|5|6|7|8|9)
        ['a'-'z']  →  (a|b|c|...|z)
        ['a''b']   →  (a|b)
    
    El formato en .yalex usa corchetes y comillas simples.
    """
    result = []
    i = 0
    
    while i < len(regex):
        if regex[i] == '[':
            # Encontramos una clase de caracteres
            # Buscar el cierre ']'
            j = regex.index(']', i)
            class_content = regex[i+1:j]  # lo que está dentro de [...]
            
            # Expandir el contenido de la clase
            chars = parse_char_class(class_content)
            
            # Convertir a unión: (a|b|c|...)
            union = '|'.join(chars)
            result.append(f'({union})')
            
            i = j + 1  # saltar hasta después del ']'
        else:
            result.append(regex[i])
            i += 1
    
    return ''.join(result)


def parse_char_class(content):
    """
    Parsea el contenido de una clase de caracteres.
    Soporta rangos 'a'-'z' y secuencias de escape \t, \n, \r.
    """
    # Mapa de secuencias de escape
    ESCAPES = {'t': '\t', 'n': '\n', 'r': '\r', '\\': '\\'}

    chars = []
    i = 0

    while i < len(content):
        # Saltar espacios
        if content[i] == ' ':
            i += 1
            continue

        # Solo procesamos lo que empieza con comilla
        if content[i] != "'":
            i += 1
            continue

        # Verificar que hay algo despues de la comilla
        if i + 1 >= len(content):
            break

        # Leer el caracter — puede ser normal 'x' o escape '\t'
        if content[i + 1] == '\\' and i + 2 < len(content):
            # Secuencia de escape: '\t', '\n', '\r'
            escape_key = content[i + 2]
            char1 = ESCAPES.get(escape_key, escape_key)
            # Saltar '\x' y la comilla de cierre si existe
            i += 4 if (i + 3 < len(content) and content[i + 3] == "'") else 3
        else:
            # Caracter normal: 'x'
            char1 = content[i + 1]
            i += 3  # saltar 'x'

        # Ver si hay un rango '-' despues
        if i < len(content) and content[i:i + 2] == "-'":
            if i + 2 >= len(content):
                chars.append(char1)
                continue

            # Leer el caracter del lado derecho del rango
            if content[i + 2] == '\\' and i + 3 < len(content):
                escape_key = content[i + 3]
                char2 = ESCAPES.get(escape_key, escape_key)
                i += 5 if (i + 4 < len(content) and content[i + 4] == "'") else 4
            else:
                char2 = content[i + 2]
                i += 4

            # Expandir el rango
            for c in range(ord(char1), ord(char2) + 1):
                chars.append(chr(c))
        else:
            chars.append(char1)

    return chars


def add_concat_operator(regex):
    """
    Agrega el operador de concatenación '·' de forma explícita.
    """
    left_chars = set('abcdefghijklmnopqrstuvwxyz'
                     'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                     '0123456789)*+?')
    
    right_chars = set('abcdefghijklmnopqrstuvwxyz'
                      'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                      '0123456789(\\')  # ← agregar \\ aquí
    
    result = []
    i = 0
    
    while i < len(regex):
        char = regex[i]
        
        # Si es un carácter escapado \c, tratarlo como UN solo operando
        if char == '\\' and i + 1 < len(regex):
            next_char = regex[i + 1]
            result.append(char)
            result.append(next_char)
            
            # ¿Necesitamos concatenación después del \c?
            if i + 2 < len(regex):
                after = regex[i + 2]
                if after in right_chars or after == '\\':
                    result.append('·')
            
            i += 2  # saltar \c completo
            continue
        
        result.append(char)
        
        if i + 1 < len(regex):
            next_char = regex[i + 1]
            # No agregar · si el siguiente es parte de un escape
            if char in left_chars and (next_char in right_chars):
                result.append('·')
        
        i += 1
    
    return ''.join(result)

def to_postfix(regex):
    """
    Convierte regex de infix a postfix (Shunting Yard).
    """
    precedence = {'|': 1, '·': 2, '*': 3, '+': 3, '?': 3}
    
    output = []
    stack = []
    i = 0
    
    while i < len(regex):
        char = regex[i]
        
        # Si es un carácter escapado \c → tratarlo como operando simple
        if char == '\\' and i + 1 < len(regex):
            output.append(char + regex[i + 1])  # agregar '\c' como unidad
            i += 2
            continue
        
        if char == '(':
            stack.append(char)
            
        elif char == ')':
            while stack and stack[-1] != '(':
                output.append(stack.pop())
            if stack:
                stack.pop()
                
        elif char in precedence:
            while (stack and
                   stack[-1] != '(' and
                   stack[-1] in precedence and
                   precedence[stack[-1]] >= precedence[char]):
                output.append(stack.pop())
            stack.append(char)
            
        else:
            output.append(char)
        
        i += 1
    
    while stack:
        output.append(stack.pop())
    
    return output  # ← ahora retorna LISTA en vez de string (maneja \c de 2 chars)

# AFN Thompson
def build_nfa_from_postfix(postfix):
    """
    Construye el AFN desde postfix.
    postfix ahora es una LISTA de tokens (cada elemento puede ser \\c o un char).
    """
    stack = []
    
    for token in postfix:  # ← iteramos sobre lista, no sobre string
        
        if token == '·':
            nfa2 = stack.pop()
            nfa1 = stack.pop()
            stack.append(_concat(nfa1, nfa2))
            
        elif token == '|':
            nfa2 = stack.pop()
            nfa1 = stack.pop()
            stack.append(_union(nfa1, nfa2))
            
        elif token == '*':
            nfa = stack.pop()
            stack.append(_kleene(nfa))
            
        elif token == '+':
            nfa = stack.pop()
            nfa_copy = stack_copy_nfa(nfa)
            stack.append(_concat(nfa, _kleene(nfa_copy)))
            
        elif token == '?':
            nfa = stack.pop()
            stack.append(_optional(nfa))
            
        else:
            # Carácter literal — si es \c, extraer solo c
            if token.startswith('\\') and len(token) == 2:
                actual_char = token[1]  # el carácter real sin el backslash
            else:
                actual_char = token
            stack.append(_single_char(actual_char))
    
    if not stack:
        raise ValueError("La expresión regular está vacía o es inválida")
    
    return stack.pop()


def _single_char(char):
    """
    Crea el AFN más simple posible para un carácter.
    
    Estructura:
    (start) --char--> (accept)
    """
    start = State()
    accept = State()
    accept.is_accept = True
    start.add_transition(char, accept)
    return NFA(start, accept)


def _concat(nfa1, nfa2):
    """
    Concatena dos AFNs: nfa1 seguido de nfa2.
    
    Conecta el estado de aceptación de nfa1 con ε al estado inicial de nfa2.
    
    Estructura:
    [nfa1_start ... nfa1_accept] --ε--> [nfa2_start ... nfa2_accept]
    """
    # El estado de aceptación de nfa1 ya no es de aceptación
    nfa1.accept.is_accept = False
    # Conectar con ε al inicio de nfa2
    nfa1.accept.add_transition('ε', nfa2.start)
    # El nuevo AFN va desde el inicio de nfa1 hasta el fin de nfa2
    return NFA(nfa1.start, nfa2.accept)


def _union(nfa1, nfa2):
    """
    Une dos AFNs: acepta lo que acepta nfa1 O lo que acepta nfa2.
    
    Estructura:
              ε→ [nfa1] --ε→
    → (start)                 (accept)
              ε→ [nfa2] --ε→
    """
    start = State()
    accept = State()
    accept.is_accept = True
    
    # Conectar nuevo inicio con ε a ambos AFNs
    start.add_transition('ε', nfa1.start)
    start.add_transition('ε', nfa2.start)
    
    # Los estados de aceptación anteriores apuntan con ε al nuevo final
    nfa1.accept.is_accept = False
    nfa2.accept.is_accept = False
    nfa1.accept.add_transition('ε', accept)
    nfa2.accept.add_transition('ε', accept)
    
    return NFA(start, accept)


def _kleene(nfa):
    """
    Cerradura de Kleene: acepta el lenguaje de nfa repetido 0 o más veces.
    
    Estructura:
              ε──────────────────────→
    → (start) ε→ [nfa_start...accept] ε→ (new_accept)
              ←──────────────ε
    """
    start = State()
    accept = State()
    accept.is_accept = True
    
    # El nuevo inicio va con ε al AFN Y al nuevo estado de aceptación (0 veces)
    start.add_transition('ε', nfa.start)
    start.add_transition('ε', accept)
    
    # El estado de aceptación del AFN vuelve al inicio (repetir)
    # Y también va al nuevo estado de aceptación (terminar)
    nfa.accept.is_accept = False
    nfa.accept.add_transition('ε', nfa.start)
    nfa.accept.add_transition('ε', accept)
    
    return NFA(start, accept)


def _optional(nfa):
    """
    Operador ?: acepta el lenguaje de nfa O la cadena vacía.
    
    Es equivalente a nfa | ε_nfa
    """
    start = State()
    accept = State()
    accept.is_accept = True
    
    # Puede ir por el AFN o saltar directo al final (0 veces)
    start.add_transition('ε', nfa.start)
    start.add_transition('ε', accept)
    
    nfa.accept.is_accept = False
    nfa.accept.add_transition('ε', accept)
    
    return NFA(start, accept)


def stack_copy_nfa(nfa):
    """
    Crea una copia independiente de un AFN.
    Necesaria para r+ = r·r* (necesitamos dos copias de r).
    
    Recorre todos los estados del AFN original y crea
    estados nuevos con las mismas transiciones.
    """
    # Mapeo de estado original → estado nuevo
    mapping = {}
    
    # Recolectar todos los estados del AFN original
    all_states = _collect_states(nfa.start)
    
    # Crear un estado nuevo por cada estado original
    for state in all_states:
        new_state = State()
        new_state.is_accept = state.is_accept
        new_state.token_name = state.token_name
        mapping[state.id] = new_state
    
    # Copiar las transiciones usando el mapeo
    for state in all_states:
        new_state = mapping[state.id]
        for symbol, destinations in state.transitions.items():
            for dest in destinations:
                new_state.add_transition(symbol, mapping[dest.id])
    
    new_start = mapping[nfa.start.id]
    new_accept = mapping[nfa.accept.id]
    return NFA(new_start, new_accept)


def _collect_states(start_state):
    """
    Recolecta todos los estados alcanzables desde start_state
    usando búsqueda en anchura (BFS).
    """
    visited = set()
    result = []
    queue = [start_state]

    while queue:
        state = queue.pop(0)
        if state.id in visited:
            continue
        visited.add(state.id)
        result.append(state)  # agregar al resultado aquí
        for destinations in state.transitions.values():
            for dest in destinations:
                if dest.id not in visited:
                    queue.append(dest)

    return result

# Función principal
def regex_to_nfa(regex, token_name=None):
    """
    Función principal: convierte una regex (texto) en un AFN.
    
    Pasos:
    1. Preprocesar (expandir clases, agregar '·')
    2. Convertir a postfix
    3. Construir AFN con Thompson
    4. Marcar el estado de aceptación con el nombre del token
    
    Retorna el AFN construido.
    """
    # Paso 1: preprocesar la regex
    processed = preprocess_regex(regex)
    
    # Paso 2: convertir a postfix
    postfix = to_postfix(processed)
    
    # Paso 3: construir el AFN
    nfa = build_nfa_from_postfix(postfix)
    
    # Paso 4: marcar el estado de aceptación con el nombre del token
    if token_name:
        nfa.accept.token_name = token_name
    
    return nfa

# AFN a AFD
class DFAState:
    """
    Representa un estado del AFD.
    
    Cada estado del AFD corresponde a un CONJUNTO de estados del AFN.
    Por ejemplo, el estado AFD que representa {nfa_state_0, nfa_state_2}
    significa "el AFN podría estar en el estado 0 o en el estado 2".
    
    Atributos:
    - id: número único
    - nfa_states: el conjunto de estados AFN que representa
    - transitions: {símbolo: dfa_state_destino}  (determinista: solo 1 destino)
    - is_accept: True si algún estado AFN del conjunto es de aceptación
    - token_name: el token que produce (del primer estado de aceptación encontrado)
    """
    
    _counter = 0
    
    def __init__(self, nfa_states):
        self.id = DFAState._counter
        DFAState._counter += 1
        # Guardamos como frozenset para poder usarlo como clave de diccionario
        self.nfa_states = frozenset(s.id for s in nfa_states)
        self.transitions = {}    # {símbolo: DFAState}
        self.is_accept = False
        self.token_name = None
    
    def __repr__(self):
        return f"DFAState({self.id}, nfa={set(self.nfa_states)}, accept={self.is_accept})"


class DFA:
    """
    Representa un AFD completo.
    
    Atributos:
    - start: estado inicial
    - states: lista de todos los estados
    - accept_states: lista de estados de aceptación
    """
    
    def __init__(self, start, states, accept_states):
        self.start = start
        self.states = states
        self.accept_states = accept_states


def epsilon_closure(states):
    """
    Calcula la ε-clausura de un conjunto de estados AFN.
    
    La ε-clausura es el conjunto de todos los estados alcanzables
    usando SOLO transiciones ε (sin consumir ningún carácter).
    
    Usamos BFS para explorar todas las transiciones ε.
    
    Ejemplo:
        Si Estado_0 --ε--> Estado_1 --ε--> Estado_2
        epsilon_closure([Estado_0]) = {Estado_0, Estado_1, Estado_2}
    """
    # El resultado siempre incluye los estados originales
    closure = set(states)
    # Pila de estados a explorar
    stack = list(states)
    
    while stack:
        state = stack.pop()
        # Ver todas las transiciones ε de este estado
        for next_state in state.transitions.get('ε', []):
            if next_state not in closure:
                closure.add(next_state)
                stack.append(next_state)
    
    return closure


def move(states, symbol):
    """
    Calcula el conjunto de estados alcanzables desde 'states'
    consumiendo el símbolo 'symbol'.
    
    Recorre todos los estados del conjunto y recolecta
    todos los destinos de transiciones con ese símbolo.
    
    Ejemplo:
        Estados {0, 1}, símbolo 'a':
        Estado_0 --a--> Estado_3
        Estado_1 --a--> Estado_4
        move({0,1}, 'a') = {Estado_3, Estado_4}
    """
    result = set()
    for state in states:
        for next_state in state.transitions.get(symbol, []):
            result.add(next_state)
    return result


def get_alphabet(nfa):
    """
    Obtiene todos los símbolos usados en el AFN,
    excluyendo ε (que no es un símbolo real del alfabeto).
    """
    alphabet = set()
    # Recorrer todos los estados y recolectar símbolos
    all_states = _collect_states(nfa.start)
    for state in all_states:
        for symbol in state.transitions:
            if symbol != 'ε':
                alphabet.add(symbol)
    return alphabet


def nfa_to_dfa(nfa):
    """
    Convierte un AFN a un AFD usando el algoritmo de construcción de subconjuntos.
    
    Pasos:
    1. El estado inicial del AFD = ε-clausura del estado inicial del AFN
    2. Para cada estado AFD no procesado:
       Para cada símbolo del alfabeto:
         - Calcular mover(estado_actual, símbolo)
         - Calcular ε-clausura del resultado
         - Si ese conjunto no existe como estado AFD, crearlo
         - Agregar la transición
    3. Marcar estados de aceptación
    """
    # Obtener el alfabeto del AFN (todos los símbolos excepto ε)
    alphabet = get_alphabet(nfa)
    
    # Paso 1: estado inicial del AFD
    initial_closure = epsilon_closure([nfa.start])
    start_dfa = DFAState(initial_closure)
    
    # Diccionario: frozenset de IDs de estados AFN → DFAState
    # Para no crear estados duplicados
    dfa_states_map = {start_dfa.nfa_states: start_dfa}
    
    # Lista de todos los estados del AFD
    all_dfa_states = [start_dfa]
    
    # Cola de estados por procesar
    unprocessed = [start_dfa]
    
    # Paso 2: procesar cada estado del AFD
    while unprocessed:
        current_dfa = unprocessed.pop(0)
        
        # Obtener los objetos State del AFN que corresponden a este estado AFD
        # (necesitamos los objetos, no solo los IDs)
        current_nfa_states = _get_nfa_state_objects(nfa, current_dfa.nfa_states)
        
        for symbol in alphabet:
            # Calcular mover(estados_actuales, símbolo)
            moved = move(current_nfa_states, symbol)
            
            if not moved:
                # No hay transición con este símbolo → ignorar
                continue
            
            # Calcular ε-clausura del resultado
            closure = epsilon_closure(moved)
            closure_ids = frozenset(s.id for s in closure)
            
            # Ya existe este conjunto como estado AFD
            if closure_ids not in dfa_states_map:
                # Crear nuevo estado AFD
                new_dfa = DFAState(closure)
                dfa_states_map[closure_ids] = new_dfa
                all_dfa_states.append(new_dfa)
                unprocessed.append(new_dfa)
            
            # Agregar la transición al estado AFD actual
            current_dfa.transitions[symbol] = dfa_states_map[closure_ids]
    
    # Paso 3: marcar estados de aceptación
    # Un estado AFD es de aceptación si contiene algún estado de aceptación del AFN
    accept_states = []
    all_nfa_states = _collect_states(nfa.start)
    
    for dfa_state in all_dfa_states:
        for nfa_state in all_nfa_states:
            if nfa_state.id in dfa_state.nfa_states and nfa_state.is_accept:
                dfa_state.is_accept = True
                dfa_state.token_name = nfa_state.token_name
                accept_states.append(dfa_state)
                break  # un estado AFD solo necesita un token (el primero que encuentre)
    
    return DFA(start_dfa, all_dfa_states, accept_states)


def _get_nfa_state_objects(nfa, state_ids):
    """
    Dado un conjunto de IDs de estados AFN, retorna los objetos State correspondientes.
    
    Necesitamos esto porque DFAState guarda IDs (no objetos) para poder usarlos como claves de diccionario.
    """
    all_states = _collect_states(nfa.start)
    return [s for s in all_states if s.id in state_ids]


def simulate_dfa(dfa, input_string):
    """
    Simula el AFD sobre una cadena de entrada.
    
    Recorre la cadena carácter por carácter, siguiendo transiciones.
    
    Retorna:
    - (True, token_name) si la cadena es aceptada
    - (False, None) si la cadena es rechazada
    
    Ejemplo:
        dfa acepta dígitos, input = "123"
        → sigue transiciones para '1', '2', '3'
        → llega a estado de aceptación
        → retorna (True, 'INT')
    """
    current_state = dfa.start
    
    for char in input_string:
        if char in current_state.transitions:
            current_state = current_state.transitions[char]
        else:
            # No hay transición → cadena rechazada
            return False, None
    
    if current_state.is_accept:
        return True, current_state.token_name
    else:
        return False, None