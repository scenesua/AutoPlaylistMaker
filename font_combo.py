"""Reusable, keyboard-friendly searchable system-font picker for Tk."""

import tkinter as tk
from tkinter import font as tkfont
from i18n import t


class SearchableFontComboBox(tk.Frame):
    _font_cache = None

    @classmethod
    def font_families(cls, root):
        if cls._font_cache is None:
            try:
                names = {str(name).strip() for name in tkfont.families(root)}
                cls._font_cache = sorted(
                    (name for name in names if name), key=str.casefold
                )
            except Exception:
                cls._font_cache = ["Arial"]
        return cls._font_cache

    def __init__(self, master, variable, theme, ui_font=None, **kwargs):
        super().__init__(
            master,
            bg=theme["bg_input"],
            highlightthickness=1,
            highlightbackground=theme["border"],
            **kwargs,
        )
        self.variable = variable
        self.theme = theme
        self.ui_font = ui_font
        self.popup = None
        self._outside_bind_id = None
        self._filter_job = None
        self._visible_fonts = []
        self.button = tk.Button(
            self,
            textvariable=variable,
            anchor="w",
            relief=tk.FLAT,
            borderwidth=0,
            bg=theme["bg_input"],
            fg=theme["fg"],
            activebackground=theme["bg_hover"],
            activeforeground=theme["fg"],
            font=ui_font,
            cursor="hand2",
            command=self.open,
        )
        self.button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 2), pady=5)
        self.arrow = tk.Button(
            self,
            text="▼",
            width=2,
            relief=tk.FLAT,
            borderwidth=0,
            bg=theme["bg_input"],
            fg=theme["fg_dim"],
            activebackground=theme["bg_hover"],
            command=self.open,
            cursor="hand2",
        )
        self.arrow.pack(side=tk.RIGHT, padx=(0, 4), pady=3)
        self.bind("<Destroy>", self._on_destroy, add="+")

    def open(self):
        if self.popup and self.popup.winfo_exists():
            self.close()
            return
        root = self.winfo_toplevel()
        popup = self.popup = tk.Toplevel(root)
        popup.withdraw()
        popup.overrideredirect(True)
        popup.transient(root)
        popup.attributes("-topmost", True)
        popup.configure(
            bg=self.theme["bg_card"],
            highlightthickness=1,
            highlightbackground=self.theme["border"],
        )
        self.search_var = tk.StringVar()
        self.search = tk.Entry(
            popup,
            textvariable=self.search_var,
            relief=tk.FLAT,
            bg=self.theme["bg_input"],
            fg=self.theme["fg"],
            insertbackground=self.theme["fg"],
            font=self.ui_font,
        )
        self.search.pack(fill=tk.X, padx=7, pady=7, ipady=5)
        body = tk.Frame(popup, bg=self.theme["bg_card"])
        body.pack(fill=tk.BOTH, expand=True, padx=7)
        self.listbox = tk.Listbox(
            body,
            height=10,
            exportselection=False,
            activestyle="none",
            relief=tk.FLAT,
            highlightthickness=0,
            bg=self.theme["bg_input"],
            fg=self.theme["fg"],
            selectbackground=self.theme["accent"],
            selectforeground="#ffffff",
            font=self.ui_font,
        )
        scrollbar = tk.Scrollbar(body, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.preview = tk.Label(
            popup,
            text=t("font.preview"),
            anchor="w",
            bg=self.theme["bg_card"],
            fg=self.theme["fg_dim"],
        )
        self.preview.pack(fill=tk.X, padx=9, pady=(5, 7))

        self.search_var.trace_add("write", self._schedule_filter)
        self.search.bind("<Down>", self._focus_list)
        self.search.bind("<Escape>", lambda _e: self.close())
        self.listbox.bind("<Double-Button-1>", self._choose)
        self.listbox.bind("<Return>", self._choose)
        self.listbox.bind("<Escape>", lambda _e: self.close())
        self.listbox.bind("<<ListboxSelect>>", self._update_preview)
        for widget in (popup, self.search, self.listbox, body):
            widget.bind("<MouseWheel>", self._wheel, add="+")
        popup.bind("<FocusOut>", self._focus_out, add="+")
        self._apply_filter()

        width = max(310, self.winfo_width())
        height = 310
        x = self.winfo_rootx()
        below = self.winfo_rooty() + self.winfo_height() + 2
        screen_h = root.winfo_screenheight()
        y = below if below + height <= screen_h else max(0, self.winfo_rooty() - height)
        screen_w = root.winfo_screenwidth()
        x = max(0, min(x, screen_w - width))
        popup.geometry(f"{width}x{height}+{x}+{y}")
        popup.deiconify()
        popup.lift()
        self._outside_bind_id = root.bind(
            "<Button-1>", lambda _event: self.close(), add="+"
        )
        self.search.focus_set()

    def close(self):
        popup, self.popup = self.popup, None
        if self._filter_job:
            try:
                self.after_cancel(self._filter_job)
            except tk.TclError:
                pass
            self._filter_job = None
        if popup and popup.winfo_exists():
            popup.destroy()
        if self._outside_bind_id:
            try:
                self.winfo_toplevel().unbind(
                    "<Button-1>", self._outside_bind_id
                )
            except tk.TclError:
                pass
            self._outside_bind_id = None

    def _schedule_filter(self, *_args):
        if self._filter_job:
            self.after_cancel(self._filter_job)
        self._filter_job = self.after(100, self._apply_filter)

    def _apply_filter(self):
        self._filter_job = None
        query = self.search_var.get().strip().casefold()
        fonts = self.font_families(self.winfo_toplevel())
        self._visible_fonts = [
            name for name in fonts if not query or query in name.casefold()
        ]
        self.listbox.delete(0, tk.END)
        if not self._visible_fonts:
            self.listbox.insert(tk.END, t("font.noResults"))
            self.listbox.itemconfigure(0, foreground=self.theme["fg_dimmer"])
            return
        for name in self._visible_fonts:
            self.listbox.insert(tk.END, name)
        selected = self.variable.get()
        try:
            index = self._visible_fonts.index(selected)
        except ValueError:
            index = 0
        self.listbox.selection_set(index)
        self.listbox.activate(index)
        self.listbox.see(index)
        self._update_preview()

    def _focus_list(self, _event):
        if self._visible_fonts:
            self.listbox.focus_set()
        return "break"

    def _choose(self, _event=None):
        selection = self.listbox.curselection()
        if selection and self._visible_fonts:
            self.variable.set(self._visible_fonts[selection[0]])
            self.close()
        return "break"

    def _update_preview(self, _event=None):
        selection = self.listbox.curselection()
        if not selection or not self._visible_fonts:
            return
        family = self._visible_fonts[selection[0]]
        try:
            self.preview.configure(font=(family, 11))
        except tk.TclError:
            self.preview.configure(font=self.ui_font)

    def _wheel(self, event):
        self.listbox.yview_scroll(-1 if event.delta > 0 else 1, "units")
        return "break"

    def _focus_out(self, _event):
        self.after_idle(self._close_if_focus_outside)

    def _close_if_focus_outside(self):
        if not self.popup:
            return
        focused = self.focus_get()
        if focused is None or focused.winfo_toplevel() is not self.popup:
            self.close()

    def _on_destroy(self, event):
        if event.widget is self:
            self.close()
