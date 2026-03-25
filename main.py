import sys
import os
import json
import tempfile
import shutil
import zipfile
import py7zr
import rarfile
import concurrent.futures
import requests
import subprocess
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QTextEdit, QFileDialog, QMessageBox,
                             QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QDialog, QSplitter, QListWidget, QProgressBar)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from parser import parse_vpk
from cf_kv import CloudflareKV

VERSION = "v1.0.12"
CONFIG_FILE = "config.json"
REPO_API = "https://api.github.com/repos/winteroften/vpk_reader_KV_uploader/releases/latest"

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
        "log_records": "条记录",
        "update_found_title": "发现新版本",
        "update_found_msg": "检测到新版本: {version}\n\n更新内容:\n{body}\n\n请选择更新方式：",
        "update_direct": "GitHub 直连更新",
        "update_proxy1": "国内代理更新 (ghproxy)",
        "update_proxy2": "国内代理更新 (99988866)",
        "update_cancel": "暂不更新",
        "update_downloading": "正在下载更新...",
        "update_download_fail": "下载失败: {error}",
        "kv_manager_title": "Cloudflare KV 管理",
        "kv_manage_btn": "管理 KV 列表",
        "kv_refresh": "刷新列表",
        "kv_delete": "删除选中",
        "kv_save": "保存修改",
        "kv_key": "键 (Key)",
        "kv_value": "值 (Value)",
        "kv_loading": "正在加载...",
        "kv_load_err": "加载失败: {error}"
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
        "log_records": "records",
        "update_found_title": "New Version Available",
        "update_found_msg": "New version detected: {version}\n\nRelease notes:\n{body}\n\nPlease select an update method:",
        "update_direct": "GitHub Direct Update",
        "update_proxy1": "Proxy Update (ghproxy)",
        "update_proxy2": "Proxy Update (99988866)",
        "update_cancel": "Cancel",
        "update_downloading": "Downloading update...",
        "update_download_fail": "Download failed: {error}",
        "kv_manager_title": "Cloudflare KV Manager",
        "kv_manage_btn": "Manage KV",
        "kv_refresh": "Refresh List",
        "kv_delete": "Delete Selected",
        "kv_save": "Save Changes",
        "kv_key": "Key",
        "kv_value": "Value",
        "kv_loading": "Loading...",
        "kv_load_err": "Load failed: {error}"
    }
}

# Add fallback translations
for lang in ["russian", "spanish", "japanese", "tchinese"]:
    TRANSLATIONS[lang] = TRANSLATIONS.get(lang, TRANSLATIONS["english"].copy())
    TRANSLATIONS[lang].update(TRANSLATIONS.get("schinese" if lang == "tchinese" else "english"))

current_lang = "schinese"

def _(key):
    return TRANSLATIONS.get(current_lang, TRANSLATIONS["schinese"]).get(key, key)

class CheckUpdateThread(QThread):
    result_signal = pyqtSignal(bool, dict)
    
    def run(self):
        try:
            resp = requests.get(REPO_API, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                latest_version = data.get("tag_name", "")
                if latest_version and latest_version != VERSION:
                    self.result_signal.emit(True, data)
                    return
        except Exception:
            pass
        self.result_signal.emit(False, {})

class DownloadUpdateThread(QThread):
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, download_url):
        super().__init__()
        self.download_url = download_url

    def run(self):
        try:
            response = requests.get(self.download_url, stream=True, timeout=10)
            response.raise_for_status()
            total_length = int(response.headers.get('content-length', 0))
            
            temp_file = tempfile.mktemp(suffix=".exe")
            with open(temp_file, 'wb') as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_length > 0:
                            self.progress_signal.emit(int(downloaded * 100 / total_length))
            self.finished_signal.emit(temp_file)
        except Exception as e:
            self.error_signal.emit(str(e))

def apply_update(new_exe_path):
    if not getattr(sys, 'frozen', False):
        return
        
    current_exe = sys.executable
    bat_path = os.path.join(tempfile.gettempdir(), "update_l4d2_vpk.bat")
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(f"""@echo off
timeout /t 2 /nobreak > NUL
copy /y "{new_exe_path}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
""")
    subprocess.Popen(bat_path, creationflags=subprocess.CREATE_NO_WINDOW)
    QApplication.quit()

class UpdateDialog(QDialog):
    def __init__(self, parent, release_data):
        super().__init__(parent)
        self.setWindowTitle(_("update_found_title"))
        self.resize(450, 350)
        self.release_data = release_data
        
        layout = QVBoxLayout(self)
        version = release_data.get("tag_name", "")
        body = release_data.get("body", "")
        
        msg = _("update_found_msg").format(version=version, body=body)
        lbl = QLabel(msg)
        lbl.setWordWrap(True)
        layout.addWidget(lbl)
        
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        btn_layout = QVBoxLayout()
        
        self.btn_direct = QPushButton(_("update_direct"))
        self.btn_direct.clicked.connect(lambda: self.start_download("direct"))
        
        self.btn_proxy1 = QPushButton(_("update_proxy1"))
        self.btn_proxy1.clicked.connect(lambda: self.start_download("proxy1"))
        
        self.btn_proxy2 = QPushButton(_("update_proxy2"))
        self.btn_proxy2.clicked.connect(lambda: self.start_download("proxy2"))
        
        self.btn_cancel = QPushButton(_("update_cancel"))
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_direct)
        btn_layout.addWidget(self.btn_proxy1)
        btn_layout.addWidget(self.btn_proxy2)
        btn_layout.addWidget(self.btn_cancel)
        
        layout.addLayout(btn_layout)
        
    def start_download(self, mode):
        assets = self.release_data.get("assets", [])
        if not assets:
            return
        download_url = assets[0].get("browser_download_url", "")
        
        if mode == "proxy1":
            download_url = "https://mirror.ghproxy.com/" + download_url
        elif mode == "proxy2":
            download_url = "https://gh.api.99988866.xyz/" + download_url
            
        self.btn_direct.setEnabled(False)
        self.btn_proxy1.setEnabled(False)
        self.btn_proxy2.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        
        self.downloader = DownloadUpdateThread(download_url)
        self.downloader.progress_signal.connect(self.progress.setValue)
        self.downloader.finished_signal.connect(self.on_downloaded)
        self.downloader.error_signal.connect(self.on_error)
        self.downloader.start()
        
    def on_downloaded(self, filepath):
        self.accept()
        apply_update(filepath)
        
    def on_error(self, err):
        QMessageBox.warning(self, "Error", _("update_download_fail").format(error=err))
        self.reject()

class FetchKVKeysThread(QThread):
    result_signal = pyqtSignal(bool, list, str)
    def __init__(self, cf):
        super().__init__()
        self.cf = cf
    def run(self):
        success, res = self.cf.list_keys()
        if success:
            self.result_signal.emit(True, res, "")
        else:
            self.result_signal.emit(False, [], str(res))

class FetchKVValueThread(QThread):
    result_signal = pyqtSignal(bool, str, str)
    def __init__(self, cf, key):
        super().__init__()
        self.cf = cf
        self.key = key
    def run(self):
        success, res = self.cf.get_value(self.key)
        self.result_signal.emit(success, res, self.key)

class DeleteKVThread(QThread):
    result_signal = pyqtSignal(bool, str)
    def __init__(self, cf, key):
        super().__init__()
        self.cf = cf
        self.key = key
    def run(self):
        success, res = self.cf.delete_key(self.key)
        self.result_signal.emit(success, self.key)

class KVManagerDialog(QDialog):
    def __init__(self, parent=None, cf=None):
        super().__init__(parent)
        self.cf = cf
        self.resize(600, 400)
        self.setWindowTitle(_("kv_manager_title"))
        
        layout = QVBoxLayout(self)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(self.on_item_changed)
        splitter.addWidget(self.list_widget)
        
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0,0,0,0)
        
        self.value_edit = QTextEdit()
        right_layout.addWidget(self.value_edit)
        
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton(_("kv_save"))
        self.save_btn.clicked.connect(self.on_save)
        self.delete_btn = QPushButton(_("kv_delete"))
        self.delete_btn.setStyleSheet("background-color: #dc3545; color: white; border-radius: 3px; padding: 5px;")
        self.delete_btn.clicked.connect(self.on_delete)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.delete_btn)
        right_layout.addLayout(btn_layout)
        
        splitter.addWidget(right_widget)
        layout.addWidget(splitter)
        
        bottom_layout = QHBoxLayout()
        self.refresh_btn = QPushButton(_("kv_refresh"))
        self.refresh_btn.clicked.connect(self.refresh_list)
        bottom_layout.addWidget(self.refresh_btn)
        bottom_layout.addStretch()
        layout.addLayout(bottom_layout)
        
        self.refresh_list()
        
    def refresh_list(self):
        self.list_widget.clear()
        self.value_edit.clear()
        self.list_widget.addItem(_("kv_loading"))
        self.fetch_thread = FetchKVKeysThread(self.cf)
        self.fetch_thread.result_signal.connect(self.on_keys_fetched)
        self.fetch_thread.start()
        
    def on_keys_fetched(self, success, keys, error):
        self.list_widget.clear()
        if success:
            for k in keys:
                self.list_widget.addItem(k.get("name"))
        else:
            self.list_widget.addItem(_("kv_load_err").format(error=error))
            
    def on_item_changed(self, current, previous):
        if current:
            key = current.text()
            if key == _("kv_loading") or key.startswith(_("kv_load_err").split(":")[0]):
                return
            self.value_edit.setPlainText(_("kv_loading"))
            self.val_thread = FetchKVValueThread(self.cf, key)
            self.val_thread.result_signal.connect(self.on_value_fetched)
            self.val_thread.start()
            
    def on_value_fetched(self, success, value, key):
        if self.list_widget.currentItem() and self.list_widget.currentItem().text() == key:
            if success:
                self.value_edit.setPlainText(value)
            else:
                self.value_edit.setPlainText(_("kv_load_err").format(error=value))
                
    def on_save(self):
        item = self.list_widget.currentItem()
        if not item: return
        key = item.text()
        value = self.value_edit.toPlainText()
        
        self.save_btn.setEnabled(False)
        self.save_thread = UploadThread({key: value}, self.cf.account_id, self.cf.namespace_id, self.cf.api_token)
        self.save_thread.finished_signal.connect(self.on_save_finished)
        self.save_thread.start()
        
    def on_save_finished(self, success):
        self.save_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, "OK", _("msg_upload_success"))
        else:
            QMessageBox.warning(self, "Error", "Failed to save")
        
    def on_delete(self):
        item = self.list_widget.currentItem()
        if not item: return
        key = item.text()
        
        self.delete_btn.setEnabled(False)
        self.del_thread = DeleteKVThread(self.cf, key)
        self.del_thread.result_signal.connect(self.on_deleted)
        self.del_thread.start()
        
    def on_deleted(self, success, key):
        self.delete_btn.setEnabled(True)
        if success:
            self.refresh_list()
        else:
            QMessageBox.warning(self, "Error", "Failed to delete")


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
            sub_dir = tempfile.mkdtemp(dir=base_temp_dir)
            vpks.extend(self.extract_and_find_vpks(file, sub_dir))
        else:
            self.log_signal.emit(f"{_('log_skip_file')}: {file}")
            return results

        for vpk_file in vpks:
            self.log_signal.emit(f"{_('log_parsing')} {os.path.basename(vpk_file)}...")
            try:
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
    clicked_signal = pyqtSignal()

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
        self.setCursor(Qt.CursorShape.PointingHandCursor)

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
            self.clicked_signal.emit()

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

        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton()
        self.save_btn.clicked.connect(self.save_config)
        self.kv_manage_btn = QPushButton()
        self.kv_manage_btn.clicked.connect(self.open_kv_manager)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.kv_manage_btn)
        config_layout.addLayout(btn_layout)

        layout.addLayout(config_layout)

        # Drag Drop Area
        self.drop_area = DragDropArea()
        self.drop_area.files_dropped.connect(self.process_files)
        self.drop_area.clicked_signal.connect(self.open_file_dialog)
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
        self.upload_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.upload_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                color: #ffffff;
                font-weight: bold;
                padding: 10px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 5px;
            }
            QPushButton:hover:!disabled {
                background-color: rgba(255, 255, 255, 0.2);
            }
            QPushButton:pressed:!disabled {
                background-color: rgba(255, 255, 255, 0.05);
            }
            QPushButton:disabled {
                background-color: rgba(255, 255, 255, 0.05);
                color: rgba(255, 255, 255, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)
        self.upload_btn.clicked.connect(self.start_upload)
        layout.addWidget(self.upload_btn)

        self.load_config()
        self.update_ui_texts()
        
        self.setFocus()
        
        # Check for updates if running as exe
        if getattr(sys, 'frozen', False):
            self.check_update_thread = CheckUpdateThread()
            self.check_update_thread.result_signal.connect(self.on_update_checked)
            self.check_update_thread.start()

    def on_update_checked(self, has_update, release_data):
        if has_update:
            dlg = UpdateDialog(self, release_data)
            dlg.exec()

    def open_kv_manager(self):
        acc_id = self.acc_id_input.text().strip()
        ns_id = self.ns_id_input.text().strip()
        token = self.token_input.text().strip()
        if not acc_id or not ns_id or not token:
            QMessageBox.warning(self, _("msg_missing_title"), _("msg_missing_config"))
            return
        cf = CloudflareKV(acc_id, ns_id, token)
        dlg = KVManagerDialog(self, cf)
        dlg.exec()

    def update_ui_texts(self):
        self.setWindowTitle(f"{_('window_title')} (v{VERSION})")
        self.acc_id_label.setText(_("acc_id_label"))
        self.acc_id_input.setPlaceholderText(_("acc_id_placeholder"))
        self.ns_id_label.setText(_("ns_id_label"))
        self.ns_id_input.setPlaceholderText(_("ns_id_placeholder"))
        self.token_label.setText(_("token_label"))
        self.token_input.setPlaceholderText(_("token_placeholder"))
        self.lang_label.setText(_("lang_label"))
        self.save_btn.setText(_("save_btn"))
        self.kv_manage_btn.setText(_("kv_manage_btn"))
        self.drop_area.update_text()
        self.table.setHorizontalHeaderLabels([_("table_col_code"), _("table_col_name")])
        self.upload_btn.setText(_("upload_btn"))

    def change_language(self):
        global current_lang
        current_lang = self.lang_combo.currentData()
        self.update_ui_texts()

    def open_file_dialog(self):
        try:
            files, selected_filter = QFileDialog.getOpenFileNames(
                self,
                _("file_dialog_title"),
                "",
                _("file_dialog_filter")
            )
            if files:
                self.process_files(files)
        except Exception as e:
            self.log(f"File dialog error: {e}")

    def log(self, message):
        self.log_output.append(message)
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
            key_item.setFlags(key_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

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
            self.acc_id_input.clearFocus()
            self.ns_id_input.clearFocus()
            self.token_input.clearFocus()

            QMessageBox.information(self, _("msg_success_title"), _("msg_upload_success"))
            self.table.setRowCount(0)
            self.upload_btn.setEnabled(False)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
