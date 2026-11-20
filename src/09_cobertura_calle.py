"""Paso 9. Cobertura con 100, 200 y 300 metros, en línea recta y andando por la calle.

Repite el cálculo del paso 4 para seis variantes: tres distancias y dos formas de medir. Andando,
una sección está cubierta si algún aparato abierto queda a esa distancia o menos por la red de calles
(paso 8). Así se ve cuánto cambia el resultado según lo exigentes que seamos.
Salidas: datos/elaborados/cobertura_variantes.csv y web/variantes.json (la web la carga al cambiar el selector)
"""
import base64
import json
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from pyproj import Transformer
from config import ELABORADOS, WEB, CRS_METROS

RADIOS = [100, 200, 300]
DIAS = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']

sec = pd.read_csv(ELABORADOS / 'secciones.csv', dtype={'cod_ine_seccion': str, 'cod_ine_muni': str})
dea = pd.read_csv(ELABORADOS / 'desfibriladores.csv', dtype=str)
tablas = np.load(ELABORADOS / 'horarios_semana.npy').reshape(len(dea), 168)
calle = pd.read_csv(ELABORADOS / 'distancias_calle.csv', dtype={'cod_ine_seccion': str})

a_metros = Transformer.from_crs(4326, CRS_METROS, always_xy=True)
fijos = np.flatnonzero(dea['fijo'].eq('True').values)
dx, dy = a_metros.transform(dea['lon'].astype(float).values[fijos], dea['lat'].astype(float).values[fijos])
arbol = cKDTree(sec[['x', 'y']].values)
pos_sec = {c: i for i, c in enumerate(sec['cod_ine_seccion'])}

pob, may = sec['poblacion'].values, sec['mayores_65'].values
fuera = sec['cod_ine_muni'].ne('28079').values


def cerca_recta(r):
    """Para cada aparato (fila de desfibriladores.csv), las secciones a menos de r metros en línea recta."""
    return dict(zip(fijos, arbol.query_ball_point(np.c_[dx, dy], r)))


def cerca_andando(r):
    """Lo mismo, pero medido andando por la calle."""
    c = calle[calle['metros_andando'] <= r]
    res = {}
    for fila, s in zip(c['fila_dea'], c['cod_ine_seccion']):
        res.setdefault(fila, []).append(pos_sec[s])
    return res


filas, web = [], {}
for medida, funcion in [('recta', cerca_recta), ('andando', cerca_andando)]:
    for r in RADIOS:
        cerca = funcion(r)
        cubiertas = np.zeros((168, len(sec)), bool)
        for t in range(168):
            for j in np.flatnonzero(tablas[:, t]):
                cubiertas[t, cerca.get(j, [])] = True
            c = cubiertas[t]
            fila = {'medida': medida, 'radio_m': r, 'dia': DIAS[t // 24], 'hora': t % 24,
                    'pct_poblacion': round(100 * pob[c].sum() / pob.sum(), 1),
                    'pct_poblacion_fuera_capital': round(100 * pob[c & fuera].sum() / pob[fuera].sum(), 1),
                    'pct_mayores_65': round(100 * may[c].sum() / may.sum(), 1)}
            filas.append(fila)
        if (medida, r) != ('recta', 200):   # esa ya va en datos.json
            web[f'{medida}-{r}'] = {'cov': [base64.b64encode(np.packbits(c).tobytes()).decode() for c in cubiertas]}
        print(f'{medida:8} {r} m   martes 11:00 {filas[-168 + 35]["pct_poblacion"]:5.1f} %   domingo 3:00 {filas[-168 + 147]["pct_poblacion"]:5.1f} %')

pd.DataFrame(filas).to_csv(ELABORADOS / 'cobertura_variantes.csv', index=False)
(WEB / 'variantes.json').write_text(json.dumps(web, separators=(',', ':')), encoding='utf-8')
