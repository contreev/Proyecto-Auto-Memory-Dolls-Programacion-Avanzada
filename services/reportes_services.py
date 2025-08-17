from database import get_db_connection

def generar_reporte_doll(doll_id):
    conn = get_db_connection()
    cur = conn.cursor()

    # Total de cartas
    cur.execute("SELECT COUNT(*) FROM cartas WHERE doll_id = %s", (doll_id,))
    total_cartas = cur.fetchone()[0]

    # Cartas en borrador
    cur.execute("SELECT COUNT(*) FROM cartas WHERE doll_id = %s AND estado = 'borrador'", (doll_id,))
    cartas_borrador = cur.fetchone()[0]

    # Cartas en proceso (estado = 'revisado')
    cur.execute("SELECT COUNT(*) FROM cartas WHERE doll_id = %s AND estado = 'revisado'", (doll_id,))
    cartas_proceso = cur.fetchone()[0]

    # Cartas enviadas
    cur.execute("SELECT COUNT(*) FROM cartas WHERE doll_id = %s AND estado = 'enviado'", (doll_id,))
    cartas_enviadas = cur.fetchone()[0]

    # Clientes distintos
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
    """
    Devuelve lista de todas las dolls con sus métricas
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, nombre, estado FROM dolls ORDER BY id ASC")
    dolls = cur.fetchall()
    cur.close()
    conn.close()

    reporte = []
    for doll in dolls:
        doll_id, nombre, estado = doll
        metrics = generar_reporte_doll(doll_id)
        reporte.append({
            "id": doll_id,
            "nombre": nombre,
            "estado": estado,
            **metrics
        })
    return reporte
