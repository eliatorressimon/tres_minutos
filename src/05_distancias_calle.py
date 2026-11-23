"""Paso 5. Distancias andando por la calle.

En línea recta se atraviesan edificios, vías de tren y autopistas. Aquí pedimos la distancia a pie
por la red de calles y caminos de OpenStreetMap al servidor OSRM de routing.openstreetmap.de
(servicio 'table', perfil a pie). A esa distancia le sumamos lo que hay desde cada punto hasta la
calle más cercana, que OSRM no cuenta. Solo preguntamos por parejas que están cerca en línea recta,
porque andando nunca puede salir menos.

Dos tablas:
  1. Cada sección con los desfibriladores (fijos y con horario conocido) a menos de 300 m.
  2. Cada sitio candidato para un aparato nuevo con las secciones a menos de 200 m: el centro de
     cada sección (sitio ideal), las farmacias y las gasolineras de 24 horas.

Agrupamos puntos vecinos en lotes de como mucho 100 y esperamos un segundo entre peticiones para no
cargar el servidor (son unas 210 peticiones en total).
Salidas: datos/elaborados/distancias_calle.csv y datos/elaborados/distancias_candidatos.csv
"""
import time
import numpy as np
import pandas as pd
import requests
from scipy.spatial import cKDTree
from pyproj import Transformer
from config import ELABORADOS, CRS_METROS, RADIO_M
from candidatos import farmacias, gasolineras_24h

MAX_DEA_M = 300      # hasta dónde miramos para la cobertura (el selector de la web llega a 300 m)
MAX_PUNTOS = 100
OSRM = 'https://routing.openstreetmap.de/routed-foot/table/v1/driving/'
a_metros = Transformer.from_crs(4326, CRS_METROS, always_xy=True)


def con_metros(df):
    df = df.reset_index(drop=True)
    df['x'], df['y'] = a_metros.transform(df['lon'].astype(float).values, df['lat'].astype(float).values)
    return df


def lotes(cerca, origen):
    """Agrupa orígenes vecinos (y sus destinos) en lotes de como mucho MAX_PUNTOS puntos."""
    con_algo = [i for i in range(len(origen)) if cerca[i]]
    # orden espacial: franjas de 1 km de norte a sur, de oeste a este dentro de cada franja
    con_algo.sort(key=lambda i: (int(origen.at[i, 'y'] // 1000), origen.at[i, 'x']))
    resultado, o_act, d_act = [], [], set()
    for i in con_algo:
        nuevos = d_act | set(cerca[i])
        if o_act and len(o_act) + 1 + len(nuevos) > MAX_PUNTOS:
            resultado.append((o_act, sorted(d_act)))
            o_act, nuevos = [], set(cerca[i])
        o_act.append(i)
        d_act = nuevos
    if o_act:
        resultado.append((o_act, sorted(d_act)))
    return resultado


def andando(origen, destino, max_m):
    """Parejas (i de origen, j de destino, metros en línea recta, metros andando) con andando <= max_m."""
    cerca = cKDTree(destino[['x', 'y']].values).query_ball_point(origen[['x', 'y']].values, max_m)
    grupos = lotes(cerca, origen)
    print(len(grupos), 'peticiones')
    parejas = []
    for k, (o_idx, d_idx) in enumerate(grupos):
        puntos = [(origen.at[i, 'lon'], origen.at[i, 'lat']) for i in o_idx] + [(destino.at[j, 'lon'], destino.at[j, 'lat']) for j in d_idx]
        n = len(o_idx)
        r = requests.get(OSRM + ';'.join(f'{float(lo):.6f},{float(la):.6f}' for lo, la in puntos),
                         params={'sources': ';'.join(map(str, range(n))), 'destinations': ';'.join(map(str, range(n, len(puntos)))),
                                 'annotations': 'distance'}, timeout=60)
        r.raise_for_status()
        j = r.json()
        for a, i in enumerate(o_idx):
            for b, jj in enumerate(d_idx):
                d = j['distances'][a][b]
                if jj not in cerca[i] or d is None:
                    continue
                m = d + j['sources'][a]['distance'] + j['destinations'][b]['distance']
                if m <= max_m:
                    recta = float(np.hypot(origen.at[i, 'x'] - destino.at[jj, 'x'], origen.at[i, 'y'] - destino.at[jj, 'y']))
                    parejas.append((i, jj, round(recta), round(m)))
        if k % 20 == 0:
            print(k, '/', len(grupos))
        time.sleep(1)
    return parejas


if __name__ == '__main__':
    sec = pd.read_csv(ELABORADOS / 'secciones.csv', dtype={'cod_ine_seccion': str, 'cod_ine_muni': str})
    dea = pd.read_csv(ELABORADOS / 'desfibriladores.csv', dtype=str)
    dea['fila_dea'] = np.arange(len(dea))   # fila en desfibriladores.csv (hay un código repetido)
    dea = con_metros(dea[dea['fijo'].eq('True') & dea['estado_horario'].isin(['24h', 'horario'])])

    # 1. secciones y desfibriladores
    p = andando(sec, dea, MAX_DEA_M)
    pd.DataFrame([{'cod_ine_seccion': sec.at[i, 'cod_ine_seccion'], 'fila_dea': int(dea.at[j, 'fila_dea']),
                   'codigo_dea': dea.at[j, 'codigo_dea'], 'metros_linea_recta': r, 'metros_andando': m}
                  for i, j, r, m in p]).to_csv(ELABORADOS / 'distancias_calle.csv', index=False)
    print(len(p), 'parejas sección y aparato a', MAX_DEA_M, 'm o menos andando')

    # 2. sitios candidatos y secciones
    ideal = pd.DataFrame({'id': sec['cod_ine_seccion'], 'tipo': 'Sitio ideal', 'lon': sec['lon'], 'lat': sec['lat']})
    cand = con_metros(pd.concat([ideal, farmacias()[['id', 'tipo', 'lon', 'lat']], gasolineras_24h()[['id', 'tipo', 'lon', 'lat']]]))
    p = andando(cand, sec, RADIO_M)
    pd.DataFrame([{'tipo': cand.at[i, 'tipo'], 'id': cand.at[i, 'id'], 'cod_ine_seccion': sec.at[j, 'cod_ine_seccion'],
                   'metros_andando': m} for i, j, r, m in p]).to_csv(ELABORADOS / 'distancias_candidatos.csv', index=False)
    print(len(p), 'parejas sitio y sección a', RADIO_M, 'm o menos andando')
