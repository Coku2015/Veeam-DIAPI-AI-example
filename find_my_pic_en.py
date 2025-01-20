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

        if response_text.answer.lower() == "yes":
            log_message(f"The target was found - Answer: {response_text.answer}  Description: {response_text.description} Confidence: {response_text.confidence}")
        else:
            log_message(f"No target was found from the restore point")
            return response_text.answer, response_text.description, response_text.confidence
    except Exception as e:
        log_message(f"Error during image analysis: {e}")
        import traceback
        log_message(traceback.format_exc())
        return False, "Error occurred", 0       

def process_restore_point(info, config_data):
    photo_path = f"{info['mountPoint']}"
    # find photo in photo_path
    for filename in os.listdir(photo_path):
        if filename.endswith('.jpeg'):
            log_message(f"Analyzing photo: {filename} ...")
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
    log_message("Start Loading data from Archived Backups...")
    try:
        token = login_and_logout.get_access_token(config_data['vbr_server'], config_data['username'], config_data['password'])
        dp01 = DiskPublish(config_data['vbr_server'], config_data['target_server'], config_data['VM_name'], token, config_data['number_of_rp'])
        results = dp01.process_restore_point(config_data['target_path'])
        for info in results:
            log_message(f"Backup data loaded, Starting analysis:")
            log_message(f"VM name:{info['vmName']}, Backups name:{info['backupName']}, Restore point CreationTime:{info['creationTime']}")
            process_restore_point(info, config_data)
            log_message(f"Finished analysis, preparing next restore point...")
    except Exception as e:
        log_message(f"An error occurred: {e}")
    dp01.cleanup_mounts(results)
    login_and_logout.log_out(config_data['vbr_server'], token)
    endtime = time.time()
    duration = endtime - starttime
    log_message(f"Program finished, Running time:{duration}")
