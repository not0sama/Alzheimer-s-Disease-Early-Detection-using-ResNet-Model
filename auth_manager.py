
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from database import init_db, User
from sqlalchemy.orm import Session
import threading

# Colors
COLOR_PRIMARY = "#00695C"    # Medical Teal
COLOR_SECONDARY = "#546E7A"  # Blue Grey
COLOR_BG = "#F5F7FA"         # Cool Grey-White

class AuthManager:
    def __init__(self, app):
        self.app = app
        self.Session = init_db()
        self.current_user = None
        self._ensure_superadmin()

    def _ensure_superadmin(self):
        """Ensures 'admin' user exists"""
        session = self.Session()
        try:
            admin = session.query(User).filter_by(username="admin").first()
            if not admin:
                print("Creating Superadmin...")
                new_admin = User(
                    username="admin", 
                    password="admin",
                    full_name="Super Admin",
                    specialty="System Administrator"
                )
                session.add(new_admin)
                session.commit()
        finally:
            session.close()

    def login(self, username, password):
        session = self.Session()
        try:
            user = session.query(User).filter_by(username=username).first()
            if user and user.password == password:
                self.current_user = user
                return True, "Login Successful"
            return False, "Invalid Credentials"
        finally:
            session.close()

    def register_user(self, full_name, specialty, phone, username, password):
        session = self.Session()
        try:
            if session.query(User).filter_by(username=username).first():
                return False, "Username already exists"
            
            new_user = User(
                username=username,
                password=password,
                full_name=full_name,
                specialty=specialty,
                phone=phone
            )
            session.add(new_user)
            session.commit()
            return True, "User Registered Successfully"
        except Exception as e:
            return False, str(e)
        finally:
            session.close()

    def get_all_users(self):
        """Returns list of (username, full_name) tuples"""
        session = self.Session()
        try:
            users = session.query(User.username, User.full_name).all()
            return users
        finally:
            session.close()
