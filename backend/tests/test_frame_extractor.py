
from unittest.mock import patch, MagicMock

from unittest.mock import patch

import pytest


from core.frame_extractor import FrameExtractor


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
