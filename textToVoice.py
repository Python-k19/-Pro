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
                None, "runas", sys.executable, f'"{script}" {params}', None, 1
            )
            
            # ShellExecuteW возвращает > 32 при успехе
            if ret > 32:
                sys.exit(0)  # Закрываем текущий процесс
            else:
                return False
        else:
            # Linux/macOS: используем sudo
            script = os.path.abspath(sys.argv[0])
            subprocess.check_call(['sudo', sys.executable, script] + sys.argv[1:])
            sys.exit(0)
    except Exception as e:
        print(f"Не удалось получить права администратора: {e}")
        return False


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
                timeout=5
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
                        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
                timeout=5
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
            subprocess.run(cmd, check=True, capture_output=True, timeout=60)
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


if __name__ == "__main__":
    # Инициализация pygame
    pygame.mixer.init()
    
    # Запускаем установщик зависимостей
    installer = DependencyInstaller()
    installer.mainloop()