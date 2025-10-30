# deployment/terraform/variables.tf
/*
SMGI Backend - Terraform Variables
Sistema de Monitoreo Geoespacial Inteligente
Variables de entrada para parametrizar el despliegue en AWS
*/

# --- MEJORA: Variables del Proveedor de Nube (AWS) ---
variable "aws_region" {
  description = "AWS Region where resources will be deployed"
  type        = string
  default     = "us-east-1"
}

variable "aws_access_key" {
  description = "AWS Access Key ID (preferably set via environment variable)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "aws_secret_key" {
  description = "AWS Secret Access Key (preferably set via environment variable)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "aws_profile" {
  description = "AWS CLI profile to use (if not using access/secret keys)"
  type        = string
  default     = ""
}

# --- MEJORA: Variables de Red (VPC, Subnets) ---
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

variable "public_subnet_cidrs" {
  description = "List of CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "private_subnet_cidrs" {
  description = "List of CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.11.0/24", "10.0.12.0/24", "10.0.13.0/24"]
}

# --- MEJORA: Variables de Computo (EC2, ECS, EKS) ---
variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.medium"
}

variable "key_name" {
  description = "Name of the SSH key pair to use for EC2 instances"
  type        = string
  default     = ""
}

variable "ami_id" {
  description = "AMI ID to use for EC2 instances (if not using default)"
  type        = string
  default     = ""
}

# --- MEJORA: Variables de Base de Datos (RDS PostgreSQL/PostGIS) ---
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

variable "db_allocated_storage" {
  description = "Allocated storage for the RDS instance (in GB)"
  type        = number
  default     = 20
}

variable "db_engine_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "15.3" # Compatible con PostGIS
}

variable "db_parameter_group_name" {
  description = "Name of the DB parameter group"
  type        = string
  default     = "default.postgres15"
}

variable "db_backup_retention_period" {
  description = "Backup retention period for the RDS instance (in days)"
  type        = number
  default     = 7
}

variable "db_backup_window" {
  description = "Backup window for the RDS instance (UTC)"
  type        = string
  default     = "03:00-04:00"
}

variable "db_maintenance_window" {
  description = "Maintenance window for the RDS instance (UTC)"
  type        = string
  default     = "sun:04:00-sun:05:00"
}

variable "db_multi_az" {
  description = "Enable Multi-AZ deployment for the RDS instance"
  type        = bool
  default     = true
}

variable "db_deletion_protection" {
  description = "Enable deletion protection for the RDS instance"
  type        = bool
  default     = true
}

variable "db_skip_final_snapshot" {
  description = "Skip final snapshot when deleting the RDS instance"
  type        = bool
  default     = false
}

# --- MEJORA: Variables de Caché/Mensajería (ElastiCache Redis) ---
variable "redis_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "redis_engine_version" {
  description = "Redis engine version"
  type        = string
  default     = "7.0"
}

variable "redis_parameter_group_name" {
  description = "Name of the Redis parameter group"
  type        = string
  default     = "default.redis7"
}

variable "redis_port" {
  description = "Port for the Redis cluster"
  type        = number
  default     = 6379
}

# --- MEJORA: Variables de Almacenamiento (S3 Bucket) ---
variable "s3_bucket_name" {
  description = "S3 bucket name for static/media files"
  type        = string
  default     = "smgi-static-media-bucket"
}

variable "s3_bucket_versioning" {
  description = "Enable versioning for the S3 bucket"
  type        = bool
  default     = true
}

variable "s3_bucket_encryption" {
  description = "Enable server-side encryption for the S3 bucket"
  type        = bool
  default     = true
}

variable "s3_bucket_public_access_block" {
  description = "Block public access to the S3 bucket"
  type        = bool
  default     = true
}

# --- MEJORA: Variables de Balanceador de Carga (Application Load Balancer) ---
variable "alb_name" {
  description = "Name of the Application Load Balancer"
  type        = string
  default     = "smgi-alb"
}

variable "alb_internal" {
  description = "Whether the ALB is internal (true) or internet-facing (false)"
  type        = bool
  default     = false
}

variable "alb_load_balancer_type" {
  description = "Type of the load balancer"
  type        = string
  default     = "application"
}

variable "alb_enable_deletion_protection" {
  description = "Enable deletion protection for the ALB"
  type        = bool
  default     = true
}

# --- MEJORA: Variables de Certificado SSL (ACM) ---
variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = "smgi.iiap.edu.pe"
}

variable "certificate_arn" {
  description = "ARN of the ACM certificate (if not creating one)"
  type        = string
  default     = ""
}

variable "validation_method" {
  description = "Validation method for the ACM certificate (DNS or EMAIL)"
  type        = string
  default     = "DNS"
}

# --- MEJORA: Variables de DNS (Route 53) ---
variable "hosted_zone_id" {
  description = "Route 53 hosted zone ID"
  type        = string
  default     = ""
}

variable "dns_record_name" {
  description = "Name of the DNS record"
  type        = string
  default     = "smgi"
}

variable "dns_record_type" {
  description = "Type of the DNS record"
  type        = string
  default     = "A"
}

# --- MEJORA: Variables de Monitoreo (CloudWatch) ---
variable "cloudwatch_log_group_retention_days" {
  description = "Retention period for CloudWatch log groups (in days)"
  type        = number
  default     = 30
}

variable "cloudwatch_log_group_kms_key_id" {
  description = "KMS key ID for encrypting CloudWatch log groups"
  type        = string
  default     = ""
}

# --- MEJORA: Variables de Seguridad (IAM, Security Groups) ---
variable "security_group_name" {
  description = "Name of the main security group"
  type        = string
  default     = "smgi-security-group"
}

variable "security_group_description" {
  description = "Description of the main security group"
  type        = string
  default     = "Security group for SMGI Backend"
}

variable "ingress_rules" {
  description = "List of ingress rules for the security group"
  type        = list(object({
    from_port   = number
    to_port     = number
    protocol    = string
    cidr_blocks = list(string)
    description = string
  }))
  default     = [
    {
      from_port   = 80
      to_port     = 80
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
      description = "HTTP"
    },
    {
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
      description = "HTTPS"
    },
    {
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"] # Solo para desarrollo, restringir en producción
      description = "SSH"
    },
    {
      from_port   = 5432
      to_port     = 5432
      protocol    = "tcp"
      cidr_blocks = ["10.0.0.0/16"] # Solo dentro de la VPC
      description = "PostgreSQL"
    },
    {
      from_port   = 6379
      to_port     = 6379
      protocol    = "tcp"
      cidr_blocks = ["10.0.0.0/16"] # Solo dentro de la VPC
      description = "Redis"
    }
  ]
}

variable "egress_rules" {
  description = "List of egress rules for the security group"
  type        = list(object({
    from_port   = number
    to_port     = number
    protocol    = string
    cidr_blocks = list(string)
    description = string
  }))
  default     = [
    {
      from_port   = 0
      to_port     = 0
      protocol    = "-1"
      cidr_blocks = ["0.0.0.0/0"]
      description = "All outbound traffic"
    }
  ]
}

variable "iam_role_name" {
  description = "Name of the IAM role for EC2 instances"
  type        = string
  default     = "smgi-ec2-role"
}

variable "iam_policy_name" {
  description = "Name of the IAM policy for EC2 instances"
  type        = string
  default     = "smgi-ec2-policy"
}

variable "secrets_manager_secret_name" {
  description = "Name of the Secrets Manager secret"
  type        = string
  default     = "smgi/secrets"
}

# --- MEJORA: Variables Misceláneas ---
variable "environment" {
  description = "Environment (development, staging, production)"
  type        = string
  default     = "development"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "SMGI Backend"
}

variable "owner" {
  description = "Owner of the project"
  type        = string
  default     = "IIAP - Instituto de Investigaciones de la Amazonía Peruana"
}

variable "cost_center" {
  description = "Cost center for billing purposes"
  type        = string
  default     = "SMGI-DEV"
}
