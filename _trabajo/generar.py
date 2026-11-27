"""Fase 4: escribe la bóveda de Obsidian (notas, colores del grafo y nodos anclados)."""
import json, math, os, re, sys
from mc import HERE
from obras import catalogo

sys.stdout.reconfigure(encoding="utf-8")
VAULT = os.path.dirname(HERE)
tomos = json.load(open(os.path.join(HERE, "indice.json"), encoding="utf-8"))
cosecha = json.load(open(os.path.join(HERE, "cosecha.json"), encoding="utf-8"))
descargas = {}
p = os.path.join(HERE, "descargas.json")
if os.path.exists(p):
    descargas = json.load(open(p, encoding="utf-8"))

HUB = "Poesía chilena"
ROMAN = {"Tomo I": "I", "Tomo II": "II", "Tomo III": "III"}


def safe(s, n=110):
    s = re.sub(r'[\\/:*?"<>|#^\[\]]', "", s).replace("\n", " ")
    s = re.sub(r"\s+", " ", s).strip(" .")
    return s[:n].strip()


def write(rel, content):
    path = os.path.join(VAULT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(content)


def yaml_list(xs):
    return "[" + ", ".join(json.dumps(x, ensure_ascii=False) for x in xs) + "]"


def anio_libro(d):
    for src in (d.get("Datos de publicación", []), d.get("Año", [])):
        for x in src:
            m = re.findall(r"1[5-9]\d\d|20\d\d", x)
            if m and not re.fullmatch(r"\d{4} \d{4}", x.strip()):
                return m[-1]
    return ""


def es_poesia(d):
    mats = " ".join(d.get("Materias", [])).lower()
    return "poes" in mats or "poema" in mats or "verso" in mats


def cargar_bios():
    """Notas biográficas propias para autores sin minisitio (biografias.txt)."""
    bios, cur = {}, None
    ruta = os.path.join(HERE, "biografias.txt")
    if not os.path.exists(ruta):
        return bios
    for line in open(ruta, encoding="utf-8"):
        if line.startswith("## "):
            cur = line[3:].strip(); bios[cur] = []
        elif cur and not line.startswith("#"):
            bios[cur].append(line.rstrip())
    return {k: "\n".join(v).strip() for k, v in bios.items() if "".join(v).strip()}


BIOS = cargar_bios()


def limpiar_pres(t):
    t = re.sub(r'^id="UT_texto_presentacion"[^>]*>\s*', "", t)
    return t.strip()


tomo_notes, mov_notes = {}, {}
obra_count = 0
renombrados = 0
canvas_obras = {}
pin = {}

for ti, t in enumerate(tomos):
    tnote = f"{t['tomo']} — {t['titulo']}"
    tomo_notes[t["tomo"]] = tnote
    movs = []
    for pa in t["partes"]:
        mnote = pa["nombre"]
        movs.append(mnote)
        autores_links = []
        cuerpo = []
        for g in pa["grupos"]:
            if not g["autores"]:
                continue
            if g["nombre"]:
                cuerpo.append(f"\n### Sección {g['nombre'].split()[1]}\n")
            for a in g["autores"]:
                n = a["nombre"]
                autores_links.append(n)
                c = cosecha.get(n, {})
                mini = c.get("minisitio")
                fechas = ""
                if mini:
                    m = re.search(r"\((\d{4}[^)]*)\)", mini["titulo"])
                    fechas = f" ({m.group(1)})" if m else ""
                elif a.get("anio"):
                    fechas = f" ({a['anio']})"
                cuerpo.append(f"- [[{n}]]{fechas}")

                # ---- nota de obra (libros) ----
                obras_poesia, obras_otras = [], []
                for o in catalogo(n):
                    d, anio = o["d"], o["y"]
                    titulo = safe(o["t"], 90)
                    onote = safe(f"{titulo} — {n}" + (f" ({anio})" if anio else ""), 140)
                    canvas_obras.setdefault(n, []).append(onote)
                    if d is None:  # obra sin PDF en Memoria Chilena (bibliografía de Wikipedia)
                        lineas = ["---", "tipo: obra", f"autor: \"[[{n}]]\"",
                                  f"titulo: {json.dumps(o['t'], ensure_ascii=False)}", f"anio: {json.dumps(anio)}",
                                  f"genero: {json.dumps(o['gen'], ensure_ascii=False)}", "pdf: \"\"", "tags: [obra, sin-pdf]", "---",
                                  f"# {o['t']}", "", f"**Autor:** [[{n}]]  "]
                        if anio:
                            lineas.append(f"**Año:** {anio}  ")
                        lineas.append(f"**Género:** {o['gen']}  ")
                        lineas += ["", "## Introducción", "", o["intro"], ""]
                        if not o["curada"]:
                            lineas += ["*Introducción generada con los datos de la bibliografía.*", ""]
                        lineas.append("*Memoria Chilena no tiene digitalizada esta obra.*")
                        lineas.append("")
                        lineas.append(f"🔗 [Buscar en Memoria Chilena]({o['buscar']})"
                                      + (f" · [Bibliografía en Wikipedia]({o['w']})" if o["w"] else ""))
                        write(f"Obras/{onote}.md", "\n".join(lineas) + "\n")
                        obra_count += 1
                        (obras_poesia if o["poe"] else obras_otras).append(
                            (anio, onote, f"[buscar en Memoria Chilena]({o['buscar']}) · *sin PDF*"))
                        continue
                    pdf_local = descargas.get(d["pdf"])
                    if pdf_local:  # nombre limpio: igual que la nota, sin código BN
                        nuevo = f"Obras/PDF/{onote}.pdf"
                        if pdf_local != nuevo and os.path.exists(os.path.join(VAULT, pdf_local)):
                            os.replace(os.path.join(VAULT, pdf_local), os.path.join(VAULT, nuevo))
                            descargas[d["pdf"]] = pdf_local = nuevo
                            renombrados += 1
                    lineas = [
                        "---",
                        "tipo: obra",
                        f"autor: \"[[{n}]]\"",
                        f"titulo: {json.dumps(d['titulo'], ensure_ascii=False)}",
                        f"anio: {json.dumps(anio)}",
                        f"memoria_chilena: {d['url']}",
                        f"pdf_url: {d['pdf']}",
                        f"pdf: {json.dumps(pdf_local or '', ensure_ascii=False)}",
                        "tags: [obra]",
                        "---",
                        f"# {d['titulo']}",
                        "",
                        f"**Autor:** [[{n}]]  ",
                    ]
                    for k in ("Autor secundario", "Datos de publicación", "Descripción física", "Notas", "Materias", "Propiedad intelectual"):
                        if d.get(k):
                            lineas.append(f"**{k}:** {'; '.join(d[k])}  ")
                    lineas += ["", "## Introducción", "", o["intro"], ""]
                    if not o["curada"]:
                        lineas += ["*Introducción generada con los datos de la ficha.*", ""]
                    if pdf_local:
                        lineas.append(f"📖 **[[{pdf_local}|Abrir el libro]]**")
                        lineas.append("")
                    lineas.append(f"🔗 [Ficha en Memoria Chilena]({d['url']}) · [PDF en línea]({d['pdf']})")
                    write(f"Obras/{onote}.md", "\n".join(lineas) + "\n")
                    obra_count += 1
                    (obras_poesia if o["poe"] else obras_otras).append(
                        (anio, onote, f"[ficha]({d['url']}) · [PDF en línea]({d['pdf']})"))

                # ---- nota de autor ----
                L = ["---", "tipo: autor", f"movimiento: \"[[{mnote}]]\""]
                if mini:
                    L.append(f"memoria_chilena: {mini['url']}")
                if fechas:
                    L.append(f"fechas: {json.dumps(fechas.strip(' ()'))}")
                L += ["tags: [autor]", "---", f"# {n}{fechas}", "",
                      f"**Movimiento:** [[{mnote}]]"
                      + (f" · Sección {g['nombre'].split()[1]}" if g["nombre"] else ""), ""]
                L.append("## Descripción (Memoria Chilena)\n")
                if mini:
                    lead = re.sub(r"^.*?\(\d{4}[^)]*\)\s*", "", mini["lead"]).strip()
                    if lead:
                        L.append("> " + lead.replace("\n", "\n> "))
                        L.append("")
                    pres = limpiar_pres(mini["presentacion"])
                    if pres:
                        L.append(pres)
                        L.append("")
                    L.append(f"*Fuente:* [{mini['titulo']} — Memoria Chilena]({mini['url']})")
                else:
                    if n in BIOS:
                        L[-1] = "## Nota biográfica\n"
                        L.append(BIOS[n])
                        L.append("")
                        L.append("*Nota redactada para este mapa: Memoria Chilena no tiene un minisitio dedicado a este autor.*")
                    else:
                        L.append("> [!note] Memoria Chilena no tiene un minisitio dedicado a este autor.")
                    if c.get("autoridad"):
                        L.append(("" if n in BIOS else "> ") + f"Ficha de autoría en Memoria Chilena: https://www.memoriachilena.gob.cl/602/w3-propertyvalue-{c['autoridad'][0]}.html")
                L.append("")
                L.append("## Poemas en la antología de Nómez\n")
                L += [f"- {x}" for x in a["poemas"]]
                L.append("")
                L.append("## Obras\n")
                if obras_poesia or obras_otras:
                    if obras_poesia:
                        L.append("### Poesía\n")
                        L += [f"- [[{o}]] · {ln}" for _, o, ln in sorted(obras_poesia, key=lambda x: (x[0] or "9999", x[1]))]
                        L.append("")
                    if obras_otras:
                        L.append("### Otras obras\n" if obras_poesia else "")
                        L += [f"- [[{o}]] · {ln}" for _, o, ln in sorted(obras_otras, key=lambda x: (x[0] or "9999", x[1]))]
                        L.append("")
                else:
                    L.append("*No se encontró la bibliografía de este autor en Memoria Chilena ni en Wikipedia.*\n")
                write(f"Autores/{n}.md", "\n".join(L))
        # ---- nota de movimiento ----
        sub = re.sub(r"^Parte [IV]+(?: \([^)]*\))?\.\s*", "", pa["titulo"])
        M = ["---", "tipo: movimiento", "tags: [movimiento]", "---",
             f"# {mnote}", "", f"*{sub[0].upper() + sub[1:]}*", "", f"↑ [[{HUB}]]", "",
             "## Autores", ""] + cuerpo
        write(f"Movimientos/{mnote}.md", "\n".join(M) + "\n")
        mov_notes[mnote] = tnote
pin[f"{HUB}.md"] = {"x": 0, "y": 0}
todos_movs = [pa["nombre"] for t in tomos for pa in t["partes"]]
for k, mv in enumerate(todos_movs):
    a2 = math.radians(-90 + 360 * k / len(todos_movs))
    pin[f"Movimientos/{mv}.md"] = {"x": round(1200 * math.cos(a2)), "y": round(1200 * math.sin(a2))}
H = ["---", "tipo: indice", "tags: [indice]", "---", f"# {HUB}", "",
     "Mapa conceptual a partir del índice de **Naín Nómez, *Antología crítica de la poesía chilena***.",
     "Cada movimiento lleva a sus poetas; cada poeta, a sus libros digitalizados en Memoria Chilena.", "", "## Movimientos", ""]
H += [f"- [[{m}]]" for m in todos_movs]
H.append("")
write(f"{HUB}.md", "\n".join(H))

# ---- configuración de Obsidian ----
obs = os.path.join(VAULT, ".obsidian")
os.makedirs(obs, exist_ok=True)


def rgb(h):
    return int(h.lstrip("#"), 16)


graph = {
    "collapse-filter": False, "search": "-path:_trabajo", "showTags": False, "showAttachments": False,
    "hideUnresolved": True, "showOrphans": False,
    "collapse-color-groups": False,
    "colorGroups": [
        {"query": "path:\"Poesía chilena.md\"", "color": {"a": 1, "rgb": rgb("#f5c542")}},
        {"query": "path:Movimientos", "color": {"a": 1, "rgb": rgb("#d64550")}},
        {"query": "path:Autores", "color": {"a": 1, "rgb": rgb("#4a90d9")}},
        {"query": "path:Obras", "color": {"a": 1, "rgb": rgb("#5bb874")}},
    ],
    "collapse-display": False, "showArrow": False, "textFadeMultiplier": -0.6, "nodeSizeMultiplier": 1.4,
    "lineSizeMultiplier": 1, "collapse-forces": False,
    "centerStrength": 0.35, "repelStrength": 14, "linkStrength": 0.9, "linkDistance": 160,
    "scale": 0.25, "close": False,
}
json.dump(graph, open(os.path.join(obs, "graph.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(["extended-graph"], open(os.path.join(obs, "community-plugins.json"), "w"))
egdir = os.path.join(obs, "plugins", "extended-graph")
os.makedirs(egdir, exist_ok=True)
eg = {
    "states": [{"id": "default-vault", "name": "Mapa (nodos anclados)", "toggleTypes": {}, "logicTypes": {},
                "pinNodes": pin, "enableLayers": False, "currentLayerLevel": 0,
                "engineOptions": {k: graph[k] for k in ("search", "showTags", "showAttachments", "hideUnresolved",
                                                         "showOrphans", "colorGroups", "showArrow", "textFadeMultiplier",
                                                         "nodeSizeMultiplier", "lineSizeMultiplier", "centerStrength",
                                                         "repelStrength", "linkStrength", "linkDistance", "scale")}}],
    "startingStateID": "default-vault",
    "enableFeatures": {"graph": {"auto-enabled": True}, "localgraph": {"auto-enabled": False}},
}
json.dump(eg, open(os.path.join(egdir, "data.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump({"userIgnoreFilters": ["_trabajo/"], "attachmentFolderPath": "Obras/PDF", "alwaysUpdateLinks": True},
          open(os.path.join(obs, "app.json"), "w"), indent=1)
print(f"autores={sum(len(g['autores']) for t in tomos for p in t['partes'] for g in p['grupos'])} obras={obra_count} anclados={len(pin)}")

json.dump(descargas, open(os.path.join(HERE, "descargas.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("PDFs renombrados:", renombrados)

# ---- Canvas con posiciones fijas: centro -> movimientos -> autores -> obras (en rayos) ----
nodes, edges = [], []
def card(id_, txt, x, y, w, h, color=None):
    n = {"id": id_, "type": "text", "text": txt, "x": round(x - w / 2), "y": round(y - h / 2), "width": w, "height": h}
    if color: n["color"] = color
    nodes.append(n)
def edge(a, b, color=None):
    e = {"id": f"e{len(edges)}", "fromNode": a, "toNode": b}
    if color: e["color"] = color
    edges.append(e)

card("hub", f"# [[{HUB}]]", 0, 0, 520, 140, "3")
movs_autores = [(pa["nombre"], [a["nombre"] for g in pa["grupos"] for a in g["autores"]]) for t in tomos for pa in t["partes"]]
total = sum(len(al) for _, al in movs_autores)
R_MOV, R_AUT, R_OBRA = 4500, 13000, 13500
idx = 0
for mi, (mv, al) in enumerate(movs_autores):
    a0 = -math.pi / 2 + 2 * math.pi * idx / total
    a1 = -math.pi / 2 + 2 * math.pi * (idx + len(al)) / total
    am = (a0 + a1) / 2
    mid = f"m{mi}"
    card(mid, f"## [[{mv}]]", R_MOV * math.cos(am), R_MOV * math.sin(am), 560, 120, "1")
    edge("hub", mid, "1")
    for ai, n in enumerate(al):
        ang = -math.pi / 2 + 2 * math.pi * (idx + 0.5) / total
        aid = f"a{idx}"
        card(aid, f"**[[{n}]]**", R_AUT * math.cos(ang), R_AUT * math.sin(ang), 380, 70, "5")
        edge(mid, aid, "5")
        paso = abs(math.cos(ang)) * 420 + abs(math.sin(ang)) * 60 + 40  # extensión de la tarjeta a lo largo del rayo
        for oi, o in enumerate(canvas_obras.get(n, [])):
            r = R_OBRA + oi * paso
            oid = f"o{idx}_{oi}"
            card(oid, f"[[{o}|{o.split(' — ')[0]}]]", r * math.cos(ang), r * math.sin(ang), 420, 60, "4")
            edge(aid, oid, "4")
        idx += 1
json.dump({"nodes": nodes, "edges": edges}, open(os.path.join(VAULT, "Mapa de la poesía chilena.canvas"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("canvas:", len(nodes), "nodos")
