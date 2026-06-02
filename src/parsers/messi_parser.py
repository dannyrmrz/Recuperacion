# Parser para MessiScript.
# Solo hace pruebas de analisis sintactico — no interpreta el codigo.
#
# MessiScript es un lenguaje esoterico donde el codigo son jugadas de futbol.
# Referencia: https://github.com/Erawaa/MessiScriptInterpreter

import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)
)))
sys.path.insert(0, ROOT)

from src.yapar.parser_reader        import YAParReader
from src.yapar.first_follow         import FirstFollowCalculator
from src.yapar.lalr_table           import LALRTable
from src.yapar.shift_reduce_parser  import build_lalr_parser

# COMANDOS OFICIALES DE MESSISCRIPT
# Los comandos se verifican en orden — los mas largos primero
# para evitar que "sigue messi" coincida antes que "siempre messi"
MESSI_COMMANDS = [
    ("la agarra messi",                 "CMD_INICIO"),
    ("la mueve messi por la derecha",   "CMD_DERECHA"),
    ("la mueve messi por la izquierda", "CMD_IZQUIERDA"),
    ("la pisa messi",                   "CMD_PISA"),
    ("le pega",                         "CMD_FIN"),      # gol = fin
    ("va messi",                        "CMD_VA"),
    ("juega messi",                     "CMD_JUEGA"),
    ("siempre messi",                   "CMD_SIEMPRE"),
    ("gambetea messi",                  "CMD_GAMBETEA"),
    ("sigue messi",                     "CMD_SIGUE"),
    ("vuelve messi",                    "CMD_VUELVE"),
    ("encara messi",                    "CMD_ENCARA"),
    ("ankara messi",                    "CMD_ANKARA"),
    ("corre messi",                     "CMD_CORRE"),
    ("amaga messi",                     "CMD_AMAGA"),
]

# Programas de ejemplo tomados directamente del repositorio oficial
EXAMPLE_PROGRAMS = [
    {
        'name': 'contar (del repositorio)',
        'description': 'Cuenta desde un valor hasta 0',
        'file': 'contar.messi',
        'code': """La agarra Messi.
        La mueve Messi por la derecha.
        Va Messi, moviendo la pelota con clase.
        Va Messi, jugando de forma increible, impecable, magistral e impresionante.
        La mueve Messi por la izquierda.
        Siempre Messi. Juega Messi.
        Sigue Messi.
        La mueve Messi por la derecha.
        La pisa Messi.
        La mueve Messi por la izquierda.
        Va Messi, con un futbol de calidad.
        Va Messi, como juega al futbol, senores.
        Juega Messi.
        Vuelve Messi.
        Le pega Messiiiii... gol!"""
    },
    {
        'name': '10 a 0 (del repositorio)',
        'description': 'Cuenta de 10 a 0',
        'file': '10_a_0.messi',
        'code': """La agarra Messi.
        La mueve Messi por la derecha.
        Va Messi, moviendo la pelota con clase.
        Va Messi, jugando de forma increible, impecable, magistral e impresionante.
        La mueve Messi por la izquierda.
        Va Messi, con una actuacion magistral, impecable y unica.
        Va Messi, con una jugada por la banda.
        Juega Messi.
        Sigue Messi.
        La mueve Messi por la derecha.
        La pisa Messi.
        La mueve Messi por la izquierda.
        Va Messi, con un futbol de calidad.
        Va Messi, como juega al futbol, senores.
        Juega Messi.
        Vuelve Messi.
        Le pega Messiiiii... gol!"""
    },
]

# TOKEN
class MessiToken:
    def __init__(self, type, value, line):
        self.type  = type
        self.value = value
        self.line  = line

    def __repr__(self):
        return f"MessiToken({self.type}, L{self.line})"

# TOKENIZADOR
def normalize(text):
    """
    Normaliza el texto: minusculas, sin acentos ni signos especiales.
    El interprete original hace exactamente esto antes de procesar.
    """
    text = text.lower()
    # Eliminar signos que el interprete ignora
    for char in ['\n', ',', ';', '?', '¿', '!', '¡', '(', ')']:
        text = text.replace(char, ' ')
    # Normalizar acentos para comparar con comandos
    replacements = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'ü': 'u', 'ñ': 'n',
    }
    for accented, plain in replacements.items():
        text = text.replace(accented, plain)
    return text


def tokenize_messi(source_code):
    """
    Tokeniza codigo MessiScript.

    El interprete original divide por '.' — cada punto separa un comando.
    Para cada fragmento:
    1. Normalizar (minusculas, sin signos)
    2. Buscar cual comando encaja al inicio del fragmento
    3. Si encaja CMD_VA, el resto del texto es CONTENIDO
    4. Si no encaja ningun comando, ignorar (texto decorativo)

    Retorna (tokens, errors).
    """
    tokens  = []
    errors  = []

    # Dividir por puntos, igual que el interprete original
    fragments = source_code.split('.')

    for line_num, fragment in enumerate(fragments, 1):
        fragment = fragment.strip()
        if not fragment:
            continue

        normalized = normalize(fragment)
        normalized = ' '.join(normalized.split())  # normalizar espacios

        matched = False

        for command_text, token_type in MESSI_COMMANDS:
            if normalized.startswith(command_text):
                tokens.append(MessiToken(token_type, fragment.strip(), line_num))

                # Si es CMD_VA, el contenido extra es el valor a asignar
                # Lo tokenizamos como CONTENIDO
                remainder = normalized[len(command_text):].strip()
                if token_type == 'CMD_VA' and remainder:
                    tokens.append(MessiToken('CONTENIDO', remainder, line_num))

                matched = True
                break

        # Si no coincidio con ningun comando, es texto decorativo
        # El interprete original simplemente lo ignora
        if not matched and normalized:
            # Solo reportamos error si parece un intento de comando
            # (contiene "messi") pero no es ninguno conocido
            if 'messi' in normalized:
                errors.append({
                    'fragment': fragment.strip(),
                    'line':     line_num,
                    'message':  (f"Linea {line_num}: fragmento con 'messi' "
                                 f"no reconocido como comando: '{fragment.strip()}'")
                })

    return tokens, errors


# PARSER MESSISCRIPT
class MessiParser:
    """
    Parser para MessiScript usando tabla LALR.

    Solo hace analisis sintactico — verifica que la estructura
    del programa es valida (empieza con CMD_INICIO, termina con CMD_FIN,
    y los comandos del medio son validos).

    No ejecuta el programa.
    """

    def __init__(self, yapar_path):
        print("Cargando gramatica MessiScript (LALR)...")

        self.reader     = YAParReader(yapar_path)
        self.calc       = FirstFollowCalculator(self.reader)
        self.lalr_table = LALRTable(self.reader, self.calc)
        self.parser     = build_lalr_parser(self.reader, self.lalr_table)

        print(f"  Producciones: {len(self.reader.grammar)}")
        print(f"  Estados LALR: {len(self.lalr_table.states)}")

        if self.lalr_table.has_conflicts():
            print(f"  Conflictos: {len(self.lalr_table.conflicts)}")
        else:
            print("  Sin conflictos LALR")

    def parse(self, source_code):
        """
        Parsea un programa MessiScript.

        Verifica:
        1. Que empieza con 'la agarra messi'
        2. Que termina con 'le pega messiiii... gol!'
        3. Que los comandos del medio son validos

        Retorna diccionario con:
        - source:    codigo original
        - tokens:    tokens encontrados
        - errors:    errores lexicos
        - accepted:  True si la estructura es valida
        - commands:  lista de comandos reconocidos
        - tree:      arbol sintactico
        """
        result = {
            'source':   source_code,
            'tokens':   [],
            'errors':   [],
            'accepted': False,
            'commands': [],
            'tree':     None,
            'paths':    []
        }

        tokens, lex_errors = tokenize_messi(source_code)
        result['tokens']  = tokens
        result['errors']  = lex_errors
        result['commands'] = [t.type for t in tokens]

        if not tokens:
            result['errors'].append({'message': 'Programa vacio'})
            return result

        parse_results      = self.parser.parse(tokens)
        result['paths']    = parse_results
        accepted_paths     = [r for r in parse_results if r['accepted']]
        result['accepted'] = len(accepted_paths) > 0

        if accepted_paths:
            result['tree'] = accepted_paths[0]['tree']

        return result

    def print_result(self, result):
        """Muestra el resultado del analisis."""
        print(f"\n{'='*55}")
        print("MessiScript Parser")
        print(f"{'='*55}")

        lines = result['source'].splitlines()
        print(f"Codigo ({len(lines)} lineas):")
        for i, line in enumerate(lines[:5], 1):
            print(f"  {i}. {line}")
        if len(lines) > 5:
            print(f"  ... ({len(lines)} lineas en total)")

        if result['errors']:
            print("\nErrores lexicos:")
            for err in result['errors']:
                print(f"  {err['message']}")

        print(f"\nComandos reconocidos ({len(result['tokens'])}):")
        for token in result['tokens']:
            print(f"  L{token.line}: {token.type}")

        if result['accepted']:
            print("\nPrograma MessiScript VALIDO")
        else:
            print("\nPrograma MessiScript INVALIDO")

            # Mostrar por que fue invalido
            types = result['commands']
            if not types:
                print("  -> Programa vacio")
            elif types[0] != 'CMD_INICIO':
                print(f"  -> No empieza con CMD_INICIO, empieza con {types[0]}")
            elif types[-1] != 'CMD_FIN':
                print(f"  -> No termina con CMD_FIN, termina con {types[-1]}")

        if len(result['paths']) > 1:
            accepted = sum(1 for r in result['paths'] if r['accepted'])
            print(f"\nCaminos paralelos: {len(result['paths'])} "
                  f"({accepted} aceptados)")