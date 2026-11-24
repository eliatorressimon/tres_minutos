"""Paso 9. Prepara web/datos.json, el único fichero que lee la web, y la carpeta web/descargas/.

Incluye: centros de sección con población, desfibriladores fijos con su horario, municipio y tipo de sitio, qué secciones están
cubiertas en cada una de las 168 horas (comprimido en bits), la curva de la semana, los polígonos
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
from scipy.spatial import cKDTree
from candidatos import farmacias, gasolineras_todas, centros_sanitarios

sec = pd.read_csv(ELABORADOS / 'puntos.csv', dtype={'punto': str, 'cod_ine_seccion': str, 'cod_ine_muni': str})
dea = pd.read_csv(ELABORADOS / 'desfibriladores.csv', dtype=str)
tablas = np.load(ELABORADOS / 'horarios_semana.npy')
cubiertas = np.load(ELABORADOS / 'cubiertas_por_hora.npy')
semana = pd.read_csv(ELABORADOS / 'cobertura_semana.csv')
muni = pd.read_csv(ELABORADOS / 'cobertura_municipios.csv', dtype={'cod_ine_muni': str})
nuevos = pd.read_csv(ELABORADOS / 'nuevos_sitios.csv')
reales = pd.read_csv(ELABORADOS / 'sitios_reales.csv').fillna('')
si_todos = pd.read_csv(ELABORADOS / 'sitios_reales_resumen.csv')

codigos = sorted(sec['cod_ine_muni'].unique())
idx = {m: i for i, m in enumerate(codigos)}
nombres = sec.drop_duplicates('cod_ine_muni').set_index('cod_ine_muni')['municipio']

# cifras generales que la web escribe en sus textos (así se actualizan solas con cada descarga)
var = pd.read_csv(ELABORADOS / 'cobertura_variantes.csv')
def pct(medida, dia, hora):
    return float(var.query('medida == @medida and radio_m == 200 and dia == @dia and hora == @hora')['pct_poblacion'].iloc[0])
resumen = {
    'registro': len(dea),
    'movil': int(dea['estado_horario'].eq('movil').sum()),
    'siempre': int(dea['estado_horario'].eq('24h').sum()),
    'desconocido': int(dea['estado_horario'].eq('desconocido').sum()),
    'formas': int(dea['horario_acceso'].nunique()),
    'andando_martes': pct('andando', 'martes', 11), 'recta_martes': pct('recta', 'martes', 11),
    'andando_domingo': pct('andando', 'domingo', 3), 'recta_domingo': pct('recta', 'domingo', 3),
}

# desfibriladores fijos: [lon, lat, estado, índice de su horario]
fijos = dea['fijo'].eq('True').values
dea, tablas = dea[fijos].reset_index(drop=True), tablas[fijos]
codigo_estado = {'24h': 0, 'horario': 1, 'desconocido': 2, 'eventos': 3}
TIPOS = {  # nombres cortos para la ficha de cada municipio
    'Otros': 'Otros sitios', 'Centro educativo': 'Colegios e institutos',
    'Establecimiento dependiente de una Administración Pública': 'Edificios públicos',
    'Centro de trabajo con más de 250 trabajadores': 'Empresas grandes',
    'Instalación, centro o complejo deportivo con más de 500 usuarios diarios': 'Polideportivos',
    'Instalaciones de transporte': 'Transporte', 'Establecimiento hotelero con más de 100 plazas': 'Hoteles',
    'Grandes establecimientos comerciales con una superficie superior a 2500 m2': 'Centros comerciales',
    'Aeropuertos': 'Aeropuertos', 'Establecimiento público con aforo igual o superior a 2000 personas': 'Grandes aforos',
    'Centros residenciales de mayores con 200 plazas': 'Residencias de mayores'}
# "Otros" es el tipo más común (casi un tercio). El registro no dice más, pero muchos están en el mismo sitio
# que una clínica, una farmacia o una gasolinera de otros registros: si hay una a 25 m o menos, lo decimos.
# Si no, al menos separamos los públicos de los privados.
CERCA_M = 25
MAS_OTROS = ['Clínicas y centros sanitarios', 'Farmacias', 'Gasolineras', 'Otros sitios públicos', 'Otros sitios privados']
tipos = sorted(set(TIPOS.values()) - {'Otros sitios'}) + MAS_OTROS
a_m = Transformer.from_crs(4326, CRS_METROS, always_xy=True)
def a_metros(lon, lat):
    return np.c_[a_m.transform(np.asarray(lon, float), np.asarray(lat, float))]
pos_dea = a_metros(dea['lon'], dea['lat'])
tipo_dea = dea['tipo_establecimiento'].map(lambda t: TIPOS.get(t, 'Otros sitios')).values.copy()
otros = tipo_dea == 'Otros sitios'
tipo_dea[otros] = np.where(dea.loc[otros, 'tipo_titularidad'].eq('Pública'), 'Otros sitios públicos', 'Otros sitios privados')
for nombre, sitios in [('Gasolineras', gasolineras_todas()), ('Farmacias', farmacias()), ('Clínicas y centros sanitarios', centros_sanitarios(todos=True))]:
    d, _ = cKDTree(a_metros(sitios['lon'], sitios['lat'])).query(pos_dea[otros])
    idx_o = np.flatnonzero(otros)[d <= CERCA_M]
    tipo_dea[idx_o] = nombre
print('Otros sitios aclarados:', pd.Series(tipo_dea[otros]).value_counts().to_dict())
horarios, pos, filas_dea = [], {}, []
textos, pos_texto = [], {}  # horario tal como viene escrito, para enseñarlo en la web
for (_, d), tabla in zip(dea.iterrows(), tablas):
    k = -1
    if d['estado_horario'] == 'horario':
        clave = ''.join('1' if v else '0' for v in tabla.reshape(-1))
        k = pos.setdefault(clave, len(horarios))
        if k == len(horarios):
            horarios.append(clave)
    filas_dea.append([round(float(d['lon']), 5), round(float(d['lat']), 5), codigo_estado[d['estado_horario']], k,
                      idx.get('28' + str(d['municipio_codigo']), -1), tipos.index(tipo_dea[len(filas_dea)])])
    texto = ' '.join(str(d['horario_acceso']).split()) if isinstance(d['horario_acceso'], str) else ''
    filas_dea[-1].append(pos_texto.setdefault(texto, len(textos)))
    if filas_dea[-1][-1] == len(textos):
        textos.append(texto)

# si un aparato no trae municipio, se le asigna el de la sección más cercana
from scipy.spatial import cKDTree
arbol = cKDTree(sec[['lon', 'lat']].values)
for fila in filas_dea:
    if fila[4] == -1:
        fila[4] = idx[sec['cod_ine_muni'].iloc[arbol.query(fila[:2])[1]]]

# contornos municipales a partir de las secciones
a_grados = Transformer.from_crs(CRS_METROS, 4326, always_xy=True)
with tempfile.TemporaryDirectory() as tmp:
    zipfile.ZipFile(ORIGINALES / 'secciones_censales.zip').extractall(tmp)
    lector = shapefile.Reader(str(next(Path(tmp).glob('*.shp'))), encoding='latin1')
    por_muni = {}
    for reg in lector.iterShapeRecords():
        por_muni.setdefault(reg.record['CDGSECCION'][:3], []).append(shape(reg.shape.__geo_interface__).buffer(0))
# polígonos de cada municipio, en el mismo orden que 'munis'
poligonos = [[] for _ in codigos]
for cdmuni, geoms in por_muni.items():
    g = unary_union(geoms).simplify(80)
    for p in ([g] if g.geom_type == 'Polygon' else g.geoms):
        x, y = a_grados.transform(*p.exterior.xy)
        poligonos[idx['28' + cdmuni]].append([[round(a, 4), round(b, 4)] for a, b in zip(x, y)])

# centros de salud y hospitales (no están en el registro): posición, tipo y puntos de población a 200 m o menos andando,
# para el interruptor de la web que los cuenta como si tuvieran un aparato con su horario habitual
sani = centros_sanitarios()
pos_punto = {p: i for i, p in enumerate(sec['punto'])}
cerca = pd.read_csv(ELABORADOS / 'distancias_candidatos.csv', dtype={'id': str, 'punto': str})
cerca = cerca[cerca['tipo'].isin(['Centro de salud', 'Hospital'])]
por_sitio = {}
for i, punto, m in zip(cerca['id'], cerca['punto'], cerca['metros_andando']):
    if punto in pos_punto:
        por_sitio.setdefault(i, []).extend([pos_punto[punto], int(round(m))])
sanitarios_web = [[round(r.lon, 5), round(r.lat, 5), 1 if r.tipo == 'Hospital' else 0, por_sitio.get(r.id, [])] for r in sani.itertuples()]

datos = {
    'munis': [nombres[m] for m in codigos],
    'secs': [[round(r.lon, 5), round(r.lat, 5), int(round(r.poblacion)), int(round(r.mayores_65)), idx[r.cod_ine_muni]]
             for r in sec.itertuples()],
    'dea': filas_dea,
    'masks': horarios,
    'cov': [base64.b64encode(np.packbits(c).tobytes()).decode() for c in cubiertas],
    'curva': semana[['aparatos_abiertos', 'pct_poblacion', 'pct_poblacion_fuera_capital', 'pct_mayores_65']].values.tolist(),
    'poligonos': poligonos,
    'tipos': tipos,
    'horarios_texto': textos,
    'nuevos': [{'lon': r.lon, 'lat': r.lat, 'muni': r.municipio, 'personas': int(r.vecinos_nuevos), 'mayores': int(r.mayores_65_nuevos)}
               for r in nuevos.itertuples()],
    'reales': [{'momento': 'noche' if r.momento.startswith('domingo') else 'dia', 'tipo': r.tipo, 'nombre': r.nombre,
                'direccion': r.direccion, 'muni': r.municipio, 'lon': round(r.lon, 5), 'lat': round(r.lat, 5),
                'personas': int(r.vecinos_nuevos), 'mayores': int(r.mayores_65_nuevos)} for r in reales.itertuples()],
    'si_todos': si_todos.to_dict('records'),
    'resumen': resumen,
    'sanitarios': sanitarios_web,
    'municipios': [[r.municipio, int(r.poblacion), r.pct_martes_11h, r.pct_domingo_3h, int(r.tiene_desfibrilador_fijo)]
                   for r in muni.itertuples()],
}
WEB.mkdir(exist_ok=True)
(WEB / 'datos.json').write_text(json.dumps(datos, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
print('web/datos.json:', round((WEB / 'datos.json').stat().st_size / 1e6, 2), 'MB')

# descargas: los datos elaborados que se pueden bajar desde la pestaña Método de la web
DESCARGAS = WEB / 'descargas'
DESCARGAS.mkdir(exist_ok=True)
# en el formato habitual de los portales de datos españoles, para que se abran bien en Excel:
# separador punto y coma, coma decimal y UTF-8 con marca inicial (así se ven bien las tildes)
def guardar(df, nombre):
    df.to_csv(DESCARGAS / nombre, index=False, sep=';', decimal=',', encoding='utf-8-sig')
for nombre in ['desfibriladores.csv', 'cobertura_semana.csv', 'cobertura_variantes.csv', 'nuevos_sitios.csv',
               'sitios_reales.csv', 'sitios_reales_resumen.csv']:
    guardar(pd.read_csv(ELABORADOS / nombre, dtype={'codigo_dea': str, 'municipio_codigo': str, 'cod_ine_muni': str, 'id': str}), nombre)
# cobertura de cada municipio en cada hora de la semana, a 200 m andando (la medida principal de la web)
andando = np.load(ELABORADOS / 'cubiertas_andando.npy')
pob = sec['poblacion'].fillna(0).values
DIAS = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
filas = []
for m, pos_m in sec.groupby('cod_ine_muni').indices.items():
    total = pob[pos_m].sum()
    cubiertos = andando[:, pos_m].astype(float) @ pob[pos_m]
    for t in range(168):
        filas.append({'cod_ine_muni': m, 'municipio': nombres[m], 'poblacion': round(total), 'dia': DIAS[t // 24], 'hora': t % 24,
                      'pct_cubierto': round(100 * cubiertos[t] / total, 1) if total else 0.0,
                      'personas_sin_cubrir': round(total - cubiertos[t])})
guardar(pd.DataFrame(filas), 'cobertura_municipio_hora.csv')
print('web/descargas:', len(list(DESCARGAS.iterdir())), 'ficheros')
