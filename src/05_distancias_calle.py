"""Paso 5. Distancias andando por la calle.

En línea recta se atraviesan edificios, vías de tren y autopistas. Aquí pedimos la distancia a pie
por la red de calles y caminos de OpenStreetMap al servidor OSRM de routing.openstreetmap.de
(servicio 'table', perfil a pie). A esa distancia le sumamos lo que hay desde cada punto hasta la
calle más cercana, que OSRM no cuenta. Solo preguntamos por parejas que están cerca en línea recta,
porque andando nunca puede salir menos.

Dos tablas:
  1. Cada sección con los desfibriladores (fijos y con horario conocido) a menos de 300 m.
  2. Cada sitio candidato para un aparato nuevo con las secciones a menos de 200 m: el centro de
     cada sección (sitio ideal), las farmacias y las gasolineras de 24 horas. También los centros de
     salud y hospitales, que tienen aparato aunque no estén en el registro.

Agrupamos puntos vecinos en lotes de como mucho 100 y esperamos un segundo entre peticiones para no
cargar el servidor (son unas 210 peticiones en total).
Salidas: datos/elaborados/distancias_calle.csv y datos/elaborados/distancias_candidatos.csv
"""
import time
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd
import requests
from scipy.spatial import cKDTree
from pyproj import Transformer
from config import ELABORADOS, CRS_METROS, RADIO_M, RAIZ
from candidatos import farmacias, gasolineras_24h, centros_sanitarios, centros_secciones

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
        if len(cerca[i]) >= MAX_PUNTOS:   # un punto con muchísimos destinos va solo, en varias peticiones
            if o_act:
                resultado.append((o_act, sorted(d_act)))
                o_act, d_act = [], set()
            todos = sorted(cerca[i])
            for k in range(0, len(todos), MAX_PUNTOS - 1):
                resultado.append(([i], todos[k:k + MAX_PUNTOS - 1]))
            continue
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
    # varios aparatos pueden estar en el mismo sitio exacto (hay edificios con decenas): se pregunta una vez por cada sitio
    clave = list(zip(destino['lon'].astype(float).round(6), destino['lat'].astype(float).round(6)))
    unicos = destino.loc[~pd.Series(clave).duplicated().values].reset_index()
    iguales = {}
    for j, c in enumerate(clave):
        iguales.setdefault(c, []).append(j)
    parejas = _andando(origen, unicos, max_m)
    return [(i, jj, r, m) for i, ju, r, m in parejas
            for jj in iguales[(round(float(unicos.at[ju, 'lon']), 6), round(float(unicos.at[ju, 'lat']), 6))]]


CACHE_F = RAIZ / 'datos' / 'respaldo' / 'rutas_a_pie.csv.gz'
CACHE = {}   # (lon, lat de origen, lon, lat de destino) -> metros andando (inf si no hay ruta)


def clave(lo1, la1, lo2, la2):
    return (round(float(lo1), 5), round(float(la1), 5), round(float(lo2), 5), round(float(la2), 5))


def cargar_cache():
    """Las distancias ya preguntadas otras semanas: solo se pregunta por las parejas nuevas."""
    if CACHE_F.exists():
        c = pd.read_csv(CACHE_F)
        CACHE.update({clave(*k): m for *k, m in c.itertuples(index=False)})
        print(len(CACHE), 'distancias guardadas de otras veces')


def guardar_cache():
    pd.DataFrame([(*k, round(m, 1)) for k, m in CACHE.items()], columns=['lon1', 'lat1', 'lon2', 'lat2', 'metros']) \
        .to_csv(CACHE_F, index=False, compression='gzip')


def pedir(url, params, intentos=4):
    for k in range(intentos):
        try:
            r = requests.get(url, params=params, timeout=90)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            if k == intentos - 1:
                raise
            print('   reintento', k + 1, type(e).__name__)
            time.sleep(15 * (k + 1))


def _andando(origen, destino, max_m):
    cerca = cKDTree(destino[['x', 'y']].values).query_ball_point(origen[['x', 'y']].values, max_m)
    ol, oa, dl, da = (origen['lon'].astype(float).values, origen['lat'].astype(float).values,
                      destino['lon'].astype(float).values, destino['lat'].astype(float).values)
    falta = [[j for j in cerca[i] if clave(ol[i], oa[i], dl[j], da[j]) not in CACHE] for i in range(len(origen))]
    grupos = lotes(falta, origen)
    print(len(grupos), 'peticiones')
    def una(grupo):
        o_idx, d_idx = grupo
        puntos = [(ol[i], oa[i]) for i in o_idx] + [(dl[j], da[j]) for j in d_idx]
        n = len(o_idx)
        r = pedir(OSRM + ';'.join(f'{lo:.6f},{la:.6f}' for lo, la in puntos),
                  {'sources': ';'.join(map(str, range(n))), 'destinations': ';'.join(map(str, range(n, len(puntos)))),
                   'annotations': 'distance'})
        time.sleep(1)
        return r

    # tres peticiones a la vez: el servidor tarda en responder, pero no lo saturamos
    with ThreadPoolExecutor(max_workers=3) as hilos:
        for k, ((o_idx, d_idx), j) in enumerate(zip(grupos, hilos.map(una, grupos))):
            for a, i in enumerate(o_idx):
                dentro = set(cerca[i])
                for b, jj in enumerate(d_idx):
                    if jj not in dentro:
                        continue
                    d = j['distances'][a][b]
                    CACHE[clave(ol[i], oa[i], dl[jj], da[jj])] = (float('inf') if d is None else
                                                                  d + j['sources'][a]['distance'] + j['destinations'][b]['distance'])
            if k % 20 == 0:
                print(k, '/', len(grupos), flush=True)
            if k % 200 == 199:
                guardar_cache()
    guardar_cache()
    parejas = []
    for i in range(len(origen)):
        for jj in cerca[i]:
            m = CACHE[clave(ol[i], oa[i], dl[jj], da[jj])]
            if m <= max_m:
                recta = float(np.hypot(origen.at[i, 'x'] - destino.at[jj, 'x'], origen.at[i, 'y'] - destino.at[jj, 'y']))
                parejas.append((i, jj, round(recta), round(m)))
    return parejas


if __name__ == '__main__':
    sec = pd.read_csv(ELABORADOS / 'puntos.csv', dtype={'punto': str, 'cod_ine_seccion': str, 'cod_ine_muni': str})
    dea = pd.read_csv(ELABORADOS / 'desfibriladores.csv', dtype=str)
    dea['fila_dea'] = np.arange(len(dea))   # fila en desfibriladores.csv (hay un código repetido)
    dea = con_metros(dea[dea['fijo'].eq('True') & dea['estado_horario'].isin(['24h', 'horario'])])
    cargar_cache()

    # 1. secciones y desfibriladores
    p = andando(sec, dea, MAX_DEA_M)
    pd.DataFrame([{'punto': sec.at[i, 'punto'], 'fila_dea': int(dea.at[j, 'fila_dea']),
                   'codigo_dea': dea.at[j, 'codigo_dea'], 'metros_linea_recta': r, 'metros_andando': m}
                  for i, j, r, m in p]).to_csv(ELABORADOS / 'distancias_calle.csv', index=False)
    print(len(p), 'parejas sección y aparato a', MAX_DEA_M, 'm o menos andando')

    # 2. sitios candidatos y secciones
    # sitio ideal: el centro de las viviendas de cada sección (con un candidato por cada grupo de casas serían
    # diez veces más preguntas al servidor de rutas para casi el mismo resultado)
    centros = centros_secciones(sec)
    ideal = pd.DataFrame({'id': centros.index, 'tipo': 'Sitio ideal', 'lon': centros['lon'].values, 'lat': centros['lat'].values})
    cand = con_metros(pd.concat([ideal, farmacias()[['id', 'tipo', 'lon', 'lat']], gasolineras_24h()[['id', 'tipo', 'lon', 'lat']],
                                centros_sanitarios()[['id', 'tipo', 'lon', 'lat']]]))
    p = andando(cand, sec, RADIO_M)
    pd.DataFrame([{'tipo': cand.at[i, 'tipo'], 'id': cand.at[i, 'id'], 'punto': sec.at[j, 'punto'],
                   'metros_andando': m} for i, j, r, m in p]).to_csv(ELABORADOS / 'distancias_candidatos.csv', index=False)
    print(len(p), 'parejas sitio y sección a', RADIO_M, 'm o menos andando')
