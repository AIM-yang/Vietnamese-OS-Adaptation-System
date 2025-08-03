# Vietnamese-OS-Adaptation-System
项目介绍：
  该项目完成了越南语语音识别、翻译、合成、适配麒麟OS。
  支持语音识别、文本翻译和语音合成功能。
	用户可以上传音频文件进行越南语识别并翻译成中文，或者直接输入文本进行中越互译，并可以听到翻译结果的语音合成。

环境依赖 ：
	python3.9+
	所需的依赖库见 requirements.txt 文档

1.使用模型 ：
    	语音识别：faster-whisper，whisper-base-ct2-int8
    	翻译模型：nllb-200-distilled-600M
    	语音合成：edge-tts提供的语音合成服务

2.启动命令 ：
	后端：可以通过运行``main.py`` 文件来启动后端服务，使用uvicorn作为ASGI服务器。
	前端：打开index.html文件或打开index.html文件所处的文件夹，右键打开终端 执行：python3 -m http.server 8080

3.系统结构 ：
    后端：backend\
		dependencies.py ：加载模型和依赖
		main.py ： 主应用和API路由
		schemas.py ：数据模型定义

    前端：frontend
