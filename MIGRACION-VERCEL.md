# Migración a Vercel

GitHub Pages sale. El repo se queda: Vercel despliega **desde** GitHub, así que
GitHub sigue siendo la fuente del código y Vercel pasa a ser el que sirve el
sitio. Lo que cambia es el host, el dominio y que recién ahí se puede medir y
capturar data de verdad.

## Qué se gana

| Hoy (GitHub Pages) | Con Vercel |
|---|---|
| `pvt-build.github.io/privatebuild/diagnostico/` | `privatebuild.vercel.app/diagnostico` |
| Solo archivos estáticos | Funciones en `/api` → escribir en Supabase sin exponer llaves |
| Sin variables de entorno | Llaves de Supabase y PostHog fuera del código |
| Sin analítica de verdad | Web Analytics + PostHog |
| Deploy a ciegas | Preview por rama antes de publicar |

## Los pasos (una vez, ~5 minutos)

1. **Conectar el repo.** En vercel.com → Add New → Project → importar
   `pvt-build/privatebuild`.
2. **Framework Preset: Other.** No hay build. Root Directory: `./`.
   Build Command y Output Directory se dejan vacíos.
3. **Deploy.** Queda en `privatebuild.vercel.app`.
4. **Comprobar las rutas:**
   - `/` → el nivelador de siempre
   - `/diagnostico` → el quiz con las tres salidas
   - `/interno/offer` → el deck
5. **Dominio.** Cuando tengas el definitivo, se agrega en Settings → Domains.
   Mientras tanto la URL de vercel.app sirve para la bio.

## Lo que ya quedó preparado en el repo

- **`vercel.json`** — URLs limpias (`/diagnostico`, sin `.html` ni barra final),
  cabeceras de seguridad, caché larga para imágenes y corta para HTML, y
  redirecciones de `/quiz` y `/nivelador` a `/diagnostico`.
- **`manifest.webmanifest`** — al guardarlo en la pantalla de inicio abre en
  pantalla completa, sin barra de navegador. Falta el ícono: cuando tengas el
  logo en PNG de 512×512, se agrega acá y queda con cara de app.
- **El sync de Notion quedó desactivado.** Pusheaba `index.html` a `main` cada
  hora; con Vercel conectado eso serían 24 deploys diarios pisando lo que
  construyamos. Sigue en el repo y se revive descomentando el bloque
  `schedule` en `.github/workflows/notion-sync.yml`.

## Links para la bio

El parámetro `from` identifica de dónde llegó cada lead y viaja con él hasta
Notion:

```
privatebuild.vercel.app/diagnostico?from=ig
privatebuild.vercel.app/diagnostico?from=yt
privatebuild.vercel.app/diagnostico?from=private
```

## Medición: qué hay y qué falta

La página ya dispara los eventos. Están probados y funcionando:

`diagnostico_view` · `quiz_start` · `quiz_answer` (n° y valor) · `lead_submit` ·
`result_view` · `cta_click` (ruta, destino y texto del botón)

Cada evento lleva el canal (`from`), la etapa y la ruta de salida.

Hoy se guardan en `localStorage` bajo `pb_eventos` — se revisan abriendo la
consola del navegador y escribiendo `JSON.parse(localStorage.pb_eventos)`.
Sirve para comprobar que todo dispara, pero **no sirve para medir**: esa data
vive en el teléfono de cada visitante y nunca llega a ti.

Para que llegue falta el proveedor. La función `pvtTrack` ya está escrita para
que, apenas PostHog esté cargado en la página, empiece a mandarle todo sin
tocar una línea más. Eso y el esquema de Supabase es lo que está trabajando el
chat de **Backend y medición**.

## Lo que sigue después del deploy

1. Rellenar las tres URLs en `PVT_RUTAS` (arriba del script en
   `diagnostico/index.html`). Mientras digan `PEGAR-`, esos botones caen a
   WhatsApp con un mensaje propio de cada rama — publica igual.
2. Conectar PostHog y Supabase (chat de backend).
3. Reemplazar el webhook de Make por una función en `/api/lead` que escriba
   directo en Supabase. Ahí recién se puede apagar Make y Notion.
