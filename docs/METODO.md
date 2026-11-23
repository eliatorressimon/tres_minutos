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

Un aparato solo cuenta como abierto a una hora si su horario lo dice. Por eso las cifras son un mínimo: si todos los de horario desconocido estuvieran abiertos de madrugada, la cobertura en línea recta del domingo a las 3:00 subiría del 25,9 % al 56,6 % (lo calcula `src/04_cobertura.py`).

## 2. Población

Cada sección censal se representa por su centroide (calculado con la fórmula del área con signo). La población por sección es la del INE para 2019, que usa el mismo seccionado, reescalada para que cada municipio sume su población de 2024. En los municipios donde el INE no da datos de 2019 por sección, la población se reparte por superficie.

## 3. Cobertura

Una sección está cubierta a una hora si hay al menos un aparato abierto a 200 m o menos de su centro. Primero se calcula en línea recta, con un árbol k-d (`scipy.spatial.cKDTree`) en coordenadas UTM, para las 168 horas de la semana (`src/04_cobertura.py`). Después se repite andando por la calle (apartado 6), que es la medida que usa la web por defecto.

Ir y volver 400 m a paso rápido cabe en unos tres minutos. Por qué tres minutos, con las fuentes: [POR_QUE_IMPORTA.md](POR_QUE_IMPORTA.md).

## 4. Sitios nuevos

Problema de máxima cobertura: elegir k puntos que cubran a la mayor cantidad de gente. Lo resuelvo de forma voraz, eligiendo en cada paso el punto que más añade a la cobertura andando del domingo a las 3:00 (`src/07_nuevos_sitios.py`). Cada vecino cuenta uno y los mayores de 65 cuentan doble (peso = población + mayores de 65). El algoritmo voraz garantiza al menos un 1 − 1/e ≈ 63 % del óptimo. Los candidatos son los centros de las secciones: es el "sitio ideal", sin mirar si allí hay un local donde ponerlo. Un sitio cubre las secciones a 200 m o menos andando. Los diez mejores suman 54.195 vecinos, 9.892 de ellos mayores de 65.

## 5. Sitios reales

`src/08_sitios_reales.py` repite la elección voraz, con el mismo peso, pero solo entre locales que existen:

- De día (martes a las 11:00): las 2.954 oficinas de farmacia del registro de la Comunidad.
- De madrugada (domingo a las 3:00): las 550 gasolineras cuyo horario en la API del Ministerio es `L-D: 24H` o `L-D: 00:00-23:59`.

Para cada grupo se eligen los diez mejores y se calcula también qué pasaría si todos los locales tuvieran uno. Las distancias de cada local a las secciones se miden andando (apartado 6). Con todas las farmacias, la cobertura del martes a las 11:00 pasaría del 20,7 % al 45,7 %. Con todas las gasolineras de 24 horas, la del domingo a las 3:00 solo pasaría del 9,6 % al 10,4 %.

## 6. Andando por la calle

En línea recta, 200 m pueden ser mucho más andando: hay que rodear manzanas, cruzar por un paso de peatones o buscar el puente sobre una vía. `src/05_distancias_calle.py` toma cada pareja de sección y aparato (fijo y con horario conocido) que está a 300 m o menos en línea recta, unas 13.600, y pide su distancia a pie por la red de calles y caminos de OpenStreetMap al servidor OSRM de routing.openstreetmap.de (servicio `table`, perfil a pie). A esa distancia se le suma lo que hay desde el centro de la sección y desde el aparato hasta la calle más cercana. Se agrupan secciones vecinas para hacer unas 90 peticiones de 100 puntos como mucho. El mismo script mide también, andando, qué secciones quedan a 200 m o menos de cada sitio candidato: el centro de cada sección, cada farmacia y cada gasolinera de 24 horas (unas 120 peticiones más).

Solo 4.850 parejas quedan a 300 m o menos andando. La mediana de la distancia andando es 1,5 veces la distancia en línea recta.

`src/06_cobertura_calle.py` repite el cálculo de cobertura con 100, 200 y 300 m, en línea recta y andando:

| | 100 m | 200 m | 300 m |
|---|---|---|---|
| Martes 11:00, línea recta | 17,7 % | 45,5 % | 66,3 % |
| Martes 11:00, andando | 5,1 % | 20,7 % | 38,7 % |
| Domingo 3:00, línea recta | 7,9 % | 25,9 % | 42,7 % |
| Domingo 3:00, andando | 2,0 % | 9,6 % | 22,2 % |

Los sitios propuestos (pasos 7 y 8) se calculan andando con 200 m.

## 7. Pantalla de emergencia

La pantalla de inicio de la web es para una emergencia. Al pulsar el botón grande pide la ubicación del móvil, busca los tres aparatos abiertos más cercanos a un punto (la ubicación del móvil o un punto del mapa), pide la ruta a pie de cada uno al servidor OSRM de routing.openstreetmap.de y se queda con la más corta. Calcula el tiempo de ida y vuelta corriendo (2,8 m/s) y andando (1,35 m/s). Si el servidor no responde, usa la línea recta. Enseña la ruta en un mapa, la distancia y si el aparato está abierto ahora, y lo dice en voz alta con la síntesis de voz del navegador. También tiene un botón para llamar al 112, un metrónomo de 110 compresiones por minuto para guiar la reanimación y un botón para avisar a un contacto por WhatsApp o SMS con la ubicación. El contacto se guarda solo en el navegador de quien lo usa.

## Límites

- La distancia andando depende de OpenStreetMap y de un servidor público de rutas; si una calle está mal dibujada, la distancia sale mal.
- Andando, el punto de partida es el centro de la sección. En una manzana cerrada ese centro cae dentro de los edificios, y lo que hay hasta la calle se suma a la distancia. Para quien vive en la fachada, la distancia real es algo menor.
- OpenStreetMap no recoge todos los pasos interiores, como patios o galerías comerciales.
- "24 horas" no garantiza que se pueda entrar al edificio de madrugada.
- En pueblos con secciones grandes, el centro de la sección es solo una aproximación de dónde vive la gente.
- El seccionado es de 2019; las secciones creadas después no aparecen por separado.

## Próximos pasos

- Que el registro recoja el horario en un formato fijo (días y horas por separado). Hoy un tercio de los aparatos no tiene un horario que se pueda leer.
- Comprobar sobre el terreno si los aparatos "24 horas" son accesibles de madrugada o están dentro de un edificio cerrado.
- Más candidatos reales: farmacias de guardia, comisarías y estaciones.
