import os
import logging
import json

from tqdm import tqdm
from argparse import ArgumentParser
from model import YOLO
from label_studio_sdk.client import LabelStudio
from label_studio_ml.response import ModelResponse


LABEL_STUDIO_URL = os.getenv("LABEL_STUDIO_URL", "http://localhost:8080")
LABEL_STUDIO_API_KEY = os.getenv("LABEL_STUDIO_API_KEY", "your_api_key")
PROJECT_ID = os.getenv("LABEL_STUDIO_PROJECT_ID", "1")

logger = logging.getLogger(__name__)


def arg_parser():
    parser = ArgumentParser(description="YOLO client for Label Studio ML Backend")

    parser.add_argument(
        "--ls-url", type=str, default=LABEL_STUDIO_URL, help="Label Studio URL"
    )
    parser.add_argument(
        "--ls-api-key",
        type=str,
        default=LABEL_STUDIO_API_KEY,
        help="Label Studio API Key",
    )
    parser.add_argument(
        "--project", type=str, default="1", help="Label Studio Project ID"
    )
    parser.add_argument(
        "--tasks",
        type=str,
        default="tasks.json",
        help="Path to tasks JSON file with list of ids or task datas. Example: tasks.json\n"
        "String with ids separated by comma: if you provide task ids, "
        "task data will be downloaded automatically from the Label Studio instance. Example: 1,2,3",
    )
    return parser.parse_args()


class LabelStudioMLPredictor:
    def __init__(self, ls_url, ls_api_key):
        self.ls = LabelStudio(base_url=ls_url, api_key=ls_api_key)
        logger.info(f"Successfully connected to Label Studio: {ls_url}")

    def run(self, project, tasks):
        # initialize Label Studio SDK client
        ls = self.ls
        project = ls.projects.get(id=project)
        logger.info(f"Project is retrieved: {project.id}")

        tasks = self.prepare_tasks(ls, tasks)

        # load YOLO model
        # TODO: use get_all_classes_inherited_LabelStudioMLBase to detect model classes
        model = YOLO(project_id=project.id, label_config=project.label_config)
        logger.info(f"YOLO ML backend is created")

        # predict and send prediction to Label Studio
        for task in tqdm(tasks, desc="Predict tasks"):
            response = model.predict([task])
            predictions = self.postprocess_response(model, response, task)

            # send predictions to Label Studio
            for prediction in predictions:
                ls.predictions.create(
                    task=task["id"],
                    score=prediction.get("score", 0),
                    model_version=prediction.get("model_version", "none"),
                    result=prediction["result"],
                )

        logger.info("Model predictions are done!")

    @staticmethod
    def postprocess_response(model, response, task):
        if response is None:
            logger.warning(f"No predictions for task: {task}")
            return None

        # model returned ModelResponse
        if isinstance(response, ModelResponse):
            # check model version
            if not response.has_model_version():
                if model.model_version:
                    response.set_version(str(model.model_version))
            else:
                response.update_predictions_version()
            response = response.model_dump()
            predictions = response.get("predictions")
        # model returned list of dicts with predictions (old format)
        elif isinstance(response, list):
            predictions = response
        else:
            logger.error("No predictions generated by model")
            return None

        return predictions

    @staticmethod
    def prepare_tasks(ls, tasks):
        # get tasks
        if os.path.exists(tasks):
            with open(tasks) as f:
                tasks = json.load(f)
        else:
            tasks = tasks.split(",")
            tasks = [int(task) for task in tasks]
        assert isinstance(tasks, list), "Tasks should be a list"
        assert len(tasks) > 0, "'Task list can't be empty"
        logger.info(f"Detected {len(tasks)} tasks")
        # check task data
        if isinstance(tasks[0], dict):
            if "data" not in tasks[0] or "id" not in tasks[0]:
                raise ValueError("'data' and 'id' must be presented in all tasks")
        elif isinstance(tasks[0], int):
            # load tasks from Label Studio instance using SDK
            logger.info("Task loading from Label Studio instance ...")
            tasks = [
                {"id": task_id, "data": ls.tasks.get(task_id).data}
                for task_id in tqdm(tasks)
            ]
            logger.info("Task loading finished")
        else:
            raise ValueError(
                "Unknown task format: "
                "tasks should be a list of dicts (task data) or a list of task ids"
            )
        return tasks


if __name__ == "__main__":
    args = arg_parser()
    predictor = LabelStudioMLPredictor(args.ls_url, args.ls_api_key)
    predictor.run(args.project, args.tasks)
