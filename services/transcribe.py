from PyQt5.QtCore import QThread, pyqtSignal
from faster_whisper import WhisperModel
from opencc import OpenCC
import os

class TranscribeWorker(QThread):
    transcribe_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    complete_signal = pyqtSignal(bool)

    def __init__(self, model_size, audio_file, device, compute_type, parent=None, model_path=None, language='zh'):
        super().__init__(parent)
        self.model_size = model_size
        self.audio_file = audio_file
        self.device = device
        self.compute_type = compute_type
        self.model_path = model_path
        self.language = language
        self.running = True
        self.stop_requested = False
        self.model = None
        self.cc = OpenCC('t2s') if language == 'zh' else None

    def run(self):
        try:
            self.progress_signal.emit(0)
            self.transcribe_signal.emit("初次使用将下载模型，请耐心等待！\n")
            
            # 根据模型路径的不同情况选择合适的初始化方式
            if self.model_path:
                # 检查是否是具体的模型目录而不是缓存根目录
                model_path = self.model_path
                
                # 尝试检测具体的模型目录
                # 情况1: 是否为Hugging Face缓存格式
                hf_path = os.path.join(self.model_path, f"models--guillaumekln--faster-whisper-{self.model_size}")
                if os.path.isdir(hf_path):
                    self.transcribe_signal.emit(f"使用Hugging Face缓存模型: {self.model_size}\n")
                    # 使用环境变量方式
                    self.model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
                else:
                    # 情况2: 是否为直接的模型目录
                    direct_path = os.path.join(self.model_path, self.model_size)
                    if os.path.isdir(direct_path):
                        self.transcribe_signal.emit(f"使用本地模型: {direct_path}\n")
                        self.model = WhisperModel(direct_path, device=self.device, compute_type=self.compute_type)
                    # 情况3: 是否为模型自身
                    elif self.model_size in self.model_path.lower() and (
                            self.model_path.endswith('.bin') or os.path.isdir(self.model_path)):
                        self.transcribe_signal.emit(f"使用本地模型: {self.model_path}\n")
                        model_dir = self.model_path
                        if self.model_path.endswith('.bin'):
                            model_dir = os.path.dirname(self.model_path)
                        self.model = WhisperModel(model_dir, device=self.device, compute_type=self.compute_type)
                    else:
                        # 默认使用指定的模型大小
                        self.transcribe_signal.emit(f"使用默认模型: {self.model_size}\n")
                        self.model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
            else:
                # 无指定路径，使用默认下载
                self.model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
            
            self.transcribe_signal.emit("模型加载完毕，正在提取...\n")
            
            # 修改为实时流式处理
            segments, info = self.model.transcribe(self.audio_file, beam_size=5, language=self.language)
            
            # 不再需要预先转换为列表，直接处理迭代器
            segment_count = 0
            for segment in segments:
                if self.stop_requested:
                    break
                segment_count += 1
                text = self.cc.convert(segment.text) if self.cc else segment.text
                self.transcribe_signal.emit(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {text}\n")
                
                # 估算进度 - 由于无法预先知道总数，基于时间估算进度
                # 假设音频长度信息在 segment.end 可获取
                estimated_progress = min(int((segment.end / info.duration if info.duration > 0 else 1.0) * 100), 99)
                self.progress_signal.emit(estimated_progress)

            if not self.stop_requested:
                self.progress_signal.emit(100)
                self.complete_signal.emit(True)
                
        except Exception as e:
            self.transcribe_signal.emit(f"发生错误: {str(e)}\n")
            self.complete_signal.emit(False)

    def stop(self):
        """优雅停止线程"""
        self.stop_requested = True
        self.running = False

class MultiTranscribeWorker(QThread):
    transcribe_signal = pyqtSignal(str)  # 转录文本信号
    progress_signal = pyqtSignal(int)    # 总体进度信号
    file_progress_signal = pyqtSignal(int, str)  # 单文件进度信号 (进度, 文件名)
    complete_signal = pyqtSignal(bool)   # 完成信号
    file_complete_signal = pyqtSignal(str)  # 单文件完成信号

    def __init__(self, model_size, audio_files, device, compute_type, parent=None, model_path=None, language='zh'):
        super().__init__(parent)
        self.model_size = model_size
        self.audio_files = audio_files
        self.device = device
        self.compute_type = compute_type
        self.model_path = model_path
        self.language = language
        self.running = True
        self.stop_requested = False
        self.cc = OpenCC('t2s') if language == 'zh' else None
        self.model = None

    def run(self):
        try:
            self.progress_signal.emit(0)
            
            # 根据模型路径的不同情况选择合适的初始化方式
            if self.model_path:
                # 检查是否是具体的模型目录而不是缓存根目录
                model_path = self.model_path
                
                # 尝试检测具体的模型目录
                # 情况1: 是否为Hugging Face缓存格式
                hf_path = os.path.join(self.model_path, f"models--guillaumekln--faster-whisper-{self.model_size}")
                if os.path.isdir(hf_path):
                    self.transcribe_signal.emit(f"使用Hugging Face缓存模型: {self.model_size}\n")
                    # 使用环境变量方式
                    self.model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
                else:
                    # 情况2: 是否为直接的模型目录
                    direct_path = os.path.join(self.model_path, self.model_size)
                    if os.path.isdir(direct_path):
                        self.transcribe_signal.emit(f"使用本地模型: {direct_path}\n")
                        self.model = WhisperModel(direct_path, device=self.device, compute_type=self.compute_type)
                    # 情况3: 是否为模型自身
                    elif self.model_size in self.model_path.lower() and (
                            self.model_path.endswith('.bin') or os.path.isdir(self.model_path)):
                        self.transcribe_signal.emit(f"使用本地模型: {self.model_path}\n")
                        model_dir = self.model_path
                        if self.model_path.endswith('.bin'):
                            model_dir = os.path.dirname(self.model_path)
                        self.model = WhisperModel(model_dir, device=self.device, compute_type=self.compute_type)
                    else:
                        # 默认使用指定的模型大小
                        self.transcribe_signal.emit(f"使用默认模型: {self.model_size}\n")
                        self.model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
            else:
                # 无指定路径，使用默认下载
                self.model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
            
            total_files = len(self.audio_files)
            for file_index, audio_file in enumerate(self.audio_files):
                if self.stop_requested:
                    break
                
                # 发送当前处理文件信息
                current_file = os.path.basename(audio_file)
                self.transcribe_signal.emit(f"\n正在处理: {current_file}\n")
                self.file_progress_signal.emit(0, current_file)
                
                # 处理单个文件 - 修改为实时流式处理
                segments, info = self.model.transcribe(audio_file, beam_size=5, language=self.language)
                
                # 直接处理迭代器，不预先转换为列表
                for segment in segments:
                    if self.stop_requested:
                        break
                    # 根据语言决定是否转换
                    text = self.cc.convert(segment.text) if self.cc else segment.text
                    self.transcribe_signal.emit(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {text}\n")
                    
                    # 基于时间估算文件内进度
                    file_progress = min(int((segment.end / info.duration if info.duration > 0 else 1.0) * 100), 99)
                    self.file_progress_signal.emit(file_progress, current_file)
                
                # 文件处理完成后发送信号
                self.file_complete_signal.emit(audio_file)
                self.file_progress_signal.emit(100, current_file)
                
                # 更新总体进度
                total_progress = int((file_index + 1) / total_files * 100)
                self.progress_signal.emit(total_progress)
                
            if not self.stop_requested:
                self.progress_signal.emit(100)
                self.complete_signal.emit(True)
                
        except Exception as e:
            self.transcribe_signal.emit(f"发生错误: {str(e)}\n")
            self.complete_signal.emit(False)
        finally:
            self.running = False

    def stop(self):
        """优雅停止线程"""
        self.stop_requested = True
        self.running = False