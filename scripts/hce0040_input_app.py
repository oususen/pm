"""
hce0040_input_app.py
仕入先納入実績 → 基幹システム(HCE0040)自動入力アプリ

使用方法:
    python hce0040_input_app.py

事前準備:
    pip install pyautogui pyperclip openpyxl pywin32 keyboard pillow
"""

import ctypes
import json
import threading
import time
from datetime import datetime
from pathlib import Path

import keyboard
import openpyxl
import pyautogui
import pyperclip
import win32api
import win32con
import win32gui
import win32process
from PIL import ImageGrab

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

CONFIG_FILE = Path(__file__).parent / "hce0040_input_config.json"
LOG_FILE    = Path(__file__).parent / "hce0040_input_log.txt"

DEFAULT_CONFIG = {
    "window_title":   "HCE0040",
    "delay_key":      1.0,
    "delay_hinban":   2.0,
    "delay_register": 1.5,
    "countdown_sec":  10,
}

SHEET_NAME = "仕入先納入実績"

# ============================================================
# 例外
# ============================================================
class ErrorDialogDetected(Exception):
    pass


# ============================================================
# ウィンドウ操作
# ============================================================
def find_window(title_part):
    handles = []
    def cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd) and title_part in win32gui.GetWindowText(hwnd):
            handles.append(hwnd)
    win32gui.EnumWindows(cb, None)
    return handles[0] if handles else None


def activate_window(hwnd):
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    fg_hwnd   = win32gui.GetForegroundWindow()
    fg_thread = win32process.GetWindowThreadProcessId(fg_hwnd)[0]
    my_thread = win32api.GetCurrentThreadId()
    tgt_thread = win32process.GetWindowThreadProcessId(hwnd)[0]
    a_fg  = fg_thread != my_thread
    a_tgt = fg_thread != tgt_thread
    if a_fg:  win32process.AttachThreadInput(fg_thread, my_thread,  True)
    if a_tgt: win32process.AttachThreadInput(fg_thread, tgt_thread, True)
    try:
        win32gui.BringWindowToTop(hwnd)
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        ctypes.windll.user32.SetForegroundWindow(hwnd)
    finally:
        if a_fg:  win32process.AttachThreadInput(fg_thread, my_thread,  False)
        if a_tgt: win32process.AttachThreadInput(fg_thread, tgt_thread, False)
    time.sleep(0.5)


# ============================================================
# フォーマット
# ============================================================
def format_nyukobi(raw):
    """YYYYMMDD → YYYY/MM/DD"""
    s = str(int(raw)) if isinstance(raw, float) else str(raw).strip()
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}/{s[4:6]}/{s[6:8]}"
    return s


# ============================================================
# 画面検知
# ============================================================
def wait_for_screen_change(hwnd, min_wait=0.3, max_wait=8.0, interval=0.15, stop_check=None):
    time.sleep(min_wait)
    if not hwnd:
        return
    try:
        rect = win32gui.GetWindowRect(hwnd)
        x, y, x2, y2 = rect
        w, h = x2 - x, y2 - y
        bbox = (x + 5, y + 30, x + w - 10, y + min(250, h - 50))
        before = ImageGrab.grab(bbox=bbox, all_screens=True)
        elapsed = min_wait
        while elapsed < max_wait:
            time.sleep(interval)
            if stop_check:
                stop_check()
            after = ImageGrab.grab(bbox=bbox, all_screens=True)
            if before.tobytes() != after.tobytes():
                time.sleep(0.1)
                return
            elapsed += interval
    except InterruptedError:
        raise
    except Exception:
        pass


def check_error_dialog(hwnd):
    if not hwnd:
        return
    fg = win32gui.GetForegroundWindow()
    if fg != hwnd:
        title = win32gui.GetWindowText(fg)
        main_title = win32gui.GetWindowText(hwnd)
        if main_title and main_title in title:
            return
        if 'HCE0040自動入力' in title or 'hce0040' in title.lower():
            return
        pyautogui.press('enter')
        time.sleep(0.3)
        raise ErrorDialogDetected(title)


# ============================================================
# 1レコード入力
# ============================================================
def input_one_record(record, cfg, hwnd=None, stop_check=None, log_func=None):
    """
    G外作:
        入荷日 → Tab → 品番 → Tab×tabs_after_hinban → 仕入先コード → Tab → Tab → 入荷数 → F12
    K購入:
        入荷日 → Tab → 品番 → Tab×tabs_after_hinban → 仕入先コード → Tab → Tab → 入荷数 → Tab → F12
    """
    delay_key    = cfg["delay_key"]
    delay_hinban = cfg["delay_hinban"]

    def check_stop():
        if (stop_check and stop_check()) or keyboard.is_pressed('ctrl+p'):
            raise InterruptedError("停止")

    def tab_to(n=1):
        for _ in range(n):
            check_stop()
            pyautogui.press('tab')
            _poll_sleep(delay_key)

    def input_field(text):
        check_stop()
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.05)
        pyperclip.copy(str(text))
        pyautogui.hotkey('ctrl', 'v')
        _poll_sleep(delay_key)

    def _poll_sleep(duration, poll=0.1):
        deadline = time.monotonic() + duration
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(poll, remaining))
            check_stop()
            check_error_dialog(hwnd)

    nyukobi      = format_nyukobi(record['入荷日'])
    kikan_hinban = str(record['基幹品番']).strip()
    supplier_cd  = str(record['仕入先コード']).strip()
    tabs_hinban  = int(record['品番後Tabキー回数'] or 1)
    tabs_nyuuko  = int(record['入荷数後Tabキー回数'] or 0)
    nyuuko_su    = str(int(float(record['入荷数'])))

    # 入荷日
    input_field(nyukobi)
    # 入荷日 → 品番
    tab_to(1)
    input_field(kikan_hinban)
    # 品番確定後 待機
    tab_to(1)
    wait_for_screen_change(hwnd, min_wait=0.3, max_wait=cfg["delay_hinban"], stop_check=stop_check)
    _poll_sleep(delay_hinban * 0.5)
    check_error_dialog(hwnd)
    # 追加Tab（2か所=2のとき1回追加）
    if tabs_hinban >= 2:
        tab_to(tabs_hinban - 1)
    # 仕入先コード
    input_field(supplier_cd)
    # 仕入先コード → 入荷数（Tab×2）
    tab_to(2)
    # 入荷数
    input_field(nyuuko_su)
    # 入荷数後Tab（K=1回）
    if tabs_nyuuko >= 1:
        tab_to(tabs_nyuuko)
    # F12 登録
    check_stop()
    pyautogui.press('f12')
    wait_for_screen_change(hwnd, min_wait=0.3, max_wait=3.0, stop_check=stop_check)
    pyautogui.press('enter')  # 確認ダイアログ「はい」
    wait_for_screen_change(hwnd, min_wait=0.2, max_wait=3.0, stop_check=stop_check)
    check_error_dialog(hwnd)
    wait_for_screen_change(hwnd, min_wait=0.1, max_wait=cfg["delay_register"], stop_check=stop_check)
    check_error_dialog(hwnd)


# ============================================================
# Excel 読み込み
# ============================================================
def load_excel(filepath):
    wb = openpyxl.load_workbook(filepath)
    ws = wb[SHEET_NAME] if SHEET_NAME in wb.sheetnames else wb.active
    headers = [str(cell.value or '').strip() for cell in ws[1]]
    required = {'マッピング状態', '入荷日', '基幹品番', '仕入先コード', '品番後Tabキー回数', '入荷数後Tabキー回数', '入荷数'}
    missing = required - set(headers)
    if missing:
        raise ValueError(f"必要な列が見つかりません: {', '.join(missing)}")

    records, skipped, unmapped = [], [], []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row[0]:
            break
        record = dict(zip(headers, row))
        status = str(record.get('マッピング状態') or '').strip()
        if status != '変換済み':
            code = str(record.get('アプリ品番') or record.get('基幹品番') or '?').strip()
            if status == '未設定':
                unmapped.append(code)
            else:
                skipped.append(code)
            continue
        qty = record.get('入荷数')
        if not qty or (isinstance(qty, (int, float)) and qty <= 0):
            skipped.append(str(record.get('基幹品番') or '?'))
            continue
        records.append(record)

    return records, skipped, unmapped


# ============================================================
# GUI アプリ
# ============================================================
class HCE0040InputApp:
    def __init__(self, root):
        self.root = root
        self.root.title("HCE0040 仕入先納入自動入力")
        self.root.resizable(False, False)
        self.cfg = self._load_config()
        self.records = []
        self._stop_flag  = False
        self._running    = False
        self._mouse_locked = False
        self._right_button_prev = False
        self._right_click_last_time = 0.0
        self._build_ui()

    # ---- 設定 ----
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
        def iv(var, d):
            try: return int(var.get())
            except: return d
        def fv(var, d):
            try: return float(var.get())
            except: return d
        return {
            "window_title":   self.v_window_title.get(),
            "delay_key":      fv(self.v_d_key,      1.0),
            "delay_hinban":   fv(self.v_d_hinban,   2.0),
            "delay_register": fv(self.v_d_register, 1.5),
            "countdown_sec":  iv(self.v_countdown,  10),
        }

    # ---- UI 構築 ----
    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        # ファイル選択
        frm_file = ttk.LabelFrame(self.root, text="  Excelファイル（仕入先納入実績）  ")
        frm_file.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 4))
        self.v_filepath = tk.StringVar()
        ttk.Entry(frm_file, textvariable=self.v_filepath, width=55).grid(row=0, column=0, **pad)
        ttk.Button(frm_file, text="参照...", command=self._browse).grid(row=0, column=1, **pad)
        ttk.Button(frm_file, text="読み込み", command=self._load_file).grid(row=0, column=2, **pad)

        # 待機時間
        frm_delay = ttk.LabelFrame(self.root, text="  待機時間（秒）  ")
        frm_delay.grid(row=1, column=0, sticky="ew", padx=10, pady=4)
        delay_items = [
            ("キー間",     "v_d_key",      "delay_key"),
            ("品番確定後", "v_d_hinban",   "delay_hinban"),
            ("登録後",     "v_d_register", "delay_register"),
            ("開始前(秒)", "v_countdown",  "countdown_sec"),
        ]
        for i, (label, attr, key) in enumerate(delay_items):
            ttk.Label(frm_delay, text=label).grid(row=0, column=i*2, sticky="e", padx=(8,2), pady=3)
            var = tk.StringVar(value=str(self.cfg[key]))
            setattr(self, attr, var)
            ttk.Entry(frm_delay, textvariable=var, width=6).grid(row=0, column=i*2+1, sticky="w", padx=(0,12))

        # ウィンドウタイトル
        frm_win = ttk.Frame(self.root)
        frm_win.grid(row=2, column=0, sticky="ew", padx=10, pady=2)
        ttk.Label(frm_win, text="基幹ウィンドウタイトル:").grid(row=0, column=0, padx=(0,4))
        self.v_window_title = tk.StringVar(value=self.cfg["window_title"])
        ttk.Entry(frm_win, textvariable=self.v_window_title, width=20).grid(row=0, column=1)
        ttk.Button(frm_win, text="設定保存", command=self._save_config_ui).grid(row=0, column=2, padx=(12,0))
        ttk.Button(frm_win, text="ログ表示", command=self._open_log).grid(row=0, column=3, padx=(8,0))

        # プレビュー
        frm_prev = ttk.LabelFrame(self.root, text="  入力対象レコード  ")
        frm_prev.grid(row=3, column=0, sticky="ew", padx=10, pady=4)
        cols = ("区分", "入荷日", "基幹品番", "仕入先CD", "品番後Tab", "入荷数後Tab", "入荷数")
        self.tree = ttk.Treeview(frm_prev, columns=cols, show="headings", height=6)
        widths    = (50,  90,     120,     90,     70,       80,         70)
        for col, w in zip(cols, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="center")
        vsb = ttk.Scrollbar(frm_prev, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self.lbl_count = ttk.Label(frm_prev, text="0 件")
        self.lbl_count.grid(row=1, column=0, sticky="w", padx=4, pady=2)

        # プログレス
        frm_prog = ttk.Frame(self.root)
        frm_prog.grid(row=4, column=0, sticky="ew", padx=10, pady=4)
        self.progress_var = tk.IntVar(value=0)
        self.progressbar = ttk.Progressbar(frm_prog, variable=self.progress_var, maximum=100, length=480)
        self.progressbar.grid(row=0, column=0, padx=(0,8))
        self.lbl_progress = ttk.Label(frm_prog, text="0 / 0 件", width=12)
        self.lbl_progress.grid(row=0, column=1)

        # ログ
        frm_log = ttk.LabelFrame(self.root, text="  ログ  ")
        frm_log.grid(row=5, column=0, sticky="ew", padx=10, pady=4)
        self.log_text = tk.Text(frm_log, height=8, width=72, state="disabled",
                                bg="#1e1e1e", fg="#d4d4d4", font=("Consolas", 9))
        log_sb = ttk.Scrollbar(frm_log, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_sb.set)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        log_sb.grid(row=0, column=1, sticky="ns")

        # ボタン
        frm_btn = ttk.Frame(self.root)
        frm_btn.grid(row=6, column=0, pady=(4, 10))
        self.btn_start = ttk.Button(frm_btn, text="▶  入力開始", command=self._start, width=18)
        self.btn_start.grid(row=0, column=0, padx=8)
        self.btn_stop = ttk.Button(frm_btn, text="■  停止", command=self._stop, width=12, state="disabled")
        self.btn_stop.grid(row=0, column=1, padx=8)
        self.lbl_status = ttk.Label(frm_btn, text="待機中", foreground="gray")
        self.lbl_status.grid(row=0, column=2, padx=16)

    # ---- ファイル操作 ----
    def _browse(self):
        path = filedialog.askopenfilename(
            title="仕入先納入実績Excelを選択",
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
            records, skipped, unmapped = load_excel(path)
            self.records = records
            for row in self.tree.get_children():
                self.tree.delete(row)
            for r in records:
                self.tree.insert("", "end", values=(
                    r.get('品目区分', ''),
                    r.get('入荷日', ''),
                    r.get('基幹品番', ''),
                    r.get('仕入先コード', ''),
                    r.get('品番後Tabキー回数', ''),
                    r.get('入荷数後Tabキー回数', ''),
                    int(float(r.get('入荷数', 0))),
                ))
            msg = f"{len(records)} 件"
            if skipped:
                msg += f"  （スキップ {len(skipped)} 件）"
            self.lbl_count.config(text=msg)
            self._log(f"読み込み完了: {len(records)} 件")
            if skipped:
                self._log(f"スキップ: {', '.join(skipped[:5])}" + (" ..." if len(skipped) > 5 else ""))
            if unmapped:
                messagebox.showwarning(
                    "マッピング未設定",
                    f"以下の品番はマッピング未設定のため入力されません。\n"
                    f"納入実績照会のマッピング設定タブで設定してください。\n\n"
                    + "\n".join(f"  {c}" for c in unmapped[:20])
                    + (f"\n  ... 他 {len(unmapped)-20} 件" if len(unmapped) > 20 else "")
                )
        except Exception as e:
            messagebox.showerror("読み込みエラー", str(e))
            self._log(f"エラー: {e}")

    # ---- ログ ----
    def _open_log(self):
        if not LOG_FILE.exists():
            messagebox.showinfo("ログ", "まだログファイルがありません")
            return
        import os
        os.startfile(LOG_FILE)

    def _save_config_ui(self):
        self.cfg = self._collect_config_from_ui()
        self._save_config()
        self._log("設定を保存しました")
        messagebox.showinfo("保存", "設定を保存しました")

    # ---- 入力開始/停止 ----
    def _start(self):
        if not self.records:
            messagebox.showwarning("注意", "先にExcelファイルを読み込んでください")
            return
        self.cfg = self._collect_config_from_ui()
        hwnd = find_window(self.cfg["window_title"])
        if not hwnd:
            messagebox.showerror(
                "エラー",
                f"基幹システムのウィンドウが見つかりません\n"
                f"（検索タイトル: '{self.cfg['window_title']}'）\n\n"
                f"HCE0040を開いてから再実行してください"
            )
            return
        self._log(f"基幹システム検出: {win32gui.GetWindowText(hwnd)}")
        self._stop_flag = False
        self._running   = True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.progress_var.set(0)
        threading.Thread(target=self._run_input, args=(hwnd,), daemon=True).start()

    def _stop(self):
        self._stop_flag = True
        self._log("★ 停止リクエスト送信...")
        self.root.after(0, lambda: self.lbl_status.config(text="停止中...", foreground="orange"))

    def _lock_mouse(self):
        if self._mouse_locked:
            return
        x, y = win32gui.GetCursorPos()
        class RECT(ctypes.Structure):
            _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long),
                        ('right', ctypes.c_long), ('bottom', ctypes.c_long)]
        rect = RECT(x, y, x+1, y+1)
        ctypes.windll.user32.ClipCursor(ctypes.byref(rect))
        self._mouse_locked = True

    def _unlock_mouse(self):
        if not self._mouse_locked:
            return
        ctypes.windll.user32.ClipCursor(None)
        self._mouse_locked = False

    def _poll_right_click(self):
        state = win32api.GetAsyncKeyState(win32con.VK_RBUTTON)
        is_pressed       = bool(state & 0x8000)
        pressed_since_last = bool(state & 0x0001)
        rising = (is_pressed and not self._right_button_prev) or (pressed_since_last and not is_pressed)
        if rising:
            now = time.monotonic()
            if (now - self._right_click_last_time) < 0.4:
                self._stop_flag = True
                self._unlock_mouse()
                self._log("★ 右ダブルクリックで停止")
            else:
                if self._mouse_locked:
                    self._unlock_mouse()
                    self._log("★ 右クリックでマウス固定解除")
            self._right_click_last_time = now
        self._right_button_prev = is_pressed

    def _show_countdown(self, seconds):
        popup = tk.Toplevel(self.root)
        popup.title("入力開始まで")
        popup.resizable(False, False)
        popup.attributes("-topmost", True)
        w, h = 340, 220
        sx, sy = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        popup.geometry(f"{w}x{h}+{(sx-w)//2}+{(sy-h)//2}")
        tk.Label(popup, text="基幹システムの\n入荷日にカーソルを置いてください",
                 font=("Yu Gothic UI", 12), fg="#333").pack(pady=(18, 6))
        lbl = tk.Label(popup, text=str(seconds), font=("Yu Gothic UI", 56, "bold"), fg="#e05c00")
        lbl.pack()
        tk.Label(popup, text="秒後に入力を開始します", font=("Yu Gothic UI", 10), fg="#555").pack(pady=(0,4))
        tk.Label(popup, text="停止: Ctrl+P", font=("Yu Gothic UI", 9), fg="#888").pack()
        self._countdown_popup = popup
        self._countdown_label = lbl

    def _update_countdown(self, val):
        try:
            self._countdown_label.config(text=str(val))
        except Exception:
            pass

    def _close_countdown(self):
        try:
            self._countdown_popup.destroy()
        except Exception:
            pass

    def _run_input(self, hwnd):
        countdown = int(self.cfg.get("countdown_sec", 10))
        self.root.after(0, lambda: self._show_countdown(countdown))
        self._log(f"★ {countdown}秒後に開始。基幹の入荷日にカーソルを置いてください。")
        self._log("★ 停止: Ctrl+P  /  緊急停止: マウスを画面左上角")

        for i in range(countdown, 0, -1):
            if self._stop_flag:
                self.root.after(0, self._close_countdown)
                self._finish(0, 0, stopped=True)
                return
            self.root.after(0, lambda v=i: self._update_countdown(v))
            time.sleep(1)

        self.root.after(0, self._close_countdown)

        pyautogui.FAILSAFE = True
        self._right_button_prev = False
        self._lock_mouse()
        total   = len(self.records)
        success = 0
        errors  = 0

        def should_stop():
            self._poll_right_click()
            return self._stop_flag or keyboard.is_pressed('ctrl+p')

        for i, record in enumerate(self.records):
            self._poll_right_click()
            if should_stop():
                self._stop_flag = True
                break

            self._set_status(f"入力中 {i+1}/{total}", "blue")
            item_type = str(record.get('品目区分') or '').strip()
            self._log(f"[{i+1}/{total}] 区分={item_type}  品番={record.get('基幹品番')}  入荷数={record.get('入荷数')}")

            try:
                input_one_record(record, self.cfg, hwnd=hwnd, stop_check=should_stop, log_func=self._log)
                success += 1
                self._record_log(record)
                self._log(f"  → 登録OK")
            except InterruptedError:
                self._stop_flag = True
                self._log("★ 停止しました")
                break
            except ErrorDialogDetected as e:
                self._stop_flag = True
                self._log(f"★ エラーダイアログ検出により中止\n  行={i+1}/{total}  品番={record.get('基幹品番')}\n  [{e}]")
                break
            except pyautogui.FailSafeException:
                self._log("★★ フェイルセーフ発動 - 緊急停止 ★★")
                break
            except Exception as e:
                errors += 1
                self._log(f"  → エラー: {e}")

            pct = int((i + 1) / total * 100)
            self.root.after(0, lambda p=pct, c=i+1, t=total: (
                self.progress_var.set(p),
                self.lbl_progress.config(text=f"{c} / {t} 件")
            ))

        self._finish(success, errors)

    def _finish(self, success, errors, stopped=False):
        self._unlock_mouse()
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

    def _record_log(self, record):
        try:
            write_header = not LOG_FILE.exists()
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                if write_header:
                    f.write('入荷日,基幹品番,品目区分,入力日時\n')
                dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"{record.get('入荷日')},{record.get('基幹品番')},{record.get('品目区分')},{dt}\n")
        except Exception as e:
            self._log(f"ログ保存エラー: {e}")

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
    style = ttk.Style()
    try:
        style.theme_use('vista')
    except Exception:
        pass
    HCE0040InputApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
