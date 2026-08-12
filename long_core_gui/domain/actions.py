"""Deterministic translation from queue plans to semantic instrument actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from types import MappingProxyType
from typing import Any, ClassVar, Mapping

from .models import (
    ActionOpcode,
    Axis,
    DAQType,
    DomainValidationError,
    HomingPolicy,
    MeasurementMode,
    MeasurementType,
    MoveTarget,
    QueuePlan,
    QueueStep,
    TreatmentOrder,
    TreatmentType,
    _check_unknown,
    _enum_value,
)


@dataclass(frozen=True)
class Action:
    opcode: ActionOpcode
    sample_id: str | None = None
    purpose: str | None = None
    axis: Axis | None = None
    daq_type: DAQType | None = None
    move_target: MoveTarget | None = None
    value: float | None = None
    parameters: Mapping[str, Any] = field(default_factory=dict)

    _FIELDS: ClassVar[set[str]] = {
        "opcode",
        "sample_id",
        "purpose",
        "axis",
        "daq_type",
        "move_target",
        "value",
        "parameters",
    }

    def __post_init__(self) -> None:
        errors: dict[str, str] = {}
        if not isinstance(self.opcode, ActionOpcode):
            errors["opcode"] = "must be ActionOpcode"
        for name in ("sample_id", "purpose"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, str):
                errors[name] = "must be text or null"
        if self.axis is not None and not isinstance(self.axis, Axis):
            errors["axis"] = "must be Axis or null"
        if self.daq_type is not None and not isinstance(self.daq_type, DAQType):
            errors["daq_type"] = "must be DAQType or null"
        if self.move_target is not None and not isinstance(self.move_target, MoveTarget):
            errors["move_target"] = "must be MoveTarget or null"
        if self.value is not None and (
            isinstance(self.value, bool)
            or not isinstance(self.value, (int, float))
            or not isfinite(self.value)
        ):
            errors["value"] = "must be a finite number or null"
        if not isinstance(self.parameters, Mapping):
            errors["parameters"] = "must be a mapping"
        if self.opcode is ActionOpcode.MOVE and self.move_target is None:
            errors["move_target"] = "is required for MOVE"
        if self.opcode in (ActionOpcode.SQUID_DAQ, ActionOpcode.MS_DAQ):
            if self.daq_type is None:
                errors["daq_type"] = "is required for a DAQ action"
        elif self.daq_type is not None:
            errors["daq_type"] = "is only valid for a DAQ action"
        if errors:
            raise DomainValidationError(errors)
        object.__setattr__(self, "parameters", MappingProxyType(dict(self.parameters)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "opcode": self.opcode.value,
            "sample_id": self.sample_id,
            "purpose": self.purpose,
            "axis": self.axis.value if self.axis else None,
            "daq_type": self.daq_type.value if self.daq_type else None,
            "move_target": self.move_target.value if self.move_target else None,
            "value": self.value,
            "parameters": dict(self.parameters),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Action":
        _check_unknown(data, cls._FIELDS)
        if "opcode" not in data:
            raise DomainValidationError({"opcode": "is required"})
        return cls(
            opcode=_enum_value(ActionOpcode, data["opcode"], "opcode"),
            sample_id=data.get("sample_id"),
            purpose=data.get("purpose"),
            axis=(
                _enum_value(Axis, data["axis"], "axis")
                if data.get("axis") is not None
                else None
            ),
            daq_type=(
                _enum_value(DAQType, data["daq_type"], "daq_type")
                if data.get("daq_type") is not None
                else None
            ),
            move_target=(
                _enum_value(MoveTarget, data["move_target"], "move_target")
                if data.get("move_target") is not None
                else None
            ),
            value=data.get("value"),
            parameters=data.get("parameters", {}),
        )


class ActionBuilder:
    """Build an auditable semantic action list without hardware assumptions."""

    def build(self, plan: QueuePlan) -> tuple[Action, ...]:
        if not isinstance(plan, QueuePlan):
            raise DomainValidationError({"plan": "must be QueuePlan"})
        actions: list[Action] = []
        if plan.homing is HomingPolicy.EVERY_QUEUE:
            actions.append(self._move(MoveTarget.HOME, None, "queue home"))
        for run_number, step in enumerate(plan.steps, start=1):
            if plan.homing is HomingPolicy.EVERY_RUN:
                actions.append(
                    self._move(MoveTarget.HOME, step.sample.sample_id, "run home")
                )
            actions.append(self._move(MoveTarget.LOAD, step.sample.sample_id, "load"))
            if step.treatment_order is TreatmentOrder.BEFORE_MEASUREMENT:
                actions.extend(self._treatment(step))
                actions.extend(self._measurement(step))
            else:
                actions.extend(self._measurement(step))
                actions.extend(self._treatment(step))
            actions.append(
                Action(
                    ActionOpcode.SAVE,
                    sample_id=step.sample.sample_id,
                    purpose="save run",
                    parameters={
                        "run_number": run_number,
                        "measurement_type": step.measurement_type.value,
                        "treatment_type": step.treatment_type.value,
                        "treatment_order": step.treatment_order.value,
                    },
                )
            )
            actions.append(
                self._move(MoveTarget.UNLOAD, step.sample.sample_id, "unload")
            )
        actions.append(Action(ActionOpcode.DONE, purpose="queue complete"))
        return tuple(actions)

    @staticmethod
    def _move(target: MoveTarget, sample_id: str | None, purpose: str) -> Action:
        return Action(
            ActionOpcode.MOVE,
            sample_id=sample_id,
            purpose=purpose,
            move_target=target,
        )

    def _measurement(self, step: QueueStep) -> list[Action]:
        if step.measurement_type is MeasurementType.NONE:
            return []
        sample_id = step.sample.sample_id
        actions = [self._move(MoveTarget.MEASURE, sample_id, "position for DAQ")]
        parameters = self._measurement_parameters(step)
        if step.measurement_type is MeasurementType.MAGNETIC_MOMENT:
            for daq_type in (
                DAQType.BACKGROUND,
                DAQType.LEADER,
                DAQType.SAMPLE,
                DAQType.TRAILER,
            ):
                actions.append(
                    Action(
                        ActionOpcode.SQUID_DAQ,
                        sample_id=sample_id,
                        purpose=f"SQUID {daq_type.value.lower()}",
                        axis=Axis.XYZ,
                        daq_type=daq_type,
                        parameters=parameters,
                    )
                )
        else:
            for daq_type in (DAQType.BACKGROUND, DAQType.SAMPLE):
                actions.append(
                    Action(
                        ActionOpcode.MS_DAQ,
                        sample_id=sample_id,
                        purpose=f"MS {daq_type.value.lower()}",
                        daq_type=daq_type,
                        parameters=parameters,
                    )
                )
        return actions

    @staticmethod
    def _measurement_parameters(step: QueueStep) -> dict[str, Any]:
        parameters: dict[str, Any] = {"mode": step.measurement_mode.value}
        if step.measurement_mode is MeasurementMode.CONTINUOUS:
            parameters.update(step.continuous.to_dict())
        else:
            parameters.update(step.discrete.to_dict())
        return parameters

    @staticmethod
    def _treatment(step: QueueStep) -> list[Action]:
        treatment = step.treatment_type
        sample_id = step.sample.sample_id
        value = step.treatment_value
        if treatment is TreatmentType.NONE:
            return []
        if treatment is TreatmentType.PAUSE:
            return [
                Action(
                    ActionOpcode.PAUSE,
                    sample_id=sample_id,
                    purpose="operator pause",
                    value=step.pause_seconds,
                    parameters={"seconds": step.pause_seconds},
                )
            ]
        specs: dict[TreatmentType, tuple[tuple[ActionOpcode, Axis | None], ...]] = {
            TreatmentType.DEGAUSS_XYZ: ((ActionOpcode.DG, Axis.XYZ),),
            TreatmentType.DEGAUSS_XY: ((ActionOpcode.DG, Axis.XY),),
            TreatmentType.DEGAUSS_Z: ((ActionOpcode.DG, Axis.Z),),
            TreatmentType.DEGAUSS_ARM_AXIAL: (
                (ActionOpcode.DG, Axis.XYZ),
                (ActionOpcode.ARM, Axis.AXIAL),
            ),
            TreatmentType.DEGAUSS_ARM_TRANSVERSE: (
                (ActionOpcode.DG, Axis.XYZ),
                (ActionOpcode.ARM, Axis.TRANSVERSE),
            ),
            TreatmentType.ARM_AXIAL: ((ActionOpcode.ARM, Axis.AXIAL),),
            TreatmentType.ARM_TRANSVERSE: ((ActionOpcode.ARM, Axis.TRANSVERSE),),
            TreatmentType.IRM: ((ActionOpcode.IRM, None),),
            TreatmentType.FURNACE: ((ActionOpcode.FURNACE, None),),
        }
        return [
            Action(
                opcode,
                sample_id=sample_id,
                purpose=treatment.value,
                axis=axis,
                value=value,
                parameters={"treatment_type": treatment.value},
            )
            for opcode, axis in specs[treatment]
        ]
