import urllib.request
import zipfile
import os
import cv2
import glob

def make_video(zip_url, zip_path, extract_dir, out_video, title):
    print(f"Downloading {title} dataset...")
    urllib.request.urlretrieve(zip_url, zip_path)
    
    print(f"Extracting {title} images...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
        
    images = glob.glob(os.path.join(extract_dir, '**', '*.jpg'), recursive=True)
    images += glob.glob(os.path.join(extract_dir, '**', '*.png'), recursive=True)
    images += glob.glob(os.path.join(extract_dir, '**', '*.bmp'), recursive=True)
    images.sort()
    
    if not images:
        print(f"No images found for {title}.")
        return
        
    print(f"Found {len(images)} images. Creating {title} video...")
    
    first_img = cv2.imread(images[0])
    height, width = first_img.shape[:2]
    
    video = cv2.VideoWriter(out_video, cv2.VideoWriter_fourcc(*'mp4v'), 2, (width, height))
    
    for idx, img_path in enumerate(images):
        img = cv2.imread(img_path)
        if img is not None:
            img = cv2.resize(img, (width, height)) 
            video.write(img)
            
    video.release()
    print(f"Successfully created video: {out_video}")
    
    # Cleanup
    os.remove(zip_path)

if __name__ == "__main__":
    # Figshare: Mine Detection (2017 portion)
    make_video(
        "https://ndownloader.figshare.com/files/43169005",
        "data/videos/MineDetection2017.zip",
        "data/videos/MineDetection2017",
        "data/videos/mine_detection_video.mp4",
        "Sea Mines"
    )
    
    print("All additional videos created successfully!")
