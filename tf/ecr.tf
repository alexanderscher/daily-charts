resource "aws_ecr_repository" "spotify_charts_ecr" {
  name = "spotify-charts-ecr"
}


data "aws_ecr_image" "spotify_charts_ecr" {
  repository_name = aws_ecr_repository.spotify_charts_ecr.name
  image_tag       = "latest"
}


resource "aws_ecr_repository" "velocity_ecr" {
  name = "velocity-ecr"
}

data "aws_ecr_image" "velocity_ecr" {
  repository_name = aws_ecr_repository.velocity_ecr.name
  image_tag       = "latest"
}


resource "aws_ecr_repository" "apple_charts_ecr" {
  name = "apple-charts-ecr"
}

data "aws_ecr_image" "apple_charts_ecr" {
  repository_name = aws_ecr_repository.apple_charts_ecr.name
  image_tag       = "latest"
}

resource "aws_ecr_repository" "shazam_charts_ecr" {
  name = "shazam-charts-ecr"
}

data "aws_ecr_image" "shazam_charts_ecr" {
  repository_name = aws_ecr_repository.shazam_charts_ecr.name
  image_tag       = "latest"
}


resource "aws_ecr_repository" "genius_charts_ecr" {
  name = "genius-charts-ecr"
}

data "aws_ecr_image" "genius_charts_ecr" {
  repository_name = aws_ecr_repository.genius_charts_ecr.name
  image_tag       = "latest"
}

resource "aws_ecr_repository" "no_track_ecr" {
  name = "no-track-ecr"
}

data "aws_ecr_image" "no_track_ecr" {
  repository_name = aws_ecr_repository.no_track_ecr.name
  image_tag       = "latest"
}

