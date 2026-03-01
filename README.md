# PyQt Venv Manager: Feature Summary

The **PyQt Venv Manager** is a desktop application built with Python and PyQt6 designed to simplify the management of Python virtual environments and their associated projects.

## 🚀 Core Features

### 📦 Virtual Environment Management
- **Create New Environments**: Easily create new virtual environments using any installed Python 3 version.
- **Clone Environments**: Duplicate existing environments, including all installed packages, to quickly set up similar setups.
- **Delete Environments**: Remove unwanted virtual environments and their contents directly from the interface.
- **Disk Usage Visualization**: View the total disk space occupied by each environment (KB, MB, or GB).
- **Python Version Detection**: Automatically identifies the Python version used by each environment.

### 🛠 Package Management (Pip Integration)
- **Visual Package Manager**: A dedicated dialog to view, install, and uninstall packages.
- **Bootstrap Tools**: One-click update for core tools: `pip`, `setuptools`, and `wheel`.
- **Update Checks**: Identify outdated packages within an environment.
- **System Site-Package Toggle**: Enable or disable access to global system packages for specific environments.
- **Requirements Support**:
    - **Import**: Install multiple packages from a `requirements.txt` file.
    - **Export**: Save current environment's package list to a `requirements.txt` file (with option to include/exclude system packages).
- **Activity Console**: Real-time feedback from `pip` commands within the application.

### 📁 Project Integration
- **Folder Linking**: Link one or multiple project folders to a specific virtual environment.
- **Quick Terminal Access**: Open a pre-configured terminal (Bash) with the environment already activated in the project directory.
- **Direct Script Execution**: Run Python scripts directly using the environment's interpreter without leaving the app.

## 🎨 User Experience
- **Search & Filter**: Quickly find environments or linked projects using the dynamic search bar.
- **Persistent Settings**: Configurable default storage path for virtual environments.
- **Visual Feedback**: Clean, modern UI with "cards" for each environment, providing status at a glance.
- **Multi-Terminal Support**: Automatically detects and uses available terminal emulators (Konsole, GNOME Terminal, etc.).

![Screenshot 1](https://github.com/my-names-dave/PyQt-Venv-Manager/blob/main/Screenshot1.png)

![Screenshot 2](https://github.com/my-names-dave/PyQt-Venv-Manager/blob/main/Screenshot2.png)
