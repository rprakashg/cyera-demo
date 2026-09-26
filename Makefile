REGISTRY ?= quay.io/rprakashg

.PHONY: build
build:
	echo "Building connector container"
	podman build \
		--platform linux/amd64 \
		-t cyera-connector:latest \
		-f ./connector/Containerfile \
		./connector
	
	echo "Pushing the connector container to registry"
	podman tag cyera-connector:latest ${REGISTRY}/cyera-connector:latest
	podman push ${REGISTRY}/cyera-connector:latest

	echo "Building simulated controlplane container"
	podman build \
		--platform linux/amd64 \
		-t cyera-control-plane:latest \
		-f ./control-plane/Containerfile \
		./control-plane

	echo "Pushing the controlplane container to registry"
	podman tag cyera-control-plane:latest ${REGISTRY}/cyera-control-plane:latest
	podman push ${REGISTRY}/cyera-control-plane:latest

	echo "Building simulated agent container"
	podman build \
		--platform linux/amd64 \
		-t cyera-agent:latest \
		-f ./agent/Containerfile \
		./agent

	echo "Pushing the simulated agent container to registry"
	podman tag cyera-agent:latest ${REGISTRY}/cyera-agent:latest
	podman push ${REGISTRY}/cyera-agent:latest

.PHONY: deploy-cluster
deploy-cluster:
	echo "Deploying EKS cluster using terraform"
	terraform -chdir=./tf init 
	terraform -chdir=./tf plan -out=tfplan
	terraform -chdir=./tf apply -auto-approve tfplan

.PHONY: update-kubeconfig
update-kubeconfig:
	echo "Updating local kubeconfig"
	aws eks update-kubeconfig --region us-east-2 --name demo-cluster
	
.PHONY: deploy-workloads
deploy-workloads:
	echo "Deploying to kubernetes cluster"
	kubectl apply -f k8s/00-namespace.yaml
	kubectl apply -f k8s/01-postgres.yaml
	kubectl apply -f k8s/02-connector.yaml
	kubectl apply -f k8s/03-control-plane.yaml
	kubectl apply -f k8s/04-agent.yaml

	echo "Waiting for pods to be ready"
	kubectl -n cyera-demo wait --for=condition=available --timeout=120s deployment/postgres
	kubectl -n cyera-demo wait --for=condition=available --timeout=120s deployment/connector
	kubectl -n cyera-demo wait --for=condition=available --timeout=120s deployment/control-plane
	kubectl -n cyera-demo wait --for=condition=available --timeout=120s deployment/cyera-privacy-agent

	echo ""
	kubectl get pods -n cyera-demo

.PHONY: cleanup
cleanup:
	echo "Removing workloads from cluster"
	kubectl delete -f k8s/04-agent.yaml
	kubectl delete -f k8s/03-control-plane.yaml
	kubectl delete -f k8s/02-connector.yaml
	kubectl delete -f k8s/01-postgres.yaml
	kubectl delete -f k8s/00-namespace.yaml
	