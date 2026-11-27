# app/updater.py
import os, sys, threading, urllib.request, stat, subprocess, tempfile, time

def _ejecutable_actual():
    # AppImage
    if os.environ.get("APPIMAGE"):
        return os.environ["APPIMAGE"]
    if getattr(sys, "frozen", False):
        return sys.executable
    return os.path.abspath(sys.argv[0])

def _es_frozen():
    return getattr(sys, "frozen", False) or bool(os.environ.get("APPIMAGE"))

def _asset_para_plataforma(release_json):
    assets = release_json.get("assets", []) or []
    if sys.platform == "win32":
        for a in assets:
            if a.get("name", "").lower().endswith(".exe"):
                return a
    else:
        for a in assets:
            name = a.get("name", "").lower()
            if name.endswith(".appimage"):
                return a
    return None

def descargar_y_actualizar(parent, release_json):
    """Descarga la nueva versión y la aplica, preservando los datos del usuario."""
    if not _es_frozen():
        # Modo desarrollo: solo abrir la página
        import webbrowser
        webbrowser.open(release_json.get("html_url", ""))
        return

    asset = _asset_para_plataforma(release_json)
    if not asset:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.warning(parent, "Actualización", "No se encontró el archivo de actualización para tu sistema.")
        return

    url = asset["browser_download_url"]
    nombre = asset["name"]
    exe_actual = _ejecutable_actual()
    carpeta = os.path.dirname(exe_actual) or os.getcwd()

    from PySide6.QtWidgets import QProgressDialog, QMessageBox
    from PySide6.QtCore import Qt

    dlg = QProgressDialog(f"Descargando {nombre}...", "Cancelar", 0, 100, parent)
    dlg.setWindowTitle("Actualizando")
    dlg.setWindowModality(Qt.WindowModality.WindowModal)
    dlg.setMinimumDuration(0)
    dlg.setValue(0)

    tmp_path = os.path.join(carpeta, nombre + ".new")
    cancelado = {"v": False}

    def progreso(bloque, tam_bloque, tam_total):
        if cancelado["v"]:
            return
        if tam_total > 0:
            porc = int(bloque * tam_bloque * 100 / tam_total)
            dlg.setValue(min(100, porc))

    def tarea():
        try:
            urllib.request.urlretrieve(url, tmp_path, progreso)
            if cancelado["v"]:
                try: os.remove(tmp_path)
                except Exception: pass
                return
            dlg.setValue(100)
            _aplicar_actualizacion(parent, exe_actual, tmp_path, nombre)
        except Exception as e:
            try: os.remove(tmp_path)
            except Exception: pass
            from PySide6.QtCore import QMetaObject, Qt as _Qt
            QMetaObject.invokeMethod(parent, "_error_actualizacion",
                                    _Qt.ConnectionType.QueuedConnection,
                                    __import__("PySide6.QtCore", fromlist=["Q_ARG"]).Q_ARG(str, str(e)))

    dlg.canceled.connect(lambda: cancelado.__setitem__("v", True))
    threading.Thread(target=tarea, daemon=True).start()
    dlg.exec()

def _aplicar_actualizacion(parent, exe_actual, nuevo_path, nombre):
    os.chmod(nuevo_path, os.stat(nuevo_path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    if sys.platform == "win32":
        # Crear bat que espera, reemplaza y lanza
        bat = os.path.join(os.path.dirname(exe_actual), "update_cd_factu.bat")
        with open(bat, "w") as f:
            f.write(f'@echo off\n')
            f.write(f'timeout /t 2 /nobreak >nul\n')
            f.write(f'del /f /q "{exe_actual}"\n')
            f.write(f'move /y "{nuevo_path}" "{exe_actual}"\n')
            f.write(f'start "" "{exe_actual}"\n')
            f.write(f'del /f /q "%~f0"\n')
        subprocess.Popen(["cmd", "/c", bat], creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(parent, "Actualización", "La actualización se aplicará al cerrar el programa. Se reiniciará automáticamente.")
        # Salir para que el bat pueda reemplazar
        from PySide6.QtWidgets import QApplication
        QApplication.quit()
    else:
        # Linux: reemplazar en caliente (rename)
        backup = exe_actual + ".old"
        try:
            if os.path.exists(backup):
                os.remove(backup)
            os.replace(exe_actual, backup)
            os.replace(nuevo_path, exe_actual)
        except Exception as e:
            # fallback: dejar el .new y avisar
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(parent, "Actualización", f"No se pudo reemplazar automáticamente: {e}\\nEl nuevo archivo está en:\\n{nuevo_path}")
            return
        # Lanzar nueva versión y salir
        try:
            subprocess.Popen([exe_actual], start_new_session=True)
        except Exception:
            pass
        from PySide6.QtWidgets import QApplication
        QApplication.quit()
