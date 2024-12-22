import os 
import auth.gmail_auth
import utils.html_module 
import scraping.scrap_job_blocks
import scraping.scrap_job_elements
import processing.latest_emails
import scraping.overall_scrap
import listener.gmail_listener
import processing.logs
import tkinter as tk
from tkinter import ttk, messagebox, Toplevel
from datetime import datetime
from tkinter.scrolledtext import ScrolledText  # Import ScrolledText for better log display
import threading
import time
from bs4 import BeautifulSoup
from tkinter import ttk, messagebox, Toplevel
from datetime import datetime
import threading
import os
import subprocess

SEARCH_SENDERS = ["malikhqtech@gmail.com", "alert@indeed.com", "noreply@example.com"] 
LABEL_NAME_SUCCESS = "fetched_by_app"
LABEL_NAME_FAILURE = "fetch_failed_for_job_app"
ERROR_NOTIFICATION_EMAIL = "malikhqtech@gmail.com"
is_fetching = False
fetch_thread = None



class EmailProcessingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Email Processing App")
        self.is_fetching = False
        self.service = None  # Gmail API service
        self.email_address = None  # Email address of the signed-in user
        self.root.configure(bg="#f7f9fc")  # Subtle light background

        # Configure window close event
        self.root.protocol("WM_DELETE_WINDOW", self.confirm_exit)

        # Frame for Gmail Actions
        gmail_frame = tk.LabelFrame(root, text="Gmail Actions", padx=10, pady=10, bg="#ffffff", font=("Arial", 10, "bold"))
        gmail_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        self.auth_button = tk.Button(gmail_frame, text="Sign In", command=self.handle_sign_in_out, bg="#d4edda", fg="#155724", font=("Arial", 10, "bold"), relief="raised")
        self.auth_button.grid(row=0, column=0, padx=5, pady=5)

        self.status_label = tk.Label(gmail_frame, text="Not Signed In", fg="#721c24", bg="#ffffff", font=("Arial", 10))
        self.status_label.grid(row=0, column=1, padx=10, pady=5, sticky="w")

        # Start/Stop Fetching Button
        action_frame = tk.LabelFrame(root, text="Actions", padx=10, pady=10, bg="#ffffff", font=("Arial", 10, "bold"))
        action_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        self.fetch_button = tk.Button(action_frame, text="Start Fetching", command=self.handle_fetching, state="disabled", bg="#cce5ff", fg="#004085", font=("Arial", 10, "bold"), relief="raised")
        self.fetch_button.grid(row=0, column=0, padx=5, pady=5)

        self.fetch_status_label = tk.Label(action_frame, text="Not Fetching", fg="#721c24", bg="#ffffff", font=("Arial", 10))
        self.fetch_status_label.grid(row=0, column=1, padx=10, pady=5, sticky="w")

        # Log Buttons Section
        log_frame = tk.LabelFrame(root, text="Logs", padx=10, pady=10, bg="#ffffff", font=("Arial", 10, "bold"))
        log_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        self.ui_log_button = tk.Button(log_frame, text="UI Log", command=lambda: threading.Thread(target=self.open_log_window, args=("UI Logs",), daemon=True).start(), bg="#e2e3e5", fg="#383d41", font=("Arial", 10, "bold"), relief="raised")
        self.ui_log_button.pack(side="left", padx=5, pady=5)

        self.daily_log_button = tk.Button(log_frame, text="Daily Log", command=lambda: threading.Thread(target=self.open_log_directory, args=("./logs/daily",), daemon=True).start(), bg="#e2e3e5", fg="#383d41", font=("Arial", 10, "bold"), relief="raised")
        self.daily_log_button.pack(side="left", padx=5, pady=5)

        self.monthly_log_button = tk.Button(log_frame, text="Monthly Log", command=lambda: threading.Thread(target=self.open_log_directory, args=("./logs/monthly",), daemon=True).start(), bg="#e2e3e5", fg="#383d41", font=("Arial", 10, "bold"), relief="raised")
        self.monthly_log_button.pack(side="left", padx=5, pady=5)

        self.logs = []

    def log(self, message):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        self.logs.append((timestamp, message))
        print(f"[LOG] {timestamp}: {message}")  # Debug output

    def open_log_directory(self, path):
        try:
            if os.path.exists(path):
                subprocess.Popen(f'explorer {os.path.realpath(path)}')
            else:
                messagebox.showerror("Error", f"Directory not found: {path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open directory: {e}")

    def handle_sign_in_out(self):
        self.auth_button.config(state="disabled")
        threading.Thread(target=self.toggle_sign_in_out, daemon=True).start()

    def toggle_sign_in_out(self):
        if self.service:
            self.confirm_action("Sign Out")
        else:
            self.gmail_sign_in()
        self.auth_button.config(state="normal")

    def gmail_sign_in(self):
        self.status_label.config(text="Signing In...", fg="#ffc107")
        try:
            self.service = auth.gmail_auth.authenticate_gmail()
            self.email_address = auth.gmail_auth.get_account_email(self.service)
            sign_in_time = datetime.now().strftime('%Y-%m-%d %H:%M')
            self.status_label.config(text=f"Signed in as: {self.email_address} at {sign_in_time}", fg="#155724")
            self.auth_button.config(text="Sign Out", bg="#f8d7da", fg="#721c24")
            self.fetch_button.config(state="normal")
            self.log(f"Signed in as {self.email_address} at {sign_in_time}.")
        except Exception as e:
            self.status_label.config(text="Sign In Failed", fg="#721c24")
            self.log(f"Error during sign in: {e}")
            messagebox.showerror("Error", f"Sign In failed: {e}")

    def confirm_action(self, action):
        confirmation_dialog = Toplevel(self.root)
        confirmation_dialog.title(f"Confirm {action}")
        tk.Label(confirmation_dialog, text=f"To confirm {action}, enter the keyword 'Kush Raho'").pack(pady=10)
        keyword_entry = tk.Entry(confirmation_dialog)
        keyword_entry.pack(pady=5)

        def validate_action():
            if keyword_entry.get() == "Kush Raho":
                confirmation_dialog.destroy()
                if action == "Sign Out":
                    self.gmail_sign_out()
                elif action == "Stop Fetching":
                    self.stop_fetching()
                elif action == "Exit":
                    self.send_notification_email(ERROR_NOTIFICATION_EMAIL,f"Application Closed by User at {datetime.now()}")
                    self.root.destroy()
            else:
                messagebox.showerror("Error", "Incorrect keyword. Action canceled.")

        tk.Button(confirmation_dialog, text="Confirm", command=validate_action).pack(pady=10)

    def confirm_exit(self):
        self.confirm_action("Exit")

    def handle_fetching(self):
        self.fetch_button.config(state="disabled")
        threading.Thread(target=self.toggle_fetching, daemon=True).start()

    def toggle_fetching(self):
        if self.is_fetching:
            self.confirm_action("Stop Fetching")
        else:
            self.start_fetching()
        self.fetch_button.config(state="normal")

    def start_fetching(self):
        self.fetch_status_label.config(text="Starting Fetching...", fg="#ffc107")
        try:
            self.is_fetching = True
            self.fetch_button.config(text="Stop Fetching", bg="#f8d7da", fg="#721c24")
            self.fetch_status_label.config(text="Fetching Started", fg="#155724")
            self.log("Fetching started...")
            listener.gmail_listener.start_email_fetch(self.service, SEARCH_SENDERS, ERROR_NOTIFICATION_EMAIL)
        except Exception as e:
            self.fetch_status_label.config(text="Error Fetching", fg="#721c24")
            self.log(f"Error during fetching: {e}")
            messagebox.showerror("Error", f"Fetching failed: {e}")

    def stop_fetching(self):
        self.fetch_status_label.config(text="Stopping Fetching...", fg="#ffc107")
        try:
            listener.gmail_listener.stop_email_fetch()
            self.is_fetching = False
            self.fetch_button.config(text="Start Fetching", bg="#cce5ff", fg="#004085")
            self.fetch_status_label.config(text="Fetching Stopped", fg="#721c24")
            self.log("Fetching process stopped.")
            self.send_notification_email(ERROR_NOTIFICATION_EMAIL,"Fetching stopped by user.")
        except Exception as e:
            self.fetch_status_label.config(text="Error Stopping", fg="#721c24")
            self.log(f"Error during stopping fetch: {e}")
            messagebox.showerror("Error", f"Stopping fetching failed: {e}")

    # def send_notification_email(self, body):
    #     if not self.service:
    #         return
    #     try:
    #         subject = f"Job Scraper Stopped {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    #         # Replace with actual email-sending code using Gmail API
    #         print(f"Sending email to {ERROR_NOTIFICATION_EMAIL}: {subject}\n{body}")
    #     except Exception as e:
    #         print(f"Error sending email: {e}")

    def open_log_window(self, title):
        log_window = Toplevel(self.root)
        log_window.title(title)

        text_widget = ScrolledText(log_window, wrap=tk.WORD, font=("Arial", 10))
        text_widget.pack(fill="both", expand=True)

        for entry in self.logs:
            text_widget.insert(tk.END, f"{entry[0]} - {entry[1]}\n")
    
    def send_notification_email(self, recipient, description):
        """
        Sends a simple notification email using the Gmail service object.
    
        Args:
            service: The Gmail API service object for sending emails.
            recipient (str): The email address to send the notification to.
            description (str): A short description to include in the email content.
    
        Example:
            self.send_notification_email(service, "example@gmail.com", "Job Scraper was interrupted unexpectedly.")
        """
        service =  auth.gmail_auth.authenticate_gmail()
        if not service:
            self.log("Cannot send email: Gmail service object is not provided.")
            return
    
        if not recipient:
            self.log("Cannot send email: Recipient email address is missing.")
            return
    
        try:
            from email.mime.text import MIMEText
            import base64
    
            # Construct the email
            subject = "Job Scraper Has Been Interrupted"
            content = f"""
            Dear User,
    
            The job scraper has been interrupted. Below is the description of the issue:
    
            {description}
    
            Please take necessary action to resolve the issue.
    
            Regards,
            Job Scraper Application
            """
            message = MIMEText(content)  # Construct the email body with the description
            message['to'] = recipient
            message['from'] = "<Your Service Authenticated Email>"  # Replace with authenticated email address
            message['subject'] = subject
    
            # Encode the message in base64
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
            message_body = {'raw': raw_message}
    
            # Log the preparation step
            self.log(f"Preparing to send email to {recipient} with subject: {subject}")
    
            # Send the email
            service.users().messages().send(userId='me', body=message_body).execute()
            self.log(f"Notification email successfully sent to {recipient}.")
        except Exception as e:
            error_message = f"Failed to send email to {recipient}: {e}"
            self.log(error_message)
            print(f"Error sending email: {e}")


if __name__ == "__main__":
    processing.logs.configure_logging()  # Ensure logging is properly set up
    root = tk.Tk()
    app = EmailProcessingApp(root)
    root.mainloop()

    