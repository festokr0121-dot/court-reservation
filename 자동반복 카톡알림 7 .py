###############################################
# 블럭 1 — 엔진 전체 + 중앙관리 + 모든 기능
###############################################

import ctypes, sys
import datetime
import time
import os
import threading
import pyautogui
import keyboard

import tkinter as tk
from tkinter import ttk

LAST_FILE = "last_settings.txt"

def save_last_settings(time_str, court, people):
    with open(LAST_FILE, "w", encoding="utf-8") as f:
        f.write(f"{time_str},{court},{people}")

def save_last_settings():
    try:
        sel = time_listbox.curselection()
        last_time = time_listbox.get(sel[0]) if sel else ""
    except:
        last_time = ""

    last_court = court_var.get()
    last_people = people_var.get()

    last_hour = hour_var.get()
    last_min = min_var.get()
    last_sec = sec_var.get()

    repeat_sec = auto_repeat_sec_var.get()

    with open(LAST_FILE, "w", encoding="utf-8") as f:
        repeat_flag = "1" if auto_repeat_enabled.get() else "0"
        f.write(f"{last_time},{last_court},{last_people},{last_hour},{last_min},{last_sec},{repeat_sec},{repeat_flag}")


############################################################
# 전역 변수 (반드시 최상단)
############################################################
emergency_stop = False
running = False
current_thread = None   # 🔥 현재 예약 실행 스레드 저장용
current_thread = None
auto_repeat_started = False  # 🔥 자동반복 기준점 플래그

click_delay_var = None
press_delay_var = None
page_delay_var = None
calendar_delay_var = None
court_delay_var = None
pay_delay_var = None

############################################################
# 중앙관리 테이블 (좌표 / 색상 / 딜레이)
############################################################

PIXEL_POS = {
    "ready_color": (427, 739),
    "payment_blue": (492, 899),
    "popup_check": (632, 190),
    "loading_check": (58, 12),
    "time_window_check": (610, 262),

    "btn_next_time": (526, 813),
    "btn_next_court": (532, 856),
    "btn_next_type": (537, 822),
    "btn_next_people": (534, 836),

    "btn_pay1": (264, 576),
    "btn_pay2": (310, 751),
    "btn_pay3": (404, 901),
    "btn_pay_confirm": (902, 972),

    "people_input": (446, 527),
}

PIXEL_COLOR = {
    "ready_color": (207, 10, 103),
    "payment_blue": (56, 89, 153),
    "popup_color": (160, 189, 237),
    "target_time_color": (62, 74, 140),
}

DELAY = {
    "click": 0.01,
    "press": 0.01,
    "page": 0.05,
    "calendar": 0.05,
    "court": 0.05,
    "payment": 0.05,
}

############################################################
# 브라우저 핸들 관련 함수 (블럭 1로 이동)
############################################################

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

def instant_move(x, y):
    ctypes.windll.user32.SetCursorPos(x, y)

def get_browser_hwnd_by_click():
    x, y = 807, 248
    instant_move(x, y)
    pt = POINT(x, y)
    hwnd = ctypes.windll.user32.WindowFromPoint(pt)
    ctypes.windll.user32.SetForegroundWindow(hwnd)
    return hwnd

def get_browser_hwnd():
    return ctypes.windll.user32.FindWindowW(None, "광명도시공사")

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

def on_escape(event=None):
    global emergency_stop, running, current_thread
    emergency_stop = True
    running = False

    kill_thread(current_thread)

    print("⚠ ESC 감지 → 즉시 중단")
    status.set("⚠ ESC로 즉시 중단됨")


############################################################
# 픽셀 엔진
############################################################

def fast_pixel(x, y):
    hdc = ctypes.windll.user32.GetDC(0)
    color = ctypes.windll.gdi32.GetPixel(hdc, x, y)
    ctypes.windll.user32.ReleaseDC(0, hdc)
    r = color & 0xff
    g = (color >> 8) & 0xff
    b = (color >> 16) & 0xff
    return r, g, b

def fast_pixel_strong(x, y):
    r_total = g_total = b_total = 0
    for _ in range(2):
        r, g, b = fast_pixel(x, y)
        r_total += r
        g_total += g
        b_total += b
        time.sleep(0.002)
    return r_total // 2, g_total // 2, b_total // 2

def color_close(r, g, b, target, tol=15):
    return (
        abs(r - target[0]) <= tol and
        abs(g - target[1]) <= tol and
        abs(b - target[2]) <= tol
    )

def click_date(date_str):
    if date_str not in date_positions:
        print(f"날짜 좌표 없음: {date_str}")
        return False

    x, y = date_positions[date_str]
    fast_click(x, y)
    time.sleep(DELAY["calendar"])
    return True

def click_time(time_str):
    if time_str not in time_positions:
        print(f"시간 좌표 없음: {time_str}")
        return False

    x, y = time_positions[time_str]
    fast_click(x, y)
    time.sleep(DELAY["page"])
    return True


def click_court(court_num):
    if court_num not in court_positions:
        print(f"코트 좌표 없음: {court_num}")
        return False

    x, y = court_positions[court_num]
    fast_click(x, y)
    time.sleep(DELAY["court"])
    return True


############################################################
# 화면 감지 엔진
############################################################

def wait_for_payment_window_strong(timeout=0.1):
    targets = [
        (PIXEL_POS["ready_color"], PIXEL_COLOR["ready_color"]),
        (PIXEL_POS["payment_blue"], PIXEL_COLOR["payment_blue"]),
    ]

    start = time.time()
    while time.time() - start < timeout:
        ok = 0
        for (x, y), target_color in targets:
            r, g, b = fast_pixel_strong(x, y)
            if color_close(r, g, b, target_color, tol=15):
                ok += 1
        if ok == len(targets):
            return True
        time.sleep(0.01)
    return False

############################################################
# 팝업 감지
############################################################

def detect_already_reserved():
    x, y = PIXEL_POS["popup_check"]
    r, g, b = fast_pixel_strong(x, y)
    return color_close(r, g, b, PIXEL_COLOR["popup_color"], tol=12)

############################################################
# 안전 클릭 / 입력
############################################################

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

    SAFE_X, SAFE_Y = 437, 996

    # ESC 체크
    if emergency_stop:
        return False

    pyautogui.moveTo(SAFE_X, SAFE_Y)
    if not safe_sleep(0.02):
        return False

    # ESC 체크
    if emergency_stop:
        return False

    pyautogui.moveTo(x, y)
    if emergency_stop:
        return False

    pyautogui.click()

    pyautogui.moveTo(SAFE_X, SAFE_Y)

    return safe_sleep(click_delay_var.get())


def safe_press(key):
    if emergency_stop:
        return False

    SAFE_X, SAFE_Y = 437, 996

    if emergency_stop:
        return False

    pyautogui.press(key)

    if emergency_stop:
        return False

    pyautogui.moveTo(SAFE_X, SAFE_Y)

    return safe_sleep(press_delay_var.get())


############################################################
# 달력 관련 함수 (블럭 1로 이동)
############################################################

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

def page_down_and_fix(date_str):
    time.sleep(0.05)
    y, m, d = map(int, date_str.split("-"))
    dx, dy = get_date_position(y, m, d)
    pyautogui.moveTo(dx, dy)
    time.sleep(0.05)

    ok = False
    for _ in range(3):
        r, g, b = fast_pixel_strong(dx, dy)
        if r > 230 and g > 230 and b > 230:
            ok = True
            break
        if r > 230 and g > 200 and b < 160:
            ok = True
            break
        if 150 < r < 210 and 150 < g < 210 and 150 < b < 210:
            return False
        time.sleep(0.03)

    pyautogui.doubleClick(dx, dy)
    time.sleep(DELAY["calendar"])
    return True

############################################################
# 코트 관련 함수 (블럭 1로 이동)
############################################################

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

court_positions = {
    1: (279, 514), 2: (384, 515), 3: (484, 517), 4: (587, 513), 5: (692, 515),
    6: (282, 613), 7: (383, 614), 8: (485, 616), 9: (589, 620), 10: (689, 620),
    11: (282, 713), 12: (380, 715), 13: (484, 714),
}

TARGET_COLOR = (62, 74, 140)

def detect_court_available(court_num):
    x, y = court_positions[court_num]
    r, g, b = fast_pixel_strong(x, y)
    return color_close(r, g, b, TARGET_COLOR, tol=20)

def find_available_court(start_court):
    for c in range(start_court, 14):
        if detect_court_available(c):
            return c
    for c in range(1, start_court):
        if detect_court_available(c):
            return c
    return None

############################################################
# F2 시간 관련 함수 (블럭 1로 이동)
############################################################

TIME_FILE = "time_settings.txt"

def auto_calculate_times():
    try:
        h = int(hour_var.get())
        m = int(min_var.get())
    except:
        return
    sync_time = datetime.datetime(2024, 1, 1, h, m) - datetime.timedelta(minutes=5)
    sync_hour_var.set(sync_time.hour)
    sync_min_var.set(sync_time.minute)

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
    start = time.time()
    while time.time() - start < timeout:

        if emergency_stop:
            return False

        r, g, b = fast_pixel_strong(x, y)
        if abs(r - 56) < 6 and abs(g - 89) < 6 and abs(b - 153) < 6:
            return True

        if not safe_sleep(0.01):
            return False

    return False


import ctypes

def kill_thread(thread):
    if thread is None:
        return
    tid = thread.ident
    if tid is None:
        return
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
        ctypes.c_long(tid),
        ctypes.py_object(SystemExit)
    )
    if res == 0:
        print("❌ 스레드 종료 실패")
    elif res > 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), None)
        print("❌ 스레드 종료 오류 (복구)")

# ============================
# 🔥 선택 예약 실행 스레드 래퍼 (여기에 추가)
# ============================
def run_selected_thread():
    global current_thread
    if running:
        return
    current_thread = threading.Thread(target=run_selected, daemon=True)
    current_thread.start()


############################################################
# 예약 실행 엔진 (run_reservation)
############################################################

STATE_TIME = 1
STATE_COURT = 2
STATE_TYPE = 3
STATE_PEOPLE = 4
STATE_PAYMENT = 5
STATE_DONE = 6

def run_reservation(res):
    global emergency_stop
    status.set(f"{res['id']}번 예약 실행 중...")

    state = STATE_TIME

    while state != STATE_DONE and not emergency_stop:

        # 🔥 ESC 즉시 중단
        if emergency_stop:
            return "STOP"
        
        # ============================
        # 이미 예약됨 팝업 감지
        # ============================
        if detect_already_reserved():
            print("⚠ 이미 예약됨 팝업 감지 → 다음 예약으로 이동")
            keyboard.press("esc"); time.sleep(0.05)
            keyboard.press("esc"); time.sleep(0.05)
            safe_click(411, 807)
            return "NEXT_RESERVATION"

        # ============================
        # 1) 시간 선택 단계
        # ============================
        if state == STATE_TIME:

            for _ in range(5):
                if wait_for_window(478, 812, timeout=0.3):
                    break
                time.sleep(0.05)

            tx, ty = time_positions[res["time"]]

            r, g, b = fast_pixel_strong(tx, ty)
            if not color_close(r, g, b, TARGET_COLOR, tol=15):
                print("❌ 시간칸 감지 실패 → 다음 예약")
                safe_click(411, 807)
                return "NEXT_RESERVATION"

            safe_click(tx, ty)
            safe_click(526, 813)
            wait_for_window(495, 852, timeout=0.5)

            state = STATE_COURT

        # ============================
        # 2) 코트 선택 단계
        # ============================
        elif state == STATE_COURT:

            wait_for_window(495, 852, timeout=0.5)

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

            safe_click(637, 635)
            wait_for_window(494, 821, timeout=0.5)

            safe_click(537, 822)
            wait_for_window(610, 262, timeout=0.5)

            state = STATE_PEOPLE

        # ============================
        # 4) 인원 선택 (벤치마킹 적용)
        # ============================
        elif state == STATE_PEOPLE:

            safe_click(446, 527)
            time.sleep(0.05)

            safe_press("backspace")
            safe_press(str(res["people"]))
            time.sleep(0.05)

            safe_click(534, 836)

            # 🔥 벤치마킹 핵심: 인원 입력 후 결제창 로딩을 여기서만 감지
            wait_for_window(492, 899, timeout=0.5)

            state = STATE_PAYMENT

        # ============================
        # 5) 결제 단계 (대기 제거)
        # ============================
        elif state == STATE_PAYMENT:

            # 🔥 결제창은 이미 STATE_PEOPLE에서 감지됨 → 여기서는 기다리지 않음

            if detect_already_reserved():
                print("⚠ 결제단계에서 이미 예약됨 → 다음 예약")
                keyboard.press("esc"); time.sleep(0.05)
                keyboard.press("esc"); time.sleep(0.05)
                return "NEXT_RESERVATION"

            safe_click(264, 576)
            safe_click(310, 751)
            safe_click(404, 901)

            status.set(f"{res['id']}번 예약 완료!")
            safe_click(902, 972)

            state = STATE_DONE

    if emergency_stop:
        return "STOP"

    return "DONE"




############################################################
# 선택 예약 실행 (run_selected)
############################################################

def run_selected():
    global emergency_stop, running

    # 🔥 ESC 누르면 함수 시작 즉시 전체 중단
    if emergency_stop:
        running = False
        return "STOP"

    if running:
        return
    running = True
    

    selected = tree.selection()
    if not selected:
        status.set("실행할 예약을 선택하세요")
        running = False
        return

    item = selected[0]

    if "done" in tree.item(item, "tags"):
        status.set("이미 완료된 예약입니다")
        running = False
        return

    values = tree.item(item)["values"]

    res = {
        "id": values[0],
        "date": values[1],
        "time": values[2],
        "court": int(values[3]),
        "people": int(values[4]),
    }

    # 🔹 예약시간 → time_listbox에서 선택
    time_listbox.selection_clear(0, tk.END)
    for i in range(time_listbox.size()):
        if time_listbox.get(i) == res["time"]:
            time_listbox.selection_set(i)
            time_listbox.see(i)
            break

    # 🔹 코트번호 → court_cb
    court_var.set(str(res["court"]))
    court_cb.set(str(res["court"]))

    # 🔹 인원 → people_cb
    people_var.set(str(res["people"]))
    people_cb.set(str(res["people"]))

    # 🔹 자동 달력 클릭 모드일 때 날짜 클릭
    if calendar_click_mode.get() == "auto":
        ok = page_down_and_fix(res["date"])
        if not ok:
            status.set(f"{res['id']}번 날짜 클릭 실패 → 실행 중단")
            running = False
            return

    status.set(f"{res['id']}번 예약 시작")
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
    save_last_settings()
    running = False

def run_selected_manual():
    global current_thread
    # 이미 실행 중이면 새로 시작하지 않음
    if running:
        return
    # 🔥 예약 실행을 별도 스레드로 돌림
    current_thread = threading.Thread(target=run_selected, daemon=True)
    current_thread.start()


def run_selected_auto():
    global current_thread
    # 시간 기다리는 부분은 그대로 두고,
    # 시간이 되었을 때 스레드로 실행
    try:
        h = int(hour_var.get())
        m = int(min_var.get())
        s = int(sec_var.get())
    except:
        status.set("⚠ 예약 시간 설정 오류")
        return

    now = datetime.datetime.now()
    target = now.replace(hour=h, minute=m, second=s, microsecond=0)

    if target < now:
        target += datetime.timedelta(days=1)

    status.set(f"⏳ 자동 모드 — {target.strftime('%H:%M:%S')}까지 대기합니다")

    while datetime.datetime.now() < target:
        if emergency_stop:
            status.set("⚠ ESC로 취소됨")
            return
        time.sleep(0.2)

    # 🔥 시간이 되면 스레드로 실행
    if running:
        return
    current_thread = threading.Thread(target=run_selected, daemon=True)
    current_thread.start()


def auto_f2_monitor():
    global auto_repeat_started

    while True:
        if emergency_stop:
            return

        try:
            # 🔥 자동반복 조건
            if auto_repeat_enabled.get() and auto_repeat_started and f2_mode_var.get() == "manual":

                repeat_sec = int(auto_repeat_sec_var.get())

                # 🔥 start_on_enter 결과 받기
                result = start_on_enter(from_auto=True)

                # 🔥 STOP이면 자동반복 즉시 종료
                if result == "STOP":
                    return

                # 모든 예약 완료 시 종료
                all_done = True
                for item in tree.get_children():
                    if "done" not in tree.item(item, "tags"):
                        all_done = False
                        break

                if all_done:
                    status.set("예약 전체 완료 — 자동 반복 종료")
                    return

                time.sleep(repeat_sec)

            # 🔥 F2 자동 모드
            elif f2_mode_var.get() == "auto":
                now = datetime.datetime.now()
                target_h = int(hour_var.get())
                target_m = int(min_var.get())
                target_s = int(sec_var.get())

                if now.hour == target_h and now.minute == target_m and now.second == target_s:
                    result = start_on_enter(from_auto=True)

                    if result == "STOP":
                        return

                    time.sleep(1)

        except Exception as e:
            print("auto_f2_monitor 오류:", e)

        time.sleep(0.2)


############################################################
# 자동반복 엔진 (start_on_enter)
############################################################

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

import ctypes

def kill_thread(thread):
    if thread is None:
        return
    tid = thread.ident
    if tid is None:
        return
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
        ctypes.c_long(tid),
        ctypes.py_object(SystemExit)
    )
    if res == 0:
        print("❌ 스레드 종료 실패")
    elif res > 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), None)
        print("❌ 스레드 종료 오류 (복구)")


def check_ready_color():
    # 준비 색상 좌표
    x, y = 427, 739

    # 목표 색상 (준비 버튼 색상)
    target = (207, 10, 103)

    # 픽셀 읽기 (안정화 버전)
    r, g, b = fast_pixel_strong(x, y)

    print(f"[준비색상 감지] 좌표=({x},{y})  R={r}, G={g}, B={b}")

    # 오차 범위 확대 (기존 tol=8 → tol=15)
    return color_close(r, g, b, target, tol=15)


def start_on_enter(event=None, from_auto=False, from_f2=False):
    global emergency_stop, auto_repeat_started
  

    # F2 자동 모드일 때 수동 실행 막기
    if f2_mode_var.get() == "auto" and not from_auto and not from_f2:
        status.set("⏳ F2 자동 모드 — 설정된 시간까지 대기합니다")
        return

    # 🔥 자동반복 기준점 생성 (수동 실행일 때만)
    if not from_auto and not from_f2:
        auto_repeat_started = True

    # 자동반복일 때는 날짜만 클릭
    if from_auto:
        items = tree.get_children()
        if items:
            first_item = items[0]
            values = tree.item(first_item)["values"]
            first_date = values[1]

            if calendar_click_mode.get() == "auto":
                ok = page_down_and_fix(first_date)
                if not ok:
                    status.set("❌ 자동반복: 날짜 클릭 실패")
                    emergency_stop = True
                    return "STOP"

    # 예약 리스트 전체 실행
    for item in tree.get_children():

        # 🔥 ESC 즉시 중단
        if emergency_stop:
            status.set("⚠ ESC로 취소됨")
            return "STOP"

        values = tree.item(item)["values"]

        res = {
            "id": values[0],
            "date": values[1],
            "time": values[2],
            "court": int(values[3]),
            "people": int(values[4]),
        }

        status.set(f"{res['id']}번 예약 시작")

        if calendar_click_mode.get() == "auto":
            ok = page_down_and_fix(res["date"])
            if not ok:
                status.set(f"{res['id']}번 날짜 클릭 실패")
                return "STOP"

        # 🔥 run_reservation 결과 받기
        result = run_reservation(res)

        # 이미 예약됨 → 다음 예약
        if result == "NEXT_RESERVATION":
            continue

        # ESC → 전체 즉시 중단
        if result == "STOP":
            return "STOP"

        tree.item(item, tags=("done",))

    status.set("전체 예약 완료!")
    return "DONE"


###############################################
# 블럭 1 끝 — 엔진 전체 완료
###############################################

###############################################
# 블럭 2 — UI 전체 (가로폭 최적화 버전)
###############################################

root = tk.Tk()
root.bind("<Escape>", on_escape)

import tkinter as tk
from tkinter import ttk

# 화면 우측 상단 배치
root.update_idletasks()
screen_width = root.winfo_screenwidth()
window_width = 750
window_height = 600
x = screen_width - window_width
root.geometry(f"{window_width}x{window_height}+{x}+0")

############################################################
# UI 변수들
############################################################

auto_repeat_sec_var = tk.StringVar(value="10")   # 🔥 자동반복시간 변수 통일

status = tk.StringVar(value="대기 중")

auto_repeat_enabled = tk.BooleanVar(value=False)
f2_mode_var = tk.StringVar(value="manual")
calendar_click_mode = tk.StringVar(value="auto")
calendar_mode_var = tk.StringVar(value="5week")

hour_var = tk.StringVar(value="00")
min_var = tk.StringVar(value="00")
sec_var = tk.StringVar(value="00")

sync_hour_var = tk.StringVar(value="00")
sync_min_var = tk.StringVar(value="00")

court_var = tk.StringVar()
people_var = tk.StringVar()

def load_last_settings():
    if not os.path.exists(LAST_FILE):
        return

    with open(LAST_FILE, "r", encoding="utf-8") as f:
        raw = f.read().strip()

    if not raw:
        return

    parts = raw.split(",")

    # 🔥 새로운 저장 형식: 8개 항목
    # time, court, people, hour, min, sec, repeat_sec, repeat_flag
    if len(parts) == 8:
        time_str, court, people, last_hour, last_min, last_sec, repeat_sec, repeat_flag = parts

        auto_repeat_sec_var.set(repeat_sec)
        auto_repeat_enabled.set(True if repeat_flag == "1" else False)

    # 🔥 기존 형식(7개)도 호환 유지
    elif len(parts) == 7:
        time_str, court, people, last_hour, last_min, last_sec, repeat_sec = parts
        auto_repeat_sec_var.set(repeat_sec)

    else:
        print("⚠ last_settings.txt 형식 오류")
        return

    # 시간 리스트박스 선택
    time_listbox.selection_clear(0, tk.END)
    for i in range(time_listbox.size()):
        if time_listbox.get(i) == time_str:
            time_listbox.selection_set(i)
            time_listbox.see(i)
            break

    court_var.set(court)
    court_cb.set(court)

    people_var.set(people)
    people_cb.set(people)

    hour_var.set(last_hour)
    min_var.set(last_min)
    sec_var.set(last_sec)


############################################################
# 딜레이 변수 UI
############################################################

click_delay_var = tk.DoubleVar(value=0.01)
press_delay_var = tk.DoubleVar(value=0.01)
page_delay_var = tk.DoubleVar(value=0.05)
calendar_delay_var = tk.DoubleVar(value=0.05)
court_delay_var = tk.DoubleVar(value=0.05)
pay_delay_var = tk.DoubleVar(value=0.05)

############################################################
# 예약 리스트 UI (가로폭 축소)
############################################################

tree = ttk.Treeview(root, columns=("id","date","time","court","people"), show="headings", height=8)
tree.heading("id", text="ID")
tree.heading("date", text="날짜")
tree.heading("time", text="시간")
tree.heading("court", text="코트")
tree.heading("people", text="인원")

tree.column("id", width=40)
tree.column("date", width=120)
tree.column("time", width=80)
tree.column("court", width=60)
tree.column("people", width=60)

tree.grid(row=0, column=0, columnspan=3, padx=10, pady=10)

############################################################
# 날짜 리스트박스 (가로폭 축소)
############################################################

date_listbox = tk.Listbox(root, selectmode="multiple", height=8, width=12, exportselection=False)
date_listbox.grid(row=1, column=0, rowspan=5, padx=5)

def load_dates(filter_mode="all", weekday_filter=None, month_filter=None):
    date_listbox.delete(0, tk.END)
    today = datetime.date.today()
    for i in range(60):
        d = today + datetime.timedelta(days=i)
        wd = d.weekday()

        if filter_mode == "weekday" and wd >= 5:
            continue
        if filter_mode == "weekend" and wd < 5:
            continue
        if weekday_filter is not None and wd not in weekday_filter:
            continue
        if month_filter is not None and d.month != month_filter:
            continue

        date_listbox.insert(tk.END, d.strftime("%Y-%m-%d"))

load_dates()

ttk.Button(root, text="전체", width=8, command=lambda: load_dates("all")).grid(row=1, column=1)
ttk.Button(root, text="주중", width=8, command=lambda: load_dates("weekday")).grid(row=2, column=1)
ttk.Button(root, text="주말", width=8, command=lambda: load_dates("weekend")).grid(row=3, column=1)
ttk.Button(root, text="월수금", width=8, command=lambda: load_dates("all", weekday_filter=[0,2,4])).grid(row=4, column=1)
ttk.Button(root, text="다음달", width=8, command=lambda: load_dates("all", month_filter=(datetime.date.today().month % 12)+1)).grid(row=5, column=1)

############################################################
# 시간 리스트박스 (가로폭 축소)
############################################################

time_listbox = tk.Listbox(root, selectmode="multiple", height=8, width=10, exportselection=False)
time_listbox.grid(row=1, column=2, rowspan=5, padx=5)

def load_times(mode="all", custom_range=None):
    time_listbox.delete(0, tk.END)

    all_times = ["06:00","08:00","10:00","12:00","14:00","16:00","18:00","20:00"]
    morning = ["06:00","08:00","10:00"]
    afternoon = ["12:00","14:00","16:00"]
    evening = ["18:00","20:00"]

    if custom_range is not None:
        start, end = custom_range
        for t in all_times:
            if start <= t <= end:
                time_listbox.insert(tk.END, t)
        return

    if mode == "morning":
        for t in morning: time_listbox.insert(tk.END, t)
    elif mode == "afternoon":
        for t in afternoon: time_listbox.insert(tk.END, t)
    elif mode == "evening":
        for t in evening: time_listbox.insert(tk.END, t)
    else:
        for t in all_times:
            time_listbox.insert(tk.END, t)

load_times()

ttk.Button(root, text="전체", width=8, command=lambda: load_times("all")).grid(row=1, column=3)
ttk.Button(root, text="오전", width=8, command=lambda: load_times("morning")).grid(row=2, column=3)
ttk.Button(root, text="오후", width=8, command=lambda: load_times("afternoon")).grid(row=3, column=3)
ttk.Button(root, text="야간", width=8, command=lambda: load_times("evening")).grid(row=4, column=3)
ttk.Button(root, text="10~16", width=8, command=lambda: load_times(custom_range=("10:00","16:00"))).grid(row=5, column=3)


############################################################
# 코트 / 인원 선택 (가로폭 축소)
############################################################

court_cb = ttk.Combobox(root, textvariable=court_var, values=[str(i) for i in range(1,14)], state="readonly", width=5)
court_cb.grid(row=1, column=4)

people_cb = ttk.Combobox(root, textvariable=people_var, values=["2","4"], state="readonly", width=5)
people_cb.grid(row=2, column=4)

############################################################
# 🔥 여기에서 불러오기 실행 (UI 요소 생성 이후)
############################################################

load_last_settings()
load_time_settings()


############################################################
# CRUD 기능
############################################################

reservations = []

def add_reservation():
    selected_dates = [date_listbox.get(i) for i in date_listbox.curselection()]
    selected_times = [time_listbox.get(i) for i in time_listbox.curselection()]

    if not selected_dates or not selected_times or not court_var.get() or not people_var.get():
        status.set("날짜/시간/코트/인원을 모두 선택하세요")
        return

    count = 0
    for d in selected_dates:
        for t in selected_times:
            next_id = len(tree.get_children()) + 1
            tree.insert("", "end", values=(next_id, d, t, court_var.get(), people_var.get()))
            reservations.append({
                "id": next_id,
                "date": d,
                "time": t,
                "court": int(court_var.get()),
                "people": int(people_var.get()),
            })
            count += 1

    status.set(f"{count}개의 예약 추가됨")

def delete_reservation():
    selected = tree.selection()
    if not selected:
        status.set("삭제할 예약을 선택하세요")
        return

    item = selected[0]
    values = tree.item(item)["values"]
    del_id = values[0]

    tree.delete(item)

    global reservations
    reservations = [r for r in reservations if r["id"] != del_id]

    # ID 재정렬
    for idx, r in enumerate(reservations, start=1):
        r["id"] = idx

    # UI 재정렬
    for row in tree.get_children():
        tree.delete(row)

    for r in reservations:
        tree.insert("", "end", values=(r["id"], r["date"], r["time"], r["court"], r["people"]))

    status.set(f"{del_id}번 예약 삭제 완료")

############################################################
# 버튼 UI (가로폭 축소)
############################################################

ttk.Button(root, text="예약 추가", width=10, command=add_reservation).grid(row=6, column=0)
ttk.Button(root, text="예약 삭제", width=10, command=delete_reservation).grid(row=6, column=1)
ttk.Button(root, text="선택 실행", width=10, command=run_selected).grid(row=6, column=2)
ttk.Button(root, text="전체 실행", width=10, command=start_on_enter).grid(row=6, column=3)

add_btn = tk.Button(root, text="예약 추가", width=10,
                    bg="#4CAF50", fg="white", activebackground="#45A049")
add_btn.config(command=add_reservation)
add_btn.grid(row=6, column=0, padx=3, pady=5)

del_btn = tk.Button(root, text="예약 삭제", width=10,
                    bg="#F44336", fg="white", activebackground="#D32F2F")
del_btn.config(command=delete_reservation)
del_btn.grid(row=6, column=1, padx=3, pady=5)

run_selected_btn = tk.Button(root, text="선택 실행", width=10,
                             bg="#2196F3", fg="white", activebackground="#1976D2")
run_selected_btn.config(command=run_selected_thread)   # 🔥 여기 수정
run_selected_btn.grid(row=6, column=2, padx=3, pady=5)


run_all_btn = tk.Button(root, text="전체 실행", width=10,
                        bg="#FF9800", fg="white", activebackground="#FB8C00")
run_all_btn.config(command=start_on_enter)
run_all_btn.grid(row=6, column=3, padx=3, pady=5)

ttk.Label(root, text="F2 실행 모드").grid(row=8, column=0, sticky="w")

ttk.Radiobutton(root, text="수동", variable=f2_mode_var, value="manual").grid(row=8, column=1, sticky="w")
ttk.Radiobutton(root, text="자동", variable=f2_mode_var, value="auto").grid(row=8, column=2, sticky="w")

ttk.Label(root, text="달력 모드").grid(row=9, column=0, sticky="w")

ttk.Radiobutton(root, text="5주", variable=calendar_mode_var, value="5week").grid(row=9, column=1, sticky="w")
ttk.Radiobutton(root, text="6주", variable=calendar_mode_var, value="6week").grid(row=9, column=2, sticky="w")

ttk.Label(root, text="달력 클릭").grid(row=10, column=0, sticky="w")

ttk.Radiobutton(root, text="수동", variable=calendar_click_mode, value="manual").grid(row=10, column=1, sticky="w")
ttk.Radiobutton(root, text="자동", variable=calendar_click_mode, value="auto").grid(row=10, column=2, sticky="w")

ttk.Label(root, text="결제 모드").grid(row=11, column=0, sticky="w")

ttk.Radiobutton(root, text="대기", variable=pay_delay_var, value=0.05).grid(row=11, column=1, sticky="w")
ttk.Radiobutton(root, text="결제", variable=pay_delay_var, value=0.1).grid(row=11, column=2, sticky="w")

ttk.Label(root, text="자동 반복 시간(초)").grid(row=12, column=0, sticky="w")

# 🔥 수정: auto_repeat_time_var 제거, auto_repeat_sec_var로 통일
ttk.Entry(root, textvariable=auto_repeat_sec_var, width=6).grid(row=12, column=1)

ttk.Checkbutton(root, text="자동 반복 ON", variable=auto_repeat_enabled, onvalue=True, offvalue=False).grid(row=12, column=2)
ttk.Checkbutton(root, text="자동 반복 OFF", variable=auto_repeat_enabled, onvalue=False, offvalue=True).grid(row=12, column=3)

############################################################
# F2 실행시간 설정 UI (시간 / 분 / 초 표기)
############################################################

ttk.Label(root, text="F2 실행시간 설정").grid(row=13, column=0, sticky="w")

ttk.Label(root, text="예약 시간").grid(row=14, column=0, sticky="e")

hour_entry = ttk.Entry(root, textvariable=hour_var, width=4)
min_entry = ttk.Entry(root, textvariable=min_var, width=4)
sec_entry = ttk.Entry(root, textvariable=sec_var, width=4)

hour_entry.grid(row=14, column=1)
ttk.Label(root, text="시").grid(row=14, column=2)

min_entry.grid(row=14, column=3)
ttk.Label(root, text="분").grid(row=14, column=4)

sec_entry.grid(row=14, column=5)
ttk.Label(root, text="초").grid(row=14, column=6)

def validate_hour_event(event):
    try:
        v = int(hour_var.get())
        if v < 0 or v > 24:
            hour_var.set("00")
    except:
        hour_var.set("00")

hour_entry.bind("<FocusOut>", validate_hour_event)

ttk.Label(root, text="동기화 시간").grid(row=15, column=0, sticky="e")

ttk.Entry(root, textvariable=sync_hour_var, width=4).grid(row=15, column=1)
ttk.Label(root, text="시").grid(row=15, column=2)

ttk.Entry(root, textvariable=sync_min_var, width=4).grid(row=15, column=3)
ttk.Label(root, text="분").grid(row=15, column=4)

ttk.Button(root, text="자동 계산", command=auto_calculate_times).grid(row=14, column=7)
ttk.Button(root, text="시간 저장", command=save_time_settings).grid(row=15, column=7)

############################################################
# 상태 표시
############################################################

ttk.Label(root, textvariable=status).grid(row=7, column=0, columnspan=5)

root.bind("<Escape>", on_escape)

# 🔥 삭제됨: load_last_settings() (중복 호출로 오류 발생하던 부분)
# load_last_settings()

def on_close():
    save_last_settings()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)

threading.Thread(target=auto_f2_monitor, daemon=True).start()

root.mainloop()
