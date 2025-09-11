import os
import docx
import pandas as pd
import fitz  # PyMuPDF
from datetime import datetime  # Импортируем datetime
from .database import process_and_add_text

# Определяем путь к директории, где находится этот скрипт
script_dir = os.path.dirname(os.path.abspath(__file__))
# Директория, в которую нужно складывать исходные файлы (относительно этого скрипта)
SOURCE_DIRECTORY = os.path.join(script_dir, "source_documents")


def load_from_docx(file_path):
    """
    Извлекает текст из файла .docx, пропуская параграфы, которые не удается прочитать.
    Это делает загрузку более устойчивой к поврежденным или сложным файлам.
    """
    full_text = []
    try:
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            try:
                # Пытаемся добавить текст каждого параграфа отдельно
                if para.text.strip():
                    full_text.append(para.text)
            except Exception as para_e:
                # Если не удалось прочитать конкретный параграф, логируем и пропускаем
                print(f"  [!] Пропущен нечитаемый параграф в файле {os.path.basename(file_path)}: {para_e}")
                continue
        
        if not full_text:
             print(f"  [!] Не удалось извлечь текст из файла {os.path.basename(file_path)}. Возможно, он пуст или содержит только нетекстовые элементы.")
             return None

        return '\n'.join(full_text)
        
    except Exception as e:
        # Обработка общей ошибки, если файл не открывается в принципе
        print(f"  [!] КРИТИЧЕСКАЯ ОШИБКА при чтении .docx файла {os.path.basename(file_path)}: {e}")
        return None


def load_from_xlsx(file_path, category):
    """
    Гибкая загрузка из XLSX. Справляется с одним или двумя столбцами.
    Если есть только столбец с названием услуги, формирует осмысленный текст для поиска.
    """
    try:
        df = pd.read_excel(file_path)
        
        # 1. Определяем столбец с названием
        name_col = next((col for col in df.columns if 'услуг' in col.lower() or 'название' in col.lower() or 'тема' in col.lower()), df.columns[0])
        
        # 2. Пытаемся найти столбец с описанием (он может отсутствовать)
        content_col = next((col for col in df.columns if 'описание' in col.lower() or 'содержание' in col.lower()), None)

        print(f"  -> Обработка XLSX: '{os.path.basename(file_path)}'. Колонка с названием: '{name_col}'.", end=" ")
        if content_col:
            print(f"Колонка с описанием: '{content_col}'.")
        else:
            print("Колонка с описанием не найдена.")
            
        texts_with_metadata = []
        for _, row in df.iterrows():
            service_name = row[name_col]
            if pd.isna(service_name):
                continue

            # 3. Формируем текст для поиска в зависимости от наличия описания
            if content_col and pd.notna(row.get(content_col)):
                # Есть и название, и описание
                text = f"ИТ-услуга: {service_name}. Описание: {row[content_col]}"
            else:
                # Есть только название, создаем более описательный текст
                text = f"В каталоге предоставляется ИТ-услуга: {service_name}"

            metadata = {
                "source": os.path.basename(file_path), 
                "category": category, 
                "doc_type": "knowledge",
                "load_date": datetime.now().isoformat(),
                "service_name": service_name
            }
            texts_with_metadata.append((text, metadata))
            
        return texts_with_metadata
    except Exception as e:
        print(f"!!! Ошибка при чтении XLSX файла {file_path}: {e}")
        return []


def load_from_pdf(file_path):
    """Извлекает текст из файла .pdf."""
    try:
        doc = fitz.open(file_path)
        full_text = [page.get_text() for page in doc]
        doc.close()
        return '\n'.join(full_text)
    except Exception as e:
        print(f"  [!] Ошибка при чтении .pdf файла {os.path.basename(file_path)}: {e}")
        return None


def load_from_txt(file_path):
    """Извлекает текст из файла .txt."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"  [!] Ошибка при чтении .txt файла {os.path.basename(file_path)}: {e}")
        return None


def load_from_routing_xlsx(file_path):
    """Загружает примеры запросов и департаменты для маршрутизации."""
    try:
        df = pd.read_excel(file_path)
        
        # Ищем столбцы для запроса и отдела
        request_col = next((col for col in df.columns if 'запрос' in col.lower()), df.columns[0])
        department_col = next((col for col in df.columns if 'отдел' in col.lower() or 'департамент' in col.lower()), df.columns[1])

        print(f"  -> Обработка XLSX для маршрутизации: '{os.path.basename(file_path)}'. Используются столбцы: '{request_col}' и '{department_col}'.")

        texts_with_metadata = []
        for _, row in df.iterrows():
            if pd.notna(row[request_col]) and pd.notna(row[department_col]):
                text = row[request_col]
                metadata = {
                    "source": os.path.basename(file_path),
                    "department": row[department_col],
                    "doc_type": "routing_example",
                    "load_date": datetime.now().isoformat() # Добавляем дату загрузки
                }
                texts_with_metadata.append((text, metadata))
        return texts_with_metadata
    except Exception as e:
        print(f"!!! Ошибка при чтении XLSX файла для маршрутизации {file_path}: {e}")
        return []


def main():
    """
    Основная функция для рекурсивного обхода директории с документами,
    извлечения текста, формирования метаданных и добавления в векторную базу.
    """
    print("="*50)
    print("🚀 Запуск скрипта загрузки данных в векторную базу...")
    print(f"Ищем файлы в директории: {SOURCE_DIRECTORY}")
    print("="*50)
    
    processed_files_count = 0
    
    if not os.path.isdir(SOURCE_DIRECTORY):
        print(f"❌ Ошибка: Директория '{SOURCE_DIRECTORY}' не найдена.")
        print("Пожалуйста, создайте ее и поместите в нее файлы для обработки.")
        return

    # Рекурсивный обход всех папок и файлов
    for root, dirs, files in os.walk(SOURCE_DIRECTORY):
        # Исключаем временные файлы Excel
        files = [f for f in files if not f.startswith('~')]
        
        for filename in files:
            file_path = os.path.join(root, filename)
            
            # Определяем категорию и тип документа
            relative_path = os.path.relpath(root, SOURCE_DIRECTORY)
            is_routing_file = relative_path.startswith('routing_examples')
            category = os.path.basename(root) if not is_routing_file else 'routing'

            print(f"[*] Обработка файла: {filename} (Категория: {category})")

            # --- Новая, более четкая логика обработки ---

            # 1. Обработка XLSX файлов (и для маршрутизации, и для базы знаний)
            if filename.lower().endswith(".xlsx"):
                records_to_process = []
                if is_routing_file:
                    records_to_process = load_from_routing_xlsx(file_path)
                else:
                    records_to_process = load_from_xlsx(file_path, category)
                
                # Обрабатываем каждую запись из файла
                for text, metadata in records_to_process:
                    process_and_add_text(text, metadata=metadata)
                
                if records_to_process:
                    processed_files_count += 1
                continue # Переходим к следующему файлу

            # 2. Обработка остальных файлов базы знаний (DOCX, PDF, TXT)
            text = None
            if filename.lower().endswith(".docx"):
                text = load_from_docx(file_path)
            elif filename.lower().endswith(".pdf"):
                text = load_from_pdf(file_path)
            elif filename.lower().endswith(".txt"):
                text = load_from_txt(file_path)
            else:
                print(f"  [-] Пропуск файла: неподдерживаемый формат.")
                continue

            # Добавляем весь текст файла как один документ
            if text and text.strip():
                metadata = {
                    "source": filename,
                    "category": category,
                    "doc_type": "knowledge",
                    "load_date": datetime.now().isoformat()
                }
                if process_and_add_text(text, metadata=metadata):
                    processed_files_count += 1
            else:
                print(f"  [!] Файл '{filename}' пуст или не удалось извлечь текст. Пропускается.")
    
    print("="*50)
    if processed_files_count > 0:
        print(f"✅ Успешно обработано и загружено: {processed_files_count} файлов.")
    else:
        print("🟡 Новых файлов для загрузки не найдено или не удалось обработать.")
    print("Скрипт завершил работу.")
    print("="*50)


if __name__ == "__main__":
    main()
