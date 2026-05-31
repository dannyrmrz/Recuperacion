# Construye la tabla de análisis SLR(1) a partir del autómata LR(0).
# Usa FOLLOW para decidir cuándo reducir.
#
# La tabla tiene dos partes:
# - ACTION: qué hacer con terminales (shift, reduce, accept, error)
# - GOTO: a qué estado ir después de reducir (para no terminales)


# Constantes para los tipos de acción
SHIFT  = 'SHIFT'
REDUCE = 'REDUCE'
ACCEPT = 'ACCEPT'
ERROR  = 'ERROR'


class SLRTable:
    """
    Construye la tabla SLR(1).

    Recibe:
    - yapar_reader: la gramática
    - lr0_automaton: el autómata LR(0) ya construido
    - first_follow: el calculador de FIRST y FOLLOW

    Produce:
    - action_table: {estado_id: {terminal: (tipo, valor)}}
    - goto_table:   {estado_id: {no_terminal: estado_id}}
    - conflicts:    lista de conflictos encontrados
    """

    def __init__(self, yapar_reader, lr0_automaton, first_follow):
        self.grammar        = yapar_reader.grammar
        self.terminals      = yapar_reader.get_terminals()
        self.non_terminals  = yapar_reader.get_non_terminals()
        self.start_symbol   = yapar_reader.start_symbol
        self.augmented_start = lr0_automaton.augmented_start
        self.automaton      = lr0_automaton
        self.calc           = first_follow

        # ACTION[estado_id][terminal] = (tipo, valor)
        # tipo puede ser SHIFT, REDUCE, ACCEPT, ERROR
        # valor es el estado destino (SHIFT) o índice de producción (REDUCE)
        self.action_table = {}

        # GOTO[estado_id][no_terminal] = estado_id_destino
        self.goto_table = {}

        # Lista de conflictos: cada uno tiene tipo, estado, símbolo, acciones
        self.conflicts = []

        # Construir la tabla
        self._build()

    def _build(self):
        """
        Llena la tabla ACTION y GOTO recorriendo todos los estados del autómata LR(0).
        """
        # Inicializar tablas vacías para cada estado
        for state in self.automaton.states:
            self.action_table[state.id] = {}
            self.goto_table[state.id]   = {}

        # Procesar cada estado
        for state in self.automaton.states:
            for item in state.items:
                symbol = item.symbol_after_dot()

                if symbol is not None:
                    # El punto NO está al final

                    if symbol in self.terminals:
                        # CASO 1: A → α • a β  (a es terminal)
                        # → SHIFT al estado destino
                        dest_state = state.transitions.get(symbol)
                        if dest_state:
                            self._add_action(
                                state.id, symbol,
                                (SHIFT, dest_state.id)
                            )

                    elif symbol in self.non_terminals:
                        # CASO 4: A → α • B β  (B es no terminal)
                        # → GOTO
                        dest_state = state.transitions.get(symbol)
                        if dest_state:
                            self.goto_table[state.id][symbol] = dest_state.id

                else:
                    # El punto ESTÁ al final → ítem completo

                    if item.non_terminal == self.augmented_start:
                        # CASO 3: S' → S •
                        # → ACCEPT
                        self._add_action(state.id, '$', (ACCEPT, None))

                    else:
                        # CASO 2: A → α •
                        # → REDUCE para cada terminal en FOLLOW(A)
                        prod_index = self._find_production_index(
                            item.non_terminal, item.symbols
                        )
                        follow_a = self.calc.get_follow(item.non_terminal)

                        for terminal in follow_a:
                            self._add_action(
                                state.id, terminal,
                                (REDUCE, prod_index)
                            )

    def _add_action(self, state_id, terminal, action):
        """
        Agrega una acción a la tabla ACTION.

        Si la celda ya tiene una acción diferente → CONFLICTO.
        Guardamos ambas acciones para el parser paralelo.
        """
        if terminal in self.action_table[state_id]:
            existing = self.action_table[state_id][terminal]

            if existing != action:
                # CONFLICTO Dos acciones para el mismo estado y terminal
                conflict_type = f"{existing[0]}/{action[0]}"  # ej: "SHIFT/REDUCE"

                self.conflicts.append({
                    'state':   state_id,
                    'terminal': terminal,
                    'action1': existing,
                    'action2': action,
                    'type':    conflict_type
                })

                # Guardar AMBAS acciones como lista para el parser paralelo
                current = self.action_table[state_id][terminal]
                if isinstance(current, list):
                    current.append(action)
                else:
                    self.action_table[state_id][terminal] = [existing, action]
        else:
            self.action_table[state_id][terminal] = action

    def _find_production_index(self, non_terminal, symbols):
        """
        Encuentra el índice de una producción en la gramática.
        Necesario para saber qué producción usar al reducir.
        """
        for i, (nt, syms) in enumerate(self.grammar):
            if nt == non_terminal and syms == symbols:
                return i
        return -1

    def get_action(self, state_id, terminal):
        """
        Consulta la tabla ACTION.

        Retorna:
        - (tipo, valor) si hay una acción única
        - [(tipo1, val1), (tipo2, val2)] si hay conflicto (para parser paralelo)
        - None si es error
        """
        return self.action_table.get(state_id, {}).get(terminal, None)

    def get_goto(self, state_id, non_terminal):
        """
        Consulta la tabla GOTO.
        Retorna el estado destino o None.
        """
        return self.goto_table.get(state_id, {}).get(non_terminal, None)

    def has_conflicts(self):
        """Retorna True si hay conflictos shift/reduce o reduce/reduce."""
        return len(self.conflicts) > 0

    def __str__(self):
        lines = ["=== Tabla SLR(1) ==="]

        sorted_terminals     = sorted(self.terminals)
        sorted_non_terminals = sorted(self.non_terminals)

        lines.append("\n--- ACTION ---")
        header = f"{'Estado':8}" + ''.join(f"{t:12}" for t in sorted_terminals)
        lines.append(header)
        lines.append('-' * len(header))

        for state in sorted(self.action_table.keys()):
            row = f"{state:<8}"
            for terminal in sorted_terminals:
                action = self.action_table[state].get(terminal)
                if action is None:
                    cell = ""
                elif isinstance(action, list):
                    cell = "CONFLICTO"
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

        for state in sorted(self.goto_table.keys()):
            row = f"{state:<8}"
            for nt in sorted_non_terminals:
                dest = self.goto_table[state].get(nt)
                cell = str(dest) if dest is not None else ""
                row += f"{cell:15}"
            lines.append(row)

        if self.conflicts:
            lines.append(f"Conflictos encontrados: {len(self.conflicts)}")
            for c in self.conflicts:
                lines.append(
                    f"  Estado {c['state']}, token '{c['terminal']}': "
                    f"{c['type']} — "
                    f"{c['action1']} vs {c['action2']}"
                )
        else:
            lines.append("Sin conflictos — la gramática es SLR(1)")

        return '\n'.join(lines)