import tkinter as tk
from tkinter import ttk
import speech_recognition as sr
from selenium import webdriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from threading import Thread
import time
from PIL import Image, ImageTk
from selenium.common.exceptions import SessionNotCreatedException
import subprocess
import os
import sys
import shutil

running = False
driver = None
recognizer = sr.Recognizer()

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
        "browser_error": "Browser error: {}. Please update Chrome/Chromium.",
        "installing_chrome": "Installing Google Chrome. Please wait...",
        "chrome_not_found": "Google Chrome 114 not found. Installing..."
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
        "browser_error": "Ошибка браузера: {}. Обновите Chrome/Chromium.",
        "installing_chrome": "Установка Google Chrome. Пожалуйста, подождите...",
        "chrome_not_found": "Google Chrome 114 не найден. Устанавливается..."
    }
}

def ensure_chrome():
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    if os.name == "nt" and not os.path.exists(chrome_path):
        status_label.config(text=translations[current_language]["chrome_not_found"])
        # Путь к установщику в сборке
        setup_path = os.path.join(sys._MEIPASS, "ChromeSetup.exe") if hasattr(sys, '_MEIPASS') else "ChromeSetup.exe"
        if os.path.exists(setup_path):
            status_label.config(text=translations[current_language]["installing_chrome"])
            try:
                # Запускаем установщик и ждём завершения
                subprocess.run([setup_path, "/silent", "/install"], check=True)
                # Копируем ChromeDriver для версии 114
                chromedriver_path = os.path.join(sys._MEIPASS, "chromedriver.exe") if hasattr(sys, '_MEIPASS') else "chromedriver.exe"
                if os.path.exists(chromedriver_path):
                    target_path = os.path.expanduser("~/.cache/webdriver-manager/chromedriver.exe")
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    shutil.copy(chromedriver_path, target_path)
            except subprocess.CalledProcessError:
                status_label.config(text=translations[current_language]["browser_error"].format("Failed to install Chrome"))
                return False
        else:
            status_label.config(text=translations[current_language]["browser_error"].format("ChromeSetup.exe not found"))
            return False
    return True

def voice_control_loop(trigger_word):
    global running, driver
    while running:
        with sr.Microphone() as source:
            status_label.config(text=translations[current_language]["listening"])
            recognizer.adjust_for_ambient_noise(source)
            try:
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=3)
                text = recognizer.recognize_sphinx(audio)
                status_label.config(text=translations[current_language]["recognized"].format(text))
                text_lower = text.lower()
                if trigger_word.lower() in text_lower:
                    try:
                        button_text = button_text_entry.get()
                        button = driver.find_element(By.LINK_TEXT, button_text) or \
                                 driver.find_element(By.PARTIAL_LINK_TEXT, button_text) or \
                                 driver.find_element(By.XPATH, f"//button[contains(text(), '{button_text}')]")
                        button.click()
                        url_entry.delete(0, tk.END)
                        url_entry.insert(0, driver.current_url)
                        status_label.config(text=translations[current_language]["button_clicked"].format(button_text))
                    except Exception as e:
                        status_label.config(text=translations[current_language]["button_not_found"].format(button_text))
            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                status_label.config(text=translations[current_language]["audio_not_understood"])
            except sr.RequestError as e:
                status_label.config(text=translations[current_language]["recognition_error"].format(e))
            time.sleep(0.5)

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
        if not ensure_chrome():
            running = False
            return
        service = Service(ChromeDriverManager(driver_version="114.0.5735.90").install())
        driver = webdriver.Chrome(service=service)
        driver.get(url)
        thread = Thread(target=voice_control_loop, args=(trigger_word,))
        thread.start()
    except SessionNotCreatedException as e:
        status_label.config(text=translations[current_language]["browser_error"].format(str(e)))
        running = False
    except Exception as e:
        status_label.config(text=translations[current_language]["browser_error"].format(str(e)))
        running = False

def stop_voice_control():
    global running, driver
    running = False
    status_label.config(text=translations[current_language]["status_label"])
    if driver:
        driver.quit()
        driver = None

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

root = tk.Tk()
root.title("Voice Control for Websites")
root.geometry("500x400")
root.configure(bg="#f0f0f0")

style = ttk.Style()
style.configure("TButton", font=("Helvetica", 12), padding=10)
style.configure("TLabel", font=("Helvetica", 12), background="#f0f0f0")
style.configure("TEntry", font=("Helvetica", 12))

main_frame = tk.Frame(root, bg="#f0f0f0")
main_frame.pack(pady=20, padx=20, fill="both", expand=True)

# Поле для URL
url_label = ttk.Label(main_frame, text="Website URL:")
url_label.pack(pady=5)
url_entry = ttk.Entry(main_frame, width=50)
url_entry.pack(pady=5)

button_text_label = ttk.Label(main_frame, text="Button Text on Website:")
button_text_label.pack(pady=5)
button_text_entry = ttk.Entry(main_frame, width=50)
button_text_entry.pack(pady=5)

trigger_label = ttk.Label(main_frame, text="Trigger Word:")
trigger_label.pack(pady=5)
trigger_entry = ttk.Entry(main_frame, width=50)
trigger_entry.pack(pady=5)

button_frame = tk.Frame(main_frame, bg="#f0f0f0")
button_frame.pack(pady=20)
start_button = ttk.Button(button_frame, text="Start Capturing Commands", command=start_voice_control)
start_button.pack(side="left", padx=10)
stop_button = ttk.Button(button_frame, text="Stop Capturing", command=stop_voice_control)
stop_button.pack(side="left", padx=10)

status_label = ttk.Label(main_frame, text="Voice capture stopped")
status_label.pack(pady=10)

current_language = "English"
language_button = ttk.Button(root, text="Language: English", command=lambda: language_menu.tk_popup(language_button.winfo_rootx(), language_button.winfo_rooty() + language_button.winfo_height()))
language_button.place(relx=0.95, rely=0.05, anchor="ne")

language_menu = tk.Menu(root, tearoff=0)
try:
    ru_flag = ImageTk.PhotoImage(Image.open("russia.png").resize((16, 16)))
    uk_flag = ImageTk.PhotoImage(Image.open("uk.png").resize((16, 16)))
    language_menu.add_command(label="Русский", image=ru_flag, compound="left", command=lambda: change_language("Русский"))
    language_menu.add_command(label="English", image=uk_flag, compound="left", command=lambda: change_language("English"))
    root.ru_flag = ru_flag
    root.uk_flag = uk_flag
except FileNotFoundError:
    language_menu.add_command(label="Русский", command=lambda: change_language("Русский"))
    language_menu.add_command(label="English", command=lambda: change_language("English"))
    root.ru_flag = None
    root.uk_flag = None

root.mainloop()