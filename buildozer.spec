[app]

# ==========================================
# ۱. تنظیمات هویت برنامه
# ==========================================
title = Nova AI
package.name = novaai
package.domain = org.novaai
version = 1.0.0

# ==========================================
# ۲. تنظیمات سورس و منابع
# ==========================================
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,ttf,otf
source.exclude_exts = spec,md,txt,gitignore

# ==========================================
# ۳. وابستگی‌ها (بسیار مهم برای AI)
# ==========================================
# requests و duckduckgo-search برای AIBrain ضروری هستند
# certifi برای جلوگیری از خطای SSL در اندروید
requirements = python3,kivy,requests,duckduckgo-search,certifi

# ==========================================
# ۴. تنظیمات نمایش و UI
# ==========================================
orientation = portrait
fullscreen = 0
icon.filename = icon.png
presplash.filename = presplash.png
presplash.color = #1a1a2e

# ==========================================
# ۵. مجوزهای اندروید
# ==========================================
android.permissions = INTERNET, ACCESS_NETWORK_STATE, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE

# ==========================================
# ۶. تنظیمات کامپایل و API
# ==========================================
android.api = 34
android.minapi = 24
android.ndk_api = 24
android.enable_androidx = True
android.accept_sdk_license = True

# ==========================================
# ۷. معماری و بهینه‌سازی
# ==========================================
# فقط arm64-v8a برای کاهش حجم APK (99% گوشی‌های جدید)
android.archs = arm64-v8a
android.allow_backup = False
android.add_src =

# ==========================================
# ۸. نقطه ورود
# ==========================================
android.entrypoint = main.py

# ==========================================
# ۹. تنظیمات پیشرفته بیلد
# ==========================================
log_level = 2
warn_on_root = 1
p4a.bootstrap = sdl2
p4a.local_recipes = ./recipes
