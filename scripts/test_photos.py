import os
import requests
import pandas as pd
from datetime import datetime
from tqdm import tqdm  # 用于显示进度条

# 配置参数
API_URL = "http://ir.drwjsd.com:8000/predict"  # 接口地址
# 使用绝对路径并创建测试图片目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGE_FOLDER = os.path.join(BASE_DIR, "static", "frames", "client_test-20251104110538")
EXCEL_OUTPUT = f"接口调用结果_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"  # 输出Excel路径
SUPPORTED_FORMATS = ('.jpg', '.jpeg', '.png', '.bmp', '.gif')  # 支持的图片格式

def get_image_files(folder):
    """获取文件夹中所有支持的图片文件"""
    # 检查路径是否存在，如果不存在则创建
    if not os.path.exists(folder):
        print(f"路径 {folder} 不存在，正在创建...")
        os.makedirs(folder, exist_ok=True)
        # 创建一些测试图片文件（如果需要）
        for i in range(3):
            test_file = os.path.join(folder, f"test_image_{i}.jpg")
            with open(test_file, 'w') as f:
                f.write("This is a test image file")
        print(f"已创建测试目录和测试文件")
    
    image_files = []
    try:
        for filename in os.listdir(folder):
            if filename.lower().endswith(SUPPORTED_FORMATS):
                file_path = os.path.abspath(os.path.join(folder, filename))
                image_files.append((filename, file_path))
    except Exception as e:
        print(f"读取文件夹时出错: {str(e)}")
    return image_files

def call_predict_api(image_path):
    """调用预测接口，返回结果"""
    try:
        with open(image_path, 'rb') as f:
            files = {'file': f}  # 注意：接口使用的参数名是'file'（从截图中可知）
            response = requests.post(API_URL, files=files, timeout=30)
        
        # 检查响应状态
        if response.status_code == 200:
            return True, response.json()  # 成功返回结果
        else:
            return False, f"接口返回状态码：{response.status_code}"
    except Exception as e:
        return False, f"调用失败：{str(e)}"

def main():
    # 1. 获取所有图片文件
    image_files = get_image_files(IMAGE_FOLDER)
    if not image_files:
        print(f"在 {IMAGE_FOLDER} 中未找到任何图片文件，请检查路径或文件格式")
        return
    
    print(f"共发现 {len(image_files)} 个图片文件，开始调用接口...")
    
    # 2. 循环调用接口并记录结果
    results = []
    for filename, file_path in tqdm(image_files, desc="处理进度"):
        success, result = call_predict_api(file_path)
        # 整理结果（根据接口返回格式提取关键信息）
        if success:
            # 从返回的JSON中提取需要的字段（根据截图中的响应格式）
            result_str = f"标签: {result.get('label_name')}, 置信度: {result.get('confidence')}, 图片ID: {result.get('img_id')}"
        else:
            result_str = result  # 失败信息
        
        results.append({
            "图片文件名": filename,
            "图片路径": file_path,
            "接口调用结果": result_str,
            "是否成功": "成功" if success else "失败"
        })
    
    # 3. 导出到Excel
    df = pd.DataFrame(results)
    df.to_excel(EXCEL_OUTPUT, index=False)
    print(f"所有任务完成！结果已导出到：{os.path.abspath(EXCEL_OUTPUT)}")

if __name__ == "__main__":
    # 检查依赖并安装
    try:
        import pandas as pd
        from tqdm import tqdm
    except ImportError:
        print("正在安装所需依赖...")
        os.system("pip install pandas openpyxl tqdm requests")
    
    main()