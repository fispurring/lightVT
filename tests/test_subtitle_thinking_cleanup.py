import sys
import unittest
from pathlib import Path


LIGHTVT_ROOT = Path(__file__).resolve().parents[1]
if str(LIGHTVT_ROOT) not in sys.path:
    sys.path.insert(0, str(LIGHTVT_ROOT))

from service.translator.prompt import subtitle as subtitle_prompt
from utils.grammars import json_array_to_subtitle_format


class SubtitleThinkingCleanupTest(unittest.TestCase):
    def setUp(self):
        self.context = [
            {"id": "10", "text": "Hello"},
            {"id": "11", "text": "World"},
        ]
        self.main_indices = [0, 1]

    def test_subtitle_prompts_append_nothink(self):
        translation_prompt = subtitle_prompt.generate_translation_prompt(
            self.context, self.main_indices
        )
        review_prompt = subtitle_prompt.generate_review_translation_prompt(
            self.context, self.main_indices, "[[10]]\nOld"
        )
        improved_prompt = subtitle_prompt.generate_improved_translation_prompt_with_recommendation(
            self.context, self.main_indices, "[[10]]\nOld", "Use natural wording."
        )

        self.assertTrue(translation_prompt.rstrip().endswith("/nothink"))
        self.assertTrue(review_prompt.rstrip().endswith("/nothink"))
        self.assertTrue(improved_prompt.rstrip().endswith("/nothink"))
        self.assertNotEqual(translation_prompt.lstrip().splitlines()[0], "/nothink")

    def test_normal_json_array_to_subtitle_format(self):
        result = json_array_to_subtitle_format(
            '["Hello", "World"]', self.context, self.main_indices
        )

        self.assertEqual(result, "[[10]]\nHello\n[[11]]\nWorld")

    def test_extracts_json_after_thinking_block(self):
        result = json_array_to_subtitle_format(
            '<think>\nAnalyze the subtitle.\n</think>\n["Hello", "World"]',
            self.context,
            self.main_indices,
        )

        self.assertEqual(result, "[[10]]\nHello\n[[11]]\nWorld")

    def test_cleans_thinking_inside_json_items(self):
        result = json_array_to_subtitle_format(
            '["<think>Analyze first.</think>Hello", "World"]',
            self.context,
            self.main_indices,
        )

        self.assertEqual(result, "[[10]]\nHello\n[[11]]\nWorld")

    def test_warns_and_truncates_unclosed_thinking_tag_inside_json_items(self):
        with self.assertLogs("utils.llm_utils", level="WARNING"):
            result = json_array_to_subtitle_format(
                '["Before <think>Analyze first.", "World"]',
                self.context,
                self.main_indices,
            )

        self.assertEqual(result, "[[10]]\nBefore\n[[11]]\nWorld")

    def test_preserves_translation_that_starts_with_analysis_word(self):
        result = json_array_to_subtitle_format(
            '["分析：这是关键线索", "World"]',
            self.context,
            self.main_indices,
        )

        self.assertEqual(result, "[[10]]\n分析：这是关键线索\n[[11]]\nWorld")

    def test_extracts_json_after_thinking_prefix(self):
        result = json_array_to_subtitle_format(
            'Thinking Process: analyze the target.\nOutput: ["Hello", "World"]',
            self.context,
            self.main_indices,
        )

        self.assertEqual(result, "[[10]]\nHello\n[[11]]\nWorld")

    def test_thinking_without_json_does_not_pollute_subtitles(self):
        with self.assertLogs("utils.grammars", level="WARNING"):
            result = json_array_to_subtitle_format(
                "<think>\nAnalyze the whole subtitle chunk.",
                self.context,
                self.main_indices,
            )

        self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main()
