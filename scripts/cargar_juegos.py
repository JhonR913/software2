
import pandas as pd
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["analisis_videojuegos"]

df = pd.read_csv("ventas.csv")
df = df.rename(columns={
    "Name": "nombre", "Platform": "plataforma", "Year": "anio",
    "Genre": "genero", "Publisher": "editor", "Global_Sales": "ventas_globales"
})
db.juegos.insert_many(df.to_dict(orient="records"))
