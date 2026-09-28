OpenBlok
========

[![Linux/OSX build status](https://travis-ci.org/mmatyas/openblok.svg?branch=master)](https://travis-ci.org/mmatyas/openblok)
[![Windows build status](https://ci.appveyor.com/api/projects/status/github/mmatyas/openblok?svg=true&branch=master)](https://ci.appveyor.com/project/mmatyas/openblok)
[![Coverity Scan Build Status](https://scan.coverity.com/projects/10795/badge.svg)](https://scan.coverity.com/projects/mmatyas-openblok)

A customizable, cross platform, open-source falling block game, packed with a bunch of features.

> **About this fork:** this is [mmatyas/openblok](https://github.com/mmatyas/openblok) with a
> Jstris-inspired **cheese mode** and five extra themes. Everything else is the upstream game.
>
> **New game modes**
>
> | Menu | Mode | Rules |
> |---|---|---|
> | Singleplayer | **Cheese Race** | Dig through 18 lines of messy garbage as fast as you can. At most 10 cheese lines are on the field; new ones are pushed in from the bottom as you clear them. The GOAL counter shows the remaining lines. |
> | Multiplayer | **Cheese Race** | Every player gets the exact same cheese (shared random seed). The first one to dig through wins. |
> | Multiplayer | **Cheese Battle** | A regular team battle, but everyone starts with 8 cheese lines, and all garbage sent between players is messy. |
>
> Cheese garbage has one hole per row, never in the same column as the row above it.
> The tunables live at the top of `src/game/states/substates/ingame/Gameplay.cpp`.
>
> **Extra themes** (in `data/themes`, installed with the game): `synthwave`, `nes`, `crt_verde`,
> `dracula` and `aurora`, each with its own blocks, wallpaper, colors and sound effects.
> They are generated procedurally by `tools/theme-generator/gen.py`.
>
> **Prebuilt binary:** the [releases page](https://github.com/taprile314/openblok/releases) has an
> aarch64 Linux build (tested on a Raspberry Pi 5 running Batocera 43 as a PortMaster port). It links
> against the system SDL2 libraries and needs glibc 2.34 or newer.
>
> Note: the upstream unit tests currently don't compile (`tests/test_WellTSpin.cpp` uses an old
> `InputEvent` constructor), independently of the changes in this fork. Build with `-DBUILD_TESTS=OFF`.

![Screenshot](etc/promo/screenshot01.png)

**Features:**

- [x] Ghost piece support
- [x] Hold piece support
- [x] Customizable next pieces support
- [x] Customizable DAS support
- [x] SRS, TGM and Classic rotation
- [x] Full wall- and floor kick support
- [x] 7-piece bag random generator
- [x] Classic, Extended and Infinity lock support
- [x] Sonic drop and Zangi-move support
- [x] T-Spin and Mini T-Spin support
- [x] Combo support
- [x] Battle mode, Sprint and Ultra
- [x] Proper menu, configuration and stats
- [x] Gamepad support
- [x] Music and sound effects
- [x] Big screen, small screen support
- [x] Runs on most desktop systems
- [x] Runs on embedded Linux, even without X11
- [x] Runs in browsers (experimental)
- [x] Theme support


Download
--------

See the [Releases](https://github.com/mmatyas/openblok/releases) page to download the latest version.


Dependencies
------------

- CMake (at least 3.1)
- C++11 supporting compiler (GCC 4.9 or better)
- SDL2, SDL2_image, SDL2_mixer, SDL2_ttf
- optional: gcov, lcov (for generating test coverage report)

Eg. on Debian: `sudo apt install cmake libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev`

or on Fedora/RPM: `sudo dnf install cmake SDL2-devel SDL2_image-devel SDL2_mixer-devel SDL2_ttf-devel`


Build
-----

```sh
mkdir build && cd build
cmake ..
make
./src/openblok --data ../data
```

**Optional build parameters:**

- `ENABLE_MP3`, `ENABLE_MOD`, `ENABLE_FLAC`: Enable/disable loading certain media formats. By default, all of them are `ON`.
- `CMAKE_BUILD_TYPE`: To create an **optimized release build**, set this to `Release`. To create a **debug build**, set this value to `Debug`. See the CMake documentation. Default: `Release`.
- `INSTALL_PORTABLE`: The game needs to know where it can find the data files. By default, the game is searching for them in the absolute path of the installation location, which is usually `/usr/local/share/openblok` or `C:\Program Files\openblok`. By setting `INSTALL_PORTABLE` to `ON`, the game will search for the files in the same directory as the binary. Default: `OFF` on Linux, `ON` on Windows.
- `CMAKE_INSTALL_PREFIX`: The base directory of the installation step (eg. `make install`). Defaults to `/usr/local` or `C:\Program Files`. See the CMake documentation.
- `BUILD_TESTS`: Builds the test suite. You can run them by calling `./build/tests/openblok_test`. Debug build only, default: `ON`.
- `BUILD_COVERAGE`: Allows building the test coverage report. Requires `BUILD_TESTS` and `gcov`/`lcov`. Default: `OFF`.

**Useful build targets**

- `make coverage`: Builds the test coverage report
- `make install/strip`: Installs the game on your system
- `make package`: Creates `tar.gz` and Debian `deb` packages


Notes
-----

**Runtime arguments**

You can change certain game parameters, eg. the location of the data directory. Run the game with the `--help` flag to see the available options.

**Hardware acceleration on ARM Linux**

Using the default SDL2 library shipped with Debian/Raspian, hardware acceleration may not work properly, causing slowness and ugly graphics. For the best performance, it is recommended to build your own SDL2, as described [here](https://github.com/mmatyas/openblok/wiki/Custom-SDL2-build-for-ARM). With hardware acceleration, OpenBlok runs full speed even on a first-gen Raspberry Pi.
