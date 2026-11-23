# Método

## 1. Horarios

El registro guarda el horario de cada desfibrilador como texto libre: "L-V 8-20 h", "lunes a jueves de 9 a 18 y viernes de 9 a 15", "horario escolar", "24 horas / 7 días a la semana"... Hay 2.336 textos distintos. `src/horarios.py` los convierte en una tabla de 7 días por 24 horas con estas reglas:

- "24 h", "24 horas", "permanente" y parecidos: abierto siempre.
- "Horario escolar": de lunes a viernes de 8:00 a 17:00.
- "Horario de oficina", "laboral", "comercial": de lunes a viernes de 9:00 a 18:00.
- Rangos de horas con o sin días: se asignan a los días que se nombran, ya sean rangos ("L-V", "martes a sábado") o días sueltos con su abreviatura ("S 9-14", "D: 10-15", "sábados"). Si no se nombra ninguno y solo hay un rango, se entiende todos los días.
- "Autobús urbano" o "durante el servicio de transporte": aparato móvil, se deja fuera.
- "Según eventos", "partidos", "competiciones": solo abierto en actos, no cuenta.
- Vacío o ilegible: desconocido, no cuenta como abierto.

Revisando la tabla de "L-V 8:00-15:00 / S 9-14" vi que el sábado salía vacío: las abreviaturas de una letra sueltas ("S", "D") no se reconocían, y "S y D" se partía en dos. Al arreglarlo cambiaron las tablas de unos 270 aparatos, sobre todo en fin de semana. La cobertura del martes a las 11:00 en línea recta subió unas décimas, hasta el 45,6 % con el registro de entonces, y la del domingo a las 3:00 no cambió.

Un aparato solo cuenta como abierto a una hora si su horario lo dice. Por eso las cifras son un mínimo: si todos los de horario desconocido estuvieran abiertos de madrugada, la cobertura en línea recta del domingo a las 3:00 subiría del 28,2 % al 61,6 % (lo calcula `src/04_cobertura.py`).

## 2. Población

La población por sección censal es la del INE para 2019, que usa el mismo seccionado, reescalada para que cada municipio sume su población de 2024. En los municipios donde el INE no da datos de 2019 por sección, la población se reparte por superficie.

Dentro de cada sección, la población se reparte entre sus edificios según el número de viviendas que tienen en el Catastro (servicio INSPIRE de edificios, `src/viviendas_catastro.py`, unos 497.000 edificios con vivienda). Al principio todos los vecinos de una sección se ponían en su centro. En Madrid capital, donde una sección es poco más que una manzana, eso apenas cambia nada. Pero en un pueblo de urbanizaciones una sección mide varios kilómetros: en Valdemorillo, por ejemplo, 14.000 vecinos estaban en solo cinco puntos y ninguno de sus ocho aparatos de 24 horas quedaba a menos de 600 m de ellos.

Ahora (`src/03b_puntos_de_poblacion.py`), si todas las viviendas de una sección están a 150 m o menos de su centro, la sección sigue siendo un solo punto, colocado en el centro de sus viviendas. Si no, sus edificios se agrupan en cuadrados de 150 m y cada cuadrado es un punto con su parte de los vecinos. Las secciones sin viviendas en el Catastro se quedan en su centro geométrico. Salen 42.982 puntos de población. Los mayores de 65 se reparten igual.

## 3. Cobertura

Un punto de población está cubierto a una hora si hay al menos un aparato abierto a 200 m o menos. Primero se calcula en línea recta, con un árbol k-d (`scipy.spatial.cKDTree`) en coordenadas UTM, para las 168 horas de la semana (`src/04_cobertura.py`). Después se repite andando por la calle (apartado 6), que es la medida que usa la web por defecto.

Ir y volver 400 m a paso rápido cabe en unos tres minutos. Por qué tres minutos, con las fuentes: [POR_QUE_IMPORTA.md](POR_QUE_IMPORTA.md).

## 4. Sitios nuevos

Problema de máxima cobertura: elegir k puntos que cubran a la mayor cantidad de gente. Lo resuelvo de forma voraz, eligiendo en cada paso el punto que más añade a la cobertura andando del domingo a las 3:00 (`src/07_nuevos_sitios.py`). Cada vecino cuenta uno y los mayores de 65 cuentan doble (peso = población + mayores de 65). El algoritmo voraz garantiza al menos un 1 − 1/e ≈ 63 % del óptimo. Los candidatos son los centros de las viviendas de cada sección: es el "sitio ideal", sin mirar si allí hay un local donde ponerlo. Un sitio cubre los puntos de población a 200 m o menos andando. Los diez mejores suman 52.522 vecinos, 11.139 de ellos mayores de 65.

## 5. Sitios reales

`src/08_sitios_reales.py` repite la elección voraz, con el mismo peso, pero solo entre locales que existen:

- De día (martes a las 11:00): las 2.954 oficinas de farmacia del registro de la Comunidad.
- De madrugada (domingo a las 3:00): las 550 gasolineras cuyo horario en la API del Ministerio es `L-D: 24H` o `L-D: 00:00-23:59`.

Para cada grupo se eligen los diez mejores y se calcula también qué pasaría si todos los locales tuvieran uno. Las distancias de cada local a los puntos de población se miden andando (apartado 6). Con todas las farmacias, la cobertura del martes a las 11:00 pasaría del 20,7 % al 50,7 %. Con todas las gasolineras de 24 horas, la del domingo a las 3:00 solo pasaría del 10,4 % al 11,4 %.

Los centros sanitarios no están en el registro, que solo recoge los aparatos de fuera del ámbito sanitario, pero tienen el suyo. `src/08_sitios_reales.py` calcula también cuánto subiría la cobertura si se contaran: los centros de salud y consultorios de atención primaria, de lunes a viernes de 8:00 a 21:00, y los hospitales generales, con urgencias las 24 horas. El horario no viene en los datos; es el habitual de estos centros en la Comunidad. La web lo enseña aparte y no lo mezcla con el mapa principal, que usa solo el registro.

## 6. Andando por la calle

En línea recta, 200 m pueden ser mucho más andando: hay que rodear manzanas, cruzar por un paso de peatones o buscar el puente sobre una vía. `src/05_distancias_calle.py` toma cada pareja de punto de población y aparato (fijo y con horario conocido) que está a 300 m o menos en línea recta, y pide su distancia a pie por la red de calles y caminos de OpenStreetMap a un servidor de rutas OSRM (servicio `table`, perfil a pie). En GitHub Actions se monta un OSRM propio con el mapa de la Comunidad de Madrid de Geofabrik, para no cargar el servidor público de routing.openstreetmap.de (que se usa si se ejecuta en otro sitio). A esa distancia se le suma lo que hay desde el punto y desde el aparato hasta la calle más cercana. Se agrupan puntos vecinos para hacer unas 230 peticiones de 100 puntos como mucho. El mismo script mide también, andando, qué puntos de población quedan a 200 m o menos de cada sitio candidato: el centro de las viviendas de cada sección, cada farmacia, cada gasolinera de 24 horas y cada centro sanitario (unas 320 peticiones más). Las distancias ya calculadas se guardan en `datos/respaldo/rutas_a_pie.csv.gz` y no se vuelven a pedir.

Quedan 20.998 parejas a 300 m o menos andando. La mediana de la distancia andando es 1,5 veces la distancia en línea recta.

`src/06_cobertura_calle.py` repite el cálculo de cobertura con 100, 200 y 300 m, en línea recta y andando:

| | 100 m | 200 m | 300 m |
|---|---|---|---|
| Martes 11:00, línea recta | 17,2 % | 48,6 % | 71,0 % |
| Martes 11:00, andando | 4,4 % | 20,7 % | 42,6 % |
| Domingo 3:00, línea recta | 8,6 % | 28,2 % | 46,2 % |
| Domingo 3:00, andando | 2,0 % | 10,4 % | 24,5 % |

Los sitios propuestos (pasos 7 y 8) se calculan andando con 200 m.

## 7. Pantalla de emergencia

La pantalla de inicio de la web es para una emergencia. Al pulsar el botón grande pide la ubicación del móvil, busca los tres aparatos abiertos más cercanos a un punto (la ubicación del móvil o un punto del mapa), pide la ruta a pie de cada uno al servidor OSRM de routing.openstreetmap.de y se queda con la más corta. Calcula el tiempo de ida y vuelta corriendo (2,8 m/s) y andando (1,35 m/s). Si el servidor no responde, usa la línea recta. Enseña la ruta en un mapa, la distancia y si el aparato está abierto ahora, y lo dice en voz alta con la síntesis de voz del navegador. También tiene un botón para llamar al 112, un metrónomo de 110 compresiones por minuto para guiar la reanimación y un botón para avisar a un contacto por WhatsApp o SMS con la ubicación. El contacto se guarda solo en el navegador de quien lo usa.

## Límites

- La distancia andando depende de OpenStreetMap y de un servidor público de rutas; si una calle está mal dibujada, la distancia sale mal.
- Andando, el punto de partida es el centro de las viviendas de cada punto. En una manzana cerrada ese centro cae dentro de los edificios, y lo que hay hasta la calle se suma a la distancia. Para quien vive en la fachada, la distancia real es algo menor.
- OpenStreetMap no recoge todos los pasos interiores, como patios o galerías comerciales.
- "24 horas" no garantiza que se pueda entrar al edificio de madrugada.
- Dentro de cada sección se supone que todas las viviendas tienen el mismo número de vecinos, y que las viviendas vacías o de segunda residencia se reparten igual por toda la sección. Cada punto agrupa las casas de un cuadrado de 150 m, así que puede haber hasta unos 100 m de diferencia con la casa de cada vecino.
- El seccionado es de 2019; las secciones creadas después no aparecen por separado.

## Próximos pasos

- Que el registro recoja el horario en un formato fijo (días y horas por separado). Hoy un tercio de los aparatos no tiene un horario que se pueda leer.
- Comprobar sobre el terreno si los aparatos "24 horas" son accesibles de madrugada o están dentro de un edificio cerrado.
- Más candidatos reales: farmacias de guardia, comisarías y estaciones.
