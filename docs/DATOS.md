# Datos

## Originales (`datos/originales/`)

Se descargan con `src/01_descargar.py`. No se suben al repositorio.

| Fichero | Fuente | Notas |
|---|---|---|
| `desfibriladores.csv` | Registro de desfibriladores externos fuera del ámbito sanitario, Portal de Datos Abiertos de la Comunidad de Madrid | Separador `;`, coordenadas con coma decimal. El horario (`horario_acceso`) es texto libre. |
| `secciones_censales.zip` | Secciones censales, Portal de Datos Abiertos de la Comunidad de Madrid | Shapefile del seccionado de 2019 en ETRS89 / UTM 30N. En Collado Villalba, Majadahonda y Pinto el campo `CDTSECCION` viene vacío, por eso se usa `CDGSECCION`. |
| `ine_31105.csv` | INE, Atlas de distribución de renta de los hogares, indicadores demográficos | Números con punto de miles y coma decimal. En secciones de pueblos muy pequeños el valor de 2019 es 0. |
| `oficinas_farmacia.csv` | Oficinas de farmacia, Portal de Datos Abiertos de la Comunidad de Madrid | Trae el nombre del titular; no se usa ni se guarda en los elaborados. |
| `gasolineras.json` | API REST de precios de carburantes del Ministerio para la Transición Ecológica (filtro Comunidad de Madrid, código 13) | Hay que pedirla con la cabecera `Accept: application/json`. Coordenadas con coma decimal; el horario es texto como `L-D: 24H`. |
| `centros_sanitarios.csv` | Centros, servicios y establecimientos sanitarios, Portal de Datos Abiertos de la Comunidad de Madrid | Separador `;`. Una fila por cada servicio de cada centro: se agrupa por `centro_nro_registro`. Coordenadas en ETRS89 / UTM 30N. Solo se usan los centros de salud, los consultorios de atención primaria y los hospitales generales. |
| `defunciones_causa.csv` | Defunciones por causa de muerte y sexo, Portal de Datos Abiertos de la Comunidad de Madrid | Solo se usa como contexto. |

## Elaborados (`datos/elaborados/`)

### `desfibriladores.csv`
Una fila por aparato del registro.

| Columna | Significado |
|---|---|
| `codigo_dea` | Código del aparato en el registro |
| `tipo_establecimiento`, `tipo_titularidad` | Tal y como vienen en el registro |
| `municipio_codigo`, `municipio_nombre` | Municipio (código de 3 cifras) |
| `lon`, `lat` | Coordenadas en grados (WGS84) |
| `horario_acceso` | Texto original del horario |
| `estado_horario` | `24h`, `horario` (se ha podido leer), `desconocido`, `movil` (va en un autobús) o `eventos` (solo en partidos o actos) |
| `abierto_martes_11h`, `abierto_domingo_3h` | Si consta como abierto a esa hora |
| `fijo` | Falso para los que van en autobús o no tienen coordenadas |

### `secciones.csv`
Una fila por sección censal (4.417).

| Columna | Significado |
|---|---|
| `cod_ine_seccion` | Código de 10 cifras (provincia, municipio, distrito, sección) |
| `cod_ine_muni`, `municipio` | Municipio |
| `x`, `y` | Centro de la sección en metros (ETRS89 / UTM 30N) |
| `lon`, `lat` | El mismo centro en grados |
| `poblacion` | Habitantes estimados en 2024 |
| `mayores_65` | Habitantes de 65 o más años estimados |

### `cobertura_semana.csv`
Una fila por hora de la semana (168).

| Columna | Significado |
|---|---|
| `dia`, `hora` | Día de la semana y hora de inicio |
| `aparatos_abiertos` | Aparatos fijos que constan como abiertos |
| `pct_poblacion` | % de habitantes con uno abierto a 200 m o menos en línea recta (andando, en `cobertura_variantes.csv`) |
| `pct_poblacion_fuera_capital` | Lo mismo sin contar Madrid capital |
| `pct_mayores_65` | Lo mismo para mayores de 65 |

### `cobertura_municipios.csv`
Una fila por municipio: población, % cubierto el martes a las 11:00 y el domingo a las 3:00, y si tiene algún desfibrilador fijo.

### `nuevos_sitios.csv`
Los diez puntos propuestos, en orden de elección, con los vecinos y mayores de 65 que añaden a la cobertura andando del domingo a las 3:00.

### `sitios_reales.csv`
Las diez mejores farmacias (martes 11:00) y las diez mejores gasolineras 24 h (domingo 3:00).

| Columna | Significado |
|---|---|
| `orden` | Orden de elección dentro de su grupo |
| `momento` | `martes 11:00` o `domingo 3:00` |
| `tipo` | `Farmacia` o `Gasolinera 24 h` |
| `nombre`, `direccion`, `municipio` | Rótulo y dirección del local |
| `lon`, `lat` | Coordenadas en grados |
| `vecinos_nuevos`, `mayores_65_nuevos` | Lo que añade a la cobertura, después de los anteriores |

### `sitios_reales_resumen.csv`
Qué pasaría si todos los locales de cada grupo tuvieran un aparato: número de locales, % cubierto antes y después y vecinos nuevos. Las dos últimas filas cuentan los centros de salud y hospitales, que ya tienen aparato aunque no estén en el registro.

### `distancias_calle.csv`
Una fila por pareja de sección y aparato que están a 300 m o menos andando (4.850 con el registro del 23 de noviembre).

| Columna | Significado |
|---|---|
| `cod_ine_seccion` | Sección censal |
| `fila_dea`, `codigo_dea` | Aparato: fila en `desfibriladores.csv` (un código del registro está repetido) y su código |
| `metros_linea_recta` | Distancia en línea recta entre el centro de la sección y el aparato |
| `metros_andando` | Distancia a pie por la red de calles de OpenStreetMap, más lo que hay hasta la calle desde cada punto |

### `cobertura_variantes.csv`
Una fila por hora de la semana para cada forma de medir (`medida`: `recta` o `andando`) y cada distancia (`radio_m`: 100, 200 o 300), con las mismas columnas de porcentaje que `cobertura_semana.csv`.

### `distancias_candidatos.csv`
Una fila por pareja de sitio candidato y sección que están a 200 m o menos andando (7.317 con el registro del 23 de noviembre, antes de sumar los centros sanitarios). La usan los pasos 7 y 8.

| Columna | Significado |
|---|---|
| `tipo` | `Sitio ideal` (el centro de una sección), `Farmacia`, `Gasolinera 24 h`, `Centro de salud` u `Hospital` |
| `id` | Código de la sección (sitio ideal), número de la farmacia en el registro, `lon,lat` de la gasolinera o número del centro sanitario en su registro |
| `cod_ine_seccion` | Sección que quedaría cubierta |
| `metros_andando` | Distancia a pie, calculada igual que en `distancias_calle.csv` |

### `cubiertas_andando.npy`
Matriz de 168 × 4.417 (horas de la semana por secciones) con `True` si la sección está cubierta a 200 m o menos andando. La genera el paso 6 y parten de ella los pasos 7 y 8. No se sube al repositorio.

### `municipios.csv`
Código, nombre y población de 2024 de los 179 municipios.

## Descargas (`web/descargas/`)

El paso 9 copia en `web/descargas/` los ficheros elaborados que se pueden bajar desde la pestaña Método de la web: `desfibriladores.csv`, `cobertura_semana.csv`, `cobertura_variantes.csv`, `nuevos_sitios.csv`, `sitios_reales.csv` y `sitios_reales_resumen.csv`, con las columnas descritas arriba. Además genera uno propio:

### `cobertura_municipio_hora.csv`
Una fila por municipio y hora de la semana (179 × 168), con la medida principal de la web: 200 m andando.

| Columna | Significado |
|---|---|
| `cod_ine_muni`, `municipio` | Municipio |
| `poblacion` | Habitantes estimados en 2024 |
| `dia`, `hora` | Día de la semana y hora de inicio |
| `pct_cubierto` | % de habitantes con un aparato abierto a 200 m o menos andando |
| `personas_sin_cubrir` | Habitantes sin ninguno abierto a esa distancia |
