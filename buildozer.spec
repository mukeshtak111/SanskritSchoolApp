[app]

# 1. APP NAME & IDENTITY
title = Sanskrit School Nasirabad
package.name = sanskritschool
package.domain = org.sanskrit

# 2. SOURCE CODE SETTINGS
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf
version = 1.0

# 3. APP ICON
icon.filename = %(source.dir)s/icon.png

# 4. REQUIREMENTS (The Compatibility Matrix Fix)
# Locking Python to 3.11.5 and Kivy to 2.3.0 so ReportLab compiles perfectly
requirements = python3==3.11.5, hostpython3==3.11.5, kivy==2.3.0, requests, openssl, reportlab
# 5. BUILD BRANCH
p4a.branch = develop

# 6. SCREEN & PERMISSIONS
orientation = portrait
fullscreen = 0
android.permissions = INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE

# 7. ARCHITECTURE & NDK (The Vaccine)
# Locking NDK to 25b to avoid C-compilation crashes with OpenSSL/ReportLab
android.archs = arm64-v8a
android.allow_backup = True
android.ndk = 25b
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
