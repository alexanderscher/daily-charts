resource "aws_iam_role" "charts_role" {
  name = "charts-role"

  assume_role_policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [{
      "Action" : "sts:AssumeRole",
      "Effect" : "Allow",
      "Principal" : {
        "Service" : "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "charts_policy" {
  name = "charts-policy"
  role = aws_iam_role.charts_role.id

  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Action" : "ses:SendEmail",
        "Resource" : "arn:aws:ses:us-east-1:742736545134:identity/*"
      },
      {
        "Effect" : "Allow",
        "Action" : [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        "Resource" : "*"
      }
    ]
  })
}

resource "aws_iam_role" "charts_scheduler_role" {
  name = "charts-scheduler-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = {
        Service = "scheduler.amazonaws.com"
      },
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "charts_scheduler_policy" {
  name = "charts-scheduler-policy"
  role = aws_iam_role.charts_scheduler_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect   = "Allow",
      Action   = "lambda:InvokeFunction",
      Resource = "arn:aws:lambda:us-east-1:742736545134:function:*"
    }]
  })
}

resource "aws_iam_role_policy" "allow_lambda_access_to_secrets" {
  name = "AllowLambdaAccessToSecrets"
  role = aws_iam_role.charts_role.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = aws_secretsmanager_secret.google_private_key.arn
      }
    ]
  })
}



resource "aws_iam_role_policy" "charts_invoke_policy" {
  name = "charts-invoke-policy"
  role = aws_iam_role.charts_role.id
  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Action" : "lambda:InvokeFunction",
        "Resource" : "*"
      },
      {
        "Effect" : "Allow",
        "Action" : "ses:SendEmail",
        "Resource" : "arn:aws:ses:us-east-1:742736545134:identity/*"
      },
      {
        "Effect" : "Allow",
        "Action" : [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        "Resource" : "*"
      }
    ]
  })
}
