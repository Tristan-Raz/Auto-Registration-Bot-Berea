# QuikRegist Pro
[![License: GPL v3](https://img.shields.svg.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0.html)

***

## For Most Users (Easy Install)

If you just want to use the bot and don't want to code, this is for you.

[![Auto Register Youtube Video](https://img.youtube.com/vi/W8HPJDqJKtA/0.jpg)](https://www.youtube.com/watch?v=W8HPJDqJKtA)

1.  Go to the **[Releases Page](https://github.com/Tristan-Raz/Auto-Registration-Bot-Berea/releases)**.
2.  Download the `.zip` file from the latest release (e.g., `BereaBot_v1.0.1.zip`).
3.  Unzip the folder.
4.  **IMPORTANT:** Leave the `.exe` file **inside** the folder it came in. Do not move it to your desktop by itself. It needs the other files in that folder to work.
5.  Run the `.exe` file (e.g., `BereaBot.exe`). The bot will start and create the `config.txt` and `crns.txt` files for you *inside that same folder*.
6.  Skip to the **"Setup (CRITICAL First-Time Run)"** section below to configure the bot.

***

This is a registration bot I built to help level the playing field for class registration at Berea College. It's designed to be fast, reliable, and fair.

## CRITICAL DISCLAIMER

* **USE THIS TOOL ENTIRELY AT YOUR OWN RISK.**
* This tool needs your **Berea username, password, and registration PIN** to work. It stores this info locally in the `config.txt` file on your computer. I never see this information, but you need to be aware that you're storing your credentials in a text file.
* This is a third-party tool. It is **NOT** officially supported or endorsed by Berea College.
* I am **not responsible** for any issues that happen from using this. This includes (but is not limited to):
    * Failing to register for a class.
    * Registering for the wrong class.
    * Any issues with your student account, like getting locked out.
* **DUO IS REQUIRED:** This bot will trigger a DUO push. You **must have your phone ready** to approve the login. The bot will wait 5 minutes for you.
* **WEBSITE CHANGES WILL BREAK THIS:** The bot relies on specific button and field IDs on the Berea registration site. If the college updates its website, this tool **will break** until I or someone else updates the code.
* **ALWAYS** double-check your registration manually on MyBerea after the bot has run.

---

## The Motive: Why I Built This

I created this to combat the systemic issue of class holding and paid registration "bots" at Berea. I've seen friends and classmates stress over the "registration game"—frantically typing in CRNs and PINs, only to lose a spot to someone else.

This is personal for me, too. **I’ve personally had someone hold a class** I needed. I’ve even gotten to the point where I **almost paid someone for a class** because it was something I really, *really* wanted and needed for my schedule.

And that’s just wrong. It completely **goes against what it means to be a Berean.**

Berea is a place where students shouldn't have to worry about this. People don't have extra money to pay someone for a class. It creates a terrible, unfair cycle that goes against everything this college stands for.

This tool is my answer. It's designed to be a simple, effective, and free way for *every* student to have a fair shot.

* **It is 100% Free**
* **NO "Favors"**
* **NO PAYING for classes**
* **NO holding classes**

This is open-source and for the community.

## How It Works

This script opens a real Chrome browser (using Selenium) and logs in for you. It will wait for you to approve the DUO push. After logging in, it navigates to the registration page and enters your PIN.

Then, it waits. It constantly pings the Berea server to read its *exact* time, so it doesn't rely on your computer's clock. The very millisecond registration opens, it submits your PIN, moves to the next page, and submits all your CRNs.

## Installation

You'll need Python 3 and a few libraries.

1.  **Install Google Chrome:** The bot uses Chrome. Make sure it's installed.
2.  **Install Python:** If you don't have it, download and install Python 3 from [python.org](https://www.python.org/downloads/).
3.  **Install Required Libraries:** Open a terminal or Command Prompt and run this command:
    ```bash
    pip install selenium webdriver-manager requests pytz
    ```

## Setup (CRITICAL First-Time Run)

You have to configure the bot before you can use it.

1.  **First Run:** Save the script as a `.py` file (e.g., `berea_bot.py`) and run it from your terminal:
    ```bash
    python berea_bot.py
    ```
2.  **Popup Message:** A popup will appear: "Welcome! I've created `config.txt` and `crns.txt` for you...". This is normal. The script will close.
3.  **Find New Files:** In the same folder as the script, you will now see two new files: `config.txt` and `crns.txt`. You'll also see a new `logs` folder.
4.  **Edit `crns.txt`:** Open it and add your CRNs, one per line.
    ```
    # Add your 5-digit CRNs below, one per line.
    #Example:
    11111
    22222
    33333
    ```
5.  **Edit `config.txt`:** This is the most important step. Open it and fill in *every* field.
    ```
    # --- User Credentials ---
    USERNAME=your_username_here
    PASSWORD=your_password_here
    PIN=your_pin_here
    
    # --- Term Information ---
    TERM_ID=202512
    TERM_TEXT=Spring 2026
    
    # --- Bot Settings ---
    HEADLESS=false
    THROTTLE_SPEED=false
    REGISTRATION_DATE=2025-11-05
    ```
    * `USERNAME`: Your Berea email (e.g., `razotet@berea.edu`)
    * `PASSWORD`: Your Berea password.
    * `PIN`: Your 6-digit registration PIN.
    * `HEADLESS`: Set to `true` to run invisibly in the background, or `false` to watch the browser do its work. **(I recommend `false` for your first time).**
    * `THROTTLE_SPEED` & `REGISTRATION_DATE`: Leave these as-is. They are for testing on days other than registration day.

### How to Find Your `TERM_ID` and `TERM_TEXT`

This is easy.
1.  Log in to MyBerea and go to the "Register for Classes" page, where you see the dropdown to select a term.
2.  Right-click on the page and select **"View Page Source"**.
3.  A new tab opens with code. Press `Ctrl+F` (or `Cmd+F`) to search.
4.  Type in the name of the term, for example: `Fall 2025`.
5.  You will find a line that looks like this:
    `<div id="202510" class="select2-result-label">Fall 2025</div>`
6.  From this:
    * `TERM_ID` is `202510`
    * `TERM_TEXT` is `Fall 2025`

**Your setup is now complete.**

## How to Use (Registration Day)

1.  **Run the Bot:** Run the script again from your terminal:
    ```bash
    python berea_bot.py
    ```
2.  **Scheduler Window:** A small GUI window will appear.
3.  **To Test (Recommended):**
    * I highly recommend you test this *before* registration day.
    * Click **"Start Immediately"**.
    * A Chrome browser will open.
    * It will log in. **HAVE YOUR PHONE READY** to approve the DUO push.
    * It will navigate to the PIN page, enter the PIN, submit, enter your CRNs, and submit again.
    * This is the perfect way to test your config.
4.  **To Schedule for Registration:**
    * A few minutes before registration opens, run the bot.
    * In the GUI, set the **Hour**, **Minute**, and **Second** that registration opens.
        * *Example: For 7:30:00 AM, use Hour: `7`, Minute: `30`, Second: `0`.*
    * Click **"Start at Set Time"**.
    * The status will say "Starting browser...". A Chrome window will open.
    * It will log in (approve the DUO push!) and navigate all the way to the PIN entry page.
    * It will enter your PIN and then **wait**. The status will say `Waiting for 7:30:00...`
    * Now, **hands off**. Don't touch your mouse or keyboard.
    * At the exact time, the status will change to "Syncing with server..." and it will **automatically submit the PIN and all your CRNs** in less than a second.
5.  **Verify:**
    * The bot will pop up a "Success" or "Error" message.
    * Check the `logs` folder for a detailed log of the run.
    * **Log in to MyBerea manually** and confirm your schedule is correct.

## License

This project is licensed under the GNU General Public License v3.0.

<details>
<summary>Click to read the full GPLv3 License</summary>
