cmake_minimum_required(VERSION 3.20)

project(lmu_race_engineer_plugin LANGUAGES CXX)

add_library(lmu_race_engineer_plugin SHARED
    lmu_race_engineer_plugin.cpp
)

target_compile_features(lmu_race_engineer_plugin PRIVATE cxx_std_17)
target_compile_definitions(lmu_race_engineer_plugin PRIVATE
    WIN32_LEAN_AND_MEAN
    NOMINMAX
)
target_include_directories(lmu_race_engineer_plugin PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/../src/lmu_race_engineer
)

set_target_properties(lmu_race_engineer_plugin PROPERTIES
    OUTPUT_NAME "LMURaceEngineerPlugin"
    PREFIX ""
)