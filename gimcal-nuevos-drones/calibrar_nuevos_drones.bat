@echo off
setlocal
cd /d "%~dp0nuevos_drones"
title Gimbal Calibration Tool V3.6 - nuevos modelos
color 0B

set "PY=%~dp0python.exe"
if not exist "%PY%" set "PY=py"

set "MODEL=%~1"
if not "%MODEL%"=="" goto aviso

echo.
echo  ==== GIMBAL CALIBRATION TOOL V3.6 - NUEVOS MODELOS ====
echo.
echo   1. DJI Mini 3
echo   2. DJI Mini 3 Pro
echo   3. DJI Mini 4 Pro
echo   4. DJI Avata
echo   5. DJI FPV
echo.
set /P op=Elige el dron (1-5): 
if "%op%"=="1" set "MODEL=MINI3"
if "%op%"=="2" set "MODEL=MINI3PRO"
if "%op%"=="3" set "MODEL=MINI4PRO"
if "%op%"=="4" set "MODEL=AVATA"
if "%op%"=="5" set "MODEL=DJIFPV"
if "%MODEL%"=="" (
  echo Opcion no valida.
  pause
  exit /b 1
)

:aviso
color 0E
echo.
echo  *************************** AVISO ***************************
echo   La calibracion de %MODEL% es EXPERIMENTAL.
echo   Usa la orden de calibracion del Spark / Mavic Mini, que DJI
echo   no ha documentado para este dron. El gimbal responde (probado
echo   en Mini 3), pero la herramienta NO puede confirmar que la
echo   calibracion haya terminado bien.
echo   La calibracion oficial de este dron esta en la app DJI Fly.
echo  *************************************************************
echo.
echo   Dron encendido, en una superficie plana, sin helices y sin
echo   protector del gimbal. Conectado al PC por USB.
echo.
set /P ok=Escribe SI para continuar: 
if /I not "%ok%"=="SI" (
  echo Cancelado.
  pause
  exit /b 0
)
color 0B

echo.
echo  Usa el Administrador de dispositivos para ver el puerto COM
echo  (DJI USB VCOM For Protocol).
set /P id=Numero de puerto COM (solo el numero): 

set "LOG=%~dp0calibracion_%MODEL%.log"
echo ===== %DATE% %TIME% %MODEL% COM%id% >> "%LOG%"

echo.
echo  Paso 1: JointCoarse
"%PY%" "%~dp0nuevos_drones\comm_og_service_tool.py" --port COM%id% -vv %MODEL% GimbalCalib JointCoarse 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -FilePath '%LOG%' -Append"
echo.
pause

echo.
set /P lh=Hacer tambien el paso 2 (LinearHall)? (S/N): 
if /I "%lh%"=="S" (
  "%PY%" "%~dp0nuevos_drones\comm_og_service_tool.py" --port COM%id% -vv %MODEL% GimbalCalib LinearHall 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -FilePath '%LOG%' -Append"
)

echo.
echo  Terminado. Reinicia el dron y comprueba el horizonte en DJI Fly
echo  antes de volar. Registro guardado en:
echo  %LOG%
pause
