import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import pyautogui
import time
import os
import json
import logging
from logging.handlers import RotatingFileHandler

# Конфігурація
DEFAULT_CONFIG = {
    "actions_file": os.path.join(os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(__file__), "actions.json"),
    "desktop_path": os.path.join(os.path.expanduser("~"), "Desktop"),
    "log_file": os.path.join(os.path.expanduser("~"), "Desktop", "record_actions.log"),
    "default_font": "Arial 8",
    "max_log_size_bytes": 10 * 1024 * 1024,
    "backup_log_count": 5,
    "action_delay": {
        "подвійний_клік": 10.0,
        "клік": 10.0,
        "введення_тексту": 10.0,
        "натискання_клавіші": 10.0,
        "enter_key": 10.0
    },
    "timer_duration": 3000,
    "mouse_fixation_time": 0.5,
    "mouse_fixation_threshold": 5,
    "mouse_check_interval": 200,
    "debug_point_duration": 500,
    "debug_point_size": 8,
    "checkmark_duration": 500,
    "checkmark_size": 16,
    "action_number_duration": 1000,
    "action_number_size": 12,
    "template_canvas_height": 100  # Додано для керування висотою полотна
}

# Словник для локалізації
TEXTS = {
    "record_tab": "Запис дій",
    "profiles_templates_tab": "Профілі та шаблони",
    "run_tab": "Запуск бота",
    "status_ready": "Готово",
    "status_recording": "Запис дії через {seconds} секунд...",
    "status_action_saved": "Дію збережено",
    "status_action_edited": "Дію відредаговано",
    "status_running": "{action} ({profile}): {progress:.1f}%",
    "status_completed": "Виконання завершено",
    "error_no_template": "Виберіть шаблон!",
    "error_no_profile": "Виберіть профіль!",
    "error_no_action_name": "Введіть назву дії!",
    "error_no_extra_input": "Введіть текст, клавішу або селектор!",
    "error_no_shortcut": "Ярлик не вибрано!",
    "error_open_shortcut": "Не вдалося відкрити ярлик: {path}",
    "error_no_action_selected": "Виберіть дію!",
    "tooltip_template_menu": "Виберіть шаблон для запису або виконання",
    "tooltip_profile_menu": "Виберіть профіль для прив’язки",
    "tooltip_action_name": "Введіть назву дії",
    "tooltip_extra_input": "Введіть текст, клавішу або селектор (XPath/CSS)",
    "tooltip_record_button": "Почати/зупинити запис дії",
    "tooltip_run_bot": "Запустити бота для вибраних шаблонів",
    "action_types": ["подвійний_клік", "клік", "введення_тексту", "натискання_клавіші"],
    "x_input": "X координата:",
    "y_input": "Y координата:",
    "run_bot": "Запустити бота",
}

# Налаштування логування
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler = RotatingFileHandler(DEFAULT_CONFIG["log_file"], maxBytes=DEFAULT_CONFIG["max_log_size_bytes"],
                                  backupCount=DEFAULT_CONFIG["backup_log_count"], encoding='utf-8')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def log_error(message, error):
    logger.error(f"{message}: {error}")

def async_delay(window, ms, callback):
    window.after(ms, callback)

def get_shortcut_name_at_position(x, y):
    shortcut_path = tk.filedialog.askopenfilename(
        title="Виберіть ярлик",
        filetypes=[("Ярлики", "*.lnk")],
        initialdir=DEFAULT_CONFIG["desktop_path"]
    )
    if shortcut_path:
        shortcut_name = os.path.splitext(os.path.basename(shortcut_path))[0]
        return shortcut_name, shortcut_path
    return "", ""

def open_shortcut(shortcut_path):
    try:
        os.startfile(shortcut_path)
        return True
    except OSError as e:
        log_error(f"Помилка відкриття ярлика: {shortcut_path}", e)
        return False

def show_checkmark(x, y):
    try:
        check_window = tk.Toplevel()
        check_window.geometry(f"20x20+{x}+{y}")
        check_window.attributes('-alpha', 0.7)
        check_window.attributes('-topmost', True)
        check_window.overrideredirect(True)
        tk.Label(check_window, text="✔", fg="green", font=("Arial", DEFAULT_CONFIG["checkmark_size"])).pack()
        check_window.after(DEFAULT_CONFIG["checkmark_duration"], check_window.destroy)
        logger.info(f"Галочка на ({x}, {y})")
    except tk.TclError as e:
        log_error(f"Помилка галочки на ({x}, {y})", e)

def show_debug_point(x, y):
    try:
        point_window = tk.Toplevel()
        point_window.geometry(f"{DEFAULT_CONFIG['debug_point_size']}x{DEFAULT_CONFIG['debug_point_size']}+{x}+{y}")
        point_window.attributes('-alpha', 0.5)
        point_window.attributes('-topmost', True)
        point_window.overrideredirect(True)
        tk.Label(point_window, text="•", fg="red", font=("Arial", DEFAULT_CONFIG["debug_point_size"])).pack()
        point_window.after(DEFAULT_CONFIG["debug_point_duration"], point_window.destroy)
        logger.info(f"Маркер на ({x}, {y})")
    except tk.TclError as e:
        log_error(f"Помилка маркера на ({x}, {y})", e)

def show_action_number(x, y, action_index):
    try:
        number_window = tk.Toplevel()
        number_window.geometry(f"30x30+{x + 10}+{y + 10}")
        number_window.attributes('-alpha', 0.7)
        number_window.attributes('-topmost', True)
        number_window.overrideredirect(True)
        tk.Label(number_window, text=str(action_index + 1), fg="blue", bg="white",
                 font=("Arial", DEFAULT_CONFIG["action_number_size"])).pack()
        number_window.after(DEFAULT_CONFIG["action_number_duration"], number_window.destroy)
        logger.info(f"Номер дії {action_index + 1} відображено на ({x}, {y})")
    except tk.TclError as e:
        log_error(f"Помилка відображення номера дії на ({x}, {y})", e)

class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        x, y = self.widget.winfo_pointerxy()
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x + 10}+{y + 10}")
        label = tk.Label(self.tooltip_window, text=self.text, background="lightyellow", relief=tk.SOLID, borderwidth=1,
                         font=DEFAULT_CONFIG["default_font"])
        label.pack()

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

class ActionManager:
    def __init__(self):
        self.data = {
            "screen_resolution": {"width": pyautogui.size().width, "height": pyautogui.size().height},
            "profiles": {},
            "templates": {}
        }
        self.screen_size = pyautogui.size()
        self.screen_width = self.screen_size.width
        self.screen_height = self.screen_size.height
        self.load_actions()

    def load_actions(self):
        file_path = DEFAULT_CONFIG["actions_file"]
        logger.info(f"Завантаження файлу дій: {file_path}")
        try:
            if not os.path.exists(file_path):
                logger.info(f"Файл {file_path} не існує, створюємо новий")
                directory = os.path.dirname(file_path) or "."
                os.makedirs(directory, exist_ok=True)
                initial_data = {
                    "screen_resolution": {"width": self.screen_width, "height": self.screen_height},
                    "profiles": {},
                    "templates": {}
                }
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(initial_data, f, indent=4, ensure_ascii=False)
                logger.info(f"Створено новий файл: {file_path}")
                self.data = initial_data
                return

            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.screen_width = data.get("screen_resolution", {}).get("width", self.screen_width)
                self.screen_height = data.get("screen_resolution", {}).get("height", self.screen_height)
                self.data["profiles"] = data.get("profiles", {})
                self.data["templates"] = data.get("templates", data.get("projects", {}))
                for template in self.data["templates"].values():
                    if "profiles" not in template:
                        template["profiles"] = []
                        for action in template.get("actions", []):
                            template["profiles"] = list(set(template["profiles"] + action.get("profiles", [])))
                logger.info("Дії успішно завантажено")
        except json.JSONDecodeError as e:
            log_error(f"Помилка JSON у {file_path}", e)
            messagebox.showerror("Помилка", f"Файл {file_path} пошкоджено: {str(e)}")
            self.data["templates"] = {}
        except OSError as e:
            log_error(f"Помилка доступу до {file_path}", e)
            messagebox.showerror("Помилка", f"Не вдалося відкрити файл {file_path}: {str(e)}")
            self.data["templates"] = {}

    def save_actions(self):
        file_path = DEFAULT_CONFIG["actions_file"]
        logger.info(f"Спроба зберегти файл: {file_path}")
        try:
            directory = os.path.dirname(file_path) or "."
            logger.info(f"Перевірка директорії: {directory}")
            os.makedirs(directory, exist_ok=True)
            logger.info(f"Директорія {directory} існує або створена")
            if not os.access(directory, os.W_OK):
                error_msg = f"Немає прав на запис у директорію: {directory}"
                logger.error(error_msg)
                messagebox.showerror("Помилка", error_msg)
                return
            file_exists = os.path.exists(file_path)
            if file_exists and not os.access(file_path, os.W_OK):
                error_msg = f"Немає прав на запис у файл: {file_path}"
                logger.error(error_msg)
                messagebox.showerror("Помилка", error_msg)
                return
            if not file_exists and not os.access(directory, os.W_OK):
                error_msg = f"Немає прав на створення файлу: {file_path}"
                logger.error(error_msg)
                messagebox.showerror("Помилка", error_msg)
                return
            logger.info(f"Зберігаємо шаблони: {list(self.data['templates'].keys())}")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
            logger.info(f"Дії успішно збережено у {file_path}")
        except OSError as e:
            error_msg = f"Помилка збереження у {file_path}: {str(e)}"
            log_error(error_msg, e)
            messagebox.showerror("Помилка", error_msg)
        except Exception as e:
            error_msg = f"Непередбачена помилка збереження у {file_path}: {str(e)}"
            log_error(error_msg, e)
            messagebox.showerror("Помилка", error_msg)

class MainWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Automation Tool")
        self.root.geometry("600x400")
        self.root.minsize(400, 300)
        pyautogui.FAILSAFE = True
        self.action_manager = ActionManager()
        self.recording = False
        self.running = False
        self.edit_mode = False
        self.undo_stack = []
        self.current_profiles = []
        self.deferred_actions = []
        self.profile_check_vars = {}
        self.profile_check_buttons = {}
        self.run_template_vars = {}
        self.record_template_check_vars = {}
        self.bind_profile_check_vars = {}
        self.mouse_positions = []
        self.last_fixed_position = None
        self.mouse_tracking = False
        self.notebook_frame = tk.Frame(self.root)
        self.notebook_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        self.notebook = ttk.Notebook(self.notebook_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.profiles_templates_frame = tk.Frame(self.notebook)
        self.record_frame = tk.Frame(self.notebook)
        self.run_frame = tk.Frame(self.notebook)
        self.notebook.add(self.profiles_templates_frame, text=TEXTS["profiles_templates_tab"])
        self.notebook.add(self.record_frame, text=TEXTS["record_tab"])
        self.notebook.add(self.run_frame, text=TEXTS["run_tab"])
        self.status_label = tk.Label(self.root, text=TEXTS["status_ready"], relief=tk.SUNKEN, anchor=tk.W,
                                     font=DEFAULT_CONFIG["default_font"])
        self.status_label.pack(fill=tk.X, padx=1, pady=1)
        self.setup_profiles_templates_tab()
        self.setup_record_tab()
        self.setup_run_tab()
        self.update_profiles_list()
        self.update_templates_list()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.bind('<Control-Shift-Escape>', lambda event: self.emergency_stop())
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    def on_tab_changed(self, event):
        self.toggle_mouse_tracking()

    def toggle_mouse_tracking(self):
        if self.notebook.select() == self.notebook.tabs()[1]:
            self.mouse_tracking = True
            self.update_mouse_coords()
        else:
            self.mouse_tracking = False

    def update_mouse_coords(self):
        if self.mouse_tracking and not self.recording:
            x, y = pyautogui.position()
            self.x_entry.delete(0, tk.END)
            self.x_entry.insert(0, str(x))
            self.y_entry.delete(0, tk.END)
            self.y_entry.insert(0, str(y))
            self.root.after(100, self.update_mouse_coords)

    def on_closing(self):
        self.running = False
        self.recording = False
        self.mouse_tracking = False
        self.root.destroy()

    def emergency_stop(self):
        if self.running:
            self.stop_bot()
        if self.recording:
            self.recording = False
            self.status_label.config(text="Запис зупинено")
            self.timer_label.config(text="")
            self.record_button.config(state=tk.NORMAL)
            logger.info("Аварійна зупинка запису")

    def setup_record_tab(self):
        main_frame = tk.Frame(self.record_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        left_frame = tk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky=tk.NSEW, padx=1, pady=1)
        template_frame = tk.LabelFrame(left_frame, text="Шаблони", font=DEFAULT_CONFIG["default_font"])
        template_frame.pack(fill=tk.X, padx=1, pady=1)
        self.templates_canvas = tk.Canvas(template_frame, height=DEFAULT_CONFIG["template_canvas_height"])
        self.templates_scrollbar = ttk.Scrollbar(template_frame, orient=tk.VERTICAL, command=self.templates_canvas.yview)
        self.templates_scrollable_frame = tk.Frame(self.templates_canvas)
        self.templates_scrollable_frame.bind("<Configure>",
                                            lambda e: self.templates_canvas.configure(scrollregion=self.templates_canvas.bbox("all")))
        self.templates_canvas.create_window((0, 0), window=self.templates_scrollable_frame, anchor="nw")
        self.templates_canvas.configure(yscrollcommand=self.templates_scrollbar.set)
        self.templates_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=1)
        self.templates_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tk.Label(left_frame, text="Назва дії:", font=DEFAULT_CONFIG["default_font"]).pack(anchor=tk.W, padx=1, pady=1)
        self.action_name_entry = tk.Entry(left_frame, font=DEFAULT_CONFIG["default_font"], width=20)
        self.action_name_entry.pack(fill=tk.X, padx=1, pady=1)
        Tooltip(self.action_name_entry, TEXTS["tooltip_action_name"])
        tk.Label(left_frame, text="Тип дії:", font=DEFAULT_CONFIG["default_font"]).pack(anchor=tk.W, padx=1, pady=1)
        self.action_type_var = tk.StringVar(value=TEXTS["action_types"][0])
        self.action_type_menu = tk.OptionMenu(left_frame, self.action_type_var, *TEXTS["action_types"])
        self.action_type_menu.config(font=DEFAULT_CONFIG["default_font"], width=15)
        self.action_type_menu.pack(fill=tk.X, padx=1, pady=1)
        self.record_button = tk.Button(left_frame, text="Записати", command=self.start_recording,
                                       font=DEFAULT_CONFIG["default_font"], width=7)
        self.record_button.pack(anchor=tk.W, padx=1, pady=1)
        Tooltip(self.record_button, TEXTS["tooltip_record_button"])
        coord_frame = tk.Frame(left_frame)
        coord_frame.pack(fill=tk.X, padx=1, pady=1)
        tk.Label(coord_frame, text=TEXTS["x_input"], font=DEFAULT_CONFIG["default_font"]).pack(side=tk.LEFT, padx=1)
        self.x_entry = tk.Entry(coord_frame, font=DEFAULT_CONFIG["default_font"], width=8)
        self.x_entry.pack(side=tk.LEFT, padx=1)
        tk.Label(coord_frame, text=TEXTS["y_input"], font=DEFAULT_CONFIG["default_font"]).pack(side=tk.LEFT, padx=1)
        self.y_entry = tk.Entry(coord_frame, font=DEFAULT_CONFIG["default_font"], width=8)
        self.y_entry.pack(side=tk.LEFT, padx=1)
        Tooltip(self.x_entry, "Введіть X координату")
        Tooltip(self.y_entry, "Введіть Y координату")
        self.extra_frame = tk.Frame(left_frame)
        tk.Label(self.extra_frame, text="Текст/Клавіша/Селектор:", font=DEFAULT_CONFIG["default_font"]).pack(side=tk.LEFT, padx=1)
        self.extra_entry = tk.Entry(self.extra_frame, font=DEFAULT_CONFIG["default_font"], width=15)
        self.extra_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
        Tooltip(self.extra_entry, TEXTS["tooltip_extra_input"])
        self.action_type_var.trace("w", self.toggle_extra_input)
        self.delay_frame = tk.Frame(left_frame)
        self.delay_frame.pack(fill=tk.X, padx=1, pady=1)
        tk.Label(self.delay_frame, text="Затримка (сек):", font=DEFAULT_CONFIG["default_font"]).pack(side=tk.LEFT, padx=1)
        self.delay_entry = tk.Entry(self.delay_frame, font=DEFAULT_CONFIG["default_font"], width=8)
        self.delay_entry.pack(side=tk.LEFT, padx=1)
        Tooltip(self.delay_entry, "Введіть затримку в секундах після виконання дії")
        right_frame = tk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky=tk.NSEW, padx=1, pady=1)
        tk.Label(right_frame, text="Дії:", font=DEFAULT_CONFIG["default_font"]).pack(anchor=tk.W, padx=1, pady=1)
        self.actions_list = tk.Listbox(right_frame, height=10, font=DEFAULT_CONFIG["default_font"], width=25, selectmode=tk.MULTIPLE)
        self.actions_list.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        button_frame = tk.Frame(main_frame)
        button_frame.grid(row=1, column=0, columnspan=2, sticky=tk.EW, padx=1, pady=1)
        self.delete_action_button = tk.Button(button_frame, text="Видалити", command=self.delete_action,
                                              font=DEFAULT_CONFIG["default_font"], width=7)
        self.delete_action_button.pack(side=tk.LEFT, padx=1)
        self.edit_action_button = tk.Button(button_frame, text="Редагувати", command=self.edit_action_in_window,
                                            font=DEFAULT_CONFIG["default_font"], width=7)
        self.edit_action_button.pack(side=tk.LEFT, padx=1)
        self.copy_action_button = tk.Button(button_frame, text="Копіювати", command=self.copy_actions,
                                            font=DEFAULT_CONFIG["default_font"], width=7)
        self.copy_action_button.pack(side=tk.LEFT, padx=1)
        self.cancel_edit_button = tk.Button(button_frame, text="Скасувати", command=self.cancel_edit,
                                            font=DEFAULT_CONFIG["default_font"], width=7, state=tk.DISABLED)
        self.cancel_edit_button.pack(side=tk.LEFT, padx=1)
        self.move_up_button = tk.Button(button_frame, text="Вгору", command=self.move_action_up,
                                        font=DEFAULT_CONFIG["default_font"], width=7)
        self.move_up_button.pack(side=tk.LEFT, padx=1)
        Tooltip(self.move_up_button, "Перемістити дію вгору у списку")
        self.move_down_button = tk.Button(button_frame, text="Вниз", command=self.move_action_down,
                                          font=DEFAULT_CONFIG["default_font"], width=7)
        self.move_down_button.pack(side=tk.LEFT, padx=1)
        Tooltip(self.move_down_button, "Перемістити дію вниз у списку")
        self.timer_label = tk.Label(main_frame, text="", font=DEFAULT_CONFIG["default_font"])
        self.timer_label.grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=1, pady=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)
        self.root.bind('<Escape>', lambda event: self.emergency_stop() if self.recording else None)

    def toggle_extra_input(self, *args):
        logger.info(f"Toggle extra input: action_type={self.action_type_var.get()}")
        if self.action_type_var.get() in ["введення_тексту", "натискання_клавіші"]:
            self.extra_frame.pack(fill=tk.X, padx=1, pady=1)
        else:
            self.extra_frame.pack_forget()

    def setup_profiles_templates_tab(self):
        main_frame = tk.Frame(self.profiles_templates_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        profiles_frame = tk.LabelFrame(main_frame, text="Профілі", font=DEFAULT_CONFIG["default_font"])
        profiles_frame.grid(row=0, column=0, sticky=tk.NSEW, padx=1, pady=1)
        self.profiles_list = tk.Listbox(profiles_frame, height=8, font=DEFAULT_CONFIG["default_font"], width=20)
        self.profiles_list.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        profiles_button_frame = tk.Frame(profiles_frame)
        profiles_button_frame.pack(fill=tk.X, padx=1, pady=1)
        tk.Button(profiles_button_frame, text="Додати", command=self.add_profile,
                  font=DEFAULT_CONFIG["default_font"], width=7).pack(side=tk.LEFT, padx=1)
        tk.Button(profiles_button_frame, text="Оновити", command=self.update_profile_shortcut,
                  font=DEFAULT_CONFIG["default_font"], width=7).pack(side=tk.LEFT, padx=1)
        tk.Button(profiles_button_frame, text="Видалити", command=self.delete_profile,
                  font=DEFAULT_CONFIG["default_font"], width=7).pack(side=tk.LEFT, padx=1)
        templates_frame = tk.LabelFrame(main_frame, text="Шаблони", font=DEFAULT_CONFIG["default_font"])
        templates_frame.grid(row=0, column=1, sticky=tk.NSEW, padx=1, pady=1)
        self.templates_list = tk.Listbox(templates_frame, height=8, font=DEFAULT_CONFIG["default_font"], width=20)
        self.templates_list.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        templates_button_frame = tk.Frame(templates_frame)
        templates_button_frame.pack(fill=tk.X, padx=1, pady=1)
        tk.Button(templates_button_frame, text="Додати", command=self.add_template,
                  font=DEFAULT_CONFIG["default_font"], width=7).pack(side=tk.LEFT, padx=1)
        tk.Button(templates_button_frame, text="Видалити", command=self.delete_template,
                  font=DEFAULT_CONFIG["default_font"], width=7).pack(side=tk.LEFT, padx=1)
        tk.Button(templates_button_frame, text="Прив’язати", command=self.bind_profiles_to_template,
                  font=DEFAULT_CONFIG["default_font"], width=7).pack(side=tk.LEFT, padx=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)

    def bind_profiles_to_template(self):
        selected = self.templates_list.curselection()
        if not selected:
            messagebox.showwarning("Попередження", "Виберіть шаблон!")
            return
        template_names = [self.templates_list.get(idx) for idx in selected]
        bind_window = tk.Toplevel(self.root)
        bind_window.title(f"Прив’язка профілів до шаблонів")
        bind_window.geometry("300x400")
        bind_window.resizable(False, False)
        profiles_frame = tk.LabelFrame(bind_window, text="Доступні профілі", font=DEFAULT_CONFIG["default_font"])
        profiles_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        profiles_canvas = tk.Canvas(profiles_frame)
        profiles_scrollbar = ttk.Scrollbar(profiles_frame, orient=tk.VERTICAL, command=profiles_canvas.yview)
        profiles_scrollable_frame = tk.Frame(profiles_canvas)
        profiles_scrollable_frame.bind("<Configure>",
                                      lambda e: profiles_canvas.configure(scrollregion=profiles_canvas.bbox("all")))
        profiles_canvas.create_window((0, 0), window=profiles_scrollable_frame, anchor="nw")
        profiles_canvas.configure(yscrollcommand=profiles_scrollbar.set)
        profiles_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        profiles_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.bind_profile_check_vars.clear()
        for profile in self.action_manager.data["profiles"].keys():
            var = tk.BooleanVar(value=profile in self.action_manager.data["templates"][template_names[0]]["profiles"])
            self.bind_profile_check_vars[profile] = var
            checkbutton = tk.Checkbutton(profiles_scrollable_frame, text=profile, variable=var,
                                         font=DEFAULT_CONFIG["default_font"])
            checkbutton.pack(anchor=tk.W, padx=5)
        def save_binding():
            selected_profiles = [name for name, var in self.bind_profile_check_vars.items() if var.get()]
            if selected_profiles:
                for template_name in template_names:
                    self.action_manager.data["templates"][template_name]["profiles"] = selected_profiles
            self.action_manager.save_actions()
            self.update_profiles_list()
            self.status_label.config(text=f"Профілі прив’язані до {', '.join(template_names)}")
            logger.info(f"Прив’язані профіли до {selected_profiles}: {template_names}")
            bind_window.destroy()
        button_frame = tk.Frame(bind_window)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Button(button_frame, text="Зберегти", command=save_binding,
                  font=DEFAULT_CONFIG["default_font"], width=7).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Скасувати", command=bind_window.destroy,
                  font=DEFAULT_CONFIG["default_font"], width=7).pack(side=tk.LEFT, padx=5)

    def setup_run_tab(self):
        main_frame = tk.Frame(self.run_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        profiles_frame = tk.LabelFrame(main_frame, text="Профілі", font=DEFAULT_CONFIG["default_font"])
        profiles_frame.grid(row=0, column=0, sticky=tk.NSEW, padx=1, pady=10)
        self.profiles_canvas = tk.Canvas(profiles_frame, height=150)
        self.profiles_scrollbar = ttk.Scrollbar(profiles_frame, orient=tk.VERTICAL, command=self.profiles_canvas.yview)
        self.profiles_scrollable_frame = tk.Frame(self.profiles_canvas)
        self.profiles_scrollable_frame.bind("<Configure>",
                                            lambda e: self.profiles_canvas.configure(scrollregion=self.profiles_canvas.bbox("all")))
        self.profiles_canvas.create_window((0, 0), window=self.profiles_scrollable_frame, anchor="nw")
        self.profiles_canvas.configure(yscrollcommand=self.profiles_scrollbar.set)
        self.profiles_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=1, pady=1)
        self.profiles_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        templates_frame = tk.LabelFrame(main_frame, text="Шаблони", font=DEFAULT_CONFIG["default_font"])
        templates_frame.grid(row=0, column=1, sticky=tk.NSEW, padx=1, pady=10)
        self.run_templates_canvas = tk.Canvas(templates_frame, height=150)
        self.run_templates_scrollbar = ttk.Scrollbar(templates_frame, orient=tk.VERTICAL,
                                                    command=self.run_templates_canvas.yview)
        self.run_templates_scrollable_frame = tk.Frame(self.run_templates_canvas)
        self.run_templates_scrollable_frame.bind("<Configure>",
                                                lambda e: self.run_templates_canvas.configure(
                                                    scrollregion=self.run_templates_scrollable_frame.bbox("all")))
        self.run_templates_canvas.create_window((0, 0), window=self.run_templates_scrollable_frame, anchor="nw")
        self.run_templates_canvas.configure(yscrollcommand=self.run_templates_scrollbar.set)
        self.run_templates_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=1, pady=1)
        self.run_templates_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        bottom_frame = tk.Frame(main_frame)
        bottom_frame.grid(row=1, column=0, columnspan=2, sticky=tk.EW, padx=1, pady=1)
        button_frame = tk.Frame(bottom_frame)
        button_frame.pack(side=tk.LEFT, padx=1)
        run_button = tk.Button(button_frame, text=TEXTS["run_bot"], command=self.start_bot,
                               font=DEFAULT_CONFIG["default_font"], width=7)
        run_button.pack(side=tk.LEFT, padx=1)
        Tooltip(run_button, TEXTS["tooltip_run_bot"])
        self.stop_button = tk.Button(button_frame, text="Зупинити", command=self.stop_bot,
                                     font=DEFAULT_CONFIG["default_font"], width=7, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=2)
        Tooltip(self.stop_button, "Зупинити виконання бота")
        progress_frame = tk.Frame(bottom_frame)
        progress_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        self.progress_label = tk.Label(progress_frame, text="", font=DEFAULT_CONFIG["default_font"])
        self.progress_label.pack(side=tk.LEFT, padx=10)
        self.progress_bar = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=500)

    def copy_actions(self):
        selected_templates = [name for name, var in self.record_template_check_vars.items() if var.get()]
        if not selected_templates:
            messagebox.showerror("Помилка", TEXTS["error_no_template"])
            self.status_label.config(text="Виберіть шаблон!")
            return
        selected = self.actions_list.curselection()
        if not selected:
            messagebox.showwarning("Попередження", TEXTS["error_no_action_selected"])
            self.status_label.config(text="Виберіть дію")
            return
        copy_count = simpledialog.askinteger("Кількість копій", "Введіть кількість копій:", parent=self.root, minvalue=1)
        if not copy_count:
            messagebox.showerror("Помилка", "Введіть додатнє число!")
            self.status_label.config(text="Невірна кількість копій")
            return
        try:
            for template_name in selected_templates:
                actions = self.action_manager.data["templates"][template_name]["actions"]
                copied_actions = []
                for idx in selected:
                    action = actions[idx].copy()
                    action["action"] = f"{action['action']} (копія)"
                    copied_actions.append(action)
                for _ in range(copy_count):
                    start_index = len(actions)
                    actions.extend([action.copy() for action in copied_actions])
                    self.undo_stack.append(("copy", template_name, start_index, [action.copy() for action in copied_actions]))
            self.action_manager.save_actions()
            self.update_actions_list()
            self.status_label.config(text=f"Скопійовано {len(selected) * copy_count} дій")
            logger.info(f"Скопійовано {len(selected) * copy_count} дій для шаблонів: {selected_templates}")
        except Exception as e:
            log_error("Помилка копіювання дій", e)
            messagebox.showerror("Помилка", "Не вдалося скопіювати дії!")
            self.status_label.config(text="Помилка копіювання")

    def start_recording(self):
        selected_templates = [name for name, var in self.record_template_check_vars.items() if var.get()]
        if not selected_templates:
            messagebox.showerror("Помилка", TEXTS["error_no_template"])
            self.status_label.config(text="Виберіть шаблон")
            return
        action_type = self.action_type_var.get()
        action_name = self.action_name_entry.get()
        extra_value = self.extra_entry.get() if action_type in ["введення_тексту", "натискання_клавіші"] else ""
        logger.info(f"Starting recording: action_type={action_type}")
        if not action_name:
            messagebox.showerror("Помилка", TEXTS["error_no_action_name"])
            self.status_label.config(text="Введіть назву")
            return
        if action_type in ["введення_тексту", "натискання_клавіші"] and not extra_value:
            messagebox.showerror("Помилка", TEXTS["error_no_extra_input"])
            self.status_label.config(text="Введіть текст/клавішу")
            return
        delay_value = self.delay_entry.get()
        if delay_value:
            try:
                float(delay_value)
            except ValueError:
                messagebox.showerror("Помилка", "Затримка має бути числовим значенням!")
                self.status_label.config(text="Невірна затримка")
                return
        self.recording = True
        self.record_button.config(state=tk.DISABLED)
        self.delete_action_button.config(state=tk.DISABLED)
        self.edit_action_button.config(state=tk.DISABLED)
        self.copy_action_button.config(state=tk.DISABLED)
        self.cancel_edit_button.config(state=tk.DISABLED)
        self.move_up_button.config(state=tk.DISABLED)
        self.move_down_button.config(state=tk.DISABLED)
        self.timer_seconds = DEFAULT_CONFIG["timer_duration"] // 1000
        self.timer_label.config(text=TEXTS["status_recording"].format(seconds=self.timer_seconds))
        self.current_templates = selected_templates
        self.mouse_positions = []
        self.last_fixed_position = None

        def monitor_recording():
            if not self.recording:
                self.timer_label.config(text="")
                self.record_button.config(state=tk.NORMAL)
                self.delete_action_button.config(state=tk.NORMAL)
                self.edit_action_button.config(state=tk.NORMAL)
                self.copy_action_button.config(state=tk.NORMAL)
                self.cancel_edit_button.config(state=tk.NORMAL if self.edit_mode else tk.DISABLED)
                self.move_up_button.config(state=tk.NORMAL)
                self.move_down_button.config(state=tk.NORMAL)
                return
            current_pos = pyautogui.position()
            self.mouse_positions.append(current_pos)
            if len(self.mouse_positions) > 5:
                self.mouse_positions.pop(0)
                if all(abs(current_pos[0] - pos[0]) <= DEFAULT_CONFIG["mouse_fixation_threshold"] and
                       abs(current_pos[1] - pos[1]) <= DEFAULT_CONFIG["mouse_fixation_threshold"]
                       for pos in self.mouse_positions):
                    if self.last_fixed_position != current_pos:
                        self.last_fixed_position = current_pos
                        show_debug_point(current_pos[0], current_pos[1])
                        logger.info(f"Мишка зафіксована: {current_pos}")
            self.root.after(DEFAULT_CONFIG["mouse_check_interval"], monitor_recording)

        def update_timer():
            if not self.recording:
                return
            self.timer_seconds -= 1
            if self.timer_seconds >= 0:
                self.timer_label.config(text=TEXTS["status_recording"].format(seconds=self.timer_seconds))
                self.root.after(1000, update_timer)
            else:
                self.fix_action()

        monitor_recording()
        update_timer()

    def fix_action(self):
        selected_templates = self.current_templates
        action_type = self.action_type_var.get()
        action_name = self.action_name_entry.get()
        x, y = pyautogui.position()
        logger.info(f"Fixing action: type={action_type}, name={action_name}, x={x}, y={y}, templates={selected_templates}")
        current_resolution = {"width": pyautogui.size().width, "height": pyautogui.size().height}
        x = min(max(0, x), current_resolution["width"] - 1)
        y = min(max(0, y), current_resolution["height"] - 1)
        show_checkmark(x, y)
        action = {"action": action_name, "x": x, "y": y, "type": action_type}
        if action_type in ["введення_тексту", "натискання_клавіші"]:
            extra_value = self.extra_entry.get()
            if action_type == "введення_тексту":
                if not extra_value:
                    logger.error("extra_entry is empty during fix_action")
                    messagebox.showerror("Помилка", TEXTS["error_no_extra_input"])
                    self.recording = False
                    self.timer_label.config(text="")
                    self.record_button.config(state=tk.NORMAL)
                    self.delete_action_button.config(state=tk.NORMAL)
                    self.edit_action_button.config(state=tk.NORMAL)
                    self.copy_action_button.config(state=tk.NORMAL)
                    self.move_up_button.config(state=tk.NORMAL)
                    self.move_down_button.config(state=tk.NORMAL)
                    return
                action["text"] = extra_value
            elif action_type == "натискання_клавіші":
                if not extra_value:
                    logger.error("extra_entry is empty during fix_action")
                    messagebox.showerror("Помилка", TEXTS["error_no_extra_input"])
                    self.recording = False
                    self.timer_label.config(text="")
                    self.record_button.config(state=tk.NORMAL)
                    self.delete_action_button.config(state=tk.NORMAL)
                    self.edit_action_button.config(state=tk.NORMAL)
                    self.copy_action_button.config(state=tk.NORMAL)
                    self.move_up_button.config(state=tk.NORMAL)
                    self.move_down_button.config(state=tk.NORMAL)
                    return
                action["key"] = extra_value
            logger.info(f"Extra value for {action_type}: {extra_value}")
        delay_value = self.delay_entry.get()
        if delay_value:
            try:
                action["delay"] = float(delay_value)
            except ValueError:
                logger.warning(f"Невірне значення затримки: {delay_value}, ігнорується")
        try:
            for template_name in selected_templates:
                if template_name not in self.action_manager.data["templates"]:
                    self.action_manager.data["templates"][template_name] = {"profiles": [], "actions": []}
                action_with_profiles = action.copy()
                action_with_profiles["profiles"] = self.action_manager.data["templates"][template_name]["profiles"]
                if self.edit_mode:
                    self.undo_stack.append(("edit", template_name, self.edit_action_index,
                                            self.action_manager.data["templates"][template_name]["actions"][self.edit_action_index]))
                    self.action_manager.data["templates"][template_name]["actions"][self.edit_action_index] = action_with_profiles
                    logger.info(f"Edited action in {template_name}: {action_with_profiles}")
                else:
                    self.undo_stack.append(("add", template_name, len(self.action_manager.data["templates"][template_name]["actions"]), action_with_profiles))
                    self.action_manager.data["templates"][template_name]["actions"].append(action_with_profiles)
                    logger.info(f"Added action to {template_name}: {action_with_profiles}")
            self.action_manager.save_actions()
            self.update_actions_list()
            self.status_label.config(text=TEXTS["status_action_saved"] if not self.edit_mode else TEXTS["status_action_edited"])
        except Exception as e:
            log_error("Помилка збереження дії", e)
            messagebox.showerror("Помилка", "Не вдалося зберегти дію!")
            self.status_label.config(text="Помилка збереження")
        self.action_name_entry.delete(0, tk.END)
        self.x_entry.delete(0, tk.END)
        self.extra_entry.delete(0, tk.END)
        self.delay_entry.delete(0, tk.END)
        self.recording = False
        self.timer_label.config(text="")
        self.record_button.config(state=tk.NORMAL)
        self.delete_action_button.config(state=tk.NORMAL)
        self.edit_action_button.config(state=tk.NORMAL)
        self.copy_action_button.config(state=tk.NORMAL)
        self.move_up_button.config(state=tk.NORMAL)
        self.move_down_button.config(state=tk.NORMAL)
        self.edit_mode = False
        self.cancel_edit_button.config(state=tk.DISABLED)

    def update_actions_list(self):
        self.actions_list.delete(0, tk.END)
        selected_templates = [name for name, var in self.record_template_check_vars.items() if var.get()]
        logger.info(f"Updating actions list for templates: {selected_templates}")
        for template_name in selected_templates:
            if template_name in self.action_manager.data["templates"]:
                for idx, action in enumerate(self.action_manager.data["templates"][template_name]["actions"], 1):
                    extra_info = ""
                    if action["type"] == "введення_тексту":
                        extra_info = f" ({action.get('text', '')})"
                    elif action["type"] == "натискання_клавіші":
                        extra_info = f" ({action.get('key', '')})"
                    self.actions_list.insert(tk.END, f"{idx}: {action['action']} ({template_name}): {action['type']}{extra_info}")

    def delete_action(self):
        selected_templates = [name for name, var in self.record_template_check_vars.items() if var.get()]
        if not selected_templates:
            messagebox.showerror("Помилка", TEXTS["error_no_template"])
            return
        selected = self.actions_list.curselection()
        if not selected:
            messagebox.showwarning("Попередження", TEXTS["error_no_action_selected"])
            return
        for idx in sorted(selected, reverse=True):
            for template_name in selected_templates:
                action = self.action_manager.data["templates"][template_name]["actions"][idx]
                self.undo_stack.append(("delete", template_name, idx, action))
                del self.action_manager.data["templates"][template_name]["actions"][idx]
        self.action_manager.save_actions()
        self.update_actions_list()
        self.status_label.config(text="Дію видалено")

    def move_action_up(self):
        selected_templates = [name for name, var in self.record_template_check_vars.items() if var.get()]
        if not selected_templates:
            messagebox.showerror("Помилка", TEXTS["error_no_template"])
            logger.error("Не вибрано шаблонів для переміщення дії")
            return
        selected = self.actions_list.curselection()
        if not selected:
            messagebox.showwarning("Попередження", TEXTS["error_no_action_selected"])
            logger.warning("Не вибрано дію для переміщення")
            return
        action_index = selected[0]
        if action_index == 0:
            messagebox.showinfo("Інформація", "Дія вже на початку списку!")
            logger.info("Спроба перемістити першу дію вгору")
            return
        try:
            for template_name in selected_templates:
                actions = self.action_manager.data["templates"][template_name]["actions"]
                actions[action_index], actions[action_index - 1] = actions[action_index - 1], actions[action_index]
                logger.info(f"Переміщено дію {actions[action_index]['action']} з позиції {action_index + 1} на {action_index} у шаблоні {template_name}")
            self.action_manager.save_actions()
            self.update_actions_list()
            self.actions_list.selection_clear(0, tk.END)
            self.actions_list.selection_set(action_index - 1)
            self.status_label.config(text="Дію переміщено вгору")
        except Exception as e:
            log_error("Помилка переміщення дії вгору", e)
            messagebox.showerror("Помилка", "Не вдалося перемістити дію!")

    def move_action_down(self):
        selected_templates = [name for name, var in self.record_template_check_vars.items() if var.get()]
        if not selected_templates:
            messagebox.showerror("Помилка", TEXTS["error_no_template"])
            logger.error("Не вибрано шаблонів для переміщення дії")
            return
        selected = self.actions_list.curselection()
        if not selected:
            messagebox.showwarning("Попередження", TEXTS["error_no_action_selected"])
            logger.warning("Не вибрано дію для переміщення")
            return
        action_index = selected[0]
        max_index = len(self.action_manager.data["templates"][selected_templates[0]]["actions"]) - 1
        if action_index >= max_index:
            messagebox.showinfo("Інформація", "Дія вже в кінці списку!")
            logger.info("Спроба перемістити останню дію вниз")
            return
        try:
            for template_name in selected_templates:
                actions = self.action_manager.data["templates"][template_name]["actions"]
                actions[action_index], actions[action_index + 1] = actions[action_index + 1], actions[action_index]
                logger.info(f"Переміщено дію {actions[action_index]['action']} з позиції {action_index + 1} на {action_index + 2} у шаблоні {template_name}")
            self.action_manager.save_actions()
            self.update_actions_list()
            self.actions_list.selection_clear(0, tk.END)
            self.actions_list.selection_set(action_index + 1)
            self.status_label.config(text="Дію переміщено вниз")
        except Exception as e:
            log_error("Помилка переміщення дії вниз", e)
            messagebox.showerror("Помилка", "Не вдалося перемістити дію!")

    def edit_action_in_window(self):
        selected_templates = [name for name, var in self.record_template_check_vars.items() if var.get()]
        if not selected_templates:
            messagebox.showerror("Помилка", TEXTS["error_no_template"])
            return
        selected = self.actions_list.curselection()
        if not selected:
            messagebox.showwarning("Попередження", TEXTS["error_no_action_selected"])
            return
        self.edit_action_index = selected[0]
        template_name = selected_templates[0]
        action = self.action_manager.data["templates"][template_name]["actions"][self.edit_action_index]
        logger.info(f"Відкриття вікна редагування для дії: {action['action']}, тип: {action['type']}")
        edit_window = tk.Toplevel(self.root)
        edit_window.title("Редагування дії")
        edit_window.geometry("300x300")
        edit_window.resizable(False, False)
        edit_window.transient(self.root)
        edit_window.grab_set()
        main_frame = tk.Frame(edit_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        tk.Label(main_frame, text="Назва дії:", font=DEFAULT_CONFIG["default_font"]).pack(anchor=tk.W, padx=5, pady=2)
        action_name_entry = tk.Entry(main_frame, font=DEFAULT_CONFIG["default_font"], width=25)
        action_name_entry.insert(0, action["action"])
        action_name_entry.pack(fill=tk.X, padx=5, pady=2)
        Tooltip(action_name_entry, TEXTS["tooltip_action_name"])
        tk.Label(main_frame, text="Тип дії:", font=DEFAULT_CONFIG["default_font"]).pack(anchor=tk.W, padx=5, pady=2)
        action_type_var = tk.StringVar(value=action["type"])
        action_type_menu = tk.OptionMenu(main_frame, action_type_var, *TEXTS["action_types"])
        action_type_menu.config(font=DEFAULT_CONFIG["default_font"], width=20)
        action_type_menu.pack(fill=tk.X, padx=5, pady=2)
        tk.Label(main_frame, text="Затримка (сек):", font=DEFAULT_CONFIG["default_font"]).pack(anchor=tk.W, padx=5, pady=2)
        delay_entry = tk.Entry(main_frame, font=DEFAULT_CONFIG["default_font"], width=10)
        if "delay" in action:
            delay_entry.insert(0, str(action["delay"]))
        else:
            default_delay = DEFAULT_CONFIG["action_delay"].get(action["type"], 2.0)
            if action["type"] == "натискання_клавіші" and action.get("key") == "enter":
                default_delay = DEFAULT_CONFIG["action_delay"]["enter_key"]
            delay_entry.insert(0, str(default_delay))
        delay_entry.pack(fill=tk.X, padx=5, pady=2)
        Tooltip(delay_entry, "Введіть затримку в секундах після виконання дії")
        extra_frame = tk.Frame(main_frame)
        tk.Label(extra_frame, text="Текст/Клавіша/Селектор:", font=DEFAULT_CONFIG["default_font"]).pack(side=tk.LEFT, padx=5)
        extra_entry = tk.Entry(extra_frame, font=DEFAULT_CONFIG["default_font"], width=15)
        extra_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        Tooltip(extra_entry, TEXTS["tooltip_extra_input"])
        if action["type"] in ["введення_тексту", "натискання_клавіші"]:
            extra_value = action.get("text", action.get("key", ""))
            extra_entry.insert(0, extra_value)
            extra_frame.pack(fill=tk.X, padx=5, pady=2)
            logger.info(f"Поле Текст/Клавіша/Селектор відображено з ініціалізацією: {extra_value}")

        def toggle_extra_input(*args):
            current_type = action_type_var.get()
            logger.info(f"Зміна типу дії: {current_type}")
            extra_frame.pack_forget()
            if current_type in ["введення_тексту", "натискання_клавіші"]:
                extra_frame.pack(fill=tk.X, padx=5, pady=2)
                extra_entry.delete(0, tk.END)
                if current_type == action["type"]:
                    extra_value = action.get("text", action.get("key", ""))
                    extra_entry.insert(0, extra_value)
                    logger.info(f"Відновлено значення Текст/Клавіша/Сошук: {extra_value}")
                else:
                    logger.info("Поле Текст/Клавіша/Сошук очищено для нового типу")

        action_type_var.trace("w", toggle_extra_input)
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)

        def save_edit():
            new_action_name = action_name_entry.get()
            if not new_action_name:
                messagebox.showerror("Помилка", TEXTS["error_no_action_name"])
                return
            new_action_type = action_type_var.get()
            if new_action_type in ["введення_тексту", "натискання_клавіші"] and not extra_entry.get():
                messagebox.showerror("Помилка", TEXTS["error_no_extra_input"])
                return
            delay_value = delay_entry.get()
            if delay_value:
                try:
                    float(delay_value)
                except ValueError:
                    messagebox.showerror("Помилка", "Затримка має бути числовим значенням!")
                    return
            new_action = {
                "action": new_action_name,
                "x": action["x"],
                "y": action["y"],
                "type": new_action_type,
                "profiles": self.action_manager.data["templates"][template_name]["profiles"]
            }
            if new_action_type == "введення_тексту":
                new_action["text"] = extra_entry.get()
            elif new_action_type == "натискання_клавіші":
                new_action["key"] = extra_entry.get()
            if delay_value:
                new_action["delay"] = float(delay_value)
            self.undo_stack.append(("edit", template_name, self.edit_action_index,
                                    self.action_manager.data["templates"][template_name]["actions"][self.edit_action_index]))
            self.action_manager.data["templates"][template_name]["actions"][self.edit_action_index] = new_action
            self.action_manager.save_actions()
            self.update_actions_list()
            self.status_label.config(text=TEXTS["status_action_edited"])
            logger.info(f"Відредаговано дію: {new_action} у {template_name}")
            edit_window.destroy()

        tk.Button(button_frame, text="Зберегти", command=save_edit,
                  font=DEFAULT_CONFIG["default_font"], width=7).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Скасувати", command=edit_window.destroy,
                  font=DEFAULT_CONFIG["default_font"], width=7).pack(side=tk.LEFT, padx=5)

    def cancel_edit(self):
        self.edit_mode = False
        self.record_button.config(text="Записати", command=self.start_recording)
        self.cancel_edit_button.config(state=tk.DISABLED)
        self.action_name_entry.delete(0, tk.END)
        self.x_entry.delete(0, tk.END)
        self.extra_entry.delete(0, tk.END)
        self.delay_entry.delete(0, tk.END)
        self.status_label.config(text="Редагування скасовано")

    def update_profiles_list(self):
        self.profiles_list.delete(0, tk.END)
        profiles = list(self.action_manager.data["profiles"].keys())
        logger.info(f"Оновлення списку профілів: {profiles}")
        for profile in profiles:
            self.profiles_list.insert(tk.END, profile)
        for widget in self.profiles_scrollable_frame.winfo_children():
            widget.destroy()
        self.profile_check_vars.clear()
        self.profile_check_buttons.clear()
        selected_templates = [name for name, var in self.run_template_vars.items() if var.get()]
        run_profiles = []
        for template_name in selected_templates:
            run_profiles.extend(self.action_manager.data["templates"][template_name]["profiles"])
        run_profiles = list(set(run_profiles))
        for profile in run_profiles:
            var = tk.BooleanVar()
            self.profile_check_vars[profile] = var
            button = tk.Checkbutton(self.profiles_scrollable_frame, text=profile, variable=var,
                                    font=DEFAULT_CONFIG["default_font"])
            button.pack(anchor=tk.W, padx=1)
            self.profile_check_buttons[profile] = button

    def update_templates_list(self):
        self.templates_list.delete(0, tk.END)
        templates = list(self.action_manager.data["templates"].keys())
        logger.info(f"Оновлення списку шаблонів: {templates}")
        for template in templates:
            self.templates_list.insert(tk.END, template)
        for widget in self.templates_scrollable_frame.winfo_children():
            widget.destroy()
        self.record_template_check_vars.clear()
        for template in templates:
            var = tk.BooleanVar()
            self.record_template_check_vars[template] = var
            checkbutton = tk.Checkbutton(self.templates_scrollable_frame, text=template, variable=var,
                                         font=DEFAULT_CONFIG["default_font"],
                                         command=self.update_actions_list)
            checkbutton.pack(anchor=tk.W, padx=1)
        for widget in self.run_templates_scrollable_frame.winfo_children():
            widget.destroy()
        self.run_template_vars.clear()
        for template in templates:
            var = tk.BooleanVar()
            self.run_template_vars[template] = var
            checkbutton = tk.Checkbutton(self.run_templates_scrollable_frame, text=template, variable=var,
                                         font=DEFAULT_CONFIG["default_font"],
                                         command=self.update_profiles_list)
            checkbutton.pack(anchor=tk.W, padx=1)

    def add_profile(self):
        shortcut_name, shortcut_path = get_shortcut_name_at_position(0, 0)
        if not shortcut_path:
            messagebox.showerror("Помилка", TEXTS["error_no_shortcut"])
            return
        profile_name = shortcut_name
        if not profile_name:
            messagebox.showerror("Помилка", "Не вдалося отримати назву ярлика!")
            return
        if profile_name in self.action_manager.data["profiles"]:
            messagebox.showerror("Помилка", f"Профіль '{profile_name}' уже існує!")
            return
        self.action_manager.data["profiles"][profile_name] = {"shortcut_path": shortcut_path}
        self.action_manager.save_actions()
        self.update_profiles_list()
        self.status_label.config(text=f"Профіль '{profile_name}' додано")
        logger.info(f"Додано профіль: {profile_name}, шлях: {shortcut_path}")

    def update_profile_shortcut(self):
        selected = self.profiles_list.curselection()
        if not selected:
            messagebox.showwarning("Попередження", "Виберіть профіль!")
            return
        profile_name = self.profiles_list.get(selected[0])
        shortcut_name, shortcut_path = get_shortcut_name_at_position(0, 0)
        if not shortcut_path:
            messagebox.showerror("Помилка", TEXTS["error_no_shortcut"])
            return
        self.action_manager.data["profiles"][profile_name]["shortcut_path"] = shortcut_path
        self.action_manager.save_actions()
        self.status_label.config(text=f"Ярлик для '{profile_name}' оновлено")
        logger.info(f"Оновлено ярлик для профілю: {profile_name}, шлях: {shortcut_path}")

    def delete_profile(self):
        selected = self.profiles_list.curselection()
        if not selected:
            messagebox.showwarning("Попередження", "Виберіть профіль!")
            return
        profile_name = self.profiles_list.get(selected[0])
        for template in self.action_manager.data["templates"].values():
            if profile_name in template["profiles"]:
                template["profiles"].remove(profile_name)
            for action in template["actions"]:
                if profile_name in action["profiles"]:
                    action["profiles"].remove(profile_name)
        del self.action_manager.data["profiles"][profile_name]
        self.action_manager.save_actions()
        self.update_profiles_list()
        self.status_label.config(text=f"Профіль '{profile_name}' видалено")
        logger.info(f"Видалено профіль: {profile_name}")

    def add_template(self):
        template_name = tk.simpledialog.askstring("Додати шаблон", "Введіть назву шаблону:", parent=self.root)
        if not template_name:
            return
        if template_name in self.action_manager.data["templates"]:
            messagebox.showerror("Помилка", f"Шаблон '{template_name}' уже існує!")
            return
        self.action_manager.data["templates"][template_name] = {"profiles": [], "actions": []}
        self.action_manager.save_actions()
        self.update_templates_list()
        self.status_label.config(text=f"Шаблон '{template_name}' додано")
        logger.info(f"Додано шаблон: {template_name}")

    def delete_template(self):
        selected = self.templates_list.curselection()
        if not selected:
            messagebox.showwarning("Попередження", "Виберіть шаблон!")
            return
        template_name = self.templates_list.get(selected[0])
        del self.action_manager.data["templates"][template_name]
        self.action_manager.save_actions()
        self.update_templates_list()
        self.status_label.config(text=f"Шаблон '{template_name}' видалено")
        logger.info(f"Видалено шаблон: {template_name}")

    def check_resolution(self, template_name):
        current_resolution = pyautogui.size()
        if current_resolution.width != self.action_manager.screen_width or current_resolution.height != self.action_manager.screen_height:
            messagebox.showwarning("Попередження",
                                  f"Роздільна здатність екрана змінилась!\nЗбережено: {self.action_manager.screen_width}x{self.action_manager.screen_height}\nПоточна: {current_resolution.width}x{current_resolution.height}")

    def start_bot(self):
        self.running = True
        self.stop_button.config(state=tk.NORMAL)
        self.deferred_actions = []
        selected_templates = [name for name, var in self.run_template_vars.items() if var.get()]
        logger.info(f"Запуск бота: шаблони={selected_templates}")
        if not selected_templates:
            messagebox.showerror("Помилка", TEXTS["error_no_template"])
            self.status_label.config(text="Виберіть шаблон")
            return

        total_actions = 0
        for template_name in selected_templates:
            template = self.action_manager.data["templates"][template_name]
            if not template["profiles"]:
                messagebox.showerror("Помилка", f"Шаблон '{template_name}' не має прив’язаних профілів!")
                self.status_label.config(text="Прив’яжіть профілі")
                return
            total_actions += len(template["actions"]) * len(template["profiles"])
        current_action = [0]

        def update_progress(action_name, profile_name, template_name):
            current_action[0] += 1
            progress = (current_action[0] / total_actions) * 100 if total_actions > 0 else 0
            logger.debug(f"Оновлення прогресу: action={action_name}, profile={profile_name}, progress={progress}")
            try:
                self.progress_label.config(
                    text=f"{template_name}: {TEXTS['status_running'].format(action=action_name, profile=profile_name, progress=progress)}"
                )
            except ValueError as e:
                logger.error(f"Помилка форматування прогресу: {e}")
                self.progress_label.config(text=f"{template_name}: {action_name} ({profile_name})")
            self.progress_bar["value"] = progress
            self.root.update()

        def reset_progress():
            self.progress_label.config(text="")
            self.progress_bar["value"] = 0

        def run_profile(profile_name, template_name, callback):
            if not self.running:
                callback()
                return
            shortcut_path = self.action_manager.data["profiles"].get(profile_name, {}).get("shortcut_path", "")
            if not shortcut_path or not os.path.exists(shortcut_path):
                messagebox.showinfo("Оновлення", f"Виберіть ярлик для '{profile_name}'")
                shortcut_name, new_path = get_shortcut_name_at_position(0, 0)
                if not new_path:
                    messagebox.showerror("Помилка", TEXTS["error_no_shortcut"])
                    self.status_label.config(text="Ярлик не вибрано")
                    logger.error(f"Ярлик не вибрано для {profile_name}")
                    callback()
                    return
                self.action_manager.data["profiles"][profile_name]["shortcut_path"] = new_path
                self.action_manager.save_actions()
                self.update_profiles_list()
                shortcut_path = new_path
            if not open_shortcut(shortcut_path):
                messagebox.showerror("Помилка", TEXTS["error_open_shortcut"].format(path=shortcut_path))
                self.status_label.config(text="Помилка ярлика")
                callback()
                return
            self.check_resolution(template_name)
            current_resolution = pyautogui.size()
            scale_x = min(max(current_resolution.width / self.action_manager.screen_width, 0.5), 2.0)
            scale_y = min(max(current_resolution.height / self.action_manager.screen_height, 0.5), 2.0)

            def execute_action(action, action_callback, retries=2, index=0):
                if not self.running or profile_name not in action.get("profiles", []):
                    action_callback()
                    return
                logger.info(f"Виконуємо: {action['action']} для {profile_name} у {template_name}")
                update_progress(action['action'], profile_name, template_name)
                try:
                    x, y = int(action['x'] * scale_x), int(action['y'] * scale_y)
                    x = min(max(0, x), current_resolution.width - 1)
                    y = min(max(0, y), current_resolution.height - 1)
                    logger.info(f"Координати: {action['action']}: x={x}, y={y}")
                    if x < 0 or y < 0 or x >= current_resolution.width or y >= current_resolution.height:
                        raise ValueError(f"Недійсні координати: x={x}, y={y}")
                    show_action_number(x, y, index)
                    pyautogui.moveTo(x, y)
                    show_debug_point(x, y)
                    delay = action.get("delay", DEFAULT_CONFIG["action_delay"].get(action['type'], 2.0))
                    if action['type'] == "натискання_клавіші" and action.get("key") == "enter":
                        delay = action.get("delay", DEFAULT_CONFIG["action_delay"]["enter_key"])

                    action_handlers = {
                        "подвійний_клік": lambda: pyautogui.doubleClick(),
                        "клік": lambda: pyautogui.click(),
                        "введення_тексту": lambda: (
                            pyautogui.click(x, y),
                            time.sleep(0.5),
                            pyautogui.hotkey('ctrl', 'a'),
                            pyautogui.press('delete'),
                            pyautogui.write(action['text'], interval=0.1),
                            logger.info(f"Текст введено: {action['text']}")
                        ),
                        "натискання_клавіші": lambda: pyautogui.press(action['key']),
                    }

                    handler = action_handlers.get(action['type'])
                    if handler:
                        handler()
                        logger.info(f"Виконано дію: {action['type']}")
                        async_delay(self.root, int(delay * 1000), action_callback)
                    else:
                        logger.info(f"Дія {action['type']} пропущена (немає селектора або WebDriver)")
                        async_delay(self.root, int(delay * 1000), action_callback)

                except Exception as e:
                    log_error(f"Помилка виконання дії {action['action']}", e)
                    if retries > 0:
                        logger.info(f"Повторна спроба: {action['action']}, залишилося спроб: {retries - 1}")
                        async_delay(self.root, 1000, lambda: execute_action(action, action_callback, retries - 1, index))
                    else:
                        logger.warning(f"Дія {action['action']} відкладена")
                        self.deferred_actions.append((template_name, profile_name, action))
                        action_callback()

            def execute_deferred_actions(deferred_callback):
                if not self.running or not self.deferred_actions:
                    deferred_callback()
                    return
                template_name, profile_name, action = self.deferred_actions.pop(0)
                logger.error(f"Відкладена дія: {action['action']} для {profile_name} у {template_name}")
                execute_action(action, lambda: execute_deferred_actions(deferred_callback), index=0)

            def process_actions(index=0):
                if not self.running or index >= len(self.action_manager.data["templates"][template_name]["actions"]):
                    logger.info(
                        f"Перевірка завершення профілю: {profile_name}, шаблон: {template_name}, індекс: {index}")
                    execute_deferred_actions(lambda: (self.profile_check_buttons[profile_name].config(bg="lightgreen"),
                                                      self.root.update(),
                                                      logger.info(f"Завершено: {profile_name} для {template_name}"),
                                                      callback()))
                    return
                action = self.action_manager.data["templates"][template_name]["actions"][index]
                execute_action(action, lambda: process_actions(index + 1), index=index)

            async_delay(self.root, 5000, lambda: process_actions())

        def run_template(template_index=0):
            if not self.running or template_index >= len(selected_templates):
                self.stop_button.config(state=tk.DISABLED)
                reset_progress()
                self.status_label.config(text=TEXTS["status_completed"] if self.running else "Виконання зупинено")
                logger.info(f"Усі шаблони виконано або зупинено")
                return
            template_name = selected_templates[template_index]
            logger.info(f"Починаємо виконання шаблону: {template_name}")
            for button in self.profile_check_buttons.values():
                button.config(bg="SystemButtonFace")

            selected_profiles = [profile for profile, var in self.profile_check_vars.items()
                                 if var.get() and profile in self.action_manager.data["templates"][template_name][
                                     "profiles"]]

            if not selected_profiles:
                logger.warning(f"Жоден профіль не вибрано для шаблону: {template_name}")
                messagebox.showwarning("Попередження", f"Виберіть хоча б один профіль для шаблону '{template_name}'!")
                run_template(template_index + 1)
                return

            def run_all_profiles(profile_index=0):
                if not self.running or profile_index >= len(selected_profiles):
                    logger.info(f"Завершено шаблон: {template_name}")
                    run_template(template_index + 1)
                    return
                run_profile(selected_profiles[profile_index], template_name,
                            lambda: run_all_profiles(profile_index + 1))

            run_all_profiles()

        reset_progress()
        run_template()

    def stop_bot(self):
        self.running = False
        self.stop_button.config(state=tk.DISABLED)
        self.status_label.config(text="Виконання зупинено")
        logger.info("Виконання бота зупинено")
        self.progress_label.config(text="")
        self.progress_bar["value"] = 0

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = MainWindow()
    app.run()