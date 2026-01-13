import json
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import List, Dict, Optional


# ----------------------------
# Datenmodell
# ----------------------------

@dataclass
class Option:
    label: str = ""
    target: str = ""  # node_id

@dataclass
class Node:
    node_id: str = "start"      # HTML anchor id
    title: str = "Start"
    scene: str = ""
    dialog: str = ""
    content: str = ""           # allgemeiner Inhalt
    info_items: List[str] = field(default_factory=list)
    tech_flags: List[str] = field(default_factory=list)
    outcomes: List[str] = field(default_factory=list)
    notes: str = ""
    options: List[Option] = field(default_factory=list)

@dataclass
class QuestMeta:
    quest_name: str = "Neue Quest"
    region: str = "Unbekannt"
    short_description: str = "Kurzbeschreibung hier…"
    quest_giver: str = ""
    prerequisite: str = ""
    quest_type: str = ""
    meta_short: str = ""
    rewards: str = ""
    important_flags: str = ""
    version_stamp: str = ""

@dataclass
class QuestProject:
    meta: QuestMeta = field(default_factory=QuestMeta)
    nodes: List[Node] = field(default_factory=list)


# ----------------------------
# Hilfsfunktionen
# ----------------------------

def sanitize_id(raw: str) -> str:
    """
    Macht aus beliebigem Text eine HTML-taugliche id: a-z0-9_-
    """
    raw = raw.strip().lower()
    raw = raw.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    raw = re.sub(r"[^a-z0-9\-_]+", "-", raw)
    raw = re.sub(r"-{2,}", "-", raw).strip("-")
    return raw or "node"

def lines_to_list(text: str) -> List[str]:
    return [ln.strip() for ln in text.splitlines() if ln.strip()]

def list_to_lines(items: List[str]) -> str:
    return "\n".join(items)

def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")

def html_escape(s: str) -> str:
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;"))

def option_to_dict(opt: Option) -> Dict:
    return {"label": opt.label, "target": opt.target}

def option_from_dict(d: Dict) -> Option:
    return Option(label=d.get("label",""), target=d.get("target",""))

def project_to_jsonable(p: QuestProject) -> Dict:
    return {
        "meta": asdict(p.meta),
        "nodes": [
            {
                **{k: v for k, v in asdict(n).items() if k != "options"},
                "options": [option_to_dict(o) for o in n.options]
            }
            for n in p.nodes
        ]
    }

def project_from_jsonable(d: Dict) -> QuestProject:
    meta_d = d.get("meta", {})
    nodes_d = d.get("nodes", [])
    meta = QuestMeta(**{k: meta_d.get(k, "") for k in QuestMeta().__dict__.keys()})

    nodes: List[Node] = []
    for nd in nodes_d:
        n = Node(
            node_id=nd.get("node_id","node"),
            title=nd.get("title",""),
            scene=nd.get("scene",""),
            dialog=nd.get("dialog",""),
            content=nd.get("content",""),
            info_items=nd.get("info_items", []) or [],
            tech_flags=nd.get("tech_flags", []) or [],
            outcomes=nd.get("outcomes", []) or [],
            notes=nd.get("notes",""),
            options=[option_from_dict(o) for o in (nd.get("options", []) or [])]
        )
        nodes.append(n)

    return QuestProject(meta=meta, nodes=nodes)


# ----------------------------
# HTML Renderer
# ----------------------------

CSS_BLOCK = r"""
  <style>
    :root{
      --bg: #eef4ff;
      --card: #ffffff;
      --text: #111827;
      --muted: #475569;
      --line: rgba(15, 23, 42, .12);
      --accent: #2f6feb;
      --accent-soft: rgba(47,111,235,.12);
      --shadow: 0 10px 24px rgba(15,23,42,.08);
      --radius: 14px;
    }
    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body{
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Noto Sans", "Apple Color Emoji", "Segoe UI Emoji";
      background: var(--bg);
      color: var(--text);
      line-height: 1.55;
    }
    header, main, footer{
      max-width: 980px;
      margin: 0 auto;
      padding: 18px 18px;
    }
    header{ padding-top: 28px; }
    header h1{
      margin: 0 0 6px 0;
      font-size: clamp(1.4rem, 2.3vw, 2rem);
      letter-spacing: .2px;
    }
    header p{ margin: 6px 0 0 0; color: var(--muted); }
    hr{
      border: 0;
      border-top: 1px solid var(--line);
      margin: 18px 0;
    }
    section{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      padding: 18px 18px;
      margin: 14px 0;
      scroll-margin-top: 14px;
    }
    main { padding-bottom: 45vh; }

    section h2{ margin: 0 0 10px 0; font-size: 1.25rem; }
    section h3{ margin: 14px 0 8px 0; font-size: 1.05rem; }

    section:target{
      border-color: var(--accent);
      background: linear-gradient(0deg, #fff, #fff) padding-box,
                  linear-gradient(135deg, rgba(47,111,235,.35), rgba(47,111,235,0)) border-box;
      box-shadow: 0 14px 35px rgba(47,111,235,.18), var(--shadow);
      position: relative;
    }
    section:target::before{
      content: "Aktiver Knoten";
      position: absolute;
      top: -10px;
      right: 14px;
      font-size: .78rem;
      color: var(--accent);
      background: #fff;
      border: 1px solid rgba(47,111,235,.35);
      padding: 4px 8px;
      border-radius: 999px;
      box-shadow: 0 8px 16px rgba(15,23,42,.08);
    }

    nav{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 10px;
    }
    nav a{
      display: inline-block;
      text-decoration: none;
      color: var(--accent);
      background: var(--accent-soft);
      border: 1px solid rgba(47,111,235,.25);
      padding: 6px 10px;
      border-radius: 999px;
      font-weight: 600;
      font-size: .92rem;
    }
    nav a:hover{ filter: brightness(0.98); text-decoration: underline; }

    ul, ol { margin: 8px 0 0 22px; }
    li { margin: 4px 0; }

    details{
      margin-top: 10px;
      padding: 10px 12px;
      border: 1px dashed rgba(15,23,42,.18);
      border-radius: 12px;
      background: rgba(255,255,255,.6);
    }
    summary{ cursor: pointer; font-weight: 700; color: var(--text); }

    blockquote{
      margin: 10px 0;
      padding: 10px 12px;
      border-left: 4px solid rgba(47,111,235,.45);
      background: rgba(47,111,235,.06);
      border-radius: 10px;
      color: #0f172a;
    }
    pre{
      margin: 0;
      padding: 10px 12px;
      background: rgba(15,23,42,.06);
      border: 1px solid rgba(15,23,42,.10);
      border-radius: 10px;
      overflow: auto;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      font-size: .92rem;
      white-space: pre-wrap;
    }
    code{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      font-size: .92em;
    }

    footer small{ color: var(--muted); }

    .flash{ animation: flashGlow .7s ease-out; }
    @keyframes flashGlow{
      0% { box-shadow: 0 0 0 rgba(47,111,235,0); }
      40% { box-shadow: 0 0 0 6px rgba(47,111,235,.18), 0 16px 36px rgba(47,111,235,.20); }
      100% { box-shadow: 0 0 0 rgba(47,111,235,0); }
    }
  </style>
"""

JS_BLOCK = r"""
  <script>
    (function(){
      function focusTargetFromHash(){
        const id = location.hash ? location.hash.slice(1) : "";
        if(!id) return;
        const el = document.getElementById(id);
        if(!el) return;
        el.scrollIntoView({ behavior: "smooth", block: "start" });
        el.classList.add("flash");
        setTimeout(()=> el.classList.remove("flash"), 700);
      }
      window.addEventListener("load", focusTargetFromHash);
      window.addEventListener("hashchange", focusTargetFromHash);
    })();
  </script>
"""

def render_nav(nodes: List[Node]) -> str:
    parts = ['<nav aria-label="Quest-Navigation">', '<a href="#top">Übersicht</a>']
    for n in nodes:
        label = html_escape(n.title or n.node_id)
        parts.append(f'<a href="#{html_escape(n.node_id)}">{label}</a>')
    parts.append("</nav>")
    return "\n      ".join(parts)

def render_meta_list(meta: QuestMeta) -> str:
    items = [
        ("Questgeber", meta.quest_giver),
        ("Voraussetzung", meta.prerequisite),
        ("Art", meta.quest_type),
        ("Kurzbeschreibung", meta.meta_short),
        ("Belohnungen", meta.rewards),
        ("Wichtige Flags", meta.important_flags),
    ]
    lis = []
    for k, v in items:
        v = v.strip() or "—"
        lis.append(f'<li><strong>{html_escape(k)}:</strong> {html_escape(v)}</li>')
    return "\n        ".join(lis)

def render_options(node: Node, node_ids: List[str]) -> str:
    if not node.options:
        return "<p><em>Keine Optionen.</em></p>"
    out = ["<h3>Optionen</h3>", "<ol>"]
    for opt in node.options:
        label = html_escape(opt.label.strip() or "Option")
        target = opt.target.strip()
        if target not in node_ids:
            # Ziel existiert nicht (noch). Link bleibt, aber wir markieren’s.
            out.append(f'<li><a href="#{html_escape(target or "top")}">{label}</a> <em style="color:#b42318;">(Ziel unbekannt)</em></li>')
        else:
            out.append(f'<li><a href="#{html_escape(target)}">{label}</a></li>')
    out.append("</ol>")
    return "\n      ".join(out)

def render_list_block(title: str, items: List[str]) -> str:
    if not items:
        return ""
    lis = "\n        ".join(f"<li>{html_escape(it)}</li>" for it in items)
    return f"""
      <p><strong>{html_escape(title)}:</strong></p>
      <ul>
        {lis}
      </ul>
""".rstrip()

def render_details(title: str, items: List[str]) -> str:
    if not items:
        return ""
    lis = "\n          ".join(f"<li>{html_escape(it)}</li>" for it in items)
    return f"""
      <details>
        <summary>{html_escape(title)}</summary>
        <ul>
          {lis}
        </ul>
      </details>
""".rstrip()

def render_node_section(node: Node, node_ids: List[str]) -> str:
    h2 = html_escape(node.title.strip() or node.node_id)
    scene = node.scene.strip()
    dialog = node.dialog.strip()
    content = node.content.strip()
    notes = node.notes.strip()

    parts = [f'<section id="{html_escape(node.node_id)}">', f"  <h2>{h2}</h2>"]

    if scene:
        parts.append(f'  <p><strong>Szene:</strong> {html_escape(scene)}</p>')

    if content:
        parts.append(f'  <p><strong>Inhalt:</strong> {html_escape(content)}</p>')

    if dialog:
        parts.append("  <p><strong>Dialog:</strong></p>")
        parts.append("  <blockquote>")
        parts.append("    <pre>")
        parts.append(html_escape(dialog))
        parts.append("    </pre>")
        parts.append("  </blockquote>")

    info_block = render_list_block("Wichtige Information", node.info_items)
    if info_block:
        parts.append(info_block)

    tech_details = render_details("Technik/Flags", node.tech_flags)
    if tech_details:
        parts.append(tech_details)

    outcomes_details = render_details("Enden/Outcomes (Notizblock)", node.outcomes)
    if outcomes_details:
        parts.append(outcomes_details)

    # Optionen
    parts.append(render_options(node, node_ids))

    if notes:
        parts.append(f'  <p><strong>Notizen:</strong> {html_escape(notes)}</p>')

    parts.append('  <p><a href="#top">↑ Zur Übersicht</a></p>')
    parts.append("</section>")
    return "\n    ".join(parts)

def render_html(project: QuestProject, include_js: bool = True) -> str:
    meta = project.meta
    nodes = project.nodes
    node_ids = [n.node_id for n in nodes]

    title = f"Quest-Präsentator: {meta.quest_name}".strip()
    nav = render_nav(nodes)

    version = meta.version_stamp.strip() or now_stamp()

    # Übersicht + Metadaten
    top_section = f"""
    <section id="top">
      <h2>Übersicht</h2>
      <p><strong>Kurzbeschreibung:</strong> {html_escape(meta.short_description.strip() or "—")}</p>
      <p><strong>Quest Metadaten</strong></p>
      <ul>
        {render_meta_list(meta)}
      </ul>
      <hr>
      <p><a href="#{html_escape(nodes[0].node_id if nodes else "top")}">→ Zum Start</a></p>
    </section>
""".rstrip()

    node_sections = "\n\n    ".join(render_node_section(n, node_ids) for n in nodes)

    html = f"""<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>{html_escape(title)}</title>
{CSS_BLOCK}
</head>
<body>

  <header>
    <h1>Quest: {html_escape(meta.quest_name.strip() or "—")}</h1>
    <p><strong>Region:</strong> {html_escape(meta.region.strip() or "—")}</p>
    {nav}
    <hr>
  </header>

  <main>
{top_section}

    {node_sections}

    <section id="end">
      <h2>Ende / Notizen</h2>
      <p>[Hier kannst du „Was der Spieler gelernt hat“, „Welche Weltinfos gesetzt wurden“ und „Follow-ups“ reinschreiben.]</p>
      <p><a href="#top">↑ Zur Übersicht</a></p>
    </section>
  </main>

  <footer>
    <hr>
    <p><small>Quest-Präsentator — Stand: {html_escape(version)}</small></p>
  </footer>

{JS_BLOCK if include_js else ""}

</body>
</html>
"""
    return html


# ----------------------------
# GUI
# ----------------------------

class QuestEditorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Quest Editor (Tkinter) → HTML Export")
        self.geometry("1250x780")
        self.minsize(1050, 680)

        self.project = QuestProject()
        # Default: ein Startknoten
        self.project.nodes.append(Node(node_id="start", title="Start: Ardea"))

        self.current_node_index: Optional[int] = None

        self._build_ui()
        self._load_meta_to_ui()
        self._refresh_node_list()
        self._select_node(0)

    # ---------- UI Aufbau ----------
    def _build_ui(self):
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # Left panel: Meta + Node list + Buttons
        left = ttk.Frame(self, padding=10)
        left.grid(row=0, column=0, sticky="nsw")
        left.rowconfigure(2, weight=1)

        meta_box = ttk.Labelframe(left, text="Quest Metadaten", padding=10)
        meta_box.grid(row=0, column=0, sticky="new", padx=0, pady=(0,10))

        # Meta fields (compact)
        self.var_quest_name = tk.StringVar()
        self.var_region = tk.StringVar()
        self.var_quest_giver = tk.StringVar()
        self.var_prereq = tk.StringVar()
        self.var_type = tk.StringVar()
        self.var_version = tk.StringVar()

        def add_row(r, label, widget):
            ttk.Label(meta_box, text=label).grid(row=r, column=0, sticky="w", pady=2)
            widget.grid(row=r, column=1, sticky="ew", pady=2)
            meta_box.columnconfigure(1, weight=1)

        add_row(0, "Questname", ttk.Entry(meta_box, textvariable=self.var_quest_name, width=26))
        add_row(1, "Region/Ort", ttk.Entry(meta_box, textvariable=self.var_region, width=26))
        add_row(2, "Questgeber", ttk.Entry(meta_box, textvariable=self.var_quest_giver, width=26))
        add_row(3, "Voraussetzung", ttk.Entry(meta_box, textvariable=self.var_prereq, width=26))
        add_row(4, "Art", ttk.Entry(meta_box, textvariable=self.var_type, width=26))
        add_row(5, "Stand (Datum/Version)", ttk.Entry(meta_box, textvariable=self.var_version, width=26))

        ttk.Label(meta_box, text="Kurzbeschreibung").grid(row=6, column=0, sticky="nw", pady=2)
        self.txt_short = ScrolledText(meta_box, height=4, width=30, wrap="word")
        self.txt_short.grid(row=6, column=1, sticky="ew", pady=2)

        ttk.Label(meta_box, text="Meta-Kurzbeschreibung").grid(row=7, column=0, sticky="nw", pady=2)
        self.txt_meta_short = ScrolledText(meta_box, height=3, width=30, wrap="word")
        self.txt_meta_short.grid(row=7, column=1, sticky="ew", pady=2)

        ttk.Label(meta_box, text="Belohnungen").grid(row=8, column=0, sticky="nw", pady=2)
        self.txt_rewards = ScrolledText(meta_box, height=3, width=30, wrap="word")
        self.txt_rewards.grid(row=8, column=1, sticky="ew", pady=2)

        ttk.Label(meta_box, text="Wichtige Flags").grid(row=9, column=0, sticky="nw", pady=2)
        self.txt_imp_flags = ScrolledText(meta_box, height=3, width=30, wrap="word")
        self.txt_imp_flags.grid(row=9, column=1, sticky="ew", pady=2)

        # Nodes list
        nodes_box = ttk.Labelframe(left, text="Knoten", padding=10)
        nodes_box.grid(row=2, column=0, sticky="nsew")
        nodes_box.rowconfigure(0, weight=1)
        nodes_box.columnconfigure(0, weight=1)

        self.lst_nodes = tk.Listbox(nodes_box, height=18, exportselection=False)
        self.lst_nodes.grid(row=0, column=0, sticky="nsew")
        self.lst_nodes.bind("<<ListboxSelect>>", self._on_node_select)

        btns = ttk.Frame(nodes_box)
        btns.grid(row=1, column=0, sticky="ew", pady=(8,0))
        for c in range(4):
            btns.columnconfigure(c, weight=1)

        ttk.Button(btns, text="＋ Knoten", command=self._add_node).grid(row=0, column=0, sticky="ew", padx=2)
        ttk.Button(btns, text="－ Löschen", command=self._delete_node).grid(row=0, column=1, sticky="ew", padx=2)
        ttk.Button(btns, text="↑", command=lambda: self._move_node(-1)).grid(row=0, column=2, sticky="ew", padx=2)
        ttk.Button(btns, text="↓", command=lambda: self._move_node(1)).grid(row=0, column=3, sticky="ew", padx=2)

        # Project buttons
        proj_btns = ttk.Frame(left)
        proj_btns.grid(row=3, column=0, sticky="ew", pady=(10,0))
        proj_btns.columnconfigure(0, weight=1)
        proj_btns.columnconfigure(1, weight=1)
        proj_btns.columnconfigure(2, weight=1)

        ttk.Button(proj_btns, text="💾 Projekt speichern (JSON)", command=self._save_project).grid(row=0, column=0, sticky="ew", padx=2)
        ttk.Button(proj_btns, text="📂 Projekt öffnen (JSON)", command=self._load_project).grid(row=0, column=1, sticky="ew", padx=2)
        ttk.Button(proj_btns, text="🧾 HTML exportieren", command=self._export_html).grid(row=0, column=2, sticky="ew", padx=2)

        # Right panel: Node editor
        right = ttk.Frame(self, padding=10)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)

        editor = ttk.Labelframe(right, text="Knoten bearbeiten", padding=10)
        editor.grid(row=0, column=0, sticky="nsew")
        editor.columnconfigure(1, weight=1)
        editor.rowconfigure(8, weight=1)  # for big dialog/content zone

        self.var_node_id = tk.StringVar()
        self.var_node_title = tk.StringVar()

        ttk.Label(editor, text="Knoten-ID (Anchor)").grid(row=0, column=0, sticky="w", pady=3)
        self.ent_node_id = ttk.Entry(editor, textvariable=self.var_node_id, width=22)
        self.ent_node_id.grid(row=0, column=1, sticky="w", pady=3)
        ttk.Button(editor, text="ID aus Titel", command=self._id_from_title).grid(row=0, column=2, sticky="w", padx=6)

        ttk.Label(editor, text="Titel").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Entry(editor, textvariable=self.var_node_title).grid(row=1, column=1, columnspan=2, sticky="ew", pady=3)

        ttk.Label(editor, text="Szene (optional)").grid(row=2, column=0, sticky="nw", pady=3)
        self.txt_scene = ScrolledText(editor, height=3, wrap="word")
        self.txt_scene.grid(row=2, column=1, columnspan=2, sticky="ew", pady=3)

        ttk.Label(editor, text="Inhalt (Freitext)").grid(row=3, column=0, sticky="nw", pady=3)
        self.txt_content = ScrolledText(editor, height=4, wrap="word")
        self.txt_content.grid(row=3, column=1, columnspan=2, sticky="ew", pady=3)

        ttk.Label(editor, text="Dialog (Pre-Block)").grid(row=4, column=0, sticky="nw", pady=3)
        self.txt_dialog = ScrolledText(editor, height=8, wrap="word")
        self.txt_dialog.grid(row=4, column=1, columnspan=2, sticky="nsew", pady=3)

        ttk.Label(editor, text="Wichtige Info (je Zeile 1 Punkt)").grid(row=5, column=0, sticky="nw", pady=3)
        self.txt_info = ScrolledText(editor, height=4, wrap="word")
        self.txt_info.grid(row=5, column=1, columnspan=2, sticky="ew", pady=3)

        ttk.Label(editor, text="Technik/Flags (je Zeile 1 Punkt)").grid(row=6, column=0, sticky="nw", pady=3)
        self.txt_tech = ScrolledText(editor, height=4, wrap="word")
        self.txt_tech.grid(row=6, column=1, columnspan=2, sticky="ew", pady=3)

        ttk.Label(editor, text="Outcomes/Enden (je Zeile 1 Punkt)").grid(row=7, column=0, sticky="nw", pady=3)
        self.txt_outcomes = ScrolledText(editor, height=4, wrap="word")
        self.txt_outcomes.grid(row=7, column=1, columnspan=2, sticky="ew", pady=3)

        ttk.Label(editor, text="Notizen (optional)").grid(row=8, column=0, sticky="nw", pady=3)
        self.txt_notes = ScrolledText(editor, height=4, wrap="word")
        self.txt_notes.grid(row=8, column=1, columnspan=2, sticky="nsew", pady=3)

        # Options editor (separate box)
        opt_box = ttk.Labelframe(right, text="Optionen dieses Knotens (Label → Ziel-ID)", padding=10)
        opt_box.grid(row=1, column=0, sticky="ew", pady=(10,0))
        opt_box.columnconfigure(0, weight=1)

        self.tree_opts = ttk.Treeview(opt_box, columns=("label", "target"), show="headings", height=6)
        self.tree_opts.heading("label", text="Label (Text der Option)")
        self.tree_opts.heading("target", text="Ziel-Knoten-ID")
        self.tree_opts.column("label", width=520, stretch=True)
        self.tree_opts.column("target", width=160, stretch=False)
        self.tree_opts.grid(row=0, column=0, sticky="ew")

        opt_btns = ttk.Frame(opt_box)
        opt_btns.grid(row=1, column=0, sticky="ew", pady=(8,0))
        opt_btns.columnconfigure(0, weight=1)
        opt_btns.columnconfigure(1, weight=1)
        opt_btns.columnconfigure(2, weight=1)
        opt_btns.columnconfigure(3, weight=1)

        ttk.Button(opt_btns, text="＋ Option", command=self._add_option).grid(row=0, column=0, sticky="ew", padx=2)
        ttk.Button(opt_btns, text="✎ Bearbeiten", command=self._edit_option).grid(row=0, column=1, sticky="ew", padx=2)
        ttk.Button(opt_btns, text="－ Entfernen", command=self._remove_option).grid(row=0, column=2, sticky="ew", padx=2)
        ttk.Button(opt_btns, text="💾 Änderungen übernehmen", command=self._apply_current_node).grid(row=0, column=3, sticky="ew", padx=2)

    # ---------- Meta <-> UI ----------
    def _load_meta_to_ui(self):
        m = self.project.meta
        self.var_quest_name.set(m.quest_name)
        self.var_region.set(m.region)
        self.var_quest_giver.set(m.quest_giver)
        self.var_prereq.set(m.prerequisite)
        self.var_type.set(m.quest_type)
        self.var_version.set(m.version_stamp or now_stamp())

        self._set_text(self.txt_short, m.short_description)
        self._set_text(self.txt_meta_short, m.meta_short)
        self._set_text(self.txt_rewards, m.rewards)
        self._set_text(self.txt_imp_flags, m.important_flags)

    def _apply_meta_from_ui(self):
        m = self.project.meta
        m.quest_name = self.var_quest_name.get().strip()
        m.region = self.var_region.get().strip()
        m.quest_giver = self.var_quest_giver.get().strip()
        m.prerequisite = self.var_prereq.get().strip()
        m.quest_type = self.var_type.get().strip()
        m.version_stamp = self.var_version.get().strip()

        m.short_description = self._get_text(self.txt_short).strip()
        m.meta_short = self._get_text(self.txt_meta_short).strip()
        m.rewards = self._get_text(self.txt_rewards).strip()
        m.important_flags = self._get_text(self.txt_imp_flags).strip()

    # ---------- Nodes list ----------
    def _refresh_node_list(self):
        self.lst_nodes.delete(0, tk.END)
        for n in self.project.nodes:
            self.lst_nodes.insert(tk.END, f"{n.node_id}  —  {n.title}")

    def _on_node_select(self, _evt):
        if not self.lst_nodes.curselection():
            return
        idx = int(self.lst_nodes.curselection()[0])
        self._select_node(idx)

    def _select_node(self, idx: int):
        # vorherigen Knoten sichern
        if self.current_node_index is not None:
            self._apply_current_node(silent=True)

        self.current_node_index = idx
        n = self.project.nodes[idx]

        self.var_node_id.set(n.node_id)
        self.var_node_title.set(n.title)
        self._set_text(self.txt_scene, n.scene)
        self._set_text(self.txt_dialog, n.dialog)
        self._set_text(self.txt_content, n.content)
        self._set_text(self.txt_info, list_to_lines(n.info_items))
        self._set_text(self.txt_tech, list_to_lines(n.tech_flags))
        self._set_text(self.txt_outcomes, list_to_lines(n.outcomes))
        self._set_text(self.txt_notes, n.notes)

        self._reload_options_tree(n)

        self.lst_nodes.selection_clear(0, tk.END)
        self.lst_nodes.selection_set(idx)
        self.lst_nodes.activate(idx)

    def _add_node(self):
        # Metas & current node sichern
        self._apply_meta_from_ui()
        self._apply_current_node(silent=True)

        # neue ID generieren
        base = "knoten"
        i = 1
        existing = {n.node_id for n in self.project.nodes}
        new_id = f"{base}-{i}"
        while new_id in existing:
            i += 1
            new_id = f"{base}-{i}"

        new_node = Node(node_id=new_id, title=f"Knoten {i}", options=[Option(label="Weiter", target="end")])
        self.project.nodes.append(new_node)
        self._refresh_node_list()
        self._select_node(len(self.project.nodes)-1)

    def _delete_node(self):
        if self.current_node_index is None:
            return
        if len(self.project.nodes) <= 1:
            messagebox.showwarning("Nein.", "Mindestens ein Knoten muss bleiben. (Sonst stolpert die HTML über die Leere.)")
            return

        idx = self.current_node_index
        n = self.project.nodes[idx]
        if not messagebox.askyesno("Knoten löschen", f"Knoten '{n.node_id}' wirklich löschen?"):
            return

        del self.project.nodes[idx]
        self.current_node_index = None
        self._refresh_node_list()
        self._select_node(max(0, idx-1))

    def _move_node(self, direction: int):
        if self.current_node_index is None:
            return
        idx = self.current_node_index
        new_idx = idx + direction
        if new_idx < 0 or new_idx >= len(self.project.nodes):
            return

        self._apply_current_node(silent=True)

        self.project.nodes[idx], self.project.nodes[new_idx] = self.project.nodes[new_idx], self.project.nodes[idx]
        self._refresh_node_list()
        self._select_node(new_idx)

    # ---------- Node <-> UI ----------
    def _apply_current_node(self, silent: bool=False):
        if self.current_node_index is None:
            return
        n = self.project.nodes[self.current_node_index]

        node_id = sanitize_id(self.var_node_id.get())
        title = self.var_node_title.get().strip()

        # ID-Kollision prüfen
        if node_id != n.node_id:
            existing = {x.node_id for x in self.project.nodes}
            if node_id in existing:
                if not silent:
                    messagebox.showerror("ID existiert", f"Die Knoten-ID '{node_id}' gibt es schon. Wähle eine andere.")
                self.var_node_id.set(n.node_id)
                return

        n.node_id = node_id
        n.title = title or n.node_id
        n.scene = self._get_text(self.txt_scene).strip()
        n.dialog = self._get_text(self.txt_dialog).rstrip()
        n.content = self._get_text(self.txt_content).strip()
        n.info_items = lines_to_list(self._get_text(self.txt_info))
        n.tech_flags = lines_to_list(self._get_text(self.txt_tech))
        n.outcomes = lines_to_list(self._get_text(self.txt_outcomes))
        n.notes = self._get_text(self.txt_notes).strip()

        # Optionen aus Tree übernehmen
        n.options = []
        for iid in self.tree_opts.get_children():
            label = self.tree_opts.set(iid, "label").strip()
            target = sanitize_id(self.tree_opts.set(iid, "target").strip())
            n.options.append(Option(label=label, target=target))

        self._refresh_node_list()

    def _id_from_title(self):
        t = self.var_node_title.get().strip()
        if not t:
            return
        self.var_node_id.set(sanitize_id(t))

    # ---------- Optionen ----------
    def _reload_options_tree(self, node: Node):
        self.tree_opts.delete(*self.tree_opts.get_children())
        for opt in node.options:
            self.tree_opts.insert("", tk.END, values=(opt.label, opt.target))

    def _add_option(self):
        self.tree_opts.insert("", tk.END, values=("Neue Option", "top"))

    def _remove_option(self):
        sel = self.tree_opts.selection()
        if not sel:
            return
        for iid in sel:
            self.tree_opts.delete(iid)

    def _edit_option(self):
        sel = self.tree_opts.selection()
        if not sel:
            return
        iid = sel[0]
        cur_label = self.tree_opts.set(iid, "label")
        cur_target = self.tree_opts.set(iid, "target")

        dlg = tk.Toplevel(self)
        dlg.title("Option bearbeiten")
        dlg.transient(self)
        dlg.grab_set()
        dlg.geometry("520x200")

        dlg.columnconfigure(1, weight=1)

        var_l = tk.StringVar(value=cur_label)
        var_t = tk.StringVar(value=cur_target)

        ttk.Label(dlg, text="Label").grid(row=0, column=0, sticky="w", padx=10, pady=10)
        ent_l = ttk.Entry(dlg, textvariable=var_l)
        ent_l.grid(row=0, column=1, sticky="ew", padx=10, pady=10)

        ttk.Label(dlg, text="Ziel-ID").grid(row=1, column=0, sticky="w", padx=10, pady=10)
        ent_t = ttk.Entry(dlg, textvariable=var_t)
        ent_t.grid(row=1, column=1, sticky="ew", padx=10, pady=10)

        # Quick dropdown mit existierenden IDs
        ids = [n.node_id for n in self.project.nodes] + ["top", "end"]
        cmb = ttk.Combobox(dlg, values=ids, textvariable=var_t, state="readonly")
        cmb.grid(row=2, column=1, sticky="ew", padx=10, pady=(0,10))
        ttk.Label(dlg, text="(oder auswählen)").grid(row=2, column=0, sticky="w", padx=10, pady=(0,10))

        def ok():
            self.tree_opts.set(iid, "label", var_l.get().strip())
            self.tree_opts.set(iid, "target", sanitize_id(var_t.get().strip()) or "top")
            dlg.destroy()

        ttk.Button(dlg, text="OK", command=ok).grid(row=3, column=1, sticky="e", padx=10, pady=10)
        ent_l.focus_set()

    # ---------- Projekt speichern/laden ----------
    def _save_project(self):
        self._apply_meta_from_ui()
        self._apply_current_node(silent=True)

        path = filedialog.asksaveasfilename(
            title="Projekt speichern",
            defaultextension=".json",
            filetypes=[("Quest Project (*.json)", "*.json")]
        )
        if not path:
            return

        data = project_to_jsonable(self.project)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("Gespeichert", f"Projekt gespeichert:\n{path}")
        except Exception as e:
            messagebox.showerror("Fehler", f"Konnte nicht speichern:\n{e}")

    def _load_project(self):
        path = filedialog.askopenfilename(
            title="Projekt öffnen",
            filetypes=[("Quest Project (*.json)", "*.json")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.project = project_from_jsonable(data)
            if not self.project.nodes:
                self.project.nodes.append(Node(node_id="start", title="Start"))
            self._load_meta_to_ui()
            self._refresh_node_list()
            self._select_node(0)
            messagebox.showinfo("Geladen", f"Projekt geladen:\n{path}")
        except Exception as e:
            messagebox.showerror("Fehler", f"Konnte nicht laden:\n{e}")

    # ---------- HTML Export ----------
    def _export_html(self):
        self._apply_meta_from_ui()
        self._apply_current_node(silent=True)

        # Minimal sanity: eindeutige IDs
        ids = [n.node_id for n in self.project.nodes]
        if len(ids) != len(set(ids)):
            messagebox.showerror("Fehler", "Es gibt doppelte Knoten-IDs. Bitte korrigieren.")
            return

        path = filedialog.asksaveasfilename(
            title="HTML exportieren",
            defaultextension=".html",
            filetypes=[("HTML (*.html)", "*.html")]
        )
        if not path:
            return

        html = render_html(self.project, include_js=True)
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            messagebox.showinfo("Export fertig", f"HTML exportiert:\n{path}")
        except Exception as e:
            messagebox.showerror("Fehler", f"Konnte HTML nicht schreiben:\n{e}")

    # ---------- Text helpers ----------
    def _get_text(self, widget: ScrolledText) -> str:
        return widget.get("1.0", "end-1c")

    def _set_text(self, widget: ScrolledText, text: str):
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text or "")


if __name__ == "__main__":
    app = QuestEditorApp()
    app.mainloop()
