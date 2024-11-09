# simplismart-k8s-cli
This project is a CLI/API script designed to automate operations on a Kubernetes cluster, such as installing necessary tooling (like Helm and KEDA), creating deployments with event-driven scaling, and providing health status for deployments.

### Features
1. **Kubernetes Cluster Connection**: Connects to a Kubernetes cluster using kubectl and verifies access.
2. **Tool Installation**: Installs Helm for package management and KEDA for event-driven autoscaling.
3. **Deployment Creation**: Automates deployment creation with configurable CPU, memory, ports, and autoscaling targets.
4. **Health Status Retrieval**: Provides health status of a given deployment, including CPU and memory usage.

### Requirements
1. Python 3.8+
2. Kubernetes CLI (kubectl)
3. Helm 3.x
4. KEDA (installed via Helm)
5. DockerHub account (for public image)
6. kubernetes metrics server (if not installed already)

### Installation

1. **Clone the repository**:
```
git clone https://github.com/kartikay1506/simplismart-k8s-cli.git
cd simplismart-k8s-cli
```

2. **Install Python Dependencies**:
```
pip install -r requirements.txt
```

3. **Setup Kubernetes Access**:
    - Ensure you have access to the Kubernetes cluster and kubeconfig file is available.
    - Place your kubeconfig file in a known location (e.g., ~/.kube/config)


4. **Check Docker Access**:
    - Login to docker remote repository to ensure container images can be downloaded if not available locally.
      ```
      docker login <docker repo>
      ```





