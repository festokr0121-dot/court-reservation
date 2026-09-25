import ctypes, sys
import datetime
import time
import os
import json
import threading
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

# PyAutoGUI's default pause is 0.1 seconds after every call. Explicitly
# control timing through the application's delay variables instead.
pyautogui.PAUSE = 0.01
pyautogui.MINIMUM_DURATION = 0

# ============================
# OS 클릭 (저수준 클릭)
# ============================
def os_click(x, y):
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
    for _ in range(3):  # 3회 샘플링
        r, g, b = fast_pixel(x, y)
        r_total += r
        g_total += g
        b_total += b
        time.sleep(0.003)  # 화면 갱신 대기

    return r_total // 3, g_total // 3, b_total // 3


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

    print("✔ 카카오톡 창 활성화 완료")

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
    pyautogui.doubleClick(center_pos)
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

    print("✔ 카카오톡 메시지 전송 완료")


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

def instant_move(x, y):
    ctypes.windll.user32.SetCursorPos(x, y)

def get_hwnd_by_click(x, y):
    instant_move(x, y)
    pyautogui.click()
    pt = POINT(x, y)
    hwnd = ctypes.windll.user32.WindowFromPoint(pt)
    ctypes.windll.user32.SetForegroundWindow(hwnd)
    return hwnd

def get_browser_hwnd_by_click():
    x, y = 807, 248   # 브라우저 탭/타이틀바 좌표
    instant_move(x, y)
    pyautogui.click()
    pt = POINT(x, y)
    hwnd = ctypes.windll.user32.WindowFromPoint(pt)
    ctypes.windll.user32.SetForegroundWindow(hwnd)
    return hwnd

def get_browser_hwnd():
    return ctypes.windll.user32.FindWindowW(None, "광명도시공사")

def focus_reservation_window():
    """Bring the reservation browser window to foreground before automation."""
    hwnd = get_browser_hwnd()
    if hwnd:
        ctypes.windll.user32.SetForegroundWindow(hwnd)
        time.sleep(0.05)
        return True

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
        pyautogui.click(REFRESH_FOCUS_X, REFRESH_FOCUS_Y)
        time.sleep(REFRESH_PRE_F5_DELAY_SEC)
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
def safe_sleep(sec):
    global emergency_stop
    end_time = time.time() + sec
    while time.time() < end_time:
        if emergency_stop:
            return False
        try:
            root.update_idletasks()
            root.update()
        except:
            pass
        time.sleep(0.01)
    return True

def safe_click(x, y):
    if emergency_stop:
        return False
    pyautogui.click(x, y)
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
    if emergency_stop:
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

def close_popup_with_esc():
    """Close popups using ESC without triggering the emergency monitor."""
    global ignore_esc_until
    ignore_esc_until = time.time() + 0.5
    keyboard.send("esc")
    time.sleep(0.05)
    keyboard.send("esc")
    time.sleep(0.05)

def cancel_time_selection_with_fallback():
    """ESC-only cancel for time selection (test mode)."""
    close_popup_with_esc()
    safe_sleep(0.05)

def reset_after_reservation():
    """결제 완료 후 다음 예약이 달력 화면에서 시작되도록 모달을 닫는다."""
    if emergency_stop:
        return False
    cancel_time_selection_with_fallback()
    return safe_sleep(page_delay_var.get())

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

TARGET_COLOR = (62, 74, 140)

# ============================
# 코트 감지 (속도+안정성 절충안: 중앙 1픽셀만 fast_pixel_strong)
# ============================
def detect_court_available(court_num):
    x, y = court_positions[court_num]
    r, g, b = fast_pixel_strong(x, y)  # 중앙 1픽셀만 사용
    return color_close(r, g, b, TARGET_COLOR, tol=10)

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
DEFAULT_SYNC_OFFSET_MIN = -10
DEFAULT_REFRESH_STOP_OFFSET_MIN = -10


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

    try:
        stop_offset_min = int(refresh_stop_offset_var.get())
    except:
        stop_offset_min = DEFAULT_REFRESH_STOP_OFFSET_MIN

    return target_dt + datetime.timedelta(minutes=stop_offset_min)

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
def wait_for_window(x, y, timeout=0.6):
    target_r, target_g, target_b = 56, 89, 153
    start = time.time()
    while time.time() - start < timeout:
        r, g, b = fast_pixel_strong(x, y)
        if abs(r - target_r) < 6 and abs(g - target_g) < 6 and abs(b - target_b) < 6:
            return True
        time.sleep(0.01)
    return False

def is_time_window_open():
    r, g, b = fast_pixel_strong(610, 262)
    return (r > 150 and g > 150 and b > 150)


def wait_for_usage_type_window(timeout=0.5):
    return wait_for_window(494, 821, timeout)


def detect_usage_type_selected():
    r, g, b = fast_pixel_strong(529, 545)
    return abs(r - 255) <= 12 and abs(g) <= 12 and abs(b) <= 12


def wait_for_usage_type_selected(timeout=0.5):
    start = time.time()
    while time.time() - start < timeout:
        if detect_usage_type_selected():
            return True
        if emergency_stop:
            return False
        time.sleep(0.01)
    return False


def detect_people_input_completed():
    r, g, b = fast_pixel_strong(496, 775)
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
        time.sleep(0.01)
    return False


def page_down_and_fix(date_str):
    time.sleep(0.05)

    # 회색 감지 → 날짜 클릭 진행
    r, g, b = fast_pixel_strong(91, 894)
    if abs(r-95) < 5 and abs(g-95) < 5 and abs(b-95) < 5:
        print("회색 감지 → 날짜 클릭으로 진행")

    y, m, d = map(int, date_str.split("-"))
    dx, dy = get_date_position(y, m, d)

    time.sleep(0.1)
    pyautogui.click(dx, dy)

    time.sleep(calendar_delay_var.get())

# ============================
# 색상 비교 헬퍼 (안정화 버전)
# ============================
def color_close(r, g, b, target, tol=8):
    return (
        abs(r - target[0]) <= tol and
        abs(g - target[1]) <= tol and
        abs(b - target[2]) <= tol
    )

# ============================
# 준비 색상 감지 함수
# ============================
def check_ready_color():
    x, y = 427, 739
    r, g, b = pyautogui.pixel(x, y)
    print(f"준비색상: R={r}, G={g}, B={b}")
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
    target = (160, 189, 237)

    def area_match(x, y):
        count = 0
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                r, g, b = fast_pixel_strong(x+dx, y+dy)
                if abs(r-target[0]) < 12 and abs(g-target[1]) < 12 and abs(b-target[2]) < 12:
                    count += 1
        return count >= 5

    return (
        area_match(632, 190) and
        area_match(580, 260) and
        area_match(700, 350)
    )

def detect_already_reserved():
    x, y = 631, 190
    r, g, b = fast_pixel_strong(x, y)
    return abs(r-160) < 12 and abs(g-189) < 12 and abs(b-237) < 12

def detect_full_agree_popup():
    x, y = 305, 819
    r, g, b = fast_pixel_strong(x, y)
    return abs(r-248) < 12 and abs(g-94) < 12 and abs(b-19) < 12

def wait_payment_result(timeout=2.0):
    start = time.time()
    while time.time() - start < timeout:
        if detect_already_reserved():
            return "ALREADY_RESERVED"
        if detect_full_agree_popup():
            return "FULL_AGREE"
        time.sleep(0.01)
    return "UNKNOWN"

# ============================
# 예약 실행
# ============================
def run_reservation(res):
    global emergency_stop
    status.set(f"{res['id']}번 예약 실행 중...")

    state = STATE_TIME

    while state != STATE_DONE and not emergency_stop:

        # ============================
        # 이미 예약됨 팝업 감지
        # ============================
        if detect_already_reserved():
            print("⚠ 이미 예약됨 팝업 감지 → 다음 예약으로 이동")
            safe_click(631, 190)
            close_popup_with_esc()
            return "NEXT_RESERVATION"

        # ============================
        # 1) 시간 선택 단계
        # ============================
        if state == STATE_TIME:

            time_window_opened = False
            for _ in range(5):
                if wait_for_window(478, 812, timeout=0.3) or is_time_window_open():
                    time_window_opened = True
                    break
                time.sleep(0.05)

            if not time_window_opened:
                print("❌ 시간창 미오픈(예약불가 날짜 가능성) → 다음 예약으로 이동")
                cancel_time_selection_with_fallback()
                return "NEXT_RESERVATION"

            selected_pos = None
            selected_source = None

            # 1) 기본 시간표 좌표 먼저 정밀 감지
            default_pos = time_positions.get(res["time"])
            if default_pos:
                tx, ty = default_pos
                r, g, b = fast_pixel_strong(tx, ty)
                if color_close(r, g, b, TARGET_COLOR, tol=15):
                    selected_pos = (tx, ty)
                    selected_source = "default"

            # 2) 기본 실패 시, 백업 시간표 좌표는 빠르게 1회 감지
            if selected_pos is None:
                backup_pos = short_time_positions.get(res["time"])
                if backup_pos:
                    tx, ty = backup_pos
                    r, g, b = fast_pixel(tx, ty)
                    if color_close(r, g, b, TARGET_COLOR, tol=18):
                        selected_pos = (tx, ty)
                        selected_source = "backup"

            if selected_pos is None:
                print("❌ 기본/백업 시간칸 모두 감지 실패 → 백업 취소 후 다음 예약")
                cancel_time_selection_with_fallback()
                return "NEXT_RESERVATION"

            tx, ty = selected_pos
            safe_click(tx, ty)
            if selected_source == "backup":
                safe_sleep(0.2)
                safe_click(520, 760)
            else:
                safe_click(520, 810)
            wait_for_window(495, 852, timeout=0.5)

            state = STATE_COURT

        # ============================
        # 2) 코트 선택 단계
        # ============================
        elif state == STATE_COURT:

            wait_for_window(495, 852, timeout=0.5)

            # 완전 오름차순 순환 검색
            target_court = find_available_court(res["court"])

            if not target_court:
                print("❌ 코트 없음 → 다음 예약")
                safe_click(411, 807)
                return "NEXT_RESERVATION"

            cx, cy = court_positions[target_court]
            safe_click(cx, cy)
            safe_sleep(court_delay_var.get())

            safe_click(532, 856)
            wait_for_window(494, 821, timeout=0.5)

            state = STATE_TYPE

        # ============================
        # 3) 이용유형 선택
        # ============================
        elif state == STATE_TYPE:

            # 창 열림 좌표는 클릭하지 않고 색상으로만 감지한다.
            if not wait_for_usage_type_window(timeout=0.5):
                print("❌ 이용유형 창 열림 색상 감지 실패")
                return "NEXT_RESERVATION"

            safe_click(529, 545)

            if not wait_for_usage_type_selected(timeout=0.5):
                print("❌ 이용유형 선택 색상 변화 감지 실패")
                return "NEXT_RESERVATION"

            safe_click(494, 821)

            state = STATE_PEOPLE

        # ============================
        # 4) 인원 선택 (최종 안정화)
        # ============================
        elif state == STATE_PEOPLE:

            # 창 열림 여부는 좌표 색상으로만 확인한다.
            if not wait_for_window(493, 834, timeout=0.5):
                print("❌ 인원선택 창 열림 색상 감지 실패")
                return "NEXT_RESERVATION"

            safe_click(453, 520)
            safe_sleep(0.05)

            safe_press("backspace")
            safe_press(str(res["people"]))
            safe_sleep(0.05)

            safe_press("enter")

            if not wait_for_people_input_completed(timeout=0.5):
                print("❌ 인원 입력 색상 변화 감지 실패")
                return "NEXT_RESERVATION"

            safe_click(493, 834)
            wait_for_window(492, 899, timeout=0.5)

            state = STATE_PAYMENT

        # ============================
        # 5) 결제 단계
        # ============================
        elif state == STATE_PAYMENT:

            wait_for_window(492, 899, timeout=0.5)

            # 대기 모드: 약관/카드 선택만 하고 결제창 닫은 뒤 다음 예약으로 이동
            if mode_var.get() == "wait":
                safe_click(266, 569)
                safe_click(312, 745)
                safe_click(682, 125)
                return "NEXT_RESERVATION"

            # 결제 모드: 결제 클릭 후 정상/이미예약완료 분기 처리
            if detect_already_reserved():
                print("⚠ 결제단계에서 이미 예약됨 → 다음 예약")
                safe_click(631, 190)
                close_popup_with_esc()
                return "NEXT_RESERVATION"

            safe_click(266, 569)
            safe_click(312, 745)
            safe_click(530, 901)

            pay_result = wait_payment_result(timeout=2.0)

            if pay_result == "ALREADY_RESERVED":
                print("⚠ 결제 클릭 후 이미 예약됨 팝업 감지 → 다음 예약")
                safe_click(631, 190)
                close_popup_with_esc()
                return "NEXT_RESERVATION"

            if pay_result == "FULL_AGREE":
                safe_click(807, 247)

            status.set(f"{res['id']}번 예약 완료!")

            state = STATE_DONE

    if emergency_stop:
        return "STOP"

    return "DONE"

# ============================
# 선택 예약 실행
# ============================
def run_selected():
    global emergency_stop, running

    if running:
        return
    running = True
    emergency_stop = False

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
        page_down_and_fix(res["date"])

    status.set(f"{res['id']}번 예약 시작 ({res['date']} {res['time']})")
    result = run_reservation(res)

    if result == "NEXT_RESERVATION":
        status.set(f"{res['id']}번 예약 불가")
        running = False
        return

    if emergency_stop:
        status.set("⚠ ESC로 즉시 정지됨")
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
        time.sleep(0.1)
    return False


def start_on_enter(event=None, from_auto=False, from_f2=False):
    global emergency_stop, auto_repeat_armed, next_auto_run_at, refresh_repeat_enabled, sync_done_for_target, refresh_stop_guard_enabled
    emergency_stop = False
    auto_repeat_armed = False

    # Manual full-start runs one refresh immediately for quick verification.
    if not from_auto and not from_f2:
        if focus_reservation_window() and send_refresh_f5():
            status.set("시작 확인용 새로고침 1회 실행 완료")

            # In F2 auto mode, also arm periodic refresh automatically.
            if f2_mode_var.get() == "auto":
                refresh_repeat_enabled = True
                auto_repeat_armed = True
                sync_done_for_target = False
                stop_dt = get_refresh_stop_datetime()
                refresh_stop_guard_enabled = stop_dt is not None and stop_dt > datetime.datetime.now()
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
    if from_auto:

        # 최대 5회 재시도 루프
        for attempt in range(5):

            if emergency_stop:
                status.set("⚠ ESC로 취소됨")
                return

            status.set(f"자동 실행 준비 중... ({attempt+1}/5)")

            # 1) 페이지 클릭
            pyautogui.click(235, 330)
            time.sleep(0.2)


            # 3) 준비색상 감지 (5회 제한)
            if check_ready_color_limited(5):
                # 준비색상 성공 → 다음 단계로 진행
                break

            # 4) 실패 → 재시도
            status.set("⚠ 준비 색상 감지 실패 — 재시도 중...")
            time.sleep(0.3)

        else:
            # 5회 모두 실패 → 종료
            status.set("❌ 준비 색상 5회 실패 — 자동 실행 중단")
            emergency_stop = True
            return

        # 준비색상 성공 후 다음 단계
        pyautogui.click(659, 686)
        time.sleep(0.3)

        pyautogui.press("pagedown")
        time.sleep(0.2)

        from_auto = False
        from_f2 = True

    # ============================
    # 시간 저장
    # ============================
    auto_calculate_times()
    save_time_settings()

    # ============================
    # 예약 실행 루프
    # ============================
    items = get_tree_items_sorted_by_datetime()
    for index, item in enumerate(items):

        if emergency_stop:
            status.set("⚠ ESC로 취소됨")
            return

        values = tree.item(item)["values"]

        res = {
            "id": values[0],
            "date": values[1],
            "time": values[2],
            "court": int(values[3]),
            "people": int(values[4]),
        }

        status.set(f"{res['id']}번 예약 시작 ({res['date']} {res['time']})")

        if calendar_click_mode.get() == "auto":
            page_down_and_fix(res["date"])

        result = run_reservation(res)

        if result == "NEXT_RESERVATION":
            if index < len(items) - 1:
                reset_after_reservation()
            continue

        if result == "STOP":
            return

        tree.item(item, tags=("done",))

        if index < len(items) - 1:
            reset_after_reservation()

    status.set("전체 예약 완료!")

    if f2_mode_var.get() == "manual" and is_auto_repeat_on() and not emergency_stop:
        repeat_seconds = get_repeat_wait_seconds()
        auto_repeat_armed = True
        next_auto_run_at = time.time() + repeat_seconds
    elif f2_mode_var.get() == "auto" and refresh_repeat_enabled and not emergency_stop:
        repeat_seconds = get_repeat_wait_seconds()
        auto_repeat_armed = True
        next_auto_run_at = time.time() + repeat_seconds


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
        auto_repeat_armed = False

    if f2_mode_var.get() == "manual" and is_auto_repeat_on():
        status.set(f"예약 {added_count}건 추가됨 - 전체 예약 시작 버튼을 눌러주세요")
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
).grid(row=12, column=0, columnspan=3, padx=2, pady=2)

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

def on_close():
    global emergency_stop
    emergency_stop = True
    try:
        save_time_settings()
        save_repeat_time()
        save_ui_state()
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

status = tk.StringVar(value="대기 중")

click_x_var = tk.StringVar(value="800")
click_y_var = tk.StringVar(value="250")

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
ttk.Label(settings_frame, text="-10분전까지 실행").grid(row=3, column=3, sticky="w")

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

tk.Button(root, text="날짜 선택해제", command=clear_date_selection, bg="#E0E0E0", activebackground="#D5D5D5", fg="black", font=("맑은 고딕", 9)).grid(row=10, column=0)
tk.Button(root, text="예약 추가", command=add_reservation, bg="#64B5F6", activebackground="#42A5F5", fg="black", font=("맑은 고딕", 9)).grid(row=10, column=2)
tk.Button(root, text="예약 수정", command=modify_reservation, bg="#FFB74D", activebackground="#FFA726", fg="black", font=("맑은 고딕", 9)).grid(row=10, column=3)
tk.Button(root, text="예약 삭제", command=delete_reservation, bg="#E57373", activebackground="#EF5350", fg="white", font=("맑은 고딕", 9)).grid(row=10, column=4)

# 기본 조건: 날짜/시간은 자동 선택하지 않고 사용자가 직접 선택한다.
fill_date_list_until_day(17)
date_listbox.selection_clear(0, tk.END)
time_listbox.selection_clear(0, tk.END)

columns = ("id", "date", "time", "court", "people")
tree = ttk.Treeview(root, columns=columns, show="headings", height=6, selectmode="extended")
tree.grid(row=11, column=0, columnspan=5)
tree.tag_configure("done", background="#c8f7c5")

def get_tree_items_sorted_by_datetime():
    """Return tree items sorted by reservation date/time, then ID."""
    def sort_key(item_id):
        values = tree.item(item_id)["values"]
        date_text = str(values[1]).strip()
        time_text = str(values[2]).strip()

        try:
            dt = datetime.datetime.strptime(f"{date_text} {time_text}", "%Y-%m-%d %H:%M")
        except Exception:
            dt = datetime.datetime.max

        try:
            rid = int(values[0])
        except Exception:
            rid = 999999

        return (dt, rid)

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
        if f2_mode_var.get() == "auto":
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

# 최초 실행부터 빠름 프로필을 사용한다.
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

# 프로필 저장
def set_profile_fast():
    click_delay_var.set(0.01)
    press_delay_var.set(0.01)
    page_delay_var.set(0.05)
    pay_delay_var.set(0.05)
    calendar_delay_var.set(0.05)
    court_delay_var.set(0.05)

    status.set("빠름 모드 적용됨")
    with open(settings_path("profile_settings.txt"), "w") as f:
        f.write("FAST")

def set_profile_normal():
    click_delay_var.set(0.08)
    press_delay_var.set(0.06)
    page_delay_var.set(0.25)
    pay_delay_var.set(0.18)
    calendar_delay_var.set(0.15)
    court_delay_var.set(0.15)
    status.set("보통 모드 적용됨")
    with open(settings_path("profile_settings.txt"), "w") as f:
        f.write("NORMAL")

def set_profile_safe():
    click_delay_var.set(0.15)
    press_delay_var.set(0.10)
    page_delay_var.set(0.50)
    pay_delay_var.set(0.30)
    calendar_delay_var.set(0.20)
    court_delay_var.set(0.20)
    status.set("안정 모드 적용됨")
    with open(settings_path("profile_settings.txt"), "w") as f:
        f.write("SAFE")

tk.Button(root, text="빠름", command=set_profile_fast, bg="#E57373", activebackground="#EF5350", fg="white", font=("맑은 고딕", 9)).grid(row=24, column=0)
tk.Button(root, text="보통", command=set_profile_normal, bg="#FFF176", activebackground="#FFEE58", fg="black", font=("맑은 고딕", 9)).grid(row=24, column=1)
tk.Button(root, text="안정", command=set_profile_safe, bg="#81C784", activebackground="#66BB6A", fg="black", font=("맑은 고딕", 9)).grid(row=24, column=2)

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
    }
    with open(UI_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

def load_ui_state():
    if not os.path.exists(UI_STATE_FILE):
        return

    with open(UI_STATE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

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
refresh_stop_guard_enabled = False
last_auto_f2_trigger = ""
added_cooldown_until = None
esc_pressed_at = None
esc_stop_triggered = False
esc_hold_threshold_sec = 0.8

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
    auto_repeat_armed = False
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
    if not os.path.exists(settings_path("profile_settings.txt")):
        set_profile_fast()
        return
    with open(settings_path("profile_settings.txt"), "r") as f:
        mode = f.read().strip()
    if mode == "FAST":
        set_profile_fast()
    elif mode == "NORMAL":
        set_profile_normal()
    elif mode == "SAFE":
        set_profile_safe()
    else:
        set_profile_fast()

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
apply_f2_mode_rules(update_status=False)

# 실행 시 창을 항상 우측 상단에 배치
place_window_top_right()

# ============================
# 자동 반복 기능 (메인 루프 스케줄러)
# ============================
def run_auto_repeat_once():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not focus_reservation_window():
        stop_all_automation("❌ 광명도시공사 창 인식 실패 - 자동 반복 중지")
        return

    status.set(f"🔄 자동 반복 실행 — {now} (주기: {get_repeat_wait_seconds()}초)")
    root.update_idletasks()

    for item in get_tree_items_sorted_by_datetime():
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
        time.sleep(0.1)
        pyautogui.click(dx, dy)
        time.sleep(calendar_delay_var.get())

        result = run_reservation(res)

        if result == "NEXT_RESERVATION":
            status.set(f"{res['id']}번 예약 불가 → 다음으로 이동")
            root.update_idletasks()
            reset_after_reservation()
            continue

        if result == "STOP":
            break

        tree.item(item, tags=("done",))
        reset_after_reservation()

    if emergency_stop:
        stop_all_automation("⚠ ESC로 즉시 정지됨")
    else:
        status.set("자동 반복 예약 1회 완료")


def get_pending_reservation_count():
    count = 0
    for item in tree.get_children():
        if "done" not in tree.item(item)["tags"]:
            count += 1
    return count


def auto_repeat_tick():
    global next_auto_run_at, auto_repeat_running, added_cooldown_until, auto_repeat_armed, refresh_repeat_enabled, sync_done_for_target, refresh_stop_guard_enabled

    try:
        if f2_mode_var.get() == "auto":
            if not refresh_repeat_enabled:
                next_auto_run_at = None
                auto_repeat_armed = False
                root.after(500, auto_repeat_tick)
                return

            if emergency_stop:
                stop_all_automation("⚠ ESC로 즉시 정지됨")
                next_auto_run_at = None
                root.after(500, auto_repeat_tick)
                return

            stop_dt = get_refresh_stop_datetime()
            if refresh_stop_guard_enabled and stop_dt is not None and datetime.datetime.now() >= stop_dt:
                refresh_repeat_enabled = False
                auto_repeat_armed = False
                next_auto_run_at = None
                sync_done_for_target = False
                refresh_stop_guard_enabled = False
                status.set("새로고침 종료 시각 도달 - 자동 반복 중지")
                root.after(500, auto_repeat_tick)
                return

            sync_dt = get_sync_datetime()
            if (not sync_done_for_target) and sync_dt is not None and datetime.datetime.now() >= sync_dt:
                if sync_pc_time():
                    status.set(f"동기화 시각 실행 완료 {datetime.datetime.now().strftime('%H:%M:%S')}")
                else:
                    status.set("동기화 시각 실행 실패(w32tm)")
                sync_done_for_target = True

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
            stop_all_automation("⚠ ESC로 즉시 정지됨")
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
        elif remaining > 0 and (not auto_repeat_running):
            status.set(f"예약반복대기 {remaining}초 (미완료 {pending}건)")

        if (not auto_repeat_running) and now_ts >= next_auto_run_at:
            auto_repeat_running = True
            try:
                run_auto_repeat_once()
            finally:
                auto_repeat_running = False
                next_auto_run_at = time.time() + repeat_seconds

    except Exception as e:
        print("자동 체크 오류:", e)
        next_auto_run_at = time.time() + 5

    root.after(500, auto_repeat_tick)

def stop_all_automation(reason="⚠ ESC 감지 — 모든 자동 실행 정지"):
    global emergency_stop, auto_repeat_armed, refresh_repeat_enabled, refresh_stop_guard_enabled
    emergency_stop = True
    auto_repeat_enabled.set(False)
    auto_on_var.set(False)
    auto_off_var.set(True)
    auto_repeat_armed = False
    refresh_repeat_enabled = False
    refresh_stop_guard_enabled = False
    status.set(reason)


def on_f5_refresh(event=None):
    """F5로 새로고침 반복 ON/OFF를 전환한다."""
    global next_auto_run_at, emergency_stop, refresh_repeat_enabled, auto_repeat_armed, sync_done_for_target, refresh_stop_guard_enabled

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

    if not focus_reservation_window():
        status.set("❌ 광명도시공사 창을 찾지 못했습니다")
        return "break"

    refresh_repeat_enabled = True
    auto_repeat_armed = True
    sync_done_for_target = False
    stop_dt = get_refresh_stop_datetime()
    refresh_stop_guard_enabled = stop_dt is not None and stop_dt > datetime.datetime.now()
    next_auto_run_at = time.time()
    next_auto_run_at = time.time() + get_refresh_interval_seconds()
    status.set(f"F5: 새로고침 반복 ON (간격 {repeat_time_var.get()}초)")
    return "break"


def check_escape_hold():
    global esc_stop_triggered
    if esc_pressed_at is None or esc_stop_triggered:
        return

    if time.time() - esc_pressed_at >= esc_hold_threshold_sec:
        esc_stop_triggered = True
        stop_all_automation("⛔ ESC 길게 눌림 - 모든 자동 실행 정지")
        return

    root.after(30, check_escape_hold)


def on_escape_press(event=None):
    global esc_pressed_at, esc_stop_triggered
    if time.time() < ignore_esc_until:
        return

    if esc_pressed_at is None:
        esc_pressed_at = time.time()
        esc_stop_triggered = False
        root.after(30, check_escape_hold)


def on_escape_release(event=None):
    global esc_pressed_at, esc_stop_triggered
    esc_pressed_at = None
    esc_stop_triggered = False


def esc_poll_tick():
    """Global ESC hold detection that works even when browser has focus."""
    global esc_pressed_at, esc_stop_triggered

    try:
        if time.time() < ignore_esc_until:
            esc_pressed_at = None
            esc_stop_triggered = False
            root.after(30, esc_poll_tick)
            return

        if keyboard.is_pressed("esc"):
            if esc_pressed_at is None:
                esc_pressed_at = time.time()
                esc_stop_triggered = False
            elif (not esc_stop_triggered) and (time.time() - esc_pressed_at >= esc_hold_threshold_sec):
                esc_stop_triggered = True
                stop_all_automation("⛔ ESC 길게 눌림 - 모든 자동 실행 정지")
        else:
            esc_pressed_at = None
            esc_stop_triggered = False
    except Exception as e:
        print("esc_poll_tick 오류:", e)

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
