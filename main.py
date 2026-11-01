"""Actividad 4. Tablero de mortalidad no fetal Colombia 2019 (DANE)."""
from pathlib import Path
import os
import json
import unicodedata
from urllib.request import Request, urlopen
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash,Input,Output,dcc,html,dash_table

ROOT=Path(__file__).resolve().parent
FILE=ROOT/'data'/'mortalidad_2019_procesado.csv'
POPFILE=ROOT/'data'/'poblacion_municipal_2019_DANE.csv'
GEOFILE=ROOT/'data'/'departamentos_referencia.geojson'
# Primero se consulta la capa del DANE; se conserva una fuente alternativa basada en el MGN 2025.
MAP_SOURCES=[
 'https://geoportal.dane.gov.co/mparcgis/rest/services/Territoriales_DANE/Serv_Territoriales_DANE_2025/MapServer/1/query?where=1%3D1&outFields=*&returnGeometry=true&f=geojson&outSR=4326',
 'https://raw.githubusercontent.com/ytolosa/mapas-colombia/main/output/geojson/col_departamentos_real_nacional.geojson'
]

def _norm(v):
    return ''.join(c for c in unicodedata.normalize('NFKD',str(v or '').upper()) if not unicodedata.combining(c)).strip()

def load_geojson():
    """Leer cartografía guardada o descargarla una sola vez; no requiere token."""
    paths=[GEOFILE]
    for i, source in enumerate([None]+MAP_SOURCES):
        try:
            if i==0:
                if not GEOFILE.is_file(): continue
                geo=json.loads(GEOFILE.read_text(encoding='utf-8'))
            else:
                req=Request(source,headers={'User-Agent':'Mozilla/5.0 (academic Dash application)'})
                with urlopen(req,timeout=18) as resp:
                    geo=json.load(resp)
            features=geo.get('features',[])
            if not features or geo.get('type')!='FeatureCollection': continue
            clean=[]
            for feat in features:
                props=feat.get('properties') or {}
                code=None
                for key,val in props.items():
                    if _norm(key) in {'DPTO_CCDGO','DPTO_CODIGO','COD_DPTO','COD_DANE','DECODIGO','CODIGO_DANE','CODIGO','DPTO'}:
                        code=''.join(c for c in str(val).split('.')[0] if c.isdigit()).zfill(2)
                        if len(code)==2: break
                        code=None
                if code is None:
                    # Cuando el campo no sigue una convención, buscar un código DANE 2 dígitos.
                    for key,val in props.items():
                        if 'COD' in _norm(key):
                            candidate=''.join(c for c in str(val) if c.isdigit())
                            if len(candidate)==2: code=candidate;break
                if code is None: continue
                geom=feat.get('geometry')
                if not geom or geom.get('type') not in ('Polygon','MultiPolygon'):continue
                feat['id']=code
                clean.append(feat)
            if len(set(x['id'] for x in clean))<30: continue
            result={'type':'FeatureCollection','features':clean}
            if not GEOFILE.exists():
                GEOFILE.write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
            return result
        except Exception as exc:
            print(f'Aviso: cartografía no disponible desde fuente {i}: {exc}')
    return None

MONTHS=['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
AGES=[('Mortalidad neonatal',0,4),('Mortalidad infantil',5,6),('Primera infancia',7,8),('Niñez',9,10),('Adolescencia',11,11),('Juventud',12,13),('Adultez temprana',14,16),('Adultez intermedia',17,19),('Vejez',20,24),('Longevidad / centenarios',25,28),('Edad desconocida',29,29)]

def normalize_municipal_code(series):
    """Convertir códigos DANE a cinco dígitos sin perder ceros iniciales."""
    numeric = pd.to_numeric(series, errors='coerce')
    valid = numeric.where(numeric.between(0, 99999) & numeric.mod(1).eq(0))
    return valid.astype('Int64').astype('string').str.zfill(5)


def lowest_residence_rates(data, population):
    """Calcular tasas brutas registradas según municipio de residencia."""
    residents = data[['cod_municipio_residencia', 'municipio_residencia',
                      'departamento_residencia']].copy()
    residents['codigo'] = normalize_municipal_code(residents['cod_municipio_residencia'])
    residents = residents.dropna(subset=['codigo'])

    counts = residents.groupby('codigo', as_index=False).size().rename(columns={'size': 'Defunciones'})
    names = (residents.dropna(subset=['municipio_residencia', 'departamento_residencia'])
             .drop_duplicates('codigo')[['codigo', 'municipio_residencia', 'departamento_residencia']])

    popdata = population[['cod_municipio', 'poblacion_total']].copy()
    popdata['codigo'] = normalize_municipal_code(popdata['cod_municipio'])
    popdata['poblacion_total'] = pd.to_numeric(popdata['poblacion_total'], errors='coerce')
    popdata = popdata.dropna(subset=['codigo'])
    if popdata['codigo'].duplicated().any():
        raise ValueError('La tabla poblacional tiene códigos municipales duplicados; verificar datos antes de calcular tasas.')

    rates = counts.merge(popdata[['codigo', 'poblacion_total']], on='codigo', how='inner', validate='one_to_one')
    rates = rates.loc[rates['poblacion_total'].gt(0)].copy()
    rates['Tasa por 100.000'] = rates['Defunciones'] / rates['poblacion_total'] * 100000.0
    rates = rates.nsmallest(10, 'Tasa por 100.000').merge(names, on='codigo', how='left', validate='one_to_one')
    rates['Lugar'] = (rates['municipio_residencia'].fillna(rates['codigo']) + ' · ' +
                      rates['departamento_residencia'].fillna('Departamento sin identificar'))
    return rates


def age_category(v):
    if pd.isna(v):return 'Edad desconocida'
    for label,a,b in AGES:
        if a<=v<=b:return label
    return 'Edad desconocida'

def blank(message):
    f=go.Figure();f.add_annotation(text=message,showarrow=False,font_size=15);f.update_layout(template='plotly_white',height=380)
    return f

def card(title,component,description=''):
    return html.Section([html.H2(title),component,html.P(description,className='note')],className='card')

app=Dash(__name__,title='Mortalidad en Colombia 2019 | DANE')
server=app.server
if not FILE.exists():
    app.layout=html.Main([html.H1('Mortalidad en Colombia · 2019'),html.H2('Falta procesar los datos'),html.P('Ejecuta primero: .venv312/bin/python prepare_data.py'),html.P('Asegúrate de que los tres originales del DANE estén en la carpeta data/.')],className='shell')
else:
    d=pd.read_csv(FILE,dtype={'dep':'string','mun':'string','cod_municipio':'string','sexo':'string','causa':'string','grupo_edad':'Int64'},low_memory=False)
    for col in ['cod_municipio_residencia','municipio_residencia','departamento_residencia']:
        if col not in d.columns:
            raise ValueError(f'Falta la columna {col}. Ejecuta primero: .venv312/bin/python prepare_data.py')
    d['grupo_edad_etiqueta']=d.grupo_edad.map(age_category)
    d['sexo_etiqueta']=d.sexo.map({'1':'Hombres','2':'Mujeres','3':'Indeterminado','9':'Sin información'}).fillna('Sin información')
    for col in ['lat','lon','mes']:d[col]=pd.to_numeric(d[col],errors='coerce')
    pop=pd.read_csv(POPFILE,dtype={'cod_municipio':'string'}) if POPFILE.exists() else pd.DataFrame(columns=['cod_municipio','poblacion_total'])
    if not pop.empty:
        pop['cod_municipio']=pop.cod_municipio.str.zfill(5)
        pop['poblacion_total']=pd.to_numeric(pop.poblacion_total,errors='coerce')
    mapa_departamentos=load_geojson()
    deps=sorted(d.departamento.dropna().unique().tolist())
    n=len(d)
    app.layout=html.Main([
        html.Header([html.P('MAESTRÍA EN INTELIGENCIA ARTIFICIAL · APLICACIONES I',className='eyebrow'),html.H1('Mortalidad en Colombia · 2019'),html.P('Análisis interactivo de defunciones no fetales · DANE · Plotly + Dash')]),
        html.Section([html.Label('Departamento'),dcc.Dropdown(id='dep',options=[{'label':'Todos los departamentos','value':'TODOS'}]+[{'label':a,'value':a} for a in deps],value='TODOS',clearable=False),html.P('El filtro actualiza los gráficos mensuales, las causas, la distribución por sexo y los grupos de edad. Los rankings y el mapa conservan la perspectiva nacional.',className='note')],className='card'),
        html.Div([html.Section([html.Small('Defunciones analizadas'),html.Strong(f'{n:,}'.replace(',','.'))],className='metric'),html.Section([html.Small('Departamentos identificados'),html.Strong(str(d.dep.nunique()))],className='metric'),html.Section([html.Small('Año de referencia'),html.Strong('2019')],className='metric')],className='metrics'),
        html.Div([card('01 · Distribución geográfica por departamento',dcc.Graph(id='map'), 'Mapa por polígonos departamentales: color = número de defunciones registradas. Límites de referencia DANE (2025), no reconstrucción cartográfica de 2019.'),card('02 · Defunciones por mes',dcc.Graph(id='monthly'),'Evolución mensual del número de registros durante 2019.')],className='grid'),
        html.Div([card('03 · Cinco municipios con más casos X95',dcc.Graph(id='x95'),'Solo casos cuyo código CIE-10 comienza por X95 (agresión con disparo de otras armas de fuego y las no especificadas). No equivale a todos los homicidios.'),card('04 · Diez menores tasas municipales de mortalidad por residencia (2019)',dcc.Graph(id='lowest'),'Se seleccionan los 10 municipios con menor tasa calculada a partir de defunciones de residentes en Colombia y población municipal de 2019 (por 100.000 hab.). El tamaño de cada porción representa las defunciones de residentes dentro de esos 10 municipios, NO el porcentaje de la tasa. Se excluyen municipios sin muertes registradas y residencias no identificables; por tanto, no es un ranking exhaustivo de todos los municipios.')],className='grid'),
        card('05 · Diez principales causas básicas de muerte',dash_table.DataTable(id='topcauses',columns=[{'name':'Código CIE-10','id':'causa'},{'name':'Descripción','id':'nombre_causa'},{'name':'Casos','id':'casos'}],style_header={'fontWeight':'bold','backgroundColor':'#e8f1fa'},style_cell={'fontFamily':'Arial','textAlign':'left','padding':'12px','whiteSpace':'normal','height':'auto'},style_table={'overflowX':'auto'})),
        html.Div([card('06 · Defunciones por sexo y departamento',dcc.Graph(id='sex'),'Barras apiladas con sexo codificado según microdatos DANE.'),card('07 · Distribución por grupos de edad DANE',dcc.Graph(id='ages'),'Agrupación de GRU_ED1 según los intervalos establecidos en las instrucciones de la actividad.')],className='grid'),
        html.Footer('Fuente: DANE, Estadísticas Vitales — defunciones no fetales 2019, clasificación CIE-10 2019 y DIVIPOLA (versión 2026). Los códigos territoriales posteriores se consideran una referencia auxiliar, no una reconstrucción histórica.')
    ],className='shell')

    @app.callback(Output('map','figure'),Output('monthly','figure'),Output('x95','figure'),Output('lowest','figure'),Output('topcauses','data'),Output('sex','figure'),Output('ages','figure'),Input('dep','value'))
    def update(dep):
        q=d if dep=='TODOS' else d[d.departamento==dep]
        geo=d.groupby(['dep','departamento'],dropna=False).size().reset_index(name='Defunciones')
        geo['dep']=geo['dep'].astype('string').str.zfill(2)
        if mapa_departamentos is not None:
            mp=px.choropleth_map(geo,geojson=mapa_departamentos,locations='dep',featureidkey='id',
                color='Defunciones',hover_name='departamento',hover_data={'dep':True,'Defunciones':':,'},
                color_continuous_scale='Blues',range_color=(0,max(1,int(geo['Defunciones'].max()))),
                map_style='carto-positron',zoom=3.7,center={'lat':4.2,'lon':-73.9},opacity=0.87)
            mp.update_traces(marker_line_width=0.7,marker_line_color='#ffffff')
        else:
            # Únicamente como contingencia si no hay conexión para obtener límites territoriales.
            geo=d.groupby(['dep','departamento','lat','lon'],dropna=False).size().reset_index(name='Defunciones').dropna(subset=['lat','lon'])
            mp=px.scatter_map(geo,lat='lat',lon='lon',size='Defunciones',hover_name='departamento',
                hover_data={'dep':True,'Defunciones':':,','lat':False,'lon':False},size_max=60,
                zoom=4.2,center={'lat':4.5,'lon':-73.8},map_style='open-street-map',color='Defunciones',
                color_continuous_scale='Blues') if not geo.empty else blank('Cartografía no disponible: conecta internet para descargarla')
        bymonth=q[q.mes.between(1,12)].groupby('mes').size().reindex(range(1,13),fill_value=0).reset_index(name='Defunciones')
        bymonth['Mes']=MONTHS
        monthly=px.line(bymonth,x='Mes',y='Defunciones',markers=True)
        victims=d[d.causa.str.startswith('X95',na=False)]
        five=victims.groupby(['cod_municipio','municipio','departamento'],dropna=False).size().reset_index(name='Casos').nlargest(5,'Casos')
        five['Lugar']=five.municipio+' · '+five.departamento
        violent=px.bar(five,x='Casos',y='Lugar',orientation='h',color='Casos',color_continuous_scale='Reds') if len(five) else blank('No se identificaron casos X95')
        violent.update_yaxes(categoryorder='total ascending')
        # Tasas por residencia habitual: unir códigos DANE normalizados.
        # Las porciones de la dona son defunciones; las tasas figuran en el hover.
        lowest = lowest_residence_rates(d, pop)
        if not lowest.empty:
            pie=px.pie(lowest,names='Lugar',values='Defunciones',hole=.35,
                       custom_data=['Tasa por 100.000','poblacion_total'],
                       labels={'Defunciones':'Defunciones de residentes'})
            pie.update_traces(textinfo='none',hovertemplate=(
                '<b>%{label}</b><br>Defunciones de residentes: %{value}'
                '<br>Tasa: %{customdata[0]:.2f} por 100.000 hab.'
                '<br>Población 2019: %{customdata[1]:,.0f}<extra></extra>'))
        else:
            pie=blank('No hay datos válidos de residencia y población para calcular las tasas')
        causes=q.groupby(['causa','nombre_causa'],dropna=False).size().reset_index(name='casos').nlargest(10,'casos')
        causes['casos']=causes.casos.map(lambda x:f'{x:,}'.replace(',','.'))
        sex=q.groupby(['departamento','sexo_etiqueta']).size().reset_index(name='Defunciones')
        s=px.bar(sex,x='departamento',y='Defunciones',color='sexo_etiqueta',barmode='stack',labels={'departamento':'Departamento','sexo_etiqueta':'Sexo'})
        age=q.groupby('grupo_edad_etiqueta').size().reindex([x[0] for x in AGES],fill_value=0).reset_index(name='Defunciones').rename(columns={'grupo_edad_etiqueta':'Grupo de edad'})
        a=px.bar(age,x='Grupo de edad',y='Defunciones',color='Defunciones',color_continuous_scale='Blues')
        for f in (mp,monthly,violent,pie,s,a):f.update_layout(template='plotly_white',height=430,margin={'l':20,'r':20,'t':30,'b':75},font={'family':'Arial'})
        s.update_xaxes(tickangle=-45);a.update_xaxes(tickangle=-35)
        return mp,monthly,violent,pie,causes.to_dict('records'),s,a

if __name__=='__main__':
    app.run(debug=os.environ.get('DASH_DEBUG','0')=='1',host=os.environ.get('HOST','127.0.0.1'),port=int(os.environ.get('PORT','8050')))
