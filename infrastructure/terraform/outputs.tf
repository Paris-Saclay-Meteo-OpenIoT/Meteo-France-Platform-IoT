output "ec2_instance_id" {
  description = "EC2 instance ID"
  value       = module.ec2.instance_id
}

output "ec2_public_ip" {
  description = "Public IP of EC2 instance"
  value       = module.ec2.instance_public_ip
}

output "ec2_private_ip" {
  description = "Private IP of EC2 instance"
  value       = module.ec2.instance_private_ip
}

output "security_group_id" {
  description = "Security group ID"
  value       = module.ec2.security_group_id
}
