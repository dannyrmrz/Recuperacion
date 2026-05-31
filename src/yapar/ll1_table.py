# Construye la tabla de análisis LL(1) y ejecuta el parser LL(1).
#
# La tabla se construye usando FIRST y FOLLOW.
# El parser usa la tabla junto con una pila para validar la entrada.


class LL1Table:
    """
    Construye y representa la tabla de análisis LL(1).

    La tabla es un diccionario de diccionarios:
        table[no_terminal][terminal] = (no_terminal, [símbolos])

    Si una celda tiene más de una producción entonces hay conflicto y no es LL(1).
    """

    def __init__(self, yapar_reader, first_follow_calculator):
        self.grammar       = yapar_reader.grammar
        self.terminals     = yapar_reader.get_terminals()
        self.non_terminals = yapar_reader.get_non_terminals()
        self.start_symbol  = yapar_reader.start_symbol
        self.calc          = first_follow_calculator

        # La tabla: {no_terminal: {terminal: (nt, [símbolos])}}
        self.table = {}

        # Lista de conflictos encontrados
        self.conflicts = []

        # Construir la tabla
        self._build_table()

    def _build_table(self):
        """
        Construye la tabla LL(1).

        Para cada producción A → α:
        1. Calcular FIRST(α)
        2. Para cada terminal en FIRST(α) - {ε} → tabla[A][terminal] = producción
        3. Si ε ∈ FIRST(α) → para cada terminal en FOLLOW(A) → tabla[A][terminal] = producción
        """
        # Inicializar la tabla vacía para cada no terminal
        for nt in self.non_terminals:
            self.table[nt] = {}

        # Procesar cada producción
        for non_terminal, symbols in self.grammar:

            # Calcular FIRST de la parte derecha (los símbolos)
            first_alpha = self.calc.get_first_of_sequence(symbols)

            # Regla 1: para cada terminal en FIRST(α) - {ε}
            for terminal in first_alpha - {'ε'}:
                self._add_to_table(non_terminal, terminal, (non_terminal, symbols))

            # Regla 2: si ε ∈ FIRST(α), usar FOLLOW(A)
            if 'ε' in first_alpha:
                for terminal in self.calc.get_follow(non_terminal):
                    self._add_to_table(non_terminal, terminal, (non_terminal, symbols))

    def _add_to_table(self, non_terminal, terminal, production):
        """
        Agrega una producción a la tabla en la celda [non_terminal][terminal].

        Si la celda ya tiene una producción → conflicto LL(1).
        Guardamos el conflicto pero continuamos (para reportarlo después).
        """
        if terminal in self.table[non_terminal]:
            # Ya hay algo en esta celda - CONFLICTO
            existing = self.table[non_terminal][terminal]
            if existing != production:
                self.conflicts.append({
                    'non_terminal': non_terminal,
                    'terminal': terminal,
                    'production1': existing,
                    'production2': production
                })
        else:
            self.table[non_terminal][terminal] = production

    def is_ll1(self):
        """Retorna True si la gramática no tiene conflictos LL(1)."""
        return len(self.conflicts) == 0

    def get_production(self, non_terminal, terminal):
        """
        Consulta la tabla: dado un no terminal y un terminal,
        retorna la producción a usar, o None si no hay entrada.
        """
        return self.table.get(non_terminal, {}).get(terminal, None)

    def __str__(self):
        """Imprime la tabla de forma legible."""
        lines = ["=== Tabla LL(1) ==="]

        # Obtener todos los terminales que aparecen en la tabla
        all_terminals = sorted(self.terminals)

        # Encabezado
        header = f"{'':20}" + ''.join(f"{t:15}" for t in all_terminals)
        lines.append(header)
        lines.append('-' * len(header))

        # Filas
        for nt in sorted(self.non_terminals):
            row = f"{nt:20}"
            for terminal in all_terminals:
                prod = self.get_production(nt, terminal)
                if prod:
                    # Mostrar solo el lado derecho de la producción
                    rhs = ' '.join(prod[1])
                    cell = f"{rhs}"
                else:
                    cell = ""
                row += f"{cell:15}"
            lines.append(row)

        if self.conflicts:
            lines.append(f"\n Conflictos LL(1): {len(self.conflicts)}")
            for c in self.conflicts:
                p1 = ' '.join(c['production1'][1])
                p2 = ' '.join(c['production2'][1])
                lines.append(
                    f"  [{c['non_terminal']}][{c['terminal']}]: "
                    f"'{p1}' vs '{p2}'"
                )
        else:
            lines.append("\n La gramática ES LL(1) — sin conflictos")

        return '\n'.join(lines)

#Parser LL(1)
class LL1Parser:
    """
    Parser LL(1) que valida si una lista de tokens es válida
    según la gramática.

    Usa una pila y la tabla LL(1) para hacer derivaciones.
    """

    def __init__(self, ll1_table):
        self.table        = ll1_table
        self.start_symbol = ll1_table.start_symbol

    def parse(self, tokens):
        """
        Valida una lista de tokens usando el algoritmo LL(1).
        """
        if tokens and hasattr(tokens[0], 'type'):
            input_tokens = [t.type for t in tokens]
        else:
            input_tokens = list(tokens)

        if not input_tokens or input_tokens[-1] != '$':
            input_tokens.append('$')

        stack = ['$', self.start_symbol]
        pos = 0
        steps = []

        # Límite de seguridad — evita loops infinitos con gramáticas inválidas
        MAX_STEPS = 1000

        while stack and len(steps) < MAX_STEPS:
            top = stack[-1]
            current_token = input_tokens[pos] if pos < len(input_tokens) else '$'

            step = {
                'stack': list(stack),
                'input': input_tokens[pos:],
                'action': ''
            }

            if top == '$' and current_token == '$':
                step['action'] = 'ACEPTAR'
                steps.append(step)
                return True, steps

            elif top == current_token:
                step['action'] = f'MATCH {top}'
                steps.append(step)
                stack.pop()
                pos += 1

            elif top in self.table.non_terminals:
                production = self.table.get_production(top, current_token)

                if production is None:
                    step['action'] = (
                        f'ERROR: no hay producción para '
                        f'[{top}][{current_token}]'
                    )
                    steps.append(step)
                    return False, steps

                nt, symbols = production
                step['action'] = f'EXPANDIR {top} → {" ".join(symbols)}'
                steps.append(step)
                stack.pop()

                if symbols != ['ε']:
                    for symbol in reversed(symbols):
                        stack.append(symbol)

            else:
                step['action'] = f'ERROR: esperaba {top}, encontré {current_token}'
                steps.append(step)
                return False, steps

        # Si llegamos aquí es porque superamos el límite de pasos
        if len(steps) >= MAX_STEPS:
            steps.append({
                'stack': list(stack),
                'input': input_tokens[pos:],
                'action': 'ERROR: límite de pasos alcanzado — posible recursión infinita'
            })

        return False, steps