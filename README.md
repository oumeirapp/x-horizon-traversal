To build the app

uv run pyinstaller \                               
  --clean \
  --noconfirm \
  --windowed \
  --name "X Traversal" \
  --icon=logo.icns \
  --add-data "logo.png:." \
  --add-binary "$(which ffmpeg):." \
  --add-binary "$(which ffprobe):." \
  app.py


Get visibility into the bundled app's stdout/stderr
./dist/X\ Traversal.app/Contents/MacOS/X\ Traversal