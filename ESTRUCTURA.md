# Estructura del sitio

Definida el 2026-08-16. Dos mundos que no se mezclan, más el nivelador en la
raíz.

```
/                     Nivelador — quiz de captación (público, indexado)
/interno/             Lo que opera el negocio propio (no indexado)
  /interno/offer/     Oferta v1.0 — la página que se manda a un lead
/consultoria/         Lo que se entrega o se copia al negocio de un cliente
```

## La regla que separa los dos

| Va a `/interno` | Va a `/consultoria` |
|---|---|
| Es de Patricio y para Patricio | Se duplica, se entrega o se copia a un cliente |
| Oferta, paneles, planes, proyecciones | Moldes, roadmaps por cliente, biblioteca de recursos |
| `noindex` | `noindex` |

Si una pieza sirve para las dos cosas, vive en `/interno` y se **duplica** al
entregarla. El molde nunca se edita en su lugar.

## Migración a Vercel

Esta estructura ya está pensada para eso. Hoy en GitHub Pages las rutas
arrastran el nombre del repo:

```
pvt-build.github.io/privatebuild/interno/offer/
```

En Vercel, apuntando el proyecto a este repo con output estático, quedan
limpias:

```
tudominio.com/interno/offer
```

No hay que reescribir nada: las rutas son relativas y las carpetas se traducen
directo. Lo único a revisar al migrar:

1. **El favicon y los assets** usan rutas relativas (`../claude-favicon.png`).
   Si cambia la profundidad de una página, se ajusta ahí.
2. **`/interno` y `/consultoria` deben quedar fuera del indexado.** Ya llevan
   `<meta name="robots" content="noindex, nofollow">`; en Vercel conviene
   sumar un `robots.txt` que los excluya.
3. **El nivelador tiene sync automático desde Notion** que reescribe
   `index.html` cada hora. Ese proceso apunta a la raíz — confirmar que no
   pise las carpetas nuevas.

## Pendientes de la estructura

- Consolidar los paneles que hoy viven en repos aparte (`dashboard`,
  `athlete-os`) bajo `/interno`, o dejarlos y enlazarlos. Decisión abierta.
- Publicar los roadmaps de cliente que ya existen en el disco
  (`consulting-laurastm-ready-to-push/`, `Clientes/KATHE_SABRENT/`).
- Mover el molde de consultoría desde `Docs vivos/consultoria-template.html`.
