output "instance_id" {
  description = "ID of the EC2 instance"
  value       = aws_instance.meteo_server.id
}

output "instance_public_ip" {
  description = "Public IP of the EC2 instance"
  value       = aws_eip.meteo_eip.public_ip
}

output "instance_private_ip" {
  description = "Private IP of the EC2 instance"
  value       = aws_instance.meteo_server.private_ip
}

output "security_group_id" {
  description = "ID of the security group"
  value       = aws_security_group.meteo_sg.id
}

output "eip_allocation_id" {
  description = "Allocation ID of the Elastic IP"
  value       = aws_eip.meteo_eip.id
}
