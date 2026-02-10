terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}


resource "aws_instance" "meteo_server" {
  ami                    = var.ami_id
  instance_type          = var.instance_type
  key_name               = var.key_name
  vpc_security_group_ids = var.security_group_ids
  subnet_id              = var.subnet_id

  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.root_volume_size
    delete_on_termination = true
  }

  monitoring = true

  
  user_data = base64encode(templatefile("${path.module}/user_data.sh", {
    github_repo = var.github_repo
  }))

  tags = merge(
    var.common_tags,
    {
      Name = var.instance_name
      Environment = var.environment
    }
  )

  depends_on = []
}

resource "aws_eip" "meteo_eip" {
  instance = aws_instance.meteo_server.id
  domain   = "vpc"

  tags = merge(
    var.common_tags,
    {
      Name = "${var.instance_name}-eip"
    }
  )

  depends_on = [aws_instance.meteo_server]
}

# Security Group
resource "aws_security_group" "meteo_sg" {
  name        = var.security_group_name
  description = "Security group for Meteo France Platform"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    //cidr_blocks = var.ssh_cidr_blocks
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    var.common_tags,
    {
      Name = var.security_group_name
    }
  )
}
