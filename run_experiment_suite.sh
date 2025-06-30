#!/bin/bash
source venv/bin/activate

cleanup() {
    kubectl config set-context --current --namespace=system-under-evaluation
    helm uninstall astronomy-shop
    sleep 30
    kubectl delete pvc data-astronomy-shop-elasticsearch-data-0
    kubectl delete pvc data-astronomy-shop-elasticsearch-data-1
    kubectl delete pvc data-astronomy-shop-elasticsearch-master-0
    kubectl delete pvc data-astronomy-shop-elasticsearch-master-1
    sleep 30
    kubectl config set-context --current --namespace=isto-system
    helm uninstall istio-base
    helm uninstall istiod
    helm uninstall istio-ingressgateway
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
    helm install astronomy-shop open-telemetry/opentelemetry-demo --namespace system-under-evaluation --create-namespace --version 0.36.4 -f values_opentelemetry_demo.yaml
    kubectl config set-context --current --namespace=system-under-evaluation
    sleep 60
}

setup_external_jaeger_backend() {
    kubectl config set-context --current --namespace=oxn-external-monitoring
    helm install kube-prometheus prometheus-community/kube-prometheus-stack --namespace oxn-external-monitoring --create-namespace --version 62.5.1 -f values_kube_prometheus.yaml
    sleep 30
    kubectl config set-context --current --namespace=system-under-evaluation
    helm install astronomy-shop open-telemetry/opentelemetry-demo --namespace system-under-evaluation --create-namespace --version 0.36.4 -f values_opentelemetry_demo_persistence.yaml
    kubectl config set-context --current --namespace=system-under-evaluation
    sleep 60
}

setup_external_jaeger_backend_istio() {
    kubectl config set-context --current --namespace=oxn-external-monitoring
    helm install kube-prometheus prometheus-community/kube-prometheus-stack --namespace oxn-external-monitoring --create-namespace --version 62.5.1 -f values_kube_prometheus.yaml
    sleep 30
    helm install istio-base istio/base --version 1.26.2 -n istio-system --set defaultRevision=default --create-namespace
    helm install istiod istio/istiod -n istio-system \
        --set global.proxy.autoInject=enabled \
        --set meshConfig.enablePrometheusMerge=true \
        --set values.pilot.resources.requests.cpu=100m \
        --set meshConfig.enableTracing=true \
        --set meshConfig.defaultConfig.tracing.sampling=100 \
        --set meshConfig.defaultConfig.tracing.zipkin.address="jaeger-collector.system-under-evaluation.svc.cluster.local:9411" # "otel-collector.system-under-evaluation.svc.cluster.local:9411"
    helm install istio-ingressgateway istio/gateway -n istio-system --create-namespace
    # kubectl rollout restart deployment -n system-under-evaluation
    kubectl label namespace system-under-evaluation istio-injection=enabled --overwrite
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

cleanup
setup
python -m oxn experiments/recommendation_k8_base_1s_otel.yml --report reports/
sleep 60

cleanup
setup
python -m oxn experiments/recommendation_k8_base_5_percent.yml --report reports/
sleep 60

cleanup
setup
python -m oxn experiments/recommendation_k8_base_10_percent.yml --report reports/
sleep 60

cleanup
setup
python -m oxn experiments/recommendation_k8_base_50_percent.yml --report reports/
sleep 60

cleanup
setup_external_jaeger_backend
python -m oxn experiments/recommendation_k8_base_1m_otel_persistence.yml --report reports/
sleep 60

cleanup
setup_external_jaeger_backend
python -m oxn experiments/recommendation_k8_base_5_percent_persistence.yml --report reports/
sleep 60

cleanup
setup_external_jaeger_backend
python -m oxn experiments/recommendation_k8_base_10_percent_persistence.yml --report reports/
sleep 60

cleanup
setup_external_jaeger_backend
python -m oxn experiments/recommendation_k8_base_50_percent_persistence.yml --report reports/
sleep 60

cleanup
setup
python -m oxn experiments/recommendation_k8_base_0_percent.yml --report reports/
sleep 60

cleanup
setup_external_jaeger_backend_istio
python -m oxn experiments/recommendation_k8_base_1m_otel_persistence_istio.yml --report reports/
sleep 60

#cleanup
#setup_external_jaeger_backend_istio
