# provider.tf - Proxmox Provider Configuration
#
# This file configures how Terraform connects to your Proxmox cluster.
# The actual credentials (API token, endpoints) are in terraform.tfvars

terraform {
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.69"
    }
  }
  required_version = ">= 1.0"
}

provider "proxmox" {
  endpoint  = var.proxmox_endpoint
  api_token = "${var.proxmox_api_token_id}=${var.proxmox_api_token}"
  insecure  = var.proxmox_tls_insecure
}
