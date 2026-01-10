"""
Quick diagnostic script to visualize the difference between slice orientations.
This helps verify we're extracting the correct anatomical view from NIfTI files.
"""
import nibabel as nib
import numpy as np
import matplotlib.pyplot as plt
import os

def visualize_all_orientations(nifti_path):
    """
    Show all three anatomical views from a NIfTI file to verify orientation.
    """
    if not os.path.exists(nifti_path):
        print(f"❌ File not found: {nifti_path}")
        return
    
    # Load the 3D volume
    nii_img = nib.load(nifti_path)
    nii_data = nii_img.get_fdata()
    
    print(f"📊 NIfTI Shape: {nii_data.shape}")
    print(f"   Interpretation: (Axis 0: {nii_data.shape[0]} slices, "
          f"Axis 1: {nii_data.shape[1]} slices, Axis 2: {nii_data.shape[2]} slices)")
    
    # Extract middle slices from each axis
    mid_0 = nii_data.shape[0] // 2
    mid_1 = nii_data.shape[1] // 2
    mid_2 = nii_data.shape[2] // 2
    
    # Get slices
    axial_slice = nii_data[mid_0, :, :]      # Axis 0 - AXIAL (what we want!)
    coronal_slice = nii_data[:, mid_1, :]    # Axis 1 - CORONAL
    sagittal_slice = nii_data[:, :, mid_2]   # Axis 2 - SAGITTAL (old incorrect method)
    
    # Normalize each slice
    def normalize(slice_2d):
        return (slice_2d - np.min(slice_2d)) / (np.max(slice_2d) - np.min(slice_2d) + 1e-8)
    
    axial_norm = normalize(axial_slice)
    coronal_norm = normalize(coronal_slice)
    sagittal_norm = normalize(sagittal_slice)
    
    # Create visualization
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    axes[0].imshow(axial_norm, cmap='gray')
    axes[0].set_title('AXIAL View (Axis 0)\n✅ CORRECT - Brain Cross-Section\n(What model was trained on)', 
                      fontsize=12, color='green', weight='bold')
    axes[0].axis('off')
    
    axes[1].imshow(coronal_norm, cmap='gray')
    axes[1].set_title('CORONAL View (Axis 1)\nFront View', fontsize=12)
    axes[1].axis('off')
    
    axes[2].imshow(sagittal_norm, cmap='gray')
    axes[2].set_title('SAGITTAL View (Axis 2)\n❌ OLD METHOD - Side Profile\n(Wrong orientation!)', 
                      fontsize=12, color='red', weight='bold')
    axes[2].axis('off')
    
    plt.tight_layout()
    plt.savefig('nifti_orientation_comparison.png', dpi=150, bbox_inches='tight')
    print("\n✅ Visualization saved as 'nifti_orientation_comparison.png'")
    print("\n🔍 Notice the difference:")
    print("   - AXIAL (left): Shows brain from top-down (like a CT scan)")
    print("   - SAGITTAL (right): Shows brain from the side (profile view)")
    print("\n💡 The model expects AXIAL views, so the fix is critical!")
    plt.show()

if __name__ == "__main__":
    # Try to find a .nii file in the dataset
    dataset_paths = [
        "FINAL_DATASET",
        "raw_datasets"
    ]
    
    nifti_file = None
    for base_path in dataset_paths:
        if os.path.exists(base_path):
            for root, dirs, files in os.walk(base_path):
                for file in files:
                    if file.endswith('.nii') or file.endswith('.nii.gz'):
                        nifti_file = os.path.join(root, file)
                        break
                if nifti_file:
                    break
        if nifti_file:
            break
    
    if nifti_file:
        print(f"🧠 Testing with: {nifti_file}\n")
        visualize_all_orientations(nifti_file)
    else:
        print("❌ No .nii files found in dataset directories.")
        print("Please provide a path to a .nii file:")
        manual_path = input("Path: ").strip()
        if manual_path:
            visualize_all_orientations(manual_path)
