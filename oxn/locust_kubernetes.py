import os
import importlib
from importlib.machinery import ModuleSpec
import importlib.util
import logging
from jinja2 import Environment as JinjaEnvironment, FileSystemLoader

from locust import HttpUser, TaskSet, task
from locust.env import Environment
from locust.stats import stats_printer, stats_history
from locust.log import setup_logging

from .models.load_generator import BaseLoadGenerator
from .errors import LocustException, OxnException
from .kubernetes_orchestrator import KubernetesOrchestrator
from .models.orchestrator import Orchestrator
import oxn.utils as utils

from gevent import Greenlet
from gevent.pool import Group

import requests


from oxn.models import orchestrator

logger = logging.getLogger(__name__)


class LocustKubernetesLoadgenerator(BaseLoadGenerator):
    """
    Locust loader for oxn.
    This loads the locust file and either runs the load locally or deploys
    Kubernetes resources using dynamic templating (when a target is specified).
    """

    def __init__(self, orchestrator: KubernetesOrchestrator, config: dict):
        super().__init__(orchestrator, config)
        self.run_time: int = 0  # total desired run time (in seconds)
        self.locust_files = None  # list of locust file definitions (each is a dict with at least "path")
        self._read_config()
        self.greenlets = Group()

    def _read_config(self):
        """Read the load generation section of an experiment specification."""
        loadgen_section: dict = self.config["experiment"]["loadgen"]
        self.stages = loadgen_section.get("stages", None)
        self.run_time = int(utils.time_string_to_seconds(loadgen_section["run_time"]))
        self.locust_files = loadgen_section.get("locust_files", None)

        self.target = loadgen_section.get("target")

        self.max_users = loadgen_section.get("max_users", 100)
        self.spawn_rate = loadgen_section.get("spawn_rate", 10)

        # Default to local host if no target specified.
        self.base_address = "localhost"
        self.port = 8080

        if self.target:
            # When a target is provided, we expect the orchestrator to be a KubernetesOrchestrator.
            assert isinstance(self.orchestrator, KubernetesOrchestrator), \
                "Orchestrator must be KubernetesOrchestrator if target is specified"
            self.base_address = self.orchestrator.get_address_for_service(
                name=self.target["name"],
                namespace=self.target["namespace"]
            )
            self.port = self.target["port"]

        logger.info(f"Base address for load generation set to {self.base_address}:{self.port}")

        # In local mode, we create a Locust environment.
        if not self.target:
            self.env = Environment(user_classes=[], host=f"http://{self.base_address}:{self.port}")
            self.env.create_local_runner()

        # Load locust files locally (to register user classes) even if running in Kubernetes.
        for locust_file in self.locust_files or []:
            path = locust_file["path"]
            locust_module = self._load_locust_file(path)
            for user_class in dir(locust_module):
                user_class_instance = getattr(locust_module, user_class)
                if isinstance(user_class_instance, type) and issubclass(user_class_instance, HttpUser) \
                   and user_class_instance is not HttpUser:
                    if not self.target:
                        self.env.user_classes.append(user_class_instance)
                    logger.info(f"Added user class {user_class_instance.__name__} from {path}")

    def _load_locust_file(self, path):
        """Load a locust file from the specified path."""
        spec = importlib.util.spec_from_file_location("locustfile", path)
        if not spec:
            raise LocustException(f"Could not load locust file from {path}")
        assert isinstance(spec, ModuleSpec)
        assert spec.loader is not None
        locustfile = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(locustfile)
        return locustfile

    def _generate_locustfile_content(self) -> str:
        """
        Generate the content for the locustfile. For simplicity, the content is taken from
        the first locust file provided. Extend this if merging multiple files is needed.
        """
        if self.locust_files and len(self.locust_files) > 0:
            path = self.locust_files[0]["path"]
            with open(path, "r") as f:
                return f.read()
        return ""

    
    def _generate_k8s_yaml(self) -> dict:
        """
        Generate Kubernetes YAML manifests using Jinja2 templates loaded from files.
        Returns a dict with keys for each YAML resource.
        """
        locustfile_content = self._generate_locustfile_content()

        # Define the directory containing the templates.
        templates_path = os.path.join(os.path.dirname(__file__), '../locust/kubernetes')
        jinja_env = JinjaEnvironment(loader=FileSystemLoader(templates_path), trim_blocks=True, lstrip_blocks=True)

        # Load each template file.
        configmap_template = jinja_env.get_template('configmap.yaml')
        master_template = jinja_env.get_template('master.yaml')
        worker_template = jinja_env.get_template('worker.yaml')
        service_template = jinja_env.get_template('service.yaml')

        # Render the templates with dynamic parameters.
        configmap_yaml = configmap_template.render(locustfile_content=locustfile_content)
        master_yaml = master_template.render(
            max_users=self.max_users,
            spawn_rate=self.spawn_rate,
            run_time=self.run_time,
            base_address=self.base_address,
            port=self.port
        )
        worker_yaml = worker_template.render(worker_replicas=2, master_host="locust-master")

        return {
            "configmap": configmap_yaml,
            "master": master_yaml,
            "worker": worker_yaml,
            "service": service_template.render()
        }

    def start(self):
        """Start the load generation or deploy the Kubernetes resources if target is specified."""
        setup_logging("INFO", None)

        if self.target:
            # Generate and deploy YAMLs on Kubernetes.
            self.resources = self._generate_k8s_yaml()
            # Assumes the orchestrator exposes a method `deploy_yaml(yaml_str)` to deploy a YAML manifest.
            self.orchestrator.deploy_configmap_yaml(self.resources["configmap"])
            self.orchestrator.deploy_deployment_yaml(self.resources["master"])
            self.orchestrator.deploy_deployment_yaml(self.resources["worker"])
            self.orchestrator.deploy_service_yaml(self.resources["service"])
            logger.info("Deployed locust master and worker pods on Kubernetes.")
        else:
            # Local runner mode.
            assert self.env is not None, "Locust environment must be initialized before starting"
            assert self.env.runner is not None, "Locust runner must be initialized before starting"
            self.env.runner.start(self.max_users, self.spawn_rate)
            self.greenlets.spawn(stats_printer(self.env.stats))
            self.greenlets.spawn(stats_history, self.env.runner)

        self.loadgen_start_time = utils.utc_timestamp()

    def stop(self):
        """Stop load generation or clean up Kubernetes resources."""
        if self.target:
            self.stats = self.get_stats_from_master()
            # Optionally, use the orchestrator to delete deployed resources.
            self.orchestrator.delete_configmap_yaml(self.resources["configmap"])
            self.orchestrator.delete_deployment_yaml(self.resources["master"])
            self.orchestrator.delete_deployment_yaml(self.resources["worker"])
            self.orchestrator.delete_service_yaml(self.resources["service"])
            logger.info("Cleaned up Kubernetes resources for the locust load test.")
        else:
            if self.env and self.env.runner:
                self.env.runner.quit()
                self.greenlets.join(timeout=30)  # Ensure no hanging threads.
                self.greenlets.kill()

        self.loadgen_stop_time = utils.utc_timestamp()

    def kill(self):
        """Kill all spawned greenlets and stop the runner if needed."""
        self.greenlets.kill()
        if self.env and self.env.runner:
            self.env.runner.quit()

    def get_stats_from_master(self):
        """Get the stats from the locust master."""
        if not self.target:
            return None
    
        # Get the master service's address.
        locust_master_address = self.orchestrator.get_address_for_service(
            name="locust-master",
            namespace=self.target["namespace"]
        )
        # Build the URL for the stats endpoint.
        url = f"http://{locust_master_address}:8089/stats/requests"
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            stats = response.json()  # Convert JSON response into Python dict.
            return stats
        except requests.RequestException as e:
            raise Exception(f"Error fetching stats from master: {e}")
