"""
app.py — X Traversal
Automated Asset Discovery & Collection
"""

import threading
import tkinter as tk
from tkinter import filedialog, ttk
from pathlib import Path
from datetime import datetime
import math
import time

import sys

import pipeline
from pipeline import LogEntry, LogType


def resource_path(relative: str) -> Path:
   """Return the correct path to a bundled resource.

   When frozen by PyInstaller the unpacked files live under sys._MEIPASS;
   when running from source they live next to this script.
   """
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

FONT_UI    = ("SF Pro Display", 12) if True else ("Helvetica", 12)
FONT_TITLE = ("SF Pro Display", 22, "bold")
FONT_SUB   = ("SF Pro Display", 11)
FONT_MONO  = ("Menlo", 11)
FONT_BADGE = ("SF Pro Display", 10, "bold")

# Average seconds per ticket (used for progress estimation)
AVG_SECS_PER_TICKET = 71.67


# ═════════════════════════════════════════════════════════════
#  Rounded rectangle helper
# ═════════════════════════════════════════════════════════════

def round_rect(canvas, x1, y1, x2, y2, r=12, **kwargs):
    """Draw a rounded rectangle on a Canvas."""
    pts = [
        x1+r, y1,   x2-r, y1,
        x2,   y1,   x2,   y1+r,
        x2,   y2-r, x2,   y2,
        x2-r, y2,   x1+r, y2,
        x1,   y2,   x1,   y2-r,
        x1,   y1+r, x1,   y1,
        x1+r, y1,
    ]
    return canvas.create_polygon(pts, smooth=True, **kwargs)


# ═════════════════════════════════════════════════════════════
#  Main App
# ═════════════════════════════════════════════════════════════

class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("X Traversal")
        self.resizable(True, True)
        self.minsize(860, 780)
        self.configure(bg=BG)

        # State
        self.input_var      = tk.StringVar()
        self.output_var     = tk.StringVar()
        self._all_logs: list[LogEntry] = []
        self._error_count   = 0
        self._warn_count    = 0
        self._running       = False
        self._start_time: float | None = None
        self._total_tickets = 0
        self._elapsed_var   = tk.StringVar(value="00:00:00")
        self._remain_var    = tk.StringVar(value="--:--:--")
        self._pct_var       = tk.StringVar(value="0%")
        self._active_tab    = "activity"   # "activity" | "errors" | "warnings"
        self._current_ticket: str | None = None
        self._last_error_ticket: str | None = None
        self._last_warn_ticket: str | None = None

        # Logo image reference (kept alive to avoid GC)
        self._logo_img: tk.PhotoImage | None = None

        self._build_ui()

    # ─────────────────────────────────────────────────────────
    #  UI Build
    # ─────────────────────────────────────────────────────────

    def _build_ui(self):
        outer = tk.Frame(self, bg=BG)
        outer.pack(fill="both", expand=True)

        self._main = tk.Frame(outer, bg=BG, padx=28, pady=24)
        self._main.pack(fill="both", expand=True)

        self._header_frame   = self._build_header()
        self._folders_frame  = self._build_folder_section()
        self._run_frame      = self._build_run_button()
        self._progress_frame = self._build_progress_section()
        self._activity_frame = self._build_activity_section()

    # ── Header ────────────────────────────────────────────────

    def _build_header(self) -> tk.Frame:
        frame = tk.Frame(self._main, bg=BG)
        frame.pack(fill="x", pady=(0, 20))

        # ── Logo ──────────────────────────────────────────────
        logo_path = resource_path("logo.png")

        if logo_path.exists():
            try:
                raw = tk.PhotoImage(file=str(logo_path))
                # Scale down to fit a ~52px tall header
                w, h = raw.width(), raw.height()
                scale = max(1, h // 52)
                self._logo_img = raw.subsample(scale)
                logo_lbl = tk.Label(frame, image=self._logo_img, bg=BG)
                logo_lbl.pack(side="left", padx=(0, 14))
            except Exception:
                self._draw_fallback_logo(frame)
        else:
            self._draw_fallback_logo(frame)

        # ── Title block ───────────────────────────────────────
        title_block = tk.Frame(frame, bg=BG)
        title_block.pack(side="left", anchor="w")

        tk.Label(
            title_block, text="X Traversal",
            font=FONT_TITLE, fg=FG, bg=BG, anchor="w"
        ).pack(anchor="w")

        tk.Label(
            title_block, text="Automated Asset Discovery & Collection",
            font=FONT_SUB, fg=FG_DIM, bg=BG, anchor="w"
        ).pack(anchor="w")

        return frame

    def _draw_fallback_logo(self, parent):
        """Draw a simple green X on canvas as fallback if logo.png not found."""
        c = tk.Canvas(parent, width=52, height=52, bg=BG, highlightthickness=0)
        c.pack(side="left", padx=(0, 14))
        c.create_line(8, 8, 44, 44, fill=GREEN, width=5, capstyle="round")
        c.create_line(44, 8, 8, 44, fill=GREEN, width=5, capstyle="round")

    # ── Section card helper ───────────────────────────────────

    def _card(self, pady=(0, 16)):
        """A dark rounded surface card. Returns (outer_frame, inner_frame)."""
        outer = tk.Frame(self._main, bg=BORDER, padx=1, pady=1)
        outer.pack(fill="x", pady=pady)
        inner = tk.Frame(outer, bg=SURFACE, padx=20, pady=18)
        inner.pack(fill="both", expand=True)
        return outer, inner

    def _section_header(self, parent, number: str, title: str, subtitle: str):
        row = tk.Frame(parent, bg=SURFACE)
        row.pack(fill="x", pady=(0, 14))

        # Numbered badge
        badge_c = tk.Canvas(row, width=26, height=26, bg=SURFACE, highlightthickness=0)
        badge_c.pack(side="left", padx=(0, 10))
        badge_c.create_oval(1, 1, 25, 25, fill=GREEN_DIM, outline=GREEN, width=1)
        badge_c.create_text(13, 13, text=number, fill=GREEN, font=FONT_BADGE)

        tk.Label(row, text=title, font=("SF Pro Display", 14, "bold"),
                 fg=FG, bg=SURFACE).pack(side="left", padx=(0, 12))
        tk.Label(row, text=subtitle, font=FONT_SUB,
                 fg=FG_DIM, bg=SURFACE).pack(side="left")

    # ── Folder section ────────────────────────────────────────

    def _build_folder_section(self) -> tk.Frame:
        outer, card = self._card()
        self._section_header(card, "1", "Select Folders",
                              "Choose input and output directories for the pipeline.")

        self._folder_row(card, "Input Folder",  self.input_var,  "📁")
        self._spacer(card, 8)
        self._folder_row(card, "Output Folder", self.output_var, "📂")
        return outer

    def _folder_row(self, parent, label: str, var: tk.StringVar, icon: str):
        row = tk.Frame(parent, bg=SURFACE)
        row.pack(fill="x", pady=4)
        row.columnconfigure(2, weight=1)  # entry column expands

        # Icon box (coloured square like reference)
        icon_canvas = tk.Canvas(row, width=34, height=34,
                                bg=SURFACE, highlightthickness=0)
        icon_canvas.grid(row=0, column=0, padx=(0, 10))
        icon_canvas.create_rectangle(0, 0, 34, 34, fill=SURFACE2,
                                     outline=BORDER, width=1)
        icon_canvas.create_text(17, 17, text=icon, font=("SF Pro Display", 14))

        # Label
        tk.Label(
            row, text=label, font=("SF Pro Display", 12),
            fg=FG_MID, bg=SURFACE, width=13, anchor="w"
        ).grid(row=0, column=1, sticky="w", padx=(0, 10))

        # Path entry with border frame
        entry_frame = tk.Frame(row, bg=BORDER, padx=1, pady=1)
        entry_frame.grid(row=0, column=2, sticky="ew", padx=(0, 10))

        entry = tk.Entry(
            entry_frame, textvariable=var,
            font=FONT_MONO, bg=SURFACE2, fg=FG,
            insertbackground=FG, relief="flat",
            state="readonly", readonlybackground=SURFACE2,
            disabledforeground=FG,
        )
        entry.pack(fill="x", ipady=8, padx=8)

        # Browse button — styled like reference (dark bg, border, text + icon)
        btn = tk.Button(
            row, text="🗂  Browse",
            font=("SF Pro Display", 12),
            fg=SURFACE, bg=SURFACE2,
            activebackground=BORDER, activeforeground=FG,
            relief="flat", cursor="hand2",
            padx=16, pady=7,
            bd=1, highlightthickness=1,
            highlightbackground=BORDER, highlightcolor=GREEN,
            command=lambda v=var: self._browse(v),
        )
        btn.grid(row=0, column=3, sticky="e")

    # ── Run button ────────────────────────────────────────────

    def _build_run_button(self):
        # tk.Button ignores bg on macOS due to native rendering.
        # Use a Canvas instead for full color + rounded corner control.
        self._run_canvas = tk.Canvas(
            self._main, height=58, bg=BG,
            highlightthickness=0, cursor="hand2"
        )
        self._run_canvas.pack(fill="x", pady=(0, 16))
        self._run_canvas.bind("<Configure>",  self._draw_run_btn)
        self._run_canvas.bind("<Button-1>",   lambda e: self._on_run())
        self._run_canvas.bind("<Enter>",      lambda e: self._run_btn_hover(True))
        self._run_canvas.bind("<Leave>",      lambda e: self._run_btn_hover(False))
        self._run_btn_enabled = True
        self._run_btn_color   = GREEN
        return self._run_canvas

    def _draw_run_btn(self, event=None):
        c = self._run_canvas
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 2:
            return
        # Rounded rectangle fill
        r = 8
        color = self._run_btn_color
        pts = [
            r, 0,   w-r, 0,
            w, 0,   w,   r,
            w, h-r, w,   h,
            w-r, h, r,   h,
            0, h,   0,   h-r,
            0, r,   0,   0,
            r, 0,
        ]
        c.create_polygon(pts, smooth=True, fill=color, outline="")
        # Label
        label = "  ▶   Run Pipeline" if self._run_btn_enabled else "  ⏳   Running..."
        c.create_text(w // 2, h // 2, text=label,
                      fill="white",
                      font=("SF Pro Display", 16, "bold"))

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

    # ── Progress section ──────────────────────────────────────

    def _build_progress_section(self) -> tk.Frame:
        outer, card = self._card()
        self._section_header(card, "2", "Progress",
                              "Track the status of the current pipeline run.")

        body = tk.Frame(card, bg=SURFACE)
        body.pack(fill="x")

        # ── Circular arc ──────────────────────────────────────
        self._arc_canvas = tk.Canvas(body, width=110, height=110,
                                     bg=SURFACE, highlightthickness=0)
        self._arc_canvas.pack(side="left", padx=(0, 24))
        self._draw_arc(0)

        # ── Right side ────────────────────────────────────────
        right = tk.Frame(body, bg=SURFACE)
        right.pack(side="left", fill="both", expand=True)

        # Timing row
        timing = tk.Frame(right, bg=SURFACE)
        timing.pack(anchor="w", pady=(0, 10))

        tk.Label(timing, text="Elapsed", font=FONT_SUB,
                 fg=FG_DIM, bg=SURFACE).grid(row=0, column=0, padx=(0, 24))
        tk.Label(timing, text="Estimated Remaining", font=FONT_SUB,
                 fg=FG_DIM, bg=SURFACE).grid(row=0, column=1)

        tk.Label(timing, textvariable=self._elapsed_var,
                 font=("SF Pro Display", 16, "bold"),
                 fg=GREEN, bg=SURFACE).grid(row=1, column=0, padx=(0, 24), sticky="w")
        tk.Label(timing, textvariable=self._remain_var,
                 font=("SF Pro Display", 16, "bold"),
                 fg=FG_MID, bg=SURFACE).grid(row=1, column=1, sticky="w")

        # Linear progress bar
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("X.Horizontal.TProgressbar",
                        troughcolor=SURFACE2, background=GREEN,
                        bordercolor=SURFACE2, lightcolor=GREEN,
                        darkcolor=GREEN, thickness=8)

        self._progress_bar = ttk.Progressbar(
            right, style="X.Horizontal.TProgressbar",
            mode="determinate", maximum=100, value=0
        )
        self._progress_bar.pack(fill="x", pady=(4, 0))

        return outer

    def _draw_arc(self, pct: float):
        """Redraw the circular progress arc for a given percentage (0–100)."""
        c = self._arc_canvas
        c.delete("all")
        cx, cy, r = 55, 55, 44
        # Background ring
        c.create_oval(cx-r, cy-r, cx+r, cy+r,
                      outline=SURFACE2, width=10)
        # Foreground arc
        if pct > 0:
            extent = min(359.9, 3.6 * pct)
            c.create_arc(cx-r, cy-r, cx+r, cy+r,
                         start=90, extent=-extent,
                         outline=GREEN, width=10,
                         style="arc")
        # Percentage text
        c.create_text(cx, cy,
                      text=f"{int(pct)}%",
                      font=("SF Pro Display", 16, "bold"),
                      fill=FG)

    # ── Activity section ──────────────────────────────────────

    def _build_activity_section(self) -> tk.Frame:
        outer, card = self._card(pady=(0, 0))

        # Header row with tabs
        hdr = tk.Frame(card, bg=SURFACE)
        hdr.pack(fill="x", pady=(0, 12))

        # Left: badge + title + subtitle
        left = tk.Frame(hdr, bg=SURFACE)
        left.pack(side="left", fill="x", expand=True)

        badge_c = tk.Canvas(left, width=26, height=26, bg=SURFACE, highlightthickness=0)
        badge_c.pack(side="left", padx=(0, 10))
        badge_c.create_oval(1, 1, 25, 25, fill=GREEN_DIM, outline=GREEN, width=1)
        badge_c.create_text(13, 13, text="3", fill=GREEN, font=FONT_BADGE)

        tk.Label(left, text="Activity", font=("SF Pro Display", 14, "bold"),
                 fg=FG, bg=SURFACE).pack(side="left", padx=(0, 12))
        tk.Label(left, text="Real-time logs from the pipeline run.",
                 font=FONT_SUB, fg=FG_DIM, bg=SURFACE).pack(side="left")

        # Right: canvas-drawn tabs + expand button (rightmost)
        right = tk.Frame(hdr, bg=SURFACE)
        right.pack(side="right")

        tabs = tk.Frame(right, bg=SURFACE)
        tabs.pack(side="left")

        self._tab_activity_canvas = tk.Canvas(tabs, height=32, width=110,
                                              bg=SURFACE, highlightthickness=0,
                                              cursor="hand2")
        self._tab_activity_canvas.pack(side="left", padx=(0, 2))
        self._tab_activity_canvas.bind("<Button-1>",  lambda e: self._switch_tab("activity"))
        self._tab_activity_canvas.bind("<Configure>", lambda e: self._update_tab_styles())

        self._tab_warnings_canvas = tk.Canvas(tabs, height=32, width=130,
                                              bg=SURFACE, highlightthickness=0,
                                              cursor="hand2")
        self._tab_warnings_canvas.pack(side="left", padx=(0, 2))
        self._tab_warnings_canvas.bind("<Button-1>",  lambda e: self._switch_tab("warnings"))
        self._tab_warnings_canvas.bind("<Configure>", lambda e: self._update_tab_styles())

        self._tab_errors_canvas = tk.Canvas(tabs, height=32, width=130,
                                            bg=SURFACE, highlightthickness=0,
                                            cursor="hand2")
        self._tab_errors_canvas.pack(side="left")
        self._tab_errors_canvas.bind("<Button-1>",  lambda e: self._switch_tab("errors"))
        self._tab_errors_canvas.bind("<Configure>", lambda e: self._update_tab_styles())

        # Expand/collapse toggle button — rightmost element
        self._log_expanded  = False
        self._expand_canvas = tk.Canvas(right, width=28, height=28,
                                        bg=SURFACE, highlightthickness=0,
                                        cursor="hand2")
        self._expand_canvas.pack(side="left", padx=(16, 0))
        self._expand_canvas.bind("<Button-1>",  lambda e: self._toggle_log_expand())
        self._expand_canvas.bind("<Configure>", lambda e: self._draw_expand_btn())

        # Log frame (holds the text widget)
        log_outer = tk.Frame(card, bg=BORDER, padx=1, pady=1)
        log_outer.pack(fill="both", expand=True)

        self._log_frame = tk.Frame(log_outer, bg=SURFACE2)
        self._log_frame.pack(fill="both", expand=True)

        self._log_text = tk.Text(
            self._log_frame,
            font=FONT_MONO, bg=SURFACE2, fg=FG,
            relief="flat", wrap="none",
            state="disabled", padx=12, pady=10,
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
                                  font=("SF Pro Display", 10))
        self._log_text.tag_config("ticket_hdr", foreground=FG_MID,
                                  font=("SF Pro Display", 11, "bold"))
        self._update_tab_styles()

        return outer

    def _draw_expand_btn(self):
        """Draw the expand/collapse icon — arrows pointing out or in."""
        c = self._expand_canvas
        c.delete("all")
        w = c.winfo_width() or 28
        h = c.winfo_height() or 28
        # Rounded background on hover feel
        c.create_rectangle(0, 0, w, h, fill=SURFACE2, outline=BORDER, width=1)
        mid = w // 2
        if not self._log_expanded:
            # Two outward arrows ↕
            c.create_line(mid, 5,  mid, 12, fill=FG_DIM, width=1)
            c.create_line(mid-3, 8,  mid, 5,  fill=FG_DIM, width=1)
            c.create_line(mid,   5,  mid+3, 8, fill=FG_DIM, width=1)
            c.create_line(mid, 23, mid, 16, fill=FG_DIM, width=1)
            c.create_line(mid-3, 20, mid, 23, fill=FG_DIM, width=1)
            c.create_line(mid,   23, mid+3, 20, fill=FG_DIM, width=1)
        else:
            # Two inward arrows ↕
            c.create_line(mid, 11, mid, 5,  fill=FG_DIM, width=1)
            c.create_line(mid-3, 8,  mid, 11, fill=FG_DIM, width=1)
            c.create_line(mid,   11, mid+3, 8, fill=FG_DIM, width=1)
            c.create_line(mid, 17, mid, 23, fill=FG_DIM, width=1)
            c.create_line(mid-3, 20, mid, 17, fill=FG_DIM, width=1)
            c.create_line(mid,   17, mid+3, 20, fill=FG_DIM, width=1)

    def _toggle_log_expand(self):
        self._log_expanded = not self._log_expanded

        if self._log_expanded:
            # Hide all sections except activity
            self._header_frame.pack_forget()
            self._folders_frame.pack_forget()
            self._run_frame.pack_forget()
            self._progress_frame.pack_forget()
            # Re-pack activity to fill all available space
            self._activity_frame.pack(fill="both", expand=True, pady=(0, 0))
        else:
            # Restore all sections in original order
            self._activity_frame.pack_forget()
            self._header_frame.pack(fill="x",      pady=(0, 20))
            self._folders_frame.pack(fill="x",     pady=(0, 16))
            self._run_frame.pack(fill="x",         pady=(0, 16))
            self._progress_frame.pack(fill="x",    pady=(0, 16))
            self._activity_frame.pack(fill="both", expand=True, pady=(0, 0))

        self._draw_expand_btn()

    def _draw_tab(self, canvas: tk.Canvas, label: str, active: bool, color: str):
        """Draw a single underline-style tab on a canvas."""
        canvas.delete("all")
        # Use constructor width — winfo_width() returns 0 before layout completes
        w = int(canvas.cget("width"))
        h = int(canvas.cget("height"))
        fg   = color if active else FG_DIM
        font = ("SF Pro Display", 11, "bold") if active else ("SF Pro Display", 11)
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
    #  Folder browse
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

        if not input_dir:
            return
        if not Path(input_dir).is_dir():
            return
        if not output_dir:
            return

        # Count ticket folders for progress estimation
        self._total_tickets = len([
            p for p in Path(input_dir).iterdir() if p.is_dir()
        ])

        # Reset state
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
        self._draw_arc(0)
        self._progress_bar["value"] = 0
        self._pct_var.set("0%")
        self._elapsed_var.set("00:00:00")
        self._remain_var.set("--:--:--")

        self._set_run_btn_state(False)

        pipeline.set_log_sink(self._on_log_entry)

        threading.Thread(
            target=self._run_pipeline,
            args=(input_dir, output_dir),
            daemon=True,
        ).start()

        self._tick_timer()

    def _run_pipeline(self, input_dir: str, output_dir: str):
        try:
            pipeline.process_all(root=input_dir, output_dir=output_dir)
            self.after(0, self._on_done, None)
        except Exception as exc:
            self.after(0, self._on_done, str(exc))

    def _on_done(self, error: str | None):
        self._running = False
        pipeline.set_log_sink(None)

        self._draw_arc(100)
        self._progress_bar["value"] = 100

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

        # Progress estimate
        estimated_total = self._total_tickets * AVG_SECS_PER_TICKET
        if estimated_total > 0:
            pct = min(99.0, (elapsed / estimated_total) * 100)
            remain = max(0.0, estimated_total - elapsed)
        else:
            pct, remain = 0.0, 0.0

        self._draw_arc(pct)
        self._progress_bar["value"] = pct
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
        """Called from pipeline thread — schedule UI update on main thread."""
        # Track current ticket name for grouping in errors tab
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
        """Write one entry to the visible log, respecting active tab filter."""
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

        # Ticket divider — shown in both tabs
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

        # Normal row: timestamp  [LEVEL]  message
        self._log_text.insert("end", f"  {ts}  ", "ts")
        self._log_text.insert("end", f" {lvl:<8} ", lvl)
        self._log_text.insert("end", f"  {msg}\n", "msg")

        self._log_text.config(state="disabled")
        self._log_text.see("end")

    def _redraw_log(self):
        """Redraw from scratch based on active tab."""
        self._log_text.config(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.config(state="disabled")

        if self._active_tab in ("errors", "warnings"):
            target_level = LogType.ERROR if self._active_tab == "errors" else LogType.WARNING

            # Bucket matching entries by ticket — only render tickets that have matches
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

            # Flush last ticket
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

    # ─────────────────────────────────────────────────────────
    #  Misc helpers
    # ─────────────────────────────────────────────────────────

    def _spacer(self, parent, h: int = 8):
        tk.Frame(parent, bg=SURFACE, height=h).pack(fill="x")


# ═════════════════════════════════════════════════════════════
#  Entry point
# ═════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = App()
    app.mainloop()