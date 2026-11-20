"""Traduce el horario escrito a mano de cada desfibrilador a una tabla de 7 días x 24 horas.

parse(texto) devuelve (estado, tabla):
  estado: '24h', 'horario', 'desconocido', 'movil' (va en un autobús) o 'eventos' (solo en partidos o actos)
  tabla:  matriz booleana 7x24 (fila 0 = lunes, columna 0 = de 0:00 a 1:00), o None si no se sabe
"""
import re, unicodedata
import numpy as np

DIAS = {'l':0,'lu':0,'lun':0,'lunes':0,'m':1,'ma':1,'mar':1,'martes':1,'x':2,'mi':2,'mie':2,'miercoles':2,
        'j':3,'ju':3,'jue':3,'jueves':3,'v':4,'vi':4,'vie':4,'viernes':4,'s':5,'sa':5,'sab':5,'sabado':5,'sabados':5,
        'd':6,'do':6,'dom':6,'domingo':6,'domingos':6,'vier':4,'sabad':5}

def norm(s):
    s = s.replace('\u2013','-').replace('\u2014','-').replace('?','-')
    s = unicodedata.normalize('NFKD', s.lower()).encode('ascii','ignore').decode()
    s = s.replace('l/v','l-v').replace('l/d','l-d').replace('l/s','l-s').replace('l/j','l-j')
    return re.sub(r'\s+',' ', s).strip()

HORA = r'(\d{1,2})(?:[:\.,h]\s?(\d{2}))?\s*(?:h|hs|horas|hrs)?\.?'
RANGO = re.compile(r'(?:de\s*|entre\s*)?' + HORA + r'\s*(?:am|de la manana)?\s*(?:a|-|hasta|y las|y|al?|\s)\s*(?:las\s*)?' + HORA)

def rangos(txt):
    out=[]
    for m in RANGO.finditer(txt):
        h1=int(m.group(1)); m1=int(m.group(2) or 0); h2=int(m.group(3)); m2=int(m.group(4) or 0)
        if h1>24 or h2>24 or m1>59 or m2>59: continue
        a=h1+m1/60; b=h2+m2/60
        if b==0: b=24
        out.append((a,b))
    return out

DIA = r'(lunes|martes|miercoles|jueves|viernes|sabados?|domingos?|vier|sabad|lun|mar|mie|jue|vie|sab|dom|lu|ma|mi|ju|vi|sa|do|l|m|x|j|v|s|d)'
# un día suelto de una letra solo cuenta si no va pegado a un punto (para no leer 'a.m.' como martes)
DIA_SUELTO = re.compile(r'(?<![\.\w])' + DIA + r'(?=[\s:\.,\d]|$)')
RANGO_DIAS = re.compile(r'(?<![\.\w])' + DIA + r'\s*(?:a|-|al)\s*' + DIA + r'(?=de\b|[^a-z]|$)')
LUNES_VIERNES = re.compile(r'\b(lunes|lun|lu|l)\s+(viernes|vie|vi|v)\b')

def dias_de(seg):
    """Días mencionados en un trozo; None si no menciona ninguno."""
    seg=' '+re.sub(r'\bdel(?=[\s-])', 'de l', seg)+' '
    if re.search(r'todos los dias|diario|365|7 dias|l-d|l a d|lunes a domingo|7/7|7 d|l - d', seg): return list(range(7))
    d=set()
    # rangos de días: 'l-v', 'lunes a viernes', 'martes a sabado'...
    for a, b in RANGO_DIAS.findall(seg):
        i, j = DIAS[a], DIAS[b]
        d |= set(range(i, j + 1)) if i <= j else set(range(i, 7)) | set(range(0, j + 1))
    if LUNES_VIERNES.search(seg): d |= set(range(5))
    sin_rangos = LUNES_VIERNES.sub(' ', RANGO_DIAS.sub(' ', seg))
    if re.search(r'fines? de semana', sin_rangos): d |= {5, 6}
    if re.search(r'festivos?|fest\b', sin_rangos): d.add(6)
    # días sueltos ('s', 'd', 'sabados'...), solo antes de la primera hora: en '9-21 S 10-14' la S
    # no dice de qué días es el 9-21
    for w in DIA_SUELTO.findall(re.split(r'\d', sin_rangos, maxsplit=1)[0]):
        d.add(DIAS[w])
    return sorted(d) if d else None

def parse(raw):
    M=np.zeros((7,24),bool)
    s=norm(raw or '')
    if not s or s in {'-','.','no','n/a','no consta'}: return 'desconocido', None
    if 'autobus' in s or 'servicio de transporte' in s or 'prestacion servicio' in s: return 'movil', None
    if re.search(r'evento|partido|competicion|actividad', s): return 'eventos', None
    if s in {'24','total','todo el dia'} or re.fullmatch(r'(l\s*(a|-)\s*[vd]\s*)?24\s*h?', s) and not s.startswith('l'):
        M[:]=True; return '24h', M
    if re.search(r'24\s*(h|horas|hs)|24/7|24x7|permanente|siempre|ininterrumpid', s) and not re.search(r'de \d{1,2}.{0,6} a 24', s):
        if not re.search(r'(l-v|lunes a viernes|l a v).{0,6}24', s) or re.search(r'365|todos|7 dias|s-d|sabados', s):
            M[:]=True; return '24h', M
    if 'horario escolar' in s or 'horario lectivo' in s:
        M[0:5,8:17]=True; return 'horario', M
    if re.search(r'^(l\s*(a|-)\s*v)\s*24\s*h', s):
        M[0:5,:]=True; return 'horario', M
    if re.search(r'oficinas?|laboral|horario (del )?centro|comercial|colegio|conserjeria|porteria', s):
        M[0:5,9:18]=True; return 'horario', M
    if re.search(r'horario (de )?(apertura|de trabajo)|ver en observaciones|ver observaciones|segun horario', s):
        return 'desconocido', None
    # partimos el texto en bloques de días (por ejemplo 'L-V 8-20 / S 9-14')
    trozos=re.split(r'[;|/\n]|(?<=\d)\s*,\s*(?=[a-z])|(?<=[\dh])\s+y (?=(?:s|sab|d|dom|fines|festivos|sabados|domingos)\b)', s)
    asignado=False; ultimo_dias=None
    for t in trozos:
        rs=rangos(t)
        if not rs: continue
        d=dias_de(t)
        if d is None: d=ultimo_dias if ultimo_dias is not None and not asignado else list(range(5)) if re.search(r'laborable', s) else None
        if d is None: d=list(range(7)) if len(trozos)==1 else list(range(5))
        for a,b in rs:
            if b<=a: b+=24
            for h in range(int(a), int(np.ceil(b))):
                for dd in d: M[(dd + h//24)%7, h%24]=True
        asignado=True; ultimo_dias=d
    if asignado: return 'horario', M
    return 'desconocido', None
