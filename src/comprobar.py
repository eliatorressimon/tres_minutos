"""Comprobación antes de publicar: si una descarga ha salido mal (portal caído, fichero vacío o
cortado), los números se van a cero o se disparan. En ese caso paramos y no se publica nada.
También se compara con la última versión publicada (web/datos.json en el repositorio): si una cifra
cambia de golpe, es más probable que sea un error en los datos que un cambio real en una semana."""
import json
import os
import subprocess
import sys
import pandas as pd
from config import ELABORADOS, WEB

problemas = []
dea = pd.read_csv(ELABORADOS / 'desfibriladores.csv', dtype=str)
if len(dea) < 10000:
    problemas.append(f'solo hay {len(dea)} desfibriladores en el registro (se esperaban más de 10.000)')
sec = pd.read_csv(ELABORADOS / 'secciones.csv', dtype=str)
if len(sec) < 4000:
    problemas.append(f'solo hay {len(sec)} secciones censales')
osm = ELABORADOS.parent / 'originales' / 'sitios_osm.csv'
if osm.exists() and len(pd.read_csv(osm)) < 300:
    problemas.append(f'solo hay {len(pd.read_csv(osm))} comisarías, bomberos y estaciones de OpenStreetMap (se esperaban unos 800)')
datos = json.loads((WEB / 'datos.json').read_text(encoding='utf-8'))
if not datos:
    problemas.append('web/datos.json está vacío')

# comparación con lo publicado la última vez
try:
    antes = json.loads(subprocess.run(['git', 'show', 'HEAD:web/datos.json'], capture_output=True, check=True,
                                      cwd=WEB.parent).stdout)['resumen']
except (subprocess.CalledProcessError, KeyError, ValueError, FileNotFoundError):
    antes = None
# si el cambio es a propósito (por ejemplo, un cambio de método), se lanza a mano con 'forzar'
if antes and 'resumen' in datos and os.environ.get('FORZAR') != 'true':
    ahora = datos['resumen']
    for clave, nombre in [('andando_martes', 'cobertura del martes a las 11:00'), ('andando_domingo', 'cobertura del domingo a las 3:00')]:
        if clave in antes and abs(ahora[clave] - antes[clave]) > 5:
            problemas.append(f'la {nombre} pasa del {antes[clave]} % al {ahora[clave]} % en una semana')
    if 'registro' in antes and abs(ahora['registro'] - antes['registro']) > 0.2 * antes['registro']:
        problemas.append(f"el registro pasa de {antes['registro']} a {ahora['registro']} aparatos")

if problemas:
    print('No se publica:')
    for p in problemas:
        print(' -', p)
    sys.exit(1)
print('Todo en orden:', len(dea), 'desfibriladores y', len(sec), 'secciones.')
