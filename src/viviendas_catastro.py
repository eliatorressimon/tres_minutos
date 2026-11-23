"""Viviendas de cada edificio, del Catastro (servicio INSPIRE de edificios, un fichero por municipio).

De cada edificio guardamos el centro de su contorno y el número de viviendas. El Catastro solo
cambia de verdad un par de veces al año, así que la descarga (unos 180 ficheros, varios GB) se hace
una vez y se guarda en datos/respaldo/viviendas_catastro.csv.gz. Para volver a bajarla, se borra ese fichero.
Salida: datos/respaldo/viviendas_catastro.csv.gz (columnas x, y en metros EPSG:25830, viviendas)
"""
import io
import re
import time
import zipfile
import pandas as pd
import requests
from config import RAIZ

ATOM = 'https://www.catastro.hacienda.gob.es/INSPIRE/buildings/28/ES.SDGC.BU.atom_28.xml'
SALIDA = RAIZ / 'datos' / 'respaldo' / 'viviendas_catastro.csv.gz'
num = re.compile(r'>\s*([\d.]+)\s+([\d.]+)\s*<')


def edificios(gml):
    """Recorre building.gml línea a línea: (x, y, viviendas) de cada edificio con alguna vivienda."""
    lo = hi = None
    viv = 0
    for linea in gml:
        if b'lowerCorner' in linea and lo is None:
            lo = num.search(linea.decode('latin1')).groups()
        elif b'upperCorner' in linea and hi is None:
            hi = num.search(linea.decode('latin1')).groups()
        elif b'numberOfDwellings>' in linea:
            m = re.search(rb'numberOfDwellings>(\d+)<', linea)
            viv = int(m.group(1)) if m else 0
        elif b'</bu-ext2d:Building>' in linea:
            if viv > 0 and lo and hi:
                yield ((float(lo[0]) + float(hi[0])) / 2, (float(lo[1]) + float(hi[1])) / 2, viv)
            lo = hi = None
            viv = 0


def bajar(url, intentos=4):
    for k in range(intentos):
        try:
            r = requests.get(url, timeout=600)
            r.raise_for_status()
            return r.content
        except requests.RequestException as e:
            print('   reintento', k + 1, type(e).__name__)
            time.sleep(10 * (k + 1))
    raise RuntimeError('No se ha podido bajar ' + url)


if __name__ == '__main__':
    if SALIDA.exists():
        print('Ya están las viviendas del Catastro en', SALIDA.name)
        raise SystemExit
    zips = sorted(set(re.findall(r'https[^"<]*\.zip', requests.get(ATOM, timeout=120).text)))
    print(len(zips), 'municipios en el Catastro')
    filas = []
    for k, url in enumerate(zips):
        datos = bajar(url)
        with zipfile.ZipFile(io.BytesIO(datos)) as z:
            nombre = next(n for n in z.namelist() if n.endswith('.building.gml'))
            with z.open(nombre) as gml:
                antes = len(filas)
                filas.extend(edificios(gml))
        print(f'{k + 1:3}/{len(zips)} {url.split("/")[-2]:40} {len(filas) - antes:7} edificios con viviendas')
    df = pd.DataFrame(filas, columns=['x', 'y', 'viviendas']).round({'x': 0, 'y': 0}).astype(int)
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(SALIDA, index=False, compression='gzip')
    print(len(df), 'edificios,', df['viviendas'].sum(), 'viviendas')
