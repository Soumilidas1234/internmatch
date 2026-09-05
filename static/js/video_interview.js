// Local AI video interview. Camera and mic stay in the browser.
const lobby = document.getElementById("lobby");
const callScreen = document.getElementById("callScreen");
const resultScreen = document.getElementById("resultScreen");
const joinBtn = document.getElementById("joinBtn");
const domainSelect = document.getElementById("domain");
const userVideo = document.getElementById("userVideo");
const cameraOff = document.getElementById("cameraOff");
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

function showCameraHelp(message) {
    cameraOff.textContent = message;
    cameraOff.classList.remove("hidden");
    setStatus(message);
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

async function startCamera() {
    try {
        if (mediaStream) {
            mediaStream.getTracks().forEach(function (track) {
                track.stop();
            });
            mediaStream = null;
        }
        mediaStream = await navigator.mediaDevices.getUserMedia({ video: true });
        userVideo.srcObject = mediaStream;
        await userVideo.play();
        cameraOff.classList.add("hidden");
        cameraOn = true;
    } catch (error) {
        cameraOn = false;
        if (error && error.name === "NotReadableError") {
            showCameraHelp("Camera is already in use. Close other InternMatch tabs, then click Camera.");
        } else if (error && error.name === "NotAllowedError") {
            showCameraHelp("Chrome blocked the camera. Click the camera icon in the address bar, choose Allow, refresh, then click Camera.");
        } else {
            showCameraHelp("Camera could not start. You can still type your answers.");
        }
    }
}

function stopCamera() {
    if (mediaStream) {
        mediaStream.getTracks().forEach(function (track) {
            track.stop();
        });
        mediaStream = null;
    }
    userVideo.srcObject = null;
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
    lobbyStatus.textContent = "Starting practice...";
    domain = domainSelect.value;
    const response = await fetch("/api/video-interview/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ domain: domain }),
    });
    const data = await response.json();
    if (!response.ok) {
        lobbyStatus.textContent = data.error || "Could not start the interview.";
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
    if (cameraOn) {
        cameraOff.classList.add("hidden");
    } else {
        showCameraHelp("Camera is off. Click Camera to turn it back on.");
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
