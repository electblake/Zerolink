SHELL := sh

APP := zero
SPEC := zero.spec
# Derive version from pyproject.toml (simple regex; no extra tools)
VER := $(shell python -c "import re,io;print(re.search(r'^version\\s*=\\s*\\\"([^\\\"]+)\\\"', io.open('pyproject.toml','r',encoding='utf-8').read(), re.M).group(1))")
# Use Python for stable arch on Windows (e.g., amd64)
ARCH := $(shell python -c "import platform;print(platform.machine().lower())")
OS := windows
DIST_DIR := dist/$(APP)-$(VER)-$(OS)-$(ARCH)
DIST_EXE := $(DIST_DIR)/$(APP).exe

.PHONY: all help build install uninstall clean dist-clean wheel wheel-install wheelhouse wheelhouse-install

all: build

help:
	@set -eu; \
	echo 'Targets:'; \
    echo '  make build     - Build $(APP) via PyInstaller spec (always)'; \
	echo '  make install   - Copy exe to $$LOCALAPPDATA/zerolink/Scripts'; \
	echo '  make uninstall - Remove installed exe'; \
	echo '  make wheel     - Build a pip wheel into ./dist'; \
	echo '  make wheel-install - pip install the built wheel from ./dist'; \
	echo '  make wheelhouse - Build offline wheelhouse with deps in ./wheelhouse'; \
	echo '  make wheelhouse-install - Offline pip install from ./wheelhouse'; \
	echo '  make clean     - Remove build directory only'; \
	echo '  make dist-clean- Remove build and dist directories'; \
	echo ''; \
	echo 'Environment:'; \
	uv --version 2>/dev/null || echo '  uv:            not found'; \
	python --version; \
	uv run --group dev pyinstaller --version 2>/dev/null || pyinstaller --version 2>/dev/null || echo '  pyinstaller:   not found (install dev deps with: uv sync --group dev)'; \
	echo ''; \
	echo 'Build output dir:'; \
	echo '  $(DIST_DIR)'

build:
	set -eu; \
	echo '[build] Starting build for $(APP)'; \
	echo '[build] Version: $(VER)'; \
	echo '[build] Target:  $(OS)-$(ARCH)'; \
	echo '[build] Spec:    $(SPEC)'; \
	echo '[build] Dist:    $(DIST_DIR)'; \
	uv --version; \
	echo '[build] PyInstaller version (via uv):'; \
	uv run --group dev pyinstaller --version; \
	echo '[build] Embedding version into zerolink/_version.py'; \
	python -c "import re,io,os; t=io.open('pyproject.toml','r',encoding='utf-8').read(); v=re.search(r'^version\\s*=\\s*\\\"([^\\\"]+)\\\"', t, re.M).group(1); os.makedirs('zerolink', exist_ok=True); io.open('zerolink/_version.py','w',encoding='utf-8').write(f'VERSION = \"{v}\"\\n'); print(f'[build] Wrote zerolink/_version.py with VERSION {v}')"; \
	echo '[build] Command: uv run --group dev pyinstaller --distpath $(DIST_DIR) $(SPEC)'; \
	uv run --group dev pyinstaller --distpath "$(DIST_DIR)" $(SPEC); \
	test -f '$(DIST_EXE)'; \
	echo "[build] Output: $(DIST_EXE)"; \
	echo "[next] Run: make install"


install: build
	set -eu; \
	destdir="$$LOCALAPPDATA/zerolink/Scripts"; \
	destexe="$$destdir/$(APP).exe"; \
	echo "[install] Source: $(DIST_EXE)"; \
	echo "[install] Dest:   $$destexe"; \
	mkdir -p "$$destdir"; \
	tmp="$$destexe.tmp"; \
	cp '$(DIST_EXE)' "$$tmp"; \
	mv "$$tmp" "$$destexe"; \
	ls "$$destexe"; \
	echo ''; \
	echo '[alias] PowerShell (copy/paste):'; \
	echo '  Set-Alias -Name zero -Value "$$env:LOCALAPPDATA\\zerolink\\Scripts\\zero.exe"'

wheel:
	set -eu; \
	echo '[wheel] Building wheel into ./dist'; \
	uv build --wheel; \
	ls dist/*.whl

wheel-install: wheel
	set -eu; \
	echo '[wheel] Installing from local wheel'; \
	pip install dist/*.whl

wheelhouse: wheel
	set -eu; \
	echo '[wheelhouse] Rebuilding wheelhouse'; \
	rm -rf wheelhouse; \
	mkdir wheelhouse; \
	echo '[wheelhouse] Downloading deps for built wheel'; \
	pip download --dest wheelhouse dist/*.whl; \
	echo '[wheelhouse] Adding project wheel'; \
	cp dist/*.whl wheelhouse/; \
	ls wheelhouse

wheelhouse-install: wheelhouse
	set -eu; \
	echo '[wheelhouse] Offline install from ./wheelhouse'; \
	pip install --no-index --find-links wheelhouse dist/*.whl

uninstall:
	set -eu; \
	destdir="$$LOCALAPPDATA/zerolink/Scripts"; \
	destexe="$$destdir/$(APP).exe"; \
	if [ -f "$$destexe" ]; then rm -f "$$destexe"; echo "[uninstall] Removed: $$destexe"; else echo '[uninstall] Not installed'; fi; \
	rmdir "$$destdir" || true

clean:
	set -eu; \
	echo '[clean] Removing build'; \
	rm -rf build; \
	echo '[clean] Done'

dist-clean:
	set -eu; \
	echo '[dist-clean] Removing build and dist'; \
	rm -rf build dist; \
	echo '[dist-clean] Done'
