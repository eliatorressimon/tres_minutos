"""Paso 2. Limpia el registro de desfibriladores y traduce sus horarios.

Salida: datos/elaborados/desfibriladores.csv (una fila por aparato, con su estado y si está abierto
el martes a las 11:00 y el domingo a las 3:00) y datos/elaborados/horarios_semana.npy (tabla 7x24 de cada aparato).
"""
import numpy as np
import pandas as pd
from config import ORIGINALES, ELABORADOS
from horarios import parse

dea = pd.read_csv(ORIGINALES / 'desfibriladores.csv', sep=';', dtype=str, keep_default_na=False)
print('Aparatos en el registro:', len(dea))

# las coordenadas vienen con coma decimal
for col in ['direccion_longitud', 'direccion_latitud']:
    dea[col] = pd.to_numeric(dea[col].str.replace(',', '.'), errors='coerce')
dea = dea.rename(columns={'direccion_longitud': 'lon', 'direccion_latitud': 'lat'})

estados, tablas = [], []
for texto in dea['horario_acceso']:
    estado, tabla = parse(texto)
    estados.append(estado)
    if tabla is None:
        tabla = np.ones((7, 24), bool) if estado == '24h' else np.zeros((7, 24), bool)
    tablas.append(tabla)
dea['estado_horario'] = estados
tablas = np.array(tablas)

print(dea['estado_horario'].value_counts())

# solo tenemos certeza de que está abierto si es 24 h o si su horario lo dice
dea['abierto_martes_11h'] = tablas[:, 1, 11]
dea['abierto_domingo_3h'] = tablas[:, 6, 3]
dea['fijo'] = ~dea['estado_horario'].eq('movil') & dea['lon'].notna()

ELABORADOS.mkdir(parents=True, exist_ok=True)
cols = ['codigo_dea', 'tipo_establecimiento', 'tipo_titularidad', 'municipio_codigo', 'municipio_nombre',
        'lon', 'lat', 'horario_acceso', 'estado_horario', 'abierto_martes_11h', 'abierto_domingo_3h', 'fijo']
dea[cols].to_csv(ELABORADOS / 'desfibriladores.csv', index=False)
np.save(ELABORADOS / 'horarios_semana.npy', tablas)
print('Guardado desfibriladores.csv y horarios_semana.npy')
