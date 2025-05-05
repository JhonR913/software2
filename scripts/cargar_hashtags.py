import pandas as pd
from pymongo import MongoClient

# Conectar a MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["analisis_videojuegos"]

# Leer el archivo CSV
df = pd.read_csv("hashtags.csv")

# Renombrar columnas
df = df.rename(columns={
    "meta_score": "puntaje_meta",
    "title": "titulo",
    "platform": "plataforma",
    "date": "fecha",
    "user_score": "puntaje_usuario",
    "link": "enlace",
    "esrb_rating": "calificacion_esrb",
    "developers": "desarrolladores",
    "genres": "generos"
})

# Procesar rangos de puntajes si es necesario
df['puntaje_meta'] = df['puntaje_meta'].apply(lambda x: sum(map(float, x.split(' - '))) / 2 if isinstance(x, str) else x)

# Manejar valores nulos (rellenar con 0)
df.fillna({"puntaje_meta": 0, "puntaje_usuario": 0}, inplace=True)

# Procesar las plataformas y géneros (si son listas separadas por coma)
df['generos'] = df['generos'].apply(lambda x: x.split(',') if isinstance(x, str) else [])
df['plataforma'] = df['plataforma'].apply(lambda x: x.split(',') if isinstance(x, str) else [])

# Insertar los datos en MongoDB
db.juegos_meta_score.insert_many(df.to_dict(orient="records"))
