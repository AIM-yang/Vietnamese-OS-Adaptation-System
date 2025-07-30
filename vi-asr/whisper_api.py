from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from faster_whisper import WhisperModel
import time
import os
import tempfile
import logging
import json
import subprocess

# 配置日志，方便调试
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化FastAPI应用
app = FastAPI(title="语音识别API", description="基于Whisper的语音转文字服务")

# 配置CORS，允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，解决前端跨域问题
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有请求头
)

# 模型配置 - 请确保路径正确
MODEL_PATH = "/home/lym/桌面/越南语音识别/whisper-base-ct2-int8"
DEVICE = "cpu"
COMPUTE_TYPE = "int8"

# 加载模型（启动时加载一次）
try:
    model = WhisperModel(MODEL_PATH, device=DEVICE, compute_type=COMPUTE_TYPE)
    logger.info("模型加载成功")
except Exception as e:
    logger.error(f"模型加载失败: {str(e)}")
    raise RuntimeError(f"模型加载失败: {str(e)}")

@app.post("/transcribe", summary="语音转文字")
async def transcribe_audio(
    audio: UploadFile = File(..., description="待识别的音频文件（支持wav、mp3等格式）"),
    language: str = "vi",
    beam_size: int = 1  # 默认1，提升速度
):
    try:
        logger.info(f"收到音频文件: {audio.filename}, 语言: {language}, beam_size: {beam_size}")
        # 保存上传的临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio.filename)[1]) as temp_file:
            temp_file.write(await audio.read())
            temp_file_path = temp_file.name
            logger.info(f"临时文件保存至: {temp_file_path}")

        # 音频预处理：降采样为16kHz单声道
        processed_path = temp_file_path + "_16k.wav"
        cmd = [
            "ffmpeg", "-y", "-i", temp_file_path,
            "-ar", "16000", "-ac", "1", processed_path
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info(f"音频已降采样至: {processed_path}")

        # 开始计时
        start_time = time.time()

        # 识别：VAD切割
        segments, info = model.transcribe(
            processed_path,
            beam_size=beam_size,
            language=language,
            max_new_tokens=128,
            condition_on_previous_text=False,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=300),
        )
        # segments是生成器，转为list
        segments = list(segments)

        # 处理结果
        results = [
            {
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
                "text": seg.text
            } for seg in segments
        ]

        process_duration = time.time() - start_time
        logger.info(f"识别完成，处理时长: {process_duration:.2f}秒")

        result = {
            "language": info.language,
            "duration": round(info.duration, 2),
            "process_duration": round(process_duration, 2),
            "realtime_ratio": round(process_duration / info.duration, 2),
            "segments": results
        }

        # 删除临时文件
        os.unlink(temp_file_path)
        if os.path.exists(processed_path):
            os.unlink(processed_path)
        logger.info(f"临时文件已删除: {temp_file_path}, {processed_path}")

        return JSONResponse(content=result)

    except Exception as e:
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        if 'processed_path' in locals() and os.path.exists(processed_path):
            os.unlink(processed_path)
        logger.error(f"处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")

@app.post("/transcribe-stream", summary="语音转文字（流式输出）")
async def transcribe_audio_stream(
    audio: UploadFile = File(..., description="待识别的音频文件"),
    language: str = "vi",
    beam_size: int = 1,
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    try:
        logger.info(f"收到流式识别请求: {audio.filename}")
        
        # 保存并预处理音频
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio.filename)[1]) as temp_file:
            temp_file.write(await audio.read())
            temp_file_path = temp_file.name

        processed_path = temp_file_path + "_16k.wav"
        cmd = [
            "ffmpeg", "-y", "-i", temp_file_path,
            "-ar", "16000", "-ac", "1", processed_path
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # 定义清理临时文件的函数
        def cleanup():
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            if os.path.exists(processed_path):
                os.unlink(processed_path)
            logger.info("临时文件已清理")
        
        # 添加清理任务
        background_tasks.add_task(cleanup)

        # 定义生成器函数用于流式输出
        def generate():
            # 实时识别并逐段返回结果
            segments, info = model.transcribe(
                processed_path,
                beam_size=beam_size,
                language=language,
                max_new_tokens=128,
                condition_on_previous_text=False,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=300),
                word_timestamps=False  # 禁用词级时间戳提高速度
            )
            
            # 先发送元数据
            yield f"data: {json.dumps({
                'type': 'metadata',
                'language': info.language,
                'duration': round(info.duration, 2)
            })}\n\n"
            
            # 逐段发送识别结果
            for seg in segments:
                yield f"data: {json.dumps({
                    'type': 'segment',
                    'start': round(seg.start, 2),
                    'end': round(seg.end, 2),
                    'text': seg.text
                })}\n\n"
            
            # 发送结束标志
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        # 返回流式响应
        return StreamingResponse(
            generate(),
            media_type="text/event-stream"
        )

    except Exception as e:
        # 出错时清理临时文件
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        if 'processed_path' in locals() and os.path.exists(processed_path):
            os.unlink(processed_path)
        logger.error(f"流式处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")

@app.get("/health", summary="健康检查")
async def health_check():
    return {"status": "healthy", "message": "语音识别API运行正常", "timestamp": time.time()}

# 运行服务
if __name__ == "__main__":
    import uvicorn
    # 绑定0.0.0.0，允许外部访问
    uvicorn.run("whisper_api:app", host="0.0.0.0", port=8000, reload=True)