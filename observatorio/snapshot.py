#!/usr/bin/env python3
"""Captura una lander y la guarda fechada, para poder comparar con el tiempo.

Una lander de competencia cambia sin avisar: cambian el titular, suman un paso
al formulario, mueven el precio. Si no la capturaste antes, el cambio no existe.
Esto deja una foto con fecha de cada una y, cuando vuelves a capturar, te dice
qué se movió.

    python3 observatorio/snapshot.py                 # todas las pendientes
    python3 observatorio/snapshot.py virtus-planescalado
    python3 observatorio/snapshot.py --listar
    python3 observatorio/snapshot.py --hosts         # qué falta permitir en la red

Las capturas van a observatorio/capturas/<slug>/<fecha>/.
"""

import datetime
import html
import io
import json
import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OBS = os.path.join(RAIZ, 'observatorio')
CAPTURAS = os.path.join(OBS, 'capturas')
INDICE = os.path.join(OBS, 'landers.json')

# Qué hay debajo de la página. Saber el stack dice cómo la corren.
STACK = {
    'GoHighLevel':   r'cdn\.msgsndr|leadconnector\.com|//[\w.-]*gohighlevel\.com',
    'Meta Pixel':    r'fbq\(|connect\.facebook\.net',
    'Google Ads/GA': r'gtag\(|googletagmanager',
    'TikTok Pixel':  r'ttq\.|analytics\.tiktok',
    'Typeform':      r'//[\w.-]*typeform\.com',
    'ManyChat':      r'//[\w.-]*manychat\.com',
    'Calendly':      r'//[\w.-]*calendly\.com',
    'Hotjar':        r'//[\w.-]*hotjar\.com',
    'MS Clarity':    r'clarity\.ms',
    'Hubspot':       r'hs-scripts|hubspot',
    'Klaviyo':       r'//[\w.-]*klaviyo\.com',
    'Stripe':        r'js\.stripe\.com',
    'Vimeo':         r'player\.vimeo',
    'Wistia':        r'//[\w.-]*wistia\.(com|net)',
    'YouTube':       r'youtube\.com/embed|youtu\.be',
    'WhatsApp':      r'wa\.me|api\.whatsapp',
    'Framer':        r'framerusercontent',
    'Webflow':       r'//[\w.-]*webflow\.com',
    'Unbounce':      r'//[\w.-]*unbounce\.com',
    'ClickFunnels':  r'//[\w.-]*clickfunnels\.com',
}

# Recursos de urgencia y prueba. Lo que usan para que lo completes.
PALANCAS = {
    'escasez por tiempo':  r'solo hoy|s[o\u00f3]lo hoy|[u\u00fa]ltimas? horas|termina (hoy|en)|expira',
    'escasez por cupo':    r'cupos?|plazas?|quedan \d+|[u\u00fa]ltimos? \d+',
    'gratis / sin tarjeta': r'\bgratis\b|sin costo|sin tarjeta',
    'barra de progreso':   r'paso \d+ de \d+|pregunta \d+ de \d+|\d+%\s*completado',
    'gamificacion':        r'\bxp\b|nivel \d+|desbloquea|bloqueado',
    'prueba social':       r'testimonio|caso de [e\u00e9]xito|clientes? dicen|rese[n\u00f1]a',
    'garantia':            r'garant[i\u00ed]a|devoluci[o\u00f3]n|reembolso',
    'autoridad por cifra': r'\+?\d[\d.,]*\s*(k|mil|millones|m)\b.*(facturad|vendid|generad)',
}


def cargar():
    return json.load(io.open(INDICE, encoding='utf-8'))


def bajar(url):
    """Devuelve (html, error). Usa curl, que ya está configurado para el proxy."""
    try:
        r = subprocess.run(
            ['curl', '-sS', '-L', '--max-time', '60', '--compressed', url],
            capture_output=True, timeout=90)
    except subprocess.TimeoutExpired:
        return None, 'se agotó el tiempo'
    if r.returncode != 0:
        err = r.stderr.decode('utf-8', 'replace').strip()
        if '403' in err or 'tunnel' in err.lower() or 'resolve' in err.lower():
            return None, 'host bloqueado por la red de la sesión'
        return None, err[:200] or 'curl salió con código %d' % r.returncode
    return r.stdout.decode('utf-8', 'replace'), None


def texto_visible(s):
    t = re.sub(r'<(script|style|noscript)[^>]*>.*?</\1>', ' ', s, flags=re.S | re.I)
    t = re.sub(r'<[^>]+>', '\n', t)
    t = html.unescape(t)
    out, vistos = [], set()
    for l in t.split('\n'):
        l = ' '.join(l.split())
        if len(l) < 2 or l in vistos:
            continue
        vistos.add(l)
        out.append(l)
    return out


def campos(s):
    res = []
    for m in re.finditer(r'<(input|select|textarea)\b[^>]*>', s, re.I):
        at = dict(re.findall(r'([\w-]+)=["\']([^"\']*)["\']', m.group(0)))
        if at.get('type') in ('hidden', 'submit', 'button'):
            continue
        d = {k: at[k] for k in ('type', 'name', 'placeholder', 'inputmode') if k in at}
        if d and d not in res:
            res.append(d)
    return res


def preguntas(lineas):
    return [l for l in lineas if l.rstrip().endswith('?') and 8 < len(l) < 130]


def analizar(s):
    lineas = texto_visible(s)
    plano = '\n'.join(lineas).lower()
    return {
        'bytes': len(s),
        'stack': sorted(k for k, p in STACK.items() if re.search(p, s, re.I)),
        'palancas': sorted(k for k, p in PALANCAS.items() if re.search(p, plano, re.I)),
        'campos_formulario': campos(s),
        'preguntas': preguntas(lineas)[:25],
        'titular': next((l for l in lineas if len(l) > 18), ''),
        'lineas_texto': len(lineas),
    }


def anteriores(slug):
    d = os.path.join(CAPTURAS, slug)
    return sorted(os.listdir(d)) if os.path.isdir(d) else []


def diferencias(viejo, nuevo):
    out = []
    for campo in ('stack', 'palancas', 'preguntas'):
        a, b = set(map(str, viejo.get(campo, []))), set(map(str, nuevo.get(campo, [])))
        for x in sorted(b - a):
            out.append('+ %s: %s' % (campo, x))
        for x in sorted(a - b):
            out.append('- %s: %s' % (campo, x))
    if viejo.get('titular') != nuevo.get('titular'):
        out.append('~ titular: "%s"  ->  "%s"' % (viejo.get('titular', '')[:70],
                                                  nuevo.get('titular', '')[:70]))
    na, nb = len(viejo.get('campos_formulario', [])), len(nuevo.get('campos_formulario', []))
    if na != nb:
        out.append('~ campos del formulario: %d -> %d' % (na, nb))
    return out


def capturar(l, hoy):
    slug, url = l['slug'], l.get('url', '')
    if not url or url == 'PENDIENTE':
        print('  %-24s sin URL todavía' % slug)
        return None

    local = l.get('local')
    if local and os.path.exists(os.path.join(RAIZ, local)):
        s = io.open(os.path.join(RAIZ, local), encoding='utf-8').read()
        err = None
    else:
        s, err = bajar(url)

    if err:
        print('  %-24s %s' % (slug, err))
        return err

    ficha = analizar(s)
    ficha.update({'slug': slug, 'url': url, 'fecha': hoy,
                  'dueno': l.get('dueno'), 'categoria': l.get('categoria'),
                  'nichos': l.get('nichos', [])})

    prev = anteriores(slug)
    d = os.path.join(CAPTURAS, slug, hoy)
    os.makedirs(d, exist_ok=True)
    io.open(os.path.join(d, 'pagina.html'), 'w', encoding='utf-8').write(s)
    io.open(os.path.join(d, 'texto.txt'), 'w', encoding='utf-8').write('\n'.join(texto_visible(s)))
    io.open(os.path.join(d, 'ficha.json'), 'w', encoding='utf-8').write(
        json.dumps(ficha, ensure_ascii=False, indent=2))

    print('  %-24s %d KB · stack: %s' % (slug, len(s) // 1024,
                                         ', '.join(ficha['stack']) or 'nada detectado'))
    if ficha['palancas']:
        print('  %-24s palancas: %s' % ('', ', '.join(ficha['palancas'])))

    viejas = [p for p in prev if p != hoy]
    if viejas:
        ant = os.path.join(CAPTURAS, slug, viejas[-1], 'ficha.json')
        if os.path.exists(ant):
            cambios = diferencias(json.load(io.open(ant, encoding='utf-8')), ficha)
            if cambios:
                print('  %-24s CAMBIOS desde %s:' % ('', viejas[-1]))
                for c in cambios:
                    print('  %-24s   %s' % ('', c))
            else:
                print('  %-24s sin cambios desde %s' % ('', viejas[-1]))
    return None


def main():
    d = cargar()
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    flags = [a for a in sys.argv[1:] if a.startswith('--')]

    if '--listar' in flags:
        for cat in d['categorias']:
            ls = [l for l in d['landers'] if l.get('categoria') == cat]
            print('\n%s  (%d)' % (cat.upper(), len(ls)))
            print('  ' + d['categorias'][cat])
            for l in ls:
                print('    %-24s %-12s %s' % (l['slug'], l.get('dueno', ''),
                                              ', '.join(l.get('nichos', []))))
        return 0

    if '--hosts' in flags:
        hs = sorted({re.sub(r'^https?://([^/]+).*', r'\1', l['url'])
                     for l in d['landers']
                     if l.get('url', 'PENDIENTE') != 'PENDIENTE' and not l.get('local')})
        print('Hosts que el observatorio necesita alcanzar:')
        for h in hs:
            print('  ' + h)
        return 0

    hoy = datetime.date.today().isoformat()
    objetivo = [l for l in d['landers'] if not args or l['slug'] in args]
    print('Capturando %d lander(s) · %s\n' % (len(objetivo), hoy))
    bloqueados = []
    for l in objetivo:
        err = capturar(l, hoy)
        if err and 'bloqueado' in err:
            bloqueados.append(re.sub(r'^https?://([^/]+).*', r'\1', l['url']))
    if bloqueados:
        print('\nHay que permitir estos hosts en la red de la sesión:')
        for h in sorted(set(bloqueados)):
            print('  ' + h)
    return 0


if __name__ == '__main__':
    sys.exit(main())
