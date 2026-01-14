# ASCII ONLY
# admin_module.py - SIN TILDES - VERSION FINAL

import time
import json
from locker_hardware import apagar_todo
from common_utils import (
    limpiar_pantalla, cargar_casilleros, guardar_casilleros,
    cargar_bd_creditos, guardar_bd_creditos,
    leer_tarjeta, esperar_retiro_tarjeta, ejecutar_escaneo_facial,
    cargar_admins, guardar_admins,
    cargar_estado, guardar_estado,
    obtener_input_hibrido
)

def admin_registrar():
    limpiar_pantalla()
    print("--- REGISTRO DE NUEVO ADMINISTRADOR ---")
    nombre = ejecutar_escaneo_facial()
    if not nombre: return False

    admins = cargar_admins()
    if nombre in admins:
        print("Ya es administrador.")
        time.sleep(3)
        return False # No es critico, vuelve al menu

    admins[nombre] = True
    guardar_admins(admins)
    print(f"Bienvenido, {nombre}.")
    time.sleep(5)
    return True # Registro OK, reinicia sistema

def admin_login():
    limpiar_pantalla()
    print("--- ACCESO ADMINISTRATIVO ---")
    nombre = ejecutar_escaneo_facial()
    if not nombre: return None
    admins = cargar_admins()
    if nombre not in admins:
        print("No tienes permisos.")
        time.sleep(3)
        return None
    return nombre

def admin_panel_acciones(lector):
    """
    Menu interno del Admin.
    Retorna True si hizo una accion final (Reiniciar).
    Retorna False si dio volver.
    """
    while True:
        limpiar_pantalla()
        print("===== PANEL DE CONTROL =====")
        print("1. Cargar Creditos")
        print("2. Eliminar Tarjeta")
        print("3. Reiniciar Sistema")
        print("4. Bloquear/Desbloquear")
        print("5. Ver Estado")
        print("6. Volver")

        op = obtener_input_hibrido("Comando:", 
            ["cargar", "creditos", "eliminar", "borrar", "reiniciar", 
             "bloquear", "estado", "volver"])

        if op in ["6", "volver", "salir"]:
            return False # Navegacion hacia atras

        # ACCIONES
        if op in ["1", "cargar", "creditos"]: 
            print("Cuanto? (1, 5, 10)...")
            val = obtener_input_hibrido("Monto:", ["uno", "cinco", "diez"])
            monto = 1 # default
            if val in ["1","uno"]: monto=1
            elif val in ["5","cinco"]: monto=5
            elif val in ["10","diez"]: monto=10
            
            print("Pon la tarjeta...")
            uid = leer_tarjeta(lector)
            if uid:
                esperar_retiro_tarjeta(lector)
                db = cargar_bd_creditos()
                db[uid] = db.get(uid,0) + monto
                guardar_bd_creditos(db)
                print(f"Cargado. Saldo: {db[uid]}")
                time.sleep(5)
                return True # Termina tarea, reinicia
        
        elif op in ["2", "eliminar"]:
            print("Pon tarjeta a borrar...")
            uid = leer_tarjeta(lector)
            if uid:
                esperar_retiro_tarjeta(lector)
                db = cargar_bd_creditos()
                if uid in db: del db[uid]
                guardar_bd_creditos(db)
                print("Borrada.")
                time.sleep(5)
                return True

        elif op in ["3", "reiniciar"]:
            guardar_casilleros({str(i): "Nadie" for i in range(1,13)})
            apagar_todo()
            print("Sistema reiniciado.")
            time.sleep(5)
            return True

        elif op in ["4", "bloquear"]:
            st = cargar_estado()
            st["bloqueado"] = not st["bloqueado"]
            guardar_estado(st)
            print("Estado cambiado.")
            time.sleep(3)
            return True

        elif op in ["5", "estado"]:
            c = cargar_casilleros()
            print(json.dumps(c, indent=2))
            print("Esperando 5 seg...")
            time.sleep(5)
            # Ver estado a veces requiere seguir en el menu
            # Si quieres que tambien salga, cambia a 'return True'
            continue 

def menu_admin(lector):
    while True:
        limpiar_pantalla()
        print("===== MENU ADMINISTRADOR =====")
        print("1. Registrar nuevo Admin")
        print("2. Entrar al Panel")
        print("3. Volver")

        op = obtener_input_hibrido("Opcion:", ["registrar", "panel", "volver"])

        fin = False
        if op in ["1", "registrar"]: 
            fin = admin_registrar()
        elif op in ["2", "panel"]:
            if admin_login():
                fin = admin_panel_acciones(lector)
        elif op in ["3", "volver"]: 
            return False # Regresa al menu de sesion

        if fin: return True # Regresa a Bienvenida