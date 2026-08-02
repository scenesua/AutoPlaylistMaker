"""Minimal packaged entry point: keep the boot splash responsive, then load APM."""

import datetime
import os
import sys
import threading
import time


_T0 = time.perf_counter()
os.environ["APM_BOOTSTRAP_T0"] = repr(_T0)


def _mark(name):
    log_dir = os.path.join(os.path.expanduser("~"), "AutoPlaylistMaker_logs")
    os.makedirs(log_dir, exist_ok=True)
    with open(
        os.path.join(log_dir, "startup_timing.log"), "a", encoding="utf-8"
    ) as stream:
        stream.write(
            f"{datetime.datetime.now().isoformat()} "
            f"{time.perf_counter() - _T0:.6f} {name}\n"
        )


class BootstrapSplash:
    """Minimal opaque Tk splash whose root becomes the main application root."""

    def __init__(self):
        import tkinter as tk

        self._tk = tk
        self._handed_off = False
        self.root = tk.Tk()
        self.root.withdraw()
        self.window = tk.Toplevel(self.root)
        self.window.overrideredirect(True)
        self.window.configure(bg="#111827")
        width, height = 440, 300
        x = max(0, (self.root.winfo_screenwidth() - width) // 2)
        y = max(0, (self.root.winfo_screenheight() - height) // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")
        base = getattr(
            sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))
        )
        self.image = tk.PhotoImage(file=os.path.join(base, "app_splash.png"))
        self.label = tk.Label(
            self.window, image=self.image, bg="#111827", borderwidth=0
        )
        self.label.place(relx=.5, rely=.5, anchor=tk.CENTER)
        self.window.attributes("-topmost", True)
        self.window.deiconify()
        self.window.lift()
        self.root.update_idletasks()
        self.root.update()

    def update(self, _text, _progress):
        self.root.update_idletasks()
        self.root.update()

    def handoff_root(self):
        self._handed_off = True
        return self.root

    def close(self):
        if self._handed_off:
            self.window.destroy()
        else:
            self.root.destroy()


class NativeWindowsSplash:
    """Responsive Win32 splash shown before the packaged Tcl/Tk runtime loads."""

    def __init__(self):
        self._ready = threading.Event()
        self._hwnd = None
        self._error = None
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        if not self._ready.wait(5) or self._error:
            raise RuntimeError(self._error or "Native splash did not start")

    def _run(self):
        try:
            import ctypes
            from ctypes import wintypes

            user32, gdi32, kernel32 = (
                ctypes.windll.user32, ctypes.windll.gdi32,
                ctypes.windll.kernel32,
            )
            long_ptr = ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long
            WNDPROC = ctypes.WINFUNCTYPE(
                long_ptr, wintypes.HWND, wintypes.UINT,
                wintypes.WPARAM, wintypes.LPARAM,
            )
            user32.DefWindowProcW.argtypes = (
                wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
            )
            user32.DefWindowProcW.restype = long_ptr

            class WNDCLASSW(ctypes.Structure):
                _fields_ = [
                    ("style", wintypes.UINT),
                    ("lpfnWndProc", WNDPROC),
                    ("cbClsExtra", ctypes.c_int),
                    ("cbWndExtra", ctypes.c_int),
                    ("hInstance", wintypes.HINSTANCE),
                    ("hIcon", wintypes.HICON),
                    ("hCursor", wintypes.HANDLE),
                    ("hbrBackground", wintypes.HBRUSH),
                    ("lpszMenuName", wintypes.LPCWSTR),
                    ("lpszClassName", wintypes.LPCWSTR),
                ]

            class PAINTSTRUCT(ctypes.Structure):
                _fields_ = [
                    ("hdc", wintypes.HDC), ("fErase", wintypes.BOOL),
                    ("rcPaint", wintypes.RECT),
                    ("fRestore", wintypes.BOOL),
                    ("fIncUpdate", wintypes.BOOL),
                    ("rgbReserved", ctypes.c_byte * 32),
                ]

            base = getattr(
                sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))
            )
            icon_path = os.path.join(base, "app_icon.ico")
            icon = user32.LoadImageW(
                None, icon_path, 1, 128, 128, 0x10
            )
            background = gdi32.CreateSolidBrush(0x00271811)
            title_font = gdi32.CreateFontW(
                -24, 0, 0, 0, 700, 0, 0, 0, 1, 0, 0, 5, 0,
                "Segoe UI",
            )
            detail_font = gdi32.CreateFontW(
                -15, 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 5, 0,
                "Segoe UI",
            )

            def wndproc(hwnd, message, wparam, lparam):
                if message == 0x000F:  # WM_PAINT
                    ps = PAINTSTRUCT()
                    hdc = user32.BeginPaint(hwnd, ctypes.byref(ps))
                    rect = wintypes.RECT(0, 0, 440, 300)
                    user32.FillRect(hdc, ctypes.byref(rect), background)
                    if icon:
                        user32.DrawIconEx(
                            hdc, 156, 30, icon, 128, 128, 0, None, 3
                        )
                    gdi32.SetBkMode(hdc, 1)
                    gdi32.SetTextColor(hdc, 0x00FFFFFF)
                    gdi32.SelectObject(hdc, title_font)
                    title_rect = wintypes.RECT(20, 175, 420, 220)
                    user32.DrawTextW(
                        hdc, "Auto Playlist Maker", -1,
                        ctypes.byref(title_rect), 0x0001 | 0x0004,
                    )
                    gdi32.SetTextColor(hdc, 0x00C7CEDA)
                    gdi32.SelectObject(hdc, detail_font)
                    detail_rect = wintypes.RECT(20, 224, 420, 260)
                    user32.DrawTextW(
                        hdc, "v1.3.1  ·  Starting…", -1,
                        ctypes.byref(detail_rect), 0x0001 | 0x0004,
                    )
                    user32.EndPaint(hwnd, ctypes.byref(ps))
                    return 0
                if message == 0x0010:  # WM_CLOSE
                    user32.DestroyWindow(hwnd)
                    return 0
                if message == 0x0002:  # WM_DESTROY
                    user32.PostQuitMessage(0)
                    return 0
                return user32.DefWindowProcW(hwnd, message, wparam, lparam)

            self._wndproc = WNDPROC(wndproc)
            instance = kernel32.GetModuleHandleW(None)
            class_name = "AutoPlaylistMakerBootstrapSplash"
            window_class = WNDCLASSW(
                0, self._wndproc, 0, 0, instance, icon,
                user32.LoadCursorW(None, 32512), background,
                None, class_name,
            )
            user32.RegisterClassW(ctypes.byref(window_class))
            screen_w, screen_h = (
                user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
            )
            self._hwnd = user32.CreateWindowExW(
                0x00000088, class_name, "", 0x90000000,
                (screen_w - 440) // 2, (screen_h - 300) // 2,
                440, 300, None, None, instance, None,
            )
            if not self._hwnd:
                raise ctypes.WinError()
            user32.ShowWindow(self._hwnd, 5)
            user32.UpdateWindow(self._hwnd)
            self._ready.set()
            message = wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
                user32.TranslateMessage(ctypes.byref(message))
                user32.DispatchMessageW(ctypes.byref(message))
            for handle in (title_font, detail_font, background):
                if handle:
                    gdi32.DeleteObject(handle)
        except Exception as error:
            self._error = error
            self._ready.set()

    def update(self, _text, _progress):
        return None

    def wait_until_visible(self, timeout=5):
        return self._ready.wait(timeout) and self._hwnd is not None

    def close(self):
        if self._hwnd:
            import ctypes
            ctypes.windll.user32.PostMessageW(self._hwnd, 0x0010, 0, 0)
            self._thread.join(timeout=2)


def main():
    _mark("bootstrap_enter")
    _mark("splash_create_start")
    splash = (
        NativeWindowsSplash() if os.name == "nt" else BootstrapSplash()
    )
    _mark("splash_create_end")
    _mark("splash_first_paint")
    _mark("app_import_start")
    import app

    _mark("app_import_end")
    app.main(startup_splash=splash)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback

        log_dir = os.path.join(
            os.path.expanduser("~"), "AutoPlaylistMaker_logs"
        )
        os.makedirs(log_dir, exist_ok=True)
        with open(
            os.path.join(log_dir, "startup_error.log"),
            "w", encoding="utf-8",
        ) as stream:
            traceback.print_exc(file=stream)
        raise
