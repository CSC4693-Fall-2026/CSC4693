import * as d3 from "d3";
import scrollama from "scrollama";
import statesTopology from "us-atlas/states-10m.json";
import { feature } from "topojson-client";
import "./style.css";

const asset = (file) => `${import.meta.env.BASE_URL}data/${file}`;
const money = d3.format("$,.0f");
const svg = d3.select("#visualization");
const majorSvg = d3.select("#major-comparison-chart");
const tooltip = d3.select("#map-tooltip");
const status = d3.select("#graphic-status");
const mapLayer = svg.append("g").attr("class", "map-layer");
const states = feature(statesTopology, statesTopology.objects.states).features;
const california = states.find((item) => String(item.id).padStart(2, "0") === "06");
const story = { step: 0, schools: [], gaps: [], gapSchools: new Set() };
let resizeTimer;

Promise.all([
  d3.json(asset("derived/schools.json")),
  d3.json(asset("derived/calpoly-major-gaps.json")),
]).then(([schools, gaps]) => {
  story.schools = schools;
  story.gaps = gaps;
  const facultyHigher = schools.filter((d) => d.studentMinusFacultyGap < 0)
    .sort((a, b) => d3.ascending(a.studentMinusFacultyGap, b.studentMinusFacultyGap)).slice(0, 5);
  const studentsHigher = schools.filter((d) => d.studentMinusFacultyGap > 0)
    .sort((a, b) => d3.descending(a.studentMinusFacultyGap, b.studentMinusFacultyGap)).slice(0, 5);
  story.gapSchools = new Set([...facultyHigher, ...studentsHigher].map((d) => d.institution));
  render();
  setupScroller();
}).catch((error) => {
  console.error(error);
  d3.select(".graphic").append("p").attr("class", "load-error")
    .text("The visualization data could not be loaded. Run npm run prepare-data, then restart the development server.");
});

function graphicDimensions() {
  const container = document.querySelector(".graphic");
  return { width: container.clientWidth, height: Math.max(480, Math.min(window.innerHeight - 24, 760)) };
}

function scales() {
  const earningsExtent = d3.extent(story.schools, (d) => d.medianEarnings);
  const gapMaximum = d3.max(story.schools, (d) => Math.abs(d.studentMinusFacultyGap));
  return {
    earningsRadius: d3.scaleSqrt().domain(earningsExtent).range([4.5, 18]),
    gapColor: d3.scaleDiverging([-gapMaximum, 0, gapMaximum],
      d3.interpolateRgbBasis(["#2166ac", "#f7f7f7", "#b2182b"])),
    gapMaximum,
    earningsExtent,
  };
}

function render() {
  const { width, height } = graphicDimensions();
  svg.attr("viewBox", `0 0 ${width} ${height}`).attr("height", height);
  renderStoryMap(width, height);
  renderMajorChart();
  updateScene(false);
}

function renderStoryMap(width, height) {
  const projection = d3.geoMercator().fitExtent([[width * 0.18, 58], [width * 0.82, height - 42]], california);
  const path = d3.geoPath(projection);
  const { earningsRadius, gapColor, gapMaximum, earningsExtent } = scales();
  mapLayer.selectAll("*").remove();
  mapLayer.append("path").datum(california).attr("class", "state-shape").attr("d", path);

  const dots = mapLayer.append("g").attr("class", "school-dots").selectAll("circle")
    .data(story.schools, (d) => d.institution).join("circle")
    .attr("cx", (d) => projection([d.longitude, d.latitude])[0])
    .attr("cy", (d) => projection([d.longitude, d.latitude])[1])
    .attr("data-earnings-radius", (d) => earningsRadius(d.medianEarnings))
    .attr("data-gap-color", (d) => gapColor(d.studentMinusFacultyGap))
    .attr("data-gap-school", (d) => story.gapSchools.has(d.institution) ? "true" : "false")
    .attr("tabindex", 0).attr("role", "img")
    .attr("aria-label", (d) => `${d.institution}, ${money(d.medianEarnings)} median graduate earnings`)
    .on("pointerover pointermove mouseover mousemove", (event, d) => showStoryTooltip(event, d))
    .on("pointerout mouseout blur", hideStoryTooltip)
    .on("focus click", (event, d) => showStoryTooltip(event, d));

  const calPoly = story.schools.find((d) => d.institution === "California Polytechnic State University-San Luis Obispo");
  if (calPoly) {
    const [x, y] = projection([calPoly.longitude, calPoly.latitude]);
    mapLayer.attr("data-calpoly-x", x).attr("data-calpoly-y", y);
    mapLayer.append("circle").attr("class", "calpoly-ring").attr("cx", x).attr("cy", y).attr("r", 24);
    mapLayer.append("text").attr("class", "calpoly-label").attr("x", x + 18).attr("y", y - 18).text("Cal Poly");
  }
  drawEarningsSizeLegend(mapLayer, 28, height - 92, earningsRadius, earningsExtent, "story-earnings-legend");
  drawGapLegend(mapLayer, width - 260, height - 82, gapColor, gapMaximum, "story-gap-legend");
}

function renderMajorChart() {
  const container = document.querySelector(".major-chart-wrap");
  if (!container) return;
  const width = Math.max(container.clientWidth, 700);
  const height = Math.max(580, story.gaps.length * 48 + 120);
  majorSvg.attr("viewBox", `0 0 ${width} ${height}`).attr("height", height).selectAll("*").remove();
  const margin = { top: 48, right: 42, bottom: 48, left: Math.max(150, width * 0.25) };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;
  const values = story.gaps.flatMap((d) => [d.facultyCompensation, d.graduateEarnings]);
  const x = d3.scaleLinear().domain([0, d3.max(values) * 1.08]).range([0, innerWidth]).nice();
  const y = d3.scaleBand().domain(story.gaps.map((d) => d.major)).range([0, innerHeight]).padding(0.34);
  const root = majorSvg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);
  const secondGroupIndex = story.gaps.findIndex((d) => d.comparisonGroup === "Smallest or negative gaps");
  root.append("text").attr("class", "comparison-group-label").attr("x", 0).attr("y", -16)
    .text("FIVE LARGEST FACULTY-OVER-GRADUATE GAPS");
  if (secondGroupIndex >= 0) {
    root.append("text").attr("class", "comparison-group-label").attr("x", 0)
      .attr("y", y(story.gaps[secondGroupIndex].major) - 6).text("FIVE SMALLEST OR NEGATIVE GAPS");
  }
  root.append("g").attr("class", "x-axis").attr("transform", `translate(0,${innerHeight})`).call(d3.axisBottom(x).ticks(5).tickFormat(money));
  root.append("g").attr("class", "y-axis").call(d3.axisLeft(y).tickSize(0));
  const rows = root.append("g").selectAll("g").data(story.gaps).join("g");
  rows.append("line").attr("class", "gap-line").attr("x1", (d) => x(d.graduateEarnings)).attr("x2", (d) => x(d.facultyCompensation)).attr("y1", (d) => y(d.major) + y.bandwidth() / 2).attr("y2", (d) => y(d.major) + y.bandwidth() / 2);
  rows.append("circle").attr("class", "graduate-dot").attr("cx", (d) => x(d.graduateEarnings)).attr("cy", (d) => y(d.major) + y.bandwidth() / 2).attr("r", 4.5);
  rows.append("circle").attr("class", "faculty-dot").attr("cx", (d) => x(d.facultyCompensation)).attr("cy", (d) => y(d.major) + y.bandwidth() / 2).attr("r", 4.5);
}

function drawEarningsSizeLegend(layer, x, y, radius, extent, className) {
  const legend = layer.append("g").attr("class", className).attr("transform", `translate(${x},${y})`);
  legend.append("text").attr("class", "legend-title").attr("y", -16).text("DOT SIZE · FIVE-YEAR GRADUATE EARNINGS");
  const values = [extent[0], d3.mean(extent), extent[1]];
  values.forEach((value, index) => {
    const cx = 18 + index * 86;
    legend.append("circle").attr("cx", cx).attr("cy", 10).attr("r", radius(value)).attr("class", "legend-bubble");
    legend.append("text").attr("x", cx).attr("y", 42).attr("text-anchor", "middle").text(money(value));
  });
}

function drawGapLegend(layer, x, y, color, maximum, className) {
  const safeX = Math.max(20, x);
  const legend = layer.append("g").attr("class", className).attr("transform", `translate(${safeX},${y})`);
  const gradientId = `${className}-gradient`;
  const defs = layer.selectAll("defs").data([null]).join("defs");
  const gradient = defs.append("linearGradient").attr("id", gradientId).attr("x1", "0%").attr("x2", "100%");
  gradient.selectAll("stop").data(d3.range(0, 1.01, 0.1)).join("stop")
    .attr("offset", (d) => `${d * 100}%`).attr("stop-color", (d) => color(-maximum + d * maximum * 2));
  legend.append("text").attr("class", "legend-title").attr("y", -16).text("COLOR · STUDENT EARNINGS MINUS FACULTY BENCHMARK");
  legend.append("rect").attr("width", 240).attr("height", 12).attr("rx", 2).attr("fill", `url(#${gradientId})`);
  legend.append("text").attr("y", 30).text("Faculty higher");
  legend.append("text").attr("x", 120).attr("y", 30).attr("text-anchor", "middle").text("$0 gap");
  legend.append("text").attr("x", 240).attr("y", 30).attr("text-anchor", "end").text("Students higher");
}

function updateScene(animate = true) {
  const duration = window.matchMedia("(prefers-reduced-motion: reduce)").matches || !animate ? 0 : 750;
  const calPolyX = Number(mapLayer.attr("data-calpoly-x"));
  const calPolyY = Number(mapLayer.attr("data-calpoly-y"));
  const zoom = story.step === 3 ? 2.05 : 1;
  const tx = story.step === 3 ? calPolyX - calPolyX * zoom : 0;
  const ty = story.step === 3 ? calPolyY - calPolyY * zoom : 0;
  mapLayer.transition().duration(duration).attr("transform", `translate(${tx},${ty}) scale(${zoom})`)
    .style("opacity", 1);
  d3.select(".map-header").transition().duration(duration).style("opacity", 1);

  mapLayer.selectAll(".school-dots circle").transition().duration(duration)
    .attr("opacity", function (d) {
      if (story.step === 0) return 0.82;
      if (story.step === 1) return story.gapSchools.has(d.institution) ? 0.98 : 0;
      if (story.step === 2) return 0.9;
      return d.institution === "California Polytechnic State University-San Luis Obispo" ? 1 : 0.06;
    })
    .attr("r", function (d) {
      if (story.step === 0) return Number(d3.select(this).attr("data-earnings-radius"));
      if (story.step === 1) return story.gapSchools.has(d.institution) ? 10 : 2;
      if (story.step === 2) return Number(d3.select(this).attr("data-earnings-radius"));
      return d.institution === "California Polytechnic State University-San Luis Obispo" ? 13 : 3;
    })
    .attr("fill", function (d) {
      if (story.step === 1) return d3.select(this).attr("data-gap-color");
      if (story.step === 0) return "#397f99";
      if (story.step === 2) return d3.select(this).attr("data-gap-color");
      return "#6e8790";
    })
    .style("pointer-events", (d) => {
      if (story.step === 0) return "all";
      if (story.step === 1) return story.gapSchools.has(d.institution) ? "all" : "none";
      if (story.step === 2) return "all";
      return d.institution === "California Polytechnic State University-San Luis Obispo" ? "all" : "none";
    });
  mapLayer.select(".story-earnings-legend").transition().duration(duration).style("opacity", story.step === 0 || story.step === 2 ? 1 : 0);
  mapLayer.select(".story-gap-legend").transition().duration(duration).style("opacity", story.step === 1 || story.step === 2 ? 1 : 0);
  mapLayer.selectAll(".calpoly-ring, .calpoly-label").transition().duration(duration).style("opacity", story.step === 3 ? 1 : 0);
  hideStoryTooltip();
  status.text(["Schools sized by five-year graduate earnings.", "Ten schools colored by the proof-of-concept pay gap.", "Complete map with both encodings.", "Cal Poly campus focus."][story.step]);
}

function storyTooltipHtml(d) {
  const base = `<strong>${d.institution}</strong><span>${d.city}, California</span><span>Graduate earnings: ${money(d.medianEarnings)}</span>`;
  if (story.step === 0) return base;
  const direction = d.studentMinusFacultyGap >= 0 ? "students higher" : "faculty benchmark higher";
  return `${base}<span>Cal Poly faculty benchmark: ${money(d.facultyBenchmark)}</span><span>Gap: ${money(Math.abs(d.studentMinusFacultyGap))} · ${direction}</span>`;
}

function positionTooltip(selection, event, containerSelector) {
  const bounds = document.querySelector(containerSelector).getBoundingClientRect();
  const x = event.clientX ? event.clientX - bounds.left + 14 : bounds.width / 2;
  const y = event.clientY ? event.clientY - bounds.top + 14 : bounds.height / 2;
  selection.style("left", `${Math.max(8, Math.min(x, bounds.width - 250))}px`)
    .style("top", `${Math.max(8, Math.min(y, bounds.height - 145))}px`)
    .attr("aria-hidden", "false").classed("is-visible", true);
}

function showStoryTooltip(event, d) {
  tooltip.html(storyTooltipHtml(d));
  positionTooltip(tooltip, event, ".graphic");
}
function hideStoryTooltip() { tooltip.attr("aria-hidden", "true").classed("is-visible", false); }
function setupScroller() {
  const scroller = scrollama();
  scroller.setup({ step: ".step", offset: 0.58 }).onStepEnter(({ element }) => {
    story.step = Number(element.dataset.step);
    updateScene();
  });
  window.addEventListener("resize", () => {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(() => { render(); scroller.resize(); }, 140);
  });
}
