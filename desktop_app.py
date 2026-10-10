import tkinter as tk
from tkinter import filedialog, messagebox
import cv2
from ultralytics import YOLO
import threading

# Load YOLO model globally
model_path = "sonar_yolo11s_balanced_v1_best.pt"
try:
    model = YOLO(model_path)
except Exception as e:
    model = None
    print(f"Failed to load model: {e}")

class SonarApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Marine Sonar Real-Time Detector")
        self.root.geometry("450x280")
        
        self.video_path = None
        self.is_playing = False
        
        # UI Elements
        self.lbl_title = tk.Label(root, text="Real-Time Sonar Detection", font=("Helvetica", 16, "bold"))
        self.lbl_title.pack(pady=10)
        
        self.btn_select = tk.Button(root, text="Select Video File", command=self.select_video, width=30)
        self.btn_select.pack(pady=5)
        
        self.lbl_file = tk.Label(root, text="No video selected", fg="gray")
        self.lbl_file.pack(pady=5)
        
        self.lbl_conf = tk.Label(root, text="Confidence Threshold:")
        self.lbl_conf.pack()
        
        self.conf_slider = tk.Scale(root, from_=1, to=100, orient=tk.HORIZONTAL, length=250)
        self.conf_slider.set(25) # 0.25 default
        self.conf_slider.pack(pady=5)
        
        self.btn_play = tk.Button(root, text="Play Real-Time", command=self.play_video, width=30, bg="green", fg="white", font=("Helvetica", 10, "bold"))
        self.btn_play.pack(pady=10)
        
    def select_video(self):
        file_path = filedialog.askopenfilename(
            title="Select Video",
            filetypes=[("Video Files", "*.mp4 *.avi *.mov *.mkv"), ("All Files", "*.*")]
        )
        if file_path:
            self.video_path = file_path
            # Just show the file name instead of full path to save space
            filename = file_path.split("/")[-1] if "/" in file_path else file_path.split("\\")[-1]
            self.lbl_file.config(text=filename)
            
    def play_video(self):
        if not self.video_path:
            messagebox.showwarning("Warning", "Please select a video file first.")
            return
        if model is None:
            messagebox.showerror("Error", "YOLO model failed to load. Check model path.")
            return
            
        if self.is_playing:
            # Prevent opening multiple windows
            messagebox.showinfo("Info", "Video is already playing.")
            return
            
        self.is_playing = True
        
        # Run video processing in a background thread so the UI remains responsive (slider works)
        threading.Thread(target=self._run_inference_loop, daemon=True).start()
        
    def _run_inference_loop(self):
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            # Have to use root.after to safely show message box from background thread
            self.root.after(0, lambda: messagebox.showerror("Error", "Could not open video."))
            self.is_playing = False
            return
            
        window_name = "Sonar Detection (Press 'q' to close window)"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        
        while cap.isOpened() and self.is_playing:
            ret, frame = cap.read()
            if not ret:
                break # End of video
                
            # Get the real-time value from the slider!
            conf = self.conf_slider.get() / 100.0
            
            # Run YOLO inference
            results = model(frame, conf=conf, verbose=False)
            res_frame = results[0].plot()
            
            # Show the result in the OpenCV window
            cv2.imshow(window_name, res_frame)
            
            # Wait 1 ms, and exit if 'q' is pressed
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
        cap.release()
        cv2.destroyAllWindows()
        self.is_playing = False

if __name__ == "__main__":
    root = tk.Tk()
    app = SonarApp(root)
    root.mainloop()
