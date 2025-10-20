import json
import pathlib
import time
import traceback
import cv2
import numpy as np
import os
from typing import List

from fastapi import APIRouter, WebSocket

router = APIRouter()
SEP = b"\n\n"

def now_str(): return time.strftime("%Y%m%d%H%M%S")

def frames_to_video(frames_dir: pathlib.Path, output_path: str, fps: int = 10):
    """将目录中的JPEG帧合成为MP4视频"""
    # 获取所有帧文件并按名称排序
    frame_files = sorted([f for f in frames_dir.iterdir() if f.suffix == '.jpg'], key=lambda x: x.name)
    
    if not frame_files:
        print(f"没有找到帧文件: {frames_dir}")
        return False
    
    # 读取第一帧以获取视频尺寸
    first_frame = cv2.imread(str(frame_files[0]))
    if first_frame is None:
        print(f"无法读取第一帧: {frame_files[0]}")
        return False
    
    height, width, layers = first_frame.shape
    
    # 创建VideoWriter对象
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # 使用MP4V编码器
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # 写入所有帧
    for frame_file in frame_files:
        frame = cv2.imread(str(frame_file))
        if frame is not None:
            out.write(frame)
        else:
            print(f"警告: 无法读取帧: {frame_file}")
    
    # 释放VideoWriter
    out.release()
    print(f"视频合成完成: {output_path}")
    return True


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()

    base = pathlib.Path("app") / "static" / "frames"
    sn = (ws.query_params.get("sn") if hasattr(ws, "query_params") else None) or "session"
    session_dir = base / f"{sn}-{now_str()}"
    session_dir.mkdir(parents=True, exist_ok=True)

    saved = 0

    try:
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                break
            
            if msg.get("text") is not None:
                txt = msg["text"]
                await ws.send_text(json.dumps({"ok": True, "echo": txt}))
                if json.loads(txt).get("type") == "FINISH":
                    # 合成视频
                    video_path = str(session_dir / f"all.mp4")
                    if not frames_to_video(session_dir, video_path):
                        await ws.send_text(json.dumps({"ok": False, "error": "video合成失败"}))
                        continue
                    else:
                        await ws.send_text(json.dumps({"ok": True, "video": video_path}))

            if msg.get("bytes") is not None:
                data = msg["bytes"]
                i = data.find(SEP)
                if i < 0:
                    await ws.send_text(json.dumps({"ok": False, "error": "bad packet: no separator"}))
                    continue

                # 解析 header（可选）
                try:
                    header = json.loads(data[:i].decode("utf-8"))
                except Exception:
                    header = {}

                jpeg = data[i + len(SEP):]

                # 简单校验 JPEG 头
                if not (len(jpeg) >= 2 and jpeg[0] == 0xFF and jpeg[1] == 0xD8):
                    await ws.send_text(json.dumps({"ok": False, "error": "payload is not JPEG"}))
                    continue

                # 文件名：优先用 seq，否则用自增；零填充方便排序
                seq = header.get("seq", saved)
                filename = session_dir / f"{int(seq):06d}.jpg"

                with open(filename, "wb") as f:
                    f.write(jpeg)

                saved += 1
                # 每 30 帧回个进度（可选）
                if saved % 30 == 0:
                    # await ws.send_text(json.dumps({"ok": True, "saved": saved}))
                    pass

                continue
    except Exception:
        print("ws fatal error:\n", traceback.format_exc())
    finally:
        await ws.close()
        print(f"saved {saved} frames -> {session_dir}")
