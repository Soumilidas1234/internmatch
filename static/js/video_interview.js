// Local AI video interview. Camera and mic stay in the browser.
const lobby = document.getElementById("lobby");
const callScreen = document.getElementById("callScreen");
const resultScreen = document.getElementById("resultScreen");
const joinBtn = document.getElementById("joinBtn");
const domainSelect = document.getElementById("domain");
const userVideo = document.getElementById("userVideo");
const userCanvas = document.getElementById("userCanvas");
const youTile = document.getElementById("youTile");
const cameraOff = document.getElementById("cameraOff");
const previewCtx = userCanvas ? userCanvas.getContext("2d", { alpha: false }) : null;
let previewTimer = 0;
let imageCapture = null;
const questionText = document.getElementById("questionText");
const answerBox = document.getElementById("answerBox");
const callStatus = document.getElementById("callStatus");
const lobbyStatus = document.getElementById("lobbyStatus");
const aiTile = document.getElementById("aiTile");
const aiSpeaking = document.getElementById("aiSpeaking");
const callProgress = document.getElementById("callProgress");
const micBtn = document.getElementById("micBtn");
const cameraBtn = document.getElementById("cameraBtn");
const submitBtn = document.getElementById("submitBtn");
const endBtn = document.getElementById("endBtn");

let mediaStream = null;
let cameraOn = true;
let questions = [];
let domain = "";
let index = 0;
let results = [];
let listening = false;
let recognition = null;

function speak(text) {
    window.speechSynthesis.cancel();
    const voice = new SpeechSynthesisUtterance(text);
    voice.rate = 1;
    voice.pitch = 1;
    aiTile.classList.add("talking");
    aiSpeaking.textContent = "AI is speaking...";
    voice.onend = function () {
        aiTile.classList.remove("talking");
        aiSpeaking.textContent = "Listening";
    };
    window.speechSynthesis.speak(voice);
}

function setStatus(message) {
    callStatus.textContent = message;
}

function askCurrentQuestion() {
    const item = questions[index];
    const round = "Round " + (index + 1) + " of " + questions.length + ". " + item.q;
    questionText.textContent = round;
    answerBox.value = "";
    callProgress.style.width = Math.round((index / questions.length) * 100) + "%";
    speak("Hello. " + round + " Please answer when you are ready.");
    setStatus("Answer by speaking or typing, then send.");
}

function sizePreview() {
    if (!userCanvas) {
        return;
    }
    const rect = userCanvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const width = Math.max(2, Math.round(rect.width * dpr));
    const height = Math.max(2, Math.round(rect.height * dpr));
    if (userCanvas.width !== width) {
        userCanvas.width = width;
    }
    if (userCanvas.height !== height) {
        userCanvas.height = height;
    }
}

function drawBitmap(bitmap) {
    if (!previewCtx || !userCanvas) {
        return;
    }
    sizePreview();
    const canvasW = userCanvas.width;
    const canvasH = userCanvas.height;
    previewCtx.fillStyle = "#111827";
    previewCtx.fillRect(0, 0, canvasW, canvasH);
    const scale = Math.min(canvasW / bitmap.width, canvasH / bitmap.height);
    const drawW = bitmap.width * scale;
    const drawH = bitmap.height * scale;
    previewCtx.drawImage(bitmap, (canvasW - drawW) / 2, (canvasH - drawH) / 2, drawW, drawH);
}

function stopPreview() {
    if (previewTimer) {
        window.clearTimeout(previewTimer);
        previewTimer = 0;
    }
}

function useLiveVideo() {
    stopPreview();
    imageCapture = null;
    if (youTile) {
        youTile.classList.remove("snapshot-preview");
    }
}

async function grabLoop() {
    if (!imageCapture || !cameraOn) {
        previewTimer = window.setTimeout(grabLoop, 120);
        return;
    }
    try {
        const bitmap = await imageCapture.grabFrame();
        drawBitmap(bitmap);
        if (bitmap.close) {
            bitmap.close();
        }
    } catch (error) {
        useLiveVideo();
        return;
    }
    previewTimer = window.setTimeout(grabLoop, 120);
}

function startSnapshotPreview(track) {
    if (!window.ImageCapture) {
        useLiveVideo();
        return;
    }
    try {
        imageCapture = new ImageCapture(track);
    } catch (error) {
        useLiveVideo();
        return;
    }
    if (youTile) {
        youTile.classList.add("snapshot-preview");
    }
    stopPreview();
    grabLoop();
}

async function startCamera() {
    try {
        mediaStream = await navigator.mediaDevices.getUserMedia({
            video: true,
        });
        userVideo.srcObject = mediaStream;
        try {
            await userVideo.play();
        } catch (playError) {
            /* Stream is attached; a later gesture can start playback. */
        }
        cameraOff.classList.add("hidden");
        cameraOn = true;
        startSnapshotPreview(mediaStream.getVideoTracks()[0]);
    } catch (error) {
        cameraOff.classList.remove("hidden");
        cameraOn = false;
        setStatus("Camera permission was denied. You can still continue with typed answers.");
    }
}

function stopCamera() {
    stopPreview();
    imageCapture = null;
    if (mediaStream) {
        mediaStream.getTracks().forEach(function (track) {
            track.stop();
        });
        mediaStream = null;
    }
    window.speechSynthesis.cancel();
    if (recognition && listening) {
        recognition.stop();
    }
}

function setupSpeech() {
    const Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Speech) {
        return;
    }
    recognition = new Speech();
    recognition.lang = "en-IN";
    recognition.interimResults = false;
    recognition.onresult = function (event) {
        answerBox.value = event.results[0][0].transcript;
        setStatus("Voice captured. You can edit the text, then send.");
    };
    recognition.onend = function () {
        listening = false;
        micBtn.textContent = "🎙️ Speak";
    };
}

joinBtn.addEventListener("click", async function () {
    lobbyStatus.textContent = "Connecting to AI interviewer...";
    domain = domainSelect.value;
    const response = await fetch("/api/video-interview/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ domain: domain }),
    });
    const data = await response.json();
    if (!response.ok) {
        lobbyStatus.textContent = data.error || "Could not start the call.";
        return;
    }
    questions = data.questions;
    domain = data.domain;
    index = 0;
    results = [];
    lobby.classList.add("hidden");
    callScreen.classList.remove("hidden");
    await startCamera();
    setupSpeech();
    askCurrentQuestion();
});

micBtn.addEventListener("click", function () {
    if (!recognition) {
        setStatus("Voice input is not supported in this browser. Please type your answer.");
        return;
    }
    if (listening) {
        recognition.stop();
        return;
    }
    listening = true;
    micBtn.textContent = "🛑 Stop";
    setStatus("Listening... speak clearly.");
    recognition.start();
});

cameraBtn.addEventListener("click", function () {
    if (!mediaStream) {
        startCamera();
        return;
    }
    cameraOn = !cameraOn;
    mediaStream.getVideoTracks().forEach(function (track) {
        track.enabled = cameraOn;
    });
    cameraOff.classList.toggle("hidden", cameraOn);
    if (!cameraOn && previewCtx && userCanvas) {
        previewCtx.fillStyle = "#111827";
        previewCtx.fillRect(0, 0, userCanvas.width, userCanvas.height);
    }
});

submitBtn.addEventListener("click", async function () {
    const answer = answerBox.value.trim();
    if (!answer) {
        setStatus("Please speak or type an answer first.");
        return;
    }
    setStatus("AI interviewer is reviewing your answer...");
    const response = await fetch("/api/video-interview/score", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ domain: domain, index: index, answer: answer }),
    });
    const result = await response.json();
    results.push(result);
    speak(result.tip + " Sample answer: " + result.model);
    setStatus("Score: " + result.score + "/100. " + result.tip);

    index += 1;
    if (index >= questions.length) {
        callProgress.style.width = "100%";
        setTimeout(endCall, 3500);
    } else {
        setTimeout(askCurrentQuestion, 3500);
    }
});

function endCall() {
    stopCamera();
    callScreen.classList.add("hidden");
    resultScreen.classList.remove("hidden");
    const total = results.reduce(function (sum, item) {
        return sum + item.score;
    }, 0);
    const average = results.length ? Math.round(total / results.length) : 0;
    let rank = "Keep Training";
    if (average >= 80) {
        rank = "Arena Champion";
    } else if (average >= 60) {
        rank = "Strong Contender";
    }
    document.getElementById("finalScore").textContent = average + "/100";
    document.getElementById("finalRank").textContent = rank;
    const list = document.getElementById("resultList");
    list.innerHTML = "";
    results.forEach(function (item, number) {
        const card = document.createElement("article");
        card.className = "profile-card profile-card-wide";
        card.innerHTML = "<h3>Q" + (number + 1) + ". " + item.question + "</h3><p>Your answer: " + item.answer + "</p><p>Score: " + item.score + "/100</p>";
        list.appendChild(card);
    });
}

endBtn.addEventListener("click", endCall);
window.addEventListener("beforeunload", stopCamera);
