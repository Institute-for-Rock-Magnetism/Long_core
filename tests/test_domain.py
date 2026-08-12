import json
import math
import unittest

from long_core_gui.domain import (
    Action,
    ActionBuilder,
    ActionOpcode,
    Axis,
    ContinuousMeasurementParameters,
    DAQType,
    DiscreteMeasurementParameters,
    DomainValidationError,
    HomingPolicy,
    MeasurementMode,
    MeasurementType,
    MoveTarget,
    QueuePlan,
    QueueStep,
    SampleMetadata,
    TreatmentOrder,
    TreatmentType,
    VectorMeasurementResult,
    calculate_coordinate_results,
    geographic_to_tilt,
    specimen_to_geographic,
    vector_properties,
)


def moment_step(
    *,
    treatment=TreatmentType.DEGAUSS_ARM_AXIAL,
    order=TreatmentOrder.BEFORE_MEASUREMENT,
):
    return QueueStep(
        sample=SampleMetadata(sample_id="CORE-001"),
        measurement_type=MeasurementType.MAGNETIC_MOMENT,
        treatment_type=treatment,
        treatment_order=order,
        measurement_mode=MeasurementMode.CONTINUOUS,
        treatment_value=20.0 if treatment not in (TreatmentType.NONE, TreatmentType.PAUSE) else None,
        continuous=ContinuousMeasurementParameters(sample_rate_hz=10.0),
    )


class ValidationTests(unittest.TestCase):
    def test_validation_errors_are_field_addressable(self):
        with self.assertRaises(DomainValidationError) as raised:
            SampleMetadata(sample_id="", azimuth_deg=360.0)
        self.assertIn("sample_id", raised.exception.errors)
        self.assertIn("azimuth_deg", raised.exception.errors)
        self.assertIn("plunge_deg", raised.exception.errors)

    def test_mode_requires_matching_parameter_model(self):
        with self.assertRaises(DomainValidationError) as raised:
            QueueStep(
                sample=SampleMetadata("A"),
                measurement_type=MeasurementType.MAGNETIC_SUSCEPTIBILITY,
                treatment_type=TreatmentType.NONE,
                treatment_order=TreatmentOrder.BEFORE_MEASUREMENT,
                measurement_mode=MeasurementMode.DISCRETE,
                continuous=ContinuousMeasurementParameters(),
            )
        self.assertIn("discrete", raised.exception.errors)
        self.assertIn("continuous", raised.exception.errors)

    def test_pause_has_its_own_duration(self):
        with self.assertRaises(DomainValidationError) as raised:
            QueueStep(
                sample=SampleMetadata("A"),
                measurement_type=MeasurementType.NONE,
                treatment_type=TreatmentType.PAUSE,
                treatment_order=TreatmentOrder.BEFORE_MEASUREMENT,
            )
        self.assertIn("pause_seconds", raised.exception.errors)

    def test_hardware_parameters_can_remain_unverified(self):
        self.assertEqual(ContinuousMeasurementParameters().to_dict()["sample_rate_hz"], None)
        self.assertEqual(DiscreteMeasurementParameters().positions_mm, ())


class SerializationTests(unittest.TestCase):
    def test_queue_plan_json_round_trip(self):
        plan = QueuePlan((moment_step(),), HomingPolicy.EVERY_QUEUE)
        encoded = json.loads(json.dumps(plan.to_dict()))
        self.assertEqual(QueuePlan.from_dict(encoded), plan)

    def test_action_round_trip(self):
        action = Action(
            ActionOpcode.SQUID_DAQ,
            sample_id="A",
            axis=Axis.XYZ,
            daq_type=DAQType.SAMPLE,
            parameters={"mode": "Continuous"},
        )
        self.assertEqual(Action.from_dict(action.to_dict()), action)

    def test_unknown_serialized_field_is_rejected(self):
        with self.assertRaises(DomainValidationError) as raised:
            SampleMetadata.from_dict({"sample_id": "A", "mystery": 1})
        self.assertIn("mystery", raised.exception.errors)


class ActionBuilderTests(unittest.TestCase):
    def test_queue_homing_treatment_daq_save_unload_and_done_are_visible(self):
        actions = ActionBuilder().build(
            QueuePlan((moment_step(),), HomingPolicy.EVERY_QUEUE)
        )
        self.assertEqual(actions[0].move_target, MoveTarget.HOME)
        self.assertEqual(actions[1].move_target, MoveTarget.LOAD)
        self.assertEqual(
            [action.opcode for action in actions[2:4]],
            [ActionOpcode.DG, ActionOpcode.ARM],
        )
        daq_types = [
            action.daq_type
            for action in actions
            if action.opcode is ActionOpcode.SQUID_DAQ
        ]
        self.assertEqual(
            daq_types,
            [DAQType.BACKGROUND, DAQType.LEADER, DAQType.SAMPLE, DAQType.TRAILER],
        )
        self.assertEqual(actions[-3].opcode, ActionOpcode.SAVE)
        self.assertEqual(actions[-2].move_target, MoveTarget.UNLOAD)
        self.assertEqual(actions[-1].opcode, ActionOpcode.DONE)
        self.assertEqual(
            actions[-3].parameters["treatment_order"], "Before Measurement"
        )

    def test_after_measurement_order_and_every_run_homing(self):
        actions = ActionBuilder().build(
            QueuePlan(
                (moment_step(order=TreatmentOrder.AFTER_MEASUREMENT),),
                HomingPolicy.EVERY_RUN,
            )
        )
        self.assertEqual(actions[0].purpose, "run home")
        squid_index = next(
            index for index, action in enumerate(actions) if action.opcode is ActionOpcode.SQUID_DAQ
        )
        treatment_index = next(
            index for index, action in enumerate(actions) if action.opcode is ActionOpcode.DG
        )
        self.assertLess(squid_index, treatment_index)

    def test_susceptibility_uses_background_and_sample_only(self):
        step = QueueStep(
            sample=SampleMetadata("MS-1"),
            measurement_type=MeasurementType.MAGNETIC_SUSCEPTIBILITY,
            treatment_type=TreatmentType.NONE,
            treatment_order=TreatmentOrder.BEFORE_MEASUREMENT,
            measurement_mode=MeasurementMode.DISCRETE,
            discrete=DiscreteMeasurementParameters(positions_mm=(1.0, 2.0)),
        )
        actions = ActionBuilder().build(QueuePlan((step,), HomingPolicy.NEVER))
        daq = [action for action in actions if action.opcode is ActionOpcode.MS_DAQ]
        self.assertEqual([action.daq_type for action in daq], [DAQType.BACKGROUND, DAQType.SAMPLE])
        self.assertFalse(any(action.move_target is MoveTarget.HOME for action in actions))


class CalculationTests(unittest.TestCase):
    def test_intensity_inclination_declination(self):
        direction = vector_properties(0.0, 3.0, 4.0)
        self.assertAlmostEqual(direction.intensity, 5.0)
        self.assertAlmostEqual(direction.inclination_deg, math.degrees(math.atan2(4, 3)))
        self.assertAlmostEqual(direction.declination_deg, 90.0)

    def test_zero_vector_direction_is_undefined(self):
        direction = vector_properties(0.0, 0.0, 0.0)
        self.assertEqual(direction.intensity, 0.0)
        self.assertIsNone(direction.inclination_deg)
        self.assertIsNone(direction.declination_deg)

    def test_specimen_rotation_and_tilt_preserve_intensity(self):
        source = VectorMeasurementResult(1.0, 2.0, 3.0)
        geographic = specimen_to_geographic(source, 90.0, 0.0)
        self.assertAlmostEqual(geographic.x, -2.0)
        self.assertAlmostEqual(geographic.y, 1.0)
        self.assertAlmostEqual(geographic.z, 3.0)
        tilted = geographic_to_tilt(geographic, 15.0, 30.0)
        self.assertAlmostEqual(
            math.sqrt(source.x**2 + source.y**2 + source.z**2),
            math.sqrt(tilted.x**2 + tilted.y**2 + tilted.z**2),
        )

    def test_full_coordinate_result_uses_available_metadata(self):
        metadata = SampleMetadata(
            "A",
            azimuth_deg=0.0,
            plunge_deg=0.0,
            bedding_strike_deg=0.0,
            bedding_dip_deg=0.0,
        )
        result = calculate_coordinate_results(VectorMeasurementResult(1, 0, 0), metadata)
        self.assertEqual(result.specimen.declination_deg, 0.0)
        self.assertEqual(result.geographic.declination_deg, 0.0)
        self.assertEqual(result.tilt_corrected.declination_deg, 0.0)


if __name__ == "__main__":
    unittest.main()
