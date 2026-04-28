# outputs.tf

output "container_id" {
  description = "VMID of the inbox-receiver container"
  value       = proxmox_virtual_environment_container.inbox_receiver.vm_id
}

output "container_ip" {
  description = "Static IP assigned to the inbox-receiver"
  value       = var.container_ip
}
