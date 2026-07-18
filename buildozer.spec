[app]

title = Nova AI
package.name = novaai
package.domain = org.novaai

source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version = 1.0.0

requirements = python3,kivy,requests

orientation = portrait
fullscreen = 0

icon.filename = icon.png

android.permissions = INTERNET, WRITE_EXTERNAL_STORAGE, ACCESS_NETWORK_STATE

android.api = 31
android.minapi = 21

android.gradle_dependencies =
android.enable_androidx = True
android.add_src =

android.arch = arm64-v8a

android.entrypoint = main.py
