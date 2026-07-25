from unittest.mock import MagicMock, patch

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