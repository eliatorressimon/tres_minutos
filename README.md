# Tres minutos

Si alguien sufre una parada cardiaca en la calle, ¿hay un desfibrilador abierto lo bastante cerca como para llegar a tiempo? Tres minutos mide, para cada hora de la semana, qué parte de la población de la Comunidad de Madrid tiene uno a menos de 200 metros, y propone dónde colocar los siguientes.

Proyecto para **DataMad 2026**, el datathon de datos abiertos de la Comunidad de Madrid.

Equipo: Elia Torres Simón y Clara Juarros.

## Qué hemos encontrado

- Un martes a las 11:00, el 45,2 % de la población tiene un desfibrilador abierto a menos de 200 m. Un domingo a las 3:00, el 25,9 %. Fuera de Madrid capital, la cifra pasa del 30,7 % al 13,4 %.
- De los 13.673 aparatos del registro, 2.206 tienen como horario "autobús urbano": van en autobuses de Madrid capital y no cubren un barrio fijo.
- 4.543 aparatos no indican su horario o lo indican de una forma que no se puede interpretar.
- 15 municipios no tienen ningún desfibrilador fijo registrado. El mayor es El Molar, con 9.805 habitantes.
- Diez aparatos de 24 horas bien colocados darían cobertura de madrugada a unas 86.440 personas más, 20.820 de ellas mayores de 65 años.
- Si cada una de las 2.954 farmacias de la Comunidad tuviera un desfibrilador, un martes a las 11:00 la cobertura pasaría del 45,2 % al 71,6 %: 1,84 millones de personas más.
- Las gasolineras abiertas 24 horas sirven de poco de madrugada: aunque las 550 tuvieran uno, la cobertura del domingo a las 3:00 solo pasaría del 25,9 % al 28,4 %, porque están en carreteras y avenidas y no donde vive la gente.

## Estructura

```
datos/
  originales/     datos tal y como se descargan (no se suben; se obtienen con el paso 1)
  elaborados/     datos limpios y calculados por nosotros (ver docs/DATOS.md)
src/              código, un fichero por paso
web/              la web: index.html y datos.json
docs/
  DATOS.md        fuentes y diccionario de cada fichero elaborado
  METODO.md       cómo se calcula todo y qué límites tiene
```

## Cómo reproducirlo

Con Python 3.10 o posterior:

```bash
python -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate
pip install -r requirements.txt

cd src
python 01_descargar.py                 # baja los datos originales
python 02_limpiar_desfibriladores.py   # limpia el registro y traduce los horarios
python 03_poblacion_secciones.py       # centro y población de cada sección censal
python 04_cobertura.py                 # cobertura en las 168 horas de la semana
python 05_nuevos_sitios.py             # dónde poner los próximos aparatos
python 07_sitios_reales.py             # las mejores farmacias y gasolineras 24 h
python 06_exportar_web.py              # genera web/datos.json
```

Para ver la web en local:

```bash
cd web
python -m http.server 8000
```

y abrir `http://localhost:8000` en el navegador.

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
| [Precios de carburantes en estaciones de servicio (API REST)](https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/help) | Ministerio para la Transición Ecológica | Gasolineras con horario de 24 horas como sitios candidatos de noche |
| [Indicadores demográficos por sección censal (tabla 31105)](https://www.ine.es/jaxiT3/Tabla.htm?t=31105) | INE | Población y porcentaje de mayores de 65 por sección |

Las cifras sobre paradas cardiacas (incidencia, tiempos de llegada de la ambulancia, supervivencia) vienen del informe EuReCa THREE del Consejo Europeo de Resucitación y de una revisión de 41 estudios sobre desfibriladores usados por testigos. Están citadas en `docs/METODO.md`.

## Herramientas

Python con pandas, NumPy y SciPy (búsquedas por cercanía con `cKDTree`), pyproj (cambio de coordenadas), pyshp y Shapely (lectura del shapefile y contornos municipales) y requests (descargas). La web es un único HTML: MapLibre GL con el mapa base de OpenFreeMap (datos de OpenStreetMap) y deck.gl para las columnas en 3D. Las fotos de cada municipio se piden a Wikipedia al abrir su ficha.

## Licencia

El código se publica con licencia MIT. Los datos de origen mantienen la licencia de cada organismo, que permite su reutilización citando la fuente.

Herramienta no oficial, sin relación con la Comunidad de Madrid.
