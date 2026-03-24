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

class ParseThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(list)

    def __init__(self, files, target_lang="schinese"):
        super().__init__()
        self.files = files
        self.target_lang = target_lang

    def extract_and_find_vpks(self, archive_path, temp_dir):
        vpks = []
        try:
            if zipfile.is_zipfile(archive_path):
                self.log_signal.emit(f"正在解压 zip: {os.path.basename(archive_path)}")
                with zipfile.ZipFile(archive_path, 'r') as zf:
                    zf.extractall(temp_dir)
            elif py7zr.is_7zfile(archive_path):
                self.log_signal.emit(f"正在解压 7z: {os.path.basename(archive_path)}")
                with py7zr.SevenZipFile(archive_path, mode='r') as z:
                    z.extractall(path=temp_dir)
            elif rarfile.is_rarfile(archive_path):
                self.log_signal.emit(f"正在解压 rar: {os.path.basename(archive_path)}")
                with rarfile.RarFile(archive_path) as rf:
                    rf.extractall(path=temp_dir)
            else:
                self.log_signal.emit(f"不支持的压缩包格式: {os.path.basename(archive_path)}")
                return vpks

            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.lower().endswith(".vpk"):
                        vpks.append(os.path.join(root, file))
        except Exception as e:
            self.log_signal.emit(f"解压失败 {archive_path}: {e}")
            
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
            self.log_signal.emit(f"跳过不支持的文件: {file}")
            return results
            
        for vpk_file in vpks:
            self.log_signal.emit(f"正在解析 {os.path.basename(vpk_file)}...")
            try:
                res = parse_vpk(vpk_file, target_lang=self.target_lang)
                if not res:
                    self.log_signal.emit(f"未在 {os.path.basename(vpk_file)} 中找到 mission 数据")
                else:
                    for r in res:
                        results.append(r)
                        self.log_signal.emit(f"提取成功: {r['map_code']} -> {r['campaign_name']}: {r['chapter_name']} [{r['chapter_num']}/{r['total_chapters']}]")
            except Exception as e:
                self.log_signal.emit(f"解析 {vpk_file} 时发生错误: {e}")
                
        return results

    def run(self):
        all_results = []
        temp_dir = tempfile.mkdtemp()
        
        try:
            if not self.files:
                self.log_signal.emit("未选择任何文件。")
                return

            # 并发执行，最大线程数4
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(self.process_file, f, temp_dir) for f in self.files]
                
                # 等待任务完成，设置 120 秒超时
                done, not_done = concurrent.futures.wait(futures, timeout=120)
                
                if not_done:
                    self.log_signal.emit("警告: 部分文件解析超时 (超过2分钟)！已取消剩余任务。")
                    for future in not_done:
                        future.cancel()
                
                for future in done:
                    try:
                        res = future.result()
                        all_results.extend(res)
                    except Exception as e:
                        self.log_signal.emit(f"处理文件时发生异常: {e}")

            if not all_results:
                self.log_signal.emit("未提取到任何数据。处理结束。")
                
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
                self.log_signal.emit(f"成功上传 {len(self.kv_pairs)} 条记录到 Cloudflare KV！")
            else:
                self.log_signal.emit(f"上传失败。API 返回信息: {response}")
            self.finished_signal.emit(success)
        except Exception as e:
            self.log_signal.emit(f"上传时发生异常: {e}")
            self.finished_signal.emit(False)

class DragDropArea(QLabel):
    files_dropped = pyqtSignal(list)

    def __init__(self):
        super().__init__("将 VPK/ZIP/RAR/7z 文件拖拽到此处\n或者点击选择文件")
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
            files, _ = QFileDialog.getOpenFileNames(self, "选择 VPK/压缩包 文件", "", "支持的文件 (*.vpk *.zip *.rar *.7z);;所有文件 (*.*)")
            if files:
                self.files_dropped.emit(files)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("求生之路2 VPK地图解析与 Cloudflare KV 上传工具")
        self.resize(700, 600)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Config Area
        config_layout = QVBoxLayout()
        
        self.acc_id_input = QLineEdit()
        self.acc_id_input.setPlaceholderText("在此输入 Cloudflare Account ID")
        config_layout.addWidget(QLabel("Account ID (账户ID):"))
        config_layout.addWidget(self.acc_id_input)

        self.ns_id_input = QLineEdit()
        self.ns_id_input.setPlaceholderText("在此输入 Cloudflare KV Namespace ID")
        config_layout.addWidget(QLabel("Namespace ID (命名空间ID):"))
        config_layout.addWidget(self.ns_id_input)

        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("在此输入 Cloudflare API Token")
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        config_layout.addWidget(QLabel("API Token (API令牌):"))
        config_layout.addWidget(self.token_input)

        # Language Selector
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("首选语言 (Language):"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("简体中文 (schinese)", "schinese")
        self.lang_combo.addItem("繁體中文 (tchinese)", "tchinese")
        self.lang_combo.addItem("English (english)", "english")
        self.lang_combo.addItem("Русский (russian)", "russian")
        self.lang_combo.addItem("Español (spanish)", "spanish")
        self.lang_combo.addItem("日本語 (japanese)", "japanese")
        lang_layout.addWidget(self.lang_combo)
        config_layout.addLayout(lang_layout)

        save_btn = QPushButton("保存配置")
        save_btn.clicked.connect(self.save_config)
        config_layout.addWidget(save_btn)
        
        layout.addLayout(config_layout)

        # Drag Drop Area
        self.drop_area = DragDropArea()
        self.drop_area.files_dropped.connect(self.process_files)
        layout.addWidget(self.drop_area)

        # Table Area for Editing
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["建图代码 (不可修改)", "显示名称 (可修改)"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        
        # Log Area
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(100)
        layout.addWidget(self.log_output)

        # Upload Button
        self.upload_btn = QPushButton("确认修改并上传")
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

    def log(self, message):
        self.log_output.append(message)
        # scroll to bottom
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    self.acc_id_input.setText(config.get("account_id", ""))
                    self.ns_id_input.setText(config.get("namespace_id", ""))
                    self.token_input.setText(config.get("api_token", ""))
                    
                    lang = config.get("language", "schinese")
                    index = self.lang_combo.findData(lang)
                    if index >= 0:
                        self.lang_combo.setCurrentIndex(index)
            except Exception as e:
                self.log(f"加载配置文件失败: {e}")
        else:
            # 默认设置为简体中文
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
            self.log("配置已保存。")
        except Exception as e:
            self.log(f"保存配置文件失败: {e}")

    def process_files(self, files):
        self.log_output.clear()
        self.table.setRowCount(0)
        self.drop_area.setEnabled(False)
        self.upload_btn.setEnabled(False)
        
        target_lang = self.lang_combo.currentData()
        
        self.worker = ParseThread(files, target_lang=target_lang)
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
        self.log("✅ 解析完成！请在上方表格中确认或修改名称，确认无误后点击【确认修改并上传】按钮。")
        
    def start_upload(self):
        acc_id = self.acc_id_input.text().strip()
        ns_id = self.ns_id_input.text().strip()
        token = self.token_input.text().strip()

        if not acc_id or not ns_id or not token:
            QMessageBox.warning(self, "缺少配置", "请输入 Cloudflare Account ID, Namespace ID 以及 API Token。")
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
        self.log(f"正在上传 {len(kv_pairs)} 条记录...")
        
        self.upload_worker = UploadThread(kv_pairs, acc_id, ns_id, token)
        self.upload_worker.log_signal.connect(self.log)
        self.upload_worker.finished_signal.connect(self.on_upload_finished)
        self.upload_worker.start()
        
    def on_upload_finished(self, success):
        self.upload_btn.setEnabled(True)
        self.table.setEnabled(True)
        if success:
            QMessageBox.information(self, "上传成功", "所有数据已成功上传至 Cloudflare KV！")
            self.table.setRowCount(0) # Clear after successful upload
            self.upload_btn.setEnabled(False)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
