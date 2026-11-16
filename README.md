# Proyecto SRE – Milena Quesada Bruno

Documentación paso a paso de lo realizado en esta carpeta, desde la app en Flask hasta su despliegue en Kubernetes con Minikube.

## Estructura actual

```
Proyecto_SRE/
├── Application development/
│   └── app.py              # Aplicación Flask
├── Kubernetes Deployment/
│   ├── Dockerfile          # Imagen del contenedor
│   ├── deployment.yaml     # Deployment de Kubernetes
│   └── service.yaml        # Service de Kubernetes
├── Prometheus integration/
│   ├── prometheus.yaml             # Namespace, ConfigMap, Deployment y Service de Prometheus
│   ├── alertmanager.yaml           # ConfigMap, Deployment y Service de Alertmanager
│   ├── prometheus-alert-rules.yaml # ConfigMap con las reglas de alerta
│   └── infra.yaml                  # Playbook de Ansible que aplica prometheus.yaml
├── Grafana Visualization/
│   ├── grafana.yaml        # Deployment, Service y ConfigMaps de Grafana
│   └── infra.yaml          # Playbook de Ansible que aplica grafana.yaml
├── AlertManager Deployment/
│   ├── cadvisor.yaml                # DaemonSet de cAdvisor
│   └── prometheus-rbac-cluster.yaml # ClusterRole y ClusterRoleBinding para Prometheus
├── ansible_quickstart/
│   └── inventory.ini       # Inventario de Ansible (localhost)
├── milejay/                # Entorno virtual (venv)
└── README.md               # Este documento
```

---

## Paso 1: Crear la aplicación `app.py`

Se creó una app mínima en Flask:

- La ruta `/` devuelve una página HTML con estilo que muestra **Proyecto SRE** y **Milena Quesada Bruno**.
- Corre en el puerto 5001 y escucha en todas las interfaces (`0.0.0.0`).

Contenido esencial de [`app.py`](Application%20development/app.py):

```python
from flask import Flask

app = Flask(__name__)

HOME_PAGE = """ ...HTML con estilo... """

@app.route('/')
def home():
    return HOME_PAGE


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
```

> `app.run(..., port=5001)` solo se ejecuta con `python app.py`. Con `flask run` se ignora (ver Paso 3).

---

## Paso 2: Crear el entorno virtual (venv)

El entorno virtual se llama `milejay` y aísla las dependencias del proyecto.

```bash
cd Proyecto_SRE
python3 -m venv milejay          # crear el entorno
source milejay/bin/activate      # activarlo (el prompt muestra "(milejay)")
pip install flask                # instalar Flask
```

Ejecutar la app en local, sin Docker:

```bash
python "Application development/app.py"
```

Abrir <http://127.0.0.1:5001/>.

Para salir del entorno: `deactivate`.

---

## Paso 3: Crear el `Dockerfile`

Archivo [`Dockerfile`](Kubernetes%20Deployment/Dockerfile):

```dockerfile
FROM python:3.10
EXPOSE 5001
WORKDIR /app
RUN pip install flask
COPY . .
CMD ["flask", "run", "--host", "0.0.0.0", "--port", "5001"]
```

| Instrucción | Qué hace |
|---|---|
| `FROM python:3.10` | Imagen base con Python 3.10 |
| `EXPOSE 5001` | Documenta el puerto que usa la app |
| `WORKDIR /app` | Directorio de trabajo dentro del contenedor |
| `RUN pip install flask` | Instala Flask en la imagen |
| `COPY . .` | Copia el código al contenedor |
| `CMD [...]` | Comando de arranque |

> `flask run` no ejecuta el bloque `if __name__ == '__main__':` de `app.py`, por eso el puerto se indica con `--port 5001` en el `CMD`.

---

## Paso 4: Docker con Colima

En macOS se usa [Colima](https://github.com/abiosoft/colima) como runtime para Docker, sin Docker Desktop.

### 4.1 Iniciar Colima

```bash
colima start --runtime docker
```

Verificar que corre:

```bash
colima list      # STATUS: Running
docker ps        # responde sin errores
```

### 4.2 Construir la imagen

```bash
cd Proyecto_SRE
docker build -f "Kubernetes Deployment/Dockerfile" -t my-python-sre-app_v2:latest "Application development"
```

---

## Paso 5: Kubernetes con Minikube

[Minikube](https://minikube.sigs.k8s.io/) crea un cluster de Kubernetes local. Usa el driver `docker`, que corre sobre Colima (Paso 4).

### 5.1 Iniciar el cluster

```bash
minikube start --driver=docker
```

Verificar que el cluster está listo:

```bash
minikube status      # host, kubelet y apiserver en Running
kubectl get nodes    # el nodo "minikube" en STATUS Ready
kubectl get pods -A  # los pods de kube-system en Running
```

### 5.2 Crear el `deployment.yaml`

Archivo [`deployment.yaml`](Kubernetes%20Deployment/deployment.yaml):

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sre-final-project-mqb
spec:
  replicas: 3
  selector:
    matchLabels:
      app: sre-final-project-mqb
  template:
    metadata:
      labels:
        app: sre-final-project-mqb
    spec:
      containers:
      - name: sre-final-project-mqb
        image: milenanacr/my-python-sre-app_v2:latest
        ports:
        - containerPort: 5001
```

### 5.3 Aplicar el Deployment

```bash
kubectl apply -f "Kubernetes Deployment/deployment.yaml"
```

Verificar que las 3 réplicas están corriendo:

```bash
kubectl get deployments    # READY 3/3
kubectl get pods           # 3 pods en STATUS Running
```
### 5.4 Crear y aplicar el `service.yaml`

Archivo [`service.yaml`](Kubernetes%20Deployment/service.yaml):

```yaml
apiVersion: v1
kind: Service
metadata:
  name: sre-final-project-service
spec:
  type: NodePort
  selector:
    app: sre-final-project-mqb
  ports:
  - port: 5001
    targetPort: 5001
```

```bash
kubectl apply -f "Kubernetes Deployment/service.yaml"
kubectl get service sre-final-project-service
```

Salida:

```
NAME                        TYPE       CLUSTER-IP     EXTERNAL-IP   PORT(S)          AGE
sre-final-project-service   NodePort   10.99.42.166   <none>        5001:31568/TCP   37s
```

### 5.5 Acceder a la aplicación

```bash
minikube service sre-final-project-service --url
```

Salida:

```
http://127.0.0.1:53559
```

Abrir esa URL en el navegador. Con el driver Docker en macOS, la terminal debe quedar abierta mientras se usa la app.

---

## Paso 6: Integración de Prometheus

Prometheus se despliega en el mismo cluster de Minikube, en su propio namespace `monitoring`.

### 6.1 Crear el `prometheus.yaml`

Archivo [`prometheus.yaml`](Prometheus%20integration/prometheus.yaml). Define cuatro recursos separados por `---`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: monitoring

---
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: monitoring
  labels:
    app: prometheus
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s

    scrape_configs:
      - job_name: 'prometheus'
        static_configs:
          - targets: ['localhost:9090']

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prometheus-deployment
  namespace: monitoring
  labels:
    app: prometheus
spec:
  replicas: 1
  selector:
    matchLabels:
      app: prometheus
  template:
    metadata:
      labels:
        app: prometheus
    spec:
      containers:
        - name: prometheus
          image: prom/prometheus:latest
          args:
            - "--config.file=/etc/prometheus/prometheus.yml"
          ports:
            - containerPort: 9090
          volumeMounts:
            - name: prometheus-config-volume
              mountPath: /etc/prometheus/
      volumes:
        - name: prometheus-config-volume
          configMap:
            name: prometheus-config

---
apiVersion: v1
kind: Service
metadata:
  name: prometheus-service
  namespace: monitoring
  labels:
    app: prometheus
spec:
  selector:
    app: prometheus
  ports:
    - protocol: TCP
      port: 9090
      targetPort: 9090
  type: NodePort
```

### 6.2 Crear el playbook `infra.yaml`

Archivo [`infra.yaml`](Prometheus%20integration/infra.yaml). Es un playbook de Ansible que ejecuta `kubectl apply` sobre `prometheus.yaml`:

```yaml
---
- name: Apply Prometheus configuration and start service in Minikube
  hosts: all
  #become: yes  # Optional, if sudo permissions are required
  tasks:
    - name: Apply Prometheus configuration
      command: kubectl apply -f prometheus.yaml
      args:
        chdir: ./  # Adjust path as needed
```

El playbook busca `prometheus.yaml` en el directorio donde se ejecuta (`chdir: ./`), así que debe lanzarse desde `Prometheus integration/`.

### 6.3 Aplicar la configuración

Desde la carpeta `Prometheus integration/`, con el inventario de Ansible [`inventory.ini`](ansible_quickstart/inventory.ini):

```ini
[allhosts]
127.0.0.1 ansible_connection=local
```

```bash
cd "Prometheus integration"
ansible-playbook -i ../ansible_quickstart/inventory.ini infra.yaml
```

> El inventario se pasa con `-i`. Sin esa opción, Ansible interpreta `inventory.ini` como si fuera el playbook y falla con `YAML parsing failed`.

También se puede aplicar directamente, sin Ansible:

```bash
kubectl apply -f prometheus.yaml
```

Verificar que quedó desplegado:

```bash
kubectl get pods -n monitoring        # prometheus-deployment en Running
kubectl get svc -n monitoring         # prometheus-service, NodePort 9090
kubectl get configmap -n monitoring   # prometheus-config
```

### 6.4 Acceder a Prometheus

```bash
minikube service prometheus-service -n monitoring --url
```

Abrir la URL que devuelve en el navegador. Con el driver Docker en macOS, la terminal debe quedar abierta mientras se usa.

---

## Paso 7: Visualización con Grafana

Grafana se despliega en el mismo namespace `monitoring` que Prometheus y se conecta a él como fuente de datos.

### 7.1 Crear el `grafana.yaml`

Archivo [`grafana.yaml`](Grafana%20Visualization/grafana.yaml). Define cuatro recursos separados por `---`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grafana-deployment
  namespace: monitoring
  labels:
    app: grafana
spec:
  replicas: 1
  selector:
    matchLabels:
      app: grafana
  template:
    metadata:
      labels:
        app: grafana
    spec:
      containers:
        - name: grafana
          image: grafana/grafana:latest
          ports:
            - containerPort: 3000
          volumeMounts:
            - name: grafana-config-datasources
              mountPath: /etc/grafana/provisioning/datasources
              readOnly: true
            - name: grafana-config-dashboards
              mountPath: /etc/grafana/provisioning/dashboards
              readOnly: true
      volumes:
        - name: grafana-config-datasources
          configMap:
            name: grafana-datasources-config
        - name: grafana-config-dashboards
          configMap:
            name: grafana-dashboards-config

---

apiVersion: v1
kind: Service
metadata:
  name: grafana-service
  namespace: monitoring
  labels:
    app: grafana
spec:
  selector:
    app: grafana
  ports:
    - protocol: TCP
      port: 3000
      targetPort: 3000
  type: NodePort

---

apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-datasources-config
  namespace: monitoring
  labels:
    app: grafana
data:
  datasources.yaml: |
    apiVersion: 1
    datasources:
      - name: Prometheus
        type: prometheus
        access: proxy
        url: http://prometheus-service.monitoring.svc.cluster.local:9090
        isDefault: true
        editable: true

---

apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-dashboards-config
  namespace: monitoring
  labels:
    app: grafana
data:
  dashboards.yaml: |
    apiVersion: 1
    providers:
      - name: 'default'
        orgId: 1
        folder: ''
        type: file
        disableDeletion: false
        options:
          path: /etc/grafana/provisioning/dashboards
  example-dashboard.json: |
    {
      "id": null,
      "uid": "example-dashboard",
      "title": "Example Dashboard",
      "tags": [],
      "style": "dark",
      "timezone": "browser",
      "editable": true,
      "panels": [
        {
          "datasource": "Prometheus",
          "id": 1,
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 0,
            "y": 0
          },
          "targets": [
            {
              "expr": "sum by(job) (rate(process_cpu_seconds_total[1m]))",
              "refId": "A"
            }
          ],
          "title": "CPU Usage",
          "type": "graph"
        },
        {
          "datasource": "Prometheus",
          "id": 2,
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 12,
            "y": 0
          },
          "targets": [
            {
              "expr": "sum(rate(container_cpu_usage_seconds_total[5m])) by (container_label_io_kubernetes_pod_name)",
              "refId": "B"
            }
          ],
          "title": "Pod CPU Usage",
          "type": "graph"
        }
      ],
      "schemaVersion": 16,
      "version": 1
    }
```

La fuente de datos apunta a `prometheus-service` por su nombre DNS interno del cluster, `prometheus-service.monitoring.svc.cluster.local:9090`.

### 7.2 Crear el playbook `infra.yaml`

Archivo [`infra.yaml`](Grafana%20Visualization/infra.yaml). Igual que en el Paso 6, es un playbook de Ansible que ejecuta `kubectl apply`, esta vez sobre `grafana.yaml`:

```yaml
---
- name: Apply Grafana configuration and start service in Minikube
  hosts: all
  #become: yes  # Optional, if sudo permissions are required
  tasks:
    - name: Apply Grafana configuration
      command: kubectl apply -f grafana.yaml
      args:
        chdir: ./  # Adjust path as needed
```

### 7.3 Aplicar la configuración

Desde la carpeta `Grafana Visualization/`:

```bash
cd "Grafana Visualization"
ansible-playbook -i ../ansible_quickstart/inventory.ini infra.yaml
```

Verificar que quedó desplegado:

```bash
kubectl get pods -n monitoring        # grafana-deployment en Running
kubectl get svc -n monitoring         # grafana-service, NodePort 3000
kubectl get configmap -n monitoring   # grafana-datasources-config y grafana-dashboards-config
```

### 7.4 Acceder a Grafana

```bash
minikube service grafana-service -n monitoring --url
```

Abrir la URL que devuelve en el navegador. Con el driver Docker en macOS, la terminal debe quedar abierta mientras se usa.

---

## Paso 8: Métricas de contenedores con cAdvisor

[cAdvisor](https://github.com/google/cadvisor) expone métricas de CPU, memoria, red y disco de los contenedores. Prometheus las recoge con un job nuevo.

### 8.1 Medir el número de métricas antes

En Prometheus, ejecutar la consulta:

```promql
count({__name__=~".+"})
```

Se anota el valor inicial (en este proyecto, 961).

### 8.2 Desplegar cAdvisor

Archivo [`cadvisor.yaml`](AlertManager%20Deployment/cadvisor.yaml): un DaemonSet con la etiqueta `app: cadvisor` que expone `/metrics` en el puerto 8080.

```bash
cd "AlertManager Deployment"
kubectl apply -f cadvisor.yaml
kubectl get pods -n default -l app=cadvisor    # Running
```

### 8.3 Dar permisos a Prometheus (RBAC)

Prometheus corre en el namespace `monitoring` y cAdvisor en `default`. Archivo [`prometheus-rbac-cluster.yaml`](AlertManager%20Deployment/prometheus-rbac-cluster.yaml): crea un `ClusterRole` con permisos `get`, `list` y `watch` sobre `pods` y `endpoints`, y lo asigna con un `ClusterRoleBinding` a la cuenta `default` del namespace `monitoring`.

```bash
kubectl apply -f prometheus-rbac-cluster.yaml
kubectl get clusterrolebinding prometheus-pod-reader-binding-cluster
```

### 8.4 Añadir el job `cadvisor` a Prometheus

Aplicar solo cAdvisor y el RBAC no basta: Prometheus solo lee lo que está en su configuración. Hay que añadir este job en `scrape_configs` del ConfigMap de [`prometheus.yaml`](Prometheus%20integration/prometheus.yaml):

```yaml
      - job_name: 'cadvisor'
        kubernetes_sd_configs:
          - role: pod
            namespaces:
              names:
                - default
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_label_app]
            action: keep
            regex: cadvisor
        metrics_path: /metrics
        scheme: http
```

Prometheus busca los pods del namespace `default` con la etiqueta `app=cadvisor` y los lee en `/metrics`.

Aplicar el cambio y reiniciar Prometheus, porque no recarga el ConfigMap por sí solo:

```bash
cd "../Prometheus integration"
kubectl apply -f prometheus.yaml
kubectl rollout restart deployment/prometheus-deployment -n monitoring
kubectl rollout status deployment/prometheus-deployment -n monitoring
```

### 8.5 Validar

Esperar unos segundos y repetir la consulta:

```promql
count({__name__=~".+"})
```

El conteo aumentó de 961 a 4992. En **Status → Targets** de Prometheus deben aparecer los jobs `prometheus` y `cadvisor` en estado `UP`.

Con las métricas de cAdvisor ya se puede consultar la CPU por pod:

```promql
sum(rate(container_cpu_usage_seconds_total[5m])) by (container_label_io_kubernetes_pod_name)
```

### 8.6 Mostrar la CPU por pod en Grafana

El dashboard de [`grafana.yaml`](Grafana%20Visualization/grafana.yaml) incluye un segundo panel, **Pod CPU Usage**, con la consulta anterior. Queda a la derecha del panel **CPU Usage** (`"w": 12` cada uno). Está en el ConfigMap `grafana-dashboards-config`, así que no hay que crearlo a mano.

Aplicar el cambio y reiniciar Grafana, porque no recarga el dashboard por sí solo:

```bash
cd "../Grafana Visualization"
kubectl apply -f grafana.yaml
kubectl rollout restart deployment/grafana-deployment -n monitoring
kubectl rollout status deployment/grafana-deployment -n monitoring
```

Abrir Grafana (ver 7.4) con el usuario `admin` y la contraseña `admin` (por defecto) y entrar al dashboard **Example Dashboard**: deben verse los dos paneles.

---

## Paso 9: Alertas con Alertmanager

[Alertmanager](https://prometheus.io/docs/alerting/latest/alertmanager/) recibe las alertas que dispara Prometheus y las envía por correo. Los archivos están en `Prometheus integration/`.

### 9.1 Crear el Secret con las credenciales de correo

Alertmanager lee la contraseña SMTP desde un Secret de Kubernetes, para no escribirla en un archivo. El Secret se llama `alertmanager-email` y tiene las claves `smtp_username` y `smtp_password`:

```bash
kubectl create secret generic alertmanager-email \
  -n monitoring \
  --from-literal=smtp_username='<correo>' \
  --from-literal=smtp_password='<contraseña de aplicación>'
```

> Con Gmail hay que usar una **contraseña de aplicación**, no la contraseña normal de la cuenta. Los valores no se guardan en el repositorio.

### 9.2 Crear el `alertmanager.yaml`

Archivo [`alertmanager.yaml`](Prometheus%20integration/alertmanager.yaml). Define tres recursos:

```yaml
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: alertmanager-config
  namespace: monitoring
data:
  alertmanager.yml: |
    global:
      resolve_timeout: 5m
      smtp_smarthost: 'smtp.gmail.com:587'
      smtp_from: 'milenanacr@gmail.com'
      smtp_auth_username: 'milenanacr@gmail.com'
      smtp_auth_password_file: '/etc/alertmanager/secrets/smtp_password'
      smtp_require_tls: true

    route:
      receiver: email-notifications
      group_by: ['alertname', 'severity']
      group_wait: 30s
      group_interval: 5m
      repeat_interval: 4h

    receivers:
      - name: email-notifications
        email_configs:
          - to: 'milenanacr@gmail.com'
            send_resolved: true

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: alertmanager
  namespace: monitoring
  labels:
    app: alertmanager
spec:
  replicas: 1
  selector:
    matchLabels:
      app: alertmanager
  template:
    metadata:
      labels:
        app: alertmanager
    spec:
      containers:
        - name: alertmanager
          image: prom/alertmanager:latest
          args:
            - "--config.file=/etc/alertmanager/alertmanager.yml"
          ports:
            - containerPort: 9093
          volumeMounts:
            - name: alertmanager-config
              mountPath: /etc/alertmanager
            - name: alertmanager-secret
              mountPath: /etc/alertmanager/secrets
              readOnly: true
      volumes:
        - name: alertmanager-config
          configMap:
            name: alertmanager-config
        - name: alertmanager-secret
          secret:
            secretName: alertmanager-email
            items:
              - key: smtp_password
                path: smtp_password

---
apiVersion: v1
kind: Service
metadata:
  name: alertmanager
  namespace: monitoring
spec:
  selector:
    app: alertmanager
  ports:
    - name: web
      port: 9093
      targetPort: 9093
  type: ClusterIP
```

- El ConfigMap define cómo se envían los correos (SMTP de Gmail) y a quién (`email-notifications`).
- Las alertas se agrupan por `alertname` y `severity`, y se repiten cada 4 horas (`repeat_interval`).
- `send_resolved: true` envía otro correo cuando la alerta se resuelve.
- El Secret se monta como archivo en `/etc/alertmanager/secrets/smtp_password`.
- El Service es `ClusterIP`: solo es accesible dentro del cluster, que es lo que Prometheus necesita.

### 9.3 Crear las reglas de alerta

Archivo [`prometheus-alert-rules.yaml`](Prometheus%20integration/prometheus-alert-rules.yaml): un ConfigMap con una regla.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-alert-rules
  namespace: monitoring
data:
  alert-rules.yml: |
    groups:
      - name: infrastructure-alerts
        rules:
          - alert: PrometheusTargetDown
            expr: up == 0
            for: 1m
            labels:
              severity: critical
            annotations:
              summary: "A monitoring target is down"
              description: "Prometheus cannot scrape target {{ $labels.job }} ({{ $labels.instance }})."
```

La alerta `PrometheusTargetDown` se dispara si algún target (`up == 0`) lleva 1 minuto sin responder.

### 9.4 Conectar Prometheus con Alertmanager

En el ConfigMap de [`prometheus.yaml`](Prometheus%20integration/prometheus.yaml) se añaden dos bloques en `prometheus.yml`:

```yaml
    alerting:
      alertmanagers:
        - static_configs:
            - targets: ['alertmanager.monitoring.svc.cluster.local:9093']

    rule_files:
      - /etc/prometheus/alert-rules.yml
```

- `alerting` indica a qué Alertmanager enviar las alertas, usando el nombre DNS interno del Service.
- `rule_files` indica el archivo donde Prometheus busca las reglas de alerta.

### 9.5 Aplicar

```bash
cd "Prometheus integration"
kubectl apply -f prometheus-alert-rules.yaml
kubectl apply -f alertmanager.yaml
kubectl apply -f prometheus.yaml
kubectl rollout restart deployment/prometheus-deployment -n monitoring
kubectl rollout status deployment/prometheus-deployment -n monitoring
```

Prometheus se reinicia porque no recarga el ConfigMap por sí solo.

### 9.6 Verificar

```bash
kubectl get pods -n monitoring    # alertmanager en Running
kubectl get svc -n monitoring     # alertmanager, ClusterIP 9093
kubectl get secret -n monitoring  # alertmanager-email
```

Para comprobar que Prometheus ya conoce a Alertmanager, en **Status → Alertmanagers** debe aparecer `http://alertmanager.monitoring.svc.cluster.local:9093/api/v2/alerts`.

---

## Próximos pasos

_Este documento se irá ampliando con cada paso nuevo del deployment._
