"""
app.py — X Traversal
Automated Asset Discovery & Collection
"""

import threading
import tkinter as tk
from tkinter import filedialog
from pathlib import Path
from datetime import datetime
import math
import time
import sys

import pipeline
from pipeline import LogEntry, LogType


def resource_path(relative: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return base / relative


# ═════════════════════════════════════════════════════════════
#  Theme
# ═════════════════════════════════════════════════════════════

BG         = "#0D1117"
SURFACE    = "#111827"
SURFACE2   = "#161F2E"
BORDER     = "#1F2937"
FG         = "#F9FAFB"
FG_DIM     = "#6B7280"
FG_MID     = "#9CA3AF"

GREEN      = "#10B981"
GREEN_DIM  = "#064E3B"
BLUE       = "#3B82F6"
BLUE_DIM   = "#1E3A5F"
AMBER      = "#F59E0B"
AMBER_DIM  = "#451A03"
RED        = "#EF4444"
RED_DIM    = "#450A0A"

# Tightened font sizes throughout
FONT_TITLE = ("SF Pro Display", 16, "bold")
FONT_SUB   = ("SF Pro Display", 10)
FONT_UI    = ("SF Pro Display", 11)
FONT_MONO  = ("Menlo", 10)
FONT_BADGE = ("SF Pro Display", 9, "bold")
FONT_SMALL = ("SF Pro Display", 10)

AVG_SECS_PER_TICKET = 71.67


# ═════════════════════════════════════════════════════════════
#  Main App
# ═════════════════════════════════════════════════════════════

class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("X Traversal")
        self.resizable(True, True)
        self.minsize(860, 680)
        self.configure(bg=BG)

        # State
        self.input_var         = tk.StringVar()
        self.output_var        = tk.StringVar()
        self.filter_var        = tk.StringVar()
        self._filter_match_var = tk.StringVar(value="")
        self._all_logs: list[LogEntry] = []
        self._error_count      = 0
        self._warn_count       = 0
        self._running          = False
        self._start_time: float | None = None
        self._total_tickets    = 0
        self._elapsed_var      = tk.StringVar(value="00:00:00")
        self._remain_var       = tk.StringVar(value="--:--:--")
        self._active_tab       = "activity"
        self._current_ticket: str | None = None
        self._last_error_ticket: str | None = None
        self._last_warn_ticket: str | None  = None
        self._logo_img: tk.PhotoImage | None = None

        self._build_ui()

    # ─────────────────────────────────────────────────────────
    #  UI Build
    # ─────────────────────────────────────────────────────────

    def _build_ui(self):
        outer = tk.Frame(self, bg=BG)
        outer.pack(fill="both", expand=True)

        self._main = tk.Frame(outer, bg=BG, padx=24, pady=16)
        self._main.pack(fill="both", expand=True)

        self._header_frame  = self._build_header()
        self._folders_frame = self._build_folder_section()
        self._run_frame     = self._build_run_button()
        self._activity_frame = self._build_activity_section()

    # ── Header ────────────────────────────────────────────────

    def _build_header(self) -> tk.Frame:
        frame = tk.Frame(self._main, bg=BG)
        frame.pack(fill="x", pady=(0, 10))

        logo_path = resource_path("logo.png")
        if logo_path.exists():
            try:
                raw = tk.PhotoImage(file=str(logo_path))
                w, h = raw.width(), raw.height()
                scale = max(1, h // 40)
                self._logo_img = raw.subsample(scale)
                tk.Label(frame, image=self._logo_img, bg=BG).pack(side="left", padx=(0, 10))
            except Exception:
                self._draw_fallback_logo(frame)
        else:
            self._draw_fallback_logo(frame)

        title_block = tk.Frame(frame, bg=BG)
        title_block.pack(side="left", anchor="w")

        tk.Label(title_block, text="X Traversal",
                 font=FONT_TITLE, fg=FG, bg=BG, anchor="w").pack(anchor="w")
        tk.Label(title_block, text="Automated Asset Discovery & Collection",
                 font=FONT_SUB, fg=FG_DIM, bg=BG, anchor="w").pack(anchor="w")

        return frame

    def _draw_fallback_logo(self, parent):
        c = tk.Canvas(parent, width=40, height=40, bg=BG, highlightthickness=0)
        c.pack(side="left", padx=(0, 10))
        c.create_line(6, 6, 34, 34, fill=GREEN, width=4, capstyle="round")
        c.create_line(34, 6, 6, 34, fill=GREEN, width=4, capstyle="round")

    # ── Card helper ───────────────────────────────────────────

    def _card(self, pady=(0, 10), expand=False):
        outer = tk.Frame(self._main, bg=BORDER, padx=1, pady=1)
        outer.pack(fill="both" if expand else "x", expand=expand, pady=pady)
        inner = tk.Frame(outer, bg=SURFACE, padx=16, pady=12)
        inner.pack(fill="both", expand=True)
        return outer, inner

    def _section_label(self, parent, number: str, title: str, subtitle: str = ""):
        row = tk.Frame(parent, bg=SURFACE)
        row.pack(fill="x", pady=(0, 8))

        badge_c = tk.Canvas(row, width=20, height=20, bg=SURFACE, highlightthickness=0)
        badge_c.pack(side="left", padx=(0, 8))
        badge_c.create_oval(1, 1, 19, 19, fill=GREEN_DIM, outline=GREEN, width=1)
        badge_c.create_text(10, 10, text=number, fill=GREEN, font=FONT_BADGE)

        tk.Label(row, text=title, font=("SF Pro Display", 12, "bold"),
                 fg=FG, bg=SURFACE).pack(side="left", padx=(0, 8))
        if subtitle:
            tk.Label(row, text=subtitle, font=FONT_SMALL,
                     fg=FG_DIM, bg=SURFACE).pack(side="left")

    # ── Folder section ────────────────────────────────────────

    def _build_folder_section(self) -> tk.Frame:
        outer, card = self._card()
        self._section_label(card, "1", "Select Folders",
                            "Choose input and output directories.")

        self._folder_row(card, "Input Folder",  self.input_var,  "📁")
        tk.Frame(card, bg=SURFACE, height=6).pack(fill="x")
        self._folder_row(card, "Output Folder", self.output_var, "📂")
        tk.Frame(card, bg=SURFACE, height=8).pack(fill="x")
        self._build_filter_row(card)
        return outer

    def _folder_row(self, parent, label: str, var: tk.StringVar, icon: str):
        row = tk.Frame(parent, bg=SURFACE)
        row.pack(fill="x", pady=2)
        row.columnconfigure(2, weight=1)

        icon_c = tk.Canvas(row, width=28, height=28, bg=SURFACE, highlightthickness=0)
        icon_c.grid(row=0, column=0, padx=(0, 8))
        icon_c.create_rectangle(0, 0, 28, 28, fill=SURFACE2, outline=BORDER, width=1)
        icon_c.create_text(14, 14, text=icon, font=("SF Pro Display", 12))

        tk.Label(row, text=label, font=FONT_UI, fg=FG_MID, bg=SURFACE,
                 width=12, anchor="w").grid(row=0, column=1, sticky="w", padx=(0, 8))

        ef = tk.Frame(row, bg=BORDER, padx=1, pady=1)
        ef.grid(row=0, column=2, sticky="ew", padx=(0, 8))

        tk.Entry(ef, textvariable=var, font=FONT_MONO, bg=SURFACE2, fg=FG,
                 insertbackground=FG, relief="flat",
                 state="readonly", readonlybackground=SURFACE2,
                 disabledforeground=FG).pack(fill="x", ipady=6, padx=6)

        tk.Button(row, text="🗂  Browse", font=FONT_UI,
                  fg=FG_MID, bg=SURFACE2,
                  activebackground=BORDER, activeforeground=FG,
                  relief="flat", cursor="hand2", padx=12, pady=4,
                  bd=1, highlightthickness=1,
                  highlightbackground=BORDER, highlightcolor=GREEN,
                  command=lambda v=var: self._browse(v)
                  ).grid(row=0, column=3, sticky="e")

    def _build_filter_row(self, parent):
        row = tk.Frame(parent, bg=SURFACE)
        row.pack(fill="x", pady=2)
        row.columnconfigure(2, weight=1)

        icon_c = tk.Canvas(row, width=28, height=28, bg=SURFACE, highlightthickness=0)
        icon_c.grid(row=0, column=0, padx=(0, 8))
        icon_c.create_rectangle(0, 0, 28, 28, fill=SURFACE2, outline=BORDER, width=1)
        icon_c.create_text(14, 14, text="🔍", font=("SF Pro Display", 12))

        tk.Label(row, text="Folder Filter", font=FONT_UI, fg=FG_MID, bg=SURFACE,
                 width=12, anchor="w").grid(row=0, column=1, sticky="w", padx=(0, 8))

        ef = tk.Frame(row, bg=BORDER, padx=1, pady=1)
        ef.grid(row=0, column=2, sticky="ew", padx=(0, 8))

        self._filter_entry = tk.Entry(
            ef, textvariable=self.filter_var,
            font=FONT_MONO, bg=SURFACE2, fg=FG,
            insertbackground=FG, relief="flat")
        self._filter_entry.pack(fill="x", ipady=6, padx=6)

        self._match_badge = tk.Label(
            row, textvariable=self._filter_match_var,
            font=FONT_SMALL, fg=FG_DIM, bg=SURFACE, padx=4)
        # hidden until input dir is set

        hint = tk.Label(
            parent,
            text='e.g. "P5"  ·  "P1, P3, P10"  ·  "P20-P40"  ·  "P1-P5, P10". '
                 'Blank = all folders.',
            font=("SF Pro Display", 9), fg=FG_DIM, bg=SURFACE,
            anchor="w", justify="left")
        hint.pack(fill="x", padx=(36, 0), pady=(3, 0))

        self.filter_var.trace_add("write", lambda *_: self._update_filter_match())
        self.input_var.trace_add("write",  lambda *_: self._update_filter_match())

    # ── Run button ────────────────────────────────────────────

    def _build_run_button(self):
        self._run_canvas = tk.Canvas(
            self._main, height=44, bg=BG,
            highlightthickness=0, cursor="hand2")
        self._run_canvas.pack(fill="x", pady=(0, 10))
        self._run_canvas.bind("<Configure>", self._draw_run_btn)
        self._run_canvas.bind("<Button-1>",  lambda e: self._on_run())
        self._run_canvas.bind("<Enter>",     lambda e: self._run_btn_hover(True))
        self._run_canvas.bind("<Leave>",     lambda e: self._run_btn_hover(False))
        self._run_btn_enabled = True
        self._run_btn_color   = GREEN
        return self._run_canvas

    def _draw_run_btn(self, event=None):
        c = self._run_canvas
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        if w < 2:
            return
        r, color = 6, self._run_btn_color
        pts = [r,0, w-r,0, w,0, w,r, w,h-r, w,h, w-r,h, r,h, 0,h, 0,h-r, 0,r, 0,0, r,0]
        c.create_polygon(pts, smooth=True, fill=color, outline="")
        label = "  ▶   Run Pipeline" if self._run_btn_enabled else "  ⏳   Running..."
        c.create_text(w // 2, h // 2, text=label, fill="white",
                      font=("SF Pro Display", 13, "bold"))

    def _run_btn_hover(self, hovering: bool):
        if not self._run_btn_enabled:
            return
        self._run_btn_color = "#0EA572" if hovering else GREEN
        self._draw_run_btn()

    def _set_run_btn_state(self, enabled: bool):
        self._run_btn_enabled = enabled
        self._run_btn_color   = GREEN if enabled else "#064E3B"
        self._draw_run_btn()
        self._run_canvas.config(cursor="hand2" if enabled else "watch")

    # ── Activity section ──────────────────────────────────────

    def _build_activity_section(self) -> tk.Frame:
        outer, card = self._card(pady=(0, 0), expand=True)

        # ── Row 1: title + ETA ───────────────────────────────
        row1 = tk.Frame(card, bg=SURFACE)
        row1.pack(fill="x", pady=(0, 16))

        badge_c = tk.Canvas(row1, width=20, height=20, bg=SURFACE, highlightthickness=0)
        badge_c.pack(side="left", padx=(0, 8))
        badge_c.create_oval(1, 1, 19, 19, fill=GREEN_DIM, outline=GREEN, width=1)
        badge_c.create_text(10, 10, text="2", fill=GREEN, font=FONT_BADGE)

        tk.Label(row1, text="Activity", font=("SF Pro Display", 12, "bold"),
                 fg=FG, bg=SURFACE).pack(side="left", padx=(0, 8))
        tk.Label(row1, text="Real-time logs from the pipeline run.",
                 font=FONT_SMALL, fg=FG_DIM, bg=SURFACE).pack(side="left")

        # ETA far right of row 1
        timing = tk.Frame(row1, bg=SURFACE)
        timing.pack(side="right")

        tk.Label(timing, text="Elapsed:", font=FONT_SMALL,
                 fg=FG_DIM, bg=SURFACE).pack(side="left", padx=(0, 4))
        tk.Label(timing, textvariable=self._elapsed_var,
                 font=("Menlo", 10), fg=GREEN, bg=SURFACE).pack(side="left", padx=(0, 12))
        tk.Label(timing, text="ETA:", font=FONT_SMALL,
                 fg=FG_DIM, bg=SURFACE).pack(side="left", padx=(0, 4))
        tk.Label(timing, textvariable=self._remain_var,
                 font=("Menlo", 10), fg=FG_MID, bg=SURFACE).pack(side="left")

        # ── Row 2: tabs + expand ──────────────────────────────
        row2 = tk.Frame(card, bg=SURFACE)
        row2.pack(fill="x", pady=(0, 6))

        tabs = tk.Frame(row2, bg=SURFACE)
        tabs.pack(side="left")

        self._tab_activity_canvas = tk.Canvas(tabs, height=26, width=90,
                                              bg=SURFACE, highlightthickness=0, cursor="hand2")
        self._tab_activity_canvas.pack(side="left", padx=(0, 2))
        self._tab_activity_canvas.bind("<Button-1>",  lambda e: self._switch_tab("activity"))
        self._tab_activity_canvas.bind("<Configure>", lambda e: self._update_tab_styles())

        self._tab_warnings_canvas = tk.Canvas(tabs, height=26, width=110,
                                              bg=SURFACE, highlightthickness=0, cursor="hand2")
        self._tab_warnings_canvas.pack(side="left", padx=(0, 2))
        self._tab_warnings_canvas.bind("<Button-1>",  lambda e: self._switch_tab("warnings"))
        self._tab_warnings_canvas.bind("<Configure>", lambda e: self._update_tab_styles())

        self._tab_errors_canvas = tk.Canvas(tabs, height=26, width=110,
                                            bg=SURFACE, highlightthickness=0, cursor="hand2")
        self._tab_errors_canvas.pack(side="left")
        self._tab_errors_canvas.bind("<Button-1>",  lambda e: self._switch_tab("errors"))
        self._tab_errors_canvas.bind("<Configure>", lambda e: self._update_tab_styles())

        self._log_expanded  = False
        self._expand_canvas = tk.Canvas(row2, width=24, height=24,
                                        bg=SURFACE, highlightthickness=0, cursor="hand2")
        self._expand_canvas.pack(side="right")
        self._expand_canvas.bind("<Button-1>",  lambda e: self._toggle_log_expand())
        self._expand_canvas.bind("<Configure>", lambda e: self._draw_expand_btn())

        # ── Log area ─────────────────────────────────────────
        log_outer = tk.Frame(card, bg=BORDER, padx=1, pady=1)
        log_outer.pack(fill="both", expand=True)

        self._log_frame = tk.Frame(log_outer, bg=SURFACE2)
        self._log_frame.pack(fill="both", expand=True)

        self._log_text = tk.Text(
            self._log_frame,
            font=FONT_MONO, bg=SURFACE2, fg=FG,
            relief="flat", wrap="none",
            state="disabled", padx=10, pady=8,
            height=16,
        )
        scrollbar = tk.Scrollbar(self._log_frame, command=self._log_text.yview,
                                 bg=SURFACE2, troughcolor=SURFACE2)
        self._log_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self._log_text.pack(side="left", fill="both", expand=True)

        # Text tags
        self._log_text.tag_config("ts",        foreground=FG_DIM,  font=FONT_MONO)
        self._log_text.tag_config("INFO",       foreground=BLUE)
        self._log_text.tag_config("SUCCESS",    foreground=GREEN)
        self._log_text.tag_config("WARNING",    foreground=AMBER)
        self._log_text.tag_config("ERROR",      foreground=RED)
        self._log_text.tag_config("msg",        foreground=FG,      font=FONT_MONO)
        self._log_text.tag_config("divider",    foreground="#374151",
                                  font=("SF Pro Display", 9))
        self._log_text.tag_config("ticket_hdr", foreground=FG_MID,
                                  font=("SF Pro Display", 10, "bold"))
        self._update_tab_styles()

        return outer

    # ── Expand/collapse ───────────────────────────────────────

    def _draw_expand_btn(self):
        c = self._expand_canvas
        c.delete("all")
        w = c.winfo_width() or 24
        h = c.winfo_height() or 24
        c.create_rectangle(0, 0, w, h, fill=SURFACE2, outline=BORDER, width=1)
        mid = w // 2
        if not self._log_expanded:
            c.create_line(mid, 4,  mid, 10, fill=FG_DIM, width=1)
            c.create_line(mid-3, 7,  mid, 4,  fill=FG_DIM, width=1)
            c.create_line(mid,   4,  mid+3, 7, fill=FG_DIM, width=1)
            c.create_line(mid, 20, mid, 14, fill=FG_DIM, width=1)
            c.create_line(mid-3, 17, mid, 20, fill=FG_DIM, width=1)
            c.create_line(mid,   20, mid+3, 17, fill=FG_DIM, width=1)
        else:
            c.create_line(mid, 10, mid, 4,  fill=FG_DIM, width=1)
            c.create_line(mid-3, 7,  mid, 10, fill=FG_DIM, width=1)
            c.create_line(mid,   10, mid+3, 7, fill=FG_DIM, width=1)
            c.create_line(mid, 14, mid, 20, fill=FG_DIM, width=1)
            c.create_line(mid-3, 17, mid, 14, fill=FG_DIM, width=1)
            c.create_line(mid,   14, mid+3, 17, fill=FG_DIM, width=1)

    def _toggle_log_expand(self):
        self._log_expanded = not self._log_expanded
        if self._log_expanded:
            self._header_frame.pack_forget()
            self._folders_frame.pack_forget()
            self._run_frame.pack_forget()
            self._activity_frame.pack(fill="both", expand=True, pady=(0, 0))
        else:
            self._activity_frame.pack_forget()
            self._header_frame.pack(fill="x",      pady=(0, 10))
            self._folders_frame.pack(fill="x",      pady=(0, 10))
            self._run_frame.pack(fill="x",          pady=(0, 10))
            self._activity_frame.pack(fill="both", expand=True, pady=(0, 0))
        self._draw_expand_btn()

    # ── Tabs ──────────────────────────────────────────────────

    def _draw_tab(self, canvas: tk.Canvas, label: str, active: bool, color: str):
        canvas.delete("all")
        w = int(canvas.cget("width"))
        h = int(canvas.cget("height"))
        fg   = color if active else FG_DIM
        font = ("SF Pro Display", 10, "bold") if active else ("SF Pro Display", 10)
        canvas.create_text(w // 2, h // 2 - 2, text=label, fill=fg, font=font)
        if active:
            canvas.create_line(4, h - 2, w - 4, h - 2, fill=color, width=2)

    def _switch_tab(self, tab_id: str):
        self._active_tab = tab_id
        self._update_tab_styles()
        self._redraw_log()

    def _update_tab_styles(self):
        warn_label = f"Warnings ({self._warn_count})" if self._warn_count > 0 else "Warnings"
        err_label  = f"Errors ({self._error_count})"  if self._error_count > 0 else "Errors"
        self._draw_tab(self._tab_activity_canvas, "Activity",
                       self._active_tab == "activity", GREEN)
        self._draw_tab(self._tab_warnings_canvas, warn_label,
                       self._active_tab == "warnings", AMBER)
        self._draw_tab(self._tab_errors_canvas,   err_label,
                       self._active_tab == "errors",   RED)

    def _draw_error_badge(self, count: int):
        self._update_tab_styles()

    # ─────────────────────────────────────────────────────────
    #  Folder filter
    # ─────────────────────────────────────────────────────────

    @staticmethod
    def _parse_filter(text: str) -> list[tuple]:
        import re
        text = text.strip()
        if not text:
            return []
        rules = []
        for token in re.split(r"[,;]\s*", text):
            token = token.strip()
            if not token:
                continue
            m = re.fullmatch(r"([A-Za-z]*)(\d+)\s*-\s*[A-Za-z]*(\d+)", token)
            if m:
                prefix, lo, hi = m.group(1), int(m.group(2)), int(m.group(3))
                if lo > hi:
                    lo, hi = hi, lo
                rules.append((prefix.upper(), lo, hi))
                continue
            m = re.fullmatch(r"([A-Za-z]*)(\d+)", token)
            if m:
                prefix, n = m.group(1), int(m.group(2))
                rules.append((prefix.upper(), n, n))
                continue
            raise ValueError(f"Unrecognised token: '{token}'")
        return rules

    def _folder_matches(self, name: str, rules: list[tuple]) -> bool:
        import re
        if not rules:
            return True
        m = re.fullmatch(r"([A-Za-z]*)(\d+)(.*)", name)
        if not m:
            return False
        prefix, num = m.group(1).upper(), int(m.group(2))
        for rule_prefix, lo, hi in rules:
            if rule_prefix and rule_prefix != prefix:
                continue
            if lo <= num <= hi:
                return True
        return False

    def _resolve_folders(self, input_dir: str) -> list[Path]:
        all_dirs = sorted(
            [p for p in Path(input_dir).iterdir() if p.is_dir()],
            key=lambda p: p.name)
        raw = self.filter_var.get().strip()
        try:
            rules = self._parse_filter(raw)
        except ValueError:
            rules = []
        return [d for d in all_dirs if self._folder_matches(d.name, rules)]

    def _update_filter_match(self):
        input_dir = self.input_var.get().strip()
        raw       = self.filter_var.get().strip()

        if not input_dir or not Path(input_dir).is_dir():
            self._match_badge.grid_remove()
            return

        if not raw:
            total = len([p for p in Path(input_dir).iterdir() if p.is_dir()])
            self._filter_match_var.set(f"all {total}")
            self._match_badge.config(fg=FG_DIM)
            self._match_badge.grid(row=0, column=3, sticky="e")
            return

        try:
            self._parse_filter(raw)
            matched = self._resolve_folders(input_dir)
            self._filter_match_var.set(f"{len(matched)} matched")
            self._match_badge.config(fg=GREEN if matched else AMBER)
            self._match_badge.grid(row=0, column=3, sticky="e")
        except ValueError:
            self._filter_match_var.set("invalid syntax")
            self._match_badge.config(fg=RED)
            self._match_badge.grid(row=0, column=3, sticky="e")

    # ─────────────────────────────────────────────────────────
    #  Browse
    # ─────────────────────────────────────────────────────────

    def _browse(self, var: tk.StringVar):
        folder = filedialog.askdirectory(title="Select folder")
        if folder:
            var.set(folder)

    # ─────────────────────────────────────────────────────────
    #  Run pipeline
    # ─────────────────────────────────────────────────────────

    def _on_run(self):
        input_dir  = self.input_var.get().strip()
        output_dir = self.output_var.get().strip()

        if not input_dir or not Path(input_dir).is_dir():
            return
        if not output_dir:
            return

        folders = self._resolve_folders(input_dir)
        if not folders:
            return

        self._total_tickets = len(folders)

        self._all_logs.clear()
        self._error_count = 0
        self._warn_count  = 0
        self._running     = True
        self._start_time  = time.time()
        self._last_error_ticket = None
        self._last_warn_ticket  = None
        self._clear_log()
        self._draw_error_badge(0)
        self._update_tab_styles()
        self._elapsed_var.set("00:00:00")
        self._remain_var.set("--:--:--")

        self._set_run_btn_state(False)
        pipeline.set_log_sink(self._on_log_entry)

        threading.Thread(
            target=self._run_pipeline,
            args=(input_dir, output_dir, [str(f) for f in folders]),
            daemon=True,
        ).start()

        self._tick_timer()

    def _run_pipeline(self, input_dir: str, output_dir: str, folders: list[str]):
        try:
            pipeline.process_all(root=input_dir, output_dir=output_dir, folders=folders)
            self.after(0, self._on_done, None)
        except Exception as exc:
            self.after(0, self._on_done, str(exc))

    def _on_done(self, error: str | None):
        self._running = False
        pipeline.set_log_sink(None)

        elapsed = time.time() - (self._start_time or time.time())
        self._elapsed_var.set(self._fmt_time(elapsed))
        self._remain_var.set("00:00:00")
        self._set_run_btn_state(True)

    # ─────────────────────────────────────────────────────────
    #  Timer
    # ─────────────────────────────────────────────────────────

    def _tick_timer(self):
        if not self._running:
            return
        elapsed = time.time() - (self._start_time or time.time())
        self._elapsed_var.set(self._fmt_time(elapsed))

        estimated_total = self._total_tickets * AVG_SECS_PER_TICKET
        if estimated_total > 0:
            pct    = min(99.0, (elapsed / estimated_total) * 100)
            remain = max(0.0, estimated_total - elapsed)
        else:
            pct, remain = 0.0, 0.0

        self._remain_var.set(self._fmt_time(remain))
        self.after(1000, self._tick_timer)

    @staticmethod
    def _fmt_time(seconds: float) -> str:
        s = int(seconds)
        h, rem = divmod(s, 3600)
        m, sec = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{sec:02d}"

    # ─────────────────────────────────────────────────────────
    #  Log handling
    # ─────────────────────────────────────────────────────────

    def _on_log_entry(self, entry: LogEntry):
        if "── TICKET:" in entry.message:
            try:
                self._current_ticket = entry.message.split("TICKET:")[1].split("──")[0].strip()
            except Exception:
                pass
        self._all_logs.append(entry)
        if entry.level == LogType.ERROR:
            self._error_count += 1
            self.after(0, self._update_tab_styles)
        elif entry.level == LogType.WARNING:
            self._warn_count += 1
            self.after(0, self._update_tab_styles)
        self.after(0, self._append_entry_to_log, entry)

    def _append_entry_to_log(self, entry: LogEntry):
        if self._active_tab == "errors":
            if entry.level == LogType.ERROR:
                if self._current_ticket and self._last_error_ticket != self._current_ticket:
                    for e in reversed(self._all_logs):
                        if "── TICKET:" in e.message:
                            self._write_entry(e)
                            break
                    self._last_error_ticket = self._current_ticket
                self._write_entry(entry)
        elif self._active_tab == "warnings":
            if entry.level == LogType.WARNING:
                if self._current_ticket and self._last_warn_ticket != self._current_ticket:
                    for e in reversed(self._all_logs):
                        if "── TICKET:" in e.message:
                            self._write_entry(e)
                            break
                    self._last_warn_ticket = self._current_ticket
                self._write_entry(entry)
        else:
            self._write_entry(entry)

    def _write_entry(self, entry: LogEntry):
        self._log_text.config(state="normal")
        ts  = entry.timestamp.strftime("%H:%M:%S")
        lvl = entry.level.value
        msg = entry.message

        if "── TICKET:" in msg:
            try:
                ticket_name = msg.split("TICKET:")[1].split("──")[0].strip()
            except Exception:
                ticket_name = msg
            self._log_text.insert("end", "\n", "divider")
            self._log_text.insert("end",
                f"  ── {ticket_name} {'─' * max(0, 48 - len(ticket_name))}\n",
                "ticket_hdr")
            self._log_text.insert("end", "\n", "divider")
            self._log_text.config(state="disabled")
            self._log_text.see("end")
            return

        self._log_text.insert("end", f"  {ts}  ", "ts")
        self._log_text.insert("end", f" {lvl:<8} ", lvl)
        self._log_text.insert("end", f"  {msg}\n", "msg")
        self._log_text.config(state="disabled")
        self._log_text.see("end")

    def _redraw_log(self):
        self._log_text.config(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.config(state="disabled")

        if self._active_tab in ("errors", "warnings"):
            target_level = LogType.ERROR if self._active_tab == "errors" else LogType.WARNING
            sections: list[tuple] = []
            current_ticket_entry = None
            current_entries: list[LogEntry] = []

            for entry in self._all_logs:
                if "── TICKET:" in entry.message:
                    if current_ticket_entry and current_entries:
                        sections.append((current_ticket_entry, current_entries))
                    current_ticket_entry = entry
                    current_entries = []
                elif entry.level == target_level:
                    current_entries.append(entry)

            if current_ticket_entry and current_entries:
                sections.append((current_ticket_entry, current_entries))

            for ticket_entry, entries in sections:
                self._write_entry(ticket_entry)
                for e in entries:
                    self._write_entry(e)
        else:
            for entry in self._all_logs:
                self._write_entry(entry)

    def _clear_log(self):
        self._log_text.config(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.config(state="disabled")


# ═════════════════════════════════════════════════════════════
#  Entry point
# ═════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = App()
    app.mainloop()