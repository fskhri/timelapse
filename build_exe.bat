@echo off
echo Membuat file executable...

python -m PyInstaller --name=Timelapse --windowed --onefile --clean timelapse.py

echo.
echo Jika berhasil, file Timelapse.exe akan berada di folder "dist"
echo.
pause 