import pandas as pd
from pymongo import MongoClient

# Conectar a MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["analisis_videojuegos"]

# Leer el archivo CSV (ajusta el nombre del archivo a tu caso)
df = pd.read_csv("comentarios.csv")

# Renombrar las columnas según el formato que proporcionaste
df = df.rename(columns={
    "Url of a game": "url",
    "types": "tipo_paquete",
    "name": "nombre",
    "desc_snippet": "descripcion_corta",
    "recent_reviews": "comentarios_recientes",
    "all_reviews": "comentarios_totales",
    "release_date": "fecha_lanzamiento",
    "developer": "desarrollador",
    "publisher": "publicador",
    "popular_tags": "etiquetas_populares"
})

# Insertar los datos en la colección 'juegos' en MongoDB
db.juegos.insert_many(df.to_dict(orient="records"))
