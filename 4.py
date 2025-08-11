import tkinter as tk
from tkinter import messagebox
import subprocess
import threading

def upload_files():
    username = entry_user.get().strip()
    repo = entry_repo.get().strip()
    email = entry_email.get().strip()
    token = entry_token.get().strip()

    if not username or not repo or not token:
        messagebox.showerror("Помилка", "Будь ласка, заповніть всі обов'язкові поля!")
        return

    btn_start.config(state="disabled")
    status_label.config(text="⏳ Завантаження файлів на GitHub...", fg="blue")

    def run_git_commands():
        try:
            remote_url = f"https://{token}@github.com/{username}/{repo}.git"

            commands = [
                ["git", "init"],
                ["git", "config", "user.name", username],
                ["git", "config", "user.email", email if email else f"{username}@users.noreply.github.com"],
                ["git", "config", "--global", "--unset", "credential.helper"],
                ["git", "rm", "--cached", "-r", "oneone"],
                ["git", "add", "."],
                ["git", "commit", "-m", "upload via script"],
                ["git", "branch", "-M", "main"],
                ["git", "remote", "set-url", "origin", remote_url],
                ["git", "push", "-u", "origin", "main", "--force"]
            ]

            for cmd in commands:
                subprocess.run(cmd, shell=True)

            status_label.config(text="✅ Завантаження завершено!", fg="green")
        except Exception as e:
            messagebox.showerror("Помилка", str(e))
            status_label.config(text="❌ Помилка завантаження", fg="red")
        finally:
            btn_start.config(state="normal")

    threading.Thread(target=run_git_commands).start()


# Функція для контекстного меню "Вставити"
def show_context_menu(event, entry_widget):
    context_menu = tk.Menu(root, tearoff=0)
    context_menu.add_command(label="Вставити", command=lambda: entry_widget.event_generate("<<Paste>>"))
    context_menu.tk_popup(event.x_root, event.y_root)

# Створення вікна
root = tk.Tk()
root.title("GitHub Uploader")
root.geometry("400x300")

tk.Label(root, text="GitHub Username:").pack(pady=3)
entry_user = tk.Entry(root, width=40)
entry_user.pack()
entry_user.bind("<Button-3>", lambda e: show_context_menu(e, entry_user))

tk.Label(root, text="Repository Name:").pack(pady=3)
entry_repo = tk.Entry(root, width=40)
entry_repo.pack()
entry_repo.bind("<Button-3>", lambda e: show_context_menu(e, entry_repo))

tk.Label(root, text="GitHub Email (необов'язково):").pack(pady=3)
entry_email = tk.Entry(root, width=40)
entry_email.pack()
entry_email.bind("<Button-3>", lambda e: show_context_menu(e, entry_email))

tk.Label(root, text="GitHub Token або пароль:").pack(pady=3)
entry_token = tk.Entry(root, width=40, show="*")
entry_token.pack()
entry_token.bind("<Button-3>", lambda e: show_context_menu(e, entry_token))

btn_start = tk.Button(root, text="🚀 Старт", command=upload_files, bg="green", fg="white")
btn_start.pack(pady=15)

status_label = tk.Label(root, text="Очікую на введення даних...", fg="gray")
status_label.pack(pady=5)

root.mainloop()
