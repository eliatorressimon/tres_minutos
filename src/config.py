"""Rutas y parámetros comunes a todos los pasos."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ORIGINALES = RAIZ / 'datos' / 'originales'
ELABORADOS = RAIZ / 'datos' / 'elaborados'
WEB = RAIZ / 'web'

RADIO_M = 200        # distancia máxima, en metros y en línea recta, para considerar cubierta una sección
NUEVOS_APARATOS = 10 # cuántos sitios nuevos proponemos
CRS_METROS = 25830   # ETRS89 / UTM 30N, el sistema en metros que usa la Comunidad de Madrid

URLS = {
    'desfibriladores.csv': 'https://datos.comunidad.madrid/dataset/d2478503-a4ae-4753-9540-9200071803c4/resource/94756e35-3059-451d-81a6-3427d2551de4/download/desfibriladores_externos_fuera_ambito_sanitario.csv',
    'secciones_censales.zip': 'https://datos.comunidad.madrid/dataset/2c176a23-a6cd-4c18-b5df-b32a3a3a1219/resource/b53b766c-e013-444c-b3b0-0992c4a0dbfc/download/558.zip',
    'ine_31105.csv': 'https://www.ine.es/jaxiT3/files/t/es/csv_bdsc/31105.csv',
    'defunciones_causa.csv': None,  # se busca por la API del portal (ver 01_descargar.py)
}
