![state](https://img.shields.io/badge/STATE-beta-blue.svg?logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAADpSURBVFhH7ZbbCoJgEIY/C5J7sJO7mJuwAW8SnLhJ3EQu7mBDNICfmf+y88sPIP8wLwz7AAALE7A83d7c3Hz+0SoiIy6jV7p7yooEgAlAAyCCMgAXQAUTsDb5kLe9nSoB0AOc6wJgR038716kAVDeAUyLQNQDcK0LwFcNUAyA6XqgSQCY5YFGAZCOAXh2AMx6YHEAiHVALgBEe6AyAMR7YFYAoj1QGQDgGNpvAEz7YHcAKP2B2AAk/YHYASCdVwjEAYh3QMQBiHdAxAGId0DEAYh3QMQBiHdA5AWI7wHlGqhYAPUlAAAAAElFTkSuQmCC) ![version](https://img.shields.io/github/v/release/YeonV/LedFx-Frontend-v2?label=VERSION&logo=git&logoColor=white) [![creator](https://img.shields.io/badge/CREATOR-Yeon-blue.svg?logo=github&logoColor=white)](https://github.com/YeonV) [![creator](https://img.shields.io/badge/A.K.A-Blade-darkred.svg?logo=github&logoColor=white)](https://github.com/YeonV)

# LedFx - Build Tools and Development Environment Setup

![logo192](https://user-images.githubusercontent.com/28861537/119760144-c5126680-bea9-11eb-991a-c08eedbc5929.png)

## Introduction

Welcome to the LedFx-Builds repository! This repository provides a comprehensive suite of tools, scripts, and configurations designed to streamline the development and build process for the LedFx project.

Whether you're looking to set up a robust development environment or build LedFx applications for various operating systems (including Windows, macOS, and Linux), you'll find the necessary resources here.

It's important to note that LedFx is a separate project. This `LedFx-Builds` repository is dedicated to managing its development lifecycle, from initial setup to final application packaging. We aim to make the process as smooth and efficient as possible for all contributors and users.

## What is LedFx?

LedFx is a real-time music visualization software designed to control LED strips and other lighting devices. It excels at synchronizing dynamic light effects with audio input, creating immersive visual experiences.

## Core Functionality of this Repository

This `LedFx-Builds` repository serves several key functions in the LedFx development and deployment lifecycle:

*   **Development Environment Setup:** It provides scripts and configurations to initialize a complete development environment for LedFx. This setup process includes:
    *   Cloning the main LedFx backend repository (`LedFx/LedFx`).
    *   Cloning the LedFx frontend repository (`LedFx/LedFx-Frontend-v2`).
    *   Establishing a Python virtual environment for the backend to isolate dependencies.
    *   Installing all necessary Python (backend) and Node.js (frontend) dependencies.

*   **Build Tooling:** The repository contains a collection of scripts, configuration files, and tools specifically designed to build distributable versions of the LedFx application for major operating systems:
    *   Windows
    *   macOS
    *   Linux

*   **Pre-compiled Dependencies:** To simplify the build process and ensure compatibility, this repository stores certain pre-compiled binaries and libraries. These are typically components that can be challenging to build from source or require specific versions critical for the LedFx project.

*   **Automation:** It includes GitHub Actions workflows that automate various stages of the build and testing processes, ensuring consistency and enabling continuous integration and delivery (CI/CD) practices.

## Getting Started (Development Setup)

This section guides you through setting up a local development environment for LedFx using the scripts provided in this repository. While the primary scripts (`init.bat`, `dev.bat`) are for Windows, users on other operating systems can adapt the steps.

### Prerequisites

Before you begin, ensure you have the following installed:

*   **Git:** For cloning the repositories. You can download Git from [git-scm.com](https://git-scm.com/).
*   **Python:** Version 3.9 or 3.10. The `init.bat` script specifically checks for these versions. You can download Python from [python.org](https://www.python.org/). Make sure to check the box "Add Python to PATH" during installation.
*   **Node.js:** Required for the frontend. The scripts will attempt to install `yarn` (a package manager for Node.js) if it's not found, but a base Node.js installation is recommended. You can download Node.js from [nodejs.org](https://nodejs.org/).

### Using `init.bat` (Windows)

The `init.bat` script is the primary tool for initializing your LedFx development environment on Windows.

1.  **Clone this Repository:** If you haven't already, clone this `LedFx-Builds` repository to your local machine.
    ```bash
    git clone https://github.com/LedFx/LedFx-Builds.git
    ```
2.  **Run `init.bat`:** Navigate to the root directory of your cloned `LedFx-Builds` repository in your command prompt or terminal and execute `init.bat`:
    ```batch
    cd path\to\LedFx-Builds
    init.bat
    ```

**What `init.bat` does:**

*   Prompts you to choose a drive for the project setup and creates a main project directory (defaulting to `ledfx_v2` in the chosen drive's root, e.g., `C:\ledfx_v2`).
*   Clones the LedFx backend repository (`LedFx/LedFx`) and the LedFx frontend repository (`LedFx/LedFx-Frontend-v2`) into this new project directory.
*   Sets up a Python virtual environment (`venv`) within the backend's directory to isolate dependencies.
*   Installs all necessary Python dependencies for the backend (from `requirements.txt`).
*   Installs Node.js dependencies for the frontend using `yarn` (it will attempt to install `yarn` globally if not already present).
*   Performs a cleanup operation: it moves essential scripts (like `dev.bat`, `build.bat`) into the new project directory, and then removes the original `LedFx-Builds` cloned folder (including `init.bat`, this `README.md`, etc., and its `.git` directory). This effectively transforms the `LedFx-Builds` clone into your main project workspace.
*   Creates a desktop shortcut named `LedFx Dev Env` pointing to `dev.bat` in your new project directory.

After `init.bat` completes, your project directory (e.g., `C:\ledfx_v2`) will be your main workspace for LedFx development.

### Using `dev.bat` (Windows)

Once the initialization is complete, you use `dev.bat` (either from the desktop shortcut or by navigating to your project directory, e.g., `C:\ledfx_v2`, and running it) to start the development servers.

`dev.bat` offers the following options:

*   **`dev.bat` or `dev`:**
    *   Starts both the LedFx backend server and the frontend development server.
    *   This will typically open in a new Windows Terminal with a split view (if Windows Terminal is your default).
*   **`dev.bat backend` or `dev backend`:**
    *   Starts only the LedFx backend server.
*   **`dev.bat frontend` or `dev frontend`:**
    *   Starts only the frontend development server.

**Default URLs:**

*   LedFx Backend: `http://localhost:8888`
*   LedFx Frontend: `http://localhost:3000`

### Note for macOS and Linux Users

The `init.bat` and `dev.bat` scripts are Windows batch files and will not work directly on macOS or Linux. Users on these systems will need to perform the setup steps manually by inspecting the logic within these scripts. The general process involves:

1.  Cloning this `LedFx-Builds` repository.
2.  Manually cloning the `LedFx/LedFx` (backend) and `LedFx/LedFx-Frontend-v2` (frontend) repositories into a desired project directory.
3.  Creating and activating a Python virtual environment (e.g., using `python3 -m venv venv` and `source venv/bin/activate`).
4.  Installing Python dependencies using `pip install -r requirements.txt` (from the backend directory).
5.  Installing frontend dependencies using `yarn install` (from the frontend directory).
6.  Running the backend (e.g., `python ledfx_server.py` from the backend directory, though you'll need to adapt how configuration is loaded as `dev.bat` handles this).
7.  Running the frontend (e.g., `yarn start` from the frontend directory).

Refer to the contents of `init.bat` and `dev.bat` for more specific commands and configurations.

## Build Process

This section outlines how LedFx is packaged for distribution. The process leverages automation, specific build tools, and platform-tailored configurations.

### Automated Builds via GitHub Actions

The primary and recommended method for building LedFx is through the GitHub Actions workflows defined in the `.github/workflows/` directory of this repository.

*   These workflows automate the entire build pipeline, which includes:
    *   Fetching the latest code for both the backend and frontend.
    *   Setting up the build environment for Windows, macOS, and Linux.
    *   Running linters and tests (where configured).
    *   Packaging the application using tools like PyInstaller for the backend and standard web build processes for the frontend.
    *   Preparing distributable installers or application bundles.
*   Builds are typically triggered by pushes to specific branches (e.g., `main`, `dev`) or by creating new releases. Look for official builds on the main [LedFx project's releases page](https://github.com/LedFx/LedFx/releases).

### Build Tools and Configurations

The core of the build process relies on scripts and configuration files located primarily within the `tools/` directory:

*   **PyInstaller `.spec` files:** Files like `yzlinux.spec`, `mac.spec`, and `win.spec` are crucial configuration files for PyInstaller. PyInstaller is used to bundle the LedFx Python backend (along with its dependencies and assets) into standalone executables for each operating system. These spec files define how the bundling should occur, what files to include, and other platform-specific details.

*   **Platform-Specific Directories (`tools/linux/`, `tools/mac/`, `tools/win/`):** These directories contain resources tailored for each target operating system:
    *   **Helper Scripts:** Additional scripts that assist in the build process, such as those for code signing, creating installers, or setting up specific environments.
    *   **Pre-compiled Dependencies:** Certain dependencies, like specific versions of `aubio` (as Python wheels) or `libsamplerate`, might be included here. These are often components that are difficult to compile consistently across different environments or for which specific pre-built versions are required.
    *   **Patches:** Occasionally, patches for dependencies or build tools might be stored here to address specific issues encountered during the build for a particular OS.

### Manual Builds

While it is theoretically possible to perform builds manually by dissecting the GitHub Actions workflows and directly using the scripts and spec files found in the `tools/` directory, this approach is complex and not recommended for general use.

*   The automated workflows are carefully orchestrated and tested to ensure reliable and consistent builds.
*   Manually replicating this process would require a deep understanding of the build steps for each OS, managing dependencies, and correctly applying all configurations.
*   For development or custom builds, it's often more practical to use the development setup (`dev.bat` or equivalent) and, if needed, adapt the existing build scripts for specific modifications rather than starting from scratch.

### Output

The result of the build process, whether automated or manual, is a set of distributable artifacts for each targeted operating system:

*   **Windows:** Typically an installer (`.exe`).
*   **macOS:** A disk image (`.dmg`) containing the application bundle (`.app`).
*   **Linux:** Often a compressed archive (e.g., `.tar.gz` or `.zip`) containing the executable and necessary files, or sometimes a `.deb` or `.AppImage` package.

## Tools Overview

The `tools/` directory is a critical part of this repository, housing a collection of scripts, pre-compiled dependencies, and configuration files. These components are essential for supporting both the development setup and the build processes for LedFx across Windows, macOS, and Linux.

### Key Contents

*   **PyInstaller Spec Files:** At the root of the `tools/` directory (and sometimes within OS-specific subdirectories), you'll find `*.spec` files (e.g., `yzlinux.spec`, `mac.spec`, `win.spec`, `win-gh.spec`). These are configuration files used by PyInstaller, a tool that packages the LedFx Python backend application into standalone executables for different operating systems. They define what files, modules, and data to include, as well as various packaging options.

*   **Platform-Specific Subdirectories (`tools/linux/`, `tools/mac/`, `tools/win/`):** These directories contain resources specifically tailored for each operating system:
    *   **Pre-compiled Libraries:** To ensure compatibility and simplify the build process, certain libraries are provided in pre-compiled form. Examples include:
        *   `aubio` wheels (Python audio processing library)
        *   `libsamplerate.dylib` (for macOS, a sample rate converter library)
        *   `libportaudio64bit.dll` (for Windows, part of the PortAudio library for audio I/O)
    *   **Helper Scripts:** Each platform directory contains various scripts used during the build, packaging, or sometimes even development stages. These might include scripts for code signing, creating installers, environment setup, or specific build steps. For example, the `tools/win/` directory contains PowerShell scripts for version bumping (e.g., `version-bump-pre-release.ps1`, `version-bump-prod.ps1`).
    *   **Patches:** You may find patch files (e.g., `cors.patch`, `sentry.patch`) within these directories. These patches are applied to source code (either LedFx's own or that of its dependencies) during the setup or build process to address specific issues or enable certain functionalities.

*   **Development Helper Scripts:** While many helper scripts are platform-specific, some general-purpose tools or scripts that aid development might also reside in the `tools/` directory or its subdirectories.

### `tools/Readme.md`

For more specific details about the contents and usage of the items within the `tools/` directory, you can refer to the `tools/Readme.md` file. (Note: At the time of writing this main README, the `tools/Readme.md` might be minimal or outdated, so its usefulness may vary.)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
