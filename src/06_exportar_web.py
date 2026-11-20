"""Paso 6. Prepara web/datos.json, el único fichero que lee la web.

Incluye: centros de sección con población, desfibriladores fijos con su horario, qué secciones están
cubiertas en cada una de las 168 horas (comprimido en bits), la curva de la semana, los contornos
municipales (uniendo las secciones de cada municipio), los sitios propuestos y el resumen por municipio.
"""
import base64, json, zipfile, tempfile
from pathlib import Path
import numpy as np
import pandas as pd
import shapefile
from shapely.geometry import shape
from shapely.ops import unary_union
from pyproj import Transformer
from config import ORIGINALES, ELABORADOS, WEB, CRS_METROS

sec = pd.read_csv(ELABORADOS / 'secciones.csv', dtype={'cod_ine_seccion': str, 'cod_ine_muni': str})
dea = pd.read_csv(ELABORADOS / 'desfibriladores.csv', dtype=str)
tablas = np.load(ELABORADOS / 'horarios_semana.npy')
cubiertas = np.load(ELABORADOS / 'cubiertas_por_hora.npy')
semana = pd.read_csv(ELABORADOS / 'cobertura_semana.csv')
muni = pd.read_csv(ELABORADOS / 'cobertura_municipios.csv', dtype={'cod_ine_muni': str})
nuevos = pd.read_csv(ELABORADOS / 'nuevos_sitios.csv')

codigos = sorted(sec['cod_ine_muni'].unique())
idx = {m: i for i, m in enumerate(codigos)}
nombres = sec.drop_duplicates('cod_ine_muni').set_index('cod_ine_muni')['municipio']

# desfibriladores fijos: [lon, lat, estado, índice de su horario]
fijos = dea['fijo'].eq('True').values
dea, tablas = dea[fijos].reset_index(drop=True), tablas[fijos]
codigo_estado = {'24h': 0, 'horario': 1, 'desconocido': 2, 'eventos': 3}
horarios, pos, filas_dea = [], {}, []
for (_, d), tabla in zip(dea.iterrows(), tablas):
    k = -1
    if d['estado_horario'] == 'horario':
        clave = ''.join('1' if v else '0' for v in tabla.reshape(-1))
        k = pos.setdefault(clave, len(horarios))
        if k == len(horarios):
            horarios.append(clave)
    filas_dea.append([round(float(d['lon']), 5), round(float(d['lat']), 5), codigo_estado[d['estado_horario']], k])

# contornos municipales a partir de las secciones
a_grados = Transformer.from_crs(CRS_METROS, 4326, always_xy=True)
with tempfile.TemporaryDirectory() as tmp:
    zipfile.ZipFile(ORIGINALES / 'secciones_censales.zip').extractall(tmp)
    lector = shapefile.Reader(str(next(Path(tmp).glob('*.shp'))), encoding='latin1')
    por_muni = {}
    for reg in lector.iterShapeRecords():
        por_muni.setdefault(reg.record['CDMUNI'], []).append(shape(reg.shape.__geo_interface__).buffer(0))
contornos = []
for geoms in por_muni.values():
    g = unary_union(geoms).simplify(80)
    for p in ([g] if g.geom_type == 'Polygon' else g.geoms):
        x, y = a_grados.transform(*p.exterior.xy)
        contornos.append([[round(a, 4), round(b, 4)] for a, b in zip(x, y)])

datos = {
    'munis': [nombres[m] for m in codigos],
    'secs': [[round(r.lon, 5), round(r.lat, 5), int(round(r.poblacion)), int(round(r.mayores_65)), idx[r.cod_ine_muni]]
             for r in sec.itertuples()],
    'dea': filas_dea,
    'masks': horarios,
    'cov': [base64.b64encode(np.packbits(c).tobytes()).decode() for c in cubiertas],
    'curva': semana[['aparatos_abiertos', 'pct_poblacion', 'pct_poblacion_fuera_capital', 'pct_mayores_65']].values.tolist(),
    'contornos': contornos,
    'nuevos': [{'lon': r.lon, 'lat': r.lat, 'muni': r.municipio, 'personas': int(r.vecinos_nuevos), 'mayores': int(r.mayores_65_nuevos)}
               for r in nuevos.itertuples()],
    'municipios': [[r.municipio, int(r.poblacion), r.pct_martes_11h, r.pct_domingo_3h, int(r.tiene_desfibrilador_fijo)]
                   for r in muni.itertuples()],
}
WEB.mkdir(exist_ok=True)
(WEB / 'datos.json').write_text(json.dumps(datos, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
print('web/datos.json:', round((WEB / 'datos.json').stat().st_size / 1e6, 2), 'MB')
