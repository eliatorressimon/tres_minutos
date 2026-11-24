"""Paso 1b. Más sitios donde poner un aparato, sacados de OpenStreetMap: comisarías y cuarteles, parques de
bomberos y estaciones de metro, metro ligero y tren.

Usa el mismo mapa de Geofabrik que el servidor de rutas (ver .github/workflows/actualizar.yml). Si el mapa no
está (por ejemplo, al ejecutarlo en otro ordenador), usa la última copia guardada en datos/respaldo/.

  - Policía (nacional, local o municipal), Guardia Civil y bomberos: hay gente de guardia toda la noche, así que
    los tratamos como abiertos las 24 horas. Es una suposición: habría que acordarlo con cada cuerpo. Quitamos
    oficinas que solo atienden de día (DNI y pasaporte, atención al ciudadano), unidades sin público, agentes
    forestales y Protección Civil, que es voluntaria.
  - Estaciones: abren de día y por la tarde, pero cierran de madrugada (el metro, de 1:30 a 6:00). Cuentan solo
    como candidatos de día.
Salida: datos/originales/sitios_osm.csv y una copia en datos/respaldo/sitios_osm.csv
"""
import os
import re
import shutil
import pandas as pd
from config import ORIGINALES, RAIZ

PBF = os.environ.get('OSM_PBF', str(RAIZ / 'osrm' / 'madrid.osm.pbf'))
RESPALDO = RAIZ / 'datos' / 'respaldo' / 'sitios_osm.csv'
SALIDA = ORIGINALES / 'sitios_osm.csv'

SIN_PUBLICO = re.compile(r'dni|pasaporte|atenci[oó]n al ciudadano|oficina|formaci[oó]n|personal|direcci[oó]n general|'
                         r'unidad|forestal|museo|academia|escuela|jefatura superior', re.I)


def clasificar(tags):
    """Tipo de sitio a partir de las etiquetas de OpenStreetMap, o None si no nos vale."""
    nombre = tags.get('name', '')
    texto = ' '.join([nombre, tags.get('operator', ''), tags.get('police:ES', '')]).lower()
    if tags.get('disused') == 'yes' or 'disused:railway' in tags:
        return None
    if tags.get('amenity') == 'police':
        if SIN_PUBLICO.search(nombre):
            return None
        if 'guardia civil' in texto:
            return 'Guardia Civil'
        if 'local' in texto or 'municipal' in texto:
            return 'Policía local'
        return 'Policía nacional' if ('nacional' in texto or 'comisar' in texto or 'interior' in texto) else 'Policía'
    if tags.get('amenity') == 'fire_station':
        return None if 'protecci' in texto else 'Bomberos'
    if tags.get('railway') == 'station':
        if 'aena' in texto:                      # el tren interno de la T4 del aeropuerto
            return None
        if tags.get('station') == 'subway':
            return 'Estación de metro'
        if tags.get('station') == 'light_rail':
            return 'Estación de metro ligero'
        return 'Estación de tren'
    return None


def leer_pbf(ruta):
    import osmium
    filas = []
    fp = (osmium.FileProcessor(ruta).with_locations()
          .with_filter(osmium.filter.KeyFilter('amenity', 'railway')))
    for o in fp:
        if o.is_relation():
            continue
        tags = dict(o.tags)
        tipo = clasificar(tags)
        if tipo is None:
            continue
        if o.is_node():
            lon, lat = o.location.lon, o.location.lat
        else:                                       # un edificio dibujado como polígono: su punto medio
            pts = [(n.location.lon, n.location.lat) for n in o.nodes if n.location.valid()]
            if not pts:
                continue
            lon, lat = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
        filas.append({'id': f'osm-{o.type_str()}{o.id}', 'tipo': tipo, 'nombre': tags.get('name', ''),
                      'lon': round(lon, 6), 'lat': round(lat, 6)})
    return pd.DataFrame(filas)


if __name__ == '__main__':
    ORIGINALES.mkdir(parents=True, exist_ok=True)
    if os.path.exists(PBF):
        s = leer_pbf(PBF)
        # la misma comisaría a veces está dos veces (el punto y el edificio): nos quedamos con una
        s['r'] = s['lon'].round(3).astype(str) + s['lat'].round(3).astype(str)
        s = s.drop_duplicates(['tipo', 'r']).drop(columns='r').sort_values(['tipo', 'id'])
        s.to_csv(SALIDA, index=False)
        RESPALDO.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(SALIDA, RESPALDO)
    elif RESPALDO.exists():
        print('No está el mapa de OpenStreetMap; uso la copia de', RESPALDO)
        shutil.copy(RESPALDO, SALIDA)
    else:
        raise SystemExit('Falta el mapa de OpenStreetMap (' + PBF + ') y no hay copia en datos/respaldo/')
    print(pd.read_csv(SALIDA)['tipo'].value_counts().to_string())
