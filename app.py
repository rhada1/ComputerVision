from flask import Flask, render_template, Response, request
import cv2
import face_recognition
import numpy as np
import pickle
from models import session, Presence, get_today_presences
import datetime
import os

app = Flask(__name__)

# Fonction pour générer le fichier d'encodages
def generate_encodings():
    KNOWN_FACES_DIR = "images"  # Dossier contenant les images de référence
    known_face_encodings = []
    known_face_names = []

    print("Generating encodings...")
    for filename in os.listdir(KNOWN_FACES_DIR):
        if filename.endswith((".jpg", ".jpeg", ".png")):
            # Charger l'image
            image_path = os.path.join(KNOWN_FACES_DIR, filename)
            image = face_recognition.load_image_file(image_path)
            # Obtenir l'encodage
            encodings = face_recognition.face_encodings(image)
            if encodings:
                known_face_encodings.append(encodings[0])
                # Utiliser le nom du fichier (sans extension) comme nom de la personne
                known_face_names.append(os.path.splitext(filename)[0])

    # Sauvegarder les encodages
    with open('face_encodings.pkl', 'wb') as f:
        pickle.dump((known_face_encodings, known_face_names), f)
    print("Encodings generated and saved!")
    return known_face_encodings, known_face_names

# Générer ou charger les encodages
try:
    with open('face_encodings.pkl', 'rb') as f:
        known_face_encodings, known_face_names = pickle.load(f)
    print("Existing encodings loaded!")
except FileNotFoundError:
    known_face_encodings, known_face_names = generate_encodings()


# Initialize video capture globally
video_capture = None


def get_video_capture():
    global video_capture
    if video_capture is None:
        video_capture = cv2.VideoCapture(0)
    return video_capture

def process_frame(frame):
    # Resize frame for faster processing
    small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
    
    face_locations = face_recognition.face_locations(rgb_small_frame)
    face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
    
    current_time = datetime.datetime.utcnow()
    face_names = []
    
    for face_encoding in face_encodings:
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
        name = "Unknown"
        if True in matches:
            face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
            best_match_index = np.argmin(face_distances)
            name = known_face_names[best_match_index]
            
            # Vérifier si assez de temps s'est écoulé depuis la dernière détection
            last_presence = session.query(Presence).filter_by(name=name).order_by(Presence.timestamp.desc()).first()
            if not last_presence or \
               (current_time - last_presence.timestamp).total_seconds() > 86400:  # 24h entre chaque détection
                # Save to database
                new_entry = Presence(name=name, timestamp=current_time)
                session.add(new_entry)
                try:
                    session.commit()
                    print(f"Presence recorded for {name}")
                except Exception as e:
                    print(f"Error saving to database: {e}")
                    session.rollback()
                
        face_names.append(name)
    
    # Scale back up face locations
    face_locations = np.array(face_locations) * 4
    
    # Draw the results
    for (top, right, bottom, left), name in zip(face_locations, face_names):
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
        cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 255, 0), cv2.FILLED)
        cv2.putText(frame, name, (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)
    
    return frame

def generate_frames():
    while True:
        cap = get_video_capture()
        success, frame = cap.read()
        if not success:
            break
        
        processed_frame = process_frame(frame)
        
        ret, buffer = cv2.imencode('.jpg', processed_frame)
        frame = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/regenerate_encodings', methods=['POST'])
def regenerate_encodings():
    global known_face_encodings, known_face_names
    known_face_encodings, known_face_names = generate_encodings()
    return "Encodings regenerated successfully"

@app.route('/stop', methods=['POST'])
def stop():
    global video_capture
    if video_capture:
        video_capture.release()
        video_capture = None
    return "Video stopped"

@app.route('/today_presences')
def today_presences():
    presences = get_today_presences()
    return render_template('presences.html', presences=presences)

@app.route('/upload_image', methods=['GET', 'POST'])
def upload_image():
    # Directory to save images
    upload_folder = "images"
    if request.method == 'POST':
        # Check if the POST request has the file part
        if 'image' not in request.files:
            return "No file part", 400
        file = request.files['image']
        if file.filename == '':
            return "No selected file", 400
        if file and file.filename.endswith((".jpg", ".jpeg", ".png")):
            file_path = os.path.join(upload_folder, file.filename)
            # Save the file to the images directory
            file.save(file_path)
            print(f"Image uploaded to {file_path}")
            
            # Remove the existing .pkl file
            if os.path.exists('face_encodings.pkl'):
                os.remove('face_encodings.pkl')
                print("Existing .pkl file removed.")
            
            # Regenerate encodings
            global known_face_encodings, known_face_names
            known_face_encodings, known_face_names = generate_encodings()
            return "Image uploaded and encodings regenerated successfully!"
        else:
            return "Invalid file type. Please upload a .jpg, .jpeg, or .png file.", 400
    return render_template('upload_image.html')


if __name__ == '__main__':
    app.run(debug=True)