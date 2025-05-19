import pandas as pd
import os
import csv
from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
import plotly.graph_objects as go
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta'

# Conexión a MongoDB
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

# Redirige al usuario según su rol
def redirect_by_role():
    if session.get('rol') == 'admin':
        return redirect(url_for('admin_panel'))
    return redirect(url_for('index'))

@app.route("/")
def home():
    if 'usuario' in session:
        return redirect_by_role()
    return redirect(url_for('login'))

@app.route("/admin_panel")
@login_required
def admin_panel():
    if session.get('rol') != 'admin':
        flash('No tienes permisos para acceder al panel de administración', 'error')
        return redirect(url_for('index'))
    juegos_mongo = set(db.juegos.distinct("nombre"))
    generos = db.juegos.distinct("genero")
    plataformas = db.juegos.distinct("plataforma")
    try:
        df_csv = pd.read_csv(CSV_FILE, encoding='utf-8')
        juegos_csv = set(df_csv['nombre'].dropna().tolist())
    except FileNotFoundError:
        juegos_csv = set()
    juegos = sorted(juegos_mongo.union(juegos_csv), key=str)
    return render_template("admin_index.html", juegos=juegos, generos=generos, plataformas=plataformas)

@app.route("/index")
@login_required
def index():
    juegos_mongo = set(db.juegos.distinct("nombre"))
    generos = db.juegos.distinct("genero")
    plataformas = db.juegos.distinct("plataforma")
    try:
        df_csv = pd.read_csv(CSV_FILE, encoding='utf-8')
        juegos_csv = set(df_csv['nombre'].dropna().tolist())
    except FileNotFoundError:
        juegos_csv = set()
    juegos = sorted(juegos_mongo.union(juegos_csv), key=str)
    return render_template("index.html", juegos=juegos, generos=generos, plataformas=plataformas)

@app.route("/formulario-agregar-juego")
@login_required
def formulario_agregar_juego():
    generos = db.juegos.distinct("genero")
    plataformas = db.juegos.distinct("plataforma")
    return render_template("agregar.html", generos=generos, plataformas=plataformas)

@app.route("/formulario-agregar-resena")
@login_required
def formulario_agregar_resena():
    juegos_mongo = set(db.juegos.distinct("nombre"))
    try:
        df_csv = pd.read_csv(CSV_FILE, encoding='utf-8')
        juegos_csv = set(df_csv['nombre'].dropna().tolist())
    except FileNotFoundError:
        juegos_csv = set()
    juegos = sorted(juegos_mongo.union(juegos_csv), key=str)
    return render_template("agregar_resena.html", juegos=juegos)

@app.route("/agregar_juego", methods=["POST"])
@login_required
def agregar_juego():
    try:
        form = request.form
        user_id = session.get("usuario")

        nuevo_juego = {
            "nombre":     form['nombre'],
            "plataforma": form['plataforma'],
            "genero":     form['genero'],
            "editor":     form.get('editor', ''),
            "Developer":  form.get('Developer', '')
        }

        # Campos numéricos opcionales
        if form.get('Year_of_Release'):
            nuevo_juego["Year_of_Release"] = int(form['Year_of_Release'])

        for f, key in [
            ('ventas_globales', 'ventas_globales'),
            ('NA_Sales', 'NA_Sales'),
            ('EU_Sales', 'EU_Sales'),
            ('JP_Sales', 'JP_Sales'),
            ('Other_Sales', 'Other_Sales')
        ]:
            val = form.get(f)
            if val:
                nuevo_juego[key] = float(val)

        # Puntajes y conteos
        if form.get('Critic_Score'):
            nuevo_juego["Critic_Score"] = int(form['Critic_Score'])
        if form.get('Critic_Count'):
            nuevo_juego["Critic_Count"] = int(form['Critic_Count'])
        if form.get('User_Score'):
            nuevo_juego["User_Score"] = form['User_Score']
        if form.get('User_Count'):
            nuevo_juego["User_Count"] = int(form['User_Count'])

        if form.get('Rating'):
            nuevo_juego["Rating"] = form['Rating']

        nuevo_juego.update({
            "user_id": user_id,
            "status": "pending",
            "submitted_at": datetime.utcnow()
        })

        db.juegos_pendientes.insert_one(nuevo_juego)
        flash("Tu juego ha quedado en espera de revisión.", "success")
        return redirect_by_role()
    except Exception as e:
        flash(f"Error al procesar el formulario: {e}", "error")
        return redirect(url_for('formulario_agregar_juego'))

@app.route("/agregar_resena", methods=["GET", "POST"])
@login_required
def agregar_resena():
    if request.method == "GET":
        juegos_db = set(db.juegos.distinct("nombre"))
        try:
            df_csv = pd.read_csv(CSV_FILE, encoding='utf-8')
            juegos_csv = set(df_csv['nombre'].dropna().tolist())
        except FileNotFoundError:
            juegos_csv = set()
        juegos = sorted(juegos_db.union(juegos_csv), key=str)
        return render_template("agregar_resena.html", juegos=juegos)
    
    if request.method == "POST":
        try:
            form = request.form

            # Obtener nombre del usuario logueado
            user_id = session.get("usuario")
            usuario = db.usuarios.find_one({"_id": user_id})
            autor = usuario["usuario"] if usuario and "usuario" in usuario else "Anónimo"

            fecha = datetime.utcnow()

            nueva_resena = {
                "name": form['nombre'].strip(),
                "autor": autor,
                "fecha": fecha,
                "valoracion": float(form.get('estrellas', 3)),  # Valoración general en estrellas
                "comentario": form.get('reseña', '').strip(),
                "reseña": form.get('reseña', '').strip(),
                "jugabilidad": int(form.get('jugabilidad', 5)),
                "historia": int(form.get('historia', 5)),
                "graficos": int(form.get('graficos', 5)),
                "sonido": int(form.get('sonido', 5)),
                "recomendado": form.get('recomendado', 'no'),

                # Metadatos
                "user_id": user_id,
                "status": "pending",
                "submitted_at": datetime.utcnow()
            }

            db.resenas_pendientes.insert_one(nueva_resena)
            flash("Tu reseña ha quedado en espera de aprobación.", "success")
            return redirect_by_role()

        except Exception as e:
            flash(f"Error al procesar el formulario: {e}", "error")
            return redirect(url_for('agregar_resena'))
@app.route("/buscar", methods=["POST"])
@login_required
def buscar():
    nombre_juego = request.form.get("juego", "")
    hashtag      = request.form.get("hashtag", "")
    plataforma   = request.form.get("plataforma", "")
    genero       = request.form.get("genero", "")

    # 1) Filtrar juegos
    consulta = {}
    if nombre_juego:
        consulta["nombre"] = {"$regex": nombre_juego, "$options": "i"}
    if genero:
        consulta["genero"] = {"$regex": genero, "$options": "i"}
    if plataforma:
        consulta["plataforma"] = {"$regex": plataforma, "$options": "i"}
    juegos_resultados = list(db.juegos.find(consulta))

    # 2) Comentarios genéricos
    comentarios_resultados = list(db.comentarios.find({
        **({"name": {"$regex": nombre_juego, "$options": "i"}} if nombre_juego else {}),
        **({"plataforma": {"$regex": plataforma, "$options": "i"}} if plataforma else {})
    }))

    # 3) Hashtags
    hashtags_resultados = list(db.hashtags.find({
        **({"red_social": {"$regex": hashtag, "$options": "i"}} if hashtag else {}),
        **({"genres": {"$regex": hashtag, "$options": "i"}} if hashtag else {})
    }))

    # 4) Reseñas de usuarios
    filtros_resenas = {}
    if nombre_juego:
        filtros_resenas["name"] = {"$regex": nombre_juego, "$options": "i"}
    if plataforma:
        filtros_resenas["plataforma"] = {"$regex": plataforma, "$options": "i"}
    resenas_resultados = list(db.resenas_juegos.find(filtros_resenas))

    # 🔵 Ventas por plataforma
    plataformas_ventas = {}
    for juego in juegos_resultados:
        plat = juego.get("plataforma", "Desconocida")
        ventas = juego.get("ventas_globales", 0)
        plataformas_ventas[plat] = plataformas_ventas.get(plat, 0) + ventas
    fig_plataforma = go.Figure(
        data=[go.Bar(x=list(plataformas_ventas.keys()),
                     y=list(plataformas_ventas.values()))]
    )
    fig_plataforma.update_layout(
        title="Ventas por Plataforma",
        xaxis_title="Plataforma",
        yaxis_title="Ventas Globales (millones)"
    )
    graph_plataforma_html = fig_plataforma.to_html(full_html=False)

    # 🟢 Ventas por región
    ventas_por_region = {"NA": 0, "EU": 0, "JP": 0, "Other": 0}
    for juego in juegos_resultados:
        ventas_por_region["NA"]    += juego.get("NA_Sales", 0)
        ventas_por_region["EU"]    += juego.get("EU_Sales", 0)
        ventas_por_region["JP"]    += juego.get("JP_Sales", 0)
        ventas_por_region["Other"] += juego.get("Other_Sales", 0)
    fig_region = go.Figure(
        data=[go.Bar(x=list(ventas_por_region.keys()),
                     y=list(ventas_por_region.values()))]
    )
    fig_region.update_layout(
        title="Ventas por Región",
        xaxis_title="Región",
        yaxis_title="Ventas (millones)"
    )
    graph_region_html = fig_region.to_html(full_html=False)

    # 🟡 Ventas por género
    ventas_por_genero = {}
    for juego in juegos_resultados:
        gen = juego.get("genero", "Desconocido")
        ventas = juego.get("ventas_globales", 0)
        ventas_por_genero[gen] = ventas_por_genero.get(gen, 0) + ventas
    fig_genero = go.Figure(
        data=[go.Pie(labels=list(ventas_por_genero.keys()),
                     values=list(ventas_por_genero.values()))]
    )
    fig_genero.update_layout(title="Ventas por Género")
    graph_genero_html = fig_genero.to_html(full_html=False)

    # 🟠 Calificaciones Críticos vs Usuarios
    calificaciones = {"nombres": [], "criticos": [], "usuarios": []}
    for juego in juegos_resultados:
        nombre = juego.get("nombre", "Desconocido")
        critic = juego.get("Critic_Score", 0)
        user   = juego.get("User_Score", 0)
        if isinstance(user, str) and user:
            try:
                user = float(user) * 10
            except ValueError:
                user = 0
        calificaciones["nombres"].append(nombre)
        calificaciones["criticos"].append(critic)
        calificaciones["usuarios"].append(user)
    fig_calificaciones = go.Figure()
    fig_calificaciones.add_trace(
        go.Bar(x=calificaciones["nombres"],
               y=calificaciones["criticos"],
               name="Críticos")
    )
    fig_calificaciones.add_trace(
        go.Bar(x=calificaciones["nombres"],
               y=calificaciones["usuarios"],
               name="Usuarios")
    )
    fig_calificaciones.update_layout(
        title="Calificaciones de Críticos vs Usuarios",
        xaxis_title="Juego",
        yaxis_title="Puntuación",
        barmode='group'
    )
    graph_calificaciones_html = fig_calificaciones.to_html(full_html=False)

    # 🔴 Valoración media de reseñas de usuarios
    valoracion_media = {}
    conteo_resenas = {}
    for resena in resenas_resultados:
        nombre = resena.get("name", "Desconocido")
        valoracion = resena.get("valoracion", 0)  # Puntuación de 1 a 5
        if valoracion:
            conteo_resenas[nombre] = conteo_resenas.get(nombre, 0) + 1
            valoracion_media[nombre] = valoracion_media.get(nombre, 0) + valoracion
    
    # Promedio de las valoraciones
    for nombre in valoracion_media:
        valoracion_media[nombre] = valoracion_media[nombre] / conteo_resenas[nombre]
    
    fig_valoracion = go.Figure(
        data=[go.Bar(
            x=list(valoracion_media.keys()),
            y=list(valoracion_media.values()),
            text=[f"{v:.1f} ⭐" for v in valoracion_media.values()],
            textposition="auto"
        )]
    )
    fig_valoracion.update_layout(
        title="Valoración Media de Usuarios",
        xaxis_title="Juego",
        yaxis_title="Valoración (1-5)",
        yaxis=dict(range=[0, 5])
    )
    graph_valoracion_html = fig_valoracion.to_html(full_html=False)

    return render_template(
        "resultados.html",
        juego=nombre_juego,
        juegos=juegos_resultados,
        comentarios=comentarios_resultados,
        hashtags=hashtags_resultados,
        resenas=resenas_resultados,
        graph_region=graph_region_html,
        graph_genero=graph_genero_html,
        graph_calificaciones=graph_calificaciones_html,
        graph_plataforma=graph_plataforma_html,
        graph_valoracion=graph_valoracion_html
    )

@app.route("/registro", methods=["GET", "POST"])
def registro():
    if 'usuario' in session:
        return redirect_by_role()
    if request.method == "POST":
        usuario    = request.form["usuario"]
        correo     = request.form["correo"]
        contraseña = request.form["contraseña"]
        if db.usuarios.find_one({"usuario": usuario}):
            flash("El usuario ya está registrado.", "error")
            return redirect(url_for("registro"))
        hash_pwd = generate_password_hash(contraseña)
        db.usuarios.insert_one({
            "usuario":    usuario,
            "correo":     correo,
            "contraseña": hash_pwd,
            "rol":        "usuario"
        })
        flash("Registro exitoso. Ya puedes iniciar sesión.", "success")
        return redirect(url_for("login"))
    return render_template("registro.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if 'usuario' in session:
        return redirect_by_role()

    if request.method == "POST":
        usuario = request.form["usuario"]
        pwd     = request.form.get("contraseña", "")
        user_db = db.usuarios.find_one({"usuario": usuario})

        if user_db and check_password_hash(user_db["contraseña"], pwd):
            # ----------------------------------------------------
            # 1) Preparamos los campos para el registro de sesión
            # ----------------------------------------------------
            ahora = datetime.now()
            fecha_str = ahora.strftime("%Y-%m-%d")
            hora_str  = ahora.strftime("%H:%M")
            ip_cliente = request.remote_addr or "desconocida"

            # ----------------------------------------------------
            # 2) Insertamos en la colección "registros"
            # ----------------------------------------------------
            db.registros.insert_one({
                "usuario": usuario,
                "correo":  user_db.get("correo", ""),
                "fecha":   fecha_str,
                "hora":    hora_str,
                "ip":      ip_cliente
            })
            # ----------------------------------------------------

            # ----------------------------------------------------
            # 3) Guardamos la sesión y redirigimos según el rol
            # ----------------------------------------------------
            session["usuario"] = usuario
            session["rol"]     = user_db.get("rol", "usuario")
            flash(f"Bienvenido, {usuario}", "success")
            return redirect_by_role()

        flash("Usuario o contraseña incorrectos", "error")
        return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("usuario", None)
    session.pop("rol", None)
    flash("Has cerrado sesión", "info")
    return redirect(url_for("login"))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "usuario" not in session:
            return redirect(url_for("login"))
        usuario = db.usuarios.find_one({"usuario": session["usuario"]})
        if not usuario or usuario.get("rol") != "admin":
            flash("Acceso denegado. Solo administradores.", "error")
            return redirect(url_for("inicio"))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/ingresos-sesion")
@login_required
def ingresos_sesion():
    # 1) Obtenemos todos los documentos de la colección "registros"
    registros_cursor = db.registros.find().sort([("fecha", -1), ("hora", -1)])
    
    # 2) Convertimos el cursor a lista de diccionarios
    registros = []
    for r in registros_cursor:
        # Asegurarnos de convertir la fecha a string YYYY-MM-DD
        # Si "fecha" está almacenada como ISODate, hacemos:
        fecha_obj = r.get("fecha")
        fecha_str = fecha_obj.strftime("%Y-%m-%d") if hasattr(fecha_obj, "strftime") else r.get("fecha", "")
        
        registros.append({
            "usuario": r.get("usuario", ""),
            "correo":  r.get("correo", ""),
            "fecha":   fecha_str,
            "hora":    r.get("hora", ""),
            "ip":      r.get("ip", "")
        })
    
    # 3) Pasamos esa lista al template
    return render_template("registros.html", registros=registros)


@app.route("/registro-usuario", methods=["GET", "POST"])
@admin_required
def registrar_usuario():
    if request.method == "POST":
        usuario    = request.form["usuario"]
        correo     = request.form["correo"]
        contraseña = request.form["contraseña"]
        rol        = request.form["rol"]

        if db.usuarios.find_one({"usuario": usuario}):
            flash("El usuario ya existe.", "error")
            return redirect(url_for("registrar_usuario"))

        hash_pwd = generate_password_hash(contraseña)
        db.usuarios.insert_one({
            "usuario":    usuario,
            "correo":     correo,
            "contraseña": hash_pwd,
            "rol":        rol
        })

        flash("Usuario registrado exitosamente.", "success")
        return redirect(url_for("registrar_usuario"))

    # Mostrar lista de usuarios
    usuarios = list(db.usuarios.find({}, {"_id": 0, "usuario": 1, "correo": 1, "rol": 1}))
    return render_template("registro_admin.html", usuarios=usuarios)

# Moderación de Juegos Pendientes
@app.route('/aceptar-juegos', methods=['GET'])
@login_required
def aceptar_juegos():
    if session.get('rol') != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect_by_role()
    juegos_pendientes = list(db.juegos_pendientes.find({"status": "pending"}))
    return render_template('revisar_juegos.html', juegos_pendientes=juegos_pendientes)


@app.route('/aceptar_juego', methods=['POST'])
@login_required
def aceptar_juego():
    if session.get('rol') != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect_by_role()

    juego_id = request.form.get('id')
    juego = db.juegos_pendientes.find_one({"_id": ObjectId(juego_id)})
    if juego:
        del juego['_id']
        db.juegos.insert_one(juego)
        db.juegos_pendientes.delete_one({"_id": ObjectId(juego_id)})
        flash("Juego aceptado correctamente", "success")
    else:
        flash("Juego no encontrado", "error")

    return redirect(url_for('aceptar_juegos'))


@app.route('/rechazar_juego', methods=['POST'])
@login_required
def rechazar_juego():
    if session.get('rol') != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect_by_role()

    juego_id = request.form.get('id')
    result = db.juegos_pendientes.delete_one({"_id": ObjectId(juego_id)})
    if result.deleted_count:
        flash("Juego rechazado", "warning")
    else:
        flash("Juego no encontrado", "error")

    return redirect(url_for('aceptar_juegos'))


# Moderación de Reseñas Pendientes
@app.route('/aceptar-reseñas', methods=['GET'])
@login_required
def aceptar_resenas():
    if session.get('rol') != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect_by_role()
    resenas_pendientes = list(db.resenas_pendientes.find({"status": "pending"}))
    return render_template('revisar_resena.html', resenas_pendientes=resenas_pendientes)

@app.route('/confirmar_resena/<id>')
@login_required
def confirmar_resena(id):
    if session.get('rol') != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect_by_role()
    resena = db.resenas_pendientes.find_one({"_id": ObjectId(id)})
    if resena:
        del resena['_id']  # Eliminamos el id de MongoDB para insertarlo en la nueva colección
        db.resenas_juegos.insert_one(resena)  # Insertamos la reseña en la colección "resenas"
        db.resenas_pendientes.delete_one({"_id": ObjectId(id)})  # Eliminamos la reseña de "resenas_pendientes"
        flash("Reseña aceptada correctamente", "success")
    return redirect(url_for('aceptar_resenas'))

@app.route('/rechazar_resena/<id>')
@login_required
def rechazar_resena(id):
    if session.get('rol') != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect_by_role()
    db.resenas_pendientes.delete_one({"_id": ObjectId(id)})  # Eliminamos la reseña de "resenas_pendientes"
    flash("Reseña rechazada", "warning")
    return redirect(url_for('aceptar_resenas'))

if __name__ == "__main__":
    app.run(debug=True)
