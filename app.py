from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2
from config import DB_CONFIG
from datetime import date
import random

# Servicios 
from services.cartas_services import (
    cambiar_estado_carta,
    crear_carta,
    crear_carta_para_cliente,
)
from services.dolls_services import (
    activar_doll,
    desactivar_doll,
    liberar_cartas_de_doll,
)

app = Flask(__name__)
app.secret_key = "clave_secreta_segura"

# Solo para selects/etiquetas; la validación real está en cartas_services
ESTADOS = ["en espera", "borrador", "revisado", "enviado"]

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

#  HELPERS DE REPORTES 
def completar_datos_doll(nombre=None, edad=None, estado=None):
    if not nombre or nombre.strip() == "":
        nombre = f"Doll_{random.randint(100,999)}"
    if not edad or str(edad).strip() == "":
        edad = random.randint(18, 40)
    if not estado or estado.strip() == "":
        estado = random.choice(["activo", "inactivo"])
    return nombre, edad, estado

def generar_reporte_doll(doll_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM cartas WHERE doll_id = %s", (doll_id,))
    total_cartas = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM cartas WHERE doll_id = %s AND estado = 'borrador'", (doll_id,))
    cartas_borrador = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM cartas WHERE doll_id = %s AND estado = 'revisado'", (doll_id,))
    cartas_proceso = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM cartas WHERE doll_id = %s AND estado = 'enviado'", (doll_id,))
    cartas_enviadas = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT cliente_id) FROM cartas WHERE doll_id = %s", (doll_id,))
    clientes_distintos = cur.fetchone()[0]

    cur.close()
    conn.close()

    return {
        "total_cartas": total_cartas,
        "cartas_borrador": cartas_borrador,
        "cartas_en_proceso": cartas_proceso,
        "enviadas": cartas_enviadas,
        "clientes_unicos": clientes_distintos
    }

def obtener_reporte_dolls():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, nombre, edad, estado FROM dolls ORDER BY id ASC")
    dolls = cur.fetchall()
    cur.close()
    conn.close()

    reporte = []
    for doll in dolls:
        doll_id, nombre, edad, estado = doll
        metrics = generar_reporte_doll(doll_id)
        reporte.append({
            "id": doll_id,
            "nombre": nombre,
            "edad": edad,
            "estado": estado,
            **metrics
        })
    return reporte

# RUTAS PRINCIPALES 


@app.route('/')
def home():
    return render_template('index.html')

# DOLLS 
@app.route('/dolls')
def listar_dolls():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT d.id, d.nombre, d.edad, d.estado,
               COALESCE(
                   (SELECT COUNT(*) FROM cartas c
                    WHERE c.doll_id = d.id AND c.estado = 'revisado'), 0
               ) AS cartas_en_proceso
        FROM dolls d
        ORDER BY d.id ASC;
    """)
    dolls = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('dolls.html', dolls=dolls)

@app.route('/dolls/nuevo', methods=['GET', 'POST'])
def nuevo_doll():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        edad = request.form.get('edad')
        estado = request.form.get('estado')
        nombre, edad, estado = completar_datos_doll(nombre, edad, estado)

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO dolls (nombre, edad, estado) VALUES (%s, %s, %s) RETURNING id",
            (nombre, edad, estado)
        )
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()

        if estado == 'activo':
            try:
                reasignadas = activar_doll(new_id)
                if reasignadas:
                    flash(f"Doll creada y activada. Reasignadas {reasignadas} cartas en espera.", "success")
                else:
                    flash("Doll creada y activada. No había cartas en espera o ya tiene 5.", "info")
            except Exception as e:
                flash(f"Doll creada, pero falló la reasignación: {e}", "warning")
        else:
            flash("Doll creada correctamente (estado inactivo).", "success")

        return redirect(url_for('listar_dolls'))
    return render_template('form_doll.html')

@app.route('/dolls/editar/<int:id>', methods=['GET', 'POST'])
def editar_doll(id):
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        edad = request.form.get('edad')
        estado = request.form.get('estado')  # 'activo' o 'inactivo'

        # Actualiza nombre/edad
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE dolls SET nombre=%s, edad=%s WHERE id=%s", (nombre, edad, id))
        conn.commit()
        cur.close()
        conn.close()

        # Cambiamos estado con side-effects 
        try:
            if estado == 'activo':
                reasignadas = activar_doll(id)
                if reasignadas:
                    flash(f"Doll activada. Se reasignaron {reasignadas} cartas en espera.", "success")
                else:
                    flash("Doll activada. No había cartas en espera o ya tiene 5.", "info")
            else:
                desactivar_doll(id)
                flash("Doll desactivada. Sus cartas fueron puestas en 'en espera'.", "warning")
        except Exception as e:
            flash(f"Error al cambiar estado de la Doll: {e}", "danger")

        return redirect(url_for('listar_dolls'))

    # GET
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM dolls WHERE id=%s", (id,))
    doll = cur.fetchone()
    cur.close()
    conn.close()
    return render_template('form_doll.html', doll=doll)

@app.route('/dolls/eliminar/<int:id>')
def eliminar_doll(id):
    try:
        liberar_cartas_de_doll(id)
    except Exception as e:
        flash(f"No se pudieron liberar las cartas de la Doll: {e}", "warning")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM dolls WHERE id=%s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("Doll eliminada (sus cartas pasaron a 'en espera').", "danger")
    return redirect(url_for('listar_dolls'))

# CLIENTES 
@app.route('/clientes')
def listar_clientes():
    q = request.args.get('q', '')
    ciudad = request.args.get('ciudad', '')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM clientes WHERE nombre ILIKE %s AND ciudad ILIKE %s ORDER BY id ASC",
        (f'%{q}%', f'%{ciudad}%')
    )
    clientes = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('clientes.html', clientes=clientes)

@app.route('/clientes/nuevo', methods=['GET', 'POST'])
def nuevo_cliente():
    if request.method == 'POST':
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO clientes (nombre, ciudad, motivo, contacto) VALUES (%s, %s, %s, %s) RETURNING id",
            (request.form['nombre'], request.form['ciudad'], request.form['motivo'], request.form['contacto'])
        )
        cliente_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()

        try:
            crear_carta_para_cliente(cliente_id)
            flash("Cliente creado (se generó su carta: asignada o en espera).", "success")
        except Exception as e:
            flash(f"Cliente creado, pero no se pudo crear la carta: {e}", "warning")

        return redirect(url_for('listar_clientes'))
    return render_template('form_cliente.html')

@app.route('/clientes/editar/<int:id>', methods=['GET', 'POST'])
def editar_cliente(id):
    conn = get_db_connection()
    cur = conn.cursor()
    if request.method == 'POST':
        cur.execute(
            "UPDATE clientes SET nombre=%s, ciudad=%s, motivo=%s, contacto=%s WHERE id=%s",
            (request.form['nombre'], request.form['ciudad'], request.form['motivo'], request.form['contacto'], id)
        )
        conn.commit()
        cur.close()
        conn.close()
        flash("Cliente actualizado", "info")
        return redirect(url_for('listar_clientes'))
    cur.execute("SELECT * FROM clientes WHERE id=%s", (id,))
    cliente = cur.fetchone()
    cur.close()
    conn.close()
    return render_template('form_cliente.html', cliente=cliente)

@app.route('/clientes/eliminar/<int:id>')
def eliminar_cliente(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM clientes WHERE id=%s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("Cliente eliminado", "danger")
    return redirect(url_for('listar_clientes'))

#  CARTAS 
@app.route('/cartas')
def listar_cartas():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT cartas.id,
               clientes.nombre AS cliente_nombre,
               dolls.nombre   AS doll_nombre,
               cartas.fecha,
               cartas.estado,
               cartas.contenido
        FROM cartas
        JOIN clientes ON cartas.cliente_id = clientes.id
        LEFT JOIN dolls ON cartas.doll_id = dolls.id
        ORDER BY cartas.id ASC;
    """)
    cartas = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('cartas.html', cartas=cartas)

@app.route('/cartas/nuevo', methods=['GET', 'POST'])
def nueva_carta():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM clientes;")
    clientes = cur.fetchall()
    cur.close()
    conn.close()

    if request.method == 'POST':
        datos = {
            "cliente_id": request.form['cliente_id'],
            "contenido": request.form['contenido']
        }
        try:
            crear_carta(datos)
            flash("Carta creada (asignada si había Doll activa; si no, quedó en 'en espera').", "success")
        except Exception as e:
            flash(str(e), "warning")
        return redirect(url_for('listar_cartas'))

    return render_template('form_carta.html', clientes=clientes, doll=None)

@app.route('/cartas/editar/<int:id>', methods=['GET', 'POST'])
def editar_carta(id):
    conn = get_db_connection()
    cur = conn.cursor()
    if request.method == 'POST':
        nuevo_estado = request.form['estado']
        try:
            cambiar_estado_carta(id, nuevo_estado)
            cur.execute(
                "UPDATE cartas SET contenido=%s WHERE id=%s",
                (request.form['contenido'], id)
            )
            conn.commit()
            flash("Carta actualizada", "info")
        except Exception as e:
            flash(str(e), "warning")
        cur.close()
        conn.close()
        return redirect(url_for('listar_cartas'))

    cur.execute("SELECT * FROM cartas WHERE id=%s", (id,))
    carta = cur.fetchone()
    cur.close()
    conn.close()
    return render_template('form_carta.html', carta=carta)

@app.route('/cartas/eliminar/<int:id>')
def eliminar_carta(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT estado FROM cartas WHERE id=%s", (id,))
    carta = cur.fetchone()
    if carta and carta[0] in ('borrador', 'en espera'):
        cur.execute("DELETE FROM cartas WHERE id=%s", (id,))
        conn.commit()
        flash("Carta eliminada", "danger")
    else:
        flash("Solo se pueden eliminar cartas en 'borrador' o 'en espera'.", "warning")
    cur.close()
    conn.close()
    return redirect(url_for('listar_cartas'))

#  REPORTES 
@app.route('/reporte_dolls')
def reporte_dolls():
    reporte = obtener_reporte_dolls()
    return render_template('v_reporte_doll.html', reporte=reporte)


if __name__ == '__main__':
    app.run(debug=True)
