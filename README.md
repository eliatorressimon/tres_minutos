# Tres minutos

Si alguien sufre una parada cardiaca en la calle, ¿hay un desfibrilador abierto lo bastante cerca como para llegar a tiempo? Tres minutos mide, para cada hora de la semana, qué parte de la población de la Comunidad de Madrid tiene uno a 200 metros o menos andando por la calle, y propone dónde colocar los siguientes.

**Web: https://tres-minutos.web.app**

Proyecto para **DataMad 2026**, el datathon de datos abiertos de la Comunidad de Madrid.

Autora: Elia Torres Simón.

## Qué he encontrado

Cifras con el registro descargado el 23 de noviembre de 2026. La web se actualiza cada semana, así que puede mostrar números algo distintos.

- Medido andando por la calle, que es como se llega de verdad, un martes a las 11:00 solo el 20,7 % de la población tiene un desfibrilador abierto a 200 metros o menos. Un domingo a las 3:00, el 10,4 %. Con 300 m andando, el 42,6 % y el 24,5 %.
- En línea recta saldría bastante más: el 48,6 % y el 28,2 %. La distancia andando es, en la mediana, 1,5 veces la recta.
- De los 13.651 aparatos del registro, 2.206 tienen como horario "autobús urbano": van en autobuses de Madrid capital y no cubren un barrio fijo.
- 4.521 aparatos no indican su horario o lo indican de una forma que no se puede interpretar.
- 15 municipios no tienen ningún desfibrilador fijo registrado. El mayor es El Molar, con 9.805 habitantes.
- Si cada una de las 2.954 farmacias de la Comunidad tuviera un desfibrilador, un martes a las 11:00 la cobertura andando pasaría del 20,7 % al 50,7 %: 2,1 millones de personas más. Las diez mejores ya suman 48.747, por unos 25.000 euros en cinco años contando compra y mantenimiento: unos 51 céntimos por persona (cuentas y fuentes en [docs/POR_QUE_IMPORTA.md](docs/POR_QUE_IMPORTA.md)).
- Las gasolineras abiertas 24 horas sirven de poco de madrugada: aunque las 550 tuvieran uno, la cobertura del domingo a las 3:00 solo pasaría del 10,4 % al 11,4 %, porque están en carreteras y avenidas y no donde vive la gente. Las 329 comisarías, cuarteles de la Guardia Civil y parques de bomberos de OpenStreetMap, que tienen gente de guardia toda la noche, la llevarían al 11,6 %, y todo junto al 12,5 %. Los diez mejores sitios de todos ellos suman 23.648 personas.
- De madrugada, 548.816 de las 730.421 personas con un aparato cerca dependen de uno solo. Por eso la lista de aparatos "24 horas" por comprobar (`24h_a_revisar.csv`) va ordenada por cuánta gente depende solo de cada uno. 550 de esos "24 horas" están en sitios que suelen cerrar de noche, como colegios, oficinas, tiendas grandes o polideportivos.
- El registro tiene 2.338 formas distintas de escribir el horario. Leídas y pasadas a un formato fijo, quedan 473 horarios distintos (`horarios_formato_fijo.csv`, con una columna por día y el formato `opening_hours` de OpenStreetMap).
- Diez aparatos de 24 horas en el mejor sitio posible darían cobertura de madrugada a 52.522 personas más, 11.139 de ellas mayores de 65 años.
- Los vecinos de cada sección censal se reparten entre sus casas según las viviendas de cada edificio en el Catastro. Antes se ponían todos en el centro de la sección, y en los pueblos de urbanizaciones eso escondía aparatos: 155 municipios salían con un 0 % de madrugada y ahora son 69.

Por qué importan tres minutos y 200 metros, con todas las fuentes: [docs/POR_QUE_IMPORTA.md](docs/POR_QUE_IMPORTA.md).

## La web

La web tiene tres pestañas, pensadas para tres tipos de público:

- **Emergencia.** Es la pantalla de inicio. Un botón localiza a quien lo pulsa, busca el desfibrilador abierto más cercano a esa hora, dibuja la ruta a pie y lee en voz alta la distancia. También tiene un botón para llamar al 112, un metrónomo de 110 compresiones por minuto para guiar la reanimación y un aviso a un contacto por WhatsApp o SMS con la ubicación.
- **Administraciones.** Para ayuntamientos y la Comunidad. Un mapa de los barrios sin ningún aparato abierto cerca, que cambia hora a hora durante la semana (100, 200 o 300 metros, andando o en línea recta), con la ficha de cada municipio y un informe imprimible para su ayuntamiento; un simulador para colocar un aparato en el mapa y ver cuántos vecinos gana; las diez mejores farmacias de día, los diez mejores sitios abiertos de noche (gasolineras de 24 horas, comisarías, cuarteles de la Guardia Civil y parques de bomberos) y los diez mejores puntos de madrugada para poner uno nuevo; el método y la descarga de los datos elaborados en CSV.
- **Información.** Para vecinos, familias y personas mayores, en dos partes. En "Tu calle" se toca un punto del mapa o se usa la ubicación y sale a cuántos metros andando queda el desfibrilador más cercano un martes por la mañana, un sábado por la tarde y un domingo de madrugada. También explica qué hacer si alguien se desploma y si cualquiera puede usar un desfibrilador. "Para decidir" recoge qué mirar al buscar casa o colegio, consejos para mayores y qué significa cada cosa del mapa. Tiene un botón para agrandar la letra.

## Estructura

```
datos/
  originales/     datos tal y como se descargan (no se suben; se obtienen con el paso 1)
  elaborados/     datos limpios y calculados en este proyecto (ver docs/DATOS.md)
src/              código, un fichero por paso
web/              la web: index.html, datos.json, variantes.json (otras distancias) y descargas/ (CSV para bajar)
docs/
  DATOS.md        fuentes y diccionario de cada fichero elaborado
  METODO.md       cómo se calcula todo y qué límites tiene
  POR_QUE_IMPORTA.md  contexto médico y legal, con fuentes
```

## Cómo reproducirlo

Con Python 3.9 o posterior:

```bash
python -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate
pip install -r requirements.txt

cd src
python 01_descargar.py                 # baja los datos originales
python 01b_sitios_osm.py               # comisarías, cuarteles, bomberos y estaciones de OpenStreetMap (con el mapa de Geofabrik en osrm/)
python 02_limpiar_desfibriladores.py   # limpia el registro y traduce los horarios
python viviendas_catastro.py           # viviendas de cada edificio, del Catastro (solo la primera vez)
python 03_poblacion_secciones.py       # centro y población de cada sección censal
python 03b_puntos_de_poblacion.py      # reparte los vecinos de cada sección entre sus viviendas
python 04_cobertura.py                 # cobertura en las 168 horas de la semana
python 05_distancias_calle.py          # distancias andando por la calle (unas 550 peticiones a OSRM; las ya hechas se guardan)
python 06_cobertura_calle.py           # cobertura con 100, 200 y 300 m, en línea recta y andando
python 07_nuevos_sitios.py             # los diez mejores sitios posibles para aparatos de 24 h
python 08_sitios_reales.py             # las diez mejores farmacias y los diez mejores sitios abiertos de noche
python 08b_revisar_horarios.py         # horarios en formato fijo y aparatos 24 h por comprobar
python 09_exportar_web.py              # genera web/datos.json
```

Para ver la web en local:

```bash
cd web
python -m http.server 8000
```

y abrir `http://localhost:8000` en el navegador.

## Actualización automática

Cada lunes por la mañana, GitHub Actions (`.github/workflows/actualizar.yml`) vuelve a descargar los datos abiertos, ejecuta los pasos 1 a 9 y comprueba que los números tienen sentido (`src/comprobar.py`). Si el registro de desfibriladores, las farmacias o las gasolineras han cambiado, guarda los datos nuevos en el repositorio y publica la web otra vez. Si una descarga falla, o si una cifra cambia de golpe respecto a la semana anterior (más de 5 puntos de cobertura o más de un 20 % de aparatos), se para y la web se queda como estaba. Si el cambio es a propósito, se puede lanzar a mano marcando la opción de forzar. La única excepción son las gasolineras: el servicio del Ministerio a veces no responde desde fuera de España, y como cambian muy poco se usa la última copia buena, guardada en `datos/respaldo/`. También se puede lanzar a mano desde la pestaña Actions.

## Publicar la web

La web es estática (`web/index.html` y `web/datos.json`) y se publica con Firebase Hosting:

```bash
npm install -g firebase-tools
firebase login
firebase use --add            # elegir el proyecto creado en la consola de Firebase
firebase deploy --only hosting
```

## Datos

| Conjunto | Organismo | Uso |
|---|---|---|
| [Desfibriladores externos fuera del ámbito sanitario](https://datos.comunidad.madrid/dataset/desfibriladores_externos_fuera_ambito_sanitario) | Comunidad de Madrid | Ubicación, tipo y horario de cada aparato |
| [Secciones censales](https://datos.comunidad.madrid/dataset/secciones_censales) | Comunidad de Madrid | Dónde vive la gente |
| [Defunciones por causa de muerte y sexo. Municipios](https://datos.comunidad.madrid/dataset/defunciones_por_causa_y_sexo) | Comunidad de Madrid | Contexto: muertes por enfermedades del sistema circulatorio |
| [Oficinas de farmacia](https://datos.comunidad.madrid/dataset/oficinas_farmacia) | Comunidad de Madrid | Farmacias como sitios candidatos de día |
| [Centros, servicios y establecimientos sanitarios](https://datos.comunidad.madrid/dataset/centros_servicios_establecimientos_sanitarios) | Comunidad de Madrid | Centros de salud y hospitales, que tienen desfibrilador aunque no estén en el registro |
| [Precios de carburantes en estaciones de servicio (API REST)](https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/help) | Ministerio para la Transición Ecológica | Gasolineras con horario de 24 horas como sitios candidatos de noche |
| [OpenStreetMap](https://www.openstreetmap.org) (copia de [Geofabrik](https://download.geofabrik.de/europe/spain/madrid.html)) | Colaboradores de OpenStreetMap | Red de calles para las distancias a pie; comisarías, cuarteles de la Guardia Civil, parques de bomberos y estaciones como sitios candidatos |
| [Indicadores demográficos por sección censal (tabla 31105)](https://www.ine.es/jaxiT3/Tabla.htm?t=31105) | INE | Población y porcentaje de mayores de 65 por sección |
| [Edificios (servicio INSPIRE)](https://www.catastro.hacienda.gob.es/webinspire/index.html) | Dirección General del Catastro | Número de viviendas de cada edificio, para repartir a los vecinos dentro de cada sección |

Las cifras sobre paradas cardiacas (incidencia, tiempos de llegada de la ambulancia, supervivencia) vienen del informe EuReCa THREE del Consejo Europeo de Resucitación y de una revisión de 41 estudios sobre desfibriladores usados por testigos. Están citadas, con enlaces, en [docs/POR_QUE_IMPORTA.md](docs/POR_QUE_IMPORTA.md).

## Herramientas

Python con pandas, NumPy y SciPy (búsquedas por cercanía con `cKDTree`), pyproj (cambio de coordenadas), pyshp y Shapely (lectura del shapefile y contornos municipales) y requests (descargas). Las distancias andando se piden al servidor OSRM de routing.openstreetmap.de, que usa la red de calles de OpenStreetMap. La web es un único HTML: MapLibre GL con el mapa base de OpenFreeMap (datos de OpenStreetMap) y deck.gl para las columnas en 3D. Las direcciones de los aparatos, que el registro no publica, se buscan desde la web con Nominatim (OpenStreetMap).

## Licencia

El código se publica con licencia MIT. Los datos de origen mantienen la licencia de cada organismo, que permite su reutilización citando la fuente.

Herramienta no oficial, sin relación con la Comunidad de Madrid.
