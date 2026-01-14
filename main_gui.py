# ASCII ONLY
# main_gui.py - VERSION VISUAL FINAL (Iconos, Grid 12, Push Door)

import threading
import sys
import os
import time
import cv2
import json
import subprocess
import atexit
import numpy as np
from flask import Flask, render_template, Response, request, redirect, url_for, session, jsonify

# --- MODULOS ---
from locker_hardware import activar_casillero_fisico, apagar_todo, iniciar_hardware
from common_utils import (
    cargar_casilleros, guardar_casilleros,
    cargar_bd_creditos, guardar_bd_creditos,
    cargar_admins, guardar_admins,
    cargar_estado, guardar_estado
)
import face_recognition_core as fr_core 

# --- WEBSERVER REGISTRO ---
proceso_web = None
def arrancar_webserver_registro():
    global proceso_web
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "webserver.py")
    if os.path.exists(ruta):
        try:
            proceso_web = subprocess.Popen([sys.executable, ruta], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("[INFO] Webserver Registro: ON (Puerto 8000)")
        except: pass

def detener_webserver():
    global proceso_web
    if proceso_web:
        proceso_web.terminate()
        proceso_web = None
atexit.register(detener_webserver)

# --- RFID ---
RFID_READER = None
try:
    from rc522_spi_library import RC522SPILibrary, StatusCodes
    RFID_READER = RC522SPILibrary()
    print("[INFO] RFID: ON")
except:
    print("[WARN] RFID: OFF (Simulacion)")

app = Flask(__name__)
app.secret_key = "DANTE_SYSTEM_SECRET"

# --- CAMARA ---
LAST_FRAME = None
LAST_DB_UPDATE = 0 

def generate_frames():
    global LAST_FRAME
    while True:
        try:
            if fr_core.PICAM2:
                frame = fr_core.PICAM2.capture_array()
                frame = cv2.resize(frame, (640, 480))
                LAST_FRAME = frame 
                ret, buffer = cv2.imencode('.jpg', frame)
                yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            else: time.sleep(0.1)
        except: time.sleep(0.1)

def scan_face_single_frame():
    global LAST_FRAME, LAST_DB_UPDATE
    if time.time() - LAST_DB_UPDATE > 15:
        try:
            fr_core.cargar_encodings_seguro()
            LAST_DB_UPDATE = time.time()
        except: pass

    if LAST_FRAME is None: return None
    
    rgb = cv2.cvtColor(LAST_FRAME, cv2.COLOR_BGR2RGB)
    small = cv2.resize(rgb, (0, 0), fx=0.5, fy=0.5) # Escala 0.5 para distancia
    
    boxes = fr_core.face_recognition.face_locations(small)
    if not boxes: return None
    
    encodings = fr_core.face_recognition.face_encodings(small, boxes)
    
    for encoding in encodings:
        if not fr_core.KNOWN_FACE_ENCODINGS: return None
        dists = fr_core.face_recognition.face_distance(fr_core.KNOWN_FACE_ENCODINGS, encoding)
        best = np.argmin(dists)
        if dists[best] < 0.6:
            return fr_core.KNOWN_FACE_NAMES[best].upper()
    return None

# --- API ---
@app.route('/api/rfid_scan')
def api_rfid_scan():
    if not RFID_READER: return jsonify({"status": "waiting"})
    (st, _) = RFID_READER.request()
    if st == StatusCodes.OK:
        (st, uid) = RFID_READER.anticoll()
        if st == StatusCodes.OK:
            return jsonify({"status": "found", "uid": ":".join([f"{x:02X}" for x in uid])})
    return jsonify({"status": "waiting"})

@app.route('/api/check_face')
def api_check_face():
    user = scan_face_single_frame()
    if user:
        session['user'] = user
        print(f"[LOGIN] Usuario detectado y guardado en sesion: {user}")
    return jsonify({"status": "found" if user else "searching", "user": user})
    
# --- FUNCION PARA ABRIR KIOSKO ---
def abrir_navegador_kiosk():
    time.sleep(4) # Damos 4 segundos para asegurarnos de que el servidor este arriba
    print("[INFO] Abriendo Chromium en modo Kiosko...")
    cmd = "chromium-browser --kiosk --noerrdialogs --disable-infobars --check-for-update-interval=31536000 http://127.0.0.1:5000"
    os.system(cmd)

# --- RUTAS PRINCIPALES ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/login_select')
def login_select():
    # VERIFICAR SI YA ES ADMIN PARA OCULTAR EL BOTON
    user = session.get('user')
    admins = cargar_admins()
    is_admin = (user in admins)
    
    st = cargar_estado()
    if st.get("bloqueado", False) and not is_admin:
        return render_template('message.html', msg="SISTEMA BLOQUEADO", sub="Mantenimiento en curso.", dest="/")
        
    return render_template('selection.html', is_admin=is_admin)

@app.route('/scan/<role>')
def scan_page(role):
    return render_template('scan.html', role=role)

@app.route('/auth_success/<role>')
def auth_success(role):
    user = session.get('user')
    if not user: return redirect(url_for('index'))
    
    if role == 'admin':
        if user not in cargar_admins():
            return render_template('message.html', msg="ACCESO DENEGADO", sub="No eres administrador.", dest="/")
        return redirect(url_for('admin_menu'))
    
    elif role == 'register_admin':
        admins = cargar_admins()
        admins[user] = True
        guardar_admins(admins)
        return render_template('message.html', msg="REGISTRO EXITOSO", sub=f"{user} ahora es Admin.", dest="/login_select")
        
    else: # Cliente
        if cargar_estado().get("bloqueado", False):
             return render_template('message.html', msg="BLOQUEADO", sub="Sistema en mantenimiento.", dest="/")
        return redirect(url_for('client_menu'))

@app.route('/push_instruction/<locker_id>')
def push_instruction(locker_id):
    # Pantalla intermedia: "Empuje la puerta"
    return render_template('push_door.html', locker_id=locker_id)

# --- CLIENTE ---
@app.route('/client/menu')
def client_menu():
    if 'user' not in session: return redirect(url_for('index'))
    return render_template('client_menu.html', user=session['user'])

@app.route('/client/action/<action>')
def client_action(action):
    return render_template('locker_grid.html', action=action, lockers=cargar_casilleros())

@app.route('/client/process/<action>/<locker_id>')
def client_process(action, locker_id):
    user = session['user']
    casilleros = cargar_casilleros()
    
    if action == "reservar":
        if casilleros.get(locker_id) != "Nadie":
             return render_template('message.html', msg="OCUPADO", sub="Selecciona otro.", dest=f"/client/action/reservar")
        session['pending_locker'] = locker_id
        return redirect(url_for('card_wait', mode='pay', value=1))

    elif action == "abrir":
        if casilleros.get(locker_id) != user:
            return render_template('message.html', msg="ERROR", sub="No es tuyo.", dest="/client/menu")
        activar_casillero_fisico(locker_id)
        # REDIRIGIR A PANTALLA EMPUJAR
        return redirect(url_for('push_instruction', locker_id=locker_id))

    elif action == "liberar":
        if casilleros.get(locker_id) != user:
            return render_template('message.html', msg="ERROR", sub="No es tuyo.", dest="/client/menu")
        casilleros[locker_id] = "Nadie"
        guardar_casilleros(casilleros)
        activar_casillero_fisico(locker_id)
        # REDIRIGIR A PANTALLA EMPUJAR
        return redirect(url_for('push_instruction', locker_id=locker_id))
    
    return redirect(url_for('index'))

# --- ADMIN ---
@app.route('/admin/menu')
def admin_menu():
    if 'user' not in session: return redirect(url_for('index'))
    st = cargar_estado()
    return render_template('admin_menu.html', user=session['user'], locked=st.get("bloqueado", False))

@app.route('/admin/credits/select')
def admin_credits_select():
    return render_template('admin_credits.html')

@app.route('/admin/card_wait/<mode>/<value>')
def card_wait(mode, value):
    return render_template('admin_card_scan.html', mode=mode, value=value)

@app.route('/process_card_action', methods=['POST'])
def process_card_action():
    data = request.json
    uid, mode, value = data.get('uid'), data.get('mode'), int(data.get('value', 0))
    db = cargar_bd_creditos()
    
    if mode == 'charge': 
        db[uid] = db.get(uid, 0) + value
        guardar_bd_creditos(db)
        return jsonify({"status": "ok", "msg": f"Cargado. Total: {db[uid]}", "redirect": "/admin/menu"})
        
    elif mode == 'delete':
        if uid in db: del db[uid]
        guardar_bd_creditos(db)
        return jsonify({"status": "ok", "msg": "Tarjeta Eliminada.", "redirect": "/admin/menu"})
        
    elif mode == 'pay':
        current = db.get(uid, 0)
        if current < value:
            # ESTADO 'DENIED' PARA QUE EL JS MUESTRE EL ICONO NO_CREDIT
            return jsonify({"status": "denied", "msg": "Saldo Insuficiente", "redirect": "/client/menu"})
        
        db[uid] = current - value
        guardar_bd_creditos(db)
        
        locker_id = session.get('pending_locker')
        user = session.get('user')
        if locker_id:
            casilleros = cargar_casilleros()
            casilleros[locker_id] = user
            guardar_casilleros(casilleros)
            activar_casillero_fisico(locker_id)
            # EXITO -> EMPUJAR PUERTA
            return jsonify({"status": "ok", "msg": "Reserva Exitosa", "redirect": f"/push_instruction/{locker_id}"})
            
    return jsonify({"status": "error", "msg": "Error Desconocido"})

@app.route('/admin/toggle_lock')
def admin_toggle_lock():
    st = cargar_estado()
    st["bloqueado"] = not st.get("bloqueado", False)
    guardar_estado(st)
    return render_template('message.html', msg="ESTADO ACTUALIZADO", sub="Cambios guardados.", dest="/admin/menu")

@app.route('/admin/status')
def admin_status():
    return render_template('admin_status.html', lockers=cargar_casilleros(), admins=cargar_admins())

@app.route('/admin/restart')
def admin_restart():
    apagar_todo()
    guardar_casilleros({str(i): "Nadie" for i in range(1,13)})
    return render_template('message.html', msg="SISTEMA REINICIADO", sub="Hardware OK.", dest="/")

@app.route('/register/admin_start')
def register_admin_start():
    return render_template('scan.html', role='register_admin')

if __name__ == '__main__':
    iniciar_hardware()
    arrancar_webserver_registro()
    hilo_kiosk = threading.Thread(target=abrir_navegador_kiosk)
    hilo_kiosk.start()
    print("--- DANTE KIOSK V_FINAL RUNNING ---")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)