import logging
import os
import sys
import threading
import time
import tkinter as tk
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tkinter import ttk, messagebox

import pytz
import requests
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
# Removed webdriver_manager import - Selenium 4.6+ handles this automatically
# from webdriver_manager.chrome import ChromeDriverManager


class BereaRegistrationBot:
    # --- Constants ---
    BEREA_LOGIN_URL = "https://b9student-prod.berea.edu:8444/StudentRegistrationSsb/ssb/registration/registration"
    BEREA_TERM_URL = "https://b9student-prod.berea.edu:8444/StudentRegistrationSsb/ssb/term/termSelection?mode=registration"
    LOCAL_TIMEZONE = "America/New_York"

    def __init__(self):
        # --- Pathing for .exe / .py ---
        if getattr(sys, 'frozen', False):
            self.base_dir = Path(sys.executable).parent
        else:
            self.base_dir = Path(__file__).parent

        # Define file paths
        self.log_dir = self.base_dir / "logs"
        self.config_file = self.base_dir / "config.txt"
        self.crns_file = self.base_dir / "crns.txt"

        # --- Logging Setup ---
        self.log_dir.mkdir(exist_ok=True)
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_dir / f"registration_{current_time}.log"

        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.FileHandler(log_file), logging.StreamHandler()]
        )

        # Check if config files exist. If not, create them and exit.
        config_exists = self.config_file.exists()
        crns_exist = self.crns_file.exists()

        if not config_exists:
            self._create_template_config()
        if not crns_exist:
            self._create_template_crns()

        if not config_exists or not crns_exist:
            logging.warning("Initial setup: config/crns files were created. Shutting down.")
            messagebox.showinfo("Setup Required",
                                "Welcome! I've created `config.txt` and `crns.txt` for you.\n\n"
                                "Please open them, fill in your information, and then run me again.")
            sys.exit(0)  # Cleanly exit after informing the user

        # --- Load Config and CRNs (only if they exist) ---
        try:
            self.config = self.load_config()
            self.crns = self.load_crns()
        except (FileNotFoundError, ValueError) as e:
            logging.error(f"Initialization failed: {e}")
            messagebox.showerror("Error", f"Initialization failed: {e}")
            sys.exit(1)

        # --- Bot State ---
        self.driver = None
        self.wait = None
        self.scheduler_window = None

    def _create_template_config(self):
        """Creates a template config.txt file for the user."""
        logging.info("Creating template config.txt...")
        template_content = """# --- User Credentials ---
# Please fill in your Berea username, password, and registration PIN
USERNAME=your_username_here
PASSWORD=your_password_here
PIN=your_pin_here

# --- Term Information ---
# Find this in the website's HTML source (e.g., 202510 for Fall 2025)
TERM_ID=
# Find this in the dropdown (e.g., Fall 2025)
TERM_TEXT=

# --- Bot Settings ---
# Run in headless (no browser window) mode? (true/false)
HEADLESS=false
# Intentionally slow down the connection for testing? (true/false)
THROTTLE_SPEED=false
# Registration date (YYYY-MM-DD). Only used for throttling logic.
REGISTRATION_DATE=2025-11-05
"""
        try:
            with open(self.config_file, 'w') as f:
                f.write(template_content)
            logging.info(f"Created: {self.config_file}")
        except Exception as e:
            logging.error(f"Failed to create config.txt: {e}")
            messagebox.showerror("File Error", f"Failed to create config.txt: {e}")

    def _create_template_crns(self):
        """Creates a template crns.txt file for the user."""
        logging.info("Creating template crns.txt...")
        template_content = """# Add your 5-digit CRNs below, one per line.
# Example:
# 12345
# 67890
"""
        try:
            with open(self.crns_file, 'w') as f:
                f.write(template_content)
            logging.info(f"Created: {self.crns_file}")
        except Exception as e:
            logging.error(f"Failed to create crns.txt: {e}")
            messagebox.showerror("File Error", f"Failed to create crns.txt: {e}")

    def _create_driver(self):
        """Creates and configures the Chrome webdriver instance."""
        try:
            logging.info("Setting up Chrome driver...")
            chrome_options = Options()
            chrome_options.add_argument("--incognito")

            if self.config['HEADLESS']:
                logging.info("Running in HEADLESS mode.")
                chrome_options.add_argument("--headless")
                chrome_options.add_argument("--window-size=1920,1080")


            print("Initializing Chrome driver...")
            # --- FIX 1: Use Selenium's built-in driver manager ---
            # This line automatically downloads and manages the correct chromedriver
            # service = Service(ChromeDriverManager().install()) # This is the old, broken line
            service = Service() # This lets Selenium 4.6+ manage the driver
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            # --- End Fix 1 ---

            if self.config['THROTTLE_SPEED']:
                reg_date = self.config['REGISTRATION_DATE']
                if datetime.now().date() != reg_date.date():
                    logging.warning("ENABLING NETWORK THROTTLING FOR TESTING.")
                    self.driver.execute_cdp_cmd('Network.enable', {})
                    self.driver.execute_cdp_cmd('Network.emulateNetworkConditions', {
                        'offline': False,
                        'downloadThroughput': 50 * 1024,
                        'uploadThroughput': 50 * 1024,
                        'latency': 500
                    })
                else:
                    logging.info("Registration day. Throttling is disabled.")

            self.wait = WebDriverWait(self.driver, 20)
            logging.info("Driver setup complete.")

        except Exception as e:
            logging.error(f"Failed to create webdriver: {e}", exc_info=True)
            logging.error("Please ensure Google Chrome is installed and up to date.")
            messagebox.showerror("Driver Error",
                                 f"Failed to create webdriver: {e}\nPlease ensure Google Chrome is installed and up to date.")
            raise

    def create_scheduler_window(self):
        """Create the scheduler GUI window"""
        self.scheduler_window = tk.Tk()
        self.scheduler_window.title("Registration Scheduler")
        self.scheduler_window.geometry("400x300")

        main_frame = ttk.Frame(self.scheduler_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        time_frame = ttk.LabelFrame(main_frame, text="Registration Time", padding="10")
        time_frame.pack(fill=tk.X, pady=(0, 20))

        time_controls = ttk.Frame(time_frame)
        time_controls.pack(fill=tk.X)

        hour_frame = ttk.Frame(time_controls)
        hour_frame.pack(side=tk.LEFT, padx=10)
        ttk.Label(hour_frame, text="Hour (0-23):").pack(side=tk.LEFT)
        self.hour_var = tk.StringVar(value="7")
        ttk.Spinbox(hour_frame, from_=0, to=23, width=3, textvariable=self.hour_var).pack(side=tk.LEFT, padx=5)

        minute_frame = ttk.Frame(time_controls)
        minute_frame.pack(side=tk.LEFT, padx=10)
        ttk.Label(minute_frame, text="Minute:").pack(side=tk.LEFT)
        self.minute_var = tk.StringVar(value="30")
        ttk.Spinbox(minute_frame, from_=0, to=59, width=3, textvariable=self.minute_var).pack(side=tk.LEFT, padx=5)

        second_frame = ttk.Frame(time_controls)
        second_frame.pack(side=tk.LEFT, padx=10)
        ttk.Label(second_frame, text="Second:").pack(side=tk.LEFT)
        self.second_var = tk.StringVar(value="0")
        ttk.Spinbox(second_frame, from_=0, to=59, width=3, textvariable=self.second_var).pack(side=tk.LEFT, padx=5)

        self.status_var = tk.StringVar(value="Ready to start...")
        status_label = ttk.Label(main_frame, textvariable=self.status_var)
        status_label.pack(fill=tk.X, pady=20)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=20)

        self.start_time_btn = ttk.Button(button_frame, text="Start at Set Time", command=self.start_at_time)
        self.start_time_btn.pack(side=tk.LEFT, padx=5)

        self.start_now_btn = ttk.Button(button_frame, text="Start Immediately", command=self.start_immediately)
        self.start_now_btn.pack(side=tk.LEFT, padx=5)

        self.scheduler_window.mainloop()

    def wait_for_server_ready(self, target_time_local, poll_frequency=0.1, timeout=300):
        """
        Wait until the server's reported time (via its Date header) reaches or exceeds the target time.
        """
        try:
            local_tz = pytz.timezone(self.LOCAL_TIMEZONE)
            target_time_with_tz = local_tz.localize(target_time_local)
            target_time_utc = target_time_with_tz.astimezone(pytz.utc)

            logging.info("Pinging server to get time offset...")
            response = requests.head(self.BEREA_TERM_URL)
            date_header = response.headers.get("Date")
            if not date_header:
                logging.warning("No Date header found in server response. Proceeding without server time sync.")
                return True

            server_time_utc = datetime.strptime(date_header, "%a, %d %b %Y %H:%M:%S GMT").replace(tzinfo=pytz.utc)
            local_utc_now = datetime.now(timezone.utc)
            offset_seconds = (server_time_utc - local_utc_now).total_seconds()

            # This is the server's clock time (in UTC) that we are aiming for
            target_server_time_utc = target_time_utc - timedelta(seconds=offset_seconds)

            logging.info(f"Time offset between server and local UTC time: {offset_seconds:.2f} seconds")
            logging.info(
                f"Local target {target_time_local.strftime('%H:%M:%S')} corresponds to server time {target_server_time_utc.strftime('%H:%M:%S')} UTC")
            logging.info(f"Waiting for server time to reach target...")

            end_time = time.time() + timeout

            while time.time() < end_time:
                try:
                    response = requests.head(self.BEREA_TERM_URL)
                    date_header = response.headers.get("Date")
                    if date_header:
                        server_time = datetime.strptime(date_header, "%a, %d %b %Y %H:%M:%S GMT").replace(
                            tzinfo=pytz.utc)

                        logging.debug(f"Current Server Time: {server_time.strftime('%H:%M:%S.%f')} UTC")

                        if server_time >= target_server_time_utc:
                            logging.info("Server time reached target. Proceeding.")
                            return True
                except Exception as e:
                    logging.error(f"Error retrieving server time: {e}")
                time.sleep(poll_frequency)

            logging.warning("Timeout reached while waiting for server time.")


        except Exception as e:
            logging.error(f"Error in wait_for_server_ready: {e}")


    def calibrate_dynamic_buffer(self, num_trials=1, margin=0.05, min_buffer=0.5, max_buffer=1):
        """
        Run several HEAD requests to the registration URL to measure the network delay.
        """
        delays = []
        for i in range(num_trials):
            start = time.time()
            try:
                requests.head(self.BEREA_TERM_URL)
            except Exception as e:
                logging.error(f"Calibration trial {i + 1} error: {e}")
                continue
            delay = time.time() - start
            delays.append(delay)

        if delays:
            delays.sort()
            median_delay = delays[len(delays) // 2]
            calibrated_buffer = median_delay + margin
            calibrated_buffer = max(min_buffer, min(calibrated_buffer, max_buffer))
            logging.info(
                f"Calibration: median delay: {median_delay:.3f} sec, using dynamic buffer: {calibrated_buffer:.3f} sec")
            return calibrated_buffer
        else:
            logging.warning("Calibration failed; using default buffer of 0.3 sec")
            return 0.3

    def validate_time(self):
        """Validate the time inputs"""
        try:
            hour = int(self.hour_var.get())
            minute = int(self.minute_var.get())
            second = int(self.second_var.get())

            if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
                raise ValueError("Time values are out of range.")
            return hour, minute, second

        except ValueError:
            messagebox.showerror("Error", "Please enter valid time values (H: 0-23, M/S: 0-59)")
            return None

    def log_submission_times(self):
        """Logs current UTC/local time and server time offset for comparison."""
        try:
            local_tz = pytz.timezone(self.LOCAL_TIMEZONE)
            local_now = datetime.now(local_tz)
            utc_now = datetime.now(timezone.utc)

            response = requests.head(self.BEREA_TERM_URL)
            server_date = response.headers.get("Date")

            if server_date:
                server_utc = datetime.strptime(server_date, "%a, %d %b %Y %H:%M:%S GMT").replace(tzinfo=pytz.utc)
                server_local = server_utc.astimezone(local_tz)
                delay = (server_utc - utc_now).total_seconds()
            else:
                server_utc = server_local = None
                delay = "N/A"

            submission_log_file = self.log_dir / "submission_times.log"
            with open(submission_log_file, "a") as f:
                f.write(f"\n=== Submission Log ({datetime.now().isoformat()}) ===\n")
                f.write(
                    f"Server UTC:      {server_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC\n" if server_utc else "Server UTC:      Not Available\n")
                f.write(f"Local UTC:       {utc_now.strftime('%Y-%m-%d %H:%M:%S')} UTC\n")
                f.write(f"Local Local:     {local_now.strftime('%Y-%m-%d %H:%M:%S %Z')}\n")
                f.write(
                    f"Server Local:    {server_local.strftime('%Y-%m-%d %H:%M:%S %Z')}\n" if server_local else "Server Local:    Not Available\n")
                f.write(f"Delay (seconds): {delay if isinstance(delay, str) else f'{delay:.3f}'} sec\n")
                f.write(f"{'-' * 40}\n")
        except Exception as e:
            logging.error(f"Failed to log submission times: {e}")

    def start_at_time(self):
        """Start registration at specified time"""
        time_values = self.validate_time()
        if time_values is None:
            return

        hour, minute, second = time_values
        target_time = datetime.now().replace(hour=hour, minute=minute, second=second, microsecond=0)

        if target_time < datetime.now():
            messagebox.showerror("Error", "Please set a future time")
            return

        self.status_var.set(f"Waiting for {target_time.strftime('%H:%M:%S')}")
        self.schedule_registration(target_time)

    def start_immediately(self):
        """Start registration immediately"""
        self.status_var.set("Starting registration immediately...")
        self.schedule_registration(None)

    def _update_status_safe(self, message):
        """Helper function to safely update the GUI status label from any thread."""
        if self.scheduler_window:
            # Schedules self.status_var.set(message) to run on the main GUI thread
            self.scheduler_window.after(0, self.status_var.set, message)

    def _show_message_safe(self, title, message, mtype='info'):
        """Helper function to safely show a messagebox from any thread."""
        if self.scheduler_window:
            if mtype == 'info':
                self.scheduler_window.after(0, messagebox.showinfo, title, message)
            elif mtype == 'error':
                self.scheduler_window.after(0, messagebox.showerror, title, message)

    def _reenable_buttons_safe(self):
        """Helper function to safely re-enable GUI buttons from any thread."""

        def reenable():
            self.start_time_btn.config(state='normal')
            self.start_now_btn.config(state='normal')

        if self.scheduler_window:
            self.scheduler_window.after(0, reenable)

    def schedule_registration(self, target_time):
        """Schedule and run the registration process in a separate thread."""
        self.start_time_btn.config(state='disabled')
        self.start_now_btn.config(state='disabled')

        self.status_var.set("Starting browser...")
        self.scheduler_window.update_idletasks()  # Force GUI to update now

        def run_registration():
            try:
                # The first log message should now be the *very* first thing
                # the thread does, and it will appear in your console.
                self._create_driver()

                self._update_status_safe("Logging in...")
                if not self.login():
                    raise Exception("Login failed. Check credentials in config.txt.")

                self._update_status_safe("Selecting term...")
                if not self.select_term():
                    raise Exception("Term selection failed. Check TERM_ID and TERM_TEXT in config.txt.")

                self._update_status_safe("Entering PIN...")
                if not self.enter_pin_only():
                    raise Exception("Entering PIN failed.")

                # --- START: New "Poll-and-Sleep" Logic ---
                if target_time:
                    self._update_status_safe(f"Waiting for {target_time.strftime('%H:%M:%S')}...")
                    logging.info(f"Target local time set for: {target_time}")

                    # 1. Polite Polling Logic
                    FINAL_POLL_BUFFER_SECONDS = 25.0  # Poll-twice logic buffer
                    target_minus_buffer = target_time - timedelta(seconds=FINAL_POLL_BUFFER_SECONDS)

                    now = datetime.now()
                    while now < target_minus_buffer:
                        remaining = (target_minus_buffer - now).total_seconds()

                        # Determine sleep duration based on remaining time
                        if remaining > 30:
                            sleep_duration = 30  # Poll every 30s
                            self._update_status_safe(f"Waiting... (T-{remaining:.0f}s)")
                        elif remaining > 5:
                            sleep_duration = 5   # Poll every 5s
                            self._update_status_safe(f"Waiting... (T-{remaining:.0f}s)")
                        else:
                            sleep_duration = 0.5 # Poll every 0.5s in the last few seconds

                        time.sleep(sleep_duration)
                        now = datetime.now()

                    # 2. "Poll Twice" (Final Poll)
                    self._update_status_safe(f"Final sync (T-{FINAL_POLL_BUFFER_SECONDS}s)...")
                    logging.info(f"Reached T-{FINAL_POLL_BUFFER_SECONDS}s. Polling server for final time sync.")

                    try:
                        # Get server time *once* to calculate offset
                        response = requests.head(self.BEREA_TERM_URL)
                        date_header = response.headers.get("Date")
                        if not date_header:
                            raise Exception("No Date header found in server response.")

                        server_time_utc = datetime.strptime(date_header, "%a, %d %b %Y %H:%M:%S GMT").replace(tzinfo=pytz.utc)
                        local_utc_now = datetime.now(timezone.utc)
                        offset_seconds = (server_time_utc - local_utc_now).total_seconds()

                        logging.info(f"Server time offset: {offset_seconds:.3f} seconds.")

                        # Convert local target time to UTC
                        local_tz = pytz.timezone(self.LOCAL_TIMEZONE)
                        target_time_with_tz = local_tz.localize(target_time)
                        target_time_utc = target_time_with_tz.astimezone(pytz.utc)

                        # Determine the *local* UTC time we need to submit at
                        # (This is the target server time, adjusted by the offset)
                        target_local_time_as_utc = target_time_utc - timedelta(seconds=offset_seconds)

                        # 3. "Add a Delay" (Final Local Sleep)
                        remaining_sleep_seconds = (target_local_time_as_utc - datetime.now(timezone.utc)).total_seconds()

                        if remaining_sleep_seconds > 0:
                            logging.info(f"Calculated final sleep: {remaining_sleep_seconds:.4f} seconds.")
                            self._update_status_safe(f"Final sleep: {remaining_sleep_seconds:.3f}s")
                            time.sleep(remaining_sleep_seconds)
                        else:
                            logging.warning(f"Offset calculation resulted in zero/negative sleep ({remaining_sleep_seconds:.4f}s). Submitting immediately.")

                    except Exception as e:
                        logging.error(f"Final server time sync failed: {e}. Proceeding with local time.")
                        # Fallback: just sleep until the local target time
                        remaining_local_sleep = (target_time - datetime.now()).total_seconds()
                        if remaining_local_sleep > 0:
                            time.sleep(remaining_local_sleep)

                    self._update_status_safe("Submitting PIN...")
                    self.submit_pin_form()
                    self.log_submission_times()
                else:
                    # This is the "Start Immediately" logic
                    self._update_status_safe("Submitting PIN...")
                    self.submit_pin_form()
                # --- END: New "Poll-and-Sleep" Logic ---

                self._update_status_safe("Entering CRNs...")
                if not self.enter_crns():
                    raise Exception("Failed to enter CRNs.")

                self._update_status_safe("Submitting registration...")
                success = self.submit_registration()

                if success:
                    self._update_status_safe("Registration completed successfully!")
                    self._show_message_safe("Success", "Registration completed successfully!", mtype='info')
                else:
                    self._update_status_safe("Registration failed or had errors. Check logs.")
                    self._show_message_safe("Error", "Registration failed or had errors. Check logs.", mtype='error')

            except Exception as e:
                error_msg = f"Error: {str(e)}"
                logging.error(f"Registration thread error: {e}", exc_info=True)
                self._update_status_safe(error_msg)
                self._show_message_safe("Error", error_msg, mtype='error')
            finally:
                self._reenable_buttons_safe()
                if self.driver:
                    logging.info("Registration thread finished. Waiting 30 seconds before closing browser...")
                    time.sleep(600)  # <-- ADDED DELAY to 10 minutes for user to inspect results.
                    self.driver.quit()
                    self.driver = None

        thread = threading.Thread(target=run_registration)
        thread.daemon = True
        thread.start()

    def load_config(self):
        """Load configuration from config.txt file."""
        config_path = self.config_file
        # No need to check for existence, __init__ already did

        config = {}
        with open(config_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip().upper()] = value.strip()

        required_fields = ['USERNAME', 'PASSWORD', 'PIN', 'TERM_ID', 'TERM_TEXT']
        missing_fields = [field for field in required_fields if field not in config or not config[field]]

        if missing_fields:
            raise ValueError(f"Missing or empty required fields in config.txt: {', '.join(missing_fields)}")

        # Parse settings and store them in lowercase
        parsed_config = {}
        parsed_config['username'] = config.pop('USERNAME')
        parsed_config['password'] = config.pop('PASSWORD')
        parsed_config['pin'] = config.pop('PIN')
        parsed_config['term_id'] = config.pop('TERM_ID')
        parsed_config['term_text'] = config.pop('TERM_TEXT')

        parsed_config['HEADLESS'] = config.get('HEADLESS', 'false').lower() == 'true'
        parsed_config['THROTTLE_SPEED'] = config.get('THROTTLE_SPEED', 'false').lower() == 'true'
        try:
            parsed_config['REGISTRATION_DATE'] = datetime.strptime(config.get('REGISTRATION_DATE', ''), "%Y-%m-%d")
        except ValueError:
            parsed_config['REGISTRATION_DATE'] = datetime.now()  # Default to today
            if parsed_config['THROTTLE_SPEED']:
                logging.warning(
                    "Invalid or missing REGISTRATION_DATE in config.txt. Throttling may behave unexpectedly.")

        logging.info("Configuration loaded successfully from config.txt")
        return parsed_config

    def load_crns(self):
        """Load CRNs from crns.txt file."""
        crns_path = self.crns_file
        # No need to check for existence, __init__ already did

        try:
            with open(crns_path, 'r') as f:
                crns = [line.strip() for line in f if line.strip() and not line.startswith('#')]

            if not crns:
                raise ValueError("crns.txt is empty. Please add your CRNs.")

            invalid_crns = [crn for crn in crns if not (len(crn) == 5 and crn.isdigit())]
            if invalid_crns:
                raise ValueError(f"Invalid CRNs found: {', '.join(invalid_crns)}. Each CRN must be 5 digits.")

            logging.info(f"Successfully loaded {len(crns)} CRNs from crns.txt")
            return crns

        except Exception as e:
            logging.error(f"Error loading CRNs: {str(e)}")
            raise

    def enter_crns(self):
        try:
            add_button = self.wait.until(EC.element_to_be_clickable((By.ID, "addAnotherCRN")))

            for i in range(len(self.crns) - 1):
                add_button.click()
                # Wait for the *new* box to appear before trying to click again
                self.wait.until(EC.presence_of_element_located((By.ID, f"txt_crn{i + 2}")))

            for i, crn in enumerate(self.crns, 1):
                field = self.wait.until(EC.presence_of_element_located((By.ID, f"txt_crn{i}")))
                field.clear()
                field.send_keys(crn)

            self.wait.until(EC.element_to_be_clickable((By.ID, "addCRNbutton"))).click()
            logging.info("CRNs entered and 'Add to Summary' clicked.")
            return True

        except Exception as e:
            logging.error(f"CRN entry failed: {str(e)}")


    def login(self):
        try:
            self.driver.get(self.BEREA_LOGIN_URL)

            register_btn = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//span[contains(@class, 'title') and text()='Register for Classes']")))
            register_btn.click()

            username_field = self.wait.until(EC.presence_of_element_located((By.ID, "name")))
            username_field.clear()
            username_field.send_keys(self.config['username'])

            password_field = self.driver.find_element(By.ID, "password")
            password_field.clear()
            password_field.send_keys(self.config['password'])

            self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[name='_eventId_proceed']"))).click()

            if not self.handle_duo_auth():
                raise Exception("DUO authentication failed or timed out")

            logging.info("Login successful.")
            return True
        except Exception as e:
            logging.error(f"Login failed: {e}")
            return False

    # --- FIX 2: Replaced with the robust DUO auth logic ---
    def handle_duo_auth(self):
        try:
            logging.info("Starting DUO authentication process...")

            # Initial wait for any DUO-related content
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "#duo_iframe, .device-health-check, .card--white-label")))

            # Wait for term selector with periodic checks
            success = False
            timeout = time.time() + 300  # 5 minute timeout

            while time.time() < timeout and not success:
                try:
                    # Check if we've reached the term selector
                    term_selector = self.driver.find_element(By.ID, "s2id_txt_term")
                    if term_selector.is_displayed():
                        success = True
                        break
                except:
                    # Still in DUO process
                    time.sleep(2)
                    continue

            if not success:
                raise Exception("DUO authentication timed out")

            logging.info("DUO authentication completed successfully")
            time.sleep(2)  # Brief pause after completion
            return True

        except Exception as e:
            logging.error(f"DUO authentication failed: {str(e)}")

            return False
    # --- End Fix 2 ---

    def select_term(self):
        try:
            term_selector = self.wait.until(EC.element_to_be_clickable((By.ID, "select2-chosen-1")))
            term_selector.click()

            term_input = self.wait.until(EC.presence_of_element_located((By.ID, "s2id_autogen1_search")))

            term_id = self.config['term_id']
            term_text = self.config['term_text']

            term_input.clear()
            term_input.send_keys(term_text)

            term_option = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, f"//div[@id='{term_id}' and contains(text(), '{term_text}')]")))
            term_option.click()

            # Verification
            selected_term = self.wait.until(EC.presence_of_element_located((By.ID, "select2-chosen-1"))).text
            if term_text not in selected_term:
                raise Exception(f"Term selection verification failed. Expected '{term_text}', got '{selected_term}'")

            logging.info(f"Selected term: {term_text} (ID: {term_id})")
            return True

        except Exception as e:
            logging.error(f"Term selection failed: {str(e)}")


    def submit_pin_form(self):
        try:
            term_go = self.wait.until(EC.element_to_be_clickable((By.ID, "term-go")))
            term_go.click()
            logging.info("PIN form submitted successfully")

            # Handle the notification that *sometimes* appears
            try:
                notification_buttons = WebDriverWait(self.driver, 2).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "button.notification-flyout-item.primary"))
                )
                if notification_buttons:
                    ok_button = notification_buttons[0]
                    if ok_button.is_displayed() and ok_button.is_enabled():
                        logging.info("Dismissing 'You are registered' notification.")
                        ok_button.click()
            except TimeoutException:
                logging.info("No notification popup after PIN submit. Proceeding.")

            logging.info("Waiting for CRN entry page to load...")

            # 1. Wait for the tab to be clickable and click it
            crn_tab = self.wait.until(EC.element_to_be_clickable((By.ID, "enterCRNs-tab")))
            crn_tab.click()

            # 2. Wait for the *content* of that tab (the first CRN box) to be present.
            # This makes it bulletproof.
            self.wait.until(EC.presence_of_element_located((By.ID, "txt_crn1")))

            logging.info("CRN entry page is loaded and ready.")
            return True
        except Exception as e:
            logging.error(f"Failed to submit PIN form: {e}")


    def enter_pin_only(self):
        try:
            pin_field = self.wait.until(EC.element_to_be_clickable((By.ID, "input_alt_pin")))
            pin_field.clear()
            pin_field.send_keys(self.config['pin'])

            logging.info("PIN entered, waiting for submission time...")
            return True

        except Exception as e:
            logging.error(f"PIN entry failed: {str(e)}")


    def submit_registration(self):
        try:
            # Wait until the submit button is present and clickable
            self.wait.until(EC.element_to_be_clickable((By.ID, "saveButton"))).click()
            logging.info("Clicked 'Submit' button.")

            # Wait for the page to process
            time.sleep(1)  # Brief pause to let notifications appear

            if not self.verify_registration():
                logging.error("Registration verification failed.")


            logging.info("Registration appears successful.")
            return True

        except Exception as e:
            logging.error(f"Submission failed: {str(e)}")


    def verify_registration(self):
        """Fast verification with immediate notification handling"""
        try:
            # Check for any error notifications first
            try:
                error_notification = WebDriverWait(self.driver, 2).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.notification.error"))
                )
                if error_notification:
                    error_text = error_notification.text
                    logging.error(f"Registration error notification detected: {error_text}")

            except TimeoutException:
                pass  # No error notification, good.

            # Check for success messages
            page_text = self.driver.page_source.lower()
            success_indicators = [
                "successfully registered",
                "registration complete",
                "saved successfully"
            ]
            if any(indicator in page_text for indicator in success_indicators):
                logging.info("Found success indicator text on page.")
                return True

            # Verify CRNs are in the "Registered" status
            registered_crns = set()
            # Find all summary rows
            rows = self.driver.find_elements(By.CSS_SELECTOR, "div.summary-grid div.summary-row")
            for row in rows:
                status = row.find_element(By.CSS_SELECTOR, "div.summary-status span").text.lower()
                crn = row.find_element(By.CSS_SELECTOR, "div.summary-crn span").text

                if status == "registered":
                    registered_crns.add(crn)

            expected_crns = set(self.crns)
            missing_crns = expected_crns - registered_crns

            if not missing_crns:
                logging.info("All submitted CRNs found with 'Registered' status.")

            else:
                logging.warning(f"Missing registered CRNs: {missing_crns}")


        except Exception as e:
            logging.error(f"Verification failed: {str(e)}")



def main():
    try:
        bot = BereaRegistrationBot()
        bot.create_scheduler_window()
    except SystemExit:
        print("Initial setup complete. Please edit config files and restart.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        messagebox.showerror("Fatal Error", f"An unexpected error occurred: {e}\nCheck logs for details.")


if __name__ == "__main__":
    main()