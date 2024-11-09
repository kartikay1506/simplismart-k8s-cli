import argparse
import json
import subprocess
import yaml
from kubernetes import client, config


def connect_k8s_cluster(args):
    # Connecting to kubernetes cluster
    try:
        print("Connecting to Kubernetes cluster {}".format(args.name))
        subprocess.run(["kubectl", "config", "use-context", "{}".format(args.name)], check=True)
        print("\nConnected to Kubernetes cluster {}".format(args.name))
    except subprocess.CalledProcessError as e:
        print("Failed to connect to Kubernetes cluster: {}".format(e))


def check_tools():
    # Checking if Helm is installed or not
    try:
        print("\nChecking if helm is installed........")
        subprocess.run(["helm", "version"], check=True)
    except subprocess.CalledProcessError as e:
        print("Helm is not installed or accessible. Please install helm.")
        return False

    # Checking if kubectl is accessible or not
    try:
        print("\nChecking if kubectl is installed........")
        subprocess.run(["kubectl", "version", "--client"], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print("Kubectl is not installed or not accessible.")
        return False


def add_repo(chart, repo):
    command = ["helm", "repo", "add"]
    command.append(chart)
    command.append(repo)
    try:
        print("Adding HELM chart: {}".format(chart))
        subprocess.run(command, check=True)
        subprocess.run(["helm", "repo", "update"], check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError("Unable to add chart for {}: {}".format(chart, e))


def load_config():
    # Load the config to initialise clients for kubernetes api
    config.load_kube_config()


def verify_pods(args):
    # TODO: add wait timeout logic here to check for service to come online after few minutes
    try:
        load_config()
        apps_v1 = client.CoreV1Api()
        pods = apps_v1.list_namespaced_pod(namespace=args.namespace)
        for pod in pods.items:
            if pod.status.phase != "Running":
                raise Exception("{} is not in running state. Check the pod for more details.".format(pod.metadata.name))
        print("{} is running successfully.".format(args.chart.split('/')[-1]))
    except Exception as e:
        print("Exception caught: {}".format(e))


def install_tools(args):
    command = ["helm", "install"]
    command.append(args.chart.split('/')[1])
    command.append(args.chart)
    command.append("--namespace")
    command.append(args.namespace)
    command.append("--create-namespace")
    try:
        # Adding the HELM repo
        add_repo(args.chart.split('/')[0], args.repo)

        # Installing the tool via HELM
        subprocess.run(command, check=True)
        print("{} installed successfully.".format(args.chart.split('/')[-1]))
        # Check whether the pods are running or not.
        verify_pods(args)
    except subprocess.CalledProcessError as e:
        raise RuntimeError("Failed to install {}: {}".format(args.chart, e))


def create_service(args):
    # Service to expose the deployment
    try:
        core_client = client.CoreV1Api()
        ports = [port.strip("") for port in args.ports.split(",")]
        service_ports = [client.V1ServicePort(port=int(port), target_port=int(port)) for port in ports]
        service_spec = client.V1Service(
            metadata=client.V1ObjectMeta(name=f"{args.name}-service", namespace=args.namespace),
            spec=client.V1ServiceSpec(
                selector={"app": args.name},
                ports=service_ports
            )
        )
        core_client.create_namespaced_service(namespace=args.namespace, body=service_spec)
        print("Service for {} created successfully.\n".format(args.name))
        subprocess.run(["kubectl", "get", "svc", "{}-service".format(args.name), "-n", "{}".format(args.namespace)], check=True)
    except Exception as e:
        print("Error creating service: {}".format(e))
    except subprocess.CalledProcessError as e:
        print("Exception caught: {}".format(e))


def create_deployment(args):
    try:
        # Load the kubernetes config for the kubernetes api to function
        load_config()
        # Create a deployment spec using Kubernetes API
        apps_client = client.AppsV1Api()

        ports = [port.strip("") for port in args.ports.split(",")]

        container_ports = [client.V1ContainerPort(container_port=int(port)) for port in ports]

        container_list = [
            client.V1Container(
                name=args.name,
                image=args.image,
                ports=container_ports,
                resources=client.V1ResourceRequirements(
                    requests={"cpu": args.cpu_request, "memory": args.memory_request},
                    limits={"cpu": args.cpu_limit, "memory": args.memory_limit}
                )
            )
        ]

        deployment_spec = client.V1Deployment(
            metadata=client.V1ObjectMeta(name=args.name, namespace=args.namespace),
            spec=client.V1DeploymentSpec(
                replicas=1,
                selector={"matchLabels": {"app": args.name}},
                template=client.V1PodTemplateSpec(
                    metadata={"labels": {"app": args.name}},
                    spec=client.V1PodSpec(
                        containers=container_list
                    )
                )
            )
        )

        # Apply Deployment
        apps_client.create_namespaced_deployment(namespace=args.namespace, body=deployment_spec)
        print("Deployment {} created successfully in namespace {}\n".format(args.name, args.namespace))
        subprocess.run(["kubectl", "get", "deployment", "{}".format(args.name), "-n", "{}".format(args.namespace)], check=True)

        # Create the service for the deployment
        create_service(args)

        # Setup autoscaler using KEDA
        setup_autoscaler(args)
    except Exception as e:
        raise Exception("Exception caught: {}".format(e))
    except subprocess.CalledProcessError as e:
        raise Exception("Exception caught: {}".format(e))


def setup_autoscaler(args):
    # Autoscaler setup using KEDA
    # We can customise the KEDA autoscaler with necessary configurations from the event source
    try:
        stream = open("keda.yaml", "r")
        keda_yaml = yaml.safe_load(stream)

        keda_yaml["metadata"]["name"] = args.name + "-autoscaler"
        keda_yaml["metadata"]["namespace"] = args.namespace
        keda_yaml["spec"]["scaleTargetRef"]["name"] = args.name

        args.event_source = json.loads(args.event_source)
        for trigger in keda_yaml["spec"]["triggers"]:
            trigger["type"] = args.event_source["type"]
            trigger["metadata"] = args.event_source["metadata"]

        subprocess.run(["kubectl", "apply", "-f", "-"], input=json.dumps(keda_yaml).encode(), check=True)
        print("KEDA Scaled Object for {} created.".format(args.name))

    except Exception as e:
        raise Exception("Exception caught: {}".format(e))
    except subprocess.CalledProcessError as e:
        raise Exception("Exception caught: {}".format(e))


def get_deployment_health_status(args):
    # Load the kubernetes config for the kubernetes api to function
    load_config()

    app_client = client.AppsV1Api()
    core_client = client.CoreV1Api()

    # Get the deployment status
    try:
        deployment = app_client.read_namespaced_deployment(args.deployment, args.namespace)
        replicas = deployment.status.replicas
        ready_replicas = deployment.status.ready_replicas

        # Pod Metrics for health status
        pods = core_client.list_namespaced_pod(args.namespace, label_selector="app={}".format(args.labels))
        print("POD METRICS")
        for pod in pods.items:
            subprocess.run(["kubectl", "top", "pod", "{}".format(pod.metadata.name), "-n", "{}".format(args.namespace)])
            print("Ready - {}".format(pod.status.conditions[-1].status))

        print("\nDEPLOYMENT STATUS")
        print("Deployment {}: {}/{} replicas ready".format(args.deployment, ready_replicas, replicas))

        print("\nDEPLOYMENT EVENTS")
        subprocess.run(
            [
                "kubectl", "get", "event", "--field-selector", "involvedObject.name={}".format(args.deployment),
                "--namespace", "{}".format(args.namespace)
            ],
            check=True)
    except Exception as e:
        raise Exception("Error retrieving deployment health status: {}".format(e))
    except subprocess.CalledProcessError as e:
        print("Exception caught: {}".format(e))


def main():
    # create parser object
    parser = argparse.ArgumentParser(
        prog="simplismart",
        description="A command line utility to automate operations on a bare Kubernetes cluster.",
    )

    #defining the arguments for the parser object
    subparsers = parser.add_subparsers(dest="operation", help="Operation to perform on the Kubernetes cluster")

    # 'connect' operation with its own positional and optional arguments
    connect_parser = subparsers.add_parser("connect", help="Connect to a kubernetes cluster.")
    connect_parser.add_argument("name", help="Cluster name to connect to.")

    # 'install' operation with its own positional and optional arguments
    install_parser = subparsers.add_parser("install", help="Install tools on the kubernetes cluster.")
    install_parser.add_argument("-c", "--chart", help="Helm chart name for the tool to be installed", required=True)
    install_parser.add_argument("-r", "--repo", help="Repo link for the helm chart", required=True)
    install_parser.add_argument("-n", "--namespace", default="default", help="namespace for the tool to be installed in.")

    # 'create' operation with its own positional and optional arguments
    create_parser = subparsers.add_parser("create", help="Create deployment and expose the deployment via service.")
    create_parser.add_argument("name", help="Name of the deployment.")
    create_parser.add_argument("-n", "--namespace", default="default", help="Namespace for the deployment to be created in.")
    create_parser.add_argument("-i", "--image", help="Image to be used for the deployment", required=True)
    create_parser.add_argument("-p", "--ports", help="Port to be exposed for connecting to the service.")
    create_parser.add_argument("--cpu_limit", help="CPU limit for the deployment.")
    create_parser.add_argument("--cpu_request", help="CPU request for the deployment.")
    create_parser.add_argument("--memory_limit", help="Memory limit for the deployment.")
    create_parser.add_argument("--memory_request", help="Memory request for the deployment.")
    create_parser.add_argument("--event_source", help="Event source for autoscaler in JSON format enclosed in ''.")

    health_parser = subparsers.add_parser("health-status", help="Get the health status of the deployment.")
    health_parser.add_argument("deployment", help="Deployment ID for which health status needs to be fetched.")
    health_parser.add_argument("-n", "--namespace", default="default", help="Namespace where ths deployment exists")
    health_parser.add_argument("-l", "--labels", help="Labels for the pod to be matched in the deployment.", required=True)

    # Parse the arguments from the standard input
    args = parser.parse_args()
    if args.operation == "connect":
        connect_k8s_cluster(args)
        # Check if neecessary tools are installed or not.
        if not check_tools():
            raise Exception("Required tools are not installed. Please install them before using this script.")
    elif args.operation == "install":
        install_tools(args)
    elif args.operation == "create":
        # create_deployment(args)
        setup_autoscaler(args)
    elif args.operation == "health-status":
        get_deployment_health_status(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
