#!/usr/bin/env python3
"""
Private Build — Notion → HTML sync
Uso: python sync.py
     python sync.py --dry-run   (solo previsualiza cambios, no hace push)
     python sync.py --phase 0   (solo reconstruye fase 0)
"""

import os, sys, json, re, subprocess, argparse
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("Instalando dependencias…")
    subprocess.run([sys.executable, "-m", "pip", "install", "requests"], check=True)
    import requests

# ─── Configuración ──────────────────────────────────────────────────────────
NOTION_TOKEN   = os.environ.get("NOTION_TOKEN", "")          # secret_xxxx
NOTION_VERSION = "2022-06-28"
REPO_DIR       = Path(__file__).parent.parent                 # raíz del repo
HTML_FILE      = REPO_DIR / "index.html"                      # privatebuild.html hosteado
TEMPLATE_FILE  = Path(__file__).parent / "template.html"      # plantilla base (el HTML actual)

# IDs de tus bases de datos en Notion (los consigues desde la URL de cada DB)
NOTION_DBS = {
    "phases":       os.environ.get("NOTION_DB_PHASES",      ""),  # 4 fases con metadata
    "attributes":   os.environ.get("NOTION_DB_ATTRIBUTES",  ""),  # atributos por fase
    "deliverables": os.environ.get("NOTION_DB_DELIVERABLES",""),  # entregables por fase
    "actions":      os.environ.get("NOTION_DB_ACTIONS",     ""),  # acciones/semanas
    "failures":     os.environ.get("NOTION_DB_FAILURES",    ""),  # fracasos típicos
    "tools":        os.environ.get("NOTION_DB_TOOLS",       ""),  # stack de herramientas
    "community":    os.environ.get("NOTION_DB_COMMUNITY",   ""),  # formulario bienvenida
    "mentorships":  os.environ.get("NOTION_DB_MENTORSHIPS", ""),  # formulario mentorías
}

PHASE_NAMES  = ["SKILLER", "OPERATOR", "BUILDER", "OWNER"]
PHASE_COLORS = {
    "SKILLER":  "linear-gradient(135deg,#c0c0d8 0%,#f0f0ff 40%,#d0d0e8 100%)",
    "OPERATOR": "linear-gradient(135deg,#b86820 0%,#e88c30 40%,#ffb060 100%)",
    "BUILDER":  "linear-gradient(135deg,#1a6fcc 0%,#3a9fff 40%,#88ccff 100%)",
    "OWNER":    "linear-gradient(135deg,#7a6010 0%,#c8a840 40%,#f0d870 100%)",
}

# ─── Notion API helpers ───────────────────────────────────────────────────────
def notion_headers():
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }

def query_db(db_id, filter_body=None):
    """Trae todas las páginas de una DB de Notion (pagina automáticamente)."""
    if not db_id:
        return []
    results, cursor = [], None
    while True:
        body = {"page_size": 100}
        if filter_body:
            body["filter"] = filter_body
        if cursor:
            body["start_cursor"] = cursor
        r = requests.post(
            f"https://api.notion.com/v1/databases/{db_id}/query",
            headers=notion_headers(), json=body
        )
        r.raise_for_status()
        data = r.json()
        results.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return results

def get_prop(page, key, default=""):
    """Extrae el valor de una propiedad de Notion de forma segura."""
    props = page.get("properties", {})
    prop  = props.get(key, {})
    ptype = prop.get("type", "")

    if ptype == "title":
        items = prop.get("title", [])
        return "".join(t.get("plain_text", "") for t in items) or default
    if ptype == "rich_text":
        items = prop.get("rich_text", [])
        return "".join(t.get("plain_text", "") for t in items) or default
    if ptype == "number":
        return prop.get("number", default)
    if ptype == "select":
        sel = prop.get("select")
        return sel.get("name", default) if sel else default
    if ptype == "multi_select":
        return [s.get("name", "") for s in prop.get("multi_select", [])]
    if ptype == "checkbox":
        return prop.get("checkbox", False)
    if ptype == "url":
        return prop.get("url", default)
    if ptype == "email":
        return prop.get("email", default)
    if ptype == "date":
        d = prop.get("date")
        return d.get("start", default) if d else default
    return default

# ─── Builders HTML por sección ───────────────────────────────────────────────

def build_attr_cell(attr):
    """Genera el HTML de una celda de atributo desde un registro de Notion."""
    name      = get_prop(attr, "Nombre")
    score     = get_prop(attr, "Score", 0)
    desc      = get_prop(attr, "Descripción")
    delta     = get_prop(attr, "Delta")
    direction = get_prop(attr, "Dirección", "up")   # "up" o "down"
    tag       = get_prop(attr, "Categoría")         # Ego/Marketing/Finance/Systems/IA
    excellent = get_prop(attr, "Excellent", False)

    tag_colors = {
        "Ego":      ("#e03535", "rgba(224,53,53,0.25)"),
        "Marketing":("#38b068", "rgba(56,176,104,0.25)"),
        "Finance":  ("#c8a840", "rgba(200,168,64,0.25)"),
        "Systems":  ("#c8a840", "rgba(200,168,64,0.25)"),
        "IA":       ("#3a9fff", "rgba(58,159,255,0.25)"),
    }
    tag_color, tag_border = tag_colors.get(tag, ("#70708c","rgba(112,112,140,0.25)"))

    fill_class = "fill-red" if direction == "down" else ("fill-metal" if score > 50 else "fill-dim")
    delta_class = "d-down" if direction == "down" else "d-up"
    arrow = "▼" if direction == "down" else "▲"

    tag_html = ""
    if tag:
        tag_html = (
            f'<span style="display:inline-block;margin-left:6px;font-size:7px;font-weight:700;'
            f'letter-spacing:0.15em;text-transform:uppercase;padding:2px 6px;'
            f'border:1px solid {tag_border};color:{tag_color};vertical-align:middle">{tag}</span>'
        )

    excellent_class = " excellent" if excellent else ""
    led_html = '<div class="excellent-led"></div>\n        ' if excellent else ""

    score_style = ""
    if direction == "down":
        score_style = ' style="background:none;-webkit-background-clip:initial;background-clip:initial;color:var(--red)"'

    return f'''      <div class="attr-cell{excellent_class}">{led_html}
        <div class="attr-top"><div class="attr-name">{name} {tag_html}</div><div class="attr-score"{score_style}>{score}</div></div>
        <div class="attr-desc">{desc}</div>
        <div class="attr-bar-track"><div class="attr-bar-fill {fill_class}" style="width:0%" data-w="{score}%"></div></div>
        <div class="attr-delta {delta_class}">{arrow} {delta}</div>
      </div>'''


def build_deliv_item(deliv, phase_idx):
    """Genera el HTML de un ítem de entregable."""
    title = get_prop(deliv, "Título")
    desc  = get_prop(deliv, "Descripción")
    return (
        f'      <div class="deliv-item" onclick="toggleDeliv(this,{phase_idx},25)">'
        f'<div class="dchk"></div>'
        f'<div class="deliv-text"><div class="dt-title">{title}</div>'
        f'<div class="dt-desc">{desc}</div></div></div>'
    )


def build_action_card(action):
    """Genera el HTML de una tarjeta de acción semanal."""
    title     = get_prop(action, "Título")
    priority  = get_prop(action, "Prioridad", "")
    milestone = get_prop(action, "Hito", "")
    items     = get_prop(action, "Items", "")   # texto separado por \n
    tool_name = get_prop(action, "Herramienta")
    tool_logo = get_prop(action, "Logo URL")

    logo_html = ""
    if tool_logo:
        logo_html = (
            f'<div style="width:32px;height:32px;background:#1c1c24;border:1px solid var(--border2);'
            f'display:flex;align-items:center;justify-content:center;flex-shrink:0;overflow:hidden">'
            f'<img src="{tool_logo}" style="width:22px;height:22px;object-fit:contain" '
            f'onerror="this.style.display=\'none\'" /></div>'
        )

    items_html = ""
    if items:
        lines = [l.strip() for l in items.split("\n") if l.strip()]
        items_html = "<ul class=\"wc-items\">" + "".join(f"<li>{l}</li>" for l in lines) + "</ul>"

    milestone_html = f'<div class="wc-milestone">⬡ {milestone}</div>' if milestone else ""
    priority_html  = f'<div class="wc-pri">Prioridad {priority}</div>' if priority else ""

    return f'''    <div class="week-card tool-card">
      <div class="wc-header">
        {logo_html}
        <div>
          <div class="wc-title">{title}</div>
          {priority_html}
        </div>
      </div>
      <div class="wc-body">
        {items_html}
        {milestone_html}
      </div>
    </div>'''


def build_fail_card(fail, is_booster=False):
    """Genera el HTML de una tarjeta de fracaso o potenciador."""
    title = get_prop(fail, "Título")
    body  = get_prop(fail, "Descripción")
    card_class = "booster-card" if is_booster else "fail-card"
    icon = "◈" if is_booster else "◆"
    return f'''    <div class="{card_class}">
      <div class="fail-title">{icon} {title}</div>
      <div class="fail-body">{body}</div>
    </div>'''


def build_tool_card(tool):
    """Genera el HTML de una tarjeta de herramienta del stack."""
    name    = get_prop(tool, "Nombre")
    use     = get_prop(tool, "Uso")
    cost    = get_prop(tool, "Costo")
    favicon = get_prop(tool, "Favicon URL")
    note    = get_prop(tool, "Nota")

    logo_html = (
        f'<div style="width:36px;height:36px;background:#1c1c24;border:1px solid var(--border2);'
        f'display:flex;align-items:center;justify-content:center;flex-shrink:0;overflow:hidden">'
        f'<img src="{favicon}" style="width:24px;height:24px;object-fit:contain;filter:brightness(1.1)" '
        f'onerror="this.style.display=\'none\'" /></div>'
        if favicon else
        f'<div style="width:36px;height:36px;background:#1c1c24;border:1px solid var(--border2);'
        f'display:flex;align-items:center;justify-content:center;flex-shrink:0;'
        f'font-size:10px;font-weight:800;color:var(--gray4)">{name[:2]}</div>'
    )

    cost_html  = f'<div class="wc-milestone">{cost}</div>' if cost else ""
    note_html  = f'<div class="wc-milestone" style="color:var(--green)">⬡ {note}</div>' if note else ""

    return f'''    <div class="week-card tool-card">
      <div class="wc-header">
        {logo_html}
        <div class="wc-title">{name}</div>
      </div>
      <div class="wc-body">
        <div class="wc-desc">{use}</div>
        {cost_html}
        {note_html}
      </div>
    </div>'''


# ─── Sección de comunidad (lectura de formularios) ────────────────────────────

def build_community_stats():
    """Lee la DB de comunidad (Google Forms → Notion via Make) y genera un bloque de stats."""
    members = query_db(NOTION_DBS["community"])
    mentors = query_db(NOTION_DBS["mentorships"])
    total   = len(members)
    phases  = {"SKILLER":0, "OPERATOR":0, "BUILDER":0, "OWNER":0}
    for m in members:
        phase = get_prop(m, "Etapa actual", "SKILLER")
        if phase in phases:
            phases[phase] += 1

    phase_bars = ""
    for name, count in phases.items():
        pct = round((count / total * 100) if total else 0)
        phase_bars += (
            f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">'
            f'<span style="font-size:9px;font-weight:700;letter-spacing:0.15em;'
            f'text-transform:uppercase;color:var(--gray4);min-width:80px">{name}</span>'
            f'<div style="flex:1;height:4px;background:var(--bg4);">'
            f'<div style="width:{pct}%;height:100%;background:var(--metal-grad2)"></div></div>'
            f'<span style="font-size:9px;color:var(--gray4)">{count}</span>'
            f'</div>'
        )

    return f'''  <!-- COMMUNITY STATS (generado automáticamente desde Notion) -->
  <div style="margin:0 56px 32px;padding:24px 28px;background:var(--bg2);border:1px solid var(--border);">
    <div style="font-size:8px;font-weight:700;letter-spacing:0.3em;text-transform:uppercase;color:var(--gray4);margin-bottom:16px;">
      🏴‍☠️ Comunidad · {total} miembros activos · {len(mentors)} mentorías completadas
    </div>
    {phase_bars}
    <div style="font-size:10px;color:var(--gray5);margin-top:12px;">Última actualización: {datetime.now().strftime("%d %b %Y %H:%M")}</div>
  </div>'''


# ─── Build completo de una fase ───────────────────────────────────────────────

def build_phase_section(phase_idx, dry_run=False):
    """Construye el bloque HTML completo de una fase desde Notion."""
    phase_name = PHASE_NAMES[phase_idx]
    phase_color = PHASE_COLORS[phase_name]
    month_num  = f"0{phase_idx + 1}"

    print(f"  → Fase {phase_idx + 1}: {phase_name}")

    # Traer datos de cada DB filtrados por fase
    def by_phase(db_key, filter_field="Fase"):
        return query_db(
            NOTION_DBS[db_key],
            {"property": filter_field, "select": {"equals": phase_name}}
        )

    attrs   = sorted(by_phase("attributes"),   key=lambda x: get_prop(x, "Orden", 99))
    delivs  = sorted(by_phase("deliverables"), key=lambda x: get_prop(x, "Orden", 99))
    actions = sorted(by_phase("actions"),      key=lambda x: get_prop(x, "Prioridad", 99))
    fails   = [f for f in by_phase("failures") if not get_prop(f, "Potenciador", False)]
    boosters= [f for f in by_phase("failures") if get_prop(f, "Potenciador", False)]
    tools   = sorted(by_phase("tools"),        key=lambda x: get_prop(x, "Orden", 99))

    # Fetch phase metadata
    phases_data = query_db(
        NOTION_DBS["phases"],
        {"property": "Nombre", "select": {"equals": phase_name}}
    )
    phase_meta = phases_data[0] if phases_data else {}
    income_range = get_prop(phase_meta, "Rango de ingresos", "$0–$500")
    phase_why    = get_prop(phase_meta, "Descripción",
                            f"Fase {phase_idx + 1} del desafío Private Build.")
    trap_text    = get_prop(phase_meta, "Trampa", "")
    build_text   = get_prop(phase_meta, "Lo que se construye", "")
    seal_label   = get_prop(phase_meta, "Sello label", f"Sello del {phase_name}")
    mastery_text = get_prop(phase_meta, "Mastery", "")

    # Render attr cells
    attrs_html = "\n".join(build_attr_cell(a) for a in attrs) if attrs else "<!-- sin atributos -->"

    # Render deliverables
    delivs_html = "\n".join(build_deliv_item(d, phase_idx) for d in delivs) if delivs else ""

    # Render actions
    actions_html = "\n".join(build_action_card(a) for a in actions) if actions else ""

    # Render failures + boosters
    fails_html    = "\n".join(build_fail_card(f, False) for f in fails)    if fails    else ""
    boosters_html = "\n".join(build_fail_card(b, True)  for b in boosters) if boosters else ""

    # Render tool stack
    tools_html = "\n".join(build_tool_card(t) for t in tools) if tools else ""

    active_class = ' active' if phase_idx == 0 else ''

    # Mastery banner
    mastery_html = ""
    if mastery_text:
        mastery_html = (
            f'  <!-- MASTERY BANNER -->\n'
            f'  <div style="margin:0 56px;padding:24px 32px;'
            f'background:linear-gradient(135deg,rgba(96,96,160,0.08) 0%,rgba(13,13,16,0) 100%);'
            f'border-left:3px solid #6060a0;margin-bottom:8px;">\n'
            f'    <p style="font-size:13px;font-weight:600;color:var(--metal3);line-height:1.5;">'
            f'{mastery_text}</p>\n  </div>\n'
        )

    seal_checks = "\n".join(
        f'      <label class="seal-check"><input type="checkbox" onchange="updateSeal(this)"> '
        f'<span>{get_prop(d, "Título")}</span></label>'
        for d in delivs
    ) if delivs else ""

    seal_count = len(delivs)
    data_phase = f'data-phase="{phase_idx}"'

    return f'''
<!-- ══════════════ FASE {phase_idx + 1}: {phase_name} ══════════════ -->
<div class="phase-section{active_class}" id="phase-{phase_idx}">

  <div class="ph-block">
    <div class="ph-giant"><span class="ph-giant-outline">{month_num}</span>{month_num}</div>
    <div class="ph-meta">
      <div class="ph-phase-tag">Mes {month_num} · Punto de partida</div>
      <div class="ph-phase-name" style="background:{phase_color};-webkit-background-clip:text;background-clip:text;color:transparent">{phase_name}</div>
      <p class="ph-why">{phase_why}</p>
    </div>
    <div class="ph-stats-col">
      <div class="ph-stat-item">
        <div class="psi-label">Ingresos objetivo</div>
        <div class="psi-val green">{income_range}</div>
      </div>
      <div class="ph-stat-item">
        <div class="psi-label">Duración</div>
        <div class="psi-val metal">1 mes</div>
      </div>
      <div class="ph-stat-item">
        <div class="psi-label">Estado</div>
        <div class="psi-val red">{'🔓 ACTIVO' if phase_idx == 0 else '🔒 BLOQUEADO'}</div>
      </div>
    </div>
  </div>

  <div class="sdiv"><div class="sdiv-label">01 · Atributos — inicio vs fin de fase</div><div class="sdiv-line"></div></div>
  <div class="attrs-wrap">
    <div class="attrs-grid" {data_phase}>
{attrs_html}
    </div>
  </div>

{mastery_html}
  <div class="sdiv"><div class="sdiv-label">02 · Acciones del mes</div><div class="sdiv-line"></div></div>
  <div class="weeks-wrap">
    <div class="weeks-grid">
{actions_html}
    </div>
  </div>

  <div class="sdiv"><div class="sdiv-label">03 · Fracasos típicos</div><div class="sdiv-line"></div></div>
  <div class="attrs-wrap">
    <div class="fail-grid">
{fails_html}
{boosters_html}
    </div>
  </div>

  <div class="sdiv"><div class="sdiv-label">04 · Mecanismo interno</div><div class="sdiv-line"></div></div>
  <div class="inner-wrap">
    <div class="inner-grid">
      <div class="inner-card trap">
        <div class="inner-label">▸ El patrón que frena al {phase_name}</div>
        <div class="inner-body">{trap_text}</div>
      </div>
      <div class="inner-card build">
        <div class="inner-label">▸ Lo que se construye de verdad</div>
        <div class="inner-body">{build_text}</div>
      </div>
    </div>
  </div>

  <div class="sdiv"><div class="sdiv-label">05 · Stack mínimo — {phase_name}</div><div class="sdiv-line"></div></div>
  <div class="weeks-wrap">
    <div class="weeks-grid">
{tools_html}
    </div>
  </div>

  <div class="sdiv"><div class="sdiv-label">06 · Entregables de fase</div><div class="sdiv-line"></div></div>
  <div class="deliv-wrap">
    <div class="deliv-grid" {data_phase}>
{delivs_html}
    </div>
  </div>

  <div class="sdiv"><div class="sdiv-label">07 · {seal_label}</div><div class="sdiv-line"></div></div>
  <div class="close-wrap">
    <p class="close-intro">Marca solo lo que es verdad hoy. No lo que planeas. No lo que deberías tener.</p>
    <div class="seal-checks">
{seal_checks}
    </div>
    <div class="seal-footer">
      <span class="seal-counter" id="sealCount-{phase_idx}">Checks 0/{seal_count}  ·  Entregables 0/{seal_count}</span>
    </div>
    <button class="seal-btn" id="sealBtn-{phase_idx}" onclick="sealPhase({phase_idx})">○ Sellar fase {month_num}</button>
    <div class="seal-ctas">
      <a class="repo-cta" href="https://chat.whatsapp.com/GgsNoRUVHbfDQ0GySqrmaq?mode=gi_t" target="_blank">◈ Ir a la comunidad</a>
      <a class="repo-cta" href="https://forms.gle/sGzi3f9RwKd4uXjC6" target="_blank">◉ Ayuda 1:1 con mentor</a>
    </div>
  </div>

</div><!-- /phase-{phase_idx} -->
'''


# ─── Inyección en el HTML ─────────────────────────────────────────────────────

PHASE_MARKER_START = "<!-- ══════════════ FASE {n}: {name} ══════════════ -->"
PHASE_MARKER_END   = "<!-- /phase-{n} -->"

def inject_phases(html, phases_html_list):
    """Reemplaza los bloques de fase en el HTML existente."""
    for i, new_html in enumerate(phases_html_list):
        name   = PHASE_NAMES[i]
        start  = f"<!-- ══════════════ FASE {i+1}: {name} ══════════════ -->"
        end    = f"<!-- /phase-{i} -->"
        idx_s  = html.find(start)
        idx_e  = html.find(end)
        if idx_s == -1 or idx_e == -1:
            print(f"  ⚠ Marcador no encontrado para fase {i+1} ({name})")
            continue
        html = html[:idx_s] + new_html.strip() + "\n" + html[idx_e + len(end):]
        print(f"  ✓ Fase {i+1} ({name}) inyectada")
    return html


# ─── Git push ─────────────────────────────────────────────────────────────────

def git_push(commit_msg):
    cmds = [
        ["git", "-C", str(REPO_DIR), "add", "index.html"],
        ["git", "-C", str(REPO_DIR), "commit", "-m", commit_msg],
        ["git", "-C", str(REPO_DIR), "push"],
    ]
    for cmd in cmds:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            if "nothing to commit" in result.stdout:
                print("  → Sin cambios para commitear")
                return False
            print(f"  ✗ Error git: {result.stderr}")
            return False
    print(f"  ✓ Push exitoso")
    return True


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Private Build — Notion sync")
    parser.add_argument("--dry-run", action="store_true", help="Solo previsualiza, no hace push")
    parser.add_argument("--phase",   type=int, default=None, help="Solo rebuild fase N (0-3)")
    parser.add_argument("--stats",   action="store_true",    help="Solo actualiza stats de comunidad")
    args = parser.parse_args()

    if not NOTION_TOKEN:
        print("❌ Falta NOTION_TOKEN. Exporta la variable de entorno.")
        sys.exit(1)

    print(f"\n🔒 Private Build Sync — {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # Leer HTML base
    if not HTML_FILE.exists():
        # Si no existe index.html en raíz, usa el template
        if TEMPLATE_FILE.exists():
            html = TEMPLATE_FILE.read_text(encoding="utf-8")
            print(f"  → Usando template: {TEMPLATE_FILE}")
        else:
            print("❌ No se encontró index.html ni template.html")
            sys.exit(1)
    else:
        html = HTML_FILE.read_text(encoding="utf-8")
        print(f"  → HTML base: {HTML_FILE} ({len(html.splitlines())} líneas)")

    # Build fases
    phases_to_build = [args.phase] if args.phase is not None else range(4)
    phases_html = {}

    print("\n📋 Leyendo Notion…")
    for i in phases_to_build:
        phases_html[i] = build_phase_section(i, args.dry_run)

    # Inyectar en HTML
    print("\n🔧 Inyectando en HTML…")
    for i, new_html in phases_html.items():
        name  = PHASE_NAMES[i]
        start = f"<!-- ══════════════ FASE {i+1}: {name} ══════════════ -->"
        end   = f"<!-- /phase-{i} -->"
        idx_s = html.find(start)
        idx_e = html.find(end)
        if idx_s >= 0 and idx_e >= 0:
            html = html[:idx_s] + new_html.strip() + "\n" + html[idx_e + len(end):]
            print(f"  ✓ Fase {i+1} ({name})")

    # Stats de comunidad (opcional)
    if args.stats or NOTION_DBS.get("community"):
        print("\n👥 Generando stats de comunidad…")
        try:
            stats_html = build_community_stats()
            # Inyectar antes del footer
            html = html.replace("<!-- FOOTER -->", stats_html + "\n<!-- FOOTER -->")
            print("  ✓ Stats inyectados")
        except Exception as e:
            print(f"  ⚠ Error en stats: {e}")

    # Actualizar timestamp en el HTML
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    html = re.sub(
        r'<!-- LAST_SYNC: .* -->',
        f'<!-- LAST_SYNC: {timestamp} -->',
        html
    )
    if "<!-- LAST_SYNC:" not in html:
        html = html.replace("</body>", f'<!-- LAST_SYNC: {timestamp} -->\n</body>')

    # Escribir HTML
    if not args.dry_run:
        HTML_FILE.write_text(html, encoding="utf-8")
        print(f"\n✅ HTML actualizado: {HTML_FILE}")

        # Git push
        print("\n🚀 Publicando en GitHub Pages…")
        changed_phases = ", ".join(PHASE_NAMES[i] for i in phases_to_build)
        git_push(f"sync({changed_phases}): {timestamp}")
    else:
        # Dry run: guardar preview
        preview = Path("/tmp/privatebuild_preview.html")
        preview.write_text(html, encoding="utf-8")
        print(f"\n[DRY RUN] Preview guardado en: {preview}")
        print(f"  Líneas: {len(html.splitlines())}")

    print("\n✓ Listo\n")


if __name__ == "__main__":
    main()
