"""Genera docs/data.js para el mapa web (GitHub Pages)."""
import json, os, re, sys
from mc import HERE
from generar import limpiar_pres, BIOS  # reutiliza funciones (genera la bóveda de paso)
from obras import catalogo

sys.stdout.reconfigure(encoding="utf-8")
VAULT = os.path.dirname(HERE)
tomos = json.load(open(os.path.join(HERE, "indice.json"), encoding="utf-8"))
cosecha = json.load(open(os.path.join(HERE, "cosecha.json"), encoding="utf-8"))

movs, autores = [], []
for t in tomos:
    for pa in t["partes"]:
        sub = re.sub(r"^Parte [IV]+(?: \([^)]*\))?\.\s*", "", pa["titulo"])
        movs.append({"id": pa["nombre"], "sub": sub[0].upper() + sub[1:]})
        for g in pa["grupos"]:
            for a in g["autores"]:
                n = a["nombre"]
                grupo = {"t": t["tomo"], "m": pa["nombre"], "l": [p for p in a["poemas"] if p]}
                previo = next((x for x in autores if x["id"] == n), None)
                if previo:  # el poeta figura en otro tomo: suma el movimiento y los poemas
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
                obras = []
                for o in catalogo(n):
                    obras.append({k: o[k] for k in ("t", "y", "u", "p", "poe", "pub", "gen", "intro", "w", "buscar")}
                                 | {"auto": not o["curada"]})
                obras.sort(key=lambda o: (not o["poe"], o["y"] or "9999"))
                autores.append({
                    "id": n, "mov": pa["nombre"], "movs": [pa["nombre"]], "pg": [grupo], "f": fechas,
                    "lead": re.sub(r"^.*?\(\d{4}[^)]*\)\s*", "", mini["lead"]).strip() if mini else "",
                    "pres": limpiar_pres(mini["presentacion"]) if mini else "",
                    "bio": BIOS.get(n, "") if not mini else "",
                    "mc": mini["url"] if mini else (f"https://www.memoriachilena.gob.cl/602/w3-propertyvalue-{c['autoridad'][0]}.html" if c.get("autoridad") else ""),
                    "obras": obras,
                })

os.makedirs(os.path.join(VAULT, "docs"), exist_ok=True)
with open(os.path.join(VAULT, "docs", "data.js"), "w", encoding="utf-8") as f:
    f.write("window.DATA=" + json.dumps({"movs": movs, "autores": autores}, ensure_ascii=False) + ";\n")
print("movimientos", len(movs), "autores", len(autores), "obras", sum(len(a["obras"]) for a in autores))
