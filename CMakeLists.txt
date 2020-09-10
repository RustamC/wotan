cmake_minimum_required(VERSION 3.9)

list(APPEND CMAKE_MODULE_PATH ${CMAKE_CURRENT_SOURCE_DIR}/cmake/modules)
include(FilesToDirs)

project("wotan")

if (${CMAKE_SOURCE_DIR} STREQUAL ${CMAKE_BINARY_DIR})
    message("CMAKE_SOURCE_DIR: ${CMAKE_SOURCE_DIR}")
    message("CMAKE_BINARY_DIR: ${CMAKE_BINARY_DIR}")
    message(FATAL_ERROR "In-source builds not allowed. Use the Makefile wrapper (e.g. make), or create a new build directory and call cmake manually from there (e.g. mkdir -p build && cd build && cmake .. && make). You may need to 'rm -rf CMakeCache.txt CMakeFiles' first.")
endif ()

#We install to the source directory by default
if (CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT)
    set(CMAKE_INSTALL_PREFIX "${CMAKE_BINARY_DIR}" CACHE PATH "default install path" FORCE)
endif ()

#Allow the user to decide weather to compile the graphics library
set(ENABLE_GRAPHICS "auto" CACHE STRING "Specify whether Wotan uses the graphics library")
set_property(CACHE ENABLE_GRAPHICS PROPERTY STRINGS auto off on)

#Handle graphics setup
set(GRAPHICS_DEFINES "")

if (ENABLE_GRAPHICS STREQUAL "off")
    list(APPEND GRAPHICS_DEFINES "NO_GRAPHICS")
    message(STATUS "Wotan: graphics disabled")
endif()

#
# Build Configuration
#
include(CheckCXXSymbolExists)

#
# We require c++11 support
#
set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF) #No compiler specific extensions

find_package(Threads REQUIRED)
find_package(Freetype REQUIRED)
find_package(Fontconfig REQUIRED)
find_package(X11 COMPONENTS X11 Xft REQUIRED)

#
# Warning flags
#

set(WOTAN_WARN_FLAGS "")
set(WOTAN_WARN_FLAGS_TO_CHECK "")

if (NOT MSVC)
    set(WOTAN_WARN_FLAGS_TO_CHECK
            "-Wall"
            "-Wpointer-arith"
            "-Wcast-qual"
            "-ansi"
            "-pedantic"
            "-Wshadow"
            "-Wcast-align"
            "-Wno-write-strings")

    if(WOTAN_DEBUG)
        set(WOTAN_WARN_FLAGS_TO_CHECK
            "-O0 -g"
            ${WOTAN_WARN_FLAGS_TO_CHECK})
    endif()
endif ()

#Check and see if the compiler supports the various warning flags,
#and add valid flags
#foreach(flag ${WOTAN_WARN_FLAGS_TO_CHECK})
#    CHECK_CXX_COMPILER_FLAG(${flag} CXX_COMPILER_SUPPORTS_${flag})
#    if(CXX_COMPILER_SUPPORTS_${flag})
#        #Flag supported, so enable it
#        set(WOTAN_WARN_FLAGS "${WOTAN_WARN_FLAGS} ${flag}")
#    endif()
#endforeach()

set(WOTAN_WARN_FLAGS ${WOTAN_WARN_FLAGS_TO_CHECK})
separate_arguments(
        WOTAN_WARN_FLAGS UNIX_COMMAND "${WOTAN_WARN_FLAGS}"
)

add_compile_options(${WOTAN_WARN_FLAGS}) #Add warn flags

add_subdirectory(SRC/libs)

#
# Collect the source files
#
file(GLOB_RECURSE EXEC_SOURCES SRC/main.cxx)
file(GLOB_RECURSE LIB_SOURCES SRC/*/*.cxx SRC/*/*.cpp SRC/*/*/*/*.cpp)
file(GLOB_RECURSE LIB_HEADERS SRC/*/*.h SRC/*/*.hpp SRC/*/*/*/*.hpp)
files_to_dirs(LIB_HEADERS LIB_INCLUDE_DIRS)

set(LIB_HEADERS ${LIB_HEADERS})
set(LIB_SOURCES ${LIB_SOURCES})
set(LIB_INCLUDE_DIRS ${LIB_INCLUDE_DIRS})

message("LIB_HEADERS: ${LIB_HEADERS}")
message("LIB_SOURCES: ${LIB_SOURCES}")
message("LIB_INCLUDE_DIRS: ${LIB_INCLUDE_DIRS}")

#
# Create the lib
#
add_library(libwotan STATIC ${LIB_HEADERS} ${LIB_SOURCES})
target_include_directories(libwotan PUBLIC ${LIB_INCLUDE_DIRS} PRIVATE ${FREETYPE_INCLUDE_DIRS})
set_target_properties(libwotan PROPERTIES PREFIX "")

target_link_libraries(libwotan PUBLIC libpugixml PRIVATE Threads::Threads PRIVATE Fontconfig::Fontconfig PRIVATE Freetype::Freetype PRIVATE X11 PRIVATE Xft)
target_compile_definitions(libwotan PUBLIC ${GRAPHICS_DEFINES} PUBLIC "EZXML_NOMMAP" PUBLIC "_POSIX_C_SOURCE" PUBLIC "__USE_FIXED_PROTOTYPES__")

#
# Create executable
#
add_executable(wotan ${EXEC_SOURCES})
target_include_directories(wotan PUBLIC ${LIB_INCLUDE_DIRS} PRIVATE ${FREETYPE_INCLUDE_DIRS})
target_link_libraries(wotan PUBLIC libwotan PRIVATE Threads::Threads PRIVATE Fontconfig::Fontconfig PRIVATE Freetype::Freetype PRIVATE X11 PRIVATE Xft)
target_compile_definitions(wotan PUBLIC ${GRAPHICS_DEFINES} PUBLIC "EZXML_NOMMAP" PUBLIC "_POSIX_C_SOURCE" PUBLIC "__USE_FIXED_PROTOTYPES__")

#
# Install wotan
#
install(TARGETS wotan libwotan DESTINATION bin)
