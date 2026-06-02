# Parser para el lenguaje esoterico COW.
# COW tiene exactamente 12 instrucciones — las unicas palabras validas.
# Un programa valido es cualquier secuencia no vacia de esas instrucciones.
#
# Las instrucciones son case-sensitive: moo != MOO != MoO
# Referencia: http://www.bigzaphod.org/cow/

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


# Las 12 instrucciones de COW mapeadas a sus tokens
# Los nombres de token usan prefijo INSTR_ para evitar
# conflictos con palabras reservadas del parser
COW_INSTRUCTIONS = {
    'moo': 'INSTR_moo',   # si bloque es 0, saltar adelante hasta MOO
    'mOo': 'INSTR_mOo',   # decrementar puntero de memoria
    'moO': 'INSTR_moO',   # incrementar puntero de memoria
    'mOO': 'INSTR_mOO',   # ejecutar bloque actual como instruccion COW
    'Moo': 'INSTR_Moo',   # leer caracter de stdin
    'MOo': 'INSTR_MOo',   # decrementar bloque actual de memoria
    'MoO': 'INSTR_MoO',   # incrementar bloque actual de memoria
    'MOO': 'INSTR_MOO',   # si bloque no es 0, retroceder hasta moo
    'OOO': 'INSTR_OOO',   # poner bloque actual en 0
    'MMM': 'INSTR_MMM',   # guardar/recuperar bloque en registro
    'OOM': 'INSTR_OOM',   # imprimir bloque como entero
    'oom': 'INSTR_oom',   # leer entero de stdin al bloque actual
}

# Descripcion de cada instruccion para mostrar en el output
COW_DESCRIPTIONS = {
    'moo': 'si bloque es 0, saltar adelante hasta MOO',
    'mOo': 'decrementar puntero de memoria',
    'moO': 'incrementar puntero de memoria',
    'mOO': 'ejecutar bloque actual como instruccion COW',
    'Moo': 'leer caracter de stdin (o imprimir 0 si bloque es 0)',
    'MOo': 'decrementar bloque actual de memoria',
    'MoO': 'incrementar bloque actual de memoria',
    'MOO': 'si bloque no es 0, retroceder hasta moo',
    'OOO': 'poner bloque actual en 0',
    'MMM': 'guardar/recuperar bloque en registro',
    'OOM': 'imprimir bloque actual como entero',
    'oom': 'leer entero de stdin al bloque actual',
}

# Programas de ejemplo
EXAMPLE_PROGRAMS = [
    {
        'name': 'Incrementar y mostrar',
        'description': 'Incrementa memoria tres veces e imprime como entero',
        'code': 'MoO MoO MoO OOM'
    },
    {
        'name': 'Limpiar y leer',
        'description': 'Limpia bloque, lee entero desde stdin e imprime',
        'code': 'OOO oom OOM'
    },
    {
        'name': 'Loop basico',
        'description': 'Incrementa 3 veces, luego decrementa en loop hasta 0',
        'code': 'MoO MoO MoO moo MOo MOO OOM'
    },
    {
        'name': 'Todas las instrucciones',
        'description': 'Usa las 12 instrucciones en secuencia',
        'code': 'moo mOo moO mOO Moo MOo MoO MOO OOO MMM OOM oom'
    },
]

# TOKEN
class COWToken:
    """
    Token del lenguaje COW.

    type:     nombre del token (ej: 'INSTR_moo')
    value:    la instruccion original (ej: 'moo')
    position: posicion en la lista de palabras
    """

    def __init__(self, type, value, position):
        self.type     = type
        self.value    = value
        self.position = position

    def __repr__(self):
        return f"COWToken({self.type}, pos={self.position})"

# TOKENIZADOR
def tokenize_cow(source_code):
    """
    Tokeniza codigo COW.

    Las instrucciones estan separadas por espacios o saltos de linea.
    Solo se reconocen las 12 instrucciones oficiales.
    Las instrucciones son case-sensitive: 'moo' y 'MOO' son distintas.
    Las lineas que empiezan con // se ignoran como comentarios.

    Retorna (tokens, errors).
    """
    tokens = []
    errors = []

    words = source_code.split()

    for i, word in enumerate(words):
        # Ignorar comentarios
        if word.startswith('//'):
            break

        if word in COW_INSTRUCTIONS:
            token_type = COW_INSTRUCTIONS[word]
            tokens.append(COWToken(token_type, word, i))
        else:
            errors.append({
                'word':     word,
                'position': i,
                'message':  (f"Instruccion no reconocida: '{word}' "
                             f"en posicion {i}. "
                             f"Las instrucciones validas son: "
                             f"{list(COW_INSTRUCTIONS.keys())}")
            })

    return tokens, errors

# PARSER COW
class COWParser:
    """
    Parser para el lenguaje COW usando tabla LALR.

    Verifica que un programa COW consiste unicamente
    de las 12 instrucciones validas en cualquier secuencia.
    No ejecuta el programa — solo hace analisis sintactico.
    """

    def __init__(self, yapar_path):
        print("Cargando gramatica COW (LALR)...")

        self.reader     = YAParReader(yapar_path)
        self.calc       = FirstFollowCalculator(self.reader)
        self.lalr_table = LALRTable(self.reader, self.calc)
        self.parser     = build_lalr_parser(self.reader, self.lalr_table)

        print(f"  Instrucciones reconocidas: {len(COW_INSTRUCTIONS)}")
        print(f"  Producciones: {len(self.reader.grammar)}")
        print(f"  Estados LR(1) antes de fusionar: "
              f"{len(self.lalr_table.lr1_states)}")
        print(f"  Estados LALR despues de fusionar: "
              f"{len(self.lalr_table.states)}")

        if self.lalr_table.has_conflicts():
            print(f"  Conflictos (manejados con paralelismo): "
                  f"{len(self.lalr_table.conflicts)}")
        else:
            print("  Sin conflictos LALR")

    def parse(self, source_code):
        """
        Parsea un programa COW.

        Retorna diccionario con:
        - source:            codigo original
        - tokens:            instrucciones encontradas
        - errors:            errores lexicos
        - accepted:          True si el programa es valido
        - instruction_count: numero de instrucciones reconocidas
        - tree:              arbol sintactico
        - paths:             caminos del parser paralelo
        """
        result = {
            'source':            source_code,
            'tokens':            [],
            'errors':            [],
            'accepted':          False,
            'instruction_count': 0,
            'tree':              None,
            'paths':             []
        }

        tokens, lex_errors = tokenize_cow(source_code)
        result['tokens']            = tokens
        result['errors']            = lex_errors
        result['instruction_count'] = len(tokens)

        if lex_errors:
            return result

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
        print(f"\n{'='*50}")
        print("COW Parser")
        print(f"{'='*50}")
        print(f"Codigo: {result['source']}")

        if result['errors']:
            print("\nErrores lexicos:")
            for err in result['errors']:
                print(f"  {err['message']}")
            return

        print(f"\nInstrucciones reconocidas ({result['instruction_count']}):")
        for token in result['tokens']:
            desc = COW_DESCRIPTIONS.get(token.value, '')
            print(f"  {token.value:5} -> {desc}")

        if result['accepted']:
            print("\nPrograma COW VALIDO")
        else:
            print("\nPrograma COW INVALIDO")

        if len(result['paths']) > 1:
            accepted = sum(1 for r in result['paths'] if r['accepted'])
            print(f"\nCaminos paralelos: {len(result['paths'])} "
                  f"({accepted} aceptados)")