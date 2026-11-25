import unittest

from src.tts import expected_speech_seconds, pick_english_voice, pick_sapi_voice


class FakeVoice:
    def __init__(self, voice_id, name, languages):
        self.id = voice_id
        self.name = name
        self.languages = languages


class FakeEngine:
    def __init__(self, voices):
        self.voices = voices
        self.properties = {}

    def getProperty(self, name):
        if name == "voices":
            return self.voices
        return None

    def setProperty(self, name, value):
        self.properties[name] = value


class FakeSapiToken:
    def __init__(self, description):
        self.description = description

    def GetDescription(self):
        return self.description


class FakeSapiVoice:
    def __init__(self, descriptions):
        self.tokens = [FakeSapiToken(d) for d in descriptions]

    def GetVoices(self):
        return self.tokens


class EnglishVoiceTests(unittest.TestCase):
    def test_prefers_en_us(self):
        engine = FakeEngine(
            [
                FakeVoice("de", "Microsoft Hedda - German", [b"de-DE"]),
                FakeVoice("gb", "Microsoft Hazel - English (Great Britain)", [b"en-GB"]),
                FakeVoice("us", "Microsoft Zira - English (United States)", [b"en-US"]),
            ]
        )

        voice = pick_english_voice(engine, "en")
        self.assertIsNotNone(voice)
        self.assertEqual(voice.id, "us")

    def test_falls_back_to_en_gb(self):
        engine = FakeEngine(
            [
                FakeVoice("de", "Microsoft Hedda - German", [b"de-DE"]),
                FakeVoice("gb", "Microsoft Hazel - English (Great Britain)", [b"en-GB"]),
            ]
        )

        voice = pick_english_voice(engine, "en")
        self.assertIsNotNone(voice)
        self.assertEqual(voice.id, "gb")

    def test_returns_none_without_english(self):
        engine = FakeEngine(
            [
                FakeVoice("de", "Microsoft Hedda - German", [b"de-DE"]),
                FakeVoice("fr", "Microsoft Hortense - French", [b"fr-FR"]),
            ]
        )

        self.assertIsNone(pick_english_voice(engine, "en"))


class SapiVoiceTests(unittest.TestCase):
    def test_prefers_en_us(self):
        voice = FakeSapiVoice(
            [
                "Microsoft Hedda Desktop - German",
                "Microsoft Hazel Desktop - English (Great Britain)",
                "Microsoft Zira Desktop - English (United States)",
            ]
        )
        token = pick_sapi_voice(voice)
        self.assertIsNotNone(token)
        self.assertIn("Zira", token.GetDescription())

    def test_returns_none_without_english(self):
        voice = FakeSapiVoice(
            [
                "Microsoft Hedda Desktop - German",
                "Microsoft Hortense Desktop - French",
            ]
        )
        self.assertIsNone(pick_sapi_voice(voice))


class DurationTests(unittest.TestCase):
    def test_expected_duration_scales_with_words(self):
        short = expected_speech_seconds("Hello.", 175)
        longer = expected_speech_seconds(
            "There is a person close in front of you.", 175
        )
        self.assertGreaterEqual(short, 0.6)
        self.assertGreater(longer, short)


if __name__ == "__main__":
    unittest.main()
