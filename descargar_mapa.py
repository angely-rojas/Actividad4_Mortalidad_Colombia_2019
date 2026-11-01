"""Descarga y valida límites departamentales oficiales para la Actividad 4."""
from pathlib import Path
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
DESTINO = ROOT / 'data' / 'departamentos_referencia.geojson'
FUENTES = [
    'https://portalgis.dane.gov.co/mparcgis/rest/services/Hosted/Departamento_Municipio_dg/FeatureServer/0/query',
    'https://geoportal.dane.gov.co/mparcgis/rest/services/Hosted/Departamentos_Colombia/FeatureServer/0/query',
]
PARAMS = {'where':'1=1','outFields':'*','returnGeometry':'true','outSR':4326,'f':'geojson'}
CLAVES = ('dpto_ccdgo','decodigo','DeCodigo','DPTO_CCDGO','COD_DPTO','CODIGO_DANE')

def obtener():
    errores=[]
    for url in FUENTES:
        try:
            req=Request(url+'?'+urlencode(PARAMS), headers={'User-Agent':'Mozilla/5.0','Accept':'application/geo+json, application/json'})
            with urlopen(req,timeout=40) as response:
                datos=json.load(response)
            if datos.get('type')!='FeatureCollection':
                raise ValueError(f'La respuesta no es GeoJSON: {str(datos)[:170]}')
            limpios=[]
            for f in datos.get('features',[]):
                propiedades=f.get('properties') or {}
                codigo=next((propiedades[c] for c in CLAVES if c in propiedades and propiedades[c] is not None),None)
                if codigo is None: continue
                codigo=str(codigo).strip().split('.')[0]
                if not codigo.isdigit():continue
                codigo=codigo.zfill(2)
                if len(codigo)!=2:continue
                geom=f.get('geometry') or {}
                if geom.get('type') not in ('Polygon','MultiPolygon'):continue
                f['id']=codigo
                limpios.append(f)
            distintos={f['id'] for f in limpios}
            if len(distintos)<30:
                raise ValueError(f'Solo se reconocieron {len(distintos)} códigos departamentales: {sorted(distintos)}')
            salida={'type':'FeatureCollection','features':limpios}
            DESTINO.parent.mkdir(parents=True,exist_ok=True)
            DESTINO.write_text(json.dumps(salida,ensure_ascii=False),encoding='utf-8')
            print(f'CORRECTO: {len(limpios)} polígonos; {len(distintos)} códigos departamentales.')
            print(f'Archivo guardado en: {DESTINO}')
            print(f'Tamaño: {DESTINO.stat().st_size/1024:.1f} KB')
            return
        except Exception as e:
            errores.append(f'{url}: {type(e).__name__}: {e}')
    print('NO SE PUDO DESCARGAR EL MAPA. Detalles:')
    for e in errores:print('-',e)
    raise SystemExit(1)

if __name__=='__main__':
    obtener()
