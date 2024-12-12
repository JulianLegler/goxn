from abc import ABC, abstractmethod
import logging
from typing import List
from locust.env import Environment

logger = logging.getLogger(__name__)

class BaseLoadGenerator(ABC):
    """Abstract base class for load generators"""

    def __init__(self, orchestrator, config):
        assert orchestrator is not None, "Orchestrator must not be None"
        self.orchestrator = orchestrator
        """A reference to the orchestrator instance"""
        assert config is not None, "Config must not be None"
        self.config = config
        """The experiment spec"""
        self.env = None
        """Locust environment"""
        self._read_config()

    @abstractmethod
    def _read_config(self):
        """Read the configuration and set up the environment"""
        pass

    @abstractmethod
    def start(self):
        """Start the load generation"""
        pass

    @abstractmethod
    def stop(self):
        """Stop the load generation"""
        pass

    @abstractmethod
    def kill(self):
        """Kill all associated processes"""
        pass
