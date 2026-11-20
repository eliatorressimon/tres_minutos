"""Paso 8. Distancias andando por la calle entre cada sección y los desfibriladores cercanos.

Hasta aquí medimos en línea recta, pero nadie atraviesa edificios, vías de tren ni autopistas.
Para cada pareja sección–aparato que está a menos de MAX_CALLE_M en línea recta (andando nunca
puede ser menos), pedimos la distancia a pie por la red de calles de OpenStreetMap al servidor
OSRM de routing.openstreetmap.de. A esa distancia le sumamos lo que hay desde cada punto hasta la
calle más cercana, que OSRM no cuenta.

Agrupamos secciones vecinas en lotes de como mucho 100 puntos y esperamos un segundo entre
peticiones para no cargar el servidor (son unas 90 peticiones).
Salida: datos/elaborados/distancias_calle.csv
"""
import time
import numpy as np
import pandas as pd
import requests
from scipy.spatial import cKDTree
from pyproj import Transformer
from config import ELABORADOS, CRS_METROS

MAX_CALLE_M = 300
MAX_PUNTOS = 100
OSRM = 'https://routing.openstreetmap.de/routed-foot/table/v1/driving/'


def cargar():
    sec = pd.read_csv(ELABORADOS / 'secciones.csv', dtype={'cod_ine_seccion': str, 'cod_ine_muni': str})
    dea = pd.read_csv(ELABORADOS / 'desfibriladores.csv', dtype=str)
    dea['fila_dea'] = np.arange(len(dea))   # fila en desfibriladores.csv (hay un código repetido)
    # solo los fijos que alguna vez constan como abiertos
    dea = dea[dea['fijo'].eq('True') & dea['estado_horario'].isin(['24h', 'horario'])].reset_index(drop=True)
    a_metros = Transformer.from_crs(4326, CRS_METROS, always_xy=True)
    dea['x'], dea['y'] = a_metros.transform(dea['lon'].astype(float).values, dea['lat'].astype(float).values)
    return sec, dea


def lotes(sec, dea):
    """Parejas a menos de MAX_CALLE_M en línea recta, agrupadas en lotes de secciones vecinas."""
    cerca = cKDTree(dea[['x', 'y']].values).query_ball_point(sec[['x', 'y']].values, MAX_CALLE_M)
    con_algo = [i for i in range(len(sec)) if cerca[i]]
    # orden espacial: franjas de 1 km de norte a sur, de oeste a este dentro de cada franja
    con_algo.sort(key=lambda i: (int(sec.at[i, 'y'] // 1000), sec.at[i, 'x']))
    resultado, s_act, d_act = [], [], set()
    for i in con_algo:
        nuevos = d_act | set(cerca[i])
        if s_act and len(s_act) + 1 + len(nuevos) > MAX_PUNTOS:
            resultado.append((s_act, sorted(d_act)))
            s_act, nuevos = [], set(cerca[i])
        s_act.append(i)
        d_act = nuevos
    if s_act:
        resultado.append((s_act, sorted(d_act)))
    return resultado, cerca


def pedir(sec, dea, s_idx, d_idx):
    puntos = [(sec.at[i, 'lon'], sec.at[i, 'lat']) for i in s_idx] + \
             [(float(dea.at[j, 'lon']), float(dea.at[j, 'lat'])) for j in d_idx]
    url = OSRM + ';'.join(f'{lon:.6f},{lat:.6f}' for lon, lat in puntos)
    n = len(s_idx)
    params = {'sources': ';'.join(map(str, range(n))),
              'destinations': ';'.join(map(str, range(n, len(puntos)))),
              'annotations': 'distance'}
    r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    j = r.json()
    hasta_calle_s = [w['distance'] for w in j['sources']]
    hasta_calle_d = [w['distance'] for w in j['destinations']]
    return j['distances'], hasta_calle_s, hasta_calle_d


if __name__ == '__main__':
    sec, dea = cargar()
    grupos, cerca = lotes(sec, dea)
    print(len(grupos), 'peticiones')
    filas = []
    for k, (s_idx, d_idx) in enumerate(grupos):
        dist, cs, cd = pedir(sec, dea, s_idx, d_idx)
        for a, i in enumerate(s_idx):
            for b, j in enumerate(d_idx):
                if j not in cerca[i] or dist[a][b] is None:
                    continue
                m = dist[a][b] + cs[a] + cd[b]
                if m <= MAX_CALLE_M:
                    recta = float(np.hypot(sec.at[i, 'x'] - dea.at[j, 'x'], sec.at[i, 'y'] - dea.at[j, 'y']))
                    filas.append({'cod_ine_seccion': sec.at[i, 'cod_ine_seccion'], 'fila_dea': int(dea.at[j, 'fila_dea']),
                                  'codigo_dea': dea.at[j, 'codigo_dea'],
                                  'metros_linea_recta': round(recta), 'metros_andando': round(m)})
        if k % 20 == 0:
            print(k, '/', len(grupos))
        time.sleep(1)
    res = pd.DataFrame(filas)
    res.to_csv(ELABORADOS / 'distancias_calle.csv', index=False)
    print(len(res), 'parejas a menos de', MAX_CALLE_M, 'm andando')
