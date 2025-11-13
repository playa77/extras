#!/usr/bin/env python3
# ============================================================================
# SCRIPT: md2pdf.py
# VERSION: 1.1
# DATE: 2025-11-13
#
# DESCRIPTION:
#   Markdown to PDF Converter with Serif Fonts.
#   This script converts Markdown files to beautifully formatted PDF documents
#   with serif fonts. It fully manages its own virtual environment and
#   dependencies, and cleans up after itself.
#
# USAGE:
#   python md2pdf.py <path_to_markdown_file.md>
#
# REQUIREMENTS:
#   - Python 3.9+
#   - Internet connection for downloading packages.
#   - System dependencies for WeasyPrint (the script will check for them).
#
# CHANGELOG (v1.1):
#   - Fixed bug where PDF was generated without content due to incorrect
#     f-string brace escaping in the temporary conversion script.
#   - Added overwrite protection: script now prompts user if output PDF exists.
#   - Improved system package check to be cross-platform (Linux, macOS, Windows).
#   - Reordered main logic to validate input and check for overwrites *before*
#     creating the virtual environment, allowing for a faster exit.
#   - Updated comments and terminal output for better clarity.
# ============================================================================

import sys
import os
import subprocess
import tempfile
import shutil
import signal
from pathlib import Path

# ============================================================================
# SCRIPT CONFIGURATION
# ============================================================================
SCRIPT_VERSION = "1.1"
VENV_DIR = ".md2pdf_venv"
REQUIRED_PACKAGES = [
    "weasyprint>=60.0",
    "markdown-it-py>=3.0.0",
]

# ============================================================================
# GLOBAL STATE FOR CLEANUP
# ============================================================================
# These globals are used to ensure cleanup happens even if the script exits
# unexpectedly (e.g., via Ctrl+C).
cleanup_required = False
venv_created = False


# ============================================================================
# SIGNAL HANDLER for Graceful Exit
# ============================================================================
def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully by triggering the cleanup process."""
    print("\n\n[INFO] Received interrupt signal (Ctrl+C).")
    print("[INFO] Cleaning up before exit...")
    cleanup_environment()
    print("[INFO] Cleanup complete. Exiting.")
    sys.exit(0)

# Register the signal handler for SIGINT (Ctrl+C)
signal.signal(signal.SIGINT, signal_handler)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================
def print_header(message):
    """Prints a formatted header to the console."""
    print(f"\n{'=' * 78}")
    print(f"  {message}")
    print(f"{'=' * 78}\n")


def print_step(step_num, total_steps, message):
    """Prints a formatted step message."""
    print(f"\n--- [STEP {step_num}/{total_steps}] {message} ---")


def run_command(cmd, description, check=True, capture_output=False):
    """
    Runs a shell command with verbose output and robust error handling.

    Args:
        cmd (list or str): The command to execute.
        description (str): A human-readable description of the command's purpose.
        check (bool): If True, raises CalledProcessError on a non-zero exit code.
        capture_output (bool): If True, captures and returns stdout/stderr.

    Returns:
        subprocess.CompletedProcess or None: The result object if capture_output is True.
    """
    print(f"[INFO] Executing: {description}...")
    try:
        if capture_output:
            result = subprocess.run(
                cmd,
                check=check,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            return result
        else:
            # For non-captured output, stream directly to the console
            subprocess.run(cmd, check=check)
            print(f"[SUCCESS] {description} completed.")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Task '{description}' failed with exit code {e.returncode}!")
        if e.stdout:
            print(f"[STDOUT] {e.stdout.strip()}")
        if e.stderr:
            print(f"[STDERR] {e.stderr.strip()}")
        raise
    except FileNotFoundError:
        print(f"[ERROR] Command '{cmd[0]}' not found. Is it in your PATH?")
        raise
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred during '{description}': {e}")
        raise


def check_system_packages():
    """
    Checks for WeasyPrint's system-level dependencies and provides instructions.
    This is a best-effort check and may not cover all distributions.
    """
    print("[INFO] Checking for WeasyPrint system dependencies...")

    if sys.platform.startswith('linux'):
        # For Debian/Ubuntu-based systems
        try:
            result = run_command(
                ["dpkg", "-s", "libpango-1.0-0"],
                "Checking for Pango library on Linux",
                capture_output=True
            )
            if "Status: install ok installed" in result.stdout:
                print("[SUCCESS] Found required system libraries for Linux.")
                return
        except (subprocess.CalledProcessError, FileNotFoundError):
            # dpkg might not be present or the package is not found
            pass # Fall through to the warning
        print("[WARNING] Could not confirm all system dependencies for WeasyPrint.")
        print("[WARNING] On Debian/Ubuntu, please ensure these are installed:")
        print("  sudo apt update && sudo apt install -y libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0")

    elif sys.platform == 'darwin': # macOS
        if shutil.which("brew"):
            print("[INFO] For macOS, WeasyPrint requires Pango, Cairo, and libffi.")
            print("[INFO] These can be installed with Homebrew:")
            print("  brew install pango cairo libffi")
        else:
            print("[WARNING] Homebrew not found. Please install WeasyPrint dependencies manually.")

    elif sys.platform == 'win32': # Windows
        print("[WARNING] For Windows, WeasyPrint requires an installation of GTK3.")
        print("[WARNING] Please follow the instructions at:")
        print("  https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows")

    else:
        print(f"[WARNING] Unsupported platform '{sys.platform}'. Please install WeasyPrint's system dependencies manually.")

    response = input("Do you want to continue anyway? (y/N): ")
    if response.lower() != 'y':
        print("[INFO] Exiting. Please install required packages first.")
        sys.exit(1)


def create_virtual_environment():
    """Creates a clean virtual environment for isolated package installation."""
    global venv_created
    if os.path.exists(VENV_DIR):
        print(f"[INFO] Removing existing virtual environment at '{VENV_DIR}'...")
        try:
            shutil.rmtree(VENV_DIR)
        except OSError as e:
            print(f"[ERROR] Failed to remove existing venv: {e}")
            print("[ERROR] Please remove the directory manually and try again.")
            raise
    run_command(
        [sys.executable, "-m", "venv", VENV_DIR],
        "Creating virtual environment"
    )
    venv_created = True
    print(f"[SUCCESS] Virtual environment created at '{VENV_DIR}'")


def get_venv_executable(name):
    """
    Gets the path to an executable (like python or pip) in the venv.

    Args:
        name (str): The name of the executable (e.g., "python").

    Returns:
        str: The full path to the executable.
    """
    if sys.platform == "win32":
        return os.path.join(VENV_DIR, "Scripts", f"{name}.exe")
    return os.path.join(VENV_DIR, "bin", name)


def install_dependencies():
    """Installs required Python packages into the virtual environment."""
    pip_path = get_venv_executable("pip")
    run_command(
        [pip_path, "install", "--upgrade", "pip"],
        "Upgrading pip"
    )
    for package in REQUIRED_PACKAGES:
        run_command(
            [pip_path, "install", package],
            f"Installing {package}"
        )
    print("[SUCCESS] All Python dependencies installed successfully.")


def validate_markdown_file(filepath):
    """
    Validates that the input file exists, is a file, and is readable.

    Args:
        filepath (str): Path to the markdown file.

    Returns:
        pathlib.Path: A Path object if the file is valid.
    """
    print(f"[INFO] Validating input file: '{filepath}'...")
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"The file '{filepath}' does not exist.")
    if not path.is_file():
        raise ValueError(f"The path '{filepath}' is a directory, not a file.")
    if not os.access(path, os.R_OK):
        raise PermissionError(f"The file '{filepath}' is not readable.")

    print(f"[SUCCESS] Input file is valid: {path.name} ({path.stat().st_size} bytes)")
    return path


def convert_markdown_to_pdf(md_path, output_path):
    """
    Converts the markdown file to a PDF using a temporary, isolated script
    that runs within the virtual environment.

    Args:
        md_path (pathlib.Path): Path to the source markdown file.
        output_path (pathlib.Path): Path for the generated PDF file.
    """
    python_path = get_venv_executable("python")

    # This script will be executed by the venv's Python interpreter,
    # ensuring it uses the packages we just installed.
    #
    # *** CRITICAL BUG FIX ***
    # The original script had a bug here. In an f-string, `{{` escapes to a
    # literal `{`. The original template placeholder `{{content}}` became
    # `{content}` in the generated script, which was not what the `.replace()`
    # call was looking for.
    # To get a literal `{{content}}` into the generated script, we must use
    # `{{{{content}}}}` in this outer f-string.
    conversion_script = f"""
import sys
from markdown_it import MarkdownIt
from weasyprint import HTML, CSS

try:
    # Configure markdown parser with common extensions
    md = MarkdownIt('commonmark', {{'breaks': True, 'html': True}}).enable(['table', 'strikethrough'])

    # Read markdown content from the source file
    md_filepath = r'{md_path}'
    print(f"[INFO] Reading content from {{md_filepath}}...")
    with open(md_filepath, 'r', encoding='utf-8') as f:
        md_content = f.read()

    print("[INFO] Parsing markdown to HTML...")
    html_content = md.render(md_content)

    # Create a complete HTML document with beautiful serif styling
    # Note the placeholder `{{{{content}}}}` which will be replaced.
    html_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Document</title>
</head>
<body>
{{{{content}}}}
</body>
</html>'''

    full_html = html_template.replace('{{{{content}}}}', html_content)

    # Custom CSS for professional, serif-based typography
    custom_css = '''
    @page {{
        size: A4;
        margin: 2.5cm 2cm;
        @bottom-center {{
            content: counter(page);
            font-family: "Liberation Serif", "Georgia", "Times New Roman", serif;
            font-size: 10pt;
            color: #666;
        }}
    }}
    body {{
        font-family: "Liberation Serif", "Georgia", "Times New Roman", serif;
        font-size: 11pt;
        line-height: 1.6;
        color: #333;
        text-align: justify;
        hyphens: auto;
    }}
    h1, h2, h3, h4, h5, h6 {{
        font-family: "Liberation Serif", "Georgia", "Times New Roman", serif;
        font-weight: bold;
        color: #1a1a1a;
        page-break-after: avoid;
        margin-top: 1.5em;
        margin-bottom: 0.5em;
    }}
    h1 {{ font-size: 24pt; margin-top: 0; border-bottom: 2px solid #333; padding-bottom: 0.3em; }}
    h2 {{ font-size: 20pt; border-bottom: 1px solid #666; padding-bottom: 0.2em; }}
    h3 {{ font-size: 16pt; }}
    h4 {{ font-size: 14pt; }}
    p {{ margin: 0.8em 0; }}
    a {{ color: #0066cc; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    code {{
        font-family: "Liberation Mono", "Courier New", monospace;
        font-size: 10pt;
        background-color: #f5f5f5;
        padding: 0.1em 0.3em;
        border-radius: 3px;
        border: 1px solid #e0e0e0;
    }}
    pre {{
        font-family: "Liberation Mono", "Courier New", monospace;
        font-size: 10pt;
        background-color: #f5f5f5;
        padding: 1em;
        border-radius: 5px;
        border: 1px solid #e0e0e0;
        overflow-x: auto;
        page-break-inside: avoid;
    }}
    pre code {{ background-color: transparent; padding: 0; border: none; }}
    blockquote {{
        font-style: italic;
        border-left: 4px solid #ccc;
        margin-left: 0;
        padding-left: 1em;
        color: #555;
    }}
    table {{
        width: 100%;
        border-collapse: collapse;
        margin: 1em 0;
        font-size: 10pt;
        page-break-inside: avoid;
    }}
    th, td {{ padding: 0.5em; border: 1px solid #ccc; }}
    th {{ background-color: #f0f0f0; font-weight: bold; text-align: left; }}
    tr:nth-child(even) {{ background-color: #fafafa; }}
    hr {{ border: none; border-top: 2px solid #ccc; margin: 2em 0; }}
    img {{ max-width: 100%; height: auto; display: block; margin: 1em auto; }}
    h1, h2, h3, h4, h5, h6 {{ page-break-after: avoid; }}
    p, blockquote, ul, ol {{ orphans: 3; widows: 3; }}
    '''

    output_filepath = r'{output_path}'
    print(f"[INFO] Generating PDF with WeasyPrint -> {{output_filepath}}")
    HTML(string=full_html).write_pdf(
        output_filepath,
        stylesheets=[CSS(string=custom_css)]
    )
    print("[SUCCESS] PDF generation complete.")

except Exception as e:
    import traceback
    print(f"[ERROR] PDF conversion failed inside the temporary script.")
    print(f"[ERROR] {{type(e).__name__}}: {{e}}")
    traceback.print_exc()
    sys.exit(1) # Ensure the subprocess exits with an error code
"""

    # Write the conversion script to a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        temp_script_path = f.name
        f.write(conversion_script)

    try:
        # Execute the temporary script using the venv's Python
        run_command(
            [python_path, temp_script_path],
            "Converting Markdown to PDF"
        )
    finally:
        # Ensure the temporary script is always cleaned up
        if os.path.exists(temp_script_path):
            os.unlink(temp_script_path)


def cleanup_environment():
    """Removes the virtual environment directory if it was created."""
    global cleanup_required, venv_created
    if not cleanup_required or not venv_created:
        return

    print("\n--- [CLEANUP] Removing virtual environment ---")
    if os.path.exists(VENV_DIR):
        try:
            shutil.rmtree(VENV_DIR)
            print(f"[SUCCESS] Removed virtual environment: '{VENV_DIR}'")
        except Exception as e:
            print(f"[WARNING] Failed to remove virtual environment: {e}")
            print(f"[WARNING] You may need to manually delete the directory: '{VENV_DIR}'")


# ============================================================================
# MAIN EXECUTION
# ============================================================================
def main():
    """Main execution function to orchestrate the conversion process."""
    global cleanup_required
    total_steps = 6

    print_header(f"Markdown to PDF Converter v{SCRIPT_VERSION}")

    # Check command-line arguments
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        print("Converts a Markdown file to a styled PDF.")
        print(f"\nUsage: python {Path(__file__).name} <path_to_markdown_file.md>")
        print("\nExample:")
        print(f"  python {Path(__file__).name} my-document.md")
        sys.exit(0)

    md_file_arg = sys.argv[1]

    try:
        # STEP 1: Validate input file and check for overwrite
        print_step(1, total_steps, "Validating Input and Output Files")
        md_path = validate_markdown_file(md_file_arg)
        output_pdf_path = md_path.with_suffix('.pdf')

        if output_pdf_path.exists():
            print(f"[WARNING] Output file '{output_pdf_path.name}' already exists.")
            response = input("              Do you want to overwrite it? (y/N): ")
            if response.lower() != 'y':
                print("[INFO] Aborting conversion. No files were changed.")
                sys.exit(0)
            print("[INFO] The existing file will be overwritten.")

        # STEP 2: Check system requirements
        print_step(2, total_steps, "Checking System Requirements")
        check_system_packages()

        # From this point on, cleanup will be required on exit
        cleanup_required = True

        # STEP 3: Create virtual environment
        print_step(3, total_steps, "Setting Up Virtual Environment")
        create_virtual_environment()

        # STEP 4: Install dependencies
        print_step(4, total_steps, "Installing Python Dependencies")
        install_dependencies()

        # STEP 5: Convert to PDF
        print_step(5, total_steps, "Converting Markdown to PDF")
        convert_markdown_to_pdf(md_path, output_pdf_path)

        # STEP 6: Cleanup
        print_step(6, total_steps, "Cleaning Up")
        cleanup_environment()

        # Final success message
        print_header("Conversion Complete!")
        print(f"[SUCCESS] PDF created: {output_pdf_path.resolve()}")
        print(f"[SUCCESS] File size: {output_pdf_path.stat().st_size:,} bytes")

    except (FileNotFoundError, PermissionError, ValueError) as e:
        print(f"\n[FATAL ERROR] Input file error: {e}")
        cleanup_environment()
        sys.exit(1)
    except subprocess.CalledProcessError:
        print("\n[FATAL ERROR] A command failed to execute. See details above.")
        cleanup_environment()
        sys.exit(1)
    except Exception as e:
        print(f"\n[FATAL ERROR] An unexpected error occurred:")
        print(f"[ERROR DETAILS] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        cleanup_environment()
        sys.exit(1)


if __name__ == "__main__":
    main()
