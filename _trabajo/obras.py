"""Catálogo unificado de obras por autor: libros de Memoria Chilena (con PDF) + bibliografía de Wikipedia.

Cada obra: {t, y, gen, poe, u (ficha MC), p (PDF MC), pub, w (Wikipedia), intro, curada}
"""
import json, os, re, urllib.parse
from mc import HERE, norm

cosecha = json.load(open(os.path.join(HERE, "cosecha.json"), encoding="utf-8"))
_wp = os.path.join(HERE, "wiki.json")
wiki = json.load(open(_wp, encoding="utf-8")) if os.path.exists(_wp) else {}
BUSCAR_MC = "https://www.memoriachilena.gob.cl/602/w3-search.php?searchmode=and&start=0&keywords="


def _cargar_intros():
    out, cur = {}, None
    ruta = os.path.join(HERE, "obras_intro.txt")
    if os.path.exists(ruta):
        for line in open(ruta, encoding="utf-8"):
            if line.startswith("## "):
                a, _, t = line[3:].partition("|")
                cur = (a.strip(), norm(t).strip()); out[cur] = []
            elif cur and not line.startswith("#"):
                out[cur].append(line.rstrip())
    return {k: "\n".join(v).strip() for k, v in out.items() if "".join(v).strip()}


INTROS = _cargar_intros()


def _cargar_extra():
    out, cur = {}, None
    ruta = os.path.join(HERE, "obras_extra.txt")
    if os.path.exists(ruta):
        for line in open(ruta, encoding="utf-8"):
            line = line.strip()
            if line.startswith("## "):
                cur = line[3:].strip(); out[cur] = []
            elif cur and line and not line.startswith("#"):
                t, y, g = (line.split("|") + ["", ""])[:3]
                out[cur].append({"t": t.strip(), "y": y.strip(), "g": g.strip()})
    return out


EXTRA = _cargar_extra()
usadas = set()


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


def clave(t):
    k = norm(t)
    k = re.sub(r"\b(el|la|los|las|un|una|y|de|del|en)\b", " ", k)
    return re.sub(r"\s+", " ", k).strip()[:28]


def mismo(a, b):
    ka, kb = clave(a), clave(b)
    return bool(ka and kb) and (ka.startswith(kb) or kb.startswith(ka))


GEN = [
    (r"poes|poema|verso|cancion|sonet|lir", "Libro de poesía", True),
    (r"antolog|seleccion|recopil", "Antología", None),
    (r"novel", "Novela", False),
    (r"cuent|relato|narrativ", "Libro de narrativa", False),
    (r"ensay|critic|estudio|prosa", "Ensayo o prosa", False),
    (r"teatro|drama|comedia", "Obra de teatro", False),
    (r"cronic|memori|autobiogr|testimon|diario", "Crónica o memorias", False),
    (r"traduc", "Traducción", False),
    (r"infantil|niños|ninos", "Libro para niños", None),
]


def genero(texto, default_poe):
    t = norm(texto or "")
    for pat, nombre, poe in GEN:
        if re.search(pat, t):
            return nombre, (default_poe if poe is None else poe)
    return ("Libro de poesía" if default_poe else "Obra"), default_poe


def _intro_curada(autor, t):
    ct = clave(t)
    for (a, k), txt in INTROS.items():
        ck = clave(k)
        if a == autor and ck and ct and (ct.startswith(ck[:20]) or ck.startswith(ct)):
            usadas.add((a, k))
            return txt
    return ""


def _intro_auto(autor, o, prev, nxt, idx, total):
    partes = []
    fem = o["gen"].split()[0] in ("Novela", "Antología", "Obra", "Traducción", "Crónica")
    cuando = f", publicad{'a' if fem else 'o'} en {o['y']}" if o["y"] else ""
    partes.append(f"{o['gen']} de {autor}{cuando}.")
    if o.get("pub"):
        partes.append(f"Datos de edición: {o['pub'].rstrip('.')}.")
    if o.get("extra"):
        partes.append(o["extra"].rstrip(".") + ".")
    if total > 1 and o["y"]:
        if idx == 0:
            partes.append("Es el primer título de su bibliografía registrada.")
        elif idx == total - 1:
            partes.append("Es el título más tardío de su bibliografía registrada.")
        if prev and prev["y"] and idx > 0:
            partes.append(f"Le precede «{prev['t']}» ({prev['y']})" + (f" y le sigue «{nxt['t']}» ({nxt['y']})." if nxt and nxt["y"] else "."))
    mats = [m for m in o.get("mats", []) if not re.fullmatch(r"(?i)(poes[ií]as?|literatura|cuentos|novelas|ensayos) chilen[ao]s?", m.strip())]
    if mats:
        partes.append("Materias en Memoria Chilena: " + "; ".join(mats) + ".")
    return " ".join(partes)


def _extra_wiki(w):
    """Lo que la línea de Wikipedia dice además del título y el año (editorial, premio, etc.)."""
    nota = w.get("nota", "")
    nota = re.sub(re.escape(w["t"]), "", nota, flags=re.I)
    nota = re.sub(r"[''«»\"]", "", nota)
    nota = re.sub(r"^[\s,.:;()\-–—\d]+|[\s,.:;(\-–—]+$", "", nota)
    nota = re.sub(r"\(\s*\)|\s{2,}", " ", nota).strip(" ,.;:")
    sin_gen = re.sub(r"(?i)\b(poes[ií]a|poemario|poemas|novela|cuentos?|ensayos?|teatro|antolog[ií]a|cr[oó]nicas?)\b", "", nota)
    if len(nota) < 4 or re.fullmatch(r"[\d\s,.;:()\-–]+", sin_gen):
        return ""
    return nota[0].upper() + nota[1:]


BASURA = {"poesia", "poesias", "plaquette", "narrativa", "ensayo", "ensayos", "antologia", "antologias", "novela",
          "cuentos", "teatro", "obras", "obra", "libros", "inedito", "ineditos"}


def catalogo(autor):
    c = cosecha.get(autor, {})
    out = []
    for d in c.get("libros", []):
        gen, poe = ("Libro de poesía", True) if es_poesia(d) else genero(" ".join(d.get("Materias", [])), False)
        out.append({"t": d["titulo"], "y": anio_libro(d), "gen": gen, "poe": poe, "u": d["url"],
                    "p": d["pdf"].replace("http://", "https://"), "pub": "; ".join(d.get("Datos de publicación", [])),
                    "mats": d.get("Materias", []), "w": "", "d": d})
    wk = wiki.get(autor) or {}
    for w in wk.get("obras", []):
        if norm(w["t"]).strip() in BASURA or re.match(r"(?i)en coautor|con prólogo|edición de|traducción de", w["t"]) \
                or re.search(r"(?i)enciclopedia de chile|diccionario histórico, biográfico|diccionario de literatura española|\|\w+=", w["t"]):  # fuentes citadas, no obras
            continue
        if any(mismo(o["t"], w["t"]) and not o["u"] for o in out):  # repetida dentro de Wikipedia
            continue
        prev = next((o for o in out if mismo(o["t"], w["t"])), None)
        if prev:
            prev["w"] = wk["url"]
            continue
        resto = re.sub(re.escape(w["t"]), "", w.get("nota", ""), flags=re.I)
        gen, poe = genero(w.get("g") or resto, True)
        out.append({"t": w["t"], "y": w["y"], "gen": gen, "poe": poe, "u": "", "p": "", "pub": "", "mats": [],
                    "w": wk["url"], "extra": _extra_wiki(w), "d": None})
    for x in EXTRA.get(autor, []):
        if any(mismo(o["t"], x["t"]) for o in out):
            continue
        gen, poe = genero(x["g"], not x["g"])
        out.append({"t": x["t"], "y": x["y"], "gen": gen, "poe": poe, "u": "", "p": "", "pub": "", "mats": [],
                    "w": "", "extra": "", "d": None})
    out.sort(key=lambda o: (o["y"] or "9999", o["t"]))
    for i, o in enumerate(out):
        cur = _intro_curada(autor, o["t"])
        o["curada"] = bool(cur)
        o["intro"] = cur or _intro_auto(autor, o, out[i - 1] if i else None, out[i + 1] if i + 1 < len(out) else None, i, len(out))
        o["buscar"] = BUSCAR_MC + urllib.parse.quote(o["t"][:60])
    return out
