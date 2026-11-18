@echo off
setlocal

set "BAT_DIR=%~dp0"
set "PROJECT_DIR=%BAT_DIR%.."

set "VENV_DIR=%PROJECT_DIR%\venv"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
set "PIP_EXE=%VENV_DIR%\Scripts\pip.exe"
set "APP_FILE=%PROJECT_DIR%\main.py"
set "REQUIREMENTS_FILE=%PROJECT_DIR%\requirements.txt"

cd /d "%PROJECT_DIR%"

echo ========================================
echo Iniciando projeto
echo Pasta do projeto: "%PROJECT_DIR%"
echo ========================================

if not exist "%VENV_DIR%" (
    echo .venv nao encontrado. Criando ambiente virtual...

    py -3 -m venv "%VENV_DIR%"

    if errorlevel 1 (
        echo Falha ao criar .venv usando py -3.
        echo Tentando criar usando python...

        python -m venv "%VENV_DIR%"

        if errorlevel 1 (
            echo Erro ao criar ambiente virtual.
            exit /b 1
        )
    )
)

if not exist "%PYTHON_EXE%" (
    echo Python da .venv nao encontrado:
    echo "%PYTHON_EXE%"
    exit /b 1
)

echo Atualizando pip...
"%PYTHON_EXE%" -m pip install --upgrade pip

if exist "%REQUIREMENTS_FILE%" (
    echo Instalando dependencias do requirements.txt...
    "%PIP_EXE%" install -r "%REQUIREMENTS_FILE%"

    if errorlevel 1 (
        echo Erro ao instalar dependencias.
        exit /b 1
    )
) else (
    echo requirements.txt nao encontrado. Pulando instalacao de dependencias.
)

if not exist "%APP_FILE%" (
    echo Arquivo main.py nao encontrado:
    echo "%APP_FILE%"
    exit /b 1
)

echo Executando aplicacao...
"%PYTHON_EXE%" "%APP_FILE%"
pause
endlocal