#include <algorithm>
#include <cstring>
#include <cstdint>
#include <optional>
#include <utility>

#include "SharedMemoryInterface.hpp"

static_assert(sizeof(TelemInfoV01) == 1888, "Unexpected LMU TelemInfoV01 size");
static_assert(offsetof(TelemInfoV01, mLocalVel) == 184, "Unexpected mLocalVel offset");
static_assert(offsetof(TelemInfoV01, mLocalAccel) == 208, "Unexpected mLocalAccel offset");
static_assert(offsetof(TelemInfoV01, mUnfilteredThrottle) == 388, "Unexpected throttle offset");
static_assert(offsetof(TelemInfoV01, mFrontRideHeight) == 484, "Unexpected front ride height offset");
static_assert(offsetof(TelemInfoV01, mWheel) == 848, "Unexpected wheel array offset");
static_assert(sizeof(TelemWheelV01) == 260, "Unexpected LMU TelemWheelV01 size");
static_assert(offsetof(TelemWheelV01, mTireLoad) == 104, "Unexpected tire load offset");
static_assert(offsetof(TelemWheelV01, mGripFract) == 112, "Unexpected tire grip offset");
static_assert(offsetof(TelemWheelV01, mCamber) == 80, "Unexpected tire camber offset");

namespace
{

    constexpr long kTelemetryPlayerOnly = 1;
    constexpr long kMaximumVehicles = 104;

    class RaceEngineerPlugin final : public InternalsPluginV08
    {
    public:
        RaceEngineerPlugin()
        {
            initialize_shared_memory();
        }

        ~RaceEngineerPlugin() override
        {
            shutdown_shared_memory();
        }

        bool WantsScoringUpdates() override
        {
            return true;
        }

        long WantsTelemetryUpdates() override
        {
            return kTelemetryPlayerOnly;
        }

        void StartSession() override
        {
            clear_session_data();
        }

        void EndSession() override
        {
            signal_event(SME_END_SESSION);
        }

        void EnterRealtime() override
        {
            signal_event(SME_ENTER_REALTIME);
        }

        void ExitRealtime() override
        {
            signal_event(SME_EXIT_REALTIME);
        }

        void UpdateScoring(const ScoringInfoV01 &info) override
        {
            if (shared_data_ == nullptr)
            {
                return;
            }

            shared_data_->generic.events[SME_UPDATE_SCORING] = static_cast<SharedMemoryEvent>(1);
            shared_data_->scoring.scoringInfo = info;
            shared_data_->scoring.scoringInfo.mVehicle =
                shared_data_->scoring.vehScoringInfo;
            shared_data_->scoring.scoringInfo.mResultsStream = nullptr;

            const long vehicle_count = std::clamp(info.mNumVehicles, 0L, kMaximumVehicles);
            shared_data_->scoring.scoringInfo.mNumVehicles = vehicle_count;
            if (info.mVehicle != nullptr && vehicle_count > 0)
            {
                std::memcpy(
                    shared_data_->scoring.vehScoringInfo,
                    info.mVehicle,
                    sizeof(VehicleScoringInfoV01) * vehicle_count);
            }

            shared_data_->scoring.scoringStreamSize = 0;
            signal_event(SME_UPDATE_SCORING);
        }

        void UpdateTelemetry(const TelemInfoV01 &info) override
        {
            if (shared_data_ == nullptr)
            {
                return;
            }

            shared_data_->telemetry.activeVehicles = 1;
            shared_data_->telemetry.playerVehicleIdx = 0;
            shared_data_->telemetry.playerHasVehicle = true;
            shared_data_->telemetry.telemInfo[0] = info;
            shared_data_->generic.events[SME_UPDATE_TELEMETRY] = static_cast<SharedMemoryEvent>(1);
            signal_event(SME_UPDATE_TELEMETRY);
        }

    private:
        void initialize_shared_memory()
        {
            map_handle_ = CreateFileMappingA(
                INVALID_HANDLE_VALUE,
                nullptr,
                PAGE_READWRITE,
                0,
                static_cast<DWORD>(sizeof(SharedMemoryLayout)),
                LMU_SHARED_MEMORY_FILE);
            if (map_handle_ == nullptr)
            {
                return;
            }
            const bool mapping_already_exists = GetLastError() == ERROR_ALREADY_EXISTS;

            shared_layout_ = static_cast<SharedMemoryLayout *>(MapViewOfFile(
                map_handle_,
                FILE_MAP_ALL_ACCESS,
                0,
                0,
                sizeof(SharedMemoryLayout)));
            if (shared_layout_ == nullptr)
            {
                CloseHandle(map_handle_);
                map_handle_ = nullptr;
                return;
            }

            shared_data_ = &shared_layout_->data;
            if (!mapping_already_exists)
            {
                std::memset(shared_data_, 0, sizeof(SharedMemoryObjectOut));
            }

            event_handle_ = CreateEventA(nullptr, FALSE, FALSE, LMU_SHARED_MEMORY_EVENT);
            if (event_handle_ == nullptr)
            {
                shutdown_shared_memory();
                return;
            }

            shared_data_->scoring.scoringInfo.mVehicle =
                shared_data_->scoring.vehScoringInfo;
            signal_event(SME_STARTUP);
        }

        void clear_session_data()
        {
            if (shared_data_ == nullptr)
            {
                return;
            }

            shared_data_->telemetry.activeVehicles = 0;
            shared_data_->telemetry.playerVehicleIdx = 0;
            shared_data_->telemetry.playerHasVehicle = false;
            shared_data_->generic.events[SME_START_SESSION] = static_cast<SharedMemoryEvent>(1);
            signal_event(SME_START_SESSION);
        }

        void signal_event(SharedMemoryEvent event)
        {
            if (shared_data_ != nullptr)
            {
                shared_data_->generic.events[event] = static_cast<SharedMemoryEvent>(1);
            }
            if (event_handle_ != nullptr)
            {
                SetEvent(event_handle_);
            }
        }

        void shutdown_shared_memory()
        {
            if (shared_data_ != nullptr)
            {
                shared_data_->generic.events[SME_SHUTDOWN] = static_cast<SharedMemoryEvent>(1);
            }
            if (event_handle_ != nullptr)
            {
                SetEvent(event_handle_);
                CloseHandle(event_handle_);
                event_handle_ = nullptr;
            }
            if (shared_layout_ != nullptr)
            {
                UnmapViewOfFile(shared_layout_);
                shared_layout_ = nullptr;
                shared_data_ = nullptr;
            }
            if (map_handle_ != nullptr)
            {
                CloseHandle(map_handle_);
                map_handle_ = nullptr;
            }
        }

        HANDLE map_handle_ = nullptr;
        HANDLE event_handle_ = nullptr;
        SharedMemoryLayout *shared_layout_ = nullptr;
        SharedMemoryObjectOut *shared_data_ = nullptr;
    };

} // namespace

extern "C" __declspec(dllexport) const char *__cdecl GetPluginName()
{
    return "LMU Race Engineer";
}

extern "C" __declspec(dllexport) PluginObjectType __cdecl GetPluginType()
{
    return PO_INTERNALS;
}

extern "C" __declspec(dllexport) int __cdecl GetPluginVersion()
{
    return 8;
}

extern "C" __declspec(dllexport) PluginObject *__cdecl CreatePluginObject()
{
    return new RaceEngineerPlugin();
}

extern "C" __declspec(dllexport) void __cdecl DestroyPluginObject(PluginObject *object)
{
    delete object;
}