(function () {
    var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var nav = document.querySelector(".navbar");
    if (nav) {
        window.addEventListener("scroll", function () {
            nav.classList.toggle("scrolled", window.scrollY > 12);
        }, { passive: true });
    }

    document.querySelectorAll(".nav-drop").forEach(function (drop) {
        drop.addEventListener("toggle", function () {
            if (!drop.open) return;
            document.querySelectorAll(".nav-drop").forEach(function (other) {
                if (other !== drop) other.removeAttribute("open");
            });
        });
    });

    document.addEventListener("click", function (event) {
        if (!event.target.closest(".nav-drop")) {
            document.querySelectorAll(".nav-drop[open]").forEach(function (drop) {
                drop.removeAttribute("open");
            });
        }
    });

    if (!reduce && "IntersectionObserver" in window) {
        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add("in");
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.12 });
        document.querySelectorAll(".intern-card, .feature-card, .ai-tool-card, .roadmap-node, .admin-stat, .step").forEach(function (el) {
            if (!el.classList.contains("reveal")) {
                el.classList.add("js-inview");
                observer.observe(el);
            }
        });
    }

    document.querySelectorAll(".score-ring[data-score]").forEach(function (ring) {
        var target = Math.max(0, Math.min(100, parseInt(ring.getAttribute("data-score"), 10) || 0));
        var label = ring.querySelector("span");
        if (reduce) {
            ring.style.setProperty("--pct", String(target));
            if (label) label.textContent = target + "%";
            return;
        }
        var start = performance.now();
        function tick(now) {
            var t = Math.min(1, (now - start) / 900);
            var n = Math.round(target * t);
            ring.style.setProperty("--pct", String(n));
            if (label) label.textContent = n + "%";
            if (t < 1) requestAnimationFrame(tick);
        }
        requestAnimationFrame(tick);
    });

    document.querySelectorAll(".skill-meter .bar > i[data-width]").forEach(function (bar) {
        var width = bar.getAttribute("data-width");
        requestAnimationFrame(function () {
            bar.style.width = width + "%";
        });
    });

    var greet = document.getElementById("dash-greet");
    if (greet) {
        var hour = new Date().getHours();
        var phrase = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
        greet.textContent = phrase + ",";
    }

    document.querySelectorAll("form").forEach(function (form) {
        form.addEventListener("submit", function () {
            var loader = form.querySelector(".ai-loader");
            if (loader) loader.classList.add("on");
            var steps = loader ? loader.querySelectorAll(".analyze-steps li") : [];
            if (steps.length && !reduce) {
                var i = 0;
                steps[0].classList.add("on");
                var timer = setInterval(function () {
                    i += 1;
                    if (i >= steps.length) {
                        clearInterval(timer);
                        return;
                    }
                    steps[i].classList.add("on");
                }, 700);
            }
        });
    });

    var SOUND_KEY = "im-feature-sound";
    var PLAYED_KEY = "im-feature-sound-played";
    var FEATURE_PATHS = [
        "/dashboard",
        "/resume-analyzer",
        "/resume-fixer",
        "/skill-gap",
        "/readiness",
        "/career-roadmap",
        "/preparation-plan",
        "/examiner",
        "/resume-interview",
        "/interview-questions",
        "/video-interview",
        "/video_interview",
        "/progress",
        "/ats-simulator",
        "/job-analyzer"
    ];
    var audioCtx = null;
    var soundOn = localStorage.getItem(SOUND_KEY);
    if (soundOn === null) soundOn = "on";
    var toggle = document.getElementById("sound-toggle");

    function soundEnabled() {
        return soundOn !== "off";
    }

    function syncToggle() {
        if (!toggle) return;
        var on = soundEnabled();
        toggle.classList.toggle("is-on", on);
        toggle.setAttribute("aria-pressed", on ? "true" : "false");
        toggle.title = on ? "Feature sounds on" : "Feature sounds off";
        toggle.textContent = on ? "Sound on" : "Sound off";
    }

    function getAudio() {
        var Ctx = window.AudioContext || window.webkitAudioContext;
        if (!Ctx) return null;
        if (!audioCtx) audioCtx = new Ctx();
        if (audioCtx.state === "suspended") audioCtx.resume();
        return audioCtx;
    }

    function playFeatureSound() {
        if (!soundEnabled()) return;
        var ctx = getAudio();
        if (!ctx) return;

        function start() {
            markPlayed();
            var now = ctx.currentTime;
            var master = ctx.createGain();
            master.gain.setValueAtTime(0.07, now);
            master.connect(ctx.destination);

            function tone(freq, at, dur, type) {
                var osc = ctx.createOscillator();
                var gain = ctx.createGain();
                osc.type = type || "sine";
                osc.frequency.setValueAtTime(freq, now + at);
                gain.gain.setValueAtTime(0.0001, now + at);
                gain.gain.exponentialRampToValueAtTime(0.9, now + at + 0.018);
                gain.gain.exponentialRampToValueAtTime(0.0001, now + at + dur);
                osc.connect(gain);
                gain.connect(master);
                osc.start(now + at);
                osc.stop(now + at + dur + 0.03);
            }

            tone(392, 0, 0.18, "sine");
            tone(523.25, 0.06, 0.22, "triangle");
            tone(783.99, 0.14, 0.28, "sine");
        }

        if (ctx.state === "suspended") {
            ctx.resume().then(start);
            return;
        }
        start();
    }

    function isFeaturePath(path) {
        return FEATURE_PATHS.some(function (item) {
            return path === item || path.indexOf(item + "/") === 0;
        });
    }

    function markPlayed() {
        try { sessionStorage.setItem(PLAYED_KEY, String(Date.now())); } catch (err) {}
    }

    function recentlyPlayed() {
        try {
            var stamp = parseInt(sessionStorage.getItem(PLAYED_KEY) || "0", 10);
            return Date.now() - stamp < 1600;
        } catch (err) {
            return false;
        }
    }

    function openFeatureSound() {
        if (recentlyPlayed()) return;
        playFeatureSound();
    }

    syncToggle();
    if (toggle) {
        toggle.addEventListener("click", function () {
            soundOn = soundEnabled() ? "off" : "on";
            localStorage.setItem(SOUND_KEY, soundOn);
            syncToggle();
            if (soundEnabled()) playFeatureSound();
        });
    }

    document.querySelectorAll(".feature-card, .ai-tool-card").forEach(function (card) {
        card.addEventListener("click", function () {
            openFeatureSound();
        });
    });

    document.querySelectorAll(".navbar nav a").forEach(function (link) {
        var href = link.getAttribute("href") || "";
        var path = href.replace(window.location.origin, "");
        if (isFeaturePath(path)) {
            link.addEventListener("click", function () {
                openFeatureSound();
            });
        }
    });

    if (isFeaturePath(window.location.pathname)) {
        function playArrival() {
            if (!soundEnabled() || recentlyPlayed()) return;
            openFeatureSound();
        }
        playArrival();
        document.addEventListener("pointerdown", playArrival, { once: true });
        document.addEventListener("keydown", playArrival, { once: true });
    }
})();
