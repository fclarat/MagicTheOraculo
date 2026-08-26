# 🐈‍⬛ Black Cat Magic

Un oráculo de **20 preguntas** que adivina tu carta de *Magic: The Gathering*
preguntando por sus **propiedades** (color, coste, tipo, subtipo, keywords,
efectos…), no deletreando el nombre.

Inspirado en [TwentyQuestionsMagicTheGathering](https://jslinker.github.io/TwentyQuestionsMagicTheGathering/),
pero con un motor distinto para que "ande mejor".

## Por qué anda mejor que un árbol de decisión

El proyecto original usa un **árbol de decisión precomputado**: preguntas fijas
y, cuando quedan pocas cartas, un *tiebreaker* que te hace deletrear el nombre.
Tiene tres problemas: si te equivocás en una respuesta se va por la rama
equivocada y no se recupera; adivina deletreando en vez de por propiedades; y el
orden de preguntas es rígido.

Black Cat Magic usa un **motor bayesiano con ganancia de información** (más
parecido a Akinator):

- **Creencia probabilística.** Mantiene una probabilidad sobre las 450 cartas.
  Cada respuesta *re-pondera* (nunca elimina), así que una respuesta equivocada
  baja una carta pero no la mata → **es recuperable**.
- **Pregunta más informativa.** En cada paso elige la pregunta que maximiza la
  reducción de entropía dada la creencia actual. No hay orden fijo.
- **Respuestas difusas.** Sí / Probablemente / No sé / Probablemente no / No,
  cada una con su verosimilitud.
- **Por propiedades reales de Scryfall**, sin depender del Tagger privado. Los
  empates se rompen por popularidad (EDHREC), no por el abecedario.

## Estructura

```
blackcatmagic/
├── index.html          App standalone (GitHub Pages / doble-clic)
├── artifact.html       Misma app, sin wrapper, para publicar como Artifact
├── data/
│   └── cards.json      450 cartas + catálogo de 57 features (generado)
└── scripts/
    ├── build_data.py   Baja cartas de Scryfall y deriva el feature vector
    ├── app.html        Fuente única de la app (con placeholder __DATA__)
    └── build_site.py   Inyecta los datos y genera index.html + artifact.html
```

## Regenerar / buildear

Requiere Python 3 (solo stdlib, sin dependencias).

```bash
python scripts/build_data.py     # baja el dataset de Scryfall -> data/cards.json
python scripts/build_site.py     # arma index.html + artifact.html
```

## Correr localmente

```bash
python -m http.server 8765
```

Y abrí <http://localhost:8765/index.html>. (También funciona con doble-clic en
`index.html`, porque los datos van embebidos.)

## Deploy a GitHub Pages

Subí el repo a GitHub y activá Pages sobre la rama `main` / carpeta raíz.
`index.html` es el punto de entrada.

## Roadmap

- [ ] Arte real de las cartas (la versión GitHub Pages puede cargar imágenes del
      CDN de Scryfall; el Artifact no, por CSP).
- [ ] Comprimir las preguntas de color (hoy pregunta color por color).
- [ ] Modo "adiviná vos": el juego piensa una carta y vos preguntás.
- [ ] Más cartas / elegir el pool (Commander, Standard, Vintage…).

## Créditos

- Datos de cartas: [Scryfall](https://scryfall.com) (API pública).
- Idea original: proyecto de jslinker enlazado arriba.
- *Magic: The Gathering* es propiedad de Wizards of the Coast. Proyecto de
  hobby, sin fines comerciales.
