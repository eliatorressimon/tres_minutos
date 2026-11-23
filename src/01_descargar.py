"""Paso 1. Descarga los datos originales en datos/originales/.

Fuentes:
  - Registro de desfibriladores externos fuera del ámbito sanitario (Portal de Datos Abiertos, Comunidad de Madrid)
  - Secciones censales, shapefile (Portal de Datos Abiertos, Comunidad de Madrid)
  - Indicadores demográficos por sección censal, tabla 31105 del Atlas de distribución de renta (INE)
  - Defunciones por causa de muerte y sexo, municipios (Portal de Datos Abiertos, Comunidad de Madrid)
  - Oficinas de farmacia (Portal de Datos Abiertos, Comunidad de Madrid)
  - Centros, servicios y establecimientos sanitarios (Portal de Datos Abiertos, Comunidad de Madrid)
  - Gasolineras con su horario (Ministerio para la Transición Ecológica, servicio REST de precios de carburantes)
"""
import shutil
import requests
from config import ORIGINALES, URLS, RAIZ

# El servicio del Ministerio a veces no responde fuera de España (por ejemplo, desde GitHub Actions).
# Las gasolineras de 24 horas cambian muy poco, así que si falla usamos la última copia buena.
RESPALDO = RAIZ / 'datos' / 'respaldo'
CON_RESPALDO = {'gasolineras.json'}

CKAN = 'https://datos.comunidad.madrid/api/3/action/package_show?id='


def bajar(url, destino):
    print('Descargando', destino.name)
    r = requests.get(url, timeout=120, headers={'Accept': 'application/json'})
    r.raise_for_status()
    destino.write_bytes(r.content)
    print('  ', round(len(r.content) / 1e6, 1), 'MB')


def url_csv_ckan(id_conjunto):
    """Pregunta a la API del portal por el enlace del CSV de un conjunto de datos."""
    recursos = requests.get(CKAN + id_conjunto, timeout=60).json()['result']['resources']
    return next(r['url'] for r in recursos if r['format'].lower() == 'csv')


if __name__ == '__main__':
    ORIGINALES.mkdir(parents=True, exist_ok=True)
    for nombre, url in URLS.items():
        if url is None:
            url = url_csv_ckan('defunciones_por_causa_y_sexo')
        if nombre not in CON_RESPALDO:
            bajar(url, ORIGINALES / nombre)
            continue
        try:
            bajar(url, ORIGINALES / nombre)
            RESPALDO.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ORIGINALES / nombre, RESPALDO / nombre)
        except requests.RequestException as e:
            print('  No se ha podido descargar', nombre, f'({type(e).__name__}); se usa la copia de datos/respaldo/')
            shutil.copyfile(RESPALDO / nombre, ORIGINALES / nombre)
