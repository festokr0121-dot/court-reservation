import ctypes, sys
import datetime
import time
import os
import json
import threading
import colorsys
import math
import tkinter as tk
from tkinter import ttk
import pyautogui
import keyboard
from tkcalendar import Calendar

# 실행 방식(더블클릭/IDE 실행 등)에 따라 현재 작업 폴더가 달라져도
# 항상 이 스크립트가 있는 폴더에 설정 파일을 저장/불러오기 하도록 고정한다.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REFRESH_FOCUS_X = 766
REFRESH_FOCUS_Y = 373
REFRESH_PRE_F5_DELAY_SEC = 0.40
AUTO_START_FIRST_CLICK_X = 235
AUTO_START_FIRST_CLICK_Y = 330
AUTO_START_AFTER_FIRST_CLICK_DELAY_SEC = 0.1
AUTO_START_NOT_PERIOD_CHECK_X = 665
AUTO_START_NOT_PERIOD_CHECK_Y = 207
AUTO_START_NOT_PERIOD_COLOR = (0, 0, 0)
AUTO_START_LOADING_CHECK_X = 56
AUTO_START_LOADING_CHECK_Y = 60
AUTO_START_LOADING_COLOR = (39, 35, 32)
AUTO_START_LOADING_POLL_SEC = 0.005
AUTO_START_RESPONSE_SETTLE_SEC = 0.3
AUTO_START_RETRY_CLICK_DELAY_SEC = 0.1
AUTO_START_NEXT_MONTH_CLICK_X = 682
AUTO_START_NEXT_MONTH_CLICK_Y = 675
AUTO_START_AFTER_NEXT_CLICK_DELAY_SEC = 0.1
AUTO_START_AFTER_PAGE_DOWN_DELAY_SEC = 0.3
MANUAL_START_AFTER_PAGE_DOWN_DELAY_SEC = 0.3
MANUAL_START_POPUP_CLOSE_TIMEOUT_SEC = 1.0
MANUAL_POPUP_RECLICK_DELAY_SEC = 0.1
MANUAL_ERROR_POPUP_POSITION = (665, 207)
MANUAL_ERROR_POPUP_COLOR = (39, 35, 32)
MANUAL_ERROR_POPUP_HOVER_COLOR = (0, 0, 0)
MANUAL_DEV_POPUP_POSITION = (579, 705)
MANUAL_DEV_POPUP_COLOR = (240, 248, 255)
MANUAL_DEV_POPUP_PAGE_UP_DELAY_SEC = 0.3
AUTO_START_AFTER_LIST_COMPLETE_DELAY_SEC = 0.3
AUTO_START_AFTER_LIST_PAGE_UP_DELAY_SEC = 0.3
AUTO_START_PAGE_UP_RETRY_DELAY_SEC = 0.3
AUTO_RECOVERY_ENABLED = True
STARTUP_STRONG_PRECHECK_ENABLED = True
RESERVATION_LIGHT_CHECK_ENABLED = True
RECOVERY_RETRY_LIMIT = 2
RECOVERY_WARMUP_DELAY_SEC = 0.03

# ============================
# 창 열림 색상감지 시간(한곳 관리)
# ============================
TIME_WINDOW_OPEN_TIMEOUT_SEC = 0.35
COURT_WINDOW_OPEN_TIMEOUT_SEC = 1.0
USAGE_WINDOW_OPEN_TIMEOUT_SEC = 1.0
PEOPLE_WINDOW_OPEN_TIMEOUT_SEC = 1.0
PEOPLE_NEXT_STEP_MARKER_TIMEOUT_SEC = 1.0
PAYMENT_WINDOW_OPEN_TIMEOUT_SEC = 1.0
TIME_WINDOW_CLOSE_TIMEOUT_SEC = 1.0
COURT_WINDOW_CLOSE_TIMEOUT_SEC = 1.0
USAGE_WINDOW_CLOSE_TIMEOUT_SEC = 1.0
PAYMENT_WINDOW_CLOSE_TIMEOUT_SEC = 1.0
PAYMENT_WINDOW_OPEN_RETRY_TIMEOUT_SEC = 1.0
PAYMENT_WINDOW_OPEN_FINAL_TIMEOUT_SEC = 1.0
WINDOW_DETECT_POLL_INTERVAL_SEC = 1.0 / 60.0
SAFE_SLEEP_TICK_SEC = 1.0 / 60.0
NEXT_RESERVATION_TRANSITION_DELAY_SEC = 0.10
DATE_CLICK_PREP_DELAY_SEC = 0.01
DATE_CLICK_BEFORE_CLICK_DELAY_SEC = 0.02
TIME_WINDOW_OPEN_MAX_RETRIES = 2
TIME_WINDOW_CANCEL_MAX_ATTEMPTS = 2
TIME_WINDOW_OPEN_RETRY_GAP_SEC = 0.01
TIME_WINDOW_OPEN_TIMEOUT_STEPS_SEC = [0.35, 0.50]
TIME_WINDOW_USE_BRIGHTNESS_FALLBACK = False
NEXT_RESERVATION_AFTER_ESC = "NEXT_RESERVATION_AFTER_ESC"
PEOPLE_STAGE_TEST_LOG_ENABLED = False
WINDOW_OPEN_STABLE_HITS = 1
WINDOW_CLOSE_STABLE_HITS = 2
PAYMENT_WINDOW_MARKERS = [
    (492, 899),
    (574, 893),
]
PAYMENT_WINDOW_MARKER_REQUIRED_HITS = 1
TIME_WINDOW_MARKERS = [
    (478, 812),
    (559, 806),
]
TIME_WINDOW_MARKER_REQUIRED_HITS = 1
COURT_WINDOW_MARKERS = [
    (495, 852),
    (573, 852),
]
COURT_WINDOW_MARKER_REQUIRED_HITS = 1
USAGE_WINDOW_MARKERS = [
    (494, 821),
    (573, 819),
]
USAGE_WINDOW_MARKER_REQUIRED_HITS = 1
USAGE_TYPE_SELECTED_MARKERS = [
    (529, 545),
    (559, 568),
]
PEOPLE_WINDOW_MARKERS = [
    (494, 839),
    (579, 830),
]
PEOPLE_WINDOW_MARKER_REQUIRED_HITS = 1


def ensure_admin():
    """Relaunch as admin so key/mouse input and w32tm sync are more reliable."""
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        is_admin = False

    if not is_admin:
        ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            sys.executable,
            " ".join(sys.argv),
            None,
            1,
        )
        sys.exit()

def settings_path(filename):
    return os.path.join(BASE_DIR, filename)

def log_click_event(x, y, click_type, action=None):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    action_text = f" action={action}" if action else ""
    print(f"[CLICK] {timestamp} type={click_type} coord=({x},{y}){action_text}")


def logged_click(*args, double=False, action=None):
    if not args:
        x, y = pyautogui.position()
    elif len(args) == 1:
        x, y = args[0]
    else:
        x, y = args[:2]

    click_type = "double" if double else "single"
    log_click_event(x, y, click_type, action=action)

    if double:
        return pyautogui.doubleClick(x, y)
    return pyautogui.click(x, y)


def logged_date_click(date_text, x, y, reservation_id=None):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    reservation = f" reservation={reservation_id}" if reservation_id is not None else ""
    print(f"[DATE-CLICK] {timestamp}{reservation} date={date_text} coord=({x},{y})")
    return logged_click(x, y)


# PyAutoGUI's default pause is 0.1 seconds after every call. Explicitly
# control timing through the application's delay variables instead.
pyautogui.PAUSE = 0.01
pyautogui.MINIMUM_DURATION = 0

# ============================
# OS 클릭 (저수준 클릭)
# ============================
def os_click(x, y):
    log_click_event(x, y, "single")
    ctypes.windll.user32.SetCursorPos(x, y)
    ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)  # left down
    time.sleep(0.01)
    ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)  # left up


# ============================
# ★ 초고속 픽셀 읽기 엔진 ★
# ============================
def fast_pixel(x, y):
    hdc = ctypes.windll.user32.GetDC(0)
    color = ctypes.windll.gdi32.GetPixel(hdc, x, y)
    ctypes.windll.user32.ReleaseDC(0, hdc)
    r = color & 0xff
    g = (color >> 8) & 0xff
    b = (color >> 16) & 0xff
    return r, g, b

# ============================
# ★ 강화된 픽셀 읽기 엔진 (안정화 버전)
# ============================
def fast_pixel_strong(x, y):
    r_total = g_total = b_total = 0
    for _ in range(2):  # 2회 샘플링(속도 우선)
        r, g, b = fast_pixel(x, y)
        r_total += r
        g_total += g
        b_total += b
        # 샘플 간 sleep 제거: 감지 지연을 줄인다.

    return r_total // 2, g_total // 2, b_total // 2


def rgb_to_hsv_deg(r, g, b):
    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    return (h * 360.0, s, v)


def hsv_close(hsv, target_hsv, h_tol=16.0, s_tol=0.28, v_tol=0.28):
    h, s, v = hsv
    th, ts, tv = target_hsv
    dh = abs(h - th)
    hue_diff = min(dh, 360.0 - dh)
    return (hue_diff <= h_tol and abs(s - ts) <= s_tol and abs(v - tv) <= v_tol)


import pyperclip

def activate_kakao():
    hwnd = ctypes.windll.user32.FindWindowW(None, "카카오톡")
    if hwnd == 0:
        print("❌ 카카오톡 창을 찾을 수 없습니다.")
        return False

    ctypes.windll.user32.SetForegroundWindow(hwnd)
    time.sleep(0.3)
    return True

def send_kakao_message(text):
    if not kakao_notify_var.get():
        return

    if not activate_kakao():
        return

    # 채팅방 이미지 탐색
    target = pyautogui.locateOnScreen(
        r"C:\Users\Desktop\AUTO\kakao\minyonggi.png",
        confidence=0.8
    )

    if target is None:
        print("❌ 화면에서 '민용기' 채팅방을 찾지 못했습니다.")
        return

    center_pos = pyautogui.center(target)

    # 채팅방 열기
    logged_click(center_pos, double=True)
    time.sleep(0.4)

    # ★ 메시지 입력창 자동 포커스됨

    # ★★★ 줄바꿈은 Shift+Enter 로 처리 ★★★
    lines = text.split("\n")
    for line in lines:
        pyautogui.write(line, interval=0.01)
        pyautogui.hotkey("shift", "enter")  # ← 줄바꿈

    time.sleep(0.2)

    pyautogui.press("enter")  # 최종 전송
    time.sleep(0.2)


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

def instant_move(x, y):
    ctypes.windll.user32.SetCursorPos(x, y)

def get_hwnd_by_click(x, y):
    instant_move(x, y)
    logged_click()
    pt = POINT(x, y)
    hwnd = ctypes.windll.user32.WindowFromPoint(pt)
    ctypes.windll.user32.SetForegroundWindow(hwnd)
    return hwnd

def get_browser_hwnd_by_click():
    x, y = 807, 248   # 브라우저 탭/타이틀바 좌표
    instant_move(x, y)
    logged_click()
    pt = POINT(x, y)
    hwnd = ctypes.windll.user32.WindowFromPoint(pt)
    ctypes.windll.user32.SetForegroundWindow(hwnd)
    return hwnd

def get_browser_hwnd():
    return ctypes.windll.user32.FindWindowW(None, "광명도시공사")

def focus_reservation_window(allow_click_fallback=True):
    """Bring the reservation browser window to foreground before automation."""
    hwnd = get_browser_hwnd()
    if hwnd:
        ctypes.windll.user32.SetForegroundWindow(hwnd)
        time.sleep(0.05)
        return True

    if not allow_click_fallback:
        print("[FOCUS-FAIL] 예약 브라우저를 찾지 못했습니다 - 좌표 클릭 생략")
        return False

    # Fallback: use known browser title/tab coordinates to recover focus.
    try:
        get_browser_hwnd_by_click()
        time.sleep(0.05)
        return True
    except Exception:
        return False


def send_refresh_f5():
    """Use the proven refresh order: focus click -> short wait -> F5."""
    try:
        if not safe_sleep(0):
            return False
        logged_click(REFRESH_FOCUS_X, REFRESH_FOCUS_Y, action="새로고침")
        if not safe_sleep(REFRESH_PRE_F5_DELAY_SEC):
            return False
        pyautogui.press("f5")
        return True
    except Exception:
        pass

    try:
        keyboard.send("f5")
        return True
    except Exception:
        pass

    try:
        keyboard.press_and_release("f5")
        return True
    except Exception:
        return False


def enforce_browser_zoom_100():
    """Normalize browser zoom to 100% so fixed coordinates remain valid."""
    try:
        pyautogui.hotkey("ctrl", "0")
        return True
    except Exception:
        return False


def warmup_browser_interaction():
    """Stabilize first input frame before reservation steps."""
    try:
        logged_click(REFRESH_FOCUS_X, REFRESH_FOCUS_Y)
    except Exception:
        return False
    return safe_sleep(RECOVERY_WARMUP_DELAY_SEC)


def auto_recover_context(reason="unknown"):
    """Recover focus/zoom/input readiness with bounded retries."""
    if not AUTO_RECOVERY_ENABLED:
        return False

    for _ in range(RECOVERY_RETRY_LIMIT):
        focused = focus_reservation_window()
        if focused:
            enforce_browser_zoom_100()
            warmup_browser_interaction()
            # Re-check focus after warmup click.
            if focus_reservation_window():
                return True
        if not safe_sleep(0.03):
            return False

    print(f"[RECOVERY-FAIL] 환경 자동 보정 실패 reason={reason}")
    return False


def run_startup_strong_precheck(warmup_click=True):
    """One-time strong precheck before list execution starts."""
    if not STARTUP_STRONG_PRECHECK_ENABLED:
        return True

    if focus_reservation_window():
        enforce_browser_zoom_100()
        if warmup_click and not warmup_browser_interaction():
            return False
        return True

    return auto_recover_context(reason="startup_precheck")


def run_reservation_light_check():
    """Per-reservation lightweight environment check."""
    if not RESERVATION_LIGHT_CHECK_ENABLED:
        return True

    if focus_reservation_window(allow_click_fallback=False):
        return True

    return False


def sync_pc_time():
    """Match 카토자동화.py sync behavior."""
    try:
        rc = os.system("w32tm /resync")
        return rc == 0
    except Exception:
        return False

# ============================
# F2 메시지 방식
# ============================
def press_f2(hwnd):
    WM_KEYDOWN = 0x0100
    WM_KEYUP = 0x0101
    VK_F2 = 0x71
    ctypes.windll.user32.PostMessageW(hwnd, WM_KEYDOWN, VK_F2, 0)
    time.sleep(0.05)
    ctypes.windll.user32.PostMessageW(hwnd, WM_KEYUP, VK_F2, 0)

def press_f2_scancode():
    KEYEVENTF_SCANCODE = 0x0008
    KEYEVENTF_KEYUP = 0x0002
    SCAN_F2 = 0x3C
    ctypes.windll.user32.keybd_event(0, SCAN_F2, KEYEVENTF_SCANCODE, 0)
    ctypes.windll.user32.keybd_event(0, SCAN_F2, KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP, 0)

def send_f2():
    keyboard.send("f2")

# ============================
# 긴급정지 플래그
# ============================
emergency_stop = False
running = False
ignore_esc_until = 0.0
esc_pressed_at = None
esc_stop_triggered = False
ESC_HOLD_THRESHOLD_SEC = 0.5
pause_requested = False

# ============================
# 딜레이 변수 (UI에서 실제로 초기화)
# ============================
click_delay_var = None
press_delay_var = None
page_delay_var = None
pay_delay_var = None
calendar_delay_var = None
court_delay_var = None

# ============================
# 안전 래퍼 함수
# ============================
def check_esc_hold_runtime():
    """실행 중과 대기 중에 같은 ESC 짧게 정지/0.5초 취소 상태를 사용한다."""
    global esc_pressed_at, esc_stop_triggered

    if time.time() < ignore_esc_until:
        esc_pressed_at = None
        esc_stop_triggered = False
        return emergency_stop

    now = time.monotonic()
    pressed = keyboard.is_pressed("esc")
    if pressed and esc_pressed_at is None:
        esc_pressed_at = now
        esc_stop_triggered = False

    if esc_pressed_at is not None:
        held_sec = now - esc_pressed_at
        if not esc_stop_triggered and held_sec >= ESC_HOLD_THRESHOLD_SEC:
            esc_stop_triggered = True
            stop_all_automation("⛔ ESC 0.5초 이상 - 전체 자동 실행 취소")
        elif not pressed and not esc_stop_triggered:
            toggle_pause_resume()

    if not pressed:
        esc_pressed_at = None
        esc_stop_triggered = False
    return emergency_stop


def safe_sleep(sec):
    global emergency_stop, pause_requested
    end_time = time.monotonic() + sec
    while True:
        if check_esc_hold_runtime() or emergency_stop:
            return False

        if pause_requested:
            paused_at = time.monotonic()
            while pause_requested and not emergency_stop:
                if check_esc_hold_runtime():
                    return False
                root.update_idletasks()
                root.update()
                time.sleep(SAFE_SLEEP_TICK_SEC)
            end_time += time.monotonic() - paused_at

        if emergency_stop:
            return False

        root.update_idletasks()
        root.update()
        if pause_requested:
            continue
        if emergency_stop:
            return False
        remaining = end_time - time.monotonic()
        if remaining <= 0:
            return True
        time.sleep(min(SAFE_SLEEP_TICK_SEC, remaining))

def safe_click(x, y, before_click=None):
    if not safe_sleep(0):
        return False
    if before_click is not None and not before_click():
        print(f"[CLICK-SKIP] 클릭 직전 감지 실패 coord=({x},{y})")
        return False
    logged_click(x, y)
    return safe_sleep(click_delay_var.get())

def is_reservation_available(res):
    t = res["time"]
    candidates = [time_positions.get(t), short_time_positions.get(t)]
    for pos in candidates:
        if not pos:
            continue
        tx, ty = pos
        r, g, b = fast_pixel_strong(tx, ty)
        if color_close(r, g, b, TARGET_COLOR, tol=15):
            return True
    return False

def safe_press(key):
    if not safe_sleep(0):
        return False
    pyautogui.press(key)
    return safe_sleep(press_delay_var.get())

def press_many(key, count):
    for _ in range(count):
        if emergency_stop:
            return False
        if not safe_press(key):
            return False
        if not safe_sleep(page_delay_var.get()):
            return False
    return True

def close_popup_with_esc(method="keyboard"):
    """Close popups using ESC without triggering the emergency monitor."""
    global ignore_esc_until
    if not safe_sleep(0):
        return False
    ignore_esc_until = time.time() + 0.8
    for count in range(1, 3):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        print(f"[KEY] {timestamp} key=esc count={count}/2 method={method}")
        if method == "pyautogui":
            pyautogui.press("esc")
        else:
            keyboard.send("esc")
        time.sleep(0.1)
    return True

def cancel_time_selection_with_fallback():
    """Cancel the time window with ESC and verify it closed before continuing."""
    for attempt in range(TIME_WINDOW_CANCEL_MAX_ATTEMPTS):
        if not close_popup_with_esc():
            return False
        if wait_for_time_window_close(timeout=TIME_WINDOW_CLOSE_TIMEOUT_SEC):
            return True
        if attempt < TIME_WINDOW_CANCEL_MAX_ATTEMPTS - 1:
            print("[TIME-CANCEL] 시간창 닫힘 미확인 - ESC 취소 재시도")

    print("[TIME-CANCEL-FAIL] 시간창이 닫히지 않아 마우스 입력 없이 예약 실행을 중단합니다")
    return False

TIME_WINDOW_CLOSE_BUTTON_X = 681
TIME_WINDOW_CLOSE_BUTTON_Y = 207
TIME_WINDOW_CLOSE_CLICK_MAX_ATTEMPTS = 2
TIME_WINDOW_CANCEL_COORDINATES = ((410, 810), (410, 760))


def close_time_window_by_click_and_continue():
    """Click the time window close button, verify it closed, then allow the next reservation."""
    for attempt in range(1, TIME_WINDOW_CLOSE_CLICK_MAX_ATTEMPTS + 1):
        if not safe_click(TIME_WINDOW_CLOSE_BUTTON_X, TIME_WINDOW_CLOSE_BUTTON_Y):
            return False
        if wait_for_time_window_close(timeout=TIME_WINDOW_CLOSE_TIMEOUT_SEC):
            print(f"[TIME-CLOSE] 시간창 닫기 클릭 성공 attempt={attempt} → 다음 예약")
            return True
        print(
            f"[TIME-CLOSE] 시간창 닫힘 미확인 attempt={attempt} "
            f"markers=[{get_time_marker_debug()}] - 닫기 재클릭"
        )

    print("[TIME-CLOSE-FAIL] 시간창이 닫히지 않아 다음 예약 클릭 없이 중단합니다")
    return False


def cancel_time_window_by_coordinates_and_continue():
    """Try the primary and backup cancel coordinates, verifying the window closes."""
    for attempt, (x, y) in enumerate(TIME_WINDOW_CANCEL_COORDINATES, start=1):
        if not safe_click(x, y):
            return False
        if wait_for_time_window_close(timeout=TIME_WINDOW_CLOSE_TIMEOUT_SEC):
            print(
                f"[TIME-CANCEL-COORD] 취소 좌표 클릭 성공 attempt={attempt} "
                f"coord=({x},{y}) → 다음 예약"
            )
            return True
        print(
            f"[TIME-CANCEL-COORD] 시간창 닫힘 미확인 attempt={attempt} "
            f"coord=({x},{y}) markers=[{get_time_marker_debug()}]"
        )

    print("[TIME-CANCEL-COORD-FAIL] 취소 좌표 모두 실패 - 다음 예약 클릭 없이 중단합니다")
    return False


def cancel_time_window_and_continue():
    """Send ESC twice, verify the time window closed, then allow the next reservation."""
    for attempt, method in enumerate(("keyboard", "pyautogui", "pyautogui"), start=1):
        if not close_popup_with_esc(method=method):
            return False
        if wait_for_time_window_close(timeout=TIME_WINDOW_CLOSE_TIMEOUT_SEC):
            print(f"[TIME-CANCEL] 시간창 닫힘 확인 attempt={attempt} → 처음부터시작")
            return True
        print(
            f"[TIME-CANCEL] 시간창 닫힘 미확인 attempt={attempt} "
            f"markers=[{get_time_marker_debug()}] - ESC 재시도"
        )

    print("[TIME-CANCEL-FAIL] ESC로 시간창이 닫히지 않아 다음 예약 클릭 없이 중단합니다")
    return False

def reset_after_reservation():
    """결제 완료 후 다음 예약이 달력 화면에서 시작되도록 모달을 닫는다."""
    if emergency_stop:
        return False
    if not cancel_time_selection_with_fallback():
        return False
    return safe_sleep(NEXT_RESERVATION_TRANSITION_DELAY_SEC)


def wait_for_next_reservation_transition():
    """Allow the calendar to settle after a failed reservation closes its time window."""
    print(
        "[NEXT-RESERVATION] 시간창 닫힘 후 달력 전환 대기 "
        f"{NEXT_RESERVATION_TRANSITION_DELAY_SEC:.2f}초"
    )
    return safe_sleep(NEXT_RESERVATION_TRANSITION_DELAY_SEC)


# ============================
# 시간 / 코트 좌표
# ============================
time_positions = {
    "06:00": (309, 471),
    "08:00": (483, 466),
    "10:00": (651, 472),
    "12:00": (316, 568),
    "14:00": (483, 565),
    "16:00": (655, 568),
    "18:00": (313, 672),
    "20:00": (485, 668),
}

# 단축운영 시간표 좌표 (기본 시간표 감지 실패 시 백업으로 사용)
short_time_positions = {
    "08:00": (270, 543),
    "10:00": (440, 543),
    "12:00": (604, 541),
    "14:00": (263, 642),
    "16:00": (436, 641),
}

court_positions = {
    1: (279, 514), 2: (384, 515), 3: (484, 517), 4: (587, 513), 5: (692, 515),
    6: (282, 613), 7: (383, 614), 8: (485, 616), 9: (589, 620), 10: (689, 620),
    11: (282, 713), 12: (380, 715), 13: (484, 714),
}

# 예약 가능 칸 기준색: 딥 블루 (#3E4A8C)
TARGET_COLOR = (62, 74, 140)
# 선택 완료 기준색: 진한 마젠타 (#CF0A67)
SELECTED_COLOR = (207, 10, 103)

# 화면 안티앨리어싱/렌더링 차이를 흡수하기 위한 보조 기준색
WINDOW_OPEN_COLOR = (56, 89, 153)
TIME_WINDOW_OPEN_COLOR = (56, 90, 155)
TIME_AVAILABLE_COLORS = [TARGET_COLOR, (56, 89, 153)]
TIME_AVAILABLE_HSV_COLORS = [rgb_to_hsv_deg(*c) for c in TIME_AVAILABLE_COLORS]
WINDOW_OPEN_HSV = rgb_to_hsv_deg(*WINDOW_OPEN_COLOR)
SELECTED_HSV = rgb_to_hsv_deg(*SELECTED_COLOR)

# ============================
# 코트 감지 (속도+안정성 절충안: 중앙 1픽셀만 fast_pixel_strong)
# ============================
def color_match_area(
    x,
    y,
    targets,
    tol=12,
    radius=1,
    min_hits=3,
    use_strong=True,
    hsv_targets=None,
    h_tol=16.0,
    s_tol=0.28,
    v_tol=0.28,
):
    """(x,y) 주변 영역에서 목표색 다중 샘플 매칭."""
    if isinstance(targets, tuple):
        targets = [targets]

    if hsv_targets is None:
        hsv_targets = []
    elif isinstance(hsv_targets, tuple):
        hsv_targets = [hsv_targets]

    hits = 0
    total = 0
    reader = fast_pixel_strong if use_strong else fast_pixel

    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            total += 1
            r, g, b = reader(x + dx, y + dy)
            matched = False

            for target in targets:
                if color_close(r, g, b, target, tol=tol):
                    hits += 1
                    matched = True
                    break

            if (not matched) and hsv_targets:
                hsv = rgb_to_hsv_deg(r, g, b)
                for target_hsv in hsv_targets:
                    if hsv_close(hsv, target_hsv, h_tol=h_tol, s_tol=s_tol, v_tol=v_tol):
                        hits += 1
                        break

    return hits >= min_hits, hits, total


def temporal_color_confirm(sample_count=2, required=1, interval=0.0, **match_kwargs):
    """연속 프레임 중 required회 이상 매칭되면 성공."""
    matched, _, _, _ = temporal_color_confirm_details(
        sample_count=sample_count,
        required=required,
        interval=interval,
        **match_kwargs,
    )
    return matched


def temporal_color_confirm_details(sample_count=2, required=1, interval=0.0, **match_kwargs):
    """Return the match result and the sample that satisfied the color check."""
    success = 0
    last_hits = 0
    last_total = 0
    for sample in range(1, sample_count + 1):
        if emergency_stop:
            return False, last_hits, last_total, sample
        matched, hits, total = color_match_area(**match_kwargs)
        last_hits = hits
        last_total = total
        if matched:
            success += 1
            if success >= required:
                return True, hits, total, sample
        if interval > 0:
            if not safe_sleep(interval):
                return False, last_hits, last_total, sample
    return False, last_hits, last_total, sample_count


def detect_court_available(court_num):
    x, y = court_positions[court_num]
    matched, hits, total, sample = temporal_color_confirm_details(
        sample_count=2,
        required=1,
        interval=0.0,
        x=x,
        y=y,
        targets=TIME_AVAILABLE_COLORS,
        tol=16,
        radius=0,
        min_hits=1,
        use_strong=False,
        hsv_targets=TIME_AVAILABLE_HSV_COLORS,
        h_tol=20.0,
        s_tol=0.35,
        v_tol=0.35,
    )
    r, g, b = fast_pixel(x, y)
    log_color_detection(
        "court-available",
        matched,
        coords=(x, y),
        rgb=(r, g, b),
        target=TIME_AVAILABLE_COLORS,
        detail=f"court={court_num} hits={hits}/{total} sample={sample}/2",
    )
    return matched

def find_available_court(start_court):
    # 1) start_court 이후 먼저 검사
    for c in range(start_court, 14):
        if detect_court_available(c):
            return c

    # 2) 그 다음 1~start_court-1 검사
    for c in range(1, start_court):
        if detect_court_available(c):
            return c

    return None

# ============================
# 달력 좌표
# ============================
calendar_bounds = {
    "5week": {"lt": (55, 225), "rb": (915, 775)},
    "6week": {"lt": (55, 113), "rb": (915, 775)},
}

def get_date_position(year, month, day):
    mode = calendar_mode_var.get()
    bounds = calendar_bounds[mode]
    lt_x, lt_y = bounds["lt"]
    rb_x, rb_y = bounds["rb"]
    width = rb_x - lt_x
    height = rb_y - lt_y
    week_count = 5 if mode == "5week" else 6
    cell_w = width / 7
    cell_h = height / week_count
    first_weekday = datetime.date(year, month, 1).weekday()
    first_col = (first_weekday + 1) % 7
    weekday = datetime.date(year, month, day).weekday()
    col = (weekday + 1) % 7
    row = (day + first_col - 1) // 7
    click_x = lt_x + col * cell_w + cell_w / 2
    click_y = lt_y + row * cell_h + cell_h / 2
    return int(click_x), int(click_y)

# ============================
# F2 실행시간 관련
# ============================
TIME_FILE = settings_path("time_settings.txt")
UI_STATE_FILE = settings_path("ui_state_settings.json")
CALIBRATION_FILE = settings_path("calibration_settings.json")
DEFAULT_SYNC_OFFSET_MIN = -10
DEFAULT_REFRESH_STOP_OFFSET_MIN = -10


def _clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def _to_float(value, fallback):
    try:
        return float(value)
    except Exception:
        return float(fallback)


def _sanitize_timeout(value, baseline):
    return round(_clamp(_to_float(value, baseline), 0.35, 2.20), 2)


def _stage_baselines():
    return {
        "time": {
            "open_a": 0.35,
            "open_b": 0.50,
        },
        "court": {
            "open": 1.0,
            "close": 1.0,
        },
        "usage": {
            "open": 1.0,
            "close": 1.0,
        },
        "people": {
            "open": 1.0,
            "close": 1.0,
        },
        "payment": {
            "open": 1.0,
            "close": 1.0,
        },
    }


def default_calibration_state():
    base = _stage_baselines()
    return {
        "version": 1,
        "baseline": base,
        "adaptive": {
            "time": dict(base["time"]),
            "court": dict(base["court"]),
            "usage": dict(base["usage"]),
            "people": dict(base["people"]),
            "payment": dict(base["payment"]),
        },
        "history": {
            "time": [],
            "court": [],
            "usage": [],
            "people": [],
            "payment": [],
        },
        "fail_streak": {
            "time": 0,
            "court": 0,
            "usage": 0,
            "people": 0,
            "payment": 0,
        },
        "last_increase_prev": {},
    }


calibration_state = default_calibration_state()


def apply_calibration_runtime():
    global TIME_WINDOW_OPEN_TIMEOUT_STEPS_SEC
    global COURT_WINDOW_OPEN_TIMEOUT_SEC, COURT_WINDOW_CLOSE_TIMEOUT_SEC
    global USAGE_WINDOW_OPEN_TIMEOUT_SEC, USAGE_WINDOW_CLOSE_TIMEOUT_SEC
    global PEOPLE_WINDOW_OPEN_TIMEOUT_SEC, PEOPLE_NEXT_STEP_MARKER_TIMEOUT_SEC
    global PAYMENT_WINDOW_OPEN_TIMEOUT_SEC, PAYMENT_WINDOW_CLOSE_TIMEOUT_SEC

    adaptive = calibration_state.get("adaptive", {})
    baseline = calibration_state.get("baseline", _stage_baselines())

    t_base = baseline.get("time", {"open_a": 0.35, "open_b": 0.50})
    t_adapt = adaptive.get("time", dict(t_base))
    ta = _sanitize_timeout(t_adapt.get("open_a", t_base.get("open_a", 0.35)), t_base.get("open_a", 0.35))
    tb = _sanitize_timeout(t_adapt.get("open_b", t_base.get("open_b", 0.50)), t_base.get("open_b", 0.50))
    if tb < ta:
        tb = ta
    adaptive["time"] = {"open_a": ta, "open_b": tb}
    TIME_WINDOW_OPEN_TIMEOUT_STEPS_SEC = [ta, tb]

    for stage_name, open_global, close_global in (
        ("court", "COURT_WINDOW_OPEN_TIMEOUT_SEC", "COURT_WINDOW_CLOSE_TIMEOUT_SEC"),
        ("usage", "USAGE_WINDOW_OPEN_TIMEOUT_SEC", "USAGE_WINDOW_CLOSE_TIMEOUT_SEC"),
        ("people", "PEOPLE_WINDOW_OPEN_TIMEOUT_SEC", "PEOPLE_NEXT_STEP_MARKER_TIMEOUT_SEC"),
        ("payment", "PAYMENT_WINDOW_OPEN_TIMEOUT_SEC", "PAYMENT_WINDOW_CLOSE_TIMEOUT_SEC"),
    ):
        s_base = baseline.get(stage_name, {})
        s_adapt = adaptive.get(stage_name, dict(s_base))
        o = _sanitize_timeout(s_adapt.get("open", s_base.get("open", 1.0)), s_base.get("open", 1.0))
        c = _sanitize_timeout(s_adapt.get("close", s_base.get("close", 1.0)), s_base.get("close", 1.0))
        adaptive[stage_name] = {"open": o, "close": c}
        globals()[open_global] = o
        globals()[close_global] = c


def save_calibration_state():
    try:
        with open(CALIBRATION_FILE, "w", encoding="utf-8") as f:
            json.dump(calibration_state, f, ensure_ascii=False)
    except Exception:
        pass


def load_calibration_state():
    global calibration_state
    state = default_calibration_state()
    if os.path.exists(CALIBRATION_FILE):
        try:
            with open(CALIBRATION_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                for key in ("baseline", "adaptive", "history", "fail_streak", "last_increase_prev"):
                    if isinstance(raw.get(key), dict):
                        state[key].update(raw[key])
        except Exception:
            state = default_calibration_state()

    for stage in ("time", "court", "usage", "people", "payment"):
        hist = state.get("history", {}).get(stage, [])
        if not isinstance(hist, list):
            hist = []
        state["history"][stage] = [bool(x) for x in hist][-30:]
        try:
            state["fail_streak"][stage] = int(state["fail_streak"].get(stage, 0))
        except Exception:
            state["fail_streak"][stage] = 0

    calibration_state = state
    apply_calibration_runtime()


def _update_stage_adaptive(stage):
    history = calibration_state["history"].get(stage, [])
    if len(history) < 5:
        return

    recent = history[-10:]
    fail_count = sum(1 for ok in recent if not ok)
    fail_rate = fail_count / len(recent)
    adaptive = calibration_state["adaptive"]
    baseline = calibration_state["baseline"]
    prev_map = calibration_state["last_increase_prev"]

    if stage == "time":
        a = adaptive["time"]
        b = baseline["time"]
        if fail_rate >= 0.40:
            prev_map[stage] = dict(a)
            a["open_a"] = round(_clamp(a["open_a"] + 0.03, 0.20, 0.90), 2)
            a["open_b"] = round(_clamp(a["open_b"] + 0.05, 0.25, 1.00), 2)
        elif fail_rate <= 0.10 and len(recent) >= 8:
            a["open_a"] = round(max(b["open_a"], a["open_a"] - 0.01), 2)
            a["open_b"] = round(max(b["open_b"], a["open_b"] - 0.02), 2)

        if calibration_state["fail_streak"].get(stage, 0) >= 4 and isinstance(prev_map.get(stage), dict):
            a.update(prev_map[stage])
            prev_map.pop(stage, None)
    else:
        a = adaptive[stage]
        b = baseline[stage]
        if fail_rate >= 0.40:
            prev_map[stage] = dict(a)
            a["open"] = round(_clamp(a["open"] + 0.08, 0.35, 2.20), 2)
            a["close"] = round(_clamp(a["close"] + 0.08, 0.35, 2.20), 2)
        elif fail_rate <= 0.10 and len(recent) >= 8:
            a["open"] = round(max(b["open"], a["open"] - 0.03), 2)
            a["close"] = round(max(b["close"], a["close"] - 0.03), 2)

        if calibration_state["fail_streak"].get(stage, 0) >= 4 and isinstance(prev_map.get(stage), dict):
            a.update(prev_map[stage])
            prev_map.pop(stage, None)


def record_stage_outcome(stage, ok):
    if stage not in ("time", "court", "usage", "people", "payment"):
        return

    hist = calibration_state["history"][stage]
    hist.append(bool(ok))
    calibration_state["history"][stage] = hist[-30:]
    if ok:
        calibration_state["fail_streak"][stage] = 0
    else:
        calibration_state["fail_streak"][stage] = calibration_state["fail_streak"].get(stage, 0) + 1

    _update_stage_adaptive(stage)
    apply_calibration_runtime()
    save_calibration_state()


def get_next_target_datetime():
    try:
        h = int(hour_var.get())
        m = int(min_var.get())
        s = int(sec_var.get())
    except:
        return None

    now = datetime.datetime.now()
    target_dt = now.replace(hour=h, minute=m, second=s, microsecond=0)
    if target_dt <= now:
        target_dt += datetime.timedelta(days=1)
    return target_dt


def get_sync_datetime():
    target_dt = get_next_target_datetime()
    if target_dt is None:
        return None

    try:
        offset_min = int(sync_offset_var.get())
    except:
        offset_min = DEFAULT_SYNC_OFFSET_MIN

    return target_dt + datetime.timedelta(minutes=offset_min)


def get_refresh_stop_datetime():
    target_dt = get_next_target_datetime()
    if target_dt is None:
        return None

    # 목표시각 10분 전에 마지막 새로고침을 실행하고 반복을 종료한다.
    return target_dt + datetime.timedelta(minutes=DEFAULT_REFRESH_STOP_OFFSET_MIN)

def auto_calculate_times():
    sync_dt = get_sync_datetime()
    if sync_dt is None:
        return

    sync_hour_var.set(f"{sync_dt.hour:02d}")
    sync_min_var.set(f"{sync_dt.minute:02d}")

def save_time_settings():
    with open(TIME_FILE, "w", encoding="utf-8") as f:
        f.write(f"{hour_var.get()},{min_var.get()},{sec_var.get()}")

def load_time_settings():
    if not os.path.exists(TIME_FILE):
        return
    with open(TIME_FILE, "r", encoding="utf-8") as f:
        raw = f.read().strip()
    if raw:
        h, m, s = raw.split(",")
        hour_var.set(h)
        min_var.set(m)
        sec_var.set(s)

# ============================
# 창 열림 감지 (공통 파란색, 초고속)
# ============================
def wait_for_window(x, y, timeout=TIME_WINDOW_OPEN_TIMEOUT_SEC):
    # 공통 창 열림 기준색: 중간 톤 네이비 블루 (#385999)
    start = time.time()
    stable_hits = 0
    while time.time() - start < timeout:
        if is_window_marker_open(x, y):
            stable_hits += 1
            if stable_hits >= WINDOW_OPEN_STABLE_HITS:
                return True
        else:
            stable_hits = 0
        if not safe_sleep(WINDOW_DETECT_POLL_INTERVAL_SEC):
            return False
    return False


def wait_for_window_close(x, y, timeout=TIME_WINDOW_OPEN_TIMEOUT_SEC, stable_hits_required=WINDOW_CLOSE_STABLE_HITS):
    """지정 좌표의 창 열림 마커가 연속으로 사라질 때까지 대기한다."""
    start = time.time()
    stable_hits = 0
    while time.time() - start < timeout:
        if not is_window_marker_open(x, y):
            stable_hits += 1
            if stable_hits >= stable_hits_required:
                return True
        else:
            stable_hits = 0
        if not safe_sleep(WINDOW_DETECT_POLL_INTERVAL_SEC):
            return False
    return False


def people_test_log(msg):
    if PEOPLE_STAGE_TEST_LOG_ENABLED:
        print(msg)


def is_window_marker_open(x, y, target_color=WINDOW_OPEN_COLOR):
    matched, _, _ = color_match_area(
        x,
        y,
        target_color,
        tol=18,
        radius=0,
        min_hits=1,
        use_strong=False,
        hsv_targets=[rgb_to_hsv_deg(*target_color)],
        h_tol=20.0,
        s_tol=0.35,
        v_tol=0.35,
    )
    return matched


def detect_payment_window_open(required_hits=PAYMENT_WINDOW_MARKER_REQUIRED_HITS):
    hits = 0
    for mx, my in PAYMENT_WINDOW_MARKERS:
        if is_window_marker_open(mx, my):
            hits += 1
            if hits >= required_hits:
                return True
    return False


def sample_time_window_markers(required_hits=TIME_WINDOW_MARKER_REQUIRED_HITS):
    """Return the open decision and the exact RGB samples used to make it."""
    hits = 0
    samples = []
    for mx, my in TIME_WINDOW_MARKERS:
        r, g, b = fast_pixel(mx, my)
        matched = color_close(r, g, b, TIME_WINDOW_OPEN_COLOR, tol=18)
        if not matched:
            matched = hsv_close(
                rgb_to_hsv_deg(r, g, b),
                rgb_to_hsv_deg(*TIME_WINDOW_OPEN_COLOR),
                h_tol=20.0,
                s_tol=0.35,
                v_tol=0.35,
            )
        samples.append((mx, my, (r, g, b), matched))
        if matched:
            hits += 1
            if hits >= required_hits:
                break
    return hits >= required_hits, samples


def format_time_window_samples(samples):
    return " | ".join(
        f"({mx},{my}):RGB={rgb} matched={matched}"
        for mx, my, rgb, matched in samples
    )


def detect_time_window_open(required_hits=TIME_WINDOW_MARKER_REQUIRED_HITS):
    matched, _ = sample_time_window_markers(required_hits)
    return matched


def detect_court_window_open(required_hits=COURT_WINDOW_MARKER_REQUIRED_HITS):
    hits = 0
    for mx, my in COURT_WINDOW_MARKERS:
        if is_window_marker_open(mx, my):
            hits += 1
            if hits >= required_hits:
                return True
    return False


def detect_usage_window_open(required_hits=USAGE_WINDOW_MARKER_REQUIRED_HITS):
    hits = 0
    for mx, my in USAGE_WINDOW_MARKERS:
        if is_window_marker_open(mx, my):
            hits += 1
            if hits >= required_hits:
                return True
    return False


def detect_people_window_open(required_hits=PEOPLE_WINDOW_MARKER_REQUIRED_HITS):
    hits = 0
    for mx, my in PEOPLE_WINDOW_MARKERS:
        if is_window_marker_open(mx, my):
            hits += 1
            if hits >= required_hits:
                return True
    return False


def get_payment_marker_debug():
    """결제창 다점 마커의 좌표/RGB/판정 상태를 문자열로 반환한다."""
    parts = []
    for mx, my in PAYMENT_WINDOW_MARKERS:
        r, g, b = fast_pixel(mx, my)
        open_flag = is_window_marker_open(mx, my)
        parts.append(f"({mx},{my}):RGB=({r},{g},{b}) open={open_flag}")
    return " | ".join(parts)


def get_time_marker_debug():
    """시간창 다점 마커의 좌표/RGB/판정 상태를 문자열로 반환한다."""
    parts = []
    for mx, my in TIME_WINDOW_MARKERS:
        r, g, b = fast_pixel(mx, my)
        open_flag = is_window_marker_open(mx, my)
        parts.append(f"({mx},{my}):RGB=({r},{g},{b}) open={open_flag}")
    return " | ".join(parts)


def get_court_marker_debug():
    """코트창 다점 마커의 좌표/RGB/판정 상태를 문자열로 반환한다."""
    parts = []
    for mx, my in COURT_WINDOW_MARKERS:
        r, g, b = fast_pixel(mx, my)
        open_flag = is_window_marker_open(mx, my)
        parts.append(f"({mx},{my}):RGB=({r},{g},{b}) open={open_flag}")
    return " | ".join(parts)


def get_usage_marker_debug():
    """이용유형창 다점 마커의 좌표/RGB/판정 상태를 문자열로 반환한다."""
    parts = []
    for mx, my in USAGE_WINDOW_MARKERS:
        r, g, b = fast_pixel(mx, my)
        open_flag = is_window_marker_open(mx, my)
        parts.append(f"({mx},{my}):RGB=({r},{g},{b}) open={open_flag}")
    return " | ".join(parts)


def get_people_marker_debug():
    """인원창 다점 마커의 좌표/RGB/판정 상태를 문자열로 반환한다."""
    parts = []
    for mx, my in PEOPLE_WINDOW_MARKERS:
        r, g, b = fast_pixel(mx, my)
        open_flag = is_window_marker_open(mx, my)
        parts.append(f"({mx},{my}):RGB=({r},{g},{b}) open={open_flag}")
    return " | ".join(parts)


def log_color_detection(stage, matched, coords=None, rgb=None, target=None, detail=""):
    """Print one concise color-detection result with its sampled values."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    coord_text = f"coord={coords}" if coords is not None else ""
    rgb_text = f"RGB={rgb}" if rgb is not None else ""
    target_text = f"target={target}" if target is not None else ""
    detail_text = f" {detail}" if detail else ""
    fields = " ".join(value for value in (coord_text, rgb_text, target_text) if value)
    print(
        f"[COLOR] {timestamp} stage={stage} result={'PASS' if matched else 'FAIL'} "
        f"{fields}{detail_text}"
    )


def wait_for_people_window_open(timeout=PEOPLE_WINDOW_OPEN_TIMEOUT_SEC):
    start = time.time()
    stable_hits = 0
    while time.time() - start < timeout:
        if detect_people_window_open():
            stable_hits += 1
            if stable_hits >= WINDOW_OPEN_STABLE_HITS:
                log_color_detection(
                    "people-window", True, detail=f"markers=[{get_people_marker_debug()}]"
                )
                return True
        else:
            stable_hits = 0

        if not safe_sleep(WINDOW_DETECT_POLL_INTERVAL_SEC):
            return False
    log_color_detection(
        "people-window", False, detail=f"markers=[{get_people_marker_debug()}]"
    )
    return False


def wait_for_time_window_open(timeout=TIME_WINDOW_OPEN_TIMEOUT_SEC):
    start = time.time()
    stable_hits = 0
    last_samples = []
    while time.time() - start < timeout:
        matched, last_samples = sample_time_window_markers()
        if matched:
            stable_hits += 1
            if stable_hits >= WINDOW_OPEN_STABLE_HITS:
                return True, last_samples
        else:
            stable_hits = 0

        if not safe_sleep(WINDOW_DETECT_POLL_INTERVAL_SEC):
            return False, last_samples
    return False, last_samples


def wait_for_time_window_ready(max_attempts=TIME_WINDOW_OPEN_MAX_RETRIES):
    """시간창 마커와 밝기 보조 감지를 기존 재시도 설정으로 확인한다."""
    for attempt in range(max_attempts):
        if emergency_stop:
            return False
        if attempt < len(TIME_WINDOW_OPEN_TIMEOUT_STEPS_SEC):
            attempt_timeout = TIME_WINDOW_OPEN_TIMEOUT_STEPS_SEC[attempt]
        else:
            attempt_timeout = TIME_WINDOW_OPEN_TIMEOUT_SEC

        attempt_started = time.monotonic()
        marker_open, decision_samples = wait_for_time_window_open(timeout=attempt_timeout)
        if emergency_stop:
            return False
        bright_open = is_time_window_open() if TIME_WINDOW_USE_BRIGHTNESS_FALLBACK else False
        elapsed = time.monotonic() - attempt_started
        post_check_markers = get_time_marker_debug()
        log_color_detection(
            "time-window",
            marker_open or bright_open,
            target=TIME_WINDOW_OPEN_COLOR,
            detail=(
                f"attempt={attempt + 1}/{max_attempts} elapsed={elapsed:.3f}s "
                f"marker_open={marker_open} brightness_open={bright_open} "
                f"decision_markers=[{format_time_window_samples(decision_samples)}] "
                f"post_check_markers=[{post_check_markers}]"
            ),
        )
        if marker_open or bright_open:
            return True
        if not safe_sleep(TIME_WINDOW_OPEN_RETRY_GAP_SEC):
            return False
    return False


def wait_for_court_window_open(timeout=COURT_WINDOW_OPEN_TIMEOUT_SEC):
    start = time.time()
    stable_hits = 0
    while time.time() - start < timeout:
        if detect_court_window_open():
            stable_hits += 1
            if stable_hits >= WINDOW_OPEN_STABLE_HITS:
                log_color_detection(
                    "court-window", True, detail=f"markers=[{get_court_marker_debug()}]"
                )
                return True
        else:
            stable_hits = 0

        if not safe_sleep(WINDOW_DETECT_POLL_INTERVAL_SEC):
            return False
    log_color_detection(
        "court-window", False, detail=f"markers=[{get_court_marker_debug()}]"
    )
    return False


def wait_for_usage_window_open(timeout=USAGE_WINDOW_OPEN_TIMEOUT_SEC):
    start = time.time()
    stable_hits = 0
    while time.time() - start < timeout:
        if detect_usage_window_open():
            stable_hits += 1
            if stable_hits >= WINDOW_OPEN_STABLE_HITS:
                log_color_detection(
                    "usage-window", True, detail=f"markers=[{get_usage_marker_debug()}]"
                )
                return True
        else:
            stable_hits = 0

        if not safe_sleep(WINDOW_DETECT_POLL_INTERVAL_SEC):
            return False
    log_color_detection(
        "usage-window", False, detail=f"markers=[{get_usage_marker_debug()}]"
    )
    return False


def wait_for_time_window_close(timeout=TIME_WINDOW_CLOSE_TIMEOUT_SEC):
    start = time.time()
    stable_hits = 0
    while time.time() - start < timeout:
        if not detect_time_window_open():
            stable_hits += 1
            if stable_hits >= WINDOW_CLOSE_STABLE_HITS:
                log_color_detection(
                    "time-window-close", True, detail=f"markers=[{get_time_marker_debug()}]"
                )
                return True
        else:
            stable_hits = 0

        if not safe_sleep(WINDOW_DETECT_POLL_INTERVAL_SEC):
            return False
    log_color_detection(
        "time-window-close", False, detail=f"markers=[{get_time_marker_debug()}]"
    )
    return False


def wait_for_court_window_close(timeout=COURT_WINDOW_CLOSE_TIMEOUT_SEC):
    start = time.time()
    stable_hits = 0
    while time.time() - start < timeout:
        if not detect_court_window_open():
            stable_hits += 1
            if stable_hits >= WINDOW_CLOSE_STABLE_HITS:
                log_color_detection(
                    "court-window-close", True, detail=f"markers=[{get_court_marker_debug()}]"
                )
                return True
        else:
            stable_hits = 0

        if not safe_sleep(WINDOW_DETECT_POLL_INTERVAL_SEC):
            return False
    log_color_detection(
        "court-window-close", False, detail=f"markers=[{get_court_marker_debug()}]"
    )
    return False


def wait_for_usage_window_close(timeout=USAGE_WINDOW_CLOSE_TIMEOUT_SEC):
    start = time.time()
    stable_hits = 0
    while time.time() - start < timeout:
        if not detect_usage_window_open():
            stable_hits += 1
            if stable_hits >= WINDOW_CLOSE_STABLE_HITS:
                log_color_detection(
                    "usage-window-close", True, detail=f"markers=[{get_usage_marker_debug()}]"
                )
                return True
        else:
            stable_hits = 0

        if not safe_sleep(WINDOW_DETECT_POLL_INTERVAL_SEC):
            return False
    log_color_detection(
        "usage-window-close", False, detail=f"markers=[{get_usage_marker_debug()}]"
    )
    return False


def wait_for_people_window_close(timeout=PEOPLE_NEXT_STEP_MARKER_TIMEOUT_SEC):
    start = time.time()
    stable_hits = 0
    while time.time() - start < timeout:
        if not detect_people_window_open():
            stable_hits += 1
            if stable_hits >= WINDOW_CLOSE_STABLE_HITS:
                log_color_detection(
                    "people-window-close", True, detail=f"markers=[{get_people_marker_debug()}]"
                )
                return True
        else:
            stable_hits = 0

        if not safe_sleep(WINDOW_DETECT_POLL_INTERVAL_SEC):
            return False
    log_color_detection(
        "people-window-close", False, detail=f"markers=[{get_people_marker_debug()}]"
    )
    return False


def wait_for_payment_window(timeout=PAYMENT_WINDOW_OPEN_TIMEOUT_SEC):
    """결제창 전용 판정: 결제창 마커는 열리고, 인원창 마커는 닫혀야 한다."""
    start = time.monotonic()
    stable_hits = 0
    while time.monotonic() - start < timeout:
        payment_open = detect_payment_window_open()
        people_open = detect_people_window_open()

        if payment_open and (not people_open):
            stable_hits += 1
            if stable_hits >= 2:
                log_color_detection(
                    "payment-window",
                    True,
                    detail=(
                        f"payment_markers=[{get_payment_marker_debug()}] "
                        f"people_markers=[{get_people_marker_debug()}]"
                    ),
                )
                return True
        else:
            stable_hits = 0

        if not safe_sleep(WINDOW_DETECT_POLL_INTERVAL_SEC):
            log_color_detection(
                "payment-window",
                False,
                detail=(
                    f"reason=interrupted elapsed={time.monotonic() - start:.3f}s "
                    f"payment_markers=[{get_payment_marker_debug()}] "
                    f"people_markers=[{get_people_marker_debug()}]"
                ),
            )
            return False

    log_color_detection(
        "payment-window",
        False,
        detail=(
            f"reason=timeout elapsed={time.monotonic() - start:.3f}s "
            f"payment_markers=[{get_payment_marker_debug()}] "
            f"people_markers=[{get_people_marker_debug()}]"
        ),
    )
    return False


def wait_for_payment_window_close(timeout=PAYMENT_WINDOW_CLOSE_TIMEOUT_SEC):
    start = time.monotonic()
    stable_hits = 0
    while time.monotonic() - start < timeout:
        payment_open = detect_payment_window_open()
        if not payment_open:
            stable_hits += 1
            if stable_hits >= WINDOW_CLOSE_STABLE_HITS:
                log_color_detection(
                    "payment-window-close", True,
                    detail=f"markers=[{get_payment_marker_debug()}]",
                )
                return True
        else:
            stable_hits = 0

        if not safe_sleep(WINDOW_DETECT_POLL_INTERVAL_SEC):
            log_color_detection(
                "payment-window-close", False,
                detail=(
                    f"reason=interrupted elapsed={time.monotonic() - start:.3f}s "
                    f"markers=[{get_payment_marker_debug()}]"
                ),
            )
            return False

    log_color_detection(
        "payment-window-close",
        False,
        detail=(
            f"reason=timeout elapsed={time.monotonic() - start:.3f}s "
            f"markers=[{get_payment_marker_debug()}]"
        ),
    )
    return False


def get_window_open_flags():
    """현재 인원창/결제창 열림 상태를 함께 반환한다."""
    payment_open = detect_payment_window_open()
    people_open = detect_people_window_open()
    return payment_open, people_open

def is_time_window_open():
    # 색상 고정값 비교가 아니라, 좌표 (610, 262)의 밝기만으로 창 가시성을 판단한다.
    r, g, b = fast_pixel_strong(610, 262)
    return (r > 150 and g > 150 and b > 150)


def wait_for_usage_type_window(timeout=USAGE_WINDOW_OPEN_TIMEOUT_SEC):
    return wait_for_usage_window_open(timeout)


def detect_usage_type_selected():
    # 이용유형 선택 완료 색: 빨강 (#FF0000)
    for mx, my in USAGE_TYPE_SELECTED_MARKERS:
        if temporal_color_confirm(
            sample_count=2,
            required=1,
            interval=0.0,
            x=mx,
            y=my,
            targets=(255, 0, 0),
            tol=18,
            radius=0,
            min_hits=1,
            use_strong=False,
            hsv_targets=[rgb_to_hsv_deg(255, 0, 0)],
            h_tol=22.0,
            s_tol=0.40,
            v_tol=0.40,
        ):
            return True
    return False


def wait_for_usage_type_selected(timeout=1.2):
    start = time.time()
    while time.time() - start < timeout:
        if detect_usage_type_selected():
            markers = " | ".join(
                f"({mx},{my}):RGB={fast_pixel(mx, my)}"
                for mx, my in USAGE_TYPE_SELECTED_MARKERS
            )
            log_color_detection(
                "usage-type-selected", True, target=(255, 0, 0),
                detail=f"markers=[{markers}]",
            )
            return True
        if emergency_stop:
            return False
        if not safe_sleep(WINDOW_DETECT_POLL_INTERVAL_SEC):
            return False
    markers = " | ".join(
        f"({mx},{my}):RGB={fast_pixel(mx, my)}"
        for mx, my in USAGE_TYPE_SELECTED_MARKERS
    )
    log_color_detection(
        "usage-type-selected", False, target=(255, 0, 0), detail=f"markers=[{markers}]"
    )
    return False


def detect_people_input_completed():
    # 인원 입력 완료 색: 어두운 회색 (#555555)
    r, g, b = fast_pixel_strong(495, 775)
    return (
        abs(r - 85) < 6 and
        abs(g - 85) < 6 and
        abs(b - 85) < 6
    )


def wait_for_people_input_completed(timeout=0.5):
    start = time.time()
    while time.time() - start < timeout:
        if detect_people_input_completed():
            return True
        if emergency_stop:
            return False
        if not safe_sleep(WINDOW_DETECT_POLL_INTERVAL_SEC):
            return False
    return False


def page_down_and_fix(date_str, reservation_id=None):
    if not safe_sleep(DATE_CLICK_PREP_DELAY_SEC):
        return

    # 회색 감지(#5F5F5F) → 날짜 클릭 진행
    r, g, b = fast_pixel_strong(91, 894)
    if abs(r-95) < 5 and abs(g-95) < 5 and abs(b-95) < 5:
        pass

    y, m, d = map(int, date_str.split("-"))
    dx, dy = get_date_position(y, m, d)

    if not safe_sleep(DATE_CLICK_BEFORE_CLICK_DELAY_SEC):
        return
    logged_date_click(date_str, dx, dy, reservation_id)

    safe_sleep(calendar_delay_var.get())

# ============================
# 색상 비교 헬퍼 (안정화 버전)
# ============================
def color_close(r, g, b, target, tol=8):
    return (
        abs(r - target[0]) <= tol and
        abs(g - target[1]) <= tol and
        abs(b - target[2]) <= tol
    )


def log_time_detection_debug(target_time):
    """시간칸 감지 실패 원인 분석용 상세 로그."""
    default_pos = time_positions.get(target_time)
    backup_pos = short_time_positions.get(target_time)

    if default_pos:
        dx, dy = default_pos
        dr, dg, db = fast_pixel_strong(dx, dy)
        default_match, default_hits, default_total = color_match_area(
            dx,
            dy,
            TIME_AVAILABLE_COLORS,
            tol=18,
            radius=1,
            min_hits=2,
            use_strong=True,
            hsv_targets=TIME_AVAILABLE_HSV_COLORS,
            h_tol=20.0,
            s_tol=0.35,
            v_tol=0.35,
        )
        print(
            f"[TIME-DEBUG] 기본표 {target_time} ({dx},{dy}) "
            f"RGB=({dr},{dg},{db}) TARGETS={TIME_AVAILABLE_COLORS} "
            f"tol=18 area={default_hits}/{default_total} match={default_match}"
        )
    else:
        print(f"[TIME-DEBUG] 기본표 {target_time} 좌표 없음")

    if backup_pos:
        bx, by = backup_pos
        br, bg, bb = fast_pixel(bx, by)
        backup_match, backup_hits, backup_total = color_match_area(
            bx,
            by,
            TIME_AVAILABLE_COLORS,
            tol=20,
            radius=1,
            min_hits=2,
            use_strong=False,
            hsv_targets=TIME_AVAILABLE_HSV_COLORS,
            h_tol=22.0,
            s_tol=0.40,
            v_tol=0.40,
        )
        print(
            f"[TIME-DEBUG] 백업표 {target_time} ({bx},{by}) "
            f"RGB=({br},{bg},{bb}) TARGETS={TIME_AVAILABLE_COLORS} "
            f"tol=20 area={backup_hits}/{backup_total} match={backup_match}"
        )
    else:
        print(f"[TIME-DEBUG] 백업표 {target_time} 좌표 없음")

def click_and_confirm_selection(x, y, timeout=0.5, selected_color=SELECTED_COLOR,
                                skip_if_selected=False, before_click=None, label="selection"):
    selected_hsv = rgb_to_hsv_deg(*selected_color)
    for attempt in range(1, 4):
        if emergency_stop:
            return False
        if skip_if_selected:
            selected, hits, total, sample = temporal_color_confirm_details(
                sample_count=2,
                required=1,
                interval=0.0,
                x=x,
                y=y,
                targets=selected_color,
                tol=14,
                radius=0,
                min_hits=1,
                use_strong=False,
                hsv_targets=[selected_hsv],
                h_tol=18.0,
                s_tol=0.30,
                v_tol=0.30,
            )
            if selected:
                r, g, b = fast_pixel(x, y)
                log_color_detection(
                    label, True, coords=(x, y), rgb=(r, g, b), target=selected_color,
                    detail=f"already_selected=True hits={hits}/{total} sample={sample}/2",
                )
                return True
        if not safe_click(x, y, before_click=before_click):
            return False
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if emergency_stop:
                return False
            selected, hits, total, sample = temporal_color_confirm_details(
                sample_count=2,
                required=1,
                interval=0.0,
                x=x,
                y=y,
                targets=selected_color,
                tol=14,
                radius=0,
                min_hits=1,
                use_strong=False,
                hsv_targets=[selected_hsv],
                h_tol=18.0,
                s_tol=0.30,
                v_tol=0.30,
            )
            if selected:
                r, g, b = fast_pixel(x, y)
                log_color_detection(
                    label, True, coords=(x, y), rgb=(r, g, b), target=selected_color,
                    detail=f"attempt={attempt} hits={hits}/{total} sample={sample}/2",
                )
                return True
            if not safe_sleep(WINDOW_DETECT_POLL_INTERVAL_SEC):
                return False
    r, g, b = fast_pixel(x, y)
    log_color_detection(
        label, False, coords=(x, y), rgb=(r, g, b), target=selected_color,
        detail=f"attempts=3 hits={hits}/{total} sample={sample}/2",
    )
    return False

def select_payment_options():
    for label, x, y in (("약관 동의", 263, 567), ("신용카드", 311, 745)):
        # 결제 옵션 선택 확인색: 파란색 (#005CC8)
        if not click_and_confirm_selection(x, y, selected_color=(0, 92, 200),
                                           skip_if_selected=True, label=f"payment-{label}"):
            if not emergency_stop:
                print(f"[FAIL] {label} 색상 2회 클릭 후 미감지 - 다음 예약")
            return False
    return True

# ============================
# 준비 색상 감지 함수
# ============================
def check_ready_color():
    x, y = 427, 739
    r, g, b = pyautogui.pixel(x, y)
    # 준비 기준색: 진한 마젠타 (#CF0A67)
    return color_close(r, g, b, (207, 10, 103), tol=8)

# ============================
# 상태 머신 정의
# ============================
STATE_CALENDAR = 0
STATE_TIME = 1
STATE_COURT = 2
STATE_TYPE = 3
STATE_PEOPLE = 4
STATE_PAYMENT = 5
STATE_DONE = 6

def detect_already_reserved_strong():
    return detect_already_reserved()

def detect_already_reserved():
    x, y = 665, 207
    r, g, b = fast_pixel_strong(x, y)
    return (r, g, b) == (39, 35, 32)

def detect_full_agree_popup():
    # 전체동의 팝업 기준색: 주황색 (#F85E13)
    x, y = 305, 819
    r, g, b = fast_pixel_strong(x, y)
    return abs(r-248) < 12 and abs(g-94) < 12 and abs(b-19) < 12

def wait_payment_result(timeout=2.0):
    start = time.time()
    while time.time() - start < timeout:
        if emergency_stop:
            return "STOP"
        if detect_already_reserved():
            return "ALREADY_RESERVED"
        if detect_full_agree_popup():
            return "FULL_AGREE"
        if not safe_sleep(WINDOW_DETECT_POLL_INTERVAL_SEC):
            return "STOP"
    return "UNKNOWN"


def detect_time_slot_position(target_time):
    """기본/백업 시간표에서 target_time 좌표를 감지해 반환한다."""
    selected_pos = None
    selected_source = None

    default_pos = time_positions.get(target_time)
    if default_pos:
        tx, ty = default_pos
        matched, hits, total, sample = temporal_color_confirm_details(
            sample_count=2,
            required=1,
            interval=0.0,
            x=tx,
            y=ty,
            targets=TIME_AVAILABLE_COLORS,
            tol=18,
            radius=1,
            min_hits=2,
            use_strong=True,
            hsv_targets=TIME_AVAILABLE_HSV_COLORS,
            h_tol=20.0,
            s_tol=0.35,
            v_tol=0.35,
        )
        dr, dg, db = fast_pixel_strong(tx, ty)
        log_color_detection(
            "time-slot-default", matched, coords=(tx, ty), rgb=(dr, dg, db),
            target=TIME_AVAILABLE_COLORS,
            detail=f"time={target_time} hits={hits}/{total} sample={sample}/2",
        )
        if matched:
            selected_pos = (tx, ty)
            selected_source = "default"
    else:
        log_color_detection(
            "time-slot-default", False, target=TIME_AVAILABLE_COLORS,
            detail=f"time={target_time} coord=missing",
        )

    if selected_pos is None:
        backup_pos = short_time_positions.get(target_time)
        if backup_pos:
            tx, ty = backup_pos
            matched, hits, total, sample = temporal_color_confirm_details(
                sample_count=2,
                required=1,
                interval=0.0,
                x=tx,
                y=ty,
                targets=TIME_AVAILABLE_COLORS,
                tol=20,
                radius=1,
                min_hits=2,
                use_strong=False,
                hsv_targets=TIME_AVAILABLE_HSV_COLORS,
                h_tol=22.0,
                s_tol=0.40,
                v_tol=0.40,
            )
            br, bg, bb = fast_pixel(tx, ty)
            log_color_detection(
                "time-slot-backup", matched, coords=(tx, ty), rgb=(br, bg, bb),
                target=TIME_AVAILABLE_COLORS,
                detail=f"time={target_time} hits={hits}/{total} sample={sample}/2",
            )
            if matched:
                selected_pos = (tx, ty)
                selected_source = "backup"
        else:
            log_color_detection(
                "time-slot-backup", False, target=TIME_AVAILABLE_COLORS,
                detail=f"time={target_time} coord=missing",
            )

    return selected_pos, selected_source

def confirm_time_slot_before_click(x, y):
    """Require the actual click point to match an available color in both samples."""
    matched, hits, total, sample = temporal_color_confirm_details(
        sample_count=2,
        required=2,
        interval=0.0,
        x=x,
        y=y,
        targets=TIME_AVAILABLE_COLORS,
        tol=20,
        radius=0,
        min_hits=1,
        use_strong=False,
    )
    r, g, b = fast_pixel(x, y)
    log_color_detection(
        "time-slot-before-click", matched, coords=(x, y), rgb=(r, g, b),
        target=TIME_AVAILABLE_COLORS,
        detail=f"hits={hits}/{total} sample={sample}/2",
    )
    return matched

# ============================
# 예약 실행
# ============================
def run_reservation(res, time_window_confirmed=False, finish_on_time_window_missing=False):
    global emergency_stop
    status.set(f"{res['id']}번 예약 실행 중...")

    stage_recorded = set()

    def mark_stage(stage_name, ok):
        if stage_name in stage_recorded:
            return
        record_stage_outcome(stage_name, ok)
        stage_recorded.add(stage_name)

    def stop_on_court_window_missing():
        print("❌ 코트창 열림 미확인 - 코트 검색/클릭 없이 자동 실행 중단")
        status.set("❌ 코트창 감지 실패 - 안전을 위해 자동 실행 중단")
        mark_stage("court", False)

    if not run_reservation_light_check():
        print("❌ 예약 시작 전 환경 점검/보정 실패 → 다음 예약")
        return "NEXT_RESERVATION"

    state = STATE_TIME

    while state != STATE_DONE and not emergency_stop:

        # ============================
        # 이미 예약됨 팝업 감지
        # ============================
        if detect_already_reserved():
            print("⚠ 이미 예약됨 팝업 감지 → 다음 예약으로 이동")
            if state == STATE_TIME:
                if not cancel_time_window_and_continue():
                    return "STOP"
                return NEXT_RESERVATION_AFTER_ESC
            safe_click(665, 207)
            close_popup_with_esc()
            return "NEXT_RESERVATION"

        # ============================
        # 1) 시간 선택 단계
        # ============================
        if state == STATE_TIME:

            time_window_opened = time_window_confirmed or wait_for_time_window_ready()
            time_window_confirmed = False
            if emergency_stop:
                return "STOP"

            if not time_window_opened:
                if finish_on_time_window_missing:
                    mark_stage("time", False)
                    y, m, d = map(int, res["date"].split("-"))
                    dx, dy = get_date_position(y, m, d)
                    print("[MANUAL-LAST] 마지막 예약 시간창 미오픈 - 같은 날짜 1회 재클릭 후 목록 종료")
                    logged_date_click(res["date"], dx, dy, res["id"])
                    return "MANUAL_LIST_FINISHED"
                mr, mg, mb = fast_pixel(478, 812)
                bright_r, bright_g, bright_b = fast_pixel(610, 262)
                print(
                    "❌ 시간창 미오픈(예약불가 날짜 가능성) → 다음 예약으로 이동 "
                    f"markerCoord=(478,812) markerRGB=({mr},{mg},{mb}) "
                    f"brightnessCoord=(610,262) rgb=({bright_r},{bright_g},{bright_b}) "
                    f"post_failure_diagnostic_markers=[{get_time_marker_debug()}]"
                )
                mark_stage("time", False)
                if not cancel_time_window_and_continue():
                    return "STOP"
                return NEXT_RESERVATION_AFTER_ESC

            selected_pos, selected_source = detect_time_slot_position(res["time"])

            if selected_pos is None:
                print("❌ 기본/백업 시간칸 모두 감지 실패 → 취소 좌표 클릭 후 다음 예약")
                log_time_detection_debug(res["time"])
                mark_stage("time", False)
                if not cancel_time_window_by_coordinates_and_continue():
                    return "STOP"
                return NEXT_RESERVATION_AFTER_ESC

            tx, ty = selected_pos
            if not click_and_confirm_selection(
                tx, ty, timeout=1.2,
                before_click=lambda: confirm_time_slot_before_click(tx, ty),
                label=f"time-slot-{res['time']}",
            ):
                if emergency_stop:
                    return "STOP"
                print(f"[FAIL] {res['time']} 시간 클릭 전/선택 색상 미감지 - 시간창 닫기 클릭 후 다음 예약")
                mark_stage("time", False)
                if not close_time_window_by_click_and_continue():
                    return "STOP"
                return NEXT_RESERVATION_AFTER_ESC
            if selected_source == "backup":
                safe_sleep(0.2)
                safe_click(520, 760)
            else:
                safe_click(520, 810)
            if not wait_for_time_window_close(timeout=TIME_WINDOW_CLOSE_TIMEOUT_SEC):
                print("❌ 시간창 닫힘 확인 실패 - 다음 예약")
                print(f"[TIME-DEBUG] markers=[{get_time_marker_debug()}]")
                mark_stage("time", False)
                if not cancel_time_window_and_continue():
                    return "STOP"
                return NEXT_RESERVATION_AFTER_ESC
            if not wait_for_court_window_open(timeout=COURT_WINDOW_OPEN_TIMEOUT_SEC):
                stop_on_court_window_missing()
                return "STOP"

            mark_stage("time", True)

            state = STATE_COURT

        # ============================
        # 2) 코트 선택 단계
        # ============================
        elif state == STATE_COURT:
            # 완전 오름차순 순환 검색
            target_court = find_available_court(res["court"])

            if not target_court:
                print("❌ 코트 없음 → 다음 예약")
                safe_click(411, 807)
                mark_stage("court", False)
                return "NEXT_RESERVATION"

            cx, cy = court_positions[target_court]
            if not click_and_confirm_selection(
                cx, cy, timeout=1.2, label=f"court-{target_court}-selected"
            ):
                if emergency_stop:
                    return "STOP"
                cr, cg, cb = fast_pixel_strong(cx, cy)
                print(
                    f"[COURT-DEBUG] {target_court}번 ({cx},{cy}) RGB=({cr},{cg},{cb}) "
                    f"selected_target={SELECTED_COLOR}"
                )
                print(f"[FAIL] {target_court}번 코트 선택 색상 2회 클릭 후 미감지 - 다음 예약")
                mark_stage("court", False)
                cancel_time_selection_with_fallback()
                return "NEXT_RESERVATION"
            safe_sleep(court_delay_var.get())

            safe_click(532, 856)
            if not wait_for_court_window_close(timeout=COURT_WINDOW_CLOSE_TIMEOUT_SEC):
                print("❌ 코트창 닫힘 확인 실패 - 다음 예약")
                print(f"[COURT-DEBUG] markers=[{get_court_marker_debug()}]")
                mark_stage("court", False)
                return "NEXT_RESERVATION"

            mark_stage("court", True)

            state = STATE_TYPE

        # ============================
        # 3) 이용유형 선택
        # ============================
        elif state == STATE_TYPE:

            # 창 열림 좌표는 클릭하지 않고 색상으로만 감지한다.
            if not wait_for_usage_type_window(timeout=USAGE_WINDOW_OPEN_TIMEOUT_SEC):
                ur, ug, ub = fast_pixel_strong(494, 821)
                print(f"[USAGE-DEBUG] (494,821) RGB=({ur},{ug},{ub}) expected~{WINDOW_OPEN_COLOR}")
                print(f"[USAGE-DEBUG] markers=[{get_usage_marker_debug()}]")
                print("❌ 이용유형 창 열림 색상 감지 실패")
                mark_stage("usage", False)
                return "NEXT_RESERVATION"

            for _ in range(2):
                if emergency_stop:
                    return "STOP"
                if not safe_click(529, 545):
                    if emergency_stop:
                        return "STOP"
                    print("[FAIL] 이용유형 클릭 실패 - 다음 예약")
                    mark_stage("usage", False)
                    return "NEXT_RESERVATION"
                if wait_for_usage_type_selected(timeout=1.2):
                    break
                if emergency_stop:
                    return "STOP"
            else:
                print("[FAIL] 이용유형 선택 색상 2회 클릭 후 미감지 - 다음 예약")
                mark_stage("usage", False)
                return "NEXT_RESERVATION"

            safe_click(530, 820)
            if not wait_for_usage_window_close(timeout=USAGE_WINDOW_CLOSE_TIMEOUT_SEC):
                print("❌ 이용유형창 닫힘 확인 실패 - 다음 예약")
                print(f"[USAGE-DEBUG] markers=[{get_usage_marker_debug()}]")
                mark_stage("usage", False)
                return "NEXT_RESERVATION"

            mark_stage("usage", True)

            state = STATE_PEOPLE

        # ============================
        # 4) 인원 선택 (최종 안정화)
        # ============================
        elif state == STATE_PEOPLE:

            # 창 열림 여부는 좌표 색상으로만 확인한다.
            if not wait_for_people_window_open(timeout=PEOPLE_WINDOW_OPEN_TIMEOUT_SEC):
                print("❌ 인원선택 창 열림 색상 감지 실패")
                print(f"[PEOPLE-DEBUG] markers=[{get_people_marker_debug()}]")
                mark_stage("people", False)
                return "NEXT_RESERVATION"
            pr, pg, pb = fast_pixel(494, 839)
            people_open_now = detect_people_window_open()
            people_test_log(
                "[TEST-PEOPLE][1] 인원창 열림 감지 성공 "
                f"coord=(494,839) rgb=({pr},{pg},{pb}) people_open={people_open_now} markers=[{get_people_marker_debug()}]"
            )

            # 요청한 고정 순서:
            # 1) TAB 1회
            # 2) ENTER
            # 3) 현재 예약 항목의 인원값 입력
            # 4) ENTER
            # 5) 다음단계 클릭 ([엔터 기록] 좌표: 540,830)
            if emergency_stop:
                return "STOP"

            if not safe_press("tab"):
                print("❌ [TEST-PEOPLE][2] TAB 입력 실패")
                return "STOP"
            people_test_log("[TEST-PEOPLE][2] TAB 입력 성공")
            if not safe_sleep(0.05):
                return "STOP"

            if not safe_press("enter"):
                print("❌ [TEST-PEOPLE][3] ENTER 입력 실패")
                return "STOP"
            if not safe_sleep(0.03):
                return "STOP"
            people_test_log("[TEST-PEOPLE][3] ENTER 입력 성공")

            people_text = str(res["people"]).strip()
            people_test_log(f"[TEST-PEOPLE][4] 예약 인원값 사용 people={people_text}")

            if people_text == "2":
                if not safe_press("2"):
                    print("❌ [TEST-PEOPLE][5] 인원 숫자 입력 실패 key=2")
                    return "STOP"
                people_test_log("[TEST-PEOPLE][5] 인원 숫자 입력 성공 people=2")
            elif people_text == "4":
                if not safe_press("4"):
                    print("❌ [TEST-PEOPLE][5] 인원 숫자 입력 실패 key=4")
                    return "STOP"
                people_test_log("[TEST-PEOPLE][5] 인원 숫자 입력 성공 people=4")
            else:
                for ch in people_text:
                    if not safe_press(ch):
                        print(f"❌ [TEST-PEOPLE][5] 인원 숫자 입력 실패 key={ch}")
                        return "STOP"
                people_test_log(f"[TEST-PEOPLE][5] 인원 숫자 입력 성공 people={people_text}")
            if not safe_sleep(0.03):
                return "STOP"

            if not safe_press("enter"):
                print("❌ [TEST-PEOPLE][6] ENTER 입력 실패")
                return "STOP"
            if not safe_sleep(0.05):
                return "STOP"
            people_test_log("[TEST-PEOPLE][6] ENTER 입력 성공")

            if not safe_click(540, 830):
                print("❌ [TEST-PEOPLE][7] 다음단계 클릭 실패 coord=(540,830)")
                return "STOP"
            people_test_log("[TEST-PEOPLE][7] 다음단계 클릭 성공 coord=(540,830)")
            if not wait_for_people_window_close(timeout=PEOPLE_NEXT_STEP_MARKER_TIMEOUT_SEC):
                pr, pg, pb = fast_pixel(494, 839)
                people_open = detect_people_window_open()
                er, eg, eb = WINDOW_OPEN_COLOR
                print(
                    "❌ 인원 단계 미완료(인원창 유지) - 다음 예약 "
                    f"peopleRGB=({pr},{pg},{pb}) expectedRGB=({er},{eg},{eb}) "
                    f"diff=({abs(pr-er)},{abs(pg-eg)},{abs(pb-eb)}) people_open={people_open}"
                )
                print(f"[PEOPLE-DEBUG] markers=[{get_people_marker_debug()}]")
                mark_stage("people", False)
                return "NEXT_RESERVATION"
            pr, pg, pb = fast_pixel(494, 839)
            people_open_now = detect_people_window_open()
            people_test_log(
                "[TEST-PEOPLE][8] 인원창 닫힘 감지 성공 "
                f"coord=(494,839) rgb=({pr},{pg},{pb}) people_open={people_open_now} markers=[{get_people_marker_debug()}]"
            )

            mark_stage("people", True)

            state = STATE_PAYMENT

        # ============================
        # 5) 결제 단계
        # ============================
        elif state == STATE_PAYMENT:

            if not wait_for_payment_window(timeout=PAYMENT_WINDOW_OPEN_TIMEOUT_SEC):
                pr, pg, pb = fast_pixel_strong(492, 899)
                qr, qg, qb = fast_pixel_strong(574, 893)
                hr, hg, hb = fast_pixel_strong(494, 839)
                nr, ng, nb = fast_pixel_strong(579, 830)
                sr, sg, sb = fast_pixel_strong(573, 828)
                payment_open, people_open = get_window_open_flags()
                marker_debug = get_payment_marker_debug()
                people_marker_debug = get_people_marker_debug()
                print(
                    "❌ 결제단계 진입 차단(창상태 불일치) "
                    f"payment_open={payment_open} people_open={people_open} "
                    f"payCoord=(492,899) payRGB=({pr},{pg},{pb}) "
                    f"payCoord2=(574,893) payRGB2=({qr},{qg},{qb}) "
                    f"peopleCoord=(494,839) peopleRGB=({hr},{hg},{hb}) "
                    f"peopleCoord2=(579,830) peopleRGB2=({nr},{ng},{nb}) "
                    f"peopleCoord3=(573,828) peopleRGB3=({sr},{sg},{sb}) "
                    f"paymentMarkers=[{marker_debug}] peopleMarkers=[{people_marker_debug}]"
                )
                mark_stage("payment", False)
                return "NEXT_RESERVATION"

            # 대기 모드: 약관/카드 선택만 하고 결제창 닫은 뒤 다음 예약으로 이동
            if mode_var.get() == "wait":
                if not select_payment_options():
                    if emergency_stop:
                        return "STOP"
                    mark_stage("payment", False)
                    cancel_time_selection_with_fallback()
                    return "NEXT_RESERVATION"
                safe_click(682, 125)
                if not wait_for_payment_window_close(timeout=PAYMENT_WINDOW_CLOSE_TIMEOUT_SEC):
                    print("⚠ 결제창 닫힘 확인 실패(대기 모드) - 다음 예약 진행")
                mark_stage("payment", True)
                return "NEXT_RESERVATION"

            # 결제 모드: 결제 클릭 후 정상/이미예약완료 분기 처리
            if detect_already_reserved():
                print("⚠ 결제단계에서 이미 예약됨 → 다음 예약")
                safe_click(665, 207)
                close_popup_with_esc()
                return "NEXT_RESERVATION"

            if not select_payment_options():
                if emergency_stop:
                    return "STOP"
                mark_stage("payment", False)
                cancel_time_selection_with_fallback()
                return "NEXT_RESERVATION"
            safe_click(530, 895)

            pay_result = wait_payment_result(timeout=2.0)

            if pay_result == "STOP":
                return "STOP"

            if pay_result == "ALREADY_RESERVED":
                print("⚠ 결제 클릭 후 이미 예약됨 팝업 감지 → 다음 예약")
                safe_click(665, 207)
                close_popup_with_esc()
                return "NEXT_RESERVATION"

            if pay_result == "FULL_AGREE":
                safe_click(807, 247)

            if not wait_for_payment_window_close(timeout=PAYMENT_WINDOW_CLOSE_TIMEOUT_SEC):
                print("⚠ 결제창 닫힘 확인 실패(결제 모드) - 예약 완료로 계속 진행")

            status.set(f"{res['id']}번 예약 완료!")

            mark_stage("payment", True)

            state = STATE_DONE

    if emergency_stop:
        return "STOP"

    return "DONE"
# ============================
# 선택 예약 실행
# ============================
def run_selected():
    global emergency_stop, running, next_auto_run_at, auto_repeat_armed, added_cooldown_until, pause_requested

    if running:
        return
    running = True
    emergency_stop = False
    pause_requested = False

    # 선택 예약 실행 시에는 예약반복대기를 강제로 OFF 처리한다.
    auto_on_var.set(False)
    auto_off_var.set(True)
    auto_repeat_enabled.set(False)
    auto_repeat_armed = False
    next_auto_run_at = None
    added_cooldown_until = None
    with open(settings_path("repeat_settings.txt"), "w") as f:
        f.write("OFF")

    selected = tree.selection()
    if not selected:
        status.set("실행할 예약을 선택하세요")
        running = False
        return

    item = selected[0]
    values = tree.item(item)["values"]

    res = {
        "id": values[0],
        "date": values[1],
        "time": values[2],
        "court": int(values[3]),
        "people": int(values[4]),
    }

    if calendar_click_mode.get() == "auto":
        page_down_and_fix(res["date"], res["id"])

    status.set(f"{res['id']}번 예약 시작 ({res['date']} {res['time']})")
    result = run_reservation(res)

    if result in ("NEXT_RESERVATION", NEXT_RESERVATION_AFTER_ESC):
        status.set(f"{res['id']}번 예약 불가")
        running = False
        return

    if emergency_stop:
        status.set("⛔ ESC로 전체 실행 취소됨")
        running = False
        return "STOP"

    tree.item(item, tags=("done",))
    running = False

# ============================
# 전체 예약 실행
# ============================
import subprocess

def check_ready_color_limited(max_try=5):
    """준비 색상 감지를 최대 max_try 회만 시도"""
    for _ in range(max_try):
        if emergency_stop:
            return False
        if check_ready_color():
            return True
        if not safe_sleep(0.1):
            return False
    return False


def wait_for_auto_start_response():
    """초기 화면 반영과 로딩을 기다리면서 예약 기간 안내를 우선 감지한다."""
    ready_after = time.monotonic() + AUTO_START_RESPONSE_SETTLE_SEC
    while True:
        if emergency_stop:
            return "STOP"
        if detect_auto_start_not_period_color():
            return "RETRY"
        color = fast_pixel(AUTO_START_LOADING_CHECK_X, AUTO_START_LOADING_CHECK_Y)
        if time.monotonic() >= ready_after and color != AUTO_START_LOADING_COLOR:
            return "READY"
        if not safe_sleep(AUTO_START_LOADING_POLL_SEC):
            return "STOP"


def detect_auto_start_not_period_color():
    """관내우선예약 기간이 아님을 나타내는 픽셀 색상인지 확인한다."""
    color = fast_pixel(
        AUTO_START_NOT_PERIOD_CHECK_X,
        AUTO_START_NOT_PERIOD_CHECK_Y,
    )
    return color == AUTO_START_NOT_PERIOD_COLOR


def get_first_reservation_date_position():
    """예약리스트 1번 예약의 날짜 좌표를 반환한다. 없으면 None."""
    items = get_tree_items_sorted_by_id()
    if not items:
        return None

    first_values = tree.item(items[0]).get("values", [])
    if len(first_values) < 2:
        return None

    date_text = str(first_values[1]).strip()
    try:
        y, m, d = map(int, date_text.split("-"))
    except Exception:
        return None

    return get_date_position(y, m, d)


def clear_manual_start_popup():
    """수동 시작 팝업 처리 결과를 READY/CLEARED/STOP으로 반환한다."""
    if not safe_sleep(0):
        return "STOP"
    popup = None
    for name, position, color in (
        ("error", MANUAL_ERROR_POPUP_POSITION, MANUAL_ERROR_POPUP_COLOR),
        ("devtools", MANUAL_DEV_POPUP_POSITION, MANUAL_DEV_POPUP_COLOR),
    ):
        if name != "error":
            pyautogui.moveTo(*position)
        rgb = fast_pixel(*position)
        active_colors = (
            (color, MANUAL_ERROR_POPUP_HOVER_COLOR) if name == "error" else (color,)
        )
        matched = rgb in active_colors
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        print(
            f"[MANUAL-POPUP-CHECK] {timestamp} type={name} "
            f"coord=({position[0]},{position[1]}) RGB={rgb} "
            f"target={color} active_colors={active_colors} matched={matched}"
        )
        if matched:
            popup = (name, position, color, active_colors)
            break
    if popup is None:
        return "READY"

    name, position, color, active_colors = popup
    status.set(f"수동 시작 팝업 감지 ({name}) → 0.1초 간격 2회 클릭")
    print(f"[MANUAL-POPUP] 감지 type={name} coord={position} RGB={color}")
    if name == "error":
        print("[MANUAL-POPUP] 오류창 감지 후 0.1초 대기 → 첫 클릭")
        if not safe_sleep(MANUAL_POPUP_RECLICK_DELAY_SEC):
            return "STOP"
    if not safe_sleep(0):
        return "STOP"
    logged_click(*position)
    if not safe_sleep(MANUAL_POPUP_RECLICK_DELAY_SEC):
        return "STOP"
    logged_click(*position)
    if not safe_sleep(MANUAL_POPUP_RECLICK_DELAY_SEC):
        return "STOP"

    deadline = time.monotonic() + MANUAL_START_POPUP_CLOSE_TIMEOUT_SEC
    stable_hits = 0
    while time.monotonic() < deadline:
        if not safe_sleep(0):
            return "STOP"
        if fast_pixel(*position) in active_colors:
            stable_hits = 0
        else:
            stable_hits += 1
            if stable_hits >= WINDOW_CLOSE_STABLE_HITS:
                if name == "devtools":
                    pyautogui.press("pageup")
                    if not safe_sleep(MANUAL_DEV_POPUP_PAGE_UP_DELAY_SEC):
                        return "STOP"
                print(f"[MANUAL-POPUP] 닫힘 확인 type={name} → 시작 전 검사부터 재시작")
                return "CLEARED"
        if not safe_sleep(WINDOW_DETECT_POLL_INTERVAL_SEC):
            return "STOP"

    status.set(f"❌ 팝업 닫힘 미확인 ({name}) - 수동 시작 중단")
    print(
        f"[MANUAL-POPUP] 닫힘 확인 실패 type={name} "
        "- 다음 클릭/PageUp 없이 수동 시작 중단"
    )
    return "STOP"


def run_manual_start_flow(items=None):
    """수동 시작 시 예약 화면에 진입하고 예약리스트 첫 날짜를 선택한다."""
    if items is None:
        items = get_tree_items_sorted_by_id()
    if not items:
        status.set("❌ 예약리스트가 비어 있어 수동 시작을 중단합니다")
        return False

    first_values = tree.item(items[0]).get("values", [])
    if len(first_values) < 2:
        status.set("❌ 예약리스트 1번 날짜를 찾지 못해 수동 시작을 중단합니다")
        return False
    try:
        y, m, d = map(int, str(first_values[1]).split("-"))
    except ValueError:
        status.set("❌ 예약 날짜 형식이 잘못되어 수동 시작을 중단합니다")
        return False
    date_pos = get_date_position(y, m, d)
    if date_pos is None:
        status.set("❌ 예약 날짜 좌표를 찾지 못해 수동 시작을 중단합니다")
        return False

    while True:
        if emergency_stop:
            status.set("⚠ ESC로 취소됨")
            return False

        popup_result = clear_manual_start_popup()
        if popup_result == "STOP":
            if emergency_stop:
                status.set("⚠ ESC로 취소됨")
            return False
        if popup_result == "CLEARED":
            continue

        print("[MANUAL-START] 시작 전 팝업 미감지 → (235,330) 클릭 후 정상 진행")
        status.set("수동 시작흐름 실행 중...")
        logged_click(AUTO_START_FIRST_CLICK_X, AUTO_START_FIRST_CLICK_Y)
        if not safe_sleep(AUTO_START_AFTER_FIRST_CLICK_DELAY_SEC):
            status.set("⚠ ESC로 취소됨")
            return False

        popup_result = clear_manual_start_popup()
        if popup_result == "STOP":
            if emergency_stop:
                status.set("⚠ ESC로 취소됨")
            return False
        if popup_result == "CLEARED":
            continue

        while fast_pixel(
            AUTO_START_LOADING_CHECK_X,
            AUTO_START_LOADING_CHECK_Y,
        ) == AUTO_START_LOADING_COLOR:
            if not safe_sleep(AUTO_START_LOADING_POLL_SEC):
                status.set("⚠ ESC로 취소됨")
                return False

        if not safe_sleep(AUTO_START_AFTER_FIRST_CLICK_DELAY_SEC):
            status.set("⚠ ESC로 취소됨")
            return False

        logged_click(AUTO_START_NEXT_MONTH_CLICK_X, AUTO_START_NEXT_MONTH_CLICK_Y)
        if not safe_sleep(AUTO_START_AFTER_NEXT_CLICK_DELAY_SEC):
            status.set("⚠ ESC로 취소됨")
            return False

        pyautogui.press("pagedown")
        if not safe_sleep(MANUAL_START_AFTER_PAGE_DOWN_DELAY_SEC):
            status.set("⚠ ESC로 취소됨")
            return False

        dx, dy = date_pos
        logged_date_click(
            str(first_values[1]),
            dx,
            dy,
            first_values[0],
        )
        return True


def start_on_enter(event=None, from_auto=False, from_f2=False, pending_only=False):
    global emergency_stop, auto_repeat_armed, next_auto_run_at, refresh_repeat_enabled, sync_done_for_target, refresh_stop_guard_enabled, pause_requested
    if from_auto and not from_f2 and (pause_requested or emergency_stop):
        return
    emergency_stop = False
    pause_requested = False
    auto_repeat_armed = False

    # 새로고침은 F2 자동 모드에서만 동작한다.
    if not from_auto and not from_f2 and f2_mode_var.get() == "auto":
        arm_scheduled_time_sync()
        if focus_reservation_window() and send_refresh_f5():
            status.set("시작 확인용 새로고침 1회 실행 완료")

            stop_dt = get_refresh_stop_datetime()
            if stop_dt is not None and datetime.datetime.now() >= stop_dt:
                refresh_repeat_enabled = False
                auto_repeat_armed = False
                sync_done_for_target = False
                refresh_stop_guard_enabled = False
                next_auto_run_at = None
                status.set("새로고침 종료 시각(목표 -10분) 경과 - 반복 미시작")
            else:
                refresh_repeat_enabled = True
                auto_repeat_armed = True
                sync_done_for_target = False
                refresh_stop_guard_enabled = True
                next_auto_run_at = time.time() + get_refresh_interval_seconds()
        else:
            status.set("시작 확인용 새로고침 1회 실패")

    # F2 자동 모드 대기
    if f2_mode_var.get() == "auto" and not from_auto and not from_f2:
        status.set("⏳ F2 자동 모드 — 목표시간 설정까지 대기합니다")
        return

    # ============================
    # 자동 실행(from_auto) 루틴
    # ============================
    auto_start_date_clicked = False
    manual_start_date_clicked = False
    items = get_tree_items_sorted_by_id()
    if pending_only:
        items = [item for item in items if "done" not in tree.item(item)["tags"]]
        if not items:
            status.set("예약반복대기 중 - 모든 예약 완료")
            return
    if f2_mode_var.get() == "manual":
        manual_start_date_clicked = run_manual_start_flow(items)
        if not manual_start_date_clicked:
            return

    if from_auto:

        attempt = 0
        while True:
            if emergency_stop:
                status.set("⚠ ESC로 취소됨")
                return

            attempt += 1
            status.set(f"자동 시작흐름 실행 중... ({attempt})")

            # 1) 관내우선예약 클릭
            logged_click(AUTO_START_FIRST_CLICK_X, AUTO_START_FIRST_CLICK_Y)
            if not safe_sleep(AUTO_START_AFTER_FIRST_CLICK_DELAY_SEC):
                status.set("⚠ ESC로 취소됨")
                return

            # 마우스를 올렸을 때 표시되는 색상을 감지한다.
            pyautogui.moveTo(AUTO_START_NOT_PERIOD_CHECK_X, AUTO_START_NOT_PERIOD_CHECK_Y)

            # 늦게 뜨는 안내창도 로딩 대기 중 계속 확인한다.
            response = wait_for_auto_start_response()
            if response == "RETRY":
                status.set("예약 기간 아님 감지 → (665, 207) 클릭 후 1번부터 재시작")
                print("[AUTO-START] coord=(665,207) RGB=(0,0,0) → 클릭 후 1번 재시작")
                logged_click(AUTO_START_NOT_PERIOD_CHECK_X, AUTO_START_NOT_PERIOD_CHECK_Y)
                if not safe_sleep(AUTO_START_RETRY_CLICK_DELAY_SEC):
                    status.set("⚠ ESC로 취소됨")
                    return
                continue

            if response == "STOP":
                status.set("⚠ ESC로 취소됨")
                return

            # 4) 다음달 클릭
            logged_click(AUTO_START_NEXT_MONTH_CLICK_X, AUTO_START_NEXT_MONTH_CLICK_Y)
            if not safe_sleep(AUTO_START_AFTER_NEXT_CLICK_DELAY_SEC):
                status.set("⚠ ESC로 취소됨")
                return

            # 5) 페이지다운
            pyautogui.press("pagedown")

            # 6) 대기
            if not safe_sleep(AUTO_START_AFTER_PAGE_DOWN_DELAY_SEC):
                status.set("⚠ ESC로 취소됨")
                return

            # 첫 날짜는 색상과 무관하게 클릭하고 실제 시간창 열림을 확인한다.
            date_pos = get_first_reservation_date_position()
            if date_pos is None:
                status.set("❌ 예약리스트 1번 날짜를 찾지 못해 자동 시작 중단")
                emergency_stop = True
                return

            dx, dy = date_pos
            first_item = get_tree_items_sorted_by_id()[0]
            first_values = tree.item(first_item).get("values", [])
            logged_date_click(
                str(first_values[1]),
                dx,
                dy,
                first_values[0],
            )
            if not safe_sleep(0.1):
                status.set("⚠ ESC로 취소됨")
                return
            if wait_for_time_window_ready(max_attempts=1):
                print("[AUTO-START] 첫 시간창 열림 확인 완료 → 시간 선택 진행")
                auto_start_date_clicked = True
                break

            if emergency_stop:
                status.set("⚠ ESC로 취소됨")
                return

            status.set("시간창 열림 미감지 → 팝업 정리 후 자동 시작 재시도")
            print(
                "[AUTO-START] 시간창 미오픈 "
                f"post_failure_diagnostic_markers=[{get_time_marker_debug()}]"
            )
            if not cancel_time_window_and_continue():
                stop_all_automation("❌ 시간창 정리/닫힘 확인 실패 - 자동 시작 중단")
                return

            pyautogui.press("pageup")

            # 11) 대기 후 12) 1번부터 재시작
            if not safe_sleep(AUTO_START_PAGE_UP_RETRY_DELAY_SEC):
                status.set("⚠ ESC로 취소됨")
                return

        from_auto = False
        from_f2 = True

    # ============================
    # 시간 저장
    # ============================
    # 시작 흐름에서 날짜를 이미 눌렀으면 안정화 클릭이 날짜 선택을 방해하지 않게 생략한다.
    date_clicked_before_startup = auto_start_date_clicked or manual_start_date_clicked
    if not run_startup_strong_precheck(warmup_click=not date_clicked_before_startup):
        status.set("❌ 시작 전 환경 점검/보정 실패")
        return

    auto_calculate_times()
    save_time_settings()

    # ============================
    # 예약 실행 루프
    # ============================
    try:
        repeat_count = max(1, int(list_repeat_count_var.get()))
    except Exception:
        repeat_count = 1

    list_finished = run_reservation_items(
        items,
        repeat_count,
        date_clicked_before_startup,
        auto_start_date_clicked,
        pending_only,
    )
    if emergency_stop:
        return
    if manual_start_date_clicked and list_finished:
        if not finish_manual_reservation_list():
            return
    if not list_finished:
        return

    status.set("전체 예약리스트 처리 종료!" if manual_start_date_clicked else "전체 예약 완료!")

    if f2_mode_var.get() == "manual" and is_auto_repeat_on() and not emergency_stop:
        repeat_seconds = get_repeat_wait_seconds()
        auto_repeat_armed = True
        next_auto_run_at = time.time() + repeat_seconds
    elif f2_mode_var.get() == "auto" and refresh_repeat_enabled and not emergency_stop:
        repeat_seconds = get_repeat_wait_seconds()
        auto_repeat_armed = True
        next_auto_run_at = time.time() + repeat_seconds


def finish_manual_reservation_list():
    """마지막 항목까지 처리한 수동 예약 목록을 페이지업으로 종료한다."""
    if not safe_sleep(AUTO_START_AFTER_LIST_COMPLETE_DELAY_SEC):
        return False
    pyautogui.press("pageup")
    print("[MANUAL-END] 예약 목록 처리 종료 - PageUp 전송")
    return safe_sleep(AUTO_START_AFTER_LIST_PAGE_UP_DELAY_SEC)


def run_reservation_items(
    items, repeat_count, date_clicked_before_startup, auto_start_date_clicked, pending_only
):
    for round_idx in range(repeat_count):
        round_ended_after_esc = False
        for index, item in enumerate(items):

            if emergency_stop:
                status.set("⚠ ESC로 취소됨")
                return
            if pending_only and "done" in tree.item(item)["tags"]:
                continue

            values = tree.item(item)["values"]

            res = {
                "id": values[0],
                "date": values[1],
                "time": values[2],
                "court": int(values[3]),
                "people": int(values[4]),
            }

            status.set(
                f"[{round_idx + 1}/{repeat_count}] {res['id']}번 예약 시작 ({res['date']} {res['time']})"
            )

            date_already_clicked = (
                date_clicked_before_startup and round_idx == 0 and index == 0
            )
            if calendar_click_mode.get() == "auto" and not date_already_clicked:
                page_down_and_fix(res["date"], res["id"])

            if auto_start_date_clicked and round_idx == 0 and index == 0:
                result = run_reservation(res, time_window_confirmed=True)
            else:
                finish_on_time_window_missing = (
                    f2_mode_var.get() == "manual"
                    and round_idx == repeat_count - 1
                    and not any(
                        not pending_only or "done" not in tree.item(next_item)["tags"]
                        for next_item in items[index + 1:]
                    )
                )
                result = run_reservation(
                    res, finish_on_time_window_missing=finish_on_time_window_missing
                )
            if result == "MANUAL_LIST_FINISHED":
                return True
            round_ended_after_esc = result == NEXT_RESERVATION_AFTER_ESC

            if result in ("NEXT_RESERVATION", NEXT_RESERVATION_AFTER_ESC):
                if result == "NEXT_RESERVATION" and index < len(items) - 1:
                    if not reset_after_reservation():
                        status.set("❌ 예약창 정리 실패 - 마우스 입력 없이 자동 실행 중지")
                        return
                elif (
                    result == NEXT_RESERVATION_AFTER_ESC
                    and index < len(items) - 1
                    and not wait_for_next_reservation_transition()
                ):
                    status.set("⚠ ESC로 취소됨")
                    return
                continue

            if result == "STOP":
                if (
                    f2_mode_var.get() == "manual"
                    and index == len(items) - 1
                    and not emergency_stop
                ):
                    return True
                return

            tree.item(item, tags=("done",))

            if index < len(items) - 1:
                if not reset_after_reservation():
                    status.set("❌ 예약창 정리 실패 - 마우스 입력 없이 자동 실행 중지")
                    return

        if (
            round_idx < repeat_count - 1
            and not emergency_stop
            and not round_ended_after_esc
        ):
            if not reset_after_reservation():
                status.set("❌ 예약창 정리 실패 - 마우스 입력 없이 자동 실행 중지")
                return

    return True


# ============================
# CRUD + UI + 메인 루프
# ============================
reservations = []
TIME_OPTIONS = ["06:00", "08:00", "10:00", "12:00", "14:00", "16:00", "18:00", "20:00"]

def get_selected_dates_from_ui():
    indices = date_listbox.curselection()
    if indices:
        return [date_listbox.get(i) for i in indices]
    return []

def get_selected_times_from_ui():
    indices = time_listbox.curselection()
    if indices:
        return [time_listbox.get(i) for i in indices]
    return []

def refresh_date_listbox_height(min_rows=7, max_rows=31):
    rows = date_listbox.size()
    rows = max(min_rows, min(max_rows, rows))
    date_listbox.config(height=rows)

def refresh_time_listbox_height(min_rows=8, max_rows=24):
    rows = time_listbox.size()
    rows = max(min_rows, min(max_rows, rows))
    time_listbox.config(height=rows)

def add_date_to_list(date_text):
    if not date_text:
        return
    existing = [date_listbox.get(i) for i in range(date_listbox.size())]
    if date_text in existing:
        return
    existing.append(date_text)
    existing.sort()
    date_listbox.delete(0, tk.END)
    for d in existing:
        date_listbox.insert(tk.END, d)
    refresh_date_listbox_height()

def remove_selected_dates():
    indices = list(date_listbox.curselection())
    if not indices:
        status.set("날짜 리스트에서 제거할 항목을 선택하세요")
        return
    for i in reversed(indices):
        date_listbox.delete(i)
    refresh_date_listbox_height()
    status.set("선택한 날짜를 제거했습니다")

def clear_date_list():
    date_listbox.delete(0, tk.END)
    refresh_date_listbox_height()
    status.set("날짜 리스트를 초기화했습니다")

def clear_date_selection():
    date_listbox.selection_clear(0, tk.END)
    status.set("날짜 선택을 해제했습니다")

def fill_date_list(start_date=None, days=20):
    if start_date is None:
        start_date = datetime.date.today()
    date_listbox.delete(0, tk.END)
    for i in range(days):
        d = start_date + datetime.timedelta(days=i)
        date_listbox.insert(tk.END, d.strftime("%Y-%m-%d"))
    refresh_date_listbox_height()

def fill_date_list_until_day(total_days=17):
    # 당일을 1일로 계산해서 total_days 만큼만 표시
    today = datetime.date.today()
    date_listbox.delete(0, tk.END)
    for i in range(total_days):
        d = today + datetime.timedelta(days=i)
        date_listbox.insert(tk.END, d.strftime("%Y-%m-%d"))
    refresh_date_listbox_height()

def select_date_by_rule(rule):
    date_listbox.selection_clear(0, tk.END)
    for i in range(date_listbox.size()):
        d = date_listbox.get(i)
        dt = datetime.datetime.strptime(d, "%Y-%m-%d").date()
        wd = dt.weekday()  # Mon=0 ... Sun=6

        ok = False
        if rule == "all":
            ok = True
        elif rule == "weekday":
            ok = wd <= 4
        elif rule == "weekend":
            ok = wd >= 5
        elif rule == "wf":
            ok = wd in (2, 4)

        if ok:
            date_listbox.selection_set(i)

def set_next_month_dates(days=8):
    today = datetime.date.today()
    next_month_first = (today.replace(day=1) + datetime.timedelta(days=32)).replace(day=1)
    fill_date_list(next_month_first, days=days)
    select_date_by_rule("all")
    status.set("다음달 날짜 목록으로 변경됨")

def select_time_by_rule(rule):
    time_listbox.selection_clear(0, tk.END)
    for i in range(time_listbox.size()):
        t = time_listbox.get(i)
        hour = int(t.split(":")[0])

        ok = False
        if rule == "all":
            ok = True
        elif rule == "morning":
            ok = hour < 12
        elif rule == "afternoon":
            ok = 12 <= hour < 18
        elif rule == "night":
            ok = hour >= 18
        elif rule == "10to16":
            ok = 10 <= hour <= 16

        if ok:
            time_listbox.selection_set(i)

def add_reservation():
    global next_auto_run_at, added_cooldown_until, auto_repeat_armed
    dates = get_selected_dates_from_ui()
    times = get_selected_times_from_ui()
    # 코트/인원을 선택하지 않으면 "전체"와 동일하게 모든 값을 대상으로 한다.
    courts = [court_var.get()] if court_var.get() else list(court_cb["values"])
    peoples = [people_var.get()] if people_var.get() else list(people_cb["values"])

    if not (dates and times and courts and peoples):
        status.set("날짜/시간/코트/인원을 모두 선택하세요")
        return

    next_id = len(tree.get_children()) + 1
    added_count = 0

    for d in dates:
        for t in times:
            for c in courts:
                for p in peoples:
                    tree.insert("", "end", values=(next_id, d, t, c, p))
                    reservations.append({
                        "id": next_id,
                        "date": d,
                        "time": t,
                        "court": int(c),
                        "people": int(p),
                    })
                    next_id += 1
                    added_count += 1

    if f2_mode_var.get() == "manual" and is_auto_repeat_on():
        repeat_seconds = get_repeat_wait_seconds()
        added_cooldown_until = time.time() + repeat_seconds
        next_auto_run_at = added_cooldown_until
        auto_repeat_armed = True

    if f2_mode_var.get() == "manual" and is_auto_repeat_on():
        status.set(f"예약 {added_count}건 추가됨 - {repeat_seconds}초 후 미완료 예약 실행")
    else:
        status.set(f"예약 {added_count}건 추가됨")

def modify_reservation():
    selected = tree.selection()
    if not selected:
        status.set("수정할 예약을 선택하세요")
        return

    item = selected[0]
    values = tree.item(item)["values"]

    date_sel = get_selected_dates_from_ui()
    time_sel = get_selected_times_from_ui()
    d = date_sel[0] if date_sel else values[1]
    t = time_sel[0] if time_sel else values[2]
    c = court_var.get()
    p = people_var.get()

    if not (d and t and c and p):
        status.set("날짜/시간/코트/인원을 모두 선택하세요")
        return

    tree.item(item, values=(values[0], d, t, c, p))

    for r in reservations:
        if r["id"] == values[0]:
            r["date"] = d
            r["time"] = t
            r["court"] = int(c)
            r["people"] = int(p)

    status.set(f"예약 {values[0]}번 수정 완료")

def delete_reservation():
    selected = tree.selection()
    if not selected:
        status.set("삭제할 예약을 선택하세요")
        return

    # 선택된 모든 예약의 ID를 수집
    del_ids = []
    for item in selected:
        values = tree.item(item)["values"]
        del_ids.append(values[0])

    # 선택된 예약들을 삭제
    global reservations
    reservations = [r for r in reservations if r["id"] not in del_ids]

    # ID 재정렬
    for idx, r in enumerate(reservations, start=1):
        r["id"] = idx

    # 트리 뷰 초기화 후 재구성
    for row in tree.get_children():
        tree.delete(row)

    for r in reservations:
        tree.insert("", "end", values=(r["id"], r["date"], r["time"], r["court"], r["people"]))

    deleted_count = len(del_ids)
    status.set(f"예약 {deleted_count}건 삭제 완료")

def delete_all_reservations():
    items = tree.get_children()
    if not items:
        status.set("삭제할 예약이 없습니다")
        return

    tree.delete(*items)
    reservations.clear()
    status.set(f"예약 전체 {len(items)}건 삭제 완료")

def open_calendar():
    cal_win = tk.Toplevel(root)
    cal_win.title("날짜 선택")
    cal = Calendar(cal_win, selectmode='day', date_pattern="yyyy-mm-dd")
    cal.pack(padx=10, pady=10)

    def select_date(event=None):
        date_var.set(cal.get_date())
        add_date_to_list(cal.get_date())
        cal_win.destroy()
        root.after(100, lambda: root.focus_force())

    cal.bind("<<CalendarSelected>>", select_date)

    ttk.Button(cal_win, text="날짜 추가", command=select_date).pack(pady=5)

# ============================
# UI
# ============================
ensure_admin()
root = tk.Tk()
root.title("도시공사 예약 자동화 — 초고속 최종 버전")

combo_style = ttk.Style(root)
if "clam" in combo_style.theme_names():
    combo_style.theme_use("clam")
combo_style.configure("Court.TCombobox", padding=2)
combo_style.map(
    "Court.TCombobox",
    fieldbackground=[("readonly", "#E3F2FD")],
    selectbackground=[("readonly", "#BBDEFB")],
    selectforeground=[("readonly", "#000000")],
)
combo_style.configure("People.TCombobox", padding=2)
combo_style.map(
    "People.TCombobox",
    fieldbackground=[("readonly", "#E8F5E9")],
    selectbackground=[("readonly", "#C8E6C9")],
    selectforeground=[("readonly", "#000000")],
)

def place_window_top_right(margin_x=12, margin_y=10):
    # 위젯 배치 후 실제 창 크기를 기준으로 우상단 위치를 계산한다.
    root.update_idletasks()
    win_w = root.winfo_width()
    win_h = root.winfo_height()
    scr_w = root.winfo_screenwidth()
    x = max(0, scr_w - win_w - margin_x)
    y = max(0, margin_y)
    root.geometry(f"{win_w}x{win_h}+{x}+{y}")


def format_points(points):
    return ", ".join(f"({x},{y})" for x, y in points)


def build_process_coordinate_summary_text():
    lines = []
    lines.append("[도시공사 예약 자동화 - 전체공정 좌표 정리]")
    lines.append("")
    lines.append("1) 공통/초기")
    lines.append(f"- 브라우저 포커스 클릭 좌표: ({click_x_var.get()},{click_y_var.get()})")
    lines.append(f"- 브라우저 탭/타이틀바 클릭 좌표: (807,248)")
    lines.append(f"- 새로고침 포커스 좌표: ({REFRESH_FOCUS_X},{REFRESH_FOCUS_Y})")
    lines.append(f"- F5 전 대기: {REFRESH_PRE_F5_DELAY_SEC:.2f}초")
    lines.append("")
    lines.append("2) 달력 단계")
    lines.append(f"- 5주 달력 경계: LT{calendar_bounds['5week']['lt']} ~ RB{calendar_bounds['5week']['rb']}")
    lines.append(f"- 6주 달력 경계: LT{calendar_bounds['6week']['lt']} ~ RB{calendar_bounds['6week']['rb']}")
    lines.append("- 날짜 클릭 좌표: 위 경계 기반 계산(get_date_position)")
    lines.append("")
    lines.append("3) 시간 단계")
    lines.append(f"- 시간창 열림 마커: {format_points(TIME_WINDOW_MARKERS)}")
    lines.append(f"- 시간창 열림 대기: {TIME_WINDOW_OPEN_TIMEOUT_SEC:.2f}초")
    lines.append(f"- 시간창 닫힘 대기: {TIME_WINDOW_CLOSE_TIMEOUT_SEC:.2f}초")
    lines.append(f"- 시간창 재시도: 최대 {TIME_WINDOW_OPEN_MAX_RETRIES}회, 간격 {TIME_WINDOW_OPEN_RETRY_GAP_SEC:.2f}초")
    lines.append("- 시간칸 클릭 조건: 클릭 좌표의 예약 가능 RGB 색상 2회 확인(재클릭 시에도 확인)")
    lines.append("- 기본/백업 시간칸 모두 미감지: 취소 좌표 (410,810), (410,760) 순으로 클릭 후 닫힘 확인")
    lines.append("- 취소 좌표로 시간창이 닫히지 않으면 다음 예약 클릭 없이 중단")
    lines.append("- 다음단계 버튼: 기본 (520,810), 단축운영 백업 (520,760)")
    lines.append("- 시간칸 좌표(기본):")
    for key in sorted(time_positions.keys()):
        x, y = time_positions[key]
        lines.append(f"  {key}: ({x},{y})")
    lines.append("- 시간칸 좌표(단축운영 백업):")
    for key in sorted(short_time_positions.keys()):
        x, y = short_time_positions[key]
        lines.append(f"  {key}: ({x},{y})")
    lines.append("")
    lines.append("4) 코트 단계")
    lines.append(f"- 코트창 열림 마커: {format_points(COURT_WINDOW_MARKERS)}")
    lines.append(f"- 코트창 열림 대기: {COURT_WINDOW_OPEN_TIMEOUT_SEC:.2f}초")
    lines.append(f"- 코트창 닫힘 대기: {COURT_WINDOW_CLOSE_TIMEOUT_SEC:.2f}초")
    lines.append("- 다음단계 버튼: (532,856)")
    lines.append("- 코트 좌표:")
    for num in sorted(court_positions.keys()):
        x, y = court_positions[num]
        lines.append(f"  {num}번: ({x},{y})")
    lines.append("")
    lines.append("5) 이용유형 단계")
    lines.append(f"- 이용유형창 열림 마커: {format_points(USAGE_WINDOW_MARKERS)}")
    lines.append(f"- 이용유형 선택 확인 마커: {format_points(USAGE_TYPE_SELECTED_MARKERS)}")
    lines.append(f"- 이용유형창 열림 대기: {USAGE_WINDOW_OPEN_TIMEOUT_SEC:.2f}초")
    lines.append(f"- 이용유형창 닫힘 대기: {USAGE_WINDOW_CLOSE_TIMEOUT_SEC:.2f}초")
    lines.append("- 이용유형 선택 클릭: (529,545)")
    lines.append("- 다음단계 버튼: (530,820)")
    lines.append("")
    lines.append("6) 인원 단계")
    lines.append(f"- 인원창 열림 마커: {format_points(PEOPLE_WINDOW_MARKERS)}")
    lines.append(f"- 인원창 열림 대기: {PEOPLE_WINDOW_OPEN_TIMEOUT_SEC:.2f}초")
    lines.append(f"- 인원창 닫힘 대기: {PEOPLE_NEXT_STEP_MARKER_TIMEOUT_SEC:.2f}초")
    lines.append("- 입력칸 클릭: (453,520)")
    lines.append("- 다음단계 버튼: (540,830) [엔터 기록]")
    lines.append("")
    lines.append("7) 결제 단계")
    lines.append(f"- 결제창 열림 마커: {format_points(PAYMENT_WINDOW_MARKERS)}")
    lines.append(f"- 결제창 열림 대기: {PAYMENT_WINDOW_OPEN_TIMEOUT_SEC:.2f}초")
    lines.append(f"- 결제창 닫힘 대기: {PAYMENT_WINDOW_CLOSE_TIMEOUT_SEC:.2f}초")
    lines.append("- 옵션 클릭(약관 동의): (263,567)")
    lines.append("- 옵션 클릭(신용카드): (311,745)")
    lines.append("- 결제 버튼: (530,895)")
    lines.append("- 대기 모드 닫기(X): (682,125)")
    lines.append("- 완료 후 포커스 복귀: (807,247)")
    lines.append("- 이미예약 팝업 확인 버튼(수동/자동 공통): (665,207), RGB=(39,35,32) 감지")
    lines.append("")
    lines.append("ESC: 짧게 전체 일시정지/재개, 0.5초 이상 전체 취소")
    lines.append("")
    lines.append("8) 자동(F2) 보조 좌표")
    lines.append(f"- 수동 시작/반복: 첫 클릭 전후 {MANUAL_ERROR_POPUP_POSITION}의 RGB={MANUAL_ERROR_POPUP_COLOR} 감지 → 0.1초 대기 → 같은 좌표 클릭 → 0.1초 → 재클릭 → 0.1초")
    lines.append(f"- 수동 오류창 검사는 마우스 이동 없이 수행, 마우스 오버 색상 {MANUAL_ERROR_POPUP_HOVER_COLOR}도 감지/닫힘 확인에 포함")
    lines.append("- 수동 팝업 검사 로그: MANUAL-POPUP-CHECK에 좌표/실제 RGB/기준색/matched 기록, 미감지 시 MANUAL-START 후 첫 클릭 진행")
    lines.append("- 수동 개발도구 팝업: (579,705), RGB=(240,248,255) 감지 시 클릭 → 0.1초 → 재클릭 → 0.1초 → 닫힘 확인 → PageUp → 0.3초 → 시작 전 검사부터 재시작")
    lines.append(f"- 수동 시작 전 팝업: 닫힘을 최대 {MANUAL_START_POPUP_CLOSE_TIMEOUT_SEC:.1f}초 확인, 미확인 시 첫 클릭 없이 해당 실행 중단")
    lines.append("- 자동 실행 준비 클릭: (235,330)")
    lines.append("- 자동 실행 다음달 클릭: (682,675)")
    lines.append("- 준비 색상 검사 좌표: (427,739)")
    lines.append("")
    lines.append("9) 색상 기준")
    lines.append(f"- 예약 가능(TARGET_COLOR): {TARGET_COLOR}")
    lines.append(f"- 선택 완료(SELECTED_COLOR): {SELECTED_COLOR}")
    lines.append(f"- 창 열림(WINDOW_OPEN_COLOR): {WINDOW_OPEN_COLOR}")
    return "\n".join(lines)


def show_process_coordinate_window():
    existing = getattr(show_process_coordinate_window, "window", None)
    if existing is not None and existing.winfo_exists():
        existing.lift()
        existing.focus_force()
        text_widget = getattr(show_process_coordinate_window, "text_widget", None)
        if text_widget is not None and text_widget.winfo_exists():
            text_widget.config(state="normal")
            text_widget.delete("1.0", tk.END)
            text_widget.insert("1.0", build_process_coordinate_summary_text())
            text_widget.config(state="disabled")
        return

    win = tk.Toplevel(root)
    win.title("전체공정 좌표 정리")
    win.geometry("760x720")

    top_bar = ttk.Frame(win)
    top_bar.pack(fill="x", padx=8, pady=(8, 4))

    ttk.Label(top_bar, text="전체공정 좌표/타임아웃/설명").pack(side="left")

    text_frame = ttk.Frame(win)
    text_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    y_scroll = ttk.Scrollbar(text_frame, orient="vertical")
    x_scroll = ttk.Scrollbar(text_frame, orient="horizontal")
    text = tk.Text(
        text_frame,
        wrap="none",
        font=("Consolas", 10),
        yscrollcommand=y_scroll.set,
        xscrollcommand=x_scroll.set,
    )
    y_scroll.config(command=text.yview)
    x_scroll.config(command=text.xview)

    y_scroll.pack(side="right", fill="y")
    x_scroll.pack(side="bottom", fill="x")
    text.pack(side="left", fill="both", expand=True)

    text.insert("1.0", build_process_coordinate_summary_text())
    text.config(state="disabled")

    bottom_bar = ttk.Frame(win)
    bottom_bar.pack(fill="x", padx=8, pady=(0, 8))

    def refresh_text():
        text.config(state="normal")
        text.delete("1.0", tk.END)
        text.insert("1.0", build_process_coordinate_summary_text())
        text.config(state="disabled")

    def copy_text():
        body = build_process_coordinate_summary_text()
        root.clipboard_clear()
        root.clipboard_append(body)
        status.set("전체공정 좌표 정리를 클립보드에 복사했습니다")

    ttk.Button(bottom_bar, text="새로고침", command=refresh_text).pack(side="left")
    ttk.Button(bottom_bar, text="복사", command=copy_text).pack(side="left", padx=(6, 0))
    ttk.Button(bottom_bar, text="닫기", command=win.destroy).pack(side="right")

    show_process_coordinate_window.window = win
    show_process_coordinate_window.text_widget = text

    def on_close_coordinate_window():
        show_process_coordinate_window.window = None
        show_process_coordinate_window.text_widget = None
        win.destroy()

    win.protocol("WM_DELETE_WINDOW", on_close_coordinate_window)

# 버튼 색상 스타일 정의
tk.Button(
    root,
    text="전체 예약 시작(자동반복 활성화)",
    command=start_on_enter,
    bg="#4CAF50",
    fg="white",
    activebackground="#45A049",
    font=("맑은 고딕", 10, "bold"),
    width=22,
    height=1
).grid(row=12, column=0, columnspan=2, padx=2, pady=2)

tk.Button(
    root,
    text="선택 예약 실행",
    command=run_selected,
    bg="#FFF176",
    fg="black",
    activebackground="#FFEE58",
    font=("맑은 고딕", 10, "bold"),
    width=16,
    height=1
).grid(row=12, column=3, columnspan=2, padx=2, pady=2)


def start_reservation_test_now():
    # 테스트 버튼은 목표시간 대기 없이 즉시 실행한다.
    # F2 자동 모드에서는 실제 자동 진입 루틴(from_auto)을 그대로 테스트한다.
    if f2_mode_var.get() == "auto":
        start_on_enter(from_auto=True, from_f2=True)
    else:
        start_on_enter(from_f2=True)


tk.Button(
    root,
    text="예약 테스트(즉시)",
    command=start_reservation_test_now,
    bg="#90CAF9",
    fg="black",
    activebackground="#64B5F6",
    font=("맑은 고딕", 10, "bold"),
    width=12,
    height=1
).grid(row=12, column=2, padx=2, pady=2)

def on_close():
    global emergency_stop
    emergency_stop = True
    try:
        save_time_settings()
        save_repeat_time()
        save_ui_state()
        save_calibration_state()
    except Exception as e:
        print("설정 저장 오류:", e)
    root.destroy()
    os._exit(0)

root.protocol("WM_DELETE_WINDOW", on_close)

hour_var = tk.StringVar(value="10")
min_var = tk.StringVar(value="00")
sec_var = tk.StringVar(value="00")

sync_offset_var = tk.StringVar(value=str(DEFAULT_SYNC_OFFSET_MIN))
refresh_stop_offset_var = tk.StringVar(value=str(DEFAULT_REFRESH_STOP_OFFSET_MIN))
sync_hour_var = tk.StringVar(value="00")
sync_min_var = tk.StringVar(value="00")
repeat_time_var = tk.IntVar(value=20)
repeat_exec_sec_var = tk.IntVar(value=5)
list_repeat_count_var = tk.IntVar(value=1)

status = tk.StringVar(value="대기 중")

click_x_var = tk.StringVar(value="800")
click_y_var = tk.StringVar(value="250")

def persist_court_people_state(*_):
    """Save court/people immediately so restart/other reads can use latest values."""
    data = {}
    if os.path.exists(UI_STATE_FILE):
        try:
            with open(UI_STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

    data["court"] = court_var.get()
    data["people"] = people_var.get()

    with open(UI_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

settings_frame = ttk.LabelFrame(root, text="ui 및 코드 수정")
settings_frame.grid(row=0, column=0, columnspan=5, sticky="ew", padx=2, pady=(2, 4))

ttk.Label(settings_frame, text="").grid(row=0, column=0, padx=(4, 6), pady=(2, 2), sticky="w")
ttk.Label(settings_frame, text="항목").grid(row=0, column=1, padx=(0, 8), pady=(2, 2), sticky="w")
ttk.Label(settings_frame, text="입력란").grid(row=0, column=2, padx=(0, 8), pady=(2, 2), sticky="w")
ttk.Label(settings_frame, text="실행방법").grid(row=0, column=3, padx=(0, 6), pady=(2, 2), sticky="w")

ttk.Label(settings_frame, text="1").grid(row=1, column=0, padx=(4, 6), sticky="w")
ttk.Label(settings_frame, text="목표시간 설정").grid(row=1, column=1, sticky="w")
target_time_frame = ttk.Frame(settings_frame)
target_time_frame.grid(row=1, column=2, sticky="w")
hour_entry = ttk.Entry(target_time_frame, textvariable=hour_var, width=3)
min_entry = ttk.Entry(target_time_frame, textvariable=min_var, width=3)
sec_entry = ttk.Entry(target_time_frame, textvariable=sec_var, width=3)
hour_entry.grid(row=0, column=0)
ttk.Label(target_time_frame, text="시").grid(row=0, column=1)
min_entry.grid(row=0, column=2)
ttk.Label(target_time_frame, text="분").grid(row=0, column=3)
sec_entry.grid(row=0, column=4)
ttk.Label(target_time_frame, text="초").grid(row=0, column=5)

ttk.Label(settings_frame, text="2").grid(row=2, column=0, padx=(4, 6), sticky="w")
ttk.Label(settings_frame, text="동기화 시간").grid(row=2, column=1, sticky="w")
sync_input_frame = ttk.Frame(settings_frame)
sync_input_frame.grid(row=2, column=2, sticky="w")
sync_offset_entry = ttk.Entry(sync_input_frame, textvariable=sync_offset_var, width=6)
sync_offset_entry.grid(row=0, column=0, sticky="w")
ttk.Label(sync_input_frame, text="분").grid(row=0, column=1, padx=(4, 0))
ttk.Button(
    settings_frame,
    text="PC 시간 동기화 실행",
    command=lambda: status.set("PC 시간 인터넷 동기화 완료") if sync_pc_time() else status.set("PC 시간 동기화 실패"),
).grid(row=2, column=3, sticky="w")

ttk.Label(settings_frame, text="3").grid(row=3, column=0, padx=(4, 6), sticky="w")
ttk.Label(settings_frame, text="새로고침").grid(row=3, column=1, sticky="w")
refresh_stop_frame = ttk.Frame(settings_frame)
refresh_stop_frame.grid(row=3, column=2, sticky="w")
refresh_stop_entry = ttk.Entry(refresh_stop_frame, textvariable=refresh_stop_offset_var, width=6)
refresh_stop_entry.grid(row=0, column=0, sticky="w")
ttk.Label(refresh_stop_frame, text="분").grid(row=0, column=1, padx=(4, 0))
ttk.Label(settings_frame, text="-10분전 마지막 1회 후 종료").grid(row=3, column=3, sticky="w")

ttk.Label(settings_frame, text="4").grid(row=4, column=0, padx=(4, 6), sticky="w")
ttk.Label(settings_frame, text="새로고침 간격").grid(row=4, column=1, sticky="w")
refresh_interval_frame = ttk.Frame(settings_frame)
refresh_interval_frame.grid(row=4, column=2, sticky="w")
ttk.Entry(refresh_interval_frame, textvariable=repeat_time_var, width=6).grid(row=0, column=0, sticky="w")
ttk.Label(refresh_interval_frame, text="초").grid(row=0, column=1, padx=(4, 0))
ttk.Label(settings_frame, text="F5").grid(row=4, column=3, sticky="w")

ttk.Label(settings_frame, text="5").grid(row=5, column=0, padx=(4, 6), sticky="w")
ttk.Label(settings_frame, text="예약반복대기(초)").grid(row=5, column=1, sticky="w")
repeat_exec_frame = ttk.Frame(settings_frame)
repeat_exec_frame.grid(row=5, column=2, sticky="w")
ttk.Entry(repeat_exec_frame, textvariable=repeat_exec_sec_var, width=6).grid(row=0, column=0, sticky="w")
ttk.Label(repeat_exec_frame, text="초").grid(row=0, column=1, padx=(4, 0))

ttk.Label(settings_frame, text="6").grid(row=6, column=0, padx=(4, 6), sticky="w")
ttk.Label(settings_frame, text="카톡알림").grid(row=6, column=1, sticky="w")

ttk.Label(settings_frame, text="7").grid(row=7, column=0, padx=(4, 6), sticky="w")
ttk.Label(settings_frame, text="예약리스트 반복횟수").grid(row=7, column=1, sticky="w")
repeat_list_frame = ttk.Frame(settings_frame)
repeat_list_frame.grid(row=7, column=2, sticky="w")
ttk.Entry(repeat_list_frame, textvariable=list_repeat_count_var, width=6).grid(row=0, column=0, sticky="w")
ttk.Label(repeat_list_frame, text="회").grid(row=0, column=1, padx=(4, 0))

def on_schedule_setting_changed(*_):
    global sync_done_for_target
    sync_done_for_target = False
    auto_calculate_times()

hour_var.trace_add("write", on_schedule_setting_changed)
min_var.trace_add("write", on_schedule_setting_changed)
sec_var.trace_add("write", on_schedule_setting_changed)
sync_offset_var.trace_add("write", on_schedule_setting_changed)



ttk.Label(root, text="예약 조건 설정").grid(row=4, column=0, columnspan=5)

date_var = tk.StringVar()
court_var = tk.StringVar()
people_var = tk.StringVar()

date_listbox = tk.Listbox(root, selectmode=tk.MULTIPLE, height=7, width=14, exportselection=False)
date_listbox.grid(row=5, column=0, rowspan=5, padx=2, pady=2)

time_listbox = tk.Listbox(root, selectmode=tk.MULTIPLE, height=7, width=10, exportselection=False)
time_listbox.grid(row=5, column=2, rowspan=5, padx=2, pady=2)
for t in TIME_OPTIONS:
    time_listbox.insert(tk.END, t)
refresh_time_listbox_height()

tk.Button(root, text="전체", command=lambda: select_date_by_rule("all"), bg="#E3F2FD", activebackground="#BBDEFB", fg="black", font=("맑은 고딕", 9)).grid(row=5, column=1, padx=2, pady=1, sticky="ew")
tk.Button(root, text="주중", command=lambda: select_date_by_rule("weekday"), bg="#E3F2FD", activebackground="#BBDEFB", fg="black", font=("맑은 고딕", 9)).grid(row=6, column=1, padx=2, pady=1, sticky="ew")
tk.Button(root, text="주말", command=lambda: select_date_by_rule("weekend"), bg="#E3F2FD", activebackground="#BBDEFB", fg="black", font=("맑은 고딕", 9)).grid(row=7, column=1, padx=2, pady=1, sticky="ew")
tk.Button(root, text="수금", command=lambda: select_date_by_rule("wf"), bg="#E3F2FD", activebackground="#BBDEFB", fg="black", font=("맑은 고딕", 9)).grid(row=8, column=1, padx=2, pady=1, sticky="ew")
tk.Button(root, text="다음달", command=set_next_month_dates, bg="#E3F2FD", activebackground="#BBDEFB", fg="black", font=("맑은 고딕", 9)).grid(row=9, column=1, padx=2, pady=1, sticky="ew")

tk.Button(root, text="전체", command=lambda: select_time_by_rule("all"), bg="#FFF8E1", activebackground="#FFECB3", fg="black", font=("맑은 고딕", 9)).grid(row=5, column=3, padx=2, pady=1, sticky="ew")
tk.Button(root, text="오전", command=lambda: select_time_by_rule("morning"), bg="#FFF8E1", activebackground="#FFECB3", fg="black", font=("맑은 고딕", 9)).grid(row=6, column=3, padx=2, pady=1, sticky="ew")
tk.Button(root, text="오후", command=lambda: select_time_by_rule("afternoon"), bg="#FFF8E1", activebackground="#FFECB3", fg="black", font=("맑은 고딕", 9)).grid(row=7, column=3, padx=2, pady=1, sticky="ew")
tk.Button(root, text="야간", command=lambda: select_time_by_rule("night"), bg="#FFF8E1", activebackground="#FFECB3", fg="black", font=("맑은 고딕", 9)).grid(row=8, column=3, padx=2, pady=1, sticky="ew")
tk.Button(root, text="10~16", command=lambda: select_time_by_rule("10to16"), bg="#FFF8E1", activebackground="#FFECB3", fg="black", font=("맑은 고딕", 9)).grid(row=9, column=3, padx=2, pady=1, sticky="ew")

court_people_frame = ttk.Frame(root)
court_people_frame.grid(row=5, column=4, rowspan=2, padx=2, pady=2, sticky="n")

ttk.Label(court_people_frame, text="코트").grid(row=0, column=0, sticky="w")
court_cb = ttk.Combobox(
    court_people_frame,
    textvariable=court_var,
    values=[str(i) for i in range(1, 14)],
    state="readonly",
    style="Court.TCombobox",
    width=5
)
court_cb.grid(row=0, column=1, padx=(4, 0), pady=(0, 2))

ttk.Label(court_people_frame, text="인원").grid(row=1, column=0, sticky="w")
people_cb = ttk.Combobox(
    court_people_frame,
    textvariable=people_var,
    values=["2","4"],
    state="readonly",
    style="People.TCombobox",
    width=5
)
people_cb.grid(row=1, column=1, padx=(4, 0))

court_cb.bind("<<ComboboxSelected>>", persist_court_people_state)
people_cb.bind("<<ComboboxSelected>>", persist_court_people_state)

tk.Button(root, text="날짜 선택해제", command=clear_date_selection, bg="#E0E0E0", activebackground="#D5D5D5", fg="black", font=("맑은 고딕", 9)).grid(row=10, column=0)
tk.Button(root, text="전체삭제", command=delete_all_reservations, bg="#E57373", activebackground="#EF5350", fg="white", font=("맑은 고딕", 9)).grid(row=10, column=1)
tk.Button(root, text="예약 추가", command=add_reservation, bg="#64B5F6", activebackground="#42A5F5", fg="black", font=("맑은 고딕", 9)).grid(row=10, column=2)
tk.Button(root, text="예약 수정", command=modify_reservation, bg="#FFB74D", activebackground="#FFA726", fg="black", font=("맑은 고딕", 9)).grid(row=10, column=3)
tk.Button(root, text="선택삭제", command=delete_reservation, bg="#E57373", activebackground="#EF5350", fg="white", font=("맑은 고딕", 9)).grid(row=10, column=4)

# 기본 조건: 날짜/시간은 자동 선택하지 않고 사용자가 직접 선택한다.
fill_date_list_until_day(17)
date_listbox.selection_clear(0, tk.END)
time_listbox.selection_clear(0, tk.END)

columns = ("id", "date", "time", "court", "people")
tree = ttk.Treeview(root, columns=columns, show="headings", height=6, selectmode="extended")
tree.grid(row=11, column=0, columnspan=5)
tree.tag_configure("done", background="#c8f7c5")

def get_tree_items_sorted_by_id():
    """Return tree items sorted by reservation ID (번호)."""
    def sort_key(item_id):
        values = tree.item(item_id)["values"]
        try:
            rid = int(values[0])
        except Exception:
            rid = 999999

        return rid

    return sorted(tree.get_children(), key=sort_key)

tree.heading("id", text="번호")
tree.heading("date", text="날짜")
tree.heading("time", text="시간")
tree.heading("court", text="코트")
tree.heading("people", text="인원")

tree.column("id", width=40)
tree.column("date", width=100)
tree.column("time", width=60)
tree.column("court", width=50)
tree.column("people", width=50)

ttk.Label(root, textvariable=status).grid(row=13, column=0, columnspan=5)

# F2 모드
f2_mode_var = tk.StringVar(value="manual")

def set_f2_manual():
    f2_mode_var.set("manual")
    apply_f2_mode_rules(update_status=True)
    with open(settings_path("f2_settings.txt"), "w") as f:
        f.write("manual")

def set_f2_auto():
    f2_mode_var.set("auto")
    apply_f2_mode_rules(update_status=True)
    with open(settings_path("f2_settings.txt"), "w") as f:
        f.write("auto")

f2_manual_radio = ttk.Radiobutton(root, text="F2 수동", variable=f2_mode_var, value="manual", command=set_f2_manual)
f2_auto_radio  = ttk.Radiobutton(root, text="F2 자동", variable=f2_mode_var, value="auto", command=set_f2_auto)

f2_manual_radio.grid(row=14, column=0)
f2_auto_radio.grid(row=14, column=1)

def auto_f2_tick():
    global last_auto_f2_trigger

    try:
        if not pause_requested and not emergency_stop and f2_mode_var.get() == "auto":
            now = datetime.datetime.now()
            check_scheduled_time_sync(now)
            now = datetime.datetime.now()
            target_h = int(hour_var.get())
            target_m = int(min_var.get())
            target_s = int(sec_var.get())

            tick_key = now.strftime("%Y-%m-%d %H:%M:%S")
            if (
                now.hour == target_h and
                now.minute == target_m and
                now.second == target_s and
                last_auto_f2_trigger != tick_key
            ):
                last_auto_f2_trigger = tick_key
                start_on_enter(from_auto=True)
    except Exception as e:
        print("auto_f2_tick 오류:", e)

    root.after(200, auto_f2_tick)


def arm_scheduled_time_sync():
    """시작 버튼을 누른 뒤 아직 지나지 않은 동기화 시각만 예약한다."""
    global scheduled_sync_armed, scheduled_sync_target
    scheduled_sync_armed = True
    scheduled_sync_target = None
    check_scheduled_time_sync(datetime.datetime.now())


def check_scheduled_time_sync(now):
    """시작 후 예약한 시각에 도달했을 때만 동기화한다."""
    global sync_done_for_target, scheduled_sync_target
    global scheduled_sync_attempts, scheduled_sync_retry_at, scheduled_sync_waiting

    if not scheduled_sync_armed:
        return

    target_dt = get_next_target_datetime()
    sync_dt = get_sync_datetime()
    if target_dt is None or sync_dt is None:
        return

    schedule_key = (target_dt, sync_dt)
    if scheduled_sync_target != schedule_key:
        scheduled_sync_target = schedule_key
        scheduled_sync_attempts = 0
        scheduled_sync_retry_at = 0.0
        sync_done_for_target = False
        scheduled_sync_waiting = now < sync_dt
        if not scheduled_sync_waiting:
            print(
                f"[TIME-SYNC] 예약 시각 경과 - 자동 동기화 건너뜀 "
                f"now={now} target={target_dt} scheduled={sync_dt}"
            )

    if (
        not scheduled_sync_waiting
        or sync_done_for_target
        or now < sync_dt
        or scheduled_sync_attempts >= 3
        or time.monotonic() < scheduled_sync_retry_at
    ):
        return

    scheduled_sync_attempts += 1
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    print(
        f"[TIME-SYNC] {timestamp} target={target_dt} scheduled={sync_dt} "
        f"attempt={scheduled_sync_attempts}/3"
    )
    if sync_pc_time():
        sync_done_for_target = True
        message = f"자동 시간 동기화 완료 {datetime.datetime.now().strftime('%H:%M:%S')}"
    elif scheduled_sync_attempts < 3:
        scheduled_sync_retry_at = time.monotonic() + 5.0
        message = f"자동 시간 동기화 실패(w32tm) - 5초 후 재시도 ({scheduled_sync_attempts}/3)"
    else:
        message = "자동 시간 동기화 실패(w32tm) - 3회 실패, PC 시간 동기화 버튼으로 확인하세요"
    print(f"[TIME-SYNC] {message}")
    status.set(message)


# 달력 클릭 모드
calendar_click_mode = tk.StringVar(value="auto")

def set_calendar_click_manual():
    calendar_click_mode.set("manual")
    with open(settings_path("calendar_click_settings.txt"), "w") as f:
        f.write("manual")

def set_calendar_click_auto():
    calendar_click_mode.set("auto")
    with open(settings_path("calendar_click_settings.txt"), "w") as f:
        f.write("auto")

calendar_manual_radio = ttk.Radiobutton(root, text="달력 수동 클릭", variable=calendar_click_mode, value="manual", command=set_calendar_click_manual)
calendar_auto_radio = ttk.Radiobutton(root, text="달력 자동 클릭", variable=calendar_click_mode, value="auto", command=set_calendar_click_auto)

calendar_manual_radio.grid(row=15, column=0)
calendar_auto_radio.grid(row=15, column=1)

# 달력 모드 (5주/6주)
calendar_mode_var = tk.StringVar(value="5week")

def set_calendar_5week():
    calendar_mode_var.set("5week")
    with open(settings_path("calendar_settings.txt"), "w") as f:
        f.write("5week")

def set_calendar_6week():
    calendar_mode_var.set("6week")
    with open(settings_path("calendar_settings.txt"), "w") as f:
        f.write("6week")

calendar5_radio = ttk.Radiobutton(root, text="달력 5주", variable=calendar_mode_var, value="5week", command=set_calendar_5week)
calendar6_radio = ttk.Radiobutton(root, text="달력 6주", variable=calendar_mode_var, value="6week", command=set_calendar_6week)

calendar5_radio.grid(row=16, column=0)
calendar6_radio.grid(row=16, column=1)

# 결제 모드
mode_var = tk.StringVar(value="wait")

wait_check = ttk.Radiobutton(root, text="대기", variable=mode_var, value="wait")
pay_check = ttk.Radiobutton(root, text="결제", variable=mode_var, value="pay")

wait_check.grid(row=17, column=0)
pay_check.grid(row=17, column=1)

# 기본값은 빠름 프로필이며, 정상 종료 시 저장한 개별 값은 load_ui_state에서 복원한다.
click_delay_var = tk.DoubleVar(value=0.01)
press_delay_var = tk.DoubleVar(value=0.01)
page_delay_var = tk.DoubleVar(value=0.05)
pay_delay_var = tk.DoubleVar(value=0.05)
calendar_delay_var = tk.DoubleVar(value=0.05)
court_delay_var = tk.DoubleVar(value=0.05)

ttk.Label(root, text="클릭 딜레이").grid(row=18, column=0)
ttk.Entry(root, textvariable=click_delay_var, width=5).grid(row=18, column=1)

ttk.Label(root, text="키 입력 딜레이").grid(row=19, column=0)
ttk.Entry(root, textvariable=press_delay_var, width=5).grid(row=19, column=1)

ttk.Label(root, text="페이지 이동 딜레이").grid(row=20, column=0)
ttk.Entry(root, textvariable=page_delay_var, width=5).grid(row=20, column=1)

ttk.Label(root, text="결제 단계 딜레이").grid(row=21, column=0)
ttk.Entry(root, textvariable=pay_delay_var, width=5).grid(row=21, column=1)

ttk.Label(root, text="달력 클릭 딜레이").grid(row=22, column=0)
ttk.Entry(root, textvariable=calendar_delay_var, width=5).grid(row=22, column=1)

ttk.Label(root, text="코트 선택 딜레이").grid(row=23, column=0)
ttk.Entry(root, textvariable=court_delay_var, width=5).grid(row=23, column=1)

# 프로필 전환 시 현재 입력값을 저장하고 선택한 프로필의 사용자 값을 복원한다.
delay_profile_values = {
    "FAST": dict(zip(("click", "press", "page", "payment", "calendar", "court"),
                     (0.01, 0.01, 0.05, 0.05, 0.05, 0.05))),
    "NORMAL": dict(zip(("click", "press", "page", "payment", "calendar", "court"),
                       (0.08, 0.06, 0.25, 0.18, 0.15, 0.15))),
    "SAFE": dict(zip(("click", "press", "page", "payment", "calendar", "court"),
                     (0.15, 0.10, 0.50, 0.30, 0.20, 0.20))),
}
active_delay_profile = "FAST"


def select_delay_profile(mode):
    global active_delay_profile
    current = {}
    for name, variable in get_delay_variables().items():
        try:
            value = variable.get()
        except (tk.TclError, ValueError) as error:
            status.set("딜레이 입력 오류 - 숫자 입력 후 프로필을 변경하세요")
            print(f"[PROFILE-SWITCH-FAIL] {name}: {error}")
            return
        if not math.isfinite(value) or value < 0:
            status.set("딜레이는 0 이상의 유한한 숫자로 입력하세요")
            print(f"[PROFILE-SWITCH-FAIL] {name}: {value}")
            return
        current[name] = value
    delay_profile_values[active_delay_profile] = current
    active_delay_profile = mode
    for name, variable in get_delay_variables().items():
        variable.set(delay_profile_values[mode][name])
    try:
        save_ui_state()
        with open(settings_path("profile_settings.txt"), "w") as f:
            f.write(mode)
    except OSError as error:
        status.set("프로필 적용됨 - 저장 실패, 로그를 확인하세요")
        print(f"[PROFILE-SAVE-FAIL] {error}")
        return
    status.set(f"{ {'FAST': '빠름', 'NORMAL': '보통', 'SAFE': '안정'}[mode]} 사용자 설정 적용/저장됨")


def set_profile_fast():
    select_delay_profile("FAST")

def set_profile_normal():
    select_delay_profile("NORMAL")

def set_profile_safe():
    select_delay_profile("SAFE")

tk.Button(root, text="빠름", command=set_profile_fast, bg="#E57373", activebackground="#EF5350", fg="white", font=("맑은 고딕", 9)).grid(row=24, column=0)
tk.Button(root, text="보통", command=set_profile_normal, bg="#FFF176", activebackground="#FFEE58", fg="black", font=("맑은 고딕", 9)).grid(row=24, column=1)
tk.Button(root, text="안정", command=set_profile_safe, bg="#81C784", activebackground="#66BB6A", fg="black", font=("맑은 고딕", 9)).grid(row=24, column=2)
tk.Button(root, text="전체공정 좌표보기", command=show_process_coordinate_window, bg="#B3E5FC", activebackground="#81D4FA", fg="black", font=("맑은 고딕", 9, "bold")).grid(row=24, column=3, columnspan=2, sticky="ew", padx=2)

# 반복시간 저장

def save_repeat_time():
    with open(settings_path("repeat_time_settings.txt"), "w") as f:
        f.write(str(repeat_time_var.get()))

def load_repeat_time():
    if not os.path.exists(settings_path("repeat_time_settings.txt")):
        return
    with open(settings_path("repeat_time_settings.txt"), "r") as f:
        raw = f.read().strip()
    if raw.isdigit():
        repeat_time_var.set(int(raw))

def get_delay_variables():
    return {
        "click": click_delay_var,
        "press": press_delay_var,
        "page": page_delay_var,
        "payment": pay_delay_var,
        "calendar": calendar_delay_var,
        "court": court_delay_var,
    }


def save_ui_state():
    data = {
        "hour": hour_var.get(),
        "min": min_var.get(),
        "sec": sec_var.get(),
        "sync_offset": sync_offset_var.get(),
        "refresh_stop_offset": refresh_stop_offset_var.get(),
        "selected_times": get_selected_times_from_ui(),
        "court": court_var.get(),
        "people": people_var.get(),
        "repeat_time": repeat_time_var.get(),
        "repeat_exec_sec": repeat_exec_sec_var.get(),
        "list_repeat_count": list_repeat_count_var.get(),
    }
    delays = {}
    for name, variable in get_delay_variables().items():
        try:
            value = variable.get()
        except (tk.TclError, ValueError) as error:
            print(f"[DELAY-SAVE-FAIL] {name}: 숫자 입력 오류 ({error})")
            continue
        if not math.isfinite(value) or value < 0:
            print(f"[DELAY-SAVE-FAIL] {name}: 0 이상의 유한한 값이 필요합니다 ({value})")
            continue
        delays[name] = value
    data["delays"] = delays
    delay_profile_values[active_delay_profile].update(delays)
    data["delay_profiles"] = delay_profile_values
    data["active_delay_profile"] = active_delay_profile
    with open(UI_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

def load_ui_state():
    global active_delay_profile
    if not os.path.exists(UI_STATE_FILE):
        return

    with open(UI_STATE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    profiles = data.get("delay_profiles", {})
    if isinstance(profiles, dict):
        for mode, values in profiles.items():
            if mode not in delay_profile_values or not isinstance(values, dict):
                print(f"[PROFILE-LOAD-FAIL] 잘못된 프로필: {mode}")
                continue
            for name, value in values.items():
                if (
                    name not in delay_profile_values[mode]
                    or isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(value)
                    or value < 0
                ):
                    print(f"[PROFILE-LOAD-FAIL] {mode}/{name}: {value!r}")
                    continue
                delay_profile_values[mode][name] = value
    else:
        print("[PROFILE-LOAD-FAIL] 프로필 설정 형식 오류")
    saved_mode = data.get("active_delay_profile", active_delay_profile)
    if isinstance(saved_mode, str) and saved_mode in delay_profile_values:
        active_delay_profile = saved_mode
    else:
        print(f"[PROFILE-LOAD-FAIL] 잘못된 선택 프로필: {saved_mode!r}")
    for name, variable in get_delay_variables().items():
        variable.set(delay_profile_values[active_delay_profile][name])
    delays = (
        delay_profile_values[active_delay_profile]
        if "delay_profiles" in data else data.get("delays", {})
    )
    if not isinstance(delays, dict):
        print("[DELAY-LOAD-FAIL] 딜레이 설정 형식 오류 - 프로필 기본값 유지")
        delays = {}
    for name, variable in get_delay_variables().items():
        if name not in delays:
            continue
        value = delays[name]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
        ):
            print(f"[DELAY-LOAD-FAIL] {name}: 잘못된 값 {value!r} - 프로필 기본값 유지")
            continue
        variable.set(value)
        delay_profile_values[active_delay_profile][name] = value

    hour = str(data.get("hour", "")).strip()
    minute = str(data.get("min", "")).strip()
    sec = str(data.get("sec", "")).strip()
    if hour:
        hour_var.set(hour)
    if minute:
        min_var.set(minute)
    if sec:
        sec_var.set(sec)

    sync_offset = str(data.get("sync_offset", "")).strip()
    refresh_stop_offset = str(data.get("refresh_stop_offset", "")).strip()
    if sync_offset:
        sync_offset_var.set(sync_offset)
    if refresh_stop_offset:
        refresh_stop_offset_var.set(refresh_stop_offset)

    court = str(data.get("court", "")).strip()
    people = str(data.get("people", "")).strip()
    if court:
        court_var.set(court)
    if people:
        people_var.set(people)

    repeat_raw = data.get("repeat_time", None)
    if repeat_raw is not None:
        try:
            repeat_time_var.set(int(repeat_raw))
        except:
            pass

    repeat_exec_raw = data.get("repeat_exec_sec", None)
    if repeat_exec_raw is not None:
        try:
            repeat_exec_sec_var.set(int(repeat_exec_raw))
        except:
            pass

    list_repeat_raw = data.get("list_repeat_count", None)
    if list_repeat_raw is not None:
        try:
            list_repeat_count_var.set(max(1, int(list_repeat_raw)))
        except:
            pass

    selected_times = data.get("selected_times", [])
    if isinstance(selected_times, list):
        selected_set = set(str(t) for t in selected_times)
        time_listbox.selection_clear(0, tk.END)
        for i in range(time_listbox.size()):
            if time_listbox.get(i) in selected_set:
                time_listbox.selection_set(i)

# 자동 반복 상태 변수
auto_repeat_enabled = tk.BooleanVar(value=False)
next_auto_run_at = None
auto_repeat_running = False
auto_repeat_armed = False
refresh_repeat_enabled = False
sync_done_for_target = False
scheduled_sync_armed = False
scheduled_sync_waiting = False
scheduled_sync_target = None
scheduled_sync_attempts = 0
scheduled_sync_retry_at = 0.0
refresh_stop_guard_enabled = False
last_auto_f2_trigger = ""
added_cooldown_until = None

auto_on_var = tk.BooleanVar(value=False)
auto_off_var = tk.BooleanVar(value=True)

def is_auto_repeat_on():
    # ON is valid only when ON checked and OFF unchecked.
    return auto_repeat_enabled.get() and auto_on_var.get() and (not auto_off_var.get())

def get_repeat_wait_seconds():
    try:
        return max(1, int(repeat_exec_sec_var.get()))
    except Exception:
        return 5

def get_refresh_interval_seconds():
    try:
        return max(1, int(repeat_time_var.get())) 
    except Exception:
        return 20

def is_repeat_loop_enabled():
    if f2_mode_var.get() == "manual":
        return is_auto_repeat_on()
    return refresh_repeat_enabled

def toggle_auto_on():
    global emergency_stop, next_auto_run_at, auto_repeat_armed
    if f2_mode_var.get() != "manual":
        auto_on_var.set(False)
        auto_off_var.set(True)
        auto_repeat_enabled.set(False)
        status.set("F2 자동 모드에서는 예약반복대기 ON/OFF를 사용할 수 없습니다")
        return

    auto_on_var.set(True)
    auto_off_var.set(False)
    auto_repeat_enabled.set(True)
    # Auto-repeat restart should clear previous emergency state.
    emergency_stop = False
    # Start after full interval, not immediately.
    repeat_seconds = get_repeat_wait_seconds()
    next_auto_run_at = time.time() + repeat_seconds
    auto_repeat_armed = True
    status.set(f"예약반복대기 ON - {repeat_seconds}초 후 미완료 예약 실행")
    with open(settings_path("repeat_settings.txt"), "w") as f:
        f.write("ON")

def toggle_auto_off():
    global next_auto_run_at, auto_repeat_armed
    auto_on_var.set(False)
    auto_off_var.set(True)
    auto_repeat_enabled.set(False)
    next_auto_run_at = None
    auto_repeat_armed = False
    status.set("자동 반복 OFF - 1회 실행 모드")
    with open(settings_path("repeat_settings.txt"), "w") as f:
        f.write("OFF")

repeat_toggle_frame = ttk.Frame(settings_frame)
repeat_toggle_frame.grid(row=5, column=3, sticky="w")
repeat_on_check = ttk.Checkbutton(repeat_toggle_frame, text="ON", variable=auto_on_var, command=toggle_auto_on)
repeat_off_check = ttk.Checkbutton(repeat_toggle_frame, text="OFF", variable=auto_off_var, command=toggle_auto_off)
repeat_on_check.grid(row=0, column=0)
repeat_off_check.grid(row=0, column=1)

# 카카오톡 알림 ON/OFF
kakao_notify_var = tk.BooleanVar(value=False)
ttk.Checkbutton(settings_frame, text="ON/OFF", variable=kakao_notify_var).grid(row=6, column=3, sticky="w")

def apply_f2_mode_rules(update_status=False):
    global refresh_repeat_enabled, next_auto_run_at, auto_repeat_armed, sync_done_for_target, refresh_stop_guard_enabled
    global scheduled_sync_armed
    scheduled_sync_armed = False
    mode = f2_mode_var.get()

    if mode == "manual":
        refresh_repeat_enabled = False
        next_auto_run_at = None
        refresh_stop_guard_enabled = False
        repeat_on_check.state(["!disabled"])
        repeat_off_check.state(["!disabled"])
        sync_offset_entry.state(["disabled"])
        refresh_stop_entry.state(["disabled"])
        if update_status:
            status.set("F2 수동 모드: 예약반복대기 ON/OFF 사용")
        return

    auto_on_var.set(False)
    auto_off_var.set(True)
    auto_repeat_enabled.set(False)
    auto_repeat_armed = False
    next_auto_run_at = None
    sync_done_for_target = False
    refresh_stop_guard_enabled = False
    repeat_on_check.state(["disabled"])
    repeat_off_check.state(["disabled"])
    sync_offset_entry.state(["!disabled"])
    refresh_stop_entry.state(["!disabled"])
    if update_status:
        status.set("F2 자동 모드: 동기화시간/새로고침 사용")

# ============================
# 설정 불러오기
# ============================
def load_repeat_settings():
    global next_auto_run_at, auto_repeat_armed
    # Safety default: never auto-enable recurring execution when the app starts.
    auto_on_var.set(False)
    auto_off_var.set(True)
    auto_repeat_enabled.set(False)
    next_auto_run_at = None
    auto_repeat_armed = False

    state_file = settings_path("repeat_settings.txt")
    if not os.path.exists(state_file):
        return

    with open(state_file, "r") as f:
        state = f.read().strip()

    if state == "ON":
        # Previous session may have left ON saved; keep startup behavior explicit.
        with open(state_file, "w") as f:
            f.write("OFF")

def load_profile_settings():
    global active_delay_profile
    mode = "FAST"
    if os.path.exists(settings_path("profile_settings.txt")):
        with open(settings_path("profile_settings.txt"), "r") as f:
            mode = f.read().strip()
    if mode not in delay_profile_values:
        print(f"[PROFILE-LOAD-FAIL] 알 수 없는 모드 {mode!r} - FAST 사용")
        mode = "FAST"
    active_delay_profile = mode
    for name, variable in get_delay_variables().items():
        variable.set(delay_profile_values[mode][name])

def load_calendar_settings():
    if not os.path.exists(settings_path("calendar_settings.txt")):
        return
    with open(settings_path("calendar_settings.txt"), "r") as f:
        mode = f.read().strip()
    if mode == "5week":
        calendar_mode_var.set("5week")
    elif mode == "6week":
        calendar_mode_var.set("6week")

def load_calendar_click_settings():
    if not os.path.exists(settings_path("calendar_click_settings.txt")):
        return
    with open(settings_path("calendar_click_settings.txt"), "r") as f:
        mode = f.read().strip()
    if mode == "manual":
        calendar_click_mode.set("manual")
    elif mode == "auto":
        calendar_click_mode.set("auto")

def load_f2_settings():
    if not os.path.exists(settings_path("f2_settings.txt")):
        return
    with open(settings_path("f2_settings.txt"), "r") as f:
        mode = f.read().strip()
    if mode == "manual":
        f2_mode_var.set("manual")
    elif mode == "auto":
        f2_mode_var.set("auto")

# 설정 불러오기 실행
load_time_settings()
load_repeat_time()
load_repeat_settings()
load_profile_settings()
load_calendar_settings()
load_calendar_click_settings()
load_f2_settings()
load_ui_state()
load_calibration_state()
apply_f2_mode_rules(update_status=False)

# 실행 시 창을 항상 우측 상단에 배치
place_window_top_right()

# ============================
# 자동 반복 기능 (메인 루프 스케줄러)
# ============================
def run_auto_repeat_once():
    if f2_mode_var.get() == "manual":
        start_on_enter(pending_only=True)
        return

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not run_startup_strong_precheck():
        stop_all_automation("❌ 자동 반복 시작 전 환경 점검/보정 실패")
        return

    if not focus_reservation_window():
        stop_all_automation("❌ 광명도시공사 창 인식 실패 - 자동 반복 중지")
        return

    status.set(f"🔄 자동 반복 실행 — {now} (주기: {get_repeat_wait_seconds()}초)")
    root.update_idletasks()

    for item in get_tree_items_sorted_by_id():
        if not is_repeat_loop_enabled() or emergency_stop:
            break

        if "done" in tree.item(item)["tags"]:
            continue

        values = tree.item(item)["values"]
        res = {
            "id": values[0],
            "date": values[1],
            "time": values[2],
            "court": int(values[3]),
            "people": int(values[4]),
        }

        status.set(f"[자동 반복] {res['id']}번 예약 시작")
        root.update_idletasks()

        y, m, d = map(int, res["date"].split("-"))
        dx, dy = get_date_position(y, m, d)
        if not safe_sleep(DATE_CLICK_BEFORE_CLICK_DELAY_SEC):
            break
        logged_date_click(res["date"], dx, dy, res["id"])
        if not safe_sleep(calendar_delay_var.get()):
            break

        result = run_reservation(res)

        if result in ("NEXT_RESERVATION", NEXT_RESERVATION_AFTER_ESC):
            status.set(f"{res['id']}번 예약 불가 → 다음으로 이동")
            root.update_idletasks()
            if result == "NEXT_RESERVATION" and not reset_after_reservation():
                status.set("❌ 예약창 정리 실패 - 마우스 입력 없이 자동 실행 중지")
                return
            if (
                result == NEXT_RESERVATION_AFTER_ESC
                and not wait_for_next_reservation_transition()
            ):
                return
            continue

        if result == "STOP":
            break

        tree.item(item, tags=("done",))
        if not reset_after_reservation():
            status.set("❌ 예약창 정리 실패 - 마우스 입력 없이 자동 실행 중지")
            return

    if emergency_stop:
        stop_all_automation("⛔ ESC로 전체 실행 취소됨")
    else:
        status.set("자동 반복 예약 1회 완료")


def get_pending_reservation_count():
    count = 0
    for item in tree.get_children():
        if "done" not in tree.item(item)["tags"]:
            count += 1
    return count


def auto_repeat_tick():
    global next_auto_run_at, auto_repeat_running, added_cooldown_until, auto_repeat_armed, refresh_repeat_enabled, refresh_stop_guard_enabled

    try:
        if pause_requested and (not emergency_stop):
            status.set("⏸ ESC 일시정지 중 - ESC 짧게 재개 / ESC 0.5초 이상 취소")
            root.after(500, auto_repeat_tick)
            return

        if f2_mode_var.get() == "auto":
            if not refresh_repeat_enabled:
                next_auto_run_at = None
                auto_repeat_armed = False
                root.after(500, auto_repeat_tick)
                return

            if emergency_stop:
                stop_all_automation("⛔ ESC로 전체 실행 취소됨")
                next_auto_run_at = None
                root.after(500, auto_repeat_tick)
                return

            stop_dt = get_refresh_stop_datetime()
            if stop_dt is not None and datetime.datetime.now() >= stop_dt:
                refresh_repeat_enabled = False
                auto_repeat_armed = False
                next_auto_run_at = None
                refresh_stop_guard_enabled = False
                auto_repeat_running = True
                try:
                    if not focus_reservation_window():
                        message = "❌ 마지막 새로고침 실패 - 광명도시공사 창 인식 실패, 반복 종료"
                    elif not send_refresh_f5():
                        message = "❌ 마지막 새로고침 실패 - F5 전송 실패, 반복 종료"
                    else:
                        message = "목표 -10분 마지막 새로고침 완료 - 반복 종료"
                    print(
                        f"[REFRESH-LAST] {datetime.datetime.now():%Y-%m-%d %H:%M:%S} "
                        f"scheduled={stop_dt} {message}"
                    )
                    status.set(message)
                finally:
                    auto_repeat_running = False
                root.after(500, auto_repeat_tick)
                return

            refresh_seconds = get_refresh_interval_seconds()
            if next_auto_run_at is None:
                next_auto_run_at = time.time() + refresh_seconds

            now_ts = time.time()
            remaining = int(max(0, next_auto_run_at - now_ts))

            if remaining > 0 and (not auto_repeat_running):
                status.set(f"새로고침 대기 {remaining}초 (간격 {repeat_time_var.get()}초)")

            if (not auto_repeat_running) and now_ts >= next_auto_run_at:
                auto_repeat_running = True
                try:
                    if not focus_reservation_window():
                        refresh_repeat_enabled = False
                        next_auto_run_at = None
                        status.set("❌ 광명도시공사 창 인식 실패 - 새로고침 중지")
                    else:
                        if send_refresh_f5():
                            now = datetime.datetime.now().strftime("%H:%M:%S")
                            status.set(f"새로고침 실행 {now} (다음 {repeat_time_var.get()}초 후)")
                        else:
                            refresh_repeat_enabled = False
                            next_auto_run_at = None
                            status.set("❌ F5 전송 실패 - 새로고침 중지")
                finally:
                    auto_repeat_running = False
                    if refresh_repeat_enabled:
                        next_auto_run_at = time.time() + refresh_seconds

            root.after(500, auto_repeat_tick)
            return

        if not is_auto_repeat_on():
            next_auto_run_at = None
            auto_repeat_armed = False
            root.after(500, auto_repeat_tick)
            return

        if emergency_stop:
            stop_all_automation("⛔ ESC로 전체 실행 취소됨")
            next_auto_run_at = None
            root.after(500, auto_repeat_tick)
            return

        if not auto_repeat_armed:
            status.set("예약반복대기 ON - 전체 예약 시작 버튼 대기")
            root.after(500, auto_repeat_tick)
            return

        repeat_seconds = get_repeat_wait_seconds()

        if next_auto_run_at is None:
            next_auto_run_at = time.time() + repeat_seconds

        now_ts = time.time()

        if added_cooldown_until is not None:
            if now_ts < added_cooldown_until:
                pending = get_pending_reservation_count()
                remain_cd = int(max(0, added_cooldown_until - now_ts))
                status.set(f"예약 추가 후 대기 {remain_cd}초 (미완료 {pending}건)")
                next_auto_run_at = added_cooldown_until
                root.after(500, auto_repeat_tick)
                return
            added_cooldown_until = None

        remaining = int(max(0, next_auto_run_at - now_ts))
        pending = get_pending_reservation_count()

        if pending == 0:
            status.set("예약반복대기 중 - 모든 예약 완료")
            root.after(500, auto_repeat_tick)
            return
        elif remaining > 0 and (not auto_repeat_running):
            status.set(f"예약반복대기 {remaining}초 (미완료 {pending}건)")

        if (not auto_repeat_running) and now_ts >= next_auto_run_at:
            auto_repeat_running = True
            try:
                run_auto_repeat_once()
            finally:
                auto_repeat_running = False
                if not emergency_stop and is_auto_repeat_on() and auto_repeat_armed:
                    next_auto_run_at = time.time() + get_repeat_wait_seconds()

    except Exception as e:
        print("자동 체크 오류:", e)
        next_auto_run_at = time.time() + 5

    root.after(500, auto_repeat_tick)

def stop_all_automation(reason="⛔ 전체 자동 실행 취소"):
    global emergency_stop, auto_repeat_armed, refresh_repeat_enabled, refresh_stop_guard_enabled, pause_requested
    global next_auto_run_at, added_cooldown_until, sync_done_for_target
    global scheduled_sync_armed
    scheduled_sync_armed = False
    emergency_stop = True
    pause_requested = False
    auto_repeat_enabled.set(False)
    auto_on_var.set(False)
    auto_off_var.set(True)
    auto_repeat_armed = False
    refresh_repeat_enabled = False
    refresh_stop_guard_enabled = False
    next_auto_run_at = None
    added_cooldown_until = None
    sync_done_for_target = False
    status.set(reason)


def toggle_pause_resume():
    global pause_requested

    if emergency_stop:
        return

    pause_requested = not pause_requested
    if pause_requested:
        status.set("⏸ ESC 일시정지 - ESC 짧게 재개 / ESC 0.5초 이상 취소")
    else:
        status.set("▶ 일시정지 해제 - 자동 실행 재개")


def on_f5_refresh(event=None):
    """F5로 새로고침 반복 ON/OFF를 전환한다."""
    global next_auto_run_at, emergency_stop, refresh_repeat_enabled, auto_repeat_armed, sync_done_for_target, refresh_stop_guard_enabled, pause_requested

    if f2_mode_var.get() != "auto":
        status.set("F5 새로고침은 F2 자동 모드에서만 동작합니다")
        return "break"

    if refresh_repeat_enabled:
        refresh_repeat_enabled = False
        auto_repeat_armed = False
        sync_done_for_target = False
        refresh_stop_guard_enabled = False
        status.set("F5: 새로고침 반복 OFF")
        return "break"

    emergency_stop = False
    pause_requested = False

    if not focus_reservation_window():
        status.set("❌ 광명도시공사 창을 찾지 못했습니다")
        return "break"

    refresh_repeat_enabled = True
    auto_repeat_armed = True
    sync_done_for_target = False
    stop_dt = get_refresh_stop_datetime()
    if stop_dt is not None and datetime.datetime.now() >= stop_dt:
        refresh_repeat_enabled = False
        auto_repeat_armed = False
        refresh_stop_guard_enabled = False
        next_auto_run_at = None
        status.set("F5: 새로고침 종료 시각(목표 -10분) 경과 - 반복 미시작")
        return "break"
    refresh_stop_guard_enabled = True
    next_auto_run_at = time.time()
    next_auto_run_at = time.time() + get_refresh_interval_seconds()
    status.set(f"F5: 새로고침 반복 ON (간격 {repeat_time_var.get()}초)")
    return "break"


def esc_poll_tick():
    """브라우저에 포커스가 있어도 전체 ESC 정지/취소를 감지한다."""
    try:
        check_esc_hold_runtime()
    except Exception as e:
        print("esc_poll_tick 오류:", e)
    finally:
        root.after(30, esc_poll_tick)

# 반복 폴링 시작
root.after(200, auto_f2_tick)
root.after(500, auto_repeat_tick)
root.after(30, esc_poll_tick)
root.bind_all("<F5>", on_f5_refresh)

# 초기 계산값 반영
auto_calculate_times()

# 메인 루프
root.mainloop()
