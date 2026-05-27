import cv2 # pyright: ignore[reportMissingImports]
import numpy as np # pyright: ignore[reportMissingImports]

# Safe mediapipe import — handles both old and new versions
try:
    import mediapipe as mp # pyright: ignore[reportMissingImports]
    mp_pose = mp.solutions.pose
    mp_draw = mp.solutions.drawing_utils
    MEDIAPIPE_OK = True
except (AttributeError, ImportError):
    MEDIAPIPE_OK = False


# ── Geometry helpers ───────────────────────────────────────────────────────────
def calculate_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    radians = (np.arctan2(c[1] - b[1], c[0] - b[0]) -
               np.arctan2(a[1] - b[1], a[0] - b[0]))
    angle = np.abs(radians * 180.0 / np.pi)
    return 360 - angle if angle > 180 else angle


def midpoint(a, b):
    return [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]


# ── Drawing helpers ────────────────────────────────────────────────────────────
def draw_angle_arc(image, b_px, angle, color=(0, 255, 200)):
    """Draw a small arc at joint b to visualise the current angle."""
    cv2.putText(image, f"{angle:.0f}°", (b_px[0] + 10, b_px[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)


def draw_hud(image, reps, stage, feedback, form_score, exercise):
    h, w = image.shape[:2]

    # Semi-transparent overlay bar at top
    overlay = image.copy()
    cv2.rectangle(overlay, (0, 0), (w, 120), (20, 20, 40), -1)
    cv2.addWeighted(overlay, 0.6, image, 0.4, 0, image)

    # Rep count (large)
    cv2.putText(image, str(reps), (20, 80),
                cv2.FONT_HERSHEY_DUPLEX, 2.8, (0, 255, 150), 4)
    cv2.putText(image, "REPS", (20, 100),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)

    # Stage pill
    stage_color = (0, 200, 100) if stage == "up" else (0, 120, 255)
    stage_txt = (stage or "—").upper()
    cv2.putText(image, stage_txt, (120, 55),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, stage_color, 2)

    # Form score bar
    fs_pct = int(form_score / 10 * 100)
    bar_x, bar_y = 280, 30
    bar_w = 200
    cv2.rectangle(image, (bar_x, bar_y), (bar_x + bar_w, bar_y + 20), (60, 60, 60), -1)
    bar_color = (0, 200, 100) if form_score >= 7 else (0, 140, 255) if form_score >= 4 else (0, 60, 220)
    cv2.rectangle(image, (bar_x, bar_y), (bar_x + int(bar_w * form_score / 10), bar_y + 20), bar_color, -1)
    cv2.putText(image, f"Form {form_score:.1f}/10", (bar_x, bar_y + 45),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 220, 220), 1)

    # Exercise name top-right
    ex_label = exercise.replace("_", " ").title()
    cv2.putText(image, ex_label, (w - 220, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 200, 200), 1)

    # Feedback bottom bar
    cv2.rectangle(image, (0, h - 50), (w, h), (20, 20, 40), -1)
    cv2.putText(image, feedback[:70], (10, h - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 180), 2)


# ── Exercise logic ─────────────────────────────────────────────────────────────
def _bicep_curl(lm, rep_state, image, w, h):
    def pt(lmk): return [lm[lmk.value].x, lm[lmk.value].y]

    angle = calculate_angle(
        pt(mp_pose.PoseLandmark.LEFT_SHOULDER),
        pt(mp_pose.PoseLandmark.LEFT_ELBOW),
        pt(mp_pose.PoseLandmark.LEFT_WRIST)
    )
    elbow_px = (int(lm[mp_pose.PoseLandmark.LEFT_ELBOW.value].x * w),
                int(lm[mp_pose.PoseLandmark.LEFT_ELBOW.value].y * h))
    draw_angle_arc(image, elbow_px, angle)

    # Form: elbow should stay near torso (x-distance)
    shoulder_x = lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x
    elbow_x = lm[mp_pose.PoseLandmark.LEFT_ELBOW.value].x
    elbow_drift = abs(elbow_x - shoulder_x)
    form_penalty = min(elbow_drift * 20, 3)  # max 3 point deduction
    form_score = max(10 - form_penalty, 0)
    if elbow_drift > 0.08:
        feedback = "⚠️ Keep elbow tucked"
        
         # pyright: ignore[reportUndefinedVariable]
    else:
        feedback = "✅ Good form!"

    if angle > 160:
        rep_state["stage"] = "down"
        feedback = "⬇️ Good — now curl up!"
    if angle < 40 and rep_state["stage"] == "down":
        rep_state["stage"] = "up"
        rep_state["count"] += 1
        rep_state.setdefault("form_scores", []).append(form_score)
        feedback = f"💪 Rep {rep_state['count']}!"
        st.markdown( # pyright: ignore[reportUndefinedVariable]
            autoplay_audio( # pyright: ignore[reportUndefinedVariable]
                f"Great job! Rep {rep_state['count']}"
            ),
            unsafe_allow_html=True
        )
        
        

    return feedback, form_score


def _squat(lm, rep_state, image, w, h):
    def pt(lmk): return [lm[lmk.value].x, lm[lmk.value].y]

    angle = calculate_angle(
        pt(mp_pose.PoseLandmark.LEFT_HIP),
        pt(mp_pose.PoseLandmark.LEFT_KNEE),
        pt(mp_pose.PoseLandmark.LEFT_ANKLE)
    )
    knee_px = (int(lm[mp_pose.PoseLandmark.LEFT_KNEE.value].x * w),
               int(lm[mp_pose.PoseLandmark.LEFT_KNEE.value].y * h))
    draw_angle_arc(image, knee_px, angle)

    # Form: back angle (shoulder over hip over knee)
    shoulder_x = lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x
    hip_x = lm[mp_pose.PoseLandmark.LEFT_HIP.value].x
    knee_x = lm[mp_pose.PoseLandmark.LEFT_KNEE.value].x
    back_lean = abs(shoulder_x - hip_x)
    form_score = max(10 - back_lean * 15, 0)

    if back_lean > 0.12:
        feedback = "⚠️ Keep chest up!"
         # pyright: ignore[reportUndefinedVariable]
    else:
        feedback = "✅ Solid form!"

    if angle > 165:
        rep_state["stage"] = "up"
        feedback = "⬇️ Squat down — thighs parallel!"
    if angle < 90 and rep_state["stage"] == "up":
        rep_state["stage"] = "down"
        rep_state["count"] += 1
        rep_state.setdefault("form_scores", []).append(form_score)
        feedback = f"🦵 Squat {rep_state['count']}!"

    return feedback, form_score


def _pushup(lm, rep_state, image, w, h):
    def pt(lmk): return [lm[lmk.value].x, lm[lmk.value].y]

    angle = calculate_angle(
        pt(mp_pose.PoseLandmark.LEFT_SHOULDER),
        pt(mp_pose.PoseLandmark.LEFT_ELBOW),
        pt(mp_pose.PoseLandmark.LEFT_WRIST)
    )
    elbow_px = (int(lm[mp_pose.PoseLandmark.LEFT_ELBOW.value].x * w),
                int(lm[mp_pose.PoseLandmark.LEFT_ELBOW.value].y * h))
    draw_angle_arc(image, elbow_px, angle)

    # Form: hip sag (hip should be between shoulder and ankle y-pos)
    shoulder_y = lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y
    hip_y = lm[mp_pose.PoseLandmark.LEFT_HIP.value].y
    ankle_y = lm[mp_pose.PoseLandmark.LEFT_ANKLE.value].y
    ideal_hip_y = (shoulder_y + ankle_y) / 2
    hip_sag = abs(hip_y - ideal_hip_y)
    form_score = max(10 - hip_sag * 25, 0)

    if hip_sag > 0.1:
        feedback = "⚠️ Don't sag your hips!"
        # pyright: ignore[reportUndefinedVariable]
    else:
        feedback = "✅ Body straight!"
    if angle > 160:
        rep_state["stage"] = "up"
        feedback = "⬇️ Lower chest to floor!"
    if angle < 70 and rep_state["stage"] == "up":
        rep_state["stage"] = "down"
        rep_state["count"] += 1
        rep_state.setdefault("form_scores", []).append(form_score)
        feedback = f"🔥 Push-up {rep_state['count']}!"

    return feedback, form_score


def _shoulder_press(lm, rep_state, image, w, h):
    def pt(lmk): return [lm[lmk.value].x, lm[lmk.value].y]

    angle = calculate_angle(
        pt(mp_pose.PoseLandmark.LEFT_ELBOW),
        pt(mp_pose.PoseLandmark.LEFT_SHOULDER),
        pt(mp_pose.PoseLandmark.LEFT_HIP)
    )
    elbow_px = (int(lm[mp_pose.PoseLandmark.LEFT_ELBOW.value].x * w),
                int(lm[mp_pose.PoseLandmark.LEFT_ELBOW.value].y * h))
    draw_angle_arc(image, elbow_px, angle)

    # Check wrist above elbow (proper press path)
    wrist_y = lm[mp_pose.PoseLandmark.LEFT_WRIST.value].y
    elbow_y = lm[mp_pose.PoseLandmark.LEFT_ELBOW.value].y
    form_score = 9.0 if wrist_y < elbow_y else 6.0

    feedback = "⚠️ Wrists above elbows!" if wrist_y > elbow_y else "✅ Good path!"

    if angle > 150:
        rep_state["stage"] = "up"
        feedback = "⬆️ Full extension at top!"
    if angle < 80 and rep_state["stage"] == "up":
        rep_state["stage"] = "down"
        rep_state["count"] += 1
        rep_state.setdefault("form_scores", []).append(form_score)
        feedback = f"🙌 Press {rep_state['count']}!"

    return feedback, form_score


def _lateral_raise(lm, rep_state, image, w, h):
    def pt(lmk): return [lm[lmk.value].x, lm[lmk.value].y]

    # Use shoulder abduction angle
    angle = calculate_angle(
        pt(mp_pose.PoseLandmark.LEFT_HIP),
        pt(mp_pose.PoseLandmark.LEFT_SHOULDER),
        pt(mp_pose.PoseLandmark.LEFT_ELBOW)
    )
    shoulder_px = (int(lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x * w),
                   int(lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y * h))
    draw_angle_arc(image, shoulder_px, angle)

    # Form: elbow slightly bent (not locked)
    elbow_angle = calculate_angle(
        pt(mp_pose.PoseLandmark.LEFT_SHOULDER),
        pt(mp_pose.PoseLandmark.LEFT_ELBOW),
        pt(mp_pose.PoseLandmark.LEFT_WRIST)
    )
    form_score = 9.0 if 150 < elbow_angle < 175 else 6.5

    feedback = "✅ Good raise!" if angle > 70 else "⬆️ Raise arms to shoulder height!"

    if angle < 30:
        rep_state["stage"] = "down"
    if angle > 75 and rep_state["stage"] == "down":
        rep_state["stage"] = "up"
        rep_state["count"] += 1
        rep_state.setdefault("form_scores", []).append(form_score)
        feedback = f"💥 Raise {rep_state['count']}!"

    return feedback, form_score


def _lunge(lm, rep_state, image, w, h):
    def pt(lmk): return [lm[lmk.value].x, lm[lmk.value].y]

    # Front knee angle
    angle = calculate_angle(
        pt(mp_pose.PoseLandmark.LEFT_HIP),
        pt(mp_pose.PoseLandmark.LEFT_KNEE),
        pt(mp_pose.PoseLandmark.LEFT_ANKLE)
    )
    knee_px = (int(lm[mp_pose.PoseLandmark.LEFT_KNEE.value].x * w),
               int(lm[mp_pose.PoseLandmark.LEFT_KNEE.value].y * h))
    draw_angle_arc(image, knee_px, angle)

    # Form: knee shouldn't go past toes too much
    knee_x = lm[mp_pose.PoseLandmark.LEFT_KNEE.value].x
    ankle_x = lm[mp_pose.PoseLandmark.LEFT_ANKLE.value].x
    knee_overreach = max(0, knee_x - ankle_x) * 10
    form_score = max(10 - knee_overreach, 0)

    feedback = "⚠️ Knee past toes!" if knee_overreach > 0.5 else "✅ Solid lunge!"

    if angle > 160:
        rep_state["stage"] = "up"
        feedback = "⬇️ Lunge down — 90° at front knee!"
    if angle < 100 and rep_state["stage"] == "up":
        rep_state["stage"] = "down"
        rep_state["count"] += 1
        rep_state.setdefault("form_scores", []).append(form_score)
        feedback = f"🦵 Lunge {rep_state['count']}!"

    return feedback, form_score


def _plank(lm, rep_state, image, w, h):
    """Plank — counts time held, not reps. rep_state['count'] = seconds held."""
    def pt(lmk): return [lm[lmk.value].x, lm[lmk.value].y]

    # Body alignment: hip between shoulder and ankle
    shoulder_y = lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y
    hip_y = lm[mp_pose.PoseLandmark.LEFT_HIP.value].y
    ankle_y = lm[mp_pose.PoseLandmark.LEFT_ANKLE.value].y
    ideal_hip = (shoulder_y + ankle_y) / 2
    hip_deviation = abs(hip_y - ideal_hip)
    form_score = max(10 - hip_deviation * 30, 0)

    if hip_deviation < 0.05:
        if "plank_timer" not in rep_state:
            rep_state["plank_timer"] = 0
        rep_state["plank_timer"] = rep_state.get("plank_timer", 0) + 1
        rep_state["count"] = rep_state.get("plank_timer", 0) // 10  # ~seconds at ~10fps
        feedback = f"⏱️ Hold! {rep_state['count']}s — Body straight!"
    else:
        feedback = "⚠️ Hips too high or sagging — adjust alignment!"

    return feedback, form_score


def _tricep_dip(lm, rep_state, image, w, h):
    def pt(lmk): return [lm[lmk.value].x, lm[lmk.value].y]

    angle = calculate_angle(
        pt(mp_pose.PoseLandmark.LEFT_SHOULDER),
        pt(mp_pose.PoseLandmark.LEFT_ELBOW),
        pt(mp_pose.PoseLandmark.LEFT_WRIST)
    )
    elbow_px = (int(lm[mp_pose.PoseLandmark.LEFT_ELBOW.value].x * w),
                int(lm[mp_pose.PoseLandmark.LEFT_ELBOW.value].y * h))
    draw_angle_arc(image, elbow_px, angle)

    # Form: elbows stay close to body
    l_elbow_x = lm[mp_pose.PoseLandmark.LEFT_ELBOW.value].x
    l_shoulder_x = lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x
    elbow_flare = abs(l_elbow_x - l_shoulder_x)
    form_score = max(10 - elbow_flare * 20, 0)

    feedback = "⚠️ Keep elbows close!" if elbow_flare > 0.1 else "✅ Good dip!"

    if angle > 160:
        rep_state["stage"] = "up"
        feedback = "⬇️ Dip down — 90° elbows!"
    if angle < 90 and rep_state["stage"] == "up":
        rep_state["stage"] = "down"
        rep_state["count"] += 1
        rep_state.setdefault("form_scores", []).append(form_score)
        feedback = f"💪 Dip {rep_state['count']}!"

    return feedback, form_score


# ── Exercise registry ──────────────────────────────────────────────────────────
EXERCISE_HANDLERS = {
    "bicep_curl": _bicep_curl,
    "squat": _squat,
    "pushup": _pushup,
    "shoulder_press": _shoulder_press,
    "lateral_raise": _lateral_raise,
    "lunge": _lunge,
    "plank": _plank,
    "tricep_dip": _tricep_dip,
}

EXERCISE_GUIDES = {
    "bicep_curl": "Stand upright. Curl weight toward shoulder. Keep elbows fixed at sides. Lower slowly. Keep wrists neutral.",
    "squat": "Feet shoulder-width apart. Lower until thighs are parallel to floor. Keep chest up and knees behind toes. Drive through heels.",
    "pushup": "Start in plank position. Lower chest to floor keeping body straight. Push back up fully. Elbows at 45° from body.",
    "shoulder_press": "Hold weights at shoulder height. Press overhead until arms fully extended. Lower slowly under control.",
    "lateral_raise": "Hold weights at sides. Raise arms to shoulder height with slight elbow bend. Lower slowly. Don't shrug.",
    "lunge": "Step forward, lower back knee toward floor. Front knee tracks over ankle (not past toes). Push back to start.",
    "plank": "Forearms on floor, body straight from head to heels. Engage core and glutes. Hold position. Breathe steadily.",
    "tricep_dip": "Hands on surface behind you, fingers forward. Lower until elbows at 90°. Push back up. Keep elbows close.",
}

CALORIES_PER_REP = {
    "bicep_curl": 4,
    "squat": 8,
    "pushup": 6,
    "shoulder_press": 5,
    "lateral_raise": 3,
    "lunge": 7,
    "plank": 2,    # per second
    "tricep_dip": 5,
}


# ── Main process function ──────────────────────────────────────────────────────
def process_frame(frame, exercise="bicep_curl", rep_state=None):
    if rep_state is None:
        rep_state = {"count": 0, "stage": None, "form_scores": []}

    if not MEDIAPIPE_OK:
        cv2.putText(frame, "Install mediapipe==0.10.14", (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        return frame, rep_state["count"], rep_state["stage"], "MediaPipe not available", 0.0

    h, w = frame.shape[:2]

    with mp_pose.Pose(
        min_detection_confidence=0.55,
        min_tracking_confidence=0.55
    ) as pose:
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False
        results = pose.process(image)
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        feedback = "⚠️ No pose detected — step back from camera"
        form_score = 0.0

        if results.pose_landmarks:
            lm = results.pose_landmarks.landmark

            # Draw skeleton
            mp_draw.draw_landmarks(
                image,
                results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                mp_draw.DrawingSpec(color=(0, 255, 100), thickness=2, circle_radius=4),
                mp_draw.DrawingSpec(color=(100, 100, 255), thickness=2)
            )

            # Run exercise handler
            handler = EXERCISE_HANDLERS.get(exercise)
            if handler:
                feedback, form_score = handler(lm, rep_state, image, w, h)
            else:
                feedback = f"Unknown exercise: {exercise}"

        # Draw HUD on top
        avg_form = (sum(rep_state.get("form_scores", [form_score])) /
                    max(len(rep_state.get("form_scores", [1])), 1))
        draw_hud(image, rep_state["count"], rep_state.get("stage"), feedback, avg_form, exercise)

    return image, rep_state["count"], rep_state.get("stage"), feedback, form_score


def get_avg_form_score(rep_state):
    scores = rep_state.get("form_scores", [])
    return round(sum(scores) / len(scores), 1) if scores else 0.0