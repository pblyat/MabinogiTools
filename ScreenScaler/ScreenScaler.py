import win32gui
import win32api
import win32process
import psutil
import ctypes
import sys
import tkinter as tk
from tkinter import messagebox

ow = win32api.GetSystemMetrics(0)
oh = win32api.GetSystemMetrics(1)

waittime = 3
scale = 2.0

if not ctypes.windll.shell32.IsUserAnAdmin():
    messagebox.showerror("Error", "관리자 권한으로 실행해주세요")
    sys.exit(0)

def gethwnd(pname):
    def callback(hwnd, hwnds):
        if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                proc = psutil.Process(pid)
                if pname.lower() in proc.name().lower():
                    hwnds.append(hwnd)
            except psutil.NoSuchProcess:
                pass
        return True

    hwnds = []
    win32gui.EnumWindows(callback, hwnds)
    return hwnds[0] if hwnds else None


hwnd = gethwnd("mabinogimobile.exe")
if not hwnd:
    messagebox.showerror("Error", "window not found")
    exit()

def resize():
    global hwnd
    global ow, oh
    if hwnd:
        if not scale_entry.get():
            if not res_width_entry.get() or not res_height_entry.get():
                messagebox.showerror("Error", "해상도나 배율을 입력해주세요")
                return
            try:
                nw = int(res_width_entry.get())
                nh = int(res_height_entry.get())
            except ValueError:
                messagebox.showerror("Error", "해상도는 정수여야 합니다")
                return
            if nw <= 0 or nh <= 0:
                messagebox.showerror("Error", "해상도는 양수여야 합니다")
                return
            nx = ow - nw
            ny = (oh // 2) - (nh // 2)

            win32gui.MoveWindow(hwnd, nx, ny, nw, nh, True)
            print("done : ", nx, ny, nw, nh)
        else:
            scale = float(scale_entry.get())
            nw = int(ow * scale)
            nh = int(oh * scale)
            nx = ow - nw
            ny = (oh // 2) - (nh // 2)
            
            win32gui.MoveWindow(hwnd, nx, ny, nw, nh, True)
            print("done : ", nx, ny, nw, nh)
    else:
        print("Window not found")

def restore():
    global hwnd
    global ow, oh
    if hwnd:
        win32gui.MoveWindow(hwnd, 0, 0, ow, oh, True)
        print("restored")
    else:
        print("Window not found")

def validate_float(P):
    if P == "":  # 빈 값 허용
        return True
    try:
        float(P)
        return True
    except ValueError:
        return False

root = tk.Tk()
root.title("스샷 v1")

scale_label = tk.Label(root, text="배율", font=("맑은 고딕", 11), width=10)
scale_label.grid(row=0, column=0, padx=10, pady=10, sticky="e")

vcmd = (root.register(validate_float), "%P")
scale_entry = tk.Entry(root, validate="key", validatecommand=vcmd, font=("맑은 고딕", 12), justify="center", width=10)
scale_entry.grid(row=0, column=1, padx=10, pady=10, sticky="w")


res_label = tk.Label(root, text="해상도 직접 입력", font=("맑은 고딕", 11), width=20)
res_label.grid(row=1, column=0, columnspan=2, pady=(0, 5))

res_width_entry = tk.Entry(root, font=("맑은 고딕", 11), justify="center", width=10)
res_width_entry.grid(row=2, column=0, padx=10, pady=5, sticky="e")

res_height_entry = tk.Entry(root, font=("맑은 고딕", 11), justify="center", width=10)
res_height_entry.grid(row=2, column=1, padx=10, pady=5, sticky="w")

resize_button = tk.Button(root, text="창 키우기", command=resize, width=10, font=("맑은 고딕", 11))
resize_button.grid(row=3, column=0, pady=15)

restore_button = tk.Button(root, text="창 복구", command=restore, width=10, font=("맑은 고딕", 11))
restore_button.grid(row=3, column=1, pady=15)

root.mainloop()
