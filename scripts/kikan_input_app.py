"""
kikan_input_app.py
生産実績照会 Excel出力2 → 基幹システム(SSE0040) 自動入力アプリ

使用方法:
    python kikan_input_app.py

事前準備:
    pip install pyautogui pyperclip openpyxl pywin32 keyboard
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import json
import time
import ctypes
import keyboard
import pyautogui
from PIL import ImageGrab
import pyperclip
import openpyxl
import win32gui
import win32con
import win32process
import win32api
from pathlib import Path

# ============================================================
# 設定ファイルパス
# ============================================================
CONFIG_FILE  = Path(__file__).parent / "kikan_input_config.json"
LOG_FILE = Path(__file__).parent / "kikan_input_log.txt"

DEFAULT_CONFIG = {
    "window_title":        "SSE0040",
    "tabs_to_hinban":      1,
    "tabs_after_hinban":   1,
    "tabs_to_seisansu":    3,
    "tabs_to_jikan_start": 8,
    "tabs_to_jikan_end":   1,
    "delay_key":           1.0,
    "delay_hinban":        2.0,
    "delay_register":      1.0,
    "countdown_sec":       10,
}


# ============================================================
# 入力ロジック（kikan_input.py から移植）
# ============================================================

class ErrorDialogDetected(Exception):
    """基幹システムのエラーダイアログを検出した場合に送出する例外"""
    pass


def find_window(title_part):
    handles = []
    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            if title_part in win32gui.GetWindowText(hwnd):
                handles.append(hwnd)
    win32gui.EnumWindows(callback, None)
    return handles[0] if handles else None


def activate_window(hwnd):
    """Windowsのフォーカス制限を回避してウィンドウをアクティブ化"""
    # 最小化されていれば復元
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

    # AttachThreadInput でフォーカス権限を移譲してから SetForegroundWindow
    fg_hwnd      = win32gui.GetForegroundWindow()
    fg_thread    = win32process.GetWindowThreadProcessId(fg_hwnd)[0]
    my_thread    = win32api.GetCurrentThreadId()
    tgt_thread   = win32process.GetWindowThreadProcessId(hwnd)[0]

    attached_fg  = fg_thread  != my_thread
    attached_tgt = fg_thread  != tgt_thread

    if attached_fg:
        win32process.AttachThreadInput(fg_thread, my_thread, True)
    if attached_tgt:
        win32process.AttachThreadInput(fg_thread, tgt_thread, True)

    try:
        win32gui.BringWindowToTop(hwnd)
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        # 最終手段: ctypes で強制フォーカス
        ctypes.windll.user32.SetForegroundWindow(hwnd)
    finally:
        if attached_fg:
            win32process.AttachThreadInput(fg_thread, my_thread, False)
        if attached_tgt:
            win32process.AttachThreadInput(fg_thread, tgt_thread, False)

    time.sleep(0.5)


def format_seisanbi(raw):
    if hasattr(raw, 'strftime'):
        return raw.strftime('%Y/%m/%d')
    s = str(int(raw)) if isinstance(raw, float) else str(raw)
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}/{s[4:6]}/{s[6:8]}"
    return s


def format_time(raw):
    if raw is None or str(raw).strip() in ('', '—', '-', 'None'):
        return None
    s = str(int(raw)) if isinstance(raw, float) else str(raw).strip()
    s = s.zfill(4)
    return f"{s[:2]}:{s[2:4]}"


def parse_enter_count(raw, default_value):
    """Enter回数を1〜20の整数に正規化。範囲外/不正値はdefaultにフォールバック"""
    try:
        if raw is None or str(raw).strip() in ('', 'None', '—'):
            return default_value
        parsed = int(float(raw))
    except (TypeError, ValueError):
        return default_value
    if 1 <= parsed <= 20:
        return parsed
    return default_value


def load_excel(filepath):
    wb = openpyxl.load_workbook(filepath)
    ws = wb['生産実績2'] if '生産実績2' in wb.sheetnames else wb.active
    headers = [cell.value for cell in ws[1]]

    records = []
    skipped = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row[0]:
            break
        record = dict(zip(headers, row))
        if record.get('マッピング状態') != '変換済み':
            skipped.append(record.get('アプリ品番', '?'))
            continue
        qty = record.get('生産数量')
        if not qty or (isinstance(qty, (int, float)) and qty <= 0):
            skipped.append(record.get('基幹品番', '?'))
            continue
        records.append(record)

    return records, skipped, ws.title


def wait_for_koukei_blue(hwnd_main, min_wait=0.3, max_wait=8.0, interval=0.1, stop_check=None,
                         log_func=None):
    """品番確定後、工程情報テーブルの青行出現を検知して次へ進む。"""
    time.sleep(min_wait)
    if not hwnd_main:
        return
    try:
        rect = win32gui.GetWindowRect(hwnd_main)
        x, y, x2, y2 = rect
        w, h = x2 - x, y2 - y
        # 工程情報データ行エリア（ヘッダー行より下、右側生産進度を含まない左側のみ）
        region = (x + int(w * 0.03), y + int(h * 0.33), int(w * 0.41), int(h * 0.06))
        if log_func:
            log_func(f"[DEBUG] 工程青検知エリア: ウィンドウ({w}x{h}) 監視region={region}")
        elapsed = min_wait
        first_log = True
        while elapsed < max_wait:
            time.sleep(interval)
            if stop_check:
                stop_check()
            img = ImageGrab.grab(bbox=(region[0], region[1], region[0]+region[2], region[1]+region[3]), all_screens=True)
            pixels = list(img.getdata())
            # 青系ピクセル：青チャンネルが赤より30以上高く、かつ青が80以上
            blue_count = sum(1 for r, g, b in pixels if b > 80 and b > r + 30)
            if log_func and first_log:
                log_func(f"[DEBUG] 青ピクセル数={blue_count}（50超で検知）")
                first_log = False
            if blue_count > 1500:
                # 閾値超え → 安定確認：0.3秒後に再測定して同じ値なら完了
                time.sleep(0.3)
                img2 = ImageGrab.grab(bbox=(region[0], region[1], region[0]+region[2], region[1]+region[3]), all_screens=True)
                blue_count2 = sum(1 for r, g, b in img2.getdata() if b > 80 and b > r + 30)
                if log_func:
                    log_func(f"[DEBUG] 工程青行検知 blue={blue_count}→{blue_count2}")
                if blue_count2 == blue_count:
                    # 2回連続同じ値 → 安定、完了
                    return
                # まだ変化中 → 待機継続
                blue_count = blue_count2
            elapsed += interval
        if log_func:
            log_func(f"[DEBUG] 工程青検知タイムアウト（最終blue={blue_count}）")
    except InterruptedError:
        raise
    except Exception as e:
        if log_func:
            log_func(f"[DEBUG] 工程青検知エラー: {e}")


def wait_for_screen_change(hwnd_main, min_wait=0.3, max_wait=8.0, interval=0.15, stop_check=None,
                           area=None):
    """画面変化を待つ（基幹システムの応答待ち）
    Enter後に基幹システムが応答するまで監視し、変化を検出したら戻る。
    min_wait後から監視開始。max_waitに達してもタイムアウトとして続行。
    stop_checkを渡すと待機中も右クリック解除・Ctrl+P停止が有効になる。
    area: 監視エリアをウィンドウ比率で指定 (top, left, height, width) 例: (0.27, 0.03, 0.13, 0.41)
          Noneの場合はウィンドウ上部全体を監視
    """
    time.sleep(min_wait)
    if not hwnd_main:
        return
    try:
        rect = win32gui.GetWindowRect(hwnd_main)
        x, y, x2, y2 = rect
        w, h = x2 - x, y2 - y
        if area:
            top_r, left_r, h_r, w_r = area
            region = (x + int(w * left_r), y + int(h * top_r), int(w * w_r), int(h * h_r))
        else:
            # デフォルト：ウィンドウ上部全体を監視
            region = (x + 5, y + 30, w - 10, min(250, h - 50))
        bbox = (region[0], region[1], region[0]+region[2], region[1]+region[3])
        before = ImageGrab.grab(bbox=bbox, all_screens=True)
        elapsed = min_wait
        while elapsed < max_wait:
            time.sleep(interval)
            if stop_check:
                stop_check()   # 右クリック解除・Ctrl+P・停止ボタンをここでも処理
            after = ImageGrab.grab(bbox=bbox, all_screens=True)
            if before.tobytes() != after.tobytes():
                time.sleep(0.1)  # 表示安定待ち
                return
            elapsed += interval
        # タイムアウト：そのまま続行
    except InterruptedError:
        raise   # 停止リクエストはそのまま伝播
    except Exception:
        pass


def check_error_dialog(hwnd_main):
    """エラーダイアログが前面に出ていないか確認。出ていればEnterで閉じてErrorDialogDetectedを送出。
    メインウィンドウのタイトルを含む子ウィンドウは誤検知として無視する。
    """
    if not hwnd_main:
        return
    fg = win32gui.GetForegroundWindow()
    if fg != hwnd_main:
        title = win32gui.GetWindowText(fg)
        main_title = win32gui.GetWindowText(hwnd_main)
        # メインアプリのタイトルを含む場合は子ウィンドウ扱いでスキップ
        if main_title and main_title in title:
            return
        # 自アプリ（基幹システム自動入力）がフォアグラウンドになった場合もスキップ
        if '基幹システム自動入力' in title or '基幹自動入力' in title:
            return
        # ダイアログをEnterで閉じる
        pyautogui.press('enter')
        time.sleep(0.3)
        raise ErrorDialogDetected(title)


def input_one_record(record, cfg, hwnd_main=None, stop_check=None, log_func=None):
    delay_key    = cfg["delay_key"]
    delay_hinban = cfg["delay_hinban"]

    def check_stop():
        """停止フラグまたはCtrl+Pで中断"""
        if (stop_check and stop_check()) or keyboard.is_pressed('ctrl+p'):
            raise InterruptedError("停止")

    def next_field(n=1):
        """Enterキーでフィールドを移動（n回）"""
        for _ in range(n):
            check_stop()
            pyautogui.press('enter')
            _poll_sleep(delay_key)

    def clear_input(text):
        check_stop()
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.05)
        pyperclip.copy(str(text))
        pyautogui.hotkey('ctrl', 'v')
        _poll_sleep(delay_key)

    def _poll_sleep(duration, poll_interval=0.1):
        """待機中も0.1秒ごとに右クリック・停止・エラーダイアログをポーリングする"""
        deadline = time.monotonic() + duration
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(poll_interval, remaining))
            check_stop()
            check_error_dialog(hwnd_main)

    seisanbi  = format_seisanbi(record['生産日'])
    hinban    = str(record['基幹品番']).strip()
    koukei    = str(record['工順']).strip()
    seisansu  = str(int(record['生産数量']))
    start_t   = format_time(record.get('開始時間'))
    end_t     = format_time(record.get('終了時間'))

    # 生産日（カーソルはここから開始）
    clear_input(seisanbi)

    # 生産日 → 品番
    next_field(cfg["tabs_to_hinban"])
    clear_input(hinban)

    # 品番入力後 → 工程順位
    # Enter回数はマッピング設定の値を優先、なければアプリ設定値を使用
    # 固定Enterは行わず、ここで指定した回数のみEnterを送る
    enter_count_raw = record.get('工程順行きエンター回数')
    tabs_after_hinban = parse_enter_count(enter_count_raw, cfg["tabs_after_hinban"])
    # デバッグ: Enter回数の確認（動作確認後に削除可）
    print(f"[DEBUG] 品番={hinban} Excel列値={enter_count_raw!r} → Enter回数={tabs_after_hinban}")
    next_field(1)
    # ① 工程情報の青行出現を検知（最大10秒）
    wait_for_koukei_blue(hwnd_main, min_wait=0.3, max_wait=10.0, stop_check=stop_check, log_func=log_func)
    # ② 青行検知後、追加でdelay_hinban秒待機（工程情報の読み込み完全完了を待つ）
    _poll_sleep(delay_hinban)
    check_error_dialog(hwnd_main)

    if tabs_after_hinban >= 2:
        # 工程順位まで追加Enter → 工順入力
        next_field(tabs_after_hinban - 1)
        clear_input(koukei)
        # 工程順位から生産数へ
        next_field(cfg["tabs_to_seisansu"])
    else:
        # Enter1回製品: 工程順位は自動設定 → cursor は加工先にある → 生産数へ
        next_field(cfg["tabs_to_seisansu"] - 1)

    clear_input(seisansu)

    # 生産数 → 加工時間1 開始
    if start_t:
        next_field(cfg["tabs_to_jikan_start"])
        clear_input(start_t)
        if end_t:
            next_field(cfg["tabs_to_jikan_end"])
            clear_input(end_t)

    # F12 登録 → 「入力しますか？」確認ダイアログ → Enter（はい）
    check_stop()
    pyautogui.press('f12')
    wait_for_screen_change(hwnd_main, min_wait=0.3, max_wait=3.0, stop_check=stop_check)   # ダイアログ表示待ち
    pyautogui.press('enter')      # 「はい」を選択
    # ① ダイアログ消去＋ローディングゲージ出現を検知
    wait_for_screen_change(hwnd_main, min_wait=0.2, max_wait=3.0, stop_check=stop_check)
    check_error_dialog(hwnd_main)   # 登録直後にエラーダイアログが出た場合を検知
    # ② ローディングゲージ消滅＝登録完了を検知
    wait_for_screen_change(hwnd_main, min_wait=0.1, max_wait=cfg["delay_register"], stop_check=stop_check)
    check_error_dialog(hwnd_main)   # 登録完了後にエラーダイアログが残っていないか確認

    return seisanbi, hinban, koukei, seisansu


# ============================================================
# GUI アプリ
# ============================================================

class KikanInputApp:
    def __init__(self, root):
        self.root = root
        self.root.title("基幹システム自動入力")
        self.root.resizable(False, False)

        self.cfg = self._load_config()
        self.records = []
        self.history_set   = self._load_history()
        self._stop_flag    = False
        self._running      = False
        self._hotkey_handle = None
        self._mouse_locked = False
        self._right_button_prev = False
        self._right_click_last_time = 0.0

        self._build_ui()

    # ----------------------------------------------------------
    # 設定の読み書き
    # ----------------------------------------------------------
    def _load_config(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, encoding='utf-8') as f:
                    saved = json.load(f)
                cfg = DEFAULT_CONFIG.copy()
                cfg.update(saved)
                return cfg
            except Exception:
                pass
        return DEFAULT_CONFIG.copy()

    def _save_config(self):
        cfg = self._collect_config_from_ui()
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)

    def _collect_config_from_ui(self):
        def iv(var, default):
            try:    return int(var.get())
            except: return default
        def fv(var, default):
            try:    return float(var.get())
            except: return default

        return {
            "window_title":        self.v_window_title.get(),
            "tabs_to_hinban":      iv(self.v_t_hinban,       1),
            "tabs_after_hinban":   iv(self.v_t_after_hinban, 2),
            "tabs_to_seisansu":    iv(self.v_t_seisansu,     5),
            "tabs_to_jikan_start": iv(self.v_t_jikan_start,  5),
            "tabs_to_jikan_end":   iv(self.v_t_jikan_end,    1),
            "delay_key":           fv(self.v_d_key,          0.15),
            "delay_hinban":        fv(self.v_d_hinban,       0.8),
            "delay_register":      fv(self.v_d_register,     1.2),
            "countdown_sec":       iv(self.v_countdown,      5),
        }

    # ----------------------------------------------------------
    # UI 構築
    # ----------------------------------------------------------
    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        # ====== ファイル選択 ======
        frm_file = ttk.LabelFrame(self.root, text="  Excelファイル（出力2）  ")
        frm_file.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 4))

        self.v_filepath = tk.StringVar()
        ttk.Entry(frm_file, textvariable=self.v_filepath, width=55).grid(
            row=0, column=0, **pad)
        ttk.Button(frm_file, text="参照...", command=self._browse_file).grid(
            row=0, column=1, **pad)
        ttk.Button(frm_file, text="読み込み", command=self._load_file,
                   style="Accent.TButton").grid(row=0, column=2, **pad)

        # ====== Tab数設定 ======
        frm_tab = ttk.LabelFrame(self.root, text="  Tab数設定  ★要確認  ")
        frm_tab.grid(row=1, column=0, sticky="ew", padx=10, pady=4)

        tab_items = [
            ("生産日 → 品番",         "v_t_hinban",      "tabs_to_hinban"),
            ("品番確定後 → 工程順位", "v_t_after_hinban","tabs_after_hinban"),
            ("工程順位 → 生産数",     "v_t_seisansu",    "tabs_to_seisansu"),
            ("生産数 → 加工時間開始", "v_t_jikan_start", "tabs_to_jikan_start"),
            ("加工時間開始 → 終了",   "v_t_jikan_end",   "tabs_to_jikan_end"),
        ]
        for i, (label, attr, key) in enumerate(tab_items):
            col = (i % 3) * 2
            row = i // 3
            ttk.Label(frm_tab, text=label).grid(row=row, column=col, sticky="e", padx=(8,2), pady=3)
            var = tk.StringVar(value=str(self.cfg[key]))
            setattr(self, attr, var)
            ttk.Spinbox(frm_tab, textvariable=var, from_=0, to=30, width=4).grid(
                row=row, column=col+1, sticky="w", padx=(0,12), pady=3)

        # ====== 待機時間 ======
        frm_delay = ttk.LabelFrame(self.root, text="  待機時間（秒）  ")
        frm_delay.grid(row=2, column=0, sticky="ew", padx=10, pady=4)

        delay_items = [
            ("キー間",     "v_d_key",      "delay_key",      0.3),
            ("品番確定後", "v_d_hinban",   "delay_hinban",   3.0),
            ("登録後",     "v_d_register", "delay_register", 5.0),
            ("開始前(秒)", "v_countdown",  "countdown_sec",  30),
        ]
        for i, (label, attr, key, max_val) in enumerate(delay_items):
            ttk.Label(frm_delay, text=label).grid(row=0, column=i*2, sticky="e", padx=(8,2), pady=3)
            var = tk.StringVar(value=str(self.cfg[key]))
            setattr(self, attr, var)
            ttk.Entry(frm_delay, textvariable=var, width=6).grid(
                row=0, column=i*2+1, sticky="w", padx=(0,12), pady=3)

        # ====== ウィンドウタイトル ======
        frm_win = ttk.Frame(self.root)
        frm_win.grid(row=3, column=0, sticky="ew", padx=10, pady=2)
        ttk.Label(frm_win, text="基幹ウィンドウタイトル（部分一致）:").grid(row=0, column=0, padx=(0,4))
        self.v_window_title = tk.StringVar(value=self.cfg["window_title"])
        ttk.Entry(frm_win, textvariable=self.v_window_title, width=20).grid(row=0, column=1)
        ttk.Button(frm_win, text="設定保存", command=self._save_config_ui).grid(
            row=0, column=2, padx=(12,0))
        ttk.Button(frm_win, text="ログ表示", command=self._open_log).grid(
            row=0, column=3, padx=(8,0))

        # ====== レコードプレビュー ======
        frm_prev = ttk.LabelFrame(self.root, text="  入力対象レコード  ")
        frm_prev.grid(row=4, column=0, sticky="ew", padx=10, pady=4)

        cols = ("生産日", "基幹品番", "工順", "生産数量", "Enter回数", "開始時間", "終了時間")
        self.tree = ttk.Treeview(frm_prev, columns=cols, show="headings", height=6)
        widths = (90, 120, 50, 70, 60, 70, 70)
        for col, w in zip(cols, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="center")

        vsb = ttk.Scrollbar(frm_prev, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        self.lbl_count = ttk.Label(frm_prev, text="0 件")
        self.lbl_count.grid(row=1, column=0, sticky="w", padx=4, pady=2)

        # ====== 進捗 ======
        frm_prog = ttk.Frame(self.root)
        frm_prog.grid(row=5, column=0, sticky="ew", padx=10, pady=4)

        self.progress_var = tk.IntVar(value=0)
        self.progressbar = ttk.Progressbar(
            frm_prog, variable=self.progress_var,
            maximum=100, length=480, mode="determinate")
        self.progressbar.grid(row=0, column=0, padx=(0,8))

        self.lbl_progress = ttk.Label(frm_prog, text="0 / 0 件", width=12)
        self.lbl_progress.grid(row=0, column=1)

        # ====== ログ ======
        frm_log = ttk.LabelFrame(self.root, text="  ログ  ")
        frm_log.grid(row=6, column=0, sticky="ew", padx=10, pady=4)

        self.log_text = tk.Text(frm_log, height=8, width=72, state="disabled",
                                bg="#1e1e1e", fg="#d4d4d4", font=("Consolas", 9))
        log_sb = ttk.Scrollbar(frm_log, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_sb.set)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        log_sb.grid(row=0, column=1, sticky="ns")

        # ====== ボタン ======
        frm_btn = ttk.Frame(self.root)
        frm_btn.grid(row=7, column=0, pady=(4, 10))

        self.btn_start = ttk.Button(
            frm_btn, text="▶  入力開始", command=self._start,
            width=18, style="Accent.TButton")
        self.btn_start.grid(row=0, column=0, padx=8)

        self.btn_stop = ttk.Button(
            frm_btn, text="■  停止", command=self._stop,
            width=12, state="disabled")
        self.btn_stop.grid(row=0, column=1, padx=8)

        self.lbl_status = ttk.Label(frm_btn, text="待機中", foreground="gray")
        self.lbl_status.grid(row=0, column=2, padx=16)

        ttk.Button(frm_btn, text="？  ヘルプ", command=self._show_help,
                   width=12).grid(row=0, column=3, padx=8)

    # ----------------------------------------------------------
    # ヘルプ
    # ----------------------------------------------------------
    def _show_help(self):
        """ヘルプウィンドウを表示"""
        win = tk.Toplevel(self.root)
        win.title("使い方・マニュアル")
        win.resizable(True, True)
        win.attributes("-topmost", True)

        # 画面中央
        win.update_idletasks()
        w, h = 700, 600
        sx = self.root.winfo_screenwidth()
        sy = self.root.winfo_screenheight()
        win.geometry(f"{w}x{h}+{(sx-w)//2}+{(sy-h)//2}")

        txt = tk.Text(win, wrap="word", font=("Yu Gothic UI", 10),
                      bg="#fafafa", fg="#222", padx=12, pady=8,
                      spacing1=2, spacing3=4)
        sb = ttk.Scrollbar(win, command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        txt.pack(side="left", fill="both", expand=True)

        # タグ定義
        txt.tag_configure("h1",  font=("Yu Gothic UI", 16, "bold"), foreground="#1a1a6e", spacing1=8, spacing3=4)
        txt.tag_configure("h2",  font=("Yu Gothic UI", 13, "bold"), foreground="#1a5276", spacing1=10, spacing3=2)
        txt.tag_configure("h3",  font=("Yu Gothic UI", 11, "bold"), foreground="#1f618d", spacing1=6, spacing3=2)
        txt.tag_configure("th",  font=("Yu Gothic UI", 10, "bold"), foreground="#555", background="#e8eaf6")
        txt.tag_configure("td",  font=("Yu Gothic UI", 10))
        txt.tag_configure("sep", foreground="#cccccc")
        txt.tag_configure("key", font=("Consolas", 10, "bold"), foreground="#c0392b", background="#fdf2f8")
        txt.tag_configure("note", foreground="#7d6608", background="#fef9e7")

        def ins(text, tag=None):
            if tag:
                txt.insert("end", text, tag)
            else:
                txt.insert("end", text)

        ins("基幹システム自動入力ツール  使い方\n", "h1")
        ins("─" * 60 + "\n", "sep")

        ins("\n【概要】\n", "h2")
        ins("生産実績照会の「基幹システム入力用Excel」を読み込み、\n基幹システム（SSE0040）へ自動でキー入力するツールです。\n\n")

        ins("【使用手順】\n", "h2")
        ins("① ", "th"); ins("生産管理アプリにログイン → 生産実績照会 → 担当班（ライン）タブを開く\n")
        ins("② ", "th"); ins("「基幹システム入力用Excel」をクリックしてExcelをダウンロード・保存\n")
        ins("③ ", "th"); ins("基幹システムにログイン → 生産管理 → 生産実績入力（SSE0040）を開く\n")
        ins("④ ", "th"); ins("「基幹自動入力.exe」を起動する\n")
        ins("⑤ ", "th"); ins("「参照...」で②のExcelファイルを選択 → 「読み込み」\n")
        ins("⑥ ", "th"); ins("プレビューで入力対象レコード・Enter回数を確認\n")
        ins("⑦ ", "th"); ins("「▶ 入力開始」をクリック\n")
        ins("⑧ ", "th"); ins("カウントダウン中に基幹システムに切り替えて生産日フィールドにカーソルを置く\n")
        ins("⑨ ", "th"); ins("カウントダウン終了後、自動入力開始（マウスが固定される）\n\n")

        ins("【入力中の操作】\n", "h2")
        ins("  右クリック 1回  ", "key"); ins(" … マウス固定を解除（入力は継続）\n")
        ins("  右ダブルクリック", "key"); ins(" … 即座に停止\n")
        ins("  Ctrl + P        ", "key"); ins(" … 停止リクエスト\n")
        ins("  マウスを左上角  ", "key"); ins(" … フェイルセーフ緊急停止\n\n")

        ins("【エラーダイアログ検出時の動作】\n", "h2")
        ins("  登録後に基幹システムのエラーダイアログ（例:「日付の入力が不正です。」）を検出した場合、\n"
            "  自動的に入力を中止します。ログに以下の情報を記録します：\n\n")
        ins("  ★ エラーダイアログ検出により入力を中止しました\n", "key")
        ins("    行=X/Y  品番=XXXX  工順=X\n"
            "    ダイアログ内容: [エラーメッセージ]\n\n")
        ins("  ※ 中止後は該当レコードの入力内容を基幹システム側で確認・手動入力してください。\n\n", "note")

        ins("【Enter回数設定】  ※通常は変更不要（デフォルト値で動作します）\n", "h2")
        ins("  デフォルト値は以下のとおりです。基幹画面のレイアウトが変わった場合のみ変更してください。\n\n", "note")
        rows = [
            ("生産日 → 品番",         "1",  "生産日入力後、品番フィールドまでのEnter回数"),
            ("品番確定後 → 工程順位", "1",  "Excelの「工程順行きエンター回数」列の値が優先される"),
            ("工程順位 → 生産数",     "3",  "工程順位入力後、生産数フィールドまでのEnter回数"),
            ("生産数 → 加工時間開始", "8",  "生産数入力後、加工時間開始フィールドまでのEnter回数"),
            ("加工時間開始 → 終了",   "1",  "加工時間開始後、終了フィールドまでのEnter回数"),
        ]
        for label, default, desc in rows:
            ins(f"  {label:<18}", "th")
            ins(f"  デフォルト:", "td")
            ins(f" {default} ", "key")
            ins(f"  {desc}\n", "td")
        ins("\n")

        ins("【Enter回数（品番確定後）の仕様】\n", "h3")
        ins("  2回以上 → 品番確定 → Enter追加 → 工程順位入力 → 生産数へ\n")
        ins("  1回     → 品番確定後カーソルは「加工先」へ移動（工程順位は自動）→ 生産数へ\n\n")

        ins("【待機時間】  ※通常は変更不要（デフォルト値で動作します）\n", "h2")
        ins("  「品番確定後」は工程情報の青行が安定表示された後の追加待機時間です。\n"
            "  「登録後」は「はい」押下後のローディングゲージ消滅（2段階画面変化検知）の最大待機時間です。\n"
            "  基幹システムが極端に重い場合のみ値を大きくしてください。\n\n", "note")
        rows2 = [
            ("キー間",      "1.0秒",  "各キー入力間の待機時間"),
            ("品番確定後",  "2.0秒",  "工程情報の青行が安定後、さらに待機する秒数"),
            ("登録後",      "1.0秒",  "「はい」後のローディングゲージ消滅までの最大待機時間"),
            ("開始前",      "10秒",   "入力開始前カウントダウン秒数"),
        ]
        for name, default, desc in rows2:
            ins(f"  {name:<10}", "th")
            ins(f"  デフォルト:", "td")
            ins(f" {default} ", "key")
            ins(f"  {desc}\n", "td")
        ins("\n")

        ins("【注意事項】\n", "h2")
        ins("  ⚠ 入力中はキーボード・マウス操作をしないこと（誤入力の原因）\n", "note")
        ins("  ⚠ 基幹システムの画面を前面に保つこと（別ウィンドウが前面に出ると入力がずれる）\n", "note")
        ins("  ⚠ 入力結果は必ず基幹システム側で確認すること（登録成否の完全な保証はない）\n", "note")
        ins("  ⚠ 設定は kikan_input_config.json に保存されます\n", "note")
        ins("\n")

        ins("【トラブルシューティング】\n", "h2")
        troubles = [
            ("基幹ウィンドウが見つからない", "SSE0040を開いてから再実行。ウィンドウタイトルを確認"),
            ("入力がズレる",                 "Enter回数設定を見直す。手動で同品番を入力してEnter回数を数える"),
            ("品番確定後にエラー",           "品番が正しくない or 基幹に登録されていない品番"),
            ("動作が遅い / 入力が抜ける",    "「キー間」待機時間を増やす"),
            ("品番確定後・登録後に止まる",   "「品番確定後」「登録後」の待機時間を増やす"),
            ("途中で止まる",                 "ログを確認。エラーダイアログ検出により中止した場合は行番号・品番がログに記録されている"),
        ]
        for symptom, solution in troubles:
            ins(f"  症状: {symptom}\n", "th")
            ins(f"         → {solution}\n\n", "td")

        txt.config(state="disabled")
        ttk.Button(win, text="閉じる", command=win.destroy).pack(pady=6)

    # ----------------------------------------------------------
    # ファイル操作
    # ----------------------------------------------------------
    def _browse_file(self):
        path = filedialog.askopenfilename(
            title="Excel出力2ファイルを選択",
            filetypes=[("Excelファイル", "*.xlsx *.xls"), ("すべて", "*.*")]
        )
        if path:
            self.v_filepath.set(path)
            self._load_file()

    def _load_file(self):
        path = self.v_filepath.get().strip()
        if not path or not Path(path).exists():
            messagebox.showerror("エラー", "ファイルが見つかりません")
            return
        try:
            records, skipped, sheet = load_excel(path)
            self.records = records

            # ログとの重複チェック（ファイル内重複は無視、ログ既存分のみ）
            dup_keys = set()
            for r in records:
                key = (format_seisanbi(r['生産日']), str(r.get('工程コード', '')).strip())
                if key in self.history_set:
                    dup_keys.add(key)

            # ツリー更新
            for row in self.tree.get_children():
                self.tree.delete(row)
            self.tree.tag_configure("duplicate", background="#ffe0b2")
            for r in records:
                ec_raw = r.get('工程順行きエンター回数')
                ec = parse_enter_count(ec_raw, self.cfg["tabs_after_hinban"])
                key = (format_seisanbi(r['生産日']), str(r.get('工程コード', '')).strip())
                tags = ("duplicate",) if key in dup_keys else ()
                self.tree.insert("", "end", tags=tags, values=(
                    format_seisanbi(r['生産日']),
                    r['基幹品番'],
                    r['工順'],
                    int(r['生産数量']),
                    ec,
                    format_time(r.get('開始時間')) or '',
                    format_time(r.get('終了時間')) or '',
                ))

            msg = f"{len(records)} 件"
            if skipped:
                msg += f"  （スキップ {len(skipped)} 件）"
            if dup_keys:
                msg += f"  （入力済み {len(dup_keys)} 組み合わせあり）"
            self.lbl_count.config(text=msg)
            self._log(f"読み込み完了: {len(records)} 件  シート={sheet}")
            if skipped:
                self._log(f"スキップ: {', '.join(skipped[:5])}" +
                          (" ..." if len(skipped) > 5 else ""))
            if dup_keys:
                lines = "\n".join(f"  生産日: {k[0]}  工程コード: {k[1]}" for k in sorted(dup_keys))
                messagebox.showwarning(
                    "入力済み確認",
                    f"以下の組み合わせはすでにログに記録されています。\n\n{lines}\n\n"
                    f"重複入力の可能性があります。確認してください。"
                )

        except Exception as e:
            messagebox.showerror("読み込みエラー", str(e))
            self._log(f"エラー: {e}")

    # ----------------------------------------------------------
    # ログ表示
    # ----------------------------------------------------------
    def _open_log(self):
        if not LOG_FILE.exists():
            messagebox.showinfo("ログ", "まだログファイルがありません")
            return
        import os
        os.startfile(LOG_FILE)

    # ----------------------------------------------------------
    # 設定保存
    # ----------------------------------------------------------
    def _save_config_ui(self):
        self.cfg = self._collect_config_from_ui()
        self._save_config()
        self._log("設定を保存しました")
        messagebox.showinfo("保存", "設定を保存しました")

    # ----------------------------------------------------------
    # 入力開始 / 停止
    # ----------------------------------------------------------
    def _start(self):
        if not self.records:
            messagebox.showwarning("注意", "先にExcelファイルを読み込んでください")
            return

        self.cfg = self._collect_config_from_ui()

        # 基幹ウィンドウ確認
        hwnd = find_window(self.cfg["window_title"])
        if not hwnd:
            messagebox.showerror(
                "エラー",
                f"基幹システムのウィンドウが見つかりません\n"
                f"（検索タイトル: '{self.cfg['window_title']}'）\n\n"
                f"SSE0040を開いてから再実行してください"
            )
            return

        title = win32gui.GetWindowText(hwnd)
        self._log(f"基幹システム検出: {title}")

        self._stop_flag = False
        self._running   = True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.progress_var.set(0)

        # バックグラウンドスレッドで実行
        t = threading.Thread(target=self._run_input, args=(hwnd,), daemon=True)
        t.start()

    def _stop(self):
        self._stop_flag = True
        self._log("★ 停止リクエストを送信しました...")
        # tkinter UIはメインスレッドからのみ操作可（keyboard コールバック対応）
        self.root.after(0, lambda: self.lbl_status.config(text="停止中...", foreground="orange"))

    def _lock_mouse_cursor(self):
        """現在位置にマウスカーソルを固定する（右クリックで解除可能）"""
        if self._mouse_locked:
            return
        x, y = win32gui.GetCursorPos()

        class RECT(ctypes.Structure):
            _fields_ = [
                ('left', ctypes.c_long),
                ('top', ctypes.c_long),
                ('right', ctypes.c_long),
                ('bottom', ctypes.c_long),
            ]

        rect = RECT(x, y, x + 1, y + 1)
        ctypes.windll.user32.ClipCursor(ctypes.byref(rect))
        self._mouse_locked = True

    def _unlock_mouse_cursor(self):
        """マウス固定を解除する"""
        if not self._mouse_locked:
            return
        ctypes.windll.user32.ClipCursor(None)
        self._mouse_locked = False

    def _poll_right_click_unlock(self):
        """右クリック: マウス固定解除 / 右ダブルクリック: 停止
        GetAsyncKeyStateの低ビット(前回呼び出し後に押された記録)も使い、
        ポーリング間の短いクリックを確実に検出する。
        """
        state = win32api.GetAsyncKeyState(win32con.VK_RBUTTON)
        is_pressed       = bool(state & 0x8000)  # 現在押下中
        pressed_since_last = bool(state & 0x0001)  # 前回呼び出し後に押されたか

        # 立ち上がりエッジ: 現在押下かつ前回未押下 or 前回呼び出し後に押した記録
        rising_edge = (is_pressed and not self._right_button_prev) or \
                      (pressed_since_last and not is_pressed)

        if rising_edge:
            now = time.monotonic()
            if (now - self._right_click_last_time) < 0.4:
                # ダブルクリック → 停止
                self._stop_flag = True
                self._unlock_mouse_cursor()
                self._log("★ 右ダブルクリックで停止しました")
            else:
                # シングルクリック → マウス固定解除
                if self._mouse_locked:
                    self._unlock_mouse_cursor()
                    self._log("★ 右クリックでマウス固定を解除しました")
            self._right_click_last_time = now
        self._right_button_prev = is_pressed

    def _show_countdown_popup(self, seconds, cancel_event):
        """カウントダウンポップアップをメインスレッドで表示"""
        popup = tk.Toplevel(self.root)
        popup.title("入力開始まで")
        popup.resizable(False, False)
        popup.attributes("-topmost", True)

        # 画面中央に配置
        popup.update_idletasks()
        w, h = 340, 220
        sx = self.root.winfo_screenwidth()
        sy = self.root.winfo_screenheight()
        popup.geometry(f"{w}x{h}+{(sx-w)//2}+{(sy-h)//2}")

        tk.Label(popup, text="基幹システムの\n生産日にカーソルを置いてください",
                 font=("Yu Gothic UI", 12), fg="#333").pack(pady=(18, 6))

        lbl_num = tk.Label(popup, text=str(seconds),
                           font=("Yu Gothic UI", 56, "bold"), fg="#e05c00")
        lbl_num.pack()

        tk.Label(popup, text="秒後に入力を開始します",
                 font=("Yu Gothic UI", 10), fg="#555").pack(pady=(0, 4))

        tk.Label(popup, text="停止: Ctrl+P",
                 font=("Yu Gothic UI", 9), fg="#888").pack(pady=(0, 8))

        self._countdown_popup  = popup
        self._countdown_label  = lbl_num

    def _update_countdown_label(self, val):
        try:
            self._countdown_label.config(text=str(val))
        except Exception:
            pass

    def _close_countdown_popup(self):
        try:
            self._countdown_popup.destroy()
        except Exception:
            pass

    def _run_input(self, hwnd):
        """入力処理（別スレッド）"""
        countdown    = int(self.cfg.get("countdown_sec", 5))
        cancel_event = threading.Event()

        # ポップアップをメインスレッドで表示
        self.root.after(0, lambda: self._show_countdown_popup(countdown, cancel_event))
        self._log(f"★ {countdown}秒後に開始します。基幹の生産日にカーソルを置いてください。")
        self._log("★ 停止: Ctrl+P  /  緊急停止: マウスを画面の左上角に移動")
        self._log("★ 入力開始後はマウス固定（右クリックで解除）")

        for i in range(countdown, 0, -1):
            if self._stop_flag or cancel_event.is_set():
                self.root.after(0, self._close_countdown_popup)
                self._finish(0, 0, stopped=True)
                return
            self.root.after(0, lambda v=i: self._update_countdown_label(v))
            time.sleep(1)

        self.root.after(0, self._close_countdown_popup)

        pyautogui.FAILSAFE = True
        self._right_button_prev = False
        self._lock_mouse_cursor()
        total   = len(self.records)
        success = 0
        errors  = 0

        # 停止判定関数（停止ボタン / Ctrl+P どちらでも止まる）
        def should_stop():
            self._poll_right_click_unlock()
            return self._stop_flag or keyboard.is_pressed('ctrl+p')

        for i, record in enumerate(self.records):
            self._poll_right_click_unlock()
            if should_stop():
                self._stop_flag = True
                break

            self._set_status(f"入力中 {i+1}/{total}", "blue")
            process_code_check = str(record.get('工程コード', '')).strip()

            self._log(f"[{i+1}/{total}] 品番={record['基幹品番']}  "
                      f"工順={record['工順']}  生産数={int(record['生産数量'])}")

            try:
                seisanbi, _, _, _ = input_one_record(
                    record, self.cfg, hwnd_main=hwnd, stop_check=should_stop, log_func=self._log)
                success += 1
                self._record_history(seisanbi, process_code_check)
                self._log(f"  → 登録OK  生産日={seisanbi}")
            except InterruptedError:
                # 停止ボタン / Ctrl+P による中断
                self._stop_flag = True
                self._log("★ 入力中に停止しました")
                break
            except ErrorDialogDetected as e:
                # 基幹エラーダイアログ検出 → 中止
                self._stop_flag = True
                self._log(
                    f"★ エラーダイアログ検出により入力を中止しました\n"
                    f"  行={i+1}/{total}  品番={record['基幹品番']}  工順={record['工順']}\n"
                    f"  ダイアログ内容: [{e}]"
                )
                break
            except pyautogui.FailSafeException:
                self._log("★★ フェイルセーフ発動 - 緊急停止 ★★")
                break
            except Exception as e:
                errors += 1
                self._log(f"  → エラー: {e}")

            # 進捗更新
            pct = int((i + 1) / total * 100)
            self.root.after(0, lambda p=pct, c=i+1, t=total: (
                self.progress_var.set(p),
                self.lbl_progress.config(text=f"{c} / {t} 件")
            ))

        self._finish(success, errors)

    def _finish(self, success, errors, stopped=False):
        self._unlock_mouse_cursor()
        self._running = False
        self.root.after(0, lambda: (
            self.btn_start.config(state="normal"),
            self.btn_stop.config(state="disabled"),
        ))
        if stopped:
            self._log("入力を停止しました")
            self._set_status("停止", "red")
        else:
            msg = f"完了: 成功={success}件  エラー={errors}件"
            self._log(f"===== {msg} =====")
            self._set_status(msg, "green" if errors == 0 else "orange")
            self.root.after(0, lambda: messagebox.showinfo("完了", msg))

    # ----------------------------------------------------------
    # 入力履歴記録
    # ----------------------------------------------------------
    def _ask_duplicate(self, seisanbi, process_code):
        """重複確認ダイアログをメインスレッドで表示し、スキップするか否かを返す"""
        result = [None]
        event  = threading.Event()

        def show():
            answer = messagebox.askyesno(
                "入力済み確認",
                f"この組み合わせはすでに入力済みです。\n\n"
                f"  生産日　　: {seisanbi}\n"
                f"  工程コード: {process_code}\n\n"
                f"スキップしますか？\n（「いいえ」を選ぶと入力を続行します）"
            )
            result[0] = answer  # True=スキップ / False=入力する
            event.set()

        self.root.after(0, show)
        event.wait()
        return result[0]

    def _load_history(self):
        """ログファイルから処理済み (生産日, 工程コード) をセットとして読み込む"""
        result = set()
        if not LOG_FILE.exists():
            return result
        try:
            with open(LOG_FILE, encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split(',')
                    if len(parts) >= 2 and parts[0] != '生産日':
                        result.add((parts[0], parts[1]))
        except Exception:
            pass
        return result

    def _record_history(self, seisanbi, process_code):
        """入力済み履歴をログファイルに追記し、メモリ上のセットにも追加する"""
        from datetime import datetime
        input_dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            write_header = not LOG_FILE.exists()
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                if write_header:
                    f.write('生産日,工程コード,入力日時\n')
                f.write(f'{seisanbi},{process_code},{input_dt}\n')
            self.history_set.add((seisanbi, process_code))
        except Exception as e:
            self._log(f"履歴保存エラー: {e}")

    # ----------------------------------------------------------
    # UI更新ヘルパー（スレッドセーフ）
    # ----------------------------------------------------------
    def _log(self, msg):
        def _do():
            self.log_text.config(state="normal")
            self.log_text.insert("end", msg + "\n")
            self.log_text.see("end")
            self.log_text.config(state="disabled")
        self.root.after(0, _do)

    def _set_status(self, msg, color="black"):
        self.root.after(0, lambda: self.lbl_status.config(text=msg, foreground=color))


# ============================================================
# エントリーポイント
# ============================================================

def main():
    root = tk.Tk()

    # テーマ（Windowsで見やすいもの）
    style = ttk.Style()
    try:
        style.theme_use('vista')
    except Exception:
        pass

    app = KikanInputApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
