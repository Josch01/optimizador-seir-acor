# Script para configurar la autenticación de Gemini CLI

# Establece la política de ejecución (necesario si la has reseteado)
Set-ExecutionPolicy RemoteSigned -Scope Process -Force

# 1. Establece la variable de autenticación para Gemini Code Assist (GCA)
$env:GOOGLE_GENAI_USE_GCA="true"

# 2. Inicia sesión en Gemini (esto abrirá el navegador)
gemini login

# Mensaje de bienvenida una vez que la autenticación haya terminado
Write-Host "---" -ForegroundColor Green
Write-Host "🚀 Gemini CLI está lista para trabajar." -ForegroundColor Cyan
Write-Host "---" -ForegroundColor Green
Write-Host "Ahora puedes usar comandos como: gemini 'dime el comando git para rebase'" -ForegroundColor Yellow

# Mantén la ventana de PowerShell abierta
# El prompt esperará a que el usuario presione una tecla antes de cerrarse si lo ejecutas con el .bat