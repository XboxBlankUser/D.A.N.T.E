# ASCII ONLY
# locker_hardware.py - VERSION FINAL (CON TEMPORIZADOR NO-BLOCKING)

import time
import atexit
from threading import Timer  # <--- NUEVO IMPORT NECESARIO

try:
    from gpiozero import LED, Device
    try:
        from gpiozero.pins.lgpio import LGPIOFactory
        Device.pin_factory = LGPIOFactory()
    except ImportError:
        print("[ALERTA] Falta libreria 'python3-lgpio'.")
    HARDWARE_ACTIVO = True
except ImportError:
    HARDWARE_ACTIVO = False
    print("[HW] Modo simulacion.")

LOCKER_GPIO_MAP = {
    1: 20, 2: 16, 3: 13, 4: 19,
    5: 26, 6: 21, 7: 5,  8: 6,
    9: 23, 10: 24, 11: 17, 12: 27
}

reles = {}

def iniciar_hardware():
    global reles
    if not HARDWARE_ACTIVO: return
    if len(reles) > 0: return 

    print("[HW] Inicializando GPIOs...")
    for num, pin in LOCKER_GPIO_MAP.items():
        try:
            rele = LED(pin)
            rele.off()
            reles[num] = rele
        except Exception as e:
            print(f"[HW] Error Pin {pin}: {e}")

    atexit.register(liberar_pines)
    print(f"[HW] Hardware LISTO ({len(reles)} reles).")

def apagar_todo():
    if not HARDWARE_ACTIVO: return
    for r in reles.values():
        try:
            r.off()
        except: pass

def liberar_pines():
    if not HARDWARE_ACTIVO: return
    for r in reles.values():
        try:
            r.close()
        except: pass
    reles.clear()

def activar_casillero_fisico(numero):
    num_int = int(numero)
    
    if not HARDWARE_ACTIVO: 
        print(f"[SIM] Casillero {num_int} abierto por 8s.")
        return True

    if num_int not in reles: return False

    try:
        rele = reles[num_int]
        
        # 1. Encendemos el rele (Abrir cerradura)
        rele.on()
        
        # 2. Programamos el apagado en 8 SEGUNDOS (en segundo plano)
        # Esto permite que el codigo siga y muestre la pantalla "EMPUJE" de inmediato
        t = Timer(8.0, rele.off) 
        t.start()
        
        return True
    except Exception as e:
        print(f"[HW] Fallo: {e}")
        return False