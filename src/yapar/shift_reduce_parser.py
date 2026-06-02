# src/yapar/shift_reduce_parser.py
#
# Parser shift-reduce que usa las tablas SLR o LALR.
# Cuando encuentra conflictos, lanza hilos paralelos
# para explorar cada camino posible simultaneamente.

import threading


# ─────────────────────────────────────────────
# NODO DEL ARBOL SINTACTICO
# ─────────────────────────────────────────────

class ParseTreeNode:
    """
    Nodo del arbol sintactico.
    - No terminal (nodo interno): tiene hijos
    - Terminal/token (hoja): no tiene hijos
    """

    def __init__(self, symbol, children=None, token_value=None):
        self.symbol      = symbol
        self.children    = children or []
        self.token_value = token_value

    def is_leaf(self):
        return len(self.children) == 0

    def __repr__(self):
        return f"Node({self.symbol})"

    def to_string(self, indent=0):
        prefix = "  " * indent
        if self.is_leaf():
            val = f" = '{self.token_value}'" if self.token_value else ""
            return f"{prefix}{self.symbol}{val}"
        else:
            lines = [f"{prefix}{self.symbol}"]
            for child in self.children:
                lines.append(child.to_string(indent + 1))
            return '\n'.join(lines)


# ─────────────────────────────────────────────
# ESTADO INTERNO DEL PARSER
# ─────────────────────────────────────────────

class ParserState:
    """
    Estado completo de un camino de parsing.
    Cada hilo paralelo tiene su propia copia.
    """

    def __init__(self, stack, symbol_stack, tree_stack, pos, steps):
        self.stack        = list(stack)
        self.symbol_stack = list(symbol_stack)
        self.tree_stack   = list(tree_stack)
        self.pos          = pos
        self.steps        = list(steps)

    def copy(self):
        return ParserState(
            self.stack,
            self.symbol_stack,
            list(self.tree_stack),
            self.pos,
            self.steps
        )


# ─────────────────────────────────────────────
# PARSER SHIFT-REDUCE
# ─────────────────────────────────────────────

class ShiftReduceParser:
    """
    Parser shift-reduce con soporte para paralelismo en conflictos.
    Funciona con tablas SLR o LALR.

    Cuando encuentra un conflicto (celda con multiples acciones),
    lanza un hilo por cada accion posible y espera el resultado.
    """

    def __init__(self, action_table, goto_table, grammar, start_symbol):
        self.action_table = action_table
        self.goto_table   = goto_table
        self.grammar      = grammar
        self.start_symbol = start_symbol
        self._results      = []
        self._results_lock = threading.Lock()

    def parse(self, tokens):
        """
        Parsea una lista de tokens.
        Retorna lista de resultados (uno por camino explorado).
        Cada resultado: {'accepted', 'steps', 'tree', 'path_id'}
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

        self._results = []

        # ─── FIX CLAVE ───────────────────────────────────────────────────
        # El estado inicial NO siempre es 0.
        # Despues de multiples solicitudes al servidor Flask, el contador
        # de LR0State sigue acumulando, por lo que el estado inicial puede
        # tener ID 24, 48, etc. en lugar de 0.
        # Usamos min(keys) porque el estado inicial siempre se construye
        # primero y por lo tanto tiene el ID mas pequeño de la tabla.
        # ─────────────────────────────────────────────────────────────────
        initial_id = min(self.action_table.keys()) if self.action_table else 0

        initial_state = ParserState(
            stack        = [initial_id],
            symbol_stack = [],
            tree_stack   = [],
            pos          = 0,
            steps        = []
        )

        self._parse_path(
            state        = initial_state,
            input_tokens = input_tokens,
            token_values = token_values,
            path_id      = 1
        )

        return self._results

    def _parse_path(self, state, input_tokens, token_values, path_id):
        """
        Ejecuta un camino de parsing hasta ACCEPT, ERROR o conflicto.
        Si hay conflicto, lanza hilos paralelos.
        """
        MAX_STEPS = 500

        while len(state.steps) < MAX_STEPS:
            current_state = state.stack[-1]
            current_token = (input_tokens[state.pos]
                             if state.pos < len(input_tokens) else '$')

            action = self.action_table.get(current_state, {}).get(current_token)

            step_info = {
                'path_id':      path_id,
                'stack':        list(state.stack),
                'symbol_stack': list(state.symbol_stack),
                'input':        input_tokens[state.pos:],
                'action':       '',
                'conflict':     False
            }

            # ERROR: no hay accion
            if action is None:
                step_info['action'] = (
                    f'ERROR: no hay accion para '
                    f'[estado {current_state}][{current_token}]'
                )
                state.steps.append(step_info)
                self._save_result(False, state.steps, None, path_id)
                return

            # CONFLICTO: multiples acciones → paralelismo
            if isinstance(action, list):
                step_info['action'] = (
                    f'CONFLICTO en estado {current_state} con {current_token}: '
                    f'{len(action)} caminos posibles'
                )
                step_info['conflict'] = True
                state.steps.append(step_info)

                threads = []
                for i, single_action in enumerate(action):
                    new_state   = state.copy()
                    new_path_id = path_id * 10 + i + 1

                    t = threading.Thread(
                        target=self._execute_action,
                        args=(new_state, single_action,
                              input_tokens, token_values, new_path_id)
                    )
                    threads.append(t)
                    t.start()

                for t in threads:
                    t.join()

                return

            # ACCION UNICA
            self._execute_action(
                state, action,
                input_tokens, token_values,
                path_id
            )
            return

    def _execute_action(self, state, action,
                        input_tokens, token_values, path_id):
        """
        Ejecuta UNA accion (shift, reduce, accept) y continua el parsing.
        Este metodo es el que corren los hilos paralelos.
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

            # ── ACCEPT ───────────────────────────────────────────────────
            if tipo == 'ACCEPT':
                step_info['action'] = 'ACCEPT'
                state.steps.append(step_info)
                tree = state.tree_stack[-1] if state.tree_stack else None
                self._save_result(True, state.steps, tree, path_id)
                return

            # ── SHIFT ─────────────────────────────────────────────────────
            elif tipo == 'SHIFT':
                dest_state = valor
                step_info['action'] = f'SHIFT estado {dest_state}'
                state.steps.append(step_info)

                state.stack.append(dest_state)
                state.symbol_stack.append(current_token)

                token_val = token_values.get(state.pos, current_token)
                state.tree_stack.append(
                    ParseTreeNode(current_token, token_value=token_val)
                )
                state.pos += 1

            # ── REDUCE ────────────────────────────────────────────────────
            elif tipo == 'REDUCE':
                prod_index  = valor
                nt, symbols = self.grammar[prod_index]
                rule_str    = f"{nt} -> {' '.join(symbols)}"
                step_info['action'] = f'REDUCE {rule_str}'
                state.steps.append(step_info)

                n = len(symbols)
                if n > 0:
                    children           = state.tree_stack[-n:]
                    state.tree_stack   = state.tree_stack[:-n]
                    state.stack        = state.stack[:-n]
                    state.symbol_stack = state.symbol_stack[:-n]
                else:
                    children = []

                new_node = ParseTreeNode(nt, children=children)
                state.tree_stack.append(new_node)
                state.symbol_stack.append(nt)

                top_state = state.stack[-1]
                goto_dest = self.goto_table.get(top_state, {}).get(nt)

                if goto_dest is None:
                    state.steps.append({
                        'path_id':      path_id,
                        'stack':        list(state.stack),
                        'symbol_stack': list(state.symbol_stack),
                        'input':        input_tokens[state.pos:],
                        'action':       f'ERROR: GOTO[{top_state}][{nt}] vacio',
                        'conflict':     False
                    })
                    self._save_result(False, state.steps, None, path_id)
                    return

                state.stack.append(goto_dest)

            # Obtener siguiente accion
            new_state_id  = state.stack[-1]
            current_token = (input_tokens[state.pos]
                             if state.pos < len(input_tokens) else '$')
            action = (self.action_table
                      .get(new_state_id, {})
                      .get(current_token))

            if action is None:
                state.steps.append({
                    'path_id':      path_id,
                    'stack':        list(state.stack),
                    'symbol_stack': list(state.symbol_stack),
                    'input':        input_tokens[state.pos:],
                    'action':       (f'ERROR: no hay accion para '
                                     f'[estado {new_state_id}][{current_token}]'),
                    'conflict':     False
                })
                self._save_result(False, state.steps, None, path_id)
                return

            if isinstance(action, list):
                state.steps.append({
                    'path_id':      path_id,
                    'stack':        list(state.stack),
                    'symbol_stack': list(state.symbol_stack),
                    'input':        input_tokens[state.pos:],
                    'action':       f'CONFLICTO: {len(action)} caminos',
                    'conflict':     True
                })

                threads = []
                for i, single_action in enumerate(action):
                    new_state   = state.copy()
                    new_path_id = path_id * 10 + i + 1

                    t = threading.Thread(
                        target=self._execute_action,
                        args=(new_state, single_action,
                              input_tokens, token_values, new_path_id)
                    )
                    threads.append(t)
                    t.start()

                for t in threads:
                    t.join()
                return

    def _save_result(self, accepted, steps, tree, path_id):
        with self._results_lock:
            self._results.append({
                'accepted': accepted,
                'steps':    steps,
                'tree':     tree,
                'path_id':  path_id
            })


# ─────────────────────────────────────────────
# FUNCIONES DE CONSTRUCCION
# ─────────────────────────────────────────────

def build_slr_parser(yapar_reader, slr_table):
    return ShiftReduceParser(
        action_table = slr_table.action_table,
        goto_table   = slr_table.goto_table,
        grammar      = yapar_reader.grammar,
        start_symbol = yapar_reader.start_symbol
    )


def build_lalr_parser(yapar_reader, lalr_table):
    return ShiftReduceParser(
        action_table = lalr_table.action_table,
        goto_table   = lalr_table.goto_table,
        grammar      = yapar_reader.grammar,
        start_symbol = yapar_reader.start_symbol
    )