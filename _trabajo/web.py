"""Genera el mapa web (GitHub Pages) en docs/.

- docs/data.js: lo mínimo para dibujar (nombres, títulos, posiciones ya calculadas).
- docs/d/N.json: el detalle de cada poeta (descripción, poemas, introducciones de sus obras); la página
  lo descarga solo cuando alguien hace clic. Así el mapa abre rápido aunque tenga miles de obras.
- Las posiciones se calculan aquí (no en el navegador): cada movimiento ocupa un sector del círculo,
  sus poetas se acomodan en filas hacia afuera y las obras giran en espiral alrededor de su poeta.
"""
import glob, json, math, os, random, re, sys
from mc import HERE
from generar import limpiar_pres, BIOS  # reutiliza funciones (genera la bóveda de paso)
from obras import catalogo

sys.stdout.reconfigure(encoding="utf-8")
VAULT = os.path.dirname(HERE)
DOCS = os.path.join(VAULT, "docs")
tomos = json.load(open(os.path.join(HERE, "indice.json"), encoding="utf-8"))
cosecha = json.load(open(os.path.join(HERE, "cosecha.json"), encoding="utf-8"))

movs, autores = [], []
por_id = {}
for t in tomos:
    for pa in t["partes"]:
        sub = re.sub(r"^Parte [IV]+(?: \([^)]*\))?\.\s*", "", pa["titulo"])
        movs.append({"id": pa["nombre"], "sub": sub[0].upper() + sub[1:]})
        for g in pa["grupos"]:
            for a in g["autores"]:
                n = a["nombre"]
                grupo = {"t": t["tomo"], "m": pa["nombre"], "l": [p for p in a["poemas"] if p]}
                if n in por_id:  # el poeta figura en otro tomo: suma el movimiento y los poemas
                    previo = por_id[n]
                    previo["movs"].append(pa["nombre"]); previo["pg"].append(grupo)
                    if not previo["f"] and a.get("anio"):
                        previo["f"] = a["anio"]
                    continue
                c = cosecha.get(n, {})
                mini = c.get("minisitio")
                fechas = ""
                if mini:
                    m = re.search(r"\((\d{4}[^)]*)\)", mini["titulo"])
                    fechas = m.group(1) if m else ""
                elif a.get("anio"):
                    fechas = a["anio"]
                obras = [{k: o[k] for k in ("t", "y", "u", "p", "poe", "pub", "gen", "intro", "w", "buscar")}
                         | {"auto": not o["curada"]} for o in catalogo(n)]
                obras.sort(key=lambda o: (not o["poe"], o["y"] or "9999"))
                por_id[n] = {
                    "id": n, "mov": pa["nombre"], "movs": [pa["nombre"]], "pg": [grupo], "f": fechas,
                    "lead": re.sub(r"^.*?\(\d{4}[^)]*\)\s*", "", mini["lead"]).strip() if mini else "",
                    "pres": limpiar_pres(mini["presentacion"]) if mini else "",
                    "bio": BIOS.get(n, "") if not mini else "",
                    "mc": mini["url"] if mini else (f"https://www.memoriachilena.gob.cl/602/w3-propertyvalue-{c['autoridad'][0]}.html" if c.get("autoridad") else ""),
                    "obras": obras,
                }
                autores.append(por_id[n])

# ---------- posiciones (estrellas fijas, iguales en cada visita) ----------
R_MOV, R0, ESP = 900, 1180, 7.0   # radio de los movimientos, primera fila de poetas, separación entre obras
rnd = random.Random(42)
M = len(movs)


def radio_grupo(a):  # radio del racimo poeta + obras
    return 10 + ESP * math.sqrt(len(a["obras"])) + 3


for i, mv in enumerate(movs):
    th = -math.pi / 2 + 2 * math.pi * i / M
    mv.update(ang=round(th, 5), x=round(R_MOV * math.cos(th)), y=round(R_MOV * math.sin(th)))
    ancho = 2 * math.pi / M * 0.9
    propios = [a for a in autores if a["mov"] == mv["id"]]
    R, k = R0, 0
    while k < len(propios):  # llena una fila (arco) y pasa a la siguiente, más afuera
        fila, usado = [], 0.0
        while k < len(propios):
            need = 2 * radio_grupo(propios[k]) + 14
            if fila and usado + need > ancho * R:
                break
            fila.append((propios[k], need)); usado += need; k += 1
        grueso = max(2 * radio_grupo(a) for a, _ in fila)
        rc, acum = R + grueso / 2, 0.0
        for a, need in fila:
            ang = th - usado / (2 * rc) + (acum + need / 2) / rc
            rr = rc + (rnd.random() - .5) * (grueso - 2 * radio_grupo(a)) * .8
            a["x"], a["y"] = rr * math.cos(ang), rr * math.sin(ang)
            acum += need
        R += grueso + 20
for a in autores:  # obras en espiral (girasol) alrededor del poeta
    giro = rnd.random() * 2 * math.pi
    for j, o in enumerate(a["obras"]):
        r, ang = 11 + ESP * math.sqrt(j + .5), giro + j * 2.39996
        o["px"], o["py"] = round(a["x"] + r * math.cos(ang)), round(a["y"] + r * math.sin(ang))
    a["x"], a["y"] = round(a["x"]), round(a["y"])

# ---------- archivos ----------
os.makedirs(os.path.join(DOCS, "d"), exist_ok=True)
for f in glob.glob(os.path.join(DOCS, "d", "*.json")):
    os.remove(f)
ligero = []
for i, a in enumerate(autores):
    det = {k: a[k] for k in ("lead", "pres", "bio", "mc", "pg")}
    det["o"] = [{k: o[k] for k in ("u", "p", "pub", "gen", "intro", "w", "buscar", "auto")} for o in a["obras"]]
    with open(os.path.join(DOCS, "d", f"{i}.json"), "w", encoding="utf-8") as f:
        json.dump(det, f, ensure_ascii=False, separators=(",", ":"))
    # obra: [título, año, banderas (1 = PDF, 2 = poesía), x, y]
    ligero.append({"id": a["id"], "movs": a["movs"], "f": a["f"], "x": a["x"], "y": a["y"],
                   "o": [[o["t"], o["y"], (1 if o["p"] else 0) | (2 if o["poe"] else 0), o["px"], o["py"]] for o in a["obras"]]})
with open(os.path.join(DOCS, "data.js"), "w", encoding="utf-8") as f:
    f.write("window.DATA=" + json.dumps({"movs": movs, "autores": ligero}, ensure_ascii=False, separators=(",", ":")) + ";\n")
print("movimientos", len(movs), "autores", len(autores), "obras", sum(len(a["obras"]) for a in autores),
      "data.js", os.path.getsize(os.path.join(DOCS, "data.js")) // 1024, "KB")
