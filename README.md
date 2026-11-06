# RepSense – AI Calisthenics Coach (Version 1)

A beginner-friendly local webcam squat counter using Python, OpenCV and MediaPipe Pose.

## Requirements
- Python 3.10 or 3.11 (recommended: Python 3.11)
- A laptop webcam
- Windows, macOS or Linux

## Setup

Open a terminal in this folder.

### 1. Create a virtual environment

Windows:
```bash
py -3.11 -m venv .venv
.venv\Scripts\activate
```

macOS / Linux:
```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Run
```bash
python app.py
```

A camera window should open. Stand sideways to the camera with your full body visible.
Press `q` in the camera window to quit.

## How to use
- Place the laptop camera around hip height if possible.
- Stand far enough away that your hip, knee and ankle remain visible.
- Turn sideways to the camera.
- Start standing upright, then perform a controlled squat and return to standing.
- The first version uses the left hip, left knee and left ankle.
- It counts a rep after the knee angle crosses the down threshold and returns above the up threshold.

## Troubleshooting
- If the webcam does not open, close other apps using it. You can try `CAMERA_INDEX = 1` near the top of `app.py`.
- On macOS, allow camera access for Terminal or your code editor in System Settings > Privacy & Security > Camera.
- On Windows, allow desktop apps to access the camera in Settings > Privacy & security > Camera.
- If installation fails, confirm that Python 3.11 (64-bit) is installed and that the virtual environment is activated.

## Important
This is a learning prototype, not a medical or professional coaching device. The angle thresholds are starting values and may need adjustment for your body, camera position and squat style. Stop if you feel pain. Use a clear, safe space and do not rely on the rep count to judge exercise safety.
