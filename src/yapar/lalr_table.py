# Construye la tabla LALR.
#
# Proceso:
# 1. Construir ítems LR(1) — como LR(0) pero con lookahead
# 2. Agrupar estados que tienen el mismo núcleo (core)
# 3. Fusionar sus lookaheads
# 4. Construir ACTION y GOTO usando los lookaheads específicos

# Importamos las constantes de acción que ya definimos en slr_table
from src.yapar.slr_table import SHIFT, REDUCE, ACCEPT, ERROR


class LR1Item:
    """
    Ítem LR(1): producción con punto Y un lookahead.

    El lookahead es un terminal que indica:
    "solo puedo REDUCIR este ítem si el próximo token es este lookahead"

    Ejemplo:
        expresion → termino • PLUS expresion, [$]
        → el punto está antes de PLUS
        → si el punto llegara al final, solo reduciría si el próximo token es $
    """

    def __init__(self, non_terminal, symbols, dot, lookahead):
        self.non_terminal = non_terminal
        self.symbols      = list(symbols)
        self.dot          = dot
        self.lookahead    = lookahead   # un terminal string

    def core(self):
        """
        El núcleo es la parte LR(0) — sin el lookahead.
        Dos ítems con el mismo núcleo pueden fusionarse en LALR.
        """
        return (self.non_terminal, tuple(self.symbols), self.dot)

    def symbol_after_dot(self):
        if self.dot < len(self.symbols):
            return self.symbols[self.dot]
        return None

    def is_complete(self):
        return self.dot >= len(self.symbols)

    def advance(self):
        """Retorna un nuevo ítem con el punto avanzado, mismo lookahead."""
        return LR1Item(
            self.non_terminal, self.symbols,
            self.dot + 1, self.lookahead
        )

    def __eq__(self, other):
        return (self.non_terminal == other.non_terminal and
                self.symbols      == other.symbols      and
                self.dot          == other.dot          and
                self.lookahead    == other.lookahead)

    def __hash__(self):
        return hash((
            self.non_terminal,
            tuple(self.symbols),
            self.dot,
            self.lookahead
        ))

    def __repr__(self):
        syms = list(self.symbols)
        syms.insert(self.dot, '•')
        return f"{self.non_terminal} → {' '.join(syms)}, [{self.lookahead}]"


class LALRState:
    """Estado del autómata LALR."""

    _counter = 0

    def __init__(self, items):
        self.id          = LALRState._counter
        LALRState._counter += 1
        self.items       = frozenset(items)
        self.transitions = {}   # {símbolo: LALRState}

    def get_core(self):
        """Retorna el conjunto de núcleos de todos los ítems del estado."""
        return frozenset(item.core() for item in self.items)

    def __repr__(self):
        return f"LALRState({self.id})"


class LALRTable:
    """
    Construye la tabla LALR.

    Diferencia clave con SLRTable:
    - SLR reduce usando FOLLOW(A) → global para todo el autómata
    - LALR reduce usando item.lookahead → específico para cada ítem en cada estado
    """

    def __init__(self, yapar_reader, first_follow):
        self.grammar          = yapar_reader.grammar
        self.terminals        = yapar_reader.get_terminals()
        self.non_terminals    = yapar_reader.get_non_terminals()
        self.start_symbol     = yapar_reader.start_symbol
        self.augmented_start  = self.start_symbol + "'"
        self.calc             = first_follow

        # Tablas finales
        self.action_table = {}
        self.goto_table   = {}
        self.conflicts    = []

        # Estados del autómata
        self.lr1_states  = []   # antes de fusionar
        self.states      = []   # después de fusionar (estados LALR finales)
        self.initial_state = None

        # Construir todo
        self._build_lr1_automaton()
        self._merge_states()
        self._build_table()

    # Autómata LR(1)
    def _lr1_closure(self, items):
        """
        Clausura LR(1).

        Igual que LR(0) pero al agregar nuevos ítems para un no terminal B,
        calcula los lookaheads usando FIRST(β a) donde:
        - β = símbolos que vienen DESPUÉS de B en el ítem actual
        - a = lookahead del ítem actual

        Ejemplo:
            Ítem: [sentencia → ID EQUALS • expresion, $]
            B = expresion
            β = [] (nada después de expresion)
            a = $
            FIRST(β a) = FIRST($) = {$}
            → agrega [expresion → • ..., $]

            Ítem: [expresion → • termino PLUS expresion, $]
            B = termino
            β = [PLUS, expresion]
            a = $
            FIRST(PLUS expresion $) = {PLUS}
            → agrega [termino → • ..., PLUS]
        """
        closure = set(items)
        queue   = list(items)

        while queue:
            item = queue.pop(0)
            B    = item.symbol_after_dot()

            # Solo procesar si B es un no terminal
            if B is None or B not in self.non_terminals:
                continue

            # β = lo que viene después de B
            beta = item.symbols[item.dot + 1:]

            # Secuencia para calcular FIRST: β seguido del lookahead actual
            lookahead_seq = beta + [item.lookahead]
            first_set     = self.calc.get_first_of_sequence(lookahead_seq)

            # Agregar un ítem nuevo por cada producción de B
            # y por cada terminal en FIRST(β a)
            for nt, prod_symbols in self.grammar:
                if nt == B:
                    for terminal in first_set - {'ε'}:
                        new_item = LR1Item(nt, prod_symbols, 0, terminal)
                        if new_item not in closure:
                            closure.add(new_item)
                            queue.append(new_item)

        return closure

    def _lr1_goto(self, state_items, symbol):
        """GOTO para LR(1) — igual que LR(0) pero con ítems LR(1)."""
        advanced = set()
        for item in state_items:
            if item.symbol_after_dot() == symbol:
                advanced.add(item.advance())

        if not advanced:
            return None

        return self._lr1_closure(advanced)

    def _build_lr1_automaton(self):
        """
        Construye el autómata LR(1) completo.
        El estado inicial tiene el ítem [S' → •S, $]
        """
        # Ítem inicial: S' → •S con lookahead $
        initial_item  = LR1Item(
            self.augmented_start,
            [self.start_symbol],
            0, '$'
        )
        initial_items = self._lr1_closure({initial_item})
        initial_state = LALRState(initial_items)

        self.lr1_states = [initial_state]
        states_map      = {initial_state.items: initial_state}

        i = 0
        while i < len(self.lr1_states):
            current = self.lr1_states[i]

            # Encontrar todos los símbolos después de algún punto
            symbols_after = set()
            for item in current.items:
                s = item.symbol_after_dot()
                if s is not None:
                    symbols_after.add(s)

            for symbol in symbols_after:
                goto_items = self._lr1_goto(current.items, symbol)
                if goto_items is None:
                    continue

                goto_frozen = frozenset(goto_items)

                if goto_frozen not in states_map:
                    new_state = LALRState(goto_items)
                    self.lr1_states.append(new_state)
                    states_map[goto_frozen] = new_state

                current.transitions[symbol] = states_map[goto_frozen]

            i += 1

    # PASO 2: Fusionar estados con el mismo núcleo
    def _merge_states(self):
        """
        Fusiona estados LR(1) que tienen el mismo núcleo.

        Dos estados tienen el mismo núcleo si tienen exactamente
        las mismas producciones con los mismos puntos,
        independientemente de los lookaheads.

        Al fusionar, se combinan los lookaheads:
            Estado A: [expr → α•, $]    →    Estado fusionado: [expr → α•, $]
            Estado B: [expr → α•, +]                           [expr → α•, +]

        Esto reduce el número de estados 
        """
        # Agrupar estados por núcleo
        core_to_states = {}
        for state in self.lr1_states:
            core = state.get_core()
            if core not in core_to_states:
                core_to_states[core] = []
            core_to_states[core].append(state)

        # Mapa de ID de estado LR(1) → estado LALR fusionado
        lr1_to_lalr = {}

        LALRState._counter = 0  # reset para IDs limpios
        self.states = []

        for core, states_group in core_to_states.items():
            # Fusionar los ítems: misma posición de punto, lookaheads combinados
            item_cores = {}   # (nt, syms, dot) → set de lookaheads

            for state in states_group:
                for item in state.items:
                    c = item.core()
                    if c not in item_cores:
                        item_cores[c] = set()
                    item_cores[c].add(item.lookahead)

            # Crear los ítems fusionados (uno por cada lookahead)
            merged_items = set()
            for (nt, syms, dot), lookaheads in item_cores.items():
                for la in lookaheads:
                    merged_items.add(LR1Item(nt, list(syms), dot, la))

            merged_state = LALRState(merged_items)
            self.states.append(merged_state)

            # Mapear todos los estados LR(1) del grupo al estado fusionado
            for state in states_group:
                lr1_to_lalr[state.id] = merged_state

        # Reconstruir transiciones apuntando a estados LALR
        for state in self.lr1_states:
            merged = lr1_to_lalr[state.id]
            for symbol, dest in state.transitions.items():
                merged.transitions[symbol] = lr1_to_lalr[dest.id]

        # Estado inicial
        self.initial_state = lr1_to_lalr[self.lr1_states[0].id]

    # PASO 3: Construir tabla ACTION y GOTO
    def _build_table(self):
        """
        Construye ACTION y GOTO.

        Igual que SLR pero usando item.lookahead en vez de FOLLOW(A).
        Esta es LA diferencia entre SLR y LALR.
        """
        for state in self.states:
            self.action_table[state.id] = {}
            self.goto_table[state.id]   = {}

        for state in self.states:
            for item in state.items:
                symbol = item.symbol_after_dot()

                if symbol is not None:
                    if symbol in self.terminals:
                        # SHIFT
                        dest = state.transitions.get(symbol)
                        if dest:
                            self._add_action(
                                state.id, symbol, (SHIFT, dest.id)
                            )
                    elif symbol in self.non_terminals:
                        # GOTO
                        dest = state.transitions.get(symbol)
                        if dest:
                            self.goto_table[state.id][symbol] = dest.id
                else:
                    # Ítem completo
                    if item.non_terminal == self.augmented_start:
                        # ACCEPT
                        self._add_action(state.id, '$', (ACCEPT, None))
                    else:
                        # REDUCE — usando item.lookahead (no FOLLOW global)
                        prod_index = self._find_production_index(
                            item.non_terminal, item.symbols
                        )
                        # ← AQUÍ está la diferencia con SLR
                        self._add_action(
                            state.id, item.lookahead,
                            (REDUCE, prod_index)
                        )

    def _add_action(self, state_id, terminal, action):
        """Agrega acción, detecta conflictos."""
        if terminal in self.action_table[state_id]:
            existing = self.action_table[state_id][terminal]
            if existing != action:
                self.conflicts.append({
                    'state':    state_id,
                    'terminal': terminal,
                    'action1':  existing,
                    'action2':  action,
                    'type':     f"{existing[0]}/{action[0]}"
                })
                current = self.action_table[state_id][terminal]
                if isinstance(current, list):
                    current.append(action)
                else:
                    self.action_table[state_id][terminal] = [existing, action]
        else:
            self.action_table[state_id][terminal] = action

    def _find_production_index(self, non_terminal, symbols):
        for i, (nt, syms) in enumerate(self.grammar):
            if nt == non_terminal and syms == symbols:
                return i
        return -1

    def has_conflicts(self):
        return len(self.conflicts) > 0

    def __str__(self):
        lines = ["=== Tabla LALR ==="]
        lines.append(f"Estados LR(1) antes de fusionar: {len(self.lr1_states)}")
        lines.append(f"Estados LALR después de fusionar: {len(self.states)}")

        sorted_terminals     = sorted(self.terminals)
        sorted_non_terminals = sorted(self.non_terminals)

        lines.append("\n--- ACTION ---")
        header = f"{'Estado':8}" + ''.join(f"{t:12}" for t in sorted_terminals)
        lines.append(header)
        lines.append('-' * len(header))

        for state_id in sorted(self.action_table.keys()):
            row = f"{state_id:<8}"
            for terminal in sorted_terminals:
                action = self.action_table[state_id].get(terminal)
                if action is None:
                    cell = ""
                elif isinstance(action, list):
                    cell = "CONFLICT"
                else:
                    tipo, valor = action
                    if tipo == SHIFT:
                        cell = f"S{valor}"
                    elif tipo == REDUCE:
                        cell = f"R{valor}"
                    elif tipo == ACCEPT:
                        cell = "ACC"
                    else:
                        cell = ""
                row += f"{cell:12}"
            lines.append(row)

        lines.append("\n--- GOTO ---")
        header2 = f"{'Estado':8}" + ''.join(f"{nt:15}" for nt in sorted_non_terminals)
        lines.append(header2)
        lines.append('-' * len(header2))

        for state_id in sorted(self.goto_table.keys()):
            row = f"{state_id:<8}"
            for nt in sorted_non_terminals:
                dest = self.goto_table[state_id].get(nt)
                cell = str(dest) if dest is not None else ""
                row += f"{cell:15}"
            lines.append(row)

        if self.conflicts:
            lines.append(f"Conflictos LALR: {len(self.conflicts)}")
            for c in self.conflicts:
                lines.append(
                    f"  Estado {c['state']}, '{c['terminal']}': {c['type']}"
                )
        else:
            lines.append("Sin conflictos — la gramática es LALR")

        return '\n'.join(lines)