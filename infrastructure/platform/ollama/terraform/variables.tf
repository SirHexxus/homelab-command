# variables.tf - Input Variables for Terraform Configuration
#
# These variables allow you to customize the Terraform configuration without
# editing the main resource definitions. Values are provided in terraform.tfvars
# which you should create in the same directory as these files.

variable "proxmox_endpoint" {
  description = "The base URL of your Proxmox cluster (e.g., https://proxmox.example.com:8006/)"
  type        = string
  sensitive   = true
}

variable "proxmox_api_token_id" {
  description = "Proxmox API token ID in format 'username@pam!tokenname' or similar"
  type        = string
  sensitive   = true
}

variable "proxmox_api_token" {
  description = "Proxmox API token secret (keep this secret!)"
  type        = string
  sensitive   = true
}

variable "proxmox_tls_insecure" {
  description = "Skip TLS certificate verification. Set to true only for self-signed certificates in home labs."
  type        = bool
  default     = true
}

variable "proxmox_node" {
  description = "The name of the Proxmox node where the LXC container will be created (e.g., 'pve1', 'pve2')"
  type        = string
}

variable "container_name" {
  description = "Name of the LXC container (must be unique on the node)"
  type        = string
  default     = "ollama"
}

variable "container_hostname" {
  description = "Hostname inside the container"
  type        = string
  default     = "ollama-server"
}

variable "container_cpu_cores" {
  description = "Number of CPU cores to allocate to the container"
  type        = number
  default     = 8
  
  validation {
    condition     = var.container_cpu_cores > 0 && var.container_cpu_cores <= 64
    error_message = "CPU cores must be between 1 and 64."
  }
}

variable "container_memory_mb" {
  description = "Memory to allocate to the container in megabytes (default: 16GB = 16384 MB)"
  type        = number
  default     = 16384
  
  validation {
    condition     = var.container_memory_mb >= 2048
    error_message = "Memory must be at least 2GB (2048 MB)."
  }
}

variable "container_disk_gb" {
  description = "Disk size to allocate to the container in gigabytes (default: 50GB)"
  type        = number
  default     = 50
  
  validation {
    condition     = var.container_disk_gb >= 20
    error_message = "Disk size must be at least 20GB."
  }
}

variable "container_storage" {
  description = "Proxmox storage name where the container's root filesystem will be stored (e.g., 'local-lvm', 'nvme')"
  type        = string
  default     = "local-lvm"
}

variable "lxc_template" {
  description = "LXC template to use (usually the Ubuntu image available in Proxmox)"
  type        = string
  default     = "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
}

variable "network_bridge" {
  description = "Proxmox network bridge to attach the container to (e.g., 'vmbr1')"
  type        = string
  default     = "vmbr1"
}

variable "container_ip" {
  description = "IP address to assign to the container (in CIDR notation, e.g., '10.0.50.10/24'). Leave empty for DHCP."
  type        = string
  default     = "10.0.50.10/24"
}

variable "container_gateway" {
  description = "Gateway IP for the container network."
  type        = string
  default     = "10.0.50.1"
}

variable "vlan_tag" {
  description = "VLAN tag for the container network interface. Set to 0 to disable VLAN tagging."
  type        = number
  default     = 50

  validation {
    condition     = var.vlan_tag >= 0 && var.vlan_tag <= 4094
    error_message = "VLAN tag must be between 0 (disabled) and 4094."
  }
}

variable "ssh_public_key_file" {
  description = "Path to your SSH public key file for container access (e.g., ~/.ssh/id_rsa.pub)"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "enable_privileged_mode" {
  description = "Run container in privileged mode (not recommended for security). Set to true only if you need Docker or other privileged operations."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags to apply to the container for organization"
  type        = list(string)
  default     = ["ollama", "ai", "inference"]
}

variable "additional_lxc_features" {
  description = "Additional LXC features to enable. The setup enables nesting and keyctl by default for GPU support."
  type        = list(string)
  default     = []
}
