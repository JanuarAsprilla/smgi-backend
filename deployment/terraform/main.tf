# deployment/terraform/main.tf
/*
SMGI Backend - Terraform Infrastructure
Sistema de Monitoreo Geoespacial Inteligente
Infraestructura como Código (IaC) para el despliegue en AWS
*/

# --- MEJORA: Bloque terraform para requerir versión y proveedores ---
terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.0"
    }
  }
}

# --- MEJORA: Bloque provider para AWS ---
provider "aws" {
  region = var.aws_region
  # access_key = var.aws_access_key # Cargar desde variables de entorno o archivo tfvars
  # secret_key = var.aws_secret_key # Cargar desde variables de entorno o archivo tfvars
  # profile    = var.aws_profile    # Cargar desde archivo ~/.aws/config
}

# --- MEJORA: Bloque provider para Kubernetes (si se usa EKS) ---
# provider "kubernetes" {
#   host                   = aws_eks_cluster.smgi_eks.endpoint
#   cluster_ca_certificate = base64decode(aws_eks_cluster.smgi_eks.certificate_authority[0].data)
#   exec {
#     api_version = "client.authentication.k8s.io/v1beta1"
#     command     = "aws"
#     args        = ["eks", "get-token", "--cluster-name", aws_eks_cluster.smgi_eks.name]
#   }
# }

# --- MEJORA: Bloque provider para Helm (si se usa EKS) ---
# provider "helm" {
#   kubernetes {
#     host                   = aws_eks_cluster.smgi_eks.endpoint
#     cluster_ca_certificate = base64decode(aws_eks_cluster.smgi_eks.certificate_authority[0].data)
#     exec {
#       api_version = "client.authentication.k8s.io/v1beta1"
#       command     = "aws"
#       args        = ["eks", "get-token", "--cluster-name", aws_eks_cluster.smgi_eks.name]
#     }
#   }
# }

# --- MEJORA: Variables para configurar el despliegue ---
variable "aws_region" {
  description = "AWS Region"
  type        = string
  default     = "us-east-1"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.medium"
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.medium"
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "smgi_db"
}

variable "db_username" {
  description = "Database username"
  type        = string
  default     = "smgi_user"
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

variable "redis_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "s3_bucket_name" {
  description = "S3 bucket name for static/media files"
  type        = string
  default     = "smgi-static-media-bucket"
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = "smgi.iiap.edu.pe"
}

variable "certificate_arn" {
  description = "ARN of the ACM certificate"
  type        = string
  default     = ""
}

variable "hosted_zone_id" {
  description = "Route 53 hosted zone ID"
  type        = string
  default     = ""
}

# --- MEJORA: Recursos de Red (VPC, Subnets, Security Groups) ---
resource "aws_vpc" "smgi_vpc" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "smgi-vpc"
    Environment = "production"
  }
}

resource "aws_subnet" "public_subnets" {
  count                   = length(var.availability_zones)
  vpc_id                  = aws_vpc.smgi_vpc.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone       = element(var.availability_zones, count.index)
  map_public_ip_on_launch = true

  tags = {
    Name = "smgi-public-subnet-${count.index}"
    Environment = "production"
  }
}

resource "aws_subnet" "private_subnets" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.smgi_vpc.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + length(var.availability_zones))
  availability_zone = element(var.availability_zones, count.index)

  tags = {
    Name = "smgi-private-subnet-${count.index}"
    Environment = "production"
  }
}

resource "aws_internet_gateway" "smgi_igw" {
  vpc_id = aws_vpc.smgi_vpc.id

  tags = {
    Name = "smgi-igw"
    Environment = "production"
  }
}

resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.smgi_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.smgi_igw.id
  }

  tags = {
    Name = "smgi-public-route-table"
    Environment = "production"
  }
}

resource "aws_route_table_association" "public_rta" {
  count          = length(aws_subnet.public_subnets)
  subnet_id      = aws_subnet.public_subnets[count.index].id
  route_table_id = aws_route_table.public_rt.id
}

resource "aws_security_group" "smgi_sg" {
  name        = "smgi-security-group"
  description = "Security group for SMGI Backend"
  vpc_id      = aws_vpc.smgi_vpc.id

  # HTTP
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTPS
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # SSH (solo para desarrollo, restringir en producción)
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # PostgreSQL
  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  # Redis
  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  # Salida a Internet
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "smgi-security-group"
    Environment = "production"
  }
}

# --- MEJORA: Recurso de Base de Datos (RDS PostgreSQL/PostGIS) ---
resource "aws_db_instance" "smgi_db" {
  identifier              = "smgi-db-instance"
  allocated_storage       = 20
  storage_type            = "gp2"
  engine                  = "postgres"
  engine_version          = "15.3" # Compatible con PostGIS
  instance_class          = var.db_instance_class
  db_name                 = var.db_name
  username                = var.db_username
  password                = var.db_password
  publicly_accessible     = false
  vpc_security_group_ids  = [aws_security_group.smgi_sg.id]
  db_subnet_group_name    = aws_db_subnet_group.smgi_db_subnet_group.name
  parameter_group_name    = aws_db_parameter_group.smgi_db_param_group.name
  backup_retention_period = 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:00-sun:05:00"
  multi_az                = true
  deletion_protection     = true
  skip_final_snapshot     = false

  tags = {
    Name = "smgi-db-instance"
    Environment = "production"
  }
}

resource "aws_db_subnet_group" "smgi_db_subnet_group" {
  name       = "smgi-db-subnet-group"
  subnet_ids = aws_subnet.private_subnets[*].id

  tags = {
    Name = "smgi-db-subnet-group"
    Environment = "production"
  }
}

resource "aws_db_parameter_group" "smgi_db_param_group" {
  name   = "smgi-db-param-group"
  family = "postgres15"

  parameter {
    name  = "log_statement"
    value = "all"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }

  tags = {
    Name = "smgi-db-param-group"
    Environment = "production"
  }
}

# --- MEJORA: Recurso de Caché/Mensajería (ElastiCache Redis) ---
resource "aws_elasticache_cluster" "smgi_redis" {
  cluster_id           = "smgi-redis-cluster"
  engine               = "redis"
  node_type            = var.redis_node_type
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  engine_version       = "7.0"
  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.smgi_redis_subnet_group.name
  security_group_ids   = [aws_security_group.smgi_sg.id]

  tags = {
    Name = "smgi-redis-cluster"
    Environment = "production"
  }
}

resource "aws_elasticache_subnet_group" "smgi_redis_subnet_group" {
  name       = "smgi-redis-subnet-group"
  subnet_ids = aws_subnet.private_subnets[*].id

  tags = {
    Name = "smgi-redis-subnet-group"
    Environment = "production"
  }
}

# --- MEJORA: Recurso de Almacenamiento (S3 Bucket) ---
resource "aws_s3_bucket" "smgi_static_media" {
  bucket = var.s3_bucket_name

  tags = {
    Name = "smgi-static-media-bucket"
    Environment = "production"
  }
}

resource "aws_s3_bucket_versioning" "smgi_static_media_versioning" {
  bucket = aws_s3_bucket.smgi_static_media.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "smgi_static_media_encryption" {
  bucket = aws_s3_bucket.smgi_static_media.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "smgi_static_media_public_access" {
  bucket = aws_s3_bucket.smgi_static_media.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "smgi_static_media_policy" {
  bucket = aws_s3_bucket.smgi_static_media.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowCloudFrontServicePrincipalReadOnly"
        Effect    = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action    = [
          "s3:GetObject"
        ]
        Resource  = "${aws_s3_bucket.smgi_static_media.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.smgi_static_media_cf.arn
          }
        }
      }
    ]
  })
}

# --- MEJORA: Recurso de Balanceador de Carga (Application Load Balancer) ---
resource "aws_lb" "smgi_alb" {
  name               = "smgi-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.smgi_sg.id]
  subnets            = aws_subnet.public_subnets[*].id

  enable_deletion_protection = true

  tags = {
    Name = "smgi-alb"
    Environment = "production"
  }
}

resource "aws_lb_target_group" "smgi_tg" {
  name     = "smgi-target-group"
  port     = 80
  protocol = "HTTP"
  vpc_id   = aws_vpc.smgi_vpc.id

  health_check {
    path                = "/health/"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  tags = {
    Name = "smgi-target-group"
    Environment = "production"
  }
}

resource "aws_lb_listener" "smgi_http_listener" {
  load_balancer_arn = aws_lb.smgi_alb.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_lb_listener" "smgi_https_listener" {
  load_balancer_arn = aws_lb.smgi_alb.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-2016-08"
  certificate_arn   = var.certificate_arn != "" ? var.certificate_arn : aws_acm_certificate.smgi_cert.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.smgi_tg.arn
  }
}

# --- MEJORA: Recurso de Certificado SSL (ACM) ---
resource "aws_acm_certificate" "smgi_cert" {
  count = var.certificate_arn == "" ? 1 : 0 # Solo crear si no se proporciona ARN

  domain_name       = var.domain_name
  validation_method = "DNS"

  tags = {
    Name = "smgi-cert"
    Environment = "production"
  }
}

# --- MEJORA: Recurso de DNS (Route 53) ---
resource "aws_route53_record" "smgi_dns" {
  count = var.hosted_zone_id != "" ? 1 : 0 # Solo crear si se proporciona hosted_zone_id

  zone_id = var.hosted_zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = aws_lb.smgi_alb.dns_name
    zone_id                = aws_lb.smgi_alb.zone_id
    evaluate_target_health = true
  }
}

# --- MEJORA: Recurso de Monitoreo (CloudWatch) ---
resource "aws_cloudwatch_log_group" "smgi_django_logs" {
  name              = "/aws/smgi/django"
  retention_in_days = 30

  tags = {
    Name = "smgi-django-logs"
    Environment = "production"
  }
}

resource "aws_cloudwatch_log_group" "smgi_celery_logs" {
  name              = "/aws/smgi/celery"
  retention_in_days = 30

  tags = {
    Name = "smgi-celery-logs"
    Environment = "production"
  }
}

resource "aws_cloudwatch_log_group" "smgi_nginx_logs" {
  name              = "/aws/smgi/nginx"
  retention_in_days = 30

  tags = {
    Name = "smgi-nginx-logs"
    Environment = "production"
  }
}

# --- MEJORA: Recurso de Seguridad (IAM Roles, Secrets Manager) ---
# IAM Role para EC2 instances (ejemplo básico)
resource "aws_iam_role" "smgi_ec2_role" {
  name = "smgi-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "smgi-ec2-role"
    Environment = "production"
  }
}

# Policy para acceder a S3, CloudWatch, Secrets Manager
resource "aws_iam_policy" "smgi_ec2_policy" {
  name = "smgi-ec2-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.smgi_static_media.arn,
          "${aws_s3_bucket.smgi_static_media.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = "*"
      }
    ]
  })

  tags = {
    Name = "smgi-ec2-policy"
    Environment = "production"
  }
}

# Attach policy to role
resource "aws_iam_role_policy_attachment" "smgi_ec2_policy_attach" {
  role       = aws_iam_role.smgi_ec2_role.name
  policy_arn = aws_iam_policy.smgi_ec2_policy.arn
}

# Secrets Manager para almacenar secretos sensibles
resource "aws_secretsmanager_secret" "smgi_secrets" {
  name = "smgi/secrets"

  tags = {
    Name = "smgi-secrets"
    Environment = "production"
  }
}

resource "aws_secretsmanager_secret_version" "smgi_secrets_version" {
  secret_id     = aws_secretsmanager_secret.smgi_secrets.id
  secret_string = jsonencode({
    "SECRET_KEY"           = "django-insecure-production-key-change-me-!!!"
    "DB_PASSWORD"          = var.db_password
    "REDIS_PASSWORD"       = "redis-prod-password"
    "EMAIL_HOST_PASSWORD"  = "email-prod-password"
    "TWILIO_AUTH_TOKEN"    = "twilio-prod-auth-token"
    "FCM_SERVER_KEY"       = "fcm-prod-server-key"
    "ARCGIS_PASSWORD"      = "arcgis-prod-password"
    "API_KEY"              = "api-prod-key"
  })
}

# --- MEJORA: Outputs para exportar valores importantes ---
output "vpc_id" {
  value = aws_vpc.smgi_vpc.id
  description = "ID of the VPC"
}

output "public_subnet_ids" {
  value = aws_subnet.public_subnets[*].id
  description = "IDs of the public subnets"
}

output "private_subnet_ids" {
  value = aws_subnet.private_subnets[*].id
  description = "IDs of the private subnets"
}

output "db_endpoint" {
  value = aws_db_instance.smgi_db.endpoint
  description = "Endpoint of the RDS instance"
}

output "redis_endpoint" {
  value = aws_elasticache_cluster.smgi_redis.cache_nodes[0].address
  description = "Endpoint of the ElastiCache cluster"
}

output "s3_bucket_name" {
  value = aws_s3_bucket.smgi_static_media.bucket
  description = "Name of the S3 bucket"
}

output "alb_dns_name" {
  value = aws_lb.smgi_alb.dns_name
  description = "DNS name of the Application Load Balancer"
}

output "alb_zone_id" {
  value = aws_lb.smgi_alb.zone_id
  description = "Zone ID of the Application Load Balancer"
}

output "certificate_arn" {
  value = var.certificate_arn != "" ? var.certificate_arn : aws_acm_certificate.smgi_cert[0].arn
  description = "ARN of the ACM certificate"
}

output "iam_role_name" {
  value = aws_iam_role.smgi_ec2_role.name
  description = "Name of the IAM role"
}

output "secrets_manager_secret_arn" {
  value = aws_secretsmanager_secret.smgi_secrets.arn
  description = "ARN of the Secrets Manager secret"
}
