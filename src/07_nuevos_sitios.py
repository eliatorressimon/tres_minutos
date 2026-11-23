"""Paso 7. Dónde poner los próximos aparatos de 24 horas, si pudiéramos elegir cualquier sitio.

Problema de máxima cobertura resuelto de forma voraz: en cada paso elegimos el centro de las viviendas de una sección que,
con un aparato 24 h, añade más vecinos cubiertos el domingo a las 3:00, contando dos veces a los mayores de 65.
Un punto de población queda cubierto si está a RADIO_M metros o menos andando por la calle (paso 5).
(La versión voraz garantiza al menos un 63 % del óptimo; para diez aparatos es más que suficiente.)
Salida: datos/elaborados/nuevos_sitios.csv
"""
import numpy as np
import pandas as pd
from config import ELABORADOS, NUEVOS_APARATOS
from candidatos import secciones_a_pie, centros_secciones

sec = pd.read_csv(ELABORADOS / 'puntos.csv', dtype={'punto': str, 'cod_ine_seccion': str, 'cod_ine_muni': str})
cubiertas = np.load(ELABORADOS / 'cubiertas_andando.npy')[147].copy()   # domingo 3:00, andando
p65, pob = sec['mayores_65'].fillna(0).values, sec['poblacion'].fillna(0).values
peso = pob + p65   # los mayores de 65 cuentan doble
a_pie = secciones_a_pie('Sitio ideal', sec)
centros = centros_secciones(sec)
candidatos = [a_pie.get(c, []) for c in centros.index]

elegidos = []
for k in range(NUEVOS_APARATOS):
    ganancia = np.array([peso[[i for i in c if not cubiertas[i]]].sum() for c in candidatos])
    mejor = int(ganancia.argmax())
    nuevas = [i for i in candidatos[mejor] if not cubiertas[i]]
    cubiertas[nuevas] = True
    elegidos.append({'orden': k + 1, 'municipio': centros['municipio'].iloc[mejor],
                     'lon': round(centros['lon'].iloc[mejor], 5), 'lat': round(centros['lat'].iloc[mejor], 5),
                     'vecinos_nuevos': round(pob[nuevas].sum()), 'mayores_65_nuevos': round(p65[nuevas].sum())})
res = pd.DataFrame(elegidos)
res.to_csv(ELABORADOS / 'nuevos_sitios.csv', index=False)
print(res)
print('Total vecinos nuevos cubiertos de madrugada:', res['vecinos_nuevos'].sum())
