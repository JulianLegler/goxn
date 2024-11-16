source venv/bin/activate

helm uninstall astronomy-shop open-telemetry/opentelemetry-demo
sleep 30
helm install astronomy-shop open-telemetry/opentelemetry-demo --namespace system-under-evaluation --create-namespace -f values_opentelemetry_demo.yaml
sleep 30
python -m oxn experiments/recommendation_k8_base_1m_otel.yml --report reports/
sleep 60

helm uninstall astronomy-shop open-telemetry/opentelemetry-demo
sleep 30
helm install astronomy-shop open-telemetry/opentelemetry-demo --namespace system-under-evaluation --create-namespace -f values_opentelemetry_demo.yaml
sleep 30
python -m oxn experiments/recommendation_k8_delay_1m_otel.yml --report reports/
sleep 60

helm uninstall astronomy-shop open-telemetry/opentelemetry-demo
sleep 30
helm install astronomy-shop open-telemetry/opentelemetry-demo --namespace system-under-evaluation --create-namespace -f values_opentelemetry_demo.yaml
sleep 30
python -m oxn experiments/recommendation_k8_delay_1s_otel.yml --report reports/
sleep 60

helm uninstall astronomy-shop open-telemetry/opentelemetry-demo
sleep 30
helm install astronomy-shop open-telemetry/opentelemetry-demo --namespace system-under-evaluation --create-namespace -f values_opentelemetry_demo.yaml
sleep 30
python -m oxn experiments/recommendation_k8_sampling_5_percent.yml --report reports/
sleep 60