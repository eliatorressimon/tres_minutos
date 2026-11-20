# Método

## 1. Horarios

El registro guarda el horario de cada desfibrilador como texto libre: "L-V 8-20 h", "lunes a jueves de 9 a 18 y viernes de 9 a 15", "horario escolar", "24 horas / 7 días a la semana"... Hay 2.331 textos distintos. `src/horarios.py` los convierte en una tabla de 7 días por 24 horas con estas reglas:

- "24 h", "24 horas", "permanente" y parecidos: abierto siempre.
- "Horario escolar": de lunes a viernes de 8:00 a 17:00.
- "Horario de oficina", "laboral", "comercial": de lunes a viernes de 9:00 a 18:00.
- Rangos de horas con o sin días: se asignan a los días que se nombran ("L-V", "sábados", "fines de semana"...). Si no se nombra ninguno y solo hay un rango, se entiende todos los días.
- "Autobús urbano" o "durante el servicio de transporte": aparato móvil, se deja fuera.
- "Según eventos", "partidos", "competiciones": solo abierto en actos, no cuenta.
- Vacío o ilegible: desconocido, no cuenta como abierto.

Un aparato solo cuenta como abierto a una hora si su horario lo dice. Por eso las cifras son un mínimo: si todos los de horario desconocido estuvieran abiertos de madrugada, la cobertura del domingo a las 3:00 subiría del 25,9 % al 56,8 %.

## 2. Población

Cada sección censal se representa por su centroide (calculado con la fórmula del área con signo). La población por sección es la del INE para 2019, que usa el mismo seccionado, reescalada para que cada municipio sume su población de 2024. En los municipios donde el INE no da datos de 2019 por sección, repartimos la población por superficie.

## 3. Cobertura

Una sección está cubierta a una hora si hay al menos un aparato abierto a menos de 200 m en línea recta de su centro. Se calcula con un árbol k-d (`scipy.spatial.cKDTree`) en coordenadas UTM, para las 168 horas de la semana.

200 m es una distancia que se puede recorrer andando rápido en unos dos minutos y medio. Ir a por el aparato y volver no debería pasar de los cinco.

## 4. Sitios nuevos

Problema de máxima cobertura: elegir k puntos que cubran a la mayor cantidad de gente. Lo resolvemos de forma voraz, eligiendo en cada paso el punto que más mayores de 65 años añade a la cobertura del domingo a las 3:00. El algoritmo voraz garantiza al menos un 1 − 1/e ≈ 63 % del óptimo. Los candidatos son, por ahora, los centros de las secciones.

## Por qué importa

- En España, la incidencia de paradas cardiacas en las que los servicios de emergencia intentan reanimar es de 24,8 por 100.000 habitantes. Aplicada a la Comunidad de Madrid, salen unas 1.700 al año.
- La ambulancia tarda de media 13,2 minutos y solo llega antes de 8 minutos en el 23,5 % de los casos.
- Sobrevive al alta el 10,8 %. Cada minuto sin desfibrilación resta en torno a un 10 % de probabilidad de sobrevivir.
- Fuentes: informe EuReCa THREE (Consejo Europeo de Resucitación, casos de 2022, presentado en octubre de 2025).
- Cuando un testigo conecta un desfibrilador antes de que llegue la ambulancia, la supervivencia mediana es del 32 % (revisión de 41 estudios: https://evidence.nihr.ac.uk/alert/use-of-public-defibrillators-linked-to-out-of-hospital-cardiac-arrest-survival/).
- En 2024 murieron en la Comunidad de Madrid 11.747 personas por enfermedades del sistema circulatorio, la segunda causa de muerte después de los tumores (Portal de Datos Abiertos, defunciones por causa de muerte).

## Límites

- Distancias en línea recta. El siguiente paso es calcularlas andando por la red de calles.
- "24 horas" no garantiza que se pueda entrar al edificio de madrugada.
- En pueblos con secciones grandes, el centro de la sección es solo una aproximación de dónde vive la gente.
- El seccionado es de 2019; las secciones creadas después no aparecen por separado.

## Próximos pasos

- Distancias andando con la red peatonal de OpenStreetMap.
- Candidatos reales para los aparatos nuevos: farmacias de guardia, gasolineras con su horario, comisarías y estaciones.
- Buscador del aparato abierto más cercano a una dirección.
- Simulador para que cada ayuntamiento pruebe dónde colocar los suyos.
