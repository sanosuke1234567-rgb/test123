const exerciseList = document.getElementById("exerciseList");
const exerciseTemplate = document.getElementById("exerciseTemplate");
const addExerciseButton = document.getElementById("addExercise");
const startSessionButton = document.getElementById("startSession");
const resetSessionButton = document.getElementById("resetSession");
const actionButton = document.getElementById("actionButton");
const pauseButton = document.getElementById("pauseButton");
const skipButton = document.getElementById("skipButton");
const phaseLabel = document.getElementById("phaseLabel");
const timeText = document.getElementById("timeText");
const pointerLabel = document.getElementById("pointerLabel");
const ringLabel = document.getElementById("ringLabel");
const pointerHand = document.querySelector(".pointer .hand");
const ringProgress = document.querySelector(".ring-progress");
const exerciseName = document.getElementById("exerciseName");
const setCount = document.getElementById("setCount");
const weightValue = document.getElementById("weightValue");
const nextHint = document.getElementById("nextHint");
const styleButtons = document.querySelectorAll(".style-btn");
const timerFaces = document.querySelectorAll(".timer-face");

const RING_CIRCUMFERENCE = 2 * Math.PI * 100;
ringProgress.style.strokeDasharray = `${RING_CIRCUMFERENCE}`;

let exercises = [];
let sessionState = null;
let intervalId = null;

const createExerciseCard = () => {
  const fragment = exerciseTemplate.content.cloneNode(true);
  const card = fragment.querySelector(".exercise-card");
  const removeButton = fragment.querySelector(".remove-exercise");

  removeButton.addEventListener("click", () => {
    card.remove();
    syncExercises();
  });

  card.querySelectorAll("input").forEach((input) => {
    input.addEventListener("input", syncExercises);
  });

  exerciseList.appendChild(fragment);
};

const formatTime = (seconds) => {
  const safeSeconds = Math.max(0, Math.ceil(seconds));
  const mins = String(Math.floor(safeSeconds / 60)).padStart(2, "0");
  const secs = String(safeSeconds % 60).padStart(2, "0");
  return `${mins}:${secs}`;
};

const setTimerDisplay = (secondsRemaining, totalSeconds) => {
  const formatted = formatTime(secondsRemaining);
  timeText.textContent = formatted;
  pointerLabel.textContent = formatted;
  ringLabel.textContent = formatted;

  const progress = totalSeconds > 0 ? secondsRemaining / totalSeconds : 0;
  const rotation = progress * 360;
  pointerHand.style.transform = `rotate(${rotation}deg)`;
  ringProgress.style.strokeDashoffset = `${RING_CIRCUMFERENCE * (1 - progress)}`;
};

const syncExercises = () => {
  exercises = Array.from(exerciseList.querySelectorAll(".exercise-card")).map((card) => {
    const name = card.querySelector(".exercise-name").value.trim();
    const sets = Number(card.querySelector(".exercise-sets").value || 0);
    const restSet = Number(card.querySelector(".exercise-rest-set").value || 0);
    const restExercise = Number(card.querySelector(".exercise-rest-exercise").value || 0);
    const weight = card.querySelector(".exercise-weight").value.trim();

    return {
      name: name || "未命名动作",
      sets: Math.max(1, sets),
      restSet: Math.max(0, restSet),
      restExercise: Math.max(0, restExercise),
      weight: weight || "-",
    };
  });
};

const resetUIState = () => {
  phaseLabel.textContent = "未开始";
  exerciseName.textContent = "-";
  setCount.textContent = "-";
  weightValue.textContent = "-";
  nextHint.textContent = "准备开始训练。";
  setTimerDisplay(0, 0);
  actionButton.textContent = "开始休息";
  actionButton.disabled = true;
  pauseButton.disabled = true;
  skipButton.disabled = true;
  resetSessionButton.disabled = true;
  startSessionButton.disabled = false;
  toggleInputsDisabled(false);
};

const toggleInputsDisabled = (disabled) => {
  exerciseList.querySelectorAll("input").forEach((input) => {
    input.disabled = disabled;
  });
  exerciseList.querySelectorAll(".remove-exercise").forEach((button) => {
    button.disabled = disabled;
  });
  addExerciseButton.disabled = disabled;
};

const startSession = () => {
  syncExercises();
  if (!exercises.length) {
    createExerciseCard();
    syncExercises();
  }

  sessionState = {
    exerciseIndex: 0,
    setIndex: 1,
    phase: "ready",
    restType: null,
    remaining: 0,
    total: 0,
    paused: false,
  };

  startSessionButton.disabled = true;
  resetSessionButton.disabled = false;
  actionButton.disabled = false;
  pauseButton.disabled = true;
  skipButton.disabled = true;
  toggleInputsDisabled(true);
  updateStatus();
};

const updateStatus = () => {
  if (!sessionState) {
    resetUIState();
    return;
  }

  const currentExercise = exercises[sessionState.exerciseIndex];
  exerciseName.textContent = currentExercise?.name ?? "-";
  setCount.textContent = currentExercise
    ? `${sessionState.setIndex}/${currentExercise.sets}`
    : "-";
  weightValue.textContent = currentExercise?.weight ?? "-";

  if (sessionState.phase === "ready") {
    phaseLabel.textContent = "准备完成当前组";
    nextHint.textContent = "完成本组后点击“开始休息”。";
    actionButton.textContent = "开始休息";
    pauseButton.disabled = true;
    skipButton.disabled = true;
    setTimerDisplay(0, 0);
    return;
  }

  if (sessionState.phase === "rest") {
    phaseLabel.textContent = sessionState.restType === "set" ? "组间休息" : "动作间休息";
    nextHint.textContent = "倒计时结束后自动进入下一组。";
    actionButton.textContent = "完成休息";
    pauseButton.disabled = false;
    skipButton.disabled = false;
  }

  if (sessionState.phase === "finished") {
    phaseLabel.textContent = "训练完成";
    nextHint.textContent = "已经完成全部动作。";
    actionButton.disabled = true;
    pauseButton.disabled = true;
    skipButton.disabled = true;
  }
};

const moveToNext = () => {
  const currentExercise = exercises[sessionState.exerciseIndex];
  if (!currentExercise) {
    sessionState.phase = "finished";
    updateStatus();
    return;
  }

  if (sessionState.setIndex < currentExercise.sets) {
    sessionState.setIndex += 1;
  } else {
    sessionState.exerciseIndex += 1;
    sessionState.setIndex = 1;
  }

  if (sessionState.exerciseIndex >= exercises.length) {
    sessionState.phase = "finished";
  } else {
    sessionState.phase = "ready";
  }

  sessionState.restType = null;
  sessionState.remaining = 0;
  sessionState.total = 0;
  clearInterval(intervalId);
  intervalId = null;
  updateStatus();
};

const startRest = () => {
  const currentExercise = exercises[sessionState.exerciseIndex];
  if (!currentExercise) {
    sessionState.phase = "finished";
    updateStatus();
    return;
  }

  const isLastSet = sessionState.setIndex >= currentExercise.sets;
  const hasNextExercise = sessionState.exerciseIndex < exercises.length - 1;

  let restSeconds = 0;
  if (!isLastSet) {
    restSeconds = currentExercise.restSet;
    sessionState.restType = "set";
  } else if (hasNextExercise) {
    restSeconds = currentExercise.restExercise;
    sessionState.restType = "exercise";
  }

  if (restSeconds <= 0) {
    moveToNext();
    return;
  }

  sessionState.phase = "rest";
  sessionState.remaining = restSeconds;
  sessionState.total = restSeconds;
  sessionState.paused = false;
  setTimerDisplay(sessionState.remaining, sessionState.total);
  updateStatus();

  intervalId = setInterval(() => {
    if (sessionState.paused) {
      return;
    }
    sessionState.remaining -= 1;
    setTimerDisplay(sessionState.remaining, sessionState.total);
    if (sessionState.remaining <= 0) {
      clearInterval(intervalId);
      intervalId = null;
      moveToNext();
    }
  }, 1000);
};

const togglePause = () => {
  if (!sessionState || sessionState.phase !== "rest") {
    return;
  }
  sessionState.paused = !sessionState.paused;
  pauseButton.textContent = sessionState.paused ? "继续" : "暂停";
};

const skipRest = () => {
  if (!sessionState || sessionState.phase !== "rest") {
    return;
  }
  clearInterval(intervalId);
  intervalId = null;
  moveToNext();
};

const resetSession = () => {
  sessionState = null;
  clearInterval(intervalId);
  intervalId = null;
  pauseButton.textContent = "暂停";
  resetUIState();
};

const handleActionButton = () => {
  if (!sessionState) {
    return;
  }
  if (sessionState.phase === "ready") {
    startRest();
    return;
  }
  if (sessionState.phase === "rest") {
    skipRest();
  }
};

styleButtons.forEach((button) => {
  button.addEventListener("click", () => {
    styleButtons.forEach((btn) => btn.classList.remove("active"));
    button.classList.add("active");
    const style = button.dataset.style;
    timerFaces.forEach((face) => {
      face.classList.toggle("active", face.classList.contains(style));
    });
  });
});

addExerciseButton.addEventListener("click", () => {
  createExerciseCard();
  syncExercises();
});

startSessionButton.addEventListener("click", startSession);
resetSessionButton.addEventListener("click", resetSession);
actionButton.addEventListener("click", handleActionButton);
pauseButton.addEventListener("click", togglePause);
skipButton.addEventListener("click", skipRest);

createExerciseCard();
createExerciseCard();
resetUIState();
