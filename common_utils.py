# ASCII ONLY
# common_utils.py CORREGIDO - Version Final Integrada

import os
import json
import time
from voice_engine import voice_bot

# ... (MANTENER LAS IMPORTACIONES DE FACE RECOGNITION IGUAL QUE ANTES) ...
try:
    from face_recognition_core import recognize_user_face as ejecutar_escaneo_facial, stop_picam
    ESCANEO_FACIAL_HABILITADO = True
except:
    ESCANEO_FACIAL_HABILITADO = False
    def ejecutar_escaneo_facial():
        print("Escaneo facial simulado...")
        # AQUI TAMBIEN USAMOS EL BOT CON NOMBRE
        nombre = voice_bot.listen_command("Por favor, di tu nombre de usuario:")
        return nombre.upper().replace(" ", "_")
    def stop_picam():
        pass

# ... (RUTAS DE ARCHIVOS IGUAL QUE ANTES) ...
ARCHIVO_CASILLEROS = "lockers.json"
ARCHIVO_CREDITOS = "creditos.json"
ARCHIVO_ADMINS = "admins.json"
ARCHIVO_ESTADO = "system_state.json"

# ======================================================
# LOGICA DE INPUT FINAL
# ======================================================

def obtener_input_hibrido(prompt, opciones_clave=None):
    """
    Wrapper para pedir input por voz.
    Ya NO agregamos texto extra visualmente porque dimos las instrucciones
    en la pantalla de carga (main_system).
    """
    # Llama al motor de voz que gestiona la espera de "Dante"
    comando = voice_bot.listen_command(prompt, opciones_clave)
    
    # Mapeo SOLO de numeros hablados a digitos
    if comando in ["uno", "primero"]: return "1"
    if comando in ["dos", "segundo"]: return "2"
    if comando in ["tres", "tercero"]: return "3"
    if comando in ["cuatro"]: return "4"
    if comando in ["cinco"]: return "5"
    
    return comando

def limpiar_pantalla():
    os.system("cls" if os.name == "nt" else "clear")

def cuenta_regresiva_10():
    print("")
    for i in range(5, 0, -1):
        print(f"Volviendo en {i}...", end="\r")
        time.sleep(1)
    print("                     ", end="\r")

def carga_segura_json(ruta, valor_por_defecto):
    if not os.path.exists(ruta):
        guardar_json(ruta, valor_por_defecto)
        return valor_por_defecto
    try:
        with open(ruta, "r") as f:
            return json.load(f)
    except:
        guardar_json(ruta, valor_por_defecto)
        return valor_por_defecto

def guardar_json(ruta, datos):
    with open(ruta, "w") as f:
        json.dump(datos, f, indent=4)

def cargar_estado():
    return carga_segura_json(ARCHIVO_ESTADO, {"bloqueado": False})

def guardar_estado(estado):
    guardar_json(ARCHIVO_ESTADO, estado)

def cargar_admins():
    return carga_segura_json(ARCHIVO_ADMINS, {})

def guardar_admins(db):
    guardar_json(ARCHIVO_ADMINS, db)

def cargar_casilleros():
    predeterminado = {str(i): "Nadie" for i in range(1, 13)}
    return carga_segura_json(ARCHIVO_CASILLEROS, predeterminado)

def guardar_casilleros(datos):
    guardar_json(ARCHIVO_CASILLEROS, datos)

def cargar_bd_creditos():
    return carga_segura_json(ARCHIVO_CREDITOS, {})

def guardar_bd_creditos(db):
    guardar_json(ARCHIVO_CREDITOS, db)

def normalizar_valor_tarjeta(db, uid):
    val = db.get(uid, 0)
    if isinstance(val, int): return val
    return 0

def operar_creditos(db, uid, costo):
    antes = normalizar_valor_tarjeta(db, uid)
    if antes < costo:
        print("Ups, creditos insuficientes.")
        return False
    db[uid] = antes - costo
    guardar_bd_creditos(db)
    print("Pago aceptado. Tu nuevo saldo es:", db[uid])
    return True

def leer_tarjeta(lector, tiempo_espera_segundos=20):
    print("Por favor, acerca tu tarjeta al lector...")
    if lector is None:
        # En simulacion, tambien hay que decir "Dante [ID]"
        uid_voz = voice_bot.listen_command("Dicte el ID (Simulacion):")
        return uid_voz.replace(" ", "")
    
    import time
    from rc522_spi_library import StatusCodes
    inicio = time.time()
    while True:
        time.sleep(0.05)
        if time.time() - inicio > tiempo_espera_segundos: return None
        status, _ = lector.request()
        if status == StatusCodes.OK:
            st2, uid_bytes = lector.anticoll()
            if st2 == StatusCodes.OK:
                return ":".join([f"{b:02X}" for b in uid_bytes])

def esperar_retiro_tarjeta(lector):
    if lector is None: return
    print("Ya puedes retirar tu tarjeta...")
    time.sleep(2)