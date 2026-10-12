# Provisioning for the Windows VM. Runs elevated via Vagrant's winrm shell.
$ErrorActionPreference = "Stop"

Write-Host "== installing uv =="
$uvInstaller = "$env:TEMP\uv-install.ps1"
Invoke-WebRequest https://astral.sh/uv/install.ps1 -OutFile $uvInstaller
powershell -ExecutionPolicy Bypass -File $uvInstaller
$env:PATH = "$env:USERPROFILE\.local\bin;$env:PATH"
[Environment]::SetEnvironmentVariable("PATH", "$env:USERPROFILE\.local\bin;$([Environment]::GetEnvironmentVariable('PATH','User'))", "User")

Write-Host "== installing ollama =="
$ollama = "$env:TEMP\OllamaSetup.exe"
Invoke-WebRequest https://ollama.com/download/OllamaSetup.exe -OutFile $ollama
Start-Process -FilePath $ollama -ArgumentList "/S" -Wait
Start-Process -FilePath "$env:LOCALAPPDATA\Programs\Ollama\ollama app.exe"
Start-Sleep -Seconds 8
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" pull qwen3:0.6b

Write-Host "== sync + smoke =="
Set-Location C:\vagrant
& uv sync --dev
& uv run mcy doctor

Write-Host "== provisioning complete =="
