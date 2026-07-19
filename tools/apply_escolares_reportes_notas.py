from pathlib import Path
import re
import shutil
import subprocess
import sys

HTML_PATH = Path("index.html")
TXT_PATH = Path("dashboard_con_mejoras_escolares_reportes_notas.txt")
text = HTML_PATH.read_text(encoding="utf-8")
original = text


def replace_once(old: str, new: str, label: str, *, already: str | None = None) -> None:
    global text
    if already and already in text:
        print(f"[OK] {label}: ya estaba aplicado")
        return
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: se esperaba 1 coincidencia exacta y se encontraron {count}")
    text = text.replace(old, new, 1)
    print(f"[OK] {label}")


def sub_once(pattern: str, replacement: str, label: str, *, flags: int = 0, already: str | None = None) -> None:
    global text
    if already and already in text:
        print(f"[OK] {label}: ya estaba aplicado")
        return
    matches = list(re.finditer(pattern, text, flags))
    if len(matches) != 1:
        raise RuntimeError(f"{label}: se esperaba 1 coincidencia regex y se encontraron {len(matches)}")
    text = re.sub(pattern, lambda _: replacement, text, count=1, flags=flags)
    print(f"[OK] {label}")


# -----------------------------------------------------------------------------
# 1. Estética del botón principal de REPORTES
# -----------------------------------------------------------------------------
replace_once(
    '''    .syBtn.disabled{
      opacity:.65;
      pointer-events:none;
      cursor:default;
    }
''',
    '''    .syBtn.disabled{
      opacity:.65;
      pointer-events:none;
      cursor:default;
    }
    .reportFolderPrimary{
      min-width:132px;
      padding:9px 14px;
      border-color:rgba(164,0,0,.42);
      background:linear-gradient(180deg,var(--accent),var(--accent2));
      color:#fff;
      box-shadow:0 8px 20px rgba(164,0,0,.18);
    }
    .reportFolderPrimary:hover{
      border-color:rgba(164,0,0,.62);
      background:linear-gradient(180deg,#e01616,var(--accent2));
      color:#fff;
      transform:translateY(-1px);
    }
    .reportFolderPrimary.disabled{
      color:#fff;
      background:linear-gradient(180deg,#b8b8b8,#8f8f8f);
      border-color:rgba(15,23,42,.16);
      box-shadow:none;
    }
''',
    "CSS de VER REPORTES",
    already=".reportFolderPrimary{",
)


# -----------------------------------------------------------------------------
# 2. PROGRAMA: ESCOLARES U.LIMA
# -----------------------------------------------------------------------------
replace_once(
    '''  if (raw === "PUCP") return { kind:"PUCP", scope:"PUCP", theme:"PUCP" };
  if (raw === "ESCOLARES" || raw === "ESCOLAR") return { kind:"ESCOLARES", scope:"ESCOLARES", theme:"ESCOLARES" };
''',
    '''  if (raw === "PUCP") return { kind:"PUCP", scope:"PUCP", theme:"PUCP" };
  if (["ESCOLARES U.LIMA","ESCOLAR U.LIMA","ESCOLARES ULIMA","ESCOLAR ULIMA"].includes(raw)) return { kind:"ESCOLARES U.LIMA", scope:"ESCOLARES", theme:"ESCOLARES" };
  if (raw === "ESCOLARES" || raw === "ESCOLAR") return { kind:"ESCOLARES", scope:"ESCOLARES", theme:"ESCOLARES" };
''',
    "tipo de programa ESCOLARES U.LIMA",
    already='kind:"ESCOLARES U.LIMA"',
)

replace_once(
    '''            <option value="PUCP">CICLO: PUCP</option>
            <option value="ESCOLARES">CICLO: ESCOLARES</option>
''',
    '''            <option value="PUCP">CICLO: PUCP</option>
            <option value="ESCOLARES U.LIMA">CICLO: ESCOLARES U.LIMA</option>
            <option value="ESCOLARES">CICLO: ESCOLARES</option>
''',
    "selector de programa ESCOLARES U.LIMA",
    already='<option value="ESCOLARES U.LIMA">',
)


# -----------------------------------------------------------------------------
# 3. IMPRESIONES: ESCOLAR U.LIMA y ESCOLAR PUCP
# -----------------------------------------------------------------------------
sub_once(
    r'''  function ensurePreUlimaImpresionesRows\(rows\)\{.*?\n  \}\n''',
    '''  function ensurePreUlimaImpresionesRows(rows){
    const base = Array.isArray(rows) ? rows.slice() : [];
    for (const item of MANDATORY_PRE_ULIMA_IMPRESIONES){
      const exists = base.some(r => String(r?.local||"").toUpperCase() === item.local && /PRE\\s*U\\.?LIMA/.test(String(r?.salon||"").toUpperCase()));
      if (!exists) base.push({...item});
    }
    return base;
  }

  function ensureEscolaresImpresionesRows(rows){
    const normalized = (Array.isArray(rows) ? rows : []).map(r=>{
      const salon = mcNormLabel(String(r?.salon || "")).replace(/\\s+/g," ").trim();
      if (/^ESCOLAR(?:ES)?$/.test(salon)) return {...r, salon:"ESCOLAR U.LIMA"};
      return {...r};
    });

    const best = new Map();
    for (const item of normalized){
      const key = `${String(item?.local||"").toUpperCase()}||${mcNormLabel(String(item?.salon||""))}`;
      best.set(key, item);
    }
    const base = [...best.values()];

    const affectedLocals = uniq(base.filter(r=>{
      const salon = mcNormLabel(String(r?.salon || "")).replace(/\\s+/g," ").trim();
      return /^ESCOLAR(?:ES)?\\s+(?:U\\.?LIMA|ULIMA|PUCP)$/.test(salon);
    }).map(r=>String(r.local||"").toUpperCase()).filter(Boolean));

    for (const local of affectedLocals){
      const hasUlima = base.some(r=>String(r?.local||"").toUpperCase()===local && /^ESCOLAR(?:ES)?\\s+(?:U\\.?LIMA|ULIMA)$/.test(mcNormLabel(String(r?.salon||""))));
      const hasPucp = base.some(r=>String(r?.local||"").toUpperCase()===local && /^ESCOLAR(?:ES)?\\s+PUCP$/.test(mcNormLabel(String(r?.salon||""))));
      if (!hasUlima) base.push({local, salon:"ESCOLAR U.LIMA", count:0});
      if (!hasPucp) base.push({local, salon:"ESCOLAR PUCP", count:0});
    }
    return base;
  }
''',
    "normalización de escolares en IMPRESIONES",
    flags=re.S,
    already="function ensureEscolaresImpresionesRows(rows)",
)

text = text.replace(
    'state.imprRows = ensurePreUlimaImpresionesRows(parseImpresionesCSV(text));',
    'state.imprRows = ensureEscolaresImpresionesRows(ensurePreUlimaImpresionesRows(parseImpresionesCSV(text)));',
)
text = text.replace(
    'state.imprRows = ensurePreUlimaImpresionesRows(state.imprRows || []);',
    'state.imprRows = ensureEscolaresImpresionesRows(ensurePreUlimaImpresionesRows(state.imprRows || []));',
)


# -----------------------------------------------------------------------------
# 4. SÍLABOS: ESCOLAR U.LIMA y cursos solicitados
# -----------------------------------------------------------------------------
replace_once(
    '''      { name:"HABILIDAD OPERATIVA", url:"https://docs.google.com/spreadsheets/d/1GrTdfQVKnTjor-e6sso2s1ydN9nh0DbF8uj1VY9ZbVQ/edit?gid=11988891#gid=11988891" },
    ],
    "ESCOLARES INTEGRAL": [
''',
    '''      { name:"HABILIDAD OPERATIVA", url:"https://docs.google.com/spreadsheets/d/1GrTdfQVKnTjor-e6sso2s1ydN9nh0DbF8uj1VY9ZbVQ/edit?gid=11988891#gid=11988891" },
    ],
    "ESCOLAR U.LIMA": [
      { name:"TEXTOS", url:"" },
      { name:"RAZONAMIENTO MATEMÁTICO", url:"" },
      { name:"ÁLGEBRA", url:"" },
      { name:"ARITMÉTICA", url:"" },
      { name:"GEOMETRÍA Y TRIGONOMETRÍA", url:"" },
    ],
    "ESCOLARES INTEGRAL": [
''',
    "catálogo de SÍLABOS ESCOLAR U.LIMA",
    already='"ESCOLAR U.LIMA": [',
)

replace_once(
    '''    if (uni==="PUCP") return getCss("--pucp");
    if (uni==="ESCOLARES ARS") return getCss("--pucp");
''',
    '''    if (uni==="PUCP") return getCss("--pucp");
    if (uni==="ESCOLAR U.LIMA") return getCss("--schHead_ESC");
    if (uni==="ESCOLARES ARS") return getCss("--pucp");
''',
    "color de SÍLABOS ESCOLAR U.LIMA",
    already='if (uni==="ESCOLAR U.LIMA")',
)

replace_once(
    '''  function silaboUniKey(uniRaw){
    const u = String(uniRaw || "").toUpperCase().trim();
    if (u === "ESCOLARES") return "ESCOLARES INTEGRAL";
''',
    '''  function silaboUniKey(uniRaw){
    const u = String(uniRaw || "").toUpperCase().trim();
    if ((u.includes("ESCOLAR") || u.includes("ESCOLARES")) && (u.includes("U.LIMA") || u.includes("ULIMA") || u.includes("U LIMA"))) return "ESCOLAR U.LIMA";
    if (u === "ESCOLARES") return "ESCOLARES INTEGRAL";
''',
    "normalización de SÍLABOS ESCOLAR U.LIMA",
    already='return "ESCOLAR U.LIMA";',
)

replace_once(
    '''  function syProgramToRepoUni(value){
    const v = mcNormLabel(value || "");
    if (v.includes("ARS") || v.includes("POP")) return "ESCOLARES ARS";
''',
    '''  function syProgramToRepoUni(value){
    const v = mcNormLabel(value || "");
    if (v.includes("ESCOLAR") && (v.includes("U.LIMA") || v.includes("ULIMA") || v.includes("U LIMA"))) return "ESCOLAR U.LIMA";
    if (v.includes("ARS") || v.includes("POP")) return "ESCOLARES ARS";
''',
    "vinculación Materiales-Sílabos ESCOLAR U.LIMA",
    already='v.includes("ESCOLAR") && (v.includes("U.LIMA")',
)

text = text.replace(
    '["AGRARIA","U.LIMA","PUCP","ESCOLARES INTEGRAL","ESCOLARES ARS"].includes(v)',
    '["AGRARIA","U.LIMA","PUCP","ESCOLAR U.LIMA","ESCOLARES INTEGRAL","ESCOLARES ARS"].includes(v)',
)

replace_once(
    '''  let SY_LINK_EDIT_MODE = false;
  let LISTAS_LINK_EDIT_MODE = false;
  let REPORTES_LINK_EDIT_MODE = false;
''',
    '''  let SY_LINK_EDIT_MODE = false;
  let LISTAS_LINK_EDIT_MODE = false;
  let REPORTES_LINK_EDIT_MODE = false;
  let NOTAS_LINK_EDIT_MODE = false;
''',
    "estado de edición de NOTAS GENERALES",
    already="let NOTAS_LINK_EDIT_MODE = false;",
)

replace_once(
    '''          <span class="pill"><span class="dot pucp"></span>PUCP</span>
          <span class="pill"><span class="dot escolares"></span>ESCOLARES INTEGRAL</span>
''',
    '''          <span class="pill"><span class="dot pucp"></span>PUCP</span>
          <span class="pill"><span class="dot escolares"></span>ESCOLAR U.LIMA</span>
          <span class="pill"><span class="dot escolares"></span>ESCOLARES INTEGRAL</span>
''',
    "leyenda de SÍLABOS ESCOLAR U.LIMA",
    already='<span class="dot escolares"></span>ESCOLAR U.LIMA',
)

text = re.sub(r'id="sUnis">\d+</b>', 'id="sUnis">6</b>', text, count=1)
text = text.replace(
    'fillSelectKeep("sUni", ["AGRARIA","U.LIMA","PUCP","ESCOLARES INTEGRAL","ESCOLARES ARS"], "UNIVERSIDAD: TODAS");',
    'fillSelectKeep("sUni", ["AGRARIA","U.LIMA","PUCP","ESCOLAR U.LIMA","ESCOLARES INTEGRAL","ESCOLARES ARS"], "UNIVERSIDAD: TODAS");',
)


# -----------------------------------------------------------------------------
# 5. MATERIALES: ESCOLARES U.LIMA
# -----------------------------------------------------------------------------
replace_once(
    '''  { uni:"PUCP",      url:"https://drive.google.com/drive/folders/1FfUL4GEiHALYEOhBHTJA3SzHVotRGv0k?usp=sharing" },
  { uni:"ESCOLARES INTEGRAL", url:"https://drive.google.com/drive/folders/1nUdMaZU2n6b-FZlfR9WI2041e_aoOPYy" },
''',
    '''  { uni:"PUCP",      url:"https://drive.google.com/drive/folders/1FfUL4GEiHALYEOhBHTJA3SzHVotRGv0k?usp=sharing" },
  { uni:"ESCOLARES U.LIMA", url:"" },
  { uni:"ESCOLARES INTEGRAL", url:"https://drive.google.com/drive/folders/1nUdMaZU2n6b-FZlfR9WI2041e_aoOPYy" },
''',
    "carpeta raíz de MATERIALES ESCOLARES U.LIMA",
    already='uni:"ESCOLARES U.LIMA"',
)

text = text.replace('<span class="syKpiPill">CARPETAS: <b>5</b></span>', '<span class="syKpiPill">CARPETAS: <b>${MATERIALES.length}</b></span>')
text = text.replace(
    'const MAT_UNI_ORDER = ["AGRARIA","U.LIMA","PUCP","ESCOLARES INTEGRAL","ESCOLARES ARS"];',
    'const MAT_UNI_ORDER = ["AGRARIA","U.LIMA","PUCP","ESCOLARES U.LIMA","ESCOLARES INTEGRAL","ESCOLARES ARS"];',
)
replace_once(
    '''      "PUCP": getCss("--pucp"),
      "ESCOLARES INTEGRAL": getCss("--schHead_ESC"),
''',
    '''      "PUCP": getCss("--pucp"),
      "ESCOLARES U.LIMA": getCss("--schHead_ESC"),
      "ESCOLARES INTEGRAL": getCss("--schHead_ESC"),
''',
    "color de MATERIALES ESCOLARES U.LIMA",
    already='"ESCOLARES U.LIMA": getCss("--schHead_ESC")',
)

replace_once(
    '''  const ESCOLARES_INTEGRAL_COURSES = COURSES["ESCOLARES"];
  const ESCOLARES_ARS_COURSES = [
''',
    '''  const ESCOLARES_INTEGRAL_COURSES = COURSES["ESCOLARES"];
  const ESCOLARES_ULIMA_COURSES = [
    "Textos",
    "Razonamiento Matemático",
    "Álgebra",
    "Aritmética",
    "Geometría y Trigonometría"
  ];
  const ESCOLARES_ARS_COURSES = [
''',
    "cursos de MATERIALES ESCOLARES U.LIMA",
    already="const ESCOLARES_ULIMA_COURSES = [",
)

replace_once(
    '''    if (normalized === "ESCOLARES AGRARIA" || normalized === "ESCOLARES AGRARAI") return "ESCOLARES INTEGRAL";
    if (normalized.includes("ARS") || normalized.includes("POP")) return "ESCOLARES ARS";
''',
    '''    if (normalized === "ESCOLARES AGRARIA" || normalized === "ESCOLARES AGRARAI") return "ESCOLARES INTEGRAL";
    if (normalized.includes("ESCOLAR") && (normalized.includes("U.LIMA") || normalized.includes("ULIMA") || normalized.includes("U LIMA"))) return "ESCOLARES U.LIMA";
    if (normalized.includes("ARS") || normalized.includes("POP")) return "ESCOLARES ARS";
''',
    "nombre visible de MATERIALES ESCOLARES U.LIMA",
    already='return "ESCOLARES U.LIMA";',
)

replace_once(
    '''    const name = mcMaterialProgramNameRaw(program).toUpperCase();
    if (name.includes("ARS")) return ESCOLARES_ARS_COURSES;
    return ESCOLARES_INTEGRAL_COURSES;
''',
    '''    const name = mcMaterialProgramNameRaw(program).toUpperCase();
    if (name.includes("U.LIMA") || name.includes("ULIMA") || name.includes("U LIMA")) return ESCOLARES_ULIMA_COURSES;
    if (name.includes("ARS")) return ESCOLARES_ARS_COURSES;
    return ESCOLARES_INTEGRAL_COURSES;
''',
    "selección de cursos de MATERIALES ESCOLARES U.LIMA",
    already="return ESCOLARES_ULIMA_COURSES;",
)


# -----------------------------------------------------------------------------
# 6. LISTAS: eliminar ESCOLAR genérico y separar U.LIMA / PUCP
# -----------------------------------------------------------------------------
sub_once(
    r'''\s*\{ local:"SAN BORJA", name:"ESCOLAR",\s*url:"([^"]*)"\s*\},''',
    '''
  { local:"SAN BORJA", name:"ESC U.LIMA", url:"\\1" },
  { local:"SAN BORJA", name:"ESC PUCP", url:"" },''',
    "LISTAS escolares de SAN BORJA",
    already='{ local:"SAN BORJA", name:"ESC U.LIMA"',
)

replace_once(
    '''    { local:"VIRTUAL", name:"U.LIMA 1",  url:"https://docs.google.com/spreadsheets/d/1RleTyLMWqwMstCBRvG1UvTcR1XyqeTlY7TkWkaajmqs/edit?usp=drive_link" },
''',
    '''    { local:"VIRTUAL", name:"U.LIMA 1",  url:"https://docs.google.com/spreadsheets/d/1RleTyLMWqwMstCBRvG1UvTcR1XyqeTlY7TkWkaajmqs/edit?usp=drive_link" },
  { local:"VIRTUAL", name:"ESC U.LIMA", url:"" },
  { local:"VIRTUAL", name:"ESC PUCP", url:"" },
''',
    "LISTAS escolares de VIRTUAL",
    already='{ local:"VIRTUAL", name:"ESC U.LIMA"',
)


# -----------------------------------------------------------------------------
# 7. REPORTES: relación con LISTAS y visibilidad por rol
# -----------------------------------------------------------------------------
sub_once(
    r'''function getReportesCatalog\(\)\{.*?\n\}\n''',
    '''function getReportesCatalog(){
  const catalog = REPORTES.map(x=>({...x}));
  const seen = new Set(catalog.map(x=>repoSafeKey(x.local, x.name)));

  // Cada LISTA escolar debe contar con su tarjeta correspondiente en REPORTES.
  for (const item of LISTAS.filter(x=>isEscolaresSalonLabel(x.name))){
    const key = repoSafeKey(item.local, item.name);
    if (seen.has(key)) continue;
    catalog.push({ local:item.local, name:item.name, reporte:"", carpeta:"" });
    seen.add(key);
  }
  return catalog;
}
''',
    "catálogo de REPORTES relacionado con LISTAS",
    flags=re.S,
    already="Cada LISTA escolar debe contar",
)

sub_once(
    r'''      const repBtn = rep\n        \? `<a class="syBtn" href="\$\{escapeHtml\(rep\)\}" target="_blank" rel="noopener noreferrer">REPORTE</a>`\n        : `<span class="syBtn disabled">REPORTE</span>`;\n\n      const carBtn = car\n        \? `<a class="syBtn" href="\$\{escapeHtml\(car\)\}" target="_blank" rel="noopener noreferrer">CARPETA</a>`\n        : `<span class="syBtn disabled">CARPETA</span>`;''',
    '''      const isAdminReportView = String(CURRENT_ROLE || "").toLowerCase() === "admin";
      const repBtn = isAdminReportView
        ? (rep
          ? `<a class="syBtn" href="${escapeHtml(rep)}" target="_blank" rel="noopener noreferrer">REPORTE</a>`
          : `<span class="syBtn disabled">REPORTE</span>`)
        : "";

      const carBtn = car
        ? `<a class="syBtn reportFolderPrimary" href="${escapeHtml(car)}" target="_blank" rel="noopener noreferrer">VER REPORTES</a>`
        : `<span class="syBtn reportFolderPrimary disabled">VER REPORTES</span>`;''',
    "botones de REPORTES por rol",
    already="const isAdminReportView",
)


# -----------------------------------------------------------------------------
# 8. NOTAS GENERALES: edición directa de enlaces
# -----------------------------------------------------------------------------
sub_once(
    r'''function ensureNotasLayout\(\)\{.*?\n\}\n\nfunction renderNotasGenerales\(\)\{.*?\n\}\n(?=\n+function ensureMaterialesLayout\(\)\{)''',
    '''function notasRepoGetLink(st, id, fallback){
  const key = mcNormLabel(String(id || "")).replace(/\\s+/g," ").trim();
  const repo = st?.notasRepo || {};
  if (Object.prototype.hasOwnProperty.call(repo, key)) return String(repo[key] || "").trim();
  return String(fallback || "").trim();
}

function notasRepoSetLink(st, id, url){
  const key = mcNormLabel(String(id || "")).replace(/\\s+/g," ").trim();
  if (!st.notasRepo) st.notasRepo = {};
  st.notasRepo[key] = String(url || "").trim();
  return st;
}

function bindNotasEditors(){
  if (!syCanEditLinks() || !NOTAS_LINK_EDIT_MODE) return;
  document.querySelectorAll('[data-nota-save="1"]').forEach(btn=>{
    btn.addEventListener("click", ()=>{
      const item = btn.closest(".syItem");
      const input = item?.querySelector(".notaLinkInput");
      const id = btn.getAttribute("data-id") || "";
      const url = String(input?.value || "").trim();
      const st = mcLoadStore();
      notasRepoSetLink(st, id, url);
      mcSaveStore(st);
      toast(url ? "Enlace de notas guardado." : "Notas marcadas como pendientes.");
      renderNotasGenerales();
    });
  });
  document.querySelectorAll('[data-nota-clear="1"]').forEach(btn=>{
    btn.addEventListener("click", ()=>{
      const st = mcLoadStore();
      notasRepoSetLink(st, btn.getAttribute("data-id") || "", "");
      mcSaveStore(st);
      toast("Enlace de notas limpiado.");
      renderNotasGenerales();
    });
  });
}

function ensureNotasLayout(){
  const el = document.getElementById("view_notas");
  if (!el || el.dataset.ready === "1") return;

  el.innerHTML = `
    <div class="card panel12">
      <div class="syLocalHead" style="margin-bottom:10px;">
        <div>
          <div class="cardtitle" style="margin:0;">NOTAS GENERALES</div>
          <div style="color:var(--muted); font-weight:900; margin-top:6px;">Acceso directo a las hojas de notas por categoría.</div>
        </div>
        ${syCanEditLinks() ? `<button id="nEditToggle" class="syEditToggle" type="button">EDITAR ENLACES</button>` : ``}
      </div>
      <div class="panelHint" id="nEditHint" style="margin:8px 0 12px; color:var(--muted);">
        ${syCanEditLinks() ? "Vista limpia activa. Usa EDITAR ENLACES para actualizar las hojas de notas." : "Los enlaces son de solo lectura."}
      </div>
      <div class="syWrap" id="notasGrid"></div>
    </div>
  `;

  document.getElementById("nEditToggle")?.addEventListener("click", ()=>{
    NOTAS_LINK_EDIT_MODE = !NOTAS_LINK_EDIT_MODE;
    renderNotasGenerales();
  });
  el.dataset.ready = "1";
}

function renderNotasGenerales(){
  ensureNotasLayout();
  const grid = document.getElementById("notasGrid");
  if (!grid) return;

  const editBtn = document.getElementById("nEditToggle");
  if (editBtn){
    editBtn.textContent = NOTAS_LINK_EDIT_MODE ? "VISTA LIMPIA" : "EDITAR ENLACES";
    editBtn.classList.toggle("active", NOTAS_LINK_EDIT_MODE);
  }
  const hint = document.getElementById("nEditHint");
  if (hint && syCanEditLinks()){
    hint.textContent = NOTAS_LINK_EDIT_MODE
      ? "Modo edición activo: actualiza los enlaces y vuelve a VISTA LIMPIA al finalizar."
      : "Vista limpia activa. Usa EDITAR ENLACES para actualizar las hojas de notas.";
  }

  const st = mcLoadStore();
  const notasOrdered = NOTAS_GENERALES.slice().sort((a,b)=>{
    const rank = (u)=>{
      const t = String(u||"").toUpperCase();
      if (t.includes("AGRARIA")) return 0;
      if (t.includes("U.LIMA") || t.includes("ULIMA")) return 1;
      if (t.includes("PUCP")) return 2;
      if (t.includes("ESCOLAR")) return 3;
      return 9;
    };
    const ra = rank(a.uni);
    const rb = rank(b.uni);
    if (ra !== rb) return ra - rb;
    return String(a.label||"").localeCompare(String(b.label||""), "es");
  });

  grid.classList.toggle("syEditGrid", NOTAS_LINK_EDIT_MODE);
  grid.innerHTML = notasOrdered.map(x=>{
    const dot = x.uni === "AGRARIA" ? getCss("--agraria") :
      x.uni === "ESCOLARES" ? getCss("--schHead_ESC") :
      x.uni === "PUCP" ? getCss("--pucp") : getCss("--ulima");
    const url = notasRepoGetLink(st, x.id, x.url);
    const hasUrl = !!url;
    const editing = syCanEditLinks() && NOTAS_LINK_EDIT_MODE;
    const safeId = escapeHtml(x.id);

    return `
      <div class="syItem syDisplayCard${editing ? " syEditing" : ""}" style="--syAccent:${escapeHtml(dot)};">
        <div class="syLeft">
          <div class="syCourseRow">
            <span class="syColorDot" aria-hidden="true"></span>
            <div class="syCourse">${escapeHtml(x.label)}</div>
          </div>
          <div class="syMeta"><span>${escapeHtml(x.uni)}${hasUrl ? "" : " · PENDIENTE"}</span></div>
        </div>
        <div class="syBtns">
          ${hasUrl ? `<a class="syOpen" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">ABRIR</a>` : `<span class="syOpen disabled">SIN ENLACE</span>`}
        </div>
        ${editing ? `
          <div class="syEditPanel">
            <input class="notaLinkInput" type="text" value="${escapeHtml(url)}" placeholder="Pega aquí el enlace de ${escapeHtml(x.label)}" />
            <button class="syBtn" type="button" data-nota-save="1" data-id="${safeId}">GUARDAR</button>
            <button class="syBtn" type="button" data-nota-clear="1" data-id="${safeId}">LIMPIAR</button>
          </div>
        ` : ""}
      </div>
    `;
  }).join("");
  bindNotasEditors();
}
''',
    "editor de enlaces de NOTAS GENERALES",
    flags=re.S,
    already="function notasRepoGetLink(st, id, fallback)",
)


# -----------------------------------------------------------------------------
# Validaciones finales
# -----------------------------------------------------------------------------
required = [
    'name:"ESC U.LIMA"',
    'name:"ESC PUCP"',
    '"ESCOLAR U.LIMA": [',
    'CICLO: ESCOLARES U.LIMA',
    'uni:"ESCOLARES U.LIMA"',
    'VER REPORTES',
    'NOTAS_LINK_EDIT_MODE',
    'function notasRepoGetLink',
    'LIMPIAR2026',
]
for needle in required:
    if needle not in text:
        raise RuntimeError(f"Validación final: falta {needle}")

if re.search(r'\{\s*local:"SAN BORJA",\s*name:"ESCOLAR"', text):
    raise RuntimeError("Validación final: todavía existe el botón ESCOLAR genérico de SAN BORJA")

if text == original:
    raise RuntimeError("No se aplicó ningún cambio")

HTML_PATH.write_text(text, encoding="utf-8")
shutil.copyfile(HTML_PATH, TXT_PATH)
print(f"index.html actualizado: {len(original)} -> {len(text)} caracteres")
print(f"TXT generado: {TXT_PATH}")

# Validación de sintaxis JavaScript de los bloques inline.
blocks = re.findall(r'<script(?:\s[^>]*)?>(.*?)</script>', text, flags=re.I | re.S)
checked = 0
for idx, block in enumerate(blocks, start=1):
    if not block.strip():
        continue
    tmp = Path(f"/tmp/dashboard-inline-{idx}.js")
    tmp.write_text(block, encoding="utf-8")
    proc = subprocess.run(["node", "--check", str(tmp)], capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr, file=sys.stderr)
        raise RuntimeError(f"Error de sintaxis JavaScript en bloque inline {idx}")
    checked += 1
print(f"Sintaxis JavaScript validada en {checked} bloque(s) inline.")
