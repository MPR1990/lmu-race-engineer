from __future__ import annotations

import ctypes
from collections.abc import Iterator
from datetime import UTC, datetime
import math
import mmap
import time

from lmu_race_engineer.models import TelemetrySnapshot
from lmu_race_engineer.telemetry.base import TelemetrySource

# ==============================================================================
# 1. Native LMU Shared Memory Layout (LMU_Data from Studio 397 2025 SDK)
# ==============================================================================

LMU_NATIVE_SHM_NAME = "LMU_Data"
LMU_PLUGIN_SHM_NAME = "$LMU.3.8.SMMP_Telemetry$"
RF2_PLUGIN_SHM_NAME = "$rFactor2SMF_Telemetry$"


class TelemVect3(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("x", ctypes.c_double),
        ("y", ctypes.c_double),
        ("z", ctypes.c_double),
    ]


class ApplicationStateV01(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("mAppWindow", ctypes.c_uint64),
        ("mWidth", ctypes.c_uint32),
        ("mHeight", ctypes.c_uint32),
        ("mRefreshRate", ctypes.c_uint32),
        ("mWindowed", ctypes.c_uint32),
        ("mOptionsLocation", ctypes.c_uint8),
        ("mOptionsPage", ctypes.c_char * 31),
        ("mExpansion", ctypes.c_uint8 * 204),
    ]


class SharedMemoryGeneric(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("events", ctypes.c_uint32 * 17),
        ("gameVersion", ctypes.c_int32),
        ("FFBTorque", ctypes.c_float),
        ("appInfo", ApplicationStateV01),
    ]


class SharedMemoryPathData(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("userData", ctypes.c_char * 260),
        ("customVariables", ctypes.c_char * 260),
        ("stewardResults", ctypes.c_char * 260),
        ("playerProfile", ctypes.c_char * 260),
        ("pluginsFolder", ctypes.c_char * 260),
    ]


class VehicleScoringInfoV01(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("mID", ctypes.c_int32),
        ("mDriverName", ctypes.c_char * 32),
        ("mVehicleName", ctypes.c_char * 64),
        ("mTotalLaps", ctypes.c_int16),
        ("mSector", ctypes.c_int8),
        ("mFinishStatus", ctypes.c_int8),
        ("mLapDist", ctypes.c_double),
        ("mPathLateral", ctypes.c_double),
        ("mTrackEdge", ctypes.c_double),
        ("mBestSector1", ctypes.c_double),
        ("mBestSector2", ctypes.c_double),
        ("mBestLapTime", ctypes.c_double),
        ("mLastSector1", ctypes.c_double),
        ("mLastSector2", ctypes.c_double),
        ("mLastLapTime", ctypes.c_double),
        ("mCurSector1", ctypes.c_double),
        ("mCurSector2", ctypes.c_double),
        ("mNumPitstops", ctypes.c_int16),
        ("mNumPenalties", ctypes.c_int16),
        ("mIsPlayer", ctypes.c_uint8),
        ("mControl", ctypes.c_int8),
        ("mInPits", ctypes.c_uint8),
        ("mPlace", ctypes.c_uint8),
        ("mVehicleClass", ctypes.c_char * 32),
        ("mTimeBehindNext", ctypes.c_double),
        ("mLapsBehindNext", ctypes.c_int32),
        ("mTimeBehindLeader", ctypes.c_double),
        ("mLapsBehindLeader", ctypes.c_int32),
        ("mLapStartET", ctypes.c_double),
        ("mPos", TelemVect3),
        ("mLocalVel", TelemVect3),
        ("mLocalAccel", TelemVect3),
        ("mOri", TelemVect3 * 3),
        ("mLocalRot", TelemVect3),
        ("mLocalRotAccel", TelemVect3),
        ("mHeadlights", ctypes.c_uint8),
        ("mPitState", ctypes.c_uint8),
        ("mServerScored", ctypes.c_uint8),
        ("mIndividualPhase", ctypes.c_uint8),
        ("mQualification", ctypes.c_int32),
        ("mTimeIntoLap", ctypes.c_double),
        ("mEstimatedLapTime", ctypes.c_double),
        ("mPitGroup", ctypes.c_char * 24),
        ("mFlag", ctypes.c_uint8),
        ("mUnderYellow", ctypes.c_uint8),
        ("mCountLapFlag", ctypes.c_uint8),
        ("mInGarageStall", ctypes.c_uint8),
        ("mUpgradePack", ctypes.c_uint8 * 16),
        ("mPitLapDist", ctypes.c_float),
        ("mBestLapSector1", ctypes.c_float),
        ("mBestLapSector2", ctypes.c_float),
        ("mSteamID", ctypes.c_uint64),
        ("mVehFilename", ctypes.c_char * 32),
        ("mAttackMode", ctypes.c_int16),
        ("mFuelFraction", ctypes.c_uint8),
        ("mDRSState", ctypes.c_uint8),
        ("mExpansion", ctypes.c_uint8 * 4),
    ]


class ScoringInfoV01(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("mTrackName", ctypes.c_char * 64),
        ("mSession", ctypes.c_int32),
        ("mCurrentET", ctypes.c_double),
        ("mEndET", ctypes.c_double),
        ("mMaxLaps", ctypes.c_int32),
        ("mLapDist", ctypes.c_double),
        ("mResultsStream", ctypes.c_uint64),
        ("mNumVehicles", ctypes.c_int32),
        ("mGamePhase", ctypes.c_uint8),
        ("mYellowFlagState", ctypes.c_int8),
        ("mSectorFlag", ctypes.c_int8 * 3),
        ("mStartLight", ctypes.c_uint8),
        ("mNumRedLights", ctypes.c_uint8),
        ("mInRealtime", ctypes.c_uint8),
        ("mPlayerName", ctypes.c_char * 32),
        ("mPlrFileName", ctypes.c_char * 64),
        ("mDarkCloud", ctypes.c_double),
        ("mRaining", ctypes.c_double),
        ("mAmbientTemp", ctypes.c_double),
        ("mTrackTemp", ctypes.c_double),
        ("mWind", TelemVect3),
        ("mMinPathWetness", ctypes.c_double),
        ("mMaxPathWetness", ctypes.c_double),
        ("mGameMode", ctypes.c_uint8),
        ("mIsPasswordProtected", ctypes.c_uint8),
        ("mServerPort", ctypes.c_uint16),
        ("mServerPublicIP", ctypes.c_uint32),
        ("mMaxPlayers", ctypes.c_int32),
        ("mServerName", ctypes.c_char * 32),
        ("mStartET", ctypes.c_float),
        ("mAvgPathWetness", ctypes.c_double),
        ("mSessionTimeRemaining", ctypes.c_float),
        ("mTimeOfDay", ctypes.c_float),
        ("mIsFixedSetup", ctypes.c_uint8),
        ("mTrackGripLevel", ctypes.c_uint8),
        ("mCloudCoverage", ctypes.c_uint8),
        ("mTrackLimitsStepsPerPenalty", ctypes.c_uint8),
        ("mTrackLimitsStepsPerPoint", ctypes.c_uint8),
        ("mExpansion", ctypes.c_uint8 * 187),
        ("mVehicle", ctypes.c_uint64),
    ]


class SharedMemoryScoringData(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("scoringInfo", ScoringInfoV01),
        ("scoringStreamSize", ctypes.c_uint64),
        ("vehScoringInfo", VehicleScoringInfoV01 * 104),
        ("scoringStream", ctypes.c_char * 65536),
    ]


class TelemWheelV01(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("mSuspensionDeflection", ctypes.c_double),
        ("mRideHeight", ctypes.c_double),
        ("mSuspForce", ctypes.c_double),
        ("mBrakeTemp", ctypes.c_double),
        ("mBrakePressure", ctypes.c_double),
        ("mRotation", ctypes.c_double),
        ("mLateralPatchVel", ctypes.c_double),
        ("mLongitudinalPatchVel", ctypes.c_double),
        ("mLateralGroundVel", ctypes.c_double),
        ("mLongitudinalGroundVel", ctypes.c_double),
        ("mCamber", ctypes.c_double),
        ("mLateralForce", ctypes.c_double),
        ("mLongitudinalForce", ctypes.c_double),
        ("mTireLoad", ctypes.c_double),
        ("mGripFract", ctypes.c_double),
        ("mPressure", ctypes.c_double),
        ("mTemperature", ctypes.c_double * 3),
        ("mWear", ctypes.c_double),
        ("mTerrainName", ctypes.c_char * 16),
        ("mSurfaceType", ctypes.c_uint8),
        ("mFlat", ctypes.c_uint8),
        ("mDetached", ctypes.c_uint8),
        ("mStaticUndeflectedRadius", ctypes.c_uint8),
        ("mVerticalTireDeflection", ctypes.c_double),
        ("mWheelYLocation", ctypes.c_double),
        ("mToe", ctypes.c_double),
        ("mTireCarcassTemperature", ctypes.c_double),
        ("mTireInnerLayerTemperature", ctypes.c_double * 3),
        ("mOptimalTemp", ctypes.c_float),
        ("mCompoundIndex", ctypes.c_uint8),
        ("mCompoundType", ctypes.c_uint8),
        ("mExpansion", ctypes.c_uint8 * 18),
    ]


class TelemInfoV01(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("mID", ctypes.c_int32),
        ("mDeltaTime", ctypes.c_double),
        ("mElapsedTime", ctypes.c_double),
        ("mLapNumber", ctypes.c_int32),
        ("mLapStartET", ctypes.c_double),
        ("mVehicleName", ctypes.c_char * 64),
        ("mTrackName", ctypes.c_char * 64),
        ("mPos", TelemVect3),
        ("mLocalVel", TelemVect3),
        ("mLocalAccel", TelemVect3),
        ("mOri", TelemVect3 * 3),
        ("mLocalRot", TelemVect3),
        ("mLocalRotAccel", TelemVect3),
        ("mGear", ctypes.c_int32),
        ("mEngineRPM", ctypes.c_double),
        ("mEngineWaterTemp", ctypes.c_double),
        ("mEngineOilTemp", ctypes.c_double),
        ("mClutchRPM", ctypes.c_double),
        ("mUnfilteredThrottle", ctypes.c_double),
        ("mUnfilteredBrake", ctypes.c_double),
        ("mUnfilteredSteering", ctypes.c_double),
        ("mUnfilteredClutch", ctypes.c_double),
        ("mFilteredThrottle", ctypes.c_double),
        ("mFilteredBrake", ctypes.c_double),
        ("mFilteredSteering", ctypes.c_double),
        ("mFilteredClutch", ctypes.c_double),
        ("mSteeringShaftTorque", ctypes.c_double),
        ("mFront3rdDeflection", ctypes.c_double),
        ("mRear3rdDeflection", ctypes.c_double),
        ("mFrontWingHeight", ctypes.c_double),
        ("mFrontRideHeight", ctypes.c_double),
        ("mRearRideHeight", ctypes.c_double),
        ("mDrag", ctypes.c_double),
        ("mFrontDownforce", ctypes.c_double),
        ("mRearDownforce", ctypes.c_double),
        ("mFuel", ctypes.c_double),
        ("mEngineMaxRPM", ctypes.c_double),
        ("mScheduledStops", ctypes.c_uint8),
        ("mOverheating", ctypes.c_uint8),
        ("mDetached", ctypes.c_uint8),
        ("mHeadlights", ctypes.c_uint8),
        ("mDentSeverity", ctypes.c_uint8 * 8),
        ("mLastImpactET", ctypes.c_double),
        ("mLastImpactMagnitude", ctypes.c_double),
        ("mLastImpactPos", TelemVect3),
        ("mEngineTorque", ctypes.c_double),
        ("mCurrentSector", ctypes.c_int32),
        ("mSpeedLimiter", ctypes.c_uint8),
        ("mMaxGears", ctypes.c_uint8),
        ("mFrontTireCompoundIndex", ctypes.c_uint8),
        ("mRearTireCompoundIndex", ctypes.c_uint8),
        ("mFuelCapacity", ctypes.c_double),
        ("mFrontFlapActivated", ctypes.c_uint8),
        ("mRearFlapActivated", ctypes.c_uint8),
        ("mRearFlapLegalStatus", ctypes.c_uint8),
        ("mIgnitionStarter", ctypes.c_uint8),
        ("mFrontTireCompoundName", ctypes.c_char * 18),
        ("mRearTireCompoundName", ctypes.c_char * 18),
        ("mSpeedLimiterAvailable", ctypes.c_uint8),
        ("mAntiStallActivated", ctypes.c_uint8),
        ("mUnused", ctypes.c_uint8 * 2),
        ("mVisualSteeringWheelRange", ctypes.c_float),
        ("mRearBrakeBias", ctypes.c_double),
        ("mTurboBoostPressure", ctypes.c_double),
        ("mPhysicsToGraphicsOffset", ctypes.c_float * 3),
        ("mPhysicalSteeringWheelRange", ctypes.c_float),
        ("mDeltaBest", ctypes.c_double),
        ("mBatteryChargeFraction", ctypes.c_double),
        ("mElectricBoostMotorTorque", ctypes.c_double),
        ("mElectricBoostMotorRPM", ctypes.c_double),
        ("mElectricBoostMotorTemperature", ctypes.c_double),
        ("mElectricBoostWaterTemperature", ctypes.c_double),
        ("mElectricBoostMotorState", ctypes.c_uint8),
        ("mLapInvalidated", ctypes.c_uint8),
        ("mABSActive", ctypes.c_uint8),
        ("mTCActive", ctypes.c_uint8),
        ("mSpeedLimiterActive", ctypes.c_uint8),
        ("mWiperState", ctypes.c_uint8),
        ("mTC", ctypes.c_uint8),
        ("mTCMax", ctypes.c_uint8),
        ("mTCSlip", ctypes.c_uint8),
        ("mTCSlipMax", ctypes.c_uint8),
        ("mTCCut", ctypes.c_uint8),
        ("mTCCutMax", ctypes.c_uint8),
        ("mABS", ctypes.c_uint8),
        ("mABSMax", ctypes.c_uint8),
        ("mMotorMap", ctypes.c_uint8),
        ("mMotorMapMax", ctypes.c_uint8),
        ("mMigration", ctypes.c_uint8),
        ("mMigrationMax", ctypes.c_uint8),
        ("mFrontAntiSway", ctypes.c_uint8),
        ("mFrontAntiSwayMax", ctypes.c_uint8),
        ("mRearAntiSway", ctypes.c_uint8),
        ("mRearAntiSwayMax", ctypes.c_uint8),
        ("mLiftAndCoastProgress", ctypes.c_uint8),
        ("mTrackLimitsSteps", ctypes.c_uint8),
        ("mRegen", ctypes.c_float),
        ("mSoC", ctypes.c_float),
        ("mVirtualEnergy", ctypes.c_float),
        ("mTimeGapCarAhead", ctypes.c_float),
        ("mTimeGapCarBehind", ctypes.c_float),
        ("mTimeGapPlaceAhead", ctypes.c_float),
        ("mTimeGapPlaceBehind", ctypes.c_float),
        ("mVehicleModel", ctypes.c_char * 30),
        ("mVehicleClass", ctypes.c_uint8),
        ("mVehicleChampionship", ctypes.c_uint8),
        ("mExpansion", ctypes.c_uint8 * 20),
        ("mWheel", TelemWheelV01 * 4),
    ]


class SharedMemoryTelemetryData(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("activeVehicles", ctypes.c_uint8),
        ("playerVehicleIdx", ctypes.c_uint8),
        ("playerHasVehicle", ctypes.c_uint8),
        ("telemInfo", TelemInfoV01 * 104),
    ]


class SharedMemoryObjectOut(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("generic", SharedMemoryGeneric),
        ("paths", SharedMemoryPathData),
        ("scoring", SharedMemoryScoringData),
        ("telemetry", SharedMemoryTelemetryData),
    ]


# ==============================================================================
# 2. Plugin / Standalone Layout (rF2 / CrewChief Plugin Layout)
# ==============================================================================


class WheelTelem(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("rotation", ctypes.c_double),
        ("temperature", ctypes.c_double * 3),
        ("pressure", ctypes.c_double),
        ("brake_temp", ctypes.c_double),
        ("wear", ctypes.c_double),
        ("surface_type", ctypes.c_byte),
        ("flat", ctypes.c_byte),
        ("detached", ctypes.c_byte),
        ("padding", ctypes.c_byte),
    ]


class Vec3(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("x", ctypes.c_double),
        ("y", ctypes.c_double),
        ("z", ctypes.c_double),
    ]


class rF2Telemetry(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("version_update_num", ctypes.c_uint32),
        ("bytes_updated", ctypes.c_uint32),
        ("time", ctypes.c_double),
        ("lap_number", ctypes.c_int32),
        ("lap_start_time", ctypes.c_double),
        ("lap_distance", ctypes.c_double),
        ("total_path_distance", ctypes.c_double),
        ("lap_distance_fraction", ctypes.c_double),
        ("best_lap_time", ctypes.c_double),
        ("pos", Vec3),
        ("vel", Vec3),
        ("fuel", ctypes.c_double),
        ("engine_water_temp", ctypes.c_double),
        ("engine_oil_temp", ctypes.c_double),
        ("engine_rpm", ctypes.c_double),
        ("wheel", WheelTelem * 4),
        ("unfiltered_throttle", ctypes.c_double),
        ("unfiltered_brake", ctypes.c_double),
        ("unfiltered_steering", ctypes.c_double),
        ("unfiltered_clutch", ctypes.c_double),
        ("steering_arm_force", ctypes.c_double),
        ("traction_control_level", ctypes.c_int32),
        ("abs_level", ctypes.c_int32),
        ("brake_bias_percent", ctypes.c_double),
        ("wheelspin_events", ctypes.c_int32),
        ("lockup_events", ctypes.c_int32),
    ]


def _to_celsius(temp: float) -> float:
    return temp - 273.15 if temp > 200.0 else temp


def parse_lmu_native_struct(raw_bytes: bytes) -> TelemetrySnapshot:
    struct_size = ctypes.sizeof(SharedMemoryObjectOut)
    if len(raw_bytes) < struct_size:
        raise ValueError(f"Buffer size ({len(raw_bytes)}) is smaller than SharedMemoryObjectOut ({struct_size})")

    data = SharedMemoryObjectOut.from_buffer_copy(raw_bytes[:struct_size])
    p_idx = data.telemetry.playerVehicleIdx if data.telemetry.playerHasVehicle else 0
    p_telem = data.telemetry.telemInfo[p_idx]
    p_scoring = data.scoring.vehScoringInfo[p_idx]
    track_dist = data.scoring.scoringInfo.mLapDist

    speed_mps = math.sqrt(p_telem.mLocalVel.x**2 + p_telem.mLocalVel.y**2 + p_telem.mLocalVel.z**2)
    speed_kph = speed_mps * 3.6

    lap_time = p_telem.mElapsedTime - p_telem.mLapStartET if p_telem.mLapStartET > 0 else 0.0
    best_lap = p_scoring.mBestLapTime if p_scoring.mBestLapTime > 0 else None

    fl_temp = _to_celsius(p_telem.mWheel[0].mTemperature[1])
    fr_temp = _to_celsius(p_telem.mWheel[1].mTemperature[1])
    rl_temp = _to_celsius(p_telem.mWheel[2].mTemperature[1])
    rr_temp = _to_celsius(p_telem.mWheel[3].mTemperature[1])

    fl_brake = _to_celsius(p_telem.mWheel[0].mBrakeTemp)
    fr_brake = _to_celsius(p_telem.mWheel[1].mBrakeTemp)
    rl_brake = _to_celsius(p_telem.mWheel[2].mBrakeTemp)
    rr_brake = _to_celsius(p_telem.mWheel[3].mBrakeTemp)

    lap_frac = p_scoring.mLapDist / track_dist if track_dist > 0 else 0.0
    lap_fraction = max(0.0, min(1.0, float(lap_frac)))

    brake_bias = p_telem.mRearBrakeBias * 100.0 if p_telem.mRearBrakeBias <= 1.0 else p_telem.mRearBrakeBias
    wheel_keys = ("front_left", "front_right", "rear_left", "rear_right")

    return TelemetrySnapshot(
        timestamp=datetime.now(UTC),
        lap_number=int(p_telem.mLapNumber),
        lap_distance_fraction=lap_fraction,
        lap_time_seconds=max(0.0, float(lap_time)),
        best_lap_time_seconds=best_lap,
        speed_kph=float(speed_kph),
        fuel_liters=max(0.0, float(p_telem.mFuel)),
        tire_temperatures_c={
            "front_left": float(fl_temp),
            "front_right": float(fr_temp),
            "rear_left": float(rl_temp),
            "rear_right": float(rr_temp),
        },
        tire_pressures_kpa={
            "front_left": float(p_telem.mWheel[0].mPressure),
            "front_right": float(p_telem.mWheel[1].mPressure),
            "rear_left": float(p_telem.mWheel[2].mPressure),
            "rear_right": float(p_telem.mWheel[3].mPressure),
        },
        brake_temperatures_c={
            "front": float((fl_brake + fr_brake) / 2.0),
            "rear": float((rl_brake + rr_brake) / 2.0),
        },
        traction_control_level=int(p_telem.mTC),
        abs_level=int(p_telem.mABS),
        brake_bias_percent=float(brake_bias),
        wheelspin_events=1 if p_telem.mTCActive else 0,
        lockup_events=1 if p_telem.mABSActive else 0,
        throttle_input=max(0.0, min(1.0, float(p_telem.mUnfilteredThrottle))),
        brake_input=max(0.0, min(1.0, float(p_telem.mUnfilteredBrake))),
        steering_input=max(-1.0, min(1.0, float(p_telem.mUnfilteredSteering))),
        lateral_acceleration_mps2=float(p_telem.mLocalAccel.x),
        longitudinal_acceleration_mps2=float(-p_telem.mLocalAccel.z),
        tire_loads_n={key: float(p_telem.mWheel[index].mTireLoad) for index, key in enumerate(wheel_keys)},
        tire_grip_fraction={key: float(p_telem.mWheel[index].mGripFract) for index, key in enumerate(wheel_keys)},
        tire_wear_fraction={key: float(p_telem.mWheel[index].mWear) for index, key in enumerate(wheel_keys)},
        tire_camber_rad={key: float(p_telem.mWheel[index].mCamber) for index, key in enumerate(wheel_keys)},
        tire_ride_height_m={key: float(p_telem.mWheel[index].mRideHeight) for index, key in enumerate(wheel_keys)},
        suspension_deflection_m={key: float(p_telem.mWheel[index].mSuspensionDeflection) for index, key in enumerate(wheel_keys)},
        suspension_force_n={key: float(p_telem.mWheel[index].mSuspForce) for index, key in enumerate(wheel_keys)},
        lateral_tire_force_n={key: float(p_telem.mWheel[index].mLateralForce) for index, key in enumerate(wheel_keys)},
        longitudinal_tire_force_n={key: float(p_telem.mWheel[index].mLongitudinalForce) for index, key in enumerate(wheel_keys)},
        brake_pressure_fraction={key: float(p_telem.mWheel[index].mBrakePressure) for index, key in enumerate(wheel_keys)},
        lateral_patch_velocity_mps={key: float(p_telem.mWheel[index].mLateralPatchVel) for index, key in enumerate(wheel_keys)},
        longitudinal_patch_velocity_mps={key: float(p_telem.mWheel[index].mLongitudinalPatchVel) for index, key in enumerate(wheel_keys)},
        front_ride_height_m=float(p_telem.mFrontRideHeight),
        rear_ride_height_m=float(p_telem.mRearRideHeight),
        front_wing_height_m=float(p_telem.mFrontWingHeight),
    )


def parse_telemetry_struct(raw_bytes: bytes) -> TelemetrySnapshot:
    struct_size = ctypes.sizeof(rF2Telemetry)
    if len(raw_bytes) < struct_size:
        raise ValueError(f"Buffer size ({len(raw_bytes)}) is smaller than rF2Telemetry size ({struct_size})")

    data = rF2Telemetry.from_buffer_copy(raw_bytes[:struct_size])

    speed_mps = math.sqrt(data.vel.x**2 + data.vel.y**2 + data.vel.z**2)
    speed_kph = speed_mps * 3.6

    best_lap = data.best_lap_time if data.best_lap_time > 0 else None

    fl_temp = _to_celsius(data.wheel[0].temperature[1])
    fr_temp = _to_celsius(data.wheel[1].temperature[1])
    rl_temp = _to_celsius(data.wheel[2].temperature[1])
    rr_temp = _to_celsius(data.wheel[3].temperature[1])

    fl_brake = _to_celsius(data.wheel[0].brake_temp)
    fr_brake = _to_celsius(data.wheel[1].brake_temp)
    rl_brake = _to_celsius(data.wheel[2].brake_temp)
    rr_brake = _to_celsius(data.wheel[3].brake_temp)

    lap_fraction = max(0.0, min(1.0, float(data.lap_distance_fraction)))

    return TelemetrySnapshot(
        timestamp=datetime.now(UTC),
        lap_number=int(data.lap_number),
        lap_distance_fraction=lap_fraction,
        lap_time_seconds=max(0.0, float(data.time)),
        best_lap_time_seconds=best_lap,
        speed_kph=float(speed_kph),
        fuel_liters=max(0.0, float(data.fuel)),
        tire_temperatures_c={
            "front_left": float(fl_temp),
            "front_right": float(fr_temp),
            "rear_left": float(rl_temp),
            "rear_right": float(rr_temp),
        },
        tire_pressures_kpa={
            "front_left": float(data.wheel[0].pressure),
            "front_right": float(data.wheel[1].pressure),
            "rear_left": float(data.wheel[2].pressure),
            "rear_right": float(data.wheel[3].pressure),
        },
        brake_temperatures_c={
            "front": float((fl_brake + fr_brake) / 2.0),
            "rear": float((rl_brake + rr_brake) / 2.0),
        },
        traction_control_level=int(data.traction_control_level),
        abs_level=int(data.abs_level),
        brake_bias_percent=float(data.brake_bias_percent),
        wheelspin_events=int(data.wheelspin_events),
        lockup_events=int(data.lockup_events),
        throttle_input=max(0.0, min(1.0, float(data.unfiltered_throttle))),
        brake_input=max(0.0, min(1.0, float(data.unfiltered_brake))),
        steering_input=max(-1.0, min(1.0, float(data.unfiltered_steering))),
    )


class SharedMemoryTelemetrySource(TelemetrySource):
    def __init__(
        self,
        memory_name: str = LMU_NATIVE_SHM_NAME,
        poll_interval_seconds: float = 0.1,
        sleep_func=None,
        mmap_factory=None,
    ) -> None:
        self.memory_name = memory_name
        self.poll_interval_seconds = poll_interval_seconds
        self.sleep_func = sleep_func or time.sleep
        self.mmap_factory = mmap_factory

    def _default_mmap_factory(self, name: str, size: int) -> mmap.mmap:
        return mmap.mmap(
            -1,
            size,
            tagname=name,
            access=mmap.ACCESS_READ,
        )

    def stream(self) -> Iterator[TelemetrySnapshot]:
        shm = None
        mode = "plugin"

        while True:
            if shm is None:
                if self.mmap_factory:
                    try:
                        shm = self.mmap_factory()
                        try:
                            buf_len = len(shm.getvalue()) if hasattr(shm, "getvalue") else ctypes.sizeof(rF2Telemetry)
                        except Exception:
                            buf_len = ctypes.sizeof(rF2Telemetry)

                        mode = "native" if buf_len >= ctypes.sizeof(SharedMemoryObjectOut) else "plugin"
                    except (FileNotFoundError, PermissionError, OSError, ValueError):
                        shm = None
                        self.sleep_func(self.poll_interval_seconds)
                        continue
                else:
                    names_to_try = [
                        (self.memory_name, "native" if self.memory_name == LMU_NATIVE_SHM_NAME else "plugin"),
                        (LMU_NATIVE_SHM_NAME, "native"),
                        (LMU_PLUGIN_SHM_NAME, "plugin"),
                        (RF2_PLUGIN_SHM_NAME, "plugin"),
                    ]
                    for name, try_mode in names_to_try:
                        size = (
                            ctypes.sizeof(SharedMemoryObjectOut)
                            if try_mode == "native"
                            else ctypes.sizeof(rF2Telemetry)
                        )
                        try:
                            shm = self._default_mmap_factory(name, size)
                            mode = try_mode
                            break
                        except (FileNotFoundError, PermissionError, OSError, ValueError):
                            continue

                if shm is None:
                    self.sleep_func(self.poll_interval_seconds)
                    continue

            try:
                shm.seek(0)
                if mode == "native":
                    raw_bytes = shm.read(ctypes.sizeof(SharedMemoryObjectOut))
                    yield parse_lmu_native_struct(raw_bytes)
                else:
                    raw_bytes = shm.read(ctypes.sizeof(rF2Telemetry))
                    yield parse_telemetry_struct(raw_bytes)
            except Exception:
                try:
                    shm.close()
                except Exception:
                    pass
                shm = None

            self.sleep_func(self.poll_interval_seconds)
