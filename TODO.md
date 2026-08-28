# TODO / Ideas — Magic The Oráculo

## ⏸️ Base de datos compartida (parqueado — esperando config de Firebase)

Objetivo: juntar las **cartas que se buscaron y el oráculo no encontró** en una
base central, para mejorar el sistema para todos (no local).

**Estado:** el lado cliente ya está hecho y desplegado. Cada búsqueda no-encontrada
se manda a Firestore vía REST (ver `submitSearch()` en `scripts/app.html`).
Está **dormido** hasta cargar la config (`const FB = { projectId:'', apiKey:'' }`).

**Falta (del lado de Facu):**
1. Crear proyecto Firebase (gratis) + Firestore Database (modo producción).
2. Publicar las reglas de `scripts/firestore.rules` (append-only).
3. Registrar una app web y pasar `projectId` + `apiKey`.
4. → Yo relleno `FB` en `scripts/app.html`, rebuild + deploy, y pruebo una escritura real.
5. Para mejorar el grimorio: `python scripts/fetch_searches.py <projectId> <apiKey>`
   (agrega las más pedidas: faltantes → agregar; presentes → afinar features).

Alternativas si Firebase no cuaja: Supabase, o un Google Form/Formspree.

## 🟡 Decisión pendiente

- Bucket de coste **"1"** hoy incluye coste 0 (Black Lotus, Moxen). ¿Relabelear a **"0-1"**?

## 💡 Ideas de juegos nuevos (de los amigos)

- **Cardle** (guess-the-card por revelado progresivo): primero el color de fondo,
  después el tipo de carta, después una parte de la imagen, y así hasta el título.
  Adivinás el nombre; cada intento revela más. Reusa datos + imágenes de Scryfall.
- **Wordle con títulos de cartas**: adivinar el nombre de una carta estilo Wordle.
  (Ojo: los nombres no tienen largo fijo → hay que adaptar el Wordle clásico.)
