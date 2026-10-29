import asyncio
import os
import subprocess
import sys
import tempfile
import threading
import urllib.request
import zipfile
from pathlib import Path
import shutil
import ctypes

import customtkinter as ctk
import pygame

# ═══════════════════════════════════════════════════════
# ПРОВЕРКА И ЗАПУСК ОТ ИМЕНИ АДМИНИСТРАТОРА
# ═══════════════════════════════════════════════════════

def is_admin():
    """Проверка, запущена ли программа с правами администратора"""
    try:
        if sys.platform == 'win32':
            return ctypes.windll.shell32.IsUserAnAdmin()
        else:
            return os.geteuid() == 0
    except:
        return False


def run_as_admin():
    """Перезапуск программы от имени администратора"""
    if is_admin():
        return True
    
    try:
        if sys.platform == 'win32':
            # Windows: используем ShellExecuteW с verb="runas"
            script = os.path.abspath(sys.argv[0])
            params = ' '.join([f'"{arg}"' for arg in sys.argv[1:]])
            
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", _hc_gui_executable(), f'"{script}" {params}', None, 1
            )
            
            # ShellExecuteW возвращает > 32 при успехе
            if ret > 32:
                sys.exit(0)  # Закрываем текущий процесс
            else:
                return False
        else:
            # Linux/macOS: используем sudo
            script = os.path.abspath(sys.argv[0])
            subprocess.check_call(['sudo', sys.executable, script] + sys.argv[1:], **_hc_no_window_flags())
            sys.exit(0)
    except Exception as e:
        print(f"Не удалось получить права администратора: {e}")
        return False


# === HIDE CONSOLE PATCH START ===
import os as _hc_os
import shutil as _hc_shutil
import subprocess as _hc_subprocess
import sys as _hc_sys
from pathlib import Path as _hc_Path

HIDE_CONSOLE_PATCH_VERSION = "2026.10.29-1"


def _hc_is_windows():
    return _hc_sys.platform == "win32"


def _hc_find_pythonw():
    """
    Ищет pythonw.exe рядом с текущим python.exe или в PATH.
    """
    if not _hc_is_windows():
        return None

    try:
        exe = _hc_Path(_hc_sys.executable)
    except Exception:
        return None

    if exe.name.lower() == "pythonw.exe":
        return exe

    if exe.name.lower() == "python.exe":
        candidate = exe.with_name("pythonw.exe")
        if candidate.exists():
            return candidate

    which = _hc_shutil.which("pythonw.exe")
    if which:
        try:
            return _hc_Path(which)
        except Exception:
            return None

    return None


def _hc_gui_executable():
    """
    Возвращает pythonw.exe, если мы на Windows и он доступен.
    Используется для повышения прав, чтобы UAC-перезапуск не открывал консоль.
    """
    pythonw = _hc_find_pythonw()
    if pythonw:
        return str(pythonw)
    return _hc_sys.executable


def _hc_no_window_flags():
    """
    Флаги для subprocess, чтобы дочерние консольные процессы не открывали чёрное окно.
    """
    if not _hc_is_windows():
        return {}

    create_no_window = getattr(_hc_subprocess, "CREATE_NO_WINDOW", 0x08000000)
    return {"creationflags": create_no_window}


def _hc_relaunch_without_console():
    """
    Если программа запущена через python.exe на Windows, перезапускает себя через pythonw.exe.
    Это убирает основное чёрное окно.

    Важно:
    - если запускать именно textToVoice.py двойным кликом через python.exe,
      микро-вспышка консоли старого процесса всё равно возможна;
    - чтобы гарантированно не было вспышки, лучше запускать .pyw / pythonw / VBS-ярлык.
    """
    if not _hc_is_windows():
        return False

    # Позволяет принудительно показать консоль для отладки:
    # set TTS_SHOW_CONSOLE=1
    if _hc_os.environ.get("TTS_SHOW_CONSOLE") == "1":
        return False

    # Не трогаем собраные через PyInstaller/cx_Freeze и подобные.
    if getattr(_hc_sys, "frozen", False):
        return False

    # Защита от цикла перезапуска.
    if _hc_os.environ.get("TTS_NO_CONSOLE_RELAUNCH") == "1":
        return False

    try:
        exe = _hc_Path(_hc_sys.executable)
    except Exception:
        return False

    # Уже pythonw — ничего не делаем.
    if exe.name.lower() != "python.exe":
        return False

    pythonw = exe.with_name("pythonw.exe")
    if not pythonw.exists():
        which = _hc_shutil.which("pythonw.exe")
        if not which:
            return False
        pythonw = _hc_Path(which)

    try:
        script = _hc_Path(_hc_sys.argv[0]).resolve()
    except Exception:
        return False

    if not script.exists():
        return False

    env = _hc_os.environ.copy()
    env["TTS_NO_CONSOLE_RELAUNCH"] = "1"

    cmd = [str(pythonw), str(script)] + _hc_sys.argv[1:]

    try:
        # DETACHED_PROCESS помогает не наследовать консоль родительского процесса.
        detached_process = getattr(_hc_subprocess, "DETACHED_PROCESS", 0x00000008)

        _hc_subprocess.Popen(
            cmd,
            env=env,
            cwd=str(script.parent),
            close_fds=True,
            creationflags=detached_process,
        )

        _hc_sys.exit(0)
    except SystemExit:
        raise
    except Exception:
        return False

    return True


# Автоматически прячем консоль при импорте/запуске файла.
try:
    _hc_relaunch_without_console()
except SystemExit:
    raise
except Exception:
    pass
# === HIDE CONSOLE PATCH END ===

# Проверяем права при запуске
if not is_admin():
    if not run_as_admin():
        print("Программа требует прав администратора для корректной работы.")
        print("Запустите программу от имени администратора вручную.")
        input("Нажмите Enter для выхода...")
        sys.exit(1)

# ═══════════════════════════════════════════════════════
# НАСТРОЙКИ И КОНСТАНТЫ
# ═══════════════════════════════════════════════════════

# Настройка внешнего вида
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Авторские права
COPYRIGHT = "code by ТЕХНОПРАНК"

# Необходимые пакеты
REQUIRED_PACKAGES = [
    'edge-tts',
    'pydub',
    'mutagen'
]


# === SELF-DIAGNOSTICS PATCH START ===
import asyncio as _sd_asyncio
import importlib as _sd_importlib
import importlib.metadata as _sd_metadata
import os as _sd_os
import re as _sd_re
import shutil as _sd_shutil
import socket as _sd_socket
import ssl as _sd_ssl
import subprocess as _sd_subprocess
import sys as _sd_sys
import tempfile as _sd_tempfile
import time as _sd_time
import traceback as _sd_traceback
from datetime import datetime as _sd_datetime
from pathlib import Path as _sd_Path

SELF_DIAG_PATCH_VERSION = "2026.10.29-1"

try:
    SD_LOG_FILE = _sd_Path(__file__).with_name("tts_diagnostics.log")
except NameError:
    SD_LOG_FILE = _sd_Path("tts_diagnostics.log")


class SelfDiagnostics:
    """
    Самодиагностика и самолечение для Нейро-Озвучка Pro.
    """

    CORE_PACKAGES = [
        "edge-tts",
        "pydub",
        "mutagen",
        "customtkinter",
        "pygame",
    ]

    MIN_VERSIONS = {
        "edge-tts": "7.0.0",
        "pydub": "0.25.1",
        "mutagen": "1.47.0",
        "customtkinter": "5.2.0",
        "pygame": "2.5.0",
    }

    UPDATED_PACKAGES = []
    RESTART_REQUIRED = False

    EDGE_UPDATE_KEYWORDS = (
        "401",
        "403",
        "429",
        "500",
        "502",
        "503",
        "504",
        "unauthorized",
        "forbidden",
        "drm",
        "token",
        "sec-ms-gec",
        "websocket",
        "web socket",
        "handshake",
        "connection reset",
        "connection aborted",
        "server disconnected",
        "noaudioreceived",
        "no audio received",
        "empty",
        "invalid response",
        "too many requests",
        "internal server error",
        "service unavailable",
        "gateway",
        "ssl",
        "certificate",
        "cannot connect",
        "failed to receive audio",
        "synthesis",
        "speech",
        "edge",
        "microsoft",
        "status code",
        "status=",
        "http 4",
        "http 5",
    )

    @classmethod
    def log(cls, message):
        try:
            line = f"[{_sd_datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}"
            SD_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(SD_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
            print(line)
        except Exception:
            try:
                print(message)
            except Exception:
                pass

    @staticmethod
    def _module_name(pkg):
        return pkg.replace("-", "_")

    @staticmethod
    def _version_tuple(version):
        parts = []
        for part in _sd_re.split(r"[.\-+]", str(version)):
            if part.isdigit():
                parts.append(int(part))
            else:
                m = _sd_re.match(r"(\d+)", part)
                if m:
                    parts.append(int(m.group(1)))
                else:
                    parts.append(0)
        return tuple(parts) or (0,)

    @classmethod
    def get_installed_version(cls, pkg):
        try:
            return _sd_metadata.version(pkg)
        except Exception:
            return None

    @classmethod
    def is_package_installed(cls, pkg):
        try:
            _sd_importlib.import_module(cls._module_name(pkg))
            return True
        except Exception:
            return False

    @classmethod
    def needs_upgrade(cls, pkg):
        ver = cls.get_installed_version(pkg)
        if not ver:
            return True

        min_ver = cls.MIN_VERSIONS.get(pkg)
        if not min_ver:
            return False

        try:
            return cls._version_tuple(ver) < cls._version_tuple(min_ver)
        except Exception:
            return True

    @classmethod
    def pip_install(cls, pkg, upgrade=False):
        base = [_sd_sys.executable, "-m", "pip", "install"]
        if upgrade:
            base.append("--upgrade")
        base.extend(["--no-cache-dir", pkg])

        variants = [
            base,
            base + ["--user"],
            base + ["--break-system-packages"],
            base + ["--user", "--break-system-packages"],
        ]

        for cmd in variants:
            try:
                cls.log("PIP: " + " ".join(cmd))
                res = _sd_subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=600, **_hc_no_window_flags()
                )
                if res.returncode == 0:
                    cls.log(f"OK pip: {pkg}")
                    return True

                tail = (res.stderr or res.stdout or "")[-800:]
                cls.log(f"PIP failed rc={res.returncode}: {tail}")
            except Exception as e:
                cls.log(f"PIP exception: {e}")

        return False

    @classmethod
    def reload_module_if_loaded(cls, pkg):
        mod_name = cls._module_name(pkg)
        if mod_name in _sd_sys.modules:
            try:
                _sd_importlib.reload(_sd_sys.modules[mod_name])
                cls.log(f"Reloaded module: {mod_name}")
            except Exception as e:
                cls.log(f"Reload failed {mod_name}: {e}")

    @classmethod
    def ensure_package(cls, pkg, upgrade_if_old=True, force=False):
        installed = cls.is_package_installed(pkg)
        need_install = not installed
        need_upgrade = force or (installed and upgrade_if_old and cls.needs_upgrade(pkg))

        if not need_install and not need_upgrade:
            return False

        action = "install" if need_install else "upgrade"
        cls.log(
            f"{action}: {pkg}; "
            f"installed_version={cls.get_installed_version(pkg)}; "
            f"min_version={cls.MIN_VERSIONS.get(pkg, '-')}"
        )

        ok = cls.pip_install(pkg, upgrade=(need_upgrade or not installed))
        if ok:
            cls.UPDATED_PACKAGES.append(pkg)

            mod_name = cls._module_name(pkg)
            if mod_name in _sd_sys.modules:
                # Если обновили уже загруженный GUI-модуль, лучше перезапустить процесс.
                if pkg in ("customtkinter", "pygame"):
                    cls.RESTART_REQUIRED = True
                else:
                    cls.reload_module_if_loaded(pkg)

        return ok

    @classmethod
    def ensure_core_packages(cls):
        if _sd_os.environ.get("TTS_SKIP_PACKAGE_UPDATE") == "1":
            cls.log("Package update skipped by TTS_SKIP_PACKAGE_UPDATE=1.")
            return

        auto_all = _sd_os.environ.get("TTS_AUTO_UPDATE_ALL") == "1"

        for pkg in cls.CORE_PACKAGES:
            # edge-tts обновляем активнее всего, потому что он зависит от внешнего сервиса.
            upgrade_if_old = (pkg == "edge-tts") or auto_all
            cls.ensure_package(pkg, upgrade_if_old=upgrade_if_old)

    @classmethod
    def restart_if_required(cls):
        if not cls.RESTART_REQUIRED:
            return False

        if _sd_os.environ.get("TTS_NO_RESTART") == "1":
            cls.log("Restart required, but disabled by TTS_NO_RESTART=1.")
            return False

        cls.log("Restarting application after updating loaded packages...")
        try:
            _sd_subprocess.Popen([_sd_sys.executable] + _sd_sys.argv, **_hc_no_window_flags())
            _sd_sys.exit(0)
        except Exception as e:
            cls.log(f"Restart failed: {e}")

        return True

    @classmethod
    def should_update_edge_tts(cls, error):
        s = str(error).lower()
        return any(keyword in s for keyword in cls.EDGE_UPDATE_KEYWORDS)

    @classmethod
    def update_edge_tts_force(cls):
        cls.log("Force updating edge-tts...")
        return cls.ensure_package("edge-tts", upgrade_if_old=True, force=True)

    @classmethod
    def test_network(cls):
        hosts = [
            ("speech.platform.bing.com", 443),
            ("www.bing.com", 443),
        ]

        for host, port in hosts:
            try:
                _sd_socket.gethostbyname(host)
                with _sd_socket.create_connection((host, port), timeout=5):
                    pass
                cls.log(f"Network OK: {host}:{port}")
                return True
            except Exception as e:
                cls.log(f"Network fail {host}:{port}: {e}")

        return False

    @classmethod
    async def _edge_list_voices(cls):
        import edge_tts
        return await edge_tts.list_voices()

    @classmethod
    async def _edge_generate_sample(cls, output_file, voice="ru-RU-DmitryNeural"):
        import edge_tts

        text = "Самопроверка синтеза речи."

        try:
            communicate = edge_tts.Communicate(text=text, voice=voice)
        except TypeError:
            communicate = edge_tts.Communicate(text, voice)

        await communicate.save(output_file)

    @classmethod
    def test_edge_tts_service(cls, retries=3):
        last_error = None

        for attempt in range(retries):
            temp_dir = _sd_tempfile.mkdtemp(prefix="tts_diag_")
            sample = _sd_os.path.join(temp_dir, "sample.mp3")

            try:
                voices = _sd_asyncio.run(cls._edge_list_voices())
                ru_voices = [
                    v for v in voices
                    if str(v.get("Locale", "")).startswith("ru-")
                ]

                voice = ru_voices[0]["ShortName"] if ru_voices else "ru-RU-DmitryNeural"

                _sd_asyncio.run(cls._edge_generate_sample(sample, voice))

                if _sd_os.path.exists(sample) and _sd_os.path.getsize(sample) > 1024:
                    cls.log(
                        "Edge-TTS OK: "
                        f"russian_voices={len(ru_voices)}, "
                        f"sample_bytes={_sd_os.path.getsize(sample)}"
                    )
                    return True, "OK"

                raise RuntimeError("Edge-TTS вернул пустой или слишком маленький файл.")

            except Exception as e:
                last_error = e
                cls.log(f"Edge-TTS attempt {attempt + 1}/{retries} failed: {e}")

                if attempt < retries - 1:
                    if cls.should_update_edge_tts(str(e)):
                        cls.log("Error looks like Edge-TTS/service/API change. Updating edge-tts...")
                        cls.update_edge_tts_force()
                    else:
                        _sd_time.sleep(1.5 * (attempt + 1))

            finally:
                try:
                    _sd_shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception:
                    pass

        msg = str(last_error) if last_error else "Unknown Edge-TTS error"
        cls.log(f"Edge-TTS service test failed: {msg}")
        return False, msg

    @classmethod
    def run_startup_diagnostics(cls):
        if _sd_os.environ.get("TTS_SKIP_STARTUP_DIAGNOSTICS") == "1":
            cls.log("Startup diagnostics skipped by TTS_SKIP_STARTUP_DIAGNOSTICS=1.")
            return {"skipped": True}

        cls.log(f"=== Self diagnostics {SELF_DIAG_PATCH_VERSION} ===")
        cls.log(f"Python: {_sd_sys.version}")
        cls.log(f"Platform: {_sd_sys.platform}")
        cls.log(f"Executable: {_sd_sys.executable}")
        cls.log(f"Script: {getattr(_sd_sys, 'argv', ['?'])[0]}")

        report = {}

        try:
            cls.ensure_core_packages()

            if cls.restart_if_required():
                return {"restarted": True}

            report["network"] = cls.test_network()

            ok, msg = cls.test_edge_tts_service()
            report["edge_tts_ok"] = ok
            report["edge_tts_message"] = msg

            if not ok:
                cls.log(
                    "WARNING: Edge-TTS self-test failed. "
                    "Application will still start, but speech generation may fail. "
                    f"Check {SD_LOG_FILE}"
                )

        except Exception as e:
            report["error"] = str(e)
            cls.log(f"Diagnostics exception: {e}")
            cls.log(_sd_traceback.format_exc())

        return report

    @staticmethod
    def patched_load_voices(self):
        """
        Безопасная загрузка русских голосов с retry и автообновлением edge-tts.
        """
        last_error = None

        for attempt in range(3):
            try:
                import edge_tts

                async def get_ru_voices():
                    voices = await edge_tts.list_voices()
                    return [
                        v for v in voices
                        if str(v.get("Locale", "")).startswith("ru-")
                    ]

                ru_voices = _sd_asyncio.run(get_ru_voices())

                display_names = []
                self.voices = {}

                for v in ru_voices:
                    name = f"{v['ShortName']} ({v['Gender']})"
                    display_names.append(name)
                    self.voices[name] = v["ShortName"]

                self.after(
                    0,
                    lambda dn=display_names: self.voice_combo.configure(values=dn)
                )
                self.after(
                    0,
                    lambda dn=display_names: self.voice_combo.set(
                        dn[0] if dn else "Нет голосов"
                    )
                )
                self.after(
                    0,
                    lambda c=len(ru_voices): self.status_label.configure(
                        text=f"Загружено {c} русских голосов",
                        text_color="#32CD32"
                    )
                )

                SelfDiagnostics.log(f"Voices loaded: {len(ru_voices)}")
                return

            except Exception as e:
                last_error = e
                SelfDiagnostics.log(f"Load voices attempt {attempt + 1}/3 failed: {e}")

                if attempt < 2 and SelfDiagnostics.should_update_edge_tts(str(e)):
                    SelfDiagnostics.update_edge_tts_force()
                elif attempt < 2:
                    _sd_time.sleep(1.5 * (attempt + 1))

        err = str(last_error) if last_error else "Unknown error"
        SelfDiagnostics.log(f"Load voices failed permanently: {err}")
        self.after(
            0,
            lambda e=err: self.status_label.configure(
                text=f"Ошибка загрузки голосов: {e}",
                text_color="red"
            )
        )

    @staticmethod
    async def patched_generate_chunk_async(self, text, voice, output_file, index, total):
        """
        Безопасная генерация одного чанка с retry и автообновлением edge-tts.
        """
        last_error = None

        for attempt in range(3):
            try:
                import edge_tts

                try:
                    communicate = edge_tts.Communicate(text=text, voice=voice)
                except TypeError:
                    communicate = edge_tts.Communicate(text, voice)

                await communicate.save(output_file)

                if not _sd_os.path.exists(output_file):
                    raise RuntimeError("Файл не создан после generate.save()")

                size = _sd_os.path.getsize(output_file)
                if size <= 0:
                    raise RuntimeError("Получен пустой аудиофайл")

                self.after(
                    0,
                    lambda x=index: self._update_progress(
                        x + 1,
                        total,
                        f"Генерация {x + 1}/{total}..."
                    )
                )

                return

            except Exception as e:
                last_error = e
                SelfDiagnostics.log(
                    f"Chunk {index + 1}/{total} attempt {attempt + 1}/3 failed: {e}"
                )

                if attempt < 2 and SelfDiagnostics.should_update_edge_tts(str(e)):
                    SelfDiagnostics.update_edge_tts_force()
                elif attempt < 2:
                    await _sd_asyncio.sleep(1.5 * (attempt + 1))

        raise last_error

    @staticmethod
    def patched_install_ffmpeg_windows(self):
        """
        Улучшенная установка FFmpeg на Windows:
        копирует ffmpeg.exe и ffprobe.exe, fallback в папку приложения.
        """
        import urllib.request as _url
        import zipfile as _zip

        try:
            url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

            self._log("Скачивание FFmpeg...")
            temp_dir = _sd_tempfile.mkdtemp()
            zip_path = _sd_os.path.join(temp_dir, "ffmpeg.zip")

            def progress_hook(block_num, block_size, total_size):
                if total_size > 0:
                    percent = min(100, block_num * block_size * 100 / total_size)
                    self.after(
                        0,
                        lambda p=percent: self._update_progress(
                            0.75 + (p / 100) * 0.2
                        )
                    )

            _url.urlretrieve(url, zip_path, reporthook=progress_hook)

            self._log("Распаковка FFmpeg...")
            extract_dir = _sd_os.path.join(temp_dir, "ffmpeg_extracted")

            with _zip.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)

            wanted = {"ffmpeg.exe", "ffprobe.exe"}
            found = []

            for root, dirs, files in _sd_os.walk(extract_dir):
                for f in files:
                    if f.lower() in wanted:
                        found.append(_sd_os.path.join(root, f))

            if not found:
                self._log("  ✗ Не удалось найти ffmpeg.exe/ffprobe.exe в архиве")
                _sd_shutil.rmtree(temp_dir, ignore_errors=True)
                return

            system_root = _sd_os.environ.get("SystemRoot", "C:\\Windows")
            system_dir = _sd_os.path.join(system_root, "System32")

            try:
                app_dir = str(_sd_Path(_sd_sys.argv[0]).resolve().parent)
            except Exception:
                app_dir = str(_sd_Path.cwd())

            destinations = [system_dir, app_dir]
            installed = False

            for dest_dir in destinations:
                try:
                    for exe_path in found:
                        exe_name = _sd_os.path.basename(exe_path)
                        dest_file = _sd_os.path.join(dest_dir, exe_name)
                        _sd_shutil.copy2(exe_path, dest_file)

                    if dest_dir == app_dir:
                        path = _sd_os.environ.get("PATH", "")
                        if app_dir not in path.split(_sd_os.pathsep):
                            _sd_os.environ["PATH"] = app_dir + _sd_os.pathsep + path

                    self._log(f"  ✓ FFmpeg установлен в {dest_dir}")
                    installed = True
                    break

                except Exception as e:
                    self._log(f"  ! Не удалось установить в {dest_dir}: {e}")

            if not installed:
                self._log("  ✗ FFmpeg не установлен автоматически.")
                self._log("  Скачайте FFmpeg вручную: https://ffmpeg.org/download.html")

            _sd_shutil.rmtree(temp_dir, ignore_errors=True)

        except Exception as e:
            self._log(f"  ✗ Ошибка установки FFmpeg: {e}")
            SelfDiagnostics.log(f"FFmpeg install exception: {e}")
            SelfDiagnostics.log(_sd_traceback.format_exc())
            self._log("  Скачайте FFmpeg вручную с https://ffmpeg.org/download.html")


# === SELF-DIAGNOSTICS PATCH END ===

class DependencyInstaller(ctk.CTk):
    """Окно установки зависимостей"""
    
    def __init__(self):
        super().__init__()
        
        self.title("Установка компонентов | Администратор")
        self.geometry("600x400")
        self.resizable(False, False)
        
        self.missing_packages = []
        self.ffmpeg_missing = False
        
        self._create_ui()
        self.after(100, self._check_dependencies)
    
    def _create_ui(self):
        # Индикатор администратора
        admin_label = ctk.CTkLabel(
            self,
            text="✓ Запущено с правами администратора",
            text_color="#32CD32",
            font=("Segoe UI", 10)
        )
        admin_label.pack(pady=(5, 0))
        
        self.info_label = ctk.CTkLabel(
            self,
            text="Проверка необходимых компонентов...",
            font=("Segoe UI", 14, "bold")
        )
        self.info_label.pack(pady=20)
        
        self.progress = ctk.CTkProgressBar(self, width=500)
        self.progress.pack(pady=10)
        self.progress.set(0)
        
        self.log_text = ctk.CTkTextbox(self, width=550, height=250)
        self.log_text.pack(pady=10, padx=20)
        
        self.button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.button_frame.pack(pady=10)
        
        self.install_btn = ctk.CTkButton(
            self.button_frame,
            text="Установить недостающие компоненты",
            command=self._install_all,
            width=300,
            height=40,
            state="disabled"
        )
        self.install_btn.pack(side="left", padx=5)
        
        self.skip_btn = ctk.CTkButton(
            self.button_frame,
            text="Пропустить (запустить без установки)",
            command=self._skip_and_launch,
            width=300,
            height=40,
            fg_color="gray"
        )
        self.skip_btn.pack(side="left", padx=5)
    
    def _log(self, message):
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
    
    def _check_dependencies(self):
        """Проверка всех зависимостей"""
        self._log("Проверка Python-пакетов...")
        
        # Проверяем пакеты
        for package in REQUIRED_PACKAGES:
            try:
                __import__(package.replace('-', '_'))
                self._log(f"  ✓ {package} установлен")
            except ImportError:
                self._log(f"  ✗ {package} отсутствует")
                self.missing_packages.append(package)
        
        # Проверяем FFmpeg
        self._log("\nПроверка FFmpeg...")
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                timeout=5, **_hc_no_window_flags()
            )
            if result.returncode == 0:
                self._log("  ✓ FFmpeg установлен")
            else:
                self._log("  ✗ FFmpeg не найден")
                self.ffmpeg_missing = True
        except Exception:
            self._log("  ✗ FFmpeg не найден")
            self.ffmpeg_missing = True
        
        # Итог
        self._log("\n" + "="*50)
        if not self.missing_packages and not self.ffmpeg_missing:
            self.info_label.configure(text="Все компоненты установлены!", text_color="#32CD32")
            self._log("Всё готово к работе!")
            self.after(2000, self._launch_app)
        else:
            self.info_label.configure(
                text="Найдены отсутствующие компоненты",
                text_color="orange"
            )
            self.install_btn.configure(state="normal")
    
    def _install_all(self):
        """Установка всех недостающих компонентов"""
        self.install_btn.configure(state="disabled")
        self.skip_btn.configure(state="disabled")
        
        thread = threading.Thread(target=self._install_process, daemon=True)
        thread.start()
    
    def _install_process(self):
        """Процесс установки в отдельном потоке"""
        try:
            # Установка Python-пакетов
            if self.missing_packages:
                self._log("\nУстановка Python-пакетов...")
                for i, package in enumerate(self.missing_packages):
                    self._log(f"Установка {package}...")
                    self._update_progress((i + 1) / (len(self.missing_packages) + 1) * 0.5)
                    
                    try:
                        subprocess.check_call([
                            sys.executable,
                            '-m',
                            'pip',
                            'install',
                            package
                        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **_hc_no_window_flags())
                        self._log(f"  ✓ {package} установлен")
                    except Exception as e:
                        self._log(f"  ✗ Ошибка установки {package}: {e}")
            
            # Установка FFmpeg
            if self.ffmpeg_missing:
                self._log("\nУстановка FFmpeg...")
                self._update_progress(0.75)
                self._install_ffmpeg()
            
            self._update_progress(1.0)
            self._log("\n✓ Установка завершена!")
            self.after(2000, self._launch_app)
            
        except Exception as e:
            self._log(f"\n✗ Ошибка: {e}")
            self.after(0, lambda: self.install_btn.configure(state="normal"))
            self.after(0, lambda: self.skip_btn.configure(state="normal"))
    
    def _install_ffmpeg(self):
        """Установка FFmpeg"""
        if sys.platform == 'win32':
            self._install_ffmpeg_windows()
        elif sys.platform == 'darwin':
            self._log("macOS: установите FFmpeg через 'brew install ffmpeg'")
        else:
            self._log("Linux: установите FFmpeg через 'sudo apt install ffmpeg'")
    
    def _install_ffmpeg_windows(self):
        """Установка FFmpeg на Windows с правами администратора"""
        try:
            # URL для скачивания FFmpeg
            url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
            
            self._log("Скачивание FFmpeg...")
            temp_dir = tempfile.mkdtemp()
            zip_path = os.path.join(temp_dir, "ffmpeg.zip")
            
            # Скачиваем
            def progress_hook(block_num, block_size, total_size):
                if total_size > 0:
                    percent = min(100, block_num * block_size * 100 / total_size)
                    self.after(0, lambda p=percent: self._update_progress(0.75 + (p / 100) * 0.2))
            
            urllib.request.urlretrieve(url, zip_path, reporthook=progress_hook)
            
            self._log("Распаковка FFmpeg...")
            extract_dir = os.path.join(temp_dir, "ffmpeg_extracted")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Ищем папку bin
            ffmpeg_bin = None
            for root, dirs, files in os.walk(extract_dir):
                if 'ffmpeg.exe' in files:
                    ffmpeg_bin = os.path.join(root, 'ffmpeg.exe')
                    break
            
            if ffmpeg_bin:
                # Копируем в системную директорию (теперь у нас есть права!)
                system_dir = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32')
                dest_path = os.path.join(system_dir, 'ffmpeg.exe')
                
                try:
                    shutil.copy2(ffmpeg_bin, dest_path)
                    self._log(f"  ✓ FFmpeg установлен в {system_dir}")
                except Exception as e:
                    # Если не получилось в System32, копируем в папку программы
                    app_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
                    dest_path = os.path.join(app_dir, 'ffmpeg.exe')
                    shutil.copy2(ffmpeg_bin, dest_path)
                    os.environ['PATH'] = app_dir + os.pathsep + os.environ['PATH']
                    self._log(f"  ✓ FFmpeg установлен в {app_dir}")
            else:
                self._log("  ✗ Не удалось найти ffmpeg.exe")
            
            # Очистка
            shutil.rmtree(temp_dir, ignore_errors=True)
            
        except Exception as e:
            self._log(f"  ✗ Ошибка установки FFmpeg: {e}")
            self._log("  Скачайте FFmpeg вручную с https://ffmpeg.org/download.html")
    
    def _update_progress(self, value):
        self.after(0, lambda: self.progress.set(value))
    
    def _launch_app(self):
        """Запуск основного приложения"""
        self.destroy()
        app = VoiceGeneratorApp()
        app.mainloop()
    
    def _skip_and_launch(self):
        """Пропустить установку и запустить приложение"""
        self.destroy()
        app = VoiceGeneratorApp()
        app.mainloop()


class VoiceGeneratorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"Нейро-Озвучка Pro | {COPYRIGHT} | Администратор")
        self.geometry("900x880")
        self.resizable(True, True)

        # Состояние
        self.voices = {}
        self.is_processing = False
        self.current_audio_path = None
        self.is_paused = False
        self.ffmpeg_available = False

        # UI Компоненты
        self._create_ui()

        # Загружаем голоса и проверяем FFmpeg в фоне
        threading.Thread(target=self._load_voices, daemon=True).start()
        threading.Thread(target=self._check_ffmpeg, daemon=True).start()

    def _create_ui(self):
        # Поле ввода текста
        self.textbox = ctk.CTkTextbox(self, font=("Segoe UI", 14), wrap="word", height=200)
        self.textbox.pack(fill="both", expand=True, padx=20, pady=(20, 10))
        self.textbox.insert(
            "0.0",
            "Вставьте сюда любой объем текста...\n\n"
            "НОВАЯ ВЕРСИЯ: Ускоренная генерация + быстрая склейка через FFmpeg + профессиональная обработка звука!\n\n"
            "Выберите пресет обработки: от чистого голоса до эпичного подкаст-звучания с эквалайзером и компрессией."
        )

        # Панель управления голосом
        voice_panel = ctk.CTkFrame(self, fg_color="transparent")
        voice_panel.pack(fill="x", padx=20, pady=5)

        # Выбор голоса
        self.voice_combo = ctk.CTkComboBox(voice_panel, width=250, state="readonly")
        self.voice_combo.set("Загрузка голосов...")
        self.voice_combo.pack(side="left", padx=(0, 10))

        # Кнопка прослушать
        self.play_btn = ctk.CTkButton(
            voice_panel,
            text="Прослушать",
            command=self._start_preview,
            width=120,
            height=35
        )
        self.play_btn.pack(side="left", padx=5)

        # Кнопка паузы
        self.pause_btn = ctk.CTkButton(
            voice_panel,
            text="Пауза",
            command=self._toggle_pause,
            width=80,
            height=35,
            state="disabled",
            fg_color="gray",
            hover_color="gray"
        )
        self.pause_btn.pack(side="left", padx=5)

        # Кнопка стоп
        self.stop_btn = ctk.CTkButton(
            voice_panel,
            text="Стоп",
            command=self._stop_audio,
            width=80,
            height=35,
            state="disabled",
            fg_color="gray",
            hover_color="gray"
        )
        self.stop_btn.pack(side="left", padx=5)

        # Панель эффектов
        effects_frame = ctk.CTkFrame(self, fg_color="transparent")
        effects_frame.pack(fill="x", padx=20, pady=10)

        effects_label = ctk.CTkLabel(effects_frame, text="Обработка звука:", font=("Segoe UI", 13, "bold"))
        effects_label.pack(anchor="w", pady=(0, 5))

        # Пресеты эффектов
        self.preset_combo = ctk.CTkComboBox(
            effects_frame,
            values=["Чистый голос", "Радио", "Подкаст", "Эпичный", "Глубокий бас"],
            state="readonly",
            width=200
        )
        self.preset_combo.set("Подкаст")
        self.preset_combo.pack(side="left", padx=(0, 10))

        # Чекбокс нормализации
        self.normalize_check = ctk.CTkCheckBox(
            effects_frame,
            text="Нормализация громкости",
            font=("Segoe UI", 12)
        )
        self.normalize_check.select()
        self.normalize_check.pack(side="left", padx=10)

        # Чекбокс компрессии
        self.compress_check = ctk.CTkCheckBox(
            effects_frame,
            text="Компрессия (ровный звук)",
            font=("Segoe UI", 12)
        )
        self.compress_check.select()
        self.compress_check.pack(side="left", padx=10)

        # Панель сохранения
        save_panel = ctk.CTkFrame(self, fg_color="transparent")
        save_panel.pack(fill="x", padx=20, pady=10)

        # Кнопка сохранения
        self.generate_btn = ctk.CTkButton(
            save_panel,
            text="Сохранить как MP3",
            command=self._start_generation,
            height=40,
            font=("Segoe UI", 14, "bold")
        )
        self.generate_btn.pack(side="right")

        # Индикаторы
        self.speed_label = ctk.CTkLabel(
            save_panel,
            text="Параллельная генерация включена",
            text_color="gray",
            font=("Segoe UI", 11)
        )
        self.speed_label.pack(side="right", padx=10)

        self.ffmpeg_label = ctk.CTkLabel(
            save_panel,
            text="FFmpeg: проверка...",
            text_color="gray",
            font=("Segoe UI", 11)
        )
        self.ffmpeg_label.pack(side="right", padx=10)

        # Прогресс бар
        self.progress = ctk.CTkProgressBar(self, mode="determinate")
        self.progress.pack(fill="x", padx=20, pady=(0, 10))
        self.progress.set(0)

        # Статус
        self.status_label = ctk.CTkLabel(self, text="Готов к работе", text_color="gray")
        self.status_label.pack(pady=(0, 5))

        # --- БЛОК АВТОРСКИХ ПРАВ ---
        copyright_frame = ctk.CTkFrame(self, fg_color="transparent")
        copyright_frame.pack(fill="x", padx=20, pady=(5, 15))

        self.copyright_label = ctk.CTkLabel(
            copyright_frame,
            text=f"(c) {COPYRIGHT} | Все права защищены",
            text_color="gray",
            font=("Segoe UI", 10, "italic")
        )
        self.copyright_label.pack(side="left")

        self.version_label = ctk.CTkLabel(
            copyright_frame,
            text="v3.2 Pro (Admin Mode)",
            text_color="gray",
            font=("Segoe UI", 10)
        )
        self.version_label.pack(side="right")

    def _check_ffmpeg(self):
        """Проверка наличия FFmpeg в системе"""
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                timeout=5, **_hc_no_window_flags()
            )
            if result.returncode == 0:
                self.ffmpeg_available = True
                self.after(0, lambda: self.ffmpeg_label.configure(
                    text="FFmpeg: доступен (быстрая склейка)",
                    text_color="#32CD32"
                ))
            else:
                self.ffmpeg_available = False
                self.after(0, lambda: self.ffmpeg_label.configure(
                    text="FFmpeg: не найден (медленная склейка)",
                    text_color="orange"
                ))
        except Exception:
            self.ffmpeg_available = False
            self.after(0, lambda: self.ffmpeg_label.configure(
                text="FFmpeg: не найден (медленная склейка)",
                text_color="orange"
            ))

    def _load_voices(self):
        """Асинхронная загрузка списка русских голосов"""
        try:
            import edge_tts
            
            async def get_ru_voices():
                voices = await edge_tts.list_voices()
                return [v for v in voices if v["Locale"].startswith("ru-")]

            ru_voices = asyncio.run(get_ru_voices())

            display_names = []
            self.voices = {}
            for v in ru_voices:
                name = f"{v['ShortName']} ({v['Gender']})"
                display_names.append(name)
                self.voices[name] = v["ShortName"]

            self.after(0, lambda: self.voice_combo.configure(values=display_names))
            self.after(0, lambda: self.voice_combo.set(display_names[0] if display_names else "Нет голосов"))
            self.after(0, lambda: self.status_label.configure(
                text=f"Загружено {len(ru_voices)} русских голосов",
                text_color="#32CD32"
            ))

        except Exception as e:
            self.after(0, lambda: self.status_label.configure(
                text=f"Ошибка загрузки голосов: {e}",
                text_color="red"
            ))

    def _apply_audio_effects(self, audio):
        """Применение эффектов обработки звука"""
        from pydub.effects import compress_dynamic_range, normalize
        
        preset = self.preset_combo.get()

        if preset == "Радио":
            audio = audio.high_pass_filter(200)
            audio = audio.low_pass_filter(3000)
        elif preset == "Подкаст":
            audio = audio.high_pass_filter(80)
            audio = audio.low_pass_filter(12000)
        elif preset == "Эпичный":
            audio = audio.low_pass_filter(15000)
            audio = audio + 3
        elif preset == "Глубокий бас":
            audio = audio.low_pass_filter(250)
            audio = audio + 4

        if self.compress_check.get():
            audio = compress_dynamic_range(audio, threshold=-20.0, ratio=4.0, attack=5.0, release=50.0)

        if self.normalize_check.get():
            audio = normalize(audio)

        return audio

    def _fast_merge_ffmpeg(self, mp3_files: list, output_path: str):
        """Быстрая склейка MP3 через FFmpeg без перекодирования"""
        list_file = os.path.join(tempfile.gettempdir(), f"ffmpeg_list_{os.getpid()}.txt")
        try:
            with open(list_file, 'w', encoding='utf-8') as f:
                for mp3 in mp3_files:
                    safe_path = mp3.replace("'", "'\\''")
                    f.write(f"file '{safe_path}'\n")

            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', list_file,
                '-c', 'copy',
                output_path
            ]
            subprocess.run(cmd, check=True, capture_output=True, timeout=60, **_hc_no_window_flags())
        finally:
            if os.path.exists(list_file):
                try:
                    os.remove(list_file)
                except:
                    pass

    def _slow_merge_pydub(self, mp3_files: list):
        """Медленная склейка через Pydub (fallback)"""
        from pydub import AudioSegment
        
        audio_segments = []
        for mp3 in mp3_files:
            if os.path.exists(mp3):
                audio_segments.append(AudioSegment.from_mp3(mp3))

        if not audio_segments:
            raise Exception("Не удалось загрузить аудиофрагменты")

        result = audio_segments[0]
        for segment in audio_segments[1:]:
            result += segment
        return result

    def _add_id3_tags(self, file_path: str, title: str = ""):
        """Добавление ID3 тегов в MP3 файл"""
        try:
            from mutagen.id3 import ID3, TIT2, TPE1, TALB, COMM

            try:
                tags = ID3(file_path)
            except:
                tags = ID3()

            tags.add(TIT2(encoding=3, text=title if title else "Озвучка текста"))
            tags.add(TPE1(encoding=3, text="ТЕХНОПРАНК TTS"))
            tags.add(TALB(encoding=3, text="Нейро-Озвучка Pro"))
            tags.add(COMM(encoding=3, lang='rus', desc='Comment',
                         text=f"Создано с помощью Нейро-Озвучка Pro. {COPYRIGHT}"))

            tags.save(file_path)
        except Exception:
            pass

    def _merge_and_apply_effects(self, mp3_files: list, output_path: str, apply_effects: bool = True):
        """Универсальный метод склейки с эффектами"""
        from pydub import AudioSegment
        
        needs_effects = apply_effects and (
            self.preset_combo.get() != "Чистый голос" or
            self.normalize_check.get() or
            self.compress_check.get()
        )

        if self.ffmpeg_available and not needs_effects:
            self._fast_merge_ffmpeg(mp3_files, output_path)
        elif self.ffmpeg_available and needs_effects:
            temp_merged = output_path + ".temp.mp3"
            try:
                self._fast_merge_ffmpeg(mp3_files, temp_merged)
                audio = AudioSegment.from_mp3(temp_merged)
                audio = self._apply_audio_effects(audio)
                audio.export(output_path, format="mp3", bitrate="192k")
            finally:
                if os.path.exists(temp_merged):
                    try:
                        os.remove(temp_merged)
                    except:
                        pass
        else:
            audio = self._slow_merge_pydub(mp3_files)
            if needs_effects:
                audio = self._apply_audio_effects(audio)
            audio.export(output_path, format="mp3", bitrate="192k")

    def _start_preview(self):
        """Запуск прослушивания текста"""
        if self.is_processing:
            return

        self._stop_audio()

        text = self.textbox.get("0.0", "end").strip()
        selected_voice_display = self.voice_combo.get()

        if not text or selected_voice_display not in self.voices:
            self.status_label.configure(text="Введите текст и выберите голос!", text_color="orange")
            return

        self.is_processing = True
        self.play_btn.configure(state="disabled", text="Генерация...")

        thread = threading.Thread(
            target=self._process_preview,
            args=(text, self.voices[selected_voice_display]),
            daemon=True
        )
        thread.start()

    def _process_preview(self, text: str, voice: str):
        """Генерация и воспроизведение превью"""
        import edge_tts
        from pydub import AudioSegment
        
        try:
            chunks = self._smart_split(text, max_chars=2000)
            total = len(chunks)

            temp_dir = tempfile.mkdtemp()

            self.after(0, lambda: self._update_progress(0, total, "Параллельная генерация запущена..."))

            async def generate_all_chunks():
                tasks = []
                for i, chunk in enumerate(chunks):
                    temp_file = os.path.join(temp_dir, f"chunk_{i}.mp3")
                    task = self._generate_chunk_async(chunk, voice, temp_file, i, total)
                    tasks.append(task)
                return await asyncio.gather(*tasks)

            asyncio.run(generate_all_chunks())

            mp3_files = []
            for i in range(total):
                temp_file = os.path.join(temp_dir, f"chunk_{i}.mp3")
                if os.path.exists(temp_file):
                    mp3_files.append(temp_file)

            if not mp3_files:
                raise Exception("Не удалось сгенерировать аудио")

            self.after(0, lambda: self._update_progress(total, total, "Быстрая склейка и обработка..."))

            temp_output = os.path.join(temp_dir, "preview.mp3")
            self._merge_and_apply_effects(mp3_files, temp_output, apply_effects=True)

            for mp3 in mp3_files:
                try:
                    os.remove(mp3)
                except:
                    pass

            self._add_id3_tags(temp_output, title="Preview")

            self.current_audio_path = temp_output
            self.after(0, lambda: self._play_audio())

        except Exception as e:
            self.after(0, lambda: self._finish(f"Ошибка: {str(e)}", error=True))

    async def _generate_chunk_async(self, text: str, voice: str, output_file: str, index: int, total: int):
        """Асинхронная генерация одного чанка"""
        import edge_tts
        
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_file)
        self.after(0, lambda x=index: self._update_progress(
            x + 1, total, f"Генерация {x + 1}/{total}..."
        ))

    def _play_audio(self):
        """Воспроизведение аудио"""
        if not self.current_audio_path or not os.path.exists(self.current_audio_path):
            return

        try:
            pygame.mixer.music.load(self.current_audio_path)
            pygame.mixer.music.play()

            self.pause_btn.configure(state="normal", fg_color=("gray75", "gray25"), hover_color=("gray65", "gray35"))
            self.stop_btn.configure(state="normal", fg_color=("gray75", "gray25"), hover_color=("gray65", "gray35"))
            self.play_btn.configure(state="normal", text="Прослушать")
            self.status_label.configure(text="Воспроизведение с эффектами...", text_color="#1E90FF")
            self.is_processing = False

            self._check_playback_end()

        except Exception as e:
            self._finish(f"Ошибка воспроизведения: {str(e)}", error=True)

    def _check_playback_end(self):
        """Проверка окончания воспроизведения"""
        if not pygame.mixer.music.get_busy() and not self.is_paused:
            self._reset_controls()
            self.status_label.configure(text="Воспроизведение завершено", text_color="#32CD32")
        else:
            self.after(500, self._check_playback_end)

    def _toggle_pause(self):
        """Пауза/Возобновление"""
        if not pygame.mixer.music.get_busy() and not self.is_paused:
            return

        if not self.is_paused:
            pygame.mixer.music.pause()
            self.is_paused = True
            self.pause_btn.configure(text="Продолжить")
            self.status_label.configure(text="Пауза", text_color="orange")
        else:
            pygame.mixer.music.unpause()
            self.is_paused = False
            self.pause_btn.configure(text="Пауза")
            self.status_label.configure(text="Воспроизведение...", text_color="#1E90FF")

    def _stop_audio(self):
        """Остановка воспроизведения"""
        pygame.mixer.music.stop()
        self.is_paused = False
        self._reset_controls()
        self.status_label.configure(text="Остановлено", text_color="gray")

    def _reset_controls(self):
        """Сброс кнопок управления"""
        self.pause_btn.configure(state="disabled", text="Пауза", fg_color="gray", hover_color="gray")
        self.stop_btn.configure(state="disabled", fg_color="gray", hover_color="gray")
        self.play_btn.configure(state="normal", text="Прослушать")

    def _start_generation(self):
        """Сохранение в MP3"""
        if self.is_processing:
            return

        self._stop_audio()

        text = self.textbox.get("0.0", "end").strip()
        selected_voice_display = self.voice_combo.get()

        if not text or selected_voice_display not in self.voices:
            self.status_label.configure(text="Введите текст и выберите голос!", text_color="orange")
            return

        save_path = ctk.filedialog.asksaveasfilename(
            defaultextension=".mp3",
            filetypes=[("MP3 Audio", "*.mp3")],
            title="Сохранить озвучку"
        )

        if not save_path:
            return

        self.is_processing = True
        self.generate_btn.configure(state="disabled", text="Генерация...")

        thread = threading.Thread(
            target=self._process_text,
            args=(text, self.voices[selected_voice_display], save_path),
            daemon=True
        )
        thread.start()

    def _process_text(self, text: str, voice: str, output_path: str):
        """Разбиение текста, параллельная генерация и склейка для сохранения"""
        import edge_tts
        from pydub import AudioSegment
        
        try:
            chunks = self._smart_split(text, max_chars=2000)
            total = len(chunks)

            temp_dir = tempfile.mkdtemp()

            self.after(0, lambda: self._update_progress(0, total, "Параллельная генерация запущена..."))

            async def generate_all_chunks():
                tasks = []
                for i, chunk in enumerate(chunks):
                    temp_file = os.path.join(temp_dir, f"chunk_{i}.mp3")
                    task = self._generate_chunk_async(chunk, voice, temp_file, i, total)
                    tasks.append(task)
                return await asyncio.gather(*tasks)

            asyncio.run(generate_all_chunks())

            mp3_files = []
            for i in range(total):
                temp_file = os.path.join(temp_dir, f"chunk_{i}.mp3")
                if os.path.exists(temp_file):
                    mp3_files.append(temp_file)

            if not mp3_files:
                raise Exception("Не удалось сгенерировать аудио")

            self.after(0, lambda: self._update_progress(total, total, "Склейка и обработка..."))

            self._merge_and_apply_effects(mp3_files, output_path, apply_effects=True)

            for mp3 in mp3_files:
                try:
                    os.remove(mp3)
                except:
                    pass

            self._add_id3_tags(output_path, title=Path(output_path).stem)

            try:
                os.rmdir(temp_dir)
            except:
                pass

            self.after(0, lambda: self._finish(f"Готово! Сохранено: {Path(output_path).name}"))

        except Exception as e:
            self.after(0, lambda: self._finish(f"Ошибка: {str(e)}", error=True))

    @staticmethod
    def _smart_split(text: str, max_chars: int = 2000) -> list:
        """Умное разбиение текста"""
        paragraphs = text.split('\n')
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current_chunk) + len(para) + 1 <= max_chars:
                current_chunk += ("\n" if current_chunk else "") + para
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                if len(para) > max_chars:
                    sentences = para.replace('. ', '.|').replace('! ', '!|').replace('? ', '?|').split('|')
                    current_chunk = ""
                    for sent in sentences:
                        if len(current_chunk) + len(sent) + 1 <= max_chars:
                            current_chunk += (" " if current_chunk else "") + sent
                        else:
                            if current_chunk:
                                chunks.append(current_chunk)
                            current_chunk = sent
                else:
                    current_chunk = para

        if current_chunk:
            chunks.append(current_chunk)

        return chunks or [" "]

    def _update_progress(self, current: int, total: int, status: str):
        self.progress.set(current / total if total > 0 else 0)
        self.status_label.configure(text=status, text_color="#1E90FF")

    def _finish(self, message: str, error: bool = False):
        self.progress.set(1 if not error else 0)
        self.status_label.configure(text=message, text_color="red" if error else "#32CD32")
        self.generate_btn.configure(state="normal", text="Сохранить как MP3")
        self.is_processing = False

    def __del__(self):
        """Очистка при закрытии"""
        try:
            pygame.mixer.quit()
        except:
            pass
        if self.current_audio_path and os.path.exists(self.current_audio_path):
            try:
                os.remove(self.current_audio_path)
            except:
                pass


def _apply_self_diagnostic_patches():
    try:
        if "VoiceGeneratorApp" in globals():
            VoiceGeneratorApp._load_voices = SelfDiagnostics.patched_load_voices
            VoiceGeneratorApp._generate_chunk_async = SelfDiagnostics.patched_generate_chunk_async

        if "DependencyInstaller" in globals():
            DependencyInstaller._install_ffmpeg_windows = SelfDiagnostics.patched_install_ffmpeg_windows

        SelfDiagnostics.log("Runtime self-diagnostic patches applied.")
    except Exception as e:
        try:
            SelfDiagnostics.log(f"Failed to apply runtime patches: {e}")
        except Exception:
            print(f"Failed to apply runtime patches: {e}")


if __name__ == "__main__":
    try:
        SelfDiagnostics.run_startup_diagnostics()
    except Exception as e:
        print(f"Startup diagnostics failed: {e}")

    _apply_self_diagnostic_patches()

    try:
        pygame.mixer.init()
    except Exception as e:
        print(f"PyGame mixer init failed: {e}")

    installer = DependencyInstaller()
    installer.mainloop()
