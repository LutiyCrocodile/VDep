#!/usr/bin/env python3
"""
Скрипт для генерации тестового видео с помощью FFmpeg.
Создает цветное тестовое видео с текстом.
"""

import subprocess
import sys
from pathlib import Path

def generate_test_video(output_path, duration=30, resolution="1280x720"):
    """
    Генерация тестового видео с цветными полосами и текстом.
    
    Args:
        output_path: Путь для сохранения видео
        duration: Длительность в секундах
        resolution: Разрешение (например, '1280x720', '1920x1080')
    """
    try:
        # Проверяем наличие FFmpeg
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ FFmpeg не найден. Пожалуйста, установите FFmpeg:")
        print("   Windows: choco install ffmpeg")
        print("   macOS: brew install ffmpeg")
        print("   Linux: sudo apt install ffmpeg")
        return False
    
    print(f"🎬 Генерация тестового видео...")
    print(f"   Разрешение: {resolution}")
    print(f"   Длительность: {duration} сек")
    print(f"   Выходной файл: {output_path}")
    
    width, height = resolution.split('x')
    
    # Создаем фильтр для тестового видео с текстом
    filter_complex = (
        f"testsrc=duration={duration}:size={resolution}:rate=30,"
        f"drawtext=text='Тестовое видео':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2-50,"
        f"drawtext=text='{resolution} @ 30fps':fontsize=32:fontcolor=yellow:x=(w-text_w)/2:y=(h-text_h)/2+50,"
        f"drawtext=text='%{{pts\\:gmtime\\:0\\:%H\\:%M\\:%S}}':fontsize=24:fontcolor=white:x=20:y=20"
    )
    
    cmd = [
        'ffmpeg',
        '-f', 'lavfi',
        '-i', filter_complex,
        '-pix_fmt', 'yuv420p',
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-crf', '23',
        '-movflags', '+faststart',
        '-y',  # Перезаписать если существует
        output_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            file_size = Path(output_path).stat().st_size / (1024 * 1024)
            print(f"✅ Видео создано: {output_path}")
            print(f"📁 Размер файла: {file_size:.2f} MB")
            return True
        else:
            print(f"❌ Ошибка FFmpeg: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ Таймаут при создании видео")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def main():
    # Параметры по умолчанию
    output_dir = Path(__file__).parent.parent / "test_videos"
    output_dir.mkdir(exist_ok=True)
    
    # Разные разрешения для тестирования
    configs = [
        ("test_video_360p.mp4", 15, "640x360"),
        ("test_video_720p.mp4", 15, "1280x720"),
        ("test_video_1080p.mp4", 10, "1920x1080"),
    ]
    
    print("=" * 60)
    print("🎬 Генерация тестовых видео")
    print("=" * 60)
    
    generated = []
    for filename, duration, resolution in configs:
        output_path = output_dir / filename
        if generate_test_video(str(output_path), duration, resolution):
            generated.append(str(output_path))
    
    print("\n" + "=" * 60)
    if generated:
        print(f"✅ Создано видео: {len(generated)}")
        print("📁 Файлы:")
        for path in generated:
            print(f"   - {path}")
        print("\n💡 Для загрузки используйте:")
        print(f"   python scripts/upload_test_video.py {generated[0]} 'Тестовое видео'")
    else:
        print("❌ Не удалось создать видео")
        sys.exit(1)

if __name__ == "__main__":
    main()
