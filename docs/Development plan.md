# Project Development Plan: Smart System for Early Detection of Alzheimer's Disease

**Project Type:** Graduation Project (Computer Engineering)  
**Target Platform:** Python Desktop Application  
**Core Technology:** Deep Learning (CNN), Transfer Learning, Medical Image Processing

---

## 📅 Phase 1: The AI Core (Cloud / Kaggle)
**Goal:** Create a high-accuracy `.pth` model file that can classify a 2D brain slice.  
**Environment:** Kaggle Notebooks (Tesla P100 GPU).

### 1.1 Dataset Acquisition
- [ ] **Search:** Locate "Alzheimer's MRI Preprocessed Dataset" on Kaggle.
- [ ] **Requirements:** 4 Classes (*Non Demented, Very Mild, Mild, Moderate*), JPG format.
- [ ] **Data Split:** Organize into Train (80%), Validation (10%), Test (10%).

### 1.2 Model Architecture Setup
- [ ] **Framework:** PyTorch.
- [ ] **Base Model:** `ResNet-50` (Pre-trained on ImageNet).
- [ ] **Modifications:**
    - Replace Final Fully Connected Layer: Change 1000 outputs to **4 outputs**.
    - Loss Function: `CrossEntropyLoss`.
    - Optimizer: `Adam` (Initial LR: 0.001).

### 1.3 Training Strategy (Transfer Learning)
- [ ] **Step A (Freezing):** Freeze first 75% of layers. Train only the head for 5-10 epochs.
- [ ] **Step B (Fine-Tuning):** Unfreeze the last "block". Train for 10-15 epochs with low LR (0.0001).
- [ ] **Metric:** Achieve **>90% Accuracy** on Test set.
- [ ] **Export:** Save the best weights as `alzheimer_resnet50.pth`.

### 1.4 Explainability (XAI)
- [ ] **Implementation:** Write a function for **Grad-CAM**.
- [ ] **Output:** Generate a heatmap overlay on the input image to verify the model is looking at brain features (ventricles/tissue).

---

## ⚙️ Phase 2: The "Universal Input" Logic (Local / PC)
**Goal:** Bridge the gap between raw medical files and the model.  
**Environment:** VS Code (Local Machine).

### 2.1 The Preprocessing Pipeline ("The Router")
- [ ] **Input Handling:**
    - **Case A (.nii/3D):**
        - Load file using `Nibabel`.
        - Extract middle 20 slices.
        - Resize to model input (e.g., 224x224).
        - Normalize pixel values (0-1).
    - **Case B (JPG/PNG):**
        - Load using `PIL`/`OpenCV`.
        - Resize and Normalize.

### 2.2 The Inference Engine
- [ ] **Class Structure:** Create `AlzheimerPredictor` class.
- [ ] **Logic:**
    - If Single Image: Return Prediction.
    - If 3D Volume: Run prediction on all extracted slices -> Calculate **Mean Probability** (Voting System).

---

## 🖥️ Phase 3: The Desktop Application (GUI)
**Goal:** A professional, user-friendly interface for doctors.  
**Tech Stack:** Python + `CustomTkinter`.

### 3.1 UI Layout Design
- [ ] **Sidebar:** Navigation (Home, Scan, Settings, About).
- [ ] **Main Area:**
    - Drag & Drop zone for files.
    - Patient Details Form (Name, Age, ID).
- **Results View:**
    - Large Image Display.
    - "Toggle Heatmap" Switch.
    - Prediction Text (Color-coded: Green/Red).

### 3.2 Report Generation
- [ ] **Library:** `ReportLab`.
- [ ] **Function:** "Export PDF" button.
- [ ] **Content:** Patient Info + Heatmap Image + Prediction Confidence + Disclaimer.

---

## 🧪 Phase 4: Testing & Final Polish
**Goal:** Ensure stability for the presentation.

- [ ] **Stress Test:** Upload corrupted files/non-MRI images to test error handling (`try/except`).
- [ ] **Threading:** Ensure `.nii` loading runs in a background thread (keeps UI responsive).
- [ ] **Packaging (Optional):** Use `PyInstaller` to create an executable `.exe`.

---

## 🛠️ Technology Stack Summary

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Language** | Python 3.9+ | Main Application Logic |
| **GUI Framework** | `CustomTkinter` | Modern Desktop Interface |
| **Deep Learning** | `PyTorch` | Model Training & Inference |
| **Medical Data** | `Nibabel` | Processing `.nii` 3D files |
| **Image Proc.** | `OpenCV` / `Pillow` | Slicing & Resizing |
| **Data Viz** | `Matplotlib` | Generating Heatmaps |
| **Reporting** | `ReportLab` | PDF Generation |
| **Hardware** | Kaggle (Training) | Local RTX 2060 (Inference) |