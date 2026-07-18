[app]

# === شناسنامه برنامه ===
title = Nova AI
package.name = novaai
package.domain = org.novaai
version = 1.0.0

# === سورس و منابع ===
source.dir = .
# شامل کردن فونت‌ها و فایل‌های پیکربندی برای پشتیبانی RTL و i18n
source.include_exts = py,png,jpg,kv,atlas,ttf,otf,json,yaml

# === وابستگی‌های دقیق (برای بیلدهای تکرارپذیر در CI) ===
# نسخه‌های پین شده از شکستن بیلد در آینده جلوگیری می‌کنند
requirements = python3==3.11.7,kivy[base]==2.3.0,requests==2.31.0,certifi==2024.2.2,android

# === تنظیمات نمایش ===
orientation = portrait
fullscreen = 0
icon.filename = icon.png

# === مجوزهای اندروید ===
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,ACCESS_NETWORK_STATE,FOREGROUND_SERVICE

# === تنظیمات SDK/NDK ===
android.api = 34
android.minapi = 21
android.ndk_api = 24
android.enable_androidx = True

# === معماری (فقط arm64 برای کاهش حجم و سازگاری مدرن) ===
android.arch = arm64-v8a

# === نقطه ورود ===
android.entrypoint = main.py

# === امنیت: متغیرهای محیطی برای کلید امضا ===
# هرگز رمز عبور را مستقیماً اینجا ننویسید
keystore.release_path = ${KEYSTORE_PATH}
keystore.release_user = ${KEYSTORE_USER}
keystore.release_password = ${KEYSTORE_PASSWORD}
keystore.release_alias = ${KEYSTORE_ALIAS}

# === بهینه‌سازی‌های Buildozer/P4A برای CI ===
p4a.bootstrap = sdl2
p4a.local_recipes = ./recipes/
log_level = 2
p4a.no_compile_pyo = True

# === جلوگیری از خواب رفتن صفحه هنگام پردازش سنگین ===
android.wakelock = True

# === کامپایل و بسته‌بندی ===
# فشرده‌سازی ETC2/ASTC برای تکسچرها (کاهش حجم APK)
android.add_aars = 
android.gradle_dependencies = 
# غیرفعال کردن فرمت‌های قدیمی تکسچر
texture_format/etc2_astc = true
texture_format/s3tc = false
