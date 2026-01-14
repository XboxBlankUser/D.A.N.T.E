# ASCII ONLY
# client_module.py - SIN TILDES - VERSION FINAL

import time
from common_utils import (
    cargar_casilleros, guardar_casilleros,
    cargar_bd_creditos, operar_creditos,
    limpiar_pantalla, leer_tarjeta, esperar_retiro_tarjeta,
    ejecutar_escaneo_facial, cargar_estado,
    obtener_input_hibrido
)
from locker_hardware import activar_casillero_fisico

def numero_casillero_valido(num):
    if not num.isdigit(): return False
    n = int(num)
    return 1 <= n <= 12

def asignar_casillero(casilleros, nombre_usuario, numero_casillero):
    if numero_casillero not in casilleros:
        return ("DENEGAR", "Ese casillero no existe.")
    duenio = casilleros[numero_casillero]
    if duenio == "Nadie":
        casilleros[numero_casillero] = nombre_usuario
        guardar_casilleros(casilleros)
        return ("OK", "Asignado.")
    if duenio == nombre_usuario:
        return ("DENEGAR", "Ya es tuyo.")
    return ("DENEGAR", "Ocupado.")

# --- FUNCIONES DE ACCION (Retornan True si finalizan, False si cancelan) ---

def cliente_reservar(lector):
    limpiar_pantalla()
    estado = cargar_estado()
    if estado.get("bloqueado", False):
        print("SISTEMA BLOQUEADO.")
        time.sleep(3)
        return True # Finaliza y saca al usuario

    print("--- Reservar Tu Casillero ---")
    usuario = ejecutar_escaneo_facial()
    if not usuario: 
        return False # Cancelo, vuelve al menu

    print("Dime el numero (1-12) o di 'Cancelar'.")
    locker = obtener_input_hibrido("Cual prefieres?", ["uno", "dos", "tres", "cancelar", "volver"])
    
    if locker in ["cancelar", "volver", "salir"]:
        return False # Solo regresa al menu

    if not numero_casillero_valido(locker):
        print(f"Numero '{locker}' no valido.")
        time.sleep(3)
        return False # Error leve, vuelve al menu

    casilleros = cargar_casilleros()
    status, msg = asignar_casillero(casilleros, usuario, locker)

    if status == "DENEGAR":
        print("Ups:", msg)
        print("Regresando al inicio en 5 segundos...")
        time.sleep(5)
        return True # Finaliza el intento

    print("Acerca tu tarjeta para pagar 1 credito...")
    uid = leer_tarjeta(lector)
    if uid is None:
        print("Tiempo agotado.")
        casilleros[locker] = "Nadie" # Revertir
        guardar_casilleros(casilleros)
        time.sleep(3)
        return True # Fallo proceso, reinicia a Bienvenida

    esperar_retiro_tarjeta(lector)
    db = cargar_bd_creditos()
    ok = operar_creditos(db, uid, 1)

    if not ok:
        casilleros[locker] = "Nadie"
        guardar_casilleros(casilleros)
        print("Saldo insuficiente.")
        print("Regresando al inicio en 5 segundos...")
        time.sleep(5)
        return True

    print(f"Genial! Casillero {locker} reservado.")
    activar_casillero_fisico(locker)
    print("Regresando al inicio en 5 segundos...")
    time.sleep(5)
    return True # EXITO, reinicia a Bienvenida

def cliente_abrir():
    limpiar_pantalla()
    if cargar_estado().get("bloqueado", False):
        print("SISTEMA BLOQUEADO.")
        time.sleep(3)
        return True

    print("--- Abrir Casillero ---")
    usuario = ejecutar_escaneo_facial()
    if not usuario: return False

    casilleros = cargar_casilleros()
    mios = [n for n, d in casilleros.items() if d == usuario]

    if not mios:
        print("No tienes casilleros.")
        print("Regresando al inicio en 5 segundos...")
        time.sleep(5)
        return True

    locker_a_abrir = None
    if len(mios) == 1:
        locker_a_abrir = mios[0]
        print(f"Abriendo {locker_a_abrir}...")
    else:
        print("Tienes:", ", ".join(mios))
        locker = obtener_input_hibrido("Cual abrimos?", ["cancelar", "volver"])
        if locker in ["cancelar", "volver"]: return False
        if locker not in mios:
            print("Ese no es tuyo.")
            time.sleep(3)
            return False
        locker_a_abrir = locker

    activar_casillero_fisico(locker_a_abrir)
    print("Listo! Casillero ABIERTO.")
    print("Regresando al inicio en 5 segundos...")
    time.sleep(5)
    return True

def cliente_liberar():
    limpiar_pantalla()
    if cargar_estado().get("bloqueado", False):
        return True

    print("--- Dejar Casillero ---")
    usuario = ejecutar_escaneo_facial()
    if not usuario: return False

    casilleros = cargar_casilleros()
    mios = [n for n, d in casilleros.items() if d == usuario]

    if not mios:
        print("No tienes casilleros para devolver.")
        time.sleep(5)
        return True

    locker_a_liberar = None
    if len(mios) == 1:
        locker_a_liberar = mios[0]
        print(f"Liberando {locker_a_liberar}...")
    else:
        print("Tienes:", ", ".join(mios))
        locker = obtener_input_hibrido("Cual devuelves?", ["cancelar"])
        if locker in ["cancelar", "volver"]: return False
        if locker not in mios: return False
        locker_a_liberar = locker

    activar_casillero_fisico(locker_a_liberar)
    casilleros[locker_a_liberar] = "Nadie"
    guardar_casilleros(casilleros)
    
    print("Casillero devuelto. Gracias!")
    print("Regresando al inicio en 5 segundos...")
    time.sleep(5)
    return True

def menu_cliente(lector):
    """
    Retorna True si DEBE ir a Bienvenida.
    Retorna False si DEBE quedarse en el Menu de Sesion.
    """
    while True:
        limpiar_pantalla()
        print("===== ZONA DE CLIENTES =====")
        print("1. Reservar")
        print("2. Abrir")
        print("3. Liberar")
        print("4. Volver (Menu Anterior)")
        
        op = obtener_input_hibrido("Que necesitas?", 
            ["reservar", "abrir", "liberar", "volver", "salir"])

        resultado_accion = False

        if op in ["reservar", "1"]: 
            resultado_accion = cliente_reservar(lector)
        elif op in ["abrir", "2"]: 
            resultado_accion = cliente_abrir()
        elif op in ["liberar", "3"]: 
            resultado_accion = cliente_liberar()
        elif op in ["volver", "salir", "4"]: 
            return False # NAVEGACION: Se queda en Sesion
        else:
            print("No entendi.")
            time.sleep(1)
            continue

        # Si una accion se completo (True), salimos hasta el Welcome
        if resultado_accion:
            return True