


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

from unittest.mock import MagicMock, patch


from unittest.mock import patch, MagicMock


from unittest.mock import patch

import pytest


from core.frame_extractor import FrameExtractor




def test_extract_audio_encodes_as_aac(tmp_path):
    extractor = FrameExtractor(str(tmp_path / "video.mp4"), "test-job")

    mock_result = MagicMock()
    mock_result.returncode = 0

def test_extract_all_frames_removes_stale_frames_before_extraction(tmp_path):
    extractor = FrameExtractor(str(tmp_path / "video.mp4"), "test-job")

    stale_frame_1 = extractor.frames_dir / "frame_000000.png"
    stale_frame_2 = extractor.frames_dir / "frame_000001.png"
    unrelated_file = extractor.frames_dir / "keep.txt"

    stale_frame_1.touch()
    stale_frame_2.touch()
    unrelated_file.touch()

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stderr = ""


    with patch(
        "core.frame_extractor.subprocess.run",
        return_value=mock_result,

    ) as mock_run:
        extractor.extract_audio()

    cmd = mock_run.call_args.args[0]

    assert "-acodec" in cmd
    assert cmd[cmd.index("-acodec") + 1] == "aac"
    assert "copy" not in cmd

def test_extract_all_frames_rejects_end_before_start(tmp_path):

    ):
        extractor.extract_all_frames()

    assert not stale_frame_1.exists()
    assert not stale_frame_2.exists()

    # Non-frame files should not be removed.
    assert unrelated_file.exists()
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

