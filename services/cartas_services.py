import random
from database import guardar_carta, buscar_carta_dict, actualizar_carta, eliminar_carta_bd
from services.dolls_services import asignar_doll_disponible, get_dolls_activas

# Estados unificados
ESTADOS = ["en espera", "borrador", "revisado", "enviado"]


def crear_carta(datos):
    """
    Crea una carta y asigna automáticamente una Doll ACTIVA disponible (menos de 5 cartas).
    Si no hay Dolls activas, la carta queda en estado 'en espera'.
    """
    dolls_activas = get_dolls_activas()

    if not dolls_activas:
        # No hay dolls activas → dejamos carta en espera
        datos["estado"] = "en espera"
        datos["doll_id"] = None
        return guardar_carta(datos)

    doll = asignar_doll_disponible()
    if not doll:
        # Todas las dolls activas están ocupadas → carta queda en espera
        datos["estado"] = "en espera"
        datos["doll_id"] = None
        return guardar_carta(datos)

    # Si hay doll disponible, la asignamos
    datos["doll_id"] = doll["id"]
    datos["estado"] = datos.get("estado", "borrador")
    return guardar_carta(datos)


def crear_carta_para_cliente(cliente_id):
    """
    Se llama justo después de crear un cliente.
    Si hay Dolls activas, asigna una Doll con espacio y un estado aleatorio.
    Si no hay Dolls activas, la carta queda en 'en espera'.
    """
    dolls_activas = get_dolls_activas()

    if not dolls_activas:
        # Guardamos en espera
        datos = {
            "cliente_id": cliente_id,
            "doll_id": None,
            "estado": "en espera",
            "contenido": ""
        }
        return guardar_carta(datos)

    doll = asignar_doll_disponible()
    if not doll:
        # Guardamos en espera porque todas las activas están llenas
        datos = {
            "cliente_id": cliente_id,
            "doll_id": None,
            "estado": "en espera",
            "contenido": ""
        }
        return guardar_carta(datos)

    # Si hay doll disponible
    estado = random.choice(["borrador", "revisado", "enviado"])
    datos = {
        "cliente_id": cliente_id,
        "doll_id": doll["id"],
        "estado": estado,
        "contenido": ""
    }
    return guardar_carta(datos)


def cambiar_estado_carta(carta_id, nuevo_estado):
    """
    Cambia el estado de la carta siguiendo el flujo:
    borrador → revisado → enviado.
    No aplica a cartas en 'en espera'.
    """
    carta = buscar_carta_dict(carta_id)
    if not carta:
        raise Exception("Carta no encontrada")

    estado_actual = carta["estado"]

    if estado_actual == "en espera":
        raise Exception("No se puede cambiar estado de una carta en espera hasta que tenga Doll asignada")

    if (estado_actual == "borrador" and nuevo_estado == "revisado") or \
       (estado_actual == "revisado" and nuevo_estado == "enviado"):
        actualizar_carta(carta_id, {"estado": nuevo_estado})
    else:
        raise Exception("Cambio de estado inválido")


def eliminar_carta(carta_id):
    """
    Elimina una carta solo si está en estado 'borrador' o 'en espera'.
    """
    carta = buscar_carta_dict(carta_id)
    if not carta:
        raise Exception("Carta no encontrada")

    if carta["estado"] not in ["borrador", "en espera"]:
        raise Exception("Solo se pueden eliminar cartas en borrador o en espera")

    eliminar_carta_bd(carta_id)
