import pyxtf
import numpy as np
import cv2
import sys

def create_scrolling_video(xtf_path, out_path, start_ping, num_pings):
    print(f"Reading {xtf_path} for {out_path}...")
    try:
        (fh, p) = pyxtf.xtf_read(xtf_path)
    except Exception:
        pass # Handle pyxtf quirks
    
    sonar_packets = p[pyxtf.XTFHeaderType.sonar]
    
    end_ping = min(start_ping + num_pings, len(sonar_packets))
    if start_ping >= end_ping:
        return
        
    print(f"Extracting pings {start_ping} to {end_ping}...")
    
    port_data = []
    stbd_data = []
    
    for i in range(start_ping, end_ping):
        pkt = sonar_packets[i]
        if len(pkt.data) >= 2:
            port_data.append(pkt.data[0])
            stbd_data.append(pkt.data[1])
            
    if not port_data:
        return
        
    port_img = np.vstack(port_data)
    stbd_img = np.vstack(stbd_data)
    port_img = np.fliplr(port_img)
    combined = np.hstack((port_img, stbd_img))
    
    combined = combined.astype(np.float32)
    p2, p98 = np.percentile(combined, (2, 98))
    if p98 > p2:
        combined = np.clip((combined - p2) / (p98 - p2), 0, 1)
    combined = (combined * 255).astype(np.uint8)
    
    bgr = cv2.cvtColor(combined, cv2.COLOR_GRAY2BGR)
    height, width = bgr.shape[:2]
    window_h = 500
    
    out = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*'mp4v'), 24, (width, window_h))
    
    step = 5  
    for y in range(0, height - window_h, step):
        frame = bgr[y : y + window_h, :]
        out.write(frame)
        
    out.release()
    print(f"Saved {out_path}!")

if __name__ == "__main__":
    create_scrolling_video('data/survey1/data.xtf', 'data/survey_video_alpha.mp4', 4000, 4000)
    create_scrolling_video('data/survey1/data.xtf', 'data/survey_video_bravo.mp4', 8000, 4000)
    create_scrolling_video('data/survey1/data.xtf', 'data/survey_video_charlie.mp4', 12000, 4000)
    create_scrolling_video('data/survey1/data.xtf', 'data/survey_video_delta.mp4', 16000, 4000)
    create_scrolling_video('data/survey1/data.xtf', 'data/survey_video_echo.mp4', 20000, 4000)
