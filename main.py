import sys
import os
import json
import tempfile
import shutil
import zipfile
import py7zr
import rarfile
import concurrent.futures
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QTextEdit, QFileDialog, QMessageBox,
                             QTableWidget, QTableWidgetItem, QHeaderView, QComboBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from parser import parse_vpk
from cf_kv import CloudflareKV

CONFIG_FILE = "config.json"

# UI Translations Dictionary
TRANSLATIONS = {
    "schinese": {
        "window_title": "求生之路2 VPK地图解析与 Cloudflare KV 上传工具",
        "acc_id_label": "Account ID (账户ID):",
        "acc_id_placeholder": "在此输入 Cloudflare Account ID",
        "ns_id_label": "Namespace ID (命名空间ID):",
        "ns_id_placeholder": "在此输入 Cloudflare KV Namespace ID",
        "token_label": "API Token (API令牌):",
        "token_placeholder": "在此输入 Cloudflare API Token",
        "lang_label": "界面语言 (UI Language):",
        "save_btn": "保存配置",
        "drag_drop_text": "将 VPK/ZIP/RAR/7z 文件拖拽到此处\n或者点击选择文件",
        "file_dialog_title": "选择 VPK/压缩包 文件",
        "file_dialog_filter": "支持的文件 (*.vpk *.zip *.rar *.7z);;所有文件 (*.*)",
        "table_col_code": "建图代码 (不可修改)",
        "table_col_name": "显示名称 (可修改)",
        "upload_btn": "确认修改并上传",
        "msg_missing_config": "请输入 Cloudflare Account ID, Namespace ID 以及 API Token。",
        "msg_missing_title": "缺少配置",
        "msg_upload_success": "所有数据已成功上传至 Cloudflare KV！",
        "msg_success_title": "上传成功",
        "log_load_err": "加载配置文件失败",
        "log_save_ok": "配置已保存。",
        "log_save_err": "保存配置文件失败",
        "log_extracting": "正在解压",
        "log_unsupported_archive": "不支持的压缩包格式",
        "log_extract_fail": "解压失败",
        "log_skip_file": "跳过不支持的文件",
        "log_parsing": "正在解析",
        "log_no_mission": "未找到 mission 数据",
        "log_extract_ok": "提取成功",
        "log_parse_err": "解析时发生错误",
        "log_no_vpk": "未找到可处理的 VPK 文件。",
        "log_no_file": "未选择任何文件。",
        "log_timeout": "警告: 部分文件解析超时 (超过2分钟)！已取消剩余任务。",
        "log_process_err": "处理文件时发生异常",
        "log_no_data": "未提取到任何数据。处理结束。",
        "log_upload_ok": "成功上传",
        "log_upload_fail": "上传失败。API 返回信息",
        "log_upload_err": "上传时发生异常",
        "log_parse_done": "✅ 解析完成！请在上方表格中确认或修改名称，确认无误后点击【确认修改并上传】按钮。",
        "log_uploading": "正在上传",
        "log_records": "条记录"
    },
    "english": {
        "window_title": "L4D2 VPK Map Reader & CF KV Uploader",
        "acc_id_label": "Account ID:",
        "acc_id_placeholder": "Enter Cloudflare Account ID here",
        "ns_id_label": "Namespace ID:",
        "ns_id_placeholder": "Enter Cloudflare KV Namespace ID here",
        "token_label": "API Token:",
        "token_placeholder": "Enter Cloudflare API Token here",
        "lang_label": "UI Language:",
        "save_btn": "Save Config",
        "drag_drop_text": "Drag & Drop VPK/ZIP/RAR/7z files here\nor Click to select",
        "file_dialog_title": "Select VPK/Archive Files",
        "file_dialog_filter": "Supported Files (*.vpk *.zip *.rar *.7z);;All Files (*.*)",
        "table_col_code": "Map Code (Read-only)",
        "table_col_name": "Display Name (Editable)",
        "upload_btn": "Confirm & Upload",
        "msg_missing_config": "Please enter Cloudflare Account ID, Namespace ID and API Token.",
        "msg_missing_title": "Missing Config",
        "msg_upload_success": "All data successfully uploaded to Cloudflare KV!",
        "msg_success_title": "Upload Success",
        "log_load_err": "Failed to load config",
        "log_save_ok": "Configuration saved.",
        "log_save_err": "Failed to save config",
        "log_extracting": "Extracting",
        "log_unsupported_archive": "Unsupported archive format",
        "log_extract_fail": "Extraction failed",
        "log_skip_file": "Skipping unsupported file",
        "log_parsing": "Parsing",
        "log_no_mission": "No mission data found in",
        "log_extract_ok": "Extracted",
        "log_parse_err": "Error parsing",
        "log_no_vpk": "No processable VPK files found.",
        "log_no_file": "No files selected.",
        "log_timeout": "Warning: Some tasks timed out (>2 mins)! Remaining canceled.",
        "log_process_err": "Exception processing file",
        "log_no_data": "No data extracted. Finished.",
        "log_upload_ok": "Successfully uploaded",
        "log_upload_fail": "Upload failed. API response",
        "log_upload_err": "Exception during upload",
        "log_parse_done": "✅ Parsing complete! Review the table above, then click [Confirm & Upload].",
        "log_uploading": "Uploading",
        "log_records": "records"
    },
    "russian": {
        "window_title": "L4D2 VPK Map Reader & CF KV Uploader",
        "acc_id_label": "Account ID:",
        "acc_id_placeholder": "Введите Cloudflare Account ID",
        "ns_id_label": "Namespace ID:",
        "ns_id_placeholder": "Введите Cloudflare KV Namespace ID",
        "token_label": "API Token:",
        "token_placeholder": "Введите Cloudflare API Token",
        "lang_label": "Язык интерфейса:",
        "save_btn": "Сохранить",
        "drag_drop_text": "Перетащите VPK/ZIP/RAR/7z файлы сюда\nили Нажмите для выбора",
        "file_dialog_title": "Выберите файлы VPK/Архива",
        "file_dialog_filter": "Поддерживаемые файлы (*.vpk *.zip *.rar *.7z);;Все файлы (*.*)",
        "table_col_code": "Код карты (Только чтение)",
        "table_col_name": "Отображаемое имя (Редактируемое)",
        "upload_btn": "Подтвердить и Загрузить",
        "msg_missing_config": "Пожалуйста, введите Cloudflare Account ID, Namespace ID и API Token.",
        "msg_missing_title": "Отсутствует конфигурация",
        "msg_upload_success": "Все данные успешно загружены в Cloudflare KV!",
        "msg_success_title": "Успешная загрузка",
        "log_load_err": "Не удалось загрузить конфигурацию",
        "log_save_ok": "Конфигурация сохранена.",
        "log_save_err": "Не удалось сохранить конфигурацию",
        "log_extracting": "Извлечение",
        "log_unsupported_archive": "Неподдерживаемый формат архива",
        "log_extract_fail": "Ошибка извлечения",
        "log_skip_file": "Пропуск неподдерживаемого файла",
        "log_parsing": "Анализ",
        "log_no_mission": "Данные миссии не найдены в",
        "log_extract_ok": "Извлечено",
        "log_parse_err": "Ошибка анализа",
        "log_no_vpk": "Не найдено VPK файлов для обработки.",
        "log_no_file": "Файлы не выбраны.",
        "log_timeout": "Предупреждение: Превышено время ожидания (>2 мин)! Остальные отменены.",
        "log_process_err": "Исключение при обработке файла",
        "log_no_data": "Данные не извлечены. Завершено.",
        "log_upload_ok": "Успешно загружено",
        "log_upload_fail": "Ошибка загрузки. Ответ API",
        "log_upload_err": "Исключение во время загрузки",
        "log_parse_done": "✅ Анализ завершен! Проверьте таблицу выше, затем нажмите [Подтвердить и Загрузить].",
        "log_uploading": "Загрузка",
        "log_records": "записей"
    },
    "spanish": {
        "window_title": "L4D2 VPK Map Reader & CF KV Uploader",
        "acc_id_label": "Account ID:",
        "acc_id_placeholder": "Ingrese Cloudflare Account ID aquí",
        "ns_id_label": "Namespace ID:",
        "ns_id_placeholder": "Ingrese Cloudflare KV Namespace ID aquí",
        "token_label": "API Token:",
        "token_placeholder": "Ingrese Cloudflare API Token aquí",
        "lang_label": "Idioma de UI:",
        "save_btn": "Guardar Config",
        "drag_drop_text": "Arrastre y suelte archivos VPK/ZIP/RAR/7z aquí\no Haga clic para seleccionar",
        "file_dialog_title": "Seleccionar Archivos VPK/Archivo",
        "file_dialog_filter": "Archivos soportados (*.vpk *.zip *.rar *.7z);;Todos los archivos (*.*)",
        "table_col_code": "Código de Mapa (Solo lectura)",
        "table_col_name": "Nombre a Mostrar (Editable)",
        "upload_btn": "Confirmar y Subir",
        "msg_missing_config": "Por favor ingrese Cloudflare Account ID, Namespace ID y API Token.",
        "msg_missing_title": "Configuración Faltante",
        "msg_upload_success": "¡Todos los datos subidos con éxito a Cloudflare KV!",
        "msg_success_title": "Subida Exitosa",
        "log_load_err": "Error al cargar la configuración",
        "log_save_ok": "Configuración guardada.",
        "log_save_err": "Error al guardar la configuración",
        "log_extracting": "Extrayendo",
        "log_unsupported_archive": "Formato de archivo no soportado",
        "log_extract_fail": "Fallo en la extracción",
        "log_skip_file": "Omitiendo archivo no soportado",
        "log_parsing": "Analizando",
        "log_no_mission": "No se encontraron datos de misión en",
        "log_extract_ok": "Extraído",
        "log_parse_err": "Error al analizar",
        "log_no_vpk": "No se encontraron archivos VPK procesables.",
        "log_no_file": "No se seleccionaron archivos.",
        "log_timeout": "Advertencia: ¡Algunas tareas agotaron el tiempo (>2 mins)! Restantes canceladas.",
        "log_process_err": "Excepción al procesar archivo",
        "log_no_data": "No se extrajeron datos. Finalizado.",
        "log_upload_ok": "Subido exitosamente",
        "log_upload_fail": "Subida fallida. Respuesta de la API",
        "log_upload_err": "Excepción durante la subida",
        "log_parse_done": "✅ ¡Análisis completo! Revise la tabla arriba, luego haga clic en [Confirmar y Subir].",
        "log_uploading": "Subiendo",
        "log_records": "registros"
    },
    "japanese": {
        "window_title": "L4D2 VPK Map Reader & CF KV Uploader",
        "acc_id_label": "Account ID:",
        "acc_id_placeholder": "ここに Cloudflare Account ID を入力",
        "ns_id_label": "Namespace ID:",
        "ns_id_placeholder": "ここに Cloudflare KV Namespace ID を入力",
        "token_label": "API Token:",
        "token_placeholder": "ここに Cloudflare API Token を入力",
        "lang_label": "UI 言語:",
        "save_btn": "設定を保存",
        "drag_drop_text": "VPK/ZIP/RAR/7z ファイルをここにドラッグ＆ドロップ\nまたはクリックして選択",
        "file_dialog_title": "VPK/アーカイブファイルを選択",
        "file_dialog_filter": "サポートされるファイル (*.vpk *.zip *.rar *.7z);;すべてのファイル (*.*)",
        "table_col_code": "マップコード (読み取り専用)",
        "table_col_name": "表示名 (編集可能)",
        "upload_btn": "確認してアップロード",
        "msg_missing_config": "Cloudflare Account ID、Namespace ID、および API Token を入力してください。",
        "msg_missing_title": "設定が不足しています",
        "msg_upload_success": "すべてのデータが Cloudflare KV に正常にアップロードされました！",
        "msg_success_title": "アップロード成功",
        "log_load_err": "設定の読み込みに失敗しました",
        "log_save_ok": "設定が保存されました。",
        "log_save_err": "設定の保存に失敗しました",
        "log_extracting": "展開中",
        "log_unsupported_archive": "サポートされていないアーカイブ形式",
        "log_extract_fail": "展開に失敗しました",
        "log_skip_file": "サポートされていないファイルをスキップ",
        "log_parsing": "解析中",
        "log_no_mission": "ミッションデータが見つかりません",
        "log_extract_ok": "抽出成功",
        "log_parse_err": "解析エラー",
        "log_no_vpk": "処理可能な VPK ファイルが見つかりません。",
        "log_no_file": "ファイルが選択されていません。",
        "log_timeout": "警告: 一部のタスクがタイムアウト (>2分) しました！残りはキャンセルされました。",
        "log_process_err": "ファイル処理中の例外",
        "log_no_data": "データは抽出されませんでした。終了します。",
        "log_upload_ok": "アップロード成功",
        "log_upload_fail": "アップロード失敗。API 応答",
        "log_upload_err": "アップロード中の例外",
        "log_parse_done": "✅ 解析完了！上の表を確認し、[確認してアップロード] をクリックしてください。",
        "log_uploading": "アップロード中",
        "log_records": "件のレコード"
    },
    "tchinese": {
        "window_title": "惡靈勢力2 VPK地圖解析與 Cloudflare KV 上傳工具",
        "acc_id_label": "Account ID (帳戶ID):",
        "acc_id_placeholder": "在此輸入 Cloudflare Account ID",
        "ns_id_label": "Namespace ID (命名空間ID):",
        "ns_id_placeholder": "在此輸入 Cloudflare KV Namespace ID",
        "token_label": "API Token (API令牌):",
        "token_placeholder": "在此輸入 Cloudflare API Token",
        "lang_label": "介面語言 (UI Language):",
        "save_btn": "保存配置",
        "drag_drop_text": "將 VPK/ZIP/RAR/7z 檔案拖曳到此處\n或者點擊選擇檔案",
        "file_dialog_title": "選擇 VPK/壓縮包 檔案",
        "file_dialog_filter": "支援的檔案 (*.vpk *.zip *.rar *.7z);;所有檔案 (*.*)",
        "table_col_code": "建圖代碼 (不可修改)",
        "table_col_name": "顯示名稱 (可修改)",
        "upload_btn": "確認修改並上傳",
        "msg_missing_config": "請輸入 Cloudflare Account ID, Namespace ID 以及 API Token。",
        "msg_missing_title": "缺少配置",
        "msg_upload_success": "所有資料已成功上傳至 Cloudflare KV！",
        "msg_success_title": "上傳成功",
        "log_load_err": "加載配置文件失敗",
        "log_save_ok": "配置已保存。",
        "log_save_err": "保存配置文件失敗",
        "log_extracting": "正在解壓",
        "log_unsupported_archive": "不支援的壓縮包格式",
        "log_extract_fail": "解壓失敗",
        "log_skip_file": "跳過不支援的檔案",
        "log_parsing": "正在解析",
        "log_no_mission": "未找到 mission 資料",
        "log_extract_ok": "提取成功",
        "log_parse_err": "解析時發生錯誤",
        "log_no_vpk": "未找到可處理的 VPK 檔案。",
        "log_no_file": "未選擇任何檔案。",
        "log_timeout": "警告: 部分檔案解析超時 (超過2分鐘)！已取消剩餘任務。",
        "log_process_err": "處理檔案時發生異常",
        "log_no_data": "未提取到任何資料。處理結束。",
        "log_upload_ok": "成功上傳",
        "log_upload_fail": "上傳失敗。API 返回資訊",
        "log_upload_err": "上傳時發生異常",
        "log_parse_done": "✅ 解析完成！請在上方表格中確認或修改名稱，確認無誤後點擊【確認修改並上傳】按鈕。",
        "log_uploading": "正在上傳",
        "log_records": "條記錄"
    }
}

# 默认语言，全局可用
current_lang = "schinese"

def _(key):
    return TRANSLATIONS.get(current_lang, TRANSLATIONS["schinese"]).get(key, key)

class ParseThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(list)

    def __init__(self, files):
        super().__init__()
        self.files = files

    def extract_and_find_vpks(self, archive_path, temp_dir):
        vpks = []
        try:
            if zipfile.is_zipfile(archive_path):
                self.log_signal.emit(f"{_('log_extracting')} zip: {os.path.basename(archive_path)}")
                with zipfile.ZipFile(archive_path, 'r') as zf:
                    zf.extractall(temp_dir)
            elif py7zr.is_7zfile(archive_path):
                self.log_signal.emit(f"{_('log_extracting')} 7z: {os.path.basename(archive_path)}")
                with py7zr.SevenZipFile(archive_path, mode='r') as z:
                    z.extractall(path=temp_dir)
            elif rarfile.is_rarfile(archive_path):
                self.log_signal.emit(f"{_('log_extracting')} rar: {os.path.basename(archive_path)}")
                with rarfile.RarFile(archive_path) as rf:
                    rf.extractall(path=temp_dir)
            else:
                self.log_signal.emit(f"{_('log_unsupported_archive')}: {os.path.basename(archive_path)}")
                return vpks

            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.lower().endswith(".vpk"):
                        vpks.append(os.path.join(root, file))
        except Exception as e:
            self.log_signal.emit(f"{_('log_extract_fail')} {archive_path}: {e}")
            
        return vpks

    def process_file(self, file, base_temp_dir):
        results = []
        ext = file.lower().split('.')[-1]
        vpks = []
        
        if ext == "vpk":
            vpks.append(file)
        elif ext in ["zip", "rar", "7z"]:
            # 使用独立子目录防止解压冲突
            sub_dir = tempfile.mkdtemp(dir=base_temp_dir)
            vpks.extend(self.extract_and_find_vpks(file, sub_dir))
        else:
            self.log_signal.emit(f"{_('log_skip_file')}: {file}")
            return results
            
        for vpk_file in vpks:
            self.log_signal.emit(f"{_('log_parsing')} {os.path.basename(vpk_file)}...")
            try:
                # 依然尝试解析vpk，语言传入给parser即可，此处不再让用户选择vpk解析语言，直接提取vpk默认信息
                res = parse_vpk(vpk_file)
                if not res:
                    self.log_signal.emit(f"{_('log_no_mission')} {os.path.basename(vpk_file)}")
                else:
                    for r in res:
                        results.append(r)
                        self.log_signal.emit(f"{_('log_extract_ok')}: {r['map_code']} -> {r['campaign_name']}: {r['chapter_name']} [{r['chapter_num']}/{r['total_chapters']}]")
            except Exception as e:
                self.log_signal.emit(f"{_('log_parse_err')} {vpk_file}: {e}")
                
        return results

    def run(self):
        all_results = []
        temp_dir = tempfile.mkdtemp()
        
        try:
            if not self.files:
                self.log_signal.emit(_("log_no_file"))
                return

            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(self.process_file, f, temp_dir) for f in self.files]
                
                done, not_done = concurrent.futures.wait(futures, timeout=120)
                
                if not_done:
                    self.log_signal.emit(_("log_timeout"))
                    for future in not_done:
                        future.cancel()
                
                for future in done:
                    try:
                        res = future.result()
                        all_results.extend(res)
                    except Exception as e:
                        self.log_signal.emit(f"{_('log_process_err')}: {e}")

            if not all_results:
                self.log_signal.emit(_("log_no_data"))
                
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
            self.finished_signal.emit(all_results)

class UploadThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool)

    def __init__(self, kv_pairs, account_id, namespace_id, api_token):
        super().__init__()
        self.kv_pairs = kv_pairs
        self.account_id = account_id
        self.namespace_id = namespace_id
        self.api_token = api_token
        
    def run(self):
        try:
            cf = CloudflareKV(self.account_id, self.namespace_id, self.api_token)
            success, response = cf.write_bulk(self.kv_pairs)
            if success:
                self.log_signal.emit(f"{_('log_upload_ok')} {len(self.kv_pairs)} {_('log_records')} Cloudflare KV！")
            else:
                self.log_signal.emit(f"{_('log_upload_fail')}: {response}")
            self.finished_signal.emit(success)
        except Exception as e:
            self.log_signal.emit(f"{_('log_upload_err')}: {e}")
            self.finished_signal.emit(False)

class DragDropArea(QLabel):
    files_dropped = pyqtSignal(list)

    def __init__(self):
        super().__init__(_("drag_drop_text"))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #666;
                border-radius: 5px;
                padding: 20px;
                font-size: 16px;
                color: #aaa;
                background-color: #2b2b2b;
            }
        """)
        self.setAcceptDrops(True)

    def update_text(self):
        self.setText(_("drag_drop_text"))

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                QLabel {
                    border: 2px dashed #007bff;
                    border-radius: 5px;
                    padding: 20px;
                    font-size: 16px;
                    color: #007bff;
                    background-color: #3b3b3b;
                }
            """)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #666;
                border-radius: 5px;
                padding: 20px;
                font-size: 16px;
                color: #aaa;
                background-color: #2b2b2b;
            }
        """)

    def dropEvent(self, event):
        self.dragLeaveEvent(event)
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            files = [url.toLocalFile() for url in urls if url.isLocalFile()]
            if files:
                self.files_dropped.emit(files)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            try:
                # Get the parent window for proper modality
                parent_window = self.window()
                files, _ = QFileDialog.getOpenFileNames(
                    parent_window, 
                    _("file_dialog_title"), 
                    "", 
                    _("file_dialog_filter"),
                    options=QFileDialog.Option.DontUseNativeDialog
                )
                if files:
                    self.files_dropped.emit(files)
            except Exception as e:
                print(f"File dialog error: {e}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(700, 600)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Config Area
        config_layout = QVBoxLayout()
        
        self.acc_id_label = QLabel()
        self.acc_id_input = QLineEdit()
        config_layout.addWidget(self.acc_id_label)
        config_layout.addWidget(self.acc_id_input)

        self.ns_id_label = QLabel()
        self.ns_id_input = QLineEdit()
        config_layout.addWidget(self.ns_id_label)
        config_layout.addWidget(self.ns_id_input)

        self.token_label = QLabel()
        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        config_layout.addWidget(self.token_label)
        config_layout.addWidget(self.token_input)

        # Language Selector
        lang_layout = QHBoxLayout()
        self.lang_label = QLabel()
        lang_layout.addWidget(self.lang_label)
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("简体中文", "schinese")
        self.lang_combo.addItem("繁體中文", "tchinese")
        self.lang_combo.addItem("English", "english")
        self.lang_combo.addItem("Русский", "russian")
        self.lang_combo.addItem("Español", "spanish")
        self.lang_combo.addItem("日本語", "japanese")
        self.lang_combo.currentIndexChanged.connect(self.change_language)
        lang_layout.addWidget(self.lang_combo)
        config_layout.addLayout(lang_layout)

        self.save_btn = QPushButton()
        self.save_btn.clicked.connect(self.save_config)
        config_layout.addWidget(self.save_btn)
        
        layout.addLayout(config_layout)

        # Drag Drop Area
        self.drop_area = DragDropArea()
        self.drop_area.files_dropped.connect(self.process_files)
        layout.addWidget(self.drop_area)

        # Table Area for Editing
        self.table = QTableWidget(0, 2)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        
        # Log Area
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(100)
        layout.addWidget(self.log_output)

        # Upload Button
        self.upload_btn = QPushButton()
        self.upload_btn.setEnabled(False)
        self.upload_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745; 
                color: white; 
                font-weight: bold; 
                padding: 10px; 
                border-radius: 5px;
            }
            QPushButton:disabled {
                background-color: #333333;
                color: #888888;
                border: 1px solid #555555;
            }
        """)
        self.upload_btn.clicked.connect(self.start_upload)
        layout.addWidget(self.upload_btn)

        self.load_config()
        self.update_ui_texts()

    def update_ui_texts(self):
        self.setWindowTitle(_("window_title"))
        self.acc_id_label.setText(_("acc_id_label"))
        self.acc_id_input.setPlaceholderText(_("acc_id_placeholder"))
        self.ns_id_label.setText(_("ns_id_label"))
        self.ns_id_input.setPlaceholderText(_("ns_id_placeholder"))
        self.token_label.setText(_("token_label"))
        self.token_input.setPlaceholderText(_("token_placeholder"))
        self.lang_label.setText(_("lang_label"))
        self.save_btn.setText(_("save_btn"))
        self.drop_area.update_text()
        self.table.setHorizontalHeaderLabels([_("table_col_code"), _("table_col_name")])
        self.upload_btn.setText(_("upload_btn"))

    def change_language(self):
        global current_lang
        current_lang = self.lang_combo.currentData()
        self.update_ui_texts()

    def log(self, message):
        self.log_output.append(message)
        # scroll to bottom
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def load_config(self):
        global current_lang
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    self.acc_id_input.setText(config.get("account_id", ""))
                    self.ns_id_input.setText(config.get("namespace_id", ""))
                    self.token_input.setText(config.get("api_token", ""))
                    
                    lang = config.get("language", "schinese")
                    current_lang = lang
                    index = self.lang_combo.findData(lang)
                    if index >= 0:
                        self.lang_combo.setCurrentIndex(index)
            except Exception as e:
                self.log(f"{_('log_load_err')}: {e}")
        else:
            index = self.lang_combo.findData("schinese")
            if index >= 0:
                self.lang_combo.setCurrentIndex(index)

    def save_config(self):
        config = {
            "account_id": self.acc_id_input.text().strip(),
            "namespace_id": self.ns_id_input.text().strip(),
            "api_token": self.token_input.text().strip(),
            "language": self.lang_combo.currentData()
        }
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f)
            self.log(_("log_save_ok"))
        except Exception as e:
            self.log(f"{_('log_save_err')}: {e}")

    def process_files(self, files):
        self.log_output.clear()
        self.table.setRowCount(0)
        self.drop_area.setEnabled(False)
        self.upload_btn.setEnabled(False)
        
        self.worker = ParseThread(files)
        self.worker.log_signal.connect(self.log)
        self.worker.finished_signal.connect(self.on_parse_finished)
        self.worker.start()

    def on_parse_finished(self, results):
        self.drop_area.setEnabled(True)
        if not results:
            return
            
        self.table.setRowCount(len(results))
        for row, r in enumerate(results):
            key = r['map_code']
            value = f"{r['campaign_name']}: {r['chapter_name']} [{r['chapter_num']}/{r['total_chapters']}]"
            
            key_item = QTableWidgetItem(key)
            key_item.setFlags(key_item.flags() & ~Qt.ItemFlag.ItemIsEditable) # Read-only
            
            value_item = QTableWidgetItem(value)
            
            self.table.setItem(row, 0, key_item)
            self.table.setItem(row, 1, value_item)
            
        self.upload_btn.setEnabled(True)
        self.log(_("log_parse_done"))
        
    def start_upload(self):
        acc_id = self.acc_id_input.text().strip()
        ns_id = self.ns_id_input.text().strip()
        token = self.token_input.text().strip()

        if not acc_id or not ns_id or not token:
            QMessageBox.warning(self, _("msg_missing_title"), _("msg_missing_config"))
            return
            
        if self.table.rowCount() == 0:
            return
            
        kv_pairs = {}
        for row in range(self.table.rowCount()):
            key = self.table.item(row, 0).text()
            value = self.table.item(row, 1).text()
            kv_pairs[key] = value
            
        self.upload_btn.setEnabled(False)
        self.table.setEnabled(False)
        self.log(f"{_('log_uploading')} {len(kv_pairs)} {_('log_records')}...")
        
        self.upload_worker = UploadThread(kv_pairs, acc_id, ns_id, token)
        self.upload_worker.log_signal.connect(self.log)
        self.upload_worker.finished_signal.connect(self.on_upload_finished)
        self.upload_worker.start()
        
    def on_upload_finished(self, success):
        self.upload_btn.setEnabled(True)
        self.table.setEnabled(True)
        if success:
            QMessageBox.information(self, _("msg_success_title"), _("msg_upload_success"))
            self.table.setRowCount(0) # Clear after successful upload
            self.upload_btn.setEnabled(False)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
