from dataclasses import asdict, dataclass
import json
import os
import pathlib
import sys
import time
import traceback
from typing import Dict, Optional
import uuid

import cv2
from fastapi import APIRouter, WebSocket
import numpy as np
from starlette.websockets import WebSocketDisconnect

# from loguru import logger

# 把当前文件所在目录的上2级路径加入到python path中
path_to_add = pathlib.Path(__file__).parent.parent.parent.parent.joinpath("web_service")
sys.path.append(str(path_to_add))
# logger.info("added path: {}", str(path_to_add))

# from models import PigCounterModel
# pig_counter = PigCounterModel()

router = APIRouter()
SEP = b"\n\n"

def now_str(): return time.strftime("%Y%m%d%H%M%S")


@dataclass
class SessionState:
    width: int = 640
    height: int = 360
    fps: int = 25
    started: bool = False               # 是否收到 START
    closed: bool = False                # 是否已手动关闭 socket（防止重复 close）

@dataclass
class Segment:
    index: int = 0
    starttime: Optional[str] = None   # 前端传来的 keyframe（例如 00:00:05.120）
    endtime: Optional[str] = None
    start_saved: Optional[int] = None # 段开始时全局 saved 的快照
    end_saved: Optional[int] = None   # 段结束时全局 saved 的快照
    count: int = 0                    # 本段内猪只数量


def frames_to_video(frames_dir: pathlib.Path, output_path: str, fps: int = 25):
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


async def _send_ok(ws: WebSocket, **payload):
    await ws.send_text(json.dumps({"ok": True, **payload}, ensure_ascii=False))

async def _send_err(ws: WebSocket, state: SessionState, error: str, code: str = "bad_request", fatal: bool = False, **extra):
    await ws.send_text(json.dumps({"ok": False, "error": error, "code": code, **extra}, ensure_ascii=False))
    if fatal:
        await _close_ws(ws, state, error)

async def _close_ws(ws: WebSocket, state: SessionState, error: str = ""):
    if not state.closed:
        try:
            await ws.close(reason=error)
        except Exception:
            pass
        state.closed = True

@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()

    base = pathlib.Path("static") / "frames"
    sn = (ws.query_params.get("sn") if hasattr(ws, "query_params") else None) or "session"
    session_dir = base / f"{sn}-{now_str()}"
    session_dir.mkdir(parents=True, exist_ok=True)

    state = SessionState()
    saved = 0
    segments: Dict[int, Segment] = {}  # 用 index 做 key，更稳
    active_segment_idx: Optional[int] = None  # 当前处于“开始且未结束”的段

    try:
        while True:
            try:
                msg = await ws.receive()
            except WebSocketDisconnect:
                # 客户端主动断开
                break

            if msg.get("type") == "websocket.disconnect":
                break
            
            # ---------- 文本消息 ----------
            if msg.get("text") is not None:
                txt = msg["text"]
                data = json.loads(txt)
                msg_type = data.get('type') 

                # 前端传来的开始消息及 config 参数
                if msg_type == "START":
                    config = data.get("config", {})
                    missing = [k for k in ("width", "height", "fps") if k not in config]
                    if missing:
                        await _send_err(ws, state, f"config参数缺失: {','.join(missing)}", code="config_missing", fatal=True)
                        break

                    try:
                        state.width = int(config.get("width", 640))
                        state.height = int(config.get("height", 360))
                        state.fps = int(config.get("fps", 25))
                        state.started = True
                    except Exception as e:
                        await _send_err(ws, state, f"config参数非法: {e}", code="config_invalid", fatal=True)
                        break

                    await _send_ok(ws, status="started")
                    continue
                
                # 前端传来保存信号，合成视频，返回视频及分段结果
                if msg_type == "SAVE":
                    # 合成视频
                    video_path = str(session_dir / f"all.mp4")
                    if not frames_to_video(session_dir, video_path, state.fps):
                        await _send_err(ws, state, "video合成失败或没有帧", code="video_failed")
                    else:
                        # 生成正确的视频URL路径
                        static_video_url = f"/static/frames/{os.path.basename(session_dir)}/all.mp4"
                        seg_list = [asdict(s) for s in sorted(segments.values(), key=lambda s: s.index)]
                        await _send_ok(ws, status="finished", video=static_video_url, segments=seg_list)
						
                        # output_path, plus_count, minus_count = await pig_counter.process_video(
                        #     input_video=video_path,
                        #     out_path=f"session_dir/{uuid.uuid4()}.mp4", # auto_generated
                        #     conf=0.2,
                        #     iou=0.5,
                        #     device="0",
                        #     class_id=None,
                        #     persist_ids=True,
                        #     # tracker=job_data["tracker"],
                        #     line_fraction=0.5,
                        #     count_mode='l2r',
                        # )

                        # await ws.send_text(json.dumps({"ok": True, "status": "finished", "video": output_path, "total_count": plus_count - minus_count}))

                        # logger.info("received: {}, processed: {}, plus_count: {}, minus_count:{}", video_path, output_path, plus_count, minus_count)
                    
                    # 不管成功失败，都关闭 socket
                    break

                # 前端传来分段开始信号，记录分段开始时间及帧索引
                if msg_type == "segmentStart":
                    idx = int(data.get("index", 0))
                    keyframe = data.get("keyframe")

                    seg = Segment(
                        index=idx,
                        starttime=keyframe,
                        start_saved=saved,
                    )
                    segments[idx] = seg
                    active_segment_idx = idx
                    await _send_ok(ws, type="segmentAck", event="start", segment=asdict(seg))
                    continue
                
                # 前端传来分段结束信号，记录分段结束时间及帧索引
                if msg_type == "segmentEnd":
                    idx = int(data.get("index", 0))
                    keyframe = data.get("keyframe")

                    seg = segments.get(idx)
                    if seg is None:
                        # 如果异常收到 end（没有 start），也创建一个空段避免报错
                        seg = Segment(index=idx)
                        segments[idx] = seg
                    seg.endtime = keyframe
                    seg.end_saved = saved

                    # 由模型计算猪只数量
                    seg.count = 0
                    
                    if active_segment_idx == idx:
                        active_segment_idx = None

                    await _send_ok(ws, type="segmentSummary", index=idx, segment=asdict(seg))
                    continue

                await _send_err(ws, state, f"unknown message type: {msg_type}", code="unknown_type")
                continue
            
            # ---------- 二进制帧 ----------
            if msg.get("bytes") is not None:
                # 二进制帧也必须等 START 之后才能收
                if not state.started:
                    await _send_err(ws, state, "请先发送 START 再推送帧", code="not_started")
                    continue

                data = msg["bytes"]
                i = data.find(SEP)
                if i < 0:
                    await _send_err(ws, "bad packet: no separator", code="bad_packet")
                    continue

                # 解析 header（可选）
                try:
                    header = json.loads(data[:i].decode("utf-8"))
                except Exception:
                    header = {}

                jpeg = data[i + len(SEP):]

                # 简单校验 JPEG 头
                if not (len(jpeg) >= 2 and jpeg[0] == 0xFF and jpeg[1] == 0xD8):
                    await _send_err(ws, state, "payload is not JPEG", code="not_jpeg")
                    continue
                    
                # # 使用 OpenCV 读取 JPEG 数据
                # # 将字节数据转换为 numpy 数组
                # nparr = np.frombuffer(jpeg, np.uint8)
                # # 解码图像
                # img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                # if img is not None:
                #     # 在这里可以对图像进行处理
                #     # 例如：获取图像尺寸
                #     height, width = img.shape[:2]
                #     print(f"Received image dimensions: {width}x{height}")

                # 文件名：优先用 seq，否则用自增；零填充方便排序
                seq = header.get("seq", saved)
                filename = session_dir / f"{int(seq):06d}.jpg"

                try:
                    with open(filename, "wb") as f:
                        f.write(jpeg)
                    saved += 1
                except Exception as e:
                    await _send_err(ws, state, f"写入帧失败: {e}", code="io_write_failed")
                    continue

                # 可选：每 N 帧回进度
                # if saved % 30 == 0:
                #     await _send_ok(ws, saved=saved)
                continue
    except Exception as e:
        await _send_err(ws, state, f"server error: {e}", code="server_error", fatal=True)

        print("ws fatal error:\n", traceback.format_exc())
    finally:
        await _close_ws(ws, state)

        print(f"saved {saved} frames -> {session_dir}")
