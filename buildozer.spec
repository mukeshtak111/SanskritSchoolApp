[app]

# 1. APP NAME & IDENTITY
title = Sanskrit School Nasirabad
package.name = sanskritschool
package.domain = org.sanskrit

# 2. SOURCE CODE SETTINGS
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf
version = 1.0
# icon.filename = %(source.dir)s/icon.png

# 3. REQUIREMENTS (The ChatGPT Master Fix)
requirements = python3==3.11.5, hostpython3==3.11.5, kivy==2.3.0, requests, openssl, reportlab
# 4. BUILD BRANCH & RELEASE (Locking to stable past)
p4a.branch = master
p4a.local_recipes = recipes
# 5. SCREEN & PERMISSIONS
orientation = portrait
fullscreen = 0
android.permissions = INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE

# 6. ARCHITECTURE & NDK 
android.archs = arm64-v8a
android.allow_backup = True
android.ndk = 25b
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
