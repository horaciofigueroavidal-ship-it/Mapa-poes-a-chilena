"""Precarga en paralelo las páginas que cosechar.py va a pedir (solo llena la caché)."""
import json, os, sys
from concurrent.futures import ThreadPoolExecutor
from mc import get, links, HERE
import cosechar as C  # reutiliza filtros (no ejecuta __main__)

sys.stdout.reconfigure(encoding="utf-8")
authors = [a for t in C.tomos for p in t["partes"] for g in p["grupos"] for a in g["autores"]]
start = int(sys.argv[1]) if len(sys.argv) > 1 else 0


def pages_for(a):
    n = a["nombre"]
    ids = []
    mid = C.MINI_OVERRIDE.get(n) or (C.resol[n]["minisitio"][0][0] if C.resol[n]["minisitio"] else None)
    if mid:
        pg = get(f"w3-article-{mid}.html")
        ids += [i for k, i, l in links(C.section(pg, "documentos", "imagenes")) if k == "article"]
    ky = int(a["anio"]) if a.get("anio") else None
    auth = C.AUTH_OVERRIDE.get(n) or C.filter_auth(n, C.resol[n]["autoridad"], ky)
    for pid in auth:
        ids += [i for k, i, l in links(get(f"w3-propertyvalue-{pid}.html")) if k == "article"]
    return list(dict.fromkeys(ids))


with ThreadPoolExecutor(6) as ex:
    for a in authors[start:]:
        ids = pages_for(a)
        list(ex.map(lambda i: get(f"w3-article-{i}.html"), ids))
        print(a["nombre"], len(ids), flush=True)
