@echo off

:: Este script lanza PowerShell en el directorio actual y ejecuta el script de configuracion.

:: Obtiene la ruta del directorio actual donde se encuentra este .bat
set "CURRENT_DIR=%~dp0"

:: Lanza PowerShell y ejecuta el script de configuración.
powershell.exe -ExecutionPolicy Bypass -NoExit -Command "& '%CURRENT_DIR%iniciar_gemini.ps1'"

:: Fin del script batch. La ventana de PowerShell permanecerá abierta.