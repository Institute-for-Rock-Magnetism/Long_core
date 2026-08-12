from __future__ import annotations

import unittest

from long_core_gui.infrastructure.protocols import (
    Axis, SquidCommands, SquidFeedback, SquidFilter, SquidRange, SquidSlew,
)
from long_core_gui.infrastructure.squid import (
    AxisVector, SquidReplyError, acquisition_plan, calculate_measurement,
    normalize_x_analog_reply, parse_counter_reply, parse_status_reply,
)


class SquidProtocolTests(unittest.TestCase):
    def test_exact_configuration_codes(self) -> None:
        self.assertEqual(SquidCommands.filter("X", SquidFilter.HZ_1), "XCF1")
        self.assertEqual(SquidCommands.filter("Y", SquidFilter.HZ_10), "YFCT")
        self.assertEqual(SquidCommands.range("Z", SquidRange.EXTENDED), "ZCRE")
        self.assertEqual(SquidCommands.slew("X", SquidSlew.DISABLE_FAST), "XCSD")
        self.assertEqual(SquidCommands.feedback(Axis.ALL, SquidFeedback.PULSE_RESET), "ACLP")

    def test_status_reply_decoding_is_strict(self) -> None:
        status = parse_status_reply("F1?RT?SE?LO?")
        self.assertEqual(status.filter, SquidFilter.HZ_1)
        self.assertEqual(status.range, SquidRange.X10)
        self.assertEqual(status.slew, SquidSlew.ENABLE_FAST)
        self.assertEqual(status.feedback, SquidFeedback.OPEN)
        with self.assertRaises(SquidReplyError):
            parse_status_reply("F1?RT?BAD")

    def test_numeric_parsing_and_ac_normalization(self) -> None:
        self.assertEqual(parse_counter_reply("-123\r"), -123)
        self.assertEqual(normalize_x_analog_reply("P123456789ABCDE"), "AB 89 45 CD")
        with self.assertRaises(SquidReplyError):
            normalize_x_analog_reply("Pshort")

    def test_acquisition_plan_matches_connected_vi_order(self) -> None:
        plan = acquisition_plan({
            Axis.X: SquidRange.X1,
            Axis.Y: SquidRange.X10,
            Axis.Z: SquidRange.X1,
        })
        self.assertEqual(
            [step.command for step in plan],
            ["ALD", "ALC", "XSC", "ZSC", "ZSD", "YSD", "XSD"],
        )
        self.assertEqual(plan[1].delay_after_s, 0.3)
        self.assertEqual(plan[2].expected_reply_bytes, 7)
        self.assertEqual(plan[-1].expected_reply_bytes, 9)

    def test_background_and_calibration_math(self) -> None:
        result = calculate_measurement(
            AxisVector(10, 20, 30),
            AxisVector(0.5, 1.0, 1.5),
            AxisVector(1, 2, 3),
            AxisVector(0.1, 0.2, 0.3),
            {Axis.X: SquidRange.X1, Axis.Y: SquidRange.X10, Axis.Z: SquidRange.X1},
        )
        self.assertEqual(result.raw, AxisVector(10.5, 1.0, 31.5))
        self.assertEqual(result.adjusted, AxisVector(9.5, -1.0, 28.5))
        self.assertAlmostEqual(result.moment.x, 0.95)
        self.assertAlmostEqual(result.moment.y, -0.2)
        self.assertAlmostEqual(result.moment.z, 8.55)


if __name__ == "__main__":
    unittest.main()
