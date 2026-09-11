import tkinter as tk
import ctypes

def set_dark_titlebar(window):
    window.update()
    DWMWA_USE_IMMERSIVE_DARK_MODE = 20
    set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
    get_parent = ctypes.windll.user32.GetParent
    hwnd = get_parent(window.winfo_id())
    rendering_policy = DWMWA_USE_IMMERSIVE_DARK_MODE
    value = ctypes.c_int(2)
    set_window_attribute(hwnd, rendering_policy, ctypes.byref(value), ctypes.sizeof(value))

root = tk.Tk()
root.title("Dark Title Bar Test")
root.geometry("400x300")
root.configure(bg="#0A0A0A")

tk.Label(root, text="Hello Dark Mode!", bg="#0A0A0A", fg="white").pack(expand=True)

set_dark_titlebar(root)
root.mainloop()
