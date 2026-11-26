"""Fase 1: para cada autor del índice, encuentra su minisitio y su ficha de autoría en Memoria Chilena."""
import json, os, re, sys
from mc import search, get, links, tokens, norm, HERE

sys.stdout.reconfigure(encoding="utf-8")


def parse_indice():
    tomos = []
    for line in open(os.path.join(HERE, "indice.txt"), encoding="utf-8"):
        line = line.rstrip("\n")
        if not line or line.startswith("#"):
            continue
        k, _, v = line.partition(": ")
        parts = [p.strip() for p in v.split(" | ")]
        if k == "T":
            tomos.append({"tomo": parts[0], "titulo": parts[1], "partes": []})
        elif k == "P":
            tomos[-1]["partes"].append({"nombre": parts[0], "titulo": parts[1], "grupos": [{"nombre": None, "autores": []}]})
        elif k == "S":
            tomos[-1]["partes"][-1]["grupos"].append({"nombre": parts[0], "autores": []})
        elif k == "A":
            tomos[-1]["partes"][-1]["grupos"][-1]["autores"].append({"nombre": parts[0], "anio": parts[1] if len(parts) > 1 else None, "poemas": []})
        elif k == "N":
            tomos[-1]["partes"][-1]["grupos"][-1]["autores"][-1]["poemas"] = parts
    return tomos


def all_authors(tomos):
    for t in tomos:
        for p in t["partes"]:
            for g in p["grupos"]:
                for a in g["autores"]:
                    yield t, p, g, a


def match_all(name_toks, label):
    lt = set(tokens(label))
    return all(t in lt for t in name_toks)


def resolve(a):
    name = re.sub(r"\s*\(.*?\)", "", a["nombre"])  # quita (Jonás)
    toks = [t for t in tokens(name) if len(t) > 1]
    res = search(name)
    # ficha de autoría: "Apellido, Nombre, 1879-1908"
    auth = [(i, l) for kind, i, l in res if kind == "propertyvalue" and "," in l and match_all(toks, l)]
    mini = [(i, l) for kind, i, l in res if kind == "article" and re.search(r"\(\d{4}", l) and match_all(toks, l.split("(")[0])]
    if not auth and len(toks) > 2:  # intenta con nombre + primer apellido
        res2 = search(" ".join(toks[:2]))
        auth = [(i, l) for kind, i, l in res2 if kind == "propertyvalue" and "," in l and match_all(toks[:2], l)]
        mini = mini or [(i, l) for kind, i, l in res2 if kind == "article" and re.search(r"\(\d{4}", l) and match_all(toks[:2], l.split("(")[0])]
    dedup = lambda xs: list(dict.fromkeys(xs))
    return dedup(auth), dedup(mini)


if __name__ == "__main__":
    tomos = parse_indice()
    out = {}
    for t, p, g, a in all_authors(tomos):
        auth, mini = resolve(a)
        out[a["nombre"]] = {"autoridad": auth, "minisitio": mini}
        print(f"{a['nombre']:35} AUT={auth[:3]}  MINI={mini[:2]}", flush=True)
    json.dump(tomos, open(os.path.join(HERE, "indice.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(out, open(os.path.join(HERE, "resolucion.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
