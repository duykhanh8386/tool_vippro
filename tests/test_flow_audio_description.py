import inspect
import json
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from nicegui import Client, ui
from nicegui.page import page

from src.module.audio_module import AudioUpdateError, UpdateAudioModule
from web.components import add_audio_flow as flow


INPUT_LANGUAGE_CODES = (
    "en-AU en-CA en-IN en-IE en-GB en-US pt pt-BR pt-PT "
    "es es-419 es-MX es-ES es-US fr"
)


class FlowAudioDescriptionTests(unittest.IsolatedAsyncioTestCase):
    async def test_uploads_full_matching_music_for_source_and_each_dubbed_language(self):
        with tempfile.TemporaryDirectory() as folder:
            for index, language in enumerate(("pcm", "vi")):
                music = Path(folder) / f"original-{index}.mp3"
                music.write_bytes(f"full-music-{index}".encode())
                item = {
                    "video_id": f"video-{index}", "music_path": str(music),
                    "audio_path": str(Path(folder) / "intermittent-3-7.m4v"),
                }
                info = SimpleNamespace(id=item["video_id"], audio_language=language, duration_ms=60500)
                guard = threading.Lock()
                upload_paths = []
                uploaded_languages = []

                def prepare(**kwargs):
                    self.assertEqual(kwargs["input_file"], str(music))
                    self.assertEqual(kwargs["video_duration_seconds"], 60.5)
                    Path(kwargs["output_file"]).write_bytes(music.read_bytes())

                def upload(**kwargs):
                    self.assertEqual(kwargs["id_video"], item["video_id"])
                    uploaded_languages.append(kwargs["language"])
                    self.assertEqual(kwargs["channel_id"], "channel")
                    self.assertEqual(kwargs["file_name"], str(music))
                    self.assertEqual(kwargs["audio_content_type"], "descriptive")
                    upload_paths.append(Path(kwargs["upload_path"]))
                    self.assertEqual(upload_paths[-1].read_bytes(), music.read_bytes())
                    self.assertTrue(guard.locked())
                    return 200

                with (
                    patch.object(flow.upload_video_module, "_get_video_info", return_value=info),
                    patch.object(flow, "multiply_audio", side_effect=prepare) as render,
                    patch.object(flow, "get_audio_mutation_guard", return_value=guard),
                    patch.object(flow.update_audio_module, "add", side_effect=upload) as add,
                ):
                    self.assertEqual(await flow._add_flow_audio_description(
                        item, "channel", Mock(), languages=["en", "es", language.upper(), "en"],
                    ), language)
                self.assertEqual(uploaded_languages, [language, "en", "es"])
                self.assertEqual(add.call_count, 3)
                render.assert_called_once()
                self.assertEqual(len(set(upload_paths)), 1)
                self.assertFalse(guard.locked())
                self.assertFalse(upload_paths[0].exists())

    async def test_failed_upload_releases_guard_and_deletes_temporary_audio(self):
        with tempfile.TemporaryDirectory() as folder:
            music = Path(folder) / "original.mp3"
            music.write_bytes(b"full-music")
            guard = threading.Lock()
            paths = []

            def prepare(**kwargs):
                paths.append(Path(kwargs["output_file"]))

            with (
                patch.object(flow.upload_video_module, "_get_video_info", return_value=SimpleNamespace(
                    id="video", audio_language="pcm", duration_ms=60000,
                )),
                patch.object(flow, "multiply_audio", side_effect=prepare),
                patch.object(flow, "get_audio_mutation_guard", return_value=guard),
                patch.object(flow.update_audio_module, "add", side_effect=AudioUpdateError("rejected")),
            ):
                with self.assertRaisesRegex(RuntimeError, "rejected"):
                    await flow._add_flow_audio_description(
                        {"video_id": "video", "music_path": str(music)}, "channel", Mock(),
                    )
            self.assertFalse(guard.locked())
            self.assertFalse(paths[0].exists())

    async def test_partial_failure_continues_and_retry_only_uploads_the_failed_language(self):
        with tempfile.TemporaryDirectory() as folder:
            music = Path(folder) / "original.mp3"
            music.write_bytes(b"full-music")
            item = {"video_id": "video", "music_path": str(music)}
            uploaded = []
            checkpoints = []
            upload_paths = []
            guard = threading.Lock()

            def upload(**kwargs):
                lang = kwargs["language"]
                uploaded.append(lang)
                upload_paths.append(Path(kwargs["upload_path"]))
                if lang == "en" and uploaded.count("en") == 1:
                    raise AudioUpdateError("rejected")
                return 409 if lang == "es" else 200

            def persist():
                checkpoints.append(json.loads(json.dumps(item["audio_description_results"])))
                return True

            with (
                patch.object(flow.upload_video_module, "_get_video_info", return_value=SimpleNamespace(
                    id="video", audio_language="pcm", duration_ms=60000,
                )),
                patch.object(flow, "multiply_audio"),
                patch.object(flow, "get_audio_mutation_guard", return_value=guard),
                patch.object(flow.update_audio_module, "add", side_effect=upload),
            ):
                with self.assertRaisesRegex(RuntimeError, "en: rejected"):
                    await flow._add_flow_audio_description(
                        item, "channel", Mock(), languages=["en", "es"], persist=persist,
                    )
                self.assertEqual(uploaded, ["pcm", "en", "es"])
                self.assertEqual(checkpoints[0]["pcm"]["status"], "successful")
                self.assertEqual(checkpoints[-1]["es"]["status"], "already_added")
                self.assertEqual(checkpoints[-1]["en"]["status"], "unsuccessful")
                self.assertFalse(guard.locked())
                self.assertFalse(upload_paths[0].exists())
                item = json.loads(json.dumps(item))
                await flow._add_flow_audio_description(
                    item, "channel", Mock(), languages=["en", "es"], persist=persist,
                )
            self.assertEqual(uploaded, ["pcm", "en", "es", "en"])
            self.assertEqual(item["audio_description_results"]["en"]["status"], "successful")
            self.assertFalse(guard.locked())
            self.assertTrue(all(not path.exists() for path in upload_paths))

    async def test_failed_checkpoint_blocks_the_next_language(self):
        with tempfile.TemporaryDirectory() as folder:
            music = Path(folder) / "original.mp3"
            music.touch()
            guard = threading.Lock()
            with (
                patch.object(flow.upload_video_module, "_get_video_info", return_value=SimpleNamespace(
                    id="video", audio_language="pcm", duration_ms=60000,
                )),
                patch.object(flow, "multiply_audio"),
                patch.object(flow, "get_audio_mutation_guard", return_value=guard),
                patch.object(flow.update_audio_module, "add", return_value=200) as upload,
            ):
                with self.assertRaisesRegex(RuntimeError, "checkpoint"):
                    await flow._add_flow_audio_description(
                        {"video_id": "video", "music_path": str(music)}, "channel", Mock(),
                        languages=["en", "es"], persist=lambda: False,
                    )
                upload.assert_called_once()
                self.assertEqual(upload.call_args.kwargs["language"], "pcm")
            self.assertFalse(guard.locked())

    def test_progress_migration_preserves_source_and_reopens_only_missing_language_steps(self):
        item = {
            "steps": dict.fromkeys(("merge", "upload", "wait", "add_audio", "add_description"), "successful"),
            "audio_description_language": "pcm",
            "audio_language_results": {"en": {"status": "successful"}, "es": {"status": "already_added"}},
        }
        self.assertTrue(flow._restore_flow_audio_progress(item, ["en", "es"]))
        self.assertEqual(item["audio_description_results"]["pcm"]["status"], "successful")
        self.assertEqual(item["steps"]["add_description"], "pending")
        self.assertEqual(item["steps"]["add_audio"], "successful")
        self.assertTrue(all(item["steps"][step] == "successful" for step in ("merge", "upload", "wait")))
        item["audio_description_results"].update({
            "en": {"status": "successful"}, "es": {"status": "already_added"},
        })
        item["steps"]["add_description"] = "successful"
        self.assertFalse(flow._restore_flow_audio_progress(item, ["en", "es"]))
        self.assertTrue(flow._restore_flow_audio_progress(item, ["en", "es", "de"]))
        self.assertEqual(item["steps"]["add_audio"], "pending")
        self.assertEqual(item["steps"]["add_description"], "pending")
        self.assertTrue(all(item["steps"][step] == "successful" for step in ("merge", "upload", "wait")))

    async def test_completed_descriptions_do_not_render_or_upload_again(self):
        with tempfile.TemporaryDirectory() as folder:
            music = Path(folder) / "original.mp3"
            music.touch()
            item = {
                "video_id": "video", "music_path": str(music),
                "audio_description_language": "pcm",
                "audio_description_results": {
                    lang: {"status": "successful"} for lang in ("pcm", "en", "es")
                },
            }
            with (
                patch.object(flow.upload_video_module, "_get_video_info", return_value=SimpleNamespace(
                    id="video", audio_language="pcm", duration_ms=60000,
                )),
                patch.object(flow, "multiply_audio") as render,
                patch.object(flow.update_audio_module, "add") as upload,
            ):
                await flow._add_flow_audio_description(item, "channel", Mock(), languages=["en", "es"])
                render.assert_not_called()
                upload.assert_not_called()

    async def test_unknown_source_language_or_wrong_video_cannot_upload(self):
        with tempfile.TemporaryDirectory() as folder:
            music = Path(folder) / "original.mp3"
            music.touch()
            for video_id, language, message in (
                ("video", "", "chưa có ngôn ngữ gốc"),
                ("another-video", "pcm", "đúng video"),
            ):
                with (
                    patch.object(flow.upload_video_module, "_get_video_info", return_value=SimpleNamespace(
                        id=video_id, audio_language=language, duration_ms=60000,
                    )),
                    patch.object(flow.update_audio_module, "get_original_audio_language", return_value=""),
                    patch.object(flow.update_audio_module, "add") as upload,
                ):
                    with self.assertRaisesRegex(RuntimeError, message):
                        await flow._add_flow_audio_description(
                            {"video_id": "video", "music_path": str(music)}, "channel", Mock(),
                        )
                    upload.assert_not_called()

    async def test_source_only_completed_flow_adds_each_missing_description_without_reupload(self):
        with tempfile.TemporaryDirectory() as folder:
            input_languages = flow.parse_language_codes(INPUT_LANGUAGE_CODES)
            root = Path(folder)
            (root / "video.mp4").touch()
            (root / "music.mp3").touch()
            saved = {
                "video_folder": folder, "music_folder": folder, "output_folder": folder,
                "selected_channel": "channel", "audio_language": INPUT_LANGUAGE_CODES,
                "statuses": {"video.mp4": {
                    "video_id": "video", "music_path": str(root / "music.mp3"),
                    "steps": dict.fromkeys(("merge", "upload", "wait", "add_audio", "add_description"), "successful"),
                    "audio_description_language": "pcm",
                    "audio_language_results": {
                        language: {"status": "successful"} for language in input_languages
                    },
                }},
            }
            channel = SimpleNamespace(id="channel", name="Channel", img_src="", owner_email="", overlay_png="")
            client = Client(page("/test-flow-description"), request=None)
            callbacks = []

            def timer(_interval, callback, **kwargs):
                if kwargs.get("once"):
                    callbacks.append(callback)
                return Mock()

            try:
                with (
                    patch.object(flow, "get_channels_info", side_effect=lambda cid=None: channel if cid else [channel]),
                    patch.object(flow, "state_manager") as state,
                    patch.object(flow, "get_video_duration", return_value=60),
                    patch.object(flow.ui, "timer", side_effect=timer),
                    patch.object(flow.ui, "notify"),
                    patch.object(flow.upload_video_module, "validate_session"),
                    patch.object(flow.upload_video_module, "upload") as upload,
                    patch.object(flow.upload_video_module, "_get_video_info", return_value=SimpleNamespace(
                        id="video", audio_language="pcm", duration_ms=60000,
                    )),
                    patch.object(flow, "multiply_audio"),
                    patch.object(flow.update_audio_module, "add", return_value=200) as add,
                    client,
                ):
                    state.load_state.return_value = saved
                    state.save_state.return_value = True
                    flow.create_add_audio_flow_page()
                    for callback in list(callbacks):
                        result = callback()
                        if inspect.isawaitable(result):
                            await result
                    button = next(element for element in client.elements.values()
                                  if isinstance(element, ui.button) and element.text == "Xử lý")
                    listener = next(listener for listener in button._event_listeners.values() if listener.type == "click")
                    await inspect.getclosurevars(listener.handler).nonlocals["callback"]()
                    upload.assert_not_called()
                    self.assertEqual(len(add.call_args_list), 15)
                    self.assertEqual([call.kwargs["language"] for call in add.call_args_list], input_languages)
                    self.assertTrue(all(call.kwargs["id_video"] == "video" for call in add.call_args_list))
                    self.assertTrue(all(call.kwargs["audio_content_type"] == "descriptive" for call in add.call_args_list))
                    stored = state.save_state.call_args.args[1]["statuses"]["video.mp4"]
                    self.assertEqual(stored["steps"]["add_description"], "successful")
                    self.assertEqual(stored["audio_description_language"], "pcm")
                    self.assertEqual(set(stored["audio_description_results"]), {"pcm", *input_languages})
                    self.assertFalse(flow._FLOW_RUN_GUARD.locked())
                    await inspect.getclosurevars(listener.handler).nonlocals["callback"]()
                    self.assertEqual(add.call_count, 15)
            finally:
                client.delete()


class AudioDescriptionApiTests(unittest.TestCase):
    def test_descriptive_upload_registers_the_type_and_finalizes_the_bytes(self):
        module = UpdateAudioModule()
        with (
            patch("src.module.audio_module.get_channels_info", return_value=SimpleNamespace(cookies=[])),
            patch.object(module, "_get_session_token", return_value="token"),
            patch.object(module, "_upload_http", return_value=("https://upload-session", "resource")),
            patch.object(module, "_update", return_value=200) as register,
            patch.object(module, "_next_upload_http") as upload,
        ):
            status = module.add("video", "channel", "music.mp3", "pcm", data=b"full-music", audio_content_type="descriptive")
        self.assertEqual(status, 200)
        self.assertEqual(register.call_args.kwargs["audio_content_type"], "descriptive")
        self.assertEqual(upload.call_args.kwargs["data"], b"full-music")

    def test_conflict_with_only_an_original_track_is_an_error(self):
        module = UpdateAudioModule()
        with (
            patch("src.module.audio_module.get_channels_info", return_value=SimpleNamespace(cookies=[])),
            patch.object(module, "_get_session_token", return_value="token"),
            patch.object(module, "_upload_http", return_value=("https://upload-session", "resource")),
            patch.object(module, "_update", return_value=409),
            patch.object(module, "_get_video_translation_payload", return_value={"audioTracks": [{
                "videoId": "video", "audioTrackId": "original", "language": "pcm",
                "audioContentTypeString": "original", "status": "AUDIO_TRACK_STATUS_READY",
            }]}),
            patch("src.module.audio_module.wait_interruptibly"),
            patch.object(module, "_next_upload_http") as upload,
        ):
            with self.assertRaises(AudioUpdateError):
                module.add("video", "channel", "music.mp3", "pcm", data=b"full-music", audio_content_type="descriptive")
        upload.assert_not_called()

    def test_audio_registration_sends_the_descriptive_type(self):
        module = UpdateAudioModule()
        channel = SimpleNamespace(cookies=[], id="channel", delegated_session_id="delegate", role="OWNER")
        with (
            patch("src.module.audio_module.studio_authorization_header", return_value="auth"),
            patch("src.module.audio_module.post_with_stop", return_value=SimpleNamespace(status_code=200)) as post,
        ):
            module._update("video", "resource", channel, "cookie", "token", "pcm", audio_content_type="descriptive")
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["audioContentTypeString"], "descriptive")
        self.assertEqual(payload["videoId"], "video")
        self.assertEqual(payload["language"], "pcm")

    def test_original_track_does_not_verify_a_descriptive_conflict(self):
        module = UpdateAudioModule()
        payload = {"audioTracks": [{
            "videoId": "video", "audioTrackId": "original", "language": "pcm",
            "audioContentTypeString": "original", "status": "AUDIO_TRACK_STATUS_READY",
        }], "videoTranslations": [{"videoId": "video", "translations": [{
            "languageCode": "pcm", "audioTranslation": {"audioTrackId": "original"},
        }]}]}
        self.assertEqual(module._audio_language_state_from_payload(
            payload, "video", "pcm", audio_content_type="descriptive",
        ), "missing")
        for status, expected in (("READY", "healthy"), ("PROCESSING", "inflight"), ("FAILED", "terminal")):
            payload["audioTracks"].append({
                "videoId": "video", "audioTrackId": "description", "language": "pcm",
                "audioContentTypeString": "descriptive", "status": "AUDIO_TRACK_STATUS_" + status,
            })
            self.assertEqual(module._audio_language_state_from_payload(
                payload, "video", "pcm", audio_content_type="descriptive",
            ), expected)
            payload["audioTracks"].pop()

    def test_source_language_fallback_ignores_other_videos_and_dubbed_tracks(self):
        module = UpdateAudioModule()
        with patch.object(module, "_get_video_translation_payload", return_value={"audioTracks": [
            {"videoId": "other", "language": "vi", "audioContentTypeString": "original"},
            {"videoId": "video", "language": "en", "audioContentTypeString": "dubbed"},
            {"videoId": "video", "language": "pcm", "audioContentTypeString": "original"},
        ]}):
            self.assertEqual(module.get_original_audio_language("video", "channel"), "pcm")

    def test_video_info_keeps_the_original_audio_language(self):
        module = UpdateAudioModule()
        for language in ("pcm", {"languageCode": "pcm"}):
            response = Mock(status_code=200)
            response.json.return_value = {"videos": [{"videoId": "video", "audioLanguage": language}]}
            with (
                patch("src.module.base.get_channels_info", return_value=SimpleNamespace(
                    cookies=[], id="channel", delegated_session_id="delegate", role="OWNER",
                )),
                patch.object(module, "_get_session_token", return_value="token"),
                patch("src.module.base.studio_authorization_header", return_value="auth"),
                patch("src.module.base.post_with_stop", return_value=response),
            ):
                self.assertEqual(module._get_video_info("video", "channel").audio_language, "pcm")


if __name__ == "__main__":
    unittest.main()
