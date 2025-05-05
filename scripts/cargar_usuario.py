from pymongo import MongoClient
from werkzeug.security import generate_password_hash

# Conectar a MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["analisis_videojuegos"]  # Conectar a la base de datos 'analisis_videojuegos'

# Datos del usuario admin
usuario = "admin"
correo = "jramirezm16@ucentral.edu.co"  # Correo actualizado
contraseña = "admin"  # Contraseña proporcionada

# Cifrar la contraseña
password_hash = generate_password_hash(contraseña)  # Aquí cifras la contraseña

# Crear el documento para el usuario admin
nuevo_usuario = {
    "usuario": usuario,  # Usar "usuario" en lugar de "nombre_usuario"
    "correo": correo,
    "contraseña": password_hash,  # Almacenar la contraseña cifrada
    "rol": "admin"  # Asignar el rol "admin"
}

# Insertar el nuevo usuario en la colección 'usuarios'
db.usuarios.insert_one(nuevo_usuario)

# Verificar que el usuario fue insertado correctamente
usuarios = db.usuarios.find()
for usuario in usuarios:
    print(usuario)
