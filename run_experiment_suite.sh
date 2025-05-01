#!/bin/bash
source venv/bin/activate

cleanup() {
    kubectl config set-context --current --namespace=system-under-evaluation
    helm uninstall astronomy-shop
    sleep 30
    kubectl config set-context --current --namespace=oxn-external-monitoring
    helm uninstall kube-prometheus
    kubectl config set-context --current --namespace=system-under-evaluation
    sleep 30
}

setup() {
    kubectl config set-context --current --namespace=oxn-external-monitoring
    helm install kube-prometheus prometheus-community/kube-prometheus-stack --namespace oxn-external-monitoring --create-namespace --version 62.5.1 -f values_kube_prometheus.yaml
    sleep 30
    kubectl config set-context --current --namespace=system-under-evaluation
    helm install astronomy-shop open-telemetry/opentelemetry-demo --namespace system-under-evaluation --create-namespace --version 0.36.4 -f values_opentelemetry_demo_persistence.yaml
    kubectl config set-context --current --namespace=system-under-evaluation
    sleep 60
}


cleanup
setup
python -m oxn experiments/recommendation_k8_base_1m_otel.yml --report reports/
sleep 60

#cleanup
#setup
#python -m oxn experiments/recommendation_k8_delay_1m_otel.yml --report reports/
#sleep 60

cleanup
setup
python -m oxn experiments/recommendation_k8_base_1s_otel.yml --report reports/
sleep 60

#cleanup
#setup
#python -m oxn experiments/recommendation_k8_delay_1s_otel.yml --report reports/
#sleep 60

cleanup
setup
python -m oxn experiments/recommendation_k8_base_5_percent.yml --report reports/
sleep 60

#cleanup
#setup
#python -m oxn experiments/recommendation_k8_delay_5_percent.yml --report reports/
#sleep 60

cleanup
setup
python -m oxn experiments/recommendation_k8_base_10_percent.yml --report reports/
sleep 60

#cleanup
#setup
#python -m oxn experiments/recommendation_k8_delay_10_percent.yml --report reports/
#sleep 60

cleanup
setup
python -m oxn experiments/recommendation_k8_base_50_percent.yml --report reports/
sleep 60
