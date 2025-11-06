import asyncio
import json
import cv2
import numpy as np
from datetime import datetime, timedelta
import websockets
from websockets.legacy.client import WebSocketClientProtocol
import time
import os
import argparse
from loguru import logger

class VideoSegmentClient:
    def __init__(self, uri: str, video_path: str, sn: str = "test_client"):
        self.uri = uri
        self.video_path = video_path
        self.sn = sn
        self.sep = b"\n\n"
        
    async def send_messages(self, websocket: WebSocketClientProtocol):
        """
        专门负责发送消息的协程
        """
        try:
            logger.info(f"Connected to server: {self.uri}")
            
            # 打开视频文件
            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                logger.info(f"Error: Cannot open video file {self.video_path}")
                return
            
            # 获取视频属性
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            logger.info(f"Video info: {width}x{height}, {fps}fps, {total_frames} frames")
            
            # 发送START消息
            start_msg = {
                "type": "START",
                "config": {
                    "width": width,
                    "height": height,
                    "fps": fps
                }
            }
            
            await websocket.send(json.dumps(start_msg))
            logger.info("Sent START message")
            
            # 读取并发送视频帧
            frame_count = 0
            segment_duration = 10  # 每个分段10秒
            frames_per_segment = fps * segment_duration
            current_segment = 0
            segment_start_time = time.time()
            
            # 发送第一个分段开始信号
            segment_start_msg = {
                "type": "segmentStart",
                "index": current_segment,
                "keyframe": "00:00:00.000"
            }
            await websocket.send(json.dumps(segment_start_msg))
            logger.info("Sent first segmentStart message")
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # 每隔一定帧数开始一个新的分段
                if frame_count > 0 and frame_count % frames_per_segment == 0:
                    # 结束当前分段
                    timestamp = str(timedelta(seconds=frame_count//fps))
                    segment_end_msg = {
                        "type": "segmentEnd",
                        "index": current_segment,
                        "keyframe": timestamp
                    }
                    await websocket.send(json.dumps(segment_end_msg))
                    logger.info(f"Sent segmentEnd {current_segment} message")
                    
                    # 等待服务器确认segmentEnd处理完成，避免发送过快
                    await asyncio.sleep(0.1)
                    
                    # 开始新分段
                    current_segment += 1
                    segment_start_msg = {
                        "type": "segmentStart",
                        "index": current_segment,
                        "keyframe": timestamp
                    }
                    await websocket.send(json.dumps(segment_start_msg))
                    logger.info(f"Sent segmentStart {current_segment} message")
                
                # 编码帧为JPEG
                success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if not success:
                    logger.info(f"Failed to encode frame {frame_count}")
                    continue
                
                # 构造带header的消息
                header = {
                    "seq": frame_count
                }
                header_bytes = json.dumps(header).encode('utf-8')
                message = header_bytes + self.sep + buffer.tobytes()
                
                # 发送帧数据
                await websocket.send(message)
                
                frame_count += 1
                
                # 控制发送速度，模拟实时流，并避免发送过快导致缓冲区溢出
                if frame_count % fps == 0:
                    elapsed = time.time() - segment_start_time
                    if elapsed < 1.0:
                        await asyncio.sleep(1.0 - elapsed)
                    segment_start_time = time.time()
                
                # 每发送一定数量的帧就短暂暂停，防止发送过快
                if frame_count % 10 == 0:
                    await asyncio.sleep(0.01)
                
                if frame_count % 30 == 0:
                    logger.info(f"Sent {frame_count} frames...")
            
            # 结束最后一个分段
            timestamp = str(timedelta(seconds=frame_count//fps))
            segment_end_msg = {
                "type": "segmentEnd",
                "index": current_segment,
                "keyframe": timestamp
            }
            await websocket.send(json.dumps(segment_end_msg))
            logger.info(f"Sent final segmentEnd {current_segment} message")
            
            # 发送SAVE消息
            save_msg = {
                "type": "SAVE"
            }
            await websocket.send(json.dumps(save_msg))
            logger.info("Sent SAVE message")
            
            cap.release()
            logger.info(f"Finished sending {frame_count} frames in {current_segment + 1} segments")
            
        except websockets.exceptions.ConnectionClosed:
            logger.info("Connection closed by server during send_messages")
        except Exception as e:
            logger.info(f"Error in send_messages: {e}")
            import traceback
            traceback.print_exc()

    async def receive_messages(self, websocket, stop_event):
        """
        专门负责接收消息的协程
        """
        try:
            while not stop_event.is_set():
                try:
                    response = await websocket.recv()
                    logger.info(f"Server response: {response}")
                    try:
                        data = json.loads(response)
                        # 检查是否是最终完成状态
                        if data.get("status") == "finished":
                            logger.info("a segment is finished")
                        elif data.get("status") == "Final":
                            logger.info("Video processing completed!")
                            stop_event.set()  # 设置停止事件
                            break
                        elif data.get("ok") is False:
                            logger.info(f"Server error: {data}")
                    except json.JSONDecodeError:
                        pass
                except asyncio.TimeoutError:
                    # 超时继续循环，检查是否应该停止
                    continue
                except websockets.exceptions.ConnectionClosed:
                    logger.info("Connection closed by server")
                    stop_event.set()
                    break
        except Exception as e:
            logger.info(f"Error in receive_messages: {e}")
            import traceback
            traceback.print_exc()

    async def send_video_segments(self):
        """
        分段发送视频到服务器，使用分离的发送和接收协程
        """
        try:
            # 连接到WebSocket服务器，增加ping间隔和超时时间
            async with websockets.connect(
                f"{self.uri}?sn={self.sn}",
                ping_interval=30,      # 增加ping间隔到30秒
                ping_timeout=30,       # 增加ping超时到30秒
                close_timeout=30       # 增加关闭超时到30秒
            ) as websocket:
                # 创建停止事件
                stop_event = asyncio.Event()
                
                # 创建发送和接收任务
                send_task = asyncio.create_task(self.send_messages(websocket))
                recv_task = asyncio.create_task(self.receive_messages(websocket, stop_event))
                
                # 等待发送任务完成
                await send_task
                
                # 等待接收任务完成或超时
                try:
                    await asyncio.wait_for(recv_task, timeout=1200.0)  # 最多等待120秒
                except asyncio.TimeoutError:
                    logger.info("Timeout waiting for server final response")
                    recv_task.cancel()
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("Connection closed by server")
        except Exception as e:
            logger.info(f"Error establishing connection: {e}")
            import traceback
            traceback.print_exc()

async def main():
    parser = argparse.ArgumentParser(description='Send video segments to WebSocket server')
    parser.add_argument('--uri', default='ws://81.69.43.175:8006/videoserver/ws', help='WebSocket server URI')
    parser.add_argument('--video', required=True, help='Path to video file')
    parser.add_argument('--sn', default='client_test', help='Session identifier')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.video):
        logger.info(f"Error: Video file {args.video} does not exist")
        return
    
    client = VideoSegmentClient(args.uri, args.video, args.sn)
    await client.send_video_segments()

if __name__ == "__main__":
    asyncio.run(main())