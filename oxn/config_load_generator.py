""" 
Purpose: Manages load generation for experiments.
Functionality: Uses locust to generate load on the services under experiment based on the configuration.
Connection: Called by the Engine to simulate load during experiments.
 """

import logging
from typing import List

import gevent
import locust
from locust import LoadTestShape
from locust import events
from locust.env import Environment

from .models.load_generator import BaseLoadGenerator
from oxn.kubernetes_orchestrator import KubernetesOrchestrator

from .models.orchestrator import Orchestrator
import oxn.utils as utils

logger = logging.getLogger(__name__)


class ConfigLoadGenerator(BaseLoadGenerator):
    """Customizable load generation using Locust"""

    def __init__(self, orchestrator: Orchestrator, config: dict):
        super().__init__(orchestrator, config)
        self.locust_tasks: List[LocustTask] = []
        self.shape_instance = None
        self.locust_class = None

    def _read_config(self):
        loadgen_section = self.config["experiment"]["loadgen"]
        self.stages = loadgen_section.get("stages", [])
        self.run_time = utils.time_string_to_seconds(loadgen_section["run_time"])
        self.target = loadgen_section.get("target")

        if self.target:
            self.base_address = self.orchestrator.get_address_for_service(
                self.target["label_selector"], self.target["label"], self.target["namespace"]
            )
            self.port = self.target["port"]

        self.locust_tasks = [LocustTask(**task) for task in loadgen_section["tasks"]]
        self.env = Environment(
            user_classes=[self._locust_factory()],
            shape_class=self._shape_factory() if self.stages else None,
            events=events,
        )

    def _locust_factory(self):
        class CustomLocust(locust.FastHttpUser):
            tasks = {task_factory(task): task.weight for task in self.locust_tasks}
            host = f"http://{self.base_address}:{self.port}"
            wait_time = locust.between(0.1, 1)

        return CustomLocust

    def _shape_factory(self):
        class CustomLoadTestShape(LoadTestShape):
            def tick(self):
                run_time = self.get_run_time()
                for stage in self.stages:
                    if run_time < stage["duration"]:
                        return stage["users"], stage["spawn_rate"]
                return None

        return CustomLoadTestShape()

    def start(self):
        runner = self.env.create_local_runner()
        if self.shape_instance:
            runner.start_shape()
        else:
            runner.start(user_count=1, spawn_rate=1)
        gevent.spawn_later(self.run_time, lambda: runner.quit())

    def stop(self):
        if self.env.runner:
            self.env.runner.greenlet.join()

    def kill(self):
        if self.env.runner:
            self.env.runner.greenlet.kill(block=True)


class LocustTask:
    """Class to hold locust task information"""

    def __init__(self, name="", endpoint="", verb="", weight=1, params=None):
        self.name = name
        """Optional name for the task"""
        self.endpoint = endpoint
        """HTTP endpoint to hit"""
        self.verb = verb
        """HTTP verb to use"""
        self.weight = weight
        """Weight parameter that indicates how likely the task is to excecute versus other tasks"""
        self.params = params
        """Optional JSON parameters to send with the request"""

    def __str__(self):
        return f"LocustTask(name={self.name}, verb={self.verb}, url={self.endpoint})"

    def __repr__(self):
        return self.__str__()


def task_get_factory(endpoint, params):
    """Factory for a task that represents a GET request"""

    def _locust_task(locust):
        locust.client.get(endpoint, json=params)

    return _locust_task


def task_post_factory(endpoint, params):
    """Factory for a task that represents a POST request with params"""

    def _locust_task(locust):
        locust.client.post(endpoint, json=params)

    return _locust_task


@events.request.add_listener
def _on_request(
        request_type,
        name,
        response_time,
        response_length,
        response,
        context,
        exception,
        start_time,
        url,
        **kwargs,
):
    """Event hook to log requests made by Locust"""
    logger.info(
        f"{request_type} {name} {response.status_code} {response_time} {context}"
    )
    if exception:
        logger.info(f"{request_type} {exception}")


def task_factory(task: LocustTask):
    """Factory to create simple locust tasks from a loadgen section in experiment spec"""
    verb = task.verb
    if verb == "get":
        return task_get_factory(endpoint=task.endpoint, params=task.params)
    if verb == "post":
        return task_post_factory(endpoint=task.endpoint, params=task.params)
