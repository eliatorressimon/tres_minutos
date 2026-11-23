"""Paso 4. Cobertura hora a hora durante una semana.

Una sección está cubierta a una hora si tiene un desfibrilador abierto a menos de RADIO_M metros
(en línea recta) de su centro. Solo cuenta como abierto lo que el horario dice que está abierto.
Salidas: cobertura_semana.csv (168 filas), cobertura_municipios.csv y cubiertas_por_hora.npy
"""
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from pyproj import Transformer
from config import ELABORADOS, RADIO_M, CRS_METROS

DIAS = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']

sec = pd.read_csv(ELABORADOS / 'puntos.csv', dtype={'punto': str, 'cod_ine_seccion': str, 'cod_ine_muni': str})
dea = pd.read_csv(ELABORADOS / 'desfibriladores.csv', dtype=str)
tablas = np.load(ELABORADOS / 'horarios_semana.npy')

fijos = dea['fijo'].eq('True').values
dea, tablas = dea[fijos].reset_index(drop=True), tablas[fijos]
a_metros = Transformer.from_crs(4326, CRS_METROS, always_xy=True)
dx, dy = a_metros.transform(dea['lon'].astype(float).values, dea['lat'].astype(float).values)

# para cada aparato, qué secciones tiene a menos de RADIO_M
arbol = cKDTree(sec[['x', 'y']].values)
cerca = arbol.query_ball_point(np.c_[dx, dy], RADIO_M)

pob, may = sec['poblacion'].values, sec['mayores_65'].values
fuera = sec['cod_ine_muni'].ne('28079').values
abiertas = tablas.reshape(len(dea), 168)    # columna = día*24 + hora
cubiertas = np.zeros((168, len(sec)), bool)
filas = []
for t in range(168):
    for j in np.flatnonzero(abiertas[:, t]):
        cubiertas[t, cerca[j]] = True
    c = cubiertas[t]
    filas.append({'dia': DIAS[t // 24], 'hora': t % 24, 'aparatos_abiertos': int(abiertas[:, t].sum()),
                  'pct_poblacion': round(100 * pob[c].sum() / pob.sum(), 1),
                  'pct_poblacion_fuera_capital': round(100 * pob[c & fuera].sum() / pob[fuera].sum(), 1),
                  'pct_mayores_65': round(100 * may[c].sum() / may.sum(), 1)})
semana = pd.DataFrame(filas)
semana.to_csv(ELABORADOS / 'cobertura_semana.csv', index=False)
np.save(ELABORADOS / 'cubiertas_por_hora.npy', cubiertas)
print(semana.loc[[35, 147]])

# cota superior: si todos los de horario desconocido estuvieran abiertos el domingo a las 3:00
desconocido = dea['estado_horario'].eq('desconocido').values
c = cubiertas[147].copy()
for j in np.flatnonzero(desconocido):
    c[cerca[j]] = True
print('Domingo 3:00 si los de horario desconocido estuvieran abiertos:', round(100 * pob[c].sum() / pob.sum(), 1), '%')

# resumen por municipio: martes 11:00 (t=35) y domingo 3:00 (t=147)
muni = pd.read_csv(ELABORADOS / 'municipios.csv', dtype={'cod_ine_muni': str})
con_dea = set('28' + dea['municipio_codigo'].dropna())
res = []
for m, g in sec.groupby('cod_ine_muni'):
    p = g['poblacion'].sum()
    res.append({'cod_ine_muni': m, 'municipio': g['municipio'].iloc[0], 'poblacion': round(p),
                'pct_martes_11h': round(100 * g['poblacion'][cubiertas[35, g.index]].sum() / p, 1),
                'pct_domingo_3h': round(100 * g['poblacion'][cubiertas[147, g.index]].sum() / p, 1),
                'tiene_desfibrilador_fijo': m in con_dea})
res = pd.DataFrame(res)
res.to_csv(ELABORADOS / 'cobertura_municipios.csv', index=False)
print('Municipios sin ningún desfibrilador fijo:', (~res['tiene_desfibrilador_fijo']).sum())
