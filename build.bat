@echo off

echo "Building Accessify..."
pyinstaller --log-level WARN --distpath build\distribution --workpath build\temp --clean --noconfirm build\accessify.spec

