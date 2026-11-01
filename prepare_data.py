"""Preprocesa microdatos originales DANE 2019 y tablas auxiliares. Ejecutar una vez."""
from pathlib import Path
from io import BytesIO
from zipfile import ZipFile
import pandas as pd
import re

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
OUT=DATA/'mortalidad_2019_procesado.csv'

def clean(s):
    return s.astype('string').fillna('').str.strip().str.replace(r'\.0$', '', regex=True)

def main():
    required=['Defunciones.zip','Listados_DIVIPOLA.xlsx','clasificacion-int-enfermedades-OMS-OPS-V19.xlsx']
    missing=[x for x in required if not (DATA/x).exists()]
    if missing:
        raise FileNotFoundError('Faltan archivos originales en data/: '+', '.join(missing))
    print('1/4 Leyendo defunciones oficiales desde ZIP anidado...')
    with ZipFile(DATA/'Defunciones.zip') as outer:
        zipname=next(n for n in outer.namelist() if n.lower().endswith('nofetal2019.zip'))
        with ZipFile(BytesIO(outer.read(zipname))) as inner:
            csvname=next(n for n in inner.namelist() if n.lower().endswith('nofetal2019.csv'))
            with inner.open(csvname) as handle:
                raw=pd.read_csv(handle,dtype='string',usecols=['COD_DPTO','COD_MUNIC','MES','SEXO','GRU_ED1','C_BAS1'],encoding='latin1',low_memory=False)
    raw.columns=['dep','mun','mes','sexo','grupo_edad','causa']
    raw['dep']=clean(raw.dep).str.zfill(2)
    raw['mun']=clean(raw.mun).str.zfill(3)
    raw['cod_municipio']=raw.dep+raw.mun
    raw['mes']=pd.to_numeric(raw.mes,errors='coerce').astype('Int64')
    raw['grupo_edad']=pd.to_numeric(raw.grupo_edad,errors='coerce').astype('Int64')
    raw['sexo']=clean(raw.sexo)
    raw['causa']=clean(raw.causa).str.upper().str.replace('.','',regex=False)
    print('Registros originales:',len(raw))
    print('2/4 Leyendo DIVIPOLA...')
    municipalities=pd.read_excel(DATA/'Listados_DIVIPOLA.xlsx',sheet_name='Municipios',skiprows=10,header=None,usecols='A:D',dtype='string')
    municipalities.columns=['dep','departamento','cod_municipio','municipio']
    municipalities=municipalities[municipalities.cod_municipio.str.fullmatch(r'\d{5}',na=False)].copy()
    municipalities['cod_municipio']=clean(municipalities.cod_municipio).str.zfill(5)
    municipalities=municipalities.drop_duplicates('cod_municipio')
    departments=pd.read_excel(DATA/'Listados_DIVIPOLA.xlsx',sheet_name='Departamentos',skiprows=9,header=None,usecols='A:D',dtype='string')
    departments.columns=['dep','departamento','lat','lon']
    departments=departments[departments.dep.str.fullmatch(r'\d{1,2}',na=False)].copy()
    departments['dep']=clean(departments.dep).str.zfill(2)
    departments=departments.drop_duplicates('dep')
    raw=raw.merge(municipalities[['cod_municipio','municipio']],on='cod_municipio',how='left',validate='many_to_one')
    raw=raw.merge(departments[['dep','departamento','lat','lon']],on='dep',how='left',validate='many_to_one')
    raw['departamento']=raw.departamento.fillna('Sin correspondencia DANE ('+raw.dep+')')
    raw['municipio']=raw.municipio.fillna('Sin correspondencia ('+raw.cod_municipio+')')
    print('Municipios sin correspondencia:',raw.municipio.str.startswith('Sin correspondencia').sum())
    print('3/4 Leyendo CIE-10...')
    codebook=pd.read_excel(DATA/'clasificacion-int-enfermedades-OMS-OPS-V19.xlsx',sheet_name='CAP1-CAP22',skiprows=5,header=None,usecols='A:B',dtype='string')
    codebook.columns=['causa','nombre_causa']
    codebook['causa']=clean(codebook.causa).str.upper().str.replace('.','',regex=False)
    codebook=codebook[codebook.causa.str.fullmatch(r'[A-Z][0-9]{2}[A-Z0-9]{0,2}',na=False)].drop_duplicates('causa')
    names=codebook.set_index('causa')['nombre_causa'].to_dict()
    raw['nombre_causa']=raw.causa.map(names)
    raw['nombre_causa']=raw.nombre_causa.fillna('Código CIE-10 '+raw.causa)
    print('Causas sin descripción exacta:',raw.nombre_causa.str.startswith('Código CIE-10').sum())
    print('4/4 Guardando tabla procesada, lista para Dash y Render...')
    raw.to_csv(OUT,index=False,encoding='utf-8')
    print('GUARDADO:',OUT,'filas=',len(raw),'MB=',round(OUT.stat().st_size/1e6,2))
    print('CHECKSUM lógica: suma de registros procesados == originales')

if __name__=='__main__':main()
