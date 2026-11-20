"""Paso 1. Descarga los datos originales en datos/originales/.

Fuentes:
  - Registro de desfibriladores externos fuera del ámbito sanitario (Portal de Datos Abiertos, Comunidad de Madrid)
  - Secciones censales, shapefile (Portal de Datos Abiertos, Comunidad de Madrid)
  - Indicadores demográficos por sección censal, tabla 31105 del Atlas de distribución de renta (INE)
  - Defunciones por causa de muerte y sexo, municipios (Portal de Datos Abiertos, Comunidad de Madrid)
"""
import requests
from config import ORIGINALES, URLS

CKAN = 'https://datos.comunidad.madrid/api/3/action/package_show?id='


def bajar(url, destino):
    print('Descargando', destino.name)
    r = requests.get(url, timeout=120)
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
        bajar(url, ORIGINALES / nombre)
