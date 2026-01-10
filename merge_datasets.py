import os
import shutil
import hashlib
import random
from tqdm import tqdm

# --- CONFIGURATION ---
SOURCE_DIR = "raw_datasets"
OUTPUT_DIR = "FINAL_DATASET"
SPLIT_RATIOS = (0.8, 0.1, 0.1) # 80% Train, 10% Val, 10% Test

# The 4 Standard Output Classes we want
CLASSES = ["Non_Demented", "Very_Mild_Demented", "Mild_Demented", "Moderate_Demented"]

# MAPPING: Matches your specific folder names to the Standard Classes
CLASS_MAPPING = {
    # Variation 1: Standard / CamelCase (seen in Alzheimer_s Dataset, Oasis 2)
    "NonDemented": "Non_Demented",
    "VeryMildDemented": "Very_Mild_Demented",
    "MildDemented": "Mild_Demented",
    "ModerateDemented": "Moderate_Demented",

    # Variation 2: Snake Case (seen in MRI/train_images)
    "non_demented": "Non_Demented",
    "very_mild_demented": "Very_Mild_Demented",
    "mild_dementia": "Mild_Demented",
    "moderated_dementia": "Moderate_Demented", # Note: 'moderated' typo in source handled here

    # Variation 3: Spaces (seen in Oasis 1)
    "Non Demented": "Non_Demented",
    "Very mild Dementia": "Very_Mild_Demented",
    "Mild Dementia": "Mild_Demented",
    "Moderate Dementia": "Moderate_Demented",
}

def get_file_hash(filepath):
    """Calculates MD5 hash to find identical images."""
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def step_1_merge_and_deduplicate():
    print("--- STEP 1: Merging and Deduplicating ---")
    
    if os.path.exists(OUTPUT_DIR):
        print(f"Removing existing {OUTPUT_DIR}...")
        shutil.rmtree(OUTPUT_DIR)
    
    # Create temp master folder to hold merged images before splitting
    master_dir = os.path.join(OUTPUT_DIR, "TEMP_MASTER")
    
    unique_hashes = set()
    duplicate_count = 0
    total_images = 0

    # os.walk automatically goes deep into subfolders (train, test, etc.)
    for root, dirs, files in os.walk(SOURCE_DIR):
        
        # 'root' is the current folder path. 'os.path.basename(root)' gives the folder name.
        # Example: if root is "./raw_datasets/MRI/train_images/mild_dementia"
        # folder_name is "mild_dementia"
        folder_name = os.path.basename(root)
        
        # Check if this folder is one of our target classes
        target_class = None
        
        # 1. Check if name is exactly one of our destination classes
        if folder_name in CLASSES:
            target_class = folder_name
        # 2. Check if name is in our mapping list
        elif folder_name in CLASS_MAPPING:
            target_class = CLASS_MAPPING[folder_name]
            
        # If this folder contains class data, process the images inside
        if target_class:
            print(f"Processing folder: {folder_name} -> mapped to {target_class}")
            
            dest_folder = os.path.join(master_dir, target_class)
            os.makedirs(dest_folder, exist_ok=True)

            for file in files:
                if file.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tif')):
                    src_path = os.path.join(root, file)
                    
                    try:
                        # Check for Duplicate Content
                        file_hash = get_file_hash(src_path)
                        
                        if file_hash not in unique_hashes:
                            unique_hashes.add(file_hash)
                            
                            # Rename file to ensure uniqueness (e.g., img_0.jpg, img_1.jpg)
                            new_name = f"img_{total_images}.jpg" 
                            shutil.copy(src_path, os.path.join(dest_folder, new_name))
                            total_images += 1
                        else:
                            duplicate_count += 1
                    except Exception as e:
                        print(f"Error processing {src_path}: {e}")

    print(f"\nMerge Complete.")
    print(f"Total Unique Images: {total_images}")
    print(f"Duplicates Removed: {duplicate_count}")
    return master_dir

def step_2_split(master_dir):
    print("\n--- STEP 2: Splitting Train/Val/Test ---")
    
    for class_name in CLASSES:
        class_dir = os.path.join(master_dir, class_name)
        if not os.path.exists(class_dir):
            print(f"Warning: Class {class_name} has no images!")
            continue
            
        images = os.listdir(class_dir)
        random.shuffle(images) # Random shuffle is key!
        
        n = len(images)
        n_train = int(n * SPLIT_RATIOS[0])
        n_val = int(n * SPLIT_RATIOS[1])
        # The rest goes to test
        
        train_imgs = images[:n_train]
        val_imgs = images[n_train:n_train+n_val]
        test_imgs = images[n_train+n_val:]
        
        # Function to move files
        def move_files(file_list, split_name):
            target_path = os.path.join(OUTPUT_DIR, split_name, class_name)
            os.makedirs(target_path, exist_ok=True)
            
            for img in file_list:
                src = os.path.join(class_dir, img)
                shutil.move(src, os.path.join(target_path, img))
        
        move_files(train_imgs, "train")
        move_files(val_imgs, "val")
        move_files(test_imgs, "test")
        
        print(f"Class {class_name}: Train={len(train_imgs)}, Val={len(val_imgs)}, Test={len(test_imgs)}")

    # Cleanup temp folder
    if os.path.exists(master_dir):
        shutil.rmtree(master_dir)
    print(f"\nSUCCESS! Dataset ready at: {os.path.abspath(OUTPUT_DIR)}")

# --- EXECUTE ---
if __name__ == "__main__":
    master_path = step_1_merge_and_deduplicate()
    step_2_split(master_path)