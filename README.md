## Faster Whisper GUI

一款运行在CPU上的本地语音转文字(TTS)的GUI工具。

## 功能介绍

- 支持单条转写/多条批量转写
- 支持两款模型
- 支持API调用(Beta)

<img width="798" height="597" alt="image" src="https://github.com/user-attachments/assets/d43d364d-2b36-46a0-a784-e716a1a37dad" />
<img width="800" height="592" alt="image" src="https://github.com/user-attachments/assets/3bb2e373-e826-4d32-bc85-45b95fdd6978" />


## 使用方法

1. 使用 `python -m venv ./venv`创建虚拟环境
2. Windows下使用 `cd .\venv\Scripts`定位到虚拟环境位置，`.\activate`激活虚拟环境，`cd ../../`回到项目目录；Linux下使用 `source ./venv/bin/activate`激活虚拟环境
3. 使用`pip install -r requirements.txt` 安装依赖
4. 使用`python main_window.py` 打开软件

## API使用方法

在设置中启用API服务，GET `127.0.0.1:5000/health`检测服务状态，POST `127.0.0.1:5000/transcribe`转录
API调用格式

|---|---|---|---|---|
|参数名|类型|必填|默认值|说明|
|file|File|是|-|音频文件|
|model_size|string|否|"small"|模型大小|
|language|string|否|"zh"|语言代码|
|stream|string|否|"false"|是否流式返回|

------
owo
