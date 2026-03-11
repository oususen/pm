"""
kikan_input_app.py
生産実績照会 Excel出力2 → 基幹システム(SSE0040) 自動入力アプリ

使用方法:
    python kikan_input_app.py

事前準備:
    pip install pyautogui pyperclip openpyxl pywin32
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import json
import time
import ctypes
import keyboard
import pyautogui
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
CONFIG_FILE = Path(__file__).parent / "kikan_input_config.json"

DEFAULT_CONFIG = {
    "window_title":        "SSE0040",
    "tabs_to_hinban":      1,
    "tabs_after_hinban":   1,
    "tabs_to_seisansu":    5,
    "tabs_to_jikan_start": 5,
    "tabs_to_jikan_end":   1,
    "delay_key":           0.15,
    "delay_hinban":        0.8,
    "delay_register":      1.2,
    "countdown_sec":       5,
}


# ============================================================
# 入力ロジック（kikan_input.py から移植）
# ============================================================

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


def input_one_record(record, cfg, stop_check=None):
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
            time.sleep(delay_key)

    def clear_input(text):
        check_stop()
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.05)
        pyperclip.copy(str(text))
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(delay_key)

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
    pyautogui.press('enter')       # 品番確定（品名・工程情報を引く）
    time.sleep(delay_hinban)

    # 品番確定後 → 工程順位
    next_field(cfg["tabs_after_hinban"])
    clear_input(koukei)

    # 工程順位 → 生産数(完成)
    # Enter回数はマッピング設定の値を優先、なければアプリ設定値を使用
    enter_count_raw = record.get('Enter回数')
    if enter_count_raw is not None and str(enter_count_raw).strip() not in ('', 'None', '—'):
        tabs_to_seisansu = int(float(enter_count_raw))
    else:
        tabs_to_seisansu = cfg["tabs_to_seisansu"]
    next_field(tabs_to_seisansu)
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
    time.sleep(0.6)               # 確認ダイアログが表示されるまで待機
    pyautogui.press('enter')      # 「はい」を選択
    time.sleep(cfg["delay_register"])  # 登録処理完了まで待機

    return seisanbi, hinban, koukei, seisansu


# ============================================================
# GUI アプリ
# ============================================================

class KikanInputApp:
    def __init__(self, root):
        self.root = root
        self.root.title("基幹システム自動入力  -  SSE0040")
        self.root.resizable(False, False)

        self.cfg = self._load_config()
        self.records = []
        self._stop_flag    = False
        self._running      = False
        self._hotkey_handle = None

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

        # ====== レコードプレビュー ======
        frm_prev = ttk.LabelFrame(self.root, text="  入力対象レコード  ")
        frm_prev.grid(row=4, column=0, sticky="ew", padx=10, pady=4)

        cols = ("生産日", "基幹品番", "工順", "生産数量", "開始時間", "終了時間")
        self.tree = ttk.Treeview(frm_prev, columns=cols, show="headings", height=6)
        widths = (90, 120, 50, 70, 70, 70)
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

            # ツリー更新
            for row in self.tree.get_children():
                self.tree.delete(row)
            for r in records:
                self.tree.insert("", "end", values=(
                    format_seisanbi(r['生産日']),
                    r['基幹品番'],
                    r['工順'],
                    int(r['生産数量']),
                    format_time(r.get('開始時間')) or '',
                    format_time(r.get('終了時間')) or '',
                ))

            msg = f"{len(records)} 件"
            if skipped:
                msg += f"  （スキップ {len(skipped)} 件）"
            self.lbl_count.config(text=msg)
            self._log(f"読み込み完了: {len(records)} 件  シート={sheet}")
            if skipped:
                self._log(f"スキップ: {', '.join(skipped[:5])}" +
                          (" ..." if len(skipped) > 5 else ""))

        except Exception as e:
            messagebox.showerror("読み込みエラー", str(e))
            self._log(f"エラー: {e}")

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

        for i in range(countdown, 0, -1):
            if self._stop_flag or cancel_event.is_set():
                self.root.after(0, self._close_countdown_popup)
                self._finish(0, 0, stopped=True)
                return
            self.root.after(0, lambda v=i: self._update_countdown_label(v))
            time.sleep(1)

        self.root.after(0, self._close_countdown_popup)

        pyautogui.FAILSAFE = True
        total   = len(self.records)
        success = 0
        errors  = 0

        # 停止判定関数（停止ボタン / Ctrl+P どちらでも止まる）
        def should_stop():
            return self._stop_flag or keyboard.is_pressed('ctrl+p')

        for i, record in enumerate(self.records):
            if should_stop():
                self._stop_flag = True
                break

            self._set_status(f"入力中 {i+1}/{total}", "blue")
            self._log(f"[{i+1}/{total}] 品番={record['基幹品番']}  "
                      f"工順={record['工順']}  生産数={int(record['生産数量'])}")

            try:
                seisanbi, hinban, koukei, seisansu = input_one_record(
                    record, self.cfg, stop_check=should_stop)
                success += 1
                self._log(f"  → 登録OK  生産日={seisanbi}")
            except InterruptedError:
                # 停止ボタン / Ctrl+P による中断
                self._stop_flag = True
                self._log("★ 入力中に停止しました")
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
