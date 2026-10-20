(() => {
  'use strict';

  const GROUPS = [
    { name: 'Ladder faculty', roles: ['ladder_faculty'], color: '#2a78d6' },
    { name: 'Lecturers', roles: ['lecturer'], color: '#eb6834' },
    { name: 'Clinical / adjunct / in-residence', roles: ['clinical_adjunct_faculty'], color: '#1baf7a' },
    { name: 'TAs, readers, tutors', roles: ['teaching_assistant'], color: '#eda100' },
    { name: 'Grad student researchers', roles: ['grad_student_researcher'], color: '#e87ba4' },
    { name: 'Postdocs', roles: ['postdoc'], color: '#008300' },
    { name: 'Researchers, librarians, recalled', roles: ['researcher_specialist_librarian', 'recalled_emeriti'], color: '#6250d6' }
  ];
  const ROLE_NAMES = {
    researcher_specialist_librarian: 'Researchers, specialists, librarians',
    recalled_emeriti: 'Recalled emeriti'
  };
  const LABEL_MIN = 0.07;
  const ROW = 34;
  const BAR = 24;

  const raw = window.ROLE_MIX;
  const chart = document.querySelector('#chart');
  const tip = document.querySelector('#tooltip');
  const yearInput = document.querySelector('#year');
  const pct = d3.format('.0%');
  const pct1 = d3.format('.1%');
  const count = d3.format(',');
  const money = d3.format('$,.0f');
  const bigMoney = v => v >= 1e9 ? `$${(v / 1e9).toFixed(2)}B` : v >= 1e6 ? `$${(v / 1e6).toFixed(1)}M` : money(v);
  const textOn = c => d3.lab(c).l > 62 ? '#141414' : '#ffffff';

  const state = { measure: 'people', year: 2024 };

  const legend = d3.select('#legend');
  GROUPS.forEach(g => legend.append('span').style('--c', g.color).html(`<i></i>${g.name}`));

  function build(year, measure) {
    const rows = raw.filter(d => d.year === year);
    const buckets = d3.group(rows, d => d.bucket);
    const out = [];
    for (const [bucket, list] of buckets) {
      const byRole = new Map(list.map(d => [d.role, d]));
      const totals = { people: d3.sum(list, d => d.people), spend: d3.sum(list, d => d.spend) };
      let x0 = 0;
      const segs = GROUPS.map(g => {
        const parts = g.roles.map(r => byRole.get(r)).filter(Boolean);
        const people = d3.sum(parts, d => d.people);
        const spend = d3.sum(parts, d => d.spend);
        const share = (measure === 'people' ? people : spend) / totals[measure];
        const seg = { bucket, group: g, parts, people, spend, share, x0 };
        x0 += share;
        return seg;
      });
      const ladder = segs[0].share;
      out.push({ bucket, totals, segs, ladder });
    }
    return out.sort((a, b) => b.ladder - a.ladder);
  }

  function showTip(event, s) {
    const other = state.measure === 'people' ? 'spend' : 'people';
    const lines = [
      ['People', count(s.people)],
      ['Total pay', bigMoney(s.spend)],
      [state.measure === 'people' ? 'Share of people' : 'Share of pay', pct1(s.share)]
    ];
    if (s.parts.length === 1) lines.push(['Median pay', money(s.parts[0].median)]);
    else s.parts.forEach(p => lines.push([ROLE_NAMES[p.role] || p.role, `${count(p.people)} · med ${money(p.median)}`]));
    tip.innerHTML = `<strong>${s.group.name}</strong><div class="row"><span>${s.bucket}</span><span></span></div>` +
      lines.map(([k, v]) => `<div class="row"><span>${k}</span><span>${v}</span></div>`).join('');
    tip.hidden = false;
    moveTip(event);
  }

  function moveTip(event) {
    const pad = 14;
    const r = tip.getBoundingClientRect();
    let x = event.clientX + pad;
    let y = event.clientY + pad;
    if (x + r.width > window.innerWidth - 8) x = event.clientX - r.width - pad;
    if (y + r.height > window.innerHeight - 8) y = event.clientY - r.height - pad;
    tip.style.left = `${Math.max(8, x)}px`;
    tip.style.top = `${Math.max(8, y)}px`;
  }

  function hideTip() {
    tip.hidden = true;
    d3.selectAll('.seg').classed('dim', false);
  }

  function render(animate) {
    const data = build(state.year, state.measure);
    const width = chart.clientWidth;
    const narrow = width < 640;
    const labelW = narrow ? 0 : 230;
    const totalW = narrow ? 0 : 80;
    const labelGap = narrow ? 18 : 0;
    const rowH = ROW + labelGap;
    const top = 22;
    const height = top + data.length * rowH + 4;
    const x = d3.scaleLinear().domain([0, 1]).range([labelW, width - totalW]);
    const t = d3.transition().duration(animate ? 600 : 0).ease(d3.easeCubicOut);

    const svg = d3.select(chart).selectAll('svg').data([null]).join('svg')
      .attr('viewBox', `0 0 ${width} ${height}`)
      .attr('role', 'img');

    svg.selectAll('g.axis').data([null]).join('g').attr('class', 'axis')
      .attr('transform', `translate(0,${top - 6})`)
      .call(d3.axisTop(x).tickValues([0, .25, .5, .75, 1]).tickFormat(pct).tickSize(-(height - top)))
      .call(g => g.selectAll('.tick text').attr('dy', '-2px'));

    const rows = svg.selectAll('g.bucket').data(data, d => d.bucket).join(enter => {
      const g = enter.append('g').attr('class', 'bucket')
        .attr('transform', (d, i) => `translate(0,${top + i * rowH})`);
      g.append('text').attr('class', 'bucket-label');
      g.append('text').attr('class', 'total-label');
      return g;
    });

    rows.transition(t).attr('transform', (d, i) => `translate(0,${top + i * rowH})`);

    rows.select('.bucket-label')
      .attr('x', narrow ? 0 : labelW - 12)
      .attr('y', narrow ? 12 : labelGap + BAR / 2 + 6)
      .attr('dy', narrow ? 0 : '-0.15em')
      .attr('text-anchor', narrow ? 'start' : 'end')
      .attr('dominant-baseline', 'middle')
      .text(d => narrow ? `${d.bucket} · ${state.measure === 'people' ? count(d.totals.people) : bigMoney(d.totals.spend)}` : d.bucket);

    rows.select('.total-label')
      .attr('x', width - totalW + 10)
      .attr('y', labelGap + BAR / 2 + 6)
      .attr('dy', '-0.15em')
      .attr('dominant-baseline', 'middle')
      .text(d => narrow ? '' : state.measure === 'people' ? count(d.totals.people) : bigMoney(d.totals.spend));

    rows.each(function (row) {
      const g = d3.select(this);
      const y = labelGap + 6;
      g.selectAll('rect.seg').data(row.segs, d => d.group.name).join('rect')
        .attr('class', 'seg')
        .attr('y', y)
        .attr('height', BAR)
        .attr('fill', d => d.group.color)
        .attr('stroke', 'var(--paper)')
        .attr('stroke-width', 1.5)
        .on('pointerenter', (event, d) => {
          d3.selectAll('.seg').classed('dim', s => s.group !== d.group);
          showTip(event, d);
        })
        .on('pointermove', moveTip)
        .on('pointerleave', hideTip)
        .transition(t)
        .attr('x', d => x(d.x0))
        .attr('width', d => Math.max(0, x(d.x0 + d.share) - x(d.x0)));

      g.selectAll('text.seg-label').data(row.segs, d => d.group.name).join('text')
        .attr('class', 'seg-label')
        .attr('y', y + BAR / 2)
        .attr('dominant-baseline', 'central')
        .attr('text-anchor', 'middle')
        .attr('fill', d => textOn(d.group.color))
        .text(d => d.share >= LABEL_MIN && (x(d.share) - x(0)) > 28 ? pct(d.share) : '')
        .transition(t)
        .attr('x', d => x(d.x0 + d.share / 2));
    });

    svg.attr('aria-label', `Role share of ${state.measure === 'people' ? 'people' : 'pay'} per bucket, ${state.year}`);
  }

  document.querySelectorAll('.toggle button').forEach(btn => btn.addEventListener('click', () => {
    state.measure = btn.dataset.measure;
    document.querySelectorAll('.toggle button').forEach(b => b.setAttribute('aria-pressed', String(b === btn)));
    render(true);
  }));

  yearInput.addEventListener('input', () => {
    state.year = +yearInput.value;
    document.querySelector('#year-out').textContent = state.year;
    document.querySelector('#year-label').textContent = state.year;
    render(true);
  });

  let resizeTimer = null;
  new ResizeObserver(() => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => render(false), 80);
  }).observe(chart);

  chart.addEventListener('pointerleave', hideTip);
  render(false);
})();
