"""Paso 7. Los diez mejores sitios REALES para un aparato nuevo.

El paso 5 busca puntos ideales del mapa. Aquí solo valen locales que ya existen y que tienen sentido:
  - De noche (domingo a las 3:00): gasolineras abiertas las 24 horas, según su horario en el Ministerio.
  - De día (martes a las 11:00): farmacias, que abren de día en casi todos los barrios.
Mismo método voraz que el paso 5: en cada paso elegimos el local que más vecinos sin cubrir gana,
contando dos veces a los mayores de 65, y repetimos con los que quedan.
También calculamos qué pasaría si TODAS las gasolineras de 24 horas, o todas las farmacias, tuvieran uno.
Salidas: datos/elaborados/sitios_reales.csv y datos/elaborados/sitios_reales_resumen.csv
"""
import json
import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.spatial import cKDTree
from config import ORIGINALES, ELABORADOS, RADIO_M, NUEVOS_APARATOS, CRS_METROS

sec = pd.read_csv(ELABORADOS / 'secciones.csv', dtype={'cod_ine_seccion': str, 'cod_ine_muni': str})
cubiertas_semana = np.load(ELABORADOS / 'cubiertas_por_hora.npy')
pob, p65 = sec['poblacion'].fillna(0).values, sec['mayores_65'].fillna(0).values
peso = pob + p65                       # los mayores de 65 cuentan doble
arbol = cKDTree(sec[['x', 'y']].values)
a_metros = Transformer.from_crs(4326, CRS_METROS, always_xy=True)

# gasolineras: el horario viene como "L-D: 24H" o "L-D: 06:00-22:00"
g = pd.DataFrame(json.loads((ORIGINALES / 'gasolineras.json').read_text(encoding='utf-8'))['ListaEESSPrecio'])
g['lon'] = g['Longitud (WGS84)'].str.replace(',', '.').astype(float)
g['lat'] = g['Latitud'].str.replace(',', '.').astype(float)
g = g[g['Horario'].str.fullmatch(r'L-D: (24H|00:00-23:59)')].copy()
g['x'], g['y'] = a_metros.transform(g['lon'].values, g['lat'].values)
gasolineras = pd.DataFrame({'tipo': 'Gasolinera 24 h', 'nombre': g['Rótulo'].str.title(), 'direccion': g['Dirección'].str.title(),
                            'municipio': g['Municipio'], 'x': g['x'], 'y': g['y'], 'lon': g['lon'], 'lat': g['lat']})

# farmacias: coordenadas en metros (ETRS89 UTM 30N). No guardamos el nombre de los titulares.
f = pd.read_csv(ORIGINALES / 'oficinas_farmacia.csv', sep=';', dtype=str, encoding='utf-8')
f['x'] = f['LOCALIZACION_COORDENADA_X'].str.replace(',', '.').astype(float)
f['y'] = f['LOCALIZACION_COORDENADA_Y'].str.replace(',', '.').astype(float)
f = f.dropna(subset=['x', 'y'])
a_grados = Transformer.from_crs(CRS_METROS, 4326, always_xy=True)
f['lon'], f['lat'] = a_grados.transform(f['x'].values, f['y'].values)
direccion = (f['DIRECCION_VIAL_TIPO'].fillna('').str.title() + ' ' + f['DIRECCION_VIAL_NOMBRE'].fillna('') + ' ' + f['DIRECCION_VIAL_NRO'].fillna('')).str.strip()
farmacias = pd.DataFrame({'tipo': 'Farmacia', 'nombre': 'Farmacia', 'direccion': direccion, 'municipio': f['MUNICIPIO_NOMBRE'],
                          'x': f['x'], 'y': f['y'], 'lon': f['lon'], 'lat': f['lat']})


def elegir(locales, hora, cuantos):
    cubiertas = cubiertas_semana[hora].copy()
    cerca = arbol.query_ball_point(locales[['x', 'y']].values, RADIO_M)
    filas = []
    for k in range(cuantos):
        ganancia = np.array([peso[[i for i in c if not cubiertas[i]]].sum() for c in cerca])
        mejor = int(ganancia.argmax())
        nuevas = [i for i in cerca[mejor] if not cubiertas[i]]
        cubiertas[nuevas] = True
        fila = locales.iloc[mejor]
        filas.append({'orden': k + 1, 'momento': 'domingo 3:00' if hora == 147 else 'martes 11:00', **fila.drop(['x', 'y']).to_dict(),
                      'vecinos_nuevos': round(pob[nuevas].sum()), 'mayores_65_nuevos': round(p65[nuevas].sum())})
    return filas


def si_todos(locales, hora):
    cubiertas = cubiertas_semana[hora].copy()
    for c in arbol.query_ball_point(locales[['x', 'y']].values, RADIO_M):
        cubiertas[c] = True
    antes = pob[cubiertas_semana[hora]].sum() / pob.sum()
    return {'locales': len(locales), 'pct_antes': round(100 * antes, 1), 'pct_despues': round(100 * pob[cubiertas].sum() / pob.sum(), 1),
            'vecinos_nuevos': round(pob[cubiertas].sum() - pob[cubiertas_semana[hora]].sum())}


res = pd.DataFrame(elegir(gasolineras.reset_index(drop=True), 147, NUEVOS_APARATOS) +
                   elegir(farmacias.reset_index(drop=True), 35, NUEVOS_APARATOS))
res.to_csv(ELABORADOS / 'sitios_reales.csv', index=False)
resumen = pd.DataFrame([{'caso': 'Todas las gasolineras 24 h, domingo 3:00', **si_todos(gasolineras, 147)},
                        {'caso': 'Todas las farmacias, martes 11:00', **si_todos(farmacias, 35)}])
resumen.to_csv(ELABORADOS / 'sitios_reales_resumen.csv', index=False)
print(res[['orden', 'momento', 'tipo', 'nombre', 'municipio', 'vecinos_nuevos', 'mayores_65_nuevos']].to_string(index=False))
print(resumen.to_string(index=False))
