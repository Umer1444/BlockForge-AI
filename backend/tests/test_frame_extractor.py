
from unittest.mock import MagicMock, patch

from unittest.mock import patch

import pytest


from core.frame_extractor import FrameExtractor



def test_extract_audio_encodes_as_aac(tmp_path):
    extractor = FrameExtractor(str(tmp_path / "video.mp4"), "test-job")

    mock_result = MagicMock()
    mock_result.returncode = 0

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

