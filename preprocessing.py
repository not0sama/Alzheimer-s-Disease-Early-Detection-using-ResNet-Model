import os
import numpy as np
import cv2
import nibabel as nib
from PIL import Image
import torch
from torchvision import transforms

class Preprocessor:
    def __init__(self):
        # 1. Define the EXACT same transforms used in training
        # This ensures the model sees what it expects to see.
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406], 
                std=[0.229, 0.224, 0.225]
            )
        ])

    def load_and_preprocess(self, file_path):
        """
        Smart function that detects file type and processes accordingly.
        Returns: A Tensor of shape (1, 3, 224, 224) ready for the model.
        """
        ext = os.path.splitext(file_path)[1].lower()

        if ext in ['.jpg', '.jpeg', '.png', '.bmp']:
            return self._process_standard_image(file_path)
        
        elif ext in ['.nii', '.nii.gz']:
            return self._process_nifti_volume(file_path)
        
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    def _process_standard_image(self, path):
        """Handle standard 2D images (JPG, PNG)"""
        try:
            image = Image.open(path).convert('RGB')
            tensor = self.transform(image)
            return tensor.unsqueeze(0) # Add batch dimension -> (1, 3, 224, 224)
        except Exception as e:
            print(f"Error processing image: {e}")
            return None

    def _process_nifti_volume(self, path):
        """
        Handle 3D Medical Files (.nii).
        Strategy: Extract the middle AXIAL slice to match training data orientation.
        
        IMPORTANT: 3D MRI volumes contain three anatomical views:
        - Axial (axis 0): Horizontal slices, top-down view (BRAIN CROSS-SECTION) ✅
        - Sagittal (axis 2): Vertical slices, side view (PROFILE)
        - Coronal (axis 1): Vertical slices, front view (FACE-ON)
        
        The model was trained on AXIAL images, so we MUST extract along axis 0.
        """
        try:
            # 1. Attempt Skull Stripping using HD-BET (if installed)
            load_path = path 
            temp_stripped_path = None

            try:
                # HD-BET 2.0+ API Usage
                from HD_BET.run import run_hd_bet
                # Legacy API check - if this works, great (it likely won't on v2.0)
                
                print("🧠 Performing Skull Stripping with HD-BET (Legacy)...")
                # ... legacy code ...
            except ImportError:
                # Try New API
                try:
                    from HD_BET.entry_point import get_hdbet_predictor, hdbet_predict, maybe_download_parameters
                    import torch
                    
                    print("🧠 Performing Skull Stripping with HD-BET (v2.0)...")
                    
                    import tempfile
                    tf = tempfile.NamedTemporaryFile(suffix='.nii.gz', delete=False) 
                    # HD-BET often prefers .nii.gz
                    temp_stripped_path = tf.name
                    tf.close()

                    # Ensure parameters are downloaded
                    maybe_download_parameters()
                    
                    # Init Predictor (using CPU for Mac/Windows compatibility as requested)
                    # Note: HD-BET 2.0 defaults to CUDA, so we must specify CPU
                    device = torch.device('cpu')
                    predictor = get_hdbet_predictor(device=device)
                    
                    # Run Prediction
                    hdbet_predict(path, temp_stripped_path, predictor)
                    
                    load_path = temp_stripped_path
                    print("✅ Skull Stripping Complete.")

                except ImportError:
                    print("⚠️ HD-BET not installed or API mismatch. Skipping. (pip install HD-BET)")
                except Exception as e:
                    print(f"⚠️ Skull stripping failed: {e}")

            except Exception as e:
                 # Catch-all for the first block if it wasn't an ImportError but something else
                 print(f"⚠️ Skull stripping failed (Legacy): {e}")

            # 2. Load the 3D volume
            if not os.path.exists(load_path):
                # Fallback if the output file wasn't created
                load_path = path

            nii_img = nib.load(load_path)
            nii_data = nii_img.get_fdata()

            # 2. Find the middle AXIAL slice (axis 0)
            # NIfTI shape is typically (Axial_slices, Height, Width) or similar
            total_slices = nii_data.shape[0]  # Changed from shape[2] to shape[0]
            middle_index = total_slices // 2
            
            # Extract AXIAL slice (horizontal cross-section of brain)
            slice_2d = nii_data[middle_index, :, :]  # Changed indexing

            # 3. Normalize to 0-255 range (Standard Image format)
            # MRI data can be wildly different ranges, so we min-max normalize first
            slice_2d = (slice_2d - np.min(slice_2d)) / (np.max(slice_2d) - np.min(slice_2d))
            slice_2d = (slice_2d * 255).astype(np.uint8)

            # 4. Convert to RGB (Model expects 3 channels)
            # We stack the grayscale image 3 times to fake RGB
            slice_rgb = np.stack((slice_2d,)*3, axis=-1)
            
            # 5. Convert to PIL Image and Transform
            # 5. Convert to PIL Image and Transform
            image = Image.fromarray(slice_rgb)
            tensor = self.transform(image)
            
            # Cleanup temp file if it exists
            if temp_stripped_path and os.path.exists(temp_stripped_path):
                try:
                    os.remove(temp_stripped_path)
                except: pass

            return tensor.unsqueeze(0) # Add batch dimension

        except Exception as e:
            print(f"Error processing NII file: {e}")
            # Cleanup temp file on error too
            if 'temp_stripped_path' in locals() and temp_stripped_path and os.path.exists(temp_stripped_path):
                try:
                    os.remove(temp_stripped_path)
                except: pass
            return None

# --- Quick Test Block ---
if __name__ == "__main__":
    # Create a dummy test
    processor = Preprocessor()
    print("✅ Preprocessor initialized.")