variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-2"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t2.large"
}

variable "instance_name" {
  description = "Name of the EC2 instance"
  type        = string
  default     = "meteo-france-server"
}

variable "key_name" {
  description = "Name of the EC2 key pair"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID"
  type        = string
  default     = null
}

variable "security_group_name" {
  description = "Security group name"
  type        = string
  default     = "meteo-france-sg"
}

variable "ssh_cidr_blocks" {
  description = "CIDR blocks allowed for SSH"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "root_volume_size" {
  description = "Root volume size in GB"
  type        = number
  default     = 32
}

variable "github_repo" {
  description = "GitHub repository URL"
  type        = string
  default     = "https://github.com/Paris-Saclay-Meteo-OpenIoT/Meteo-France-Platform-IoT.git"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project     = "Meteo-France-Platform-IoT"
    ManagedBy   = "Terraform"
    CreatedBy   = "GitHub-Actions"
  }
}
