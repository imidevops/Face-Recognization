import cv2
import face_recognition
import os
import numpy as np
from datetime import datetime
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import csv
import io

# --- Configuration ---
KNOWN_FACES_DIR = "known_faces"
ATTENDANCE_FILE = "attendance.csv"

app = FastAPI(title="Face Attendance Server")

# --- Global State ---
known_face_encodings = []
known_face_names = []

# --- Helper Functions ---

def load_known_faces():
    """Loads images from the directory and learns the faces."""
    global known_face_encodings, known_face_names
    print(f"Loading faces from {KNOWN_FACES_DIR}...")
    
    if not os.path.exists(KNOWN_FACES_DIR):
        os.makedirs(KNOWN_FACES_DIR)
        print(f"Created directory {KNOWN_FACES_DIR}. Please put images there.")
        return

    files = os.listdir(KNOWN_FACES_DIR)
    for file in files:
        if file.lower().endswith(('.jpg', '.jpeg', '.png')):
            path = os.path.join(KNOWN_FACES_DIR, file)
            try:
                image = face_recognition.load_image_file(path)
                encodings = face_recognition.face_encodings(image)
                if encodings:
                    known_face_encodings.append(encodings[0])
                    name = os.path.splitext(file)[0]
                    known_face_names.append(name)
                    print(f"Loaded: {name}")
            except Exception as e:
                print(f"Error loading {file}: {e}")

def mark_attendance(name):
    """Writes the name and timestamp to a CSV file."""
    if name == "Unknown":
        return

    now = datetime.now()
    date_string = now.strftime("%Y-%m-%d")
    time_string = now.strftime("%H:%M:%S")
    
    file_exists = os.path.isfile(ATTENDANCE_FILE)
    
    # Check if already marked today
    already_marked = False
    if file_exists:
        with open(ATTENDANCE_FILE, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0] == name and row[1] == date_string:
                    already_marked = True
                    break
    
    if not already_marked:
        with open(ATTENDANCE_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Name", "Date", "Time"])
            writer.writerow([name, date_string, time_string])
        print(f"Attendance marked for: {name}")

# --- Startup Event ---
@app.on_event("startup")
async def startup_event():
    load_known_faces()

# --- API Endpoints ---

@app.post("/api/process_frame")
async def process_frame(file: UploadFile = File(...)):
    """
    Receives an image file from the browser, detects faces, 
    marks attendance, and returns the face locations/names.
    """
    # Read image bytes
    contents = await file.read()
    
    # Convert bytes to numpy array for OpenCV
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Convert BGR (OpenCV) to RGB (face_recognition)
    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Detect faces
    face_locations = face_recognition.face_locations(rgb_img)
    face_encodings = face_recognition.face_encodings(rgb_img, face_locations)

    results = []

    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
        name = "Unknown"

        face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
        if len(face_distances) > 0:
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                name = known_face_names[best_match_index]

        mark_attendance(name)
        
        results.append({
            "name": name,
            "box": [top, right, bottom, left] # Return coordinates to draw on frontend
        })

    return JSONResponse(content={"faces": results})

@app.post("/api/recognize_from_file")
async def recognize_from_file(file_path: str):
    """Legacy API for local server files"""
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    image = face_recognition.load_image_file(file_path)
    face_locations = face_recognition.face_locations(image)
    face_encodings = face_recognition.face_encodings(image, face_locations)
    
    results = []
    for face_encoding in face_encodings:
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
        name = "Unknown"
        face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
        if len(face_distances) > 0:
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                name = known_face_names[best_match_index]
        
        mark_attendance(name)
        results.append({"name": name})
        
    return {"results": results}

@app.get("/")
async def index():
    """
    Serves the HTML page that accesses the Laptop Camera using JavaScript.
    """
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Server Face Attendance</title>
        <style>
            body { font-family: sans-serif; text-align: center; }
            #container { position: relative; display: inline-block; }
            video { border: 2px solid #333; border-radius: 8px; }
            canvas { position: absolute; top: 0; left: 0; }
            #status { margin-top: 10px; font-weight: bold; color: green; }
        </style>
    </head>
    <body>
        <h1>Live Attendance (Client-Side Camera)</h1>
        <div id="container">
            <video id="video" width="640" height="480" autoplay muted></video>
            <canvas id="overlay" width="640" height="480"></canvas>
        </div>
        <div id="status">Waiting for camera...</div>

        <script>
            const video = document.getElementById('video');
            const overlay = document.getElementById('overlay');
            const ctx = overlay.getContext('2d');
            const statusDiv = document.getElementById('status');

            // 1. Access the Laptop Camera
            navigator.mediaDevices.getUserMedia({ video: true })
                .then(stream => {
                    video.srcObject = stream;
                    statusDiv.innerText = "Camera Active. Sending frames to server...";
                    // Start the loop
                    setInterval(sendFrameToServer, 1000); // Send 1 frame every second
                })
                .catch(err => {
                    console.error("Error accessing camera:", err);
                    statusDiv.innerText = "Error: Cannot access camera. Allow permissions.";
                    statusDiv.style.color = "red";
                });

            // 2. Function to capture frame and send to Python
            function sendFrameToServer() {
                // Create a temporary canvas to capture the frame
                const tempCanvas = document.createElement('canvas');
                tempCanvas.width = video.videoWidth;
                tempCanvas.height = video.videoHeight;
                const tempCtx = tempCanvas.getContext('2d');
                tempCtx.drawImage(video, 0, 0);

                // Convert to Blob (JPG)
                tempCanvas.toBlob(blob => {
                    const formData = new FormData();
                    formData.append('file', blob, 'frame.jpg');

                    // Send to Python API
                    fetch('/api/process_frame', {
                        method: 'POST',
                        body: formData
                    })
                    .then(response => response.json())
                    .then(data => {
                        drawBoxes(data.faces);
                    })
                    .catch(err => console.error("Server error:", err));
                }, 'image/jpeg', 0.8);
            }

            // 3. Draw boxes based on Server Response
            function drawBoxes(faces) {
                // Clear previous drawings
                ctx.clearRect(0, 0, overlay.width, overlay.height);
                
                // Adjust scale if video size differs from display size
                const scaleX = overlay.width / video.videoWidth;
                const scaleY = overlay.height / video.videoHeight;

                faces.forEach(face => {
                    const [top, right, bottom, left] = face.box;
                    const name = face.name;

                    // Draw Box
                    ctx.strokeStyle = "#00FF00";
                    ctx.lineWidth = 3;
                    ctx.strokeRect(left * scaleX, top * scaleY, (right - left) * scaleX, (bottom - top) * scaleY);

                    // Draw Name Background
                    ctx.fillStyle = "#00FF00";
                    ctx.fillRect(left * scaleX, (bottom * scaleY) - 25, (right - left) * scaleX, 25);

                    // Draw Name Text
                    ctx.fillStyle = "black";
                    ctx.font = "18px Arial";
                    ctx.fillText(name, (left * scaleX) + 5, (bottom * scaleY) - 5);
                });
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    import uvicorn
#    uvicorn.run(app, host="0.0.0.0", port=8000)
    uvicorn.run(app, host="0.0.0.0", port=8000, ssl_keyfile="key.pem", ssl_certfile="cert.pem")

