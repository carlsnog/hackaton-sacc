const fmt = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });
const integer = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
const money = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
let municipalities = [];
let currentSort = { field: "taxa_abstencao_pct", order: "desc" };

function svgText(x, y, text, anchor = "middle") {
  return `<text class="label" x="${x}" y="${y}" text-anchor="${anchor}">${text}</text>`;
}

function renderScatter(items) {
  const svg = document.querySelector("#scatter");
  const valid = items.filter(item => item.renda_pc_mediana != null && item.taxa_abstencao_pct != null);
  const minX = Math.floor(Math.min(...valid.map(item => item.renda_pc_mediana)) / 100) * 100;
  const maxX = Math.ceil(Math.max(...valid.map(item => item.renda_pc_mediana)) / 200) * 200;
  const maxY = Math.ceil(Math.max(...valid.map(item => item.taxa_abstencao_pct)) / 5) * 5;
  const left = 68, right = 690, top = 24, bottom = 315;
  const x = value => left + (value - minX) / (maxX - minX) * (right - left);
  const y = value => bottom - value / maxY * (bottom - top);
  const xTicks = Array.from({ length: 6 }, (_, index) => minX + index * (maxX - minX) / 5);
  const yTicks = Array.from({ length: maxY / 5 + 1 }, (_, index) => index * 5);
  const gridX = xTicks.map(value => `<line class="grid" x1="${x(value)}" y1="${top}" x2="${x(value)}" y2="${bottom}"/>${svgText(x(value), 334, integer.format(value))}`).join("");
  const gridY = yTicks.map(value => `<line class="grid" x1="${left}" y1="${y(value)}" x2="${right}" y2="${y(value)}"/>${svgText(58, y(value) + 4, `${value}%`, "end")}`).join("");
  svg.innerHTML = `${gridX}${gridY}<line class="axis" x1="${left}" y1="${bottom}" x2="${right}" y2="${bottom}"/><line class="axis" x1="${left}" y1="${top}" x2="${left}" y2="${bottom}"/>
    ${svgText(375, 355, "Renda mediana mensal por pessoa (R$)")}${svgText(6, 16, "Eleitores ausentes (%)", "start")}` +
    valid.map(item => `<circle cx="${x(item.renda_pc_mediana)}" cy="${y(item.taxa_abstencao_pct)}" r="7"><title>${item.municipio}: ${fmt.format(item.taxa_abstencao_pct)}% ausentes | ${money.format(item.renda_pc_mediana)}</title></circle>`).join("");
}

function renderElectoralScatter(items) {
  const svg = document.querySelector("#electoral-scatter");
  const valid = items.filter(item => item.total_aptos > 0 && item.taxa_abstencao_pct != null);
  const minX = 10 ** Math.floor(Math.log10(Math.min(...valid.map(item => item.total_aptos))));
  const maxX = 10 ** Math.ceil(Math.log10(Math.max(...valid.map(item => item.total_aptos))));
  const maxY = Math.ceil(Math.max(...valid.map(item => item.taxa_abstencao_pct)) / 5) * 5;
  const left = 76, right = 690, top = 24, bottom = 315;
  const x = value => left + (Math.log10(value) - Math.log10(minX)) / (Math.log10(maxX) - Math.log10(minX)) * (right - left);
  const y = value => bottom - value / maxY * (bottom - top);
  const xTicks = Array.from({ length: Math.log10(maxX) - Math.log10(minX) + 1 }, (_, index) => minX * 10 ** index);
  const yTicks = Array.from({ length: maxY / 5 + 1 }, (_, index) => index * 5);
  const gridX = xTicks.map(value => `<line class="grid" x1="${x(value)}" y1="${top}" x2="${x(value)}" y2="${bottom}"/>${svgText(x(value), 334, integer.format(value))}`).join("");
  const gridY = yTicks.map(value => `<line class="grid" x1="${left}" y1="${y(value)}" x2="${right}" y2="${y(value)}"/>${svgText(66, y(value) + 4, `${value}%`, "end")}`).join("");
  svg.innerHTML = `${gridX}${gridY}<line class="axis" x1="${left}" y1="${bottom}" x2="${right}" y2="${bottom}"/><line class="axis" x1="${left}" y1="${top}" x2="${left}" y2="${bottom}"/>
    ${svgText(380, 355, "Aptos registrados no recorte (escala log)")}${svgText(6, 16, "Eleitores ausentes (%)", "start")}` +
    valid.map(item => `<circle cx="${x(item.total_aptos)}" cy="${y(item.taxa_abstencao_pct)}" r="7"><title>${item.municipio}: ${integer.format(item.total_aptos)} aptos registrados | ${fmt.format(item.taxa_abstencao_pct)}% ausentes</title></circle>`).join("");
}

function featureCode(feature) {
  const properties = feature.properties || {};
  return String(properties.cod_ibge_municipio || properties.CD_MUN || properties.CD_GEOCMU || properties.id || feature.id || "");
}

function coordinates(feature) {
  const geometry = feature.geometry || {};
  if (geometry.type === "Polygon") return geometry.coordinates;
  if (geometry.type === "MultiPolygon") return geometry.coordinates.flat();
  return [];
}

function renderMap(geojson, items) {
  const svg = document.querySelector("#heat-map");
  const fallback = document.querySelector("#map-fallback");
  const features = geojson.features || [];
  const points = features.flatMap(feature => coordinates(feature).flat());
  if (!points.length) throw new Error("GeoJSON municipal vazio");
  const xs = points.map(point => point[0]), ys = points.map(point => point[1]);
  const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
  const availableWidth = 650, availableHeight = 380;
  const scale = Math.min(availableWidth / (maxX - minX), availableHeight / (maxY - minY));
  const renderedWidth = (maxX - minX) * scale, renderedHeight = (maxY - minY) * scale;
  const offsetX = (720 - renderedWidth) / 2, offsetY = (460 - renderedHeight) / 2;
  const project = point => [offsetX + (point[0] - minX) * scale, offsetY + renderedHeight - (point[1] - minY) * scale];
  const byCode = Object.fromEntries(items.map(item => [item.cod_ibge_municipio, item]));
  const rates = items.map(item => item.taxa_abstencao_pct);
  const minRate = Math.min(...rates), maxRate = Math.max(...rates);
  const color = rate => {
    if (rate == null) return "#ded8cc";
    const intensity = (rate - minRate) / (maxRate - minRate || 1);
    const palette = ["#fbe2d8", "#edb29b", "#c95a2c", "#782f1a"];
    return palette[Math.min(palette.length - 1, Math.floor(intensity * palette.length))];
  };
  svg.innerHTML = features.map(feature => {
    const item = byCode[featureCode(feature)];
    const path = coordinates(feature).map(polygon => polygon.map((point, index) => {
      const [x, y] = project(point);
      return `${index ? "L" : "M"}${x.toFixed(2)},${y.toFixed(2)}`;
    }).join(" ") + " Z").join(" ");
    const tooltip = item ? `${item.municipio}: ${fmt.format(item.taxa_abstencao_pct)}% de eleitores ausentes` : `${feature.properties?.name || "Município"}: sem indicador socioeconômico cruzado`;
    return `<path class="municipality" d="${path}" fill="${color(item?.taxa_abstencao_pct)}"><title>${tooltip}</title></path>`;
  }).join("");
  fallback.textContent = "";
  document.querySelector("#map-legend").hidden = false;
}

async function loadMap(items) {
  try {
    const geoResponse = await fetch("/api/v1/geojson");
    if (!geoResponse.ok) throw new Error("malha indisponível");
    renderMap(await geoResponse.json(), items);
  } catch {
    document.querySelector("#heat-map").innerHTML = "";
    document.querySelector("#map-fallback").textContent =
      "O mapa de calor será exibido quando a malha municipal da Paraíba for adicionada aos dados locais. Os indicadores continuam disponíveis na tabela abaixo.";
  }
}

function renderRanking() {
  const direction = currentSort.order === "asc" ? 1 : -1;
  const sorted = [...municipalities].sort((a, b) => {
    if (typeof a[currentSort.field] === "string") return direction * a[currentSort.field].localeCompare(b[currentSort.field], "pt-BR");
    return direction * (a[currentSort.field] - b[currentSort.field]);
  });
  document.querySelector("#ranking").innerHTML = sorted.map(item =>
    `<tr><td>${item.municipio}</td><td>${integer.format(item.total_aptos)}</td><td>${fmt.format(item.taxa_abstencao_pct)}%</td><td>${money.format(item.renda_pc_mediana)}</td><td>${fmt.format(item.score_vulnerabilidade)}</td></tr>`
  ).join("");
  document.querySelectorAll(".sort").forEach(button => {
    const selected = button.dataset.sort === currentSort.field;
    button.dataset.direction = selected ? currentSort.order : "";
    button.setAttribute("aria-sort", selected ? (currentSort.order === "asc" ? "ascending" : "descending") : "none");
  });
}

async function load() {
  const [summary, ranking] = await Promise.all([
    fetch("/api/v1/resumo").then(response => response.json()),
    fetch("/api/v1/municipios?page_size=300&sort=taxa_abstencao_pct&order=desc").then(response => response.json())
  ]);
  municipalities = ranking.items;
  document.querySelector("#notice").textContent =
    `Análise territorial com ${summary.municipios_validos} municípios: ${fmt.format(summary.abrangencia_territorial_pct)}% das cidades paraibanas possuem dados eleitorais e socioeconômicos compatíveis.`;
  document.querySelector("#cards").innerHTML = [
    ["Municípios analisados", summary.municipios_validos, "Cidades com dados compatíveis para comparar ausência eleitoral e renda."],
    ["Eleitores ausentes", `${fmt.format(summary.taxa_abstencao_pct)}%`, "Percentual de pessoas aptas que não compareceram às urnas no recorte analisado."],
    ["Eleitores aptos na Paraíba", integer.format(summary.eleitores_aptos_paraiba), `Os ${summary.municipios_validos} municípios analisados abrangem ${fmt.format(summary.abrangencia_eleitores_paraiba_pct)}% dos eleitores aptos do estado.`],
    ["Cobertura territorial", `${fmt.format(summary.abrangencia_territorial_pct)}%`, `${summary.municipios_validos} de ${summary.municipios_paraiba} municípios possuem dados compatíveis para a análise.`]
  ].map(([label, value, description]) => `<article class="card"><span>${label}</span><strong>${value}</strong><small>${description}</small></article>`).join("");
  renderRanking();
  renderScatter(municipalities);
  renderElectoralScatter(municipalities);
  loadMap(municipalities);
}

document.querySelectorAll(".sort").forEach(button => button.addEventListener("click", () => {
  const field = button.dataset.sort;
  currentSort = { field, order: currentSort.field === field && currentSort.order === "desc" ? "asc" : "desc" };
  renderRanking();
}));

document.querySelector("#assistant-form").addEventListener("submit", async event => {
  event.preventDefault();
  const response = await fetch("/api/v1/assistant", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: document.querySelector("#question").value }) });
  document.querySelector("#answer").textContent = (await response.json()).answer;
});
load();
