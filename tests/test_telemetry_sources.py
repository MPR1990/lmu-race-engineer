from __future__ import annotations

from datetime import datetime
import unittest

import ctypes
import io

from lmu_race_engineer.telemetry import (
    DemoTelemetrySource,
    RestApiClient,
    RestApiTelemetrySource,
    SharedMemoryTelemetrySource,
)
from lmu_race_engineer.telemetry.shared_memory import (
    SharedMemoryObjectOut,
    parse_lmu_native_struct,
    parse_telemetry_struct,
    rF2Telemetry,
)


class FakeRestApiClient(RestApiClient):
    def __init__(self) -> None:
        super().__init__("http://example.test")
        self.calls = 0

    def get_live_telemetry(self) -> dict[str, object]:
        self.calls += 1
        return {
            "timestamp": datetime(2026, 1, 1, 12, 0, self.calls).isoformat(),
            "lap_number": 1,
            "lap_distance_fraction": 0.1 * self.calls,
            "lap_time_seconds": 10.0 * self.calls,
            "best_lap_time_seconds": 89.0,
            "speed_kph": 180.0,
            "fuel_liters": 90.0,
            "tire_temperatures_c": {
                "front_left": 84.0,
                "front_right": 85.0,
                "rear_left": 88.0,
                "rear_right": 89.0,
            },
            "tire_pressures_kpa": {
                "front_left": 180.0,
                "front_right": 180.5,
                "rear_left": 183.0,
                "rear_right": 183.5,
            },
            "brake_temperatures_c": {"front": 620.0, "rear": 540.0},
            "traction_control_level": 4,
            "abs_level": 5,
            "brake_bias_percent": 53.0,
            "wheelspin_events": 0,
            "lockup_events": 0,
        }


class TelemetrySourceTest(unittest.TestCase):
    def test_demo_source_sleeps_between_samples(self) -> None:
        sleeps: list[float] = []
        source = DemoTelemetrySource(samples=3, poll_interval_seconds=0.25, sleep_func=sleeps.append)

        samples = list(source.stream())

        self.assertEqual(3, len(samples))
        self.assertEqual([0.25, 0.25], sleeps)
        self.assertEqual(0.25, (samples[1].timestamp - samples[0].timestamp).total_seconds())

    def test_rest_source_sleeps_between_polls(self) -> None:
        client = FakeRestApiClient()
        sleeps: list[float] = []
        source = RestApiTelemetrySource(client, poll_interval_seconds=0.4, sleep_func=sleeps.append)

        stream = source.stream()
        first = next(stream)
        second = next(stream)

        self.assertEqual(1, first.lap_number)
        self.assertEqual(1, second.lap_number)
        self.assertEqual(2, client.calls)
        self.assertEqual([0.4], sleeps)

    def test_shared_memory_parse_struct_and_stream(self) -> None:
        struct = rF2Telemetry()
        struct.time = 45.0
        struct.lap_number = 3
        struct.lap_distance_fraction = 0.5
        struct.best_lap_time = 88.5
        struct.vel.x = 30.0  # ~108 km/h along X
        struct.fuel = 42.5
        struct.traction_control_level = 3
        struct.abs_level = 4
        struct.brake_bias_percent = 54.0

        # FL tire (temperatures in Kelvin in rF2 SMF)
        struct.wheel[0].temperature[1] = 85.0 + 273.15
        struct.wheel[0].pressure = 180.0
        struct.wheel[0].brake_temp = 600.0 + 273.15
        # FR tire
        struct.wheel[1].temperature[1] = 86.0 + 273.15
        struct.wheel[1].pressure = 181.0
        struct.wheel[1].brake_temp = 610.0 + 273.15
        # RL tire
        struct.wheel[2].temperature[1] = 90.0 + 273.15
        struct.wheel[2].pressure = 183.0
        struct.wheel[2].brake_temp = 520.0 + 273.15
        # RR tire
        struct.wheel[3].temperature[1] = 91.0 + 273.15
        struct.wheel[3].pressure = 184.0
        struct.wheel[3].brake_temp = 530.0 + 273.15

        raw_bytes = bytes(struct)
        snapshot = parse_telemetry_struct(raw_bytes)

        self.assertEqual(3, snapshot.lap_number)
        self.assertEqual(0.5, snapshot.lap_distance_fraction)
        self.assertEqual(45.0, snapshot.lap_time_seconds)
        self.assertEqual(88.5, snapshot.best_lap_time_seconds)
        self.assertAlmostEqual(108.0, snapshot.speed_kph, delta=0.1)
        self.assertEqual(42.5, snapshot.fuel_liters)
        self.assertEqual(85.0, snapshot.tire_temperatures_c["front_left"])
        self.assertEqual(605.0, snapshot.brake_temperatures_c["front"])
        self.assertEqual(525.0, snapshot.brake_temperatures_c["rear"])

        buf = io.BytesIO(raw_bytes)
        sleeps: list[float] = []
        source = SharedMemoryTelemetrySource(
            memory_name="TestMemory",
            poll_interval_seconds=0.1,
            sleep_func=sleeps.append,
            mmap_factory=lambda: buf,
        )

        stream = source.stream()
        s1 = next(stream)
        s2 = next(stream)

        self.assertEqual(3, s1.lap_number)
        self.assertEqual(3, s2.lap_number)
        self.assertEqual([0.1], sleeps)

    def test_native_lmu_shared_memory_parse_struct(self) -> None:
        struct = SharedMemoryObjectOut()
        struct.telemetry.playerHasVehicle = 1
        struct.telemetry.playerVehicleIdx = 0

        p_telem = struct.telemetry.telemInfo[0]
        p_scoring = struct.scoring.vehScoringInfo[0]
        struct.scoring.scoringInfo.mLapDist = 5000.0  # 5 km track

        p_telem.mLapNumber = 4
        p_telem.mLapStartET = 100.0
        p_telem.mElapsedTime = 152.5  # 52.5s lap time
        p_telem.mFuel = 38.0
        p_telem.mLocalVel.x = 40.0  # ~144 km/h
        p_telem.mLocalAccel.x = 2.5
        p_telem.mLocalAccel.z = -4.0
        p_telem.mUnfilteredThrottle = 0.72
        p_telem.mUnfilteredBrake = 0.08
        p_telem.mUnfilteredSteering = -0.18
        p_telem.mFrontRideHeight = 0.035
        p_telem.mRearRideHeight = 0.060
        p_telem.mFrontWingHeight = 0.020
        p_telem.mTC = 5
        p_telem.mABS = 6
        p_telem.mRearBrakeBias = 0.54

        p_scoring.mLapDist = 2500.0  # half track => lap fraction 0.5
        p_scoring.mBestLapTime = 91.2

        # Wheel temps in Kelvin
        p_telem.mWheel[0].mTemperature[1] = 88.0 + 273.15
        p_telem.mWheel[0].mTireLoad = 1200.0
        p_telem.mWheel[0].mGripFract = 0.12
        p_telem.mWheel[0].mWear = 0.04
        p_telem.mWheel[0].mCamber = -0.05
        p_telem.mWheel[0].mRideHeight = 0.042
        p_telem.mWheel[0].mPressure = 182.0
        p_telem.mWheel[0].mBrakeTemp = 580.0 + 273.15
        p_telem.mWheel[1].mTemperature[1] = 89.0 + 273.15
        p_telem.mWheel[1].mPressure = 182.5
        p_telem.mWheel[1].mBrakeTemp = 590.0 + 273.15
        p_telem.mWheel[2].mTemperature[1] = 92.0 + 273.15
        p_telem.mWheel[2].mPressure = 185.0
        p_telem.mWheel[2].mBrakeTemp = 510.0 + 273.15
        p_telem.mWheel[3].mTemperature[1] = 93.0 + 273.15
        p_telem.mWheel[3].mPressure = 185.5
        p_telem.mWheel[3].mBrakeTemp = 520.0 + 273.15

        raw_bytes = bytes(struct)
        snapshot = parse_lmu_native_struct(raw_bytes)

        self.assertEqual(4, snapshot.lap_number)
        self.assertEqual(0.5, snapshot.lap_distance_fraction)
        self.assertEqual(52.5, snapshot.lap_time_seconds)
        self.assertEqual(91.2, snapshot.best_lap_time_seconds)
        self.assertAlmostEqual(144.0, snapshot.speed_kph, delta=0.1)
        self.assertEqual(38.0, snapshot.fuel_liters)
        self.assertEqual(88.0, snapshot.tire_temperatures_c["front_left"])
        self.assertEqual(585.0, snapshot.brake_temperatures_c["front"])
        self.assertEqual(5, snapshot.traction_control_level)
        self.assertEqual(6, snapshot.abs_level)
        self.assertEqual(54.0, snapshot.brake_bias_percent)
        self.assertEqual(0.72, snapshot.throttle_input)
        self.assertEqual(0.08, snapshot.brake_input)
        self.assertEqual(-0.18, snapshot.steering_input)
        self.assertEqual(2.5, snapshot.lateral_acceleration_mps2)
        self.assertEqual(4.0, snapshot.longitudinal_acceleration_mps2)
        self.assertEqual(1200.0, snapshot.tire_loads_n["front_left"])
        self.assertEqual(0.12, snapshot.tire_grip_fraction["front_left"])
        self.assertEqual(0.04, snapshot.tire_wear_fraction["front_left"])
        self.assertEqual(-0.05, snapshot.tire_camber_rad["front_left"])
        self.assertEqual(0.042, snapshot.tire_ride_height_m["front_left"])
        self.assertEqual(0.035, snapshot.front_ride_height_m)
        self.assertEqual(0.060, snapshot.rear_ride_height_m)
        self.assertEqual(0.020, snapshot.front_wing_height_m)

    def test_shared_memory_reconnects_on_factory_error(self) -> None:
        attempts = 0
        buf = io.BytesIO(bytes(rF2Telemetry()))

        def failing_factory():
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise FileNotFoundError("LMU not open")
            return buf

        sleeps: list[float] = []
        source = SharedMemoryTelemetrySource(
            memory_name="TestMemory",
            poll_interval_seconds=0.2,
            sleep_func=sleeps.append,
            mmap_factory=failing_factory,
        )

        stream = source.stream()
        s1 = next(stream)

        self.assertEqual(0, s1.lap_number)
        self.assertEqual(2, attempts)
        self.assertEqual([0.2], sleeps)


if __name__ == "__main__":
    unittest.main()
