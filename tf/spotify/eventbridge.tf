resource "aws_scheduler_schedule" "spotify_charts_schedule" {
  name       = "spotify-charts-schedule"
  group_name = "default"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression          = "cron(0 7 * * ? *)"
  schedule_expression_timezone = "America/Los_Angeles"

  target {
    arn      = "arn:aws:lambda:us-east-1:742736545134:function:spotify-charts"
    role_arn = aws_iam_role.charts_scheduler_role.arn
  }
}


resource "aws_scheduler_schedule" "veloctiy_schedule" {
  name       = "velocity-schedule"
  group_name = "default"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression          = "cron(20 16 09 10 ? 2024)"
  schedule_expression_timezone = "America/Los_Angeles"

  target {
    arn      = "arn:aws:lambda:us-east-1:742736545134:function:velocity"
    role_arn = aws_iam_role.store_turn_scheduler_role.arn
  }
}
