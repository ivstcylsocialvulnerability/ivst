# Índice de Vulnerabilidad Social y Territorial (IVST) – Castilla y León

Este repositorio contiene el desarrollo completo del pipeline de datos utilizado para la construcción del Índice de Vulnerabilidad Social y Territorial (IVST) a escala de sección censal en la Comunidad Autónoma de Castilla y León.

El proyecto integra múltiples fuentes de datos abiertos y aplica técnicas de análisis multivariante para generar indicadores sintéticos orientados al análisis territorial, la investigación social y la visualización avanzada.

---

## Objetivo del proyecto

El objetivo principal es modelizar la vulnerabilidad social y territorial desde un enfoque multidimensional, integrando información demográfica, socioeconómica, habitacional y de accesibilidad a servicios, y sintetizarla en un índice final (IVST) mediante Análisis de Componentes Principales (PCA).

El modelo está diseñado para:
- Trabajar a escala de sección censal (CUSEC).
- Facilitar la comparación territorial.
- Servir como base para análisis exploratorios, cartográficos y de apoyo a la toma de decisiones.

---

## Estructura del repositorio

### data/

Contiene todos los ficheros de datos utilizados y generados durante el pipeline.

> **Nota importante**  
> Por motivos de tamaño, licencias de uso y buenas prácticas académicas, los datos de entrada y salida no se incluyen en este repositorio. Las fuentes utilizadas son públicas y se describen detalladamente en la memoria del TFM.

#### data/inputs/
Ficheros fuente descargados directamente de organismos oficiales (INE, Catastro) o mediante endpoints públicos.

- `DA_Dim_servicios/`
- `DD_Dim_demografica/`
- `DH_Dim_habitacional/`
- `DS_Dim_socioeconomica/`

#### data/outputs/
Ficheros procesados y finales generados durante el pipeline, utilizados para el modelado y la visualización.

- `DA_Dim_servicios/`
- `DD_Dim_demografica/`
- `DH_Dim_habitacional/`
- `DS_Dim_socioeconomica/`

---

### src/

Contiene todo el código del proyecto, organizado por fases lógicas del pipeline.

#### src/01_utils/
Cuadernos auxiliares que deben ejecutarse en primer lugar para generar ficheros base necesarios para el resto del proceso.

- `01_meshcyl`: Procesa el shapefile nacional de secciones censales y lo restringe al ámbito territorial de Castilla y León.
- `02_callejero`: Parsea el callejero del INE para obtener entidades menores y códigos postales con fines de visualización.
- `03_coordenadas`: Asigna códigos de sección censal (CUSEC) a códigos postales utilizando coordenadas geográficas.
- `04_download_ceas`: Descarga y almacena el listado de Centros de Acción Social (CEAS).

#### src/02_dims/
Procesamiento de los ficheros fuente para construir los datasets finales de cada dimensión del modelo.

- `DA/` Dimensión de accesibilidad a servicios.
- `DD/` Dimensión demográfica.
- `DH/` Dimensión habitacional.
- `DS/` Dimensión socioeconómica.

Cada carpeta genera un CSV final por dimensión, utilizado tanto para el modelo como para la visualización.

#### src/03_ivst_model/
Incluye el cuaderno encargado de la construcción del IVST final mediante la aplicación de PCA sobre cada dimensión y la posterior integración del índice.

---

### Archivos de configuración

- `config.py`  
  Contiene la configuración base del proyecto (rutas, constantes y módulos comunes), utilizada de forma transversal en los cuadernos.

- `utils.py`  
  Incluye funciones auxiliares reutilizables empleadas en distintos puntos del pipeline, centralizando lógica común y evitando duplicidades.

---

## Flujo general del pipeline

1. Ejecución de los cuadernos de `01_utils` para generar ficheros base.
2. Procesamiento de los datos fuente por dimensiones en `02_dims`.
3. Generación de los CSV finales en `data/outputs`.
4. Construcción del Índice de Vulnerabilidad Social y Territorial (IVST) en `03_ivst_model`.

---

## Instalación y configuración del entorno

El proyecto utiliza un entorno virtual gestionado con **conda**, definido en el fichero `ivst-env.yml`.

### Requisitos previos
- Anaconda o Miniconda instalado.
- Git.

### Clonado del repositorio

```bash
git clone https://github.com/cdiezgar-uoc/ivst-tfm.git
cd ivst-tfm
```

### Creación del repositorio con conda

```bash
conda env create -f ivst-env.yml
conda activate ivst-env
jupyter notebook
```

