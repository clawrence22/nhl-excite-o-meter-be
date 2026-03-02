variable "aws_region" {
  description = "AWS region for all resources."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project prefix for resource names."
  type        = string
  default     = "nhl-excite-o-meter-network"
}

variable "environment" {
  description = "Environment tag."
  type        = string
  default     = "prod"
}

variable "vpc_cidr" {
  description = "VPC CIDR."
  type        = string
  default     = "10.20.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "Public subnet CIDRs (at least 2)."
  type        = list(string)
  default     = ["10.20.0.0/24", "10.20.1.0/24"]
}

variable "private_app_subnet_cidrs" {
  description = "Private app subnet CIDRs (at least 2)."
  type        = list(string)
  default     = ["10.20.10.0/24", "10.20.11.0/24"]
}

variable "private_db_subnet_cidrs" {
  description = "Private DB subnet CIDRs (at least 2)."
  type        = list(string)
  default     = ["10.20.20.0/24", "10.20.21.0/24"]
}

variable "service_connect_namespace_name" {
  description = "Cloud Map HTTP namespace name for ECS Service Connect."
  type        = string
  default     = ""
}
