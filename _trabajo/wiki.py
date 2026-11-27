"""Fase 2b: bibliografía completa y datos biográficos de cada autor desde Wikipedia en español.

Escribe wiki.json: {autor: {"pagina", "url", "extracto", "obras": [{"t", "y", "g"}]}}
"""
import hashlib, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
from mc import tokens, norm, HERE, CACHE

UA = "mapa-poesia-chilena/1.0 (proyecto academico; Python-urllib)"


def get(url):
    """GET con caché; respeta los límites de Wikipedia (una consulta por segundo, espera ante 429)."""
    path = os.path.join(CACHE, hashlib.md5(url.encode()).hexdigest() + ".html")
    if os.path.exists(path):
        return open(path, encoding="utf-8").read()
    for i in range(8):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            data = urllib.request.urlopen(req, timeout=60).read().decode("utf-8")
            open(path, "w", encoding="utf-8").write(data)
            time.sleep(1.0)
            return data
        except urllib.error.HTTPError as e:
            espera = int(e.headers.get("Retry-After") or 0) or 30 * (i + 1)
            print(f"  ! {e.code}, espero {espera}s", file=sys.stderr, flush=True)
            time.sleep(espera)
        except Exception as e:
            print("  ! error", e, file=sys.stderr, flush=True)
            time.sleep(5)
    return ""

sys.stdout.reconfigure(encoding="utf-8")
API = "https://es.wikipedia.org/w/api.php?format=json&"
tomos = json.load(open(os.path.join(HERE, "indice.json"), encoding="utf-8"))

# página forzada (o None para ignorar Wikipedia) cuando la búsqueda falla
PAGE_OVERRIDE = {
    "Jaime Gómez Rogers (Jonás)": "Jaime Gómez Rogers",
    "Juan Cristóbal Romero": None,  # la búsqueda da otro Juan Romero
}


def api(**kw):
    raw = get(API + urllib.parse.urlencode(kw))
    try:
        return json.loads(raw)
    except Exception:
        return {}


def buscar(nombre, anio):
    limpio = re.sub(r"\(.*?\)", "", nombre).strip()
    if nombre in PAGE_OVERRIDE:
        return PAGE_OVERRIDE[nombre]
    ntoks = set(tokens(limpio))
    for q in (f'"{limpio}" poeta chileno', f"{limpio} poeta", limpio):
        r = api(action="query", list="search", srsearch=q, srlimit=8)
        for h in r.get("query", {}).get("search", []):
            if "desambiguaci" in h["title"]:
                continue
            tt = set(tokens(re.sub(r"\(.*?\)", "", h["title"])))
            if not tt or not tt <= ntoks | {"poeta", "escritor", "escritora", "chile", "chileno", "chilena"}:
                continue
            if len(tt & ntoks) < min(2, len(ntoks)):
                continue
            snip = norm(h.get("snippet", ""))
            if "chile" not in snip and "poet" not in snip and "escrit" not in snip:
                continue
            return h["title"]
    return None


SEC_OK = re.compile(r"^(obras?|bibliograf[ií]a|publicaciones|libros|poes[ií]a|poemarios|narrativa|novelas?|cuentos?|ensayos?|"
                    r"teatro|antolog[ií]as?|cr[oó]nicas?|traducciones|prosa|obra (po[eé]tica|literaria|publicada)|"
                    r"libros publicados|obra selecta|producci[oó]n literaria)", re.I)
SEC_STOP = re.compile(r"^(referencias|notas|enlaces|v[eé]ase|bibliograf[ií]a (sobre|cr[ií]tica|consultada)|premios|"
                      r"reconocimientos|distinciones|estudios|fuentes)", re.I)
# subsecciones que no son libros del autor
SUB_NO = re.compile(r"en antolog|sobre (el|la|su)|estudios|colaboraci|prensa|peri[oó]dic|revistas?|diarios?|discograf|"
                    r"filmograf|ediciones de las obras completas|poemas (publicados|sueltos)|inc?luid[oa]s? en|"
                    r"traducciones de su obra|premios|cr[ií]tica sobre", re.I)
PRENSA = re.compile(r"\b(lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)\b|N[°º]\s*\d", re.I)


def limpiar_wiki(s):
    s = re.sub(r"<ref[^>]*/>|<ref.*?</ref>", "", s, flags=re.S)
    s = re.sub(r"\{\{.*?\}\}", "", s)
    s = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"\[https?://\S+ ([^\]]*)\]", r"\1", s)
    s = re.sub(r"<[^>]+>", "", s)
    return s


def obras_de(wikitext):
    out, genero, dentro = [], None, False
    for line in wikitext.split("\n"):
        h = re.match(r"^(=+)\s*(.*?)\s*\1\s*$", line)
        if h:
            nivel, tit = len(h.group(1)), limpiar_wiki(h.group(2)).strip()
            if SEC_STOP.match(tit):
                dentro = False
            elif SEC_OK.match(tit):
                dentro = True
                genero = tit if nivel > 2 or not re.match(r"^(obras?|bibliograf|publicaciones|libros)", tit, re.I) else None
            elif dentro and nivel > 2 and SUB_NO.search(tit):
                genero = "__omitir__"
            elif dentro and nivel > 2:
                genero = tit
            elif nivel <= 2:
                dentro = False
            continue
        if not dentro or not line.startswith(("*", "#")) or genero == "__omitir__":
            continue
        if line.startswith(("**", "##", "*:", "#:")):  # subitems (tomos, poemas sueltos dentro de un libro)
            continue
        raw = line.lstrip("*#: ")
        if PRENSA.search(raw) or re.match(r"^(?:[IVXL]+|\d+)\.\s", limpiar_wiki(raw).strip()):
            continue
        m = re.search(r"''+(.+?)''+", raw)
        txt = limpiar_wiki(raw)
        tit = limpiar_wiki(m.group(1)).strip() if m else re.split(r"\s[\(\[,.–-]\s?\(?\d{4}|\s\(", txt)[0].strip()
        tit = re.split(r'["”]|,\s*(?:poes[ií]a|poemas?|novela|cuentos?|ensayos?|teatro)\b', tit.lstrip(" \"“«'"))[0]
        tit = tit.strip(" .,:;\"«»“”'")
        y = re.search(r"\b(1[6-9]\d\d|20[0-2]\d)\b", txt)
        if not tit or len(tit) > 140 or len(tit) < 2:
            continue
        out.append({"t": tit, "y": y.group(1) if y else "", "g": genero or "", "nota": txt.strip()[:300]})
    # sin duplicados
    seen, res = set(), []
    for o in out:
        k = norm(o["t"])
        if k not in seen:
            seen.add(k); res.append(o)
    return res


def procesar(a):
    n = a["nombre"]
    page = buscar(n, a.get("anio"))
    if not page:
        return n, None
    p = api(action="parse", page=page, prop="wikitext", redirects=1)
    wt = p.get("parse", {}).get("wikitext", {}).get("*", "")
    intro = re.split(r"\n==", wt, maxsplit=1)[0]
    intro = re.sub(r"\{\{(?:[^{}]|\{\{[^{}]*\}\})*\}\}", "", intro)
    intro = re.sub(r"\[\[(?:Archivo|File|Imagen|Image):[^\n]*", "", intro)
    ext = re.sub(r"'{2,}", "", limpiar_wiki(intro)).strip()
    if "puede referirse" in ext[:300] or not re.search(r"poet|escrit|literat|cronista|periodista|narrador|dramaturg", norm(ext[:1500])):
        return n, None
    if "chile" not in norm(wt[:6000] + ext) and n not in ("Rubén Darío",):
        return n, None
    return n, {"pagina": page, "url": "https://es.wikipedia.org/wiki/" + urllib.parse.quote(page.replace(" ", "_")),
               "extracto": ext.strip(), "obras": obras_de(wt)}


if __name__ == "__main__":
    authors = [a for t in tomos for p in t["partes"] for g in p["grupos"] for a in g["autores"]]
    res = {}
    for i, a in enumerate(authors):
        n, v = procesar(a)
        res[n] = v
        estado = f"{v['pagina']} · obras {len(v['obras'])}" if v else "— sin página"
        print(f"{i + 1:3}/{len(authors)} {n:32} {estado}", flush=True)
    json.dump(res, open(os.path.join(HERE, "wiki.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    con = [k for k, v in res.items() if v]
    print("con página", len(con), "de", len(res), "· obras", sum(len(res[k]["obras"]) for k in con))
