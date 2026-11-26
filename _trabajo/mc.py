"""Utilidades para leer Memoria Chilena con caché en disco."""
import hashlib, html, json, os, re, sys, time, unicodedata, urllib.parse, urllib.request

BASE = "https://www.memoriachilena.gob.cl/602/"
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")
os.makedirs(CACHE, exist_ok=True)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) mapa-poesia-chilena"


def get(url, tries=3):
    if not url.startswith("http"):
        url = BASE + url
    key = hashlib.md5(url.encode()).hexdigest()
    path = os.path.join(CACHE, key + ".html")
    if os.path.exists(path):
        return open(path, encoding="utf-8").read()
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            data = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
            tmp = path + f".{os.getpid()}.tmp"
            open(tmp, "w", encoding="utf-8").write(data)
            os.replace(tmp, path)
            time.sleep(0.4)
            return data
        except Exception as e:
            print("  ! error", url, e, file=sys.stderr)
            time.sleep(3 * (i + 1))
    return ""


def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]", " ", s)


def tokens(name):
    stop = {"de", "la", "del", "y", "a", "los", "las"}
    return [t for t in norm(name).split() if t not in stop and len(t) > 1]


def text(fragment):
    fragment = re.sub(r"<script.*?</script>|<style.*?</style>", "", fragment, flags=re.S)
    fragment = re.sub(r"<br\s*/?>", "\n", fragment)
    fragment = re.sub(r"</p>|</li>|</h\d>", "\n\n", fragment)
    t = re.sub(r"<[^>]+>", "", fragment)
    t = html.unescape(t)
    t = re.sub(r"[ \t\r\f\v]+", " ", t)
    t = re.sub(r" *\n *", "\n", t)
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def links(page):
    out = []
    for m in re.finditer(r'<a[^>]+href="([^"]*w3-(article|propertyvalue)-(\d+)\.html)"[^>]*>(.*?)</a>', page, re.S):
        label = text(m.group(4))
        if label:
            out.append((m.group(2), int(m.group(3)), label))
    return out


def search(q):
    url = BASE + "w3-search.php?" + urllib.parse.urlencode({"keywords": q, "start": 0, "searchmode": "and"})
    return links(get(url))
