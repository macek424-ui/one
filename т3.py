import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import os

# Додаємо меню для копіювання/вставки
def make_entry_with_paste(parent, show=None):
    entry = tk.Entry(parent, width=50, show=show)
    menu = tk.Menu(entry, tearoff=0)
    menu.add_command(label="Вставити", command=lambda: entry.event_generate("<<Paste>>"))
    menu.add_command(label="Копіювати", command=lambda: entry.event_generate("<<Copy>>"))
    menu.add_command(label="Вирізати", command=lambda: entry.event_generate("<<Cut>>"))
    entry.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root))
    return entry

def select_folder():
    folder = filedialog.askdirectory()
    folder_entry.delete(0, tk.END)
    folder_entry.insert(0, folder)

def upload_files():
    username = username_entry.get().strip()
    email = email_entry.get().strip()
    token = token_entry.get().strip()
    repo_url = repo_entry.get().strip()
    folder_path = folder_entry.get().strip()

    if not all([username, email, token, repo_url, folder_path]):
        messagebox.showerror("Помилка", "Заповніть всі поля!")
        return

    try:
        os.chdir(folder_path)

        commands = [
            'rmdir -Recurse -Force .git',
            'git init',
            f'git config user.name "{username}"',
            f'git config user.email "{email}"',
            'git add .',
            'git commit -m "first commit"',
            'git branch -M main',
            f'git remote add origin https://{username}:{token}@{repo_url}',
            'git push -u origin main --force'
        ]

        for cmd in commands:
            subprocess.run(["powershell", "-Command", cmd], check=True)

        messagebox.showinfo("Готово", "Файли успішно завантажені на GitHub!")

    except Exception as e:
        messagebox.showerror("Помилка", str(e))

root = tk.Tk()
root.title("GitHub Uploader")
root.geometry("500x400")

tk.Label(root, text="GitHub логін:").pack()
username_entry = make_entry_with_paste(root)
username_entry.pack()

tk.Label(root, text="Email:").pack()
email_entry = make_entry_with_paste(root)
email_entry.pack()

tk.Label(root, text="Token:").pack()
token_entry = make_entry_with_paste(root, show="*")
token_entry.pack()

tk.Label(root, text="URL репозиторію (github.com/user/repo.git):").pack()
repo_entry = make_entry_with_paste(root)
repo_entry.pack()

tk.Label(root, text="Шлях до папки:").pack()
folder_frame = tk.Frame(root)
folder_frame.pack()
folder_entry = make_entry_with_paste(folder_frame)
folder_entry.pack(side=tk.LEFT)
tk.Button(folder_frame, text="Обрати", command=select_folder).pack(side=tk.LEFT)

tk.Button(root, text="Залити", command=upload_files, bg="green", fg="white").pack(pady=15)

root.mainloop()
