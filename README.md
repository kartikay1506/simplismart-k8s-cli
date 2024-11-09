# simplismart-k8s-cli
This project is a CLI/API script designed to automate operations on a Kubernetes cluster, such as installing necessary tooling (like Helm and KEDA), creating deployments with event-driven scaling, and providing health status for deployments.

### Features
1. **Kubernetes Cluster Connection**: Connects to a Kubernetes cluster using kubectl and verifies access.
2. **Tool Installation**: Installs KEDA for event-driven autoscaling using HELM package manager.
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

## Usage
### 1. Connect to the Kubernetes Cluster
The script will connect to the Kubernetes cluster using the cluster name provided. It will also check if required tools such kubectl and helm are available or not. Since these tools are required for the script to function properly, the following command will fail if any of the tools is not present in the system or cluster is not acceessible.
```
python simplismart.py connect <cluster-name>
```

### 2. Install Tools (KEDA)
Installs KEDA for event-driven autoscaling in the specified namespace. This can however be used to install any tool via HELM as long as the necessary charts are available for that tool in the namespace provided in the arguments. The default namespace will be used if no namespace argument is given.
```
python simplismart.py install --chart <chart name> --repo <helm chart repo url> --namespace <namespace for tool (optional)>
```

### Create Deployment with Autoscaling
Creates a Kubernetes deployment with event-driven autoscaling based on parameters given in the arguments.
We can also give additional arguments to the script while creating deployment such as memory and cpu limits and requests. A deployment can be created just by providiing a name and image to be used.
```
python simplismart.py create <deployment name> --image <image> --port <ports to be exposed> --namespace <namespace> --event_source '<event source for KEDA>'
```

### 4. Retrieve Health Status
Checks the health and status of the deployment, including CPU and memory metrics.
```
python simplismart.py health-status <deployment name> --namespace <deployment namespace> --labels <labels to get deployment pods details>
```

## Guide
For getting more information about any of the above functions of the script and the required arguments to run that function, simply use any one of the following.

For details about all supported operations:
```
python simplismart.py -h
```
For details about specific operation:
```
python simplismart.py <operation> -h
```


