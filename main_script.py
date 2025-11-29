import pyautogui
import time
import keyboard
import pyperclip
import uuid
import subprocess
import pytesseract
import requests
import json
import re
from openai import OpenAI
from PIL import Image
import sys, os

# Configure tesseract path (works for pyinstaller'd apps too)
if hasattr(sys, '_MEIPASS'):
    tess_path = os.path.join(sys._MEIPASS, "tesseract-ocr", "tesseract.exe")
else:
    tess_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
pytesseract.pytesseract.tesseract_cmd = tess_path

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# API key will be provided by the launcher via globals
# If not provided, try to get from environment variable as fallback
try:
    api_key = OPENAI_API_KEY  # This is injected by the launcher
except NameError:
    # Fallback to environment variable if not injected
    import os
    api_key = os.environ.get('OPENAI_API_KEY', '')
    if not api_key:
        raise ValueError("OpenAI API key not provided. Please set it in the launcher script (moddedscript.py).")

client = OpenAI(api_key=api_key)

# ----------------------
# Utility functions
# ----------------------
def get_clipboard_text():
    try:
        return pyperclip.paste().strip()
    except Exception:
        return ""

def capture_and_extract_text():
    try:
        screenshot = pyautogui.screenshot()
        extracted_text = pytesseract.image_to_string(screenshot)
        return extracted_text.strip()
    except Exception as e:
        print(f"Screenshot error: {e}")
        return ""

def save_code_to_file(code_lines, filename_prefix="code_output"):
    """Disabled: Do not save code to disk. Keep clipboard copy only."""
    try:
        code_text = '\n'.join(code_lines)
        pyperclip.copy(code_text)
        print("Code copied to clipboard. Saving to disk is disabled.")
        return None
    except Exception as e:
        print(f"Error copying code to clipboard: {e}")
        return None

# ----------------------
# ChatGPT-related functions
# ----------------------
def clean_code_with_chatgpt(code_text):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                { "role": "system", "content": "You are a code cleaning expert. Extract and clean code in C++. Always output C++ code regardless of the input language. Return only the complete C++ code, without any comments or additional text." }, { "role": "user", "content": f"Extract and clean the code from the following text and convert it to C++:\n\n{code_text}\n\nReturn only the complete C++ code. Use proper C++ syntax including #include statements, namespace std, main function, and proper data types. Implement all logic using C++ constructs. Write the full code always, including necessary headers, ensuring it matches the output cases given in the question at any cost. If there is any syntaxes whitelisted, you should strictly use those in code. And blacklisted syntaxes shouldn't be used. Whitelisted syntaxes will be written like set1 and set2 etc. they should be used at any cost. And dont write any comments. if header and footer are given, exactly include same codes in the output. U cant change anything from the given footer and header." },
                {
                    "role": "user",
                    "content": (
                        f"Extract and clean the code from the following text and convert it to C++:\n\n{code_text}\n\n"
                        "Return only the complete C++ code."
                    )
                }
            ],
            max_tokens=2000
        )
        
        return response.choices[0].message.content.strip().split('\n')



    except Exception as e:
        print(f"An error occurred while processing with ChatGPT: {str(e)}")
        return []

def process_mcq_with_chatgpt(mcq_text):
    """Process MCQ text with ChatGPT and return the answer"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at solving multiple choice questions. Analyze the question and options carefully, then provide the correct answer. Always start your response with the letter of the answer (A, B, C, or D) followed by a colon, then the explanation."
                },
                {
                    "role": "user",
                    "content": f"Solve this MCQ:\n\n{mcq_text}\n\nProvide the correct answer starting with the letter (A, B, C, or D) followed by a colon, then brief explanation."
                }
            ],
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error processing MCQ: {e}")
        return "Error processing MCQ"

def extract_answer_letter(answer_text):
    """Extract answer letter (A, B, C, or D) from answer text"""
    # Look for patterns like "A:", "Answer: A", "A)", "(A)", etc.
    answer_text_upper = answer_text.upper()
    
    # Check for common patterns
    patterns = [
        r'^([ABCD])[:\)\.]',  # A:, A), A.
        r'ANSWER\s*[:\)\.]\s*([ABCD])',  # Answer: A
        r'OPTION\s*([ABCD])',  # Option A
        r'\(([ABCD])\)',  # (A)
        r'\b([ABCD])\b',  # Just A, B, C, or D as a word
    ]
    
    for pattern in patterns:
        match = re.search(pattern, answer_text_upper)
        if match:
            return match.group(1)
    
    # Fallback: find first occurrence of A, B, C, or D
    for char in answer_text_upper:
        if char in ['A', 'B', 'C', 'D']:
            return char
    
    return None

def show_mcq_answer(answer):
    """Display MCQ answer with cursor direction indicator and save to file"""
    print(f"\nMCQ Answer: {answer}")
    
    # Extract answer letter and show cursor direction
    answer_letter = extract_answer_letter(answer)
    if answer_letter:
        current_pos = pyautogui.position()
        movement_distance = 150  # pixels to move
        
        print(f"\nDetected answer: {answer_letter}")
        
        if answer_letter == 'A':
            # Move cursor UP
            new_x = current_pos.x
            new_y = current_pos.y - movement_distance
            if new_y < 0:
                new_y = 0
            pyautogui.moveTo(new_x, new_y, duration=0.3)
            print("Cursor moved UP (Answer A)")
        elif answer_letter == 'B':
            # Move cursor RIGHT
            screen_width, screen_height = pyautogui.size()
            new_x = current_pos.x + movement_distance
            if new_x > screen_width:
                new_x = screen_width - 1
            pyautogui.moveTo(new_x, current_pos.y, duration=0.3)
            print("Cursor moved RIGHT (Answer B)")
        elif answer_letter == 'C':
            # Move cursor DOWN
            screen_width, screen_height = pyautogui.size()
            new_y = current_pos.y + movement_distance
            if new_y > screen_height:
                new_y = screen_height - 1
            pyautogui.moveTo(current_pos.x, new_y, duration=0.3)
            print("Cursor moved DOWN (Answer C)")
        elif answer_letter == 'D':
            # Move cursor LEFT
            new_x = current_pos.x - movement_distance
            if new_x < 0:
                new_x = 0
            pyautogui.moveTo(new_x, current_pos.y, duration=0.3)
            print("Cursor moved LEFT (Answer D)")
        
        # Wait a bit so user can see the cursor movement
        time.sleep(1)
        
        # Move cursor back to original position
        pyautogui.moveTo(current_pos.x, current_pos.y, duration=0.2)
    else:
        print("Could not determine answer letter (A, B, C, or D)")
    
    # Save MCQ answer to Downloads folder
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"mcq_answer_{timestamp}.txt"
    downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
    full_path = os.path.join(downloads_path, filename)
    
    try:
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(f"MCQ Answer:\n{answer}")
        
        # Also copy to clipboard
        pyperclip.copy(answer)
        
        print(f"MCQ answer saved to: {full_path}")
        print("MCQ answer also copied to clipboard!")
    except Exception as e:
        print(f"Error saving MCQ answer: {e}")

# ----------------------
# Printing / typing automation
# ----------------------
paused = False
abort_requested = False

def _toggle_pause(_e=None):
    global paused
    paused = not paused
    state = "paused" if paused else "resumed"
    print(f"Typing {state} (F3)")

def _wait_if_paused():
    while paused:
        time.sleep(0.05)

def _request_abort(_e=None):
    global abort_requested, paused
    abort_requested = True
    paused = False
    print("Aborting current typing (F4). Returning to main menu...")

def _should_abort():
    global abort_requested
    if abort_requested:
        abort_requested = False
        return True
    return False

def Printing(code_lines, speed_choice):
    # Do NOT save code to disk. Keep clipboard copy only (already handled in save_code_to_file if needed).
    # Prepare typing area (mimic original behavior)
    for i in range(len(code_lines)-1):
        if _should_abort():
            print("Typing aborted.")
            return
        _wait_if_paused()
        pyautogui.press('enter')
    for i in range(len(code_lines)-1):
        if _should_abort():
            print("Typing aborted.")
            return
        _wait_if_paused()
        pyautogui.press('up')
    # Type each non-empty line (start at 0 to include first line)
    for line in range(1, len(code_lines)-1):
        if _should_abort():
            print("Typing aborted.")
            return
        _wait_if_paused()
        text = code_lines[line]
        if speed_choice == "fast":
            pyautogui.write(text)
        else:
            for char in text:
                if _should_abort():
                    print("Typing aborted.")
                    return
                _wait_if_paused()
                pyautogui.write(char, interval=0.025)
        pyautogui.press('down')

# ----------------------
# Fetch from GitHub and print with Alt+Y
# ----------------------
def fetch_code_from_github_raw(url, timeout=10):
    """Fetch code text from a GitHub raw URL. Returns text or empty string on failure."""
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"Error fetching code from GitHub: {e}")
        return ""

# ----------------------
# Main program
# ----------------------
def wholeProgram():
    speed_choice = input("Choose typing speed (fast/slow) [default: fast]: ").strip().lower()
    if speed_choice not in ['fast', 'slow']:
        speed_choice = "fast"

    print("\nProgram started with the following hotkeys:")
    print("ALT+X: Take single screenshot and process as code")
    print("ALT+Q: Take single screenshot and process as MCQ (with cursor direction indicator)")
    print("ALT+SHIFT+X: Start multiple screenshot mode for code")
    print("    - ALT: Take additional screenshots")
    print("    - SPACE: Process all screenshots")
    print("CTRL+C: Process clipboard text as code")
    print("ALT+G: Open GUI mode (not implemented)")
    print("ALT+Y: Fetch code from GitHub raw link and print it using the Printing() function")
    print(f"Current typing speed: {speed_choice}")

    # Set your GitHub raw URL here
    GITHUB_RAW_URL = "https://raw.githubusercontent.com/anshadrazak/codetoprint/refs/heads/main/codetoprint"

    last_clipboard = ""
    screenshots = []
    screenshot_mode_active = False
    last_alt_press = 0

    # Register pause/resume toggle on F3
    try:
        keyboard.on_press_key('f8', _toggle_pause, suppress=False)
        keyboard.on_press_key('f4', _request_abort, suppress=False)
    except Exception:
        pass

    while True:
        try:
            # Multiple screenshot mode activation
            if keyboard.is_pressed('alt+shift+x') and not screenshot_mode_active:
                screenshot_mode_active = True
                screenshots.clear()
                print("Multiple screenshot mode activated. Press ALT to take screenshots, SPACE to process.")
                time.sleep(0.5)
                continue

            # Single MCQ screenshot
            if keyboard.is_pressed('alt+q') and not screenshot_mode_active:
                print("Taking screenshot for MCQ...")
                time.sleep(0.4)
                extracted_text = capture_and_extract_text()
                if extracted_text:
                    print("Processing MCQ (placeholder)...")
                    answer = process_mcq_with_chatgpt(extracted_text)
                    show_mcq_answer(answer)
                time.sleep(0.5)
                continue

            # Single code screenshot
            if keyboard.is_pressed('alt+x') and not keyboard.is_pressed('shift') and not screenshot_mode_active:
                print("Taking single screenshot for code...")
                time.sleep(0.4)
                extracted_text = capture_and_extract_text()
                if extracted_text:
                    print("Processing code (local cleaner)...")
                    code_lines = clean_code_with_chatgpt(extracted_text)
                    Printing(code_lines, speed_choice)
                time.sleep(0.5)
                continue

            # Multiple screenshot mode behavior
            if screenshot_mode_active:
                if keyboard.is_pressed('alt') and not keyboard.is_pressed('shift') and not keyboard.is_pressed('x'):
                    current_time = time.time()
                    if current_time - last_alt_press >= 0.5:
                        print("Taking screenshot in multiple mode...")
                        extracted_text = capture_and_extract_text()
                        if extracted_text:
                            screenshots.append(extracted_text)
                            print(f"Screenshot {len(screenshots)} captured. Press SPACE when ready to process all.")
                        last_alt_press = current_time
                        time.sleep(0.3)

                if keyboard.is_pressed('space'):
                    if screenshots:
                        combined_text = "\n\n".join(screenshots)
                        print(f"Processing {len(screenshots)} screenshots...")
                        code_lines = clean_code_with_chatgpt(combined_text)
                        Printing(code_lines, speed_choice)
                        screenshots.clear()
                        screenshot_mode_active = False
                        print("Multiple screenshot mode deactivated.")
                    else:
                        print("No screenshots taken to process.")
                    time.sleep(0.5)
                    continue

            # Process clipboard
            if keyboard.is_pressed('ctrl+c'):
                time.sleep(0.1)
                clipboard_text = get_clipboard_text()
                if clipboard_text and clipboard_text != last_clipboard:
                    last_clipboard = clipboard_text
                    print("Processing clipboard text (local cleaner)...")
                    code_lines = clean_code_with_chatgpt(clipboard_text)
                    Printing(code_lines, speed_choice)
                time.sleep(0.3)

            # Fetch code from GitHub on ALT+Y and print it
            # Fetch code from GitHub on ALT+Y and print it
            if keyboard.is_pressed('alt+y'):
                print("ALT+Y detected — fetching code from GitHub...")
                time.sleep(0.3)  # debounce
                
                code_text = fetch_code_from_github_raw(GITHUB_RAW_URL)
                if code_text:
                    print(f"Fetched {len(code_text.splitlines())} lines from GitHub. Printing now...")
            
                    # DO NOT CLEAN OR PROCESS — KEEP EXACT CODE
                    # Normalize CRLF → LF to avoid infinite loop in Printing()
                    code_lines = code_text.replace('\r', '').split('\n')
            
                    Printing(code_lines, speed_choice)
                else:
                    print("Failed to fetch code from GitHub. Check the URL or your connection.")
            
                time.sleep(0.8)
                continue


            time.sleep(0.1)

        except KeyboardInterrupt:
            print("\nProgram interrupted by user. Exiting...")
            break
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            time.sleep(0.5)

# Run the program
if __name__ == '__main__':
    wholeProgram()














