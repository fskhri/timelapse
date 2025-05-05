import os
import subprocess

print("Menginstal PyInstaller...")
subprocess.call(["pip", "install", "pyinstaller"])

print("Membuat executable...")
subprocess.call([
    "pyinstaller",
    "--name=Timelapse",
    "--windowed",  # Tanpa command prompt/console
    "--icon=NONE",  # Bisa diganti dengan path ikon jika ada
    "--onefile",  # Hanya 1 file exe
    "--clean",
    "timelapse.py"
])

print("Selesai! File exe berada di folder 'dist'.") 