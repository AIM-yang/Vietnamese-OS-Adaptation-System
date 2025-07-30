# Vietnamese-OS-Adaptation-System
越南语语音识别文件夹

项目介绍：
	支持上传越南语音频（MP3、WAV等格式），自动识别并返回文本结果。
	提供流式识别接口，前端可实时显示识别进度。
	采用 FastAPI + faster-whisper，支持跨平台部署。

环境依赖：
	python3.9+
	所需的依赖库见 requirements.txt 文档

1.使用的模型 ：whisper-base-ct2-int8 
相关的测试数据   
  whisper_base 4.37s音频   处理时长  1.42s
  whisper_base 3.78s音频   处理时长  1.35s
  whisper_base 2.82s音频   处理时长  1.28s


2.模型转换命令   
  ct2-transformers-converter --model /path/whisper_【模型】 --output_dir 【whisper-base-ct2-int8（模型名称）】 --copy_files tokenizer.json preprocessor_config.json --quantization int8

3.启动命令
（1）修改模型路径，确保模型路径正确
 （2）打开index.html文件所处的文件夹，右键打开终端 执行：python3 -m http.server 8080

4.系统结构
  页面代码：web/index.html
  模型文件：whisper-base-ct2-int8
  主要代码：whisper_api.py 
