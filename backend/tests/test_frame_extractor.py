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