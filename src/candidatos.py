"""Locales reales donde se podría poner un aparato: farmacias y gasolineras abiertas las 24 horas.

Lo usan los pasos 5 (distancias andando), 7 (sitios ideales) y 8 (los diez mejores sitios reales).
Cada local tiene un identificador fijo ('id') para poder cruzar los dos pasos.
"""
import json
import pandas as pd
from pyproj import Transformer
from config import ORIGINALES, ELABORADOS, CRS_METROS


def gasolineras_24h():
    """Gasolineras de la Comunidad con horario 'L-D: 24H' o 'L-D: 00:00-23:59' en la API del Ministerio."""
    g = pd.DataFrame(json.loads((ORIGINALES / 'gasolineras.json').read_text(encoding='utf-8'))['ListaEESSPrecio'])
    g = g[g['Horario'].str.fullmatch(r'L-D: (24H|00:00-23:59)')].copy()
    g['lon'] = g['Longitud (WGS84)'].str.replace(',', '.').astype(float)
    g['lat'] = g['Latitud'].str.replace(',', '.').astype(float)
    return pd.DataFrame({'id': [f'{lo:.6f},{la:.6f}' for lo, la in zip(g['lon'], g['lat'])],
                         'tipo': 'Gasolinera 24 h', 'nombre': g['Rótulo'].str.title(), 'direccion': g['Dirección'].str.title(),
                         'municipio': g['Municipio'], 'lon': g['lon'], 'lat': g['lat']}).reset_index(drop=True)


def farmacias():
    """Oficinas de farmacia del registro de la Comunidad. No guardamos el nombre de los titulares."""
    f = pd.read_csv(ORIGINALES / 'oficinas_farmacia.csv', sep=';', dtype=str, encoding='utf-8')
    f['x'] = f['LOCALIZACION_COORDENADA_X'].str.replace(',', '.').astype(float)
    f['y'] = f['LOCALIZACION_COORDENADA_Y'].str.replace(',', '.').astype(float)
    f = f.dropna(subset=['x', 'y'])
    # vienen en metros (ETRS89 / UTM 30N): las pasamos a grados
    f['lon'], f['lat'] = Transformer.from_crs(CRS_METROS, 4326, always_xy=True).transform(f['x'].values, f['y'].values)
    direccion = (f['DIRECCION_VIAL_TIPO'].fillna('').str.title() + ' ' + f['DIRECCION_VIAL_NOMBRE'].fillna('') + ' ' +
                 f['DIRECCION_VIAL_NRO'].fillna('')).str.strip()
    return pd.DataFrame({'id': f['FARMACIA_NRO_SOE'], 'tipo': 'Farmacia', 'nombre': 'Farmacia', 'direccion': direccion,
                         'municipio': f['MUNICIPIO_NOMBRE'], 'lon': f['lon'], 'lat': f['lat']}).reset_index(drop=True)


def secciones_a_pie(tipo, sec):
    """Para cada sitio de un tipo, las secciones (posición en secciones.csv) a RADIO_M o menos andando (paso 5)."""
    d = pd.read_csv(ELABORADOS / 'distancias_candidatos.csv', dtype={'id': str, 'cod_ine_seccion': str})
    pos = {c: i for i, c in enumerate(sec['cod_ine_seccion'])}
    res = {}
    for i, s in zip(d.loc[d['tipo'] == tipo, 'id'], d.loc[d['tipo'] == tipo, 'cod_ine_seccion']):
        res.setdefault(i, []).append(pos[s])
    return res
