import os
import logging
import requests
import yaml
import torch
from dotenv import load_dotenv
from io import BytesIO
from PIL import Image
from label_studio_ml.model import LabelStudioMLBase
from label_studio_ml.response import ModelResponse
from label_studio_ml.utils import DATA_UNDEFINED_NAME,get_single_tag_keys
from label_studio_sdk._extensions.label_studio_tools.core.utils.io import get_local_path

# from control_models.base import ControlModel
# from control_models.choices import ChoicesModel
# from control_models.rectangle_labels import RectangleLabelsModel
# from control_models.rectangle_labels_obb import RectangleLabelsObbModel
# from control_models.polygon_labels import PolygonLabelsModel
# from control_models.keypoint_labels import KeypointLabelsModel
# from control_models.video_rectangle import VideoRectangleModel
# from control_models.timeline_labels import TimelineLabelsModel  # Not yet implemented completely
from typing import List, Dict, Optional
from ultralytics import YOLO as UltralyticsYOLO

is_loaded = load_dotenv()

# 检查是否成功加载
if is_loaded:
    print(".env 文件加载成功")
else:
    print(".env 文件加载失败或未找到")
    
env_model_dir = os.getenv("MODEL_DIR")
env_log_level = os.getenv('LOG_LEVEL')
env_label_studio_url = os.getenv('LABEL_STUDIO_URL')
env_model_version = os.getenv('MODEL_VERSION')
env_model_name = os.getenv('MODEL_NAME')
env_model_score_threshold = float(os.getenv('MODEL_SCORE_THRESHOLD'))
env_label_studio_api_key = os.getenv('LABEL_STUDIO_API_KEY')
    
print("=============================================")
print(f"LOG_LEVEL: {env_log_level}")
print(f"LABEL_STUDIO_URL: {env_label_studio_url}")
print(f"MODEL_VERSION: {env_model_version}")
print(f"MODEL_NAME: {env_model_name}")
print(f"MODEL_SCORE_THRESHOLD: {env_model_score_threshold}")
print(f"LABEL_STUDIO_API_KEY: {env_label_studio_api_key}")
print("=============================================")

logger = logging.getLogger(__name__)
if not os.getenv("LOG_LEVEL"):
    logger.setLevel(logging.INFO)


# Register available model classes
# available_model_classes = [
#     ChoicesModel,
#     RectangleLabelsModel,
#     RectangleLabelsObbModel,
#     PolygonLabelsModel,
#     KeypointLabelsModel,
#     VideoRectangleModel,
#     # TimelineLabelsModel, # Not yet implemented completely
# ]


class YOLO(LabelStudioMLBase):
    """Label Studio ML Backend based on Ultralytics YOLO"""

    def setup(self):
        """Configure any parameters of your model here"""
        self.set("model_version", env_model_version)
        
        from_name, schema = list(self.parsed_label_config.items())[0]
        self.from_name = from_name
        self.to_name = schema['to_name'][0]
        model_name = env_model_dir + '/' + env_model_name
        self.model = UltralyticsYOLO(model_name)
        if torch.cuda.is_available():
            self.model.to("cuda")
        self.model.to("cpu")
       # print(f'use device: {self.model.device}')
        self.labels = list(self.model.names.values())
        
    def predict(
        self, tasks: List[Dict], context: Optional[Dict] = None, **kwargs
    ) -> ModelResponse:
        """Run YOLO predictions on the tasks
        :param tasks: [Label Studio tasks in JSON format](https://labelstud.io/guide/task_format.html)
        :param context: [Label Studio context in JSON format](https://labelstud.io/guide/ml_create)
        :return model_response
            ModelResponse(predictions=predictions) with
            predictions [Predictions array in JSON format]
            (https://labelstud.io/guide/export.html#Label-Studio-JSON-format-of-annotated-tasks)
        """
        logger.info(
            f"Run prediction on {len(tasks)} tasks, project ID = {self.project_id}"
        )
        
        header = {
            "Authorization": "Token " + env_label_studio_api_key}
        
        all_predictions = []
        
        # 遍历所有任务
        for task in tasks:
            predictions = []  # 存储单个任务的预测结果
            score = 0

            # 获取图片并进行预测
            image = Image.open(BytesIO(requests.get(
                env_label_studio_url + task['data']['image'], headers=header).content))
            original_width, original_height = image.size
            results = self.model.predict(image, conf=env_model_score_threshold)

            # 处理每个预测框
            i = 0
            for result in results:
                for i, prediction in enumerate(result.boxes):
                    xyxy = prediction.xyxy[0].tolist()
                    predictions.append({
                        "id": str(i),
                        "from_name": self.from_name,
                        "to_name": self.to_name,
                        "type": "rectanglelabels",
                        "score": prediction.conf.item(),
                        "original_width": original_width,
                        "original_height": original_height,
                        "image_rotation": 0,
                        "value": {
                            "rotation": 0,
                            "x": xyxy[0] / original_width * 100, 
                            "y": xyxy[1] / original_height * 100,
                            "width": (xyxy[2] - xyxy[0]) / original_width * 100,
                            "height": (xyxy[3] - xyxy[1]) / original_height * 100,
                            "rectanglelabels": [self.labels[int(prediction.cls.item())]]
                        }
                    })
                    score += prediction.conf.item()
        
        # 计算该任务的平均分数
        avg_score = score / (i + 1) if i > 0 else 0
        
        # 构建该任务的最终预测结果
        task_prediction = {
            "result": predictions,
            "score": avg_score,
            "model_version": env_model_version,  # 使用模型版本标记预测结果
        }
        
        # 将该任务的预测结果添加到所有任务的预测列表中
        all_predictions.append(task_prediction)

        # 返回所有任务的预测结果
        return ModelResponse(predictions=all_predictions)

    def fit(self, event, data, **kwargs):
        """
        This method is called each time an annotation is created or updated
        You can run your logic here to update the model and persist it to the cache
        It is not recommended to perform long-running operations here, as it will block the main thread
        Instead, consider running a separate process or a thread (like RQ worker) to perform the training
        :param event: event type can be ('ANNOTATION_CREATED', 'ANNOTATION_UPDATED', 'START_TRAINING')
        :param data: the payload received from the event
        (check [Webhook event reference](https://labelstud.io/guide/webhook_reference.html))

        # use cache to retrieve the data from the previous fit() runs
        old_data = self.get('my_data')
        old_model_version = self.get('model_version')
        print(f'Old data: {old_data}')
        print(f'Old model version: {old_model_version}')

        # store new data to the cache
        self.set('my_data', 'my_new_data_value')
        self.set('model_version', 'my_new_model_version')
        print(f'New data: {self.get("my_data")}')
        print(f'New model version: {self.get("model_version")}')

        print('fit() is not implemented!')
        """
        raise NotImplementedError("Training is not implemented yet")
