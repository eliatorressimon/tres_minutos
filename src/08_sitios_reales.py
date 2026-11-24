"""Paso 8. Los diez mejores sitios REALES para un aparato nuevo.

El paso 7 busca puntos ideales del mapa. Aquí solo valen locales que ya existen y que tienen sentido:
  - De noche (domingo a las 3:00): gasolineras abiertas las 24 horas, según su horario en el Ministerio, y
    comisarías, cuarteles de la Guardia Civil y parques de bomberos de OpenStreetMap, que tienen gente de
    guardia toda la noche (paso 1b).
  - De día (martes a las 11:00): farmacias, que abren de día en casi todos los barrios.
Mismo método voraz que el paso 7, también andando por la calle: en cada paso elegimos el local que más
vecinos sin cubrir gana, contando dos veces a los mayores de 65, y repetimos con los que quedan.
También calculamos qué pasaría si TODAS las gasolineras de 24 horas, todas las comisarías y parques de bomberos,
todas las farmacias o todas las estaciones de metro y tren tuvieran uno.
Y cuánto sube la cobertura si se cuentan los centros de salud y hospitales: tienen desfibrilador, pero el
registro no los recoge porque solo incluye los que están fuera del ámbito sanitario.
Salidas: datos/elaborados/sitios_reales.csv y datos/elaborados/sitios_reales_resumen.csv
"""
import numpy as np
import pandas as pd
from config import ELABORADOS, NUEVOS_APARATOS
from candidatos import farmacias, gasolineras_24h, centros_sanitarios, secciones_a_pie, sitios_osm, DE_NOCHE, ESTACIONES

sec = pd.read_csv(ELABORADOS / 'puntos.csv', dtype={'punto': str, 'cod_ine_seccion': str, 'cod_ine_muni': str})
cubiertas_semana = np.load(ELABORADOS / 'cubiertas_andando.npy')
pob, p65 = sec['poblacion'].fillna(0).values, sec['mayores_65'].fillna(0).values
peso = pob + p65                       # los mayores de 65 cuentan doble


def elegir(locales, hora, cuantos):
    cubiertas = cubiertas_semana[hora].copy()
    a_pie = secciones_a_pie(locales['tipo'].unique(), sec)
    cerca = [a_pie.get(i, []) for i in locales['id']]
    filas = []
    for k in range(cuantos):
        ganancia = np.array([peso[[i for i in c if not cubiertas[i]]].sum() for c in cerca])
        mejor = int(ganancia.argmax())
        nuevas = [i for i in cerca[mejor] if not cubiertas[i]]
        cubiertas[nuevas] = True
        fila = locales.iloc[mejor]
        filas.append({'orden': k + 1, 'momento': 'domingo 3:00' if hora == 147 else 'martes 11:00', **fila.drop('id').to_dict(),
                      'vecinos_nuevos': round(pob[nuevas].sum()), 'mayores_65_nuevos': round(p65[nuevas].sum())})
    return filas


def si_todos(locales, hora):
    cubiertas = cubiertas_semana[hora].copy()
    for tipo in locales['tipo'].unique():
        a_pie = secciones_a_pie(tipo, sec)
        for i in locales.loc[locales['tipo'] == tipo, 'id']:
            cubiertas[a_pie.get(i, [])] = True
    antes = pob[cubiertas_semana[hora]].sum() / pob.sum()
    return {'locales': len(locales), 'pct_antes': round(100 * antes, 1), 'pct_despues': round(100 * pob[cubiertas].sum() / pob.sum(), 1),
            'vecinos_nuevos': round(pob[cubiertas].sum() - pob[cubiertas_semana[hora]].sum())}


gas, farm, sani = gasolineras_24h(), farmacias(), centros_sanitarios()
guardia, estaciones = sitios_osm(DE_NOCHE), sitios_osm(ESTACIONES)
noche = pd.concat([gas, guardia], ignore_index=True)
res = pd.DataFrame(elegir(noche, 147, NUEVOS_APARATOS) + elegir(farm, 35, NUEVOS_APARATOS))
res.to_csv(ELABORADOS / 'sitios_reales.csv', index=False)
resumen = pd.DataFrame([{'caso': 'Todas las gasolineras 24 h, domingo 3:00', **si_todos(gas, 147)},
                        {'caso': 'Todas las comisarías, cuarteles y parques de bomberos, domingo 3:00', **si_todos(guardia, 147)},
                        {'caso': 'Gasolineras 24 h, comisarías, cuarteles y bomberos juntos, domingo 3:00', **si_todos(noche, 147)},
                        {'caso': 'Todas las farmacias, martes 11:00', **si_todos(farm, 35)},
                        {'caso': 'Todas las estaciones de metro y tren, martes 11:00', **si_todos(estaciones, 35)},
                        {'caso': 'Contando centros de salud y hospitales, martes 11:00', **si_todos(sani, 35)},
                        {'caso': 'Contando hospitales, domingo 3:00', **si_todos(sani[sani['tipo'] == 'Hospital'], 147)}])
resumen.to_csv(ELABORADOS / 'sitios_reales_resumen.csv', index=False)
print(res[['orden', 'momento', 'tipo', 'nombre', 'municipio', 'vecinos_nuevos', 'mayores_65_nuevos']].to_string(index=False))
print(resumen.to_string(index=False))
