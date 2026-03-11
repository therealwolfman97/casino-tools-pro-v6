[app]

title = Casino Tools Pro v6 by SH
package.name = casinotoolsp6sh
package.domain = org.sachith

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,json,txt

version = 1.0

requirements = python3,kivy,requests,certifi

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

android.api = 33
android.minapi = 21

log_level = 2

[buildozer]
log_level = 2
warn_on_root = 0
