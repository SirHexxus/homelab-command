# outputs.tf - Terraform Output Values
#
# After Terraform creates the container, these outputs display important information
# about the created resource. The container IP is particularly important because
# you'll need it for the Ansible inventory configuration.

output "container_vmid" {
  description = "Proxmox VM/Container ID for reference and direct access"
  value       = proxmox_virtual_environment_container.ollama.vm_id
}

output "container_hostname" {
  description = "Hostname assigned to the container"
  value       = proxmox_virtual_environment_container.ollama.initialization[0].hostname
}

output "container_node" {
  description = "Physical Proxmox node running this container"
  value       = proxmox_virtual_environment_container.ollama.node_name
}

output "container_network_config" {
  description = "Network configuration for reference"
  value = {
    bridge       = local.network_config.bridge
    using_dhcp   = local.network_config.dhcp
    static_ip    = local.network_config.ipv4
    gateway      = local.network_config.gateway
  }
}

output "ssh_key_path" {
  description = "SSH public key used for container access (for Ansible)"
  value       = var.ssh_public_key_file
}

output "deployment_instructions" {
  description = "Next steps after container creation"
  value = <<-EOT
    
    ============================================================
    Container created successfully!
    ============================================================
    
    Next steps:
    
    1. Wait 30-60 seconds for the container to start up and get network configuration
    
    2. Discover the container's IP address:
       - If you used static IP: ${local.network_config.ipv4 != null ? local.network_config.ipv4 : "N/A (using DHCP)"}
       - If you used DHCP: Check Proxmox UI or run:
         lxc-ls -f | grep ${proxmox_virtual_environment_container.ollama.initialization[0].hostname}
    
    3. Update ansible/inventory.ini with the container's IP address:
       Replace <CONTAINER_IP> with the IP you found above
    
    4. Verify SSH access from your workstation:
       ssh root@<CONTAINER_IP>
       (Should connect without password since SSH key was injected)
    
    5. Run Ansible provisioning:
       ansible-playbook -i ansible/inventory.ini ansible/provision.yml
    
    6. Wait 10-15 minutes for models to download (first run takes longer)
    
    7. Verify Ollama is running:
       curl http://<CONTAINER_IP>:11434/api/tags
       Should list: mistral, nomic-embed-text
    
    ============================================================
    EOT
}
