# Calcula las funciones FIRST y FOLLOW para una gramática.
# Estas funciones son necesarias para construir las tablas LL(1) y SLR(1).


class FirstFollowCalculator:
    """
    Calcula FIRST y FOLLOW para todos los símbolos de una gramática.

    Recibe un YAParReader ya procesado y calcula:
    - first:  diccionario {símbolo: conjunto de terminales}
    - follow: diccionario {no_terminal: conjunto de terminales}
    """

    def __init__(self, yapar_reader):
        # Guardamos referencia al lector para acceder a la gramática
        self.grammar      = yapar_reader.grammar        # [(nt, [símbolos]), ...]
        self.terminals    = yapar_reader.get_terminals() # {'INT', 'PLUS', ..., '$'}
        self.non_terminals = yapar_reader.get_non_terminals() # {'expresion', ...}
        self.start_symbol = yapar_reader.start_symbol

        # Resultados — se llenan al llamar compute()
        self.first  = {}   # {símbolo: set de terminales}
        self.follow = {}   # {no_terminal: set de terminales}

        # Calcular automáticamente al construir el objeto
        self._compute_first()
        self._compute_follow()

    # Calcular First
    def _compute_first(self):
        """
        Calcula FIRST para todos los símbolos de la gramática.

        Inicializa cada símbolo con un conjunto vacío y luego
        aplica las reglas repetidamente hasta que ningún conjunto cambie.
        Esto se llama algoritmo de punto fijo.
        """
        # Inicializar FIRST vacío para todos los símbolos
        for terminal in self.terminals:
            self.first[terminal] = {terminal}  # FIRST de un terminal es él mismo

        for non_terminal in self.non_terminals:
            self.first[non_terminal] = set()   # FIRST de no terminal empieza vacío

        # Repetir hasta que no haya cambios (punto fijo)
        changed = True
        while changed:
            changed = False

            for non_terminal, symbols in self.grammar:
                # Calcular FIRST de la parte derecha de esta producción
                new_first = self._first_of_sequence(symbols)

                # Si encontramos algo nuevo, agregar y marcar que hubo cambio
                before = len(self.first[non_terminal])
                self.first[non_terminal] |= new_first  # |= es unión de conjuntos
                after = len(self.first[non_terminal])

                if after > before:
                    changed = True

    def _first_of_sequence(self, symbols):
        """
        Calcula FIRST de una secuencia de símbolos [Y1, Y2, ..., Yn].

        Regla:
        - Agregar FIRST(Y1) - {ε}
        - Si ε ∈ FIRST(Y1), agregar FIRST(Y2) - {ε}
        - Si ε ∈ FIRST(Y1) y FIRST(Y2), agregar FIRST(Y3) - {ε}
        - ... y así sucesivamente
        - Si ε ∈ FIRST(Yi) para todos los Yi se agregar ε al resultado

        Ejemplo:
            símbolos = [A, B, C]
            Si A puede derivar ε y B también entonces el resultado incluye FIRST(C)
        """
        result = set()

        # Caso especial: producción vacía (épsilon)
        if symbols == ['ε'] or not symbols:
            return {'ε'}

        all_have_epsilon = True  # asumimos que todos pueden derivar ε

        for symbol in symbols:
            # Obtener FIRST del símbolo actual
            # Si el símbolo no está en first todavía, usar conjunto vacío
            symbol_first = self.first.get(symbol, set())

            # Agregar todo excepto ε
            result |= (symbol_first - {'ε'})

            if 'ε' not in symbol_first:
                # Este símbolo NO puede derivar ε
                # entonces los siguientes símbolos no contribuyen
                all_have_epsilon = False
                break

        # Si todos los símbolos pueden derivar ε → ε también está en el resultado
        if all_have_epsilon:
            result.add('ε')

        return result

    # Calcular Follow
    def _compute_follow(self):
        """
        Calcula FOLLOW para todos los no terminales.

        Reglas:
        1. $ ∈ FOLLOW(símbolo_inicial)
        2. A → α B β : FIRST(β)-{ε} ⊆ FOLLOW(B)
        3. A → α B β donde ε ∈ FIRST(β): FOLLOW(A) ⊆ FOLLOW(B)
        4. A → α B : FOLLOW(A) ⊆ FOLLOW(B)

        Repetir hasta punto fijo.
        """
        # Inicializar FOLLOW vacío para todos los no terminales
        for non_terminal in self.non_terminals:
            self.follow[non_terminal] = set()

        # Regla 1: $ siempre está en FOLLOW del símbolo inicial
        self.follow[self.start_symbol].add('$')

        # Repetir hasta que no haya cambios
        changed = True
        while changed:
            changed = False

            # Recorrer cada producción A → symbols
            for lhs, symbols in self.grammar:
                # lhs = lado izquierdo (non terminal)
                # symbols = lado derecho [Y1, Y2, ..., Yn]

                for i, symbol in enumerate(symbols):
                    # Solo calculamos FOLLOW para no terminales
                    if symbol not in self.non_terminals:
                        continue

                    # Los símbolos que vienen DESPUÉS de symbol en esta producción
                    beta = symbols[i + 1:]  # puede estar vacío si symbol es el último

                    before = len(self.follow[symbol])

                    if beta:
                        # Reglas 2 y 3: hay símbolos después de 'symbol'
                        first_beta = self._first_of_sequence(beta)

                        # Regla 2: agregar FIRST(β) - {ε} a FOLLOW(symbol)
                        self.follow[symbol] |= (first_beta - {'ε'})

                        # Regla 3: si ε ∈ FIRST(β), agregar FOLLOW(A) a FOLLOW(symbol)
                        if 'ε' in first_beta:
                            self.follow[symbol] |= self.follow[lhs]
                    else:
                        # Regla 4: symbol es el último entonces se agrega FOLLOW(A)
                        self.follow[symbol] |= self.follow[lhs]

                    after = len(self.follow[symbol])
                    if after > before:
                        changed = True

    #consultas
    def get_first(self, symbol):
        """Retorna FIRST de un símbolo."""
        return self.first.get(symbol, set())

    def get_follow(self, non_terminal):
        """Retorna FOLLOW de un no terminal."""
        return self.follow.get(non_terminal, set())

    def get_first_of_sequence(self, symbols):
        """Retorna FIRST de una secuencia de símbolos. Útil para las tablas."""
        return self._first_of_sequence(symbols)

    def __str__(self):
        """Representación legible para depuración."""
        lines = ["=== FIRST y FOLLOW ==="]

        lines.append("\nFIRST:")
        for symbol in sorted(self.non_terminals):
            first_str = ', '.join(sorted(self.first.get(symbol, set())))
            lines.append(f"  FIRST({symbol}) = {{ {first_str} }}")

        lines.append("\nFOLLOW:")
        for symbol in sorted(self.non_terminals):
            follow_str = ', '.join(sorted(self.follow.get(symbol, set())))
            lines.append(f"  FOLLOW({symbol}) = {{ {follow_str} }}")

        return '\n'.join(lines)