# Observatorio de landers

Un archivo fechado de landers propias y de competencia, para ver cómo se mueve
el mercado en vez de recordarlo.

Una lander de competencia cambia sin avisar: cambian el titular, suman un paso
al formulario, mueven el precio, meten escasez. Si no la capturaste antes, el
cambio no existe y solo queda la sensación de que "algo cambió". Esto deja una
foto con fecha y, al volver a capturar, dice exactamente qué se movió.

## Las tres categorías

| | Qué es | Qué se mira |
|---|---|---|
| **quiz-lander** | Califica con preguntas antes de pedir datos | Cuántos pasos, dónde piden el dato, qué preguntan |
| **lowticket-lander** | Vende un producto de entrada barato, sin llamada | Precio, garantía, qué incluyen |
| **thankyou-page** | Lo que ve el lead después de convertir | Si hay siguiente paso o se muere ahí |

## Uso

```bash
python3 observatorio/snapshot.py                    # captura todas
python3 observatorio/snapshot.py virtus-planescalado # solo una
python3 observatorio/snapshot.py --listar           # qué hay indexado
python3 observatorio/snapshot.py --hosts            # hosts que faltan permitir

python3 observatorio/reporte.py --guardar           # arma INFORME.md
```

## Añadir una lander

Un objeto más en `landers.json` y correr `snapshot.py`. Los campos que importan
son `slug`, `url`, `dueno` (mio / competencia), `categoria` y `nichos`.

Si el host no está permitido en la red de la sesión, la captura falla y el
script lo dice al final con el nombre del host. Hay que autorizarlo antes de
reintentar: es una decisión del dueño de la cuenta, no algo que el script pueda
saltarse.

## Qué detecta cada captura

- **Stack** — GoHighLevel, Meta Pixel, Typeform, Calendly, Stripe y compañía.
  Solo cuenta si el recurso se carga de verdad; una marca nombrada en una lista
  de herramientas no es el stack de la página.
- **Palancas de conversión** — escasez por tiempo o por cupo, gratis / sin
  tarjeta, barra de progreso, gamificación, prueba social, garantía.
- **Campos del formulario** y **preguntas** visibles.
- **Titular**.

## Una limitación que conviene saber

La captura es del HTML que devuelve el servidor, sin ejecutar JavaScript. En
una lander que arma su formulario con JS —como el diagnóstico propio— se ven
menos campos y preguntas de los que el visitante ve en pantalla. Para la
competencia suele alcanzar, porque el copy de venta viene en el HTML. Si
alguna página aparece casi vacía, es por esto y hay que mirarla con un
navegador.

## Dónde queda cada cosa

```
observatorio/
  landers.json          el índice: qué se vigila
  snapshot.py           captura y compara
  reporte.py            arma el informe
  INFORME.md            la última comparación, legible
  capturas/
    <slug>/<fecha>/     pagina.html · texto.txt · ficha.json
```

Las capturas están excluidas del deploy en `.vercelignore`: sin eso, Vercel
publicaría copias de landers ajenas colgando de tu dominio.
