module "ec2" {
  source = "./modules/ec2"

  ami_id                = data.aws_ami.ubuntu.id
  instance_type         = var.instance_type
  instance_name         = var.instance_name
  key_name              = var.key_name
  vpc_id                = var.vpc_id
  subnet_id             = var.subnet_id
  security_group_name   = var.security_group_name
  ssh_cidr_blocks       = var.ssh_cidr_blocks
  root_volume_size      = var.root_volume_size
  github_repo           = var.github_repo
  environment           = var.environment
  common_tags           = var.common_tags
}

# Data source to get the latest Ubuntu 22.04 LTS AMI
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}
