# Face Attendance System (FastAPI + OpenCV)

A robust, web-based Face Attendance System deployed on Debian 12. This project uses **FastAPI** for the backend and **face_recognition** (dlib) for state-of-the-art face detection.

It features a **Client-Side Camera** architecture, allowing the server to process video feeds from any connected client (laptop/mobile) via a web browser, ensuring the server doesn't need a physical webcam attached.

<img width="795" height="587" alt="image" src="https://github.com/user-attachments/assets/06666317-95d4-4f9f-ae7c-62e023c3e6d0" />

## 🚀 Features

*   **Live Face Recognition:** Detects faces in real-time via the browser webcam.
*   **Automatic Attendance:** Logs recognized names with timestamps to `attendance.csv`.
*   **Client-Side Capture:** Works on remote servers (VPS/Cloud) by using the client's browser camera.
*   **REST API:** Upload images programmatically to identify faces and mark attendance.
*   **Visual Feedback:** Draws bounding boxes and names on the live video feed.

## 🛠️ Prerequisites (Debian 12)

Before installing the Python libraries, you must install the system dependencies required to compile `dlib` and `opencv`.

~~~bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv cmake libopenblas-dev liblapack-dev libx11-dev libgtk-3-dev
~~~

## 📦 Installation

1.  **Clone the repository:**
    ~~~bash
    git clone https://github.com/yourusername/face-attendance.git
    cd face-attendance
    ~~~

2.  **Create a Virtual Environment:**
    ~~~bash
    python3 -m venv venv
    source venv/bin/activate
    ~~~

3.  **Install Python Dependencies:**
    ~~~bash
    pip install fastapi uvicorn[standard] numpy opencv-python face_recognition python-multipart
    ~~~

4.  **Create Directory Structure:**
    ~~~bash
    mkdir known_faces
    ~~~

## 🔐 HTTPS Configuration (Crucial)

Modern browsers (Chrome, Firefox, Safari) **block camera access** on insecure HTTP connections (unless using `localhost`). Since this runs on a server (e.g., `192.168.x.x`), you **must** use HTTPS.

Generate a self-signed certificate in the project root:

~~~bash
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
~~~
*Press `Enter` through the prompts.*

## 📸 Adding Known Faces

1.  Take a clear photo of the person you want to recognize.
2.  Rename the file to the person's name (e.g., `Elon Musk.jpg`, `Bill Gates.png`).
3.  Place the file inside the `known_faces/` directory.
4.  **Restart the server** to load the new faces.

## 🏃‍♂️ Running the Server

Activate your environment and run the app:

~~~bash
source venv/bin/activate
python3 main.py
~~~

The server will start on port `8000` with SSL enabled.

## 💻 Usage

### 1. Live Attendance (Browser)
1.  Open your web browser.
2.  Navigate to: `https://<YOUR_SERVER_IP>:8000`
    *   *Example:* `https://192.168.21.18:8000`
3.  **Security Warning:** You will see a "Potential Security Risk" warning because the certificate is self-signed.
    *   **Chrome:** Click *Advanced* -> *Proceed to...*
    *   **Firefox:** Click *Advanced* -> *Accept the Risk and Continue*.
4.  **Permissions:** Click **Allow** when the browser asks for Camera access.

### 2. API Usage
You can trigger recognition by uploading a file programmatically.

**Endpoint:** `POST /api/recognize_from_file`

**Example using cURL:**
~~~bash
curl -X POST "https://localhost:8000/api/recognize_from_file?file_path=/home/user/test_image.jpg" -k
~~~
*(Note: `-k` is used to ignore SSL warnings for self-signed certs)*

## 📂 Project Structure

~~~text
.
├── main.py                # Application entry point
├── attendance.csv         # Auto-generated attendance log
├── key.pem                # SSL Private Key
├── cert.pem               # SSL Certificate
├── known_faces/           # Directory for storing reference images
│   ├── Person A.jpg
│   └── Person B.png
└── README.md
~~~

## ❓ Troubleshooting

**"Waiting for camera..." / `navigator.mediaDevices is undefined`**
*   **Cause:** You are accessing the site via `http://` instead of `https://`.
*   **Fix:** Ensure you generated the SSL certificates and are accessing the URL with `https://`.

**"Can't open camera by index" (Server Logs)**
*   **Cause:** The server is trying to open a USB camera that doesn't exist.
*   **Fix:** Ensure you are using the updated `main.py` that relies on the *Client-Side* browser camera, not `cv2.VideoCapture(0)`.
