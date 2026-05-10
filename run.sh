#!/usr/bin/env bash
# سكريبت التشغيل التلقائي لموقع نوادر
# يقوم بإنشاء بيئة افتراضية وتثبيت المتطلبات وتجهيز قاعدة البيانات وتشغيل الخادم.

set -e

cd "$(dirname "$0")"

PYTHON_BIN="${PYTHON:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN="python"
fi

VENV_DIR=".venv"
PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"

# 1) أنشئ بيئة افتراضية إن لم تكن موجودة
if [ ! -d "$VENV_DIR" ]; then
  echo "==> إنشاء بيئة افتراضية في $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# فعّل البيئة
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# 2) ثبّت المتطلبات
echo "==> تثبيت المتطلبات"
python -m pip install --upgrade pip >/dev/null
python -m pip install -r requirements.txt

# 3) رحّلات قاعدة البيانات
echo "==> ترحيل قاعدة البيانات"
python manage.py migrate --noinput

# 4) إنشاء حساب الإدارة
echo "==> تجهيز حساب الإدارة"
python manage.py seed_admin

# 5) ابحث عن منفذ متاح ابتداءً من $PORT
find_free_port() {
  local p="$1"
  while [ "$p" -lt 65535 ]; do
    if ! (echo > "/dev/tcp/127.0.0.1/$p") >/dev/null 2>&1; then
      echo "$p"
      return
    fi
    p=$((p + 1))
  done
}

FREE_PORT="$(find_free_port "$PORT" || true)"
if [ -z "$FREE_PORT" ]; then
  FREE_PORT="$PORT"
fi

echo ""
echo "============================================"
echo "  نوادر يعمل الآن على:"
echo "  الموقع       : http://127.0.0.1:$FREE_PORT/"
echo "  لوحة الإدارة : http://127.0.0.1:$FREE_PORT/admin/"
echo "  دخول الإدارة : 345789900Dd / 345789900Dd"
echo "============================================"
echo ""

exec python manage.py runserver "$HOST:$FREE_PORT"
