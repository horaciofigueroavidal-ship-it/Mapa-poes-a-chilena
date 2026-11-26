"""Fase 3: descarga los PDF de los libros a Obras/PDF (reanudable).
Uso: python descargar.py [--medir] [--solo-poesia]"""
import json, os, re, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from mc import HERE, UA

sys.stdout.reconfigure(encoding="utf-8")
VAULT = os.path.dirname(HERE)
PDFDIR = os.path.join(VAULT, "Obras", "PDF")
os.makedirs(PDFDIR, exist_ok=True)
cosecha = json.load(open(os.path.join(HERE, "cosecha.json"), encoding="utf-8"))
REG = os.path.join(HERE, "descargas.json")
reg = json.load(open(REG, encoding="utf-8")) if os.path.exists(REG) else {}
SIZES = os.path.join(HERE, "tamanos.json")
sizes = json.load(open(SIZES, encoding="utf-8")) if os.path.exists(SIZES) else {}
lock = Lock()
solo_poesia = "--solo-poesia" in sys.argv


def safe(s, n=80):
    s = re.sub(r'[\\/:*?"<>|#^\[\]]', "", s)
    return re.sub(r"\s+", " ", s).strip(" .")[:n].strip()


def es_poesia(d):
    m = " ".join(d.get("Materias", [])).lower()
    return "poes" in m or "poema" in m or "verso" in m


jobs = []
for autor, rec in cosecha.items():
    for d in rec["libros"]:
        if solo_poesia and not es_poesia(d):
            continue
        code = (d.get("Códigos BN") or [os.path.basename(d["pdf"])[:-4]])[0]
        name = f"{safe(autor, 40)} - {safe(d['titulo'])} ({code}).pdf"
        jobs.append((d["pdf"], name))


def https(u):
    return u.replace("http://", "https://")


def medir(job):
    url, _ = job
    if url in sizes:
        return
    try:
        req = urllib.request.Request(https(url), method="HEAD", headers={"User-Agent": UA})
        n = int(urllib.request.urlopen(req, timeout=60).headers.get("Content-Length", 0))
    except Exception as e:
        n = -1
    with lock:
        sizes[url] = n


def bajar(job):
    url, name = job
    dest = os.path.join(PDFDIR, name)
    if url in reg and os.path.exists(os.path.join(VAULT, reg[url])):
        return
    tmp = dest + ".part"
    try:
        req = urllib.request.Request(https(url), headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as f:
            while chunk := r.read(1 << 20):
                f.write(chunk)
        os.replace(tmp, dest)
        with lock:
            reg[url] = f"Obras/PDF/{name}"
            json.dump(reg, open(REG, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("ok", name, flush=True)
    except Exception as e:
        print("ERROR", name, e, flush=True)


if "--medir" in sys.argv:
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(medir, jobs))
    json.dump(sizes, open(SIZES, "w"), indent=1)
    tot = sum(max(sizes[u], 0) for u, _ in jobs)
    print(f"{len(jobs)} PDFs, {tot / 1e9:.1f} GB")
else:
    with ThreadPoolExecutor(4) as ex:
        list(ex.map(bajar, jobs))
    print("descargados:", len(reg))
