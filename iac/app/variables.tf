variable "aws_region" {
  description = "AWS region for all resources."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project prefix for resource names."
  type        = string
  default     = "nhl-excite-o-meter-be"
}

variable "environment" {
  description = "Environment tag."
  type        = string
  default     = "prod"
}

variable "vpc_id" {
  description = "VPC ID from network stack outputs."
  type        = string
  default     = ""
}

variable "public_subnet_ids" {
  description = "Public subnet IDs from network stack outputs."
  type        = list(string)
  default     = []
}

variable "private_app_subnet_ids" {
  description = "Private app subnet IDs from network stack outputs."
  type        = list(string)
  default     = []
}

variable "service_connect_namespace_arn" {
  description = "Cloud Map namespace ARN from network stack output for ECS Service Connect."
  type        = string
  default     = ""
}

variable "app_image" {
  description = "Container image URI in ECR."
  type        = string
  default     = "871806636838.dkr.ecr.us-east-1.amazonaws.com/nhl-excit-o-meter-be:1.0.0"
}

variable "app_port" {
  description = "Container and target group port."
  type        = number
  default     = 5001
}

variable "health_check_path" {
  description = "ALB target group health check path."
  type        = string
  default     = "/healthz"
}

variable "health_check_interval_seconds" {
  description = "ALB target group health check interval in seconds."
  type        = number
  default     = 5
}

variable "health_check_timeout_seconds" {
  description = "ALB target group health check timeout in seconds."
  type        = number
  default     = 2
}

variable "ecs_task_cpu" {
  description = "Fargate task CPU units."
  type        = number
  default     = 256
}

variable "ecs_task_memory" {
  description = "Fargate task memory (MiB)."
  type        = number
  default     = 512
}

variable "ecs_desired_count" {
  description = "Desired ECS service task count."
  type        = number
  default     = 1
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention in days."
  type        = number
  default     = 30
}

variable "flask_env" {
  description = "Flask runtime environment."
  type        = string
  default     = "production"
}

variable "db_secret_arn" {
  description = "Secrets Manager secret ARN from DB repo. Secret JSON must include host, port, dbname, username, password."
  type        = string
  default     = ""
}

variable "db_iam_username" {
  description = "Database username the app uses with IAM auth."
  type        = string
  default     = "app_iam"
}

variable "db_resource_id" {
  description = "RDS DB resource ID from DB repo (required for IAM auth policy)."
  type        = string
  default     = ""
}
