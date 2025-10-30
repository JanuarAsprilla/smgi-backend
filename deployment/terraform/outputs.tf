# deployment/terraform/outputs.tf
/*
SMGI Backend - Terraform Outputs
Sistema de Monitoreo Geoespacial Inteligente
Salidas de valores importantes de la infraestructura provisionada con Terraform
*/

# --- MEJORA: Salidas de Red ---
output "vpc_id" {
  value       = aws_vpc.smgi_vpc.id
  description = "ID of the VPC"
}

output "public_subnet_ids" {
  value       = aws_subnet.public_subnets[*].id
  description = "IDs of the public subnets"
}

output "private_subnet_ids" {
  value       = aws_subnet.private_subnets[*].id
  description = "IDs of the private subnets"
}

output "security_group_id" {
  value       = aws_security_group.smgi_sg.id
  description = "ID of the main security group"
}

# --- MEJORA: Salidas de Base de Datos ---
output "db_endpoint" {
  value       = aws_db_instance.smgi_db.endpoint
  description = "Endpoint of the RDS instance"
}

output "db_username" {
  value       = aws_db_instance.smgi_db.username
  description = "Username for the RDS instance"
  sensitive   = true # Marcar como sensible si se expone
}

output "db_name" {
  value       = aws_db_instance.smgi_db.db_name
  description = "Name of the database in the RDS instance"
}

# --- MEJORA: Salidas de Caché/Mensajería ---
output "redis_endpoint" {
  value       = aws_elasticache_cluster.smgi_redis.cache_nodes[0].address
  description = "Endpoint of the ElastiCache cluster"
}

output "redis_port" {
  value       = aws_elasticache_cluster.smgi_redis.port
  description = "Port of the ElastiCache cluster"
}

# --- MEJORA: Salidas de Almacenamiento ---
output "s3_bucket_name" {
  value       = aws_s3_bucket.smgi_static_media.bucket
  description = "Name of the S3 bucket"
}

output "s3_bucket_arn" {
  value       = aws_s3_bucket.smgi_static_media.arn
  description = "ARN of the S3 bucket"
}

# --- MEJORA: Salidas de Balanceador de Carga ---
output "alb_dns_name" {
  value       = aws_lb.smgi_alb.dns_name
  description = "DNS name of the Application Load Balancer"
}

output "alb_zone_id" {
  value       = aws_lb.smgi_alb.zone_id
  description = "Zone ID of the Application Load Balancer"
}

# --- MEJORA: Salidas de Certificado SSL ---
output "certificate_arn" {
  value       = var.certificate_arn != "" ? var.certificate_arn : aws_acm_certificate.smgi_cert[0].arn
  description = "ARN of the ACM certificate"
}

# --- MEJORA: Salidas de DNS ---
output "dns_record_name" {
  value       = var.hosted_zone_id != "" ? aws_route53_record.smgi_dns[0].name : ""
  description = "Name of the Route 53 DNS record"
}

output "dns_record_type" {
  value       = var.hosted_zone_id != "" ? aws_route53_record.smgi_dns[0].type : ""
  description = "Type of the Route 53 DNS record"
}

# --- MEJORA: Salidas de Monitoreo ---
output "cloudwatch_log_group_names" {
  value = [
    aws_cloudwatch_log_group.smgi_django_logs.name,
    aws_cloudwatch_log_group.smgi_celery_logs.name,
    aws_cloudwatch_log_group.smgi_nginx_logs.name
  ]
  description = "Names of the CloudWatch log groups"
}

# --- MEJORA: Salidas de Seguridad ---
output "iam_role_name" {
  value       = aws_iam_role.smgi_ec2_role.name
  description = "Name of the IAM role for EC2 instances"
}

output "iam_policy_arn" {
  value       = aws_iam_policy.smgi_ec2_policy.arn
  description = "ARN of the IAM policy for EC2 instances"
}

output "secrets_manager_secret_arn" {
  value       = aws_secretsmanager_secret.smgi_secrets.arn
  description = "ARN of the Secrets Manager secret"
  sensitive   = true # Marcar como sensible ya que contiene ARN de secretos
}

# --- MEJORA: Salidas Adicionales ---
# output "eks_cluster_name" {
#   value       = aws_eks_cluster.smgi_eks.name
#   description = "Name of the EKS cluster"
# }

# output "ecs_cluster_name" {
#   value       = aws_ecs_cluster.smgi_ecs.name
#   description = "Name of the ECS cluster"
# }

# output "lambda_function_names" {
#   value = [
#     aws_lambda_function.smgi_task_processor.function_name,
#     aws_lambda_function.smgi_alert_handler.function_name
#   ]
#   description = "Names of the Lambda functions"
# }

# output "sns_topic_arns" {
#   value = [
#     aws_sns_topic.smgi_alerts.arn,
#     aws_sns_topic.smgi_notifications.arn
#   ]
#   description = "ARNs of the SNS topics"
# }

# output "sqs_queue_urls" {
#   value = [
#     aws_sqs_queue.smgi_alerts_queue.url,
#     aws_sqs_queue.smgi_notifications_queue.url
#   ]
#   description = "URLs of the SQS queues"
# }
