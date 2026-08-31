# Magic The Mini Games

Una colección de **8 juegos de Magic: The Gathering**. El principal, *El
Oráculo*, adivina una carta por sus propiedades —color, coste, tipo, subtipo,
keywords y efectos— sin hacerte deletrear su nombre.

Está inspirado en [TwentyQuestionsMagicTheGathering](https://jslinker.github.io/TwentyQuestionsMagicTheGathering/),
pero usa un motor distinto, recuperable ante respuestas imprecisas.

## El Oráculo

En lugar de un árbol de decisión fijo, mantiene una creencia probabilística
sobre más de **32.000 cartas** y elige en cada turno la pregunta con mayor
ganancia de información.

- Las respuestas son difusas: Sí / Probablemente / No sé / Probablemente no / No.
- Una respuesta equivocada baja la probabilidad de una carta, pero no la elimina.
- Las preguntas salen de propiedades reales de Scryfall.
- La popularidad de EDHREC solo desempata entre cartas muy parecidas.

## Estructura

```
blackcatmagic/
├── index.html          Hub de juegos; entrada de GitHub Pages
├── oraculo.html        El Oráculo para el sitio web
├── cardle.html …       Los otros siete juegos
├── theme.css           Sistema visual compartido
├── data/
│   ├── cards.json      Oráculo: cartas + catálogo de features
│   ├── all.json        Datos completos para MTG-dle
│   ├── names.json      Índice liviano de nombres para autocompletar
│   ├── famous.json     Pool curado de respuestas diarias
│   ├── reveal.json     Pistas del Grimorio
│   └── years.json      Año y primera impresión para Timeline
└── scripts/
    ├── build.py        Pipeline completo, en el orden correcto
    ├── build_data.py   Baja cartas de Scryfall y deriva los features
    ├── app.html        Fuente única del Oráculo
    └── build_site.py   Genera oraculo.html + artifact.html
```

## Regenerar / buildear

Requiere Python 3 y no tiene dependencias externas.

```bash
python scripts/build.py
```

El pipeline reconstruye todos los datasets derivados, completa las primeras
impresiones que falten, genera el Oráculo y aplica los metadatos de enlaces. Los
scripts individuales siguen siendo útiles para iterar una parte concreta.

## Correr localmente

```bash
python -m http.server 8765
```

Abrí <http://localhost:8765/index.html>.

El Oráculo conserva sus datos embebidos y puede abrirse solo como
`oraculo.html`. Los demás juegos cargan JSON con `fetch`, por lo que deben
servirse por HTTP: no funcionan correctamente al abrirlos con `file://` por
doble clic.

## Deploy a GitHub Pages

Subí el repo a GitHub y activá Pages sobre la rama `main` / carpeta raíz.
`index.html` es el punto de entrada.

## Roadmap

- [x] Arte real de las cartas desde el CDN de Scryfall en la versión web.
- [ ] Comprimir las preguntas de color (hoy pregunta color por color).
- [ ] Modo “adiviná vos”: el juego piensa una carta y vos preguntás.
- [ ] Más pools elegibles (Commander, Standard, Vintage…).

## Créditos

- Datos de cartas: [Scryfall](https://scryfall.com) (API pública).
- Idea original: proyecto de jslinker enlazado arriba.
- *Magic: The Gathering* es propiedad de Wizards of the Coast. Proyecto de
  hobby, sin fines comerciales.
