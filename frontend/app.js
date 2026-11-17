const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

async function api(url, opts) {
  const r = await fetch(url, opts);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || `Error ${r.status}`);
  return data;
}

// ---------------- CV base ----------------
function mostrarCvBase(d) {
  if (!d.existe) {
    $("cv-estado").innerHTML = "Aún no has subido tu CV.";
    $("cv-preview-box").hidden = true;
    return;
  }
  $("cv-estado").innerHTML = `✅ <b>${esc(d.archivo)}</b> · ${d.caracteres} caracteres · ${esc(d.actualizado)}`;
  $("cv-preview").textContent = d.texto;
  $("cv-preview-box").hidden = false;
}
$("cv-file").onchange = async (e) => {
  const f = e.target.files[0];
  if (!f) return;
  const fd = new FormData();
  fd.append("cv", f);
  $("cv-estado").textContent = "Leyendo CV…";
  try { mostrarCvBase(await api("/api/cv-base", { method: "POST", body: fd })); }
  catch (err) { $("cv-estado").innerHTML = `<span style="color:var(--err)">${esc(err.message)}</span>`; }
  e.target.value = "";
};

// ---------------- Motor de IA ----------------
let ajustes = {};
const proveedorSel = () => document.querySelector('input[name="proveedor"]:checked')?.value;
const esLocal = (p) => p === "lmstudio" || p === "ollama";
const PLACEHOLDER = { lmstudio: "http://localhost:1234/v1 o 192.168.1.20:1234", ollama: "http://localhost:11434 o 192.168.1.20" };

function mostrarAjustes(a) {
  ajustes = a;
  const p = a.proveedor;
  $("motor-nombre").textContent = a.motor;
  document.querySelector(`input[name="proveedor"][value="${p}"]`).checked = true;
  $("motor-claude").innerHTML = a.claude_instalado
    ? "Usa Claude Code con tu sesión de claude.ai (sin API key)."
    : `<span style="color:var(--err)">No encuentro Claude Code. Instálalo con <code>npm install -g @anthropic-ai/claude-code</code> e inicia sesión con <code>claude</code>.</span>`;
  $("motor-claude").hidden = p !== "claude";
  $("motor-local").hidden = !esLocal(p);
  if (!esLocal(p)) return;

  $("lm-url").value = a[`${p}_url`];
  $("lm-url").placeholder = PLACEHOLDER[p];
  $("lm-key-box").hidden = p !== "lmstudio";
  $("lm-key").placeholder = a.tiene_api_key ? "•••• guardada (escribe otra para cambiarla)" : "Solo si activaste autenticación en el servidor";
  $("ayuda-lmstudio").hidden = p !== "lmstudio";
  $("ayuda-ollama").hidden = p !== "ollama";
  const sel = $("lm-modelo"), modelo = a[`${p}_modelo`];
  if (sel.dataset.proveedor !== p) {  // al cambiar de proveedor, la lista anterior ya no sirve
    sel.dataset.proveedor = p;
    sel.innerHTML = modelo ? `<option value="${esc(modelo)}">${esc(modelo)}</option>` : '<option value="">Primero pulsa Conectar</option>';
    $("lm-estado").textContent = "";
  }
  sel.value = modelo;
}

async function guardarAjustes(extra = {}) {
  const p = proveedorSel(), datos = { proveedor: p, ...extra };
  if (esLocal(p) && $("lm-modelo").dataset.proveedor === p) {
    datos[`${p}_url`] ??= $("lm-url").value;
    datos[`${p}_modelo`] ??= $("lm-modelo").value;
  }
  if (p === "lmstudio" && $("lm-key").value) datos.lmstudio_api_key = $("lm-key").value;
  mostrarAjustes(await api("/api/ajustes", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(datos) }));
  $("lm-key").value = "";
}

async function conectarLocal() {
  const p = proveedorSel();
  $("lm-estado").textContent = "Conectando…";
  $("lm-conectar").disabled = true;
  try {
    const d = await api("/api/ajustes/modelos", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ proveedor: p, url: $("lm-url").value, api_key: p === "lmstudio" ? $("lm-key").value : "" }) });
    if (!d.modelos.length) throw new Error(p === "ollama"
      ? "Conectado, pero Ollama no tiene modelos. Descarga uno con: ollama pull qwen2.5:7b"
      : "Conectado, pero no hay modelos descargados en LM Studio.");
    const previo = ajustes[`${p}_modelo`];
    $("lm-modelo").innerHTML = d.modelos.map((m) => `<option value="${esc(m)}">${esc(m)}</option>`).join("");
    $("lm-modelo").value = d.modelos.includes(previo) ? previo : d.modelos[0];
    await guardarAjustes({ [`${p}_url`]: d.url, [`${p}_modelo`]: $("lm-modelo").value });
    $("lm-estado").innerHTML = `<span style="color:var(--ok)">✅ Conectado · ${d.modelos.length} modelo(s)</span>`;
  } catch (err) {
    $("lm-estado").innerHTML = `<span style="color:var(--err)">${esc(err.message)}</span>`;
  } finally {
    $("lm-conectar").disabled = false;
  }
}

document.querySelectorAll('input[name="proveedor"]').forEach((r) => (r.onchange = async () => {
  await guardarAjustes();
  if (esLocal(proveedorSel())) conectarLocal();
}));
$("lm-conectar").onclick = conectarLocal;
$("lm-modelo").onchange = () => guardarAjustes();

// ---------------- Generar ----------------
const PASOS_CV = ["Leyendo la vacante…", "Extrayendo palabras clave y requisitos…", "Comparando con tu CV…",
  "Reescribiendo el CV para el ATS…", "Generando carta, correo y preguntas probables…", "Ajustando a 2 páginas…", "Casi listo…"];
const PASOS_CORREO = ["Leyendo la vacante…", "Redactando el correo…", "Casi listo…"];

function actualizarBoton() {
  const cv = $("chk-cv").checked, correo = $("chk-correo").checked;
  $("btn").textContent = cv && correo ? "Generar CV y correo" : cv ? "Generar CV" : correo ? "Redactar correo" : "Marca una opción";
  $("btn").disabled = !(cv || correo);
}
$("chk-cv").onchange = $("chk-correo").onchange = actualizarBoton;

$("btn").onclick = async () => {
  const conCv = $("chk-cv").checked;
  const fd = new FormData();
  fd.append("vacante_texto", $("vacante").value);
  fd.append("vacante_url", $("url").value);
  fd.append("notas", $("notas").value);
  fd.append("generar_cv", conCv);
  fd.append("generar_correo", $("chk-correo").checked);
  const pasos = conCv ? PASOS_CV : PASOS_CORREO;
  $("btn").disabled = true;
  const t0 = Date.now();
  $("progreso").hidden = false;
  const timer = setInterval(() => {
    const s = Math.round((Date.now() - t0) / 1000);
    $("progreso").textContent = `${pasos[Math.min(Math.floor(s / (conCv ? 22 : 12)), pasos.length - 1)]} (${s}s)`;
  }, 500);
  try {
    mostrarResultado(await api("/api/optimizar", { method: "POST", body: fd }));
    cargarHistorial();
  } catch (err) {
    $("resultado").innerHTML = `<div class="empty" style="color:var(--err)">${esc(err.message)}</div>`;
  } finally {
    clearInterval(timer);
    $("progreso").hidden = true;
    actualizarBoton();
  }
};

// ---------------- Resultado ----------------
function mostrarResultado(r) {
  const a = r.analisis;
  let html = `<p class="titulo-vacante">${esc(a.cargo_vacante)}${a.empresa ? " · " + esc(a.empresa) : ""}
    <span class="muted" style="font-weight:400;font-size:13px"> ${esc(a.seniority || "")} · ${esc(r.fecha)}${r.motor ? " · " + esc(r.motor) : ""}</span></p>`;

  if (r.cv) {
    const c = r.cobertura;
    const agregadas = c.palabras.filter((p) => p.estado === "agregada");
    html += `
      <div class="scores">
        <div class="score"><div class="label">Compatibilidad (estimación de la IA)</div>
          <div class="val">${a.puntaje_original} <small>→</small> ${a.puntaje_optimizado}</div></div>
        <div class="score"><div class="label">Cobertura de palabras clave (medida por la app)</div>
          <div class="val">${c.original}% <small>→</small> ${c.optimizado}%</div></div>
        <div class="score"><div class="label">Extensión del PDF</div>
          <div class="val" style="color:${r.paginas > 2 ? "var(--err)" : "inherit"}">${r.paginas ?? "?"} <small>página(s)</small></div></div>
        <div class="score"><div class="label">Requisitos que cumples</div>
          <div class="val">${a.requisitos.filter((x) => x.cumple === "si").length} <small>/ ${a.requisitos.length}</small></div></div>
      </div>
      ${agregadas.length ? `<div class="aviso">⚠️ Estas palabras clave <b>no estaban escritas en tu CV original</b> y ahora sí:
        <b>${agregadas.map((p) => esc(p.termino)).join(", ")}</b>. Revisa en la vista previa que cada una sea cierta
        antes de enviar el CV.</div>` : ""}
      <div class="downloads">
        <a href="${r.archivos.pdf}" download>⬇ ${esc(r.nombre_archivo)}</a>
        <a href="${r.archivos.docx}" download>⬇ Word (.docx)</a>
        <a href="${r.archivos.md}" download>⬇ Markdown</a>
        <button data-accion="abrir">📂 Abrir carpeta</button>
        <button data-accion="copilot">→ Enviar a Interview Copilot</button>
      </div>`;
  }

  if (r.correo) html += correoHtml(r);

  const tabs = r.cv ? {
    "Palabras clave": tabPalabras(r.cobertura),
    "Requisitos": tabRequisitos(a.requisitos),
    "Brechas y cambios": tabListas(a),
    "Vista previa CV": cvHtml(r.cv),
    "Carta": `<div class="carta">${esc(r.carta_presentacion)}</div>`,
    "Preguntas probables": `<ul class="lista">${a.preguntas_probables.map((p) => `<li>${esc(p)}</li>`).join("")}</ul>`,
  } : null;
  if (tabs) {
    html += `<div class="tabs">${Object.keys(tabs).map((t, i) => `<button data-i="${i}" class="${i ? "" : "on"}">${t}</button>`).join("")}</div>
      <div class="panel" id="panel">${Object.values(tabs)[0]}</div>`;
  }
  $("resultado").innerHTML = html;

  if (tabs) document.querySelectorAll(".tabs button").forEach((b) => (b.onclick = () => {
    document.querySelectorAll(".tabs button").forEach((x) => x.classList.remove("on"));
    b.classList.add("on");
    $("panel").innerHTML = Object.values(tabs)[b.dataset.i];
  }));
  document.querySelectorAll("[data-accion]").forEach((b) => (b.onclick = async () => {
    try {
      if (b.dataset.accion === "abrir") await api(`/api/abrir/${r.id}`, { method: "POST" });
      if (b.dataset.accion === "copilot") {
        const d = await api(`/api/copilot/${r.id}`, { method: "POST" });
        alert(`Listo: CV y vacante copiados a ${d.destino}`);
      }
    } catch (err) { alert(err.message); }
  }));
  document.querySelectorAll("[data-copiar]").forEach((b) => (b.onclick = async () => {
    await navigator.clipboard.writeText(b.dataset.copiar === "asunto" ? r.correo.asunto
      : b.dataset.copiar === "para" ? r.correo.destinatario : r.correo.cuerpo);
    const t = b.textContent; b.textContent = "✓ Copiado"; setTimeout(() => (b.textContent = t), 1200);
  }));
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function correoHtml(r) {
  const c = r.correo;
  const q = encodeURIComponent;
  const gmail = `https://mail.google.com/mail/?view=cm&fs=1&to=${q(c.destinatario)}&su=${q(c.asunto)}&body=${q(c.cuerpo)}`;
  const outlook = `https://outlook.office.com/mail/deeplink/compose?to=${q(c.destinatario)}&subject=${q(c.asunto)}&body=${q(c.cuerpo)}`;
  return `<div class="correo">
    <h3>✉️ Correo de postulación</h3>
    <div class="campo"><div><span class="k">Para</span>${esc(c.destinatario) || '<span class="muted">(la vacante no trae correo: búscalo en la oferta o en LinkedIn)</span>'}</div>
      ${c.destinatario ? '<button data-copiar="para">Copiar</button>' : ""}</div>
    <div class="campo"><div><span class="k">Asunto</span>${esc(c.asunto)}</div><button data-copiar="asunto">Copiar</button></div>
    <div class="campo"><div class="cuerpo"><span class="k">Mensaje</span>${esc(c.cuerpo)}</div><button data-copiar="cuerpo">Copiar</button></div>
    <div class="downloads" style="margin-bottom:0">
      <a href="${gmail}" target="_blank" rel="noopener">Abrir en Gmail</a>
      <a href="${outlook}" target="_blank" rel="noopener">Abrir en Outlook</a>
      ${!r.cv ? '<button data-accion="abrir">📂 Abrir carpeta</button>' : ""}
    </div>
    <div class="adjunto">📎 Recuerda adjuntar el CV a mano:
      ${r.nombre_archivo ? `<code>${esc(r.nombre_archivo)}</code> en <code>${esc(r.carpeta)}</code>` : "aún no generaste un CV para esta vacante."}</div>
  </div>`;
}

function tabPalabras(c) {
  const orden = { faltante: 0, perdida: 1, agregada: 2, presente: 3 };
  const ps = [...c.palabras].sort((x, y) => orden[x.estado] - orden[y.estado]);
  const grupo = (imp) => `<div class="chips">${ps.filter((p) => p.importancia === imp).map((p) =>
    `<span class="chip ${p.estado}" title="${esc(p.categoria)} · ${esc(p.estado)}${p.sinonimos.length ? " · variantes: " + esc(p.sinonimos.join(", ")) : ""}">
      ${p.importancia === "obligatoria" ? "<b>" + esc(p.termino) + "</b>" : esc(p.termino)}</span>`).join("")}</div>`;
  return `<h3 style="margin-top:0">Obligatorias</h3>${grupo("obligatoria")}<h3>Deseables</h3>${grupo("deseable")}
    <div class="legend">🟢 ya estaba y se mantiene · 🟡 agregada en la versión optimizada (verifica que sea cierta) ·
    🔴 no aparece en el CV optimizado (revisa la pestaña Brechas)</div>`;
}

function tabRequisitos(reqs) {
  return `<table><tr><th>Requisito</th><th></th><th>Evidencia en tu CV</th></tr>${reqs.map((r) =>
    `<tr><td>${esc(r.requisito)}</td><td><span class="tag ${r.cumple}">${{ si: "Cumple", parcial: "Parcial", no: "No" }[r.cumple]}</span></td>
     <td class="muted">${esc(r.evidencia)}</td></tr>`).join("")}</table>`;
}

function tabListas(a) {
  const l = (t, xs) => xs.length ? `<h3>${t}</h3><ul class="lista">${xs.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : "";
  return l("Brechas: lo que pide la vacante y tu CV no respalda (no se agregó)", a.brechas)
    + l("Cambios realizados", a.cambios)
    + l("Problemas de formato ATS en tu CV original", a.alertas_formato)
    + l("Recomendaciones", a.recomendaciones);
}

function cvHtml(cv) {
  const c = cv.contacto;
  const contacto = ["ubicacion", "telefono", "email", "linkedin", "github", "portafolio"].map((k) => c[k]).filter(Boolean).join(" | ");
  const fechas = (a, b) => `${esc(a)} – ${esc(b || "Actualidad")}`;
  return `<div class="cv-preview">
    <h1>${esc(cv.nombre)}</h1><div class="tit">${esc(cv.titular)}</div><div class="con">${esc(contacto)}</div>
    ${cv.resumen ? `<h2>Resumen</h2><p>${esc(cv.resumen)}</p>` : ""}
    ${cv.habilidades.length ? `<h2>Habilidades</h2>${cv.habilidades.map((h) => `<div><b>${esc(h.categoria)}:</b> ${esc(h.items.join(", "))}</div>`).join("")}` : ""}
    ${cv.experiencia.length ? `<h2>Experiencia</h2>${cv.experiencia.map((e) => `
      <div style="margin-top:10px"><b>${esc(e.cargo)}</b> | ${esc(e.empresa)}</div>
      <div class="meta">${fechas(e.fecha_inicio, e.fecha_fin)}${e.ubicacion ? " | " + esc(e.ubicacion) : ""}</div>
      ${e.contexto ? `<div><i>${esc(e.contexto)}</i></div>` : ""}
      <ul>${e.logros.map((l) => `<li>${esc(l)}</li>`).join("")}</ul>
      ${e.tecnologias.length ? `<div><b>Tecnologías:</b> ${esc(e.tecnologias.join(", "))}</div>` : ""}`).join("")}` : ""}
    ${cv.educacion.length ? `<h2>Educación</h2>${cv.educacion.map((e) => `<div><b>${esc(e.titulo)}</b> | ${esc(e.institucion)} | ${fechas(e.fecha_inicio, e.fecha_fin)}</div>`).join("")}` : ""}
    ${cv.certificaciones.length ? `<h2>Certificaciones</h2><ul>${cv.certificaciones.map((x) => `<li>${esc(x.nombre)} | ${esc(x.entidad)} ${esc(x.fecha)}</li>`).join("")}</ul>` : ""}
    ${cv.idiomas.length ? `<h2>Idiomas</h2><ul>${cv.idiomas.map((i) => `<li>${esc(i.idioma)}: ${esc(i.nivel)}</li>`).join("")}</ul>` : ""}
  </div>`;
}

// ---------------- Historial ----------------
async function cargarHistorial() {
  const items = await api("/api/historial");
  if (!items.length) { $("historial").textContent = "Aún no hay vacantes procesadas."; return; }
  $("historial").innerHTML = items.map((i) =>
    `<button class="hist-item" data-id="${esc(i.id)}">${esc(i.cargo)}<small>${esc(i.empresa)} · ${esc(i.fecha)}
      ${i.tiene_cv ? ` · CV ${i.puntaje ?? ""}/100` : ""}${i.tiene_correo ? " · ✉️" : ""}</small></button>`).join("");
  document.querySelectorAll(".hist-item").forEach((b) => (b.onclick = async () => mostrarResultado(await api(`/api/resultado/${b.dataset.id}`))));
}

actualizarBoton();
api("/api/ajustes").then((a) => { mostrarAjustes(a); if (a.proveedor === "claude" && !a.claude_instalado) $("motor-box").open = true; });
api("/api/cv-base").then(mostrarCvBase);
cargarHistorial();
