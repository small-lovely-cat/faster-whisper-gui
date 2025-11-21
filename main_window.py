import sys
import os
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QFileDialog, QMessageBox, QApplication
from PyQt5.QtGui import QFont
from qfluentwidgets import (FluentWindow, PushButton, RadioButton, 
                          ComboBox, TextEdit, ProgressBar, setTheme, Theme, 
                          PrimaryPushButton, SubtitleLabel, setFont, FluentIcon, TitleLabel,
                          CardWidget, ScrollArea, NavigationItemPosition, InfoBar, InfoBarPosition)
from services.transcribe import TranscribeWorker, MultiTranscribeWorker
from services.api_server import APIServer
from opencc import OpenCC

class WhisperInterface(ScrollArea):
    recognition_started = pyqtSignal()
    recognition_finished = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('whisperInterface')  # 添加对象名称
        self.cc = OpenCC('t2s')
        self.is_recognizing = False
        self.audio_file = None

         # 设置样式表
        self.setStyleSheet("QWidget{background: transparent}")
        
        # 创建主Widget和布局
        self.main_widget = QWidget()
        self.main_layout = QVBoxLayout(self.main_widget)
        self.setWidget(self.main_widget)
        self.setWidgetResizable(True)

        self.title = TitleLabel('单条转写', self)
        self.main_layout.addWidget(self.title)
        self.main_layout.addSpacing(10)  # 添加间距
        
        # 顶部区域
        self.create_top_area()
        
        # 中间区域
        self.create_middle_area()
        
        # 底部区域
        self.create_bottom_area()
        
        # 信号连接
        self.setup_connections()

    def create_top_area(self):
        top_layout = QHBoxLayout()
        
        # 文件上传区域
        self.file_frame = CardWidget()
        file_layout = QVBoxLayout(self.file_frame)
        file_layout.setContentsMargins(20, 5, 20, 10)  # 设置边距
        self.file_frame.setMaximumHeight(120)  # 设置最大高度
        
        self.file_label = SubtitleLabel('文件选择', self.file_frame)
        self.file_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)  # 设置标签对齐方式
        
        self.file_button = PushButton(FluentIcon.FOLDER, '选择文件', self.file_frame)
        
        file_layout.addWidget(self.file_label)
        file_layout.addSpacing(10)  # 添加垂直间距
        file_layout.addWidget(self.file_button)
        file_layout.addStretch()  # 添加弹性空间
        
        # 模型和语言选择区域
        self.model_frame = CardWidget()
        model_layout = QVBoxLayout(self.model_frame)
        model_layout.setContentsMargins(20, 5, 20, 10)
        self.model_frame.setMaximumHeight(160)
        
        self.model_label = SubtitleLabel('模型选择', self.model_frame)
        self.model_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        self.small_radio = RadioButton('small: 最快，识别精度较低【模型大小约500MB】', self.model_frame)
        self.medium_radio = RadioButton('medium: 平衡速度与精度【模型大小约1GB】', self.model_frame)
        
        # 语言选择
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(SubtitleLabel('语言:', self.model_frame))
        self.language_combo = ComboBox(self.model_frame)
        self.language_combo.addItems(['中文', '英语', '日语'])
        self.language_combo.setCurrentIndex(0)
        lang_layout.addWidget(self.language_combo)
        lang_layout.addStretch()
        
        model_layout.addWidget(self.model_label)
        model_layout.addSpacing(10)
        model_layout.addWidget(self.small_radio)
        model_layout.addWidget(self.medium_radio)
        model_layout.addLayout(lang_layout)
        model_layout.addStretch()
        
        top_layout.addWidget(self.file_frame)
        top_layout.addWidget(self.model_frame)
        self.main_layout.addLayout(top_layout)

    def create_middle_area(self):
        # 中间控制区域
        control_layout = QHBoxLayout()
        
        # 识别按钮
        self.recognize_button = PrimaryPushButton('开始识别', self)
        self.recognize_button.setFixedWidth(200)  # 设置固定宽度

        # 添加弹性空间实现居中
        control_layout.addStretch(1)
        control_layout.addWidget(self.recognize_button)
        control_layout.addStretch(1)
        
        self.main_layout.addLayout(control_layout)
        
        # 文本显示区域
        self.result_text_edit = TextEdit(self)
        self.result_text_edit.setReadOnly(True)
        self.main_layout.addWidget(self.result_text_edit)

    def create_bottom_area(self):
        # 底部区域
        bottom_layout = QHBoxLayout()
        
        # 保存按钮
        self.save_button = PushButton(FluentIcon.SAVE, '保存结果', self)
        
        # 进度条
        self.progress_bar = ProgressBar(self)
        self.progress_bar.setFixedWidth(500)
        
        bottom_layout.addWidget(self.save_button)
        bottom_layout.addWidget(self.progress_bar)
        bottom_layout.addStretch()
        self.main_layout.addLayout(bottom_layout)

    def setup_connections(self):
        self.file_button.clicked.connect(self.select_file)
        self.recognize_button.clicked.connect(self.check_and_recognize)
        self.save_button.clicked.connect(self.save_result)

    def update_text_edit(self, text):
        self.result_text_edit.append(text)

    def update_progress_bar(self, progress):
        self.progress_bar.setValue(progress)

    def update_recognize_button(self, status):
        if status:
            self.recognize_button.setText('开始识别')
            self.is_recognizing = False

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择音频文件", "", "Audio files (*.wav *.mp3);;All files (*)")
        if file_path:
            self.audio_file = file_path
            self.file_button.setText(file_path.split('/')[-1])

    def check_and_recognize(self):
        try:
            if not self.audio_file:
                InfoBar.error(
                    title='错误',
                    content="请先选择音频文件",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    parent=self
                )
                return

            if self.small_radio.isChecked():
                model_size = "small"
            elif self.medium_radio.isChecked():
                model_size = "medium"
            else:
                InfoBar.error(
                    title='错误',
                    content="请选择模型",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    parent=self
                )
                return

            # 从主窗口获取设置界面的设备配置
            main_window = self.window()
            settings = main_window.settings_interface

            if not self.is_recognizing:
                self.is_recognizing = True
                self.recognition_started.emit()
                self.result_text_edit.clear()
                self.recognize_button.setText('停止识别')
                
                # 获取语言代码
                lang_map = {'中文': 'zh', '英语': 'en', '日语': 'ja'}
                language = lang_map[self.language_combo.currentText()]
                
                # 创建并配置转录线程
                self.transcribe_thread = TranscribeWorker(
                    model_size,
                    self.audio_file,
                    settings.device_type.currentText().lower(),
                    settings.compute_type.currentText(),
                    self,
                    language=language
                )
                
                # 连接信号
                self.transcribe_thread.transcribe_signal.connect(self.update_text_edit)
                self.transcribe_thread.progress_signal.connect(self.update_progress_bar)
                self.transcribe_thread.complete_signal.connect(self.update_recognize_button)
                self.transcribe_thread.complete_signal.connect(lambda status: self.recognition_finished.emit())  # 添加完成信号连接
                
                # 开始转录
                self.transcribe_thread.start()
            else:
                # 停止转录
                if hasattr(self, 'transcribe_thread') and self.transcribe_thread is not None:
                    # 断开所有信号连接，防止后续信号导致问题
                    try:
                        self.transcribe_thread.transcribe_signal.disconnect()
                        self.transcribe_thread.progress_signal.disconnect()
                        self.transcribe_thread.complete_signal.disconnect()
                    except:
                        pass
                    
                    # 请求停止线程
                    self.transcribe_thread.stop()
                    
                    # 不强制等待线程结束，避免界面卡死
                    self.transcribe_thread = None
                
                self.is_recognizing = False
                self.recognition_finished.emit()  # 确保信号被发射
                self.recognize_button.setText('开始识别')

        except Exception as e:
            self.is_recognizing = False
            self.recognition_finished.emit()  # 确保信号被发射
            self.recognize_button.setText('开始识别')
            if hasattr(self, 'transcribe_thread') and self.transcribe_thread is not None:
                self.transcribe_thread.stop()
                self.transcribe_thread = None
                
            InfoBar.error(
                title='错误',
                content=str(e),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                parent=self
            )
    
    def save_result(self):
        if not self.result_text_edit.toPlainText():
            InfoBar.warning(
                title='警告',
                content="没有可保存的内容",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                parent=self
            )
            return
            
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, 
            "保存文件", 
            './', 
            "Text Files (*.txt);;Subtitle Files (*.srt);;All Files (*)"
        )
        
        if file_path:
            try:
                filtered_lines = [
                    line for line in self.result_text_edit.toPlainText().split('\n')
                    if line.strip() and 
                    "初次使用将下载模型" not in line and 
                    "模型下载完毕" not in line
                ]
                
                if file_path.endswith('.srt'):
                    with open(file_path, 'w', encoding='utf-8') as f:
                        counter = 1
                        for line in filtered_lines:
                            if line.strip() and '[' in line and ']' in line:
                                try:
                                    # 解析时间戳
                                    time_str = line[line.find('[')+1:line.find(']')]
                                    text = line[line.find(']')+1:].strip()
                                    
                                    # 移除's'并转换为浮点数
                                    start_time = float(time_str.split('->')[0].strip().replace('s', ''))
                                    end_time = float(time_str.split('->')[1].strip().replace('s', ''))
                                    
                                    # 转换为srt时间格式
                                    start = "{:02d}:{:02d}:{:02d},{:03d}".format(
                                        int(start_time // 3600),
                                        int((start_time % 3600) // 60),
                                        int(start_time % 60),
                                        int((start_time % 1) * 1000)
                                    )
                                    end = "{:02d}:{:02d}:{:02d},{:03d}".format(
                                        int(end_time // 3600),
                                        int((end_time % 3600) // 60),
                                        int(end_time % 60),
                                        int((end_time % 1) * 1000)
                                    )
                                    
                                    # 写入srt格式
                                    f.write(f"{counter}\n")
                                    f.write(f"{start} --> {end}\n")
                                    f.write(f"{text}\n\n")
                                    counter += 1
                                except ValueError as ve:
                                    continue  # 跳过无效的时间戳行
                else:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(filtered_lines))
                
                InfoBar.success(
                    title='成功',
                    content="文件保存成功！",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    parent=self
                )

            except Exception as e:
                InfoBar.error(
                    title='错误',
                    content=f"保存文件失败: {str(e)}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    parent=self
                )

class MultiwhisperInterface(ScrollArea):
    recognition_started = pyqtSignal()
    recognition_finished = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('multiwhisperInterface')
        self.cc = OpenCC('t2s')
        self.is_recognizing = False
        self.audio_files = []
        self.save_directory = None

        # 设置样式表
        self.setStyleSheet("QWidget{background: transparent}")
        
        # 创建主Widget和布局
        self.main_widget = QWidget()
        self.main_layout = QVBoxLayout(self.main_widget)
        self.setWidget(self.main_widget)
        self.setWidgetResizable(True)

        # 添加标题
        self.title = TitleLabel('多条转写(Beta)', self)
        self.main_layout.addWidget(self.title)
        self.main_layout.addSpacing(10)
        
        # 创建界面区域
        self.create_top_area()
        self.create_middle_area()
        self.create_bottom_area()
        
        # 信号连接
        self.setup_connections()

    def create_top_area(self):
        top_layout = QHBoxLayout()
        
        # 文件夹选择区域
        self.file_frame = CardWidget()
        file_layout = QVBoxLayout(self.file_frame)
        file_layout.setContentsMargins(16, 5, 16, 5)
        self.file_frame.setMaximumHeight(120)  # 设置最大高度
        
        self.file_label = SubtitleLabel('文件夹选择', self.file_frame)
        self.file_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        
        self.file_button = PushButton(FluentIcon.FOLDER, '选择文件夹', self.file_frame)
        
        file_layout.addWidget(self.file_label)
        file_layout.addSpacing(5)
        file_layout.addWidget(self.file_button)
        file_layout.addStretch()
        
        # 模型和语言选择区域
        self.model_frame = CardWidget()
        model_layout = QVBoxLayout(self.model_frame)
        model_layout.setContentsMargins(16, 5, 16, 5)
        self.model_frame.setMaximumHeight(160)
        
        self.model_label = SubtitleLabel('模型选择', self.model_frame)
        self.model_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        
        self.small_radio = RadioButton('small: 最快，识别精度较低【模型大小约500MB】', self.model_frame)
        self.medium_radio = RadioButton('medium: 平衡速度与精度【模型大小约1GB】', self.model_frame)
        
        # 语言选择
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(SubtitleLabel('语言:', self.model_frame))
        self.language_combo = ComboBox(self.model_frame)
        self.language_combo.addItems(['中文', '英语', '日语'])
        self.language_combo.setCurrentIndex(0)
        lang_layout.addWidget(self.language_combo)
        lang_layout.addStretch()
        
        model_layout.addWidget(self.model_label)
        model_layout.addSpacing(5)
        model_layout.addWidget(self.small_radio)
        model_layout.addWidget(self.medium_radio)
        model_layout.addLayout(lang_layout)
        model_layout.addStretch()
        
        top_layout.addWidget(self.file_frame)
        top_layout.addWidget(self.model_frame)
        self.main_layout.addLayout(top_layout)

    def create_middle_area(self):
        # 中间控制区域
        control_layout = QHBoxLayout()
        
        # 识别按钮
        self.recognize_button = PrimaryPushButton('开始识别', self)
        self.recognize_button.setFixedWidth(200)

        control_layout.addStretch(1)
        control_layout.addWidget(self.recognize_button)
        control_layout.addStretch(1)
        
        self.main_layout.addLayout(control_layout)
        
        # 文本显示区域
        self.result_text_edit = TextEdit(self)
        self.result_text_edit.setReadOnly(True)
        self.main_layout.addWidget(self.result_text_edit)

    def create_bottom_area(self):
        bottom_layout = QHBoxLayout()
        
        # 保存按钮
        self.save_button = PushButton(FluentIcon.SAVE, '保存结果(*转写完毕会自动保存)', self)
        
        # 进度条
        self.progress_bar = ProgressBar(self)
        self.progress_bar.setFixedWidth(300)
        
        bottom_layout.addWidget(self.save_button)
        bottom_layout.addWidget(self.progress_bar)
        bottom_layout.addStretch()
        self.main_layout.addLayout(bottom_layout)

    def setup_connections(self):
        self.file_button.clicked.connect(self.select_folder)
        self.recognize_button.clicked.connect(self.check_and_recognize)
        self.save_button.clicked.connect(self.save_result)

    def select_folder(self):
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "选择音频文件夹",
            "",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if folder_path:
            # 扫描文件夹中的音频文件
            audio_files = []
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.endswith(('.mp3', '.wav', '.m4a', '.flac')):
                        audio_files.append(os.path.join(root, file))
            
            if audio_files:
                self.audio_files = audio_files
                self.file_button.setText(f'已选择: {len(audio_files)}个音频文件')
                self.file_button.setToolTip('\n'.join(audio_files))
            else:
                InfoBar.warning(
                    title='警告',
                    content="所选文件夹中没有可识别的音频文件",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    parent=self
                )

    def update_text_edit(self, text):
        self.result_text_edit.append(text)

    def update_progress_bar(self, progress):
        self.progress_bar.setValue(progress)

    def update_recognize_button(self, status):
        if status:
            self.recognize_button.setText('开始识别')
            self.is_recognizing = False
    
    def auto_save_result(self, file_name):
        try:
            if not self.save_directory:
                self.save_directory = os.path.dirname(self.audio_files[0])
            
            # 构建输出文件路径
            base_name = os.path.splitext(os.path.basename(file_name))[0]
            save_path = os.path.join(self.save_directory, f"{base_name}.txt")
            
            # 获取当前文本并过滤
            text = self.result_text_edit.toPlainText()
            current_file_text = []
            is_current_file = False
            
            for line in text.split('\n'):
                if f"正在处理: {os.path.basename(file_name)}" in line:
                    is_current_file = True
                    continue
                elif "正在处理:" in line:
                    is_current_file = False
                elif is_current_file and line.strip():
                    current_file_text.append(line)
            
            # 保存文件
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(current_file_text))
                
            self.transcribe_signal.emit(f"\n已保存至: {save_path}\n")
            
        except Exception as e:
            InfoBar.error(
                title='保存失败',
                content=str(e),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                parent=self
            )

    def check_and_recognize(self):
        try:
            if not self.audio_files:
                InfoBar.error(
                    title='错误',
                    content="请先选择文件夹",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    parent=self
                )
                return

            if self.small_radio.isChecked():
                model_size = "small"
            elif self.medium_radio.isChecked():
                model_size = "medium"
            else:
                InfoBar.error(
                    title='错误',
                    content="请选择模型",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    parent=self
                )
                return

            # 从主窗口获取设置界面的设备配置
            main_window = self.window()
            settings = main_window.settings_interface

            if not self.is_recognizing:
                self.is_recognizing = True
                self.recognition_started.emit()
                self.result_text_edit.clear()
                self.recognize_button.setText('停止识别')
                
                # 获取语言代码
                lang_map = {'中文': 'zh', '英语': 'en', '日语': 'ja'}
                language = lang_map[self.language_combo.currentText()]
                
                # 创建并配置转录线程
                self.transcribe_thread = MultiTranscribeWorker(
                    model_size,
                    self.audio_files,
                    settings.device_type.currentText().lower(),
                    settings.compute_type.currentText(),
                    self,
                    language=language
                )
                
                # 连接信号
                self.transcribe_thread.transcribe_signal.connect(self.update_text_edit)
                self.transcribe_thread.progress_signal.connect(self.update_progress_bar)
                self.transcribe_thread.complete_signal.connect(self.update_recognize_button)
                self.transcribe_thread.file_complete_signal.connect(self.auto_save_result)  # 添加自动保存信号连接
                self.transcribe_thread.complete_signal.connect(lambda status: self.recognition_finished.emit())  # 添加完成信号连接
                
                # 开始转录
                self.transcribe_thread.start()
            else:
                # 停止转录
                if hasattr(self, 'transcribe_thread') and self.transcribe_thread is not None:
                    # 断开所有信号连接，防止后续信号导致问题
                    try:
                        self.transcribe_thread.transcribe_signal.disconnect()
                        self.transcribe_thread.progress_signal.disconnect()
                        self.transcribe_thread.complete_signal.disconnect()
                        self.transcribe_thread.file_complete_signal.disconnect()
                    except:
                        pass
                    
                    # 请求停止线程
                    self.transcribe_thread.stop()
                    
                    # 不强制等待线程结束，避免界面卡死
                    self.transcribe_thread = None
                
                self.is_recognizing = False
                self.recognition_finished.emit()  # 确保信号被发射
                self.recognize_button.setText('开始识别')

        except Exception as e:
            self.is_recognizing = False
            self.recognition_finished.emit()  # 确保信号被发射
            self.recognize_button.setText('开始识别')
            if hasattr(self, 'transcribe_thread') and self.transcribe_thread is not None:
                self.transcribe_thread.stop()
                self.transcribe_thread = None
            
            InfoBar.error(
                title='错误',
                content=str(e),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                parent=self
            )
    
    def save_result(self):
        if not self.result_text_edit.toPlainText():
            InfoBar.warning(
                title='警告',
                content="没有可保存的内容",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                parent=self
            )
            return
            
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, 
            "保存文件", 
            './', 
            "Text Files (*.txt);;Subtitle Files (*.srt);;All Files (*)"
        )
        
        if file_path:
            try:
                filtered_lines = [
                    line for line in self.result_text_edit.toPlainText().split('\n')
                    if line.strip() and 
                    "初次使用将下载模型" not in line and 
                    "模型下载完毕" not in line
                ]
                
                if file_path.endswith('.srt'):
                    with open(file_path, 'w', encoding='utf-8') as f:
                        counter = 1
                        for line in filtered_lines:
                            if line.strip() and '[' in line and ']' in line:
                                try:
                                    # 解析时间戳
                                    time_str = line[line.find('[')+1:line.find(']')]
                                    text = line[line.find(']')+1:].strip()
                                    
                                    # 移除's'并转换为浮点数
                                    start_time = float(time_str.split('->')[0].strip().replace('s', ''))
                                    end_time = float(time_str.split('->')[1].strip().replace('s', ''))
                                    
                                    # 转换为srt时间格式
                                    start = "{:02d}:{:02d}:{:02d},{:03d}".format(
                                        int(start_time // 3600),
                                        int((start_time % 3600) // 60),
                                        int(start_time % 60),
                                        int((start_time % 1) * 1000)
                                    )
                                    end = "{:02d}:{:02d}:{:02d},{:03d}".format(
                                        int(end_time // 3600),
                                        int((end_time % 3600) // 60),
                                        int(end_time % 60),
                                        int((end_time % 1) * 1000)
                                    )
                                    
                                    # 写入srt格式
                                    f.write(f"{counter}\n")
                                    f.write(f"{start} --> {end}\n")
                                    f.write(f"{text}\n\n")
                                    counter += 1
                                except ValueError as ve:
                                    continue  # 跳过无效的时间戳行
                else:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(filtered_lines))
                
                InfoBar.success(
                    title='成功',
                    content="文件保存成功！",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    parent=self
                )

            except Exception as e:
                InfoBar.error(
                    title='错误',
                    content=f"保存文件失败: {str(e)}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    parent=self
                )

class SettingsInterface(ScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('settingsInterface')

        # 设置样式表
        self.setStyleSheet("QWidget{background: transparent}")
        
        # 创建主Widget和布局
        self.main_widget = QWidget()
        self.main_layout = QVBoxLayout(self.main_widget)
        self.setWidget(self.main_widget)
        self.setWidgetResizable(True)

        self.title = TitleLabel('设置', self)
        self.main_layout.addWidget(self.title)
        self.main_layout.addSpacing(10)  # 添加间距
        
        # 设备设置
        device_frame = CardWidget()
        device_layout = QVBoxLayout(device_frame)
        
        self.device_type = ComboBox(device_frame)
        self.device_type.addItems(["CPU"])
        self.compute_type = ComboBox(device_frame)
        self.compute_type.addItems(["int8", "float32"])
        
        device_layout.addWidget(SubtitleLabel('设备设置', device_frame))
        device_layout.addWidget(self.device_type)
        device_layout.addWidget(self.compute_type)
        
        self.main_layout.addWidget(device_frame)
        
        # API设置
        api_frame = CardWidget()
        api_layout = QVBoxLayout(api_frame)
        
        api_layout.addWidget(SubtitleLabel('API设置', api_frame))
        
        # API启用开关
        from qfluentwidgets import SwitchButton, SpinBox
        self.api_enabled = SwitchButton(api_frame)
        api_enabled_layout = QHBoxLayout()
        api_enabled_layout.addWidget(SubtitleLabel('启用API服务', api_frame))
        api_enabled_layout.addWidget(self.api_enabled)
        api_enabled_layout.addStretch()
        api_layout.addLayout(api_enabled_layout)
        
        # API端口设置
        port_layout = QHBoxLayout()
        port_layout.addWidget(SubtitleLabel('API端口', api_frame))
        self.api_port = SpinBox(api_frame)
        self.api_port.setRange(1024, 65535)
        self.api_port.setValue(5000)
        port_layout.addWidget(self.api_port)
        port_layout.addStretch()
        api_layout.addLayout(port_layout)
        
        self.main_layout.addWidget(api_frame)
        
        # 模型设置
        model_frame = CardWidget()
        model_layout = QVBoxLayout(model_frame)
        
        model_layout.addWidget(SubtitleLabel('模型设置', model_frame))
        
        # 添加模型选择控件
        model_path_layout = QHBoxLayout()
        self.model_path_edit = TextEdit(model_frame)
        self.model_path_edit.setFixedHeight(35)  # 增加高度，避免文字裁切
        self.model_path_edit.setPlaceholderText("默认自动下载模型，若要使用本地模型请选择模型文件夹路径")
        self.model_path_button = PushButton(FluentIcon.FOLDER, '选择路径', model_frame)
        model_path_layout.addWidget(self.model_path_edit)
        model_path_layout.addWidget(self.model_path_button)
        
        # 添加模型路径检测按钮
        self.model_check_button = PrimaryPushButton('检测模型路径', model_frame)
        
        model_layout.addLayout(model_path_layout)
        model_layout.addWidget(self.model_check_button)
        
        self.main_layout.addWidget(model_frame)
        
        # 连接信号
        self.model_path_button.clicked.connect(self.select_model_path)
        self.model_check_button.clicked.connect(self.check_model_path)
        self.api_enabled.checkedChanged.connect(self.on_api_config_changed)
        self.api_port.valueChanged.connect(self.on_api_config_changed)
        
        # 检查配置文件中的模型路径和API设置
        self.load_model_path()
        self.load_api_config()
        
        self.main_layout.addStretch()

    def select_model_path(self):
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "选择模型文件夹",
            "",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        if folder_path:
            self.model_path_edit.setText(folder_path)
            self.save_model_path(folder_path)
    
    def save_model_path(self, path):
        # 保存模型路径到配置文件
        try:
            import json
            config = {}
            if os.path.exists("config.json"):
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
            
            config["model_path"] = path
            
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
                
            # 设置环境变量
            os.environ["HF_HOME"] = path
            
            InfoBar.success(
                title='成功',
                content="模型路径已保存",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                parent=self
            )
        except Exception as e:
            InfoBar.error(
                title='错误',
                content=f"保存配置失败: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                parent=self
            )
    
    def load_model_path(self):
        # 从配置文件加载模型路径
        try:
            import json
            if os.path.exists("config.json"):
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                
                if "model_path" in config:
                    self.model_path_edit.setText(config["model_path"])
                    os.environ["HF_HOME"] = config["model_path"]
        except Exception:
            pass  # 加载失败则使用默认路径
    
    def check_model_path(self):
        path = self.model_path_edit.toPlainText().strip()
        if not path:
            InfoBar.warning(
                title='警告',
                content="未设置模型路径，将使用默认路径",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                parent=self
            )
            return
            
        if not os.path.exists(path):
            InfoBar.error(
                title='错误',
                content="模型路径不存在",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                parent=self
            )
            return
        
        # 检测模型的可能路径
        models_found = []
        
        # 检查方式1: 直接检测是否有模型目录
        possible_model_sizes = ["small", "medium", "large", "large-v2"]
        
        for size in possible_model_sizes:
            # 检查Hugging Face缓存结构
            hf_path = os.path.join(path, f"models--guillaumekln--faster-whisper-{size}")
            if os.path.isdir(hf_path):
                models_found.append(f"{size} (Hugging Face缓存格式)")
                continue
                
            # 检查直接的模型目录
            direct_path = os.path.join(path, size)
            if os.path.isdir(direct_path):
                models_found.append(f"{size} (直接文件夹格式)")
                continue
                
            # 检查是否为模型文件自身
            if size in path.lower() and (path.endswith('.bin') or os.path.isdir(path)):
                models_found.append(f"{size} (单一模型文件)")
        
        # 检查方式2: 查找model.bin文件
        for root, dirs, files in os.walk(path):
            if "model.bin" in files:
                # 尝试从路径中推断模型大小
                path_lower = root.lower()
                for size in possible_model_sizes:
                    if size in path_lower and size not in [m.split(" ")[0] for m in models_found]:
                        models_found.append(f"{size} (包含model.bin)")
                        break
        
        if models_found:
            message = "检测到以下模型:\n"
            for model in models_found:
                message += f"- {model}\n"
                
            InfoBar.success(
                title='成功',
                content=message,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                parent=self
            )
        else:
            InfoBar.warning(
                title='警告',
                content="未检测到可用模型，将自动下载需要的模型",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                parent=self
            )
    
    def save_api_config(self):
        try:
            import json
            config = {}
            if os.path.exists("config.json"):
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
            
            config["api_enabled"] = self.api_enabled.isChecked()
            config["api_port"] = self.api_port.value()
            
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            InfoBar.error(
                title='错误',
                content=f"保存API配置失败: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                parent=self
            )
    
    def load_api_config(self):
        try:
            import json
            if os.path.exists("config.json"):
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                
                if "api_enabled" in config:
                    self.api_enabled.setChecked(config["api_enabled"])
                if "api_port" in config:
                    self.api_port.setValue(config["api_port"])
        except Exception:
            pass
    
    def on_api_config_changed(self):
        self.save_api_config()
        # 通知主窗口重启API服务
        main_window = self.window()
        if hasattr(main_window, 'restart_api_server'):
            main_window.restart_api_server()

class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        
        # 设置窗口属性
        self.setWindowTitle('语音转文字 - STT - Powered by Faster Whisper')
        self.resize(800, 600)
        
        # 设置主题
        setTheme(Theme.LIGHT)
        
        # API服务
        self.api_server = None
        self.api_thread = None
        
        # 创建并添加主界面
        self.whisper_interface = WhisperInterface(self)
        self.whisper_interface.setObjectName('whisperInterface')  # 设置对象名称
        self.multi_whisper_interface = MultiwhisperInterface(self)
        self.multi_whisper_interface.setObjectName('multiWhisperInterface')  # 设置对象名称
        self.settings_interface = SettingsInterface(self)
        self.settings_interface.setObjectName('settingsInterface')

        # 连接信号
        self.whisper_interface.recognition_started.connect(self.disable_navigation)
        self.whisper_interface.recognition_finished.connect(self.enable_navigation)
        # 添加多条转写界面的信号连接
        self.multi_whisper_interface.recognition_started.connect(self.disable_navigation)
        self.multi_whisper_interface.recognition_finished.connect(self.enable_navigation)

        self.addSubInterface(
            self.whisper_interface,
            FluentIcon.LABEL,
            '单条转写',
            position=NavigationItemPosition.TOP  # 设置导航位置
        )
        self.addSubInterface(
            self.multi_whisper_interface,
            FluentIcon.CAFE,
            '多条转写',
            position=NavigationItemPosition.TOP  # 设置导航位置
        )
        self.addSubInterface(
            self.settings_interface,
            FluentIcon.SETTING,
            '设置',
            position=NavigationItemPosition.TOP
        )
        
        # 启动API服务
        self.start_api_server()
    
    def start_api_server(self):
        try:
            import json
            if os.path.exists("config.json"):
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                
                if config.get("api_enabled", False):
                    api_config = {
                        'model_path': config.get('model_path'),
                        'device': self.settings_interface.device_type.currentText().lower(),
                        'compute_type': self.settings_interface.compute_type.currentText()
                    }
                    self.api_server = APIServer(api_config)
                    self.api_thread = self.api_server.start_background(
                        host=config.get('api_host', '0.0.0.0'),
                        port=config.get('api_port', 5000)
                    )
                    print(f"API服务已启动: {config.get('api_host', '0.0.0.0')}:{config.get('api_port', 5000)}")
        except Exception as e:
            print(f"启动API服务失败: {str(e)}")
    
    def restart_api_server(self):
        # 停止现有服务
        if self.api_server:
            print("正在停止API服务...")
            self.api_server.stop()
            self.api_server = None
            self.api_thread = None
        
        # 启动新服务
        self.start_api_server()
    
    def disable_navigation(self):
        # 禁用导航栏
        print("禁用导航栏")
        self.navigationInterface.setEnabled(False)
    
    def enable_navigation(self):
        # 启用导航栏
        print("启用导航栏") 
        self.navigationInterface.setEnabled(True)

if __name__ == '__main__':
    # 设置默认环境变量
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    os.environ["HF_HOME"] = "./models"
    
    # 读取配置文件
    try:
        import json
        if os.path.exists("config.json"):
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
            
            if "model_path" in config and os.path.exists(config["model_path"]):
                os.environ["HF_HOME"] = config["model_path"]
    except Exception as e:
        print(f"读取配置文件失败: {str(e)}")
    
    # 设置高DPI缩放
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    
    # 根据屏幕DPI设置基础字体大小
    font = app.font()
    font.setPointSize(10)  # 设置基础字体大小
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())