from pathlib import Path
import os
import sys
import winreg

BASE=Path(__file__).resolve().parent
RUN=r'Software\Microsoft\Windows\CurrentVersion\Run'
NAME='JarvisLocal'

def command():
    pythonw=Path(sys.executable).with_name('pythonw.exe')
    if not pythonw.is_file(): raise RuntimeError('Windowed Python runtime unavailable.')
    return f'"{pythonw}" "{BASE / "desktop.py"}" --minimized'

def enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,RUN) as key:
            return winreg.QueryValueEx(key,NAME)[0]==command()
    except OSError: return False

def set_enabled(value):
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER,RUN) as key:
        if value: winreg.SetValueEx(key,NAME,0,winreg.REG_SZ,command())
        else:
            try: winreg.DeleteValue(key,NAME)
            except FileNotFoundError: pass
