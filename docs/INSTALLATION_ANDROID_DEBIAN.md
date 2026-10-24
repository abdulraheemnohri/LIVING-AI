# Android Debian/Linux installation

This guide targets a Debian/Linux userland running on Android (including ARM64 devices such as Pixel 6). It is not an Android APK and does not require Docker. LiteRT-LM availability depends on the Python wheel/platform combination available for your environment.

## One-command setup

Run from the Debian/Linux terminal:

```bash
git clone https://github.com/abdulraheemnohri/LIVING-AI.git
cd LIVING-AI
bash scripts/install_android_debian.sh
source .venv/bin/activate
bash scripts/run.sh
```

Then open `http://127.0.0.1:8000` in a browser on the same device.

## Requirements

- Debian/Linux userland with a working `bash` shell.
- Python 3.11 or newer; `python3-venv` support must be available.
- Git, curl, df, awk, and sha256sum.
- Internet access for Python packages and the model download.
- Approximately 5.5 GB free storage for the default model download, plus additional space for the virtual environment, caches, data, and logs.
- Memory headroom for model inference. The default Gemma 4 E2B model may put substantial pressure on a 6 GB phone; start with CPU mode and close other memory-heavy apps.
- Node.js is optional and used only for JavaScript syntax checks during install.

If venv creation fails on a Debian image where apt is available, install system prerequisites using the environment's package manager, for example:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-dev build-essential git curl
```

Some Android Linux containers do not provide `sudo` or apt access; use the host environment's supported package-install method instead.

## LiteRT-LM is installed with the project

The installer runs:

```bash
python -m pip install -e ".[dev,litert]"
```

The `litert` extra installs the LiteRT-LM Python API (`litert-lm-api`) and CLI (`litert-lm`). The application can only load LiteRT-LM models supported by the installed runtime. The CLI and Python API are separate entry points; a working CLI does not by itself prove that the app's model adapter can generate correctly.

## Automatic model download

The default `.env.example` enables `LIVING_AI_AUTO_DOWNLOAD_MODEL=true`. On first install, the installer attempts to download the configured model to:

`models/litert/gemma-4-E2B-it.litertlm`

The downloader checks free space, refuses to overwrite a non-empty destination, uses a temporary partial file, rejects obvious HTML error pages, and records a SHA-256 checksum. The checksum is a local integrity record, not a publisher signature; verify it against a trusted publisher-provided hash if one is available.

The model download is large and can consume mobile data. To skip it, set this in `.env` before running the installer:

```dotenv
LIVING_AI_AUTO_DOWNLOAD_MODEL=false
```

If a download fails, the rest of the installation continues. Retry later:

```bash
source .venv/bin/activate
bash scripts/download_litert_model.sh
```

Model defaults:

- Repository: `litert-community/gemma-4-E2B-it-litert-lm`
- File: `gemma-4-E2B-it.litertlm`
- Local path: `models/litert/gemma-4-E2B-it.litertlm`
- Backend: `cpu`

These values can be changed in the private `.env` file. Do not change the model filename/repository unless the selected repository actually publishes that artifact.

## Configure the admin password

Before using protected settings and management features, edit `.env` and set a long, unique password:

```dotenv
LIVING_AI_ADMIN_PASSWORD=replace-with-a-long-random-secret
LIVING_AI_HOST=127.0.0.1
LIVING_AI_PORT=8000
LIVING_AI_LITERTLM_BACKEND=cpu
```

Keep the server bound to `127.0.0.1` unless you understand the security implications of network exposure. Do not commit `.env` or share its password.

## Start and stop

Start:

```bash
cd LIVING-AI
source .venv/bin/activate
bash scripts/run.sh
```

Stop with `Ctrl+C` in the terminal running the server. Open the dashboard at `http://127.0.0.1:8000`.

## Verify installation

In another terminal:

```bash
cd LIVING-AI
source .venv/bin/activate
python -m compileall -q living_ai
litert-lm --help
curl -fsS http://127.0.0.1:8000/api/health
```

The health endpoint checks the web app only; it does not prove that the model loaded or that generation works. Test the LiteRT-LM model with the documented CLI command and then test chat from the UI.

## Troubleshooting

- **No space left / insufficient storage:** free space before retrying; the model is not required for the app's basic web server to start.
- **Python package install fails:** check Python version, architecture, network access, and wheel availability. Some native dependencies may not support every Debian-on-Android userland.
- **`litert-lm` command missing:** activate `.venv` and reinstall with `python -m pip install -e ".[litert]"`.
- **Model file missing:** run `bash scripts/download_litert_model.sh`; check the repo, filename, internet connection, and available storage in `.env`.
- **Model loads but generation fails:** check the LiteRT-LM runtime version, model/runtime compatibility, CPU memory pressure, and the app logs under `data/logs/`.
- **Port already in use:** change `LIVING_AI_PORT` in `.env` and restart.
- **Admin routes return 503:** set `LIVING_AI_ADMIN_PASSWORD` in `.env` and restart.
- **App starts but tests fail:** run `pytest -q` and review the first failing traceback. Do not enable automatic updates until CI is green.

## Security and update notes

The model download does not execute the model as a program, but model files and Python packages are still external inputs. Review changes before enabling automatic updates. Automatic GitHub updates remain a separate feature from model downloading. Back up `.env` and `data/` before updating.
