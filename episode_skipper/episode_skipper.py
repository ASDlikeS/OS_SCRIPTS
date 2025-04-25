import tkinter as tk
from tkinter import ttk, messagebox
import speech_recognition as sr
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from threading import Thread
import time
from PIL import Image, ImageTk
import os
import platform
import subprocess
import logging
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from ttkthemes import ThemedTk
import sys
import PIL._tkinter_finder


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

running = False
driver = None
recognizer = sr.Recognizer()

current_language = "English"

translations = {
    "English": {
        "title": "Voice Control for Websites",
        "url_label": "Website URL:",
        "button_text_label": "Button Text on Website:",
        "trigger_label": "Trigger Word:",
        "language_label": "Language: ",
        "start_button": "Start Capturing Commands",
        "stop_button": "Stop Capturing",
        "status_label": "Voice capture stopped",
        "error_url": "Error: Please enter a valid URL",
        "error_button_text": "Error: Please enter button text",
        "error_trigger": "Error: Please enter a trigger word",
        "listening": "Listening...",
        "recognized": "Recognized: {}",
        "button_clicked": "Button '{}' clicked",
        "button_not_found": "Button '{}' not found",
        "audio_not_understood": "Could not understand audio",
        "recognition_error": "Recognition error: {}",
        "browser_error": "Browser error: {}. Please make sure Chrome is installed.",
        "chrome_not_found": "Chrome browser not found. Please install Chrome.",
        "speech_error": "Error initializing speech recognition. Please check your microphone.",
        "exit_confirmation": "Are you sure you want to exit?",
        "settings": "Settings",
        "offline_recognition": "Use offline recognition",
        "volume_label": "Microphone sensitivity:",
        "timeout_label": "Listen timeout (seconds):",
        "save_settings": "Save settings"
    },
    "Русский": {
        "title": "Голосовое управление сайтами",
        "url_label": "URL сайта:",
        "button_text_label": "Текст кнопки на сайте:",
        "trigger_label": "Слово-триггер:",
        "language_label": "Язык: ",
        "start_button": "Начать захват команд",
        "stop_button": "Перестать захватывать",
        "status_label": "Захват голоса остановлен",
        "error_url": "Ошибка: Введите корректный URL",
        "error_button_text": "Ошибка: Введите текст кнопки",
        "error_trigger": "Ошибка: Введите слово-триггер",
        "listening": "Слушаю...",
        "recognized": "Распознано: {}",
        "button_clicked": "Кнопка '{}' нажата",
        "button_not_found": "Кнопка '{}' не найдена",
        "audio_not_understood": "Не удалось понять аудио",
        "recognition_error": "Ошибка распознавания: {}",
        "browser_error": "Ошибка браузера: {}. Убедитесь, что Chrome установлен.",
        "chrome_not_found": "Браузер Chrome не найден. Установите Chrome.",
        "speech_error": "Ошибка инициализации распознавания речи. Проверьте микрофон.",
        "exit_confirmation": "Вы уверены, что хотите выйти?",
        "settings": "Настройки",
        "offline_recognition": "Использовать автономное распознавание",
        "volume_label": "Чувствительность микрофона:",
        "timeout_label": "Таймаут прослушивания (секунды):",
        "save_settings": "Сохранить настройки"
    }
}

app_settings = {
    "offline_recognition": True,
    "mic_sensitivity": 50,
    "listen_timeout": 5,
    "phrase_time_limit": 3
}

def install_chrome_driver():
    try:
        driver_path = ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()
        return driver_path
    except Exception as e:
        logger.error(f"ChromeDriver installation error: {e}")
        try:
            subprocess.run(["webdriver-manager", "update", "--chromedriver"], check=True)
            driver_path = subprocess.check_output(["which", "chromedriver"]).decode().strip()
            return driver_path
        except Exception as sub_e:
            logger.error(f"Alternative ChromeDriver installation error: {sub_e}")
            return None

def find_chrome_browser():
    chrome_path = None
    
    if platform.system() == "Windows":
        for path in [
            os.path.join(os.environ.get("PROGRAMFILES", "C:\\Program Files"), "Google\\Chrome\\Application\\chrome.exe"),
            os.path.join(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"), "Google\\Chrome\\Application\\chrome.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google\\Chrome\\Application\\chrome.exe")
        ]:
            if os.path.exists(path):
                chrome_path = path
                break
    elif platform.system() == "Linux":
        for path in [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser"
        ]:
            if os.path.exists(path):
                chrome_path = path
                break
    elif platform.system() == "Darwin":
        for path in [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium"
        ]:
            if os.path.exists(path):
                chrome_path = path
                break
    
    return chrome_path


def find_button(driver, button_text):
    try:
        selectors = [
            lambda: driver.find_element(By.LINK_TEXT, button_text),
            lambda: driver.find_element(By.PARTIAL_LINK_TEXT, button_text),
            lambda: driver.find_element(By.XPATH, f"//button[contains(text(), '{button_text}')]"),
            lambda: driver.find_element(By.XPATH, f"//*[contains(@class, 'button') and contains(text(), '{button_text}')]"),
            lambda: driver.find_element(By.XPATH, f"//*[@title='{button_text}' or contains(@title, '{button_text}')]"),
            lambda: driver.find_element(By.XPATH, f"//*[contains(text(), '{button_text}')]"),
            lambda: driver.find_element(By.ID, button_text),
            lambda: driver.find_element(By.XPATH, f"//*[@aria-label='{button_text}' or contains(@aria-label, '{button_text}')]"),
            lambda: driver.find_element(By.CSS_SELECTOR, f"[data-text='{button_text}'], [data-label='{button_text}']")
        ]
        
        for selector in selectors:
            try:
                element = selector()
                if element and element.is_displayed():
                    return element
            except NoSuchElementException:
                continue
        return None
    except Exception as e:
        logger.error(f"Error finding button: {e}")
        return None

def voice_control_loop(trigger_word):
    global running, driver, app_settings
    
    while running:
        try:
            with sr.Microphone() as source:
                status_label.config(text=translations[current_language]["listening"])
                root.update()
                
                sensitivity = 1.0 - (app_settings["mic_sensitivity"] / 100.0)
                recognizer.dynamic_energy_threshold = True
                recognizer.energy_threshold = 300 + (4000 * sensitivity)
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                try:
                    audio = recognizer.listen(
                        source, 
                        timeout=app_settings["listen_timeout"], 
                        phrase_time_limit=app_settings["phrase_time_limit"]
                    )
                    
                    if app_settings["offline_recognition"]:
                        text = recognizer.recognize_sphinx(audio)
                    else:
                        text = recognizer.recognize_google(audio)
                    
                    status_label.config(text=translations[current_language]["recognized"].format(text))
                    root.update()
                    
                    text_lower = text.lower()
                    if trigger_word.lower() in text_lower:
                        try:
                            button_text = button_text_entry.get()
                            current_url = driver.current_url
                            
                            button = find_button(driver, button_text)
                            if button:
                                button.click()
                                WebDriverWait(driver, 10).until(EC.url_changes(current_url))
                                
                                root.after(0, lambda: url_entry.delete(0, tk.END))
                                root.after(0, lambda: url_entry.insert(0, driver.current_url))
                                
                                status_label.config(text=translations[current_language]["button_clicked"].format(button_text))
                            else:
                                status_label.config(text=translations[current_language]["button_not_found"].format(button_text))
                        except Exception as e:
                            logger.error(f"Button click error: {e}")
                            status_label.config(text=translations[current_language]["button_not_found"].format(button_text))
                    
                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    status_label.config(text=translations[current_language]["audio_not_understood"])
                except sr.RequestError as e:
                    status_label.config(text=translations[current_language]["recognition_error"].format(e))
                
                time.sleep(0.2)
        
        except Exception as e:
            logger.error(f"Voice control loop error: {e}")
            status_label.config(text=f"Error: {str(e)}")
            time.sleep(1)

def start_voice_control():
    global running, driver
    
    if running:
        return
    
    url = url_entry.get()
    button_text = button_text_entry.get()
    trigger_word = trigger_entry.get()
    
    if not url:
        status_label.config(text=translations[current_language]["error_url"])
        return
    if not button_text:
        status_label.config(text=translations[current_language]["error_button_text"])
        return
    if not trigger_word:
        status_label.config(text=translations[current_language]["error_trigger"])
        return
    
    running = True
    status_label.config(text=translations[current_language]["listening"])
    
    try:
        chrome_options = Options()
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        if platform.system() == "Linux":
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-setuid-sandbox")
        
        chrome_path = find_chrome_browser()
        if chrome_path:
            chrome_options.binary_location = chrome_path
        
        if platform.system() == "Linux":
            try:
                driver_path = subprocess.check_output(["which", "chromedriver"]).decode().strip()
                service = Service(driver_path)
                driver = webdriver.Chrome(service=service, options=chrome_options)
            except Exception:
                driver_path = install_chrome_driver()
                if driver_path:
                    service = Service(driver_path)
                    driver = webdriver.Chrome(service=service, options=chrome_options)
                else:
                    status_label.config(text="Could not install ChromeDriver")
                    running = False
                    return
        else:
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        
        driver.get(url)
        
        thread = Thread(target=voice_control_loop, args=(trigger_word,), daemon=True)
        thread.start()
        
        start_button.config(state=tk.DISABLED)
        stop_button.config(state=tk.NORMAL)
        
    except WebDriverException as e:
        logger.error(f"WebDriver error: {e}")
        status_label.config(text=translations[current_language]["browser_error"].format(str(e)))
        running = False
    except Exception as e:
        logger.error(f"Start error: {e}")
        status_label.config(text=f"Error: {str(e)}")
        running = False

def stop_voice_control():
    global running, driver
    
    running = False
    status_label.config(text=translations[current_language]["status_label"])
    
    if driver:
        try:
            driver.quit()
        except Exception as e:
            logger.error(f"Error closing browser: {e}")
        finally:
            driver = None
    
    start_button.config(state=tk.NORMAL)
    stop_button.config(state=tk.DISABLED)

def change_language(lang):
    global current_language
    current_language = lang
    update_ui()

def update_ui():
    root.title(translations[current_language]["title"])
    url_label.config(text=translations[current_language]["url_label"])
    button_text_label.config(text=translations[current_language]["button_text_label"])
    trigger_label.config(text=translations[current_language]["trigger_label"])
    start_button.config(text=translations[current_language]["start_button"])
    stop_button.config(text=translations[current_language]["stop_button"])
    status_label.config(text=translations[current_language]["status_label"])
    language_button.config(text=translations[current_language]["language_label"] + current_language)
    settings_button.config(text=translations[current_language]["settings"])

def on_exit():
    if messagebox.askokcancel(
        translations[current_language]["exit_confirmation"],
        translations[current_language]["exit_confirmation"]):
        stop_voice_control()
        root.destroy()

def open_settings():
    global app_settings
    
    settings_window = ThemedTk(theme="arc")
    settings_window.title(translations[current_language]["settings"])
    settings_window.geometry("400x300")
    settings_window.resizable(False, False)
    
    style = ttk.Style()
    style.configure("Settings.TFrame", background="#ffffff")
    
    settings_frame = ttk.Frame(settings_window, style="Settings.TFrame", padding=20)
    settings_frame.pack(fill="both", expand=True)
    
    offline_var = tk.BooleanVar(value=app_settings["offline_recognition"])
    offline_check = ttk.Checkbutton(
        settings_frame, 
        text=translations[current_language]["offline_recognition"],
        variable=offline_var
    )
    offline_check.pack(pady=10, anchor="w")
    
    sensitivity_label = ttk.Label(
        settings_frame, 
        text=translations[current_language]["volume_label"]
    )
    sensitivity_label.pack(pady=(10, 5), anchor="w")
    
    sensitivity_var = tk.IntVar(value=app_settings["mic_sensitivity"])
    sensitivity_scale = ttk.Scale(
        settings_frame,
        from_=0,
        to=100,
        orient=tk.HORIZONTAL,
        variable=sensitivity_var,
        length=300
    )
    sensitivity_scale.pack(pady=(0, 10), fill="x")
    
    timeout_label = ttk.Label(
        settings_frame, 
        text=translations[current_language]["timeout_label"]
    )
    timeout_label.pack(pady=(10, 5), anchor="w")
    
    timeout_var = tk.IntVar(value=app_settings["listen_timeout"])
    timeout_spinbox = ttk.Spinbox(
        settings_frame,
        from_=1,
        to=15,
        textvariable=timeout_var,
        width=5
    )
    timeout_spinbox.pack(pady=(0, 10), anchor="w")
    
    save_button = ttk.Button(
        settings_frame,
        text=translations[current_language]["save_settings"],
        command=lambda: save_settings(
            offline_var.get(),
            sensitivity_var.get(),
            timeout_var.get(),
            settings_window
        )
    )
    save_button.pack(pady=20)

def save_settings(offline, sensitivity, timeout, window):
    global app_settings
    
    app_settings["offline_recognition"] = offline
    app_settings["mic_sensitivity"] = sensitivity
    app_settings["listen_timeout"] = timeout
    
    window.destroy()
    
def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

root = ThemedTk(theme="arc")
root.title("Voice Control for Websites")
root.geometry("600x500")

globe_img = Image.open(resource_path("resources/globe.png"))
globe_img = globe_img.resize((16, 16), Image.Resampling.LANCZOS)
globe_icon = ImageTk.PhotoImage(globe_img)

usa_img = Image.open(resource_path("resources/usa.png"))
usa_img = usa_img.resize((16, 16), Image.Resampling.LANCZOS)
usa_icon = ImageTk.PhotoImage(usa_img)

rus_img = Image.open(resource_path("resources/rus.png"))
rus_img = rus_img.resize((16, 16), Image.Resampling.LANCZOS)
rus_icon = ImageTk.PhotoImage(rus_img)

style = ttk.Style()
style.configure("TButton", font=("Segoe UI", 11, "bold"), padding=10)
style.configure("TLabel", font=("Segoe UI", 11))
style.configure("TEntry", font=("Segoe UI", 11), padding=5)
style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"))

main_frame = ttk.Frame(root, padding=20)
main_frame.pack(fill="both", expand=True)

header = ttk.Label(main_frame, text=translations[current_language]["title"], style="Header.TLabel")
header.pack(pady=10)

url_label = ttk.Label(main_frame, text="Website URL:")
url_label.pack(pady=5, anchor="w")
url_entry = ttk.Entry(main_frame, width=50)
url_entry.pack(pady=5, fill="x")
url_entry.insert(0, "https://")

button_text_label = ttk.Label(main_frame, text="Button Text on Website:")
button_text_label.pack(pady=5, anchor="w")
button_text_entry = ttk.Entry(main_frame, width=50)
button_text_entry.pack(pady=5, fill="x")
trigger_label = ttk.Label(main_frame, text="Trigger Word:")
trigger_label.pack(pady=5, anchor="w")
trigger_entry = ttk.Entry(main_frame, width=50)
trigger_entry.pack(pady=5, fill="x")
trigger_entry.insert(0, "next")

control_frame = ttk.Frame(main_frame)
control_frame.pack(pady=15, fill="x")

start_button = ttk.Button(control_frame, text="Start Capturing Commands", 
                         command=start_voice_control, style="Accent.TButton")
start_button.pack(side="left", padx=5)

stop_button = ttk.Button(control_frame, text="Stop Capturing", 
                        command=stop_voice_control, state=tk.DISABLED)
stop_button.pack(side="left", padx=5)

status_frame = ttk.Frame(main_frame)
status_frame.pack(pady=10, fill="x")

status_label = ttk.Label(status_frame, text="Voice capture stopped", 
                        foreground="#666666")
status_label.pack(side="left")

bottom_panel = ttk.Frame(root)
bottom_panel.pack(side="bottom", pady=10)

language_menu = tk.Menu(root, tearoff=0)

language_menu.add_command(
    label="English",
    compound="left",
    image=usa_icon,
    command=lambda: change_language("English")
)
language_menu.add_command(
    label="Русский",
    compound="left",
    image=rus_icon,
    command=lambda: change_language("Русский")
)
language_button = ttk.Button(
    bottom_panel,
    text=current_language,
    compound="left",
    image=globe_icon,
    command=lambda: language_menu.tk_popup(
        language_button.winfo_rootx(),
        language_button.winfo_rooty() + language_button.winfo_height()
    ),
    width=15
)

language_button = ttk.Button(
    bottom_panel,
    text=current_language,
    image=globe_icon,
    compound="left",
    command=lambda: language_menu.tk_popup(
        language_button.winfo_rootx(),
        language_button.winfo_rooty() + language_button.winfo_height()
    ),
    width=15
)
language_button.pack(side="right", padx=5)

settings_button = ttk.Button(
    bottom_panel,
    text="⚙",
    width=10,
    command=open_settings
)
settings_button.pack(side="right", padx=5)

style.configure("Accent.TButton", foreground="white", background="#4CAF50")
style.map("Accent.TButton", 
         background=[("active", "#45a049"), ("disabled", "#81C784")])

update_ui()

root.protocol("WM_DELETE_WINDOW", on_exit)

if __name__ == "__main__":
    try:
        root.mainloop()
    except Exception as e:
        logger.error(f"Application error: {e}")
        messagebox.showerror("Error", f"Application error: {e}")