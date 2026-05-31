# Lee un archivo .yapar y extrae:
# - tokens: lista de terminales declarados con %token
# - grammar: lista de producciones (no_terminal, [símbolos])
# - start_symbol: el primer no terminal de la gramática


class YAParReader:
    """
    Lee un archivo .yapar y extrae la gramática.

    Un archivo .yapar tiene dos secciones separadas por '%%':

    SECCIÓN 1 — declaraciones:
        %token INT PLUS MINUS ...

    SECCIÓN 2 — reglas gramaticales:
        programa : expresion
                 ;
        expresion : expresion PLUS termino
                  | termino
                  ;
    """

    def __init__(self, filepath):
        self.filepath = filepath

        # Lista de tokens terminales declarados con %token
        # Ejemplo: ['INT', 'FLOAT', 'ID', 'PLUS']
        self.tokens = []

        # Lista de producciones: [(no_terminal, [símbolo1, símbolo2, ...]), ...]
        # Ejemplo: [('expresion', ['expresion', 'PLUS', 'termino']),
        #           ('expresion', ['termino'])]
        self.grammar = []

        # El símbolo inicial es el primer no terminal que aparece
        self.start_symbol = None

        # Conjunto de no terminales (los que aparecen a la izquierda de alguna regla)
        self.non_terminals = set()

        # Leer y procesar el archivo
        self._read_file()

    def _read_file(self):
        """Lee el archivo completo y lanza el procesamiento."""
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"No se encontró el archivo: {self.filepath}")

        # Paso 1: eliminar comentarios /* ... */
        content = self._remove_comments(content)

        # Paso 2: separar las dos secciones por '%%'
        declarations, rules = self._split_sections(content)

        # Paso 3: procesar cada sección
        self._parse_declarations(declarations)
        self._parse_rules(rules)

    def _remove_comments(self, text):
        """
        Elimina comentarios del estilo /* comentario */.
        """
        result = []
        i = 0

        while i < len(text):
            if text[i:i+2] == '/*':
                # Buscar el cierre del comentario
                end = text.find('*/', i + 2)
                if end == -1:
                    break  # no hay cierre, ignorar el resto
                i = end + 2  # saltar hasta después de '*/'
            else:
                result.append(text[i])
                i += 1

        return ''.join(result)

    def _split_sections(self, text):
        """
        Divide el archivo en dos partes usando '%%' como separador.

        Todo lo que está ANTES de '%%' son declaraciones (%token, etc.)
        Todo lo que está DESPUÉS de '%%' son las reglas gramaticales.
        """
        if '%%' not in text:
            raise ValueError(
                "El archivo .yapar no tiene '%%'. "
                "Verifica el formato del archivo."
            )

        parts = text.split('%%', 1)
        return parts[0], parts[1]

    def _parse_declarations(self, text):
        """
        Procesa la sección de declaraciones.

        Busca líneas que empiecen con '%token' y extrae
        todos los nombres de tokens que siguen.

        Ejemplo:
            '%token INT FLOAT ID PLUS MINUS'
            self.tokens = ['INT', 'FLOAT', 'ID', 'PLUS', 'MINUS']
        """
        for line in text.splitlines():
            line = line.strip()

            if line.startswith('%token'):
                # Quitar '%token' y dividir el resto por espacios
                token_part = line[len('%token'):].strip()
                tokens = token_part.split()
                self.tokens.extend(tokens)

    def _parse_rules(self, text):
        """
        Procesa la sección de reglas gramaticales.

        El formato es:
            no_terminal : simbolo1 simbolo2 ...
                        | simbolo3 simbolo4 ...
                        ;

        Cada bloque termina con ';'.
        Dentro del bloque, '|' separa producciones alternativas.

        Ejemplo:
            expresion : expresion PLUS termino
                      | termino
                      ;

            Produce:
            ('expresion', ['expresion', 'PLUS', 'termino'])
            ('expresion', ['termino'])
        """
        # Dividir por ';' para obtener cada bloque de reglas
        # Cada bloque corresponde a un no terminal
        blocks = text.split(';')

        for block in blocks:
            block = block.strip()

            # Ignorar bloques vacíos
            if not block:
                continue

            # El bloque tiene el formato: "no_terminal : alternativa1 | alternativa2"
            # Primero separamos el no terminal del resto
            if ':' not in block:
                continue

            parts = block.split(':', 1)
            non_terminal = parts[0].strip()
            alternatives_text = parts[1].strip()

            # Ignorar si el no terminal está vacío
            if not non_terminal:
                continue

            # Registrar el no terminal
            self.non_terminals.add(non_terminal)

            # El primer no terminal que aparece es el símbolo inicial
            if self.start_symbol is None:
                self.start_symbol = non_terminal

            # Separar las alternativas por '|'
            alternatives = alternatives_text.split('|')

            for alt in alternatives:
                # Dividir cada alternativa en símbolos individuales
                symbols = alt.split()

                # Ignorar alternativas vacías
                if not symbols:
                    continue

                # Agregar la producción a la gramática
                # Formato: (no_terminal, [lista de símbolos])
                self.grammar.append((non_terminal, symbols))

    def get_terminals(self):
        """
        Retorna el conjunto de símbolos terminales.

        Los terminales son los tokens declarados con %token
        más el símbolo especial '$' que representa fin de entrada.
        """
        return set(self.tokens) | {'$'}

    def get_non_terminals(self):
        """Retorna el conjunto de no terminales."""
        return set(self.non_terminals)

    def get_productions_for(self, non_terminal):
        """
        Retorna todas las producciones de un no terminal específico.

        Ejemplo:
            get_productions_for('expresion')
            → [['expresion', 'PLUS', 'termino'], ['termino']]
        """
        return [
            symbols
            for nt, symbols in self.grammar
            if nt == non_terminal
        ]

    def __str__(self):
        """Representación legible para depuración."""
        lines = ["=== YAPar Reader ==="]
        lines.append(f"Archivo: {self.filepath}")
        lines.append(f"Símbolo inicial: {self.start_symbol}")
        lines.append(f"\nTokens ({len(self.tokens)}): {self.tokens}")
        lines.append(f"\nNo terminales: {self.non_terminals}")
        lines.append(f"\nProducciones ({len(self.grammar)}):")

        for i, (nt, symbols) in enumerate(self.grammar):
            symbols_str = ' '.join(symbols)
            lines.append(f"  {i}: {nt} → {symbols_str}")

        return '\n'.join(lines)