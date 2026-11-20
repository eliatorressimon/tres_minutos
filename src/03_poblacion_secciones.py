"""Paso 3. Calcula el centro de cada sección censal y le pone su población.

- Geometría: shapefile de secciones censales de la Comunidad de Madrid (seccionado de 2019).
- Población: tabla 31105 del INE. Usamos 2019 para que los códigos de sección coincidan con el seccionado,
  y reescalamos para que cada municipio sume su población de 2024.
Salida: datos/elaborados/secciones.csv
"""
import zipfile, tempfile
import numpy as np
import pandas as pd
import shapefile  # pyshp
from pyproj import Transformer
from config import ORIGINALES, ELABORADOS, CRS_METROS


def centroide(puntos, partes):
    """Centroide y área de un polígono (fórmula del área con signo, válida con huecos)."""
    A = cx = cy = 0.0
    limites = list(partes) + [len(puntos)]
    for a, b in zip(limites[:-1], limites[1:]):
        p = np.array(puntos[a:b])
        x0, y0, x1, y1 = p[:-1, 0], p[:-1, 1], p[1:, 0], p[1:, 1]
        c = x0 * y1 - x1 * y0
        A += c.sum(); cx += ((x0 + x1) * c).sum(); cy += ((y0 + y1) * c).sum()
    A /= 2
    return cx / (6 * A), cy / (6 * A), abs(A)


# 1. geometría
with tempfile.TemporaryDirectory() as tmp:
    zipfile.ZipFile(ORIGINALES / 'secciones_censales.zip').extractall(tmp)
    shp = next(p for p in __import__('pathlib').Path(tmp).glob('*.shp'))
    lector = shapefile.Reader(str(shp), encoding='latin1')
    filas = []
    for reg in lector.iterShapeRecords():
        cod = reg.record['CDGSECCION'].replace('-', '')   # p. ej. 079-12-062 -> 07912062
        x, y, area = centroide(reg.shape.points, reg.shape.parts)
        filas.append((cod, cod[:3], x, y, area))
sec = pd.DataFrame(filas, columns=['cod', 'muni', 'x', 'y', 'area_m2'])
sec['cod_ine_seccion'] = '28' + sec['cod']
sec['cod_ine_muni'] = '28' + sec['muni']
print('Secciones:', len(sec))

# 2. población del INE
ine = pd.read_csv(ORIGINALES / 'ine_31105.csv', sep=';', dtype=str, keep_default_na=False)
ine.columns = ['municipio', 'distrito', 'seccion', 'indicador', 'periodo', 'valor']
ine['valor'] = pd.to_numeric(ine['valor'].str.replace('.', '', regex=False).str.replace(',', '.'), errors='coerce')
def es_pob(df): return df['indicador'].eq('Población')
def es_65(df): return df['indicador'].str.contains('65 y más')

s19 = ine[ine['seccion'].ne('') & ine['periodo'].eq('2019')].copy()
s19['cod_ine_seccion'] = s19['seccion'].str.split(' ').str[0]
pob19 = s19[es_pob(s19)].set_index('cod_ine_seccion')['valor']
p65_19 = s19[es_65(s19)].set_index('cod_ine_seccion')['valor']

m24 = ine[ine['distrito'].eq('') & ine['seccion'].eq('') & ine['municipio'].ne('') & ine['periodo'].eq('2024')].copy()
m24['cod_ine_muni'] = m24['municipio'].str[:5]
m24['nombre'] = m24['municipio'].str[6:]
pob_muni = m24[es_pob(m24)].set_index('cod_ine_muni')['valor']
p65_muni = m24[es_65(m24)].set_index('cod_ine_muni')['valor']
nombres = m24[es_pob(m24)].set_index('cod_ine_muni')['nombre']

sec['pob_2019'] = sec['cod_ine_seccion'].map(pob19)
sec['pct_65'] = sec['cod_ine_seccion'].map(p65_19)
# el INE da 0 en secciones de pueblos muy pequeños: lo tratamos como dato que falta
sec.loc[sec['pob_2019'] <= 0, 'pob_2019'] = np.nan
sec.loc[sec['pct_65'] <= 0, 'pct_65'] = np.nan

# 3. reescalar a 2024 dentro de cada municipio (si no hay datos de 2019, repartimos por superficie)
sec['poblacion'] = 0.0
for m, g in sec.groupby('cod_ine_muni'):
    total = pob_muni[m]
    if g['pob_2019'].notna().any():
        peso = g['pob_2019'].fillna(0)
    else:
        peso = g['area_m2']
    sec.loc[g.index, 'poblacion'] = total * peso / peso.sum()
sec['pct_65'] = sec['pct_65'].fillna(sec['cod_ine_muni'].map(p65_muni))
sec['mayores_65'] = sec['poblacion'] * sec['pct_65'] / 100
sec['municipio'] = sec['cod_ine_muni'].map(nombres)

a_grados = Transformer.from_crs(CRS_METROS, 4326, always_xy=True)
sec['lon'], sec['lat'] = a_grados.transform(sec['x'].values, sec['y'].values)

print('Población total:', round(sec['poblacion'].sum()), ' mayores de 65:', round(sec['mayores_65'].sum()))
cols = ['cod_ine_seccion', 'cod_ine_muni', 'municipio', 'x', 'y', 'lon', 'lat', 'poblacion', 'mayores_65']
sec[cols].round({'lon': 5, 'lat': 5, 'x': 1, 'y': 1, 'poblacion': 1, 'mayores_65': 1}).to_csv(ELABORADOS / 'secciones.csv', index=False)
pd.DataFrame({'cod_ine_muni': pob_muni.index, 'municipio': nombres.reindex(pob_muni.index).values,
              'poblacion_2024': pob_muni.values}).to_csv(ELABORADOS / 'municipios.csv', index=False)
print('Guardado secciones.csv y municipios.csv')
