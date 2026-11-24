"""Paso 8b. Dos tablas para mejorar el registro, sin comprar ningún aparato.

1. horarios_formato_fijo.csv: el horario de cada aparato, que en el registro es un texto libre (hay más de
   2.000 formas distintas de escribirlo), pasado a un formato fijo: una columna por día con las horas de
   apertura y cierre, y la misma información en el formato 'opening_hours' de OpenStreetMap, que ya usan
   muchos mapas y aplicaciones. Es nuestra lectura del texto, redondeada a horas enteras (un '9 a 16:30'
   queda como 09:00-17:00). Si el registro pidiera el horario así desde el principio, este paso sobraría.

2. 24h_a_revisar.csv: los aparatos que dicen estar disponibles las 24 horas, ordenados por cuántos vecinos
   dependen solo de ellos de madrugada (domingo a las 3:00, a 200 m o menos andando). Son los primeros que
   habría que comprobar sobre el terreno: si alguno en realidad no se puede usar de noche, esa gente se queda
   sin nada. Marcamos además los que están en sitios que suelen cerrar de noche (colegios, oficinas, tiendas,
   polideportivos) o cuyo texto mezcla '24 h' con otro horario.
"""
import re
import numpy as np
import pandas as pd
from config import ELABORADOS, RADIO_M
from horarios import parse, norm

DIAS = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
OSM = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su']
DOMINGO_3 = (6, 3)

dea = pd.read_csv(ELABORADOS / 'desfibriladores.csv', dtype=str, keep_default_na=False)
sec = pd.read_csv(ELABORADOS / 'puntos.csv', dtype={'punto': str})
calle = pd.read_csv(ELABORADOS / 'distancias_calle.csv', dtype={'punto': str})


def tramos(fila):
    """Horas abiertas de un día (24 valores) como texto: '08:00-14:00,17:00-21:00', o '' si cierra."""
    t, h = [], 0
    while h < 24:
        if fila[h]:
            ini = h
            while h < 24 and fila[h]:
                h += 1
            t.append(f'{ini:02d}:00-{h:02d}:00')
        h += 1
    return ','.join(t)


def opening_hours(tabla):
    """El mismo horario con la sintaxis de OpenStreetMap: 'Mo-Fr 08:00-21:00; Sa 09:00-14:00'."""
    if tabla.all():
        return '24/7'
    por_dia = [tramos(tabla[d]) for d in range(7)]
    partes, d = [], 0
    while d < 7:
        f = d
        while f + 1 < 7 and por_dia[f + 1] == por_dia[d]:
            f += 1
        if por_dia[d]:
            dias = OSM[d] if f == d else f'{OSM[d]}-{OSM[f]}' if f > d + 1 else f'{OSM[d]},{OSM[f]}'
            partes.append(f'{dias} {por_dia[d]}')
        d = f + 1
    return '; '.join(partes)


# 1. formato fijo
filas, tablas = [], []
for r in dea.itertuples():
    estado, tabla = parse(r.horario_acceso)
    if tabla is None:
        tabla = np.ones((7, 24), bool) if estado == '24h' else np.zeros((7, 24), bool)
    tablas.append(tabla)
    fila = {'codigo_dea': r.codigo_dea, 'horario_en_el_registro': r.horario_acceso, 'lectura': estado}
    sabido = estado in ('24h', 'horario')
    for d, nombre in enumerate(DIAS):
        fila[nombre] = ('00:00-24:00' if tabla[d].all() else tramos(tabla[d]) or 'cerrado') if sabido else ''
    fila['opening_hours'] = opening_hours(tabla) if sabido else ''
    filas.append(fila)
fijo = pd.DataFrame(filas)
fijo.to_csv(ELABORADOS / 'horarios_formato_fijo.csv', index=False)
tablas = np.array(tablas)
print('Horarios en formato fijo:', len(fijo), 'aparatos;', fijo['lectura'].value_counts().to_dict())
print('Textos distintos en el registro:', dea['horario_acceso'].nunique(), '-> formatos fijos distintos:',
      fijo.loc[fijo['opening_hours'] != '', 'opening_hours'].nunique())

# 2. aparatos 24 h por revisar
de_noche = tablas[:, DOMINGO_3[0], DOMINGO_3[1]] & dea['fijo'].eq('True').values
c = calle[(calle['metros_andando'] <= RADIO_M) & de_noche[calle['fila_dea'].values]]
cuantos = c.groupby('punto')['fila_dea'].nunique()          # aparatos abiertos de noche que tiene cada punto
solo = c[c['punto'].map(cuantos) == 1]                      # puntos con un único aparato abierto de noche
pob = sec.set_index('punto')['poblacion']
may = sec.set_index('punto')['mayores_65']
depende = solo.groupby('fila_dea')['punto'].agg(lambda p: pob.reindex(p).sum())
depende_may = solo.groupby('fila_dea')['punto'].agg(lambda p: may.reindex(p).sum())
cubre = c.groupby('fila_dea')['punto'].agg(lambda p: pob.reindex(p).sum())

SITIO_DUDOSO = {
    'Centro educativo': 'Colegio o instituto: suelen cerrar de noche',
    'Centro de trabajo con más de 250 trabajadores': 'Centro de trabajo: puede cerrar de noche',
    'Grandes establecimientos comerciales con una superficie de exposición y venta al público superior a 2500 m2': 'Tienda grande: cierra de noche',
    'Instalación, centro o complejo deportivo con más de 500 usuarios diarios': 'Polideportivo: suele cerrar de noche',
    'Establecimiento público con aforo igual o superior a 2000 personas': 'Recinto de espectáculos: abre en eventos',
}
TEXTO_DUDOSO = re.compile(r'escolar|lectivo|oficina|apertura|laborable|segun|excepto|salvo|cerrad')

revisar = dea[(fijo['lectura'] == '24h') & dea['fijo'].eq('True')].copy()
revisar['fila'] = revisar.index
motivo = []
for r in revisar.itertuples():
    m = [SITIO_DUDOSO[t] for t in SITIO_DUDOSO if r.tipo_establecimiento.startswith(t[:40])]
    if TEXTO_DUDOSO.search(norm(r.horario_acceso)):
        m.append('El texto mezcla "24 horas" con otro horario')
    motivo.append('; '.join(m))
revisar['motivo_de_duda'] = motivo
revisar['vecinos_que_solo_tienen_este_de_madrugada'] = revisar['fila'].map(depende).fillna(0).round().astype(int)
revisar['de_ellos_mayores_65'] = revisar['fila'].map(depende_may).fillna(0).round().astype(int)
revisar['vecinos_a_200_m_andando'] = revisar['fila'].map(cubre).fillna(0).round().astype(int)
revisar = revisar.sort_values(['vecinos_que_solo_tienen_este_de_madrugada', 'vecinos_a_200_m_andando'], ascending=False)
cols = ['codigo_dea', 'tipo_establecimiento', 'tipo_titularidad', 'municipio_nombre', 'lon', 'lat', 'horario_acceso',
        'motivo_de_duda', 'vecinos_que_solo_tienen_este_de_madrugada', 'de_ellos_mayores_65', 'vecinos_a_200_m_andando']
revisar[cols].to_csv(ELABORADOS / '24h_a_revisar.csv', index=False)

dudosos = revisar[revisar['motivo_de_duda'] != '']
total_noche = pob[cuantos.index].sum()
print('Aparatos "24 horas" fijos:', len(revisar), '; en sitio o texto dudoso:', len(dudosos))
print('Vecinos que de madrugada dependen de un único aparato:', round(depende.sum()), 'de', round(total_noche), 'cubiertos')
print('  ...y ese aparato es un "24 horas" dudoso:', dudosos['vecinos_que_solo_tienen_este_de_madrugada'].sum())
top = revisar.head(20)
print('Los 20 primeros por revisar cubren en exclusiva a', top['vecinos_que_solo_tienen_este_de_madrugada'].sum(), 'vecinos')
print(revisar[cols[1:2] + cols[3:4] + cols[7:9]].head(12).to_string(index=False))
