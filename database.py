from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2
from config import DB_CONFIG
from datetime import date
import random

app = Flask(__name__)
app.secret_key = "clave_secreta_segura"

# Se definen los estados de una carta
ESTADOS = ["borrador", "revisado", "enviado"]

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

# Completar datos de una Doll
def completar_datos_faltantes(doll):
    """
    Recibe un diccionario con los datos de una Doll
    y completa valores aleatorios si faltan.
    """
    if not doll.get("ciudad"):
        doll["ciudad"] = random.choice(["Londres", "París", "Roma", "Madrid"])
    if not doll.get("edad"):
        doll["edad"] = random.randint(15, 30)
    if not doll.get("descripcion"):
        doll["descripcion"] = random.choice([
            "Una doll misteriosa.",
            "Siempre lista para entregar cartas.",
            "Con un gran corazón y determinación.",
            "Apasionada por su trabajo."
        ])
    return doll

# FUNCIONES PARA CARTAS 
def guardar_carta(datos):
    """
    Inserta una carta en la base de datos y retorna el ID generado.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO cartas (cliente_id, doll_id, fecha, estado, contenido)
        VALUES (%s, %s, CURRENT_DATE, %s, %s)
        RETURNING id;
    """, (
        datos.get("cliente_id"),
        datos.get("doll_id"),
        datos.get("estado", "borrador"),
        datos.get("contenido", "")
    ))
    carta_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return carta_id

def buscar_carta_dict(carta_id):
    """
    Busca una carta y la retorna como diccionario.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, cliente_id, doll_id, fecha, estado, contenido
        FROM cartas WHERE id = %s;
    """, (carta_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return None
    return {
        "id": row[0],
        "cliente_id": row[1],
        "doll_id": row[2],
        "fecha": row[3],
        "estado": row[4],
        "contenido": row[5]
    }

def actualizar_carta(carta_id, datos):
    """
    Actualiza una carta con los datos proporcionados.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    set_clauses = []
    values = []
    for campo, valor in datos.items():
        set_clauses.append(f"{campo}=%s")
        values.append(valor)
    values.append(carta_id)
    query = f"UPDATE cartas SET {', '.join(set_clauses)} WHERE id=%s"
    cur.execute(query, values)
    conn.commit()
    cur.close()
    conn.close()

def eliminar_carta_bd(carta_id):
    """
    Elimina una carta de la base de datos.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM cartas WHERE id = %s", (carta_id,))
    conn.commit()
    cur.close()
    conn.close()

# HOME
@app.route('/')
def home():
    return render_template('index.html')

# DOLLS 
@app.route('/dolls')
def listar_dolls():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM dolls ORDER BY id ASC;")
    dolls = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('dolls.html', dolls=dolls)

@app.route('/dolls/nuevo', methods=['GET', 'POST'])
def nuevo_doll():
    if request.method == 'POST':
        doll = {
            "nombre": request.form.get("nombre"),
            "ciudad": request.form.get("ciudad"),
            "edad": request.form.get("edad"),
            "descripcion": request.form.get("descripcion"),
            "estado": request.form.get("estado"),
        }

        # completar datos faltantes
        doll = completar_datos_faltantes(doll)

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO dolls (nombre, ciudad, edad, descripcion, estado, cartas_en_proceso) VALUES (%s, %s, %s, %s, %s, 0)",
            (doll["nombre"], doll["ciudad"], doll["edad"], doll["descripcion"], doll["estado"])
        )
        conn.commit()
        cur.close()
        conn.close()
        flash("Doll creada correctamente con datos sincronizados", "success")
        return redirect(url_for('listar_dolls'))
    return render_template('form_doll.html')

@app.route('/dolls/editar/<int:id>', methods=['GET', 'POST'])
def editar_doll(id):
    conn = get_db_connection()
    cur = conn.cursor()
    if request.method == 'POST':
        doll = {
            "nombre": request.form.get("nombre"),
            "ciudad": request.form.get("ciudad"),
            "edad": request.form.get("edad"),
            "descripcion": request.form.get("descripcion"),
            "estado": request.form.get("estado"),
        }

        doll = completar_datos_faltantes(doll)

        cur.execute(
            "UPDATE dolls SET nombre=%s, ciudad=%s, edad=%s, descripcion=%s, estado=%s WHERE id=%s",
            (doll["nombre"], doll["ciudad"], doll["edad"], doll["descripcion"], doll["estado"], id)
        )
        conn.commit()
        cur.close()
        conn.close()
        flash("Doll actualizada con datos sincronizados", "info")
        return redirect(url_for('listar_dolls'))
    cur.execute("SELECT * FROM dolls WHERE id=%s", (id,))
    doll = cur.fetchone()
    cur.close()
    conn.close()
    return render_template('form_doll.html', doll=doll)

@app.route('/dolls/eliminar/<int:id>')
def eliminar_doll(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM dolls WHERE id=%s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("Doll eliminada", "danger")
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
            "INSERT INTO clientes (nombre, ciudad, motivo, contacto) VALUES (%s, %s, %s, %s) RETURNING id;",
            (request.form['nombre'], request.form['ciudad'], request.form['motivo'], request.form['contacto'])
        )
        cliente_id = cur.fetchone()[0]

        cur.execute("SELECT id FROM dolls ORDER BY RANDOM() LIMIT 1;")
        doll = cur.fetchone()
        doll_id = doll[0] if doll else None

        estado = random.choice(ESTADOS)

        if doll_id:
            cur.execute(
                "INSERT INTO cartas (cliente_id, doll_id, fecha, estado, contenido) VALUES (%s, %s, %s, %s, %s)",
                (cliente_id, doll_id, date.today(), estado, "")
            )

        conn.commit()
        cur.close()
        conn.close()
        flash("Cliente creado correctamente (y carta generada)", "success")
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

# CARTAS 
@app.route('/cartas')
def listar_cartas():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT cartas.id, clientes.nombre, dolls.nombre, cartas.fecha, cartas.estado, cartas.contenido
        FROM cartas
        JOIN clientes ON cartas.cliente_id = clientes.id
        JOIN dolls ON cartas.doll_id = dolls.id
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
    cur.execute("""
        SELECT * FROM dolls
        WHERE estado = 'activo' AND cartas_en_proceso < 5
        ORDER BY cartas_en_proceso ASC
        LIMIT 1;
    """)
    doll = cur.fetchone()
    if not doll:
        cur.close()
        conn.close()
        flash("No hay Dolls disponibles para asignar", "warning")
        return redirect(url_for('listar_cartas'))
    if request.method == 'POST':
        estado = random.choice(ESTADOS)
        cur.execute(
            "INSERT INTO cartas (cliente_id, doll_id, fecha, estado, contenido) VALUES (%s, %s, %s, %s, %s)",
            (request.form['cliente_id'], doll[0], date.today(), estado, request.form['contenido'])
        )
        conn.commit()
        cur.close()
        conn.close()
        flash("Carta creada correctamente", "success")
        return redirect(url_for('listar_cartas'))
    cur.close()
    conn.close()
    return render_template('form_carta.html', clientes=clientes, doll=doll)

@app.route('/cartas/editar/<int:id>', methods=['GET', 'POST'])
def editar_carta(id):
    conn = get_db_connection()
    cur = conn.cursor()
    if request.method == 'POST':
        cur.execute(
            "UPDATE cartas SET contenido=%s, estado=%s WHERE id=%s",
            (request.form['contenido'], request.form['estado'], id)
        )
        conn.commit()
        cur.close()
        conn.close()
        flash("Carta actualizada", "info")
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
    if carta and carta[0] == 'borrador':
        cur.execute("DELETE FROM cartas WHERE id=%s", (id,))
        conn.commit()
        flash("Carta eliminada", "danger")
    else:
        flash("Solo se pueden eliminar cartas en estado 'borrador'", "warning")
    cur.close()
    conn.close()
    return redirect(url_for('listar_cartas'))

#  REPORTES 
@app.route('/reporte_dolls')
def reporte_dolls():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM v_reporte_doll ORDER BY id;")
    reporte = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('v_reporte_doll.html', reporte=reporte)

if __name__ == '__main__':
    app.run(debug=True)

def obtener_reportes_dolls():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT doll_id, doll_nombre, total_cartas, cartas_borrador, cartas_revisado, cartas_enviado FROM reportes_dolls")
    reportes = cur.fetchall()
    cur.close()
    conn.close()
    return reportes
