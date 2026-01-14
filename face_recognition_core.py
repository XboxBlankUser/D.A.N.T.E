# ASCII ONLY
# face_recognition_core.py - VERSION FINAL (CORREGIDO UPPERCASE)

import face_recognition
import cv2
import numpy as np
from picamera2 import Picamera2
import time
import pickle
import threading
import subprocess
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- VARIABLES GLOBALES ---
KNOWN_FACE_ENCODINGS = []
KNOWN_FACE_NAMES = []
LAST_LOAD_TIME = 0
LOAD_INTERVAL = 5
TRAINING_INTERVAL = 15
FACIAL_RECOGNITION_READY = False

# --- FUNCION DE CARGA SEGURA ---
def cargar_encodings_seguro():
    global KNOWN_FACE_ENCODINGS, KNOWN_FACE_NAMES, LAST_LOAD_TIME
    try:
        if not os.path.exists("encodings.pickle"):
            return 
        with open("encodings.pickle", "rb") as f:
            data = pickle.loads(f.read())
        KNOWN_FACE_ENCODINGS = data["encodings"]
        KNOWN_FACE_NAMES = data["names"]
        LAST_LOAD_TIME = time.time()
    except Exception as e:
        print(f"[WARN] Error leyendo encodings: {e}")
        KNOWN_FACE_ENCODINGS = []
        KNOWN_FACE_NAMES = []

# --- SETUP INICIAL ---
cargar_encodings_seguro()

try:
    PICAM2 = Picamera2()
    config = PICAM2.create_preview_configuration(main={"format": 'XRGB8888', "size": (1920, 1080)})
    PICAM2.configure(config)
    PICAM2.start()
    CV_SCALER = 4 
    FACIAL_RECOGNITION_READY = True
    print("[INFO] Camara iniciada con exito.")
except Exception as e:
    print(f"[ERROR] No se pudo iniciar la camara: {e}")
    FACIAL_RECOGNITION_READY = False

# --- HILO DE ENTRENAMIENTO ---
def background_trainer_loop():
    while True:
        time.sleep(TRAINING_INTERVAL)
        try:
            subprocess.run(
                ["/usr/bin/env", "python3", os.path.join(BASE_DIR, "model_training.py")],
                capture_output=True, check=False
            )
        except Exception: pass

bg_thread = threading.Thread(target=background_trainer_loop, daemon=True)
bg_thread.start()

# --- FUNCION PRINCIPAL DE RECONOCIMIENTO ---

def recognize_user_face(timeout_seconds=10):
    global KNOWN_FACE_ENCODINGS, KNOWN_FACE_NAMES, LAST_LOAD_TIME

    if not FACIAL_RECOGNITION_READY:
        # En modo manual tambien forzamos mayusculas
        return input("Ingrese usuario manualmente: ").strip().upper()

    if time.time() - LAST_LOAD_TIME > LOAD_INTERVAL:
        cargar_encodings_seguro()

    print(f"[INFO] Escaneando... (Base: {len(KNOWN_FACE_NAMES)} personas)")
    
    start_time = time.time()
    
    # VARIABLES PARA EL ESTADO DE EXITO
    usuario_detectado_final = None
    tiempo_confirmacion = None
    
    while True:
        # Timeout solo si no hemos encontrado a nadie
        if usuario_detectado_final is None and (time.time() - start_time > timeout_seconds):
            break

        try:
            frame = PICAM2.capture_array()
        except: break 
        
        # Procesamiento basico
        small_frame = cv2.resize(frame, (0, 0), fx=(1/CV_SCALER), fy=(1/CV_SCALER))
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        
        # SIEMPRE buscamos la ubicacion de la cara para poder dibujar el recuadro
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_names_frame = []

        # --- LOGICA MIXTA ---
        
        if usuario_detectado_final is None:
            # MODO BUSQUEDA
            if face_locations:
                face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
                
                for face_encoding in face_encodings:
                    name = "Desconocido"
                    if len(KNOWN_FACE_ENCODINGS) > 0:
                        matches = face_recognition.compare_faces(KNOWN_FACE_ENCODINGS, face_encoding)
                        if True in matches:
                            face_distances = face_recognition.face_distance(KNOWN_FACE_ENCODINGS, face_encoding)
                            best_match_index = np.argmin(face_distances)
                            if matches[best_match_index]:
                                raw_name = KNOWN_FACE_NAMES[best_match_index]
                                
                                # --- CORRECCION AQUI: FORZAR MAYUSCULAS ---
                                name = raw_name.upper() 
                                
                                # EXITO: Guardamos el nombre YA EN MAYUSCULAS
                                usuario_detectado_final = name
                                tiempo_confirmacion = time.time()
                                print(f"[INFO] Reconocido: {name}. Esperando 3 segundos...")
                    
                    face_names_frame.append(name)
        else:
            # MODO EXITO (DELAY)
            elapsed = time.time() - tiempo_confirmacion
            
            # Si pasaron 3 segundos, salimos
            if elapsed > 3.0:
                print(f"[EXITO] Confirmado: {usuario_detectado_final}")
                cv2.destroyAllWindows()
                return usuario_detectado_final # Ya es mayuscula

            # Forzamos que todas las caras detectadas sean el usuario
            for _ in face_locations:
                face_names_frame.append(usuario_detectado_final)

        # --- DIBUJADO EN PANTALLA ---
        display_frame = cv2.resize(frame, (800, 600))
        
        sh, sw = (frame.shape[0]/CV_SCALER), (frame.shape[1]/CV_SCALER) 
        ry = 600 / sh
        rx = 800 / sw

        # Barra de progreso
        if usuario_detectado_final is not None:
            progreso = (time.time() - tiempo_confirmacion) / 3.0
            ancho_barra = int(progreso * 800)
            cv2.rectangle(display_frame, (0, 580), (ancho_barra, 600), (0, 255, 0), cv2.FILLED)

        # Dibujar recuadros
        for (top, right, bottom, left), name in zip(face_locations, face_names_frame):
            top = int(top * ry)
            right = int(right * rx)
            bottom = int(bottom * ry)
            left = int(left * rx)

            is_known = (name != "Desconocido")
            color = (0, 255, 0) if is_known else (0, 0, 255)
            grosor = 4 if usuario_detectado_final else 2
            
            cv2.rectangle(display_frame, (left, top), (right, bottom), color, grosor)
            cv2.rectangle(display_frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
            cv2.putText(display_frame, name, (left + 6, bottom - 6), 
                        cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 1)

        if not face_locations and usuario_detectado_final is None:
             cv2.putText(display_frame, "BUSCANDO...", (20, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)

        cv2.imshow('Facial Scanner', display_frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()
    print("[INFO] Tiempo agotado.")
    return None

def stop_picam():
    if FACIAL_RECOGNITION_READY:
        try:
            PICAM2.stop()
        except: pass