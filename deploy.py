#!/usr/bin/env python3
"""
Production Deployment Script
Automates deployment to Kubernetes cluster
"""

import subprocess
import sys
import time
import argparse
from pathlib import Path
import yaml
import json


class DeploymentManager:
    """Manages deployment to Kubernetes"""
    
    def __init__(self, environment='staging', namespace='credit-risk-system'):
        self.environment = environment
        self.namespace = namespace
        self.k8s_dir = Path('k8s')
        
    def run_command(self, command, check=True):
        """Run shell command"""
        print(f"Running: {command}")
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True
        )
        
        if check and result.returncode != 0:
            print(f"Error: {result.stderr}")
            sys.exit(1)
        
        return result.stdout
    
    def check_prerequisites(self):
        """Check if required tools are installed"""
        print("Checking prerequisites...")
        
        tools = ['kubectl', 'docker']
        for tool in tools:
            try:
                self.run_command(f"{tool} --version")
                print(f"✓ {tool} found")
            except:
                print(f"✗ {tool} not found")
                sys.exit(1)
    
    def build_docker_image(self, tag='latest'):
        """Build Docker image"""
        print(f"\nBuilding Docker image (tag: {tag})...")
        self.run_command(
            f"docker build -f Dockerfile.production -t credit-risk-api:{tag} ."
        )
        print("✓ Docker image built successfully")
    
    def push_docker_image(self, registry, tag='latest'):
        """Push Docker image to registry"""
        print(f"\nPushing image to {registry}...")
        
        full_tag = f"{registry}/credit-risk-api:{tag}"
        self.run_command(f"docker tag credit-risk-api:{tag} {full_tag}")
        self.run_command(f"docker push {full_tag}")
        
        print("✓ Image pushed successfully")
    
    def apply_kubernetes_manifests(self):
        """Apply Kubernetes manifests"""
        print(f"\nApplying Kubernetes manifests to {self.namespace}...")
        
        manifests = [
            'namespace.yaml',
            'configmap.yaml',
            'secrets.yaml',
            'persistent-volumes.yaml',
            'postgres-deployment.yaml',
            'redis-deployment.yaml',
            'api-deployment.yaml',
            'hpa.yaml',
            'ingress.yaml'
        ]
        
        for manifest in manifests:
            manifest_path = self.k8s_dir / manifest
            if manifest_path.exists():
                print(f"  Applying {manifest}...")
                self.run_command(f"kubectl apply -f {manifest_path}")
            else:
                print(f"  Warning: {manifest} not found, skipping...")
    
    def wait_for_rollout(self, deployment='credit-risk-api'):
        """Wait for deployment rollout to complete"""
        print(f"\nWaiting for {deployment} rollout...")
        self.run_command(
            f"kubectl rollout status deployment/{deployment} -n {self.namespace} --timeout=5m"
        )
        print("✓ Rollout completed")
    
    def run_smoke_tests(self):
        """Run basic smoke tests"""
        print("\nRunning smoke tests...")
        
        # Get service endpoint
        service_info = self.run_command(
            f"kubectl get service credit-risk-api-service -n {self.namespace} -o json"
        )
        
        # Test health endpoint
        print("  Testing /health endpoint...")
        time.sleep(10)  # Wait for pods to be ready
        
        # Port forward for testing
        print("  Setting up port forward...")
        port_forward = subprocess.Popen(
            f"kubectl port-forward -n {self.namespace} service/credit-risk-api-service 8080:80",
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        time.sleep(5)
        
        try:
            import requests
            response = requests.get("http://localhost:8080/health", timeout=10)
            if response.status_code == 200:
                print("  ✓ Health check passed")
            else:
                print(f"  ✗ Health check failed: {response.status_code}")
        except Exception as e:
            print(f"  ✗ Health check failed: {e}")
        finally:
            port_forward.terminate()
    
    def get_deployment_status(self):
        """Get deployment status"""
        print("\nDeployment Status:")
        print("=" * 60)
        
        # Pods
        print("\nPods:")
        self.run_command(
            f"kubectl get pods -n {self.namespace} -l app=credit-risk-api"
        )
        
        # Services
        print("\nServices:")
        self.run_command(
            f"kubectl get services -n {self.namespace}"
        )
        
        # HPA
        print("\nHorizontal Pod Autoscaler:")
        self.run_command(
            f"kubectl get hpa -n {self.namespace}",
            check=False
        )
    
    def deploy(self, build_image=True, push_image=False, registry=None, tag='latest'):
        """Full deployment workflow"""
        print(f"Starting deployment to {self.environment}...")
        print("=" * 60)
        
        self.check_prerequisites()
        
        if build_image:
            self.build_docker_image(tag)
        
        if push_image and registry:
            self.push_docker_image(registry, tag)
        
        self.apply_kubernetes_manifests()
        self.wait_for_rollout()
        self.run_smoke_tests()
        self.get_deployment_status()
        
        print("\n" + "=" * 60)
        print("✓ Deployment completed successfully!")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='Deploy Credit Risk API')
    parser.add_argument(
        '--environment',
        choices=['staging', 'production'],
        default='staging',
        help='Deployment environment'
    )
    parser.add_argument(
        '--namespace',
        default='credit-risk-system',
        help='Kubernetes namespace'
    )
    parser.add_argument(
        '--build',
        action='store_true',
        help='Build Docker image'
    )
    parser.add_argument(
        '--push',
        action='store_true',
        help='Push Docker image to registry'
    )
    parser.add_argument(
        '--registry',
        help='Docker registry URL'
    )
    parser.add_argument(
        '--tag',
        default='latest',
        help='Docker image tag'
    )
    
    args = parser.parse_args()
    
    deployer = DeploymentManager(
        environment=args.environment,
        namespace=args.namespace
    )
    
    deployer.deploy(
        build_image=args.build,
        push_image=args.push,
        registry=args.registry,
        tag=args.tag
    )


if __name__ == '__main__':
    main()
