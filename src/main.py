import customtkinter as ctk
from tkinter import filedialog, ttk, messagebox
import cv2
from PIL import Image
import threading
from ultralytics import YOLO
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import os
import time
import pyxtf
import numpy as np
import csv
import json
import datetime
import winsound
import torch

# Initialize CustomTkinter settings
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")


class SonnetApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("SONNET - Sonar Target Detection & Acoustic Intelligence Workstation")
        self.geometry("1420x900")
        self.minsize(1240, 780)
        self.is_fullscreen = False

        try:
            self.iconbitmap("assets/icon.ico")
        except Exception:
            pass

        # Compute Hardware Detection
        self.has_cuda = torch.cuda.is_available()
        self.device_name = torch.cuda.get_device_name(0) if self.has_cuda else "CPU (Optimized)"

        # Model Management
        self.model = None
        self.available_models = self.discover_models()
        self.current_model_path = "models/sonar_yolo11s_balanced_v1_best.pt"
        self.load_active_model(self.current_model_path)

        # Media & Playback State
        self.media_path = None
        self.is_playing = False
        self.cap = None
        self.is_image = False
        self.is_xtf = False
        self.total_frames = 0
        self.current_frame_idx = 0
        self.video_fps = 25.0
        self.playback_speed = 1.0
        self.stop_requested = False
        self.play_thread = None

        # DSP & Visual Enhancement
        self.active_colormap = "Default"
        self.clahe_enabled = False
        self.clahe_clip = 2.0
        self.contrast_factor = 1.0
        self.brightness_offset = 0

        # Telemetry State
        self.gps_data = []
        self.current_lat = "--"
        self.current_lon = "--"
        self.current_depth = "--"

        # Threat Alert System
        self.audio_alerts_enabled = True
        self.last_alert_time = 0

        # Analytics & Target Records
        self.stats = {"pipeline": 0, "shipwreck": 0, "mine_cylinder": 0, "ghost_net": 0, "crab_pot": 0}
        self.target_records = {}  # {display_id: dict}
        self.target_counter = 0
        self.selected_target_id = None
        self.log_filter = "All Targets"

        # Directories
        self.snapshots_dir = "snapshots"
        self.reports_dir = "reports"
        os.makedirs(self.snapshots_dir, exist_ok=True)
        os.makedirs(self.reports_dir, exist_ok=True)

        # Performance Monitoring
        self.start_time = 0
        self.frames_processed = 0

        # Custom Tracker
        self.custom_tracker = []
        self.global_id_counter = 0

        # Build UI & Bindings
        self.setup_ui()
        self.setup_keybindings()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def discover_models(self):
        models = {}
        for search_dir in ["models", "weights"]:
            if os.path.exists(search_dir):
                for f in os.listdir(search_dir):
                    if f.endswith(".pt"):
                        full_p = os.path.join(search_dir, f)
                        models[f] = full_p
        if not models:
            models["sonar_yolo11s_best.pt"] = "models/sonar_yolo11s_balanced_v1_best.pt"
        return models

    def load_active_model(self, model_path):
        try:
            if os.path.exists(model_path):
                self.model = YOLO(model_path)
                self.current_model_path = model_path
            else:
                self.model = None
        except Exception as e:
            self.model = None
            print("Model load error:", e)

    def setup_keybindings(self):
        self.bind("<space>", lambda e: self.toggle_play())
        self.bind("<Left>", lambda e: self.step_backward())
        self.bind("<Right>", lambda e: self.step_forward())
        self.bind("<F11>", lambda e: self.toggle_fullscreen())

    def toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        self.attributes("-fullscreen", self.is_fullscreen)
        if hasattr(self, 'btn_fullscreen'):
            self.btn_fullscreen.configure(text="⛶ EXIT FULLSCREEN" if self.is_fullscreen else "⛶ FULLSCREEN")

    # ==========================================
    # UI SETUP
    # ==========================================
    def setup_ui(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # ------------------------------------------
        # TOP BAR
        # ------------------------------------------
        self.topbar = ctk.CTkFrame(self, height=54, corner_radius=0, fg_color="#18191d")
        self.topbar.grid(row=0, column=0, columnspan=3, sticky="ew")

        # Logo & App Title
        try:
            logo_img = Image.open("assets/logo.png")
            aspect = logo_img.width / logo_img.height
            new_w = int(28 * aspect)
            self.ctk_logo = ctk.CTkImage(light_image=logo_img, dark_image=logo_img, size=(new_w, 28))
            self.lbl_logo = ctk.CTkLabel(
                self.topbar,
                text=" SONNET",
                image=self.ctk_logo,
                compound="left",
                text_color="#4dabf7",
                font=ctk.CTkFont(size=19, weight="bold")
            )
        except Exception:
            self.lbl_logo = ctk.CTkLabel(
                self.topbar,
                text="🌊 SONNET",
                text_color="#4dabf7",
                font=ctk.CTkFont(size=19, weight="bold")
            )
        self.lbl_logo.pack(side="left", padx=16, pady=10)

        # Status Pill
        self.status_pill = ctk.CTkLabel(
            self.topbar,
            text="🟢 STANDBY",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#51cf66",
            fg_color="#1a2e22",
            corner_radius=12,
            padx=12,
            pady=4
        )
        self.status_pill.pack(side="left", padx=10)

        # Compute Hardware Pill
        hw_color = "#339af0" if self.has_cuda else "#868e96"
        self.lbl_hw_badge = ctk.CTkLabel(
            self.topbar,
            text=f"⚙ {self.device_name}",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=hw_color,
            fg_color="#1e2227",
            corner_radius=6,
            padx=8,
            pady=3
        )
        self.lbl_hw_badge.pack(side="left", padx=6)

        # Top Bar Action Buttons
        self.btn_snapshots = ctk.CTkButton(
            self.topbar,
            text="🖼️ GALLERY",
            width=100,
            height=32,
            command=self.open_snapshots,
            fg_color="#b85c14",
            hover_color="#d97a32",
            font=ctk.CTkFont(size=11, weight="bold")
        )
        self.btn_snapshots.pack(side="left", padx=6)

        self.btn_report = ctk.CTkButton(
            self.topbar,
            text="📄 PDF",
            width=75,
            height=32,
            command=self.generate_report,
            fg_color="#1c7ed6",
            hover_color="#1864ab",
            font=ctk.CTkFont(size=11, weight="bold")
        )
        self.btn_report.pack(side="left", padx=4)

        self.btn_export_csv = ctk.CTkButton(
            self.topbar,
            text="📊 CSV",
            width=70,
            height=32,
            command=self.export_csv,
            fg_color="#343a40",
            hover_color="#495057",
            font=ctk.CTkFont(size=11, weight="bold")
        )
        self.btn_export_csv.pack(side="left", padx=4)

        self.btn_export_geojson = ctk.CTkButton(
            self.topbar,
            text="🌐 GEOJSON",
            width=85,
            height=32,
            command=self.export_geojson,
            fg_color="#343a40",
            hover_color="#495057",
            font=ctk.CTkFont(size=11, weight="bold")
        )
        self.btn_export_geojson.pack(side="left", padx=4)

        # Audio Alert Switch
        self.switch_audio = ctk.CTkSwitch(
            self.topbar,
            text="🔊 Alerts",
            command=self.toggle_audio_alerts,
            font=ctk.CTkFont(size=11),
            text_color="#adb5bd",
            progress_color="#e03131"
        )
        self.switch_audio.select()
        self.switch_audio.pack(side="left", padx=10)

        # Right-aligned Buttons
        self.btn_fullscreen = ctk.CTkButton(
            self.topbar,
            text="⛶ FULLSCREEN",
            width=105,
            height=32,
            command=self.toggle_fullscreen,
            fg_color="#343a40",
            hover_color="#495057",
            font=ctk.CTkFont(size=11)
        )
        self.btn_fullscreen.pack(side="right", padx=12)

        self.btn_load_gps = ctk.CTkButton(
            self.topbar,
            text="📡 LOAD GPS",
            width=100,
            height=32,
            command=self.load_gps,
            fg_color="#495057",
            hover_color="#5c636a",
            font=ctk.CTkFont(size=11, weight="bold")
        )
        self.btn_load_gps.pack(side="right", padx=4)

        self.btn_load = ctk.CTkButton(
            self.topbar,
            text="📁 LOAD MEDIA",
            width=110,
            height=32,
            command=self.load_media,
            fg_color="#228be6",
            hover_color="#1c7ed6",
            font=ctk.CTkFont(size=11, weight="bold")
        )
        self.btn_load.pack(side="right", padx=4)

        # ------------------------------------------
        # LEFT SIDEBAR: MODEL, DSP & TELEMETRY
        # ------------------------------------------
        self.left_sidebar = ctk.CTkScrollableFrame(self, width=270, corner_radius=0, fg_color="#121316")
        self.left_sidebar.grid(row=1, column=0, sticky="nsew", padx=1, pady=1)

        # Active Model Selector
        ctk.CTkLabel(
            self.left_sidebar,
            text="ACTIVE YOLO MODEL",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#868e96"
        ).pack(anchor="w", padx=10, pady=(10, 4))

        model_names = list(self.available_models.keys())
        default_model_name = os.path.basename(self.current_model_path)
        if default_model_name not in model_names and model_names:
            default_model_name = model_names[0]

        self.model_menu = ctk.CTkOptionMenu(
            self.left_sidebar,
            values=model_names,
            command=self.on_model_selected,
            fg_color="#212529",
            button_color="#343a40"
        )
        self.model_menu.set(default_model_name)
        self.model_menu.pack(fill="x", padx=10, pady=2)

        # Model Sensitivity
        ctk.CTkLabel(self.left_sidebar, text="Confidence Threshold", text_color="#ced4da", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=10, pady=(8, 0))
        self.conf_slider = ctk.CTkSlider(self.left_sidebar, from_=0.05, to=0.95, progress_color="#1c7ed6")
        self.conf_slider.set(0.25)
        self.conf_slider.pack(fill="x", padx=10, pady=2)

        ctk.CTkLabel(self.left_sidebar, text="IoU (NMS) Overlap", text_color="#ced4da", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=10)
        self.iou_slider = ctk.CTkSlider(self.left_sidebar, from_=0.10, to=0.90, progress_color="#b85c14")
        self.iou_slider.set(0.45)
        self.iou_slider.pack(fill="x", padx=10, pady=2)

        # Section: Acoustic Signal Enhancement (DSP)
        ctk.CTkLabel(
            self.left_sidebar,
            text="ACOUSTIC SIGNAL ENHANCEMENT",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#868e96"
        ).pack(anchor="w", padx=10, pady=(16, 4))

        ctk.CTkLabel(self.left_sidebar, text="Acoustic Palette", text_color="#ced4da", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=10)
        self.cmap_menu = ctk.CTkOptionMenu(
            self.left_sidebar,
            values=["Default", "Thermal (Inferno)", "Ironbow (Jet)", "Ocean Blue", "Amber (Sepia)"],
            command=self.on_colormap_changed,
            fg_color="#212529",
            button_color="#343a40"
        )
        self.cmap_menu.set("Default")
        self.cmap_menu.pack(fill="x", padx=10, pady=2)

        # CLAHE Adaptive Contrast Switch & Slider
        self.switch_clahe = ctk.CTkSwitch(
            self.left_sidebar,
            text="CLAHE Adaptive Equalizer",
            command=self.on_clahe_toggle,
            font=ctk.CTkFont(size=11),
            text_color="#ced4da",
            progress_color="#2b8a3e"
        )
        self.switch_clahe.pack(anchor="w", padx=10, pady=(10, 4))

        ctk.CTkLabel(self.left_sidebar, text="CLAHE Clip Limit", text_color="#ced4da", font=ctk.CTkFont(size=10)).pack(anchor="w", padx=10)
        self.clahe_slider = ctk.CTkSlider(self.left_sidebar, from_=1.0, to=5.0, command=self.on_clahe_clip_slide, progress_color="#2b8a3e")
        self.clahe_slider.set(2.0)
        self.clahe_slider.pack(fill="x", padx=10, pady=2)

        # Gain & Brightness
        ctk.CTkLabel(self.left_sidebar, text="Acoustic Gain (Contrast)", text_color="#ced4da", font=ctk.CTkFont(size=10)).pack(anchor="w", padx=10, pady=(6, 0))
        self.contrast_slider = ctk.CTkSlider(self.left_sidebar, from_=0.5, to=2.0, command=self.on_contrast_slide, progress_color="#1c7ed6")
        self.contrast_slider.set(1.0)
        self.contrast_slider.pack(fill="x", padx=10, pady=2)

        # Section: Telemetry Readout
        ctk.CTkLabel(
            self.left_sidebar,
            text="VESSEL TELEMETRY",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#868e96"
        ).pack(anchor="w", padx=10, pady=(16, 4))

        self.telemetry_card = ctk.CTkFrame(self.left_sidebar, fg_color="#18191d", corner_radius=6)
        self.telemetry_card.pack(fill="x", padx=10, pady=4)

        self.lbl_lat = ctk.CTkLabel(self.telemetry_card, text="Lat:    --°", text_color="#ced4da", font=ctk.CTkFont(size=11, family="Consolas"))
        self.lbl_lat.pack(anchor="w", padx=10, pady=(6, 2))
        self.lbl_lon = ctk.CTkLabel(self.telemetry_card, text="Lon:    --°", text_color="#ced4da", font=ctk.CTkFont(size=11, family="Consolas"))
        self.lbl_lon.pack(anchor="w", padx=10, pady=2)
        self.lbl_depth = ctk.CTkLabel(self.telemetry_card, text="Depth:  -- m", text_color="#ced4da", font=ctk.CTkFont(size=11, family="Consolas"))
        self.lbl_depth.pack(anchor="w", padx=10, pady=(2, 6))

        self.lbl_gps_status = ctk.CTkLabel(self.left_sidebar, text="GPS: Telemetry Offline", text_color="#fa5252", font=ctk.CTkFont(size=10))
        self.lbl_gps_status.pack(anchor="w", padx=10, pady=4)

        # ------------------------------------------
        # CENTER VIEW: VIDEO / SONAR FEED + CONTROLS
        # ------------------------------------------
        self.center_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#000000")
        self.center_frame.grid(row=1, column=1, sticky="nsew", padx=1, pady=1)
        self.center_frame.grid_rowconfigure(1, weight=1)
        self.center_frame.grid_columnconfigure(0, weight=1)

        # Video Header
        self.video_header_frame = ctk.CTkFrame(self.center_frame, height=30, corner_radius=0, fg_color="#18191d")
        self.video_header_frame.grid(row=0, column=0, sticky="ew")

        self.lbl_video_header = ctk.CTkLabel(
            self.video_header_frame,
            text=" Sidescan Acoustic View (No Media Loaded)",
            text_color="#e9ecef",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.lbl_video_header.pack(side="left", padx=10, pady=4)

        self.lbl_resolution = ctk.CTkLabel(
            self.video_header_frame,
            text="--x--",
            text_color="#868e96",
            font=ctk.CTkFont(size=11)
        )
        self.lbl_resolution.pack(side="right", padx=12, pady=4)

        # Display Label for video frames
        self.lbl_video = ctk.CTkLabel(
            self.center_frame,
            text="NO SIGNAL / NO MEDIA LOADED\n\nClick 'LOAD MEDIA' or press Space to analyze",
            text_color="#495057",
            font=ctk.CTkFont(size=15, weight="bold")
        )
        self.lbl_video.grid(row=1, column=0, sticky="nsew")

        # Transport & Video Scrubber Bar
        self.transport_frame = ctk.CTkFrame(self.center_frame, height=80, corner_radius=0, fg_color="#121316")
        self.transport_frame.grid(row=2, column=0, sticky="ew")

        # Row 1: Timeline Scrubber Slider + Time/Frame Readout
        self.scrub_frame = ctk.CTkFrame(self.transport_frame, fg_color="transparent")
        self.scrub_frame.pack(fill="x", padx=10, pady=(6, 2))

        self.scrub_slider = ctk.CTkSlider(
            self.scrub_frame,
            from_=0,
            to=100,
            command=self.on_scrub_slide,
            progress_color="#228be6"
        )
        self.scrub_slider.set(0)
        self.scrub_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.lbl_time_status = ctk.CTkLabel(
            self.scrub_frame,
            text="00:00 / 00:00 (F: 0/0)",
            text_color="#adb5bd",
            font=ctk.CTkFont(size=11, family="Consolas")
        )
        self.lbl_time_status.pack(side="right")

        # Row 2: Playback Action Buttons
        self.ctrl_buttons_frame = ctk.CTkFrame(self.transport_frame, fg_color="transparent")
        self.ctrl_buttons_frame.pack(fill="x", padx=10, pady=(2, 6))

        self.btn_step_back = ctk.CTkButton(
            self.ctrl_buttons_frame,
            text="⏮ -1s",
            width=65,
            height=28,
            command=self.step_backward,
            fg_color="#212529",
            hover_color="#343a40"
        )
        self.btn_step_back.pack(side="left", padx=3)

        self.btn_play = ctk.CTkButton(
            self.ctrl_buttons_frame,
            text="▶ PLAY",
            width=100,
            height=28,
            command=self.toggle_play,
            fg_color="#2b8a3e",
            hover_color="#2f9e44",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.btn_play.pack(side="left", padx=4)

        self.btn_step_fwd = ctk.CTkButton(
            self.ctrl_buttons_frame,
            text="+1s ⏭",
            width=65,
            height=28,
            command=self.step_forward,
            fg_color="#212529",
            hover_color="#343a40"
        )
        self.btn_step_fwd.pack(side="left", padx=3)

        self.btn_stop = ctk.CTkButton(
            self.ctrl_buttons_frame,
            text="⏹ STOP",
            width=70,
            height=28,
            command=self.stop_media,
            fg_color="#c92a2a",
            hover_color="#e03131"
        )
        self.btn_stop.pack(side="left", padx=4)

        # Speed selector
        ctk.CTkLabel(self.ctrl_buttons_frame, text="Speed:", text_color="#868e96", font=ctk.CTkFont(size=11)).pack(side="right", padx=(10, 4))
        self.speed_menu = ctk.CTkOptionMenu(
            self.ctrl_buttons_frame,
            values=["0.5x", "1.0x", "2.0x"],
            width=75,
            height=28,
            command=self.on_speed_changed,
            fg_color="#212529",
            button_color="#343a40"
        )
        self.speed_menu.set("1.0x")
        self.speed_menu.pack(side="right", padx=4)

        # ------------------------------------------
        # RIGHT SIDEBAR: MAP & TARGET INSPECTOR
        # ------------------------------------------
        self.right_sidebar = ctk.CTkFrame(self, width=340, corner_radius=0, fg_color="#121316")
        self.right_sidebar.grid(row=1, column=2, sticky="nsew", padx=1, pady=1)
        self.right_sidebar.pack_propagate(False)

        # Geospatial Map
        ctk.CTkLabel(
            self.right_sidebar,
            text="GEOSPATIAL SURVEY MAP",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#868e96"
        ).pack(anchor="w", padx=14, pady=(10, 4))

        try:
            import tkintermapview
            self.map_widget = tkintermapview.TkinterMapView(self.right_sidebar, width=310, height=250, corner_radius=6)
            self.map_widget.pack(padx=14, pady=2)
            self.map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}&s=Ga", max_zoom=22)
            self.map_widget.set_position(0, 0)
            self.map_widget.set_zoom(1)

            self.map_overlay = ctk.CTkFrame(self.right_sidebar, width=310, height=250, fg_color="#0a1220", corner_radius=6)
            self.map_overlay.place(in_=self.map_widget, relx=0, rely=0, relwidth=1, relheight=1)
            ctk.CTkLabel(self.map_overlay, text="No GPS Data Loaded.\nLoad GPS to view track.", text_color="#868e96").place(relx=0.5, rely=0.5, anchor="center")
        except ImportError:
            self.map_area = ctk.CTkFrame(self.right_sidebar, width=310, height=250, fg_color="#0a1220", corner_radius=6)
            self.map_area.pack(padx=14, pady=2)
            ctk.CTkLabel(self.map_area, text="Map widget unavailable.", text_color="#fa5252").place(relx=0.5, rely=0.5, anchor="center")

        # Target Inspector Card
        ctk.CTkLabel(
            self.right_sidebar,
            text="TARGET INSPECTOR & VERIFICATION",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#868e96"
        ).pack(anchor="w", padx=14, pady=(12, 4))

        self.inspector_card = ctk.CTkScrollableFrame(self.right_sidebar, height=350, fg_color="#18191d", corner_radius=6)
        self.inspector_card.pack(fill="both", expand=True, padx=14, pady=(2, 10))

        # Inspector Placeholder / Thumbnail
        self.lbl_insp_thumb = ctk.CTkLabel(
            self.inspector_card,
            text="Select an anomaly in the\nTarget Log to inspect details",
            text_color="#495057",
            font=ctk.CTkFont(size=11)
        )
        self.lbl_insp_thumb.pack(fill="x", padx=10, pady=(6, 4))

        self.lbl_insp_title = ctk.CTkLabel(
            self.inspector_card,
            text="--",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#4dabf7"
        )
        self.lbl_insp_title.pack(anchor="w", padx=10, pady=2)

        self.lbl_insp_meta = ctk.CTkLabel(
            self.inspector_card,
            text="Confidence: --\nCoordinates: --\nTime/Frame: --",
            justify="left",
            text_color="#ced4da",
            font=ctk.CTkFont(size=11, family="Consolas")
        )
        self.lbl_insp_meta.pack(anchor="w", padx=10, pady=2)

        # Verification Status Radio / Segmented Button
        ctk.CTkLabel(self.inspector_card, text="Operator Status:", text_color="#868e96", font=ctk.CTkFont(size=10, weight="bold")).pack(anchor="w", padx=10, pady=(6, 2))
        self.seg_verify = ctk.CTkSegmentedButton(
            self.inspector_card,
            values=["❓ Pending", "✅ Confirmed", "❌ False Alarm"],
            command=self.on_verification_changed,
            selected_color="#1c7ed6"
        )
        self.seg_verify.set("❓ Pending")
        self.seg_verify.pack(fill="x", padx=10, pady=2)

        # Operator Notes
        ctk.CTkLabel(self.inspector_card, text="Operator Notes:", text_color="#868e96", font=ctk.CTkFont(size=10, weight="bold")).pack(anchor="w", padx=10, pady=(6, 2))
        self.entry_notes = ctk.CTkEntry(self.inspector_card, placeholder_text="Type observations here...")
        self.entry_notes.pack(fill="x", padx=10, pady=2)

        self.btn_save_note = ctk.CTkButton(
            self.inspector_card,
            text="💾 Save Notes & Status",
            height=26,
            command=self.save_operator_notes,
            fg_color="#343a40",
            hover_color="#495057",
            font=ctk.CTkFont(size=11)
        )
        self.btn_save_note.pack(fill="x", padx=10, pady=(2, 6))

        # Inspector Action Buttons
        self.insp_actions_frame = ctk.CTkFrame(self.inspector_card, fg_color="transparent")
        self.insp_actions_frame.pack(fill="x", padx=10, pady=(4, 6))

        self.btn_insp_open = ctk.CTkButton(
            self.insp_actions_frame,
            text="🔍 Open Snapshot",
            width=135,
            height=28,
            command=self.open_selected_snapshot,
            fg_color="#343a40",
            hover_color="#495057",
            font=ctk.CTkFont(size=11)
        )
        self.btn_insp_open.pack(side="left", padx=2)

        self.btn_insp_map = ctk.CTkButton(
            self.insp_actions_frame,
            text="📍 Center Map",
            width=115,
            height=28,
            command=self.center_map_on_selected,
            fg_color="#343a40",
            hover_color="#495057",
            font=ctk.CTkFont(size=11)
        )
        self.btn_insp_map.pack(side="right", padx=2)

        # ------------------------------------------
        # BOTTOM: LOG & ANALYTICS
        # ------------------------------------------
        self.bottom_frame = ctk.CTkFrame(self, height=240, corner_radius=0, fg_color="#121316")
        self.bottom_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=1, pady=1)
        self.bottom_frame.grid_columnconfigure(0, weight=6)
        self.bottom_frame.grid_columnconfigure(1, weight=4)
        self.bottom_frame.grid_rowconfigure(0, weight=1)

        # Target Log Frame
        self.log_frame = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
        self.log_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=6)

        self.log_header_frame = ctk.CTkFrame(self.log_frame, fg_color="transparent")
        self.log_header_frame.pack(fill="x")

        ctk.CTkLabel(self.log_header_frame, text="● Detected Anomaly Log", font=ctk.CTkFont(size=12, weight="bold"), text_color="#4dabf7").pack(side="left")

        # Category Filter Dropdown
        self.filter_menu = ctk.CTkOptionMenu(
            self.log_header_frame,
            values=["All Targets", "Confirmed Only", "Mines Only", "Shipwrecks Only"],
            width=130,
            height=24,
            command=self.on_filter_changed,
            fg_color="#212529",
            button_color="#343a40"
        )
        self.filter_menu.set("All Targets")
        self.filter_menu.pack(side="left", padx=12)

        self.lbl_fps = ctk.CTkLabel(self.log_header_frame, text="FPS: 0.0", font=ctk.CTkFont(size=11), text_color="#868e96")
        self.lbl_fps.pack(side="right", padx=10)
        self.lbl_total_dets = ctk.CTkLabel(self.log_header_frame, text="Total Anomalies: 0", font=ctk.CTkFont(size=11), text_color="#868e96")
        self.lbl_total_dets.pack(side="right", padx=10)

        # Treeview styling
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#121316", foreground="#dee2e6", fieldbackground="#121316", borderwidth=0, rowheight=24)
        style.configure("Treeview.Heading", background="#18191d", foreground="#adb5bd", borderwidth=0, font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", "#1c7ed6")])

        cols = ("TRACK ID", "CLASS", "CONFIDENCE", "STATUS", "TIME/FRAME", "LATITUDE", "LONGITUDE")
        self.tree = ttk.Treeview(self.log_frame, columns=cols, show="headings", height=6)
        self.tree.heading("TRACK ID", text="TRACK ID")
        self.tree.column("TRACK ID", width=85, anchor="w")
        self.tree.heading("CLASS", text="CLASS")
        self.tree.column("CLASS", width=110, anchor="w")
        self.tree.heading("CONFIDENCE", text="CONFIDENCE")
        self.tree.column("CONFIDENCE", width=90, anchor="w")
        self.tree.heading("STATUS", text="STATUS")
        self.tree.column("STATUS", width=105, anchor="w")
        self.tree.heading("TIME/FRAME", text="TIME/FRAME")
        self.tree.column("TIME/FRAME", width=100, anchor="w")
        self.tree.heading("LATITUDE", text="LATITUDE")
        self.tree.column("LATITUDE", width=100, anchor="w")
        self.tree.heading("LONGITUDE", text="LONGITUDE")
        self.tree.column("LONGITUDE", width=100, anchor="w")

        self.tree.pack(fill="both", expand=True, pady=4)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # Analytics Graph
        self.graph_frame = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
        self.graph_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=6)

        ctk.CTkLabel(self.graph_frame, text="📊 Anomaly Distribution", font=ctk.CTkFont(size=12, weight="bold"), text_color="#4dabf7").pack(anchor="w")

        plt.style.use('dark_background')
        self.fig, self.ax = plt.subplots(figsize=(4, 2.3), dpi=80)
        self.fig.patch.set_facecolor('#121316')
        self.ax.set_facecolor('#121316')
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self.update_graph()

    # ==========================================
    # MODEL MANAGEMENT & HOT-SWAPPING
    # ==========================================
    def on_model_selected(self, model_name):
        model_path = self.available_models.get(model_name)
        if model_path:
            self.load_active_model(model_path)
            self.set_status(f"🟢 LOADED: {model_name}", "#51cf66", "#1a2e22")

    # ==========================================
    # DSP & ACOUSTIC IMAGE PROCESSING
    # ==========================================
    def on_colormap_changed(self, choice):
        self.active_colormap = choice

    def on_clahe_toggle(self):
        self.clahe_enabled = bool(self.switch_clahe.get())

    def on_clahe_clip_slide(self, val):
        self.clahe_clip = float(val)

    def on_contrast_slide(self, val):
        self.contrast_factor = float(val)

    def toggle_audio_alerts(self):
        self.audio_alerts_enabled = bool(self.switch_audio.get())

    def apply_dsp_filters(self, bgr_frame):
        processed = bgr_frame

        # 1. Gain & Contrast Adjustments
        if self.contrast_factor != 1.0:
            processed = cv2.convertScaleAbs(processed, alpha=self.contrast_factor, beta=self.brightness_offset)

        # 2. CLAHE Adaptive Equalization
        if self.clahe_enabled:
            lab = cv2.cvtColor(processed, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=self.clahe_clip, tileGridSize=(8, 8))
            cl = clahe.apply(l)
            limg = cv2.merge((cl, a, b))
            processed = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

        # 3. Sonar Palettes / Colormaps
        if self.active_colormap == "Thermal (Inferno)":
            gray = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
            processed = cv2.applyColorMap(gray, cv2.COLORMAP_INFERNO)
        elif self.active_colormap == "Ironbow (Jet)":
            gray = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
            processed = cv2.applyColorMap(gray, cv2.COLORMAP_JET)
        elif self.active_colormap == "Ocean Blue":
            gray = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
            processed = cv2.applyColorMap(gray, cv2.COLORMAP_OCEAN)
        elif self.active_colormap == "Amber (Sepia)":
            gray = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
            processed = cv2.applyColorMap(gray, cv2.COLORMAP_AUTUMN)

        return processed

    # ==========================================
    # MEDIA LOADING & VIDEO CONTROLS
    # ==========================================
    def load_media(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Media Files", "*.mp4 *.avi *.mkv *.mov *.jpg *.jpeg *.png *.xtf"), ("All Files", "*.*")]
        )
        if not file_path:
            return

        self.stop_media()
        self.media_path = file_path
        filename = os.path.basename(file_path)
        self.lbl_video_header.configure(text=f" Sidescan Acoustic View - {filename}")

        ext = os.path.splitext(filename)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png']:
            self.is_image = True
            self.is_xtf = False
            self.btn_play.configure(text="▶ DETECT IMAGE")
            self.total_frames = 1
            self.scrub_slider.configure(to=1)
            self.scrub_slider.set(0)
            self.lbl_time_status.configure(text="Single Still Frame")
            img = cv2.imread(self.media_path)
            if img is not None:
                h, w = img.shape[:2]
                self.lbl_resolution.configure(text=f"{w}x{h}")
                self.display_frame(self.apply_dsp_filters(img))
        elif ext == '.xtf':
            self.is_image = False
            self.is_xtf = True
            self.btn_play.configure(text="▶ PLAY XTF")
            self.lbl_time_status.configure(text="XTF Waterfall Stream")
        else:
            self.is_image = False
            self.is_xtf = False
            self.btn_play.configure(text="▶ PLAY VIDEO")

            self.cap = cv2.VideoCapture(self.media_path)
            if self.cap.isOpened():
                self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                fps = self.cap.get(cv2.CAP_PROP_FPS)
                if fps and fps > 0:
                    self.video_fps = fps
                w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                self.lbl_resolution.configure(text=f"{w}x{h}")
                self.scrub_slider.configure(to=max(1, self.total_frames - 1))
                self.scrub_slider.set(0)
                self.update_time_label(0)

                ret, frame = self.cap.read()
                if ret:
                    self.display_frame(self.apply_dsp_filters(frame))
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        self.set_status("🟢 MEDIA LOADED", "#51cf66", "#1a2e22")

    def toggle_play(self):
        if not self.media_path:
            return

        if self.is_image:
            threading.Thread(target=self.process_image, daemon=True).start()
        elif self.is_xtf:
            if not self.is_playing:
                self.is_playing = True
                self.btn_play.configure(text="⏸ PAUSE XTF", fg_color="#c92a2a")
                self.set_status("🔵 STREAMING XTF", "#339af0", "#18283b")
                threading.Thread(target=self.play_xtf_loop, daemon=True).start()
            else:
                self.is_playing = False
                self.btn_play.configure(text="▶ PLAY XTF", fg_color="#2b8a3e")
                self.set_status("🟡 PAUSED", "#fcc419", "#362b10")
        else:
            if not self.is_playing:
                self.is_playing = True
                self.stop_requested = False
                self.btn_play.configure(text="⏸ PAUSE", fg_color="#c92a2a")
                self.set_status("🔵 SCANNING", "#339af0", "#18283b")

                if self.cap is None or not self.cap.isOpened():
                    self.cap = cv2.VideoCapture(self.media_path)
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame_idx)

                self.play_thread = threading.Thread(target=self.play_loop, daemon=True)
                self.play_thread.start()
            else:
                self.is_playing = False
                self.btn_play.configure(text="▶ PLAY", fg_color="#2b8a3e")
                self.set_status("🟡 PAUSED", "#fcc419", "#362b10")

    def stop_media(self):
        self.is_playing = False
        self.stop_requested = True
        self.current_frame_idx = 0
        self.btn_play.configure(text="▶ PLAY", fg_color="#2b8a3e")
        self.set_status("🟢 STANDBY", "#51cf66", "#1a2e22")

        if self.cap and self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()
            if ret:
                self.display_frame(self.apply_dsp_filters(frame))
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        self.scrub_slider.set(0)
        self.update_time_label(0)

    def on_scrub_slide(self, value):
        if self.is_image or self.is_xtf or not self.cap or not self.cap.isOpened():
            return

        target_frame = int(value)
        self.current_frame_idx = target_frame
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        ret, frame = self.cap.read()
        if ret:
            self.sync_telemetry_for_frame(target_frame)
            processed = self.apply_dsp_filters(frame)
            self.display_frame(processed)
            self.update_time_label(target_frame)

    def step_forward(self):
        if not self.cap or not self.cap.isOpened() or self.is_image:
            return
        step = int(self.video_fps)
        new_frame = min(self.total_frames - 1, self.current_frame_idx + step)
        self.scrub_slider.set(new_frame)
        self.on_scrub_slide(new_frame)

    def step_backward(self):
        if not self.cap or not self.cap.isOpened() or self.is_image:
            return
        step = int(self.video_fps)
        new_frame = max(0, self.current_frame_idx - step)
        self.scrub_slider.set(new_frame)
        self.on_scrub_slide(new_frame)

    def on_speed_changed(self, choice):
        try:
            self.playback_speed = float(choice.replace("x", ""))
        except Exception:
            self.playback_speed = 1.0

    def update_time_label(self, frame_num):
        if self.video_fps > 0:
            cur_sec = int(frame_num / self.video_fps)
            tot_sec = int(self.total_frames / self.video_fps)
            cur_str = f"{cur_sec // 60:02d}:{cur_sec % 60:02d}"
            tot_str = f"{tot_sec // 60:02d}:{tot_sec % 60:02d}"
            self.lbl_time_status.configure(text=f"{cur_str} / {tot_str} (F: {frame_num}/{self.total_frames})")

    def set_status(self, text, fg_color, bg_color):
        self.status_pill.configure(text=text, text_color=fg_color, fg_color=bg_color)

    # ==========================================
    # PLAYBACK LOOPS & DETECTION
    # ==========================================
    def process_image(self):
        frame = cv2.imread(self.media_path)
        if frame is None:
            return

        conf = self.conf_slider.get()
        iou = self.iou_slider.get()

        if self.model is not None:
            results = self.model(frame, conf=conf, iou=iou, verbose=False)
            res_frame = results[0].plot()
            self.process_detections(results[0], "Still Image", res_frame, is_video=False)
        else:
            res_frame = frame

        colored = self.apply_dsp_filters(res_frame)
        self.display_frame(colored)

    def play_loop(self):
        self.start_time = time.time()
        self.frames_processed = 0

        while self.is_playing and self.cap and self.cap.isOpened() and not self.stop_requested:
            ret, frame = self.cap.read()
            if not ret:
                break

            self.current_frame_idx += 1
            self.frames_processed += 1
            conf = self.conf_slider.get()
            iou = self.iou_slider.get()

            elapsed = time.time() - self.start_time
            if elapsed > 0:
                fps = self.frames_processed / elapsed
                self.after(0, lambda f=fps: self.lbl_fps.configure(text=f"FPS: {f:.1f}"))

            self.sync_telemetry_for_frame(self.current_frame_idx)

            if self.model is not None:
                results = self.model.track(frame, conf=conf, iou=iou, persist=True, tracker="bytetrack.yaml", verbose=False)
                res_frame = results[0].plot(conf=False)
                self.process_detections(results[0], f"F-{self.current_frame_idx}", res_frame, is_video=True)
            else:
                res_frame = frame

            final_frame = self.apply_dsp_filters(res_frame)
            self.display_frame(final_frame)

            cur_idx = self.current_frame_idx
            self.after(0, lambda idx=cur_idx: self.scrub_slider.set(idx))
            self.after(0, lambda idx=cur_idx: self.update_time_label(idx))

            delay = (1.0 / self.video_fps) / max(0.25, self.playback_speed)
            time.sleep(max(0.005, delay))

        if self.current_frame_idx >= self.total_frames - 1:
            self.is_playing = False
            self.after(0, lambda: self.btn_play.configure(text="▶ PLAY", fg_color="#2b8a3e"))
            self.after(0, lambda: self.set_status("🟢 END OF MEDIA", "#51cf66", "#1a2e22"))

    def play_xtf_loop(self):
        try:
            (fh, p) = pyxtf.xtf_read(self.media_path)
            sonar_packets = p[pyxtf.XTFHeaderType.sonar]
            if not sonar_packets:
                print("No sonar packets found in XTF")
                self.is_playing = False
                return

            ping_count = len(sonar_packets)
            frame_size = 500
            self.start_time = time.time()
            self.frames_processed = 0

            for i in range(0, ping_count, frame_size):
                if not self.is_playing:
                    break

                chunk = sonar_packets[i:i + frame_size]
                port_data, stbd_data = [], []
                for packet in chunk:
                    if len(packet.data) >= 2:
                        port_data.append(packet.data[0])
                        stbd_data.append(packet.data[1])

                if not port_data:
                    continue

                port_img = np.vstack(port_data)
                stbd_img = np.vstack(stbd_data)
                port_img = np.fliplr(port_img)
                combined = np.hstack((port_img, stbd_img)).astype(np.float32)

                p2, p98 = np.percentile(combined, (2, 98))
                if p98 > p2:
                    combined = np.clip((combined - p2) / (p98 - p2), 0, 1)
                combined = (combined * 255).astype(np.uint8)

                bgr_frame = cv2.cvtColor(combined, cv2.COLOR_GRAY2BGR)
                self.frames_processed += 1
                conf = self.conf_slider.get()
                iou = self.iou_slider.get()

                elapsed = time.time() - self.start_time
                if elapsed > 0:
                    fps = self.frames_processed / elapsed
                    self.after(0, lambda f=fps: self.lbl_fps.configure(text=f"FPS: {f:.1f}"))

                if self.model is not None:
                    results = self.model.track(bgr_frame, conf=conf, iou=iou, persist=True, tracker="bytetrack.yaml", verbose=False)
                    res_frame = results[0].plot(conf=False)
                    self.process_detections(results[0], f"XTF-{i // frame_size}", res_frame, is_video=True)
                else:
                    res_frame = bgr_frame

                final_frame = self.apply_dsp_filters(res_frame)
                self.display_frame(final_frame)
                time.sleep(0.1 / max(0.25, self.playback_speed))

        except Exception as e:
            print("XTF Playback Error:", e)

        self.is_playing = False
        self.after(0, lambda: self.btn_play.configure(text="▶ PLAY XTF", fg_color="#2b8a3e"))
        self.after(0, lambda: self.set_status("🟢 STANDBY", "#51cf66", "#1a2e22"))

    # ==========================================
    # DETECTION & TRACKING MANAGEMENT
    # ==========================================
    def process_detections(self, result, time_frame, res_frame, is_video=False):
        boxes = result.boxes
        if len(boxes) == 0:
            return

        names = result.names
        updated_stats = False

        if not hasattr(self, 'custom_tracker'):
            self.custom_tracker = []
            self.global_id_counter = 0

        if is_video:
            self.custom_tracker = [t for t in self.custom_tracker if t['frames_since'] < 90]
            for t in self.custom_tracker:
                t['frames_since'] += 1

        for i, box in enumerate(boxes):
            cls_id = int(box.cls[0])
            cls_name = names[cls_id] if names else str(cls_id)
            conf_val = float(box.conf[0])
            coords = box.xyxy[0].cpu().numpy()

            is_new = True
            assigned_id = None

            if is_video:
                cx1, cy1 = (coords[0] + coords[2]) / 2, (coords[1] + coords[3]) / 2
                w1, h1 = coords[2] - coords[0], coords[3] - coords[1]

                for t in self.custom_tracker:
                    if t['class'] == cls_name:
                        cx2, cy2 = t['center']
                        dist = ((cx1 - cx2) ** 2 + (cy1 - cy2) ** 2) ** 0.5
                        if dist < max(w1, h1, 100) * 2.0:
                            is_new = False
                            assigned_id = t['id']
                            t['center'] = (cx1, cy1)
                            t['coords'] = coords
                            t['frames_since'] = 0
                            break

                if is_new:
                    self.global_id_counter += 1
                    assigned_id = self.global_id_counter
                    self.custom_tracker.append({
                        'class': cls_name,
                        'center': (cx1, cy1),
                        'coords': coords,
                        'frames_since': 0,
                        'id': assigned_id
                    })

            if not is_video or is_new:
                self.target_counter += 1
                display_id = f"TRK-{assigned_id:03d}" if assigned_id else f"TRK-{self.target_counter:03d}"

                snap_path = ""
                try:
                    x1, y1, x2, y2 = map(int, coords)
                    pad = 20
                    h, w, _ = res_frame.shape
                    px1 = max(0, x1 - pad)
                    py1 = max(0, y1 - pad)
                    px2 = min(w, x2 + pad)
                    py2 = min(h, y2 + pad)

                    crop = res_frame[py1:py2, px1:px2]
                    if crop.size > 0:
                        snap_path = os.path.join(self.snapshots_dir, f"{display_id}_{cls_name}.jpg")
                        cv2.imwrite(snap_path, crop)
                except Exception as e:
                    print("Snapshot crop error:", e)

                cur_lat = self.current_lat
                cur_lon = self.current_lon
                cur_depth = self.current_depth

                record = {
                    "id": display_id,
                    "class": cls_name,
                    "conf": conf_val,
                    "status": "❓ Pending",
                    "notes": "",
                    "time_frame": time_frame,
                    "snapshot": snap_path,
                    "lat": cur_lat,
                    "lon": cur_lon,
                    "depth": cur_depth,
                    "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
                }
                self.target_records[display_id] = record

                # Insert into log table if matches filter
                self.insert_tree_row(record)

                # Geotag on map
                if hasattr(self, 'map_widget') and cur_lat != "--" and cur_lon != "--":
                    try:
                        l_f = float(cur_lat)
                        lo_f = float(cur_lon)
                        self.after(0, lambda lat=l_f, lon=lo_f, text=f"{cls_name.title()} ({display_id})":
                                   self.map_widget.set_marker(lat, lon, text=text))
                    except ValueError:
                        pass

                if cls_name in self.stats:
                    self.stats[cls_name] += 1
                    updated_stats = True

                # Threat Audio-Visual Alert
                self.trigger_threat_alert(cls_name)

        self.after(0, self.prune_tree)
        if updated_stats:
            self.after(0, self.update_graph)

    def trigger_threat_alert(self, cls_name):
        # Visual alert
        self.after(0, lambda name=cls_name: self.set_status(f"🚨 DETECTED: {name.upper()}", "#ff6b6b", "#3b1818"))

        # Audio alert for high-risk targets
        now = time.time()
        if self.audio_alerts_enabled and (now - self.last_alert_time > 1.5):
            self.last_alert_time = now
            if cls_name in ["mine_cylinder", "shipwreck"]:
                threading.Thread(target=lambda: winsound.Beep(980, 160), daemon=True).start()

    def insert_tree_row(self, record):
        if self.matches_filter(record):
            tree_val = (
                record["id"],
                record["class"].replace("_", " ").title(),
                f"{record['conf'] * 100:.1f}%",
                record["status"],
                record["time_frame"],
                record["lat"],
                record["lon"]
            )
            self.after(0, lambda v=tree_val: self.tree.insert("", 0, values=v))

    def matches_filter(self, record):
        if self.log_filter == "All Targets":
            return True
        elif self.log_filter == "Confirmed Only":
            return record.get("status") == "✅ Confirmed"
        elif self.log_filter == "Mines Only":
            return record.get("class") == "mine_cylinder"
        elif self.log_filter == "Shipwrecks Only":
            return record.get("class") == "shipwreck"
        return True

    def on_filter_changed(self, choice):
        self.log_filter = choice
        self.repopulate_tree()

    def repopulate_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for record in self.target_records.values():
            if self.matches_filter(record):
                tree_val = (
                    record["id"],
                    record["class"].replace("_", " ").title(),
                    f"{record['conf'] * 100:.1f}%",
                    record["status"],
                    record["time_frame"],
                    record["lat"],
                    record["lon"]
                )
                self.tree.insert("", 0, values=tree_val)

    def prune_tree(self):
        items = self.tree.get_children()
        if len(items) > 120:
            self.tree.delete(items[-1])

    # ==========================================
    # TARGET INSPECTION & OPERATOR WORKFLOW
    # ==========================================
    def on_tree_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return

        item = self.tree.item(selected[0])
        display_id = item['values'][0]
        self.selected_target_id = display_id

        record = self.target_records.get(display_id)
        if not record:
            return

        # Update title & metadata
        self.lbl_insp_title.configure(text=f"{record['id']} • {record['class'].replace('_', ' ').upper()}")
        meta_str = (
            f"Confidence:  {record['conf'] * 100:.1f}%\n"
            f"Frame/Time:  {record['time_frame']}\n"
            f"Coordinates: {record['lat']}, {record['lon']}\n"
            f"Depth:       {record['depth']} m\n"
            f"Logged At:   {record['timestamp']}"
        )
        self.lbl_insp_meta.configure(text=meta_str)

        # Set verification status & notes
        self.seg_verify.set(record.get("status", "❓ Pending"))
        self.entry_notes.delete(0, 'end')
        self.entry_notes.insert(0, record.get("notes", ""))

        # Show thumbnail
        snap_path = record.get("snapshot")
        if snap_path and os.path.exists(snap_path):
            try:
                pil_img = Image.open(snap_path)
                pil_img.thumbnail((260, 140))
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(pil_img.width, pil_img.height))
                self.lbl_insp_thumb.configure(image=ctk_img, text="")
                self.lbl_insp_thumb.image = ctk_img
            except Exception:
                self.lbl_insp_thumb.configure(image=None, text="[Image Load Error]")
        else:
            self.lbl_insp_thumb.configure(image=None, text="[No Snapshot Available]")

    def on_verification_changed(self, choice):
        if not self.selected_target_id:
            return
        record = self.target_records.get(self.selected_target_id)
        if record:
            record["status"] = choice
            self.repopulate_tree()

    def save_operator_notes(self):
        if not self.selected_target_id:
            return
        record = self.target_records.get(self.selected_target_id)
        if record:
            record["notes"] = self.entry_notes.get()
            record["status"] = self.seg_verify.get()
            self.repopulate_tree()
            self.btn_save_note.configure(text="✅ Notes Saved!", fg_color="#2b8a3e")
            self.after(2000, lambda: self.btn_save_note.configure(text="💾 Save Notes & Status", fg_color="#343a40"))

    def open_selected_snapshot(self):
        if not self.selected_target_id:
            return
        record = self.target_records.get(self.selected_target_id)
        if record and record.get("snapshot") and os.path.exists(record["snapshot"]):
            os.startfile(os.path.abspath(record["snapshot"]))

    def center_map_on_selected(self):
        if not self.selected_target_id or not hasattr(self, 'map_widget'):
            return
        record = self.target_records.get(self.selected_target_id)
        if record and record.get("lat") != "--" and record.get("lon") != "--":
            try:
                lat = float(record["lat"])
                lon = float(record["lon"])
                self.map_widget.set_position(lat, lon)
                self.map_widget.set_zoom(17)
            except ValueError:
                pass

    # ==========================================
    # TELEMETRY & GPS MAPPING
    # ==========================================
    def load_gps(self):
        file_path = filedialog.askopenfilename(filetypes=[("GPS Telemetry", "*.csv *.txt"), ("All Files", "*.*")])
        if not file_path:
            return

        self.gps_data = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.gps_data.append(row)

            self.lbl_gps_status.configure(text=f"GPS: {len(self.gps_data)} Points Loaded", text_color="#51cf66")

            if hasattr(self, 'map_overlay'):
                self.map_overlay.destroy()
                delattr(self, 'map_overlay')

            if hasattr(self, 'map_widget'):
                path_coords = []
                for row in self.gps_data:
                    try:
                        lat = float(row.get("latitude", row.get("lat", 0)))
                        lon = float(row.get("longitude", row.get("lon", 0)))
                        if lat != 0 and lon != 0:
                            path_coords.append((lat, lon))
                    except Exception:
                        pass

                if path_coords:
                    self.map_widget.set_path(path_coords)
                    self.map_widget.set_position(path_coords[0][0], path_coords[0][1])
                    self.map_widget.set_zoom(15)

        except Exception as e:
            self.lbl_gps_status.configure(text="GPS: File Read Error", text_color="#fa5252")

    def sync_telemetry_for_frame(self, frame_idx):
        if self.gps_data and frame_idx < len(self.gps_data):
            row = self.gps_data[frame_idx]
            lat = row.get("latitude", row.get("lat", "--"))
            lon = row.get("longitude", row.get("lon", "--"))
            depth = row.get("depth", row.get("alt", "--"))
            self.current_lat = lat
            self.current_lon = lon
            self.current_depth = depth
            self.after(0, lambda l=lat, lo=lon, d=depth: self.update_nav(l, lo, d))

    def update_nav(self, lat, lon, depth):
        self.lbl_lat.configure(text=f"Lat:   {lat}")
        self.lbl_lon.configure(text=f"Lon:   {lon}")
        self.lbl_depth.configure(text=f"Depth: {depth} m")

        if hasattr(self, 'map_widget') and lat != "--" and lon != "--":
            try:
                l_f = float(lat)
                lo_f = float(lon)
                self.map_widget.set_position(l_f, lo_f)
                if not hasattr(self, 'rov_marker') or self.rov_marker is None:
                    self.rov_marker = self.map_widget.set_marker(l_f, lo_f, text="ROV")
                else:
                    self.rov_marker.set_position(l_f, lo_f)
            except ValueError:
                pass

    # ==========================================
    # FRAME RENDERING
    # ==========================================
    def display_frame(self, bgr_frame):
        rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        w = max(10, self.lbl_video.winfo_width())
        h = max(10, self.lbl_video.winfo_height())
        if w > 10 and h > 10:
            img = Image.fromarray(rgb_frame)
            img.thumbnail((w, h), Image.Resampling.LANCZOS)
            photo = ctk.CTkImage(light_image=img, dark_image=img, size=(img.width, img.height))
            self.after(0, self.update_image, photo)

    def update_image(self, photo):
        self.lbl_video.configure(image=photo, text="")
        self.lbl_video.image = photo

    def update_graph(self):
        self.ax.clear()
        classes = list(self.stats.keys())
        counts = list(self.stats.values())
        colors = ['#ff6b6b', '#339af0', '#51cf66', '#fcc419', '#cc5de8']

        bars = self.ax.bar(classes, counts, color=colors[:len(classes)], width=0.6)
        self.ax.set_xticks(range(len(classes)))
        self.ax.set_xticklabels([c.replace("_", "\n").title() for c in classes], fontsize=8, color="#adb5bd")
        self.ax.tick_params(axis='y', labelsize=8, colors="#adb5bd")
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['bottom'].set_color('#343a40')
        self.ax.spines['left'].set_color('#343a40')

        self.fig.tight_layout()
        self.canvas.draw()
        total = sum(counts)
        self.lbl_total_dets.configure(text=f"Total Anomalies: {total}")

    # ==========================================
    # DATA EXPORT: PDF, CSV, GEOJSON
    # ==========================================
    def generate_report(self):
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas

            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(self.reports_dir, f"SONNET_Mission_Report_{timestamp}.pdf")

            c = canvas.Canvas(filename, pagesize=letter)
            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, 750, "SONNET: Mission Debrief & Acoustic Intelligence Report")

            c.setFont("Helvetica", 10)
            c.drawString(50, 730, f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            media_str = self.media_path if self.media_path else 'None'
            if len(media_str) > 70:
                media_str = "..." + media_str[-67:]
            c.drawString(50, 715, f"Media Source: {media_str}")

            y = 680
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y, "Detected Anomalies Distribution:")
            y -= 20
            c.setFont("Helvetica", 10)
            for cls, count in self.stats.items():
                if count > 0:
                    c.drawString(60, y, f"- {cls.replace('_', ' ').title()}: {count}")
                    y -= 15

            y -= 20
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y, "Verified Target Visual Log:")
            y -= 20

            records = list(self.target_records.values())
            for rec in records[-4:]:
                if y < 150:
                    c.showPage()
                    y = 750

                c.setFont("Helvetica-Bold", 10)
                c.drawString(50, y, f"Target: {rec['id']} - {rec['class'].title()} [{rec.get('status', 'Pending')}] (Conf: {rec['conf'] * 100:.1f}%)")
                c.setFont("Helvetica", 9)
                note_text = f" | Notes: {rec['notes']}" if rec.get('notes') else ""
                c.drawString(50, y - 12, f"Coords: {rec['lat']}, {rec['lon']} | Depth: {rec['depth']}m{note_text}")

                snap_path = rec.get("snapshot")
                if snap_path and os.path.exists(snap_path):
                    try:
                        c.drawImage(snap_path, 50, y - 110, width=95, height=95, preserveAspectRatio=True)
                    except Exception:
                        c.drawString(50, y - 40, "[Image Render Error]")
                y -= 130

            c.save()
            self.btn_report.configure(text="✅ PDF SAVED", fg_color="#2b8a3e")
            self.after(3000, lambda: self.btn_report.configure(text="📄 PDF", fg_color="#1c7ed6"))
            os.startfile(os.path.abspath(filename))
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to generate PDF: {e}")

    def export_csv(self):
        if not self.target_records:
            messagebox.showinfo("Export CSV", "No anomalies recorded yet.")
            return

        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_path = os.path.join(self.reports_dir, f"SONNET_Targets_{timestamp}.csv")

        try:
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Track ID", "Class", "Confidence", "Status", "Notes", "Time/Frame", "Latitude", "Longitude", "Depth (m)", "Logged Time", "Snapshot File"])
                for r in self.target_records.values():
                    writer.writerow([r['id'], r['class'], f"{r['conf']:.4f}", r.get('status', ''), r.get('notes', ''), r['time_frame'], r['lat'], r['lon'], r['depth'], r['timestamp'], r['snapshot']])

            self.btn_export_csv.configure(text="✅ CSV SAVED", fg_color="#2b8a3e")
            self.after(3000, lambda: self.btn_export_csv.configure(text="📊 CSV", fg_color="#343a40"))
            os.startfile(os.path.abspath(csv_path))
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export CSV: {e}")

    def export_geojson(self):
        valid_records = [r for r in self.target_records.values() if r.get('lat') != "--" and r.get('lon') != "--"]
        if not valid_records:
            messagebox.showinfo("Export GeoJSON", "No GPS-tagged anomalies recorded yet.\nLoad GPS telemetry before detecting.")
            return

        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        geojson_path = os.path.join(self.reports_dir, f"SONNET_Targets_{timestamp}.geojson")

        features = []
        for r in valid_records:
            try:
                lat = float(r['lat'])
                lon = float(r['lon'])
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [lon, lat]
                    },
                    "properties": {
                        "id": r['id'],
                        "class": r['class'],
                        "confidence": r['conf'],
                        "status": r.get('status', ''),
                        "notes": r.get('notes', ''),
                        "frame": r['time_frame'],
                        "depth": r['depth'],
                        "timestamp": r['timestamp'],
                        "snapshot": os.path.basename(r['snapshot']) if r['snapshot'] else ""
                    }
                })
            except Exception:
                pass

        geojson_doc = {
            "type": "FeatureCollection",
            "features": features
        }

        try:
            with open(geojson_path, 'w', encoding='utf-8') as f:
                json.dump(geojson_doc, f, indent=2)

            self.btn_export_geojson.configure(text="✅ GEOJSON", fg_color="#2b8a3e")
            self.after(3000, lambda: self.btn_export_geojson.configure(text="🌐 GEOJSON", fg_color="#343a40"))
            os.startfile(os.path.abspath(geojson_path))
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export GeoJSON: {e}")

    def open_snapshots(self):
        snap_win = ctk.CTkToplevel(self)
        snap_win.title("Snapshot Gallery")
        snap_win.geometry("740x520")
        try:
            snap_win.iconbitmap("assets/icon.ico")
        except Exception:
            pass

        scroll = ctk.CTkScrollableFrame(snap_win)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        images = [f for f in os.listdir(self.snapshots_dir) if f.endswith(('.png', '.jpg'))]
        if not images:
            ctk.CTkLabel(scroll, text="No snapshots captured yet.\nPlay a video or detect an image to record anomalies.", text_color="#adb5bd").pack(pady=60)
            return

        row, col = 0, 0
        for img_name in reversed(images):
            img_path = os.path.join(self.snapshots_dir, img_name)
            try:
                pil_img = Image.open(img_path)
                pil_img.thumbnail((150, 150))
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(pil_img.width, pil_img.height))

                btn = ctk.CTkButton(
                    scroll,
                    image=ctk_img,
                    text=img_name.split(".")[0],
                    compound="top",
                    command=lambda p=img_path: os.startfile(os.path.abspath(p)),
                    fg_color="#18191d",
                    hover_color="#1c7ed6"
                )
                btn.grid(row=row, column=col, padx=8, pady=8)
                col += 1
                if col > 3:
                    col = 0
                    row += 1
            except Exception:
                pass

    def on_close(self):
        self.is_playing = False
        self.stop_requested = True
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
        self.destroy()


if __name__ == "__main__":
    app = SonnetApp()
    app.mainloop()
