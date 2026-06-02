// app.js — Logica principal del IDE YALex + YAPar
// Maneja estado, llamadas a la API y actualizacion de panels

// ─────────────────────────────────────────────
// ESTADO GLOBAL
// ─────────────────────────────────────────────

const STATE = {
  yalex:    '',
  yapar:    '',
  method:   'll1',
  language: 'maya',
  cachedTables: null,
  currentTableTab: 'll1',
};

// ─────────────────────────────────────────────
// EJEMPLOS
// ─────────────────────────────────────────────

const EXAMPLES = {
  yalex: `(* Ejemplo YALex — expresiones aritmeticas *)

let digit  = ['0'-'9']
let letter = ['a'-'z''A'-'Z']

rule tokens =
  | digit+                { INT }
  | digit+'.'digit+       { FLOAT }
  | letter(letter|digit)* { ID }
  | '+'  { PLUS }
  | '-'  { MINUS }
  | '*'  { TIMES }
  | '/'  { DIVIDE }
  | '('  { LPAREN }
  | ')'  { RPAREN }
  | '='  { EQUALS }
  | ' '  { (* ignorar *) }`,

  yapar: `/* Gramatica de expresiones */
%token INT ID PLUS MINUS TIMES DIVIDE EQUALS LPAREN RPAREN

%%

programa : lista_sentencias
         ;

lista_sentencias : lista_sentencias sentencia
                 | sentencia
                 ;

sentencia : ID EQUALS expresion
          ;

expresion : expresion PLUS termino
          | expresion MINUS termino
          | termino
          ;

termino : termino TIMES factor
        | termino DIVIDE factor
        | factor
        ;

factor : INT
       | ID
       | LPAREN expresion RPAREN
       ;`,
};

const LANG_EXAMPLES = {
  maya:     'baax yaan le nah o ?',
  valorant: 'ability credits kills plant 5\nspike ( kills > 3 ) gg\n    callout kills\ndefuse gg\n    callout 0\ngg',
  cow:      'MoO MoO MoO OOM',
  messi:    'La agarra Messi.\nLa mueve Messi por la derecha.\nVa Messi, moviendo la pelota con clase.\nJuega Messi.\nLe pega Messiiiii... gol!',
};

const LANG_DESCS = {
  maya:     'Parser Maya Yucateco — valida y traduce consultas al espanol',
  valorant: 'Parser ValorantScript — lenguaje inspirado en Valorant',
  cow:      'Parser COW — lenguaje esoterico con 12 instrucciones case-sensitive',
  messi:    'Parser MessiScript — lenguaje narrativo de futbol (repositorio oficial)',
};

// ─────────────────────────────────────────────
// API HELPER
// ─────────────────────────────────────────────

async function api(url, body) {
  const res = await fetch(url, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(body),
  });
  return res.json();
}

function setStatus(msg) {
  document.getElementById('st-result').textContent = msg;
}

function loading(id) {
  document.getElementById(id).innerHTML =
    '<div class="loading"><div class="spin"></div>Procesando...</div>';
}

// ─────────────────────────────────────────────
// NAVEGACION DE TABS
// ─────────────────────────────────────────────

function goTab(name) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.getElementById(`tab-${name}`).classList.add('active');
  document.getElementById(`panel-${name}`).classList.add('active');

  if (name === 'tables' && !STATE.cachedTables && STATE.yapar) loadTables();
  if (name === 'first-follow' && STATE.yapar) loadFF();
}

// ─────────────────────────────────────────────
// CARGA DE ARCHIVOS
// ─────────────────────────────────────────────

function loadFile(event, type) {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = e => {
    const content = e.target.result;
    document.getElementById(`${type}-input`).value = content;
    STATE[type] = content;
    type === 'yalex' ? parseYalex() : parseYapar();
  };
  reader.readAsText(file);
}

function loadExample(type) {
  document.getElementById(`${type}-input`).value = EXAMPLES[type];
  STATE[type] = EXAMPLES[type];
  type === 'yalex' ? parseYalex() : parseYapar();
}

// ─────────────────────────────────────────────
// PARSEAR YALEX
// ─────────────────────────────────────────────

async function parseYalex() {
  const content = document.getElementById('yalex-input').value.trim();
  if (!content) return;
  STATE.yalex = content;
  setStatus('Procesando .yalex...');

  const r = await api('/api/parse-yalex', { content });

  if (r.success) {
    document.getElementById('dot-yalex').classList.add('on');
    document.getElementById('yalex-meta').textContent = `${r.rules_count} reglas`;
    document.getElementById('st-yalex').textContent   = `yalex: ${r.rules_count} reglas`;
    setStatus('YALex cargado');
  } else {
    setStatus(`Error yalex: ${r.error}`);
  }
}

// ─────────────────────────────────────────────
// PARSEAR YAPAR
// ─────────────────────────────────────────────

async function parseYapar() {
  const content = document.getElementById('yapar-input').value.trim();
  if (!content) return;
  STATE.yapar = content;
  setStatus('Procesando .yapar...');

  const r = await api('/api/parse-yapar', { content });

  if (r.success) {
    document.getElementById('dot-yapar').classList.add('on');
    document.getElementById('yapar-meta').textContent = `${r.productions} prod.`;
    document.getElementById('st-yapar').textContent   = `yapar: ${r.productions} producciones`;

    // Mostrar info de gramatica en sidebar
    document.getElementById('grammar-section').style.display = '';
    document.getElementById('grammar-grid').innerHTML = `
      <div class="info-cell"><div class="k">Simbolo inicial</div><div class="v">${r.start_symbol}</div></div>
      <div class="info-cell"><div class="k">Producciones</div><div class="v">${r.productions}</div></div>
      <div class="info-cell"><div class="k">Tokens</div><div class="v">${r.tokens.length}</div></div>
      <div class="info-cell"><div class="k">No terminales</div><div class="v">${r.non_terminals.length}</div></div>
    `;
    setStatus('YAPar cargado');
  } else {
    setStatus(`Error yapar: ${r.error}`);
  }
}

// ─────────────────────────────────────────────
// METODO DE ANALISIS
// ─────────────────────────────────────────────

function setMethod(m) {
  STATE.method = m;
  ['ll1', 'slr', 'lalr'].forEach(x =>
    document.getElementById(`mbtn-${x}`).classList.toggle('active', x === m)
  );
  document.getElementById('st-method').textContent = `metodo: ${m}`;
}

// ─────────────────────────────────────────────
// ANALIZAR CODIGO
// ─────────────────────────────────────────────

async function analyze() {
  const code = document.getElementById('code-editor').value.trim();
  if (!code)    { alert('Escribe codigo primero'); return; }
  if (!STATE.yapar) { alert('Carga un .yapar primero'); return; }

  setStatus('Analizando...');
  document.getElementById('analyze-btn').textContent = '⏳ Analizando...';

  const r = await api('/api/analyze', {
    code,
    method: STATE.method,
    yapar:  STATE.yapar,
    yalex:  STATE.yalex,
  });

  document.getElementById('analyze-btn').textContent = '▶ Analizar';

  if (!r.success) {
    setStatus(`Error: ${r.error}`);
    renderResultBanner(false, `Error interno: ${r.error}`, {});
    return;
  }

  // Actualizar todos los panels
  renderResultBanner(r.accepted, null, r);
  renderTokensPanel(r.tokens);
  renderErrorsPanel(r.lex_errors, r.syn_errors);
  renderParallelPanel(r.paths);
  if (r.tree) {
    document.getElementById('tree-viz').innerHTML = '';
    drawTree(r.tree, 'tree-viz');
  }

  // Contadores en tabs
  updateTabCount('tokens', r.tokens.length, true);
  const totalErr = (r.lex_errors || []).length + (r.syn_errors || []).length;
  updateTabCount('errors', totalErr, totalErr === 0);

  setStatus(r.accepted ? 'Aceptado' : 'Rechazado');
}

function clearEditor() {
  document.getElementById('code-editor').value = '';
  document.getElementById('result-banner').style.display = 'none';
}

function updateTabCount(tabName, count, ok) {
  const el = document.getElementById(`cnt-${tabName}`);
  if (!el) return;
  if (count === 0) { el.style.display = 'none'; return; }
  el.style.display  = '';
  el.textContent    = count;
  el.className      = `tab-count${ok ? ' ok' : ' err'}`;
}

// ─────────────────────────────────────────────
// BANNER DE RESULTADO
// ─────────────────────────────────────────────

function renderResultBanner(accepted, errorMsg, r) {
  const el = document.getElementById('result-banner');
  el.style.display = '';
  el.className = `result-banner ${accepted ? 'ok' : 'err'}`;

  if (errorMsg) {
    el.innerHTML = `<div class="result-main banner-err"><div class="result-dot"></div>${errorMsg}</div>`;
    return;
  }

  const text = accepted
    ? 'ACEPTADO — la entrada es valida segun la gramatica'
    : 'RECHAZADO — la entrada no cumple la gramatica';

  const errTotal = ((r.lex_errors || []).length + (r.syn_errors || []).length);

  el.innerHTML = `
    <div class="result-main ${accepted ? 'banner-ok' : 'banner-err'}">
      <div class="result-dot"></div>
      ${text}
    </div>
    <div class="result-stats">
      <div class="stat-item">Metodo: <span class="v a">${(r.method || '').toUpperCase()}</span></div>
      <div class="stat-item">Tokens: <span class="v a">${(r.tokens || []).length}</span></div>
      <div class="stat-item">Caminos: <span class="v a">${r.paths_count || 0}</span></div>
      <div class="stat-item">Aceptados: <span class="v g">${r.accepted_paths || 0}</span></div>
      <div class="stat-item">Errores: <span class="v ${errTotal > 0 ? 'r' : ''}">${errTotal}</span></div>
    </div>
  `;
}

// ─────────────────────────────────────────────
// PANEL: TOKENS
// ─────────────────────────────────────────────

function renderTokensPanel(tokens) {
  if (!tokens || tokens.length === 0) {
    document.getElementById('tokens-content').innerHTML =
      '<div class="empty-state"><div class="empty-icon">⬡</div><p>Sin tokens</p></div>';
    return;
  }

  const chipClass = type => {
    const kw = ['SPIKE','DEFUSE','ROUND','CALLOUT','ABILITY','CREDITS','GG','PLANT',
                'IF','ELSE','WHILE','CLUTCH','WHIFF','CMD_INICIO','CMD_FIN'];
    const op = ['PLUS','MINUS','TIMES','DIVIDE','EQUALS','GT','LT',
                'LPAREN','RPAREN','LBRACE','RBRACE'];
    if (kw.includes(type))                   return 'chip-kw';
    if (op.includes(type))                   return 'chip-op';
    if (type === 'INT' || type === 'FLOAT')  return 'chip-num';
    if (type === 'ID')                       return 'chip-id';
    return 'chip-def';
  };

  let html = `
    <div class="content-title">
      Tokens
      <span class="pill pill-info">${tokens.length} encontrados</span>
    </div>
    <p style="font-size:11px;color:var(--text3);margin-bottom:10px">
      Azul = keywords &nbsp;·&nbsp; Naranja = operadores &nbsp;·&nbsp;
      Morado = numeros &nbsp;·&nbsp; Verde = identificadores
    </p>
    <div class="token-grid">
  `;

  tokens.forEach((t, i) => {
    const cls = chipClass(t.type);
    const pos = t.line ? `L${t.line}:C${t.column}` : `#${i + 1}`;
    html += `
      <div class="chip ${cls}" title="${pos}">
        <span class="t">${t.type}</span>
        ${t.value && t.value !== t.type ? `<span class="v">'${t.value}'</span>` : ''}
      </div>
    `;
  });

  html += '</div>';
  document.getElementById('tokens-content').innerHTML = html;
}

// ─────────────────────────────────────────────
// PANEL: ERRORES
// ─────────────────────────────────────────────

function renderErrorsPanel(lexErrors, synErrors) {
  const lex = lexErrors || [];
  const syn = synErrors || [];
  const total = lex.length + syn.length;

  if (total === 0) {
    document.getElementById('errors-content').innerHTML = `
      <div class="no-errors">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="20 6 9 17 4 12"></polyline>
        </svg>
        Sin errores lexicos ni sintacticos
      </div>
    `;
    return;
  }

  let html = `
    <div class="content-title">
      Errores y conflictos
      <span class="pill pill-err">${total} encontrado(s)</span>
    </div>
  `;

  if (lex.length) {
    html += `<div class="sub-block">
      <div class="sub-label">Errores lexicos (${lex.length})</div>`;
    lex.forEach(e => {
      html += `
        <div class="error-card">
          <div class="etype">Error Lexico</div>
          <div class="emsg">${e.message}</div>
          ${e.line ? `<div class="epos">Linea ${e.line}, columna ${e.column}</div>` : ''}
        </div>`;
    });
    html += '</div>';
  }

  if (syn.length) {
    html += `<div class="sub-block">
      <div class="sub-label">Conflictos sintacticos (${syn.length})</div>`;
    syn.forEach(e => {
      html += `
        <div class="error-card warn">
          <div class="etype">Conflicto ${e.conflict_type || ''}</div>
          <div class="emsg">${e.message}</div>
          <div class="epos">El parser paralelo explora ambos caminos automaticamente</div>
        </div>`;
    });
    html += '</div>';
  }

  document.getElementById('errors-content').innerHTML = html;
}

// ─────────────────────────────────────────────
// PANEL: FIRST / FOLLOW
// ─────────────────────────────────────────────

async function loadFF() {
  if (!STATE.yapar) {
    document.getElementById('ff-content').innerHTML =
      '<div class="empty-state"><div>Carga un .yapar primero</div></div>';
    return;
  }

  loading('ff-content');

  const r = await api('/api/first-follow', { yapar: STATE.yapar });

  if (!r.success) {
    document.getElementById('ff-content').innerHTML =
      `<div class="error-card"><div class="emsg">${r.error}</div></div>`;
    return;
  }

  const nts = Object.keys(r.first).sort();

  let html = `
    <div class="content-title">
      FIRST y FOLLOW
      <span class="pill pill-info">${nts.length} no terminales</span>
    </div>
    <p style="font-size:11px;color:var(--text3);margin-bottom:12px">
      FIRST(A) = terminales con los que puede <strong>empezar</strong> A &nbsp;·&nbsp;
      FOLLOW(A) = terminales que pueden aparecer <strong>despues</strong> de A
    </p>
    <table class="ff-table">
      <thead>
        <tr>
          <th>No Terminal</th>
          <th>FIRST(A)</th>
          <th>FOLLOW(A)</th>
        </tr>
      </thead>
      <tbody>
  `;

  nts.forEach(nt => {
    const first  = (r.first[nt]  || []).map(t =>
      `<span class="tag${t === 'ε' ? ' eps' : ''}">${t}</span>`
    ).join('');
    const follow = (r.follow[nt] || []).map(t =>
      `<span class="tag${t === '$' ? ' dlr' : ''}">${t}</span>`
    ).join('');

    html += `
      <tr>
        <td class="nt-cell">${nt}</td>
        <td>${first  || '<span class="muted">—</span>'}</td>
        <td>${follow || '<span class="muted">—</span>'}</td>
      </tr>
    `;
  });

  html += '</tbody></table>';
  document.getElementById('ff-content').innerHTML = html;
}

// ─────────────────────────────────────────────
// PANEL: TABLAS
// ─────────────────────────────────────────────

function switchTableTab(tab) {
  STATE.currentTableTab = tab;
  ['ll1', 'slr', 'lalr'].forEach(x =>
    document.getElementById(`ttab-${x}`).classList.toggle('active', x === tab)
  );
  if (STATE.cachedTables) renderCurrentTable();
}

async function loadTables() {
  if (!STATE.yapar) {
    document.getElementById('tables-content').innerHTML =
      '<div class="empty-state"><div>Carga un .yapar primero</div></div>';
    return;
  }

  loading('tables-content');

  const r = await api('/api/tables', { yapar: STATE.yapar, method: 'all' });

  if (!r.success) {
    document.getElementById('tables-content').innerHTML =
      `<div class="error-card"><div class="emsg">${r.error}</div></div>`;
    return;
  }

  STATE.cachedTables = r;
  renderCurrentTable();
}

function renderCurrentTable() {
  const tab = STATE.currentTableTab;
  const r   = STATE.cachedTables;
  let html  = '';

  if (tab === 'll1' && r.ll1)   html = buildLL1Table(r.ll1);
  if (tab === 'slr' && r.slr)   html = buildLRTable('SLR(1)', r.slr);
  if (tab === 'lalr' && r.lalr) {
    html = buildLRTable('LALR', r.lalr);
    html += `<p style="font-size:11px;color:var(--text3);margin-top:8px">
      Estados LR(1) generados: ${r.lalr.lr1_states_count} →
      Estados LALR fusionados: ${r.lalr.lalr_states_count}
    </p>`;
  }

  document.getElementById('tables-content').innerHTML = html ||
    '<div class="empty-state"><div>Tabla no disponible</div></div>';
}

function buildLL1Table(d) {
  const { table, terminals, non_terminals, conflicts, is_ll1 } = d;
  let html = `
    <div class="content-title">
      Tabla LL(1)
      <span class="pill ${is_ll1 ? 'pill-ok' : 'pill-err'}">
        ${is_ll1 ? 'Sin conflictos' : conflicts.length + ' conflicto(s)'}
      </span>
    </div>
    <div class="table-wrap"><table class="ptable">
      <thead>
        <tr>
          <th>NT \\ T</th>
          ${terminals.map(t => `<th>${t}</th>`).join('')}
        </tr>
      </thead>
      <tbody>
  `;
  non_terminals.forEach(nt => {
    html += `<tr><td class="cst">${nt}</td>`;
    terminals.forEach(t => {
      const p = table[nt] && table[nt][t];
      html += p
        ? `<td class="cr" title="${nt} → ${p.symbols.join(' ')}">${p.symbols.join(' ')}</td>`
        : '<td></td>';
    });
    html += '</tr>';
  });
  return html + '</tbody></table></div>';
}

function buildLRTable(title, d) {
  const { action, goto: gotoT, terminals, non_terminals, conflicts } = d;
  const states = Object.keys(action).map(Number).sort((a, b) => a - b);

  let html = `
    <div class="content-title">
      Tabla ${title}
      <span class="pill ${conflicts.length === 0 ? 'pill-ok' : 'pill-err'}">
        ${conflicts.length === 0 ? 'Sin conflictos' : conflicts.length + ' conflicto(s)'}
      </span>
    </div>
    <div class="table-wrap"><table class="ptable">
      <thead>
        <tr>
          <th rowspan="2">Estado</th>
          <th colspan="${terminals.length}">ACTION</th>
          <th colspan="${non_terminals.length}" class="nt-h">GOTO</th>
        </tr>
        <tr>
          ${terminals.map(t => `<th>${t}</th>`).join('')}
          ${non_terminals.map(n => `<th class="nt-h">${n}</th>`).join('')}
        </tr>
      </thead>
      <tbody>
  `;

  states.forEach(s => {
    html += `<tr><td class="cst">${s}</td>`;
    terminals.forEach(t => {
      const act = action[s] && action[s][t];
      if (!act) { html += '<td></td>'; return; }
      if (Array.isArray(act)) { html += `<td class="cc" title="Conflicto">CONF</td>`; return; }
      const { type, value } = act;
      if (type === 'SHIFT')  { html += `<td class="cs" title="Ir al estado ${value}">S${value}</td>`; return; }
      if (type === 'REDUCE') { html += `<td class="cr" title="Produccion ${value}">R${value}</td>`; return; }
      if (type === 'ACCEPT') { html += `<td class="ca">ACC</td>`; return; }
      html += '<td></td>';
    });
    non_terminals.forEach(nt => {
      const g = gotoT[s] && gotoT[s][nt];
      html += g !== undefined ? `<td class="cg">${g}</td>` : '<td></td>';
    });
    html += '</tr>';
  });

  return html + '</tbody></table></div>';
}

// ─────────────────────────────────────────────
// PANEL: AUTOMATA
// ─────────────────────────────────────────────

async function loadAutomaton(type) {
  if (!STATE.yapar) {
    document.getElementById('automaton-viz').innerHTML =
      '<div class="empty-state" style="height:100%"><div>Carga un .yapar primero</div></div>';
    return;
  }

  document.getElementById('automaton-viz').innerHTML =
    '<div class="loading" style="height:100%"><div class="spin"></div>Construyendo automata...</div>';

  const r = await api('/api/automaton', { yapar: STATE.yapar, type });

  if (!r.success) {
    document.getElementById('automaton-viz').innerHTML =
      `<div class="error-card" style="margin:16px"><div class="emsg">${r.error}</div></div>`;
    return;
  }

  const d = r.automaton;
  document.getElementById('automaton-hint').textContent =
    `${d.type} — ${d.nodes.length} estados, ${d.edges.length} transiciones · Zoom y arrastre disponibles`;

  drawAutomaton(d, 'automaton-viz');
}

// ─────────────────────────────────────────────
// PANEL: PARALELISMO
// ─────────────────────────────────────────────

function renderParallelPanel(paths) {
  if (!paths || paths.length === 0) {
    document.getElementById('parallel-content').innerHTML =
      '<div class="empty-state"><div class="empty-icon">⑂</div><p>Sin caminos</p></div>';
    return;
  }

  const acc     = paths.filter(p => p.accepted).length;
  const isMulti = paths.length > 1;

  let html = `
    <div class="content-title">
      Caminos paralelos
      <span class="pill pill-info">${paths.length} camino(s)</span>
    </div>
  `;

  if (isMulti) {
    html += `
      <div class="sub-block" style="border-left:3px solid var(--yellow);border-radius:0 6px 6px 0;margin-bottom:12px">
        <div style="color:var(--yellow);font-size:12px">
          Se detectaron conflictos — el parser lanzo ${paths.length} hilos en paralelo.
          ${acc} camino(s) llegaron a ACCEPT.
        </div>
      </div>
    `;
  }

  paths.forEach(p => {
    const cls    = p.accepted ? 'ok'  : 'err';
    const status = p.accepted
      ? `<span class="path-ok">ACEPTADO</span>`
      : `<span class="path-err">RECHAZADO</span>`;

    html += `
      <div class="path-card ${cls}">
        <div class="path-hdr">
          <span class="path-id">Camino ${p.path_id}</span>
          ${status}
        </div>
        <div style="font-size:11px;color:var(--text3);margin-bottom:6px">
          ${p.steps_count} pasos totales
        </div>
        <div>
    `;

    (p.last_steps || []).forEach(s => {
      html += `<div class="step-row ${s.conflict ? 'conflict' : ''}">
        ${s.conflict ? '⚡ ' : ''}${s.action}
      </div>`;
    });

    html += '</div></div>';
  });

  document.getElementById('parallel-content').innerHTML = html;
}

// ─────────────────────────────────────────────
// PANEL: LENGUAJES
// ─────────────────────────────────────────────

function setLang(lang) {
  STATE.language = lang;
  ['maya', 'valorant', 'cow', 'messi'].forEach(x =>
    document.getElementById(`ltab-${x}`).classList.toggle('active', x === lang)
  );
  document.getElementById('lang-desc').textContent = LANG_DESCS[lang];
  document.getElementById('lang-result').innerHTML =
    '<span class="muted">El resultado aparecera aqui...</span>';
}

function loadLangExample() {
  document.getElementById('lang-editor').value = LANG_EXAMPLES[STATE.language];
}

async function parseLang() {
  const code = document.getElementById('lang-editor').value.trim();
  if (!code) return;

  document.getElementById('lang-result').innerHTML =
    '<div class="loading"><div class="spin"></div>Analizando...</div>';

  const r = await api('/api/language', { language: STATE.language, code });

  if (!r.success) {
    document.getElementById('lang-result').innerHTML =
      `<div style="color:var(--red)">${r.error}</div>`;
    return;
  }

  const d = r.result;

  const badgeClass = d.accepted ? 'ok'  : 'err';
  const badgeText  = d.accepted ? 'VALIDO' : 'INVALIDO';

  let html = `
    <div class="result-banner ${badgeClass}" style="margin-bottom:10px">
      <div class="result-main ${d.accepted ? 'banner-ok' : 'banner-err'}">
        <div class="result-dot"></div>
        ${badgeText}
      </div>
    </div>
  `;

  // Tokens
  if (d.tokens && d.tokens.length) {
    html += `<p style="font-size:11px;color:var(--text2);margin-bottom:5px">
      Tokens (${d.tokens.length}):
    </p><div class="token-grid" style="margin-bottom:10px">`;
    d.tokens.forEach(t => {
      html += `<div class="chip chip-def">
        <span class="t">${t.type}</span>
        ${t.value && t.value !== t.type ? `<span class="v">'${t.value}'</span>` : ''}
      </div>`;
    });
    html += '</div>';
  }

  // Traduccion Maya
  if (d.translation) {
    html += `<div class="translation-box">
      <div class="translation-label">Traduccion al espanol</div>
      ${d.translation}
    </div>`;
  }

  // Comandos MessiScript
  if (d.commands && d.commands.length) {
    html += `<p style="font-size:11px;color:var(--text2);margin-bottom:4px">Comandos:</p>
      <p style="font-size:11px;color:var(--accent)">
        ${d.commands.join(' → ')}
      </p>`;
  }

  // Instrucciones COW
  if (d.instruction_count !== undefined) {
    html += `<p style="font-size:11px;color:var(--text2)">
      Instrucciones reconocidas: <span style="color:var(--accent)">${d.instruction_count}</span>
    </p>`;
  }

  // Errores
  if (d.errors && d.errors.length) {
    html += '<div style="margin-top:8px">';
    d.errors.forEach(e => {
      html += `<div class="error-card">
        <div class="emsg">${e.message || JSON.stringify(e)}</div>
      </div>`;
    });
    html += '</div>';
  }

  // Info de paralelismo
  if (d.paths_count > 1) {
    html += `<p style="font-size:11px;color:var(--yellow);margin-top:8px">
      Paralelismo: ${d.paths_count} caminos, ${d.accepted_paths} aceptado(s)
    </p>`;
  }

  document.getElementById('lang-result').innerHTML = html;

  // Arbol
  if (d.tree) {
    drawTree(d.tree, 'tree-viz');
  }
}

// ─────────────────────────────────────────────
// INIT
// ─────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  setLang('maya');
});