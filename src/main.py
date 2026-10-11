import customtkinter as ctk
from tkinter import filedialog, ttk
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

# Initialize customtkinter settings
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# Load YOLO model
model_path = "models/sonar_yolo11s_balanced_v1_best.pt"
try:
    model = YOLO(model_path)
except Exception as e:
    model = None
    print("Model load error:", e)

class SonnetApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("SONNET - Sonar Target Detection")
        self.geometry("1280x800")
        try:
            self.iconbitmap("assets/icon.ico")
        except:
            pass
        
        self.media_path = None
        self.is_playing = False
        self.cap = None
        self.is_image = False
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # Keep track of detection counts for the analytics graph
        self.stats = {"pipeline": 0, "shipwreck": 0, "mine_cylinder": 0, "ghost_net": 0, "crab_pot": 0}
        
        # Snapshots dir
        self.snapshots_dir = "snapshots"
        os.makedirs(self.snapshots_dir, exist_ok=True)
        
        # Performance/Dashboard data
        self.start_time = 0
        self.frames_processed = 0
        
        self.setup_ui()
        
    def setup_ui(self):
        self.topbar = ctk.CTkFrame(self, height=50, corner_radius=0, fg_color="#18191d")
        self.topbar.grid(row=0, column=0, columnspan=3, sticky="ew")
        
        try:
            logo_img = Image.open("assets/logo.png")
            # Calculate aspect ratio to fit within 30px height
            aspect = logo_img.width / logo_img.height
            new_w = int(30 * aspect)
            self.ctk_logo = ctk.CTkImage(light_image=logo_img, dark_image=logo_img, size=(new_w, 30))
            self.lbl_logo = ctk.CTkLabel(self.topbar, text=" SONNET", image=self.ctk_logo, compound="left", text_color="#3a7ebf", font=ctk.CTkFont(size=20, weight="bold"))
        except Exception as e:
            self.lbl_logo = ctk.CTkLabel(self.topbar, text="🌊 SONNET", text_color="#3a7ebf", font=ctk.CTkFont(size=20, weight="bold"))
            
        self.lbl_logo.pack(side="left", padx=20, pady=10)
        
        self.btn_snapshots = ctk.CTkButton(self.topbar, text="🖼️ SNAPSHOT GALLERY", width=140, command=self.open_snapshots, fg_color="#b85c14", hover_color="#d97a32")
        self.btn_snapshots.pack(side="left", padx=30)
        
        self.btn_report = ctk.CTkButton(self.topbar, text="📄 EXPORT REPORT", width=140, command=self.generate_report, fg_color="#3a7ebf", hover_color="#285a8a")
        self.btn_report.pack(side="left", padx=10)
        
        self.btn_load_gps = ctk.CTkButton(self.topbar, text="LOAD GPS", width=100, command=self.load_gps, fg_color="#444466")
        self.btn_load_gps.pack(side="right", padx=10)
        
        self.btn_load = ctk.CTkButton(self.topbar, text="LOAD MEDIA", width=120, command=self.load_media)
        self.btn_load.pack(side="right", padx=10)
        
        self.btn_play = ctk.CTkButton(self.topbar, text="▶ PLAY / DETECT", width=140, command=self.toggle_play, fg_color="#2b8a3e")
        self.btn_play.pack(side="right", padx=10)

        # --- LEFT SIDEBAR ---
        self.left_sidebar = ctk.CTkFrame(self, width=280, corner_radius=0, fg_color="#121316")
        self.left_sidebar.grid(row=1, column=0, sticky="nsew", padx=1, pady=1)
        
        ctk.CTkLabel(self.left_sidebar, text="MODEL CONTROLS", font=ctk.CTkFont(size=11, weight="bold"), text_color="#aaaaaa").pack(anchor="w", padx=15, pady=(15, 5))
        
        ctk.CTkLabel(self.left_sidebar, text="Confidence Threshold", text_color="#cccccc", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=15)
        self.conf_slider = ctk.CTkSlider(self.left_sidebar, from_=0.01, to=1.0, button_color="#555555", progress_color="#3a7ebf")
        self.conf_slider.set(0.25)
        self.conf_slider.pack(fill="x", padx=15, pady=5)

        ctk.CTkLabel(self.left_sidebar, text="IoU (NMS) Threshold", text_color="#cccccc", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=15)
        self.iou_slider = ctk.CTkSlider(self.left_sidebar, from_=0.05, to=0.95, button_color="#555555", progress_color="#b85c14")
        self.iou_slider.set(0.45)
        self.iou_slider.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(self.left_sidebar, text="Max Detections", text_color="#cccccc", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=15)
        self.max_det_slider = ctk.CTkSlider(self.left_sidebar, from_=1, to=300, button_color="#555555", progress_color="#b85c14")
        self.max_det_slider.set(100)
        self.max_det_slider.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(self.left_sidebar, text="NAVIGATION (SYNCED)", font=ctk.CTkFont(size=11, weight="bold"), text_color="#aaaaaa").pack(anchor="w", padx=15, pady=(30, 5))
        self.lbl_lat = ctk.CTkLabel(self.left_sidebar, text="Latitude:         -- N", text_color="#888888", font=ctk.CTkFont(size=11))
        self.lbl_lat.pack(anchor="w", padx=15)
        self.lbl_lon = ctk.CTkLabel(self.left_sidebar, text="Longitude:       -- W", text_color="#888888", font=ctk.CTkFont(size=11))
        self.lbl_lon.pack(anchor="w", padx=15)
        self.lbl_depth = ctk.CTkLabel(self.left_sidebar, text="Depth:                   -- m", text_color="#888888", font=ctk.CTkFont(size=11))
        self.lbl_depth.pack(anchor="w", padx=15)
        
        self.lbl_gps_status = ctk.CTkLabel(self.left_sidebar, text="No GPS File Loaded", text_color="#aa4444", font=ctk.CTkFont(size=10))
        self.lbl_gps_status.pack(anchor="w", padx=15, pady=5)

        # --- CENTER VIEW (VIDEO/IMAGE) ---
        self.center_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#000000")
        self.center_frame.grid(row=1, column=1, sticky="nsew", padx=1, pady=1)
        
        self.lbl_video_header = ctk.CTkLabel(self.center_frame, text=" Sidescan View (No Media)", text_color="#dddddd", font=ctk.CTkFont(size=12, weight="bold"), anchor="w")
        self.lbl_video_header.pack(fill="x", padx=10, pady=5)
        
        self.lbl_video = ctk.CTkLabel(self.center_frame, text="NO SIGNAL / NO MEDIA LOADED", text_color="#555555", font=ctk.CTkFont(size=16, weight="bold"))
        self.lbl_video.pack(expand=True, fill="both")
        
        # --- RIGHT SIDEBAR ---
        self.right_sidebar = ctk.CTkFrame(self, width=320, corner_radius=0, fg_color="#121316")
        self.right_sidebar.grid(row=1, column=2, sticky="nsew", padx=1, pady=1)
        self.right_sidebar.pack_propagate(False) 
        
        ctk.CTkLabel(self.right_sidebar, text="LOCATION MAP", font=ctk.CTkFont(size=11, weight="bold"), text_color="#aaaaaa").pack(anchor="w", padx=15, pady=(15, 10))
        
        try:
            import tkintermapview
            self.map_widget = tkintermapview.TkinterMapView(self.right_sidebar, width=280, height=350, corner_radius=0)
            self.map_widget.pack(padx=15, pady=5)
            self.map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}&s=Ga", max_zoom=22)
            self.map_widget.set_position(0, 0)
            self.map_widget.set_zoom(1)
            
            # Map Overlay to hide random location
            self.map_overlay = ctk.CTkFrame(self.right_sidebar, width=280, height=350, fg_color="#0a1220")
            self.map_overlay.place(in_=self.map_widget, relx=0, rely=0, relwidth=1, relheight=1)
            ctk.CTkLabel(self.map_overlay, text="No Map Data Provided.\nLoad GPS to view.", text_color="#888888").place(relx=0.5, rely=0.5, anchor="center")
        except ImportError:
            self.map_area = ctk.CTkFrame(self.right_sidebar, width=280, height=350, fg_color="#0a1220")
            self.map_area.pack(padx=15, pady=5)
            ctk.CTkLabel(self.map_area, text="Map unavailable.", text_color="#ff5555").place(relx=0.5, rely=0.5, anchor="center")

        # --- BOTTOM LOG & ANALYTICS ---
        self.bottom_frame = ctk.CTkFrame(self, height=250, corner_radius=0, fg_color="#121316")
        self.bottom_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=1, pady=1)
        self.bottom_frame.grid_columnconfigure(0, weight=6) # Target log gets 60%
        self.bottom_frame.grid_columnconfigure(1, weight=4) # Graph gets 40%
        self.bottom_frame.grid_rowconfigure(0, weight=1)
        
        # Target Log & Dashboard Data
        self.log_frame = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
        self.log_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)
        
        self.log_header_frame = ctk.CTkFrame(self.log_frame, fg_color="transparent")
        self.log_header_frame.pack(fill="x")
        ctk.CTkLabel(self.log_header_frame, text="● Target Log", font=ctk.CTkFont(size=12, weight="bold"), text_color="#3a7ebf").pack(side="left")
        self.lbl_fps = ctk.CTkLabel(self.log_header_frame, text="FPS: 0.0", font=ctk.CTkFont(size=10), text_color="#888888")
        self.lbl_fps.pack(side="right", padx=10)
        self.lbl_total_dets = ctk.CTkLabel(self.log_header_frame, text="Total Anomalies: 0", font=ctk.CTkFont(size=10), text_color="#888888")
        self.lbl_total_dets.pack(side="right", padx=10)
        
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#121316", foreground="#cccccc", fieldbackground="#121316", borderwidth=0, rowheight=25)
        style.configure("Treeview.Heading", background="#1a1c22", foreground="#aaaaaa", borderwidth=0, font=("Helvetica", 9, "bold"))
        
        cols = ("TRACK ID", "CLASS", "CONFIDENCE", "TIME/FRAME")
        self.tree = ttk.Treeview(self.log_frame, columns=cols, show="headings", height=6)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=150, anchor="w")
        self.tree.pack(fill="both", expand=True, pady=5)
        
        # Analytics Graph
        self.graph_frame = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
        self.graph_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=5)
        
        ctk.CTkLabel(self.graph_frame, text="📊 Anomaly Distribution", font=ctk.CTkFont(size=12, weight="bold"), text_color="#3a7ebf").pack(anchor="w")
        
        # Setup Matplotlib Figure
        plt.style.use('dark_background')
        self.fig, self.ax = plt.subplots(figsize=(4, 2.5), dpi=80)
        self.fig.patch.set_facecolor('#121316')
        self.ax.set_facecolor('#121316')
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self.update_graph()

        self.target_counter = 0

    def generate_report(self):
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            import datetime
            
            os.makedirs("reports", exist_ok=True)
            filename = f"reports/SONNET_Mission_Report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            c = canvas.Canvas(filename, pagesize=letter)
            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, 750, "SONNET: Mission Debrief Report")
            
            c.setFont("Helvetica", 10)
            c.drawString(50, 730, f"Date/Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            media_str = self.media_path if self.media_path else 'None'
            if len(media_str) > 70: media_str = "..." + media_str[-67:]
            c.drawString(50, 715, f"Media Source: {media_str}")
            
            y = 680
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y, "Detected Anomalies Summary:")
            y -= 20
            c.setFont("Helvetica", 10)
            for cls, count in self.stats.items():
                if count > 0:
                    c.drawString(60, y, f"- {cls.replace('_', ' ').title()}: {count}")
                    y -= 15
                    
            y -= 20
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y, "Recent Snapshot Log:")
            y -= 20
            
            images = [f for f in os.listdir(self.snapshots_dir) if f.endswith(('.png', '.jpg'))]
            images.sort(reverse=True)
            
            for img_name in images[:4]: 
                if y < 150:
                    c.showPage()
                    y = 750
                
                img_path = os.path.join(self.snapshots_dir, img_name)
                c.setFont("Helvetica", 10)
                c.drawString(50, y, f"Snapshot: {img_name}")
                try:
                    c.drawImage(img_path, 50, y - 110, width=100, height=100, preserveAspectRatio=True)
                except Exception as e:
                    c.drawString(50, y - 20, "[Image Load Error]")
                y -= 130
                
            c.save()
            
            self.btn_report.configure(text="✅ SAVED TO /reports", fg_color="#2b8a3e")
            self.after(3000, lambda: self.btn_report.configure(text="📄 EXPORT REPORT", fg_color="#3a7ebf"))
            os.startfile(os.path.abspath(filename))
        except Exception as e:
            print("Report error:", e)

    def open_snapshots(self):
        snap_win = ctk.CTkToplevel(self)
        snap_win.title("Snapshot Gallery")
        snap_win.geometry("700x500")
        try:
            snap_win.iconbitmap("assets/icon.ico")
        except:
            pass
        
        scroll = ctk.CTkScrollableFrame(snap_win)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        images = [f for f in os.listdir(self.snapshots_dir) if f.endswith(('.png', '.jpg'))]
        if not images:
            ctk.CTkLabel(scroll, text="No snapshots captured yet.\nPlay a video or detect an image to capture anomalies.", text_color="#aaaaaa").pack(pady=50)
            return
            
        row, col = 0, 0
        for img_name in reversed(images): # newest first
            img_path = os.path.join(self.snapshots_dir, img_name)
            try:
                pil_img = Image.open(img_path)
                pil_img.thumbnail((150, 150))
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(pil_img.width, pil_img.height))
                
                # Button to open the image using default OS viewer
                btn = ctk.CTkButton(scroll, image=ctk_img, text=img_name.split("_")[0], compound="top", 
                                    command=lambda p=img_path: os.startfile(os.path.abspath(p)), fg_color="#18191d", hover_color="#3a7ebf")
                btn.grid(row=row, column=col, padx=10, pady=10)
                
                col += 1
                if col > 3:
                    col = 0
                    row += 1
            except Exception as e:
                pass
        
    def update_graph(self):
        self.ax.clear()
        classes = list(self.stats.keys())
        counts = list(self.stats.values())
        
        colors = ['#ff9999','#66b3ff','#99ff99','#ffcc99','#c2c2f0']
        
        self.ax.bar(classes, counts, color=colors[:len(classes)])
        self.ax.set_xticks(range(len(classes)))
        self.ax.set_xticklabels([c.replace("_", "\n").title() for c in classes], fontsize=8)
        self.ax.tick_params(axis='y', labelsize=8)
        
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        
        self.fig.tight_layout()
        self.canvas.draw()
        
        # Update total label
        total = sum(counts)
        self.lbl_total_dets.configure(text=f"Total Anomalies: {total}")

    def load_gps(self):
        file_path = filedialog.askopenfilename(filetypes=[("GPS Telemetry", "*.csv *.txt"), ("All Files", "*.*")])
        if file_path:
            self.gps_data = []
            try:
                import csv
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        self.gps_data.append(row)
                self.lbl_gps_status.configure(text=f"Loaded {len(self.gps_data)} points", text_color="#44aa44")
                
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
                        except:
                            pass
                    if path_coords:
                        self.map_widget.set_path(path_coords)
                        self.map_widget.set_position(path_coords[0][0], path_coords[0][1])
                        self.map_widget.set_zoom(15)
                        
            except Exception as e:
                self.lbl_gps_status.configure(text="Error loading GPS", text_color="#ff4444")
                
    def update_nav(self, lat, lon, depth):
        self.lbl_lat.configure(text=f"Latitude:         {lat}")
        self.lbl_lon.configure(text=f"Longitude:       {lon}")
        self.lbl_depth.configure(text=f"Depth:                   {depth}")
        
        if hasattr(self, 'map_widget') and lat != "--" and lon != "--":
            try:
                l_f = float(lat)
                lo_f = float(lon)
                self.map_widget.set_position(l_f, lo_f)
                self.map_widget.set_zoom(15)
                self.map_widget.delete_all_marker()
                self.map_widget.set_marker(l_f, lo_f, text="ROV")
            except ValueError:
                pass

    def load_media(self):
        file_path = filedialog.askopenfilename(filetypes=[("Media Files", "*.mp4 *.avi *.mkv *.mov *.jpg *.jpeg *.png *.xtf"), ("All Files", "*.*")])
        if file_path:
            self.media_path = file_path
            filename = os.path.basename(file_path)
            self.lbl_video_header.configure(text=f" Sidescan View - {filename}")
            
            ext = os.path.splitext(filename)[1].lower()
            if ext in ['.jpg', '.jpeg', '.png']:
                self.is_image = True
                self.btn_play.configure(text="▶ DETECT IMAGE")
            elif ext == '.xtf':
                self.is_image = False
                self.btn_play.configure(text="▶ PLAY XTF")
            else:
                self.is_image = False
                self.btn_play.configure(text="▶ PLAY VIDEO")
            
    def toggle_play(self):
        if not self.media_path:
            return
            
        if self.is_image:
            threading.Thread(target=self.process_image, daemon=True).start()
        elif self.media_path.lower().endswith('.xtf'):
            if not self.is_playing:
                self.is_playing = True
                self.btn_play.configure(text="⏸ PAUSE XTF", fg_color="#c92a2a")
                threading.Thread(target=self.play_xtf_loop, daemon=True).start()
            else:
                self.is_playing = False
                self.btn_play.configure(text="▶ PLAY XTF", fg_color="#2b8a3e")
        else:
            if not self.is_playing:
                self.is_playing = True
                self.btn_play.configure(text="⏸ PAUSE VIDEO", fg_color="#c92a2a")
                self.cap = cv2.VideoCapture(self.media_path)
                threading.Thread(target=self.play_loop, daemon=True).start()
            else:
                self.is_playing = False
                self.btn_play.configure(text="▶ PLAY VIDEO", fg_color="#2b8a3e")
                
    def process_image(self):
        frame = cv2.imread(self.media_path)
        if frame is None:
            return
            
        conf = self.conf_slider.get()
        iou = self.iou_slider.get()
        max_det = int(self.max_det_slider.get())
        if model is not None:
            results = model(frame, conf=conf, iou=iou, max_det=max_det, verbose=False)
            res_frame = results[0].plot()
            self.process_detections(results[0], "Image", res_frame, is_video=False)
        else:
            res_frame = frame
            
        self.display_frame(res_frame)
        
    def play_loop(self):
        frame_idx = 0
        self.start_time = time.time()
        self.frames_processed = 0
        
        if not hasattr(self, 'custom_tracker'):
            self.custom_tracker = [] 
            self.global_id_counter = 0
        else:
            self.custom_tracker = [] # reset tracker for new playback loop
        
        while self.is_playing and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                break
                
            frame_idx += 1
            self.frames_processed += 1
            conf = self.conf_slider.get()
            iou = self.iou_slider.get()
            max_det = int(self.max_det_slider.get())
            
            # FPS Calculation
            elapsed = time.time() - self.start_time
            if elapsed > 0:
                fps = self.frames_processed / elapsed
                self.after(0, lambda f=fps: self.lbl_fps.configure(text=f"FPS: {f:.1f}"))
            
            # Sync GPS
            if hasattr(self, 'gps_data') and self.gps_data and frame_idx < len(self.gps_data):
                row = self.gps_data[frame_idx]
                lat = row.get("latitude", row.get("lat", "--"))
                lon = row.get("longitude", row.get("lon", "--"))
                depth = row.get("depth", row.get("alt", "--"))
                self.after(0, lambda l=lat, lo=lon, d=depth: self.update_nav(l, lo, d))
            
            if model is not None:
                results = model.track(frame, conf=conf, iou=iou, max_det=max_det, persist=True, tracker="bytetrack.yaml", verbose=False)
                res_frame = results[0].plot(conf=False) 
                
                self.process_detections(results[0], f"F-{frame_idx}", res_frame, is_video=True)
            else:
                res_frame = frame
                
            self.display_frame(res_frame)
            cv2.waitKey(33)
            
        self.is_playing = False
        self.after(0, lambda: self.btn_play.configure(text="▶ PLAY VIDEO", fg_color="#2b8a3e"))
        if self.cap:
            self.cap.release()
            self.cap = None
            
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
            
            if not hasattr(self, 'custom_tracker'):
                self.custom_tracker = [] 
                self.global_id_counter = 0
            else:
                self.custom_tracker = [] 
                
            for i in range(0, ping_count, frame_size):
                if not self.is_playing:
                    break
                    
                chunk = sonar_packets[i:i+frame_size]
                
                port_data = []
                stbd_data = []
                for packet in chunk:
                    if len(packet.data) >= 2:
                        port_data.append(packet.data[0])
                        stbd_data.append(packet.data[1])
                
                if not port_data: continue
                
                port_img = np.vstack(port_data)
                stbd_img = np.vstack(stbd_data)
                port_img = np.fliplr(port_img)
                combined = np.hstack((port_img, stbd_img))
                
                combined = combined.astype(np.float32)
                p2, p98 = np.percentile(combined, (2, 98))
                if p98 > p2:
                    combined = np.clip((combined - p2) / (p98 - p2), 0, 1)
                combined = (combined * 255).astype(np.uint8)
                
                bgr_frame = cv2.cvtColor(combined, cv2.COLOR_GRAY2BGR)
                
                self.frames_processed += 1
                conf = self.conf_slider.get()
                iou = self.iou_slider.get()
                max_det = int(self.max_det_slider.get())
                
                elapsed = time.time() - self.start_time
                if elapsed > 0:
                    fps = self.frames_processed / elapsed
                    self.after(0, lambda f=fps: self.lbl_fps.configure(text=f"FPS: {f:.1f}"))
                
                if model is not None:
                    results = model.track(bgr_frame, conf=conf, iou=iou, max_det=max_det, persist=True, tracker="bytetrack.yaml", verbose=False)
                    res_frame = results[0].plot(conf=False)
                    self.process_detections(results[0], f"XTF-{i//frame_size}", res_frame, is_video=True)
                else:
                    res_frame = bgr_frame
                    
                self.display_frame(res_frame)
                time.sleep(0.1)
                
        except Exception as e:
            print("XTF Playback Error:", e)
            
        self.is_playing = False
        self.after(0, lambda: self.btn_play.configure(text="▶ PLAY XTF", fg_color="#2b8a3e"))

    def process_detections(self, result, time_frame, res_frame, is_video=False):
        boxes = result.boxes
        if len(boxes) > 0:
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
                coords = box.xyxy[0].cpu().numpy() # [x1, y1, x2, y2]
                
                is_new = True
                assigned_id = None
                
                if is_video:
                    cx1, cy1 = (coords[0] + coords[2]) / 2, (coords[1] + coords[3]) / 2
                    w1, h1 = coords[2] - coords[0], coords[3] - coords[1]
                    
                    for t in self.custom_tracker:
                        if t['class'] == cls_name:
                            cx2, cy2 = t['center']
                            dist = ((cx1 - cx2)**2 + (cy1 - cy2)**2)**0.5
                            
                            # If center distance is within 2x the object's largest dimension or 100px, it's the same object
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
                        self.custom_tracker.append({'class': cls_name, 'center': (cx1, cy1), 'coords': coords, 'frames_since': 0, 'id': assigned_id})
                
                if not is_video or is_new:
                    self.target_counter += 1
                    display_id = f"TRK-{assigned_id:03d}" if assigned_id else f"TRK-{self.target_counter:03d}"
                    val = (display_id, cls_name, f"{conf_val:.2f}", time_frame)
                    self.after(0, lambda v=val: self.tree.insert("", 0, values=v))
                    
                    if cls_name in self.stats:
                        self.stats[cls_name] += 1
                        updated_stats = True
                        
                    # Crop and save snapshot
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
                
            self.after(0, self.prune_tree)
            if updated_stats:
                self.after(0, self.update_graph)
            
    def display_frame(self, bgr_frame):
        rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        w, h = self.lbl_video.winfo_width(), self.lbl_video.winfo_height()
        if w > 10 and h > 10:
            img = Image.fromarray(rgb_frame)
            img.thumbnail((w, h), Image.Resampling.LANCZOS)
            photo = ctk.CTkImage(light_image=img, dark_image=img, size=(img.width, img.height))
            self.after(0, self.update_image, photo)
            
    def prune_tree(self):
        items = self.tree.get_children()
        if len(items) > 50: 
            self.tree.delete(items[-1])
            
    def update_image(self, photo):
        self.lbl_video.configure(image=photo, text="")
        self.lbl_video.image = photo

if __name__ == "__main__":
    app = SonnetApp()
    app.mainloop()
