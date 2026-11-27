#!/usr/bin/env bash
# Compila CD Factu y genera un AppImage standalone (Linux x86_64)
set -e
cd "$(dirname "$0")"

# 1. Compilar con PyInstaller
pyinstaller --onefile --windowed --name "CD-Factu" \
  --add-data "assets:assets" --add-data "app/db/schema.sql:app/db" main.py

# 2. Preparar AppDir
rm -rf AppDir
mkdir -p AppDir/usr/bin AppDir/usr/share/applications AppDir/usr/share/icons/hicolor/256x256/apps
cp dist/CD-Factu AppDir/usr/bin/CD-Factu
chmod +x AppDir/usr/bin/CD-Factu
cp assets/factufacil_logo.png AppDir/usr/share/icons/hicolor/256x256/apps/cd-factu.png
cp assets/factufacil_logo.png AppDir/cd-factu.png

cat > AppDir/cd-factu.desktop <<'DESKTOP'
[Desktop Entry]
Name=CD Factu
Comment=Programa de facturación para autónomos y micropymes
Exec=CD-Factu
Icon=cd-factu
Type=Application
Categories=Office;Finance;
Terminal=false
DESKTOP
cp AppDir/cd-factu.desktop AppDir/usr/share/applications/

cat > AppDir/AppRun <<'APPRUN'
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
export PATH="${HERE}/usr/bin:${PATH}"
exec "${HERE}/usr/bin/CD-Factu" "$@"
APPRUN
chmod +x AppDir/AppRun

# 3. Generar AppImage
ARCH=x86_64 appimagetool AppDir CD-Factu-x86_64.AppImage
echo "AppImage generado: CD-Factu-x86_64.AppImage"
