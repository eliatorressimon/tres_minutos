"""Paso 5. Dónde poner los próximos aparatos de 24 horas.

Problema de máxima cobertura resuelto de forma voraz: en cada paso elegimos el centro de sección que,
con un aparato 24 h, añade más mayores de 65 años cubiertos el domingo a las 3:00.
(La versión voraz garantiza al menos un 63 % del óptimo; para diez aparatos es más que suficiente.)
Salida: datos/elaborados/nuevos_sitios.csv
"""
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from config import ELABORADOS, RADIO_M, NUEVOS_APARATOS

sec = pd.read_csv(ELABORADOS / 'secciones.csv', dtype={'cod_ine_seccion': str, 'cod_ine_muni': str})
cubiertas = np.load(ELABORADOS / 'cubiertas_por_hora.npy')[147].copy()   # domingo 3:00
peso, pob = sec['mayores_65'].fillna(0).values, sec['poblacion'].fillna(0).values
candidatos = cKDTree(sec[['x', 'y']].values).query_ball_point(sec[['x', 'y']].values, RADIO_M)

elegidos = []
for k in range(NUEVOS_APARATOS):
    ganancia = np.array([peso[[i for i in c if not cubiertas[i]]].sum() for c in candidatos])
    mejor = int(ganancia.argmax())
    nuevas = [i for i in candidatos[mejor] if not cubiertas[i]]
    cubiertas[nuevas] = True
    elegidos.append({'orden': k + 1, 'municipio': sec.at[mejor, 'municipio'],
                     'lon': sec.at[mejor, 'lon'], 'lat': sec.at[mejor, 'lat'],
                     'vecinos_nuevos': round(pob[nuevas].sum()), 'mayores_65_nuevos': round(peso[nuevas].sum())})
res = pd.DataFrame(elegidos)
res.to_csv(ELABORADOS / 'nuevos_sitios.csv', index=False)
print(res)
print('Total vecinos nuevos cubiertos de madrugada:', res['vecinos_nuevos'].sum())
