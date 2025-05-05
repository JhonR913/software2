import snscrape.modules.twitter as sntwitter
import pandas as pd
import re
import time
from datetime import datetime

# Función para extraer hashtags
def extraer_hashtags(texto):
    return " ".join(re.findall(r"#\w+", texto))

# Lista de juegos con sus nombres completos
juegos = [
    "Grand Theft Auto", "Call of Duty", "FIFA", "Minecraft", "Fortnite", "The Legend of Zelda",
    "Red Dead Redemption", "The Last of Us", "God of War", "Cyberpunk 2077", "Apex Legends",
    "Overwatch", "League of Legends", "Valorant", "Dota 2", "Counter Strike", "PUBG",
    "Among Us", "Hogwarts Legacy", "Animal Crossing", "Elden Ring", "Fall Guys",
    "Rocket League", "Halo", "Battlefield", "Resident Evil", "Assassin’s Creed",
    "Need for Speed", "Horizon Zero Dawn", "Metal Gear Solid", "Uncharted", "Doom",
    "Gran Turismo", "Super Smash Bros", "Mario Kart", "Pokemon", "Street Fighter",
    "Tekken", "Rainbow Six", "Splatoon", "Far Cry", "Star Wars Battlefront",
    "Tomb Raider", "Bayonetta", "Destiny", "Diablo", "Hitman", "Kirby", "Bioshock",
    "Left 4 Dead"
]

# Lista para almacenar los tweets
tweets_total = []
max_tweets = 50
fecha_hoy = datetime.today().strftime('%Y-%m-%d')
fecha_inicio = "2024-04-01"  # Último año desde abril 2024

# Recolectando tweets de cada juego
for juego in juegos:
    print(f"🔍 Recolectando tweets populares para: {juego}")
    
    # Realizando la búsqueda con parámetros de fecha y popularidad
    query = f'"{juego}" lang:es since:{fecha_inicio} until:{fecha_hoy} min_faves:20 min_retweets:10'
    
    for i, tweet in enumerate(sntwitter.TwitterSearchScraper(query).get_items()):
        if i >= max_tweets:
            break
        if len(tweet.content) < 100:  # Solo tweets más largos (como hilos o análisis)
            continue
        
        # Almacenando la información del tweet
        tweets_total.append({
            "juego": juego,
            "usuario": tweet.user.username,
            "fecha": tweet.date,
            "contenido": tweet.content,
            "hashtags": extraer_hashtags(tweet.content),
            "likes": tweet.likeCount,
            "retweets": tweet.retweetCount,
            "url": tweet.url
        })

    # Pausa para evitar ser bloqueado
    time.sleep(1.5)

# Guardar los resultados en un archivo CSV
df = pd.DataFrame(tweets_total)
df.to_csv("tweets_videojuegos.csv", index=False, encoding="utf-8-sig")
print("✅ Archivo guardado como: tweets_videojuegos.csv")
