# Parser de Maya Yucateco.
# Usa LALR 

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

# VOCABULARIO MAYA YUCATECO
MAYA_VOCABULARY = {
    # Palabras interrogativas
    'baax':   'BAAX',
    'tuux':   'TUUX',
    'maax':   'MAAX',
    'bix':    'BIX',
    'jayten': 'JAYTEN',
    # Verbos
    'yaan':   'YAAN',
    'bin':    'BIN',
    'taal':   'TAAL',
    'kaaj':   'KAAJ',
    'kiimax': 'KIIMAX',
    # Pronombres
    'in':     'IN',
    'ten':    'TEN',
    'u':      'PRON_U',
    # Artículo
    'le':     'LE',
    # Sufijo definitivo
    'o':      'SUFIJO_O',
    # Preposición
    'ti':     'TI',
    # Sustantivos (kaajal antes que kaaj para evitar match incorrecto)
    'kaajal': 'KAAJAL',
    'paal':   'PAAL',
    'nah':    'NAH',
    'luum':   'LUUM',
    'jaab':   'JAAB',
    'ja':     'JA',
    # Puntuación
    '?':      'INTERROGACION',
    '.':      'PUNTO',
}

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
    'SUFIJO_O':      '',
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

EXAMPLE_QUERIES = [
    ("baax yaan le nah o ?",   "¿Qué hay en la casa?"),
    ("tuux bin le paal o ?",   "¿Adónde va el niño?"),
    ("maax taal ti nah ?",     "¿Quién viene a la casa?"),
    ("bix yaan le luum o ?",   "¿Cómo está la tierra?"),
    ("in paal bin",             "Mi hijo va."),
    ("yaan ja ti nah",          "Hay agua en la casa."),
]
# TOKEN
class MayaToken:
    def __init__(self, type, value, position):
        self.type     = type
        self.value    = value
        self.position = position

    def __repr__(self):
        return f"MayaToken({self.type}, '{self.value}')"

# TOKENIZADOR
def tokenize_maya(text):
    """
    Tokeniza una consulta en Maya Yucateco.
    Retorna (tokens, errors).
    """
    tokens = []
    errors = []

    text = text.lower().strip()
    text = text.replace('?', ' ? ')
    text = text.replace('.', ' . ')

    for i, word in enumerate(text.split()):
        if word in MAYA_VOCABULARY:
            tokens.append(MayaToken(MAYA_VOCABULARY[word], word, i))
        else:
            errors.append({
                'word':     word,
                'position': i,
                'message':  f"Palabra no reconocida: '{word}' en posición {i}"
            })

    return tokens, errors

# TRADUCTOR
def translate_to_spanish(tokens):
    """Traduce tokens Maya al español."""
    parts = []
    for token in tokens:
        translation = SPANISH_TRANSLATION.get(token.type, token.value)
        if translation:
            parts.append(translation)

    result = ' '.join(parts)
    result = result.replace(' ?', '?').replace(' .', '.')

    if result.startswith('¿') and not result.endswith('?'):
        result += '?'

    if result:
        result = result[0].upper() + result[1:]

    return result

# PARSER MAYA
class MayaParser:
    """
    Parser Maya Yucateco usando tabla LALR.

    LALR es más preciso que SLR porque usa lookaheads
    específicos por estado en vez de FOLLOW global —
    esto reduce conflictos falsos.
    """

    def __init__(self, yapar_path):
        print("Cargando gramática Maya Yucateco (LALR)...")

        self.reader = YAParReader(yapar_path)
        self.calc   = FirstFollowCalculator(self.reader)

        # LALR — construye LR(1) internamente y fusiona estados
        # No necesita LR0Automaton separado como SLR
        self.lalr_table = LALRTable(self.reader, self.calc)
        self.parser     = build_lalr_parser(self.reader, self.lalr_table)

        print(f"  Producciones: {len(self.reader.grammar)}")
        print(f"  Estados LR(1) antes de fusionar: "
              f"{len(self.lalr_table.lr1_states)}")
        print(f"  Estados LALR después de fusionar: "
              f"{len(self.lalr_table.states)}")

        if self.lalr_table.has_conflicts():
            print(f"  Conflictos (manejados con paralelismo): "
                  f"{len(self.lalr_table.conflicts)}")
        else:
            print("  Sin conflictos LALR")

    def parse(self, text):
        """Parsea una consulta en Maya Yucateco."""
        result = {
            'input':       text,
            'tokens':      [],
            'errors':      [],
            'accepted':    False,
            'translation': '',
            'tree':        None,
            'paths':       []
        }

        tokens, lex_errors = tokenize_maya(text)
        result['tokens'] = tokens
        result['errors'] = lex_errors

        if lex_errors or not tokens:
            if not tokens and not lex_errors:
                result['errors'].append({'message': 'Consulta vacía'})
            return result

        parse_results      = self.parser.parse(tokens)
        result['paths']    = parse_results
        accepted_paths     = [r for r in parse_results if r['accepted']]
        result['accepted'] = len(accepted_paths) > 0
        result['translation'] = translate_to_spanish(tokens)

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
                print(f"  {err['message']}")
            return

        print(f"Tokens: {[t.type for t in result['tokens']]}")
        print(f"Traducción: {result['translation']}")

        if result['accepted']:
            print("Consulta VÁLIDA")
            if result['tree']:
                print("\nÁrbol sintáctico:")
                print(result['tree'].to_string(indent=1))
        else:
            print("Consulta INVÁLIDA")

        if len(result['paths']) > 1:
            print(f"Caminos paralelos explorados: {len(result['paths'])}")