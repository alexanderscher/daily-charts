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
# IAM policy for the scheduler role to invoke the Lambda function

resource "aws_iam_role_policy" "charts_scheduler_policy" {
  name = "charts-scheduler-policy"
  role = aws_iam_role.charts_scheduler_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect   = "Allow",
      Action   = "lambda:InvokeFunction",
      Resource = "arn:aws:lambda:us-east-1:742736545134:function:spotify-charts"
    }]
  })
}
