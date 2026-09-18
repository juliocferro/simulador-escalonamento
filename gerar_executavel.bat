@echo off
rem Gera o Simulador.exe nesta maquina (Windows) com o PyInstaller.
rem Requisitos: Python 3.10 ou superior no PATH. O PyInstaller e instalado se faltar.
rem O executavel resultante e copiado para a raiz do repositorio.

cd /d "%~dp0"
python -m pip show pyinstaller >nul 2>&1 || python -m pip install pyinstaller
python -m PyInstaller --onefile --windowed --name Simulador --clean --noconfirm main.py
if errorlevel 1 (
    echo.
    echo Falha ao gerar o executavel.
    pause
    exit /b 1
)
copy /y dist\Simulador.exe Simulador.exe >nul
rmdir /s /q build dist
del /q Simulador.spec
echo.
echo Simulador.exe gerado na raiz do repositorio.
pause
