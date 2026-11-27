"""Regenera TODO el mapa después de editar indice.txt.

Uso (desde la carpeta _trabajo):   python actualizar.py
Pasos: busca autores en Memoria Chilena -> reúne descripciones y libros -> descarga PDFs de poesía nuevos
       -> rehace las notas de Obsidian y el Canvas -> rehace el mapa web (docs/).
Todo lo ya descargado queda en caché, así que solo se consulta lo nuevo.
"""
import os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
VAULT = os.path.dirname(HERE)


def run(script, *args):
    print(f"\n=== {script} {' '.join(args)} ===", flush=True)
    r = subprocess.run([sys.executable, os.path.join(HERE, script), *args], cwd=HERE)
    if r.returncode:
        sys.exit(f"Falló {script}")


run("resolver.py")
run("cosechar.py")
run("wiki.py")  # bibliografía completa desde Wikipedia
run("descargar.py", "--solo-poesia")
# borrar notas generadas (no toca los PDFs) para que no queden notas viejas
for d in ("Autores", "Movimientos"):
    shutil.rmtree(os.path.join(VAULT, d), ignore_errors=True)
obras = os.path.join(VAULT, "Obras")
if os.path.isdir(obras):
    for f in os.listdir(obras):
        if f.endswith(".md"):
            os.remove(os.path.join(obras, f))
run("web.py")  # incluye generar.py
print("\nListo. Abre GitHub Desktop: Commit to main -> Push origin.")
