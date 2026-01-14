# ASCII ONLY
# voice_engine.py - VOZ FLUIDA (PICOTTS)

import os
import json
import vosk
import pyaudio
import unicodedata
import sys
import time
import subprocess

# Configuracion
MODEL_PATH = "vosk-es"
INPUT_RATE = 16000
NOMBRE_BOT = "dante"

class VoiceSystem:
    def __init__(self):
        self.model = None
        self.rec = None
        self.pa = None
        self.stream = None
        self.initialized = False

        # --- 1. CONFIGURACION DE RECONOCIMIENTO (VOSK) ---
        if not os.path.exists(MODEL_PATH):
            print("ERROR CRITICO: No se encuentra la carpeta 'vosk-es'.")
            return

        try:
            vosk.SetLogLevel(-1)
            self.model = vosk.Model(MODEL_PATH)
            self.rec = vosk.KaldiRecognizer(self.model, INPUT_RATE)
            self.pa = pyaudio.PyAudio()
            self.initialized = True
            print(f"[VOZ] Motor iniciado. Palabra clave: '{NOMBRE_BOT.upper()}'")
        except Exception as e:
            print(f"Error cargando motor de voz: {e}")
            self.initialized = False

    def normalize(self, text):
        """Elimina tildes y pasa a minusculas"""
        text = text.lower()
        text = unicodedata.normalize("NFD", text)
        text = text.encode("ascii", "ignore").decode("utf-8")
        return text

    def speak(self, text):
        """
        Usa PicoTTS (pico2wave) para generar una voz humana y suave.
        Genera un archivo temporal y lo reproduce.
        """
        if not text: return
        
        # Limpieza para que el comando de consola no falle
        text = text.replace('"', '').replace("'", "")
        text = text.replace("_", " ")
        
        # Archivo temporal
        wav_path = "/tmp/tts_dante.wav"
        
        try:
            # 1. Generar el audio (Voz ES-ES femenina suave)
            # -l es-ES define el idioma español
            subprocess.run(
                f'pico2wave -l es-ES -w {wav_path} "{text}"', 
                shell=True, check=True
            )
            
            # 2. Reproducir el audio
            subprocess.run(
                f'aplay -q {wav_path}', 
                shell=True, check=True
            )
        except Exception as e:
            print(f"[TTS Error] No se pudo hablar: {e}")
            print("(Asegurate de haber instalado: sudo apt-get install libttspico-utils)")

    def text_to_number(self, text):
        mapping = {
            "uno": "1", "una": "1", "un": "1", "primero": "1",
            "dos": "2", "segundo": "2",
            "tres": "3", "tercero": "3",
            "cuatro": "4",
            "cinco": "5",
            "seis": "6",
            "siete": "7",
            "ocho": "8",
            "nueve": "9",
            "diez": "10",
            "once": "11",
            "doce": "12"
        }
        words = text.split()
        for w in words:
            if w in mapping: return mapping[w]
            if w.isdigit(): return w
        return None

    def listen_command(self, prompt=None, valid_options=None):
        if not self.initialized:
            p = prompt if prompt else "Ingrese opcion: "
            return input(p).strip()

        # FASE 1: LEER INSTRUCCION (VOZ BONITA)
        print(f"\n[ESPERANDO A {NOMBRE_BOT.upper()}] {prompt or '...'}")
        
        if prompt:
            # Limpiamos el texto visual para que suene natural
            texto_a_leer = prompt.replace(" (Di 'Dante' antes del comando)", "")
            self.speak(texto_a_leer)

        # FASE 2: ESCUCHAR
        try:
            self.stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=INPUT_RATE,
                input=True,
                frames_per_buffer=4000
            )
            self.stream.start_stream()
        except Exception:
            return input("Error Mic. Use Teclado: ").strip()

        despierto = False 
        
        try:
            while True:
                data = self.stream.read(4000, exception_on_overflow=False)
                if self.rec.AcceptWaveform(data):
                    res = json.loads(self.rec.Result())
                    text = res.get("text", "")
                    
                    if not text: continue
                    norm_text = self.normalize(text)
                    
                    # LOGICA WAKE WORD
                    if not despierto:
                        if NOMBRE_BOT in norm_text:
                            print(f" >> {NOMBRE_BOT.upper()}: Si?")
                            
                            self.stop_stream()
                            self.speak("Si dime") # Voz suave
                            
                            # Reiniciar stream para escuchar comando
                            self.stream = self.pa.open(
                                format=pyaudio.paInt16, channels=1, rate=INPUT_RATE,
                                input=True, frames_per_buffer=4000
                            )
                            self.stream.start_stream()
                            
                            despierto = True
                            
                            norm_text = norm_text.replace(NOMBRE_BOT, "").strip()
                            if not norm_text: continue
                        else:
                            continue

                    # PROCESAMIENTO
                    print(f" > Oido: '{norm_text}'")

                    # 1. Numeros
                    num = self.text_to_number(norm_text)
                    if num:
                        self.stop_stream()
                        return num

                    # 2. Comandos
                    if valid_options:
                        for opt in valid_options:
                            if opt in norm_text:
                                self.stop_stream()
                                return opt 
                        
                        # No entendi
                        self.stop_stream()
                        self.speak("No te entendi")
                        self.stream = self.pa.open(
                                format=pyaudio.paInt16, channels=1, rate=INPUT_RATE,
                                input=True, frames_per_buffer=4000
                        )
                        self.stream.start_stream()
                    else:
                        self.stop_stream()
                        return norm_text

        except KeyboardInterrupt:
            self.stop_stream()
            sys.exit()
        finally:
            self.stop_stream()

    def stop_stream(self):
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except: pass
            self.stream = None

voice_bot = VoiceSystem()