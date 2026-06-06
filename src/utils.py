"""
utils.py

Módulo de utilidades para el análisis de accesibilidad territorial.

Autor: Carlos Díez García
Fecha: 2025-11-08
"""

import config as cfg
pd = cfg.pd
gpd = cfg.gpd
tqdm = cfg.tqdm
os = cfg.os
np = cfg.np
zp = cfg.zp
pt = cfg.pt

provincias = ["Avila","Burgos","Leon","Palencia","Salamanca","Segovia","Soria","Valladolid","Zamora"]

#------------------------------------------FUNCIONES PARA ACCESIBILIDAD DE SERVICIOS--------------------------------------

def calcular_accesibilidad_v2(
    df_servicio: pd.DataFrame,
    nombre_servicio: str,
    radios_pesos: dict = None,
    col_id: str = "id"
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Version ampliada: calcula la accesibilidad a un tipo de servicio y 
    devuelve tanto las métricas agregadas como una tabla detallada de relaciones
    entre CUSECs y servicios dentro de cada radio de distancia.
    """

    # --- Parámetros por defecto ---
    if radios_pesos is None:
        radios_pesos = {1000: 1.0, 5000: 0.6, 15000: 0.3, 30000: 0.1}

    # --- Cargar secciones censales ---
    ruta_shp = os.path.join(cfg.DATA_OUTPUTS_DIR, "Shapefiles", "cyl_2022.shp")
    gdf_secciones = gpd.read_file(ruta_shp).to_crs(25830)
    gdf_secciones["centroid"] = gdf_secciones.geometry.centroid

    # --- Preparar factores del servicio ---
    df_servicio = df_servicio.copy()

    # Factor comedor
    if "COMEDOR" in df_servicio.columns:
        df_servicio["factor_comedor"] = df_servicio["COMEDOR"].map({"S": 1.2, "N": 1.0}).fillna(1.0)
    else:
        df_servicio["factor_comedor"] = 1.0

    # Factor transporte
    if "TRANSPORTE" in df_servicio.columns:
        df_servicio["factor_transporte"] = df_servicio["TRANSPORTE"].map({"S": 1.3, "N": 1.0}).fillna(1.0)
    else:
        df_servicio["factor_transporte"] = 1.0
        
    # Factor combinado
    df_servicio["factor_servicio"] = df_servicio["factor_comedor"] * df_servicio["factor_transporte"]

    # --- Agregación por CUSEC ---
    servicio_cusec = (
        df_servicio.groupby("CUSEC", dropna=True)["factor_servicio"]
        .max()
        .reset_index()
    )

    # --- Unir con geometría destino ---
    gdf_destino = (
        gdf_secciones.merge(servicio_cusec, on="CUSEC", how="inner")
        [["CUSEC", "centroid", "factor_servicio"]]
    )

    # Adjuntar también el ID del servicio (merge adicional)
    gdf_destino = gdf_destino.merge(
        df_servicio[["CUSEC", col_id]],
        on="CUSEC",
        how="left"
    )

    # --- Inicialización de estructuras ---
    radios = sorted(radios_pesos.keys())
    dist_min = []
    conteos = {r: [] for r in radios}

    # Tabla de relaciones detalladas
    filas_rel = []

    # --- Cálculo de distancias ---
    for _, fila in tqdm(
        gdf_secciones.iterrows(),
        total=len(gdf_secciones),
        desc=f"Accesibilidad {nombre_servicio}",
        unit="sección"
    ):

        cusec_origen = fila["CUSEC"]
        geom = fila["centroid"]

        distancias = gdf_destino["centroid"].distance(geom)

        # Distancia mínima
        dist_min.append(distancias.min())

        # Procesar radios
        for r in radios:
            mascara = distancias <= r
            en_radio = gdf_destino.loc[mascara].copy()

            conteos[r].append(len(en_radio))

            # Construcción de la tabla de relaciones
            for idx, fila_serv in en_radio.iterrows():
                filas_rel.append({
                    "CUSEC_origen": cusec_origen,
                    col_id: fila_serv[col_id],
                    "CUSEC_servicio": fila_serv["CUSEC"],
                    "distancia": distancias.loc[idx],
                })

    # --- Construcción del DataFrame final agregado ---
    df_resultado = pd.DataFrame({
        "CUSEC": gdf_secciones["CUSEC"],
        "Seccion_id": gdf_secciones["Seccion_id"],
        f"dist_min_{nombre_servicio}_km": [d / 1000 for d in dist_min]
    })

    # Añadir conteos por radio
    for r in radios:
        df_resultado[f"n_{nombre_servicio}_{r//1000}km"] = conteos[r]

    # Disponibilidad ponderada
    col_prev = None
    disp_ponderada = 0

    for i, r in enumerate(radios):
        col = f"n_{nombre_servicio}_{r // 1000}km"
        if i == 0:
            disp_ponderada += df_resultado[col] * radios_pesos[r]
        else:
            incremento = (df_resultado[col] - df_resultado[col_prev]).clip(lower=0)
            disp_ponderada += incremento * radios_pesos[r]
        col_prev = col

    df_resultado[f"disp_ponderada_{nombre_servicio}"] = disp_ponderada

    # --- Construcción del DataFrame de relaciones ---
    df_relaciones = pd.DataFrame(filas_rel)

    df_relaciones = df_relaciones.drop_duplicates()

    return df_resultado, df_relaciones

def calcular_accesibilidad(
    df_servicio: pd.DataFrame,
    nombre_servicio: str,
    radios_pesos: dict = None
) -> pd.DataFrame:
    """
    Calcula la accesibilidad censal ponderada a un tipo de servicio a partir de un DataFrame
    que contiene códigos CUSEC de las secciones donde existen esos servicios.

    Parámetros
    ----------
    df_servicio : DataFrame
        Debe contener al menos una columna 'CUSEC'.
        Puede incluir opcionalmente:
          - 'COMEDOR': 'S' o 'N'
          - 'TRANSPORTE': 'S' o 'N'

    nombre_servicio : str
        Nombre del servicio (se usa para generar los nombres de las columnas).

    radios_pesos : dict, opcional
        Radios en metros y pesos de accesibilidad.
        Por defecto: {1000: 1.0, 5000: 0.6, 15000: 0.3, 30000: 0.1}

    Retorna
    -------
    DataFrame con columnas:
      - 'CUSEC'
      - 'dist_min_{nombre_servicio}_km'
      - 'disp_ponderada_{nombre_servicio}'
    """
    
    # --- Parámetros por defecto ---
    if radios_pesos is None:
        radios_pesos = {1000: 1.0, 5000: 0.6, 15000: 0.3, 30000: 0.1}

    # --- Cargar shapefile de secciones ---
    ruta_shp = os.path.join(cfg.DATA_OUTPUTS_DIR, "Shapefiles", "cyl_2022.shp")
    gdf_secciones = gpd.read_file(ruta_shp).to_crs(25830)
    gdf_secciones["centroid"] = gdf_secciones.geometry.centroid

    # --- Validar y preparar servicios ---
    df_servicio = df_servicio.copy()
    
    # Si no existen COMEDOR o TRANSPORTE, asignamos 1.0 por defecto
    if "COMEDOR" in df_servicio.columns:
        df_servicio["factor_comedor"] = df_servicio["COMEDOR"].map({"S": 1.2, "N": 1.0}).fillna(1.0)
    else:
        df_servicio["factor_comedor"] = 1.0

    if "TRANSPORTE" in df_servicio.columns:
        df_servicio["factor_transporte"] = df_servicio["TRANSPORTE"].map({"S": 1.3, "N": 1.0}).fillna(1.0)
    else:
        df_servicio["factor_transporte"] = 1.0
        
    df_servicio["factor_servicio"] = df_servicio["factor_comedor"] * df_servicio["factor_transporte"]

    # --- Extraer las secciones donde hay servicio ---
    servicios_cusec = (
        df_servicio.groupby("CUSEC", dropna=True)["factor_servicio"]
        .max()
        .reset_index()
    )

    # --- Unir con shapefile para obtener geometría de los destinos ---
    gdf_destinos = (
        gdf_secciones.merge(servicios_cusec, on="CUSEC", how="inner")
        [["CUSEC", "centroid", "factor_servicio"]]
    )

    # --- Inicialización ---
    radios = sorted(radios_pesos.keys())
    dist_min = []
    conteos = {r: [] for r in radios}

    # --- Calcular distancias desde todas las secciones a las que tienen el servicio ---
    for _, row in tqdm(gdf_secciones.iterrows(), total=len(gdf_secciones), desc=f"Accesibilidad {nombre_servicio}", unit="sección"):
        geom = row["centroid"]
        distancias = gdf_destinos["centroid"].distance(geom)

        # Distancia mínima al servicio
        dist_min.append(distancias.min())

        # Conteo ponderado dentro de cada radio
        for r in radios:
            dentro_radio = gdf_destinos.loc[distancias <= r, "factor_servicio"]
            conteos[r].append(dentro_radio.sum())

    # --- Construir DataFrame resultado ---
    df = pd.DataFrame({
        "CUSEC": gdf_secciones["CUSEC"],
        f"dist_min_{nombre_servicio}_km": [d / 1000 for d in dist_min]
    })

    prev_col = None
    disp_ponderada = 0

    for i, r in enumerate(radios):
        col = f"n_{nombre_servicio}_{r // 1000}km"
        df[col] = conteos[r]

        if i == 0:
            disp_ponderada += df[col] * radios_pesos[r]
        else:
            diff = (df[col] - df[prev_col]).clip(lower=0)
            disp_ponderada += diff * radios_pesos[r]

        prev_col = col

    df[f"disp_ponderada_{nombre_servicio}"] = disp_ponderada

    return df[[
        "CUSEC",
        f"dist_min_{nombre_servicio}_km",
        f"disp_ponderada_{nombre_servicio}"
    ]]

    
def asignar_cusec_por_coordenadas(
    df_servicio: pd.DataFrame,
    lon_col: str,
    lat_col: str,
    crs_origen: str = None
) -> pd.DataFrame:
    """
    Asigna el código CUSEC (sección censal) a un conjunto de servicios
    a partir de sus coordenadas geográficas.

    Para cada punto (servicio) se determina en qué polígono del GeoDataFrame
    de secciones censales se encuentra, devolviendo el DataFrame original
    con una nueva columna 'CUSEC'.

    Parámetros
    ----------
    df_servicio : pandas.DataFrame
        DataFrame que contiene los servicios o localizaciones, con columnas
        de coordenadas (latitud y longitud).

    gdf_secciones : geopandas.GeoDataFrame
        GeoDataFrame de secciones censales o unidades territoriales.
        Debe incluir una columna 'CUSEC' y geometría poligonal válida.

    lon_col : str
        Nombre de la columna con la longitud. Si no se especifica,

    lat_col : str
        Nombre de la columna con la latitud.

    crs_origen : str, opcional
        Código EPSG del sistema de coordenadas de las coordenadas de entrada.
        Por defecto: 'EPSG:4326' (WGS84).

    Retorna
    -------
    pandas.DataFrame
        DataFrame original con una nueva columna 'CUSEC' asignada a partir
        de la intersección espacial con las secciones censales.

    Ejemplo
    --------
    >>> df_centros_cusec = asignar_cusec_por_coordenadas(
    ...     df_centros_docentes_relevantes,
    ...     gdf_secciones
    ... )
    >>> df_centros_cusec.head()
         NOMBRE CENTRO    LATITUD  LONGITUD      CUSEC
    0  CEIP XYZ            41.65    -4.72   4705901001
    """

    if lon_col is None or lat_col is None:
        raise ValueError(
            "No se encontraron columnas válidas de coordenadas. "
            "Especifica los parámetros 'lon_col' y 'lat_col' explícitamente."
        )
        
    # --- Cargar shapefile de secciones ---
    ruta_shp = os.path.join(cfg.DATA_OUTPUTS_DIR, "Shapefiles", "cyl_2022.shp")
    gdf_secciones = gpd.read_file(ruta_shp).to_crs(25830)

    
    # Si no viene especificado crs asumo latitudes y longitudes, y si no el que venga
    crs = crs_origen or "EPSG:4326"

    # --- Crear GeoDataFrame a partir del DataFrame de entrada ---
    gdf_servicio = gpd.GeoDataFrame(
        df_servicio.copy(),
        geometry=gpd.points_from_xy(df_servicio[lon_col], df_servicio[lat_col]),
        crs=crs
    )

    # --- Alinear CRS con las secciones ---
    gdf_servicio = gdf_servicio.to_crs(epsg=25830)
    gdf_secciones = gdf_secciones.to_crs(epsg=25830)

    # --- Unión espacial (puntos dentro de polígonos) ---
    gdf_joined = gpd.sjoin(
        gdf_servicio,
        gdf_secciones[["CUSEC", "geometry"]],
        how="left",
        predicate="within"
    )

    # --- Limpieza final ---
    df_resultado = gdf_joined.drop(columns=["geometry", "index_right"], errors="ignore")

    return df_resultado

def asignar_cusec_por_cp(
    df: pd.DataFrame,
    columna_cp: str = "CP",
    columna_cusec: str = "CUSEC",
    columna_seccion: str = "Seccion_id",
    ruta_csv_cp_seccion: str = None
) -> pd.DataFrame:
    """
    Completa los valores de CUSEC y Seccion_id a partir de un CSV maestro
    con columnas ['Código postal', 'CUSEC', 'Seccion_id'].
    """

    df = df.copy()

    # --- Cargar CSV maestro ---
    if ruta_csv_cp_seccion is None:
        ruta_csv_cp_seccion = os.path.join(cfg.DATA_OUTPUTS_DIR, "callejero_cyl.csv")

    if not os.path.exists(ruta_csv_cp_seccion):
        raise FileNotFoundError(f"No se encontró el archivo: {ruta_csv_cp_seccion}")

    # Cargar maestro (CP + CUSEC + Seccion_id)
    df_cp_seccion = pd.read_csv(
        ruta_csv_cp_seccion,
        sep=";",
        dtype={
            "Código postal": str,
            "CUSEC": str,
            "Seccion_id": "Int64"
        }
    )

    # Normalizar CP maestro
    df_cp_seccion["CP"] = df_cp_seccion["Código postal"].str.zfill(5)

    # Diccionarios
    mapa_cusec = df_cp_seccion.set_index("CP")["CUSEC"].to_dict()
    mapa_seccion = df_cp_seccion.set_index("CP")["Seccion_id"].to_dict()

    # Normalizar CP en df
    df[columna_cp] = df[columna_cp].astype(str).str.zfill(5)

    # --- Completar CUSEC ---
    antes_cusec = (
        df[columna_cusec].isna().sum()
        if columna_cusec in df.columns
        else len(df)
    )

    if columna_cusec not in df.columns:
        df[columna_cusec] = df[columna_cp].map(mapa_cusec)
    else:
        df[columna_cusec] = df[columna_cusec].fillna(df[columna_cp].map(mapa_cusec))

    # Normalizar CUSEC (10 dígitos)
    df[columna_cusec] = df[columna_cusec].astype(str).str.zfill(10)

    despues_cusec = df[columna_cusec].isna().sum()

    # --- Completar Seccion_id ---
    antes_seccion = (
        df[columna_seccion].isna().sum()
        if columna_seccion in df.columns
        else len(df)
    )

    if columna_seccion not in df.columns:
        df[columna_seccion] = df[columna_cp].map(mapa_seccion)
    else:
        df[columna_seccion] = df[columna_seccion].fillna(df[columna_cp].map(mapa_seccion))

    df[columna_seccion] = df[columna_seccion].astype("Int64")

    despues_seccion = df[columna_seccion].isna().sum()

    # --- Log informativo ---
    print(
        f"✔️ {len(df)} registros procesados\n"
        f"   🔹 CUSEC completados: {antes_cusec - despues_cusec} | Sin asignar: {despues_cusec}\n"
        f"   🔹 Seccion_id completados: {antes_seccion - despues_seccion} | Sin asignar: {despues_seccion}"
    )

    return df



#--------------------------------------------FUNCIONES PARA DATOS DEL INE--------------------------------------------

'''Se encarga de cargar los datos socioeconomicos de cada fichero ya que son iguales en formato'''
def carga_datos_ine(path):
    """Carga los CSV socioeconómicos de todas las provincias y los concatena"""
    indicadores = {}
    for provincia in provincias:
        ruta = os.path.join(path, provincia + ".csv")

        df = pd.read_csv(ruta, sep=";", decimal=",", thousands=".", encoding="utf-8-sig")
        df["Provincia"] = provincia
        indicadores[provincia] = df

    # 🔹 Concatenar todos los dataframes fuera del bucle
    indicadores = pd.concat(indicadores.values(), ignore_index=True)

    indicadores = limpiar_datos_ine(indicadores)
    
    return indicadores

def limpiar_datos_ine(indicadores):
    """Limpia las filas sin sección y convierte los . en NaN"""
    indicadores = indicadores[indicadores["Secciones"].notna()]
    indicadores.loc[indicadores["Total"] == ".", "Total"] = np.nan
    return indicadores
    
def estandarizar_df_ine(df, nombre_col_indicador):
    """
    Estandariza el DataFrame para incluir:
    Provincia, Municipio, CP, Distrito, Seccion, Indicador, Periodo, Total
    """
    df = df.copy()
    df.columns = df.columns.str.strip()  # Limpia espacios en los nombres

    # Extrae códigos de municipio, distrito y sección
    df[["CMuni", "Municipio"]] = df["Municipios"].str.extract(r"^(\d+)\s*(.*)$")
    df["CUSEC"] = df["Secciones"].str.extract(r"^(\d+)")

    # Asegura formato texto y conserva ceros a la izquierda
    df["CUSEC"] = df["CUSEC"].fillna("").astype(str).str.strip()

    # Renombra la columna del indicador para saber de qué dimensión viene
    df = df.rename(columns={nombre_col_indicador: "Indicador"})

    # Selecciona columnas comunes
    columnas_necesarias = [
        "Provincia", "CMuni", "CUSEC",
        "Indicador", "Periodo", "Total"
    ]

    return df[columnas_necesarias]

def revisar_indicadores_disponibles(indicadores, col = "Indicador"):
    # Años disponibles
    anios = indicadores["Periodo"].unique()
    print("📅 Años disponibles:")
    print(anios)
    print("-" * 60)
    
    # Indicadores disponibles
    indicadores = indicadores[col].unique()
    print("🧩 Indicadores demográficos disponibles:")
    for ind in indicadores:
        print("  -", ind)
    print("-" * 60)

def pivotar_indicadores(df, 
                        index_cols=["Provincia", "CMuni", "CUSEC", "Periodo"], 
                        col_name="Indicador", 
                        value_name="Total"):
    """
    Convierte una tabla de indicadores demográficos en formato largo a formato ancho (pivoteado),
    aplanando las columnas y normalizando los nombres para facilitar su uso posterior.
    
    Parámetros
    ----------
    df : pandas.DataFrame
        DataFrame original en formato largo (una fila por indicador y sección).
    index_cols : list, opcional
        Columnas que se mantendrán como índices en el pivote (por defecto:
        ["Provincia", "Municipio", "Seccion", "Periodo"]).
    col_name : str, opcional
        Nombre de la columna que contiene los indicadores (por defecto: "Indicador").
    value_name : str, opcional
        Nombre de la columna que contiene los valores numéricos (por defecto: "Total").

    Retorna
    -------
    pandas.DataFrame
        DataFrame en formato ancho, con los indicadores como columnas y nombres limpios.
    """
    # --- Pivotea la tabla ---
    df_pivot = df.pivot_table(
        index=index_cols,
        columns=col_name,
        values=value_name,
        aggfunc="first"
    ).reset_index()

    # --- Aplana las columnas ---
    df_pivot.columns.name = None
    df_pivot.columns = [
        str(col)
        .strip()
        .replace(" ", "_")
        .replace(":", "")
        .replace("/", "_")
        for col in df_pivot.columns
    ]

    # --- Forzar que los códigos sigan siendo texto ---
    if "CUSEC" in df_pivot.columns:
        df_pivot["CUSEC"] = df_pivot["CUSEC"].astype(str).str.strip()

    return df_pivot

def clean_total_column(df):
    """
    Standardizes the INE 'Total' column by removing thousand separators,
    cleaning placeholders, and converting to pandas nullable integers.
    """
    
    clean_values = [".", "", " ", "..", "---"]

    # Replace INE missing-value placeholders
    df["Total"] = df["Total"].replace(clean_values, None)

    # Remove thousand separators and any stray whitespace
    df["Total"] = (
        df["Total"]
        .astype(str)
        .str.replace(r"\s+", "", regex=True)     # remove any type of whitespace
        .str.replace(".", "", regex=False)       # remove thousands separator
        .replace("None", None)                   # after astype(str) cleanup
    )
    
    # Convert to integer (allowing NaN)
    df["Total"] = pd.to_numeric(df["Total"], errors="coerce").astype("Int64")
    
    return df

#-----------------------------------DATOS CATASTRO-------------------------------------------
def load_all_cat_provinces(base_folder: str) -> pd.DataFrame:
    """
    Carga todos los ficheros CAT (.gz) de todas las provincias
    ubicadas dentro de la carpeta base. Devuelve un DataFrame unificado.
    """
    base = pt(base_folder)

    if not base.exists():
        raise ValueError(f"La ruta base no existe: {base}")

    # Detecta subcarpetas (cada una es una provincia)
    provinces = [p for p in base.iterdir() if p.is_dir()]

    if not provinces:
        print("No hay carpetas de provincias en la ruta indicada.")
        return pd.DataFrame()

    dfs = []

    print(f"Detectadas {len(provinces)} provincias. Iniciando proceso de integracion...")

    for prov_folder in tqdm(provinces, desc="Procesando provincias"):
        prov_name = prov_folder.name

        # Carga raw CAT de la provincia
        df_prov = load_all_cat_raw(prov_folder)

        if df_prov.empty:
            print(f"[WARN] Provincia sin ficheros: {prov_name}")
            continue

        # Añade identificador de provincia
        df_prov["provincia"] = prov_name

        dfs.append(df_prov)

    if not dfs:
        return pd.DataFrame()

    # Consolidacion corporativa
    df_final = pd.concat(dfs, ignore_index=True)
    print(f"Consolidacion completada: {df_final.shape[0]} registros cargados.")

    return df_final
    
def read_cat_from_gz(gz_path: str) -> pd.DataFrame:
    """
    Opens a .gz file containing a CAT file (text format),
    reads all lines, and returns them as a DataFrame
    with a single column: raw_record.
    Ensures each line is exactly 1000 characters (CAT standard).
    """
    gz_path = pt(gz_path)

    if not gz_path.exists():
        raise FileNotFoundError(f"GZ file not found: {gz_path}")

    lines = []

    with zp.open(gz_path, "rt", encoding="latin1", errors="ignore") as f:
        for line in f:
            clean = line.rstrip("\n")

            # Pad right if needed (rare but safe)
            if len(clean) < 1000:
                clean = clean.ljust(1000)

            # Trim if extra (should never happen)
            if len(clean) > 1000:
                clean = clean[:1000]

            lines.append(clean)

    return pd.DataFrame({"raw_record": lines})

# Base directory containing the folders
def load_cat_raw(path_gz: str) -> pd.DataFrame:
    """
    Reads a .gz CAT file and returns ALL raw records (as-is) in a DataFrame.
    Adds the record type and source filename.
    """
    df_raw = read_cat_from_gz(path_gz)

    # Add record type (first two chars)
    df_raw["record_type"] = df_raw["raw_record"].str.slice(0, 2)

    # Add filename
    df_raw["source_file"] = pt(path_gz).name

    return df_raw


def load_all_cat_raw(folder_path: str, show_progress=False) -> pd.DataFrame:
    folder = pt(folder_path)
    gz_files = list(folder.glob("*.gz"))

    dfs = []

    iterable = gz_files if not show_progress else tqdm(gz_files, desc="Processing CAT files", unit="file")

    for gz in iterable:
        df_raw = load_cat_raw(gz)
        dfs.append(df_raw)

    return pd.concat(dfs, ignore_index=True)
        
# --------------------------
# CAT - Registro Tipo 11 Parser (Finca)
# --------------------------

def parse_cat_record_11(line: str) -> dict:
    """
    Parses a CAT record of type 11 (Finca) according to the official CAT 2006 specification.
    """

    record = {}

    record["id_parcela"] = line[30:44] # ID de la parcela catastral para vincular
    record["superficie_finca_m2"] = line [295:305]
    record["superficie_construida_total"] = line [305:312]
    record["superficie_sobre_rasante"] = line [312:319]
    record["superficie_bajo_sasante"] = line [319:326] 
    record["superficie_cubierta"] = line [326:333] 
    record["X"] = line [333:342] # Coordenada espacial X de la parcela
    record["Y"] = line [342:352] # Coordenada espacial Y de la parcela
    record["CP"] = line [240:245]
    record["sist_coord"] = line [666:676] # Sistema de coordenadas que se ha elegido

    return record
    
# --------------------------
# CAT - Registro Tipo 15 Parser (Inmuebles)
# --------------------------

def parse_cat_record_15(line: str) -> dict:
    """
    Parses a CAT record of type 15 (Inmueble) according to the official CAT 2006 specification.
    """

    record = {}
    
    record["uso"] = line[427:428] # ID de la parcela catastral para vincular
    record["id_parcela"] = line[30:44] # ID de la parcela catastral para vincular
    record["id_bien"] = line[44:48] # ID del bien inmueble para vincular con el bien y obtener reformas
    record["superficie_inmueble_division_vertical"] = line [441:451]
    record["superficie_inmueble_en_solar"] = line [451:461]
    record["Antiguedad"] = line [371:375]

    return record


# --------------------------
# CAT - Registro Tipo 14 Parser (Construcción)
# --------------------------

def parse_cat_record_14(line: str) -> dict:
    """
    Parses a CAT record of type 15 (Inmueble) according to the official CAT 2006 specification.
    """

    record = {}
    
    record["tipo_reforma"] = line[73:74]
    record["id_parcela"] = line[30:44] # ID de la parcela catastral para vincular
    record["id_bien"] = line[50:54] # ID del bien inmueble para vincular con el bien y obtener reformas
    record["año_reforma"] = line[74:78]

    return record

def asignar_cusec_catastro(df, lon_col="X", lat_col="Y", col_crs="sist_coord"):

    if "CUSEC" not in df.columns:
        df["CUSEC"] = pd.NA

    ruta_shp = os.path.join(cfg.DATA_OUTPUTS_DIR, "Shapefiles", "cyl_2022.shp")
    gdf_secciones = gpd.read_file(ruta_shp).to_crs(25830)

    df_result = df.copy()
    faltantes = df_result[df_result["CUSEC"].isna()].copy()
    if faltantes.empty:
        return df_result

    for crs, grupo in faltantes.groupby(col_crs):

        print(f"\nProcesando CRS: {crs} ({len(grupo)} filas)")

        if pd.isna(crs):
            continue

        crs_correcto = crs if crs.startswith("EPSG") else f"EPSG:{crs}"

        gdf = gpd.GeoDataFrame(
            grupo,
            geometry=gpd.points_from_xy(grupo[lon_col], grupo[lat_col]),
            crs=crs_correcto
        ).to_crs(25830)

        joined = gpd.sjoin(
            gdf,
            gdf_secciones[["CUSEC", "geometry"]],
            how="left",
            predicate="within"
        )

        # Detectar la columna real del CUSEC del shapefile
        if "CUSEC_right" in joined.columns:
            col_cusec = "CUSEC_right"
        else:
            col_cusec = "CUSEC"

        df_result.loc[joined.index, "CUSEC"] = joined[col_cusec].values

    return df_result

    
#--------------------------------------UTILES------------------------------------------------
def normalize_text(s):
    if s is None:
        return None
    s = str(s).strip()
    reemplazos = (
        ("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"),
        ("Á", "A"), ("É", "E"), ("Í", "I"), ("Ó", "O"), ("Ú", "U"),
        ("ñ", "n"), ("Ñ", "N")
    )
    for orig, repl in reemplazos:
        s = s.replace(orig, repl)
    return s
