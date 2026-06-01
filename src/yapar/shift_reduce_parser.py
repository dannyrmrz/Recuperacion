# Parser shift-reduce que usa las tablas SLR o LALR.
# Cuando encuentra conflictos, lanza hilos paralelos para explorar cada camino posible simultáneamente.

import threading

# NODO DEL ÁRBOL SINTÁCTICO
class ParseTreeNode:
    """
    Nodo del árbol sintáctico.

    Cada nodo representa:
    - Un no terminal (nodo interno): tiene hijos
    - Un terminal/token (hoja): no tiene hijos

    Ejemplo para "ID EQUALS INT":
        sentencia
        ├── ID
        ├── EQUALS
        └── INT
    """

    def __init__(self, symbol, children=None, token_value=None):
        self.symbol      = symbol        # nombre del símbolo
        self.children    = children or []  # hijos (para no terminales)
        self.token_value = token_value   # valor real del token (para hojas)

    def is_leaf(self):
        return len(self.children) == 0

    def __repr__(self):
        return f"Node({self.symbol})"

    def to_string(self, indent=0):
        """Representación visual del árbol con indentación."""
        prefix = "  " * indent
        if self.is_leaf():
            val = f" = '{self.token_value}'" if self.token_value else ""
            return f"{prefix}{self.symbol}{val}"
        else:
            lines = [f"{prefix}{self.symbol}"]
            for child in self.children:
                lines.append(child.to_string(indent + 1))
            return '\n'.join(lines)

# ESTADO INTERNO DEL PARSER
class ParserState:
    """
    Representa el estado completo de un parser en un momento dado.

    Esto es lo que cada hilo paralelo tiene como su propio estado:
    - stack: pila de estados del autómata
    - symbol_stack: pila de símbolos (para construir el árbol)
    - pos: posición actual en la entrada
    - steps: historial de pasos (para visualización)
    - tree_stack: pila de nodos del árbol sintáctico
    """

    def __init__(self, stack, symbol_stack, tree_stack, pos, steps):
        # Copiamos todo para que cada hilo tenga su propia versión
        self.stack        = list(stack)
        self.symbol_stack = list(symbol_stack)
        self.tree_stack   = list(tree_stack)
        self.pos          = pos
        self.steps        = list(steps)

    def copy(self):
        """Crea una copia profunda del estado para un nuevo hilo."""
        return ParserState(
            self.stack,
            self.symbol_stack,
            [n for n in self.tree_stack],
            self.pos,
            self.steps
        )

# PARSER SHIFT-REDUCE
class ShiftReduceParser:
    """
    Parser shift-reduce con soporte para paralelismo en conflictos.
    Puede usar tablas SLR o LALR — ambas tienen el mismo formato.

    Cuando encuentra un conflicto (celda con múltiples acciones), lanza un hilo por cada acción posible y espera el resultado.
    """

    def __init__(self, action_table, goto_table, grammar, start_symbol):
        """
        action_table: {estado_id: {terminal: acción o lista de acciones}}
        goto_table:   {estado_id: {no_terminal: estado_id}}
        grammar:      [(no_terminal, [símbolos]), ...]
        start_symbol: símbolo inicial de la gramática
        """
        self.action_table = action_table
        self.goto_table   = goto_table
        self.grammar      = grammar
        self.start_symbol = start_symbol

        # Para guardar todos los resultados de los hilos paralelos
        self._results      = []
        self._results_lock = threading.Lock()

    def parse(self, tokens):
        """
        Parsea una lista de tokens.

        tokens: lista de objetos Token o strings con el tipo del token

        Retorna:
        - results: lista de resultados de cada camino explorado
          cada resultado tiene: {'accepted', 'steps', 'tree', 'path_id'}
        """
        # Convertir tokens a lista de tipos (strings)
        if tokens and hasattr(tokens[0], 'type'):
            input_tokens = [t.type for t in tokens]
            token_values = {i: t.value for i, t in enumerate(tokens)}
        else:
            input_tokens = list(tokens)
            token_values = {}

        # Asegurar que termina con $
        if not input_tokens or input_tokens[-1] != '$':
            input_tokens.append('$')

        # Limpiar resultados anteriores
        self._results = []

        # Estado inicial del parser
        initial_state = ParserState(
            stack        = [0],
            symbol_stack = [],
            tree_stack   = [],
            pos          = 0,
            steps        = []
        )

        # Iniciar el parsing (puede lanzar hilos si hay conflictos)
        self._parse_path(
            state       = initial_state,
            input_tokens = input_tokens,
            token_values = token_values,
            path_id     = 1
        )

        return self._results

    def _parse_path(self, state, input_tokens, token_values, path_id):
        """
        Ejecuta un camino de parsing hasta ACCEPT, ERROR o conflicto.

        Si encuentra un conflicto, lanza hilos para cada acción posible
        y continúa en paralelo.

        path_id: número del camino (1 = original, 2/3 = ramificaciones)
        """
        MAX_STEPS = 500  # límite de seguridad

        while len(state.steps) < MAX_STEPS:
            current_state = state.stack[-1]
            current_token = (input_tokens[state.pos]
                             if state.pos < len(input_tokens) else '$')

            # Obtener acción de la tabla
            action = self.action_table.get(current_state, {}).get(current_token)

            # Construir info del paso para visualización
            step_info = {
                'path_id':     path_id,
                'stack':       list(state.stack),
                'symbol_stack': list(state.symbol_stack),
                'input':       input_tokens[state.pos:],
                'action':      '',
                'conflict':    False
            }

            # ERROR: no hay acción
            if action is None:
                step_info['action'] = (
                    f'ERROR: no hay acción para '
                    f'[estado {current_state}][{current_token}]'
                )
                state.steps.append(step_info)
                self._save_result(False, state.steps, None, path_id)
                return

            # CONFLICTO: hay múltiples acciones
            if isinstance(action, list):
                step_info['action']   = (
                    f'CONFLICTO en estado {current_state} con {current_token}: '
                    f'{len(action)} caminos posibles'
                )
                step_info['conflict'] = True
                state.steps.append(step_info)

                # Lanzar un hilo por cada acción posible
                threads = []
                for i, single_action in enumerate(action):
                    # Copiar el estado para este hilo
                    new_state = state.copy()
                    new_path_id = path_id * 10 + i + 1

                    t = threading.Thread(
                        target=self._execute_action,
                        args=(
                            new_state, single_action,
                            input_tokens, token_values,
                            new_path_id
                        )
                    )
                    threads.append(t)
                    t.start()

                # Esperar a que todos los hilos terminen
                for t in threads:
                    t.join()

                return  # este camino se dividió — terminar aquí

            # ACCIÓN ÚNICA 
            self._execute_action(
                state, action,
                input_tokens, token_values,
                path_id
            )
            return

    def _execute_action(self, state, action,
                        input_tokens, token_values, path_id):
        """
        Ejecuta UNA acción (shift, reduce, accept) y continúa el parsing.

        Este método es el que corren los hilos paralelos.
        """
        MAX_STEPS = 500

        while len(state.steps) < MAX_STEPS:
            current_state_id = state.stack[-1]
            current_token    = (input_tokens[state.pos]
                                if state.pos < len(input_tokens) else '$')

            step_info = {
                'path_id':      path_id,
                'stack':        list(state.stack),
                'symbol_stack': list(state.symbol_stack),
                'input':        input_tokens[state.pos:],
                'action':       '',
                'conflict':     False
            }

            tipo, valor = action

            # ACCEPT 
            if tipo == 'ACCEPT':
                step_info['action'] = 'ACCEPT'
                state.steps.append(step_info)

                # El árbol final es el tope de tree_stack
                tree = state.tree_stack[-1] if state.tree_stack else None
                self._save_result(True, state.steps, tree, path_id)
                return

            # SHIFT 
            elif tipo == 'SHIFT':
                dest_state = valor
                step_info['action'] = f'SHIFT → estado {dest_state}'
                state.steps.append(step_info)

                # Empujar el nuevo estado a la pila
                state.stack.append(dest_state)
                state.symbol_stack.append(current_token)

                # Crear nodo hoja para el árbol
                token_val = token_values.get(state.pos, current_token)
                state.tree_stack.append(
                    ParseTreeNode(current_token, token_value=token_val)
                )

                # Avanzar en la entrada
                state.pos += 1

            # REDUCE 
            elif tipo == 'REDUCE':
                prod_index   = valor
                nt, symbols  = self.grammar[prod_index]
                rule_str     = f"{nt} → {' '.join(symbols)}"
                step_info['action'] = f'REDUCE {rule_str}'
                state.steps.append(step_info)

                # Sacar len(symbols) elementos de la pila
                n = len(symbols)
                if n > 0:
                    # Los últimos n nodos del árbol son los hijos
                    children = state.tree_stack[-n:]
                    state.tree_stack = state.tree_stack[:-n]
                    state.stack      = state.stack[:-n]
                    state.symbol_stack = state.symbol_stack[:-n]
                else:
                    children = []

                # Crear nodo interno para el no terminal
                new_node = ParseTreeNode(nt, children=children)
                state.tree_stack.append(new_node)
                state.symbol_stack.append(nt)

                # Consultar GOTO para saber al estado ir
                top_state = state.stack[-1]
                goto_dest = self.goto_table.get(top_state, {}).get(nt)

                if goto_dest is None:
                    step_info = {
                        'path_id':      path_id,
                        'stack':        list(state.stack),
                        'symbol_stack': list(state.symbol_stack),
                        'input':        input_tokens[state.pos:],
                        'action':       f'ERROR: GOTO[{top_state}][{nt}] vacío',
                        'conflict':     False
                    }
                    state.steps.append(step_info)
                    self._save_result(False, state.steps, None, path_id)
                    return

                state.stack.append(goto_dest)

            # Obtener siguiente acción
            new_state_id  = state.stack[-1]
            current_token = (input_tokens[state.pos]
                             if state.pos < len(input_tokens) else '$')
            action = (self.action_table
                      .get(new_state_id, {})
                      .get(current_token))

            # Sin acción - error
            if action is None:
                state.steps.append({
                    'path_id':      path_id,
                    'stack':        list(state.stack),
                    'symbol_stack': list(state.symbol_stack),
                    'input':        input_tokens[state.pos:],
                    'action':       (f'ERROR: no hay acción para '
                                     f'[estado {new_state_id}][{current_token}]'),
                    'conflict':     False
                })
                self._save_result(False, state.steps, None, path_id)
                return

            # Conflicto - ramificar de nuevo
            if isinstance(action, list):
                state.steps.append({
                    'path_id':      path_id,
                    'stack':        list(state.stack),
                    'symbol_stack': list(state.symbol_stack),
                    'input':        input_tokens[state.pos:],
                    'action':       (f'CONFLICTO: {len(action)} caminos'),
                    'conflict':     True
                })

                threads = []
                for i, single_action in enumerate(action):
                    new_state   = state.copy()
                    new_path_id = path_id * 10 + i + 1

                    t = threading.Thread(
                        target=self._execute_action,
                        args=(
                            new_state, single_action,
                            input_tokens, token_values,
                            new_path_id
                        )
                    )
                    threads.append(t)
                    t.start()

                for t in threads:
                    t.join()
                return

    def _save_result(self, accepted, steps, tree, path_id):
        """Guarda el resultado de un camino de forma segura (thread-safe)."""
        with self._results_lock:
            self._results.append({
                'accepted': accepted,
                'steps':    steps,
                'tree':     tree,
                'path_id':  path_id
            })

# FUNCIÓN DE CONSTRUCCIÓN
def build_slr_parser(yapar_reader, slr_table):
    """Construye un ShiftReduceParser usando la tabla SLR."""
    return ShiftReduceParser(
        action_table = slr_table.action_table,
        goto_table   = slr_table.goto_table,
        grammar      = yapar_reader.grammar,
        start_symbol = yapar_reader.start_symbol
    )


def build_lalr_parser(yapar_reader, lalr_table):
    """Construye un ShiftReduceParser usando la tabla LALR."""
    return ShiftReduceParser(
        action_table = lalr_table.action_table,
        goto_table   = lalr_table.goto_table,
        grammar      = yapar_reader.grammar,
        start_symbol = yapar_reader.start_symbol
    )