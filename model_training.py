#!/usr/bin/env python3
# model_training.py OPTIMIZADO
import os, sys, argparse, pickle, cv2, face_recognition
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "dataset")
DEFAULT_OUT = os.path.join(BASE_DIR, "encodings.pickle")
TIMESTAMP_FILE = os.path.join(BASE_DIR, "last_training_timestamp.txt")

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

def get_latest_modification(folder):
    """Devuelve la fecha de modificación más reciente en todo el dataset."""
    latest = 0
    for root, _, files in os.walk(folder):
        for f in files:
            full_path = os.path.join(root, f)
            try:
                mtime = os.path.getmtime(full_path)
                if mtime > latest:
                    latest = mtime
            except: pass
    return latest

def list_images(root):
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext in ALLOWED_EXT:
                yield os.path.join(dirpath, fn)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=DEFAULT_OUT, help="Ruta del pickle")
    ap.add_argument("--model", default="hog", choices=["hog","cnn"])
    ap.add_argument("--force", action="store_true", help="Forzar entrenamiento aunque no haya cambios")
    args = ap.parse_args()

    # --- VERIFICACION INTELIGENTE ---
    if not args.force and os.path.exists(TIMESTAMP_FILE) and os.path.exists(args.out):
        try:
            with open(TIMESTAMP_FILE, "r") as f:
                last_train_time = float(f.read().strip())
            
            last_dataset_mod = get_latest_modification(DATASET_DIR)
            
            # Si el dataset no se ha tocado desde el ultimo entrenamiento, salimos.
            if last_dataset_mod <= last_train_time:
                print("[INFO] No changes detected in dataset. Skipping training.")
                sys.exit(0)
        except Exception as e:
            print(f"[WARN] Error checking timestamp: {e}. Proceeding with training.")
    # --------------------------------

    print("[INFO] Changes detected (or forced). Starting training...")
    image_paths = list(list_images(DATASET_DIR))
    
    knownEncodings, knownNames = [], []

    for i, imagePath in enumerate(image_paths, 1):
        name = os.path.basename(os.path.dirname(imagePath))
        # print(f"[INFO] Processing {name}...") # Menos verboso para ser rapido
        
        image = cv2.imread(imagePath)
        if image is None: continue

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        boxes = face_recognition.face_locations(rgb, model=args.model)
        encs = face_recognition.face_encodings(rgb, boxes)
        
        for enc in encs:
            knownEncodings.append(enc)
            knownNames.append(name)

    data = {"encodings": knownEncodings, "names": knownNames}
    
    tmp_path = args.out + ".tmp"
    with open(tmp_path, "wb") as f:
        f.write(pickle.dumps(data))
    os.replace(tmp_path, args.out)

    # Guardamos el timestamp de FINALIZACION
    with open(TIMESTAMP_FILE, "w") as f:
        f.write(str(time.time()))

    print(f"[INFO] Training finished. Encodings: {len(knownEncodings)}")

if __name__ == "__main__":
    main()