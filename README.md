# Actividad 4 · Mortalidad en Colombia (2019)

## Introducción y objetivo
Aplicación interactiva de Python, Plotly y Dash para explorar registros oficiales de defunciones no fetales del DANE 2019 por departamento, mes, causa básica de muerte, municipio, sexo y grupo de edad.

## Fuentes
- DANE, Estadísticas Vitales 2019: https://microdatos.dane.gov.co/index.php/catalog/696
- Clasificación Internacional de Enfermedades (CIE-10), versión 2019, DANE.
- DIVIPOLA, lista descargada en 2026: nombres y coordenadas de referencia. Sus cambios históricos deben revisarse antes de cualquier análisis de fronteras de 2019.

## Estructura
- `main.py`: aplicación Dash y siete visualizaciones.
- `prepare_data.py`: lectura y procesamiento verificable del ZIP anidado y los dos Excel.
- `data/mortalidad_2019_procesado.csv`: datos reales procesados que consume Dash.
- `data/Defunciones.zip`, `data/Listados_DIVIPOLA.xlsx`, `data/clasificacion-int-enfermedades-OMS-OPS-V19.xlsx`: insumos originales para reproducibilidad; **no es necesario subir los originales a GitHub si se conserva el archivo procesado y los enlaces a fuentes oficiales**.
- `assets/style.css`: estilos de interfaz.
- `requirements.txt`: librerías y versiones.
- `render.yaml`: infraestructura como código para Render.

## Instalación en PyCharm (macOS)
Abrir la carpeta en PyCharm, seleccionar Python 3.12 y crear un virtualenv. Luego, en Terminal:

```bash
.venv312/bin/python -m pip install -r requirements.txt
```

Si la carpeta `data/` ya contiene `mortalidad_2019_procesado.csv`, NO es indispensable ejecutar el procesamiento. Para reconstruirlo desde los originales:

```bash
.venv312/bin/python prepare_data.py
```

Iniciar aplicación:

```bash
.venv312/bin/python main.py
```

Abrir http://127.0.0.1:8050/ en el navegador. Si el proyecto usa otro entorno, reemplazar `.venv312/bin/python` por su intérprete de Python 3.12.

## Visualizaciones y explicación de resultados
1. **Mapa**: círculos geográficos por departamento, proporcionales a los conteos de defunciones; no es un mapa de polígonos (coroplético).
2. **Líneas**: defunciones por mes durante 2019; permite identificar máximos y mínimos mensuales.
3. **Barras**: cinco municipios con más registros cuyo código CIE-10 comienza con X95. No equivale al total de homicidios por todas las causas.
4. **Circular**: diez municipios con menos defunciones **registradas**, entre aquellos con algún registro. **No son los menores índices/tasas de mortalidad:** para ello hacen falta denominadores poblacionales municipales de 2019.
5. **Tabla**: diez causas básicas de muerte con código CIE-10, descripción y total de casos, ordenadas descendentemente.
6. **Barras apiladas**: distribución por sexo y departamento.
7. **Grupos de edad**: recuento agrupado por `GRU_ED1` conforme a las once categorías especificadas en el documento de la actividad.

El filtro departamental afecta los gráficos de tendencias, causas, sexo y edad; mantiene nacionales el mapa y los rankings para preservar el contexto.

### Calidad de datos
La lectura directa del archivo oficial encontró **244.355 registros**. En la unión con DIVIPOLA versión 2026 hubo **1 registro con código municipal sin correspondencia exacta** y **2 con causa básica sin descripción exacta** en la tabla CIE-10, conservados sin alteración. Se deben verificar los códigos históricos 2019 antes de interpretar diferencias territoriales.

## Despliegue en Render
1. Crear un repositorio GitHub y añadir los archivos Python, CSS, `render.yaml`, `requirements.txt`, `README.md` y `data/mortalidad_2019_procesado.csv`.
2. No subir carpetas `.venv` o `.venv312`, ni archivos originales pesados, si no son necesarios. El `.gitignore` los excluye.
3. Render → New → Blueprint → conectar el repositorio → confirmar servicio gratuito cuando esté disponible.
4. Render instalará las dependencias mediante `pip install -r requirements.txt` e iniciará `gunicorn main:server --workers 1 --threads 2 --timeout 120`.
5. Probar URL pública, filtros y las siete visualizaciones desde un navegador distinto. Render Free puede suspender el servicio por inactividad y tardar al reactivarse.

## Evidencias que debes incorporar antes de entregar
Adjuntar capturas reales de la portada, mapa, cada gráfico, tabla y URL publicada. Redactar interpretaciones apoyadas en las cifras que muestre la aplicación, sin deducir tasas de conteos absolutos.

## Limitaciones para cumplir literalmente con la rúbrica
- El gráfico circular actualmente presenta *menores conteos* y no *menores índices de mortalidad* porque **no se ha proporcionado la población municipal 2019**. Para resolverlo se necesita una tabla oficial de población municipal que permita calcular muertes/población × 100.000.
- El mapa de círculos muestra la distribución geográfica, pero si el profesor espera un mapa coroplético por límites, deberá añadirse un GeoJSON departamental verificado.
