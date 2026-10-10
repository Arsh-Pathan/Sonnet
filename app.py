import gradio as gr
from ultralytics import YOLO
import cv2
import numpy as np
from PIL import Image
import tempfile
import os

# Load the trained model
model_path = "sonar_yolo11s_balanced_v1_best.pt"
try:
    model = YOLO(model_path)
except Exception as e:
    print(f"Error loading model: {e}")
    model = None

def predict_image(image, conf_threshold):
    if model is None or image is None:
        return None
    
    # Run inference
    results = model(image, conf=conf_threshold)
    res_plotted = results[0].plot()
    
    # Convert BGR back to RGB for displaying with Gradio/PIL
    res_plotted_rgb = cv2.cvtColor(res_plotted, cv2.COLOR_BGR2RGB)
    return Image.fromarray(res_plotted_rgb)

def predict_video(video_path, conf_threshold):
    if model is None or video_path is None:
        return None
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None
    
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0 or np.isnan(fps):
        fps = 25.0
        
    temp_dir = tempfile.mkdtemp()
    out_path = os.path.join(temp_dir, 'output.mp4')
    
    # mp4v codec is widely compatible enough for writing, Gradio uses browser to play
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(out_path, fourcc, fps, (width, height))
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        # Inference on each frame
        results = model(frame, conf=conf_threshold, verbose=False)
        res_plotted = results[0].plot()
        out.write(res_plotted)
        
    cap.release()
    out.release()
    
    return out_path

with gr.Blocks(title="Marine Sonar Object Detection") as interface:
    gr.Markdown("# Marine Sonar Object Detection")
    gr.Markdown("Upload an image or a video to detect objects using the trained YOLO model (`sonar_yolo11s_balanced_v1_best.pt`).")
    
    with gr.Tabs():
        with gr.TabItem("Image Detection"):
            with gr.Row():
                with gr.Column():
                    img_input = gr.Image(type="pil", label="Upload Sonar Image")
                    img_conf = gr.Slider(minimum=0.01, maximum=1.0, value=0.25, step=0.01, label="Confidence Threshold")
                    img_btn = gr.Button("Detect in Image", variant="primary")
                with gr.Column():
                    img_output = gr.Image(type="pil", label="Detection Result")
            img_btn.click(fn=predict_image, inputs=[img_input, img_conf], outputs=img_output)
            
        with gr.TabItem("Video Detection"):
            with gr.Row():
                with gr.Column():
                    vid_input = gr.Video(label="Upload Sonar Video")
                    vid_conf = gr.Slider(minimum=0.01, maximum=1.0, value=0.25, step=0.01, label="Confidence Threshold")
                    vid_btn = gr.Button("Detect in Video", variant="primary")
                with gr.Column():
                    vid_output = gr.Video(label="Detection Result")
            vid_btn.click(fn=predict_video, inputs=[vid_input, vid_conf], outputs=vid_output)

if __name__ == "__main__":
    print(f"Starting Gradio app using model: {model_path}")
    interface.launch()
