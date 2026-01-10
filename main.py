import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter as tk
from PIL import Image
import os
import threading
import platform
import subprocess
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
import datetime

# Import your AI Brain
from inference import AlzheimerPredictor

# --- CONFIGURATION ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

def open_file_dialog_native():
    """Cross-platform file dialog logic."""
    if platform.system() == "Darwin":  # macOS
        script = '''
        set fileTypes to {"jpg", "jpeg", "png", "bmp", "nii", "gz"}
        set selectedFile to choose file with prompt "Select MRI Scan" of type fileTypes
        return POSIX path of selectedFile
        '''
        try:
            result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=300)
            return result.stdout.strip() if result.returncode == 0 else ""
        except: return ""
    else:
        # Windows/Linux
        temp_root = tk.Tk()
        temp_root.withdraw()
        temp_root.attributes('-topmost', True)
        try:
            return filedialog.askopenfilename(parent=temp_root, title="Select MRI Scan",
                filetypes=[
                    ("All Supported Files", "*.nii *.nii.gz *.jpg *.jpeg *.png *.bmp"),
                    ("Medical MRI", "*.nii *.nii.gz"),
                    ("Standard Images", "*.jpg *.jpeg *.png *.bmp"),
                    ("All Files", "*.*")
                ])
        finally: temp_root.destroy()

class AlzheimerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("NeuroScan AI - Early Alzheimer's Detection")
        self.geometry("1100x700")
        
        # State Variables
        self.predictor = None
        self.model_path = "models/alzheimer_resnet50_best.pth"
        self.current_prediction = None
        self.current_confidence = None
        self.current_overlay = None  # Heatmap
        self.current_original = None # Original Image

        # Layout
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True)
        self.create_sidebar()
        self.create_main_area()
        
        # Background Load
        self.load_model_thread()

    def load_model_thread(self):
        threading.Thread(target=self._init_predictor, daemon=True).start()

    def _init_predictor(self):
        try:
            self.predictor = AlzheimerPredictor(self.model_path)
            self.status_label.configure(text="System Status: Online 🟢", text_color="#2CC985")
        except Exception as e:
            self.status_label.configure(text=f"Error: {str(e)}", text_color="red")

    def create_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self.container, width=250, corner_radius=0)
        self.sidebar_frame.pack(side="left", fill="y", padx=0, pady=0)
        self.sidebar_frame.pack_propagate(False)

        # Title
        ctk.CTkLabel(self.sidebar_frame, text="NeuroScan AI", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=(20, 10))
        self.status_label = ctk.CTkLabel(self.sidebar_frame, text="System Status: Loading... 🟡", font=ctk.CTkFont(size=12))
        self.status_label.pack(pady=(0, 20))

        # Inputs
        self.upload_btn = ctk.CTkButton(self.sidebar_frame, text="📂 Open MRI Scan", command=self.select_image)
        self.upload_btn.pack(pady=10, padx=20)

        ctk.CTkLabel(self.sidebar_frame, text="Patient Details", anchor="w").pack(pady=(40, 0), padx=20)
        self.name_entry = ctk.CTkEntry(self.sidebar_frame, placeholder_text="Patient Name / ID")
        self.name_entry.pack(pady=5, padx=20)

        # --- NEW: EXPORT BUTTON ---
        self.export_btn = ctk.CTkButton(self.sidebar_frame, text="📄 Export PDF Report", 
                                      command=self.save_report, fg_color="transparent", border_width=2)
        self.export_btn.pack(pady=20, padx=20, side="bottom")

    def create_main_area(self):
        self.main_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.main_frame.pack(side="right", fill="both", expand=True, padx=20, pady=20)

        # Image
        self.image_display = ctk.CTkLabel(self.main_frame, text="No Scan Selected", width=400, height=400, fg_color="#2b2b2b", corner_radius=10)
        self.image_display.pack(pady=20)

        # Toggle
        self.heatmap_switch = ctk.CTkSwitch(self.main_frame, text="Show AI Attention (Heatmap)", command=self.toggle_heatmap)
        self.heatmap_switch.pack(pady=10)
        self.heatmap_switch.deselect()

        # Results
        self.result_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.result_frame.pack(pady=20, fill="x")
        self.prediction_label = ctk.CTkLabel(self.result_frame, text="Prediction: --", font=ctk.CTkFont(size=28, weight="bold"))
        self.prediction_label.pack()
        self.confidence_label = ctk.CTkLabel(self.result_frame, text="Confidence: --%", font=ctk.CTkFont(size=18))
        self.confidence_label.pack()

    def select_image(self):
        path = open_file_dialog_native()
        if path: self.run_inference(path)

    def run_inference(self, path):
        if not self.predictor: return
        self.prediction_label.configure(text="Analyzing...", text_color="white")
        self.update()

        try:
            pred_class, confidence, overlay_img = self.predictor.predict_with_heatmap(path)
            
            # Store data for PDF Export
            self.current_prediction = pred_class
            self.current_confidence = confidence
            self.current_overlay = overlay_img
            self.current_original = Image.open(path).convert("RGB") if not path.endswith('.nii') else overlay_img

            # Update UI
            color = "#FF4444" if "Demented" in pred_class and "Non" not in pred_class else "#2CC985"
            if "Very Mild" in pred_class: color = "#FFB344"
            self.prediction_label.configure(text=f"{pred_class}", text_color=color)
            self.confidence_label.configure(text=f"Confidence: {confidence:.2f}%")
            
            self.heatmap_switch.deselect()
            self.update_display_image(self.current_original)
            
        except Exception as e:
            print(f"Error: {e}")

    def toggle_heatmap(self):
        if self.heatmap_switch.get() == 1 and hasattr(self, 'current_overlay'):
            self.update_display_image(self.current_overlay)
        elif hasattr(self, 'current_original'):
            self.update_display_image(self.current_original)

    def update_display_image(self, pil_image):
        display_img = pil_image.copy()
        display_img.thumbnail((400, 400))
        ctk_img = ctk.CTkImage(light_image=display_img, dark_image=display_img, size=display_img.size)
        self.image_display.configure(image=ctk_img, text="")

    # --- NEW: PDF GENERATION LOGIC ---
    def save_report(self):
        if not self.current_prediction:
            print("No analysis available to export.")
            return

        # 1. Ask where to save
        save_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Documents", "*.pdf")],
            title="Save Medical Report"
        )
        if not save_path: return

        # 2. Get Patient Name
        patient_name = self.name_entry.get() or "Unknown Patient"
        date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            # 3. Create PDF Canvas
            c = canvas.Canvas(save_path, pagesize=letter)
            width, height = letter

            # HEADER
            c.setFont("Helvetica-Bold", 24)
            c.drawString(50, height - 50, "NeuroScan AI - Medical Report")
            
            c.setFont("Helvetica", 12)
            c.drawString(50, height - 80, f"Date: {date_str}")
            c.drawString(50, height - 100, f"Patient Name/ID: {patient_name}")
            
            c.line(50, height - 110, width - 50, height - 110) # Separator Line

            # RESULTS SECTION
            c.setFont("Helvetica-Bold", 18)
            c.drawString(50, height - 150, "Analysis Results")
            
            c.setFont("Helvetica", 14)
            c.drawString(50, height - 180, f"Predicted Class: {self.current_prediction}")
            c.drawString(50, height - 200, f"Confidence Score: {self.current_confidence:.2f}%")

            # IMAGES (Save temp files to embed)
            temp_orig = "temp_orig.jpg"
            temp_heat = "temp_heat.jpg"
            self.current_original.save(temp_orig)
            self.current_overlay.save(temp_heat)

            # Draw Original Scan
            c.drawString(50, height - 250, "Original MRI Scan:")
            c.drawImage(temp_orig, 50, height - 460, width=200, height=200, preserveAspectRatio=True)

            # Draw AI Analysis
            c.drawString(300, height - 250, "AI Attention (Grad-CAM):")
            c.drawImage(temp_heat, 300, height - 460, width=200, height=200, preserveAspectRatio=True)

            # DISCLAIMER
            c.setFont("Helvetica-Oblique", 10)
            c.setFillColorRGB(0.5, 0.5, 0.5) # Grey color
            disclaimer = "DISCLAIMER: This tool is an assistive AI device. Final diagnosis must be performed by a qualified medical professional."
            c.drawCentredString(width / 2, 50, disclaimer)

            # SAVE
            c.save()
            
            # Cleanup temp files
            if os.path.exists(temp_orig): os.remove(temp_orig)
            if os.path.exists(temp_heat): os.remove(temp_heat)
            
            print(f"✅ Report saved to {save_path}")
            
        except Exception as e:
            print(f"Error saving PDF: {e}")

if __name__ == "__main__":
    app = AlzheimerApp()
    app.mainloop()