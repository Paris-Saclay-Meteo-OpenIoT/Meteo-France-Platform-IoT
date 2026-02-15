# Example terraform.tfvars file
# Copy this to terraform.tfvars and fill in your values

aws_region         = "eu-west-1"
instance_type      = "t3.medium"
instance_name      = "meteo-france-server"
key_name           = "key-pair-name"
vpc_id             = "vpc"
subnet_id          = "subnet"
security_group_name = "meteo-france-sg"
root_volume_size   = 30
github_repo        = ""
environment        = "production"

common_tags = {
  Project     = "Meteo-France-Platform-IoT"
  ManagedBy   = "Terraform"
  CreatedBy   = "GitHub-Actions"
  Owner       = "Rafik"
}
