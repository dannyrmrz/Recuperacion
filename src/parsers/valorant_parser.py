# Parser para ValorantScript — lenguaje inspirado en Valorant.
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

# VOCABULARIO
VALO_KEYWORDS = {
    'ability': 'ABILITY',
    'credits': 'CREDITS',
    'plant':   'PLANT',
    'spike':   'SPIKE',
    'defuse':  'DEFUSE',
    'round':   'ROUND',
    'callout': 'CALLOUT',
    'gg':      'GG',
    'clutch':  'CLUTCH',
    'whiff':   'WHIFF',
}

VALO_SYMBOLS = {
    '+': 'PLUS',
    '-': 'MINUS',
    '*': 'TIMES',
    '/': 'DIVIDE',
    '>': 'GT',
    '<': 'LT',
    '=': 'EQUALS',
    '(': 'LPAREN',
    ')': 'RPAREN',
}

EXAMPLE_PROGRAMS = [
    {
        'name': 'Hola Valorant',
        'description': 'Variable y callout básico',
        'code': (
            '// Programa básico\n'
            'ability credits kills plant 10\n'
            'callout kills'
        )
    },
    {
        'name': 'Spike condicional',
        'description': 'If-else con spike y defuse',
        'code': (
            'ability credits score plant 75\n'
            'spike ( score > 50 ) gg\n'
            '    callout score\n'
            'defuse gg\n'
            '    callout 0\n'
            'gg'
        )
    },
    {
        'name': 'Round loop',
        'description': 'Bucle con round',
        'code': (
            'ability credits round_num plant 3\n'
            'round ( round_num > 0 ) gg\n'
            '    callout round_num\n'
            '    round_num plant round_num - 1\n'
            'gg'
        )
    },
    {
        'name': 'Partido completo',
        'description': 'Variables, condicional y bucle',
        'code': (
            'ability credits kills plant 0\n'
            'ability credits rondas plant 5\n'
            'round ( rondas > 0 ) gg\n'
            '    kills plant kills + 1\n'
            '    rondas plant rondas - 1\n'
            'gg\n'
            'spike ( kills > 3 ) gg\n'
            '    callout kills\n'
            'defuse gg\n'
            '    callout 0\n'
            'gg'
        )
    },
]

# TOKEN
class ValoToken:
    def __init__(self, type, value, line, column):
        self.type   = type
        self.value  = value
        self.line   = line
        self.column = column

    def __repr__(self):
        return f"ValoToken({self.type}, '{self.value}', L{self.line}:C{self.column})"

# TOKENIZADOR
def tokenize_valorant(source_code):
    """Tokeniza código ValorantScript. Retorna (tokens, errors)."""
    tokens = []
    errors = []
    pos = line = 0
    line = 1
    column = 1

    while pos < len(source_code):
        char = source_code[pos]

        if char == '\n':
            line += 1; column = 1; pos += 1
            continue

        if char in ' \t\r':
            column += 1; pos += 1
            continue

        # Comentarios //
        if char == '/' and pos + 1 < len(source_code) and source_code[pos+1] == '/':
            while pos < len(source_code) and source_code[pos] != '\n':
                pos += 1
            continue

        # Enteros
        if char.isdigit():
            start_col = column
            number = ''
            while pos < len(source_code) and source_code[pos].isdigit():
                number += source_code[pos]; pos += 1; column += 1
            tokens.append(ValoToken('INT', number, line, start_col))
            continue

        # Keywords e identificadores
        if char.isalpha() or char == '_':
            start_col = column
            word = ''
            while pos < len(source_code) and (source_code[pos].isalnum() or source_code[pos] == '_'):
                word += source_code[pos]; pos += 1; column += 1
            tokens.append(ValoToken(VALO_KEYWORDS.get(word, 'ID'), word, line, start_col))
            continue

        # Símbolos
        if char in VALO_SYMBOLS:
            tokens.append(ValoToken(VALO_SYMBOLS[char], char, line, column))
            pos += 1; column += 1
            continue

        # Error
        errors.append({
            'char': char, 'line': line, 'column': column,
            'message': f"Carácter no reconocido '{char}' en L{line}:C{column}"
        })
        pos += 1; column += 1

    return tokens, errors

# PARSER VALORANTSCRIPT
class ValorantParser:
    """
    Parser ValorantScript usando tabla LALR.

    LALR es más preciso que SLR porque los lookaheads
    son específicos por estado — reduce conflictos falsos
    que SLR reportaría incorrectamente.
    """

    def __init__(self, yapar_path):
        print("Cargando gramática ValorantScript (LALR)...")

        self.reader = YAParReader(yapar_path)
        self.calc   = FirstFollowCalculator(self.reader)

        # LALR construye LR(1) internamente y fusiona estados con mismo núcleo
        self.lalr_table = LALRTable(self.reader, self.calc)
        self.parser     = build_lalr_parser(self.reader, self.lalr_table)

        print(f"  Producciones: {len(self.reader.grammar)}")
        print(f"  Estados LR(1) antes de fusionar: "
              f"{len(self.lalr_table.lr1_states)}")
        print(f"  Estados LALR después de fusionar: "
              f"{len(self.lalr_table.states)}")

        if self.lalr_table.has_conflicts():
            print(f"  Conflictos (resueltos con paralelismo): "
                  f"{len(self.lalr_table.conflicts)}")
        else:
            print("  Sin conflictos LALR")

    def parse(self, source_code):
        """Parsea código ValorantScript."""
        result = {
            'source':   source_code,
            'tokens':   [],
            'errors':   [],
            'accepted': False,
            'tree':     None,
            'paths':    []
        }

        tokens, lex_errors = tokenize_valorant(source_code)
        result['tokens'] = tokens
        result['errors'] = lex_errors

        if lex_errors or not tokens:
            if not tokens and not lex_errors:
                result['errors'].append({'message': 'Programa vacío'})
            return result

        parse_results      = self.parser.parse(tokens)
        result['paths']    = parse_results
        accepted_paths     = [r for r in parse_results if r['accepted']]
        result['accepted'] = len(accepted_paths) > 0

        if accepted_paths:
            result['tree'] = accepted_paths[0]['tree']

        return result

    def print_result(self, result):
        """Muestra el resultado del parsing."""
        print(f"\n{'='*55}")
        print("ValorantScript Parser (LALR)")
        print(f"{'='*55}")
        print(f"Código:\n{result['source']}")

        if result['errors']:
            print("\n❌ Errores léxicos:")
            for err in result['errors']:
                print(f"  {err['message']}")
            return

        print(f"\nTokens: {[t.type for t in result['tokens']]}")

        if result['accepted']:
            print("\n Sintaxis VÁLIDA — gg")
            if result['tree']:
                print("\nÁrbol sintáctico:")
                print(result['tree'].to_string(indent=1))
        else:
            print("\n Sintaxis INVÁLIDA — whiff")

        if len(result['paths']) > 1:
            accepted = sum(1 for r in result['paths'] if r['accepted'])
            print(f"\n Caminos paralelos: {len(result['paths'])} "
                  f"({accepted} aceptados)")