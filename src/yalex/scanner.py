# El Scanner toma código fuente (texto) y lo convierte en tokens.
# Usa los AFDs construidos a partir del archivo .yalex.
#
# Proceso:
# 1. Recibe la lista de (AFD, token_name) construidos por regex_engine
# 2. Recorre el código fuente carácter por carácter
# 3. Para cada posición, prueba todos los AFDs
# 4. Se queda con el match más largo 
# 5. Produce un token y avanza en el código fuente


class Token:
    """
    Representa un token encontrado en el código fuente.
    
    Atributos:
    - type: el nombre del token (ej: 'INT', 'ID', 'PLUS')
    - value: el texto exacto que se encontró (ej: '42', 'x', '+')
    - line: número de línea donde aparece (para reportar errores)
    - column: número de columna donde aparece
    """
    
    def __init__(self, type, value, line, column):
        self.type = type
        self.value = value
        self.line = line
        self.column = column
    
    def __repr__(self):
        return f"Token({self.type}, '{self.value}', L{self.line}:C{self.column})"


class Scanner:
    """
    Analizador léxico que tokeniza código fuente usando AFDs.
    
    Se construye a partir de:
    - Una lista de (dfa, token_name) donde cada AFD reconoce un token
    - Los AFDs se prueban en orden — el primero que hace match gana
      (esto define la prioridad de tokens, igual que en LEX)
    """
    
    def __init__(self, dfa_list):
        """
        dfa_list: lista de tuplas (dfa, token_name)
                  en orden de prioridad (keywords antes que identificadores)
        """
        self.dfa_list = dfa_list
    
    def tokenize(self, source_code):
        """
        Convierte el código fuente completo en una lista de tokens.
        
        Usa la estrategia maximal munch:
        Para cada posición, prueba todos los AFDs y se queda
        con el match más largo encontrado.
        
        Retorna:
        - tokens: lista de Token
        - errors: lista de errores encontrados (carácteres no reconocidos)
        """
        tokens = []
        errors = []
        
        pos = 0          # posición actual en el código fuente
        line = 1         # línea actual (para reporte de errores)
        column = 1       # columna actual
        
        while pos < len(source_code):
            char = source_code[pos]
            
            # Manejar saltos de línea para contar líneas correctamente
            if char == '\n':
                line += 1
                column = 1
                pos += 1
                continue
            
            # Intentar hacer match desde la posición actual
            token = self._next_token(source_code, pos, line, column)
            
            if token is None:
                # Ningún AFD reconoció nada desde esta posición
                errors.append({
                    'char': char,
                    'line': line,
                    'column': column,
                    'message': f"Carácter no reconocido '{char}' en L{line}:C{column}"
                })
                pos += 1
                column += 1
            else:
                # Si el token no es None (ignorar), agregarlo a la lista
                if token.type is not None:
                    tokens.append(token)
                
                # Avanzar la posición según el largo del lexema encontrado
                advance = len(token.value)
                column += advance
                pos += advance
        
        # Agregar token de fin de archivo
        tokens.append(Token('EOF', '', line, column))
        
        return tokens, errors
    
    def _next_token(self, source, pos, line, column):
        """
        Encuentra el siguiente token en 'source' comenzando en 'pos'.
        
        Estrategia maximal munch:
        - Para cada AFD, simular desde pos hasta donde llegue más lejos
        - Quedarse con el match más largo de todos los AFDs
        - Si hay empate en longitud, gana el que tenga mayor prioridad
          (el que está primero en dfa_list)
        
        Retorna un Token o None si no hay match.
        """
        best_token = None
        best_length = 0
        
        for dfa, token_name in self.dfa_list:
            # Intentar hacer match con este AFD
            matched_text, length = self._simulate_dfa_longest(dfa, source, pos)
            
            if length > best_length:
                # Este AFD encontró un match más largo
                best_length = length
                best_token = Token(token_name, matched_text, line, column)
            elif length == best_length and length > 0 and best_token is None:
                # Mismo largo pero no teníamos nada — usar este
                best_token = Token(token_name, matched_text, line, column)
        
        return best_token
    
    def _simulate_dfa_longest(self, dfa, source, start_pos):
        """
        Simula el AFD sobre 'source' comenzando en 'start_pos'.
        
        A diferencia de simulate_dfa() que prueba una cadena completa,
        este método encuentra el PREFIJO MÁS LARGO que el AFD acepta.
        
        Ejemplo:
            AFD reconoce dígitos: ['0'-'9']+
            source = "123abc", start_pos = 0
            → prueba "1"    → acepta (estado de aceptación)
            → prueba "12"   → acepta
            → prueba "123"  → acepta
            → prueba "123a" → rechaza (no hay transición)
            → retorna ("123", 3)
        
        Retorna:
        - (texto_matcheado, longitud) si encontró algo
        - ("", 0) si no encontró nada
        """
        current_state = dfa.start
        last_accept_pos = -1      # última posición donde estábamos en estado de aceptación
        last_accept_token = None  # token en esa posición
        
        pos = start_pos
        
        while pos < len(source):
            char = source[pos]
            
            if char in current_state.transitions:
                # Hay una transición con este carácter, entonces avanzar
                current_state = current_state.transitions[char]
                pos += 1
                
                # Si llegamos a un estado de aceptación, recordar esta posición
                if current_state.is_accept:
                    last_accept_pos = pos
            else:
                # No hay transición entonces el AFD no puede continuar
                break
        
        if last_accept_pos == -1:
            # Nunca llegamos a un estado de aceptación
            return "", 0
        
        # El match es desde start_pos hasta last_accept_pos
        matched = source[start_pos:last_accept_pos]
        return matched, len(matched)

# Función de construcción — une YALex con el Scanner
def build_scanner_from_yalex(yalex_reader):
    """
    Construye un Scanner completo a partir de un YALexReader.
    
    Pasos:
    1. Expandir las definiciones en los patrones
    2. Para cada patrón, construir AFN con Thompson
    3. Convertir cada AFN a AFD
    4. Crear el Scanner con la lista de AFDs
    """
    # Importamos aquí para evitar imports circulares
    from src.yalex.regex_engine import regex_to_nfa, nfa_to_dfa
    
    # Paso 1: obtener las reglas con definiciones expandidas
    expanded_rules = yalex_reader.expand_definitions()
    
    dfa_list = []
    
    for pattern, token_name in expanded_rules:
        try:
            # Paso 2: regex to AFN (Thompson)
            nfa = regex_to_nfa(pattern, token_name)
            
            # Paso 3: AFN to AFD (subconjuntos)
            dfa = nfa_to_dfa(nfa)
            
            # Agregar a la lista con su nombre de token
            # token_name puede ser None (significa "ignorar este lexema")
            dfa_list.append((dfa, token_name))
            
        except Exception as e:
            print(f"Error procesando patrón '{pattern}': {e}")
            continue
    
    return Scanner(dfa_list)