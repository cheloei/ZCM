import os
import sys
import shutil
import winreg
import ctypes
from ctypes import wintypes

APP_NAME = "ZCombine Manager"
APP_REG_KEY = "ZCombineManager"
PUBLISHER = "Abolfazl Cheloyi"
APP_VERSION = "1.0.0"

# Constants for SHChangeNotify
SHCNE_ASSOCCHANGED = 0x08000000
SHCNF_IDLIST = 0x0000

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def add_to_user_path(install_dir):
    """Add the installation directory to the User PATH environment variable."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_ALL_ACCESS)
        current_path, _ = winreg.QueryValueEx(key, "Path")
        
        if install_dir.lower() not in current_path.lower():
            new_path = f"{current_path};{install_dir}"
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
            print("[+] Added to User PATH.")
        else:
            print("[*] Already exists in User PATH.")
            
        winreg.CloseKey(key)
    except Exception as e:
        print(f"[-] Failed to update PATH: {e}")

def add_context_menu(exe_path):
    """Add 'Setup ZCombine Here' to the folder context menu."""
    try:
        reg_path = r"Software\Classes\Directory\Background\shell\ZCombine"
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_path)
        winreg.SetValue(key, "", winreg.REG_SZ, "Setup ZCombine Here")
        # Set the icon to the new exe
        winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, exe_path)
        
        cmd_key = winreg.CreateKey(key, "command")
        winreg.SetValue(cmd_key, "", winreg.REG_SZ, f'"{exe_path}" setup')
        
        winreg.CloseKey(cmd_key)
        winreg.CloseKey(key)
        print("[+] Context menu added successfully.")
    except Exception as e:
        print(f"[-] Failed to add context menu: {e}")

def register_uninstaller(install_dir, uninstaller_path):
    """Register the app in Windows Add/Remove Programs (Installed Apps)."""
    try:
        reg_path = f"Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{APP_REG_KEY}"
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_path)
        
        main_exe = os.path.join(install_dir, "zcm.exe")
        
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, APP_NAME)
        winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, APP_VERSION)
        winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, PUBLISHER)
        winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, main_exe)
        winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{uninstaller_path}"')
        winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, install_dir)
        winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
        
        winreg.CloseKey(key)
        print("[+] Registered in Windows Installed Apps.")
    except Exception as e:
        print(f"[-] Failed to register uninstaller in Registry: {e}")

def broadcast_environment_change():
    """Notify Windows Explorer to reload environment variables."""
    HWND_BROADCAST = 0xFFFF
    WM_SETTINGCHANGE = 0x001A
    SMTO_ABORTIFHUNG = 0x0002
    result = ctypes.c_long()
    ctypes.windll.user32.SendMessageTimeoutW(
        HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment",
        SMTO_ABORTIFHUNG, 5000, ctypes.byref(result)
    )

def refresh_icon_cache():
    """Notify Windows that file associations/icons have changed to refresh the cache."""
    try:
        # Use SHChangeNotify to refresh icon cache
        ctypes.windll.shell32.SHChangeNotify(
            SHCNE_ASSOCCHANGED,
            SHCNF_IDLIST,
            None,
            None
        )
        print("[+] Icon cache refreshed.")
    except Exception as e:
        print(f"[-] Could not refresh icon cache: {e}")

def main():
    print("========================================")
    print("       ZCombine Installer               ")
    print("========================================\n")
    
    # 1. Define target installation directory
    local_app_data = os.environ.get("LOCALAPPDATA")
    install_dir = os.path.join(local_app_data, "ZCombineManager")
    exe_dest = os.path.join(install_dir, "zcm.exe")
    bat_dest = os.path.join(install_dir, "zcm-template.bat")
    uninstall_dest = os.path.join(install_dir, "uninstall.bat")
    
    # 2. Create directory
    if not os.path.exists(install_dir):
        os.makedirs(install_dir)
        print(f"[+] Created directory: {install_dir}")
        
    # 3. Locate bundled files
    bundled_exe = get_resource_path("zcm.exe")
    bundled_bat = get_resource_path("zcm-template.bat")
    bundled_uninstall = get_resource_path("uninstall.bat")
    
    # 4. Copy files
    try:
        if os.path.exists(bundled_exe):
            shutil.copy2(bundled_exe, exe_dest)
            print("[+] Copied zcm.exe")
            
        if os.path.exists(bundled_bat):
            shutil.copy2(bundled_bat, bat_dest)
            print("[+] Copied zcm-template.bat")
            
        if os.path.exists(bundled_uninstall):
            shutil.copy2(bundled_uninstall, uninstall_dest)
            print("[+] Copied uninstall.bat")
    except Exception as e:
        print(f"[-] Error copying files: {e}")
        
    # 5. Add to PATH, Context Menu, and Windows Installed Apps Registry
    add_to_user_path(install_dir)
    add_context_menu(exe_dest)
    register_uninstaller(install_dir, uninstall_dest)
    
    # 6. Broadcast environment changes
    broadcast_environment_change()
    
    # 7. Refresh icon cache to show the new icon
    refresh_icon_cache()
    
    print("\n========================================")
    print(" Installation completed successfully!")
    print("========================================")
    input("Press Enter to exit...")

if __name__ == "__main__":
    main()