(() => {
  'use strict';

  const DOTS_PER_DISTRIBUTION = 96;
  const BIN_COUNT = 24;
  const BUILD_MS = 10500;
  const TRAVEL_MS = 1150;
  const HOLD_MS = 2800;
  const FADE_MS = 700;
  const CYCLE_MS = BUILD_MS + TRAVEL_MS + HOLD_MS + FADE_MS;

  const VIEW = { width: 360, height: 300, top: 28, right: 10, bottom: 25, left: 53 };
  const plotBottom = VIEW.height - VIEW.bottom;
  const stackColumns = 39;
  const stackSpacing = 3.25;
  const groups = {
    faculty: { baseline: 207, labelX: 145, shape: 'circle' },
    industry: { baseline: 340, labelX: 276, shape: 'diamond' }
  };

  const data = window.PAY_DISTRIBUTIONS;
  const grid = document.querySelector('#small-multiples');
  const money = d3.format('$,.0f');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  let ordered = [...data];
  let panels = [];
  let observer = null;
  let resizeObserver = null;
  let animationFrame = null;

  const maximum = d3.max(data, row => Math.max(
    row.faculty.mean + row.faculty.std * 3,
    row.industry.mean + row.industry.std * 3
  ));
  const yScale = d3.scaleLinear()
    .domain([0, maximum])
    .nice()
    .range([plotBottom, VIEW.top]);
  const sharedDomain = yScale.domain();
  const binSize = sharedDomain[1] / BIN_COUNT;

  const colorByMajor = new Map(
    [...data]
      .sort((a, b) => d3.ascending(a.major, b.major))
      .map((row, index, rows) => [row.major, d3.hsl((index / rows.length) * 330 + 8, 0.57, 0.47).formatHex()])
  );

  function validateConstants(rows) {
    if (!Array.isArray(rows) || rows.length === 0) throw new Error('PAY_DISTRIBUTIONS must be a non-empty array.');
    rows.forEach((row, index) => {
      if (!row.major || !row.faculty || !row.industry) throw new Error(`Invalid record at index ${index}.`);
      ['faculty', 'industry'].forEach(group => {
        const { mean, std } = row[group];
        if (!Number.isFinite(mean) || !Number.isFinite(std) || mean < 0 || std < 0) {
          throw new Error(`${row.major}: ${group} mean/std must be non-negative numbers.`);
        }
      });
    });
  }

  function hash(text) {
    let value = 2166136261;
    for (let index = 0; index < text.length; index += 1) {
      value ^= text.charCodeAt(index);
      value = Math.imul(value, 16777619);
    }
    return value >>> 0;
  }

  function randomGenerator(seed) {
    let state = seed >>> 0;
    return () => {
      state += 0x6D2B79F5;
      let value = state;
      value = Math.imul(value ^ (value >>> 15), value | 1);
      value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
      return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
    };
  }

  function normalSample(random, mean, std) {
    const first = Math.max(random(), Number.EPSILON);
    const second = random();
    return Math.max(0, mean + std * Math.sqrt(-2 * Math.log(first)) * Math.cos(2 * Math.PI * second));
  }

  function shuffle(values, random) {
    for (let index = values.length - 1; index > 0; index -= 1) {
      const swapIndex = Math.floor(random() * (index + 1));
      [values[index], values[swapIndex]] = [values[swapIndex], values[index]];
    }
    return values;
  }

  function makePoints(row) {
    const points = [];
    const sourceY = yScale(d3.mean([row.faculty.mean, row.industry.mean]));

    Object.entries(groups).forEach(([groupName, group]) => {
      const random = randomGenerator(hash(`${row.major}-${groupName}`));
      const bins = Array.from({ length: BIN_COUNT }, () => 0);
      for (let index = 0; index < DOTS_PER_DISTRIBUTION; index += 1) {
        const salary = Math.min(sharedDomain[1] - 1, normalSample(random, row[groupName].mean, row[groupName].std));
        const bin = Math.max(0, Math.min(BIN_COUNT - 1, Math.floor(salary / binSize)));
        const stackIndex = bins[bin]++;
        const column = stackIndex % stackColumns;
        const wrapRow = Math.floor(stackIndex / stackColumns);
        points.push({
          group: groupName,
          shape: group.shape,
          startX: VIEW.left + 9 + (random() - 0.5) * 3,
          startY: sourceY + (random() - 0.5) * 3,
          targetX: group.baseline - column * stackSpacing,
          targetY: yScale((bin + 0.5) * binSize) + (wrapRow - 0.5) * 3,
          travel: TRAVEL_MS * (0.82 + random() * 0.35),
          phase: random() * Math.PI * 2,
          spawn: 0
        });
      }
    });

    const scheduleRandom = randomGenerator(hash(`${row.major}-schedule`));
    shuffle(points, scheduleRandom).forEach((point, index) => {
      point.spawn = 180 + (index / (points.length - 1)) * BUILD_MS;
    });
    return { points, sourceY };
  }

  function createSvg(row, sourceY) {
    const svg = d3.create('svg')
      .attr('viewBox', `0 0 ${VIEW.width} ${VIEW.height}`)
      .attr('role', 'img')
      .attr('aria-label', `${row.major} animated faculty and industry salary histograms`);

    svg.append('g')
      .attr('class', 'panel-grid')
      .attr('transform', `translate(${VIEW.left},0)`)
      .call(d3.axisLeft(yScale).ticks(5).tickSize(-(VIEW.width - VIEW.left - VIEW.right)).tickFormat(''));
    svg.append('g')
      .attr('class', 'panel-axis')
      .attr('transform', `translate(${VIEW.left},0)`)
      .call(d3.axisLeft(yScale).ticks(5).tickFormat(value => d3.format('$,.0s')(value)));
    svg.append('text')
      .attr('class', 'panel-axis-title')
      .attr('x', 1)
      .attr('y', 10)
      .text('SALARY');

    svg.append('line')
      .attr('class', 'panel-source-guide')
      .attr('x1', VIEW.left + 9)
      .attr('x2', VIEW.left + 9)
      .attr('y1', VIEW.top)
      .attr('y2', plotBottom);
    svg.append('circle').attr('class', 'panel-source-halo').attr('cx', VIEW.left + 9).attr('cy', sourceY).attr('r', 8);
    svg.append('circle').attr('class', 'panel-source-dot').attr('cx', VIEW.left + 9).attr('cy', sourceY).attr('r', 3.2);
    svg.append('text')
      .attr('class', 'panel-source-label')
      .attr('x', VIEW.left + 9)
      .attr('y', sourceY - 12)
      .attr('text-anchor', 'middle')
      .text('IN');

    svg.append('line')
      .attr('class', 'panel-divider')
      .attr('x1', 212)
      .attr('x2', 212)
      .attr('y1', VIEW.top)
      .attr('y2', plotBottom);
    svg.append('text')
      .attr('class', 'panel-label')
      .attr('x', groups.faculty.labelX)
      .attr('y', 14)
      .attr('text-anchor', 'middle')
      .text('FACULTY ○');
    svg.append('text')
      .attr('class', 'panel-label')
      .attr('x', groups.industry.labelX)
      .attr('y', 14)
      .attr('text-anchor', 'middle')
      .text('INDUSTRY ◇');

    Object.entries(groups).forEach(([groupName, group]) => {
      svg.append('line')
        .attr('class', 'panel-mean')
        .attr('x1', groupName === 'faculty' ? 78 : 218)
        .attr('x2', group.baseline)
        .attr('y1', yScale(row[groupName].mean))
        .attr('y2', yScale(row[groupName].mean));
    });
    return svg.node();
  }

  function createPanel(row, index) {
    const article = document.createElement('article');
    article.className = 'major-panel';
    article.style.setProperty('--major-color', colorByMajor.get(row.major));
    article.tabIndex = 0;
    article.setAttribute('aria-label', `${row.major}. Faculty mean ${money(row.faculty.mean)}, standard deviation ${money(row.faculty.std)}. Industry mean ${money(row.industry.mean)}, standard deviation ${money(row.industry.std)}.`);

    const heading = document.createElement('div');
    heading.className = 'panel-heading';
    const title = document.createElement('h3');
    title.textContent = row.major;
    const number = document.createElement('span');
    number.className = 'panel-number';
    number.textContent = String(index + 1).padStart(2, '0');
    heading.append(title, number);

    const plot = document.createElement('div');
    plot.className = 'panel-plot';
    const canvas = document.createElement('canvas');
    canvas.setAttribute('aria-hidden', 'true');
    const { points, sourceY } = makePoints(row);
    plot.append(canvas, createSvg(row, sourceY));
    article.append(heading, plot);
    grid.append(article);

    const panel = {
      row,
      article,
      plot,
      canvas,
      context: canvas.getContext('2d'),
      points,
      sourceY,
      color: colorByMajor.get(row.major),
      visible: false,
      hasStarted: false,
      startedAt: 0,
      scaleX: 1,
      scaleY: 1,
      ratio: 1
    };
    sizeCanvas(panel);
    return panel;
  }

  function sizeCanvas(panel) {
    const bounds = panel.plot.getBoundingClientRect();
    if (!bounds.width) return;
    const ratio = Math.min(2, window.devicePixelRatio || 1);
    panel.canvas.width = Math.round(bounds.width * ratio);
    panel.canvas.height = Math.round(bounds.height * ratio);
    panel.scaleX = bounds.width / VIEW.width;
    panel.scaleY = bounds.height / VIEW.height;
    panel.ratio = ratio;
  }

  function drawDot(context, point, x, y, opacity) {
    context.globalAlpha = opacity;
    context.beginPath();
    if (point.shape === 'circle') {
      context.arc(x, y, 1.8, 0, Math.PI * 2);
    } else {
      context.moveTo(x, y - 2.3);
      context.lineTo(x + 2.3, y);
      context.lineTo(x, y + 2.3);
      context.lineTo(x - 2.3, y);
      context.closePath();
    }
    context.fill();
  }

  function easeCubic(value) {
    return value < 0.5
      ? 4 * value * value * value
      : 1 - Math.pow(-2 * value + 2, 3) / 2;
  }

  function renderPanel(panel, elapsed) {
    const context = panel.context;
    context.setTransform(panel.ratio * panel.scaleX, 0, 0, panel.ratio * panel.scaleY, 0, 0);
    context.clearRect(0, 0, VIEW.width, VIEW.height);
    context.fillStyle = panel.color;

    const cycleTime = reducedMotion ? BUILD_MS + TRAVEL_MS + 100 : elapsed % CYCLE_MS;
    const fadeStart = BUILD_MS + TRAVEL_MS + HOLD_MS;
    const cycleOpacity = cycleTime > fadeStart ? Math.max(0, 1 - (cycleTime - fadeStart) / FADE_MS) : 1;

    panel.points.forEach(point => {
      const age = cycleTime - point.spawn;
      if (age < 0) return;
      let x = point.targetX;
      let y = point.targetY;
      let opacity = 0.82 * cycleOpacity;

      if (age < point.travel) {
        const progress = Math.max(0, Math.min(1, age / point.travel));
        const eased = easeCubic(progress);
        x = point.startX + (point.targetX - point.startX) * eased;
        y = point.startY + (point.targetY - point.startY) * eased;
        y -= Math.sin(progress * Math.PI) * (7 + 3 * Math.sin(point.phase));
        opacity *= Math.min(1, progress * 5);
      }
      drawDot(context, point, x, y, opacity);
    });
    context.globalAlpha = 1;
  }

  function animationLoop(now) {
    panels.forEach(panel => {
      if (!panel.visible && !reducedMotion) return;
      if (!panel.hasStarted) {
        panel.hasStarted = true;
        panel.startedAt = now;
      }
      renderPanel(panel, now - panel.startedAt);
    });
    if (!reducedMotion) animationFrame = requestAnimationFrame(animationLoop);
  }

  function installObserver() {
    observer?.disconnect();
    if (!('IntersectionObserver' in window) || reducedMotion) {
      panels.forEach(panel => { panel.visible = true; });
      return;
    }
    observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        const panel = panels.find(candidate => candidate.article === entry.target);
        if (!panel) return;
        panel.visible = entry.isIntersecting;
        if (entry.isIntersecting && !panel.hasStarted) {
          panel.startedAt = performance.now();
          panel.hasStarted = true;
        }
      });
    }, { rootMargin: '120px 0px' });
    panels.forEach(panel => observer.observe(panel.article));
  }

  function renderPanels() {
    observer?.disconnect();
    resizeObserver?.disconnect();
    grid.replaceChildren();
    panels = ordered.map(createPanel);
    panels.forEach(panel => resizeObserver?.observe(panel.plot));
    installObserver();
    if (reducedMotion) {
      panels.forEach(panel => renderPanel(panel, BUILD_MS + TRAVEL_MS + 100));
    }
  }

  function initialize() {
    try {
      validateConstants(data);
      resizeObserver = new ResizeObserver(entries => {
        entries.forEach(entry => {
          const panel = panels.find(candidate => candidate.plot === entry.target);
          if (!panel) return;
          sizeCanvas(panel);
          if (reducedMotion) renderPanel(panel, BUILD_MS + TRAVEL_MS + 100);
        });
      });
      ordered = [...data].sort((a, b) => d3.ascending(a.major, b.major));
      renderPanels();

      if (reducedMotion) {
        panels.forEach(panel => renderPanel(panel, BUILD_MS + TRAVEL_MS + 100));
      } else {
        animationFrame = requestAnimationFrame(animationLoop);
      }
    } catch (error) {
      console.error(error);
    }
  }

  initialize();

  window.addEventListener('pagehide', () => {
    if (animationFrame) cancelAnimationFrame(animationFrame);
    observer?.disconnect();
    resizeObserver?.disconnect();
  }, { once: true });
})();
