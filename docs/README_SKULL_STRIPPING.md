# Skull Stripping Test Script Documentation

## Overview

The `test_skull_stripping.py` script tests HD-BET skull stripping functionality on NIfTI brain scan files and generates visual comparisons.

## Features

✅ **Automated Processing**: Processes all `.nii` and `.nii.gz` files in the `nii files` directory  
✅ **HD-BET Integration**: Uses state-of-the-art deep learning for skull stripping  
✅ **Visual Comparison**: Creates before/after comparison images with difference maps  
✅ **Comprehensive Output**: Saves processed files, comparison images, and summary reports  

## Requirements

```bash
pip install HD-BET nibabel matplotlib numpy torch
```

## Usage

### Basic Usage

Simply run the script:

```bash
python test_skull_stripping.py
```

### What It Does

1. **Initializes HD-BET**: Downloads model parameters if needed (first run only)
2. **Processes Files**: Applies skull stripping to each NIfTI file
3. **Extracts Slices**: Extracts middle axial slices for visualization
4. **Creates Comparisons**: Generates comparison images showing:
   - Original scan
   - Skull-stripped scan
   - Difference map (removed tissue)
5. **Saves Results**: All outputs saved to `skull_stripping_results/`

## Output Files

### Directory Structure

```
skull_stripping_results/
├── stripped_*.nii.gz                    # Skull-stripped NIfTI files
├── skull_stripping_comparison.png       # Comparison image (150 DPI)
├── skull_stripping_comparison_hires.png # High-res version (300 DPI)
└── processing_report.txt                # Detailed processing log
```

### Comparison Image

The comparison image shows **3 samples** in a grid format:

| Original | After Skull Stripping | Difference |
|----------|----------------------|------------|
| Raw MRI scan | Brain tissue only | Removed skull/scalp |

## Configuration

You can modify these variables at the top of `test_skull_stripping.py`:

```python
NII_FILES_DIR = r"path\to\nii\files"  # Input directory
OUTPUT_DIR = r"path\to\output"         # Output directory
NUM_SAMPLES = 3                         # Number of samples in comparison image
```

## Processing Time

- **Per file**: ~1-2 minutes (CPU) or ~10-20 seconds (GPU)
- **6 files**: ~6-12 minutes total (CPU)

💡 **Tip**: HD-BET is computationally intensive. For faster processing, use a GPU if available.

## Troubleshooting

### HD-BET Not Installed

```
❌ ERROR: HD-BET not installed!
Please install it using: pip install HD-BET
```

**Solution**: Install HD-BET:
```bash
pip install HD-BET
```

### No NIfTI Files Found

```
❌ No NIfTI files found in [directory]
```

**Solution**: Verify the `NII_FILES_DIR` path contains `.nii` or `.nii.gz` files

### Memory Issues

If you encounter memory errors:

1. Process fewer files at once
2. Reduce `NUM_SAMPLES` in the script
3. Close other applications

## Understanding the Output

### Skull Stripping Quality

Good skull stripping should:
- ✅ Remove all skull, scalp, and non-brain tissue
- ✅ Preserve all brain tissue (gray and white matter)
- ✅ Maintain brain structure integrity

### Difference Map

The difference map (hot colormap) shows:
- **Bright areas**: Removed tissue (skull, scalp)
- **Dark areas**: Preserved tissue (brain)

## Advanced Usage

### Processing Specific Files

Modify the script to process specific files:

```python
# In process_all_files method
nii_files = [Path("specific_file.nii")]
```

### Changing Slice Selection

To extract a different slice (not middle):

```python
# In extract_middle_slice method
middle_index = total_slices // 2  # Change this line
# Example: first quarter
middle_index = total_slices // 4
```

### Adjusting Visualization

Modify the comparison image layout:

```python
# In create_comparison_image method
fig = plt.figure(figsize=(16, 5 * n_samples))  # Adjust size
```

## Script Architecture

```
SkullStrippingTester
├── __init__()              # Initialize HD-BET
├── perform_skull_stripping() # Process single file
├── extract_middle_slice()    # Extract 2D slice
├── process_all_files()       # Batch processing
├── create_comparison_image() # Generate visualization
└── generate_summary_report() # Create text report
```

## Example Output

### Processing Log

```
======================================================================
HD-BET SKULL STRIPPING TEST
======================================================================
Input directory: c:\...\nii files
Output directory: c:\...\skull_stripping_results
======================================================================

🧠 Initializing HD-BET...
✅ HD-BET initialized successfully

📁 Found 6 NIfTI file(s)
======================================================================

[1/6] Processing: ADNI_002_S_0782_MR_MPR...
  Processing: ADNI_002_S_0782_MR_MPR...
  ✅ Saved to: stripped_ADNI_002_S_0782_MR_MPR...

[2/6] Processing: ADNI_002_S_1280_MR_MPR...
  Processing: ADNI_002_S_1280_MR_MPR...
  ✅ Saved to: stripped_ADNI_002_S_1280_MR_MPR...

...

======================================================================
PROCESSING COMPLETE!
======================================================================
✅ Successfully processed: 6/6 files
📁 All results saved to: skull_stripping_results
======================================================================
```

## Integration with Main Application

The skull stripping functionality is already integrated into `preprocessing.py`:

```python
from preprocessing import Preprocessor

processor = Preprocessor()
tensor = processor.load_and_preprocess("scan.nii")
# Automatically applies skull stripping if HD-BET is installed
```

## References

- **HD-BET Paper**: [Isensee et al., 2019](https://arxiv.org/abs/1901.11341)
- **GitHub**: https://github.com/MIC-DKFZ/HD-BET
- **Documentation**: See HD-BET official documentation

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the processing report in `skull_stripping_results/processing_report.txt`
3. Verify HD-BET installation: `python -c "import HD_BET; print('OK')"`

---

**Created**: 2026-01-27  
**Version**: 1.0  
**Author**: Alzheimer's Disease Early Detection Project
