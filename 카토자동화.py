import ctypes, sys

def ensure_admin():
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except:
        is_admin = False

    if not is_admin:
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit()

ensure_admin()

import os
import shutil
import pyautogui
import pyperclip
import keyboard
import tkinter as tk
import tkinter.messagebox as msg
import tkinter.simpledialog as simpledialog
from tkinter import ttk
import threading
import datetime
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ============================================================
# 전역 변수 / 경로 설정
# ============================================================

STOP_FLAG = False
RUNNING = False
captured_positions = []

BASE_DIR = r"C:\Users\Desktop\자동화"

STEP8_FILE = os.path.join(BASE_DIR, "step8_positions.txt")
TEXT_DETECT_FILE = os.path.join(BASE_DIR, "text_detect_positions.txt")
TIME_FILE = os.path.join(BASE_DIR, "time_settings.txt")
SETTINGS_FILE = os.path.join(BASE_DIR, "extra_settings.txt")
DELAY_FILE = os.path.join(BASE_DIR, "delay_settings.txt")
POSITIONS_FILE = os.path.join(BASE_DIR, "positions.txt")

driver = None
wait = None
sync_done = False
LAST_MATCHED_ROW_INDEX = None
REFRESH_PAUSED = False

FOCUS_X, FOCUS_Y = 766, 733
NAV_X, NAV_Y = 100, 60
STEP8_LIST_X, STEP8_LIST_Y = 186, 676

TEXT_DETECT_COORDS_DIRECT = [
    (80, 772),
    (80, 848),
    (80, 927),
    (80, 1005),
]

TEXT_DETECT_COORDS_PAGEDOWN = [
    (80, 258),
    (80, 331),
    (80, 409),
    (80, 488),
    (80, 572),
    (80, 643),
    (80, 718),
]

# ============================================================
# 로그 함수
# ============================================================

def add_log(msg):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

def add_step_log(step_id, title, result, detail=""):
    suffix = f" | {detail}" if detail else ""
    add_log(f"[STEP {step_id}] {title} -> {result}{suffix}")

# ============================================================
# 백업 기능 (누락된 함수 복구)
# ============================================================

def create_backup():
    try:
        current_file = os.path.abspath(__file__)
        folder = os.path.dirname(current_file)

        backup_folder = os.path.join(folder, "backup")
        os.makedirs(backup_folder, exist_ok=True)

        files_to_backup = [
            "step8_positions.txt",
            "text_detect_positions.txt",
            "time_settings.txt",
            "extra_settings.txt",
            "delay_settings.txt",
            "positions.txt"
        ]

        for filename in files_to_backup:
            src = os.path.join(folder, filename)
            if os.path.exists(src):
                shutil.copy2(src, backup_folder)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"카토자동화_backup_{timestamp}.py"
        backup_path = os.path.join(backup_folder, backup_name)

        shutil.copy2(current_file, backup_path)

        msg.showinfo("백업 완료", f"백업 폴더: backup/\n코드 백업 파일: {backup_name}")

    except Exception as e:
        msg.showerror("백업 실패", f"오류 발생: {e}")

# ============================================================
# UI 시작 (딜레이 변수는 반드시 root 아래에서 생성)
# ============================================================

root = tk.Tk()
root.title("카토 자동화 통합 UI")

def place_window_top_right(width=600, height=1200, margin_x=10, margin_y=0):
    screen_w = root.winfo_screenwidth()
    x = max(0, screen_w - width - margin_x)
    y = max(0, margin_y)
    root.geometry(f"{width}x{height}+{x}+{y}")

place_window_top_right()

# 딜레이 변수 (오류 해결: root 생성 이후에 선언)
delay_step8 = tk.StringVar(value="0.25")
delay_autocomplete = tk.StringVar(value="0.40")
delay_loading = tk.StringVar(value="10")
delay_loop_wait = tk.StringVar(value="0.30")
delay_post_loading = tk.StringVar(value="0.50")
delay_focus_wait = tk.StringVar(value="0.50")

# ============================================================
# 딜레이 저장/불러오기 (수정본)
# ============================================================

def save_delay_settings():
    with open(DELAY_FILE, "w", encoding="utf-8") as f:
        f.write(",".join([
            delay_step8.get(),
            delay_autocomplete.get(),
            delay_loading.get(),
            delay_loop_wait.get(),
            delay_post_loading.get(),
            delay_focus_wait.get(),
        ]))

def load_delay_settings():
    if not os.path.exists(DELAY_FILE):
        return
    with open(DELAY_FILE, "r", encoding="utf-8") as f:
        parts = f.read().strip().split(",")
        if len(parts) >= 3:
            delay_step8.set(parts[0])
            delay_autocomplete.set(parts[1])
            delay_loading.set(parts[2])
        if len(parts) >= 4:
            delay_loop_wait.set(parts[3])
        if len(parts) >= 5:
            delay_post_loading.set(parts[4])
        if len(parts) >= 6:
            delay_focus_wait.set(parts[5])

def get_float_setting(var_obj, default_value):
    try:
        return float(var_obj.get())
    except Exception:
        return float(default_value)

# ============================================================
# Chrome 연결
# ============================================================

def connect_chrome():
    global driver
    try:
        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except:
        msg.showerror("Chrome 연결 실패", "Chrome 디버깅 모드가 실행 중인지 확인하세요.")
        return None

def open_kato(show_success_popup=True):
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    debug_dir = r"C:\ChromeDebug"

    os.system(f'start "" "{chrome_path}" --remote-debugging-port=9222 --user-data-dir="{debug_dir}"')
    time.sleep(1.5)

    global driver, wait
    driver = connect_chrome()
    if driver is None:
        return

    wait = WebDriverWait(driver, 2)

    try:
        driver.get("https://kato.kr")
        if show_success_popup:
            msg.showinfo("KATO 접속 완료", "Chrome 디버깅 모드 실행 + KATO 접속이 완료되었습니다.")
        add_log("KATO 자동 접속 완료")
    except:
        msg.showerror("접속 실패", "Chrome은 열렸지만 KATO 접속에 실패했습니다.")

def auto_connect_on_startup():
    # UI 시작 직후 선택된 경우에만 자동 접속한다.
    if auto_connect_var.get():
        open_kato(show_success_popup=False)

# ============================================================
# Step8 좌표 저장/불러오기 (중복/꼬임 해결)
# ============================================================

def save_step8_positions():
    with open(STEP8_FILE, "w", encoding="utf-8") as f:
        for entry in step8_entries:
            f.write(entry.get() + "\n")

def load_step8_positions():
    if not os.path.exists(STEP8_FILE):
        return

    with open(STEP8_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 기존 내용 삭제 (중복 방지)
    for entry in step8_entries:
        entry.delete(0, tk.END)

    # 새 내용 삽입
    for i, line in enumerate(lines):
        if i < len(step8_entries):
            step8_entries[i].insert(0, line.strip())

def refresh_text_detect_coord_cache():
    direct_coords = []
    pagedown_coords = []

    for entry in text_detect_entries_direct:
        value = entry.get().strip()
        try:
            x, y = map(int, value.split(","))
            direct_coords.append((x, y))
        except Exception:
            direct_coords.append((0, 0))

    for entry in text_detect_entries_pagedown:
        value = entry.get().strip()
        try:
            x, y = map(int, value.split(","))
            pagedown_coords.append((x, y))
        except Exception:
            pagedown_coords.append((0, 0))

    TEXT_DETECT_COORDS_DIRECT[:] = direct_coords
    TEXT_DETECT_COORDS_PAGEDOWN[:] = pagedown_coords

def save_text_detect_positions():
    refresh_text_detect_coord_cache()
    with open(TEXT_DETECT_FILE, "w", encoding="utf-8") as f:
        for x, y in TEXT_DETECT_COORDS_DIRECT:
            f.write(f"{x},{y}\n")
        for x, y in TEXT_DETECT_COORDS_PAGEDOWN:
            f.write(f"{x},{y}\n")

def load_text_detect_positions():
    values = []
    if os.path.exists(TEXT_DETECT_FILE):
        with open(TEXT_DETECT_FILE, "r", encoding="utf-8") as f:
            values = [line.strip() for line in f.readlines()]

    default_values = [
        *(f"{x},{y}" for x, y in TEXT_DETECT_COORDS_DIRECT),
        *(f"{x},{y}" for x, y in TEXT_DETECT_COORDS_PAGEDOWN),
    ]

    while len(values) < len(default_values):
        values.append(default_values[len(values)])

    for entry in text_detect_entries_direct + text_detect_entries_pagedown:
        entry.delete(0, tk.END)

    direct_count = len(text_detect_entries_direct)
    for entry, value in zip(text_detect_entries_direct, values[:direct_count]):
        entry.insert(0, value)

    for entry, value in zip(text_detect_entries_pagedown, values[direct_count:direct_count + len(text_detect_entries_pagedown)]):
        entry.insert(0, value)

    refresh_text_detect_coord_cache()


# ============================================================
# 정각 / 새로고침 / 참가자 저장·불러오기 (완성본)
# ============================================================

def save_time_settings():
    with open(TIME_FILE, "w", encoding="utf-8") as f:
        f.write(f"{hour_var.get()},{min_var.get()},{sec_var.get()}")

def load_time_settings():
    if not os.path.exists(TIME_FILE):
        return
    with open(TIME_FILE, "r", encoding="utf-8") as f:
        raw = f.read().strip()
    if not raw:
        return
    parts = raw.split(",")
    if len(parts) >= 3:
        hour_var.set(parts[0])
        min_var.set(parts[1])
        sec_var.set(parts[2])


def save_extra_settings():
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        f.write(",".join([
            sync_hour_var.get(), sync_min_var.get(),
            refresh_start_hour.get(), refresh_start_min.get(),
            refresh_end_hour.get(), refresh_end_min.get(),
            refresh_interval.get(),
            name1_var.get(), name2_var.get(), payer_var.get(), department_var.get(),
            "1" if auto_connect_var.get() else "0"
        ]))

def load_extra_settings():
    if not os.path.exists(SETTINGS_FILE):
        return
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        parts = f.read().strip().split(",")

    if len(parts) >= 10:
        sync_hour_var.set(parts[0])
        sync_min_var.set(parts[1])
        refresh_start_hour.set(parts[2])
        refresh_start_min.set(parts[3])
        refresh_end_hour.set(parts[4])
        refresh_end_min.set(parts[5])
        refresh_interval.set(parts[6])
        name1_var.set(parts[7])
        name2_var.set(parts[8])
        payer_var.set(parts[9])
        if len(parts) >= 11:
            department_var.set(parts[10])
        if len(parts) >= 12:
            auto_connect_var.set(parts[11].strip().lower() in ("1", "true", "yes", "on"))

# ============================================================
# 좌표 저장/불러오기 (완성본)
# ============================================================

def save_positions():
    with open(POSITIONS_FILE, "w", encoding="utf-8") as f:
        for name, x, y in captured_positions:
            f.write(f"{name},{x},{y}\n")

def load_positions():
    if not os.path.exists(POSITIONS_FILE):
        return

    with open(POSITIONS_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 기존 목록 초기화
    captured_positions.clear()
    listbox.delete(0, "end")

    # 새 목록 로드
    for line in lines:
        name, x, y = line.strip().split(",")
        captured_positions.append((name, int(x), int(y)))
        listbox.insert("end", f"{name} ({x}, {y})")

def delete_selected_position():
    sel = listbox.curselection()
    if not sel:
        return
    idx = sel[0]
    captured_positions.pop(idx)
    save_positions()
    load_positions()

def delete_all_positions():
    captured_positions.clear()
    save_positions()
    load_positions()

def move_to_selected_position():
    sel = listbox.curselection()
    if not sel:
        return
    idx = sel[0]
    _, x, y = captured_positions[idx]
    pyautogui.moveTo(x, y, duration=0.3)

# ============================================================
# PC 시간 동기화
# ============================================================

def sync_pc_time():
    os.system("w32tm /resync")
    add_log("PC 시간 인터넷 동기화 완료")
    status.set("PC 시간 인터넷 동기화 완료")

def check_sync_time():
    def _check():
        global sync_done
        if sync_done:
            return

        now = datetime.datetime.now()
        try:
            sync_time = datetime.datetime.strptime(
                f"{sync_hour_var.get()}:{sync_min_var.get()}:00",
                "%H:%M:%S"
            ).replace(year=now.year, month=now.month, day=now.day)
        except ValueError:
            status.set("동기화 시간 형식 오류")
            return

        if now >= sync_time:
            sync_pc_time()
            sync_done = True
        else:
            root.after(1000, _check)

    root.after(1000, _check)

# ============================================================
# 자동 계산 기능
# ============================================================

def auto_calculate_times():
    try:
        h = int(hour_var.get())
        m = int(min_var.get())
    except:
        return

    sync_time = datetime.datetime(2024, 1, 1, h, m) - datetime.timedelta(minutes=5)
    sync_hour_var.set(sync_time.hour)
    sync_min_var.set(sync_time.minute)

    end_time = datetime.datetime(2024, 1, 1, h, m) - datetime.timedelta(minutes=5)
    refresh_end_hour.set(end_time.hour)
    refresh_end_min.set(end_time.minute)

    now = datetime.datetime.now()
    refresh_start_hour.set(now.hour)
    refresh_start_min.set(now.minute)

# ============================================================
# 로딩 감지 (완성본)
# ============================================================

def wait_loading_done_auto():
    x, y = 95, 63
    loading_rgb = (199, 199, 199)
    try:
        timeout_sec = float(delay_loading.get())
    except Exception:
        timeout_sec = 30.0
    start_time = time.time()

    # 지정 색상(로딩 색상)이 사라질 때까지 0.01초 단위로 확인한다.
    while True:
        r, g, b = pyautogui.pixel(x, y)
        if (r, g, b) != loading_rgb:
            add_log(f"로딩 완료 감지: coord=({x},{y}), rgb=({r},{g},{b})")
            break

        if (time.time() - start_time) >= timeout_sec:
            add_log(
                f"로딩 감지 타임아웃 {timeout_sec:.0f}초: coord=({x},{y}), "
                f"rgb=({r},{g},{b}) - 다음 단계 진행"
            )
            break

        time.sleep(0.01)

    # 로딩 완료 직후 UI 안정화 대기
    time.sleep(get_float_setting(delay_post_loading, 0.5))

def detect_loading_once_auto():
    """로딩 완료 색상을 짧게 감지만 하고 다음 단계로 진행한다."""
    x, y = 95, 63
    loading_rgb = (199, 199, 199)
    r, g, b = pyautogui.pixel(x, y)
    loading_visible = (r, g, b) == loading_rgb

    if loading_visible:
        add_log(f"로딩 진행 중 감지: coord=({x},{y}), rgb=({r},{g},{b})")
    else:
        add_log(f"로딩 완료 상태 감지: coord=({x},{y}), rgb=({r},{g},{b})")


# ============================================================
# 자동완성 기능
# ============================================================

def auto_select_with_hover(start_x, start_y):
    timeout = 5
    start_time = time.time()

    y1 = start_y
    y2 = start_y + 5
    toggle = True

    while time.time() - start_time < timeout:
        y = y1 if toggle else y2

        r, g, b = pyautogui.pixel(start_x, y)
        if (r, g, b) == (0, 127, 255):
            pyautogui.press("enter")
            time.sleep(float(delay_autocomplete.get()))
            pyautogui.press("tab")
            return

        pyautogui.moveTo(start_x, y, duration=float(delay_autocomplete.get()))
        time.sleep(float(delay_autocomplete.get()))
        toggle = not toggle

    pyautogui.press("enter")
    time.sleep(float(delay_autocomplete.get()))
    pyautogui.press("tab")

def action_min_yonggi_final():
    pyautogui.click(270, 725)
    time.sleep(float(delay_autocomplete.get()))
    pyautogui.moveTo(270, 795, duration=float(delay_autocomplete.get()))
    pyperclip.copy(name1_var.get())
    pyautogui.hotkey("ctrl", "v")
    time.sleep(float(delay_autocomplete.get()))
    auto_select_with_hover(270, 795)

def action_shin_myeongsik():
    pyautogui.click(270, 880)
    time.sleep(float(delay_autocomplete.get()))
    pyautogui.moveTo(270, 920, duration=float(delay_autocomplete.get()))
    pyperclip.copy(name2_var.get())
    pyautogui.hotkey("ctrl", "v")
    time.sleep(float(delay_autocomplete.get()))
    auto_select_with_hover(270, 920)

def action_min_yonggi_payment():
    pyperclip.copy(payer_var.get())
    pyautogui.hotkey("ctrl", "v")
    time.sleep(float(delay_autocomplete.get()))

def action_department_input():
    pyperclip.copy(department_var.get())
    pyautogui.hotkey("ctrl", "v")
    time.sleep(float(delay_autocomplete.get()))

def should_skip_one_input():
    dept = department_var.get().strip()
    return dept in ("개나리부", "챌린저부")

def get_department_detect_coord(step8_idx=None, did_pagedown=False):
    # 부서 감지 좌표는 별도 선택값을 우선 사용하고, 없으면 Step8 선택값을 따른다.
    if step8_idx is None:
        idx = dept_detect_selected.get()
    else:
        idx = step8_idx

    if 0 <= idx < len(TEXT_DETECT_COORDS_DIRECT):
        return TEXT_DETECT_COORDS_DIRECT[idx]

    local_idx = idx - len(TEXT_DETECT_COORDS_DIRECT)
    if 0 <= local_idx < len(TEXT_DETECT_COORDS_PAGEDOWN):
        return TEXT_DETECT_COORDS_PAGEDOWN[local_idx]

    return None

def get_row_text_from_viewport_point(x, y):
    if driver is None:
        return ""

    script = """
    const screenX = arguments[0];
    const screenY = arguments[1];
    const browserLeft = window.screenX;
    const browserTop = window.screenY + (window.outerHeight - window.innerHeight);
    const viewportX = Math.round(screenX - browserLeft);
    const viewportY = Math.round(screenY - browserTop);
    const el = document.elementFromPoint(viewportX, viewportY);
    if (!el) {
        return "";
    }
    const row = el.closest('tr');
    const text = row ? row.innerText : el.innerText;
    return (text || "").trim();
    """
    try:
        return driver.execute_script(script, x, y) or ""
    except Exception:
        return ""

def get_row_element_from_viewport_point(x, y):
    if driver is None:
        return None

    script = """
    const screenX = arguments[0];
    const screenY = arguments[1];
    const browserLeft = window.screenX;
    const browserTop = window.screenY + (window.outerHeight - window.innerHeight);
    const viewportX = Math.round(screenX - browserLeft);
    const viewportY = Math.round(screenY - browserTop);
    const el = document.elementFromPoint(viewportX, viewportY);
    if (!el) {
        return null;
    }
    return el.closest('tr');
    """
    try:
        return driver.execute_script(script, x, y)
    except Exception:
        return None

def get_candidate_rows():
    """참가신청/접수마감 상태와 무관하게 참가목록이 있는 행을 수집한다."""
    if driver is None:
        return []

    try:
        rows = driver.find_elements(
            By.XPATH,
            "//tr[.//*[contains(normalize-space(.), '참가목록')]]"
        )
        if not rows:
            return []

        visible_rows = [r for r in rows if r.is_displayed()]
        return visible_rows if visible_rows else rows
    except Exception:
        return []

def detect_department_on_page(step8_idx=None, did_pagedown=False):
    """변경흐름 기준: 선택된 부서감지 좌표의 텍스트에 목표 부서명이 포함되는지 확인한다."""

    target = department_var.get().strip()
    if not target:
        return True

    if driver is None:
        add_log("부서감지 실패: Selenium driver 없음(Chrome 디버깅 연결 필요)")
        return False

    def _norm(text):
        # 공백/구분자 제거 후 비교용 문자열로 정규화
        return "".join(ch for ch in text if ch.isalnum())

    try:
        normalized_target = _norm(target)
        detect_idx = dept_detect_selected.get()
        detect_coord = get_department_detect_coord(detect_idx, did_pagedown)
        if detect_coord is None:
            add_log(f"부서감지 좌표 없음: 선택번호={detect_idx+1}")
            return False

        x, y = detect_coord
        if x <= 0 or y <= 0:
            add_log(f"부서감지 좌표 비정상: 선택번호={detect_idx+1}, coord=({x},{y})")
            return False

        row_text = get_row_text_from_viewport_point(x, y)
        text_source = "point"
        normalized_row = _norm(row_text)

        # 좌표 직접 텍스트가 비면, 해당 좌표가 가리키는 행 텍스트를 재시도한다.
        if not normalized_row:
            row_el = get_row_element_from_viewport_point(x, y)
            if row_el is not None:
                try:
                    row_text = row_el.text.replace("\n", " ").strip()
                    normalized_row = _norm(row_text)
                    text_source = "point-row"
                except Exception:
                    pass

        # 여전히 비면 선택 번호 기준의 참가목록 행 텍스트를 폴백으로 사용한다.
        if not normalized_row:
            candidate_rows = get_candidate_rows()
            local_idx = detect_idx - 4 if did_pagedown else detect_idx
            if 0 <= local_idx < len(candidate_rows):
                row_text = candidate_rows[local_idx].text.replace("\n", " ").strip()
                normalized_row = _norm(row_text)
                text_source = "candidate-row"

        matched = normalized_target in normalized_row

        add_log(
            f"부서감지 검사: 선택번호={detect_idx+1}, did_pagedown={did_pagedown}, "
            f"coord=({x},{y}), source={text_source}, target={normalized_target}, matched={matched}, "
            f"row_text={row_text[:120]}"
        )
        return matched
    except Exception:
        add_log("부서감지 예외 발생")
        return False

# ============================================================
# Step8 색상 검사 + 클릭
# ============================================================

def is_step8_color(x, y):
    allowed_colors = [
        (75, 173, 235),
        (53, 147, 205),
        (60, 160, 220),
        (90, 185, 240),
        (45, 135, 190),
    ]

    tol = 25
    # 단일 픽셀 오검출을 줄이기 위해 중심+주변 픽셀을 함께 검사한다.
    sample_offsets = [(0, 0), (-2, 0), (2, 0), (0, -2), (0, 2)]

    for dx, dy in sample_offsets:
        r, g, b = pyautogui.pixel(x + dx, y + dy)
        for cr, cg, cb in allowed_colors:
            if abs(r - cr) <= tol and abs(g - cg) <= tol and abs(b - cb) <= tol:
                return True
    return False

def wait_for_step8_color_ready(x, y, timeout_sec=2.5, poll_sec=0.05):
    start = time.time()
    while (time.time() - start) < timeout_sec:
        if is_step8_color(x, y):
            return True
        time.sleep(poll_sec)
    return False

def click_step8_selected(idx, step8_coords, did_pagedown=False):
    # 변경흐름 기준: Step8 좌표 색상 감지 후 일치할 때만 좌표 클릭한다.
    coord = step8_coords[idx]
    if coord is None:
        add_log(f"Step8 좌표 없음: idx={idx}")
        return False

    x, y = coord
    add_log(f"Step8 색상감지 시작: idx={idx}, coord=({x},{y})")

    wait_timeout = max(1.5, float(delay_step8.get()) * 8)
    if not wait_for_step8_color_ready(x, y, timeout_sec=wait_timeout, poll_sec=0.05):
        add_log(f"Step8 색상 대기 타임아웃({wait_timeout:.2f}s): 클릭하지 않고 재시도")
        return False

    add_log(f"Step8 클릭 시도: idx={idx}, coord=({x},{y})")

    pyautogui.moveTo(x, y, duration=float(delay_step8.get()))
    time.sleep(float(delay_step8.get()))

    pyautogui.doubleClick(x, y)
    add_log("Step8 좌표 더블클릭 실행")
    return True

def prepare_step8_view(step8_idx):
    """요청 흐름 기준: Step8 1~4는 바로 진행, 5~10은 페이지다운 후 진행."""
    if step8_idx <= 3:
        add_log("Step8 준비: 바로(1~4), 페이지다운 없음")
        return False

    if step8_idx == 10:
        add_log("Step8 준비: 11번 선택(페이지다운 없음)")
        return False

    add_log("Step8 준비: 다운(5~10), pagedown 실행")
    pyautogui.press("pagedown")
    time.sleep(float(delay_step8.get()))
    return True

def restore_step8_view_if_needed(did_pagedown):
    if did_pagedown:
        pyautogui.press("pageup")
        time.sleep(float(delay_step8.get()))
        add_log("Step8 복구: pageup 실행")

def get_step8_coords():
    coords = []
    for entry in step8_entries:
        value = entry.get().strip()
        if not value:
            coords.append(None)
            continue
        try:
            x, y = map(int, value.split(","))
            coords.append((x, y))
        except:
            coords.append(None)
    return coords


# ============================================================
# Step8 이후 전체 자동화 단계 (수동 시작용)
# ============================================================

def run_after_step8():
    skip_one = should_skip_one_input()

    steps = [
        # 🔥 Step8 클릭 후 화면 이동 로딩 → 반드시 로딩 감지 필요
        ("로딩 감지(비대기)", detect_loading_once_auto),

        # 🔥 로딩 끝난 후 포커스 좌표 클릭 + 0.5초 대기
        ("포커스 고정", lambda: (pyautogui.click(766, 373), time.sleep(get_float_setting(delay_focus_wait, 0.5)))),

        # 🔥 다음 단계: 270,725 더블클릭
        ("좌표 270,725 더블클릭", lambda: (pyautogui.doubleClick(270, 725), time.sleep(float(delay_autocomplete.get())))),

        # 🔥 참가자명 자동완성 1
        ("참가자명 자동완성 1", lambda: (action_min_yonggi_final(), time.sleep(float(delay_autocomplete.get())))),


        ("좌표 270,795 클릭", lambda: (pyautogui.click(270, 795), time.sleep(float(delay_autocomplete.get())))),
        
        ("탭", lambda: (pyautogui.press("tab"), time.sleep(float(delay_autocomplete.get())))),
    ]

    if not skip_one:
        steps.append(("1 입력", lambda: (pyautogui.write("1"), time.sleep(float(delay_autocomplete.get())))))
        steps.append(("탭", lambda: (pyautogui.press("tab"), time.sleep(float(delay_autocomplete.get())))))

    steps += [
        ("좌표 270,880 클릭", lambda: (pyautogui.click(270, 880), time.sleep(float(delay_autocomplete.get())))),
        ("참가자명 자동완성 2", lambda: (action_shin_myeongsik(), time.sleep(float(delay_autocomplete.get())))),

      
        ("좌표 270,920 클릭", lambda: (pyautogui.click(270, 920), time.sleep(float(delay_autocomplete.get())))),
        
        ("탭", lambda: (pyautogui.press("tab"), time.sleep(float(delay_autocomplete.get())))),
    ]

    if not skip_one:
        steps.append(("1 입력", lambda: (pyautogui.write("1"), time.sleep(float(delay_autocomplete.get())))))
        steps.append(("탭", lambda: (pyautogui.press("tab"), time.sleep(float(delay_autocomplete.get())))))

    steps += [
        ("0 입력", lambda: (pyautogui.write("0"), time.sleep(float(delay_autocomplete.get())))),
        ("탭", lambda: (pyautogui.press("tab"), time.sleep(float(delay_autocomplete.get())))),
        ("6229 입력", lambda: (pyautogui.write("6229"), time.sleep(float(delay_autocomplete.get())))),
        ("탭", lambda: (pyautogui.press("tab"), time.sleep(float(delay_autocomplete.get())))),
        ("2975 입력", lambda: (pyautogui.write("2975"), time.sleep(float(delay_autocomplete.get())))),
        ("탭", lambda: (pyautogui.press("tab"), time.sleep(float(delay_autocomplete.get())))),
        ("입금자명 자동완성", lambda: (action_min_yonggi_payment(), time.sleep(float(delay_autocomplete.get())))),
        ("탭", lambda: (pyautogui.press("tab"), time.sleep(float(delay_autocomplete.get())))),
        ("탭", lambda: (pyautogui.press("tab"), time.sleep(float(delay_autocomplete.get())))),
    ]


    total = len(steps)
    for i, (desc, action) in enumerate(steps, start=1):
        if STOP_FLAG:
            add_step_log(f"C{i:02d}", desc, "STOP")
            return

        add_step_log(f"C{i:02d}", desc, "START", f"{i}/{total}")
        try:
            action()
            add_step_log(f"C{i:02d}", desc, "OK")
        except Exception as e:
            add_step_log(f"C{i:02d}", desc, "FAIL", str(e))
            msg.showerror("자동화 단계 오류", f"단계 실패: {desc}\n오류: {e}")
            return

    if receive_mode.get() == "RECEIVE":
        add_step_log("C99", "최종 ENTER", "START")
        pyautogui.press("enter")
        add_step_log("C99", "최종 ENTER", "OK")

    msg.showinfo("완료", "모든 자동화 순서가 완료되었습니다!")

# ============================================================
# 참가자 수동 입력용 함수 (C1)
# ============================================================

def run_manual_participants():
    global RUNNING, STOP_FLAG

    if RUNNING:
        msg.showwarning("이미 실행 중", "자동화가 이미 실행되고 있습니다.")
        return

    RUNNING = True
    STOP_FLAG = False

    def _runner():
        global RUNNING
        try:
            run_after_step8()
        finally:
            RUNNING = False

    try:
        threading.Thread(target=_runner, daemon=True).start()
    except Exception as e:
        RUNNING = False
        msg.showerror("수동 참가자 입력 오류", f"오류 발생: {e}")

# ============================================================
# 메인 자동화 (A+B+C 통합)
# ============================================================

def run_automation(step8_idx, step8_coords, immediate_start=False):
    global REFRESH_PAUSED
    skip_one = should_skip_one_input()

    if immediate_start:
        add_step_log("A01", "테스트 즉시 시작", "OK", "정각 대기 생략")
    else:
        try:
            hour = int(hour_var.get())
            minute = int(min_var.get())
            second = int(sec_var.get())
            add_step_log("A01", "목표 시간 파싱", "OK", f"{hour:02d}:{minute:02d}:{second:02d}")
        except:
            add_step_log("A01", "목표 시간 파싱", "FAIL")
            msg.showerror("시간 오류", "시/분/초에 숫자만 입력하세요.")
            return

        now = datetime.datetime.now()
        target = datetime.datetime(now.year, now.month, now.day, hour, minute, second)
        if target < now:
            target += datetime.timedelta(days=1)
        add_step_log("A02", "대기 시작", "START", f"target={target.strftime('%Y-%m-%d %H:%M:%S')}")

        while datetime.datetime.now() < target:
            if STOP_FLAG:
                add_step_log("A02", "대기 시작", "STOP")
                return
            time.sleep(0.01)

        add_step_log("A02", "대기 완료", "OK")

    time.sleep(float(delay_autocomplete.get()))

    # 2) 포커스 좌표 클릭 (시작 시 1회만)
    add_step_log("A03", "초기 포커스 클릭", "START", f"coord=({FOCUS_X},{FOCUS_Y})")
    pyautogui.click(FOCUS_X, FOCUS_Y)
    time.sleep(float(delay_autocomplete.get()))
    add_step_log("A03", "초기 포커스 클릭", "OK")

    attempt = 0
    while True:
        if STOP_FLAG:
            add_step_log("B00", "반복 루프", "STOP")
            return

        attempt += 1
        add_step_log("B00", "반복 루프", "START", f"attempt={attempt}")

        # 3) 좌표 클릭
        add_step_log("B01", "NAV 클릭", "START", f"coord=({NAV_X},{NAV_Y})")
        pyautogui.click(NAV_X, NAV_Y)
        time.sleep(get_float_setting(delay_loop_wait, 0.3))
        add_step_log("B01", "NAV 클릭", "OK")

        # 4) 로딩 감지
        add_step_log("B02", "로딩 감지", "START")
        wait_loading_done_auto()
        time.sleep(get_float_setting(delay_loop_wait, 0.3))
        add_step_log("B02", "로딩 감지", "OK")

        REFRESH_PAUSED = True
        try:
            # 5) 좌표 클릭
            add_step_log("B03", "Step8 목록 이동", "START", f"coord=({STEP8_LIST_X},{STEP8_LIST_Y})")
            pyautogui.click(STEP8_LIST_X, STEP8_LIST_Y)
            time.sleep(1.0)
            add_step_log("B03", "Step8 목록 이동", "OK")

            # 6~7) Step8 선택이 5~11이면 페이지다운 후 진행
            did_pagedown = prepare_step8_view(step8_idx)
            add_step_log("B04", "Step8 화면 준비", "OK", f"did_pagedown={did_pagedown}")
            if did_pagedown:
                # 페이지 전환 후 DOM/화면 안정화 대기
                time.sleep(1.0)

            # 8) 부서 감지 (Step8 행 좌측 텍스트 기준)
            add_step_log("B05", "부서 텍스트 감지", "START", f"step8={step8_idx+1}, dept={department_var.get()}")
            dept_matched = detect_department_on_page(step8_idx, did_pagedown)
            if not dept_matched:
                add_step_log("B05", "부서 텍스트 감지", "FAIL")
                status.set(f"부서 불일치({department_var.get()}) - 재시도")
                add_step_log("B05", "부서 불일치로 클릭 차단", "OK", f"step8={step8_idx+1}")
                restore_step8_view_if_needed(did_pagedown)
                time.sleep(float(delay_autocomplete.get()))
                # 부서가 맞지 않으면 절대 Step8 클릭하지 않고 처음부터 재시도
                continue
            add_step_log("B05", "부서 텍스트 감지", "OK")

            # 11~12) 클릭좌표 색상 감지 후 맞으면 Step8 클릭
            add_step_log("B06", "Step8 클릭", "START", f"step8={step8_idx+1}")
            if click_step8_selected(step8_idx, step8_coords, did_pagedown):
                add_step_log("B06", "Step8 클릭", "OK")
                break
            else:
                add_step_log("B06", "Step8 클릭", "FAIL")
                restore_step8_view_if_needed(did_pagedown)
                time.sleep(float(delay_autocomplete.get()))
                continue
        finally:
            REFRESH_PAUSED = False

    steps = [
        ("로딩 감지(대기)", wait_loading_done_auto),
        ("포커스 고정", lambda: (pyautogui.click(FOCUS_X, FOCUS_Y), time.sleep(get_float_setting(delay_focus_wait, 0.5)))),
        ("좌표 270,725 더블클릭", lambda: (pyautogui.doubleClick(270, 725), time.sleep(float(delay_autocomplete.get())))),
        ("참가자명 자동완성 1", lambda: (action_min_yonggi_final(), time.sleep(float(delay_autocomplete.get())))),
        ("좌표 270,795 클릭", lambda: (pyautogui.click(270, 795), time.sleep(float(delay_autocomplete.get())))),
        ("탭", lambda: (pyautogui.press("tab"), time.sleep(float(delay_autocomplete.get())))),
    ]

    if not skip_one:
        steps.append(("1 입력", lambda: (pyautogui.write("1"), time.sleep(float(delay_autocomplete.get())))))
        steps.append(("탭", lambda: (pyautogui.press("tab"), time.sleep(float(delay_autocomplete.get())))))

    steps += [
        ("좌표 270,880 포커스 보정", lambda: (pyautogui.doubleClick(270, 880), time.sleep(float(delay_autocomplete.get()) + 0.15))),
        ("참가자명 자동완성 2", lambda: (action_shin_myeongsik(), time.sleep(float(delay_autocomplete.get())))),
        ("좌표 270,920 클릭", lambda: (pyautogui.click(270, 920), time.sleep(float(delay_autocomplete.get())))),
        ("탭", lambda: (pyautogui.press("tab"), time.sleep(float(delay_autocomplete.get())))),
    ]

    if not skip_one:
        steps.append(("1 입력", lambda: (pyautogui.write("1"), time.sleep(float(delay_autocomplete.get())))))
        steps.append(("탭", lambda: (pyautogui.press("tab"), time.sleep(float(delay_autocomplete.get())))))

    steps += [
        ("0 입력", lambda: (pyautogui.write("0"), time.sleep(float(delay_autocomplete.get())))),
        ("탭", lambda: (pyautogui.press("tab"), time.sleep(float(delay_autocomplete.get())))),
        ("6229 입력", lambda: (pyautogui.write("6229"), time.sleep(float(delay_autocomplete.get())))),
        ("탭", lambda: (pyautogui.press("tab"), time.sleep(float(delay_autocomplete.get())))),
        ("2975 입력", lambda: (pyautogui.write("2975"), time.sleep(float(delay_autocomplete.get())))),
        ("탭", lambda: (pyautogui.press("tab"), time.sleep(float(delay_autocomplete.get())))),
        ("입금자명 자동완성", lambda: (action_min_yonggi_payment(), time.sleep(float(delay_autocomplete.get())))),
        ("탭", lambda: (pyautogui.press("tab"), time.sleep(float(delay_autocomplete.get())))),
        ("탭", lambda: (pyautogui.press("tab"), time.sleep(float(delay_autocomplete.get())))),
    ]

    total_steps = len(steps)
    for i, (desc, action) in enumerate(steps, start=1):
        if STOP_FLAG:
            add_step_log(f"C{i:02d}", desc, "STOP")
            return

        add_step_log(f"C{i:02d}", desc, "START", f"{i}/{total_steps}")
        try:
            action()
            add_step_log(f"C{i:02d}", desc, "OK")
        except Exception as e:
            add_step_log(f"C{i:02d}", desc, "FAIL", str(e))
            msg.showerror("자동화 단계 오류", f"단계 실패: {desc}\n오류: {e}")
            return

    if receive_mode.get() == "RECEIVE":
        add_step_log("C99", "최종 ENTER", "START")
        pyautogui.press("enter")
        add_step_log("C99", "최종 ENTER", "OK")

    msg.showinfo("완료", "모든 자동화 순서가 완료되었습니다!")

# ============================================================
# 새로고침 루프
# ============================================================

def refresh_loop():
    global STOP_FLAG

    try:
        sh = int(refresh_start_hour.get())
        sm = int(refresh_start_min.get())
        eh = int(refresh_end_hour.get())
        em = int(refresh_end_min.get())
        interval = int(refresh_interval.get())
    except:
        return

    start = datetime.datetime.now().replace(hour=sh, minute=sm, second=0, microsecond=0)
    end = datetime.datetime.now().replace(hour=eh, minute=em, second=0, microsecond=0)

    while datetime.datetime.now() < start:
        if STOP_FLAG:
            return
        time.sleep(1)

    while datetime.datetime.now() < end:
        if STOP_FLAG:
            return

        if REFRESH_PAUSED:
            # Step8 감지/클릭 구간에서는 화면 변경을 멈춰 충돌을 줄인다.
            time.sleep(0.2)
            continue

        pyautogui.click(766, 373)
        time.sleep(float(delay_autocomplete.get()))
        pyautogui.press("f5")

        next_refresh = datetime.datetime.now() + datetime.timedelta(minutes=interval)

        while datetime.datetime.now() < next_refresh:
            if STOP_FLAG:
                return
            time.sleep(1)



# ============================================================
# ESC 긴급 중단
# ============================================================

def stop_automation(source="manual"):
    global STOP_FLAG
    if STOP_FLAG:
        return
    STOP_FLAG = True
    add_log(f"자동화 중단 요청: source={source}")

def esc_listener():
    long_press_sec = 0.7
    press_started_at = None
    triggered_on_this_press = False
    while True:
        pressed = False
        try:
            pressed = keyboard.is_pressed("esc")
        except Exception:
            pressed = False

        # 실행 중 ESC 짧게 눌러도 중단, 길게 눌러도 중단되도록 처리한다.
        if RUNNING and pressed:
            if press_started_at is None:
                press_started_at = time.time()
                triggered_on_this_press = False
            elif not triggered_on_this_press and (time.time() - press_started_at) >= long_press_sec:
                stop_automation(source="esc-long-press")
                triggered_on_this_press = True
        else:
            if RUNNING and press_started_at is not None and not triggered_on_this_press:
                # 짧게 눌렀다가 뗀 경우도 중단
                stop_automation(source="esc-short-press")
            press_started_at = None
            triggered_on_this_press = False

        time.sleep(0.05)

threading.Thread(target=esc_listener, daemon=True).start()

# ============================================================
# 자동화 스레드
# ============================================================

def run_automation_thread(step8_idx, step8_coords, immediate_start=False):
    global STOP_FLAG, RUNNING, sync_done

    try:
        run_automation(step8_idx, step8_coords, immediate_start=immediate_start)
    finally:
        RUNNING = False

def start_automation(immediate_start=False):
    global STOP_FLAG, RUNNING, sync_done

    if RUNNING:
        msg.showwarning("이미 실행 중", "자동화가 이미 실행되고 있습니다.")
        return

    RUNNING = True
    STOP_FLAG = False
    sync_done = False

    # 부서 감지가 필요한 경우 Selenium driver 연결이 필수다.
    if department_var.get().strip():
        global driver, wait
        if driver is None:
            driver = connect_chrome()
            if driver is not None:
                wait = WebDriverWait(driver, 2)
        if driver is None:
            RUNNING = False
            msg.showerror("시작 실패", "부서 텍스트 감지를 위해 Chrome 디버깅 연결이 필요합니다.\nKATO 자동 접속 또는 Chrome 디버깅 실행 후 다시 시도하세요.")
            return

    # Tk 변수는 UI 스레드에서 먼저 읽고 저장한다.
    auto_calculate_times()
    save_extra_settings()
    save_delay_settings()
    save_text_detect_positions()
    check_sync_time()

    step8_idx = int(step8_selected.get())
    detect_idx = dept_detect_selected.get()
    detect_coord = get_department_detect_coord(detect_idx, step8_idx >= 4 and step8_idx <= 9)
    step8_coords = get_step8_coords()
    add_log(
        f"자동화 시작: step8_idx={step8_idx} (0-based), 표시번호={step8_idx + 1}, "
        f"부서감지번호={detect_idx + 1}, 부서감지좌표={detect_coord}, immediate_start={immediate_start}"
    )

    threading.Thread(target=refresh_loop, daemon=True).start()
    threading.Thread(
        target=run_automation_thread,
        args=(step8_idx, step8_coords, immediate_start),
        daemon=True,
    ).start()

# ============================================================
# 좌표 캡처
# ============================================================

def capture_position():
    x, y = pyautogui.position()
    name = simpledialog.askstring("좌표 이름 입력", "이 좌표의 이름을 입력하세요:")
    if not name:
        name = f"좌표{len(captured_positions)+1}"
    captured_positions.append((name, x, y))
    save_positions()
    listbox.insert(tk.END, f"{name} ({x}, {y})")
    msg.showinfo("캡처 완료", f"{name} 저장됨: {x}, {y}")

def show_flow_coordinate_table():
    try:
        step8_idx = int(step8_selected.get())
    except Exception:
        step8_idx = 0

    selected_step8_coord = "미입력"
    if 0 <= step8_idx < len(step8_entries):
        raw = step8_entries[step8_idx].get().strip()
        if raw:
            selected_step8_coord = raw

    detect_idx = int(dept_detect_selected.get())
    detect_coord = get_department_detect_coord(detect_idx, 4 <= step8_idx <= 9)
    detect_coord_text = f"{detect_coord[0]},{detect_coord[1]}" if detect_coord else "미입력"

    rows = [
        ("A", "A01", "목표시간 파싱", "-", "0", "시/분/초 입력값 검증"),
        ("A", "A02", "목표시간까지 대기", "-", "목표시각까지", "목표시각 도달 시 B단계 진입"),
        ("A", "A03", "초기 포커스 클릭", f"{FOCUS_X},{FOCUS_Y}", f"{delay_autocomplete.get()}초", "1회 실행"),
        ("B", "B01", "NAV 클릭", f"{NAV_X},{NAV_Y}", f"{delay_loop_wait.get()}초", "클릭 후 루프 대기"),
        ("B", "B02", "로딩 색상 감지", "95,63", f"최대 {delay_loading.get()}초", f"감지 완료 후 {delay_post_loading.get()}초(+루프 {delay_loop_wait.get()}초) 대기"),
        ("B", "B03", "Step8 목록 이동", f"{STEP8_LIST_X},{STEP8_LIST_Y}", "1.0초", "클릭 후 1.0초 대기"),
        ("B", "B04", "Step8 화면 준비", "PageDown 조건", "1.0초", "선택값 5~10일 때 pagedown 후 안정화"),
        ("B", "B05", "부서 텍스트 감지", detect_coord_text, "즉시", f"선택번호 {detect_idx + 1}"),
        ("B", "B06", "Step8 색상검사+더블클릭", selected_step8_coord, f"{delay_step8.get()}초", f"색상확인/더블클릭 후 대기 | 선택번호 {step8_idx + 1}"),
        ("C", "C01", "로딩 감지(비대기)", "95,63", "즉시", "색상 1회 확인 후 즉시 다음 단계 진행"),
        ("C", "C02", "포커스 고정", f"{FOCUS_X},{FOCUS_Y}", f"{delay_focus_wait.get()}초", "클릭 후 포커스 대기"),
        ("C", "C03", "참가자1 입력 시작", "270,725", f"{delay_autocomplete.get()}초", "더블클릭 + 자동완성"),
        ("C", "C04", "인원/부서 입력1", "270,795", f"{delay_autocomplete.get()}초", "챌린저/개나리: tab | 그 외: tab, 1"),
        ("C", "C05", "참가자2 입력 시작", "270,880", f"{delay_autocomplete.get()}초", "클릭 + 자동완성"),
        ("C", "C06", "인원/부서 입력2", "270,920", f"{delay_autocomplete.get()}초", "챌린저/개나리: tab | 그 외: tab, 1"),
        ("C", "C07", "결제/계좌/입금자 입력", "키보드 입력", f"{delay_autocomplete.get()}초", "0, 6229, 2975, 입금자명"),
        ("C", "C99", "최종 Enter", "Enter", "즉시", "RECEIVE 모드일 때만"),
    ]

    win = tk.Toplevel(root)
    win.title("전체흐름 단계별 좌표표")
    win.geometry("980x520")

    header = tk.Label(
        win,
        text=(
            f"Step8 선택번호: {step8_idx + 1}  |  Step8 좌표: {selected_step8_coord}  |  "
            f"부서감지번호: {detect_idx + 1}  |  부서감지좌표: {detect_coord_text}"
        ),
        anchor="w",
        justify="left",
        font=("Arial", 10, "bold")
    )
    header.pack(fill="x", padx=10, pady=(10, 6))

    columns = ("group", "step", "action", "coord", "wait", "note")
    tree = ttk.Treeview(win, columns=columns, show="headings", height=18)

    tree.heading("group", text="구간")
    tree.heading("step", text="단계")
    tree.heading("action", text="동작")
    tree.heading("coord", text="좌표/입력")
    tree.heading("wait", text="대기시간")
    tree.heading("note", text="조건/설명")

    tree.column("group", width=60, anchor="center")
    tree.column("step", width=80, anchor="center")
    tree.column("action", width=220, anchor="w")
    tree.column("coord", width=150, anchor="center")
    tree.column("wait", width=110, anchor="center")
    tree.column("note", width=340, anchor="w")

    vsb = tk.Scrollbar(win, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)

    for row in rows:
        tree.insert("", "end", values=row)

    tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=(0, 10))
    vsb.pack(side="right", fill="y", padx=(0, 10), pady=(0, 10))

def show_delay_summary_table():
    win = tk.Toplevel(root)
    win.title("딜레이 정리표")
    win.geometry("980x520")

    header = tk.Label(
        win,
        text="클릭/색상감지 후 대기 기준 요약 (여기서 수정 가능)",
        anchor="w",
        justify="left",
        font=("Arial", 10, "bold")
    )
    header.pack(fill="x", padx=10, pady=(10, 6))

    editor = tk.Frame(win)
    editor.pack(fill="x", padx=10, pady=(0, 8))

    tk.Label(editor, text="자동완성").grid(row=0, column=0, padx=(0, 4), pady=2, sticky="e")
    tk.Entry(editor, textvariable=delay_autocomplete, width=8).grid(row=0, column=1, padx=(0, 8), pady=2)
    tk.Label(editor, text="Step8").grid(row=0, column=2, padx=(0, 4), pady=2, sticky="e")
    tk.Entry(editor, textvariable=delay_step8, width=8).grid(row=0, column=3, padx=(0, 8), pady=2)
    tk.Label(editor, text="로딩 타임아웃").grid(row=0, column=4, padx=(0, 4), pady=2, sticky="e")
    tk.Entry(editor, textvariable=delay_loading, width=8).grid(row=0, column=5, padx=(0, 8), pady=2)

    tk.Label(editor, text="루프 대기").grid(row=1, column=0, padx=(0, 4), pady=2, sticky="e")
    tk.Entry(editor, textvariable=delay_loop_wait, width=8).grid(row=1, column=1, padx=(0, 8), pady=2)
    tk.Label(editor, text="감지완료 후").grid(row=1, column=2, padx=(0, 4), pady=2, sticky="e")
    tk.Entry(editor, textvariable=delay_post_loading, width=8).grid(row=1, column=3, padx=(0, 8), pady=2)
    tk.Label(editor, text="포커스 대기").grid(row=1, column=4, padx=(0, 4), pady=2, sticky="e")
    tk.Entry(editor, textvariable=delay_focus_wait, width=8).grid(row=1, column=5, padx=(0, 8), pady=2)

    info_label = tk.Label(editor, text="", fg="blue", anchor="w", justify="left")
    info_label.grid(row=2, column=0, columnspan=8, sticky="w", pady=(4, 0))

    columns = ("category", "item", "wait", "applies")
    tree = ttk.Treeview(win, columns=columns, show="headings", height=14)

    tree.heading("category", text="구분")
    tree.heading("item", text="항목")
    tree.heading("wait", text="대기시간")
    tree.heading("applies", text="적용 구간")

    tree.column("category", width=170, anchor="center")
    tree.column("item", width=180, anchor="center")
    tree.column("wait", width=130, anchor="center")
    tree.column("applies", width=390, anchor="w")

    vsb = tk.Scrollbar(win, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)

    def repopulate_rows():
        tree.delete(*tree.get_children())
        rows = [
            ("공통 클릭", "자동완성 딜레이", f"{delay_autocomplete.get()}초", "대부분 클릭/입력 직후"),
            ("Step8 클릭", "Step8 딜레이", f"{delay_step8.get()}초", "Step8 이동/색상검사/더블클릭 직후"),
            ("로딩 색상 감지(대기)", "타임아웃", f"최대 {delay_loading.get()}초", "RGB=199/199/199 소멸 대기"),
            ("로딩 색상 감지(대기)", "감지 완료 후", f"{delay_post_loading.get()}초", "로딩 완료 직후 UI 안정화"),
            ("반복 루프", "루프 고정 대기", f"{delay_loop_wait.get()}초", "NAV 클릭 후, 로딩 감지 후, 목록 클릭 후"),
            ("로딩 색상 감지(비대기)", "즉시 진행", "0초", "색상 1회 확인 후 즉시 다음 단계"),
            ("포커스 고정", "고정 대기", f"{delay_focus_wait.get()}초", "포커스 클릭 직후"),
        ]

        for row in rows:
            tree.insert("", "end", values=row)

    def apply_delay_values():
        try:
            for var_obj in [delay_autocomplete, delay_step8, delay_loading, delay_loop_wait, delay_post_loading, delay_focus_wait]:
                value = float(var_obj.get())
                if value < 0:
                    raise ValueError("음수는 사용할 수 없습니다.")
            save_delay_settings()
            repopulate_rows()
            info_label.config(text="딜레이 저장 완료: 즉시 실행 로직에 반영됩니다.")
        except Exception:
            msg.showerror("입력 오류", "딜레이는 0 이상의 숫자로 입력하세요.")

    tk.Button(editor, text="딜레이 적용/저장", command=apply_delay_values).grid(row=0, column=6, rowspan=2, padx=(10, 0), pady=2)

    repopulate_rows()

    tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=(0, 10))
    vsb.pack(side="right", fill="y", padx=(0, 10), pady=(0, 10))

# ============================================================
# UI 변수 선언 (UI 코드보다 먼저 있어야 함)
# ============================================================

step8_selected = tk.IntVar(value=0)
dept_detect_selected = tk.IntVar(value=0)
step8_entries = []
text_detect_entries_direct = []
text_detect_entries_pagedown = []
dept_detect_radio_buttons = []

def sync_dept_detect_selection_from_step8(*_):
    dept_detect_selected.set(step8_selected.get())

step8_selected.trace_add("write", sync_dept_detect_selection_from_step8)

receive_mode = tk.StringVar(value="WAIT")
auto_connect_var = tk.BooleanVar(value=False)

hour_var = tk.StringVar(value="23")
min_var = tk.StringVar(value="17")
sec_var = tk.StringVar(value="50")

sync_hour_var = tk.StringVar(value="23")
sync_min_var = tk.StringVar(value="12")

refresh_start_hour = tk.StringVar(value="23")
refresh_start_min = tk.StringVar(value="17")
refresh_end_hour = tk.StringVar(value="23")
refresh_end_min = tk.StringVar(value="12")
refresh_interval = tk.StringVar(value="4")

name1_var = tk.StringVar(value="민용기")
name2_var = tk.StringVar(value="신명식")
payer_var = tk.StringVar(value="민용기")
department_var = tk.StringVar(value="챌린저부")

progress_var = tk.DoubleVar(value=0)
progress_label = None   # ← 이 한 줄 추가하면 오류 100% 해결


# ============================================================
# 프로페셔널 UI 레이아웃 (좌우 대칭 + 스크롤)
# ============================================================

def make_scrollable(parent):
    canvas = tk.Canvas(parent)
    scrollbar = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    scroll_frame = tk.Frame(canvas)
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

    def on_config(event):
        canvas.configure(scrollregion=canvas.bbox("all"))
    scroll_frame.bind("<Configure>", on_config)

    return scroll_frame

main_frame = tk.Frame(root)
main_frame.pack(fill="both", expand=True)

left_container = tk.Frame(main_frame)
left_container.pack(side="left", fill="both", expand=True, padx=5, pady=5)

right_container = tk.Frame(main_frame)
right_container.pack(side="right", fill="both", expand=True, padx=5, pady=5)

left_frame = make_scrollable(left_container)
right_frame = make_scrollable(right_container)

# ============================================================
# LEFT PANEL — 딜레이 / Step8 / 마지막 처리 / 정각 / 새로고침
# ============================================================

# 딜레이 설정
tk.Label(left_frame, text="딜레이 설정", font=("Arial", 12, "bold")).pack(pady=10)

tk.Label(left_frame, text="Step8 딜레이 (초)").pack()
tk.Entry(left_frame, textvariable=delay_step8, width=10).pack()

tk.Label(left_frame, text="자동완성 딜레이 (초)").pack()
tk.Entry(left_frame, textvariable=delay_autocomplete, width=10).pack()

tk.Label(left_frame, text="로딩 타임아웃 (초)").pack()
tk.Entry(left_frame, textvariable=delay_loading, width=10).pack()
tk.Label(left_frame, text="루프 대기 (초)").pack()
tk.Entry(left_frame, textvariable=delay_loop_wait, width=10).pack()
tk.Label(left_frame, text="감지완료 후 대기 (초)").pack()
tk.Entry(left_frame, textvariable=delay_post_loading, width=10).pack()
tk.Label(left_frame, text="포커스 대기 (초)").pack()
tk.Entry(left_frame, textvariable=delay_focus_wait, width=10).pack()
tk.Label(
    left_frame,
    text=(
        "요약: 클릭 후 대기=자동완성 딜레이, "
        "Step8 동작 후 대기=Step8 딜레이, "
        "로딩 감지 완료 후=감지완료 후 대기"
    ),
    fg="gray",
    wraplength=260,
    justify="left"
).pack(pady=(4, 2))

load_delay_settings()

# Step8 좌표 설정
tk.Label(left_frame, text="Step8 좌표 설정 (110 다운)").pack(pady=10)
frame_step8 = tk.Frame(left_frame)
frame_step8.pack()

for i, label in enumerate([
    "바로 1","바로 2","바로 3","바로 4",
    "다운 5","다운 6","다운 7","다운 8",
    "다운 9","다운 10","다운 11"
]):
    tk.Radiobutton(frame_step8, variable=step8_selected, value=i).grid(row=i, column=0)
    tk.Label(frame_step8, text=label).grid(row=i, column=1)
    entry = tk.Entry(frame_step8, width=20)
    entry.grid(row=i, column=2)
    step8_entries.append(entry)

load_step8_positions()

tk.Label(left_frame, text="부서 텍스트 감지 좌표", font=("Arial", 12, "bold")).pack(pady=10)
frame_text_detect = tk.Frame(left_frame)
frame_text_detect.pack()

for i, label in enumerate(["1", "2", "3", "4"]):
    rb = tk.Radiobutton(frame_text_detect, variable=dept_detect_selected, value=i)
    rb.grid(row=i, column=0)
    dept_detect_radio_buttons.append(rb)
    tk.Label(frame_text_detect, text=f"바로 {label}").grid(row=i, column=1)
    entry = tk.Entry(frame_text_detect, width=20)
    entry.grid(row=i, column=2)
    text_detect_entries_direct.append(entry)

for row_idx, label in enumerate(["5", "6", "7", "8", "9", "10", "11"], start=4):
    rb = tk.Radiobutton(frame_text_detect, variable=dept_detect_selected, value=row_idx)
    rb.grid(row=row_idx, column=0)
    dept_detect_radio_buttons.append(rb)
    tk.Label(frame_text_detect, text=f"다운 {label}").grid(row=row_idx, column=1)
    entry = tk.Entry(frame_text_detect, width=20)
    entry.grid(row=row_idx, column=2)
    text_detect_entries_pagedown.append(entry)

load_text_detect_positions()
sync_dept_detect_selection_from_step8()

# 부서 텍스트 감지 좌표는 표시 전용으로 잠근다.
for entry in text_detect_entries_direct + text_detect_entries_pagedown:
    entry.configure(state="disabled")
for rb in dept_detect_radio_buttons:
    rb.configure(state="disabled")

# 마지막 처리 방식
tk.Label(left_frame, text="마지막 처리 방식 선택").pack(pady=10)
tk.Radiobutton(left_frame, text="대기", variable=receive_mode, value="WAIT").pack()
tk.Radiobutton(left_frame, text="접수", variable=receive_mode, value="RECEIVE").pack()

# 정각 설정
tk.Label(left_frame, text="정각 설정 (시/분/초)").pack(pady=10)
tk.Entry(left_frame, textvariable=hour_var, width=5).pack()
tk.Entry(left_frame, textvariable=min_var, width=5).pack()
tk.Entry(left_frame, textvariable=sec_var, width=5).pack()

load_time_settings()

# 🔥 새로고침 설정 (좌측으로 이동됨)
tk.Label(left_frame, text="F5 새로고침 설정", font=("Arial", 12, "bold")).pack(pady=15)

tk.Label(left_frame, text="시작 시").pack()
refresh_start_hour_entry = tk.Entry(left_frame, textvariable=refresh_start_hour, width=5)
refresh_start_hour_entry.pack()

tk.Label(left_frame, text="시작 분").pack()
refresh_start_min_entry = tk.Entry(left_frame, textvariable=refresh_start_min, width=5)
refresh_start_min_entry.pack()

tk.Label(left_frame, text="종료 시").pack()
refresh_end_hour_entry = tk.Entry(left_frame, textvariable=refresh_end_hour, width=5)
refresh_end_hour_entry.pack()

tk.Label(left_frame, text="종료 분").pack()
refresh_end_min_entry = tk.Entry(left_frame, textvariable=refresh_end_min, width=5)
refresh_end_min_entry.pack()

tk.Label(left_frame, text="간격(분)").pack()
refresh_interval_entry = tk.Entry(left_frame, textvariable=refresh_interval, width=5)
refresh_interval_entry.pack()

# F5 새로고침 설정은 표시 전용으로 잠근다.
for entry in [
    refresh_start_hour_entry,
    refresh_start_min_entry,
    refresh_end_hour_entry,
    refresh_end_min_entry,
    refresh_interval_entry,
]:
    entry.configure(state="disabled")

# ============================================================
# RIGHT PANEL — 동기화 / 이름 / 좌표 / 진행률 / 버튼
# ============================================================

status = tk.StringVar(value="")
tk.Label(right_frame, textvariable=status, fg="blue").pack(pady=5)

# PC 시간 동기화
tk.Label(right_frame, text="PC 시간 동기화", font=("Arial", 11, "bold")).pack(pady=5)
tk.Label(right_frame, text="동기화 시").pack()
tk.Entry(right_frame, textvariable=sync_hour_var, width=5).pack()
tk.Label(right_frame, text="동기화 분").pack()
tk.Entry(right_frame, textvariable=sync_min_var, width=5).pack()
tk.Button(right_frame, text="PC 시간 동기화 실행", command=sync_pc_time).pack(pady=8)

# 참가자 이름
tk.Label(right_frame, text="참가자 이름 1").pack(pady=8)
tk.Entry(right_frame, textvariable=name1_var, width=15).pack()

tk.Label(right_frame, text="참가자 이름 2").pack(pady=8)
tk.Entry(right_frame, textvariable=name2_var, width=15).pack()

tk.Label(right_frame, text="입금자 이름").pack(pady=8)
tk.Entry(right_frame, textvariable=payer_var, width=15).pack()

tk.Label(right_frame, text="부서 선택").pack(pady=8)
department_cb = ttk.Combobox(
    right_frame,
    textvariable=department_var,
    state="readonly",
    width=15,
    values=["챌린저부", "지도자부", "베테랑부", "마스터스부", "국화부", "개나리부", "혼합복식부"]
)
department_cb.pack()
department_cb.set(department_var.get())

tk.Button(
    right_frame,
    text="수동 시작 (참가자 입력)",
    command=lambda: threading.Thread(target=run_manual_participants).start(),
    bg="#4CAF50",      # 녹색
    fg="white"         # 글자색 흰색
).pack(pady=10)

# 좌표 캡처
tk.Button(right_frame, text="좌표 캡처(F8)", command=capture_position).pack(pady=5)
root.bind("<F8>", lambda e: capture_position())

tk.Label(right_frame, text="캡처된 좌표 목록").pack(pady=5)
listbox = tk.Listbox(right_frame, width=35, height=8)
listbox.pack()
load_positions()

tk.Button(right_frame, text="선택 좌표 삭제", command=delete_selected_position).pack(pady=3)
tk.Button(right_frame, text="전체 좌표 삭제", command=delete_all_positions).pack(pady=3)
tk.Button(right_frame, text="선택 좌표로 이동", command=move_to_selected_position).pack(pady=3)
tk.Button(right_frame, text="딜레이 정리표 보기", command=show_delay_summary_table).pack(pady=3)
tk.Button(right_frame, text="전체흐름 단계별 좌표표 보기", command=show_flow_coordinate_table).pack(pady=5)

tk.Button(
    right_frame,
    text="자동화 시작",
    command=start_automation,
    bg="#4CAF50",      # 녹색
    fg="white"         # 글자색 흰색
).pack(pady=12)

tk.Button(
    right_frame,
    text="자동화 테스트 (즉시 시작)",
    command=lambda: start_automation(immediate_start=True),
    bg="#1976D2",
    fg="white"
).pack(pady=4)

tk.Button(right_frame, text="백업 저장", command=create_backup).pack(pady=4)
tk.Checkbutton(
    right_frame,
    text="시작 시 자동 접속",
    variable=auto_connect_var
).pack(pady=2)
tk.Button(right_frame, text="KATO 자동 접속", command=open_kato).pack(pady=4)

load_extra_settings()

# 종료 시 저장
def on_close():
    save_step8_positions()
    save_text_detect_positions()
    save_time_settings()
    save_extra_settings()
    save_delay_settings()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)

# 창이 뜨면 체크된 경우에만 1회 자동 접속 실행
root.after(500, auto_connect_on_startup)

root.mainloop()
