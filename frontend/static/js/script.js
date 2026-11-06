
console.log("RepSense JavaScript loaded!");

let cameraStream = null;
let processing = false;
let animationFrame = null;

const videoCanvas = document.createElement("canvas");
const canvasContext = videoCanvas.getContext("2d");

const WEIGHT = 65;


// START WORKOUT
async function startWorkout() {

    if (cameraStream) return;

    const cameraArea = document.getElementById("cameraArea");
    const exerciseSelect = document.getElementById("exerciseSelect");

    const exercise = exerciseSelect
        ? exerciseSelect.value
        : "squat";

    const exerciseNames = {
        squat: "Squats",
        pushup: "Push-ups",
        bicep_curl: "Bicep Curls"
    };

    try {

        cameraStream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: 640,
                height: 480,
                facingMode: "user"
            },
            audio: false
        });

        const started = await fetch("/api/start", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                weight: WEIGHT,
                exercise: exercise
            })
        });

        if (!started.ok) {
            const errorData = await started.json();
            throw new Error(errorData.error || "Could not start workout");
        }

        const exerciseElement = document.getElementById("currentExercise");

        if (exerciseElement) {
        exerciseElement.innerText = exerciseNames[exercise];
} else {
    console.error("Missing HTML element: currentExercise");
}
        cameraArea.innerHTML = `
            <video id="cameraVideo"
                autoplay playsinline muted
                style="display:none">
            </video>

            <img id="processedFrame"
                style="width:100%;border-radius:10px;min-height:300px;object-fit:contain;background:#090e14">
        `;

        const video = document.getElementById("cameraVideo");
        const output = document.getElementById("processedFrame");

        video.srcObject = cameraStream;

        await video.play();

        document.getElementById("feedback").innerText =
            "AI camera connected. Detecting your posture...";

        processing = true;

        async function processFrame() {

            if (!processing || video.readyState < 2) {

                if (processing) {
                    animationFrame = requestAnimationFrame(processFrame);
                }

                return;
            }

            videoCanvas.width = 640;
            videoCanvas.height = 480;

            canvasContext.drawImage(
                video,
                0,
                0,
                640,
                480
            );

            const frame = videoCanvas.toDataURL(
                "image/jpeg",
                0.65
            );

            try {

                const response = await fetch("/api/frame", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({ frame })
                });

                if (!response.ok) {
                    throw new Error("AI processing failed");
                }

                const result = await response.json();

                output.src = result.image;

                updateStats(result.stats);

            } catch (error) {

                console.error(error);

                document.getElementById("feedback").innerText =
                    "AI processing error. Check backend.";
            }

            if (processing) {
                animationFrame = requestAnimationFrame(processFrame);
            }
        }

        processFrame();

    } catch (error) {

        console.error(error);

        stopCameraOnly();

        document.getElementById("feedback").innerText =
            error.message || "Could not connect. Check camera permissions and Flask server.";
    }
}


// UPDATE DASHBOARD
function updateStats(stats) {

    if (!stats) return;

    const repCount = document.getElementById("repCount");
    const calories = document.getElementById("calories");
    const duration = document.getElementById("duration");
    const kneeAngle = document.getElementById("kneeAngle");
    const angleLabel = document.getElementById("angleLabel");
    const formScore = document.getElementById("formScore");
    const currentExercise = document.getElementById("currentExercise");
    const feedback = document.getElementById("feedback");

    if (repCount)
        repCount.innerText = String(stats.reps).padStart(2, "0");

    if (calories)
        calories.innerText = Number(stats.calories).toFixed(1);

    if (duration) {
        const minutes = Math.floor(stats.time / 60);
        const seconds = Math.floor(stats.time % 60);

        duration.innerText =
            `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
    }

    if (kneeAngle)
        kneeAngle.innerText = stats.angle + "°";

    if (angleLabel)
        angleLabel.innerText = stats.angle_label || "Joint Angle";

    if (formScore)
        formScore.innerText = (stats.form_score ?? 0) + "%";

    if (currentExercise)
        currentExercise.innerText = stats.exercise_name || "Workout";

    if (feedback)
        feedback.innerText = stats.feedback || "Analyzing movement...";
}

// STOP CAMERA
function stopCameraOnly() {

    processing = false;

    if (animationFrame !== null) {
        cancelAnimationFrame(animationFrame);
        animationFrame = null;
    }

    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
    }
}


// STOP WORKOUT
async function stopWorkout() {

    processing = false;

    if (animationFrame !== null) {
        cancelAnimationFrame(animationFrame);
        animationFrame = null;
    }

    try {

        const response = await fetch("/api/stop", {
            method: "POST"
        });

        const result = await response.json();

        if (result.stats) {
            updateStats(result.stats);
        }

    } catch (error) {

        console.error("Stop error:", error);
    }

    stopCameraOnly();

    document.getElementById("cameraArea").innerHTML = `
        <div class="camera-symbol">◎</div>
        <h3>Workout stopped</h3>
        <p>Ready for your next session?</p>
        <button class="start-btn" onclick="startWorkout()">
            Start Again
        </button>
    `;

   const feedbackElement = document.getElementById("feedback");

if (feedbackElement) {
    feedbackElement.innerText =
        "Workout session stopped. Your session has been saved.";
}
}


// PAGE INITIALIZATION
document.addEventListener("DOMContentLoaded", () => {

    console.log("RepSense AI frontend connected.");

    window.startWorkout = startWorkout;
    window.stopWorkout = stopWorkout;

});
