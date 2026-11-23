import numpy as np, pandas as pd
from scipy.spatial import cKDTree
from config import ELABORADOS
import importlib.util, sys
p = pd.read_csv(ELABORADOS / 'puntos.csv', dtype=str)
for c in ['x', 'y', 'poblacion']: p[c] = p[c].astype(float)
dea = pd.read_csv(ELABORADOS / 'desfibriladores.csv', dtype=str)
dea = dea[dea['fijo'].eq('True') & dea['estado_horario'].isin(['24h', 'horario'])].reset_index(drop=True)
from pyproj import Transformer
t = Transformer.from_crs(4326, 25830, always_xy=True)
dea['x'], dea['y'] = t.transform(dea['lon'].astype(float).values, dea['lat'].astype(float).values)
sys.path.insert(0, '.')
spec = importlib.util.spec_from_file_location('d', '05_distancias_calle.py'); d = importlib.util.module_from_spec(spec); spec.loader.exec_module(d)
cerca = cKDTree(dea[['x', 'y']].values).query_ball_point(p[['x', 'y']].values, 300)
print('parejas punto-aparato a 300 m en recta:', sum(map(len, cerca)))
print('peticiones OSRM (tabla 1):', len(d.lotes(cerca, p)))
cerca2 = cKDTree(p[['x', 'y']].values).query_ball_point(p[['x', 'y']].values, 200)
print('peticiones OSRM sitio ideal aprox:', len(d.lotes(cerca2, p)))
v = p[p['municipio'].eq('Valdemorillo')]
print(v.groupby('cod_ine_seccion').size())
print(p.groupby('cod_ine_muni').size().sort_values().tail(10))
