@echo off
REM Compila CD Factu para Windows (ejecutar en Windows)
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --onefile --windowed --name "CD-Factu" ^
  --add-data "assets;assets" --add-data "app/db/schema.sql;app/db" main.py
echo Ejecutable generado en dist\CD-Factu.exe
pause
