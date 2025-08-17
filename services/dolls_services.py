from database import get_db_connection
import random

# =========================
#    QUERIES BÁSICAS
# =========================

def get_all_dolls():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, nombre, descripcion, estado FROM dolls ORDER BY id ASC")
    dolls = cur.fetchall()
    cur.close()
    conn.close()
    return dolls


def insert_doll(nombre, descripcion):
    conn = get_db_connection()
    cur = conn.cursor()
    # Por defecto una nueva Doll entra como "inactivo"
    cur.execute(
        "INSERT INTO dolls (nombre, descripcion, estado) VALUES (%s, %s, %s)",
        (nombre, descripcion, "inactivo")
    )
    conn.commit()
    cur.close()
    conn.close()


def asignar_doll_disponible():
    """
    Devuelve una Doll ACTIVA con menos de 5 cartas asignadas.
    Si no hay disponible, retorna None.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT d.id, d.nombre
        FROM dolls d
        LEFT JOIN cartas c ON c.doll_id = d.id
        WHERE d.estado = 'activo'
        GROUP BY d.id, d.nombre
        HAVING COUNT(c.id) < 5
        ORDER BY COUNT(c.id) ASC
        LIMIT 1
    """)
    doll = cur.fetchone()
    cur.close()
    conn.close()

    if not doll:
        return None

    return {"id": doll[0], "nombre": doll[1]}


def asignar_doll_aleatoria_id():
    """
    Devuelve el ID de una Doll aleatoria ACTIVA (sin validar límite de 5 cartas).
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM dolls WHERE estado = 'activo' ORDER BY RANDOM() LIMIT 1;")
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else None


def contar_cartas_en_estado(doll_id, estado):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM cartas WHERE doll_id = %s AND estado = %s",
        (doll_id, estado)
    )
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return count


def get_dolls_activas():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, nombre FROM dolls WHERE estado = 'activo'")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{"id": row[0], "nombre": row[1]} for row in rows]


def asignar_carta_a_doll(doll_id):
    """Utilidad de prueba: inserta una carta vacía en borrador para la doll."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO cartas (doll_id, estado) VALUES (%s, 'borrador')", (doll_id,))
    conn.commit()
    cur.close()
    conn.close()

# =========================
#   SINCRONIZACIÓN CARTAS
# =========================

def reasignar_cartas_a_doll(doll_id):
    """
    Asigna cartas en 'en espera' (doll_id IS NULL) a la Doll indicada,
    hasta un máximo total de 5 cartas asignadas a esa Doll.
    Retorna la cantidad de cartas reasignadas.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # ¿Cuántas cartas tiene ya esta doll?
    cur.execute("SELECT COUNT(*) FROM cartas WHERE doll_id = %s", (doll_id,))
    usadas = cur.fetchone()[0]
    cupo_restante = max(0, 5 - usadas)
    if cupo_restante <= 0:
        cur.close()
        conn.close()
        return 0

    # Tomamos las primeras cartas en espera
    cur.execute("""
        SELECT id FROM cartas
        WHERE estado = 'en espera' AND doll_id IS NULL
        ORDER BY id ASC
        LIMIT %s
    """, (cupo_restante,))
    cartas_espera = cur.fetchall()

    reasignadas = 0
    for (carta_id,) in cartas_espera:
        cur.execute("""
            UPDATE cartas
            SET doll_id = %s, estado = 'borrador'
            WHERE id = %s
        """, (doll_id, carta_id))
        reasignadas += 1

    conn.commit()
    cur.close()
    conn.close()
    return reasignadas


def liberar_cartas_de_doll(doll_id):
    """
    Pone en 'en espera' todas las cartas de una Doll (ej. cuando se desactiva o elimina).
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE cartas
        SET doll_id = NULL, estado = 'en espera'
        WHERE doll_id = %s
    """, (doll_id,))
    conn.commit()
    cur.close()
    conn.close()


def activar_doll(doll_id):
    """
    Cambia la doll a ACTIVO y luego intenta absorber cartas en 'en espera'
    hasta completar 5 asignadas a esa doll.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE dolls SET estado = 'activo' WHERE id = %s", (doll_id,))
    conn.commit()
    cur.close()
    conn.close()

    # Reasigna inmediatamente cartas en espera
    return reasignar_cartas_a_doll(doll_id)


def desactivar_doll(doll_id):
    """
    Cambia la doll a INACTIVO y libera todas sus cartas a 'en espera'.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE dolls SET estado = 'inactivo' WHERE id = %s", (doll_id,))
    conn.commit()
    cur.close()
    conn.close()

    liberar_cartas_de_doll(doll_id)
