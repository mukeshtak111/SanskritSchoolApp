[app]
title = Sanskrit School Nasirabad
package.name = sanskritschool
package.domain = org.sanskrit
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf
version = 1.0
icon.filename = %(source.dir)s/icon.png
requirements = python3, kivy==2.3.0, requests, openssl, reportlab
p4a.branch = develop
orientation = portrait
fullscreen = 0
android.permissions = INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE
android.archs = arm64-v8a
android.allow_backup = True
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
