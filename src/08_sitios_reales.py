"""Paso 8. Los diez mejores sitios REALES para un aparato nuevo.

El paso 7 busca puntos ideales del mapa. Aquí solo valen locales que ya existen y que tienen sentido:
  - De noche (domingo a las 3:00): gasolineras abiertas las 24 horas, según su horario en el Ministerio.
  - De día (martes a las 11:00): farmacias, que abren de día en casi todos los barrios.
Mismo método voraz que el paso 7, también andando por la calle: en cada paso elegimos el local que más
vecinos sin cubrir gana, contando dos veces a los mayores de 65, y repetimos con los que quedan.
También calculamos qué pasaría si TODAS las gasolineras de 24 horas, o todas las farmacias, tuvieran uno.
Salidas: datos/elaborados/sitios_reales.csv y datos/elaborados/sitios_reales_resumen.csv
"""
import numpy as np
import pandas as pd
from config import ELABORADOS, NUEVOS_APARATOS
from candidatos import farmacias, gasolineras_24h, secciones_a_pie

sec = pd.read_csv(ELABORADOS / 'secciones.csv', dtype={'cod_ine_seccion': str, 'cod_ine_muni': str})
cubiertas_semana = np.load(ELABORADOS / 'cubiertas_andando.npy')
pob, p65 = sec['poblacion'].fillna(0).values, sec['mayores_65'].fillna(0).values
peso = pob + p65                       # los mayores de 65 cuentan doble


def elegir(locales, hora, cuantos):
    cubiertas = cubiertas_semana[hora].copy()
    a_pie = secciones_a_pie(locales['tipo'].iloc[0], sec)
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
    for c in secciones_a_pie(locales['tipo'].iloc[0], sec).values():
        cubiertas[c] = True
    antes = pob[cubiertas_semana[hora]].sum() / pob.sum()
    return {'locales': len(locales), 'pct_antes': round(100 * antes, 1), 'pct_despues': round(100 * pob[cubiertas].sum() / pob.sum(), 1),
            'vecinos_nuevos': round(pob[cubiertas].sum() - pob[cubiertas_semana[hora]].sum())}


gas, farm = gasolineras_24h(), farmacias()
res = pd.DataFrame(elegir(gas, 147, NUEVOS_APARATOS) + elegir(farm, 35, NUEVOS_APARATOS))
res.to_csv(ELABORADOS / 'sitios_reales.csv', index=False)
resumen = pd.DataFrame([{'caso': 'Todas las gasolineras 24 h, domingo 3:00', **si_todos(gas, 147)},
                        {'caso': 'Todas las farmacias, martes 11:00', **si_todos(farm, 35)}])
resumen.to_csv(ELABORADOS / 'sitios_reales_resumen.csv', index=False)
print(res[['orden', 'momento', 'tipo', 'nombre', 'municipio', 'vecinos_nuevos', 'mayores_65_nuevos']].to_string(index=False))
print(resumen.to_string(index=False))
