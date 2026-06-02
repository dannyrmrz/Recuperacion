# src/gui/app.py
#
# Backend Flask para el IDE web de YALex + YAPar.

import sys
import os
import tempfile
import traceback

from flask import Flask, request, jsonify, send_from_directory

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)
)))
sys.path.insert(0, ROOT)

app = Flask(__name__, static_folder='static')


# ─────────────────────────────────────────────
# SERIALIZADORES
# ─────────────────────────────────────────────

def tree_to_dict(node):
    if node is None:
        return None
    return {
        'name':     node.symbol,
        'value':    node.token_value or '',
        'children': [tree_to_dict(c) for c in node.children]
    }


def automaton_to_dict(automaton):
    nodes = []
    edges = []
    for state in automaton.states:
        items = [str(item) for item in sorted(state.items, key=str)]
        nodes.append({'id': state.id, 'items': items})
        for symbol, dest in state.transitions.items():
            edges.append({'from': state.id, 'to': dest.id, 'label': symbol})
    return {
        'nodes':   nodes,
        'edges':   edges,
        'initial': automaton.initial_state.id,
        'type':    'LR(0)'
    }


def lr1_states_to_dict(lr1_states):
    nodes = []
    edges = []
    for state in lr1_states:
        items = [str(item) for item in sorted(state.items, key=str)]
        nodes.append({'id': state.id, 'items': items})
        for symbol, dest in state.transitions.items():
            edges.append({'from': state.id, 'to': dest.id, 'label': symbol})
    return {
        'nodes':   nodes,
        'edges':   edges,
        'initial': lr1_states[0].id if lr1_states else 0,
        'type':    'LR(1)'
    }


def serialize_action_table(action_table):
    result = {}
    for state_id, actions in action_table.items():
        result[str(state_id)] = {}
        for terminal, action in actions.items():
            if isinstance(action, list):
                result[str(state_id)][terminal] = [
                    {'type': a[0], 'value': a[1]} for a in action
                ]
            else:
                result[str(state_id)][terminal] = {
                    'type': action[0], 'value': action[1]
                }
    return result


def write_temp(content, suffix):
    f = tempfile.NamedTemporaryFile(
        mode='w', suffix=suffix, delete=False, encoding='utf-8'
    )
    f.write(content)
    f.close()
    return f.name


def filter_tokens(tokens):
    """
    Filtra tokens que no deben llegar al parser:
    - EOF: marcador de fin agregado por el scanner
    - '' (string vacio): espacios ignorados que pasaron el filtro

    Sin este filtro el parser falla porque recibe tokens inesperados.
    """
    return [
        t for t in tokens
        if hasattr(t, 'type') and t.type not in ('EOF', '', None)
    ]


# ─────────────────────────────────────────────
# RUTAS
# ─────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/api/parse-yalex', methods=['POST'])
def parse_yalex():
    try:
        content    = request.json.get('content', '')
        yalex_path = write_temp(content, '.yalex')

        from src.yalex.lexer import YALexReader
        reader = YALexReader(yalex_path)

        return jsonify({
            'success':     True,
            'definitions': dict(reader.definitions),
            'rules':       [(p, t) for p, t in reader.rules],
            'rules_count': len(reader.rules),
            'def_count':   len(reader.definitions),
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/parse-yapar', methods=['POST'])
def parse_yapar():
    try:
        content    = request.json.get('content', '')
        yapar_path = write_temp(content, '.yapar')

        from src.yapar.parser_reader import YAParReader
        reader = YAParReader(yapar_path)

        return jsonify({
            'success':       True,
            'tokens':        reader.tokens,
            'grammar':       [(nt, syms) for nt, syms in reader.grammar],
            'start_symbol':  reader.start_symbol,
            'non_terminals': sorted(list(reader.get_non_terminals())),
            'productions':   len(reader.grammar),
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/first-follow', methods=['POST'])
def get_first_follow():
    try:
        yapar_content = request.json.get('yapar', '')
        yapar_path    = write_temp(yapar_content, '.yapar')

        from src.yapar.parser_reader import YAParReader
        from src.yapar.first_follow  import FirstFollowCalculator

        reader = YAParReader(yapar_path)
        calc   = FirstFollowCalculator(reader)

        first_dict  = {}
        follow_dict = {}

        for nt in reader.get_non_terminals():
            first_set  = calc.get_first(nt)
            follow_set = calc.get_follow(nt)
            first_list = sorted(first_set - {'ε'}) + (['ε'] if 'ε' in first_set else [])
            first_dict[nt]  = first_list
            follow_dict[nt] = sorted(follow_set)

        return jsonify({
            'success': True,
            'first':   first_dict,
            'follow':  follow_dict,
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/tables', methods=['POST'])
def get_tables():
    try:
        yapar_content = request.json.get('yapar', '')
        method        = request.json.get('method', 'all')
        yapar_path    = write_temp(yapar_content, '.yapar')

        from src.yapar.parser_reader import YAParReader
        from src.yapar.first_follow  import FirstFollowCalculator
        from src.yapar.lr0_automaton import LR0Automaton
        from src.yapar.slr_table     import SLRTable
        from src.yapar.lalr_table    import LALRTable
        from src.yapar.ll1_table     import LL1Table

        reader = YAParReader(yapar_path)
        calc   = FirstFollowCalculator(reader)
        result = {'success': True}

        if method in ('slr', 'all'):
            lr0 = LR0Automaton(reader)
            slr = SLRTable(reader, lr0, calc)
            result['slr'] = {
                'action':        serialize_action_table(slr.action_table),
                'goto':          {str(k): v for k, v in slr.goto_table.items()},
                'conflicts':     slr.conflicts,
                'terminals':     sorted(slr.terminals),
                'non_terminals': sorted(slr.non_terminals),
                'states_count':  len(slr.action_table),
            }

        if method in ('lalr', 'all'):
            lalr = LALRTable(reader, calc)
            result['lalr'] = {
                'action':            serialize_action_table(lalr.action_table),
                'goto':              {str(k): v for k, v in lalr.goto_table.items()},
                'conflicts':         lalr.conflicts,
                'terminals':         sorted(lalr.terminals),
                'non_terminals':     sorted(lalr.non_terminals),
                'lr1_states_count':  len(lalr.lr1_states),
                'lalr_states_count': len(lalr.states),
            }

        if method in ('ll1', 'all'):
            ll1 = LL1Table(reader, calc)
            table_serialized = {}
            for nt, terminals in ll1.table.items():
                table_serialized[nt] = {}
                for terminal, production in terminals.items():
                    if production:
                        table_serialized[nt][terminal] = {
                            'nt':      production[0],
                            'symbols': production[1]
                        }
            result['ll1'] = {
                'table':         table_serialized,
                'conflicts':     ll1.conflicts,
                'terminals':     sorted(reader.get_terminals()),
                'non_terminals': sorted(reader.get_non_terminals()),
                'is_ll1':        ll1.is_ll1(),
            }

        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success':   False,
            'error':     str(e),
            'traceback': traceback.format_exc()
        })


@app.route('/api/automaton', methods=['POST'])
def get_automaton():
    try:
        yapar_content  = request.json.get('yapar', '')
        automaton_type = request.json.get('type', 'lr0')
        yapar_path     = write_temp(yapar_content, '.yapar')

        from src.yapar.parser_reader import YAParReader
        from src.yapar.first_follow  import FirstFollowCalculator
        from src.yapar.lr0_automaton import LR0Automaton
        from src.yapar.lalr_table    import LALRTable

        reader = YAParReader(yapar_path)
        calc   = FirstFollowCalculator(reader)

        if automaton_type == 'lr0':
            lr0  = LR0Automaton(reader)
            data = automaton_to_dict(lr0)
        else:
            lalr = LALRTable(reader, calc)
            data = lr1_states_to_dict(lalr.lr1_states)

        return jsonify({'success': True, 'automaton': data})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        code          = request.json.get('code', '')
        method        = request.json.get('method', 'lalr')
        yapar_content = request.json.get('yapar', '')
        yalex_content = request.json.get('yalex', '')

        yapar_path = write_temp(yapar_content, '.yapar')

        from src.yapar.parser_reader       import YAParReader
        from src.yapar.first_follow        import FirstFollowCalculator
        from src.yapar.lr0_automaton       import LR0Automaton
        from src.yapar.slr_table           import SLRTable
        from src.yapar.lalr_table          import LALRTable
        from src.yapar.ll1_table           import LL1Table, LL1Parser
        from src.yapar.shift_reduce_parser import build_slr_parser, build_lalr_parser

        reader = YAParReader(yapar_path)
        calc   = FirstFollowCalculator(reader)

        # ── Analisis lexico ───────────────────────────────────────────────
        tokens_data = []
        lex_errors  = []
        raw_tokens  = []

        if yalex_content:
            yalex_path = write_temp(yalex_content, '.yalex')

            from src.yalex.lexer   import YALexReader
            from src.yalex.scanner import build_scanner_from_yalex

            lex_reader = YALexReader(yalex_path)
            scanner    = build_scanner_from_yalex(lex_reader)
            all_tokens, errs = scanner.tokenize(code)

            # Datos para mostrar al usuario (sin EOF)
            tokens_data = [
                {'type': t.type, 'value': t.value,
                 'line': t.line, 'column': t.column}
                for t in all_tokens
                if t.type not in ('EOF', '', None)
            ]

            lex_errors = [
                {'type': 'lexical', 'message': e['message'],
                 'line': e.get('line', 0), 'column': e.get('column', 0)}
                for e in errs
            ]

            # ─── FIX: filtrar EOF y tokens vacios antes de pasar al parser ───
            # Sin este filtro el parser recibe 'EOF' como token y falla
            # porque el estado final de la tabla no tiene accion para 'EOF'
            raw_tokens = filter_tokens(all_tokens)

        else:
            # Sin yalex — usar palabras directamente
            words = code.split()
            raw_tokens  = words
            tokens_data = [
                {'type': w, 'value': w, 'line': 0, 'column': 0}
                for w in words
            ]

        # ── Analisis sintactico ───────────────────────────────────────────
        syn_errors    = []
        parse_results = []

        if method == 'slr':
            lr0    = LR0Automaton(reader)
            slr    = SLRTable(reader, lr0, calc)
            parser = build_slr_parser(reader, slr)
            parse_results = parser.parse(raw_tokens)

            syn_errors = [
                {
                    'type':          'conflict',
                    'conflict_type': c['type'],
                    'message':       (f"Conflicto {c['type']} en estado "
                                      f"{c['state']} con token '{c['terminal']}'"),
                }
                for c in slr.conflicts
            ]

        elif method == 'lalr':
            lalr   = LALRTable(reader, calc)
            parser = build_lalr_parser(reader, lalr)
            parse_results = parser.parse(raw_tokens)

            syn_errors = [
                {
                    'type':          'conflict',
                    'conflict_type': c['type'],
                    'message':       (f"Conflicto {c['type']} en estado "
                                      f"{c['state']} con token '{c['terminal']}'"),
                }
                for c in lalr.conflicts
            ]

        elif method == 'll1':
            ll1    = LL1Table(reader, calc)
            parser = LL1Parser(ll1)

            token_types     = [t.type if hasattr(t, 'type') else t
                               for t in raw_tokens]
            accepted, steps = parser.parse(token_types)
            parse_results   = [
                {'accepted': accepted, 'steps': steps,
                 'tree': None, 'path_id': 1}
            ]

            syn_errors = [
                {
                    'type':          'conflict',
                    'conflict_type': 'LL(1)',
                    'message':       (f"Conflicto LL(1) en "
                                      f"[{c['non_terminal']}][{c['terminal']}]"),
                }
                for c in ll1.conflicts
            ]

        accepted   = any(r['accepted'] for r in parse_results)
        tree_data  = None
        paths_data = []

        for r in parse_results:
            steps = r.get('steps', [])
            path  = {
                'path_id':     r['path_id'],
                'accepted':    r['accepted'],
                'steps_count': len(steps),
                'last_steps':  [
                    {'action': s.get('action', ''), 'conflict': s.get('conflict', False)}
                    for s in steps[-6:]
                ]
            }
            if r['accepted'] and r.get('tree') and tree_data is None:
                tree_data = tree_to_dict(r['tree'])
            paths_data.append(path)

        return jsonify({
            'success':        True,
            'accepted':       accepted,
            'method':         method,
            'tokens':         tokens_data,
            'lex_errors':     lex_errors,
            'syn_errors':     syn_errors,
            'tree':           tree_data,
            'paths':          paths_data,
            'paths_count':    len(parse_results),
            'accepted_paths': sum(1 for r in parse_results if r['accepted']),
        })

    except Exception as e:
        return jsonify({
            'success':   False,
            'error':     str(e),
            'traceback': traceback.format_exc()
        })


@app.route('/api/language', methods=['POST'])
def parse_language():
    try:
        language = request.json.get('language', '')
        code     = request.json.get('code', '')
        r        = {}

        if language == 'maya':
            from src.parsers.maya_parser import MayaParser
            yapar_path = os.path.join(ROOT, 'examples', 'maya.yapar')
            parser = MayaParser(yapar_path)
            result = parser.parse(code)
            r = {
                'accepted':       result['accepted'],
                'tokens':         [{'type': t.type, 'value': t.value}
                                   for t in result['tokens']],
                'errors':         result['errors'],
                'translation':    result['translation'],
                'tree':           tree_to_dict(result['tree']),
                'paths_count':    len(result['paths']),
                'accepted_paths': sum(1 for p in result['paths'] if p['accepted']),
            }

        elif language == 'valorant':
            from src.parsers.valorant_parser import ValorantParser
            yapar_path = os.path.join(ROOT, 'examples', 'valorant.yapar')
            parser = ValorantParser(yapar_path)
            result = parser.parse(code)
            r = {
                'accepted':       result['accepted'],
                'tokens':         [{'type': t.type, 'value': t.value,
                                    'line': t.line, 'column': t.column}
                                   for t in result['tokens']],
                'errors':         result['errors'],
                'tree':           tree_to_dict(result['tree']),
                'paths_count':    len(result['paths']),
                'accepted_paths': sum(1 for p in result['paths'] if p['accepted']),
            }

        elif language == 'cow':
            from src.parsers.cow_parser import COWParser
            yapar_path = os.path.join(ROOT, 'examples', 'cow.yapar')
            parser = COWParser(yapar_path)
            result = parser.parse(code)
            r = {
                'accepted':         result['accepted'],
                'tokens':           [{'type': t.type, 'value': t.value}
                                     for t in result['tokens']],
                'errors':           result['errors'],
                'instruction_count': result['instruction_count'],
                'paths_count':      len(result['paths']),
                'accepted_paths':   sum(1 for p in result['paths'] if p['accepted']),
            }

        elif language == 'messi':
            from src.parsers.messi_parser import MessiParser
            yapar_path = os.path.join(ROOT, 'examples', 'messi.yapar')
            parser = MessiParser(yapar_path)
            result = parser.parse(code)
            r = {
                'accepted':       result['accepted'],
                'tokens':         [{'type': t.type, 'value': t.value}
                                   for t in result['tokens']],
                'errors':         result['errors'],
                'commands':       result['commands'],
                'jugadas':        result['jugadas'],
                'paths_count':    len(result['paths']),
                'accepted_paths': sum(1 for p in result['paths'] if p['accepted']),
            }

        return jsonify({'success': True, 'result': r})

    except Exception as e:
        return jsonify({
            'success':   False,
            'error':     str(e),
            'traceback': traceback.format_exc()
        })


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

def run_server(port=5000, debug=False):
    print(f"Iniciando IDE en http://localhost:{port}")
    app.run(port=port, debug=debug)


if __name__ == '__main__':
    run_server(debug=True)
