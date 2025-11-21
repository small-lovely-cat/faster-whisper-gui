from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from faster_whisper import WhisperModel
from opencc import OpenCC
import json
import os
import threading

class APIServer:
    def __init__(self, config):
        self.app = Flask(__name__)
        CORS(self.app)
        self.config = config
        self.model = None
        self.cc = OpenCC('t2s')
        self.server = None
        self.setup_routes()
        
    def setup_routes(self):
        @self.app.route('/transcribe', methods=['POST'])
        def transcribe():
            if 'file' not in request.files:
                return jsonify({'error': '未提供音频文件'}), 400
            
            file = request.files['file']
            model_size = request.form.get('model_size', 'small')
            language = request.form.get('language', 'zh')
            stream = request.form.get('stream', 'false').lower() == 'true'
            
            # 保存临时文件
            temp_path = f"temp_{file.filename}"
            file.save(temp_path)
            
            try:
                if stream:
                    return Response(
                        self._transcribe_stream(temp_path, model_size, language),
                        mimetype='text/event-stream'
                    )
                else:
                    result = self._transcribe_full(temp_path, model_size, language)
                    return jsonify(result)
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        
        @self.app.route('/health', methods=['GET'])
        def health():
            return jsonify({'status': 'ok'})
    
    def _load_model(self, model_size):
        if self.model is None:
            model_path = self.config.get('model_path')
            device = self.config.get('device', 'cpu')
            compute_type = self.config.get('compute_type', 'int8')
            
            if model_path and os.path.exists(model_path):
                hf_path = os.path.join(model_path, f"models--guillaumekln--faster-whisper-{model_size}")
                if os.path.isdir(hf_path):
                    os.environ["HF_HOME"] = model_path
                    self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
                else:
                    direct_path = os.path.join(model_path, model_size)
                    if os.path.isdir(direct_path):
                        self.model = WhisperModel(direct_path, device=device, compute_type=compute_type)
                    else:
                        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
            else:
                self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
    
    def _transcribe_stream(self, audio_path, model_size, language='zh'):
        self._load_model(model_size)
        segments, info = self.model.transcribe(audio_path, beam_size=5, language=language)
        
        for segment in segments:
            text = self.cc.convert(segment.text) if language == 'zh' and self.cc else segment.text
            data = {
                'start': segment.start,
                'end': segment.end,
                'text': text
            }
            yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
    
    def _transcribe_full(self, audio_path, model_size, language='zh'):
        self._load_model(model_size)
        segments, info = self.model.transcribe(audio_path, beam_size=5, language=language)
        
        results = []
        for segment in segments:
            text = self.cc.convert(segment.text) if language == 'zh' and self.cc else segment.text
            results.append({
                'start': segment.start,
                'end': segment.end,
                'text': text
            })
        
        return {
            'duration': info.duration,
            'language': info.language,
            'segments': results
        }
    
    def run(self, host='0.0.0.0', port=5000):
        from werkzeug.serving import make_server
        self.server = make_server(host, port, self.app, threaded=True)
        self.server.serve_forever()
    
    def start_background(self, host='0.0.0.0', port=5000):
        thread = threading.Thread(target=self.run, args=(host, port), daemon=True)
        thread.start()
        return thread
    
    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server = None