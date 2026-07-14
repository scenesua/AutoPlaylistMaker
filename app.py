"""
Auto Playlist Maker GUI v3 - Dark theme, D2Coding font, dark/light toggle
4단계: 프로젝트+가져오기 → 자동분배 → 음악편집 → 영상편집+렌더링
"""

import os
import sys
import json
import threading
import time
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_loaded = False
_analyze_track = None
_create_mixed_audio = None
_load_audio_pydub = None
_generate_video = None
_load_visual_config = None
_Project = None
_distribute_tracks = None
_get_distribution_summary = None
_np = None
_PIL_Image = None
_PIL_ImageTk = None
_PIL_ImageDraw = None
_PIL_ImageFont = None
video_gen = None


def _load_heavy_modules():
    global _loaded, _analyze_track, _create_mixed_audio, _load_audio_pydub
    global _generate_video, _load_visual_config, _Project
    global _distribute_tracks, _get_distribution_summary
    global _np, _PIL_Image, _PIL_ImageTk, _PIL_ImageDraw, _PIL_ImageFont
    global video_gen
    import numpy as _numpy
    from PIL import Image as PILImage, ImageTk as PILImageTk, ImageDraw as PILImageDraw, ImageFont as PILImageFont
    from analyzer import analyze_track as _at
    from transition import create_mixed_audio as _cma, load_audio_pydub as _lap
    import video_gen as _video_gen_mod
    from video_gen import generate_video as _gv, load_visual_config as _lvc
    from project import Project as _Proj
    from distributor import distribute_tracks as _dt, get_distribution_summary as _gs
    _np = _numpy
    _PIL_Image = PILImage
    _PIL_ImageTk = PILImageTk
    _PIL_ImageDraw = PILImageDraw
    _PIL_ImageFont = PILImageFont
    _analyze_track = _at
    _create_mixed_audio = _cma
    _load_audio_pydub = _lap
    _generate_video = _gv
    video_gen = _video_gen_mod
    _load_visual_config = _lvc
    _Project = _Proj
    _distribute_tracks = _dt
    _get_distribution_summary = _gs
    _loaded = True

AUDIO_EXTS = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac', '.wma', '.opus', '.aiff'}
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff'}
VIDEO_EXTS = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}

FONT_PATH = None
_font_search_common = []
if sys.platform == 'darwin':
    _font_search_common = [
        '/System/Library/Fonts/Supplemental/Arial Unicode.ttf',
        '/System/Library/Fonts/PingFang.ttc',
        '/System/Library/Fonts/Supplemental/Arial.ttf',
        '/System/Library/Fonts/Helvetica.ttc',
        '/Library/Fonts/Arial.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    ]
elif sys.platform == 'win32':
    _font_search_common = [
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'Fonts', 'D2Coding-Ver1.3.2-20180524-all.ttc'),
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'Fonts', 'D2Coding.ttf'),
        'C:/Windows/Fonts/D2Coding-Ver1.3.2-20180524-all.ttc',
        'C:/Windows/Fonts/D2Coding.ttf',
        'C:/Windows/Fonts/NSMSEUD.ttf',
    ]
else:
    _font_search_common = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf',
    ]
for _fp in _font_search_common:
    if os.path.isfile(_fp):
        FONT_PATH = _fp
        break

if FONT_PATH:
    FONT_FAMILY = "D2Coding" if sys.platform == 'win32' else "Helvetica"
elif sys.platform == 'darwin':
    FONT_FAMILY = "Helvetica"
elif sys.platform == 'win32':
    FONT_FAMILY = "Segoe UI"
else:
    FONT_FAMILY = "DejaVu Sans"

DARK = {
    'bg':        '#202225',
    'bg_mid':    '#2f3136',
    'bg_main':   '#36393f',
    'bg_input':  '#40444b',
    'bg_hover':  '#4f545c',
    'bg_card':   '#2f3136',
    'fg':        '#dcddde',
    'fg_dim':    '#96989d',
    'fg_dimmer': '#72767d',
    'accent':    '#5865f2',
    'accent_h':  '#4752c4',
    'success':   '#57f287',
    'danger':    '#ed4245',
    'warning':   '#fee75c',
    'scroll_bg': '#202225',
    'scroll_fg': '#202225',
    'select':    '#5865f2',
    'tree_sel':  '#4752c4',
    'border':    '#202225',
    'wave_bg':   '#202225',
    'wave_line': '#5865f2',
    'wave_trim': '#57f287',
    'separator': '#4f545c',
}

LIGHT = {
    'bg':        '#f2f3f5',
    'bg_mid':    '#e3e5e8',
    'bg_main':   '#ffffff',
    'bg_input':  '#ebedef',
    'bg_hover':  '#d4d7dc',
    'bg_card':   '#e3e5e8',
    'fg':        '#060607',
    'fg_dim':    '#4e5058',
    'fg_dimmer': '#80848e',
    'accent':    '#5865f2',
    'accent_h':  '#4752c4',
    'success':   '#248046',
    'danger':    '#d83c3e',
    'warning':   '#c9a600',
    'scroll_bg': '#e3e5e8',
    'scroll_fg': '#c4c9ce',
    'select':    '#5865f2',
    'tree_sel':  '#4752c4',
    'border':    '#d4d7dc',
    'wave_bg':   '#f2f3f5',
    'wave_line': '#5865f2',
    'wave_trim': '#248046',
    'separator': '#d4d7dc',
}

THEME = DARK

def file_type(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in AUDIO_EXTS: return "audio"
    if ext in IMAGE_EXTS: return "image"
    if ext in VIDEO_EXTS: return "video"
    return "unknown"


def _font(size, bold=False):
    weight = "bold" if bold else "normal"
    return (FONT_FAMILY, size, weight)


def _pil_font(size):
    if FONT_PATH:
        try:
            from PIL import ImageFont
            return ImageFont.truetype(FONT_PATH, size)
        except Exception:
            pass
    from PIL import ImageFont
    return ImageFont.load_default()


class TrackItem:
    def __init__(self, filepath):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.filetype = file_type(filepath)
        self.analysis = None
        self.trim_start = 0.0
        self.trim_end = 0.0
        self.duration = 0.0
        self.enabled = True

    def analyze(self):
        if self.filetype != "audio": return
        try:
            self.analysis = _analyze_track(self.filepath)
            self.duration = self.analysis.duration
            self.trim_end = self.duration
        except Exception as e:
            print(f"분석 실패: {self.filename} - {e}")

    def to_dict(self):
        return {
            'filepath': self.filepath, 'filename': self.filename,
            'trim_start': self.trim_start, 'trim_end': self.trim_end,
        }


# ─── UI Helpers ───

def populate_group_tabs(container, video_groups, current_idx, on_select):
    """영상(분배 결과)이 2개 이상일 때 Mix 1 / Mix 2 ... 를 눌러 전환할 수 있는
    탭 바. 음악 편집(Stage2)과 영상 편집(Stage3)에서 공용으로 사용한다."""
    for w in container.winfo_children():
        w.destroy()
    if len(video_groups) <= 1:
        return
    styled_label(container, "영상:", size=9, color=THEME['fg_dim'],
                bg=container.cget('bg')).pack(side=tk.LEFT, padx=(0, 6))
    for i, g in enumerate(video_groups):
        active = (i == current_idx)
        n = len(g.get('tracks', []))
        dur = g.get('total_duration', 0)
        btn = styled_button(
            container, f"Mix {i+1} ({n}곡, {int(dur)}초)" if len(video_groups) <= 4 else f"Mix {i+1}",
            command=lambda ii=i: on_select(ii),
            style="primary" if active else "default",
            padx=10, pady=4,
        )
        btn.pack(side=tk.LEFT, padx=(0, 4))


def styled_button(parent, text, command=None, style="default", **kw):
    btn_bg = THEME['accent'] if style == "primary" else THEME['bg_input']
    btn_fg = "#ffffff" if style == "primary" else THEME['fg']
    if style == "danger":
        btn_bg = THEME['danger']
        btn_fg = "#ffffff"
    btn = tk.Button(
        parent, text=text, font=_font(10),
        bg=kw.get('bg', btn_bg), fg=kw.get('fg', btn_fg),
        activebackground=THEME['accent_h'] if style == "primary" else THEME['bg_hover'],
        activeforeground="#ffffff" if style == "primary" else THEME['fg'],
        relief=tk.FLAT, padx=kw.get('padx', 12), pady=kw.get('pady', 4),
        command=command, cursor="hand2",
        borderwidth=0, highlightthickness=0,
    )
    return btn


def styled_entry(parent, textvariable=None, width=None, **kw):
    ent = tk.Entry(
        parent, textvariable=textvariable, width=width,
        font=_font(10),
        bg=THEME['bg_input'], fg=THEME['fg'],
        insertbackground=THEME['fg'],
        selectbackground=THEME['accent'],
        selectforeground="#ffffff",
        relief=tk.FLAT, borderwidth=0, highlightthickness=1,
        highlightbackground=THEME['border'], highlightcolor=THEME['accent'],
    )
    return ent


def styled_label(parent, text, size=10, bold=False, color=None, **kw):
    return tk.Label(
        parent, text=text, font=_font(size, bold),
        bg=kw.get('bg', THEME['bg_main']),
        fg=color or THEME['fg'], anchor=kw.get('anchor', tk.W),
    )


def styled_option_menu(parent, variable, options, **kw):
    m = tk.OptionMenu(parent, variable, *options)
    m.configure(
        font=_font(9), bg=THEME['bg_input'], fg=THEME['fg'],
        activebackground=THEME['bg_hover'], activeforeground=THEME['fg'],
        highlightthickness=0, relief=tk.FLAT, borderwidth=0,
    )
    m["menu"].configure(
        bg=THEME['bg_input'], fg=THEME['fg'],
        activebackground=THEME['accent'], activeforeground="#ffffff",
        borderwidth=0,
    )
    return m


def styled_checkbutton(parent, text, variable, **kw):
    return tk.Checkbutton(
        parent, text=text, variable=variable,
        font=_font(10),
        bg=kw.get('bg', THEME['bg_card']), fg=THEME['fg'],
        activebackground=kw.get('bg', THEME['bg_card']),
        activeforeground=THEME['fg'],
        selectcolor=THEME['bg_input'],
        highlightthickness=0, borderwidth=0,
    )


def styled_scale(parent, variable, fr, to, res, **kw):
    return tk.Scale(
        parent, variable=variable, from_=fr, to=to, resolution=res,
        orient=tk.HORIZONTAL,
        bg=kw.get('bg', THEME['bg_card']), fg=THEME['fg'],
        troughcolor=THEME['bg_input'],
        activebackground=THEME['accent'],
        highlightthickness=0, sliderlength=16, length=140,
        borderwidth=0, showvalue=True,
    )


def styled_listbox(parent, **kw):
    lb = tk.Listbox(
        parent,
        bg=THEME['bg_input'], fg=THEME['fg'],
        selectbackground=THEME['select'], selectforeground="#ffffff",
        font=_font(10),
        relief=tk.FLAT, activestyle="none", borderwidth=0,
        highlightthickness=1, highlightbackground=THEME['border'],
        highlightcolor=THEME['accent'],
    )
    return lb


def styled_text(parent, **kw):
    return tk.Text(
        parent,
        bg=THEME['bg_input'], fg=THEME['fg'],
        insertbackground=THEME['fg'],
        selectbackground=THEME['accent'], selectforeground="#ffffff",
        font=_font(10),
        relief=tk.FLAT, borderwidth=0, highlightthickness=0,
    )


# ─── Stage 0: 프로젝트 + 파일 가져오기 ───

class Stage0Project(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=THEME['bg_main'])
        self.app = app
        self.build_ui()

    def build_ui(self):
        top = tk.Frame(self, bg=THEME['bg_main'])
        top.pack(fill=tk.X, padx=24, pady=(16, 0))

        proj_frame = tk.LabelFrame(
            top, text=" 프로젝트 ", font=_font(11, True),
            bg=THEME['bg_card'], fg=THEME['fg_dim'],
            padx=12, pady=10, borderwidth=0,
            highlightthickness=1, highlightbackground=THEME['border'],
        )
        proj_frame.pack(fill=tk.X)

        row1 = tk.Frame(proj_frame, bg=THEME['bg_card'])
        row1.pack(fill=tk.X, pady=2)
        styled_label(row1, "이름:", size=10, bg=THEME['bg_card']).pack(side=tk.LEFT)
        self.proj_name_var = tk.StringVar(value="my_mix")
        styled_entry(row1, textvariable=self.proj_name_var, width=25).pack(side=tk.LEFT, padx=6)
        styled_button(row1, "새 프로젝트", self.new_project, "primary", padx=10).pack(side=tk.LEFT, padx=4)
        styled_button(row1, "불러오기", self.load_project, padx=10).pack(side=tk.LEFT, padx=2)
        self.save_btn = styled_button(row1, "저장", self.save_project, padx=10)
        self.save_btn.pack(side=tk.LEFT, padx=2)
        self.proj_status = styled_label(row1, "", size=9, color=THEME['success'], bg=THEME['bg_card'])
        self.proj_status.pack(side=tk.RIGHT)

        row_path = tk.Frame(proj_frame, bg=THEME['bg_card'])
        row_path.pack(fill=tk.X, pady=(6, 2))
        styled_label(row_path, "저장 경로:", size=10, bg=THEME['bg_card']).pack(side=tk.LEFT)
        self.proj_path_var = tk.StringVar(value=os.path.abspath("projects"))
        styled_entry(row_path, textvariable=self.proj_path_var, width=40).pack(side=tk.LEFT, padx=6, fill=tk.X, expand=True)
        styled_button(row_path, "찾기", self._pick_proj_path, padx=8).pack(side=tk.LEFT)

        row2 = tk.Frame(proj_frame, bg=THEME['bg_card'])
        row2.pack(fill=tk.X, pady=(6, 2))
        styled_label(row2, "목표 영상 길이:", size=10, bg=THEME['bg_card']).pack(side=tk.LEFT)
        self.target_h_var = tk.StringVar(value="1")
        self.target_m_var = tk.StringVar(value="0")
        self.tolerance_var = tk.StringVar(value="10")
        styled_entry(row2, textvariable=self.target_h_var, width=3).pack(side=tk.LEFT, padx=2)
        styled_label(row2, "시간", size=10, color=THEME['fg_dim'], bg=THEME['bg_card']).pack(side=tk.LEFT)
        styled_entry(row2, textvariable=self.target_m_var, width=3).pack(side=tk.LEFT, padx=2)
        styled_label(row2, "분", size=10, color=THEME['fg_dim'], bg=THEME['bg_card']).pack(side=tk.LEFT, padx=(0, 12))
        styled_label(row2, "오차 범위:", size=10, bg=THEME['bg_card']).pack(side=tk.LEFT)
        styled_entry(row2, textvariable=self.tolerance_var, width=3).pack(side=tk.LEFT, padx=2)
        styled_label(row2, "%", size=10, color=THEME['fg_dim'], bg=THEME['bg_card']).pack(side=tk.LEFT)
        styled_label(row2, "  (±10%이면 1시간 영상은 54~66분)", size=9, color=THEME['fg_dimmer'], bg=THEME['bg_card']).pack(side=tk.LEFT)

        drop_frame = tk.Frame(self, bg=THEME['bg_main'])
        drop_frame.pack(fill=tk.X, padx=24, pady=(12, 0))
        self.drop_area = tk.Frame(
            drop_frame, bg=THEME['bg_card'],
            highlightbackground=THEME['border'],
            highlightthickness=2, highlightcolor=THEME['accent'],
        )
        self.drop_area.pack(fill=tk.X, ipady=30)
        styled_label(self.drop_area, "+", size=40, color=THEME['fg_dimmer'], bg=THEME['bg_card']).pack()
        styled_label(self.drop_area, "음악/이미지 파일을 여기에 드래그 앤 드롭",
                     size=12, color=THEME['fg_dim'], bg=THEME['bg_card']).pack()
        styled_label(self.drop_area, "MP3, WAV, FLAC, JPG, PNG 등  |  음악+사진 혼합 가능",
                     size=9, color=THEME['fg_dimmer'], bg=THEME['bg_card']).pack(pady=(2, 0))

        btn_frame = tk.Frame(self, bg=THEME['bg_main'])
        btn_frame.pack(fill=tk.X, padx=24, pady=(10, 0))
        styled_button(btn_frame, "파일 선택...", self.browse_files, padx=14).pack(side=tk.LEFT)
        styled_button(btn_frame, "전체 삭제", self.clear_files, "danger", padx=14).pack(side=tk.LEFT, padx=6)
        self.analyze_btn = styled_button(btn_frame, "분석 시작", self.start_analysis, "primary", padx=20, fg="#ffffff")
        self.analyze_btn.pack(side=tk.RIGHT)
        self.status_label = styled_label(btn_frame, "", size=9, color=THEME['fg_dim'], bg=THEME['bg_main'])
        self.status_label.pack(side=tk.RIGHT, padx=(0, 12))

        list_frame = tk.Frame(self, bg=THEME['bg_card'])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=(10, 16))
        cols = ("name", "type", "duration", "bpm", "key", "camelot")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings", selectmode="extended", height=10)
        for c, t, w in [("name", "파일명", 260), ("type", "유형", 65), ("duration", "길이", 75),
                         ("bpm", "BPM", 65), ("key", "키", 95), ("camelot", "캠롯", 65)]:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, minwidth=40)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                         background=THEME['bg_input'], foreground=THEME['fg'],
                         fieldbackground=THEME['bg_input'],
                         font=_font(10), rowheight=28, borderwidth=0)
        style.configure("Treeview.Heading",
                         background=THEME['bg_mid'], foreground=THEME['fg'],
                         font=_font(10, True), borderwidth=0, relief=tk.FLAT)
        style.map("Treeview",
                   background=[("selected", THEME['tree_sel'])],
                   foreground=[("selected", "#ffffff")])
        style.configure("Treeview", bordercolor=THEME['border'])

        sb = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.tag_configure("audio", foreground="#7ec8e3")
        self.tree.tag_configure("image", foreground="#a8d8a8")

        self._setup_dnd()

    def _setup_dnd(self):
        try:
            from tkinterdnd2 import DND_FILES
            self.drop_area.drop_target_register(DND_FILES)
            self.drop_area.dnd_bind('<<Drop>>', self._on_drop)
            self.drop_area.dnd_bind('<<DropEnter>>', lambda e: self.drop_area.configure(highlightbackground=THEME['accent']))
            self.drop_area.dnd_bind('<<DropLeave>>', lambda e: self.drop_area.configure(highlightbackground=THEME['border']))
        except Exception:
            pass
        for w in [self.drop_area] + self.drop_area.winfo_children():
            try:
                w.bind("<Button-1>", lambda e: self.browse_files())
            except:
                pass

    def _on_drop(self, event):
        self.drop_area.configure(highlightbackground=THEME['border'])
        try:
            self.add_files(self.tk.splitlist(event.data))
        except Exception:
            try:
                self.add_files([event.data])
            except:
                pass

    def browse_files(self):
        exts = " ".join(f"*{e}" for e in AUDIO_EXTS | IMAGE_EXTS)
        files = filedialog.askopenfilenames(filetypes=[("파일", exts)])
        if files: self.add_files(files)

    def add_files(self, filepaths):
        existing = {t.filepath for t in self.app.tracks}
        added = 0
        for fp in filepaths:
            fp = fp.strip()
            if not os.path.exists(fp) or fp in existing: continue
            item = TrackItem(fp)
            self.app.tracks.append(item)
            existing.add(fp)
            added += 1
            tag = item.filetype if item.filetype in ("audio", "image") else "unknown"
            self.tree.insert("", tk.END, iid=str(id(item)),
                             values=(item.filename, tag.upper(), "-", "-", "-", "-"), tags=(tag,))
        self.status_label.configure(text=f"{len(self.app.tracks)}개 파일 ({added}개 추가)")

    def clear_files(self):
        self.app.tracks.clear()
        for i in self.tree.get_children(): self.tree.delete(i)
        self.status_label.configure(text="")

    def start_analysis(self):
        audio = [t for t in self.app.tracks if t.filetype == "audio"]
        if not audio:
            messagebox.showwarning("경고", "음악 파일을 추가하세요.")
            return
        self.analyze_btn.configure(state=tk.DISABLED, text="분석 중...")

        def run():
            for i, t in enumerate(audio):
                self.after(0, lambda tt=t, ii=i: self.status_label.configure(
                    text=f"분석 중... [{ii+1}/{len(audio)}] {tt.filename}"))
                t.analyze()
                self.after(0, lambda tt=t: self._update_tree(tt))
            self.after(0, self._done)

        threading.Thread(target=run, daemon=True).start()

    def _update_tree(self, t):
        iid = str(id(t))
        if not self.tree.exists(iid): return
        if t.analysis:
            a = t.analysis
            m = "Maj" if a.mode == "major" else "Min"
            d = f"{int(a.duration//60)}:{int(a.duration%60):02d}"
            self.tree.item(iid, values=(t.filename, "AUDIO", d, f"{a.bpm:.0f}", f"{a.key} {m}", a.camelot))

    def _done(self):
        self.analyze_btn.configure(state=tk.NORMAL, text="분석 시작")
        n = sum(1 for t in self.app.tracks if t.analysis)
        self.status_label.configure(text=f"분석 완료: {n}곡")
        if n > 0: self.app.enable_next(True)

    def get_target_seconds(self):
        try:
            h = int(self.target_h_var.get() or 0)
            m = int(self.target_m_var.get() or 0)
            return h * 3600 + m * 60
        except:
            return 3600

    def get_tolerance(self):
        try: return float(self.tolerance_var.get()) / 100.0
        except: return 0.10

    def _pick_proj_path(self):
        path = filedialog.askdirectory(title="프로젝트 저장 폴더 선택")
        if path: self.proj_path_var.set(path)

    def new_project(self):
        name = self.proj_name_var.get().strip()
        if not name:
            messagebox.showwarning("경고", "프로젝트 이름을 입력하세요.")
            return
        base = self.proj_path_var.get().strip() or os.path.abspath("projects")
        self.app.project = _Project(base_dir=base)
        self.app.project.create(name)
        self.proj_status.configure(text=f"프로젝트: {name}\n{self.app.project.project_dir}")

    def load_project(self):
        path = filedialog.askdirectory(title="프로젝트 폴더 선택")
        if not path: return
        try:
            self.app.project = _Project()
            data = self.app.project.load(path)
            self.proj_name_var.set(data.get('name', ''))
            self.proj_path_var.set(os.path.dirname(self.app.project.project_dir))
            self.proj_status.configure(text=f"로드: {data.get('name','')}\n{self.app.project.project_dir}")
            self.target_h_var.set(str(int(data.get('target_duration', 3600) // 3600)))
            self.target_m_var.set(str(int(data.get('target_duration', 3600) % 3600) // 60))
            self.tolerance_var.set(str(int(data.get('tolerance', 0.10) * 100)))
            existing_files = {f['original'] for f in data.get('files', [])}
            self.add_files(list(existing_files))

            for t in self.app.tracks:
                if t.filetype == "audio" and not t.analysis:
                    a = self.app.project.get_analysis_for(t.filepath)
                    if a:
                        t.analysis = a
                        t.duration = a.duration
                        t.trim_end = a.duration
                        self._update_tree(t)

            self.app.video_groups = data.get('video_groups', [])

            for vg in self.app.video_groups:
                for t in vg.get('tracks', []):
                    if not t.get('analysis'):
                        fp = t.get('filepath', '')
                        a = self.app.project.get_analysis_for(fp)
                        if a:
                            t['analysis'] = a
                            if not t.get('duration'):
                                t['duration'] = a.duration

            n = sum(1 for t in self.app.tracks if t.analysis)
            self.status_label.configure(text=f"로드 완료: {n}곡 분석 결과 복원")
            if n > 0:
                self.app.enable_next(True)
        except Exception as e:
            messagebox.showerror("오류", str(e))

    def save_project(self):
        if not self.app.project or not self.app.project.project_dir:
            name = self.proj_name_var.get().strip()
            if not name:
                from datetime import datetime
                name = datetime.now().strftime("mix_%Y%m%d_%H%M%S")
                self.proj_name_var.set(name)
            base = self.proj_path_var.get().strip() or os.path.abspath("projects")
            self.app.project = _Project(base_dir=base)
            self.app.project.create(name)
            self.proj_status.configure(text=f"프로젝트: {name}\n{self.app.project.project_dir}")

        self.app.project.target_duration = self.get_target_seconds()
        self.app.project.tolerance = self.get_tolerance()

        analyses = {}
        for t in self.app.tracks:
            if t.analysis:
                analyses[t.filepath] = t.analysis
        video_groups = self.app.video_groups
        filepaths = [t.filepath for t in self.app.tracks]

        self.save_btn.configure(state=tk.DISABLED)
        self.proj_status.configure(text="저장 중...")

        def _on_progress(cur, total, msg):
            self.after(0, lambda c=cur, t=total, m=msg: self.proj_status.configure(text=f"{m} {c}/{t}"))

        def run():
            try:
                self.app.project.backup_files(filepaths)
                self.app.project.save(analyses=analyses, video_groups=video_groups,
                                      progress_callback=_on_progress)
                self.after(0, lambda: (
                    self.proj_status.configure(text="저장 완료!"),
                    self.save_btn.configure(state=tk.NORMAL),
                ))
            except Exception as e:
                self.after(0, lambda: (
                    messagebox.showerror("오류", f"프로젝트 저장 실패:\n{e}"),
                    self.proj_status.configure(text="저장 실패"),
                    self.save_btn.configure(state=tk.NORMAL),
                ))

        threading.Thread(target=run, daemon=True).start()


# ─── Stage 1: 자동 분배 ───

class Stage1Distribute(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=THEME['bg_main'])
        self.app = app
        self.build_ui()

    def build_ui(self):
        styled_label(self, "자동 분배", size=20, bold=True, bg=THEME['bg_main']).pack(pady=(14, 2))
        styled_label(self, "BPM/키 밸런스를 맞춰 여러 영상으로 자동 분할합니다",
                     size=11, color=THEME['fg_dim'], bg=THEME['bg_main']).pack(pady=(0, 10))

        ctrl = tk.Frame(self, bg=THEME['bg_main'])
        ctrl.pack(fill=tk.X, padx=24, pady=(0, 8))
        styled_button(ctrl, "자동 분배 실행", self.run_distribute, "primary", padx=18, pady=6).pack(side=tk.LEFT)
        self.dist_status = styled_label(ctrl, "", size=10, color=THEME['fg_dim'], bg=THEME['bg_main'])
        self.dist_status.pack(side=tk.LEFT, padx=12)

        main = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg=THEME['bg_main'], sashwidth=3, sashrelief=tk.FLAT)
        main.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 16))

        left = tk.Frame(main, bg=THEME['bg_card'])
        main.add(left, width=350, minsize=250)
        styled_label(left, "영상 그룹 목록", size=11, bold=True, bg=THEME['bg_card']).pack(pady=(10, 4), padx=10, anchor=tk.W)
        self.group_listbox = styled_listbox(left)
        self.group_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.group_listbox.bind("<<ListboxSelect>>", self.on_select_group)

        right = tk.Frame(main, bg=THEME['bg_card'])
        main.add(right, minsize=350)
        self.detail_text = styled_text(right)
        self.detail_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        bottom = tk.Frame(self, bg=THEME['bg_main'])
        bottom.pack(fill=tk.X, padx=24, pady=(0, 16))
        styled_label(bottom, "수동 이동:", size=10, bg=THEME['bg_main']).pack(side=tk.LEFT)
        self.move_from_var = tk.StringVar()
        self.move_to_var = tk.StringVar()
        styled_label(bottom, "그룹:", size=10, color=THEME['fg_dim'], bg=THEME['bg_main']).pack(side=tk.LEFT, padx=(8, 2))
        styled_entry(bottom, textvariable=self.move_from_var, width=3).pack(side=tk.LEFT)
        styled_label(bottom, "→", size=10, color=THEME['fg_dim'], bg=THEME['bg_main']).pack(side=tk.LEFT, padx=4)
        styled_entry(bottom, textvariable=self.move_to_var, width=3).pack(side=tk.LEFT)
        self.move_status = styled_label(bottom, "", size=9, color=THEME['success'], bg=THEME['bg_main'])
        self.move_status.pack(side=tk.LEFT, padx=8)

    def refresh(self):
        self.group_listbox.delete(0, tk.END)
        for i, g in enumerate(self.app.video_groups):
            dur = g.get('total_duration', 0)
            n = len(g.get('tracks', []))
            self.group_listbox.insert(tk.END, f"Mix {i+1}: {n}곡, {int(dur)}초 ({int(dur//60)}분 {int(dur%60):02d}초)")
        self._show_detail(None)

    def on_select_group(self, event):
        sel = self.group_listbox.curselection()
        if not sel: return
        self._show_detail(sel[0])

    def _show_detail(self, idx):
        self.detail_text.configure(state=tk.NORMAL)
        self.detail_text.delete("1.0", tk.END)
        if idx is None or idx >= len(self.app.video_groups):
            self.detail_text.insert("1.0", "그룹을 선택하세요")
            self.detail_text.configure(state=tk.DISABLED)
            return
        g = self.app.video_groups[idx]
        lines = [f"=== Mix {idx+1}: {g.get('name','')} ===",
                 f"총 길이: {g.get('total_duration',0):.0f}초 "
                 f"({int(g.get('total_duration',0)//60)}분 {int(g.get('total_duration',0)%60):02d}초)",
                 f"곡 수: {len(g.get('tracks',[]))}", ""]
        for j, t in enumerate(g.get('tracks', [])):
            a = t.get('analysis')
            if a:
                m = "Maj" if a.mode == "major" else "Min"
                dur = t.get('duration', a.duration)
                lines.append(f"  [{j+1}] {t.get('filename','')}")
                lines.append(f"       {a.bpm:.0f} BPM | {a.key} {m} ({a.camelot}) | {dur:.0f}s")
            else:
                lines.append(f"  [{j+1}] {t.get('filename','')} (미분석)")
        self.detail_text.insert("1.0", "\n".join(lines))
        self.detail_text.configure(state=tk.DISABLED)

    def run_distribute(self):
        audio_tracks = [t for t in self.app.tracks if t.filetype == "audio" and t.analysis]
        if not audio_tracks:
            messagebox.showwarning("경고", "분석된 음악이 없습니다.")
            return
        target = self.app.stages[0].get_target_seconds()
        tol = self.app.stages[0].get_tolerance()
        n = len(audio_tracks)
        self.dist_status.configure(text=f"분배 중... (0/{n}곡)")

        def _on_progress(current, total, msg):
            self.after(0, lambda c=current, t=total, m=msg: self.dist_status.configure(text=f"{m} {c+1}/{t}"))

        def run():
            groups = _distribute_tracks(audio_tracks, target, tol, progress_callback=_on_progress)
            for g in groups:
                for ti in g['tracks']:
                    ti['analysis'] = ti['track'].analysis

            def _apply():
                self.app.video_groups = groups
                self.refresh()
                self.dist_status.configure(text=f"{len(groups)}개 영상 생성됨")
                # 분배가 화면 전환 없이 같은 화면에서 끝나기 때문에, show_stage()가
                # 아니면 아무도 next_btn 상태를 다시 계산해주지 않아 "다음" 버튼이
                # 계속 비활성으로 남아있던 문제. 여기서 직접 활성화해준다.
                self.app.enable_next(bool(groups))
            self.after(0, _apply)
        threading.Thread(target=run, daemon=True).start()


# ─── Stage 2: 음악 편집 (타임라인) ───

_TIMELINE_COLORS = ['#5865f2', '#57f287', '#fee75c', '#ed4245', '#eb459e',
                     '#ff9063', '#3ba55c', '#5865f2', '#e67e22', '#9b59b6']

def _fmt_ts(sec):
    m = int(sec) // 60
    s = int(sec) % 60
    return f"{m}:{s:02d}"


class Stage2MusicEdit(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=THEME['bg_main'])
        self.app = app
        self.selected_group = -1
        self.tl_sel = -1
        self.tl_drag = None
        self.tl_px_per_sec = 8
        self.tl_scroll_x = 0
        self.LANE_H = 44
        self.build_ui()

    def build_ui(self):
        styled_label(self, "음악 편집", size=20, bold=True, bg=THEME['bg_main']).pack(pady=(14, 2))
        styled_label(self, "타임라인에서 트랙의 시작/끝을 드래그하면 뒤의 트랙이 자동으로 밀립니다",
                     size=11, color=THEME['fg_dim'], bg=THEME['bg_main']).pack(pady=(0, 6))

        top = tk.Frame(self, bg=THEME['bg_main'])
        top.pack(fill=tk.X, padx=24)
        self.tabs_container = tk.Frame(top, bg=THEME['bg_main'])
        self.tabs_container.pack(side=tk.LEFT)

        styled_button(top, "줌 인", self._zoom_in, padx=6).pack(side=tk.RIGHT, padx=(4, 0))
        styled_button(top, "줌 아웃", self._zoom_out, padx=6).pack(side=tk.RIGHT)
        styled_button(top, "전체 보기", self._zoom_fit, padx=6).pack(side=tk.RIGHT, padx=(0, 4))
        styled_button(top, "전체 초기화", self._reset_all, padx=6).pack(side=tk.RIGHT, padx=(0, 4))

        info_row = tk.Frame(self, bg=THEME['bg_main'])
        info_row.pack(fill=tk.X, padx=24, pady=(2, 2))
        self.tl_info = styled_label(info_row, "그룹을 선택하세요", size=10, color=THEME['fg_dim'], bg=THEME['bg_main'])
        self.tl_info.pack(side=tk.LEFT)

        tl_frame = tk.Frame(self, bg=THEME['wave_bg'])
        tl_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 4))
        self.tl_hscroll = tk.Scrollbar(tl_frame, orient=tk.HORIZONTAL)
        self.tl_hscroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.tl_canvas = tk.Canvas(tl_frame, bg=THEME['wave_bg'], highlightthickness=0,
                                    xscrollcommand=self.tl_hscroll.set)
        self.tl_canvas.pack(fill=tk.BOTH, expand=True)
        self.tl_hscroll.configure(command=self.tl_canvas.xview)
        self.tl_canvas.bind("<ButtonPress-1>", self._tl_press)
        self.tl_canvas.bind("<B1-Motion>", self._tl_drag_motion)
        self.tl_canvas.bind("<ButtonRelease-1>", self._tl_release)
        self.tl_canvas.bind("<Motion>", self._tl_hover)
        self.tl_canvas.bind("<MouseWheel>", self._tl_scroll)
        self.tl_canvas.bind("<Button-4>", lambda e: self._tl_scroll_linux(1))
        self.tl_canvas.bind("<Button-5>", lambda e: self._tl_scroll_linux(-1))

        tf = tk.Frame(self, bg=THEME['bg_main'])
        tf.pack(fill=tk.X, padx=24, pady=(0, 8))
        styled_label(tf, "시작:", size=10, bg=THEME['bg_main']).pack(side=tk.LEFT)
        self.start_ent = styled_entry(tf, width=7)
        self.start_ent.pack(side=tk.LEFT, padx=3)
        self.start_ent.bind("<Return>", lambda e: self._apply_entry())
        styled_label(tf, "끝:", size=10, bg=THEME['bg_main']).pack(side=tk.LEFT, padx=(8, 0))
        self.end_ent = styled_entry(tf, width=7)
        self.end_ent.pack(side=tk.LEFT, padx=3)
        self.end_ent.bind("<Return>", lambda e: self._apply_entry())
        styled_button(tf, "적용", self._apply_entry, "primary", padx=8).pack(side=tk.LEFT, padx=4)

        btn_row = tk.Frame(self, bg=THEME['bg_main'])
        btn_row.pack(fill=tk.X, padx=24, pady=(0, 10))
        styled_button(btn_row, "▲ 순서 변경", self._move_up, padx=10).pack(side=tk.LEFT)
        styled_button(btn_row, "▼ 순서 변경", self._move_down, padx=10).pack(side=tk.LEFT, padx=4)

        self._recompute_positions()

    def _recompute_positions(self):
        if self.selected_group < 0 or self.selected_group >= len(self.app.video_groups):
            self._track_rects = []
            return
        tracks = self.app.video_groups[self.selected_group].get('tracks', [])
        rects = []
        x_cursor = 0
        for i, t in enumerate(tracks):
            ts = t.get('trim_start', 0)
            te = t.get('trim_end', 0)
            a = t.get('analysis')
            if a:
                if te <= 0:
                    te = a.duration
                dur = max(0.1, te - ts)
            else:
                dur = t.get('duration', 1)
            x_start = x_cursor
            x_end = x_cursor + dur
            rects.append({'idx': i, 'x_start': x_start, 'x_end': x_end, 'track': t})
            x_cursor = x_end
        self._track_rects = rects

    def _draw_timeline(self):
        self.tl_canvas.delete("all")
        cw = self.tl_canvas.winfo_width()
        ch = self.tl_canvas.winfo_height()
        if cw < 20 or ch < 20:
            return
        lane_top = 36
        pps = self.tl_px_per_sec

        self.tl_canvas.create_line(0, lane_top - 1, cw, lane_top - 1, fill=THEME['separator'], width=1)

        total_dur = 0
        if self._track_rects:
            total_dur = self._track_rects[-1]['x_end']
        n_secs = int(total_dur) + 10

        if pps >= 20:
            major_step = 5
            minor_step = 1
        elif pps >= 8:
            major_step = 10
            minor_step = 5
        elif pps >= 3:
            major_step = 30
            minor_step = 10
        else:
            major_step = 60
            minor_step = 30

        for s in range(0, n_secs + 1):
            x = int(s * pps)
            if x > int(total_dur * pps) + cw:
                break
            if s % major_step == 0:
                self.tl_canvas.create_line(x, lane_top, x, ch, fill=THEME['separator'], width=1)
                self.tl_canvas.create_text(x + 3, lane_top - 12, text=_fmt_ts(s),
                                           fill=THEME['fg_dim'], font=_font(8), anchor=tk.W)
            elif s % minor_step == 0:
                self.tl_canvas.create_line(x, lane_top, x, ch, fill=THEME['bg_hover'], width=1)

        for ri, r in enumerate(self._track_rects):
            x1 = int(r['x_start'] * pps)
            x2 = int(r['x_end'] * pps)
            y1 = lane_top + 4
            y2 = lane_top + self.LANE_H - 4
            color = _TIMELINE_COLORS[ri % len(_TIMELINE_COLORS)]
            is_sel = (ri == self.tl_sel)

            self.tl_canvas.create_rectangle(x1, y1, x2, y2,
                                            fill=color if is_sel else THEME['bg_input'],
                                            outline=color, width=2 if is_sel else 1,
                                            tags=("tl_rect", f"tl_{ri}"))

            a = r['track'].get('analysis')
            fname = r['track'].get('filename', '')
            if len(fname) > 20:
                fname = fname[:17] + "..."
            label = fname
            if a:
                dur_sec = r['x_end'] - r['x_start']
                label = f"{fname}  {_fmt_ts(dur_sec)}"
            self.tl_canvas.create_text(x1 + 8, (y1 + y2) // 2, text=label,
                                       fill=THEME['fg'], font=_font(9), anchor=tk.W, tags=(f"tl_{ri}",))

            edge_w = max(6, min(16, int((x2 - x1) * 0.10)))
            self.tl_canvas.create_rectangle(x1, y1, x1 + edge_w, y2,
                                            fill=THEME['accent'], outline='', tags=("tl_edge", f"tl_{ri}"))
            self.tl_canvas.create_rectangle(x1 + 2, y1 + 4, x1 + 3, y2 - 4,
                                            fill='#ffffff', outline='', tags=("tl_edge", f"tl_{ri}"))
            self.tl_canvas.create_rectangle(x2 - edge_w, y1, x2, y2,
                                            fill=THEME['wave_trim'], outline='', tags=("tl_edge", f"tl_{ri}"))
            self.tl_canvas.create_rectangle(x2 - 3, y1 + 4, x2 - 2, y2 - 4,
                                            fill='#ffffff', outline='', tags=("tl_edge", f"tl_{ri}"))

        time_label = f"총 {_fmt_ts(total_dur)} ({int(total_dur)}초)"
        self.tl_info.configure(text=f"트랙 {len(self._track_rects)}개  |  {time_label}")

        if self.selected_group >= 0:
            self.tl_canvas.configure(scrollregion=(0, 0, int(total_dur * pps) + 50, ch))

    def _px_to_track(self, px):
        pps = self.tl_px_per_sec
        sec = px / max(pps, 1)
        for r in self._track_rects:
            if r['x_start'] <= sec <= r['x_end']:
                return r
        return None

    def _tl_press(self, event):
        if self.selected_group < 0 or not self._track_rects:
            return
        cx = self.tl_canvas.canvasx(event.x)
        cy = self.tl_canvas.canvasy(event.y)
        r = self._px_to_track(cx)
        if not r:
            return
        ri = r['idx']
        self.tl_sel = ri
        self._draw_timeline()
        pps = self.tl_px_per_sec
        sec = cx / max(pps, 1)
        x1 = r['x_start']
        x2 = r['x_end']
        edge_px = max(15 / pps, 0.15)
        if abs(sec - x1) < edge_px:
            self.tl_drag = {'mode': 'trim_start', 'idx': ri, 'offset_sec': sec - x1}
        elif abs(sec - x2) < edge_px:
            self.tl_drag = {'mode': 'trim_end', 'idx': ri, 'offset_sec': sec - x2}
        else:
            self.tl_drag = None
        self._update_entries()

    def _tl_drag_motion(self, event):
        if not self.tl_drag or self.selected_group < 0:
            return
        cx = self.tl_canvas.canvasx(event.x)
        pps = self.tl_px_per_sec
        sec = cx / max(pps, 1)
        tracks = self.app.video_groups[self.selected_group].get('tracks', [])
        ri = self.tl_drag['idx']
        t = tracks[ri]
        a = t.get('analysis')
        if not a:
            return
        orig_dur = a.duration
        mode = self.tl_drag['mode']

        if mode == 'trim_start':
            new_start = max(0, min(sec - self.tl_drag['offset_sec'], t.get('trim_end', orig_dur) - 0.5))
            old_start = t.get('trim_start', 0)
            delta = new_start - old_start
            t['trim_start'] = new_start
            for j in range(ri + 1, len(tracks)):
                tj = tracks[j]
                tj_old_start = tj.get('trim_start', 0)
                tj['trim_start'] = max(0, tj_old_start + delta)
                a_j = tj.get('analysis')
                if a_j:
                    if tj.get('trim_end', 0) <= 0:
                        tj['trim_end'] = a_j.duration
                    tj['trim_end'] = max(tj['trim_start'] + 0.5, min(tj.get('trim_end', a_j.duration) + delta, a_j.duration))
        elif mode == 'trim_end':
            old_end = t.get('trim_end', orig_dur)
            new_end = max(t.get('trim_start', 0) + 0.5, min(sec - self.tl_drag['offset_sec'], orig_dur))
            delta = new_end - old_end
            t['trim_end'] = new_end
            for j in range(ri + 1, len(tracks)):
                tj = tracks[j]
                tj_old_start = tj.get('trim_start', 0)
                tj['trim_start'] = max(0, tj_old_start + delta)
                a_j = tj.get('analysis')
                if a_j:
                    if tj.get('trim_end', 0) <= 0:
                        tj['trim_end'] = a_j.duration
                    tj['trim_end'] = max(tj['trim_start'] + 0.5, min(tj.get('trim_end', a_j.duration) + delta, a_j.duration))

        self._recompute_positions()
        self._draw_timeline()
        self._update_entries()

    def _tl_release(self, event):
        self.tl_drag = None
        self.tl_canvas.configure(cursor='')
        self._update_entries()

    def _tl_hover(self, event):
        if self.tl_drag or self.selected_group < 0:
            return
        cx = self.tl_canvas.canvasx(event.x)
        r = self._px_to_track(cx)
        if not r:
            self.tl_canvas.configure(cursor='')
            return
        pps = self.tl_px_per_sec
        sec = cx / max(pps, 1)
        edge_px = max(15 / pps, 0.15)
        x1 = r['x_start']
        x2 = r['x_end']
        if abs(sec - x1) < edge_px or abs(sec - x2) < edge_px:
            self.tl_canvas.configure(cursor='sb_h_double_arrow')
        else:
            self.tl_canvas.configure(cursor='')

    def _tl_scroll(self, event):
        if event.state & 0x4:
            if event.delta > 0:
                self.tl_px_per_sec = min(80, self.tl_px_per_sec * 1.2)
            else:
                self.tl_px_per_sec = max(1, self.tl_px_per_sec / 1.2)
            self._recompute_positions()
            self._draw_timeline()
        else:
            self.tl_canvas.xview_scroll(int(-event.delta / 120), "units")

    def _tl_scroll_linux(self, direction):
        if direction > 0:
            self.tl_px_per_sec = min(80, self.tl_px_per_sec * 1.2)
        else:
            self.tl_px_per_sec = max(1, self.tl_px_per_sec / 1.2)
        self._recompute_positions()
        self._draw_timeline()

    def _zoom_in(self):
        self.tl_px_per_sec = min(80, self.tl_px_per_sec * 1.5)
        self._recompute_positions()
        self._draw_timeline()

    def _zoom_out(self):
        self.tl_px_per_sec = max(1, self.tl_px_per_sec / 1.5)
        self._recompute_positions()
        self._draw_timeline()

    def _zoom_fit(self):
        if not self._track_rects:
            return
        self.tl_canvas.update_idletasks()
        cw = self.tl_canvas.winfo_width()
        total = self._track_rects[-1]['x_end']
        if total > 0:
            self.tl_px_per_sec = max(1, (cw - 60) / total)
        self._recompute_positions()
        self._draw_timeline()

    def _update_entries(self):
        if self.tl_sel < 0 or self.selected_group < 0:
            return
        tracks = self.app.video_groups[self.selected_group].get('tracks', [])
        if self.tl_sel >= len(tracks):
            return
        t = tracks[self.tl_sel]
        a = t.get('analysis')
        ts = t.get('trim_start', 0)
        te = t.get('trim_end', a.duration if a else 0)
        self.start_ent.delete(0, tk.END)
        self.start_ent.insert(0, f"{ts:.2f}")
        self.end_ent.delete(0, tk.END)
        self.end_ent.insert(0, f"{te:.2f}")

    def _apply_entry(self):
        if self.tl_sel < 0 or self.selected_group < 0:
            return
        tracks = self.app.video_groups[self.selected_group].get('tracks', [])
        if self.tl_sel >= len(tracks):
            return
        t = tracks[self.tl_sel]
        a = t.get('analysis')
        if not a:
            return
        try:
            s = float(self.start_ent.get())
            e = float(self.end_ent.get())
            old_start = t.get('trim_start', 0)
            new_start = max(0, min(s, a.duration))
            delta = new_start - old_start
            t['trim_start'] = new_start
            t['trim_end'] = max(new_start + 0.5, min(e, a.duration))
            for j in range(self.tl_sel + 1, len(tracks)):
                tj = tracks[j]
                tj['trim_start'] = max(0, tj.get('trim_start', 0) + delta)
                a_j = tj.get('analysis')
                if a_j:
                    if tj.get('trim_end', 0) <= 0:
                        tj['trim_end'] = a_j.duration
                    tj['trim_end'] = max(tj['trim_start'] + 0.5,
                                         min(tj.get('trim_end', a_j.duration) + delta, a_j.duration))
            self._recompute_positions()
            self._draw_timeline()
        except Exception:
            pass

    def _reset_all(self):
        if self.selected_group < 0:
            return
        tracks = self.app.video_groups[self.selected_group].get('tracks', [])
        for t in tracks:
            a = t.get('analysis')
            if a:
                t['trim_start'] = 0
                t['trim_end'] = a.duration
        self._recompute_positions()
        self._draw_timeline()
        self._update_entries()

    def _move_up(self):
        if self.tl_sel <= 0 or self.selected_group < 0:
            return
        tracks = self.app.video_groups[self.selected_group].get('tracks', [])
        i = self.tl_sel
        tracks[i], tracks[i - 1] = tracks[i - 1], tracks[i]
        self.tl_sel = i - 1
        self._recompute_positions()
        self._draw_timeline()
        self._update_entries()

    def _move_down(self):
        if self.selected_group < 0:
            return
        tracks = self.app.video_groups[self.selected_group].get('tracks', [])
        i = self.tl_sel
        if i < 0 or i >= len(tracks) - 1:
            return
        tracks[i], tracks[i + 1] = tracks[i + 1], tracks[i]
        self.tl_sel = i + 1
        self._recompute_positions()
        self._draw_timeline()
        self._update_entries()

    def refresh(self):
        if not self.app.video_groups:
            self.selected_group = -1
            self.tl_sel = -1
            self._track_rects = []
            populate_group_tabs(self.tabs_container, [], -1, self._set_group)
            self._draw_timeline()
            return

        # 새로고침해도 기존에 보고 있던 영상 선택은 그대로 유지 (범위를 벗어나면 0번으로)
        idx = self.selected_group if 0 <= self.selected_group < len(self.app.video_groups) else 0
        self._set_group(idx)

    def _set_group(self, idx):
        self.selected_group = idx
        populate_group_tabs(self.tabs_container, self.app.video_groups, idx, self._set_group)
        self.tl_sel = -1
        self._recompute_positions()
        self.after(50, self._zoom_fit)


# ─── Stage 3: 영상 편집 + 렌더링 ───

class Stage3VideoEdit(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=THEME['bg_main'])
        self.app = app
        self.selected_group = 0
        self.build_ui()

    def build_ui(self):
        styled_label(self, "영상 편집 + 렌더링", size=20, bold=True, bg=THEME['bg_main']).pack(pady=(14, 2))

        self.tabs_container = tk.Frame(self, bg=THEME['bg_main'])
        self.tabs_container.pack(pady=(0, 4))

        main = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg=THEME['bg_main'], sashwidth=3, sashrelief=tk.FLAT)
        main.pack(fill=tk.BOTH, expand=True, padx=15, pady=(8, 16))

        left = tk.Frame(main, bg=THEME['bg_card'])
        main.add(left, width=350, minsize=280)
        canvas = tk.Canvas(left, bg=THEME['bg_card'], highlightthickness=0)
        sb = ttk.Scrollbar(left, orient=tk.VERTICAL, command=canvas.yview)
        sf = tk.Frame(canvas, bg=THEME['bg_card'])
        sf.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=sf, anchor=tk.NW)
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        def _sf_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind("<MouseWheel>", _sf_mousewheel)
        sf.bind("<MouseWheel>", _sf_mousewheel)
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _sf_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        self.viz_type = tk.StringVar(value="eq_bars")
        self.viz_pos = tk.StringVar(value="bottom")
        self.viz_color = tk.StringVar(value="#ffffff")
        self.viz_bars = tk.IntVar(value=64)
        self.viz_height = tk.IntVar(value=120)
        self.viz_smooth = tk.DoubleVar(value=0.3)
        self.bg_image = tk.StringVar(value="")
        self.fade_in = tk.DoubleVar(value=2.0)
        self.fade_out = tk.DoubleVar(value=3.0)
        self.show_title = tk.BooleanVar(value=True)
        self.show_bpm = tk.BooleanVar(value=True)
        self.show_key = tk.BooleanVar(value=True)
        self.show_camelot = tk.BooleanVar(value=False)
        self.show_time = tk.BooleanVar(value=True)
        self.show_progress = tk.BooleanVar(value=True)
        self.fx_bounce = tk.BooleanVar(value=False)
        self.fx_shake = tk.BooleanVar(value=False)
        self.fx_zoom = tk.BooleanVar(value=False)
        self.fx_flash = tk.BooleanVar(value=False)
        self.fx_bounce_i = tk.DoubleVar(value=1.03)
        self.fx_shake_i = tk.DoubleVar(value=3)
        self.fx_zoom_i = tk.DoubleVar(value=1.05)
        self.fx_flash_i = tk.DoubleVar(value=0.3)
        self.resolution = tk.StringVar(value="1080p")

        def sec(t):
            styled_label(sf, t, size=11, bold=True, bg=THEME['bg_card']).pack(fill=tk.X, pady=(12, 3), padx=12, anchor=tk.W)

        def sep():
            tk.Frame(sf, bg=THEME['separator'], height=1).pack(fill=tk.X, padx=12, pady=6)

        def opt(label, var, opts):
            f = tk.Frame(sf, bg=THEME['bg_card'])
            f.pack(fill=tk.X, padx=12, pady=2)
            if label: styled_label(f, label, size=10, bg=THEME['bg_card']).pack(side=tk.LEFT)
            m = styled_option_menu(f, var, opts)
            m.pack(side=tk.LEFT, fill=tk.X, expand=True)

        def chk(label, var):
            f = tk.Frame(sf, bg=THEME['bg_card'])
            f.pack(fill=tk.X, padx=12, pady=2)
            styled_checkbutton(f, label, var, bg=THEME['bg_card']).pack(side=tk.LEFT)

        def sld(label, var, fr, to, res):
            f = tk.Frame(sf, bg=THEME['bg_card'])
            f.pack(fill=tk.X, padx=12, pady=2)
            styled_label(f, label, size=10, bg=THEME['bg_card'], width=11).pack(side=tk.LEFT)
            styled_scale(f, var, fr, to, res, bg=THEME['bg_card']).pack(side=tk.LEFT, fill=tk.X, expand=True)

        sec("배경 이미지")
        bf = tk.Frame(sf, bg=THEME['bg_card'])
        bf.pack(fill=tk.X, padx=12, pady=(0, 3))
        styled_entry(bf, textvariable=self.bg_image, width=20).pack(side=tk.LEFT, fill=tk.X, expand=True)
        styled_button(bf, "찾기", lambda: self._pick_bg(), padx=6).pack(side=tk.RIGHT, padx=(4, 0))
        styled_label(sf, " 없으면 키 기반 그라디언트", size=8, color=THEME['fg_dimmer'], bg=THEME['bg_card']).pack(anchor=tk.W, padx=12)

        sep()
        sec("비주얼라이저")
        opt("타입:", self.viz_type, ["eq_bars", "waveform", "spectrum", "circles", "radial", "none"])
        opt("위치:", self.viz_pos, ["top", "bottom"])
        sld("바 개수:", self.viz_bars, 8, 256, 8)
        sld("높이:", self.viz_height, 40, 300, 10)
        sld("스무딩:", self.viz_smooth, 0, 0.95, 0.05)

        self.viz_x_var = tk.DoubleVar(value=0)
        self.viz_y_var = tk.DoubleVar(value=0)
        self.viz_w_var = tk.IntVar(value=0)
        sv1 = tk.Frame(sf, bg=THEME['bg_card'])
        sv1.pack(fill=tk.X, padx=12, pady=2)
        styled_label(sv1, "X 오프셋:", size=10, bg=THEME['bg_card']).pack(side=tk.LEFT)
        styled_scale(sv1, self.viz_x_var, 0, 960, 1, bg=THEME['bg_card']).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        sv2 = tk.Frame(sf, bg=THEME['bg_card'])
        sv2.pack(fill=tk.X, padx=12, pady=2)
        styled_label(sv2, "Y 오프셋:", size=10, bg=THEME['bg_card']).pack(side=tk.LEFT)
        styled_scale(sv2, self.viz_y_var, 0, 540, 1, bg=THEME['bg_card']).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        sv3 = tk.Frame(sf, bg=THEME['bg_card'])
        sv3.pack(fill=tk.X, padx=12, pady=2)
        styled_label(sv3, "너비:", size=10, bg=THEME['bg_card']).pack(side=tk.LEFT)
        styled_scale(sv3, self.viz_w_var, 0, 1920, 1, bg=THEME['bg_card']).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        sep()
        sec("페이드")
        sld("인 (초):", self.fade_in, 0, 10, 0.5)
        sld("아웃 (초):", self.fade_out, 0, 10, 0.5)

        sep()
        sec("텍스트")
        chk("제목", self.show_title)
        chk("BPM", self.show_bpm)
        chk("키", self.show_key)
        chk("캠롯", self.show_camelot)
        chk("타이머", self.show_time)
        chk("프로그레스 바", self.show_progress)

        sep()
        sec("커스텀 텍스트")
        self.custom_text_var = tk.StringVar(value="")
        cf1 = tk.Frame(sf, bg=THEME['bg_card'])
        cf1.pack(fill=tk.X, padx=12, pady=2)
        styled_label(cf1, "텍스트:", size=10, bg=THEME['bg_card']).pack(side=tk.LEFT)
        styled_entry(cf1, textvariable=self.custom_text_var, width=20).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        cf2 = tk.Frame(sf, bg=THEME['bg_card'])
        cf2.pack(fill=tk.X, padx=12, pady=2)
        self.custom_x_var = tk.DoubleVar(value=0.5)
        self.custom_y_var = tk.DoubleVar(value=0.3)
        styled_label(cf2, "X 위치:", size=10, bg=THEME['bg_card']).pack(side=tk.LEFT)
        styled_scale(cf2, self.custom_x_var, 0.0, 1.0, 0.01, bg=THEME['bg_card']).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        cf3 = tk.Frame(sf, bg=THEME['bg_card'])
        cf3.pack(fill=tk.X, padx=12, pady=2)
        styled_label(cf3, "Y 위치:", size=10, bg=THEME['bg_card']).pack(side=tk.LEFT)
        styled_scale(cf3, self.custom_y_var, 0.0, 1.0, 0.01, bg=THEME['bg_card']).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        cf4 = tk.Frame(sf, bg=THEME['bg_card'])
        cf4.pack(fill=tk.X, padx=12, pady=2)
        self.custom_font_size_var = tk.IntVar(value=36)
        self.custom_bold_var = tk.BooleanVar(value=False)
        self.custom_italic_var = tk.BooleanVar(value=False)
        self.custom_underline_var = tk.BooleanVar(value=False)
        styled_label(cf4, "폰트 크기:", size=10, bg=THEME['bg_card']).pack(side=tk.LEFT)
        styled_scale(cf4, self.custom_font_size_var, 8, 120, 1, bg=THEME['bg_card']).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        cf5 = tk.Frame(sf, bg=THEME['bg_card'])
        cf5.pack(fill=tk.X, padx=12, pady=2)
        styled_checkbutton(cf5, "볼드", self.custom_bold_var, bg=THEME['bg_card']).pack(side=tk.LEFT, padx=(0,8))
        styled_checkbutton(cf5, "기울임", self.custom_italic_var, bg=THEME['bg_card']).pack(side=tk.LEFT, padx=(0,8))
        styled_checkbutton(cf5, "밑줄", self.custom_underline_var, bg=THEME['bg_card']).pack(side=tk.LEFT)

        self.custom_color_var = tk.StringVar(value="#ffffff")
        cf6 = tk.Frame(sf, bg=THEME['bg_card'])
        cf6.pack(fill=tk.X, padx=12, pady=2)
        styled_label(cf6, "색상:", size=10, bg=THEME['bg_card']).pack(side=tk.LEFT)
        styled_entry(cf6, textvariable=self.custom_color_var, width=10).pack(side=tk.LEFT, padx=4)

        self.custom_affects_fx_var = tk.BooleanVar(value=True)
        cf7 = tk.Frame(sf, bg=THEME['bg_card'])
        cf7.pack(fill=tk.X, padx=12, pady=2)
        styled_checkbutton(cf7, "이펙트(흔들림/페이드) 영향 받음", self.custom_affects_fx_var, bg=THEME['bg_card']).pack(side=tk.LEFT)

        sep()
        sec("비트 이펙트")
        chk("바운스 (위아래 통통)", self.fx_bounce)
        sld("  강도:", self.fx_bounce_i, 1.01, 1.15, 0.01)
        chk("쉐이크 (화면 흔들림)", self.fx_shake)
        sld("  강도:", self.fx_shake_i, 1, 20, 1)
        chk("줌 (확대/축소)", self.fx_zoom)
        sld("  강도:", self.fx_zoom_i, 1.01, 1.20, 0.01)
        chk("플래시 (번쩍)", self.fx_flash)
        sld("  강도:", self.fx_flash_i, 0.05, 0.8, 0.05)

        styled_button(sf, "미리보기 새로고침", self._refresh_canvas_preview, "primary", padx=8).pack(padx=12, pady=4, anchor=tk.W)

        sep()
        sec("해상도")
        opt("", self.resolution, ["720p", "1080p", "4k"])

        right = tk.Frame(main, bg=THEME['bg_card'])
        main.add(right, minsize=400)

        styled_label(right, "미리보기", size=12, bold=True, bg=THEME['bg_card']).pack(pady=(12, 4))
        self.preview_canvas = tk.Canvas(right, bg=THEME['bg'], highlightthickness=1,
                                        highlightbackground=THEME['separator'])
        self.preview_canvas.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 4))
        self._preview_photo = None
        self._last_preview_pil_frame = None
        self.preview_canvas.bind("<Configure>", self._on_preview_canvas_resize)

        prev_ctrl = tk.Frame(right, bg=THEME['bg_card'])
        prev_ctrl.pack(fill=tk.X, padx=12, pady=(0, 4))
        self.preview_play_btn = styled_button(prev_ctrl, "▶ 실시간 재생", self._preview_render_video, "primary", padx=6)
        self.preview_play_btn.pack(side=tk.RIGHT, padx=2)
        styled_button(prev_ctrl, "새로고침", self._refresh_canvas_preview, padx=6).pack(side=tk.RIGHT, padx=2)
        self._preview_status_label = styled_label(prev_ctrl, "설정 변경 후 새로고침", size=9, color=THEME['fg_dim'], bg=THEME['bg_card'])
        self._preview_status_label.pack(side=tk.LEFT)

        scrub_frame = tk.Frame(right, bg=THEME['bg_card'])
        scrub_frame.pack(fill=tk.X, padx=12, pady=(0, 4))
        self.scrub_var = tk.DoubleVar(value=0)
        self.scrub_scale = ttk.Scale(scrub_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                                      variable=self.scrub_var, command=self._on_scrub_drag)
        self.scrub_scale.pack(fill=tk.X, side=tk.LEFT, expand=True)
        self.scrub_scale.state(['disabled'])
        self._live_renderer = None
        self._live_duration = 0.0
        self._scrub_playing = False
        self._scrub_after_id = None
        self._programmatic_scrub = False

        sep_r = tk.Frame(right, bg=THEME['separator'], height=1)
        sep_r.pack(fill=tk.X, padx=12, pady=6)

        styled_label(right, "렌더링 대기열", size=12, bold=True, bg=THEME['bg_card']).pack(pady=(4, 6))

        self.queue_listbox = styled_listbox(right)
        self.queue_listbox.configure(height=10)
        self.queue_listbox.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))

        self.render_btn = styled_button(right, "전체 렌더링 시작", self._start_render, "primary", padx=10, pady=8)
        self.render_btn.pack(fill=tk.X, padx=12, pady=(0, 6))
        self.render_status = styled_label(right, "", size=9, color=THEME['fg_dim'], bg=THEME['bg_card'])
        self.render_status.pack(padx=12, anchor=tk.W)
        self.render_progress_frame = tk.Frame(right, bg=THEME['bg_card'])
        self.render_progress_frame.pack(fill=tk.X, padx=12, pady=(4, 8))
        self.render_progress_canvas = tk.Canvas(self.render_progress_frame, bg=THEME['bg_hover'],
                                                 height=12, highlightthickness=0)
        self.render_progress_canvas.pack(fill=tk.X)
        self.render_progress_label = styled_label(self.render_progress_frame, "", size=8,
                                                   color=THEME['fg_dim'], bg=THEME['bg_card'])
        self.render_progress_label.pack(anchor=tk.W)

        # sf 안의 모든 자식 위젯(버튼/슬라이더/드롭다운 등)에도 같은 마우스휠
        # 핸들러를 재귀적으로 걸어준다. 안 그러면 canvas의 <Leave>가 발생해
        # (커서가 자식 위젯으로 넘어가는 순간) unbind_all이 실행되어, 컨트롤
        # 위에서는 스크롤이 먹지 않는 문제가 있었다.
        def _bind_wheel_recursive(widget):
            widget.bind("<MouseWheel>", _sf_mousewheel)
            widget.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _sf_mousewheel))
            widget.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
            for child in widget.winfo_children():
                _bind_wheel_recursive(child)

        _bind_wheel_recursive(sf)

    def refresh(self):
        self.queue_listbox.delete(0, tk.END)
        for i, g in enumerate(self.app.video_groups):
            dur = g.get('total_duration', 0)
            n = len(g.get('tracks', []))
            self.queue_listbox.insert(tk.END, f"Mix {i+1}: {n}곡, {int(dur)}초 ({int(dur//60)}분 {int(dur%60):02d}초)  [대기]")

        # 영상이 2개 이상이면 미리보기 대상을 고를 수 있는 탭을 보여준다.
        # (예전엔 항상 video_groups[0]만 미리보기/편집 대상이라, 2번째 영상부터는
        # 화면 상에서 아예 손댈 방법이 없었음)
        if 0 <= self.selected_group < len(self.app.video_groups):
            idx = self.selected_group
        else:
            idx = 0
            self.selected_group = 0
        populate_group_tabs(self.tabs_container, self.app.video_groups, idx, self._set_group)

        # Stage0(프로젝트+가져오기)에서 음악과 함께 드래그앤드롭한 이미지가 있으면
        # 배경 이미지로 자동 연결한다. 지금까지는 이미지 파일이 트랙 목록에는
        # 추가되지만 어디에서도 배경 설정으로 이어지지 않아서, 사용자가 매번
        # "찾아보기"로 같은 파일을 다시 지정해야 했음. 사용자가 이미 배경을
        # 직접 지정/변경한 경우(비어있지 않음)는 덮어쓰지 않는다.
        if not self.bg_image.get():
            for t in self.app.tracks:
                if t.filetype == "image" and os.path.isfile(t.filepath):
                    self.bg_image.set(t.filepath)
                    for vg in self.app.video_groups:
                        if not vg.get('bg_image'):
                            vg['bg_image'] = t.filepath
                    break

    def _sync_group_bg(self, save=True):
        """그룹 전환 시 bg_image를 UI ↔ video_group dict 사이로 동기화."""
        if self.selected_group < 0 or self.selected_group >= len(self.app.video_groups):
            return
        g = self.app.video_groups[self.selected_group]
        if save:
            g['bg_image'] = self.bg_image.get()
        else:
            self.bg_image.set(g.get('bg_image', ''))

    def _set_group(self, idx):
        if idx == self.selected_group:
            return
        self._sync_group_bg(save=True)
        self.selected_group = idx
        populate_group_tabs(self.tabs_container, self.app.video_groups, idx, self._set_group)
        self._sync_group_bg(save=False)
        self._stop_scrub_play()
        self._live_renderer = None
        self._live_duration = 0.0
        self.scrub_var.set(0)
        self.scrub_scale.state(['disabled'])
        self.preview_canvas.delete("all")
        self._last_preview_pil_frame = None
        self._preview_status_label.configure(text=f"Mix {idx+1} 선택됨 — 새로고침을 눌러 미리보기")

    def _pick_bg(self):
        p = filedialog.askopenfilename(filetypes=[("이미지", " ".join(f"*{e}" for e in IMAGE_EXTS))])
        if p: self.bg_image.set(p)

    def _collect_config(self):
        return {
            "background": {"image": self.bg_image.get() or None, "opacity": 1.0, "blur": 0, "darken": 0.0},
            "visualizer": {"type": self.viz_type.get(), "position": self.viz_pos.get(), "color": self.viz_color.get(),
                           "opacity": 0.85, "bar_count": int(self.viz_bars.get()), "height": int(self.viz_height.get()),
                           "smoothing": self.viz_smooth.get(), "mirror": False, "gradient": True,
                           "x": int(self.viz_x_var.get()), "y": int(self.viz_y_var.get()),
                           "width": int(self.viz_w_var.get()), "height_override": 0},
            "text": {"show_title": self.show_title.get(), "show_bpm": self.show_bpm.get(), "show_key": self.show_key.get(),
                     "show_camelot": self.show_camelot.get(), "show_time": self.show_time.get(), "position": "center",
                     "font_size": 42, "sub_font_size": 28, "color": "#ffffff",
                     "shadow": True, "shadow_color": "#000000", "shadow_offset": 3,
                     "custom_text": self.custom_text_var.get(),
                     "custom_x": self.custom_x_var.get(), "custom_y": self.custom_y_var.get(),
                     "custom_font_size": int(self.custom_font_size_var.get()),
                     "custom_bold": self.custom_bold_var.get(),
                     "custom_italic": self.custom_italic_var.get(),
                     "custom_underline": self.custom_underline_var.get(),
                     "custom_color": self.custom_color_var.get(),
                     "custom_affects_by_effects": self.custom_affects_fx_var.get()},
            "progress_bar": {"show": self.show_progress.get(), "position": "bottom", "height": 4,
                              "color": "#ffffff", "background_color": "#333333", "margin": 30},
            "fade": {"fade_in_duration": self.fade_in.get(), "fade_out_duration": self.fade_out.get()},
            "effects": {"bounce": self.fx_bounce.get(), "bounce_intensity": self.fx_bounce_i.get(),
                        "shake": self.fx_shake.get(), "shake_intensity": self.fx_shake_i.get(),
                        "zoom": self.fx_zoom.get(), "zoom_intensity": self.fx_zoom_i.get(),
                        "flash": self.fx_flash.get(), "flash_intensity": self.fx_flash_i.get()},
        }

    def _preview_effects(self):
        self._refresh_canvas_preview()

    def _preview_done(self, path):
        pass

    def _hex_to_rgb(self, h):
        h = h.lstrip('#')
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    def _make_preview_bg(self, w, h, key='C', mode='major'):
        key_colors = {
            'C': (60, 60, 90), 'D': (50, 70, 80), 'E': (70, 50, 80),
            'F': (50, 80, 60), 'G': (80, 60, 50), 'A': (80, 50, 70),
            'B': (60, 70, 70),
        }
        base = key_colors.get(key, (50, 50, 70))
        if mode == 'minor':
            base = tuple(max(0, c - 15) for c in base)

        bg = _PIL_Image.new('RGB', (w, h), base)
        draw = _PIL_ImageDraw.Draw(bg)
        for y in range(h):
            alpha = int(60 * (y / h))
            draw.line([(0, y), (w, y)], fill=tuple(min(255, c + alpha) for c in base))
        return bg, draw

    def _refresh_canvas_preview(self):
        """설정을 다시 수집해서 실제 렌더링 코드(LiveFrameRenderer)로 미리보기를
        갱신한다. 예전엔 이 버튼이 random 값으로 그리는 가짜 미리보기를 그렸는데,
        그러면 실시간 재생 화면과 따로 놀아서 "설정을 바꿔도 반영이 안 된다"는
        문제가 있었음. 이제는 실시간 재생과 완전히 같은 렌더러를 공유한다."""
        config = self._collect_config()

        if not self.app.video_groups:
            cw = self.preview_canvas.winfo_width() or 640
            ch = self.preview_canvas.winfo_height() or 360
            bg, draw = self._make_preview_bg(max(cw, 320), max(ch, 180))
            draw.text((20, 20), "먼저 분배를 실행하세요", fill=(220, 220, 220))
            self._show_pil_frame_fit(bg)
            self._preview_status_label.configure(text="분배 결과 없음")
            return

        idx = self.selected_group if 0 <= self.selected_group < len(self.app.video_groups) else 0

        if self._live_renderer:
            # 오디오는 그대로 두고 시각 설정만 즉시 반영 (오디오 재믹싱 없어서 빠름)
            self._live_renderer.reconfigure(config)
            self._render_scrub_frame(self.scrub_var.get())
            self._preview_status_label.configure(text=f"설정 반영됨 (Mix {idx+1})")
        else:
            # 아직 준비된 렌더러가 없으면(최초 1회) 오디오 믹싱부터 진행
            self._preview_render_video()

    def _preview_render_video(self):
        if not self.app.video_groups:
            messagebox.showwarning("경고", "먼저 분배를 실행하세요.")
            return

        config = self._collect_config()
        pw, ph = 640, 360

        idx = self.selected_group if 0 <= self.selected_group < len(self.app.video_groups) else 0
        g = self.app.video_groups[idx]
        tracks = g.get('tracks', [])
        if not tracks:
            return

        analyses = []
        tracks_data = []
        for t in tracks:
            if not t.get('analysis'):
                continue
            fp = t.get('filepath', '') or (t.get('track', {}).get('filepath', '') if isinstance(t.get('track'), dict) else getattr(t.get('track'), 'filepath', ''))
            if not fp:
                continue
            samples, sr = _load_audio_pydub(fp)
            ts_val = t.get('trim_start', 0)
            te_val = t.get('trim_end', 0)
            dur_val = t.get('duration', len(samples) / sr)
            if te_val <= 0:
                te_val = dur_val
            if ts_val > 0 or te_val < dur_val:
                s_s = int(ts_val * sr)
                e_s = int(te_val * sr)
                samples = samples[s_s:e_s]
            tracks_data.append((samples, sr))
            analyses.append(t['analysis'])

        if not tracks_data:
            return

        self._stop_scrub_play()
        self.preview_play_btn.configure(state=tk.DISABLED, text="준비 중...")
        self._preview_status_label.configure(text="오디오 믹싱 중...")

        def run():
            try:
                import tempfile
                tmp_audio = os.path.join(tempfile.gettempdir(), "_livepreview_audio.wav")
                # 오디오 믹싱 자체는 그대로 필요하지만(길이·경계 계산용), 영상은
                # 더 이상 ffmpeg로 인코딩하지 않고 프레임을 직접 그려서 캔버스에
                # 표시하므로 이 뒤가 훨씬 빨라진다.
                _, dur, timestamps = _create_mixed_audio(analyses, tracks_data, tmp_audio, 4.0)

                renderer = video_gen.LiveFrameRenderer(
                    analyses, pw, ph, dur,
                    timestamps=timestamps, crossfade_duration=4.0,
                    config_dict=config,
                )

                self.after(0, lambda: self._on_live_renderer_ready(renderer, dur))
            except Exception as e:
                self.after(0, lambda: (
                    messagebox.showerror("오류", f"미리보기 준비 실패:\n{e}"),
                    self.preview_play_btn.configure(state=tk.NORMAL, text="▶ 실시간 재생"),
                    self._preview_status_label.configure(text="실패"),
                ))

        threading.Thread(target=run, daemon=True).start()

    def _on_live_renderer_ready(self, renderer, duration):
        self._live_renderer = renderer
        self._live_duration = duration
        self.scrub_scale.state(['!disabled'])
        self.scrub_scale.configure(to=max(duration, 0.1))
        self.scrub_var.set(0)
        self._render_scrub_frame(0.0)
        idx = self.selected_group if 0 <= self.selected_group < len(self.app.video_groups) else 0
        self._preview_status_label.configure(text=f"준비됨 (Mix {idx+1}, 총 {duration:.1f}초) — 슬라이더로 탐색 또는 재생")
        self.preview_play_btn.configure(state=tk.NORMAL, text="■ 정지", command=self._stop_scrub_play)
        self._start_scrub_play()

    def _show_pil_frame_fit(self, pil_img):
        """PIL 이미지를 캔버스 크기에 맞춰, 비율을 망가뜨리지 않고(가로가 남으면
        가로가, 세로가 남으면 세로가 비도록) 가운데 정렬해서 그린다."""
        self._last_preview_pil_frame = pil_img
        cw = self.preview_canvas.winfo_width()
        ch = self.preview_canvas.winfo_height()
        if cw < 10 or ch < 10:
            return
        img_w, img_h = pil_img.size
        scale = min(cw / img_w, ch / img_h)
        new_w = max(1, int(img_w * scale))
        new_h = max(1, int(img_h * scale))
        resized = pil_img.resize((new_w, new_h), _PIL_Image.LANCZOS)
        self._preview_photo = _PIL_ImageTk.PhotoImage(resized)
        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(cw // 2, ch // 2, image=self._preview_photo)

    def _on_preview_canvas_resize(self, event):
        # 창 크기가 바뀌면 마지막으로 그렸던 프레임을 새 캔버스 크기에 맞춰 다시 표시
        if self._last_preview_pil_frame is not None:
            self._show_pil_frame_fit(self._last_preview_pil_frame)

    def _render_scrub_frame(self, t):
        if not self._live_renderer:
            return
        try:
            arr = self._live_renderer.render_frame(float(t))
        except Exception:
            return
        self._show_pil_frame_fit(_PIL_Image.fromarray(arr))

    def _on_scrub_drag(self, value):
        if getattr(self, '_programmatic_scrub', False):
            return
        # 사용자가 슬라이더를 직접 드래그하는 경우 재생 중이었다면 멈추고 탐색만
        if self._scrub_playing:
            self._scrub_playing = False
            if self._scrub_after_id:
                self.after_cancel(self._scrub_after_id)
                self._scrub_after_id = None
            self.preview_play_btn.configure(text="▶ 실시간 재생", command=self._start_scrub_play)
        self._render_scrub_frame(float(value))

    def _start_scrub_play(self):
        if not self._live_renderer:
            self._preview_render_video()
            return
        self._scrub_playing = True
        self.preview_play_btn.configure(text="■ 정지", command=self._stop_scrub_play)
        self._scrub_tick()

    def _scrub_tick(self):
        if not self._scrub_playing:
            return
        t = self.scrub_var.get()
        if t >= self._live_duration:
            self._stop_scrub_play()
            return
        self._render_scrub_frame(t)
        self._programmatic_scrub = True
        try:
            self.scrub_var.set(t + 1.0 / 24.0)
        finally:
            self._programmatic_scrub = False
        self._scrub_after_id = self.after(42, self._scrub_tick)  # 대략 24fps

    def _stop_scrub_play(self):
        self._scrub_playing = False
        if self._scrub_after_id:
            self.after_cancel(self._scrub_after_id)
            self._scrub_after_id = None
        self.preview_play_btn.configure(state=tk.NORMAL, text="▶ 실시간 재생", command=self._start_scrub_play)

    def _start_render(self):
        if not self.app.video_groups:
            messagebox.showwarning("경고", "먼저 분배를 실행하세요.")
            return
        out_dir = filedialog.askdirectory(title="저장 폴더 선택")
        if not out_dir: return

        self.render_btn.configure(state=tk.DISABLED, text="렌더링 중...")
        self._sync_group_bg(save=True)
        res_map = {"720p": (1280, 720), "1080p": (1920, 1080), "4k": (3840, 2160)}
        w, h = res_map.get(self.resolution.get(), (1920, 1080))

        def run():
            try:
                total_groups = len(self.app.video_groups)
                self.after(0, lambda t=total_groups: self._render_set_progress(0, t, 0))
                for gi, g in enumerate(self.app.video_groups):
                    tracks = g.get('tracks', [])
                    if not tracks: continue
                    self.after(0, lambda ii=gi: self._update_queue(ii, "믹싱 중..."))

                    analyses = [t['analysis'] for t in tracks if t.get('analysis')]
                    if not analyses: continue

                    tracks_data = []
                    for t in tracks:
                        if not t.get('analysis'): continue
                        fp = t.get('filepath', '') or (t.get('track', {}).get('filepath', '') if isinstance(t.get('track'), dict) else getattr(t.get('track'), 'filepath', ''))
                        if not fp:
                            continue
                        samples, sr = _load_audio_pydub(fp)
                        ts = t.get('trim_start', 0)
                        te = t.get('trim_end', 0)
                        dur = t.get('duration', len(samples) / sr)
                        if te <= 0:
                            te = dur
                        if ts > 0 or te < dur:
                            s_s = int(ts * sr)
                            e_s = int(te * sr)
                            samples = samples[s_s:e_s]
                        tracks_data.append((samples, sr))

                    g_dir = os.path.join(out_dir, f"mix_{gi+1}")
                    os.makedirs(g_dir, exist_ok=True)

                    a_out = os.path.join(g_dir, "audio.wav")
                    _, dur, timestamps = _create_mixed_audio(analyses, tracks_data, a_out, 4.0)

                    self.after(0, lambda ii=gi: self._update_queue(ii, "영상 생성 중..."))

                    self.bg_image.set(g.get('bg_image', ''))
                    config = self._collect_config()
                    vc = os.path.join(g_dir, "_visual.json")
                    with open(vc, 'w', encoding='utf-8') as f:
                        json.dump(config, f, indent=2, ensure_ascii=False)

                    _last_progress_ts = [0.0]

                    def _on_frame_progress(value, total, ii=gi, tt=total_groups):
                        now = time.time()
                        if now - _last_progress_ts[0] < 0.2 and value < total:
                            return
                        _last_progress_ts[0] = now
                        frac = value / total if total else 0
                        overall = (ii + frac) / max(tt, 1)
                        self.after(0, lambda: (
                            self.render_status.configure(text=f"영상 인코딩 중... {int(frac*100)}% (Mix {ii+1}/{tt})"),
                            self._render_set_progress(ii, tt, overall),
                        ))

                    v_out = os.path.join(g_dir, f"mix_{gi+1}.mp4")
                    _generate_video(analyses, a_out, v_out, width=w, height=h,
                                   visual_config_path=vc, timestamps=timestamps,
                                   crossfade_duration=4.0,
                                   frame_progress_callback=_on_frame_progress)

                    txt_path = os.path.join(g_dir, "timestamps.txt")
                    self._save_timestamps_txt(txt_path, timestamps, dur)

                    self.after(0, lambda ii=gi: self._update_queue(ii, "완료!"))
                    self.after(0, lambda ii=gi, tt=total_groups: self._render_set_progress(ii+1, tt, (ii+1)/max(tt,1)))

                if self.app.project and self.app.project.project_dir:
                    self.app.project.target_duration = self.app.stages[0].get_target_seconds()
                    self.app.project.tolerance = self.app.stages[0].get_tolerance()
                    analyses = {}
                    for t in self.app.tracks:
                        if t.analysis:
                            analyses[t.filepath] = t.analysis
                    self.app.project.save(analyses=analyses, video_groups=self.app.video_groups)

                self.after(0, lambda: (self.render_status.configure(text="전체 렌더링 완료!"),
                                       messagebox.showinfo("완료", f"{out_dir}에 저장되었습니다")))

            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                try:
                    log_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
                    with open(os.path.join(log_dir, "render_error.log"), "w", encoding="utf-8") as ef:
                        ef.write(f"{e}\n\n{tb}\n")
                except Exception:
                    pass
                self.after(0, lambda: self.render_status.configure(text=f"오류: {e}"))
                self.after(0, lambda: messagebox.showerror("오류", f"{e}\n\n자세한 내용은 render_error.log 확인"))
            finally:
                def _restore():
                    self.render_btn.configure(state=tk.NORMAL, text="전체 렌더링 시작")
                    self._sync_group_bg(save=False)
                self.after(0, _restore)

        threading.Thread(target=run, daemon=True).start()

    def _update_queue(self, idx, text):
        dur = self.app.video_groups[idx].get('total_duration', 0)
        n = len(self.app.video_groups[idx].get('tracks', []))
        self.queue_listbox.delete(idx)
        self.queue_listbox.insert(idx, f"Mix {idx+1}: {n}곡, {int(dur)}초 ({int(dur//60)}분 {int(dur%60):02d}초)  [{text}]")

    def _render_set_progress(self, done, total, pct):
        self.render_progress_canvas.delete("all")
        cw = self.render_progress_canvas.winfo_width()
        if cw < 10:
            cw = 200
        h = 12
        self.render_progress_canvas.create_rectangle(0, 0, cw, h, fill=THEME['bg_hover'], outline='')
        if pct > 0:
            self.render_progress_canvas.create_rectangle(0, 0, int(cw * pct), h,
                                                          fill=THEME['accent'], outline='')
        self.render_progress_label.configure(text=f"{done}/{total} 완료 ({int(pct*100)}%)")

    def _save_timestamps_txt(self, filepath, timestamps, total_duration):
        lines = []
        for i, ts in enumerate(timestamps):
            start = ts.get('start_time', 0)
            sm, ss = int(start // 60), int(start % 60)
            filename = ts.get('filename', 'Unknown')
            lines.append(f"[{sm:02d}:{ss:02d}] {filename}")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')


# ─── 메인 앱 ───

class AutoPlaylistMakerApp:
    def __init__(self):
        self.tracks = []
        self.video_groups = []
        self.project = _Project()
        self.current_stage = 0
        self.dark_mode = True

        root = None
        if '--safe' not in sys.argv:
            try:
                from tkinterdnd2 import TkinterDnD
                root = TkinterDnD.Tk()
            except Exception:
                pass
        if root is None:
            root = tk.Tk()

        self.root = root
        self.root.title("Auto Playlist Maker")
        self.root.geometry("1200x750")
        self.root.minsize(950, 620)
        self.root.configure(bg=THEME['bg_main'])
        self._set_icon()

        self._apply_theme()
        self.build_nav()
        self.build_stages()
        self.show_stage(0)

    def _set_icon(self):
        try:
            if sys.platform == 'win32':
                self.root.iconbitmap(default='')
        except:
            pass

    def _apply_theme(self):
        global THEME
        THEME = DARK if self.dark_mode else LIGHT
        self.root.configure(bg=THEME['bg_main'])

    def build_nav(self):
        self.nav = tk.Frame(self.root, bg=THEME['bg_mid'], height=48)
        self.nav.pack(fill=tk.X)
        self.nav.pack_propagate(False)

        self.prev_btn = styled_button(self.nav, "◀ 이전", self.go_prev, padx=12)
        self.prev_btn.pack(side=tk.LEFT, padx=(12, 0), pady=10)

        self.stage_label = styled_label(self.nav, "", size=11, bold=True, bg=THEME['bg_mid'])
        self.stage_label.pack(side=tk.LEFT, padx=16)

        dots = tk.Frame(self.nav, bg=THEME['bg_mid'])
        dots.pack(side=tk.LEFT, padx=8)
        self.dots = []
        for _ in range(4):
            l = tk.Label(dots, text="\u25cf", font=_font(13), bg=THEME['bg_mid'], fg=THEME['fg_dimmer'])
            l.pack(side=tk.LEFT, padx=3)
            self.dots.append(l)

        self.project_label = styled_label(self.nav, "", size=9, color=THEME['success'], bg=THEME['bg_mid'])
        self.project_label.pack(side=tk.LEFT, padx=12)

        self.theme_btn = styled_button(self.nav, "☀" if self.dark_mode else "☾",
                                        self._toggle_theme, padx=8, bg=THEME['bg_input'], fg=THEME['fg'])
        self.theme_btn.pack(side=tk.RIGHT, padx=(0, 6), pady=10)

        self.next_btn = styled_button(self.nav, "다음 ▶", self.go_next, "primary", padx=12)
        self.next_btn.pack(side=tk.RIGHT, padx=(0, 12), pady=10)
        self.next_btn.configure(state=tk.DISABLED)

    def _toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self._apply_theme()

        self.nav.configure(bg=THEME['bg_mid'])
        self.stage_label.configure(bg=THEME['bg_mid'], fg=THEME['fg'])
        self.project_label.configure(bg=THEME['bg_mid'], fg=THEME['success'])
        self.theme_btn.configure(text="☀" if self.dark_mode else "☾",
                                 bg=THEME['bg_input'], fg=THEME['fg'])
        for d in self.dots:
            d.configure(bg=THEME['bg_mid'])
        self.prev_btn.configure(bg=THEME['bg_input'], fg=THEME['fg'],
                                activebackground=THEME['bg_hover'])
        self.next_btn.configure(bg=THEME['accent'], fg="#ffffff",
                                activebackground=THEME['accent_h'])

        self._rebuild_stages()

    def _rebuild_stages(self):
        if hasattr(self, '_stage_container'):
            self._stage_container.destroy()

        self._stage_container = tk.Frame(self.root, bg=THEME['bg_main'])
        self._stage_container.pack(fill=tk.BOTH, expand=True)

        self.stages = [
            Stage0Project(self._stage_container, self),
            Stage1Distribute(self._stage_container, self),
            Stage2MusicEdit(self._stage_container, self),
            Stage3VideoEdit(self._stage_container, self),
        ]
        self.titles = ["1/4  프로젝트 + 가져오기", "2/4  자동 분배",
                       "3/4  음악 편집", "4/4  영상 편집 + 렌더링"]

        self.show_stage(self.current_stage)

    def build_stages(self):
        self._stage_container = tk.Frame(self.root, bg=THEME['bg_main'])
        self._stage_container.pack(fill=tk.BOTH, expand=True)

        self.stages = [
            Stage0Project(self._stage_container, self),
            Stage1Distribute(self._stage_container, self),
            Stage2MusicEdit(self._stage_container, self),
            Stage3VideoEdit(self._stage_container, self),
        ]
        self.titles = ["1/4  프로젝트 + 가져오기", "2/4  자동 분배",
                       "3/4  음악 편집", "4/4  영상 편집 + 렌더링"]

    def show_stage(self, idx):
        for s in self.stages:
            s.pack_forget()
        self.current_stage = idx
        self.stages[idx].pack(fill=tk.BOTH, expand=True)
        self.stage_label.configure(text=self.titles[idx])
        for i, d in enumerate(self.dots):
            d.configure(fg=THEME['accent'] if i == idx else (THEME['fg_dim'] if i < idx else THEME['fg_dimmer']))
        self.prev_btn.configure(state=tk.NORMAL if idx > 0 else tk.DISABLED)

        if idx == 0:
            has = any(t.analysis for t in self.tracks if t.filetype == "audio")
            self.next_btn.configure(state=tk.NORMAL if has else tk.DISABLED)
        elif idx == 1:
            self.next_btn.configure(state=tk.NORMAL if self.video_groups else tk.DISABLED)
        else:
            self.next_btn.configure(state=tk.NORMAL)

        if self.project and self.project.name:
            self.project_label.configure(text=f"프로젝트: {self.project.name}")
        else:
            self.project_label.configure(text="")

        try:
            self.stages[idx].refresh()
        except:
            pass

        for i, s in enumerate(self.stages):
            if i == idx:
                continue
            if hasattr(s, 'refresh'):
                def _defer_refresh(panel=s):
                    try:
                        panel.refresh()
                    except:
                        pass
                self.root.after(50, _defer_refresh)

    def enable_next(self, enabled=True):
        self.next_btn.configure(state=tk.NORMAL if enabled else tk.DISABLED)

    def go_next(self):
        if self.current_stage < 3:
            self.show_stage(self.current_stage + 1)

    def go_prev(self):
        if self.current_stage > 0:
            self.show_stage(self.current_stage - 1)

    def run(self):
        self.root.mainloop()


# ─── 스플래시 스크린 ───

class SplashScreen:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.configure(bg='#202225')
        self.root.attributes('-topmost', True)
        self.root.resizable(False, False)

        w, h = 400, 210
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        outer = tk.Frame(self.root, bg='#5865f2', padx=2, pady=2)
        outer.pack(fill=tk.BOTH, expand=True)
        inner = tk.Frame(outer, bg='#36393f')
        inner.pack(fill=tk.BOTH, expand=True)

        tk.Label(inner, text="Auto Playlist Maker", font=(FONT_FAMILY, 22, "bold"),
                 bg='#36393f', fg='#ffffff').pack(pady=(24, 2))
        tk.Label(inner, text="v3", font=(FONT_FAMILY, 11),
                 bg='#36393f', fg='#96989d').pack()

        self.status_var = tk.StringVar(value="시작 중...")
        self.status_label = tk.Label(inner, textvariable=self.status_var,
                                     font=(FONT_FAMILY, 10), bg='#36393f', fg='#b9bbbe')
        self.status_label.pack(pady=(16, 6))

        bar_frame = tk.Frame(inner, bg='#202225', height=8)
        bar_frame.pack(fill=tk.X, padx=40, pady=(0, 20))
        bar_frame.pack_propagate(False)
        self.bar_canvas = tk.Canvas(bar_frame, bg='#202225', highlightthickness=0, height=8)
        self.bar_canvas.pack(fill=tk.BOTH, expand=True)

        self.bar_width = 0
        self.bar_max = 1

        self.root.deiconify()
        self.root.update_idletasks()
        self.root.update()

    def update(self, text, progress):
        try:
            self.status_var.set(text)
            self.bar_max = max(1, self.bar_canvas.winfo_width())
            self.bar_width = int(progress * self.bar_max)
            self.bar_canvas.delete("all")
            if self.bar_width > 0:
                self.bar_canvas.create_rectangle(0, 0, self.bar_width, 8,
                                                  fill='#5865f2', outline='')
            self.root.update_idletasks()
            self.root.update()
        except:
            pass

    def close(self):
        try:
            self.root.destroy()
        except:
            pass


# ─── 진입점 ───

def _load_heavy_modules_step(splash, step, prog):
    splash.update(step, prog)
    time.sleep(0.01)
    splash.root.update_idletasks()
    splash.root.update()


def _preflight_ffmpeg():
    """moviepy import 전에 ffmpeg 경로를 찾아서 환경변수에 설정."""
    _log = []

    env_exe = os.environ.get("FFMPEG_BINARY", "")
    _log.append(f"env before: {env_exe!r}")

    if env_exe and env_exe not in ("ffmpeg-imageio", "auto-detect") and os.path.isfile(env_exe):
        _log.append(f"env already valid: {env_exe}")
        _write_ffmpeg_log(_log)
        return

    candidates = []

    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        _log.append(f"imageio_ffmpeg: {exe!r} exists={os.path.isfile(exe) if exe else False}")
        if exe and os.path.isfile(exe):
            candidates.append(exe)
    except Exception as e:
        _log.append(f"imageio_ffmpeg error: {e}")

    meipass = getattr(sys, '_MEIPASS', None)
    _log.append(f"MEIPASS: {meipass!r}")
    if meipass and os.path.isdir(meipass):
        for root, dirs, files in os.walk(meipass):
            for f in files:
                if f.lower().startswith('ffmpeg') and (f.lower().endswith('.exe') or f == 'ffmpeg' or f == 'ffmpeg.exe'):
                    candidates.append(os.path.join(root, f))
                    _log.append(f"MEIPASS found: {os.path.join(root, f)}")

    search_names = ('ffmpeg', 'ffmpeg.exe') if sys.platform == 'win32' else ('ffmpeg',)
    for name in search_names:
        p = shutil.which(name)
        if p:
            candidates.append(p)
            _log.append(f"which({name}): {p}")

    try:
        import importlib.resources as _res
        ref = _res.files("imageio_ffmpeg") / "binaries"
        with _res.as_file(ref) as bindir:
            if os.path.isdir(str(bindir)):
                for f in os.listdir(str(bindir)):
                    is_valid = False
                    if sys.platform == 'win32' and f.lower().endswith('.exe'):
                        is_valid = True
                    elif sys.platform != 'win32' and 'ffmpeg' in f.lower() and not '.' in f.split('ffmpeg')[-1]:
                        is_valid = True
                    if is_valid:
                        candidates.append(os.path.join(str(bindir), f))
                        _log.append(f"res found: {os.path.join(str(bindir), f)}")
    except Exception as e:
        _log.append(f"res error: {e}")

    _log.append(f"all candidates: {candidates}")

    for c in candidates:
        if os.path.isfile(c):
            os.environ["FFMPEG_BINARY"] = c
            _log.append(f"SET FFMPEG_BINARY = {c}")
            _write_ffmpeg_log(_log)
            return

    _log.append("WARNING: ffmpeg not found!")
    _write_ffmpeg_log(_log)


def _write_ffmpeg_log(lines):
    try:
        if getattr(sys, 'frozen', False):
            if sys.platform == 'darwin':
                log_dir = os.path.expanduser("~")
            else:
                log_dir = os.path.dirname(sys.executable)
        else:
            log_dir = os.path.dirname(os.path.abspath(__file__))
        log_path = os.path.join(log_dir, "ffmpeg_debug.log")
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
    except Exception:
        # 최후의 수단: 유저 홈
        try:
            log_path = os.path.join(os.path.expanduser("~"), "ffmpeg_debug.log")
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines) + '\n')
        except Exception:
            pass


def main():
    if getattr(sys, 'frozen', False) and getattr(sys, 'frozen', False):
        if sys.stdout is None:
            sys.stdout = open(os.devnull, 'w', encoding='utf-8')
        if sys.stderr is None:
            sys.stderr = open(os.devnull, 'w', encoding='utf-8')

    try:
        import pyi_splash
        pyi_splash.close()
    except ImportError:
        pass

    splash = SplashScreen()

    _load_heavy_modules_step(splash, "numpy 로딩 중...", 0.05)
    import numpy as _numpy
    global _np
    _np = _numpy

    _load_heavy_modules_step(splash, "ffmpeg 경로 탐색 중...", 0.10)
    _preflight_ffmpeg()
    ffmpeg_found = bool(os.environ.get("FFMPEG_BINARY", ""))

    _load_heavy_modules_step(splash, "PIL 로딩 중...", 0.15)
    from PIL import Image as PILImage, ImageTk as PILImageTk, ImageDraw as PILImageDraw, ImageFont as PILImageFont
    global _PIL_Image, _PIL_ImageTk, _PIL_ImageDraw, _PIL_ImageFont
    _PIL_Image = PILImage
    _PIL_ImageTk = PILImageTk
    _PIL_ImageDraw = PILImageDraw
    _PIL_ImageFont = PILImageFont

    _load_heavy_modules_step(splash, "분석 엔진 로딩 중...", 0.35)
    from analyzer import analyze_track as _at
    from transition import create_mixed_audio as _cma, load_audio_pydub as _lap
    global _analyze_track, _create_mixed_audio, _load_audio_pydub
    _analyze_track = _at
    _create_mixed_audio = _cma
    _load_audio_pydub = _lap

    _load_heavy_modules_step(splash, "영상 엔진 로딩 중...", 0.55)
    import video_gen as _video_gen_mod
    from video_gen import generate_video as _gv, load_visual_config as _lvc
    global _generate_video, _load_visual_config, video_gen
    _generate_video = _gv
    video_gen = _video_gen_mod
    _load_visual_config = _lvc

    _load_heavy_modules_step(splash, "프로젝트 관리 로딩 중...", 0.70)
    from project import Project as _Proj
    global _Project
    _Project = _Proj

    _load_heavy_modules_step(splash, "분배 엔진 로딩 중...", 0.85)
    from distributor import distribute_tracks as _dt, get_distribution_summary as _gs
    global _distribute_tracks, _get_distribution_summary
    _distribute_tracks = _dt
    _get_distribution_summary = _gs
    global _loaded
    _loaded = True

    _load_heavy_modules_step(splash, "GUI 구성 중...", 0.95)

    splash.update("완료!", 1.0)
    splash.root.update_idletasks()
    splash.root.update()
    time.sleep(0.15)
    splash.close()
    time.sleep(0.05)

    if not ffmpeg_found:
        try:
            import tkinter as _tk
            from tkinter import messagebox as _mb
            _tmp = _tk.Tk()
            _tmp.withdraw()
            if sys.platform == 'darwin':
                msg = (
                    "ffmpeg가 설치되어 있지 않습니다.\n\n"
                    "Auto Playlist Maker는 오디오/비디오 처리에 ffmpeg가 필요합니다.\n\n"
                    "터미널에서 다음 명령으로 설치할 수 있습니다:\n\n"
                    "  brew install ffmpeg\n\n"
                    "Homebrew가 없으면 https://brew.sh 에서 설치하세요.\n"
                    "설치 후 Auto Playlist Maker를 다시 실행해주세요."
                )
            else:
                exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
                setup_bat = os.path.join(exe_dir, "setup.bat")
                msg = (
                    "ffmpeg가 설치되어 있지 않습니다.\n\n"
                    "Auto Playlist Maker는 오디오/비디오 처리에 ffmpeg가 필요합니다.\n\n"
                    f"setup.bat을 더블클릭하여 자동 설치할 수 있습니다.\n"
                    f"경로: {setup_bat}\n\n"
                    "설치 후 PC를 재시작하고 Auto Playlist Maker를 다시 실행해주세요."
                )
            _mb.showwarning("ffmpeg 필요", msg)
            _tmp.destroy()
        except Exception:
            pass

    app = AutoPlaylistMakerApp()
    app.run()


if __name__ == "__main__":
    main()
