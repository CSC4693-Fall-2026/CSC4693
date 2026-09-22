const studentPath = '../../../Steel Thread/for_analysis/calpoly_scorecard.csv';
const facultyPath = '../../../Steel Thread/for_analysis/calpoly_major_medians.csv';

const state = { step: 'spread', data: [], scene: null };
const copy = {
  spread: { kicker: 'Five-year gap by major', title: 'The spread', note: 'Each colored line is one major-level median gap.' },
  converge: { kicker: 'Major gaps moving toward one value', title: 'Convergence', note: 'The lines retain their colors as they approach the average gap.' },
  average: { kicker: 'Average of major-level median gaps', title: 'The average gap', note: 'This is an average of gaps, not an average salary.' },
  separate: { kicker: 'The full distribution returns', title: 'Pull apart', note: 'The average is useful, but it hides the range between majors.' },
  extremes: { kicker: 'Largest and smallest five-year gaps', title: 'The extremes', note: 'Faculty median compensation minus student five-year median earnings.' },
  compare: { kicker: 'The two extremes, unpacked', title: 'Where the gaps come from', note: 'Each vertical range runs from student five-year median earnings to faculty median total compensation.' }
};

const toNumber = value => {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
};
const money = value => d3.format('$,.0f')(value);
const shortMajor = value => value.length > 22 ? `${value.slice(0, 20)}…` : value;
const palette = d3.scaleOrdinal(d3.schemeTableau10);

function loadData() {
  return Promise.all([d3.csv(studentPath), d3.csv(facultyPath)]).then(([students, faculty]) => {
    const facultyByMajor = new Map(faculty.map(row => [row.Major, toNumber(row.totalpaybenefits)]));
    state.data = students
      .filter(row => row.CREDDESC === "Bachelor's Degree")
      .map((row, index) => {
        const student = toNumber(row.EARN_MDN_5YR);
        const facultyPay = facultyByMajor.get(row.Major);
        return student && facultyPay ? {
          major: row.Major,
          student,
          faculty: facultyPay,
          gap: facultyPay - student,
          color: palette(index)
        } : null;
      })
      .filter(Boolean)
      .sort((a, b) => b.gap - a.gap);
  });
}

function renderChart() {
  const host = d3.select('#chart');
  host.selectAll('*').remove();
  const width = host.node().getBoundingClientRect().width;
  const height = Math.max(430, Math.min(620, state.data.length * 19));
  const margin = { top: 20, right: 62, bottom: 64, left: width < 600 ? 124 : 154 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;
  const svg = host.append('svg').attr('viewBox', `0 0 ${width} ${height}`);
  const root = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);
  const extent = d3.extent(state.data, row => row.gap);
  const domain = [Math.min(0, extent[0]) * 1.12, Math.max(0, extent[1]) * 1.12];
  const x = d3.scaleLinear().domain(domain).nice().range([0, innerWidth]);
  const y = d3.scaleBand().domain(state.data.map(row => row.major)).range([0, innerHeight]).padding(.32);
  const average = d3.mean(state.data, row => row.gap);
  const largest = state.data[0];
  const smallest = state.data[state.data.length - 1];
  const bars = ['Smallest gap', 'Average gap', 'Largest gap'];
  const barX = d3.scaleBand().domain(bars).range([innerWidth * .18, innerWidth * .82]).padding(.36);
  const barY = d3.scaleLinear()
    .domain([Math.min(0, smallest.gap) * 1.15, Math.max(0, largest.gap, average) * 1.15])
    .nice()
    .range([innerHeight, 0]);
  const comparisonData = [smallest, largest];
  const comparisonMajors = comparisonData.map(row => row.major);
  const compareX = d3.scaleBand().domain(comparisonMajors).range([innerWidth * .18, innerWidth * .82]).padding(.28);
  const compareMeasureX = d3.scaleBand().domain(['Student 5-year', 'Faculty total']).range([0, compareX.bandwidth()]).padding(.2);
  const compareMax = d3.max(comparisonData, row => Math.max(row.student, row.faculty));
  const compareY = d3.scaleLinear().domain([0, compareMax * 1.15]).nice().range([innerHeight, 0]);

  root.append('g').attr('class', 'grid').call(d3.axisBottom(x).ticks(6).tickSize(innerHeight).tickFormat(''));
  root.append('line').attr('class', 'zero-line').attr('x1', x(0)).attr('x2', x(0)).attr('y1', 0).attr('y2', innerHeight);
  root.append('g').attr('class', 'major-axis').call(d3.axisLeft(y).tickSize(0).tickPadding(8).tickFormat(label => label.length > 18 ? `${label.slice(0, 16)}…` : label));
  const xAxis = root.append('g').attr('class', 'axis x-axis').attr('transform', `translate(0,${innerHeight})`);
  xAxis.call(d3.axisBottom(x).ticks(6).tickFormat(d3.format('$,.0s')));
  root.append('text').attr('class', 'axis-label').attr('x', 0).attr('y', -8).text('GAP: FACULTY MEDIAN - STUDENT 5-YEAR MEDIAN');

  const cases = root.selectAll('.case').data(state.data, row => row.major).join('g').attr('class', 'case');
  cases.append('line').attr('class', 'gap-line').attr('stroke', row => row.color);
  cases.append('circle').attr('class', 'gap-point').attr('r', 4.5).attr('fill', row => row.color);
  cases.append('text').attr('class', 'case-label').text(row => row.major.length > 20 ? `${row.major.slice(0, 18)}…` : row.major);
  cases.append('text').attr('class', 'gap-value').text(row => `${row.gap >= 0 ? '+' : ''}${money(row.gap)}`);
  cases.append('rect').attr('class', 'summary-bar');
  cases.append('text').attr('class', 'summary-label');
  cases.append('text').attr('class', 'summary-value');
  root.append('rect').attr('class', 'average-bar');
  const compareGroup = root.append('g').attr('class', 'comparison-group');
  compareGroup.selectAll('.comparison-bar').data(comparisonData).join('rect').attr('class', 'comparison-bar').attr('fill', 'var(--gold)');
  compareGroup.selectAll('.comparison-value').data(comparisonData.flatMap(row => [
    { major: row.major, measure: 'Student 5-year', value: row.student, student: row.student, faculty: row.faculty },
    { major: row.major, measure: 'Faculty total', value: row.faculty, student: row.student, faculty: row.faculty }
  ])).join('text').attr('class', 'comparison-value').attr('text-anchor', 'middle').text(item => money(item.value));
  compareGroup.selectAll('.comparison-endpoint').data(comparisonData.flatMap(row => [
    { major: row.major, measure: 'Student 5-year', value: row.student, color: 'var(--student)' },
    { major: row.major, measure: 'Faculty total', value: row.faculty, color: 'var(--faculty)' }
  ])).join('circle').attr('class', 'comparison-endpoint').attr('r', 6).attr('fill', item => item.color);
  compareGroup.append('g').attr('class', 'comparison-y-axis');

  state.scene = { root, cases, x, y, xAxis, innerWidth, innerHeight, average, largest, smallest, barX, barY, comparisonGroup: compareGroup, compareX, compareMeasureX, compareY };
  updateChart();
}

function updateChart(duration = 700) {
  const scene = state.scene;
  if (!scene) return;
  const { root, cases, x, y, xAxis, innerWidth, innerHeight, average, largest, smallest, barX, barY, comparisonGroup, compareX, compareMeasureX, compareY } = scene;
  const { step } = state;
  const isCompare = step === 'compare';
  const summary = step === 'average' || step === 'separate' || step === 'extremes';
  const barsVisible = step === 'separate' || step === 'extremes';
  const barOpacity = step === 'extremes' ? .9 : .45;
  const splitState = step === 'separate' || step === 'extremes';
  const xAverage = x(average);
  const lineY = innerHeight / 2;
  const xTarget = row => step === 'converge' || step === 'average' ? xAverage : x(row.gap);
  const yTarget = row => step === 'converge' || step === 'average' ? lineY : y(row.major) + y.bandwidth() / 2;
  const summaryKey = row => row === smallest ? 'Smallest gap' : row === largest ? 'Largest gap' : null;
  const summaryX = row => summaryKey(row) ? barX(summaryKey(row)) + barX.bandwidth() / 2 : xAverage;

  xAxis.call(isCompare ? d3.axisBottom(compareX).tickSize(0).tickPadding(12) : summary ? d3.axisBottom(barX).tickSize(0).tickPadding(12) : d3.axisBottom(x).ticks(6).tickFormat(d3.format('$,.0s')));
  root.select('.grid').transition().duration(duration).style('opacity', summary || isCompare ? 0 : 1);
  root.select('.zero-line').transition().duration(duration).style('opacity', summary || isCompare ? 0 : 1);
  root.select('.axis-label').transition().duration(duration).style('opacity', summary || isCompare ? 0 : 1);
  root.select('.major-axis').transition().duration(duration).style('opacity', summary || isCompare ? 0 : 1);
  root.select('.comparison-group').transition().duration(duration).style('opacity', isCompare ? 1 : 0);
  root.select('.comparison-y-axis').call(d3.axisLeft(compareY).ticks(6).tickFormat(d3.format('$,.0s')));
  root.select('.comparison-y-axis').transition().duration(duration).style('opacity', isCompare ? 1 : 0);

  cases.select('.gap-line').transition().duration(duration)
    .attr('x1', row => splitState && summaryKey(row) ? xAverage : x(0))
    .attr('x2', row => splitState && summaryKey(row) ? summaryX(row) : xTarget(row))
    .attr('y1', row => yTarget(row)).attr('y2', row => yTarget(row))
    .attr('opacity', isCompare || step === 'average' ? 0 : splitState ? row => summaryKey(row) ? .55 : 0 : 1);
  cases.select('.gap-point').transition().duration(duration)
    .attr('cx', row => splitState && summaryKey(row) ? summaryX(row) : xTarget(row))
    .attr('cy', row => yTarget(row))
    .attr('opacity', isCompare || step === 'average' ? 0 : splitState ? row => summaryKey(row) ? .9 : 0 : 1);
  cases.select('.case-label').transition().duration(duration)
    .attr('x', row => step === 'converge' || step === 'average' ? xAverage + 10 : x(row.gap) + 8)
    .attr('y', row => yTarget(row) + 3)
    .attr('opacity', 0);
  cases.select('.gap-value').transition().duration(duration)
    .attr('x', row => xTarget(row) + 9).attr('y', row => yTarget(row) - 8)
    .attr('opacity', 0);

  const summaryBars = cases.select('.summary-bar');
  if (isCompare) summaryBars.interrupt().attr('opacity', 0);
  summaryBars.transition().duration(duration)
    .attr('x', row => summaryKey(row) ? barX(summaryKey(row)) : barX('Average gap'))
    .attr('width', barX.bandwidth())
    .attr('y', row => barsVisible && (row === smallest || row === largest) ? Math.min(barY(0), barY(row.gap)) : barY(0))
    .attr('height', row => barsVisible && (row === smallest || row === largest) ? Math.abs(barY(0) - barY(row.gap)) : 0)
    .attr('fill', row => row.color)
    .attr('opacity', row => isCompare ? 0 : barsVisible && summaryKey(row) ? barOpacity : 0);
  cases.select('.summary-label').transition().duration(duration)
    .attr('x', row => (summaryKey(row) ? barX(summaryKey(row)) : barX('Average gap')) + barX.bandwidth() / 2)
    .attr('y', innerHeight + 33).attr('text-anchor', 'middle')
    .text(row => row === smallest ? shortMajor(row.major) : row === largest ? shortMajor(row.major) : '')
    .attr('opacity', step === 'extremes' ? row => row === smallest || row === largest ? 1 : 0 : 0);
  cases.select('.summary-value').transition().duration(duration)
    .attr('x', row => (summaryKey(row) ? barX(summaryKey(row)) : barX('Average gap')) + barX.bandwidth() / 2)
    .attr('y', row => barsVisible && (row === smallest || row === largest) ? barY(row.gap) - 10 : barY(0))
    .attr('text-anchor', 'middle').text(row => `${row.gap >= 0 ? '+' : ''}${money(row.gap)}`)
    .attr('opacity', step === 'extremes' ? row => row === smallest || row === largest ? 1 : 0 : 0);

  root.select('.average-bar').transition().duration(duration)
    .attr('x', Math.min(x(0), xAverage))
    .attr('y', lineY - 18)
    .attr('width', Math.abs(xAverage - x(0)))
    .attr('height', 36)
    .attr('fill', 'var(--gold)')
    .attr('opacity', step === 'average' ? .95 : 0);

  comparisonGroup.selectAll('.comparison-bar').transition().duration(duration)
    .attr('x', item => compareX(item.major) + compareX.bandwidth() * .28)
    .attr('width', compareX.bandwidth() * .44)
    .attr('y', item => isCompare ? Math.min(compareY(item.student), compareY(item.faculty)) : compareY(0))
    .attr('height', item => isCompare ? Math.abs(compareY(item.student) - compareY(item.faculty)) : 0);
  comparisonGroup.selectAll('.comparison-value').transition().duration(duration)
    .attr('x', item => compareX(item.major) + compareX.bandwidth() / 2)
    .attr('y', item => compareY(item.value) + (item.value === Math.max(item.student, item.faculty) ? -10 : 19));
  comparisonGroup.selectAll('.comparison-endpoint').transition().duration(duration)
    .attr('cx', item => compareX(item.major) + compareX.bandwidth() / 2)
    .attr('cy', item => isCompare ? compareY(item.value) : compareY(0));

  if (step === 'average') {
    root.selectAll('.average-marker').data([average]).join('line').attr('class', 'average-marker')
      .attr('x1', xAverage).attr('x2', xAverage).attr('y1', 0).attr('y2', innerHeight);
    root.selectAll('.average-text').data([average]).join('text').attr('class', 'average-text')
      .attr('x', xAverage + 10).attr('y', lineY - 18).text(`Average gap: ${money(average)}`);
  } else {
    root.selectAll('.average-marker, .average-text').remove();
  }

  d3.select('#visual-kicker').text(copy[step].kicker);
  d3.select('#visual-title').text(copy[step].title);
  const note = step === 'average'
    ? `${copy[step].note} n = ${state.data.length}; average gap = ${money(average)}.`
    : copy[step].note;
  d3.select('#chart-note').text(note);
  const legendItems = isCompare
    ? [{ label: 'student 5-year median', color: 'var(--student)' }, { label: 'faculty total compensation', color: 'var(--faculty)' }]
    : [{ label: 'major-level gap', color: 'var(--faculty)' }, { label: 'zero reference', color: 'var(--student)' }];
  d3.select('#legend').html('');
  d3.select('#legend').selectAll('.legend-item').data(legendItems).join('div').attr('class', 'legend-item').html(item => `<span class="legend-swatch" style="background:${item.color}"></span>${item.label}`);
}

function setupScroll() {
  const chapters = [...document.querySelectorAll('.step')];
  const scroller = scrollama();
  const setStep = element => {
    const nextStep = element.dataset.step;
    if (nextStep === state.step) return;
    state.step = nextStep;
    d3.selectAll('.step').classed('is-active', false);
    d3.select(element).classed('is-active', true);
    updateChart();
  };
  scroller.setup({ step: '.step', offset: .58 }).onStepEnter(({ element }) => {
    setStep(element);
  });
  const fallbackScroll = () => {
    const trigger = window.innerHeight * .58;
    let active = chapters[0];
    chapters.forEach(chapter => { if (chapter.getBoundingClientRect().top <= trigger) active = chapter; });
    setStep(active);
  };
  window.addEventListener('scroll', fallbackScroll, { passive: true });
  let resizeTimer;
  window.addEventListener('resize', () => {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(() => { renderChart(); scroller.resize(); }, 140);
  });
  fallbackScroll();
}

loadData().then(() => { renderChart(); setupScroll(); }).catch(error => {
  d3.select('#chart-note').text('The data could not load. Serve the repository root through a local web server, then refresh.');
  console.error(error);
});
