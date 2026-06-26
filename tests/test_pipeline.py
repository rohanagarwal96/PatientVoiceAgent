from pathlib import Path
from unittest.mock import call, patch


def test_pipeline_calls_all_steps():
    with (
        patch("src.pipeline.place_call", return_value="CAtest123") as mock_place,
        patch("src.pipeline.fetch_recording", return_value=Path("recordings/test.mp3")) as mock_fetch,
        patch(
            "src.pipeline.transcribe",
            return_value=(Path("transcripts/test.txt"), Path("transcripts/test.json")),
        ) as mock_transcribe,
        patch("src.pipeline.evaluate") as mock_evaluate,
    ):
        from src.pipeline import run_pipeline

        run_pipeline("01_simple_scheduling", run_eval=True)

    mock_place.assert_called_once_with("01_simple_scheduling")
    mock_fetch.assert_called_once_with("CAtest123", "01_simple_scheduling")
    mock_transcribe.assert_called_once_with(Path("recordings/test.mp3"))
    mock_evaluate.assert_called_once_with(Path("transcripts/test.json"), "01_simple_scheduling")


def test_pipeline_skips_evaluator_when_disabled():
    with (
        patch("src.pipeline.place_call", return_value="CAtest123"),
        patch("src.pipeline.fetch_recording", return_value=Path("recordings/test.mp3")),
        patch(
            "src.pipeline.transcribe",
            return_value=(Path("transcripts/test.txt"), Path("transcripts/test.json")),
        ),
        patch("src.pipeline.evaluate") as mock_evaluate,
    ):
        from src.pipeline import run_pipeline

        run_pipeline("01_simple_scheduling", run_eval=False)

    mock_evaluate.assert_not_called()
