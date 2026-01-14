#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Dataset capture server - Version Amigable
# Requires Flask

import os
import re
import unicodedata
import subprocess # For running the training script
from datetime import datetime
from flask import Flask, request, render_template_string, abort

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_BASE = os.path.join(BASE_DIR, "dataset")
os.makedirs(DATASET_BASE, exist_ok=True)

ALLOWED_EXT = {"jpg", "jpeg", "png", "webp"}

def sanitize_field(s: str) -> str:
    """Remove accents and unsafe characters, keep ASCII letters, numbers, and underscore."""
    s = (s or "").strip()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^A-Za-z0-9_-]", "", s)
    return s

def ensure_person_folder(folder_name: str) -> str:
    if not folder_name:
        raise ValueError("El nombre de la carpeta no puede estar vacio")
    folder = os.path.join(DATASET_BASE, folder_name)
    os.makedirs(folder, exist_ok=True)
    return folder

def count_user_photos(folder: str) -> int:
    if not os.path.isdir(folder):
        return 0
    return sum(
        1 for f in os.listdir(folder)
        if os.path.isfile(os.path.join(folder, f)) and f.lower().split(".")[-1] in ALLOWED_EXT
    )

# --- Trainer Execution Function ---
def run_trainer():
    """Execute model_training.py to update encodings."""
    print("[INFO] Iniciando entrenamiento de reconocimiento facial...")
    try:
        # Use python3 and the default model "hog" for speed
        result = subprocess.run(
            ["/usr/bin/env", "python3", os.path.join(BASE_DIR, "model_training.py"), "--model", "hog"],
            capture_output=True,
            text=True,
            check=True # Raise an exception for non-zero exit codes
        )
        print("[INFO] Entrenamiento completado con exito.")
        # print(result.stdout) # You can comment these if too noisy
        # print(result.stderr)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] El entrenador fallo con codigo {e.returncode}:")
        print(e.stdout)
        print(e.stderr)
        # You may want to log this error or send an alert
    except FileNotFoundError:
        print("[ERROR] No se encontro python3 o model_training.py. Revisa las rutas.")
# ---------------------------------------

# --- HTML template (Amigable y en Espanglish ASCII) ---
HTML = """
<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Registro de Usuario</title>
<style>
body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin:0; padding:24px; background:#0b1220; color:#e2e8f0; }
.card { max-width:820px; margin:0 auto; background:#1e293b; border-radius:20px; padding:30px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
h1 { margin:0 0 20px; font-size:24px; color:#38bdf8; text-align:center; }
p { line-height: 1.6; }
.row { display:flex; gap:15px; flex-wrap:wrap; margin-bottom: 15px; }
input[type=text]{ flex:1; padding:15px; border-radius:12px; border:1px solid #475569; background:#0f172a; color:#fff; font-size:16px; transition: border 0.3s; }
input[type=text]:focus { border-color: #38bdf8; outline: none; }
.btn { padding:15px 24px; border:0; border-radius:12px; font-weight:600; cursor:pointer; font-size:16px; transition: transform 0.1s; }
.btn:active { transform: scale(0.98); }
.primary { background:#38bdf8; color:#0f172a; width: 100%; }
.ghost { background:#334155; color:#fff; flex: 1; }
.warn { background:#f59e0b; color:#111; text-decoration: none; display: inline-block; text-align: center; flex: 1; }
.muted { color:#94a3b8; font-size: 14px; text-align: center; }
.ok { color:#34d399; background: rgba(52, 211, 153, 0.1); padding: 10px; border-radius: 8px; text-align: center; }
.err { color:#f87171; background: rgba(248, 113, 113, 0.1); padding: 10px; border-radius: 8px; text-align: center; }
input[type=file]{ display:none; }
</style>
</head>
<body>
<div class="card">
<h1>Bienvenido al Registro Facial</h1>

{% if not full_name %}
<p style="text-align:center; margin-bottom:20px;">Por favor, llena tus datos para crear tu perfil personal.</p>
<form method="POST" action="/" style="margin-bottom:12px;">
<div class="row">
<input type="text" name="name1" placeholder="Primer Nombre" required />
<input type="text" name="name2" placeholder="Segundo Nombre (Opcional)" />
</div>
<div class="row">
<input type="text" name="surname1" placeholder="Primer Apellido" required />
<input type="text" name="surname2" placeholder="Segundo Apellido (Opcional)" />
</div>
<button class="btn primary" type="submit">Crear Mi Perfil</button>
</form>
<p class="muted">Tus datos se guardaran de forma segura en <code>{{ dataset_base }}</code>.</p>

{% else %}
<p class="muted" style="margin:0 0 12px;">Hola <strong>{{ full_name }}</strong>! Tu carpeta personal esta lista en <code>{{ folder_path }}</code>.</p>

{% if message %}<p class="ok">{{ message|safe }}</p>{% endif %}
{% if error %}<p class="err">{{ error }}</p>{% endif %}

<div style="text-align:center; margin: 20px 0;">
    <p>Ahora necesitamos una foto tuya para reconocerte.</p>
</div>

<form id="uploadForm" method="POST" action="/upload" enctype="multipart/form-data">
<input type="hidden" name="full_name" value="{{ full_name }}" />
<input id="file" type="file" name="file" accept="image/*" capture="environment" />
<div class="row" style="margin-top:20px;">
<button class="btn ghost" type="button" id="openCam">Abrir Camara / Galeria</button>
<button class="btn primary" type="submit" id="sendBtn" disabled>Subir Foto</button>
</div>
{% if has_photos %}
<div class="row">
<a class="btn warn" href="/">Terminar Registro</a>
</div>
{% endif %}
</form>

<script>
const file = document.getElementById('file');
const openCam = document.getElementById('openCam');
const sendBtn = document.getElementById('sendBtn');

function enableSend() { 
    if(file.files && file.files.length > 0) {
        sendBtn.disabled = false;
        sendBtn.innerText = "Listo, Subir Foto";
        sendBtn.style.background = "#22c55e";
    } else {
        sendBtn.disabled = true;
    }
}
openCam.addEventListener('click', ()=>file.click());
file.addEventListener('change', enableSend);
{% if auto_open_cam %} setTimeout(() => file.click(), 500); {% endif %}
</script>

{% endif %}
</div>
</body>
</html>
"""

# --- Routes (index route remains unchanged) ---
@app.route("/", methods=["GET","POST"])
def index():
    if request.method == "GET":
        return render_template_string(HTML, full_name=None, dataset_base=DATASET_BASE)

    # Get form data
    name1 = sanitize_field(request.form.get("name1"))
    name2 = sanitize_field(request.form.get("name2"))
    surname1 = sanitize_field(request.form.get("surname1"))
    surname2 = sanitize_field(request.form.get("surname2"))

    # Validate mandatory fields
    if not name1 or not surname1:
        return render_template_string(HTML, full_name=None, dataset_base=DATASET_BASE,
                                      error="Ups, necesitamos al menos tu Primer Nombre y Primer Apellido.")

    # Build folder name
    parts = [name1]
    if name2: parts.append(name2)
    parts.append(surname1)
    if surname2: parts.append(surname2)
    full_name = "_".join(parts)

    try:
        folder = ensure_person_folder(full_name)
    except Exception as e:
        return render_template_string(HTML, full_name=None, dataset_base=DATASET_BASE,
                                      error=f"No pudimos crear tu carpeta: {e}")

    message = f"Excelente! Carpeta creada en: {folder}"
    return render_template_string(HTML, full_name=full_name, folder_path=folder,
                                  message=message, error=None,
                                  auto_open_cam=True, dataset_base=DATASET_BASE,
                                  has_photos=False)

@app.post("/upload")
def upload():
    full_name = sanitize_field(request.form.get("full_name") or "")
    if not full_name:
        abort(400, "Falta el nombre completo")

    try:
        folder = ensure_person_folder(full_name)
    except Exception as e:
        return render_template_string(HTML, full_name=None, dataset_base=DATASET_BASE,
                                      error=f"Error al verificar carpeta: {e}")

    if "file" not in request.files:
        return render_template_string(HTML, full_name=full_name, folder_path=folder,
                                      error="No recibimos ningun archivo.", auto_open_cam=False,
                                      has_photos=(count_user_photos(folder) > 0))

    f = request.files["file"]
    if f.filename == "":
        return render_template_string(HTML, full_name=full_name, folder_path=folder,
                                      error="El archivo parece estar vacio.", auto_open_cam=False,
                                      has_photos=(count_user_photos(folder) > 0))

    fname_base = f"{full_name}_{datetime.now().strftime('%Y%m%d_%H%M%S%f')[:-3]}"
    ext = os.path.splitext(f.filename)[1].lower()
    if ext.replace(".", "") not in ALLOWED_EXT:
        mt = (f.mimetype or "").lower()
        if "jpeg" in mt: ext = ".jpg"
        elif "png" in mt: ext = ".png"
        elif "webp" in mt: ext = ".webp"
        else: ext = ".jpg"

    path = os.path.join(folder, fname_base + ext)
    try:
        f.save(path)

    except Exception as e:
        return render_template_string(HTML, full_name=full_name, folder_path=folder,
                                      error=f"Hubo un problema guardando la foto: {e}", auto_open_cam=False,
                                      has_photos=(count_user_photos(folder) > 0))

    message = f"Genial! Foto guardada correctamente y sistema actualizado."
    return render_template_string(HTML, full_name=full_name, folder_path=folder,
                                  message=message, error=None, auto_open_cam=False,
                                  has_photos=True)

@app.get("/health")
def health():
    return {"ok": True}

# --- Main Execution Block ---
if __name__ == "__main__":
    # Remove the run_trainer() call here, it is now in /upload
    app.run(host="0.0.0.0", port=8000, debug=True)