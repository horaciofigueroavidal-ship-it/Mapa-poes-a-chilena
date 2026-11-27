# Cómo agregar o corregir autores

## 1. Editar `indice.txt`

Abre `_trabajo/indice.txt` con el Bloc de notas. Cada autor ocupa dos líneas, dentro del movimiento (`P:`) al que pertenece:

```
A: Nombre Apellido | 1950
N: Primer poema | Segundo poema | Tercer poema
```

- `A:` nombre del poeta, tal como se escribe en Memoria Chilena. El año de nacimiento después de `|` es opcional, pero ayuda a identificarlo.
- `N:` poemas, separados por ` | ` (no importa si la lista queda vacía: `N:`).
- Para un movimiento nuevo, agrega antes de sus autores: `P: Nombre corto | Título completo del movimiento`.
- Guarda el archivo en UTF-8 (opción por defecto del Bloc de notas).

## 1b. (Opcional) Nota biográfica propia

Si el autor no tiene minisitio en Memoria Chilena, puedes escribirle una nota en `_trabajo/biografias.txt`:

```
## Nombre exacto como en indice.txt
Texto de la nota (uno o más párrafos; *cursiva* para títulos).
```

## 2. Regenerar

En la carpeta `_trabajo`, haz clic en la barra de direcciones del Explorador, escribe `cmd` y Enter. Luego:

```
python actualizar.py
```

Busca a los autores nuevos en Memoria Chilena, baja sus descripciones y sus libros de poesía, y rehace las notas de Obsidian, el Canvas y el mapa web.

## 3. Publicar

GitHub Desktop → escribe un resumen → **Commit to main** → **Push origin**.

## Si un autor queda mal identificado

Revisa `cosecha.log`. Si a un poeta le asignó el minisitio o la ficha de otra persona, corrígelo en `cosechar.py`:
`MINI_OVERRIDE = {"Nombre": número}` (el número de `w3-article-NÚMERO.html` del minisitio) y
`AUTH_OVERRIDE = {"Nombre": [número]}` (el de `w3-propertyvalue-NÚMERO.html` de la ficha de autoría). Luego vuelve al paso 2.
