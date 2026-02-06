
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from database import init_db, User
from sqlalchemy.orm import Session
import threading
import bcrypt

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
    
    def _hash_password(self, password):
        """Hash a password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def _verify_password(self, password, hashed_password):
        """Verify a password against a hashed password"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

    def _ensure_superadmin(self):
        """Checks if 'admin' user exists and returns whether setup is needed"""
        session = self.Session()
        try:
            admin = session.query(User).filter_by(username="admin").first()
            if not admin:
                return True  # Setup needed
            return False  # Admin exists
        finally:
            session.close()
    
    def create_superadmin(self, username, password, full_name, specialty, phone=""):
        """Creates the super admin account"""
        session = self.Session()
        try:
            # Check if admin already exists
            if session.query(User).filter_by(username=username).first():
                return False, "Admin account already exists"
            
            new_admin = User(
                username=username,
                password=self._hash_password(password),
                full_name=full_name,
                specialty=specialty,
                phone=phone
            )
            session.add(new_admin)
            session.commit()
            return True, "Super Admin account created successfully"
        except Exception as e:
            return False, str(e)
        finally:
            session.close()

    def login(self, username, password):
        session = self.Session()
        try:
            user = session.query(User).filter_by(username=username).first()
            if user and self._verify_password(password, user.password):
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
                password=self._hash_password(password),
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
