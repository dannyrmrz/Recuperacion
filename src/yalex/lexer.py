# Lee un archivo .yalex y extrae sus datos en estructuras Python.
# De momento no hace nada con las regex, solo lee y organiza.


class YALexReader:
    """
    Lee un archivo .yalex y extrae:
    - definitions: diccionario de {nombre: regex_string}
    - rules: lista de [(patron, token_name)]
    """

    def __init__(self, filepath):
        # ruta del archivo .yalex a leer
        self.filepath = filepath

        # nombre → expresión regular como texto
        self.definitions = {}

        # lista de tuplas: (patron, token)
        self.rules = []

        # Lee y procesa el archivo al crear el objeto
        self._read_file()

    def _read_file(self):
        """
        Lee el archivo .yalex completo y lanza el procesamiento.
        """
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"No se encontró el archivo: {self.filepath}")

        # eliminar comentarios (* ... *)
        content = self._remove_comments(content)

        # separar en sección de definiciones y sección de reglas
        definitions_text, rules_text = self._split_sections(content)

        # procesar cada sección por separado
        self._parse_definitions(definitions_text)
        self._parse_rules(rules_text)

    def _remove_comments(self, text):
        """
        Elimina comentarios del estilo (* esto es un comentario *).

        """
        result = []
        i = 0
        while i < len(text):
            # Encontramos el inicio de un comentario
            if text[i:i+2] == '(*':
                # Buscar el cierre del comentario
                end = text.find('*)', i + 2)
                if end == -1:
                    # Si no hay cierre, ignoramos el resto del archivo
                    break
                # Saltar todo el comentario (incluyendo '(*' y '*)')
                i = end + 2
            else:
                result.append(text[i])
                i += 1

        return ''.join(result)

    def _split_sections(self, text):
        """
        Divide el archivo en dos partes:
        - Todo lo que está ANTES de 'rule tokens ='  → definiciones
        - Todo lo que está DESPUÉS de 'rule tokens =' → reglas

        Si no existe 'rule tokens =', lanza un error.
        """
        # Busca la palabra clave que separa las dos secciones
        separator = 'rule tokens ='

        if separator not in text:
            raise ValueError(
                "El archivo .yalex no tiene 'rule tokens ='. "
                "Verifica el formato del archivo."
            )

        # split(separator, 1) divide en máximo 2 partes
        parts = text.split(separator, 1)
        definitions_text = parts[0]   # antes del separador
        rules_text = parts[1]          # después del separador

        return definitions_text, rules_text

    def _parse_definitions(self, text):
        """
        Procesa las líneas de definición.
        Cada definición tiene el formato:
            let nombre = expresion_regular

        Ejemplo:
            let digit = ['0'-'9']
            → self.definitions['digit'] = "['0'-'9']"
        """
        for line in text.splitlines():
            # Limpia espacios al inicio y al final
            line = line.strip()

            # Ignora líneas vacías
            if not line:
                continue

            # Todas las definiciones empiezan con 'let'
            if not line.startswith('let '):
                continue

            # Quitar el 'let ' del inicio
            line = line[4:].strip()

            # Ahora se mira como: "nombre = expresion"
            # Divide en el primer '=' que encontremos
            if '=' not in line:
                continue

            name, regex = line.split('=', 1)
            name = name.strip()    # quitar espacios del nombre
            regex = regex.strip()  # quitar espacios de la regex

            # Guardar en el diccionario
            self.definitions[name] = regex

    def _parse_rules(self, text):
        """
        Procesa las líneas de reglas.
        Cada regla tiene el formato:
            | patron    { TOKEN }

        Ejemplo:
            | digit+    { INT }
            → self.rules.append(('digit+', 'INT'))

        También puede haber acciones a ignorar como { (* ignorar *) }
        En ese caso guardo None como token.
        """
        for line in text.splitlines():
            line = line.strip()

            # Ignorar líneas vacías
            if not line:
                continue

            # Todas las reglas empiezan con '|'
            if not line.startswith('|'):
                continue

            # Quitar el '|' del inicio
            line = line[1:].strip()

            # Buscar el bloque de acción { TOKEN }
            # El patrón está antes del '{', el token está dentro
            if '{' not in line or '}' not in line:
                continue

            # Separar patrón de acción
            brace_start = line.index('{')
            brace_end = line.index('}')

            pattern = line[:brace_start].strip()
            action = line[brace_start + 1 : brace_end].strip()

            # Si la acción contiene un comentario, es una regla a ignorar
            # Ejemplo: { (* ignorar espacios *) }
            if action.startswith('(*') or action == '':
                token = None   # None significa "ignorar este lexema"
            else:
                token = action  # El token es el texto dentro de { }

            self.rules.append((pattern, token))

    def expand_definitions(self):
        """
        Reemplaza los nombres de definiciones dentro de los patrones
        por su expresión regular real.

        Ejemplo:
            definitions = {'digit': "['0'-'9']"}
            pattern = "digit+"
            → resultado = "['0'-'9']+"

        El motor de regex no conoce los nombres, solo las expresiones.

        Se expande en orden, porque una definición
        puede usar otra definición anterior.
        """
        expanded_rules = []

        for pattern, token in self.rules:
            expanded = pattern

            # Reemplaza cada nombre de definición en el patrón
            # Itera en orden para respetar dependencias
            for name, regex in self.definitions.items():
                # Solo reemplazar si el nombre aparece como palabra completa
                # (evitar reemplazar 'digit' dentro de 'digits')
                expanded = self._replace_whole_word(expanded, name, regex)

            expanded_rules.append((expanded, token))

        return expanded_rules

    def _replace_whole_word(self, text, word, replacement):
        """
        Reemplaza 'word' por 'replacement' en 'text',
        pero solo cuando 'word' aparece como palabra completa.

        Ejemplo:
            _replace_whole_word("digit+digits", "digit", "X")
            → no debería reemplazar 'digit' dentro de 'digits'

        Usa una verificación manual de caracteres vecinos.
        """
        result = []
        i = 0
        word_len = len(word)

        while i < len(text):
            # Encontramos la palabra en esta posición
            if text[i:i + word_len] == word:
                # Verificar que no sea parte de una palabra más larga
                # Revisar carácter antes
                before_ok = (i == 0) or not text[i-1].isalnum() and text[i-1] != '_'
                # Revisar carácter después
                after_pos = i + word_len
                after_ok = (after_pos >= len(text)) or not text[after_pos].isalnum() and text[after_pos] != '_'

                if before_ok and after_ok:
                    result.append(f'({replacement})')
                    i += word_len
                    continue

            result.append(text[i])
            i += 1

        return ''.join(result)

    def __str__(self):
        """
        Representación legible del contenido leído.
        """
        lines = ["=== YALex Reader ==="]
        lines.append(f"Archivo: {self.filepath}")
        lines.append(f"\n--- Definiciones ({len(self.definitions)}) ---")

        for name, regex in self.definitions.items():
            lines.append(f"  {name} = {regex}")

        lines.append(f"\n--- Reglas ({len(self.rules)}) ---")
        for i, (pattern, token) in enumerate(self.rules):
            token_str = token if token else "(ignorar)"
            lines.append(f"  {i+1}. '{pattern}' → {token_str}")

        return '\n'.join(lines)