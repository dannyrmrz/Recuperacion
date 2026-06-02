// viz.js — Visualizaciones D3 para el IDE
// Funciones exportadas: drawTree(data, containerId), drawAutomaton(data, containerId)

// ─────────────────────────────────────────────
// ARBOL SINTACTICO
// ─────────────────────────────────────────────

function drawTree(data, containerId) {
  const container = document.getElementById(containerId);
  if (!container || !data) return;

  container.innerHTML = '';

  const W = container.clientWidth  || 800;
  const H = container.clientHeight || 480;
  const margin = { top: 30, right: 100, bottom: 30, left: 100 };
  const iW = W - margin.left - margin.right;
  const iH = H - margin.top  - margin.bottom;

  const svg = d3.select(container)
    .append('svg')
    .attr('width',  W)
    .attr('height', H);

  const g = svg.append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`);

  // Zoom + pan
  svg.call(
    d3.zoom()
      .scaleExtent([0.1, 5])
      .on('zoom', e => g.attr('transform', e.transform))
  );

  // Construir jerarquia D3
  const root = d3.hierarchy(
    data,
    d => (d.children && d.children.length > 0 ? d.children : null)
  );

  // Layout horizontal: x = altura, y = anchura
  d3.tree().size([iH, iW])(root);

  // ── Aristas ──
  g.append('g').selectAll('path')
    .data(root.links())
    .enter()
    .append('path')
    .attr('fill', 'none')
    .attr('stroke', '#484f58')
    .attr('stroke-width', 1.5)
    .attr('d', d3.linkHorizontal().x(d => d.y).y(d => d.x));

  // ── Nodos ──
  const node = g.append('g').selectAll('g')
    .data(root.descendants())
    .enter()
    .append('g')
    .attr('transform', d => `translate(${d.y},${d.x})`);

  // Forma: rectangulo para no terminales, elipse para terminales
  node.each(function(d) {
    const el   = d3.select(this);
    const leaf = !d.children;

    if (leaf) {
      el.append('ellipse')
        .attr('rx', 34).attr('ry', 13)
        .attr('fill',   '#0d280d')
        .attr('stroke', '#3fb950')
        .attr('stroke-width', 1.5);
    } else {
      el.append('rect')
        .attr('x', -36).attr('y', -13)
        .attr('width', 72).attr('height', 26)
        .attr('rx', 4)
        .attr('fill',   '#0d1f38')
        .attr('stroke', '#58a6ff')
        .attr('stroke-width', 1.5);
    }
  });

  // Etiquetas
  node.append('text')
    .attr('dy', '0.35em')
    .attr('text-anchor', 'middle')
    .attr('font-size',   10)
    .attr('font-family', 'monospace')
    .attr('fill', d => d.children ? '#79c0ff' : '#56d364')
    .text(d => {
      const lbl = d.data.value
        ? `${d.data.name}:${d.data.value}`
        : d.data.name;
      return lbl.length > 13 ? lbl.slice(0, 11) + '..' : lbl;
    });

  // Tooltip
  node.append('title')
    .text(d => d.data.value
      ? `${d.data.name} = '${d.data.value}'`
      : d.data.name
    );
}


// ─────────────────────────────────────────────
// AUTOMATA (LR(0) o LR(1)) — force-directed
// ─────────────────────────────────────────────

function drawAutomaton(data, containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  container.innerHTML = '';

  const W = container.clientWidth  || 900;
  const H = container.clientHeight || 480;

  const svg = d3.select(container)
    .append('svg')
    .attr('width',  W)
    .attr('height', H);

  // Arrowhead
  svg.append('defs')
    .append('marker')
    .attr('id', 'arr')
    .attr('viewBox', '-0 -5 10 10')
    .attr('refX', 22)
    .attr('refY', 0)
    .attr('markerWidth', 5)
    .attr('markerHeight', 5)
    .attr('orient', 'auto')
    .append('path')
    .attr('d', 'M0,-5L10,0L0,5')
    .attr('fill', '#484f58');

  const g = svg.append('g');

  // Zoom + pan
  svg.call(
    d3.zoom()
      .scaleExtent([0.15, 3])
      .on('zoom', e => g.attr('transform', e.transform))
  );

  // Copias para D3 force (no mutar el original)
  const nodes = data.nodes.map(n => ({ ...n }));
  const links = data.edges.map(e => ({
    ...e,
    source: e.from,
    target: e.to,
  }));

  // Altura del nodo segun numero de items
  const nodeH = d => Math.max(38, Math.min(d.items.length, 5) * 12 + 24);
  const NODE_W = 150;

  // Simulacion
  const sim = d3.forceSimulation(nodes)
    .force('link',   d3.forceLink(links).id(d => d.id).distance(220))
    .force('charge', d3.forceManyBody().strength(-500))
    .force('center', d3.forceCenter(W / 2, H / 2))
    .force('collide', d3.forceCollide(95));

  // Aristas
  const link = g.append('g').selectAll('line')
    .data(links)
    .enter()
    .append('line')
    .attr('stroke', '#484f58')
    .attr('stroke-width', 1.5)
    .attr('marker-end', 'url(#arr)');

  // Etiquetas de aristas
  const linkLabel = g.append('g').selectAll('text')
    .data(links)
    .enter()
    .append('text')
    .attr('font-size', 10)
    .attr('font-family', 'monospace')
    .attr('fill', '#ffa657')
    .text(d => d.label);

  // Nodos
  const node = g.append('g').selectAll('g')
    .data(nodes)
    .enter()
    .append('g')
    .call(
      d3.drag()
        .on('start', (e, d) => {
          if (!e.active) sim.alphaTarget(0.3).restart();
          d.fx = d.x; d.fy = d.y;
        })
        .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y; })
        .on('end',  (e, d) => {
          if (!e.active) sim.alphaTarget(0);
          d.fx = null; d.fy = null;
        })
    );

  // Cuerpo del nodo
  node.append('rect')
    .attr('width',  NODE_W)
    .attr('height', d => nodeH(d))
    .attr('x', -NODE_W / 2)
    .attr('y', d => -nodeH(d) / 2)
    .attr('rx', 5)
    .attr('fill',         d => d.id === data.initial ? '#0d1f38' : '#21262d')
    .attr('stroke',       d => d.id === data.initial ? '#58a6ff' : '#30363d')
    .attr('stroke-width', d => d.id === data.initial ? 2 : 1);

  // ID del estado
  node.append('text')
    .attr('text-anchor', 'middle')
    .attr('font-size',   11)
    .attr('font-weight', 700)
    .attr('font-family', 'monospace')
    .attr('fill', '#58a6ff')
    .attr('y', d => -nodeH(d) / 2 + 14)
    .text(d => `S${d.id}`);

  // Items del estado
  node.each(function(d) {
    const grp   = d3.select(this);
    const MAX   = 4;
    const start = -nodeH(d) / 2 + 26;

    d.items.slice(0, MAX).forEach((item, i) => {
      const short = item.length > 22 ? item.slice(0, 20) + '…' : item;
      grp.append('text')
        .attr('text-anchor', 'middle')
        .attr('font-size',   9)
        .attr('font-family', 'monospace')
        .attr('fill', '#8b949e')
        .attr('y', start + i * 12)
        .text(short);
    });

    if (d.items.length > MAX) {
      grp.append('text')
        .attr('text-anchor', 'middle')
        .attr('font-size', 9)
        .attr('font-family', 'monospace')
        .attr('fill', '#6e7681')
        .attr('y', start + MAX * 12)
        .text(`+${d.items.length - MAX} mas…`);
    }
  });

  // Tick — actualizar posiciones
  sim.on('tick', () => {
    link
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y);

    linkLabel
      .attr('x', d => (d.source.x + d.target.x) / 2)
      .attr('y', d => (d.source.y + d.target.y) / 2 - 4);

    node.attr('transform', d => `translate(${d.x},${d.y})`);
  });
}