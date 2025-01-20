from ollama import Client
from pydantic import BaseModel
from datetime import datetime
from colorama import Fore, Style
from disk_publish import DiskPublish
from config import Config
import login_and_logout
import time
import os

class Object(BaseModel):
    name: str
    attributes: str
    confidence: float

class ImageDescription(BaseModel):
    answer: str
    description: str
    confidence: float

def log_message(message):
    # 获取当前时间并格式化
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # 打印时间和信息
    print(f"{Fore.GREEN}[{current_time}]{Style.RESET_ALL} {message}")

def analyze_image(image_path, object_str):
    prompt_str = f"""Please analyze the image and answer the following questions:

1. Is there a {object_str} in the image?
2. If yes, describe its appearance and location in the image in detail.
3. If no, describe what you see in the image instead.
4. On a scale of 1-10, how confident are you in your answer?

Please structure your response as follows:
Answer: [YES/NO]
Description: [Your detailed description]
Confidence: [1-10]"""

    try:
        # 调用 llama 模型分析图像
        client = Client(host=config_data['ollama_host'])
        response = client.chat(
            model='llama3.2-vision',
            options={'temperature': 0},
            format=ImageDescription.model_json_schema(),
            messages=[
                {
                    'role': 'user',
                    'content': prompt_str,
                    'images': [image_path]
                }
            ]
        )
        time.sleep(1)  
        response_text = ImageDescription.model_validate_json(response.message.content)
        description_cn = localize_message(response_text.description)
        if response_text.answer.lower() == "yes":
            log_message(f"找到目标还原点 - 答案：是，描述：{description_cn.content} 置信度：{response_text.confidence}")
        else:
            log_message(f"未找到包含有效图片的目标还原点")
            return response_text.answer, response_text.description, response_text.confidence
    except Exception as e:
        log_message(f"Error during image analysis: {e}")
        import traceback
        log_message(traceback.format_exc())
        return False, "Error occurred", 0 

def localize_message(enstring):
    prompt_str = """
    请帮我翻译以下内容为中文：
     {enstring} 
    """
    try:
        localize = Client(host=config_data['ollama_host'])
        formatted_prompt_str = prompt_str.format(enstring=enstring)
        response = localize.chat(
            model='qwen2.5:7b',
            messages=[
                {
                    'role': 'user',
                    'content': formatted_prompt_str
                }
            ]
        )
        return response.message
    except Exception as e:
        return str(e)

def process_restore_point(info, config_data):
    photo_path = f"{info['mountPoint']}"
    # find photo in photo_path
    for filename in os.listdir(photo_path):
        if filename.endswith('.jpeg'):
            log_message(f"分析图像：{filename} 中...")
            filename = os.path.join(photo_path, filename)
            # 运行分析
            result = analyze_image(filename, config_data['object_to_find'])
            return result

# 主程序入口
if __name__ == "__main__":
    # 设置参数
    config = Config('config.json')
    config_data = config.get_config()
    starttime = time.time()
    log_message("开始加载来自 Veeam 的备份数据...")
    try:
        token = login_and_logout.get_access_token(config_data['vbr_server'], config_data['username'], config_data['password'])
        dp01 = DiskPublish(config_data['vbr_server'], config_data['target_server'], config_data['VM_name'], token, config_data['number_of_rp'])
        results = dp01.process_restore_point(config_data['target_path'])
        for info in results:
            log_message(f"备份数据加载成功。当前分析还原点：")
            log_message(f"机器名：{info['vmName']}, 备份存档名称：{info['backupName']}, 备份时间：{info['creationTime']}")
            process_restore_point(info, config_data)
            log_message(f"当前还原点分析完成，准备下一个还原点...")
    except Exception as e:
        log_message(f"An error occurred: {e}")
    dp01.cleanup_mounts(results)
    login_and_logout.log_out(config_data['vbr_server'], token)
    endtime = time.time()
    duration = endtime - starttime
    log_message(f"程序运行时间为{duration}秒")