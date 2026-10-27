[app]
title           = BLEMAC Shell PG
package.name    = blemacpg
package.domain  = org.blemac
version         = 0.1.0
source.dir      = .
source.include_exts = py,png,jpg,jpeg,json,ttf,ogg,wav,mp3
source.include_patterns = games/*
main.py         = main.py
p4a.branch = v2024.01.21
p4a.bootstrap = sdl2
requirements = python3==3.10.12,hostpython3==3.10.12,pygame
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE
android.api         = 33
android.minapi      = 24
android.ndk         = 25b
android.accept_sdk_license = True
orientation         = portrait
fullscreen          = 1

[buildozer]
log_level   = 2
warn_on_root = 1
