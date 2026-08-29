(() => {
  const NS = 'http://www.w3.org/2000/svg';

  function svgNode(name, attributes = {}, text = '') {
    const node = document.createElementNS(NS, name);
    Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, String(value)));
    if (text) node.textContent = text;
    return node;
  }

  function money(value, currency = 'USD') {
    return new Intl.NumberFormat('en-US', {
      style: 'currency', currency, maximumFractionDigits: 0,
    }).format(value);
  }

  function shortDate(value) {
    return new Intl.DateTimeFormat('en-GB', {
      day: '2-digit', month: 'short', year: '2-digit', timeZone: 'UTC',
    }).format(new Date(value));
  }

  function drawChart(shell, payload) {
    const svg = shell.querySelector('[data-chart-svg]');
    const status = shell.querySelector('[data-chart-status]');
    const rawDatasets = payload.datasets?.length
      ? payload.datasets
      : [{ label: payload.label || 'Equity', color: '#7ef7c7', series: payload.series || [] }];
    const datasets = rawDatasets.map((dataset, index) => ({
      label: dataset.label || `Series ${index + 1}`,
      color: dataset.color || (index ? '#68a7ff' : '#7ef7c7'),
      series: (dataset.series || [])
        .map((point) => ({ time: new Date(point.time), balance: Number(point.balance) }))
        .filter((point) => Number.isFinite(point.time.getTime()) && Number.isFinite(point.balance))
        .sort((first, second) => first.time - second.time),
    })).filter((dataset) => dataset.series.length >= 2);
    if (!datasets.length) throw new Error('Not enough balance points to draw this curve.');
    const allPoints = datasets.flatMap((dataset) => dataset.series);

    status.classList.add('hidden');
    svg.classList.remove('hidden');
    svg.replaceChildren();

    const width = 1000, height = 360, left = 78, right = 28, top = 28, bottom = 48;
    const balances = allPoints.map((point) => point.balance);
    let minimum = Math.min(...balances), maximum = Math.max(...balances);
    const padding = Math.max((maximum - minimum) * 0.12, Math.abs(maximum) * 0.01, 1);
    minimum -= padding;
    maximum += padding;
    const firstTime = Math.min(...allPoints.map((point) => point.time.getTime()));
    const lastTime = Math.max(...allPoints.map((point) => point.time.getTime()));
    const timeSpan = Math.max(lastTime - firstTime, 1);
    const plotWidth = width - left - right;
    const plotHeight = height - top - bottom;
    const x = (point) => left + ((point.time.getTime() - firstTime) / timeSpan) * plotWidth;
    const y = (value) => top + ((maximum - value) / (maximum - minimum)) * plotHeight;

    const defs = svgNode('defs');
    const gradientId = `equity-fill-${Math.random().toString(36).slice(2)}`;
    const gradient = svgNode('linearGradient', { id: gradientId, x1: 0, y1: 0, x2: 0, y2: 1 });
    gradient.appendChild(svgNode('stop', { offset: '0%', 'stop-color': '#7ef7c7', 'stop-opacity': .22 }));
    gradient.appendChild(svgNode('stop', { offset: '100%', 'stop-color': '#7ef7c7', 'stop-opacity': 0 }));
    defs.appendChild(gradient);
    svg.appendChild(defs);

    for (let index = 0; index < 5; index += 1) {
      const yy = top + (index / 4) * plotHeight;
      const value = maximum - (index / 4) * (maximum - minimum);
      svg.appendChild(svgNode('line', {
        x1: left, y1: yy, x2: width - right, y2: yy,
        stroke: 'rgba(255,255,255,.09)', 'stroke-width': 1,
      }));
      svg.appendChild(svgNode('text', {
        x: left - 12, y: yy + 4, fill: '#789089', 'font-size': 11,
        'font-family': 'IBM Plex Mono, monospace', 'text-anchor': 'end',
      }, money(value, payload.currency || 'USD')));
    }

    datasets.forEach((dataset, index) => {
      const linePoints = dataset.series.map((point) => `${x(point).toFixed(2)},${y(point.balance).toFixed(2)}`).join(' ');
      if (datasets.length === 1) {
        const areaPoints = `${left},${top + plotHeight} ${linePoints} ${width - right},${top + plotHeight}`;
        svg.appendChild(svgNode('polygon', { points: areaPoints, fill: `url(#${gradientId})` }));
      }
      svg.appendChild(svgNode('polyline', {
        points: linePoints, fill: 'none', stroke: dataset.color,
        'stroke-width': index ? 2.5 : 3, 'stroke-linecap': 'round', 'stroke-linejoin': 'round',
      }));
      const finalPoint = dataset.series.at(-1);
      svg.appendChild(svgNode('circle', {
        cx: x(finalPoint), cy: y(finalPoint.balance), r: 5, fill: dataset.color,
        stroke: '#07100f', 'stroke-width': 3,
      }));
      const legendX = left + index * 180;
      svg.appendChild(svgNode('line', { x1: legendX, y1: 14, x2: legendX + 22, y2: 14, stroke: dataset.color, 'stroke-width': 4 }));
      svg.appendChild(svgNode('text', { x: legendX + 30, y: 18, fill: '#c9dbd6', 'font-size': 11, 'font-family': 'IBM Plex Mono, monospace' }, dataset.label));
    });
    const firstPoint = allPoints.reduce((earliest, point) => point.time < earliest.time ? point : earliest, allPoints[0]);
    const finalPoint = datasets[0].series.at(-1);
    svg.appendChild(svgNode('text', {
      x: left, y: height - 14, fill: '#789089', 'font-size': 11,
      'font-family': 'IBM Plex Mono, monospace',
    }, shortDate(firstPoint.time)));
    svg.appendChild(svgNode('text', {
      x: width - right, y: height - 14, fill: '#789089', 'font-size': 11,
      'font-family': 'IBM Plex Mono, monospace', 'text-anchor': 'end',
    }, shortDate(finalPoint.time)));
    svg.appendChild(svgNode('text', {
      x: width - right - 12, y: Math.max(y(finalPoint.balance) - 12, top + 12),
      fill: '#baffdf', 'font-size': 12, 'font-weight': 700,
      'font-family': 'IBM Plex Mono, monospace', 'text-anchor': 'end',
    }, money(finalPoint.balance, payload.currency || 'USD')));
  }

  async function loadChart(shell) {
    const status = shell.querySelector('[data-chart-status]');
    try {
      const response = await fetch(shell.dataset.seriesUrl, { cache: 'no-store' });
      if (!response.ok) throw new Error(`The curve endpoint returned ${response.status}.`);
      drawChart(shell, await response.json());
    } catch (error) {
      status.classList.remove('hidden');
      status.textContent = 'Equity curve is temporarily unavailable.';
      status.title = String(error);
    }
  }

  document.querySelectorAll('[data-equity-graph]').forEach(loadChart);
})();
