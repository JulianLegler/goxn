#!/bin/bash
source venv/bin/activate


# Ensure log directory exists
mkdir -p experimentation_logs

# Create a log file with the current timestamp
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOGFILE="experimentation_logs/experiment_$TIMESTAMP.log"

# Redirect stdout and stderr to the log file, while still printing to terminal
exec > >(tee -a "$LOGFILE") 2>&1

#
# Dump current PV usage to a CSV whose name is derived from
# ------------------------------------------------------------------
dump_storage_csv () {
    local experiment_path="$1"            
    local exp_file="$(basename "$experiment_path")"
    local prefix="${exp_file%.*}"         
    local out_dir="storage_snapshots"     
    mkdir -p "$out_dir"

    local ts="$(date +'%Y-%m-%d_%H-%M-%S')"

    # File will look like   foo_storage_2025‑07‑16_14‑38‑20.csv
    local csv_file="${out_dir}/${prefix}_storage_${ts}.csv"

    # CSV header ----------------------------------------------------
    printf "PV_NAME,PVC,PATH,USAGE_BYTES\n" > "$csv_file"

    # Query the cluster and append rows ----------------------------
    kubectl get pv -o json | jq -r '
      .items[] |
      [
        .metadata.name,
        (if .spec.claimRef != null
           then "\(.spec.claimRef.namespace)/\(.spec.claimRef.name)"
           else "unbound" end),
        (
          if .spec.nfs       then .spec.nfs.path
          elif .spec.hostPath then .spec.hostPath.path
          elif .spec.csi     then .spec.csi.volumeHandle
          elif .spec.local   then .spec.local.path
          else "unknown"
          end
        )
      ] | @tsv' | \
    while IFS=$'\t' read -r pv pvc path; do
        if [ -d "$path" ]; then
            usage=$(du -sb "$path" 2>/dev/null | awk '{print $1}')
        else
            usage=""
        fi
        printf "%s,%s,%s,%s\n" "$pv" "$pvc" "$path" "$usage"
    done >> "$csv_file"

    echo "[storage]  Wrote storage snapshot →  $csv_file"
}


run_experiment () {
    local experiment_yaml="$1"

    cleanup
    setup_external_jaeger_backend

    python -m oxn "$experiment_yaml" --report reports/
    dump_storage_csv "$experiment_yaml"
    sleep 60

}

run_experiment_istio () {
    local experiment_yaml="$1"

    cleanup
    setup_external_jaeger_backend_istio

    python -m oxn "$experiment_yaml" --report reports/
    dump_storage_csv "$experiment_yaml"
    sleep 60

}

cleanup() {
    kubectl config set-context --current --namespace=system-under-evaluation
    helm uninstall astronomy-shop
    sleep 30
    kubectl delete pvc data-astronomy-shop-elasticsearch-data-0
    kubectl delete pvc data-astronomy-shop-elasticsearch-data-1
    kubectl delete pvc data-astronomy-shop-elasticsearch-master-0
    kubectl delete pvc data-astronomy-shop-elasticsearch-master-1
    kubectl delete -f k8s/kibana/
    kubectl delete -f k8s/elasticsearch/
    sleep 30
    kubectl config set-context --current --namespace=istio-system
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

setup_istio() {
    kubectl config set-context --current --namespace=oxn-external-monitoring
    helm install kube-prometheus prometheus-community/kube-prometheus-stack --namespace oxn-external-monitoring --create-namespace --version 62.5.1 -f values_kube_prometheus.yaml
    sleep 30
    helm install istio-base istio/base --version 1.26.2 -n istio-system --set defaultRevision=default --create-namespace
    helm install istiod istio/istiod -n istio-system \
        --set global.proxy.autoInject=enabled \
        --set meshConfig.enablePrometheusMerge=true \
        --set values.pilot.resources.requests.cpu=100m \
        --set meshConfig.enableTracing=true \
        --set meshConfig.defaultConfig.tracing.sampling=1 \
        --set meshConfig.defaultConfig.tracing.zipkin.address="otel-collector.system-under-evaluation.svc.cluster.local:9411"
    helm install istio-ingressgateway istio/gateway -n istio-system --create-namespace
    # kubectl rollout restart deployment -n system-under-evaluation
    kubectl label namespace system-under-evaluation istio-injection=enabled --overwrite
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
    kubectl apply -f k8s/elasticsearch/
    kubectl config set-context --current --namespace=system-under-evaluation
    sleep 60
}

setup_external_jaeger_backend_istio() {
    kubectl config set-context --current --namespace=oxn-external-monitoring
    helm install kube-prometheus prometheus-community/kube-prometheus-stack --namespace oxn-external-monitoring --create-namespace --version 62.5.1 -f values_kube_prometheus_istio.yaml
    sleep 30
    helm install istio-base istio/base --version 1.26.2 -n istio-system --set defaultRevision=default --create-namespace
    helm install istiod istio/istiod -n istio-system -f values_istiod.yaml
    helm install istio-ingressgateway istio/gateway -n istio-system --create-namespace
    # kubectl rollout restart deployment -n system-under-evaluation
    kubectl label namespace system-under-evaluation istio-injection=enabled --overwrite
    sleep 30
    kubectl config set-context --current --namespace=system-under-evaluation
    helm install astronomy-shop open-telemetry/opentelemetry-demo --namespace system-under-evaluation --create-namespace --version 0.36.4 -f values_opentelemetry_demo_persistence.yaml
    kubectl apply -f k8s/elasticsearch/
    kubectl config set-context --current --namespace=system-under-evaluation
    sleep 60
}

experiments=(
    "experiments/recommendation_k8_base_1m_otel_persistence.yml"
    "experiments/recommendation_k8_base_1m_otel_persistence_scrape_5s.yml"
    "experiments/recommendation_k8_base_1m_otel_persistence_scrape_30s.yml"
    "experiments/recommendation_k8_base_5_percent_persistence.yml"
    "experiments/recommendation_k8_base_10_percent_persistence.yml"
    "experiments/recommendation_k8_base_50_percent_persistence.yml"
)

for exp in "${experiments[@]}"; do
    run_experiment "$exp"
done

run_experiment_istio "experiments/recommendation_k8_base_1m_otel_persistence_istio.yml"

#cleanup
#setup_external_jaeger_backend