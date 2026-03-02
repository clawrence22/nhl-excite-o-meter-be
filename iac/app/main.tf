terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  tags = {
    Project     = var.project_name
    ManagedBy   = "terraform"
    Environment = var.environment
  }
}

data "aws_caller_identity" "current" {}

resource "aws_security_group" "alb" {
  name        = "${var.project_name}-alb-sg"
  description = "ALB security group"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, {
    Name = "${var.project_name}-alb-sg"
  })
}

resource "aws_security_group" "ecs_service" {
  name        = "${var.project_name}-ecs-sg"
  description = "ECS service security group"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = var.app_port
    to_port         = var.app_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, {
    Name = "${var.project_name}-ecs-sg"
  })
}

resource "aws_lb" "app" {
  name               = substr(replace("${var.project_name}-alb", "_", "-"), 0, 32)
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnet_ids

  tags = merge(local.tags, {
    Name = "${var.project_name}-alb"
  })
}

resource "aws_lb_target_group" "app" {
  name        = substr(replace("${var.project_name}-tg", "_", "-"), 0, 32)
  port        = var.app_port
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id

  health_check {
    enabled             = true
    path                = var.health_check_path
    healthy_threshold   = 3
    unhealthy_threshold = 3
    matcher             = "200-299"
    timeout             = var.health_check_timeout_seconds
    interval            = var.health_check_interval_seconds
  }

  tags = merge(local.tags, {
    Name = "${var.project_name}-tg"
  })
}

resource "aws_lb_listener" "http_forward" {
  load_balancer_arn = aws_lb.app.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = var.log_retention_days

  tags = local.tags
}

resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"

  tags = local.tags
}

resource "aws_iam_role" "ecs_task_execution" {
  name = "${var.project_name}-ecs-task-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })

  tags = local.tags
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_managed" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ecs_task_execution_secrets" {
  name = "${var.project_name}-ecs-task-exec-secrets"
  role = aws_iam_role.ecs_task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "secretsmanager:GetSecretValue",
        "kms:Decrypt"
      ]
      Resource = [
        var.db_secret_arn
      ]
    }]
  })
}

resource "aws_iam_role" "ecs_task" {
  name = "${var.project_name}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })

  tags = local.tags
}

resource "aws_iam_role_policy" "ecs_task_db_connect" {
  name = "${var.project_name}-ecs-task-db-connect"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "rds-db:connect"
      ]
      Resource = [
        "arn:aws:rds-db:${var.aws_region}:${data.aws_caller_identity.current.account_id}:dbuser/${var.db_resource_id}/${var.db_iam_username}"
      ]
    }]
  })
}

resource "aws_ecs_task_definition" "app" {
  family                   = "${var.project_name}-task"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = tostring(var.ecs_task_cpu)
  memory                   = tostring(var.ecs_task_memory)
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = var.project_name
      image     = var.app_image
      essential = true
      portMappings = [
        {
          name          = "app"
          containerPort = var.app_port
          hostPort      = var.app_port
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
      secrets = [
        { name = "DB_HOST", valueFrom = "${var.db_secret_arn}:host::" },
        { name = "DB_PORT", valueFrom = "${var.db_secret_arn}:port::" },
        { name = "DB_NAME", valueFrom = "${var.db_secret_arn}:dbname::" },
        { name = "DB_USER", valueFrom = "${var.db_secret_arn}:username::" },
        { name = "DB_PASSWORD", valueFrom = "${var.db_secret_arn}:password::" }
      ]
      environment = [
        { name = "FLASK_ENV", value = var.flask_env },
        { name = "PYTHONUNBUFFERED", value = "1" },
        { name = "DB_IAM_AUTH", value = "true" },
        { name = "DB_REGION", value = var.aws_region },
        { name = "DB_SSLMODE", value = "require" }
      ]
    }
  ])

  lifecycle {
    precondition {
      condition     = var.vpc_id != "" && length(var.public_subnet_ids) > 0 && length(var.private_app_subnet_ids) > 0
      error_message = "Set vpc_id, public_subnet_ids, and private_app_subnet_ids from network stack outputs."
    }
    precondition {
      condition     = var.db_secret_arn != ""
      error_message = "Set db_secret_arn from your DB repo output."
    }
    precondition {
      condition     = var.db_resource_id != ""
      error_message = "Set db_resource_id from your DB repo output."
    }
  }

  tags = local.tags
}

resource "aws_ecs_service" "app" {
  name            = "${var.project_name}-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.ecs_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_app_subnet_ids
    security_groups  = [aws_security_group.ecs_service.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = var.project_name
    container_port   = var.app_port
  }

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200

  service_connect_configuration {
    enabled   = true
    namespace = var.service_connect_namespace_arn

    service {
      discovery_name = var.project_name
      port_name      = "app"

      client_alias {
        dns_name = var.project_name
        port     = var.app_port
      }
    }
  }

  depends_on = [
    aws_lb_listener.http_forward
  ]

  tags = local.tags
}
