"""Comprobación antes de publicar: si una descarga ha salido mal (portal caído, fichero vacío o
cortado), los números se van a cero o se disparan. En ese caso paramos y no se publica nada."""
import json
import sys
import pandas as pd
from config import ELABORADOS, WEB

problemas = []
dea = pd.read_csv(ELABORADOS / 'desfibriladores.csv', dtype=str)
if len(dea) < 10000:
    problemas.append(f'solo hay {len(dea)} desfibriladores en el registro (se esperaban más de 10.000)')
sec = pd.read_csv(ELABORADOS / 'secciones.csv', dtype=str)
if len(sec) < 4000:
    problemas.append(f'solo hay {len(sec)} secciones censales')
datos = json.loads((WEB / 'datos.json').read_text(encoding='utf-8'))
if not datos:
    problemas.append('web/datos.json está vacío')

if problemas:
    print('No se publica:')
    for p in problemas:
        print(' -', p)
    sys.exit(1)
print('Todo en orden:', len(dea), 'desfibriladores y', len(sec), 'secciones.')
