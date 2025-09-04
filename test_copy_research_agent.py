import unittest
from unittest.mock import patch, MagicMock
import unittest
import copy_research_agent

class TestCopyResearchAgent(unittest.TestCase):

    @patch('copy_research_agent.mqtt.Client')
    def test_mqtt_client_initialization(self, mock_mqtt_client):
        client = mock_mqtt_client.return_value
        self.assertIsNotNone(client)

    def test_fix_length_padding(self):
        arr = [1, 0, 1]
        fixed = copy_research_agent.fix_length(arr)
        self.assertEqual(len(fixed), 24)
        self.assertEqual(fixed[:3], [1, 0, 1])
        self.assertEqual(fixed[3:], [0]*21)

    def test_fix_length_truncating(self):
        arr = [1]*30
        fixed = copy_research_agent.fix_length(arr)
        self.assertEqual(len(fixed), 24)
        self.assertEqual(fixed, [1]*24)

    def test_time_range_to_hours(self):
        hours = copy_research_agent.time_range_to_hours("05:00", "08:00")
        self.assertEqual(hours, [5, 6, 7])

    def test_extract_first_array(self):
        text = "Here is the array: [0, 1, 0, 1]"
        arr = copy_research_agent.extract_first_array(text)
        self.assertEqual(arr, "[0, 1, 0, 1]")

    def test_extract_first_dict(self):
        text = "Some output {\"a\": 1, \"b\": 2} more text"
        d = copy_research_agent.extract_first_dict(text)
        self.assertEqual(d, "{\"a\": 1, \"b\": 2}")

    def test_write_output_creates_file(self):
        import os
        schedules = {name: [0]*24 for name in copy_research_agent.APPLIANCES}
        copy_research_agent.write_output(schedules)
        self.assertTrue(os.path.exists('output.txt'))
        with open('output.txt') as f:
            content = f.read()
            self.assertIn("Optimised Appliance Schedules", content)
        os.remove('output.txt')

    def test_enforce_required_ons(self):
        schedules = {name: [0]*24 for name in copy_research_agent.APPLIANCES}
        tou_json = {
            "peak": {"hours": [18, 19, 20]},
            "off_peak": {"hours": [0, 1, 2, 3]},
            "day": {"hours": [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 21, 22, 23]}
        }
        required_ons = {name: 2 for name in copy_research_agent.APPLIANCES}
        result = copy_research_agent.enforce_required_ons(schedules, tou_json, required_ons)
        for arr in result.values():
            self.assertEqual(sum(arr), 2)
            self.assertTrue(all(x in [0, 1] for x in arr))

if __name__ == '__main__':
    unittest.main()