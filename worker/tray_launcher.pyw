"""Windows launcher: show startup errors rather than hiding them in pythonw."""
import sys
import tkinter as tk
from tkinter import messagebox
import tray_client

if __name__ == '__main__':
    try:
        if len(sys.argv) != 2:
            raise ValueError('Bitte eine private Tray-Konfiguration angeben.')
        tray_client.run_tray(sys.argv[1])
    except Exception as exc:
        root = tk.Tk(); root.withdraw()
        try: messagebox.showerror('Voynich Tray', str(exc), parent=root)
        finally: root.destroy()
        sys.exit(1)
