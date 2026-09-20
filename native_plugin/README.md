# LMU Race Engineer Native Plugin

This directory contains the C++ DLL loaded by LMU. It is separate from the
Python application, which reads the `LMU_Data` mapping after this DLL publishes
telemetry.

## Build on Windows

Open a **x64 Native Tools Command Prompt for Visual Studio**, then run from
the repository root:

```bat
cmake -S native_plugin -B build/native -A x64
cmake --build build/native --config Release
```

The output DLL is:

```text
build/native/Release/LMURaceEngineerPlugin.dll
```

The project must be built for x64 because LMU is a 64-bit application.

## Install

Register the resulting DLL in LMU's plugin configuration using the game's
normal plugin registration mechanism. Do not copy the Python source into the
game directory. The plugin creates these native objects while LMU is running:

- file mapping: `LMU_Data`
- update event: `LMU_Data_Event`

The Python app consumes that mapping with `mode` set to `shared_memory` and
`shared_memory_name` set to `LMU_Data`.

## Scope of this first plugin

The plugin requests player-only telemetry, copies scoring and telemetry data
into the SDK-defined `SharedMemoryLayout`, and signals an event after updates.
It intentionally does not write a second custom binary format. The Python
reader and this DLL therefore share the SDK layout from the checked-in headers.
