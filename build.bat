@echo off

pyinstaller --distpath build\distribution --workpath build\temp --clean --noconfirm build\accessify.spec

