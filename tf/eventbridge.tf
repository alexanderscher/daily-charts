# schedule_expression          = "cron(0 7 * * ? *)"
#   schedule_expression          = "cron(35 18 15 10 ? 2024)"

resource "aws_scheduler_schedule" "spotify_charts_schedule" {
  name       = "spotify-charts-schedule"
  group_name = "default"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression          = "cron(0 8 * * ? *)"
  schedule_expression_timezone = "America/Los_Angeles"

  target {
    arn      = "arn:aws:lambda:us-east-1:742736545134:function:spotify-charts"
    role_arn = aws_iam_role.charts_scheduler_role.arn
  }
}

resource "aws_scheduler_schedule" "velocity_schedule" {
  name       = "velocity-schedule"
  group_name = "default"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression          = "cron(0 7 * * ? *)"
  schedule_expression_timezone = "America/Los_Angeles"

  target {
    arn      = "arn:aws:lambda:us-east-1:742736545134:function:velocity"
    role_arn = aws_iam_role.charts_scheduler_role.arn
  }
}


resource "aws_scheduler_schedule" "apple_schedule" {
  name       = "apple-schedule"
  group_name = "default"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression          = "cron(0 7 * * ? *)"
  schedule_expression_timezone = "America/Los_Angeles"

  target {
    arn      = "arn:aws:lambda:us-east-1:742736545134:function:apple-charts"
    role_arn = aws_iam_role.charts_scheduler_role.arn
  }
}


resource "aws_scheduler_schedule" "shazam_schedule" {
  name       = "shazam-schedule"
  group_name = "default"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression          = "cron(0 7 * * ? *)"
  schedule_expression_timezone = "America/Los_Angeles"

  target {
    arn      = "arn:aws:lambda:us-east-1:742736545134:function:shazam-charts"
    role_arn = aws_iam_role.charts_scheduler_role.arn
  }
}


resource "aws_scheduler_schedule" "shazam_city_schedule" {
  name       = "shazam-city-schedule"
  group_name = "default"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression          = "cron(0 7 * * ? *)"
  schedule_expression_timezone = "America/Los_Angeles"

  target {
    arn      = "arn:aws:lambda:us-east-1:742736545134:function:shazam-city-charts"
    role_arn = aws_iam_role.charts_scheduler_role.arn
  }
}

resource "aws_scheduler_schedule" "shazam_discovery_schedule" {
  name       = "shazam-discovery-schedule"
  group_name = "default"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression          = "cron(0 7 * * ? *)"
  schedule_expression_timezone = "America/Los_Angeles"

  target {
    arn      = "arn:aws:lambda:us-east-1:742736545134:function:shazam-discovery-charts"
    role_arn = aws_iam_role.charts_scheduler_role.arn
  }
}



resource "aws_scheduler_schedule" "genius_schedule" {
  name       = "genius-schedule"
  group_name = "default"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression          = "cron(0 7 * * ? *)"
  schedule_expression_timezone = "America/Los_Angeles"

  target {
    arn      = "arn:aws:lambda:us-east-1:742736545134:function:genius-charts"
    role_arn = aws_iam_role.charts_scheduler_role.arn
  }
}



resource "aws_scheduler_schedule" "no_track_schedule" {
  name       = "no-track-schedule"
  group_name = "default"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression          = "cron(0 6 * * ? *)"
  schedule_expression_timezone = "America/Los_Angeles"

  target {
    arn      = "arn:aws:lambda:us-east-1:742736545134:function:no-track"
    role_arn = aws_iam_role.charts_scheduler_role.arn
  }
}
