import tkinter as tk
from gui import MindGuardianGUI

if __name__ == "__main__":
    try:
        app = MindGuardianGUI()
        app.mainloop()
    except tk.TclError as e:
        print(f"Failed to start GUI. This is expected in a non-GUI environment. Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during GUI execution: {e}")      