# src/config.py

# --- Librerías de uso general ---
import os
import re
import numpy as np
import pandas as pd
import geopandas as gpd
import requests as rq
import osmnx as ox
import networkx as nx
import gzip as zp
from pathlib import Path as pt

from shapely.geometry import Point
from tqdm import tqdm
import time as time

# --- Configuración global ---
tqdm.pandas()
DEFAULT_CRS = 25830   # En km
RADIOS_PESOS = {1000: 1.0, 5000: 0.6, 10000: 0.3, 25000: 0.1}   # Ponderación base de accesibilidad por distancia

# --- Parámetros de entorno (rutas, cache, etc.) ---
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
DATA_MESH_FILE = os.path.join(
    DATA_DIR, "Shapefiles", "Seccionado", "seccionado_2022", "SECC_CE_20220101.shp")
DATA_CALLEJERO_FILE = os.path.join(
    DATA_DIR, "Shapefiles","caj_esp_072022","Nacional","TRAM.P01-52.D220630.G220704")
DATA_INPUTS_DIR = os.path.join(DATA_DIR, "inputs")
DATA_INPUTS_DA = os.path.join(DATA_INPUTS_DIR, "DA_Dim_servicios")
DATA_INPUTS_DD = os.path.join(DATA_INPUTS_DIR, "DD_Dim_demografica")
DATA_INPUTS_DS = os.path.join(DATA_INPUTS_DIR, "DS_Dim_socioeconomica")
DATA_INPUTS_DH = os.path.join(DATA_INPUTS_DIR, "DH_Dim_habitacional")
DATA_OUTPUTS_DIR = os.path.join(DATA_DIR, "outputs")
DATA_OUTPUTS_DA = os.path.join(DATA_OUTPUTS_DIR, "DA_Dim_servicios")
DATA_OUTPUTS_DD = os.path.join(DATA_OUTPUTS_DIR, "DD_Dim_demografica")
DATA_OUTPUTS_DS = os.path.join(DATA_OUTPUTS_DIR, "DS_Dim_socioeconomica")
DATA_OUTPUTS_DH = os.path.join(DATA_OUTPUTS_DIR, "DH_Dim_habitacional")

# --- Exportaciones controladas ---
__all__ = [
    # Librerías
    "os", "re", "np", "pd", "gpd",
    "Point", "tqdm", "nx", "ox", "rq",
    "time", "zp", "pt",

    # Configuración global
    "DEFAULT_CRS", "RADIOS_PESOS",

    # Rutas principales
    "BASE_DIR", "DATA_DIR",
    "DATA_INPUTS_DIR", "DATA_INPUTS_DA", "DATA_INPUTS_DD",
    "DATA_INPUTS_DS", "DATA_INPUTS_DH",
    "DATA_OUTPUTS_DIR", "DATA_OUTPUTS_DA", "DATA_OUTPUTS_DD",
    "DATA_OUTPUTS_DS", "DATA_OUTPUTS_DH", "DATA_MESH_FILE",
    "DATA_CALLEJERO_FILE"
]