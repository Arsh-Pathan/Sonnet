import urllib.request
import zipfile
import os
import cv2
import glob

def main():
    zip_url = "https://zenodo.org/api/records/7922705/files/Marine_PULSE.zip/content"
    zip_path = "data/videos/Marine_PULSE.zip"
    extract_dir = "data/videos/Marine_PULSE"
    out_video = "data/videos/marine_pulse_pipeline_video.mp4"

    print("Downloading Marine_PULSE dataset (64MB)...")
    urllib.request.urlretrieve(zip_url, zip_path)
    
    print("Extracting images...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
        
    # Find all images
    images = glob.glob(os.path.join(extract_dir, '**', '*.jpg'), recursive=True)
    images += glob.glob(os.path.join(extract_dir, '**', '*.png'), recursive=True)
    images.sort()
    
    if not images:
        print("No images found.")
        return
        
    print(f"Found {len(images)} images. Creating video...")
    
    # Read first image to get dimensions
    first_img = cv2.imread(images[0])
    height, width, layers = first_img.shape
    
    video = cv2.VideoWriter(out_video, cv2.VideoWriter_fourcc(*'mp4v'), 2, (width, height))
    
    for idx, img_path in enumerate(images):
        img = cv2.imread(img_path)
        if img is not None:
            img = cv2.resize(img, (width, height)) # ensure uniform size
            video.write(img)
            if idx % 50 == 0:
                print(f"Processed {idx}/{len(images)} images")
                
    video.release()
    print(f"Successfully created video: {out_video}")
    
    # Cleanup
    os.remove(zip_path)

if __name__ == "__main__":
    main()
