from calendar import c
from typing import List
import requests

from kubernetes import client, config
from kubernetes.stream import stream
from kubernetes.client.exceptions import ApiException
from kubernetes.client.models.v1_deployment import V1Deployment
from kubernetes.client.models.v1_pod import V1Pod

from oxn.errors import OrchestratorException

# Constants
DEFAULT_STEERING_CONTAINER_PORT = 5000

class SteeringController:

    def __init__(self, kube_client: client.CoreV1Api, api_client: client.ApiClient, port: int = DEFAULT_STEERING_CONTAINER_PORT):
        self.kube_client = kube_client
        self.api_client = api_client
        self.steering_port = port

    def send_tc_add_network_delay(self, pod: V1Pod, interface: str, delay_time: str, jitter: str, correlation: str):
        command = f'tc qdisc add dev {interface} root netem delay {delay_time} {jitter} {correlation}'

        assert pod.status
        assert pod.status.pod_ip is not None

        pod_ip = pod.status.pod_ip
        pod_port = self.steering_port

        url = f'http://{pod_ip}:{pod_port}/tc'
        body = {'cmd': command}
        response = requests.post(url, json=body)

        if response.status_code != 200:
            raise ApiException(status=response.status_code, reason=response.reason)
        
        return response
    
    def send_tc_remove_network_delay(self, pod: V1Pod, interface: str):
            command = f'tc qdisc del dev {interface} root netem'
    
            assert pod.status
            assert pod.status.pod_ip is not None
    
            pod_ip = pod.status.pod_ip
            pod_port = self.steering_port
    
            url = f'http://{pod_ip}:{pod_port}/tc'
            body = {'cmd': command}
            response = requests.post(url, json=body)
    
            if response.status_code != 200:
                raise ApiException(status=response.status_code, reason=response.reason)
            
            return response
        
    def send_tc_add_network_loss(self, pod: V1Pod, interface: str, loss: str):
            command = f'tc qdisc add dev {interface} root netem loss random {loss}'
            
            assert pod.status
            assert pod.status.pod_ip is not None
    
            pod_ip = pod.status.pod_ip
            pod_port = self.steering_port
    
            url = f'http://{pod_ip}:{pod_port}/tc'
            body = {'cmd': command}
            response = requests.post(url, json=body)
    
            if response.status_code != 200:
                raise ApiException(status=response.status_code, reason=response.reason)
            
            return response
        
    def send_tc_remove_network_loss(self, pod: V1Pod, interface: str):
            command = f'tc qdisc del dev {interface} root netem'
    
            assert pod.status
            assert pod.status.pod_ip is not None
    
            pod_ip = pod.status.pod_ip
            pod_port = self.steering_port
    
            url = f'http://{pod_ip}:{pod_port}/tc'
            body = {'cmd': command}
            response = requests.post(url, json=body)
    
            if response.status_code != 200:
                raise ApiException(status=response.status_code, reason=response.reason)
            
            return response
        
    def send_tc_add_network_corruption(self, pod: V1Pod, interface: str, percentage: str, correlation: str):
            command = f'tc qdisc add dev {interface} root netem corrupt {percentage} {correlation}'
            
            assert pod.status
            assert pod.status.pod_ip is not None
    
            pod_ip = pod.status.pod_ip
            pod_port = self.steering_port
    
            url = f'http://{pod_ip}:{pod_port}/tc'
            body = {'cmd': command}
            response = requests.post(url, json=body)
    
            if response.status_code != 200:
                raise ApiException(status=response.status_code, reason=response.reason)
            
            return response
        
    def send_tc_remove_network_corruption(self, pod: V1Pod, interface: str):
            command = f'tc qdisc del dev {interface} root netem'
    
            assert pod.status
            assert pod.status.pod_ip is not None
    
            pod_ip = pod.status.pod_ip
            pod_port = self.steering_port
    
            url = f'http://{pod_ip}:{pod_port}/tc'
            body = {'cmd': command}
            response = requests.post(url, json=body)
    
            if response.status_code != 200:
                raise ApiException(status=response.status_code, reason=response.reason)
            
            return response

    def set_network_delay(self, pods: List[V1Pod], interface: str, delay_time: str, jitter: str, correlation: str):
        try:
            for pod in pods:
                self.send_tc_add_network_delay(pod, interface, delay_time, jitter, correlation)
        except OrchestratorException as e:
            raise OrchestratorException(f'Failed to set network delay: {e}')
        
        return True
    
    
    def remove_network_delay(self, pods: List[V1Pod], interface: str):
        try:
            for pod in pods:
                self.send_tc_remove_network_delay(pod, interface)
        except OrchestratorException as e:
            raise OrchestratorException(f'Failed to reset network delay: {e}')
        
        return True
        
    def set_network_loss(self, pods: List[V1Pod], interface: str, loss: str):
        try:
            for pod in pods:
                self.send_tc_add_network_loss(pod, interface, loss)
        except OrchestratorException as e:
            raise OrchestratorException(f'Failed to set network loss: {e}')
        
        return True
        
    def remove_network_loss(self, pods: List[V1Pod], interface: str):
        try:
            for pod in pods:
                self.send_tc_remove_network_delay(pod, interface)
        except OrchestratorException as e:
            raise OrchestratorException(f'Failed to reset network loss: {e}')
        
        return True
    
    def set_network_corruption(self, pods: List[V1Pod], interface: str, percentage, correlation):
        try:
            for pod in pods:
                self.send_tc_add_network_corruption(pod, interface, percentage, correlation)
        except OrchestratorException as e:
            raise OrchestratorException(f'Failed to set network corruption: {e}')
        
        return True
    
    def remove_network_corruption(self, pods: List[V1Pod], interface: str):
        try:
            for pod in pods:
                self.send_tc_remove_network_corruption(pod, interface)
        except OrchestratorException as e:
            raise OrchestratorException(f'Failed to reset network corruption: {e}')
        
        return True