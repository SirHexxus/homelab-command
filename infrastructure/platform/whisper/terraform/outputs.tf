# outputs.tf - Terraform Output Values
#
# These outputs display important information after container creation.

output "container_vmid" {
  description = "Proxmox VM/Container ID"
  value       = proxmox_virtual_environment_container.whisper.vm_id
}

output "container_hostname" {
  description = "Hostname assigned to the container"
  value       = proxmox_virtual_environment_container.whisper.initialization[0].hostname
}

output "container_node" {
  description = "Proxmox node running this container"
  value       = proxmox_virtual_environment_container.whisper.node_name
}

output "container_network_config" {
  description = "Network configuration"
  value = {
    bridge     = local.network_config.bridge
    using_dhcp = local.network_config.dhcp
    static_ip  = local.network_config.ipv4
    gateway    = local.network_config.gateway
  }
}

output "ssh_key_path" {
  description = "SSH public key used for container access"
  value       = var.ssh_public_key_file
}

output "deployment_instructions" {
  description = "Next steps after container creation"
  value       = <<-EOT

    ============================================================
    Whisper Container Created Successfully!
    ============================================================

    Next steps:

    1. Wait 30-60 seconds for the container to boot and get an IP

    2. Find the container's IP address:
       - Static IP: ${local.network_config.ipv4 != null ? local.network_config.ipv4 : "N/A (using DHCP)"}
       - DHCP: Check Proxmox UI or run:
         lxc-ls -f | grep ${proxmox_virtual_environment_container.whisper.initialization[0].hostname}

    3. Update ansible/inventory.ini with the container's IP:
       Replace <CONTAINER_IP> with the actual IP

    4. Verify SSH access:
       ssh root@<CONTAINER_IP>

    5. Run Ansible provisioning:
       ansible-playbook -i ansible/inventory.ini ansible/provision.yml

    6. Verify Whisper is running:
       curl http://<CONTAINER_IP>:9000/health

    7. Test transcription:
       curl -X POST http://<CONTAINER_IP>:9000/v1/audio/transcriptions \
         -F "file=@audio.mp3" \
         -F "model=small"

    ============================================================
    EOT
}
