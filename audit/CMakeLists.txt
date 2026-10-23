cmake_minimum_required(VERSION 3.16...3.27)
project(g4audit)

find_package(Geant4 REQUIRED)
file(GLOB sources ${PROJECT_SOURCE_DIR}/*.cc)

add_executable(g4audit ${sources})
target_link_libraries(g4audit PRIVATE ${Geant4_LIBRARIES})
