"""Paso 3b. Reparte la población de cada sección censal por sus viviendas.

Una sección censal de un pueblo con urbanizaciones puede medir varios kilómetros. Si ponemos a todos
sus vecinos en el centro, un desfibrilador que está en medio de una urbanización no le cubre a nadie.
Por eso repartimos la población de cada sección entre sus edificios según el número de viviendas que
tienen en el Catastro, y juntamos los edificios en cuadrados de CELDA metros: cada cuadrado es un
punto con su parte de los vecinos. Si todas las viviendas de la sección están a menos de JUNTOS metros
de su centro (lo normal en una ciudad), la sección se queda en un solo punto, en el centro de sus viviendas.
Una sección sin viviendas en el Catastro se queda en su centro geométrico.
Salida: datos/elaborados/puntos.csv (una fila por punto; 'punto' es el código de la sección y un número)
"""
import zipfile, tempfile
from pathlib import Path
import numpy as np
import pandas as pd
import shapefile
import shapely
from shapely.geometry import shape
from pyproj import Transformer
from config import ORIGINALES, ELABORADOS, CRS_METROS, RAIZ

CELDA = 150   # metros
JUNTOS = 150  # metros

sec = pd.read_csv(ELABORADOS / 'secciones.csv', dtype={'cod_ine_seccion': str, 'cod_ine_muni': str})
viv = pd.read_csv(RAIZ / 'datos' / 'respaldo' / 'viviendas_catastro.csv.gz')

with tempfile.TemporaryDirectory() as tmp:
    zipfile.ZipFile(ORIGINALES / 'secciones_censales.zip').extractall(tmp)
    lector = shapefile.Reader(str(next(Path(tmp).glob('*.shp'))), encoding='latin1')
    poligonos = {'28' + r.record['CDGSECCION'].replace('-', ''): shape(r.shape.__geo_interface__) for r in lector.iterShapeRecords()}
codigos = sec['cod_ine_seccion'].tolist()
geoms = [poligonos[c] for c in codigos]
arbol = shapely.STRtree(geoms)

# cada edificio a su sección (los que caen justo fuera del borde, a la más cercana)
pts = shapely.points(viv['x'].values, viv['y'].values)
dentro_p, dentro_s = arbol.query(pts, predicate='within')
viv['s'] = -1
viv.loc[viv.index[dentro_p], 's'] = dentro_s
fuera = np.flatnonzero(viv['s'].values < 0)
if len(fuera):
    viv.loc[viv.index[fuera], 's'] = arbol.query_nearest(pts[fuera], all_matches=False)[1]
print(len(viv), 'edificios con viviendas;', len(fuera), 'asignados a la sección más cercana')

filas = []
grupos = viv.groupby('s')
for s, r in sec.iterrows():
    base = {'cod_ine_seccion': r.cod_ine_seccion, 'cod_ine_muni': r.cod_ine_muni, 'municipio': r.municipio}
    if s not in grupos.groups:
        filas.append({**base, 'x': r.x, 'y': r.y, 'parte': 1.0})
        continue
    g = grupos.get_group(s)
    w = g['viviendas'].values.astype(float)
    cx, cy = np.average(g['x'], weights=w), np.average(g['y'], weights=w)
    if np.hypot(g['x'] - cx, g['y'] - cy).max() <= JUNTOS:
        filas.append({**base, 'x': cx, 'y': cy, 'parte': 1.0})
        continue
    celda = (g['x'] // CELDA).astype(int).astype(str) + '_' + (g['y'] // CELDA).astype(int).astype(str)
    for _, c in g.groupby(celda.values):
        wc = c['viviendas'].values.astype(float)
        filas.append({**base, 'x': np.average(c['x'], weights=wc), 'y': np.average(c['y'], weights=wc), 'parte': wc.sum() / w.sum()})

p = pd.DataFrame(filas)
p['punto'] = p['cod_ine_seccion'] + '-' + p.groupby('cod_ine_seccion').cumcount().add(1).astype(str)
p = p.merge(sec[['cod_ine_seccion', 'poblacion', 'mayores_65']], on='cod_ine_seccion')
p['poblacion'] *= p['parte']
p['mayores_65'] *= p['parte']
p['lon'], p['lat'] = Transformer.from_crs(CRS_METROS, 4326, always_xy=True).transform(p['x'].values, p['y'].values)
cols = ['punto', 'cod_ine_seccion', 'cod_ine_muni', 'municipio', 'x', 'y', 'lon', 'lat', 'poblacion', 'mayores_65']
p[cols].round({'lon': 5, 'lat': 5, 'x': 1, 'y': 1, 'poblacion': 2, 'mayores_65': 2}).to_csv(ELABORADOS / 'puntos.csv', index=False)
n = p.groupby('cod_ine_seccion').size()
print(len(p), 'puntos de población;', (n > 1).sum(), 'secciones repartidas en más de un punto (hasta', n.max(), ')')
print('Población total:', round(p['poblacion'].sum()))
