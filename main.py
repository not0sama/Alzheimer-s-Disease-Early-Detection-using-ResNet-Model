
import customtkinter as ctk
from tkinter import messagebox, filedialog
from PIL import Image
import os
import platform
import subprocess
import threading
import io

# Local Imports
from auth_manager import AuthManager
from inference import AlzheimerPredictor
from database import init_db, Report, User
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import datetime

# --- THEME CONFIGURATION ---
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

# --- COLOR PALETTE ---
COLOR_PRIMARY = "#00695C"      # Professional Medical Teal
COLOR_PRIMARY_HOVER = "#004D40" # Darker Teal
COLOR_BG = "#F5F7FA"           # Cool Grey-White background
COLOR_TEXT = "#37474F"         # Blue-Grey text (softer than black)
COLOR_SECONDARY = "#546E7A"    # Blue Grey
COLOR_WHITE = "#FFFFFF"

class MedicalApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Window Setup
        self.title("NeuroScan AI - Medical Diagnostic System")
        self.geometry("1280x800")
        self.configure(fg_color=COLOR_BG)
        
        # State
        self.auth = AuthManager(self)
        self.current_user = None
        self.predictor = None # Loaded lazily
        self.model_path = "models/alzheimer_resnet50_best.pth"
        
        # Start
        self.load_model_thread()
        self.show_login_screen()

    def clear_screen(self):
        for widget in self.winfo_children():
            widget.destroy()

    # =========================================================================
    # LOGIN SCREEN
    # =========================================================================
    def show_login_screen(self):
        self.clear_screen()
        
        # --- LAYOUT CONTAINER ---
        # We need a main container to hold the 3 distinct areas:
        # [Brand (Left)] - [Login Form (Center)] - [Saved Profiles Tab (Right)]
        
        main_container = ctk.CTkFrame(self, fg_color=COLOR_BG)
        main_container.pack(fill="both", expand=True)

        # 1. LEFT SIDE (Branding)
        left_frame = ctk.CTkFrame(main_container, fg_color=COLOR_PRIMARY, width=400, corner_radius=0)
        left_frame.pack(side="left", fill="y")
        left_frame.pack_propagate(False)
        
        try:
            if os.path.exists("logo.png"):
                logo_img = ctk.CTkImage(Image.open("logo.png"), size=(180, 180))
                ctk.CTkLabel(left_frame, image=logo_img, text="").pack(pady=(150, 30))
                
            ctk.CTkLabel(left_frame, text="NeuroScan AI", font=("Roboto", 36, "bold"), text_color="white").pack()
            ctk.CTkLabel(left_frame, text="Advanced Alzheimer's Detection", font=("Roboto", 14), text_color="#B2DFDB").pack(pady=10)
        except Exception as e:
            print(f"Error: {e}")

        # 2. RIGHT SIDE (Saved Profiles - Collapsible)
        # We start with it slightly visible or fully visible? User said "expandable and contractable".
        # Let's make a narrow strip that expands.
        
        self.right_sidebar = ctk.CTkFrame(main_container, fg_color="#ECEFF1", width=50, corner_radius=0)
        self.right_sidebar.pack(side="right", fill="y")
        self.right_sidebar.pack_propagate(False) # Start collapsed
        
        self.is_sidebar_expanded = False
        
        # Toggle Button (Vertical text trick or icon)
        self.toggle_btn = ctk.CTkButton(self.right_sidebar, text="◀\n\nS\na\nv\ne\nd\n\nP\nr\no\nf\ni\nl\ne\ns", 
                                      width=40, height=200, fg_color="#CFD8DC", text_color=COLOR_TEXT,
                                      command=self.toggle_sidebar)
        self.toggle_btn.pack(side="left", fill="y")
        
        # Content frame for the sidebar (hidden initially)
        self.profile_list_frame = ctk.CTkScrollableFrame(self.right_sidebar, label_text="Quick Login", fg_color="transparent")
        # We don't pack it yet because width is 50.

        # 3. CENTER (Login Form)
        center_frame = ctk.CTkFrame(main_container, fg_color=COLOR_BG)
        center_frame.pack(side="left", fill="both", expand=True)
        
        login_box = ctk.CTkFrame(center_frame, fg_color=COLOR_WHITE, corner_radius=15, width=400, height=500)
        login_box.place(relx=0.5, rely=0.5, anchor="center")
        login_box.pack_propagate(False)

        ctk.CTkLabel(login_box, text="Welcome Back", font=("Roboto", 28, "bold"), text_color=COLOR_TEXT).pack(pady=(50, 40))

        # Inputs
        self.username_entry = ctk.CTkEntry(login_box, placeholder_text="Username", width=300, height=45)
        self.username_entry.pack(pady=10)

        self.password_entry = ctk.CTkEntry(login_box, placeholder_text="Password", show="*", width=300, height=45)
        self.password_entry.pack(pady=10)
        
        # Buttons
        ctk.CTkButton(login_box, text="Login", width=300, height=45,
                    fg_color=COLOR_PRIMARY, hover_color=COLOR_PRIMARY_HOVER,
                    command=self.perform_login).pack(pady=30)
        
        ctk.CTkButton(login_box, text="Register New Account", 
                    fg_color="transparent", text_color=COLOR_PRIMARY, 
                    hover_color="#E0F2F1",
                    command=self.prompt_admin_password).pack()

        # Populate sidebar data initially
        self.refresh_saved_profiles()

    def toggle_sidebar(self):
        if self.is_sidebar_expanded:
            # Contract
            self.right_sidebar.configure(width=50)
            self.toggle_btn.configure(text="◀\n\nS\na\nv\ne\nd")
            self.profile_list_frame.pack_forget()
            self.is_sidebar_expanded = False
        else:
            # Expand
            self.right_sidebar.configure(width=250)
            self.toggle_btn.configure(text="▶")
            self.profile_list_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)
            self.is_sidebar_expanded = True

    def refresh_saved_profiles(self):
        # Clear old
        for widget in self.profile_list_frame.winfo_children():
            widget.destroy()
            
        users = self.auth.get_all_users()
        for u in users:
            username, fullname = u
            btn = ctk.CTkButton(self.profile_list_frame, text=f"{fullname}\n(@{username})", 
                              fg_color="white", text_color=COLOR_TEXT, hover_color="#B2DFDB",
                              command=lambda usr=username: self.fill_login(usr))
            btn.pack(pady=5, padx=5, fill="x")

    def fill_login(self, username):
        self.username_entry.delete(0, "end")
        self.username_entry.insert(0, username)
        self.password_entry.focus()

    def perform_login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        success, msg = self.auth.login(username, password)
        if success:
            self.current_user = self.auth.current_user
            self.show_dashboard()
        else:
            messagebox.showerror("Login Failed", msg)

    def prompt_admin_password(self):
        """Ask for Superadmin password before registration"""
        dialog = ctk.CTkInputDialog(text="Enter Superadmin (admin) Password:", title="Admin Access")
        password = dialog.get_input()
        if password == "admin": # Matches the hardcoded ensure_superadmin logic
            self.show_registration_screen()
        else:
            messagebox.showerror("Access Denied", "Incorrect Admin Password")

    # =========================================================================
    # REGISTRATION SCREEN
    # =========================================================================
    def show_registration_screen(self):
        self.clear_screen()
        
        frame = ctk.CTkFrame(self, fg_color=COLOR_WHITE, width=600, corner_radius=15)
        frame.place(relx=0.5, rely=0.5, anchor="center")
        
        ctk.CTkLabel(frame, text="Staff Registration", font=("Roboto", 24, "bold"), text_color=COLOR_TEXT).pack(pady=20)
        
        # Fields
        self.reg_fullname = ctk.CTkEntry(frame, placeholder_text="Full Name", width=400, height=40)
        self.reg_fullname.pack(pady=10)
        
        self.reg_specialty = ctk.CTkEntry(frame, placeholder_text="Specialty (e.g. Neurologist)", width=400, height=40)
        self.reg_specialty.pack(pady=10)
        
        self.reg_phone = ctk.CTkEntry(frame, placeholder_text="Phone Number", width=400, height=40)
        self.reg_phone.pack(pady=10)
        
        self.reg_user = ctk.CTkEntry(frame, placeholder_text="Username", width=400, height=40)
        self.reg_user.pack(pady=10)
        
        self.reg_pass = ctk.CTkEntry(frame, placeholder_text="Password", show="*", width=400, height=40)
        self.reg_pass.pack(pady=10)
        
        ctk.CTkButton(frame, text="Create Account", width=400, height=50,
                    fg_color=COLOR_PRIMARY, command=self.perform_registration).pack(pady=20)
                    
        ctk.CTkButton(frame, text="Cancel", fg_color="transparent", text_color="gray", command=self.show_login_screen).pack(pady=10)

    def perform_registration(self):
        success, msg = self.auth.register_user(
            self.reg_fullname.get(),
            self.reg_specialty.get(),
            self.reg_phone.get(),
            self.reg_user.get(),
            self.reg_pass.get()
        )
        if success:
            messagebox.showinfo("Success", msg)
            self.show_login_screen()
        else:
            messagebox.showerror("Error", msg)

    # =========================================================================
    # DASHBOARD
    # =========================================================================
    def show_dashboard(self):
        self.clear_screen()
        
        # Header
        header = ctk.CTkFrame(self, fg_color=COLOR_WHITE, height=80, corner_radius=0)
        header.pack(fill="x", side="top")
        
        ctk.CTkLabel(header, text="NeuroScan AI", font=("Roboto", 24, "bold"), text_color=COLOR_PRIMARY).pack(side="left", padx=30, pady=20)
        
        user_info = f"Dr. {self.current_user.full_name}" if self.current_user.full_name else self.current_user.username
        ctk.CTkLabel(header, text=f"Logged in as: {user_info}", font=("Roboto", 14), text_color="gray").pack(side="right", padx=30)

        # Main Content Area
        content = ctk.CTkFrame(self, fg_color=COLOR_BG)
        content.pack(fill="both", expand=True, padx=50, pady=50)
        
        ctk.CTkLabel(content, text="Dashboard", font=("Roboto", 32, "bold"), text_color=COLOR_TEXT).pack(anchor="w", pady=(0, 40))
        
        # Buttons Grid
        grid_frame = ctk.CTkFrame(content, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True)

        self.create_dashboard_card(grid_frame, "➕ New Scan", "Start a new Alzheimer's analysis session", self.show_scan_screen, 0)
        self.create_dashboard_card(grid_frame, "📂 Reports History", "View and manage user reports", self.show_history_screen, 1)
        self.create_dashboard_card(grid_frame, "👤 Change User", "Log out and switch account", self.show_login_screen, 2)

    def create_dashboard_card(self, parent, title, subtitle, command, col):
        card = ctk.CTkButton(parent, text="", fg_color=COLOR_WHITE, hover_color="#F1F5F9", 
                           width=350, height=250, corner_radius=15, command=command)
        card.grid(row=0, column=col, padx=20, pady=20)
        
        # We can't put widgets INSIDE a button easily in CTk, so we overlay a frame or just use the button text
        # But to make it look nice, let's just make the button styled.
        # Actually, let's use a Frame that IS clickable (by binding events) for better styling
        
        # Re-doing as Frame
        card.destroy()
        
        frame = ctk.CTkFrame(parent, fg_color=COLOR_WHITE, corner_radius=15, width=350, height=250)
        frame.grid(row=0, column=col, padx=20, pady=20)
        frame.pack_propagate(False) # Strict size
        
        # Click event
        def on_click(e): command()
        frame.bind("<Button-1>", on_click)
        
        ctk.CTkLabel(frame, text=title, font=("Roboto", 24, "bold"), text_color=COLOR_PRIMARY).pack(pady=(80, 10))
        ctk.CTkLabel(frame, text=subtitle, font=("Roboto", 14), text_color="gray").pack()
        
        # Visual hover effect
        def on_enter(e): frame.configure(fg_color="#F1F5F9")
        def on_leave(e): frame.configure(fg_color=COLOR_WHITE)
        frame.bind("<Enter>", on_enter)
        frame.bind("<Leave>", on_leave)
        
        # Bind children too so clicking label works
        for child in frame.winfo_children():
            child.bind("<Button-1>", on_click)

    # =========================================================================
    # NEW SCAN SCREEN
    # =========================================================================
    def show_scan_screen(self):
        self.clear_screen()
        
        # Top Bar
        top_frame = ctk.CTkFrame(self, height=60, fg_color=COLOR_WHITE)
        top_frame.pack(fill="x", side="top")
        
        ctk.CTkButton(top_frame, text="← Dashboard", command=self.show_dashboard, 
                    fg_color="transparent", text_color="gray", width=100).pack(side="left", padx=10)
        ctk.CTkLabel(top_frame, text="Diagnostic Imaging Session", font=("Roboto", 20, "bold"), text_color=COLOR_TEXT).pack(side="left", padx=20)

        # Main Container
        self.scan_container = ctk.CTkFrame(self, fg_color=COLOR_BG)
        self.scan_container.pack(fill="both", expand=True)

        # ---------------------------------------------------------
        # 1. LEFT SIDE: LARGE VIEWPORT (Scan Area)
        # ---------------------------------------------------------
        self.viewport_frame = ctk.CTkFrame(self.scan_container, fg_color="transparent")
        self.viewport_frame.pack(side="left", fill="both", expand=True, padx=20, pady=20)

        # Controls Row
        controls = ctk.CTkFrame(self.viewport_frame, fg_color="transparent")
        controls.pack(fill="x", pady=(0, 10))
        
        ctk.CTkButton(controls, text="📂 Upload Scan", command=self.upload_scan, fg_color=COLOR_PRIMARY).pack(side="left")
        ctk.CTkButton(controls, text="✖ Clear", command=self.clear_scan, fg_color="#EF4444", width=80).pack(side="left", padx=10)
        
        self.heatmap_switch = ctk.CTkSwitch(controls, text="AI Heatmap Overlay", command=self.toggle_heatmap, progress_color=COLOR_PRIMARY)
        self.heatmap_switch.pack(side="right")
        self.heatmap_switch.deselect()

        # Big Image Canvas
        self.image_display = ctk.CTkLabel(self.viewport_frame, text="Load MRI to Begin Analysis", 
                                        width=700, height=600,  # MUCH LARGER
                                        fg_color="#CFD8DC", corner_radius=15,
                                        font=("Roboto", 16))
        self.image_display.pack(fill="both", expand=True)
        
        # Result Banner
        self.result_frame = ctk.CTkFrame(self.viewport_frame, fg_color=COLOR_WHITE, height=80, corner_radius=10)
        self.result_frame.pack(fill="x", pady=20)
        
        self.result_label = ctk.CTkLabel(self.result_frame, text="Waiting for input...", font=("Roboto", 24, "bold"), text_color="gray")
        self.result_label.pack(side="left", padx=30, pady=20)
        
        self.confidence_label = ctk.CTkLabel(self.result_frame, text="", font=("Roboto", 18), text_color="gray")
        self.confidence_label.pack(side="right", padx=30)


        # ---------------------------------------------------------
        # 2. RIGHT SIDE: COLLAPSIBLE REPORT TAB
        # ---------------------------------------------------------
        self.report_sidebar_frame = ctk.CTkFrame(self.scan_container, fg_color=COLOR_WHITE, width=400, corner_radius=0)
        # We don't pack it yet (collapsed state)
        
        # Toggle Strip
        self.toggle_strip = ctk.CTkFrame(self.scan_container, fg_color="#B0BEC5", width=30)
        self.toggle_strip.pack(side="right", fill="y")
        
        self.is_report_open = False
        self.btn_toggle_report = ctk.CTkButton(self.toggle_strip, text="◀\n\nR\ne\np\no\nr\nt", 
                                             width=30, height=200, fg_color="transparent", text_color=COLOR_TEXT,
                                             command=self.toggle_report_panel)
        self.btn_toggle_report.pack(fill="both", expand=True)
        
        # Populate Report Form (Hidden initially)
        self.setup_report_form()

        # Internal State
        self.current_scan_path = None
        self.current_prediction_text = None
        self.current_confidence_text = None
        self.current_overlay_pil = None # Heatmap
        self.current_original_pil = None # Clean

    def setup_report_form(self):
        # Header
        ctk.CTkLabel(self.report_sidebar_frame, text="Patient Report Details", 
                   font=("Roboto", 20, "bold"), text_color=COLOR_PRIMARY).pack(pady=20)
        
        # Scrollable Form
        scroll = ctk.CTkScrollableFrame(self.report_sidebar_frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10)
        
        self.entry_name = self.create_form_field(scroll, "Full Name")
        self.entry_age = self.create_form_field(scroll, "Age")
        
        # Gender - Dropdown
        ctk.CTkLabel(scroll, text="Gender", font=("Roboto", 12, "bold"), text_color=COLOR_TEXT).pack(anchor="w", padx=10, pady=(10, 0))
        self.entry_gender = ctk.CTkOptionMenu(scroll, values=["Male", "Female"], height=35, fg_color=COLOR_WHITE, text_color=COLOR_TEXT, button_color=COLOR_PRIMARY, dropdown_fg_color=COLOR_WHITE)
        self.entry_gender.pack(fill="x", padx=10, pady=5)
        
        self.entry_phone = self.create_form_field(scroll, "Phone Number")
        
        ctk.CTkLabel(scroll, text="Medical History", font=("Roboto", 12, "bold"), text_color=COLOR_TEXT).pack(anchor="w", padx=10, pady=(10, 0))
        self.entry_history = ctk.CTkTextbox(scroll, height=100)
        self.entry_history.pack(fill="x", padx=10, pady=5)
        
        # Actions
        ctk.CTkButton(self.report_sidebar_frame, text="💾 Save to Database & Export PDF", 
                    fg_color=COLOR_PRIMARY, height=50, font=("Roboto", 14, "bold"),
                    command=self.save_and_export).pack(pady=20, padx=20, fill="x")

    def toggle_report_panel(self):
        if self.is_report_open:
            self.report_sidebar_frame.pack_forget()
            self.toggle_strip.pack_forget() # Repack strip to keep order? No, just unpack frame
            self.toggle_strip.pack(side="right", fill="y") # Ensure strip is rightmost
            self.btn_toggle_report.configure(text="◀\n\nR\ne\np\no\nr\nt")
            self.is_report_open = False
        else:
            self.toggle_strip.pack_forget()
            self.report_sidebar_frame.pack(side="right", fill="y")
            self.toggle_strip.pack(side="right", fill="y") # Strip always on edge
            self.btn_toggle_report.configure(text="▶")
            self.is_report_open = True

    def toggle_heatmap(self):
        if not self.current_original_pil: return
        
        if self.heatmap_switch.get() == 1:
            # Show Heatmap
            self.update_display_image(self.current_overlay_pil)
        else:
            # Show Original
            self.update_display_image(self.current_original_pil)

    def clear_scan(self):
        self.current_scan_path = None
        self.current_prediction_text = None
        self.current_original_pil = None
        self.current_overlay_pil = None
        
        if hasattr(self, 'image_display'):
            self.image_display.configure(image=None, text="Load MRI to Begin Analysis")
        if hasattr(self, 'result_label'):
            self.result_label.configure(text="Waiting for input...", text_color="gray")
        if hasattr(self, 'confidence_label'):
            self.confidence_label.configure(text="")
        if hasattr(self, 'heatmap_switch'):
            self.heatmap_switch.deselect()

    def update_display_image(self, pil_image):
        if not pil_image: return
        
        # Target Dimensions
        target_w, target_h = 700, 600
        
        # Calculate Aspect Ratio preserving Resize
        # We want to fill the space as much as possible, including UPSCALING
        w, h = pil_image.size
        ratio = min(target_w/w, target_h/h)
        new_w = int(w * ratio)
        new_h = int(h * ratio)
        
        # Resize with high quality filter
        display = pil_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        ctk_img = ctk.CTkImage(display, size=(new_w, new_h))
        self.image_display.configure(image=ctk_img, text="")

    def upload_scan(self):
        filetypes=[
            ("All Supported Files", "*.nii *.nii.gz *.jpg *.jpeg *.png *.bmp"),
            ("Medical MRI", "*.nii *.nii.gz"),
            ("Standard Images", "*.jpg *.jpeg *.png *.bmp"),
            ("All Files", "*.*")
        ]
        path = filedialog.askopenfilename(title="Select MRI Scan", filetypes=filetypes)
        if path:
            self.current_scan_path = path
            self.run_inference(path)

    def run_inference(self, path):
        if not self.predictor:
            messagebox.showwarning("System", "AI Model is still loading in background...")
            return

        try:
            self.result_label.configure(text="Analyzing...", text_color=COLOR_PRIMARY)
            self.update()
            
            pred_class, confidence, overlay_img = self.predictor.predict_with_heatmap(path)
            
            # Store State
            self.current_prediction_text = pred_class
            self.current_confidence_text = f"{confidence:.2f}%"
            self.current_overlay_pil = overlay_img
            self.current_original_pil = Image.open(path).convert("RGB") if not path.endswith('.nii') and not path.endswith('.gz') else overlay_img # NII fallback
            
            # Update UI
            color = "#EF4444" if "Demented" in pred_class and "Non" not in pred_class else "#10B981"
            if "Very Mild" in pred_class: color = "#F59E0B"
            
            self.result_label.configure(text=f"Diagnosis: {pred_class}", text_color=color)
            self.confidence_label.configure(text=f"Confidence: {confidence:.2f}%")
            
            # Default to Heatmap ON? Or OFF? User asked for toggle. Let's start with Original.
            self.heatmap_switch.deselect()
            self.update_display_image(self.current_original_pil)
            
            # Auto-open report tab?
            if not self.is_report_open:
                self.toggle_report_panel()
            
        except Exception as e:
            messagebox.showerror("Error", f"Inference failed: {e}")

    # ---------------------------------------------------------
    # PDF EXPORT LOGIC
    # ---------------------------------------------------------
    def export_pdf_report(self):
        if not self.current_prediction_text:
            messagebox.showwarning("Warning", "No scan results to export.")
            return

        # 1. Determine Default Path (Desktop/Reports)
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        reports_dir = os.path.join(desktop, "NeuroScan_Reports")
        if not os.path.exists(reports_dir):
            try:
                os.makedirs(reports_dir)
            except:
                reports_dir = desktop # Fallback
                
        default_name = f"Report_{self.entry_name.get().replace(' ', '_')}_{datetime.datetime.now().strftime('%Y%m%d')}.pdf"
        
        # Ask save location (defaulting to the new Reports folder)
        save_path = filedialog.asksaveasfilename(defaultextension=".pdf", 
                                                initialdir=reports_dir,
                                                initialfile=default_name,
                                                filetypes=[("PDF Document", "*.pdf")])
        if not save_path: return

        try:
            # 2. Setup Canvas
            c = canvas.Canvas(save_path, pagesize=letter)
            width, height = letter
            
            # 3. Branding Header
            # Draw Logo if exists
            if os.path.exists("logo.png"):
                c.drawImage("logo.png", 50, height - 100, width=50, height=50, preserveAspectRatio=True, mask='auto')
            
            c.setFont("Helvetica-Bold", 24)
            c.setFillColorRGB(0, 0.4, 0.4) # Teal-ish
            c.drawString(110, height - 70, "NeuroScan AI")
            
            c.setFont("Helvetica", 12)
            c.setFillColorRGB(0.5, 0.5, 0.5)
            c.drawString(110, height - 90, "Advanced Medical Diagnostic Report")
            
            c.setStrokeColorRGB(0.8, 0.8, 0.8)
            c.line(50, height - 110, width - 50, height - 110)

            # 4. Patient Info Block
            c.setFont("Helvetica-Bold", 14)
            c.setFillColorRGB(0.2, 0.2, 0.2)
            c.drawString(50, height - 150, "Patient Details")
            
            c.setFont("Helvetica", 12)
            y = height - 180
            c.drawString(50, y, f"Full Name: {self.entry_name.get()}")
            c.drawString(300, y, f"Age: {self.entry_age.get()}")
            y -= 20
            c.drawString(50, y, f"Gender: {self.entry_gender.get()}")
            c.drawString(300, y, f"Phone: {self.entry_phone.get()}")
            y -= 25
            c.drawString(50, y, "Medical History:")
            c.setFont("Helvetica-Oblique", 10)
            history_text = self.entry_history.get("0.0", "end").strip()[:200] # Truncate for one page simple layout
            c.drawString(50, y - 15, history_text if history_text else "None provided.")

            # 5. Diagnostic Results
            y -= 60
            c.setFont("Helvetica-Bold", 14)
            c.setFillColorRGB(0.2, 0.2, 0.2) # Dark Grey
            c.drawString(50, y, "Diagnostic Assessment")
            
            # Result Box
            y -= 30
            c.setFillColorRGB(0.95, 0.97, 1.0) # Light blue bg
            c.rect(50, y - 40, width - 100, 50, fill=1, stroke=0)
            
            c.setFillColorRGB(0, 0, 0)
            c.setFont("Helvetica-Bold", 16)
            c.drawString(70, y - 25, f"Prediction: {self.current_prediction_text}")
            
            c.setFont("Helvetica", 12)
            c.drawString(400, y - 25, f"Confidence: {self.current_confidence_text}")

            # 6. Images
            y -= 80
            c.drawString(50, y, "Brain Imaging Analysis")
            
            # Save temps
            temp_orig = "temp_pdf_orig.jpg"
            temp_heat = "temp_pdf_heat.jpg"
            self.current_original_pil.save(temp_orig)
            self.current_overlay_pil.save(temp_heat)
            
            img_y = y - 220
            c.drawImage(temp_orig, 50, img_y, width=200, height=200, preserveAspectRatio=True)
            c.drawImage(temp_heat, 300, img_y, width=200, height=200, preserveAspectRatio=True)
            
            c.setFont("Helvetica-Oblique", 10)
            c.drawCentredString(150, img_y - 15, "Original Scan")
            c.drawCentredString(400, img_y - 15, "AI Attention Map")

            # 7. Footer / Signature
            doc_name = self.current_user.full_name or self.current_user.username
            c.setFont("Helvetica", 10)
            c.drawCentredString(width/2, 50, f"Report Generated by: Dr./Tech {doc_name} | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
            c.drawCentredString(width/2, 35, "NeuroScan AI Assistive Technology - Verify with Clinical Specialist")

            c.save()
            
            # Cleanup
            try:
                os.remove(temp_orig)
                os.remove(temp_heat)
            except: pass
            
            messagebox.showinfo("Export Success", "Medical Report generated successfully.")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to generate PDF: {e}")

    def create_form_field(self, parent, label):
        ctk.CTkLabel(parent, text=label, font=("Roboto", 12, "bold"), text_color=COLOR_TEXT).pack(anchor="w", padx=10, pady=(10, 0))
        entry = ctk.CTkEntry(parent, height=35)
        entry.pack(fill="x", padx=10, pady=5)
        return entry

    def save_and_export(self):
        # 1. Save to Database
        if self.save_report_db(silent=True):
            # 2. Export PDF
            self.export_pdf_report()
            
    def save_report_db(self, silent=False):
        if not self.current_prediction_text:
            messagebox.showwarning("Incomplete", "Please run a scan first.")
            return False

        # Password Challenge (Only ask if not already authenticated for this session action? 
        # Actually safer to ask every time for signing)
        dialog = ctk.CTkInputDialog(text="Confirm Password to Sign Report:", title="Security Check")
        pwd = dialog.get_input()
        if pwd != self.current_user.password:
            messagebox.showerror("Error", "Incorrect Password")
            return False

        # Save to DB
        session = self.auth.Session()
        try:
            # Prepare Images for BLOB
            def img_to_bytes(pil_img):
                buf = io.BytesIO()
                pil_img.save(buf, format='JPEG')
                return buf.getvalue()

            new_report = Report(
                patient_name=self.entry_name.get(),
                age=self.entry_age.get(),
                gender=self.entry_gender.get(),
                phone=self.entry_phone.get(),
                medical_history=self.entry_history.get("0.0", "end").strip(),
                prediction=self.current_prediction_text,
                confidence=self.current_confidence_text,
                created_by_user_id=self.current_user.id,
                original_image=img_to_bytes(self.current_original_pil),
                heatmap_image=img_to_bytes(self.current_overlay_pil)
            )
            session.add(new_report)
            session.commit()
            
            if not silent:
                messagebox.showinfo("Success", "Report saved to Database successfully.")
            # self.show_dashboard() # REMOVED REDIRECT
            return True
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return False
        finally:
            session.close()

    # =========================================================================
    # HISTORY SCREEN
    # =========================================================================
    def show_history_screen(self):
        self.clear_screen()
        
        # Header
        top_bar = ctk.CTkFrame(self, height=50, fg_color="transparent")
        top_bar.pack(fill="x", padx=20, pady=10)
        ctk.CTkButton(top_bar, text="← Back", width=100, command=self.show_dashboard, fg_color="gray").pack(side="left")
        ctk.CTkLabel(top_bar, text="Previous Medical Reports", font=("Roboto", 20, "bold")).pack(side="left", padx=20)
        
        # Main List
        self.history_frame = ctk.CTkScrollableFrame(self, fg_color=COLOR_WHITE)
        self.history_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Populate
        session = self.auth.Session()
        try:
            reports = session.query(Report).order_by(Report.created_at.desc()).all()
            if not reports:
                ctk.CTkLabel(self.history_frame, text="No reports found in database.").pack(pady=20)
            
            for r in reports:
                self.create_report_row(r)
                
        finally:
            session.close()

    def create_report_row(self, report):
        row = ctk.CTkFrame(self.history_frame, fg_color="#F8FAFC", corner_radius=10)
        row.pack(fill="x", pady=5, padx=5)
        
        # Info
        info = f"Date: {report.created_at.strftime('%Y-%m-%d')} | Patient: {report.patient_name} | Pred: {report.prediction}"
        ctk.CTkLabel(row, text=info, font=("Roboto", 14), text_color=COLOR_TEXT).pack(side="left", padx=15, pady=15)
        
        # View Button
        ctk.CTkButton(row, text="View Details", width=100, 
                    command=lambda r=report: self.show_report_details(r)).pack(side="right", padx=15)

    def show_report_details(self, report):
        # Open a new top-level window
        detail_win = ctk.CTkToplevel(self)
        detail_win.title(f"Report Details: {report.patient_name}")
        detail_win.geometry("800x600")
        detail_win.attributes('-topmost', True)
        
        scroll = ctk.CTkScrollableFrame(detail_win, fg_color=COLOR_WHITE)
        scroll.pack(fill="both", expand=True)
        
        # Text Details
        ctk.CTkLabel(scroll, text="Report Details", font=("Roboto", 20, "bold")).pack(pady=10)
        
        details = f"""
        Patient Name: {report.patient_name}
        Age: {report.age}
        Gender: {report.gender}
        Contact: {report.phone}
        
        Medical History:
        {report.medical_history}
        
        Diagnosis: {report.prediction}
        Confidence: {report.confidence}
        Date: {report.created_at}
        """
        ctk.CTkLabel(scroll, text=details, justify="left", font=("Roboto", 14)).pack(pady=10, padx=20)
        
        # Images (Reconstruct from Bytes)
        img_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        img_frame.pack(pady=20)
        
        try:
            if report.heatmap_image:
                bio = io.BytesIO(report.heatmap_image)
                pil_img = Image.open(bio)
                pil_img.thumbnail((300, 300))
                ctk_img = ctk.CTkImage(pil_img, size=pil_img.size)
                
                ctk.CTkLabel(img_frame, text="AI Analysis").pack()
                ctk.CTkLabel(img_frame, image=ctk_img, text="").pack()
        except Exception as e:
            print(f"Error loading images: {e}")

    # =========================================================================
    # SYSTEM
    # =========================================================================
    def load_model_thread(self):
        threading.Thread(target=self._init_predictor, daemon=True).start()

    def _init_predictor(self):
        try:
            self.predictor = AlzheimerPredictor(self.model_path)
            print("Model Loaded")
        except Exception as e:
            print(f"Model Error: {e}")

if __name__ == "__main__":
    app = MedicalApp()
    app.mainloop()