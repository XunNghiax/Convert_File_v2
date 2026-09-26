@echo off
@chcp 65001 >nul
@title Hệ Thống Quét Tên Nhân Vật & Biên Tập Gemini AI - Convert_File_v2

cd /d "%~dp0"

echo =====================================================================
echo    KHỞI ĐỘNG HỆ THỐNG QUÉT TÊN NHÂN VẬT & BIÊN TẬP GEMINI
echo =====================================================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [LOI] Khong tim thay Python trong he thong!
    echo Vui long cai dat Python va them vao PATH.
    pause
    exit /b 1
)

python run_cli.py

if %errorlevel% neq 0 (
    echo.
    echo [THONG BAO] Chuong trinh da ket thuc voi ma loi: %errorlevel%
    pause
)
