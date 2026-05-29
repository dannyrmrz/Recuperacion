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
    """
    Convierte la regex del formato .yalex al formato estándar
    
    Hace dos cosas:
    1. Expande clases de caracteres ['0'-'9'] → (0|1|2|...|9)
    2. Agrega operadores de concatenación explícitos '.'
       Ejemplo: "ab" → "a.b"  (la concatenación normalmente es implícita)
    
    Se agrega "." porque cuando convirtamos a postfix, necesitamos que todos los
    operadores sean explícitos.
    """
    # Paso 1: expandir clases de caracteres
    regex = expand_char_classes(regex)
    
    # Paso 2: agregar concatenación explícita
    regex = add_concat_operator(regex)
    
    return regex


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
    Parsea el contenido de una clase de caracteres y retorna
    la lista de caracteres individuales.
    
    Ejemplos:
        "'0'-'9'"  →  ['0', '1', '2', ..., '9']
        "'a''z'"   →  ['a', 'z']
        "'a'-'z''A'-'Z'"  →  ['a'..'z', 'A'..'Z']
    """
    chars = []
    i = 0
    
    while i < len(content):
        # Saltar espacios
        if content[i] == ' ':
            i += 1
            continue
        
        # Encontramos una comilla, eso significa que es el inicio de un carácter
        if content[i] == "'":
            # Extraer el carácter entre comillas
            char1 = content[i+1]
            i += 3  # saltar 'x'
            
            # Hay un rango '-' después
            if i < len(content) and content[i:i+2] == "-'":
                # Es un rango: 'a'-'z'
                char2 = content[i+2]
                i += 4  # saltar -'x'
                
                # Expandir el rango
                for c in range(ord(char1), ord(char2) + 1):
                    chars.append(chr(c))
            else:
                # Es un carácter simple
                chars.append(char1)
        else:
            i += 1
    
    return chars


def add_concat_operator(regex):
    """
    Agrega el operador de concatenación '·' de forma explícita.
    
    En regex normal, "ab" significa "a concatenado con b", pero
    esa concatenación es implícita. Para convertir a postfix
    necesitamos hacerla explícita con un símbolo.
    Usamos el símbolo '·' (punto medio).
    
    Regla: agregar '·' entre dos caracteres cuando:
    - El carácter de la izquierda es: letra, dígito, ')', '*', '+', '?'
    - El carácter de la derecha es:  letra, dígito, '('
    
    Ejemplo:
        "ab*c"  →  "a·b*·c"
        "a(bc)" →  "a·(b·c)"
    """
    result = []
    
    # Caracteres que pueden ir a la IZQUIERDA de una concatenación
    left_chars = set('abcdefghijklmnopqrstuvwxyz'
                     'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                     '0123456789)*+?')
    
    # Caracteres que pueden ir a la DERECHA de una concatenación
    right_chars = set('abcdefghijklmnopqrstuvwxyz'
                      'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                      '0123456789(')
    
    for i, char in enumerate(regex):
        result.append(char)
        
        if i + 1 < len(regex):
            next_char = regex[i + 1]
            # Necesitamos agregar concatenación si char y next_char cumplen las condiciones
            if char in left_chars and next_char in right_chars:
                result.append('·')
    
    return ''.join(result)


def to_postfix(regex):
    """
    Convierte una regex en notación infix a notación postfix
    usando el algoritmo Shunting Yard de Dijkstra.
    
    ¿Por qué postfix?
    En postfix, los operadores van DESPUÉS de sus operandos, sirve para después poder evaluar
    la expresión con una pila.
    
    Ejemplo:
        infix:   "a·b|c*"
        postfix: "ab·c*|"
    
    Precedencia de operadores (mayor número = mayor precedencia):
        |  →  1  (unión, menor precedencia)
        ·  →  2  (concatenación)
        *  →  3  (cerradura Kleene)
        +  →  3  (cerradura positiva)
        ?  →  3  (cero o uno, mayor precedencia)
    """
    # Precedencia de cada operador
    precedence = {'|': 1, '·': 2, '*': 3, '+': 3, '?': 3}
    
    output = []   # cola de salida (resultado postfix)
    stack = []    # pila de operadores
    
    for char in regex:
        if char == '(':
            # Paréntesis abierto: siempre va a la pila
            stack.append(char)
            
        elif char == ')':
            # Paréntesis cerrado: sacar todo hasta encontrar '('
            while stack and stack[-1] != '(':
                output.append(stack.pop())
            if stack:
                stack.pop()  # sacar el '(' de la pila (sin agregar al output)
                
        elif char in precedence:
            # Es un operador: sacar operadores de mayor o igual precedencia
            while (stack and 
                   stack[-1] != '(' and 
                   stack[-1] in precedence and
                   precedence[stack[-1]] >= precedence[char]):
                output.append(stack.pop())
            stack.append(char)
            
        else:
            # Es un operando (carácter normal): va directo al output
            output.append(char)
    
    # Sacar todos los operadores que quedaron en la pila
    while stack:
        output.append(stack.pop())
    
    return ''.join(output)

# AFN Thompson
def build_nfa_from_postfix(postfix):
    """
    Construye el AFN usando el algoritmo de Thompson a partir de una expresión en notación postfix.
    
    Usamos una pila de AFNs.
    - Cuando encontramos un carácter, construimos AFN básico y lo ponemos en la pila
    - Cuando encontramos un operador,  sacamos AFNs de la pila, los combinamos, 
    y ponemos el resultado de vuelta
    """
    stack = []  # pila de AFNs
    
    for char in postfix:
        
        if char == '·':
            # CONCATENACIÓN: sacar dos AFNs y conectarlos en serie
            # El segundo que se saca es el de la IZQUIERDA (por LIFO - último en entrar, primero en salir)
            nfa2 = stack.pop()
            nfa1 = stack.pop()
            stack.append(_concat(nfa1, nfa2))
            
        elif char == '|':
            # UNIÓN: sacar dos AFNs y crear uno nuevo que acepta cualquiera
            nfa2 = stack.pop()
            nfa1 = stack.pop()
            stack.append(_union(nfa1, nfa2))
            
        elif char == '*':
            # KLEENE: sacar un AFN y crear su cerradura (0 o más)
            nfa = stack.pop()
            stack.append(_kleene(nfa))
            
        elif char == '+':
            # CERRADURA POSITIVA: 1 o más = concatenar con Kleene
            # r+ es equivalente a r·r*
            nfa = stack.pop()
            # Necesitamos dos copias del AFN
            nfa_copy = stack_copy_nfa(nfa)
            stack.append(_concat(nfa, _kleene(nfa_copy)))
            
        elif char == '?':
            # CERO O UNO: r? es equivalente a r|ε
            nfa = stack.pop()
            stack.append(_optional(nfa))
            
        else:
            # CARÁCTER SIMPLE: construir AFN básico
            stack.append(_single_char(char))
    
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