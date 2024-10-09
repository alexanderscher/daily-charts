resource "aws_scheduler_schedule" "spotify_charts_schedule" {
  name       = "spotify-charts-schedule"
  group_name = "default"

  flexible_time_window {
    mode = "OFF"
  }

  # Run at 8 AM every day in America/Los_Angeles timezone
  schedule_expression          = "cron(0 8 * * ? *)"
  schedule_expression_timezone = "America/Los_Angeles"

  target {
    arn      = "arn:aws:lambda:us-east-1:742736545134:function:spotify-charts"
    role_arn = aws_iam_role.charts_scheduler_role.arn
  }
}
