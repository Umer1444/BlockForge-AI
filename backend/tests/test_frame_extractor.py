
import pytest

from core.frame_extractor import FrameExtractor
def test_init_rejects_missing_video_file(tmp_path):
    missing_video = tmp_path / "missing.mp4"

    with pytest.raises(
        FileNotFoundError,
        match="Video file does not exist",
    ):
        FrameExtractor(str(missing_video), "test-job")
def test_init_rejects_directory_as_video_path(tmp_path):
    video_directory = tmp_path / "video"
    video_directory.mkdir()

    with pytest.raises(
        ValueError,
        match="Video path is not a file",
    ):
        FrameExtractor(str(video_directory), "test-job")
def test_init_accepts_existing_video_file(tmp_path):
    video_file = tmp_path / "video.mp4"
    video_file.touch()

    extractor = FrameExtractor(str(video_file), "test-job")

    assert extractor.video_path == video_file

from unittest.mock import patch

import pytest

from core.frame_extractor import FrameExtractor


def test_extract_all_frames_rejects_end_before_start(tmp_path):
    extractor = FrameExtractor(str(tmp_path / "video.mp4"), "test-job")

    with patch("core.frame_extractor.subprocess.run") as mock_run:
        with pytest.raises(
            ValueError,
            match="end_time must be greater than start_time",
        ):
            extractor.extract_all_frames(start_time=10, end_time=5)

        mock_run.assert_not_called()


def test_extract_all_frames_rejects_equal_start_and_end(tmp_path):
    extractor = FrameExtractor(str(tmp_path / "video.mp4"), "test-job")

    with patch("core.frame_extractor.subprocess.run") as mock_run:
        with pytest.raises(
            ValueError,
            match="end_time must be greater than start_time",
        ):
            extractor.extract_all_frames(start_time=10, end_time=10)

        mock_run.assert_not_called()

