@echo off
REM سكريبت التشغيل التلقائي لموقع نوادر على ويندوز
setlocal

cd /d "%~dp0"

set "VENV_DIR=.venv"
if "%PORT%"=="" set "PORT=8000"
if "%HOST%"=="" set "HOST=0.0.0.0"

REM 1) إنشاء بيئة افتراضية
if not exist "%VENV_DIR%\Scripts\python.exe" (
  echo ==^> انشاء بيئة افتراضية في %VENV_DIR%
  python -m venv "%VENV_DIR%"
)

call "%VENV_DIR%\Scripts\activate.bat"

echo ==^> تثبيت المتطلبات
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt

echo ==^> ترحيل قاعدة البيانات
python manage.py migrate --noinput

echo ==^> تجهيز حساب الادارة
python manage.py seed_admin

echo.
echo ============================================
echo   نوادر يعمل الان على:
echo   الموقع       : http://127.0.0.1:%PORT%/
echo   لوحة الادارة : http://127.0.0.1:%PORT%/admin/
echo   دخول الادارة : 345789900Dd / 345789900Dd
echo ============================================
echo.

python manage.py runserver "%HOST%:%PORT%"
