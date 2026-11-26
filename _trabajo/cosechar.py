"""Fase 2: descarga descripción (minisitio) y libros con PDF de cada autor desde Memoria Chilena."""
import json, os, re, sys
from mc import get, links, text, tokens, norm, HERE

sys.stdout.reconfigure(encoding="utf-8")
tomos = json.load(open(os.path.join(HERE, "indice.json"), encoding="utf-8"))
resol = json.load(open(os.path.join(HERE, "resolucion.json"), encoding="utf-8"))

# Correcciones manuales a la resolución automática.
AUTH_OVERRIDE = {
    "Julio Molina": [127303],          # Julio Molina Müller (1918)
    "Bernardo Cruz": [142270],         # Bernardo Cruz Adler (1904)
    "Carlos Barella": [140641, 128546, 1198614],
    "Alberto Moreno": [1190873, 1198618],
    "Augusto Iglesias": [128167],
}
MINI_OVERRIDE = {
    "Andrés Bello": 3290,
    "Rubén Darío": 3700,
}


def year_of(label):
    m = re.search(r"(1[789]\d\d)", label)
    return int(m.group(1)) if m else None


def filter_auth(name, cands, known_year):
    ntoks = set(tokens(re.sub(r"\(.*?\)", "", name)))
    keep = []
    for pid, label in cands:
        lab = re.sub(r",?\s*\d{4}-?(\d{4})?.*$", "", label)
        if "," not in lab:
            continue
        sur, given = lab.split(",", 1)
        st = tokens(sur)
        gt = [t for t in tokens(given) if len(t) > 1]
        if not st or st[0] not in ntoks or not all(t in ntoks for t in gt):
            continue
        y = year_of(label)
        if y and known_year and abs(y - known_year) > 3:
            continue
        extra = [t for t in st if t not in ntoks]
        if extra and not (y and known_year):
            continue
        keep.append(pid)
    return keep


def section(page, start_id, end_id):
    i = page.find(f'id="{start_id}"')
    if i < 0:
        return ""
    j = page.find(f'id="{end_id}"', i)
    return page[i: j if j > 0 else len(page)]


def parse_mini(mid, mini_to_author):
    page = get(f"w3-article-{mid}.html")
    title = text(re.search(r"<title>(.*?)</title>", page, re.S).group(1)).split(" - Memoria Chilena")[0]
    meta = re.search(r'<meta name="description" content="([^"]*)"', page)
    lead = text(meta.group(1)) if meta else ""
    pres_html = section(page, "UT_texto_presentacion", "documentos")
    # enlaces internos a otros autores del mapa -> [[wikilinks]]
    def repl(m):
        aid, label = int(m.group(1)), text(m.group(2))
        if aid in mini_to_author and mini_to_author[aid] != current[0]:
            return f"[[{mini_to_author[aid]}|{label}]]"
        return label
    pres_html = re.sub(r'<a[^>]+href="[^"]*w3-article-(\d+)\.html"[^>]*>(.*?)</a>', repl, pres_html, flags=re.S)
    pres = text(pres_html)
    pres = re.split(r"\n(?:Documentos|Imágenes)\n", pres)[0].strip()
    docs = [i for k, i, l in links(section(page, "documentos", "imagenes")) if k == "article"]
    return {"id": mid, "titulo": title, "lead": lead, "presentacion": pres, "docs": docs,
            "url": f"https://www.memoriachilena.gob.cl/602/w3-article-{mid}.html"}


FIELDS = ["Autor", "Autor secundario", "Propiedad intelectual", "Tipo", "Descripción física",
          "Datos de publicación", "Notas", "Materias", "Año", "Idioma", "Colección", "Códigos BN", "N° sistema",
          "Temas relacionados"]


def parse_doc(did):
    page = get(f"w3-article-{did}.html")
    if not page:
        return None
    pdf = re.findall(r'href="([^"]+\.pdf)"', page, re.I)
    t = text(page)
    i = t.find("Clasificaciones")
    if i < 0:
        return None
    body = t[i:]
    title = text(re.search(r"<title>(.*?)</title>", page, re.S).group(1)).split(" - Memoria Chilena")[0]
    d = {"id": did, "titulo": title, "pdf": pdf[0] if pdf else None,
         "url": f"https://www.memoriachilena.gob.cl/602/w3-article-{did}.html"}
    pat = "|".join(re.escape(f) for f in FIELDS)
    for m in re.finditer(rf"^({pat}):\s*\n?(.*?)(?=^(?:{pat}):|\Z|^Este documento|^Sobre Memoria)", body, re.S | re.M):
        d[m.group(1)] = [x.strip() for x in m.group(2).strip().split("\n") if x.strip()]
    d["autor_ids"] = [int(x) for x in re.findall(r"w3-propertyvalue-(\d+)\.html", page)]
    return d


if __name__ == "__main__":
    authors = [a for t in tomos for p in t["partes"] for g in p["grupos"] for a in g["autores"]]
    # minisitio elegido por autor
    minis = {}
    for a in authors:
        n = a["nombre"]
        if n in MINI_OVERRIDE:
            minis[n] = MINI_OVERRIDE[n]
        elif resol[n]["minisitio"]:
            minis[n] = resol[n]["minisitio"][0][0]
    mini_to_author = {v: k for k, v in minis.items()}
    out = {}
    for a in authors:
        n = a["nombre"]
        current = [n]
        rec = {"minisitio": None, "autoridad": [], "libros": []}
        if n in minis:
            rec["minisitio"] = parse_mini(minis[n], mini_to_author)
        ky = int(a["anio"]) if a.get("anio") else None
        if not ky and rec["minisitio"]:
            ky = year_of(rec["minisitio"]["titulo"])
        auth = AUTH_OVERRIDE.get(n) or filter_auth(n, resol[n]["autoridad"], ky)
        rec["autoridad"] = auth
        cand = []
        for pid in auth:
            cand += [i for k, i, l in links(get(f"w3-propertyvalue-{pid}.html")) if k == "article"]
        if rec["minisitio"]:
            cand += rec["minisitio"]["docs"]
        cand = [c for c in dict.fromkeys(cand) if c not in mini_to_author]
        ntoks = set(tokens(re.sub(r"\(.*?\)", "", n)))

        def es_autor(x):
            if "," not in x:
                return False
            sur, given = x.split(",", 1)
            st = tokens(sur)
            gt = [t for t in tokens(given) if len(t) > 1 and not t.isdigit()]
            return bool(st) and st[0] in ntoks and all(t in ntoks for t in gt)

        seen_pdf = set()
        for did in cand:
            d = parse_doc(did)
            if not d or not d["pdf"]:
                continue
            if "Libro" not in d.get("Tipo", []):
                continue
            ok = es_autor(d.get("Autor", [""])[0])
            if not ok or d["pdf"] in seen_pdf:
                continue
            seen_pdf.add(d["pdf"])
            rec["libros"].append(d)
        out[n] = rec
        print(f"{n:32} mini={'sí' if rec['minisitio'] else '—'}  libros={len(rec['libros'])}", flush=True)
        json.dump(out, open(os.path.join(HERE, "cosecha.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
