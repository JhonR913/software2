import pandas as pd
import os
import csv
from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
import plotly.graph_objects as go
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta'
client = MongoClient("mongodb://localhost:27017/")
db = client["analisis_videojuegos"]
CSV_FILE = 'juegos.csv'
CSV_COMENTARIOS = 'comentarios.csv'

# Decorador para requerir login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            flash('Por favor inicia sesión para acceder a esta página', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Función auxiliar para redireccionar según el rol
def redirect_by_role():
    if 'rol' in session and session['rol'] == 'admin':
        return redirect(url_for('admin_panel'))
    else:
        return redirect(url_for('index'))

# Ruta raíz redirige a login si no hay sesión, o al panel correspondiente según el rol
@app.route("/")
def home():
    if 'usuario' in session:
        return redirect_by_role()
    else:
        return redirect(url_for('login'))

@app.route("/admin_panel")
@login_required
def admin_panel():
    # Verificar si el usuario tiene rol de admin
    if session.get('rol') != 'admin':
        flash('No tienes permisos para acceder al panel de administración', 'error')
        return redirect(url_for('index'))
        
    # Leer de MongoDB
    juegos_mongo = set(db.juegos.distinct("nombre"))
    generos = db.juegos.distinct("genero")
    plataformas = db.juegos.distinct("plataforma")

    # Leer adicional de CSV
    try:
        df_csv = pd.read_csv(CSV_FILE, encoding='utf-8')
        juegos_csv = set(df_csv['nombre'].dropna().tolist())
    except FileNotFoundError:
        juegos_csv = set()

    juegos = sorted(juegos_mongo.union(juegos_csv), key=lambda x: str(x))
    return render_template("admin_index.html", juegos=juegos, generos=generos, plataformas=plataformas)


@app.route("/index")
@login_required
def index():
    # Leer de MongoDB
    juegos_mongo = set(db.juegos.distinct("nombre"))
    generos = db.juegos.distinct("genero")
    plataformas = db.juegos.distinct("plataforma")

    # Leer adicional de CSV
    try:
        df_csv = pd.read_csv(CSV_FILE, encoding='utf-8')
        juegos_csv = set(df_csv['nombre'].dropna().tolist())
    except FileNotFoundError:
        juegos_csv = set()

    juegos = sorted(juegos_mongo.union(juegos_csv), key=lambda x: str(x))
    return render_template("index.html", juegos=juegos, generos=generos, plataformas=plataformas)

@app.route("/formulario-agregar-juego")
@login_required
def formulario_agregar_juego():
    # Obtener listas para datalists
    generos = db.juegos.distinct("genero")
    plataformas = db.juegos.distinct("plataforma")
    
    return render_template("agregar.html", generos=generos, plataformas=plataformas)

@app.route("/formulario-agregar-resena")
@login_required
def formulario_agregar_resena():
    # Obtener lista de juegos y plataformas
    juegos_mongo = set(db.juegos.distinct("nombre"))
    try:
        df_csv = pd.read_csv(CSV_FILE, encoding='utf-8')
        juegos_csv = set(df_csv['nombre'].dropna().tolist())
    except FileNotFoundError:
        juegos_csv = set()
    
    juegos = sorted(juegos_mongo.union(juegos_csv), key=lambda x: str(x))
    plataformas = db.juegos.distinct("plataforma")
    
    return render_template("agregar_resena.html", juegos=juegos, plataformas=plataformas)

@app.route("/agregar_juego", methods=["POST"])
@login_required
def agregar_juego():
    if request.method == "POST":
        try:
            # --- DATOS DEL JUEGO ---
            
            # Campos obligatorios del juego
            nombre = request.form['nombre']
            genero = request.form['genero']
            plataforma = request.form['plataforma']
            
            # Campos opcionales con valores predeterminados
            editor = request.form.get('editor', '')
            desarrollador = request.form.get('Developer', '')
            año = request.form.get('Year_of_Release', '')
            if año:
                año = int(año)
            
            # Campos numéricos
            ventas_globales = request.form.get('ventas_globales', '')
            if ventas_globales:
                ventas_globales = float(ventas_globales)
            else:
                ventas_globales = 0.0
                
            na_sales = request.form.get('NA_Sales', '')
            if na_sales:
                na_sales = float(na_sales)
            else:
                na_sales = 0.0
                
            eu_sales = request.form.get('EU_Sales', '')
            if eu_sales:
                eu_sales = float(eu_sales)
            else:
                eu_sales = 0.0
                
            jp_sales = request.form.get('JP_Sales', '')
            if jp_sales:
                jp_sales = float(jp_sales)
            else:
                jp_sales = 0.0
                
            other_sales = request.form.get('Other_Sales', '')
            if other_sales:
                other_sales = float(other_sales)
            else:
                other_sales = 0.0
            
            critic_score = request.form.get('Critic_Score', '')
            if critic_score:
                critic_score = int(critic_score)
            
            user_score = request.form.get('User_Score', '')
            rating = request.form.get('Rating', '')
            
            # Crear documento para MongoDB (Juego)
            nuevo_juego = {
                "nombre": nombre,
                "plataforma": plataforma,
                "genero": genero,
                "editor": editor,
                "Developer": desarrollador
            }
            
            # Agregar campos opcionales solo si existen
            if año:
                nuevo_juego["Year_of_Release"] = año
            if ventas_globales:
                nuevo_juego["ventas_globales"] = ventas_globales
            if na_sales:
                nuevo_juego["NA_Sales"] = na_sales
            if eu_sales:
                nuevo_juego["EU_Sales"] = eu_sales
            if jp_sales:
                nuevo_juego["JP_Sales"] = jp_sales
            if other_sales:
                nuevo_juego["Other_Sales"] = other_sales
            if critic_score:
                nuevo_juego["Critic_Score"] = critic_score
            if user_score:
                nuevo_juego["User_Score"] = user_score
            if rating:
                nuevo_juego["Rating"] = rating
            
            # Verificar si el juego ya existe en la base de datos
            juego_existente = db.juegos.find_one({"nombre": nombre, "plataforma": plataforma})
            
            if not juego_existente:
                # Guardar juego en MongoDB
                db.juegos.insert_one(nuevo_juego)
                
                # Guardar en CSV para mantener consistencia
                with open(CSV_FILE, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    # Verificar si el archivo existe y tiene cabecera
                    try:
                        with open(CSV_FILE, 'r', encoding='utf-8') as check_file:
                            has_header = csv.Sniffer().has_header(check_file.read(1024))
                            if not has_header:
                                writer.writerow(['nombre', 'genero', 'plataforma', 'editor', 'Developer', 'Year_of_Release', 
                                               'ventas_globales', 'NA_Sales', 'EU_Sales', 'JP_Sales', 'Other_Sales', 
                                               'Critic_Score', 'User_Score', 'Rating'])
                    except FileNotFoundError:
                        writer.writerow(['nombre', 'genero', 'plataforma', 'editor', 'Developer', 'Year_of_Release', 
                                       'ventas_globales', 'NA_Sales', 'EU_Sales', 'JP_Sales', 'Other_Sales', 
                                       'Critic_Score', 'User_Score', 'Rating'])
                    
                    # Escribir datos del juego
                    writer.writerow([nombre, genero, plataforma, editor, desarrollador, año, 
                                   ventas_globales, na_sales, eu_sales, jp_sales, other_sales, 
                                   critic_score, user_score, rating])
                
                flash(f"¡Juego '{nombre}' agregado correctamente!", "success")
                return redirect_by_role()
            else:
                flash(f"El juego '{nombre}' ya existe en la base de datos.", "error")
                return redirect(url_for('formulario_agregar_juego'))
            
        except Exception as e:
            flash(f"Error al procesar el formulario: {str(e)}", "error")
            return redirect(url_for('formulario_agregar_juego'))

@app.route("/agregar_resena", methods=["GET", "POST"])
@login_required
def agregar_resena():
    # MÉTODO GET - Mostrar el formulario
    if request.method == "GET":
        # Listas para almacenar todos los nombres de juegos y plataformas
        todos_los_juegos = set()
        todas_las_plataformas = set()
        
        # 1. Intentar obtener juegos desde MongoDB
        juegos_db = db.juegos.find({}, {"nombre": 1, "plataforma": 1})
        for juego in juegos_db:
            todos_los_juegos.add(juego["nombre"])
            todas_las_plataformas.add(juego["plataforma"])
        
        # 2. Intentar obtener juegos desde el CSV
        try:
            df_csv = pd.read_csv(CSV_FILE, encoding='utf-8')
            for _, row in df_csv.iterrows():
                todos_los_juegos.add(row['nombre'])
                todas_las_plataformas.add(row['plataforma'])
        except FileNotFoundError:
            if not todos_los_juegos:  # Solo mostrar error si no se cargaron juegos de MongoDB
                flash("No se encontró el archivo de juegos y no hay juegos en la base de datos.", "error")
                return redirect_by_role()
        
        # Ordenar los nombres de juegos y plataformas
        juegos = sorted(todos_los_juegos)
        plataformas = sorted(todas_las_plataformas)
        
        print(f"Juegos cargados: {len(juegos)}")  # Para depuración
        
        return render_template(
            "agregar_resena.html",
            juegos=juegos,
            plataformas=plataformas
        )
    
    # MÉTODO POST - Procesar el formulario enviado
    elif request.method == "POST":
        try:
            # --- DATOS DE LA RESEÑA ---
            nombre = request.form['nombre']
            plataforma = request.form['plataforma']
            autor = request.form.get('autor', 'Anónimo')
            fecha_str = request.form.get('fecha', '')
            
            if fecha_str:
                fecha = datetime.strptime(fecha_str, '%Y-%m-%d')
            else:
                fecha = datetime.now()
            
            valoracion = request.form.get('valoracion', 3)
            if valoracion:
                valoracion = float(valoracion)
            
            comentario = request.form.get('comentario', '')
            
            # Verificar si el juego existe
            juego_existente = db.juegos.find_one({"nombre": nombre, "plataforma": plataforma})
            
            if not juego_existente:
                try:
                    df_csv = pd.read_csv(CSV_FILE, encoding='utf-8')
                    juego_csv = df_csv[(df_csv['nombre'] == nombre) & (df_csv['plataforma'] == plataforma)]
                    if juego_csv.empty:
                        flash(f"El juego '{nombre}' en plataforma '{plataforma}' no existe en la base de datos. Primero agregue el juego.", "error")
                        return redirect(url_for('agregar_resena'))
                except FileNotFoundError:
                    flash(f"El juego '{nombre}' en plataforma '{plataforma}' no existe en la base de datos. Primero agregue el juego.", "error")
                    return redirect(url_for('agregar_resena'))
            
            # Crear documento para MongoDB (Comentario/Reseña)
            nueva_resena = {
                "name": nombre,   # Igual al campo 'name' como en Steam
                "plataforma": plataforma,
                "autor": autor,
                "fecha": fecha,
                "valoracion": valoracion,
                "comentario": comentario
            }
            
            # Guardar reseña en MongoDB
            db.comentarios.insert_one(nueva_resena)
            
            # Guardar reseña en CSV
            try:
                file_exists = os.path.isfile(CSV_COMENTARIOS)
                with open(CSV_COMENTARIOS, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    
                    # Si el archivo no existe o está vacío, escribir cabecera
                    if not file_exists or os.stat(CSV_COMENTARIOS).st_size == 0:
                        writer.writerow(['name', 'plataforma', 'autor', 'fecha', 'valoracion', 'comentario'])
                    
                    # Escribir reseña
                    writer.writerow([nombre, plataforma, autor, fecha.strftime('%Y-%m-%d'), valoracion, comentario])
            
            except Exception as e_csv:
                flash(f"Error al guardar en CSV: {str(e_csv)}", "error")
            
            flash(f"¡Reseña para '{nombre}' agregada correctamente!", "success")
            return redirect_by_role()
        
        except Exception as e:
            flash(f"Error al procesar el formulario: {str(e)}", "error")
            return redirect(url_for('agregar_resena'))

@app.route("/buscar", methods=["POST"])
@login_required
def buscar():
    nombre_juego = request.form.get("juego")
    hashtag = request.form.get("hashtag")
    plataforma = request.form.get("plataforma")
    genero = request.form.get("genero")

    consulta = {}
    if nombre_juego:
        consulta["nombre"] = {"$regex": nombre_juego, "$options": "i"}
    if genero:
        consulta["genero"] = {"$regex": genero, "$options": "i"}
    if plataforma:
        consulta["plataforma"] = {"$regex": plataforma, "$options": "i"}

    juegos_resultados = list(db.juegos.find(consulta))

    comentarios_resultados = list(db.comentarios.find({
        "$and": [
            {"name": {"$regex": nombre_juego, "$options": "i"}} if nombre_juego else {},
            {"plataforma": {"$regex": plataforma, "$options": "i"}} if plataforma else {}
        ]
    }))

    hashtags_resultados = list(db.hashtags.find({
        "$or": [
            {"red_social": {"$regex": hashtag, "$options": "i"}} if hashtag else {},
            {"genres": {"$regex": hashtag, "$options": "i"}} if hashtag else {}
        ]
    }))

    # 🔵 Ventas por plataforma
    plataformas_ventas = {}
    for juego in juegos_resultados:
        plat = juego.get("plataforma", "Desconocida")
        ventas = juego.get("ventas_globales", 0)
        plataformas_ventas[plat] = plataformas_ventas.get(plat, 0) + ventas
    fig_plataforma = go.Figure(data=[go.Bar(x=list(plataformas_ventas.keys()), y=list(plataformas_ventas.values()))])
    fig_plataforma.update_layout(title="Ventas por Plataforma", xaxis_title="Plataforma", yaxis_title="Ventas Globales (millones)")
    graph_plataforma_html = fig_plataforma.to_html(full_html=False)

    # 🟢 Ventas por región
    ventas_por_region = {"NA": 0, "EU": 0, "JP": 0, "Other": 0}
    for juego in juegos_resultados:
        ventas_por_region["NA"] += juego.get("NA_Sales", 0)
        ventas_por_region["EU"] += juego.get("EU_Sales", 0)
        ventas_por_region["JP"] += juego.get("JP_Sales", 0)
        ventas_por_region["Other"] += juego.get("Other_Sales", 0)
    fig_region = go.Figure(data=[go.Bar(x=list(ventas_por_region.keys()), y=list(ventas_por_region.values()))])
    fig_region.update_layout(title="Ventas por Región", xaxis_title="Región", yaxis_title="Ventas (millones)")
    graph_region_html = fig_region.to_html(full_html=False)

    # 🟡 Ventas por género
    ventas_por_genero = {}
    for juego in juegos_resultados:
        gen = juego.get("genero", "Desconocido")
        ventas = juego.get("ventas_globales", 0)
        ventas_por_genero[gen] = ventas_por_genero.get(gen, 0) + ventas
    fig_genero = go.Figure(data=[go.Pie(labels=list(ventas_por_genero.keys()), values=list(ventas_por_genero.values()))])
    fig_genero.update_layout(title="Ventas por Género")
    graph_genero_html = fig_genero.to_html(full_html=False)

    # 🟠 Calificaciones
    calificaciones = {"nombres": [], "criticos": [], "usuarios": []}
    for juego in juegos_resultados:
        nombre = juego.get("nombre", "Desconocido")
        critic = juego.get("Critic_Score", 0)
        user = juego.get("User_Score", 0)
        if isinstance(user, str) and user:
            try:
                user = float(user) * 10
            except ValueError:
                user = 0
        calificaciones["nombres"].append(nombre)
        calificaciones["criticos"].append(critic)
        calificaciones["usuarios"].append(user)

    fig_calificaciones = go.Figure()
    fig_calificaciones.add_trace(go.Bar(x=calificaciones["nombres"], y=calificaciones["criticos"], name="Críticos"))
    fig_calificaciones.add_trace(go.Bar(x=calificaciones["nombres"], y=calificaciones["usuarios"], name="Usuarios"))
    fig_calificaciones.update_layout(
        title="Calificaciones de Críticos vs Usuarios",
        xaxis_title="Juego",
        yaxis_title="Puntuación",
        barmode='group'
    )
    graph_calificaciones_html = fig_calificaciones.to_html(full_html=False)

    # 🔴 Valoración media de comentarios
    valoracion_media = {}
    comentarios_por_juego = {}
    for comentario in comentarios_resultados:
        nombre = comentario.get("name", "Desconocido")
        valoracion = comentario.get("valoracion", 0)
        if nombre in valoracion_media:
            comentarios_por_juego[nombre] += 1
            valoracion_media[nombre] += valoracion
        else:
            comentarios_por_juego[nombre] = 1
            valoracion_media[nombre] = valoracion

    for nombre in valoracion_media:
        valoracion_media[nombre] = valoracion_media[nombre] / comentarios_por_juego[nombre]

    fig_valoracion = go.Figure(data=[go.Bar(
        x=list(valoracion_media.keys()),
        y=list(valoracion_media.values()),
        text=[f"{v:.1f}" for v in valoracion_media.values()],
        textposition="auto"
    )])
    fig_valoracion.update_layout(
        title="Valoración Media de Usuarios",
        xaxis_title="Juego",
        yaxis_title="Valoración (1-5)",
        yaxis=dict(range=[0, 5])
    )
    graph_valoracion_html = fig_valoracion.to_html(full_html=False)

    # 🔵 CREAR datos
    datos = {
        "juegos": juegos_resultados,
        "comentarios": comentarios_resultados,
        "hashtags": hashtags_resultados
    }

    return render_template(
        "resultados.html",
        graph_plataforma=graph_plataforma_html,
        graph_region=graph_region_html,
        graph_genero=graph_genero_html,
        graph_calificaciones=graph_calificaciones_html,
        graph_valoracion=graph_valoracion_html,
        datos=datos
    )


@app.route("/registro", methods=["GET", "POST"])
def registro():
    # Si ya hay sesión iniciada, redirigir según el rol
    if 'usuario' in session:
        return redirect_by_role()
        
    if request.method == "POST":
        usuario = request.form["usuario"]
        correo = request.form["correo"]
        contraseña = request.form["contraseña"]

        if db.usuarios.find_one({"usuario": usuario}):
            flash("El usuario ya está registrado.", "error")
            return redirect(url_for("registro"))

        # Guardar usuario con contraseña cifrada y rol por defecto
        hash_contraseña = generate_password_hash(contraseña)
        db.usuarios.insert_one({
            "usuario": usuario,
            "correo": correo,
            "contraseña": hash_contraseña,
            "rol": "usuario"  # Asignar el rol "usuario" por defecto
        })

        flash("Registro exitoso. Ya puedes iniciar sesión.", "success")
        return redirect(url_for("login"))

    return render_template("registro.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    # Si ya hay sesión iniciada, redirigir según el rol
    if 'usuario' in session:
        return redirect_by_role()
        
    if request.method == "POST":
        usuario = request.form["usuario"]
        contraseña = request.form.get("contraseña", request.form.get("password", ""))

        # Buscar usuario en la base de datos
        usuario_db = db.usuarios.find_one({"usuario": usuario})

        if usuario_db and check_password_hash(usuario_db["contraseña"], contraseña):
            # Iniciar sesión: guardar usuario en la sesión
            session["usuario"] = usuario
            session["rol"] = usuario_db.get("rol", "usuario")  # Guardar rol en la sesión
            flash(f"Bienvenido, {usuario}", "success")
            
            # Redirigir según el rol
            return redirect_by_role()
        else:
            flash("Usuario o contraseña incorrectos", "error")
            return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("usuario", None)
    session.pop("rol", None)  # Eliminar también el rol de la sesión
    flash("Has cerrado sesión", "info")
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)