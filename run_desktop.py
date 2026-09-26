"""
=============================================================================
NHGCC Oshodi Church Database - Windows Desktop Application Launcher & Setup
=============================================================================
This module provides the desktop application runtime:
- Automatic 1-click self-installation to %LOCALAPPDATA%\\NHGCC_Church_Database
- Windows Desktop and Start Menu shortcut creation
- Automatic port allocation and single-instance detection
- Dedicated app window launcher
- Cloud Database connection (PostgreSQL) so all church devices stay synchronized
=============================================================================
"""
import os
import sys
import time
import socket
import urllib.request
import webbrowser
import threading
import shutil
import subprocess
from pathlib import Path

# Configure stdout and stderr for UTF-8 on Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app import create_app


def get_shell_folder(folder_name):
    """Retrieves standard Windows shell folder paths (Desktop, Start Menu Programs)."""
    if sys.platform == 'win32':
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders'
            )
            val, _ = winreg.QueryValueEx(key, folder_name)
            winreg.CloseKey(key)
            expanded = os.path.expandvars(val)
            if os.path.exists(expanded):
                return expanded
        except Exception:
            pass

        if folder_name == 'Desktop':
            candidates = [
                os.path.expandvars(r'%USERPROFILE%\OneDrive\Desktop'),
                os.path.expandvars(r'%USERPROFILE%\Desktop'),
                os.path.expandvars(r'%PUBLIC%\Desktop')
            ]
            for c in candidates:
                if os.path.exists(c):
                    return c

        if folder_name == 'Programs':
            p = os.path.expandvars(r'%APPDATA%\Microsoft\Windows\Start Menu\Programs')
            if os.path.exists(p):
                return p

    return os.path.expandvars(f'%USERPROFILE%\\{folder_name}')


def create_windows_shortcut(target_exe, working_dir, icon_path, shortcut_path, description):
    """Creates a native Windows .lnk shortcut using VBScript or PowerShell."""
    if sys.platform != 'win32':
        return

    import tempfile
    vbs = (
        'Set ws = CreateObject("WScript.Shell")\n'
        f'Set sc = ws.CreateShortcut("{shortcut_path}")\n'
        f'sc.TargetPath = "{target_exe}"\n'
        f'sc.WorkingDirectory = "{working_dir}"\n'
        f'sc.Description = "{description}"\n'
        f'sc.IconLocation = "{icon_path},0"\n'
        'sc.Save\n'
    )
    temp_vbs = os.path.join(tempfile.gettempdir(), f'nhgcc_sc_{int(time.time() * 1000)}.vbs')

    try:
        with open(temp_vbs, 'w', encoding='utf-8') as f:
            f.write(vbs)
        creationflags = 0x08000000 if os.name == 'nt' else 0
        subprocess.run(['cscript', '//nologo', temp_vbs], check=True, creationflags=creationflags, timeout=5)
    except Exception:
        # Fallback to PowerShell
        try:
            ps = (
                f"$ws = New-Object -ComObject WScript.Shell; "
                f"$s = $ws.CreateShortcut('{shortcut_path}'); "
                f"$s.TargetPath = '{target_exe}'; "
                f"$s.WorkingDirectory = '{working_dir}'; "
                f"$s.Description = '{description}'; "
                f"if (Test-Path '{icon_path}') {{ $s.IconLocation = '{icon_path},0' }}; "
                f"$s.Save()"
            )
            subprocess.run(
                ['powershell', '-NoProfile', '-NonInteractive', '-Command', ps],
                creationflags=0x08000000 if os.name == 'nt' else 0,
                timeout=5
            )
        except Exception:
            pass
    finally:
        try:
            if os.path.exists(temp_vbs):
                os.remove(temp_vbs)
        except Exception:
            pass


def is_port_in_use(port):
    """Checks if a TCP port is currently open and bound on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(('127.0.0.1', port)) == 0


def is_nhgcc_running(port):
    """Probes a port to see if it is already hosting an instance of NHGCC Church Database."""
    try:
        req = urllib.request.Request(
            f'http://127.0.0.1:{port}',
            headers={'User-Agent': 'NHGCC-Desktop-Probe'}
        )
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            content = resp.read().decode('utf-8', errors='ignore')
            return 'NHGCC' in content or 'National Holy Ghost' in content or 'Oshodi' in content
    except Exception:
        return False


def open_browser(port):
    """Waits for the internal Flask server to spin up, then opens the app in the browser."""
    url = f'http://127.0.0.1:{port}'
    for _ in range(40):
        time.sleep(0.3)
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'NHGCC-Desktop-Launcher'})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status in (200, 302):
                    break
        except Exception:
            pass

    print(f'\n[NHGCC Desktop] Opening Church Management System in your browser: {url}\n')
    try:
        webbrowser.open(url, new=2)
    except Exception:
        pass


def ensure_desktop_shortcuts(target_exe=None, target_dir=None):
    """Ensures Desktop and Start Menu shortcuts exist for 1-click access."""
    try:
        if getattr(sys, 'frozen', False):
            target_exe = target_exe or Path(sys.executable).resolve()
        else:
            target_exe = target_exe or Path(__file__).resolve()

        target_dir = target_dir or target_exe.parent
        ico_path = target_dir / 'logo.ico'
        if not ico_path.exists():
            ico_path = BASE_DIR / 'logo.ico'

        desktop = get_shell_folder('Desktop')
        if desktop and os.path.exists(desktop):
            lnk_path = os.path.join(desktop, 'NHGCC Oshodi Church Database.lnk')
            if not os.path.exists(lnk_path):
                create_windows_shortcut(
                    str(target_exe),
                    str(target_dir),
                    str(ico_path),
                    lnk_path,
                    'NHGCC Oshodi Church Management System'
                )
                print(f'[OK] Created Desktop Shortcut: {lnk_path}')

        programs = get_shell_folder('Programs')
        if programs and os.path.exists(programs):
            start_lnk = os.path.join(programs, 'NHGCC Oshodi Church Database.lnk')
            if not os.path.exists(start_lnk):
                create_windows_shortcut(
                    str(target_exe),
                    str(target_dir),
                    str(ico_path),
                    start_lnk,
                    'NHGCC Oshodi Church Management System'
                )
    except Exception as e:
        print(f'[Shortcut Warning] {e}')


def run_setup_gui(install_func):
    """Displays a modern church-branded visual installation window during setup."""
    try:
        import tkinter as tk
        from tkinter import ttk

        root = tk.Tk()
        root.title('NHGCC Oshodi - 1-Click Setup')
        root.geometry('480x250')
        root.configure(bg='#0B192C')
        root.resizable(False, False)

        root.update_idletasks()
        w, h = 480, 250
        x = (root.winfo_screenwidth() // 2) - (w // 2)
        y = (root.winfo_screenheight() // 2) - (h // 2)
        root.geometry(f'{w}x{h}+{x}+{y}')

        ico = BASE_DIR / 'logo.ico'
        if ico.exists():
            try:
                root.iconbitmap(str(ico))
            except Exception:
                pass

        lbl_org = tk.Label(
            root,
            text='NATIONAL HOLY GHOST CHURCH OF CHRIST',
            font=('Segoe UI', 10, 'bold'),
            fg='#D97706',
            bg='#0B192C'
        )
        lbl_org.pack(pady=(18, 2))

        lbl_parish = tk.Label(
            root,
            text='Oshodi Parish, Lagos  *  Church Management & Attendance',
            font=('Segoe UI', 9),
            fg='#CBD5E1',
            bg='#0B192C'
        )
        lbl_parish.pack(pady=(0, 14))

        lbl_status = tk.Label(
            root,
            text='Installing Church Management System on your PC...',
            font=('Segoe UI', 9.5),
            fg='#FFFFFF',
            bg='#0B192C'
        )
        lbl_status.pack(pady=(0, 12))

        pb = ttk.Progressbar(root, length=400, mode='determinate')
        pb.pack(pady=(0, 16))
        pb['maximum'] = 100
        pb['value'] = 10

        def update_progress(val, text):
            pb['value'] = val
            lbl_status.config(text=text)
            root.update_idletasks()

        def do_install():
            try:
                install_func(update_progress)
                time.sleep(0.6)
                root.destroy()
            except Exception as err:
                lbl_status.config(text=f'Setup complete: {err}')
                root.after(2000, root.destroy)

        root.after(100, do_install)
        root.mainloop()
    except Exception as e:
        print(f'[NHGCC Setup Console] {e}')
        install_func(lambda val, txt: print(f'[{val}%] {txt}'))


def perform_self_installation(update_cb=None):
    """
    Installs the application permanently to %LOCALAPPDATA%\\NHGCC_Church_Database,
    configures shortcuts, and launches the app.
    """
    def cb(pct, msg):
        if update_cb:
            update_cb(pct, msg)
        print(f'[{pct}%] {msg}')

    cb(10, 'Setting up church application directory...')
    install_dir = Path(os.environ.get('LOCALAPPDATA', '')) / 'NHGCC_Church_Database'
    install_dir.mkdir(parents=True, exist_ok=True)
    target_exe = install_dir / 'NHGCC_Church_Database.exe'

    cb(30, 'Copying application executable...')
    if getattr(sys, 'frozen', False):
        current_exe = Path(sys.executable).resolve()
    else:
        candidates = [
            Path(__file__).parent / 'dist' / 'NHGCC_Oshodi_Church_Setup.exe',
            Path(__file__).parent / 'NHGCC_Oshodi_Church_Setup.exe',
            Path(__file__).parent / 'NHGCC_Church_Database.exe'
        ]
        current_exe = None
        for c in candidates:
            if c.exists() and c.stat().st_size > 1000000:
                current_exe = c.resolve()
                break

    if current_exe and current_exe.resolve() != target_exe.resolve():
        shutil.copy2(current_exe, target_exe)

    cb(50, 'Configuring church database and assets...')
    src_dir = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent

    for asset_name in ['logo.ico', 'nhgcc_church.db', 'NHGCC_Oshodi_Church_App_Setup_and_User_Manual.pdf', 'NHGCC database .pdf']:
        src_file = src_dir / asset_name
        if not src_file.exists() and current_exe:
            src_file = current_exe.parent / asset_name

        target_file = install_dir / asset_name
        if src_file.exists() and not target_file.exists():
            try:
                shutil.copy2(src_file, target_file)
            except Exception:
                pass

    cb(75, 'Creating official Windows Desktop and Start Menu shortcuts...')
    desktop_dir = get_shell_folder('Desktop')
    programs_dir = get_shell_folder('Programs')

    target_ico = install_dir / 'logo.ico'
    ico_ref = str(target_ico) if target_ico.exists() else str(target_exe)

    if desktop_dir and os.path.exists(desktop_dir):
        desktop_lnk = os.path.join(desktop_dir, 'NHGCC Oshodi Church Database.lnk')
        create_windows_shortcut(
            str(target_exe),
            str(install_dir),
            ico_ref,
            desktop_lnk,
            'NHGCC Oshodi Church Management System'
        )

    if programs_dir and os.path.exists(programs_dir):
        start_lnk = os.path.join(programs_dir, 'NHGCC Oshodi Church Database.lnk')
        create_windows_shortcut(
            str(target_exe),
            str(install_dir),
            ico_ref,
            start_lnk,
            'NHGCC Oshodi Church Management System'
        )

    # Generate uninstaller script
    uninstaller_content = (
        '@echo off\n'
        'title Uninstall NHGCC Oshodi Church Management System\n'
        'echo Removing Desktop and Start Menu Shortcuts...\n'
        f'del /f /q "{os.path.join(desktop_dir or "", "NHGCC Oshodi Church Database.lnk")}" 2>nul\n'
        f'del /f /q "{os.path.join(programs_dir or "", "NHGCC Oshodi Church Database.lnk")}" 2>nul\n'
        'echo Uninstall complete. Your church database backup remains in %LOCALAPPDATA%\\NHGCC_Church_Database.\n'
        'pause\n'
    )
    try:
        with open(install_dir / 'Uninstall_NHGCC_App.bat', 'w', encoding='utf-8') as f:
            f.write(uninstaller_content)
    except Exception:
        pass

    cb(95, 'Setup complete! Starting Church Management System...')
    time.sleep(0.3)

    DETACHED_PROCESS = 0x00000008
    subprocess.Popen([str(target_exe)], cwd=str(install_dir), creationflags=DETACHED_PROCESS, close_fds=True)
    cb(100, 'Opening in your browser: http://127.0.0.1:5000')


def main():
    is_frozen = getattr(sys, 'frozen', False)
    is_portable = '--portable' in sys.argv

    # Check if self-installation is needed (running setup outside %LOCALAPPDATA%)
    if is_frozen and not is_portable:
        current_exe = Path(sys.executable).resolve()
        install_dir = Path(os.environ.get('LOCALAPPDATA', '')) / 'NHGCC_Church_Database'
        target_exe = install_dir / 'NHGCC_Church_Database.exe'

        if current_exe.resolve() != target_exe.resolve():
            print('=' * 72)
            print('   [+]  NATIONAL HOLY GHOST CHURCH OF CHRIST (NHGCC) OSHODI  [+]')
            print('        CHURCH MANAGEMENT & SUNDAY ATTENDANCE DESKTOP APP SETUP  ')
            print('=' * 72)
            run_setup_gui(perform_self_installation)
            return

    print('=' * 72)
    print('   [+]  NATIONAL HOLY GHOST CHURCH OF CHRIST (NHGCC) OSHODI  [+]')
    print('        CHURCH MANAGEMENT & SUNDAY ATTENDANCE DESKTOP APP        ')
    print('=' * 72)

    ensure_desktop_shortcuts()

    preferred_port = int(os.environ.get('PORT', 5000))

    if is_port_in_use(preferred_port) and is_nhgcc_running(preferred_port):
        url = f'http://127.0.0.1:{preferred_port}'
        print(f'\n[NHGCC Desktop] Application is already running on {url}!')
        print('[NHGCC Desktop] Bringing up Church Management System in your browser...\n')
        webbrowser.open(url, new=2)
        print('Done! You can close this window.')
        time.sleep(2)
        return

    active_port = preferred_port
    if is_port_in_use(active_port):
        print(f'[!] Port {preferred_port} is busy with another application. Finding an open port...')
        for p in range(5001, 5050):
            if not is_port_in_use(p):
                active_port = p
                break

    print('[1/3] Initializing church database and configuration...')
    app = create_app()

    print(f'[2/3] Starting church server on http://127.0.0.1:{active_port}...')
    threading.Thread(target=open_browser, args=(active_port,), daemon=True).start()

    print('[3/3] Application active! Leave this window open while using the app.')
    print(f'      Official URL: http://127.0.0.1:{active_port}')
    print('      To stop the application, press Ctrl+C or close this window.')
    print('-' * 72)

    try:
        app.run(host='127.0.0.1', port=active_port, debug=False)
    except KeyboardInterrupt:
        print('\n[NHGCC Desktop] Application shut down gracefully. God bless you!\n')


if __name__ == '__main__':
    main()
