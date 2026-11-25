import unittest

from src.messages import (
    curb_message,
    indefinite_article,
    scene_message,
    there_are_people,
    there_is_object,
)


class MessageTests(unittest.TestCase):
    def test_articles(self):
        self.assertEqual(indefinite_article("bench"), "a")
        self.assertEqual(indefinite_article("umbrella"), "an")
        self.assertEqual(indefinite_article("apple"), "an")
        self.assertEqual(indefinite_article("university"), "a")

    def test_close_person_message(self):
        message = there_are_people(1, "centre", lower=True, close=True)
        self.assertEqual(
            message,
            "There is a person close in front of you.",
        )

    def test_close_side_message(self):
        message = there_is_object(
            "car", "right", lower=True, close=True
        )
        self.assertEqual(
            message,
            "There is a car close on your right.",
        )

    def test_general_left_message(self):
        message = there_is_object("bench", "left", lower=True)
        self.assertEqual(message, "There is a bench to your left.")

    def test_general_centre_message(self):
        message = there_is_object("bench", "centre", lower=True)
        self.assertEqual(message, "There is a bench in front of you.")

    def test_ahead_message(self):
        message = there_is_object("bench", "centre", lower=False)
        self.assertEqual(message, "There is a bench ahead.")

    def test_people_counts(self):
        self.assertEqual(
            there_are_people(1, "centre", lower=True),
            "There is a person in front of you.",
        )
        self.assertEqual(
            there_are_people(2, "centre", lower=True),
            "There are two people in front of you.",
        )
        self.assertEqual(
            there_are_people(3, "centre", lower=True),
            "There are several people in front of you.",
        )

    def test_curb_messages(self):
        self.assertEqual(
            curb_message("left"),
            "There may be a curb on your left.",
        )
        self.assertEqual(
            curb_message("ahead"),
            "There may be a curb or road edge ahead.",
        )

    def test_scene_messages(self):
        self.assertEqual(
            scene_message("vegetation", "left"),
            "There are trees or plants to your left.",
        )
        self.assertEqual(
            scene_message("building", "right"),
            "There is a building to your right.",
        )


if __name__ == "__main__":
    unittest.main()
