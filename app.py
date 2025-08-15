from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2
from config import DB_CONFIG
from datetime import date

app = Flask(__name__)
app.secret_key = "clave_secreta_segura"

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

@app.route('/')
def home():
    return render_template('index.html')

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
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO dolls (nombre, edad, estado, cartas_en_proceso) VALUES (%s, %s, %s, 0)",
            (request.form['nombre'], request.form['edad'], request.form['estado'])
        )
        conn.commit()
        cur.close()
        conn.close()
        flash("Doll creada correctamente", "success")
        return redirect(url_for('listar_dolls'))
    return render_template('form_doll.html')

@app.route('/dolls/editar/<int:id>', methods=['GET', 'POST'])
def editar_doll(id):
    conn = get_db_connection()
    cur = conn.cursor()
    if request.method == 'POST':
        cur.execute(
            "UPDATE dolls SET nombre=%s, edad=%s, estado=%s WHERE id=%s",
            (request.form['nombre'], request.form['edad'], request.form['estado'], id)
        )
        conn.commit()
        cur.close()
        conn.close()
        flash("Doll actualizada", "info")
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
            "INSERT INTO clientes (nombre, ciudad, motivo, contacto) VALUES (%s, %s, %s, %s)",
            (request.form['nombre'], request.form['ciudad'], request.form['motivo'], request.form['contacto'])
        )
        conn.commit()
        cur.close()
        conn.close()
        flash("Cliente creado correctamente", "success")
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
        cur.execute(
            "INSERT INTO cartas (cliente_id, doll_id, fecha, estado, contenido) VALUES (%s, %s, %s, %s, %s)",
            (request.form['cliente_id'], doll[0], date.today(), 'borrador', request.form['contenido'])
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