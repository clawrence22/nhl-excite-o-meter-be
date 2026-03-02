output "alb_dns_name" {
  description = "Public DNS name of the application load balancer."
  value       = aws_lb.app.dns_name
}

output "alb_zone_id" {
  description = "Route53 zone ID of the ALB (use for alias records)."
  value       = aws_lb.app.zone_id
}

output "ecs_cluster_name" {
  description = "ECS cluster name."
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "ECS service name."
  value       = aws_ecs_service.app.name
}

output "ecs_service_security_group_id" {
  description = "Security group ID attached to ECS tasks. Use this in DB repo SG rule for inbound 5432."
  value       = aws_security_group.ecs_service.id
}

output "db_secret_arn_in_use" {
  description = "DB secret ARN consumed by ECS task definition."
  value       = var.db_secret_arn
}
