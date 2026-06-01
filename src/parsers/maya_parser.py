# Parser de Maya Yucateco.
# Usa nuestra infraestructura YAPar para el análisis sintáctico.
# Incluye traducción al español.
#
# El Maya Yucateco es un idioma maya hablado en Yucatán, México y Belice.
#
# Estructura gramatical simplificada:
#   - Preguntas: PAL_INTERROGATIVA + VERBO + SUJETO
#   - Oraciones: SUJETO + VERBO  o  VERBO + SUJETO


import sys
import os

# Asegurar que podemos importar desde src/
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)
)))
sys.path.insert(0, ROOT)

from src.yapar.parser_reader       import YAParReader
from src.yapar.first_follow        import FirstFollowCalculator
from src.yapar.lr0_automaton       import LR0Automaton
from src.yapar.slr_table           import SLRTable
from src.yapar.shift_reduce_parser import build_slr_parser

# VOCABULARIO MAYA YUCATECO

# Mapa de palabra maya → tipo de token
# El orden importa: palabras más largas primero
# para evitar que "kaaj" coincida antes que "kaajal"
MAYA_VOCABULARY = {
    # Palabras interrogativas
    'baax':    'BAAX',      # ¿qué?
    'tuux':    'TUUX',      # ¿dónde?
    'maax':    'MAAX',      # ¿quién?
    'bix':     'BIX',       # ¿cómo?
    'jayten':  'JAYTEN',    # ¿cuánto?

    # Verbos
    'yaan':    'YAAN',      # hay/existe/tiene
    'bin':     'BIN',       # va/irá
    'taal':    'TAAL',      # viene/vendrá
    'kaaj':    'KAAJ',      # empieza
    'kiimax':  'KIIMAX',    # gusta/alegra

    # Pronombres
    'in':      'IN',        # yo/mi (1ra persona)
    'ten':     'TEN',       # yo/me (énfasis)
    'u':       'PRON_U',    # él/ella/su (3ra persona)

    # Artículo definitivo
    'le':      'LE',        # el/la/los/las

    # Sufijo definitivo (marca el final del sintagma nominal)
    'o':       'SUFIJO_O',  # -o' (marca definitiva)

    # Preposición
    'ti':      'TI',        # en/a/de

    # Sustantivos comunes
    'kaajal':  'KAAJAL',    # pueblo/ciudad (más largo que kaaj → va primero)
    'paal':    'PAAL',      # niño/hijo
    'nah':     'NAH',       # casa
    'luum':    'LUUM',      # tierra/mundo
    'jaab':    'JAAB',      # año
    'ja':      'JA',        # agua

    # Puntuación
    '?':       'INTERROGACION',
    '.':       'PUNTO',
}

# Traducción de tipos de token al español
SPANISH_TRANSLATION = {
    'BAAX':          '¿qué',
    'TUUX':          '¿dónde',
    'MAAX':          '¿quién',
    'BIX':           '¿cómo',
    'JAYTEN':        '¿cuánto',
    'YAAN':          'hay',
    'BIN':           'va',
    'TAAL':          'viene',
    'KAAJ':          'empieza',
    'KIIMAX':        'gusta',
    'IN':            'mi',
    'TEN':           'yo',
    'PRON_U':        'su',
    'LE':            'el/la',
    'SUFIJO_O':      '',        # marcador, sin traducción
    'TI':            'en',
    'KAAJAL':        'pueblo',
    'PAAL':          'niño',
    'NAH':           'casa',
    'LUUM':          'tierra',
    'JAAB':          'año',
    'JA':            'agua',
    'INTERROGACION': '?',
    'PUNTO':         '.',
}

# Ejemplos de consultas válidas para mostrar al usuario
EXAMPLE_QUERIES = [
    ("baax yaan le nah o ?",
     "¿Qué hay en la casa?"),
    ("tuux bin le paal o ?",
     "¿Adónde va el niño?"),
    ("maax taal ti nah ?",
     "¿Quién viene a la casa?"),
    ("bix yaan le luum o ?",
     "¿Cómo está la tierra?"),
    ("in paal bin",
     "Mi hijo va."),
    ("yaan ja ti nah",
     "Hay agua en la casa."),
]

# TOKENIZADOR MAYA
class MayaToken:
    """Token del lenguaje Maya."""
    def __init__(self, type, value, position):
        self.type     = type
        self.value    = value
        self.position = position

    def __repr__(self):
        return f"MayaToken({self.type}, '{self.value}')"


def tokenize_maya(text):
    """
    Tokeniza una consulta en Maya Yucateco.

    Proceso:
    1. Convertir a minúsculas
    2. Separar palabras por espacios y puntuación
    3. Buscar cada palabra en el vocabulario
    4. Reportar palabras desconocidas como errores

    Retorna:
    - tokens: lista de MayaToken
    - errors: lista de palabras no reconocidas
    """
    tokens = []
    errors = []

    # Convertir a minúsculas para normalizar
    text = text.lower().strip()

    # Separar el texto en palabras y signos de puntuación
    # Primero separamos la puntuación del texto
    text = text.replace('?', ' ? ')
    text = text.replace('.', ' . ')

    words = text.split()

    for i, word in enumerate(words):
        if word in MAYA_VOCABULARY:
            token_type = MAYA_VOCABULARY[word]
            tokens.append(MayaToken(token_type, word, i))
        else:
            errors.append({
                'word':     word,
                'position': i,
                'message':  f"Palabra no reconocida: '{word}' en posición {i}"
            })

    return tokens, errors

# TRADUCTOR AL ESPAÑOL
def translate_to_spanish(tokens):
    """
    Traduce una lista de tokens Maya al español.

    Hace una traducción palabra por palabra y luego
    limpia el resultado para que sea legible.

    Ejemplo:
        [BAAX, YAAN, LE, NAH, SUFIJO_O, INTERROGACION]
        - "¿qué hay el/la casa ?"
        - limpiado: "¿Qué hay en la casa?"
    """
    parts = []

    for token in tokens:
        translation = SPANISH_TRANSLATION.get(token.type, token.value)
        # SUFIJO_O no tiene traducción, lo saltamos
        if translation:
            parts.append(translation)

    result = ' '.join(parts)

    # Limpiar el resultado
    result = result.replace(' ?', '?')
    result = result.replace(' .', '.')

    # Si empieza con ¿, asegurar que termine con ?
    if result.startswith('¿') and not result.endswith('?'):
        result += '?'

    # Capitalizar primera letra
    if result:
        result = result[0].upper() + result[1:]

    return result

# PARSER MAYA PRINCIPAL
class MayaParser:
    """
    Parser completo para Maya Yucateco.

    Combina:
    1. Tokenizador Maya personalizado
    2. Gramática en .yapar analizada con nuestra infraestructura
    3. Parser SLR con soporte para conflictos paralelos
    4. Traductor al español
    """

    def __init__(self, yapar_path):
        """
        Construye el parser cargando y procesando la gramática.
        """
        print("Cargando gramática Maya Yucateco...")

        # Cargar gramática
        self.reader = YAParReader(yapar_path)

        # Calcular FIRST y FOLLOW
        self.calc = FirstFollowCalculator(self.reader)

        # Construir autómata LR(0)
        self.lr0 = LR0Automaton(self.reader)

        # Construir tabla SLR
        self.slr_table = SLRTable(self.reader, self.lr0, self.calc)

        # Construir parser shift-reduce
        self.parser = build_slr_parser(self.reader, self.slr_table)

        print(f"  Gramática cargada: {len(self.reader.grammar)} producciones")
        print(f"  Estados LR(0): {len(self.lr0.states)}")

        if self.slr_table.has_conflicts():
            print(f"  Conflictos (manejados con paralelismo): "
                  f"{len(self.slr_table.conflicts)}")
        else:
            print("  Sin conflictos SLR")

    def parse(self, text):
        """
        Parsea una consulta en Maya Yucateco.

        Retorna un diccionario con:
        - input:       texto original
        - tokens:      tokens encontrados
        - errors:      errores léxicos
        - accepted:    si la gramática es válida
        - translation: traducción al español
        - tree:        árbol sintáctico (si fue aceptado)
        - paths:       caminos explorados (incluye paralelos)
        """
        result = {
            'input':       text,
            'tokens':      [],
            'errors':      [],
            'accepted':    False,
            'translation': '',
            'tree':        None,
            'paths':       []
        }

        # Paso 1: tokenizar
        tokens, lex_errors = tokenize_maya(text)
        result['tokens'] = tokens
        result['errors'] = lex_errors

        if lex_errors:
            return result

        if not tokens:
            result['errors'].append({'message': 'Consulta vacía'})
            return result

        # Paso 2: parsear con el parser SLR
        parse_results = self.parser.parse(tokens)
        result['paths'] = parse_results

        # Paso 3: determinar si fue aceptado
        accepted_paths = [r for r in parse_results if r['accepted']]
        result['accepted'] = len(accepted_paths) > 0

        # Paso 4: traducir al español
        result['translation'] = translate_to_spanish(tokens)

        # Paso 5: guardar el árbol del primer camino aceptado
        if accepted_paths:
            result['tree'] = accepted_paths[0]['tree']

        return result

    def print_result(self, result):
        """Imprime el resultado de forma legible."""
        print(f"\n{'='*50}")
        print(f"Consulta Maya: {result['input']}")
        print(f"{'='*50}")

        if result['errors']:
            print("Errores léxicos:")
            for err in result['errors']:
                print(f"   {err['message']}")
            return

        print(f"\nTokens: {[t.type for t in result['tokens']]}")
        print(f"Traducción al español: {result['translation']}")

        if result['accepted']:
            print("Consulta VÁLIDA según la gramática Maya")
            if result['tree']:
                print("\nÁrbol sintáctico:")
                print(result['tree'].to_string(indent=1))
        else:
            print("Consulta INVÁLIDA — no sigue la gramática")

        if len(result['paths']) > 1:
            print(f"Se exploraron {len(result['paths'])} "
                  f"caminos paralelos")