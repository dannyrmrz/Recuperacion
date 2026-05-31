# Construye el autómata LR(0) a partir de una gramática.
#
# El autómata LR(0) es la base para construir las tablas SLR(1) y LALR.
# Cada estado del autómata es un conjunto de ítems LR(0).


class LR0Item:
    """
    Representa un ítem LR(0): una producción con un punto.

    Ejemplo:
        producción: expresion → termino PLUS expresion
        ítem:       expresion → termino • PLUS expresion
                                         punto en posición 1

    Atributos:
    - non_terminal: el lado izquierdo (ej: 'expresion')
    - symbols: el lado derecho como lista (ej: ['termino', 'PLUS', 'expresion'])
    - dot: posición del punto (0 = al inicio, len(symbols) = al final)
    """

    def __init__(self, non_terminal, symbols, dot=0):
        self.non_terminal = non_terminal
        self.symbols = list(symbols)
        self.dot = dot

    def symbol_after_dot(self):
        """
        Retorna el símbolo que está justo DESPUÉS del punto.
        Retorna None si el punto está al final (ítem completo).

        Ejemplo:
            expresion → termino • PLUS expresion
            → retorna 'PLUS'

            expresion → termino PLUS expresion •
            → retorna None  (reducción)
        """
        if self.dot < len(self.symbols):
            return self.symbols[self.dot]
        return None

    def is_complete(self):
        """
        Retorna True si el punto está al final.
        Un ítem completo significa que podemos REDUCIR.

        Ejemplo:
            expresion → termino PLUS expresion •   → True (reducir)
            expresion → termino • PLUS expresion   → False (seguir leyendo)
        """
        return self.dot >= len(self.symbols)

    def advance(self):
        """
        Crea un nuevo ítem con el punto avanzado una posición.
        No modifica el ítem actual.

        Ejemplo:
            expresion → termino • PLUS expresion
            → retorna expresion → termino PLUS • expresion
        """
        return LR0Item(self.non_terminal, self.symbols, self.dot + 1)

    def __eq__(self, other):
        """Dos ítems son iguales si tienen el mismo no terminal, símbolos y punto."""
        return (self.non_terminal == other.non_terminal and
                self.symbols == other.symbols and
                self.dot == other.dot)

    def __hash__(self):
        """Necesario para usar ítems en conjuntos y diccionarios."""
        return hash((self.non_terminal, tuple(self.symbols), self.dot))

    def __repr__(self):
        """Representación visual del ítem con el punto."""
        symbols_with_dot = list(self.symbols)
        symbols_with_dot.insert(self.dot, '•')
        rhs = ' '.join(symbols_with_dot)
        return f"{self.non_terminal} → {rhs}"


class LR0State:
    """
    Representa un estado del autómata LR(0).

    Cada estado es un conjunto de ítems LR(0).
    Tiene transiciones hacia otros estados etiquetadas con símbolos.

    Atributos:
    - id: número único del estado
    - items: conjunto de ítems LR(0)
    - transitions: {símbolo: estado_destino}
    """

    _counter = 0

    def __init__(self, items):
        self.id = LR0State._counter
        LR0State._counter += 1
        self.items = frozenset(items)   # inmutable para comparar estados
        self.transitions = {}           # {símbolo: LR0State}

    def __eq__(self, other):
        return self.items == other.items

    def __hash__(self):
        return hash(self.items)

    def __repr__(self):
        items_str = '\n  '.join(str(item) for item in self.items)
        return f"State {self.id}:\n  {items_str}"


class LR0Automaton:
    """
    Construye el autómata LR(0) completo para una gramática.

    Pasos:
    1. Agregar producción aumentada: S' → S
    2. Calcular el estado inicial = clausura del ítem inicial
    3. Para cada estado, calcular GOTO con cada símbolo
    4. Repetir hasta que no haya estados nuevos
    """

    def __init__(self, yapar_reader):
        self.grammar        = yapar_reader.grammar
        self.terminals      = yapar_reader.get_terminals()
        self.non_terminals  = yapar_reader.get_non_terminals()
        self.start_symbol   = yapar_reader.start_symbol

        # Símbolo aumentado — S' → S
        # Lo agregamos para tener un punto de inicio claro
        self.augmented_start = self.start_symbol + "'"

        # Lista de todos los estados del autómata
        self.states = []

        # Estado inicial
        self.initial_state = None

        # Construir el autómata
        self._build()

    def _build(self):
        """
        Construye el autómata LR(0) completo.
        """
        # Paso 1: crear el ítem inicial de la producción aumentada
        # S' → • S
        initial_item = LR0Item(
            self.augmented_start,
            [self.start_symbol],
            dot=0
        )

        # Paso 2: calcular la clausura del ítem inicial - estado 0
        initial_items = self._closure({initial_item})
        initial_state = LR0State(initial_items)

        self.states.append(initial_state)
        self.initial_state = initial_state

        # Paso 3: procesar cada estado hasta que no haya nuevos
        # Usamos un índice en vez de una cola para simplificar
        i = 0
        while i < len(self.states):
            current_state = self.states[i]

            # Encontrar todos los símbolos que aparecen después de algún punto
            symbols_after_dot = set()
            for item in current_state.items:
                symbol = item.symbol_after_dot()
                if symbol is not None:
                    symbols_after_dot.add(symbol)

            # Calcular GOTO para cada símbolo
            for symbol in symbols_after_dot:
                goto_state = self._goto(current_state, symbol)

                if goto_state is None:
                    continue

                # Ya existe este estado
                existing = self._find_state(goto_state.items)

                if existing is None:
                    # Estado nuevo — agregar a la lista
                    self.states.append(goto_state)
                    current_state.transitions[symbol] = goto_state
                else:
                    # Estado ya existe — solo agregar la transición
                    # pero liberar el contador (el estado nuevo se descarta)
                    LR0State._counter -= 1
                    current_state.transitions[symbol] = existing

            i += 1

    def _closure(self, items):
        """
        Calcula la clausura de un conjunto de ítems.

        Regla: si un ítem tiene el punto antes de un no terminal B,
        agregar todos los ítems B → • γ para cada producción B → γ.

        Repetir hasta que no haya cambios.

        Ejemplo:
            Ítem: expresion → • termino PLUS expresion
            → agregar: termino → • factor
            → agregar: termino → • factor TIMES termino
            → agregar: factor → • INT
            → agregar: factor → • LPAREN expresion RPAREN
        """
        closure = set(items)
        queue = list(items)

        while queue:
            item = queue.pop(0)
            symbol = item.symbol_after_dot()

            # Si el símbolo después del punto es un no terminal
            if symbol is not None and symbol in self.non_terminals:
                # Agregar todos los ítems de ese no terminal
                for nt, prod_symbols in self.grammar:
                    if nt == symbol:
                        new_item = LR0Item(nt, prod_symbols, dot=0)
                        if new_item not in closure:
                            closure.add(new_item)
                            queue.append(new_item)

        return closure

    def _goto(self, state, symbol):
        """
        Calcula GOTO(estado, símbolo).

        Toma todos los ítems donde el punto está ANTES de 'symbol',
        avanza el punto, y calcula la clausura.

        Retorna el nuevo estado, o None si no hay ítems válidos.

        Ejemplo:
            GOTO(estado_con[expresion → termino • PLUS expresion], PLUS)
            → expresion → termino PLUS • expresion
            → clausura de ese ítem
            → nuevo estado
        """
        # Encontrar ítems donde el punto está antes de 'symbol'
        advanced_items = set()
        for item in state.items:
            if item.symbol_after_dot() == symbol:
                advanced_items.add(item.advance())

        if not advanced_items:
            return None

        # Calcular la clausura del conjunto avanzado
        closure_items = self._closure(advanced_items)
        return LR0State(closure_items)

    def _find_state(self, items):
        """
        Busca si ya existe un estado con exactamente estos ítems.
        Retorna el estado existente o None.
        """
        items_frozen = frozenset(items)
        for state in self.states:
            if state.items == items_frozen:
                return state
        return None

    def get_all_symbols(self):
        """Retorna todos los símbolos (terminales + no terminales)."""
        return self.terminals | self.non_terminals

    def __str__(self):
        """Representación legible del autómata."""
        lines = ["=== Autómata LR(0) ==="]
        lines.append(f"Total de estados: {len(self.states)}")
        lines.append(f"Símbolo inicial aumentado: {self.augmented_start} → {self.start_symbol}\n")

        for state in self.states:
            lines.append(f"Estado {state.id}:")
            for item in sorted(state.items, key=str):
                # Marcar ítems completos (punto al final) con [REDUCIR]
                marker = " [REDUCIR]" if item.is_complete() else ""
                lines.append(f"  {item}{marker}")

            if state.transitions:
                lines.append("  Transiciones:")
                for symbol, dest in sorted(state.transitions.items()):
                    lines.append(f"    --{symbol}--> Estado {dest.id}")
            lines.append("")

        return '\n'.join(lines)